#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Almendras de Málaga — image candidate batch pipeline v6.

Reads data/catalog.js; searches Wikimedia Commons and Openverse; filters obvious
irrelevant search results; tries original image URL first, then thumbnail; saves
state/report/manifest after each product. Never changes catalog or approves images.
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys, time
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/catalog.js"
OUT = ROOT / "assets/images/candidates"
STATE = ROOT / "docs/candidate_batch_state.json"
REPORT = ROOT / "docs/candidate_batch_report.json"
MANIFEST = ROOT / "photo_candidates_next.json"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
OPENVERSE_API = "https://api.openverse.org/v1/images/"
UA = "AlmendrasDeMalagaCatalogPhotoAudit/6.0"
TIMEOUT = (8, 22)
ALLOWED = {"image/jpeg", "image/png", "image/webp"}
MIN_W, MIN_H, MAX_BYTES = 900, 700, 25 * 1024 * 1024

PRODUCT_SEARCH = {
    "mangoDeshidratado": ["dried mango slices", "dried mango pieces", "dehydrated mango fruit"],
    "almendraFritaGirasol": ["fried almonds nuts", "fried almond kernels", "almonds fried snack"],
    "almendraFritaSinSal": ["unsalted fried almonds", "plain fried almonds", "fried almond kernels"],
    "cacahueteFritoRepeladoSinSal": ["fried shelled peanuts", "fried blanched peanuts", "unsalted fried peanuts"],
    "cacahueteTostadoRepeladoSinSal": ["roasted shelled peanuts", "roasted blanched peanuts", "dry roasted peanuts"],
    "anacardoFritoSinSal": ["fried cashew nuts", "fried cashews snack", "plain fried cashew kernels"],
}

CORE_TERMS = {
    "mangoDeshidratado": ["mango", "mangos"],
    "almendraFritaGirasol": ["almond", "almonds", "almendra", "almendras", "badam", "mandeln", "mandel"],
    "almendraFritaSinSal": ["almond", "almonds", "almendra", "almendras", "badam", "mandeln", "mandel"],
    "cacahueteFritoRepeladoSinSal": ["peanut", "peanuts", "cacahuete", "cacahuetes", "groundnut", "arachis"],
    "cacahueteTostadoRepeladoSinSal": ["peanut", "peanuts", "cacahuete", "cacahuetes", "groundnut", "arachis"],
    "anacardoFritoSinSal": ["cashew", "cashews", "anacardo", "anacardos", "kaju"],
}
NEGATIVE_PHRASES = [
    "menu", "banquet", "breakfast", "restaurant", "chicken", "trout", "rice",
    "noodles", "eggplant", "shrimp", "prawn", "salad", "stir fry", "curry",
    "tart", "cake", "dessert", "ice cream", "yogurt", "tofu", "recipe",
    "cooking class", "food blogger", "man frying", "woman frying",
    "person cooking", "chef preparing"
]

class RateLimited(Exception):
    def __init__(self, source):
        self.source = source
        super().__init__(f"HTTP 429 en {source}")

def read_catalog():
    text = CATALOG.read_text(encoding="utf-8")
    text = re.sub(r"^\s*window\.PRODUCTS\s*=\s*", "", text).strip().removesuffix(";")
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("data/catalog.js no contiene window.PRODUCTS válido")
    return obj

def missing_products():
    return [(k, v.get("name", k)) for k, v in read_catalog().items()
            if not str(v.get("image") or "").strip()]

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default

def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.flush()
    tmp.replace(path)

def request_json(url, params, source):
    try:
        r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=TIMEOUT)
    except requests.RequestException as e:
        return None, {"source": source, "status": "NETWORK_ERROR", "error": str(e)[:500]}
    if r.status_code == 429:
        raise RateLimited(source)
    if r.status_code in (401, 403):
        return None, {"source": source, "status": "SOURCE_BLOCKED", "http": r.status_code}
    if not r.ok:
        return None, {"source": source, "status": "HTTP_ERROR", "http": r.status_code,
                      "body": r.text[:180]}
    try:
        return r.json(), None
    except ValueError:
        return None, {"source": source, "status": "BAD_JSON"}

def commons_search(query):
    data, err = request_json(COMMONS_API, {
        "action": "query", "format": "json", "list": "search",
        "srsearch": query, "srnamespace": 6, "srlimit": 10
    }, "Wikimedia Commons")
    if err:
        return [], err
    titles = [x.get("title") for x in data.get("query", {}).get("search", []) if x.get("title")]
    if not titles:
        return [], None
    data, err = request_json(COMMONS_API, {
        "action": "query", "format": "json", "titles": "|".join(titles),
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1280
    }, "Wikimedia Commons")
    if err:
        return [], err
    found = []
    for page in data.get("query", {}).get("pages", {}).values():
        ii = (page.get("imageinfo") or [{}])[0]
        mime = (ii.get("mime") or "").lower()
        if mime not in ALLOWED:
            continue
        meta = ii.get("extmetadata") or {}
        title = page.get("title", "").replace("File:", "")
        found.append({
            "source": "Wikimedia Commons", "title": title,
            "url": ii.get("url"), "thumbnail": ii.get("thumburl"),
            "mime": mime, "width": ii.get("width"), "height": ii.get("height"),
            "license": (meta.get("LicenseShortName") or {}).get("value", ""),
            "license_url": (meta.get("LicenseUrl") or {}).get("value", ""),
            "artist": (meta.get("Artist") or {}).get("value", ""),
            "source_page": "https://commons.wikimedia.org/wiki/" + quote(page.get("title", "").replace(" ", "_"))
        })
    return found, None

def openverse_search(query):
    data, err = request_json(OPENVERSE_API, {
        "q": query, "page_size": 20, "mature": "false",
        "license": "cc0,by,by-sa"
    }, "Openverse")
    if err:
        return [], err
    found = []
    for item in data.get("results", []):
        found.append({
            "source": "Openverse", "title": item.get("title", ""),
            "url": item.get("url"), "thumbnail": item.get("thumbnail"),
            "mime": item.get("mimetype") or item.get("mime_type"),
            "width": item.get("width"), "height": item.get("height"),
            "license": item.get("license"), "license_version": item.get("license_version"),
            "license_url": item.get("license_url"), "artist": item.get("creator"),
            "source_page": item.get("foreign_landing_url") or item.get("detail_url"),
            "tags": [x.get("name", "") for x in item.get("tags", []) if isinstance(x, dict)]
        })
    return found, None

def candidate_score(key, candidate):
    text = " ".join([
        str(candidate.get("title") or ""),
        " ".join(candidate.get("tags") or []),
        str(candidate.get("commons_title") or "")
    ]).lower()
    core = CORE_TERMS.get(key, [])
    if not any(term in text for term in core):
        return -100, ["missing_product_keyword"]
    score = 4
    reasons = ["product_keyword_match"]
    negatives = [phrase for phrase in NEGATIVE_PHRASES if phrase in text]
    if negatives:
        score -= 8
        reasons.append("irrelevant_context:" + ",".join(negatives))
    # Reward close-up/isolated product wording and exact preparation terms, but never
    # infer salt/oil from a generic nut photo.
    if any(x in text for x in ("close up", "close-up", "isolated", "kernels", "nuts")):
        score += 1
        reasons.append("product_focus_term")
    if key == "mangoDeshidratado" and any(x in text for x in ("dried", "dehydrated", "sun-dried")):
        score += 2
        reasons.append("dried_match")
    if any(token in key.lower() for token in ("frita", "frito")):
        if any(x in text for x in ("fried", "frying", "fritas", "fritos")):
            score += 2
            reasons.append("fried_match")
        else:
            score -= 2
            reasons.append("preparation_not_confirmed")
    if "tostado" in key.lower():
        if "roasted" in text or "tostado" in text or "tostada" in text:
            score += 2
            reasons.append("roasted_match")
        else:
            score -= 2
            reasons.append("preparation_not_confirmed")
    return score, reasons

def build_queries(key, name):
    terms = [name]
    terms.extend(PRODUCT_SEARCH.get(key, []))
    seen, result = set(), []
    for term in terms:
        term = term.strip()
        if term and term.lower() not in seen:
            result.append(term)
            seen.add(term.lower())
    return result[:4]

def normalize_legacy_candidate(candidate):
    """Adapt candidates saved by v4 (where `url` was often the thumbnail)."""
    item = dict(candidate)
    source = (item.get("source") or "").lower()
    if item.get("original_url"):
        if "openverse" in source:
            item["thumbnail"] = item.get("thumbnail") or item.get("url")
            item["url"] = item.get("original_url")
        elif "wikimedia" in source:
            item["thumbnail"] = item.get("thumbnail") or item.get("url")
            item["url"] = item.get("original_url")
    return item

def filter_and_rank(key, candidates):
    ranked, seen = [], set()
    for raw in candidates:
        candidate = normalize_legacy_candidate(raw)
        unique_key = candidate.get("url") or candidate.get("thumbnail")
        if not unique_key or unique_key in seen:
            continue
        seen.add(unique_key)
        score, reasons = candidate_score(key, candidate)
        candidate["relevance_score"] = score
        candidate["relevance_reasons"] = reasons
        if score >= 4:
            ranked.append(candidate)
    ranked.sort(key=lambda x: x.get("relevance_score", -100), reverse=True)
    return ranked

def search_product(key, name, delay, commons_blocked):
    all_candidates, errors = [], []
    commons_available = False
    openverse_available = False
    if commons_blocked:
        errors.append({"source": "Wikimedia Commons", "status": "COOLDOWN",
                       "error": "Commons se omite temporalmente tras HTTP 429 previo"})

    # Search Commons with multiple focused terms. A 429 disables Commons for
    # the remainder of this run; it does not prevent Openverse fallback.
    if not commons_blocked:
        for query in build_queries(key, name):
            found, err = [], None
            try:
                found, err = commons_search(query)
            except RateLimited as exc:
                errors.append({"source": "Wikimedia Commons", "status": "RATE_LIMITED", "error": str(exc)})
                commons_blocked = True
                break
            if err:
                errors.append(err)
                if err.get("status") in ("NETWORK_ERROR", "SOURCE_BLOCKED"):
                    break
            else:
                commons_available = True
                all_candidates.extend(found)
            if delay:
                time.sleep(delay)
            # Stop early only when this query supplies a relevant result.
            if filter_and_rank(key, all_candidates):
                break

    # Query Openverse if Commons was unavailable or its results were irrelevant.
    if not filter_and_rank(key, all_candidates):
        for query in build_queries(key, name):
            try:
                found, err = openverse_search(query)
            except RateLimited as exc:
                errors.append({"source": "Openverse", "status": "RATE_LIMITED", "error": str(exc)})
                break
            if err:
                errors.append(err)
                if err.get("status") in ("NETWORK_ERROR", "SOURCE_BLOCKED"):
                    break
            else:
                openverse_available = True
                all_candidates.extend(found)
            if delay:
                time.sleep(delay)
            if filter_and_rank(key, all_candidates):
                break

    ranked = filter_and_rank(key, all_candidates)
    if ranked:
        status = "CANDIDATES_FOUND"
    elif errors and not (commons_available and openverse_available):
        status = "SOURCE_ERROR"
    elif commons_available and openverse_available:
        status = "NO_RESULTS_RELEVANT"
    else:
        status = "INCOMPLETE_SEARCH"
    return ranked, errors, status, commons_blocked

def download_candidate(key, candidate):
    OUT.mkdir(parents=True, exist_ok=True)
    urls = []
    original = candidate.get("url")
    thumbnail = candidate.get("thumbnail")
    for u in (original, thumbnail):
        # Openverse API thumbnail endpoints can return 424 Failed Dependency.
        # Never use its /thumb/ API endpoint as a file source; use original URL.
        if u and "api.openverse.org/v1/images/" in u and u.rstrip("/").endswith("/thumb"):
            continue
        if u and u not in urls:
            urls.append(u)
    errors = []
    for url in urls:
        if urlparse(url).scheme not in ("http", "https"):
            errors.append({"url": url, "error": "invalid_url_scheme"})
            continue
        try:
            with requests.get(url, headers={"User-Agent": UA}, stream=True, timeout=TIMEOUT) as response:
                if response.status_code == 429:
                    errors.append({"url": url, "error": "HTTP 429"})
                    continue
                if response.status_code in (403, 404, 410):
                    errors.append({"url": url, "error": f"HTTP {response.status_code}"})
                    continue
                response.raise_for_status()
                content_type = (response.headers.get("Content-Type") or "").split(";")[0].lower()
                data_parts, size = [], 0
                for chunk in response.iter_content(65536):
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ValueError("image_over_25MB")
                    data_parts.append(chunk)
                data = b"".join(data_parts)
            img = Image.open(BytesIO(data))
            img.verify()
            img = Image.open(BytesIO(data))
            if img.format not in ("JPEG", "PNG", "WEBP"):
                raise ValueError(f"unsupported_image_format:{img.format}")
            if img.width < MIN_W or img.height < MIN_H:
                raise ValueError(f"low_resolution:{img.width}x{img.height}")
            ext = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[img.format]
            target = OUT / (re.sub(r"[^A-Za-z0-9_-]", "_", key) + "-candidate" + ext)
            target.write_bytes(data)
            warnings = []
            if any(x in key.lower() for x in ("sinsal", "sin_sal", "girasol", "oliva")):
                warnings.append("La foto no permite verificar ausencia de sal ni tipo de aceite; requiere confirmación documental.")
            return {
                "status": "DOWNLOADED_UNVERIFIED", "path": target.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(), "bytes": size,
                "width": img.width, "height": img.height, "format": img.format,
                "content_type": content_type, "used_url": url, "url_errors": errors,
                "variant_warnings": warnings
            }
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)[:300]})
            continue
    return {"status": "DOWNLOAD_FAILED", "url_errors": errors}

def main():
    ap = argparse.ArgumentParser(description="Search and download unapproved product-image candidates")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--delay", type=float, default=2)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--retry-no-candidates", action="store_true")
    ap.add_argument("--include-mango", action="store_true")
    ap.add_argument("--recheck-downloaded", action="store_true",
                    help="Volver a buscar y revisar productos ya descargados por versiones anteriores")
    ap.add_argument("--diagnose", action="store_true")
    args = ap.parse_args()
    if args.diagnose:
        for source, url, params in [
            ("Wikimedia Commons", COMMONS_API, {"action":"query","format":"json","meta":"siteinfo"}),
            ("Openverse", OPENVERSE_API, {"q":"dried mango","page_size":1})
        ]:
            _, error = request_json(url, params, source)
            print(f"{source}: {error if error else 'HTTP 200'}")
        return 0

    products = missing_products()
    state = load_json(STATE, {"processed": {}, "commons_blocked_until": 0})
    processed = state.setdefault("processed", {})
    state["schema_version"] = 6
    blocked_until = float(state.get("commons_blocked_until", 0) or 0)
    commons_blocked = blocked_until > time.time()

    if args.include_mango:
        cat = read_catalog()
        mango = ("mangoDeshidratado", cat.get("mangoDeshidratado", {}).get("name", "Mango deshidratado"))
        products = [mango] + [x for x in products if x[0] != mango[0]]
    if args.resume:
        retry = {"SOURCE_ERROR", "INCOMPLETE_SEARCH", "DOWNLOAD_FAILED",
                 "CANDIDATES_FOUND_DOWNLOAD_FAILED", "RATE_LIMITED", "NO_CANDIDATES",
                 "NO_RESULTS_RELEVANT", "CANDIDATES_FOUND_DOWNLOAD_FAILED"}
        products = [(k, n) for k, n in products
                    if k not in processed or processed[k].get("status") in retry
                    or (args.recheck_downloaded and processed[k].get("status") == "DOWNLOADED_UNVERIFIED")]
    else:
        products = products[max(0, args.start):]
    batch = products[:max(1, args.limit)]

    manifest = load_json(MANIFEST, [])
    if not isinstance(manifest, list):
        manifest = []
    manifest_map = {x.get("product_key"): x for x in manifest if isinstance(x, dict)}
    report = load_json(REPORT, [])
    if not isinstance(report, list):
        report = []
    report_map = {x.get("product_key"): x for x in report if isinstance(x, dict)}

    print(f"Pendientes en este bloque: {len(batch)}", flush=True)
    for index, (key, name) in enumerate(batch, 1):
        print(f"[{index}/{len(batch)}] {name} ({key})", flush=True)
        # Reuse previously found candidates when retrying a failed download.
        old_record = report_map.get(key, {})
        old_candidates = old_record.get("candidates", [])
        old_status = old_record.get("status")
        errors = []
        if old_candidates and old_status in ("CANDIDATES_FOUND_DOWNLOAD_FAILED", "DOWNLOAD_FAILED",
                                              "CANDIDATES_FOUND", "SOURCE_ERROR"):
            candidates = filter_and_rank(key, old_candidates)
            status = "CANDIDATES_FOUND" if candidates else "SEARCH_REQUIRED"
        else:
            candidates, errors, status, commons_blocked = search_product(
                key, name, args.delay, commons_blocked
            )
        if status == "SEARCH_REQUIRED":
            candidates, errors, status, commons_blocked = search_product(
                key, name, args.delay, commons_blocked
            )

        record = {"product_key": key, "product": name, "status": status,
                  "search_status": status, "candidates": candidates[:12], "errors": errors}
        prior_download = old_record.get("download") or {}
        if prior_download.get("path"):
            record["previous_unverified_download"] = prior_download
        if status == "CANDIDATES_FOUND":
            download_result, selected = None, None
            for candidate in candidates[:8]:
                download_result = download_candidate(key, candidate)
                if download_result.get("status") == "DOWNLOADED_UNVERIFIED":
                    selected = candidate
                    break
            record["download"] = download_result
            record["download_errors"] = (download_result or {}).get("url_errors", [])
            if selected:
                record["status"] = "DOWNLOADED_UNVERIFIED"
                record["selected_candidate"] = selected
                manifest_map[key] = {"product_key": key, "product": name,
                    "candidates": candidates[:12], "selected_candidate": selected,
                    "download": download_result, "status": record["status"]}
            else:
                record["status"] = "CANDIDATES_FOUND_DOWNLOAD_FAILED"
                manifest_map[key] = {"product_key": key, "product": name,
                    "candidates": candidates[:12], "download": download_result,
                    "status": record["status"]}

        processed[key] = {"status": record["status"], "timestamp": time.time(),
                          "candidate_count": len(candidates)}
        if any(e.get("status") == "RATE_LIMITED" and e.get("source") == "Wikimedia Commons" for e in errors):
            state["commons_blocked_until"] = time.time() + 900
        elif not commons_blocked:
            state["commons_blocked_until"] = 0
        state["last_run"] = time.time()
        state["last_product"] = key
        report_map[key] = record
        save_json(STATE, state)
        save_json(REPORT, list(report_map.values()))
        save_json(MANIFEST, list(manifest_map.values()))
        print(f"  búsqueda={status}; candidatos relevantes={len(candidates)}; resultado={record['status']}", flush=True)
        if index < len(batch):
            time.sleep(max(0, args.delay))

    print("\nLote terminado.")
    print(f"Informe: {REPORT.relative_to(ROOT)}")
    print(f"Manifiesto: {MANIFEST.relative_to(ROOT)}")
    print(f"Estado: {STATE.relative_to(ROOT)}")
    print("Ninguna imagen ha sido aprobada; data/catalog.js permanece intacto.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
