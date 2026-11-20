#!/usr/bin/env python3
"""Static release checks for Almendras de Málaga. No third-party dependencies."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
CATALOG = ROOT / "data" / "catalog.js"
APP = ROOT / "js" / "app.js"

class AuditHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.hrefs = []
        self.srcs = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if attrs.get("href"):
            self.hrefs.append(attrs["href"])
        if attrs.get("src"):
            self.srcs.append(attrs["src"])

def fail(message):
    print("FAIL:", message)
    return False

def main():
    ok = True
    for path in (INDEX, CATALOG, APP):
        if not path.exists():
            ok = fail(f"Missing required file: {path.relative_to(ROOT)}") and ok
    if not ok:
        return 1

    html = INDEX.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    catalog_text = CATALOG.read_text(encoding="utf-8")
    match = re.search(r"window\\.PRODUCTS\\s*=\\s*(\\{.*\\})\\s*;?\\s*$", catalog_text, re.S)
    if not match:
        return fail("data/catalog.js does not expose a parseable JSON object as window.PRODUCTS") and 1
    try:
        products = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return fail(f"Catalog JSON is invalid: {exc}") and 1

    if len(products) != 151:
        ok = fail(f"Expected 151 catalog products; found {len(products)}") and ok
    for product_id, product in products.items():
        for field in ("name", "desc", "category", "price"):
            if field not in product or product[field] in (None, ""):
                ok = fail(f"Product {product_id} missing required field: {field}") and ok
        if not isinstance(product.get("price"), (int, float)) or product["price"] <= 0:
            ok = fail(f"Product {product_id} has invalid price") and ok

    verified_urls = [p.get("image") for p in products.values() if p.get("imageVerified") is True and p.get("image")]
    duplicates = sorted({url for url in verified_urls if verified_urls.count(url) > 1})
    if duplicates:
        ok = fail(f"Duplicate verified image URLs: {duplicates}") and ok

    parser = AuditHTML()
    parser.feed(html)
    duplicate_ids = sorted({x for x in parser.ids if parser.ids.count(x) > 1})
    if duplicate_ids:
        ok = fail(f"Duplicate HTML ids: {duplicate_ids}") and ok
    id_set = set(parser.ids)
    for href in parser.hrefs:
        if href.startswith("#") and href[1:] and href[1:] not in id_set:
            ok = fail(f"Internal link target does not exist: {href}") and ok

    # Scripts must load the data before the app.
    catalog_pos = html.find('src="data/catalog.js"')
    app_pos = html.find('src="js/app.js"')
    if catalog_pos < 0 or app_pos < 0 or catalog_pos >= app_pos:
        ok = fail("data/catalog.js must load before js/app.js") and ok

    primary = "34666068765"
    secondary = "34744602855"
    if primary not in html or primary not in app:
        ok = fail("Primary order phone 34666068765 is missing from HTML or app.js") and ok
    if secondary not in html:
        ok = fail("Secondary contact 34744602855 is missing from HTML") and ok
    if "wa.me/" + secondary in html or "wa.me/" + secondary in app:
        ok = fail("WhatsApp order links must use the primary number, not the secondary contact") and ok

    if ok:
        print(f"PASS: {len(products)} catalog products; required fields, image uniqueness, HTML ids/anchors, script order and phone routing verified.")
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())
