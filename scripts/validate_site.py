#!/usr/bin/env python3
"""Release validator for the static Almendras de Málaga storefront."""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
CATALOG = ROOT / "data" / "catalog.js"
APP = ROOT / "js" / "app.js"
CSS = ROOT / "styles.css"
SITEMAP = ROOT / "sitemap.xml"
ROBOTS = ROOT / "robots.txt"
PRIMARY_PHONE = "34666068765"
SECONDARY_PHONE = "34744602855"
EXPECTED_PRODUCTS = 151


class AuditHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.srcs: list[str] = []
        self.images_without_alt: list[str] = []
        self.dialogs_without_aria: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])
        if values.get("href"):
            self.hrefs.append(values["href"])
        if values.get("src"):
            self.srcs.append(values["src"])
        if tag == "img" and "alt" not in values:
            self.images_without_alt.append(values.get("src", "(sin src)"))
        if values.get("role") == "dialog":
            if values.get("aria-modal") != "true" or not values.get("aria-labelledby"):
                self.dialogs_without_aria.append(values.get("id", "(sin id)"))


def fail(message: str) -> bool:
    print(f"FAIL: {message}")
    return False


def load_catalog():
    source = CATALOG.read_text(encoding="utf-8")
    match = re.search(r"window\.PRODUCTS\s*=\s*(\{.*\})\s*;?\s*$", source, re.S)
    if not match:
        raise ValueError("data/catalog.js must expose a JSON object as window.PRODUCTS")
    return json.loads(match.group(1))


def check_local_reference(page: Path, reference: str) -> str | None:
    """Return a diagnostic for a broken local href/src, otherwise None."""
    if not reference or reference.startswith(("#", "http://", "https://", "mailto:", "tel:", "data:", "javascript:")):
        return None
    parts = urlsplit(reference)
    relative = parts.path
    if not relative:
        return None
    candidate = (page.parent / relative).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        return f"reference escapes repository root: {reference}"
    if not candidate.exists():
        return f"local reference does not exist: {page.relative_to(ROOT)} -> {reference}"
    if parts.fragment and candidate.suffix.lower() in {".html", ".htm"}:
        target = AuditHTML()
        target.feed(candidate.read_text(encoding="utf-8"))
        if parts.fragment not in target.ids:
            return f"local fragment does not exist: {page.relative_to(ROOT)} -> {reference}"
    return None


def main() -> int:
    ok = True
    required = (INDEX, CATALOG, APP, CSS, SITEMAP, ROBOTS)
    for path in required:
        if not path.is_file():
            ok = fail(f"missing required file: {path.relative_to(ROOT)}") and ok
    if not ok:
        return 1

    try:
        products = load_catalog()
    except (ValueError, json.JSONDecodeError) as exc:
        return fail(f"catalog cannot be parsed: {exc}") and 1

    if len(products) != EXPECTED_PRODUCTS:
        ok = fail(f"expected {EXPECTED_PRODUCTS} products; found {len(products)}") and ok

    for product_id, product in products.items():
        for field in ("name", "desc", "category", "price"):
            if field not in product or product[field] in (None, ""):
                ok = fail(f"product {product_id} missing {field}") and ok
        if not isinstance(product.get("price"), (int, float)) or product["price"] <= 0:
            ok = fail(f"product {product_id} has a non-positive or non-numeric price") and ok
        image = product.get("image", "")
        if image.startswith(("assets/", "img/")) and not (ROOT / image).is_file():
            ok = fail(f"local image file does not exist for {product_id}: {image}") and ok

    verified_urls = [
        product.get("image")
        for product in products.values()
        if product.get("imageVerified") is True and product.get("image")
    ]
    duplicate_urls = sorted(url for url, count in Counter(verified_urls).items() if count > 1)
    if duplicate_urls:
        ok = fail(f"duplicate verified image URLs: {duplicate_urls}") and ok

    html_files = sorted(ROOT.glob("*.html"))
    if not html_files:
        ok = fail("no HTML pages found") and ok

    page_parsers: dict[Path, AuditHTML] = {}
    for page in html_files:
        content = page.read_text(encoding="utf-8")
        parser = AuditHTML()
        parser.feed(content)
        page_parsers[page] = parser

        duplicate_ids = sorted(value for value, count in Counter(parser.ids).items() if count > 1)
        if duplicate_ids:
            ok = fail(f"{page.name} has duplicate IDs: {duplicate_ids}") and ok
        if parser.images_without_alt:
            ok = fail(f"{page.name} has img elements without alt attributes: {parser.images_without_alt}") and ok
        if parser.dialogs_without_aria:
            ok = fail(f"{page.name} has dialogs missing aria-modal or aria-labelledby: {parser.dialogs_without_aria}") and ok
        if 'name="viewport"' not in content:
            ok = fail(f"{page.name} is missing the responsive viewport meta tag") and ok

        for reference in parser.hrefs:
            if reference.startswith("#"):
                fragment = reference[1:]
                if fragment and fragment not in parser.ids:
                    ok = fail(f"{page.name} links to a missing anchor: {reference}") and ok
                continue
            diagnostic = check_local_reference(page, reference)
            if diagnostic:
                ok = fail(diagnostic) and ok
        for reference in parser.srcs:
            diagnostic = check_local_reference(page, reference)
            if diagnostic:
                ok = fail(diagnostic) and ok

    index_html = INDEX.read_text(encoding="utf-8")
    app_js = APP.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")

    catalog_pos = index_html.find('src="data/catalog.js"')
    app_pos = index_html.find('src="js/app.js"')
    if catalog_pos < 0 or app_pos < 0 or catalog_pos >= app_pos:
        ok = fail("data/catalog.js must load before js/app.js") and ok

    if "sendCartWhatsApp666" not in index_html or "sendCartWhatsApp666" not in app_js:
        ok = fail("cart WhatsApp button/handler for primary phone is missing") and ok
    if f"wa.me/{PRIMARY_PHONE}" not in app_js:
        ok = fail("cart WhatsApp handler does not use the primary phone") and ok
    if PRIMARY_PHONE not in index_html or SECONDARY_PHONE not in index_html:
        ok = fail("main page must show both the primary and secondary contact numbers") and ok

    for page in html_files:
        if page == INDEX:
            continue
        content = page.read_text(encoding="utf-8")
        if f"wa.me/{PRIMARY_PHONE}" not in content:
            ok = fail(f"{page.name} does not route its WhatsApp enquiry CTA to the primary phone") and ok
        if f"wa.me/{SECONDARY_PHONE}" in content:
            ok = fail(f"{page.name} still sends its main WhatsApp CTA to the secondary number") and ok
        if f"tel:+{PRIMARY_PHONE}" not in content or f"tel:+{SECONDARY_PHONE}" not in content:
            ok = fail(f"{page.name} must preserve both primary and secondary telephone contacts") and ok

    if "class=\"skip-link\"" not in index_html:
        ok = fail("main page is missing the keyboard skip link") and ok
    if ":focus-visible" not in css or "prefers-reduced-motion" not in css:
        ok = fail("keyboard focus or reduced-motion accessibility styles are missing") and ok
    if "escapeHTML" not in app_js or "modalFocusSelector" not in app_js:
        ok = fail("safe dynamic HTML rendering or modal focus management is missing") and ok

    sitemap = SITEMAP.read_text(encoding="utf-8")
    try:
        sitemap_root = ET.fromstring(sitemap)
        if not sitemap_root.tag.endswith("urlset"):
            ok = fail("sitemap.xml root element must be urlset") and ok
    except ET.ParseError as exc:
        ok = fail(f"sitemap.xml is not valid XML: {exc}") and ok
    robots = ROBOTS.read_text(encoding="utf-8")
    if "Sitemap: https://jmlopez0211-web.github.io/almendras-de-malaga/sitemap.xml" not in robots:
        ok = fail("robots.txt does not point to the public sitemap") and ok

    for page in html_files:
        page_url = "https://jmlopez0211-web.github.io/almendras-de-malaga/"
        if page.name != "index.html":
            page_url += page.name
        if page_url not in sitemap:
            ok = fail(f"sitemap.xml is missing {page.name}") and ok

    if ok:
        print(
            f"PASS: {len(products)} products; local assets; all {len(html_files)} HTML pages; "
            "internal links; accessibility; primary/secondary phone routing; sitemap and script order."
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
