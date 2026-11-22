#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditoría HTTP/SEO de Almendras de Málaga (GitHub Pages).
Uso:
  python seo_audit_production.py
  python seo_audit_production.py --workers 8 --timeout 20
  python seo_audit_production.py --max-links 0  # comprobar todos los enlaces internos
"""

import argparse
import csv
import json
import re
import sys
import time
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = "https://jmlopez0211-web.github.io/almendras-de-malaga/"
SITEMAP_URL = urljoin(BASE, "sitemap.xml")
ROBOTS_URL = urljoin(BASE, "robots.txt")
USER_AGENT = "AlmendrasDeMalaga-SEO-Audit/1.0 (+production-audit)"
_thread_local = threading.local()


def get_opener():
    if not hasattr(_thread_local, "opener"):
        from urllib.request import build_opener
        _thread_local.opener = build_opener()
    return _thread_local.opener


def request_url(url, timeout=20, method="GET", max_bytes=None):
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    req = Request(url, headers=headers, method=method)
    started = time.time()
    try:
        with get_opener().open(req, timeout=timeout) as response:
            status = response.status
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
            body = b""
            if method != "HEAD":
                body = response.read(max_bytes or 5_000_000)
            return {
                "status": status, "final_url": final_url,
                "content_type": content_type, "body": body,
                "error": None, "elapsed_ms": round((time.time()-started)*1000)
            }
    except HTTPError as e:
        body = b""
        try:
            body = e.read(max_bytes or 1_000_000)
        except Exception:
            pass
        return {
            "status": e.code, "final_url": e.geturl(),
            "content_type": e.headers.get("Content-Type", "") if e.headers else "",
            "body": body, "error": f"HTTPError {e.code}",
            "elapsed_ms": round((time.time()-started)*1000)
        }
    except Exception as e:
        return {
            "status": None, "final_url": url, "content_type": "",
            "body": b"", "error": f"{type(e).__name__}: {e}",
            "elapsed_ms": round((time.time()-started)*1000)
        }


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = []
        self.in_title = False
        self.meta = {}
        self.canonical = []
        self.og = {}
        self.twitter = {}
        self.jsonld = []
        self.links = []
        self.h1 = []
        self.h1_count = 0
        self.in_h1 = False
        self._jsonld_parts = []
        self._in_jsonld = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.in_h1 = True
            self.h1_count += 1
        elif tag == "meta":
            name = (attrs.get("name") or "").lower()
            prop = (attrs.get("property") or "").lower()
            content = attrs.get("content", "")
            if name:
                self.meta[name] = content
            if prop.startswith("og:"):
                self.og[prop] = content
            if name.startswith("twitter:"):
                self.twitter[name] = content
        elif tag == "link":
            rel = (attrs.get("rel") or "").lower().split()
            href = attrs.get("href")
            if href and "canonical" in rel:
                self.canonical.append(href)
            if href:
                self.links.append({"href": href, "text": "", "rel": attrs.get("rel", "")})
        elif tag == "a":
            href = attrs.get("href")
            if href:
                self.links.append({"href": href, "text": "", "rel": attrs.get("rel", "")})
        elif tag == "script" and (attrs.get("type") or "").lower() == "application/ld+json":
            self._in_jsonld = True
            self._jsonld_parts = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif tag == "h1":
            self.in_h1 = False
        elif tag == "script" and self._in_jsonld:
            self._in_jsonld = False
            raw = "".join(self._jsonld_parts).strip()
            self.jsonld.append(raw)

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)
        if self.in_h1:
            self.h1.append(data)
        if self._in_jsonld:
            self._jsonld_parts.append(data)


def parse_html(body):
    parser = PageParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    return parser


def flatten_schema(schema):
    if isinstance(schema, dict):
        typ = schema.get("@type")
        if isinstance(typ, list):
            return typ
        return [typ] if typ else []
    if isinstance(schema, list):
        result = []
        for item in schema:
            result.extend(flatten_schema(item))
        return result
    return []


def check_schema(raw_blocks):
    parsed = []
    errors = []
    types = []
    for i, raw in enumerate(raw_blocks, 1):
        try:
            value = json.loads(raw)
            parsed.append(value)
            types.extend(flatten_schema(value))
        except Exception as e:
            errors.append(f"JSON-LD block {i}: {e}")
    return parsed, errors, sorted(set(types))


def normalize_url(url):
    url = urldefrag(url)[0]
    return url.rstrip("/") if url.endswith("/") and urlparse(url).path not in ("", "/") else url


def is_internal(url):
    p = urlparse(url)
    basep = urlparse(BASE)
    return p.scheme in ("http", "https") and p.netloc.lower() == basep.netloc.lower()


def get_sitemap_urls(timeout):
    result = request_url(SITEMAP_URL, timeout=timeout)
    if result["status"] != 200:
        raise RuntimeError(f"Sitemap no accesible: HTTP {result['status']} / {result['error']}")
    import xml.etree.ElementTree as ET
    root = ET.fromstring(result["body"])
    urls = []
    for elem in root.iter():
        if elem.tag.lower().endswith("loc") and elem.text:
            urls.append(elem.text.strip())
    return result, sorted(set(urls))


def audit_page(url, timeout):
    response = request_url(url, timeout=timeout)
    row = {
        "url": url, "status": response["status"], "final_url": response["final_url"],
        "redirected": response["final_url"] != url,
        "content_type": response["content_type"],
        "elapsed_ms": response["elapsed_ms"], "error": response["error"],
        "title": "", "title_length": 0, "meta_description": "",
        "meta_description_length": 0, "canonical": "", "canonical_count": 0,
        "canonical_ok": False, "h1": "", "h1_count": 0,
        "og_title": "", "og_description": "", "og_url": "",
        "twitter_title": "", "twitter_description": "",
        "jsonld_blocks": 0, "jsonld_valid": True, "jsonld_errors": "",
        "schema_types": "", "has_product_schema": False,
        "has_breadcrumb_schema": False, "has_faq_schema": False,
        "internal_links": 0, "external_links": 0, "links": [],
        "issues": []
    }
    if response["status"] != 200:
        row["issues"].append(f"HTTP {response['status'] or 'ERROR'}")
        return row

    parser = parse_html(response["body"])
    title = " ".join("".join(parser.title).split())
    description = parser.meta.get("description", "").strip()
    canonical = parser.canonical[0] if parser.canonical else ""
    h1s = [" ".join("".join(parser.h1).split())] if parser.h1 else []

    row.update({
        "title": title, "title_length": len(title),
        "meta_description": description, "meta_description_length": len(description),
        "canonical": canonical, "canonical_count": len(parser.canonical),
        "canonical_ok": bool(canonical and normalize_url(canonical) == normalize_url(url)),
        "h1": h1s[0] if h1s else "", "h1_count": parser.h1_count,
        "og_title": parser.og.get("og:title", ""),
        "og_description": parser.og.get("og:description", ""),
        "og_url": parser.og.get("og:url", ""),
        "twitter_title": parser.twitter.get("twitter:title", ""),
        "twitter_description": parser.twitter.get("twitter:description", ""),
        "jsonld_blocks": len(parser.jsonld)
    })

    parsed, schema_errors, schema_types = check_schema(parser.jsonld)
    row["jsonld_valid"] = not schema_errors
    row["jsonld_errors"] = " | ".join(schema_errors)
    row["schema_types"] = ", ".join(schema_types)
    row["has_product_schema"] = "Product" in schema_types
    row["has_breadcrumb_schema"] = "BreadcrumbList" in schema_types
    row["has_faq_schema"] = "FAQPage" in schema_types

    links = []
    for link in parser.links:
        href = link["href"].strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = urljoin(response["final_url"], href)
        absolute = urldefrag(absolute)[0]
        if is_internal(absolute):
            row["internal_links"] += 1
            links.append(absolute)
        else:
            row["external_links"] += 1
    row["links"] = sorted(set(links))

    if not title:
        row["issues"].append("Falta <title>")
    if not description:
        row["issues"].append("Falta meta description")
    elif len(description) < 70:
        row["issues"].append("Meta description corta (<70)")
    elif len(description) > 170:
        row["issues"].append("Meta description larga (>170)")
    if not canonical:
        row["issues"].append("Falta canonical")
    elif not row["canonical_ok"]:
        row["issues"].append("Canonical no coincide con URL")
    if len(parser.canonical) > 1:
        row["issues"].append("Canonical duplicado")
    if not h1s:
        row["issues"].append("Falta H1")
    elif parser.h1_count > 1:
        row["issues"].append(f"Hay {parser.h1_count} H1")
    if not parser.jsonld:
        row["issues"].append("Sin JSON-LD")
    if schema_errors:
        row["issues"].append("JSON-LD inválido")
    if urlparse(url).path.startswith("/almendras-de-malaga/productos/") and not row["has_product_schema"]:
        row["issues"].append("Ficha sin Schema Product")
    if not row["has_breadcrumb_schema"]:
        row["issues"].append("Sin BreadcrumbList")
    return row


def check_link(url, timeout):
    r = request_url(url, timeout=timeout, method="HEAD")
    # GitHub Pages / hosting can reject HEAD; retry with GET.
    if r["status"] in (403, 405, 501) or r["status"] is None:
        r = request_url(url, timeout=timeout, method="GET", max_bytes=100_000)
    return {
        "url": url, "status": r["status"], "final_url": r["final_url"],
        "error": r["error"], "elapsed_ms": r["elapsed_ms"]
    }


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_html(report):
    pages = report["pages"]
    links = report["links"]
    def esc(x):
        return (str(x or "").replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))
    page_rows = []
    for p in pages:
        issues = "; ".join(p["issues"])
        page_rows.append(
            "<tr><td><a href='{u}'>{u}</a></td><td>{s}</td><td>{t}</td>"
            "<td>{c}</td><td>{d}</td><td>{j}</td><td>{i}</td></tr>".format(
                u=esc(p["url"]), s=esc(p["status"]), t=esc(p["title"]),
                c=esc(p["canonical"]), d=esc(p["meta_description"]),
                j=esc(p["schema_types"]), i=esc(issues)))
    link_rows = [
        f"<tr><td><a href='{esc(x['url'])}'>{esc(x['url'])}</a></td><td>{esc(x['status'])}</td><td>{esc(x['error'])}</td></tr>"
        for x in links
    ]
    summary = report["summary"]
    return f"""<!doctype html><html lang="es"><meta charset="utf-8">
<title>Auditoría SEO HTTP - Almendras de Málaga</title>
<style>
body{{font-family:system-ui,Arial,sans-serif;margin:24px;color:#222}}
h1,h2{{margin-top:1.6em}}.cards{{display:flex;flex-wrap:wrap;gap:12px}}
.card{{border:1px solid #ddd;border-radius:10px;padding:14px;min-width:140px}}
.card strong{{font-size:1.5em;display:block}}table{{border-collapse:collapse;width:100%;margin:18px 0}}
th,td{{border:1px solid #ddd;padding:8px;vertical-align:top;text-align:left;word-break:break-word}}
th{{background:#eee;position:sticky;top:0}}.bad{{color:#b00020}}.good{{color:#137333}}
</style><h1>Auditoría HTTP/SEO de producción</h1>
<p>Generado: {esc(report['generated_at'])}</p>
<div class="cards">{''.join(f'<div class="card"><strong>{esc(v)}</strong>{esc(k)}</div>' for k,v in summary.items())}</div>
<h2>URLs del sitemap</h2><table><thead><tr><th>URL</th><th>HTTP</th><th>Title</th><th>Canonical</th><th>Meta description</th><th>Schema</th><th>Problemas</th></tr></thead><tbody>{''.join(page_rows)}</tbody></table>
<h2>Enlaces internos comprobados</h2><table><thead><tr><th>URL</th><th>HTTP</th><th>Error</th></tr></thead><tbody>{''.join(link_rows)}</tbody></table></html>"""


def main():
    ap = argparse.ArgumentParser(description="Auditoría real HTTP/SEO de GitHub Pages.")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--max-links", type=int, default=0, help="0 = comprobar todos los enlaces internos únicos")
    ap.add_argument("--output", default="seo-production-audit")
    args = ap.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    prefix = f"{args.output}-{timestamp}"
    print(f"Auditoría de: {BASE}")
    print("Comprobando sitemap y robots.txt...")

    sitemap_response, urls = get_sitemap_urls(args.timeout)
    robots_response = request_url(ROBOTS_URL, timeout=args.timeout)
    print(f"Sitemap HTTP: {sitemap_response['status']} | URLs: {len(urls)}")
    print(f"Robots HTTP: {robots_response['status']}")

    print(f"Analizando {len(urls)} páginas...")
    pages = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(audit_page, u, args.timeout): u for u in urls}
        for i, future in enumerate(as_completed(futures), 1):
            row = future.result()
            pages.append(row)
            if i % 10 == 0 or i == len(urls):
                print(f"  {i}/{len(urls)} páginas procesadas")
    pages.sort(key=lambda x: x["url"])

    all_links = sorted(set(link for page in pages for link in page["links"]))
    if args.max_links and args.max_links > 0:
        all_links = all_links[:args.max_links]
    print(f"Comprobando {len(all_links)} enlaces internos únicos...")
    link_results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(check_link, u, args.timeout): u for u in all_links}
        for i, future in enumerate(as_completed(futures), 1):
            link_results.append(future.result())
            if i % 25 == 0 or i == len(all_links):
                print(f"  {i}/{len(all_links)} enlaces comprobados")
    link_results.sort(key=lambda x: x["url"])

    page_status = Counter(str(p["status"]) for p in pages)
    issue_count = sum(len(p["issues"]) for p in pages)
    broken_links = [x for x in link_results if x["status"] != 200]
    bad_pages = [p for p in pages if p["status"] != 200]
    duplicate_titles = [x for x, c in Counter(p["title"] for p in pages if p["title"]).items() if c > 1]
    duplicate_descriptions = [x for x, c in Counter(p["meta_description"] for p in pages if p["meta_description"]).items() if c > 1]
    duplicate_canonicals = [x for x, c in Counter(p["canonical"] for p in pages if p["canonical"]).items() if c > 1]

    summary = {
        "Sitemap URLs": len(urls),
        "Pages HTTP 200": page_status.get("200", 0),
        "Pages non-200": len(bad_pages),
        "Pages with issues": sum(bool(p["issues"]) for p in pages),
        "Total SEO issues": issue_count,
        "Internal links checked": len(link_results),
        "Broken internal links": len(broken_links),
        "Duplicate titles": len(duplicate_titles),
        "Duplicate descriptions": len(duplicate_descriptions),
        "Duplicate canonicals": len(duplicate_canonicals),
        "Sitemap HTTP": sitemap_response["status"],
        "Robots HTTP": robots_response["status"],
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base": BASE,
        "sitemap": {"url": SITEMAP_URL, "status": sitemap_response["status"], "error": sitemap_response["error"], "url_count": len(urls)},
        "robots": {"url": ROBOTS_URL, "status": robots_response["status"], "body": robots_response["body"].decode("utf-8", errors="replace")},
        "summary": summary,
        "pages": pages,
        "links": link_results,
        "duplicates": {
            "titles": duplicate_titles,
            "meta_descriptions": duplicate_descriptions,
            "canonicals": duplicate_canonicals
        },
        "bad_pages": bad_pages,
        "broken_links": broken_links
    }

    json_path = prefix + ".json"
    csv_path = prefix + "-pages.csv"
    links_csv = prefix + "-links.csv"
    html_path = prefix + ".html"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    write_csv(csv_path, pages, [
        "url","status","final_url","redirected","title","title_length",
        "meta_description","meta_description_length","canonical","canonical_count",
        "canonical_ok","h1","h1_count","og_title","og_description","og_url",
        "twitter_title","twitter_description","jsonld_blocks","jsonld_valid",
        "jsonld_errors","schema_types","has_product_schema","has_breadcrumb_schema",
        "has_faq_schema","internal_links","external_links","elapsed_ms","error","issues"
    ])
    write_csv(links_csv, link_results, ["url","status","final_url","error","elapsed_ms"])
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(build_html(report))

    print("\n===== RESUMEN =====")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print("\nArchivos generados:")
    print(f"  {json_path}")
    print(f"  {csv_path}")
    print(f"  {links_csv}")
    print(f"  {html_path}")
    print("\nErrores HTTP de páginas:")
    for p in bad_pages:
        print(f"  {p['status']} {p['url']} {p['error']}")
    print("\nEnlaces rotos:")
    for l in broken_links:
        print(f"  {l['status']} {l['url']} {l['error']}")
    print("\nProblemas SEO:")
    for p in pages:
        if p["issues"]:
            print(f"  {p['url']}")
            for issue in p["issues"]:
                print(f"    - {issue}")

    if bad_pages or broken_links or issue_count:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
