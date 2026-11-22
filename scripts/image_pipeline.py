#!/usr/bin/env python3
"""
Safe photo pipeline for Almendras de Málaga.
Downloads candidates, validates real image bytes, inspects them, hashes duplicates,
and optionally synchronizes binaries. NEVER changes catalog approval/verification flags.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, mimetypes, os, re, subprocess, sys, time
from pathlib import Path
from urllib.parse import quote
import requests
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "photo_candidates.json"
DEFAULT_OUT = ROOT / "assets" / "images"
REPORT = ROOT / "docs" / "image-pipeline-report.json"
ALLOWED = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAGIC = {"image/jpeg": (b"\xff\xd8\xff",), "image/png": (b"\x89PNG\r\n\x1a\n",), "image/webp": (b"RIFF",)}
USER_AGENT = "AlmendrasDeMalagaImagePipeline/1.0 (photo audit; contact repository owner)"

def commons_file_url(title: str, *, thumbnail_width: int = 1200) -> tuple[str, dict]:
    """Resolve a Commons title to a thumbnail URL and attribution metadata.

    Exact-title lookup is attempted first. If the title is missing, Commons search
    is used as a fallback; the returned match is recorded and is NOT product approval.
    """
    api = "https://commons.wikimedia.org/w/api.php"
    headers = {"User-Agent": USER_AGENT}
    base = {"action": "query", "format": "json", "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata", "iiurlwidth": thumbnail_width}
    r = requests.get(api, params={**base, "titles": "File:" + title},
                     headers=headers, timeout=(10, 30))
    r.raise_for_status()
    page = next(iter(r.json()["query"]["pages"].values()))
    matched_title = page.get("title", "File:" + title)
    if "missing" in page:
        search = requests.get(api, params={"action":"query","format":"json",
            "generator":"search","gsrsearch":title,"gsrnamespace":6,"gsrlimit":5,
            "prop":"imageinfo","iiprop":"url|size|mime|extmetadata",
            "iiurlwidth":thumbnail_width}, headers=headers, timeout=(10,30))
        search.raise_for_status()
        pages = search.json().get("query", {}).get("pages", {})
        if not pages:
            raise ValueError(f"Commons file not found and search returned no candidates: {title}")
        page = next(iter(pages.values()))
        matched_title = page.get("title", "")
    info = page["imageinfo"][0]
    # Prefer a Commons thumbnail to reduce bandwidth and avoid repeated original-file
    # requests that trigger Wikimedia rate limits. Fall back only if unavailable.
    download_url = info.get("thumburl") or info.get("url")
    extmeta = info.get("extmetadata", {})
    metadata = {"source_url": info.get("descriptionurl"), "commons_title": matched_title,
        "requested_title": title, "mime": info.get("mime"), "width": info.get("width"),
        "height": info.get("height"), "thumbnail_width": thumbnail_width,
        "license": extmeta.get("LicenseShortName", {}).get("value"),
        "license_url": extmeta.get("LicenseUrl", {}).get("value"),
        "artist": extmeta.get("Artist", {}).get("value"),
        "credit": extmeta.get("Credit", {}).get("value"),
        "thumbnail_used": bool(info.get("thumburl"))}
    return download_url, metadata

def resolve_candidate(item: dict) -> tuple[str, dict]:
    if item.get("url"):
        return item["url"], item.get("metadata", {})
    if item.get("commons_title"):
        return commons_file_url(item["commons_title"])
    raise ValueError("Candidate requires url or commons_title")

def safe_key(value: str) -> str:
    key = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    if not key: raise ValueError("Unsafe/empty product key")
    return key[:100]

def download_one(item: dict, out_dir: Path = DEFAULT_OUT, *, retries: int = 3,
                 min_width: int = 900, min_height: int = 700, max_bytes: int = 25_000_000) -> dict:
    """Download binary candidate; validate MIME, magic bytes, decode, dimensions and size."""
    key = safe_key(item.get("product_key") or item.get("id") or item.get("name") or "candidate")
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {"product_key":key,"status":"FAILED","source":None,"path":None,"sha256":None,"errors":[]}
    temp = out_dir / (key + ".download")
    try:
        url, metadata = resolve_candidate(item); result["source"] = url
        last_error = None
        for attempt in range(retries + 1):
            try:
                with requests.get(url, headers={"User-Agent":USER_AGENT}, stream=True, timeout=(10,45), allow_redirects=True) as r:
                    if r.status_code == 429:
                        retry_after = r.headers.get("Retry-After")
                        wait = int(retry_after) if retry_after and retry_after.isdigit() else min(15 * (2 ** attempt), 120)
                        if attempt < retries:
                            time.sleep(wait)
                            continue
                    r.raise_for_status()
                    mime = r.headers.get("Content-Type","").split(";")[0].strip().lower()
                    if mime not in ALLOWED: raise ValueError(f"Rejected MIME: {mime}")
                    total = 0
                    with temp.open("wb") as f:
                        for chunk in r.iter_content(1024*64):
                            if not chunk: continue
                            total += len(chunk)
                            if total > max_bytes: raise ValueError(f"File exceeds limit ({max_bytes} bytes)")
                            f.write(chunk)
                    with temp.open("rb") as f: head = f.read(16)
                    if not any(head.startswith(m) for m in MAGIC[mime]):
                        raise ValueError("File signature does not match MIME")
                    with Image.open(temp) as im:
                        im.verify()
                    with Image.open(temp) as im:
                        width,height = im.size
                        fmt = im.format
                    if width < min_width or height < min_height:
                        raise ValueError(f"Image too small: {width}x{height}")
                    ext = ALLOWED[mime]
                    dest = out_dir / (key + ext)
                    if dest.exists(): dest = out_dir / (key + "-candidate" + ext)
                    temp.replace(dest)
                    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
                    result.update({"status":"DOWNLOADED_UNVERIFIED","path":str(dest.resolve().relative_to(ROOT.resolve())),
                        "sha256":digest,"bytes":total,"mime":mime,"format":fmt,"width":width,"height":height,
                        "aspect_ratio":round(width/height,4),"metadata":metadata})
                    return result
            except (requests.RequestException, OSError, ValueError, UnidentifiedImageError) as e:
                last_error = str(e)
                if attempt < retries: time.sleep(min(2**attempt,8))
        result["errors"].append(last_error or "download failed")
    finally:
        if temp.exists(): temp.unlink()
    return result

def inspect_file(path: Path, min_width=900, min_height=700) -> dict:
    """Read-only inspection: corruption, dimensions, ratio, format and SHA-256."""
    row={"path":str(path),"status":"INSPECTED_UNVERIFIED"}
    try:
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            w,h=im.size; fmt=im.format; mode=im.mode
        row.update({"sha256":digest,"width":w,"height":h,"format":fmt,"mode":mode,
            "aspect_ratio":round(w/h,4),"meets_minimum":w>=min_width and h>=min_height})
        if not row["meets_minimum"]: row["status"]="REJECTED_LOW_RES"
    except Exception as e:
        row.update({"status":"CORRUPT_OR_UNREADABLE","error":str(e)})
    return row

def inspect_directory(directory: Path = DEFAULT_OUT) -> dict:
    """Inspect all supported files and identify byte-identical duplicates by SHA-256."""
    rows=[]; hashes={}
    for p in sorted(directory.glob("*")):
        if p.suffix.lower() not in {".jpg",".jpeg",".png",".webp"} or not p.is_file(): continue
        row=inspect_file(p); rows.append(row)
        if row.get("sha256"):
            hashes.setdefault(row["sha256"],[]).append(str(p))
    duplicates=[{"sha256":h,"files":files} for h,files in hashes.items() if len(files)>1]
    return {"files":rows,"duplicates":duplicates,"summary":{"files":len(rows),
        "corrupt":sum(x["status"]=="CORRUPT_OR_UNREADABLE" for x in rows),
        "low_resolution":sum(x["status"]=="REJECTED_LOW_RES" for x in rows),"duplicate_groups":len(duplicates)}}

def load_manifest(path: Path) -> list[dict]:
    data=json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data,dict): data=data.get("candidates",[])
    if not isinstance(data,list): raise ValueError("Manifest must be a JSON list or {candidates:[...]}")
    return data

def download_manifest(manifest=DEFAULT_MANIFEST, out_dir=DEFAULT_OUT, **kwargs) -> dict:
    # Normalize relative paths against repository root, not the caller's current
    # working directory. This avoids Path.relative_to failures when invoked from
    # Termux/proot or a workflow with a different cwd.
    manifest = Path(manifest)
    if not manifest.is_absolute():
        manifest = ROOT / manifest
    out_dir = Path(out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir = out_dir.resolve()
    results = []
    request_delay = kwargs.pop("request_delay", 3.0)
    for index, item in enumerate(load_manifest(manifest)):
        if index:
            time.sleep(request_delay)
        results.append(download_one(item, out_dir, **kwargs))
    report={"download_results":results,"inspection":inspect_directory(out_dir),
            "note":"All downloads are candidates. This report does not approve or verify catalog products."}
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report

def git_sync(files: list[Path], repo_root: Path = ROOT, *, commit_message="Add unapproved photo candidates", push=False) -> None:
    """Stage binary files, commit, and optionally push. Does not edit catalog or approval flags."""
    rel=[]
    for p in files:
        p=p.resolve()
        if not p.is_file(): raise FileNotFoundError(p)
        try: rel.append(str(p.relative_to(repo_root.resolve())))
        except ValueError: raise ValueError(f"File outside repository: {p}")
    subprocess.run(["git","add","--",*rel],cwd=repo_root,check=True)
    subprocess.run(["git","commit","-m",commit_message],cwd=repo_root,check=True)
    if push: subprocess.run(["git","push"],cwd=repo_root,check=True)

def github_api_upload(files: list[Path], *, owner: str, repo: str, branch: str, token: str, base_path="assets/images") -> list[dict]:
    """Upload binary files via GitHub Contents API (small files; one commit per file)."""
    if not token: raise ValueError("Provide token via GITHUB_TOKEN environment variable")
    results=[]; session=requests.Session(); session.headers.update({"Authorization":f"Bearer {token}",
        "Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":USER_AGENT})
    for p in files:
        if not p.is_file(): raise FileNotFoundError(p)
        rel=f"{base_path.rstrip('/')}/{p.name}"
        url=f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(rel,safe='/')}"
        get=session.get(url,params={"ref":branch},timeout=(10,30))
        sha=get.json().get("sha") if get.status_code==200 else None
        if get.status_code not in (200,404): get.raise_for_status()
        payload={"message":f"Add unapproved photo candidate: {p.name}","content":base64.b64encode(p.read_bytes()).decode("ascii"),"branch":branch}
        if sha: payload["sha"]=sha
        put=session.put(url,json=payload,timeout=(10,60)); put.raise_for_status()
        results.append({"file":p.name,"path":rel,"commit":put.json().get("commit",{}).get("sha"),"status":"UPLOADED_UNAPPROVED"})
    return results

def main():
    ap=argparse.ArgumentParser(description="Download, inspect and optionally sync unapproved image candidates.")
    ap.add_argument("command",choices=["download","inspect","sync-git","sync-api"])
    ap.add_argument("--manifest",default=str(DEFAULT_MANIFEST)); ap.add_argument("--directory",default=str(DEFAULT_OUT))
    ap.add_argument("--min-width",type=int,default=900); ap.add_argument("--min-height",type=int,default=700)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--push", action="store_true", help="Push after git commit")
    ap.add_argument("--request-delay", type=float, default=3.0, help="Seconds between Commons candidate downloads")
    ap.add_argument("--owner"); ap.add_argument("--repo"); ap.add_argument("--branch",default="main"); ap.add_argument("--base-path",default="assets/images")
    args=ap.parse_args(); directory=Path(args.directory)
    if args.command=="download":
        print(json.dumps(download_manifest(args.manifest,directory,retries=args.retries,min_width=args.min_width,min_height=args.min_height,request_delay=args.request_delay),ensure_ascii=False,indent=2))
    elif args.command=="inspect":
        print(json.dumps(inspect_directory(directory),ensure_ascii=False,indent=2))
    elif args.command=="sync-git":
        files=[p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in {".jpg",".jpeg",".png",".webp"}]
        git_sync(files,push=args.push); print(f"Committed {len(files)} candidate image files; approval flags unchanged.")
    elif args.command=="sync-api":
        if not args.owner or not args.repo: ap.error("--owner and --repo required")
        files=[p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in {".jpg",".jpeg",".png",".webp"}]
        print(json.dumps(github_api_upload(files,owner=args.owner,repo=args.repo,branch=args.branch,token=os.environ.get("GITHUB_TOKEN",""),base_path=args.base_path),indent=2))
if __name__=="__main__": main()
