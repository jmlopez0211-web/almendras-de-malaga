#!/usr/bin/env python3
"""Compatibility wrapper: uses the secure binary pipeline for Commons candidates."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from image_pipeline import download_manifest

MANIFEST=ROOT/"photo_candidates.json"
OUT=ROOT/"assets"/"products"/"candidates"

if __name__=="__main__":
    report=download_manifest(MANIFEST,OUT,retries=3,min_width=900,min_height=700)
    for row in report["download_results"]:
        print(row["status"],row["product_key"],row.get("path") or row.get("errors"))
    print("Report:",ROOT/"docs"/"image-pipeline-report.json")
    print("Candidates remain unapproved; catalog flags are not modified.")
