#!/usr/bin/env python3
"""Download Wikimedia Commons candidates for manual catalog review.

This script NEVER marks a product image as approved or edits catalog.js.
It downloads only candidates listed in photo_candidates.json, records Commons
metadata, and rejects files below the configured resolution threshold.
"""
import json, os, re, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "photo_candidates.json"
OUT = ROOT / "assets" / "products" / "candidates"
REPORT = ROOT / "docs" / "photo-candidate-download-report.json"
API = "https://commons.wikimedia.org/w/api.php"
MIN_WIDTH, MIN_HEIGHT = 900, 700

def api(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "AlmendrasDeMalagaPhotoAudit/1.0 (catalog photo review)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def safe_name(s):
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", s).strip("_")

def main():
    candidates = json.loads(MANIFEST.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    report = []
    for item in candidates:
        title = item["commons_title"]
        row = {"product_key": item["product_key"], "product": item["product"], "commons_title": title}
        try:
            data = api({"action":"query","format":"json","prop":"imageinfo","iiprop":"url|size|mime|extmetadata","titles":"File:"+title})
            page = next(iter(data["query"]["pages"].values()))
            info = page.get("imageinfo", [{}])[0]
            meta = info.get("extmetadata", {})
            row.update({"source_url": info.get("descriptionurl"), "download_url": info.get("url"),
                        "width": info.get("width"), "height": info.get("height"),
                        "mime": info.get("mime"), "license": meta.get("LicenseShortName",{}).get("value"),
                        "artist": meta.get("Artist",{}).get("value"),
                        "credit": meta.get("Credit",{}).get("value")})
            if page.get("missing") is not None or not info.get("url"):
                row["status"] = "NOT_FOUND"
            elif info.get("mime") not in ("image/jpeg","image/png","image/webp"):
                row["status"] = "REJECTED_MIME"
            elif (info.get("width",0) < MIN_WIDTH or info.get("height",0) < MIN_HEIGHT):
                row["status"] = "REJECTED_LOW_RES"
            else:
                filename = safe_name(item["product_key"]) + Path(info["url"]).suffix.lower()
                dest = OUT / filename
                req = urllib.request.Request(info["url"], headers={"User-Agent":"AlmendrasDeMalagaPhotoAudit/1.0"})
                with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as f:
                    f.write(r.read())
                row["local_candidate"] = str(dest.relative_to(ROOT))
                row["status"] = "DOWNLOADED_UNVERIFIED"
        except Exception as e:
            row["status"] = "ERROR"
            row["error"] = str(e)
        report.append(row)
        print(row["status"], item["product"], "—", row.get("local_candidate", row.get("error","")))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nReport:", REPORT)
    print("Important: downloaded files remain candidates. Inspect each image manually before catalog integration.")

if __name__ == "__main__":
    main()
