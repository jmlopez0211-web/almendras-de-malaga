#!/usr/bin/env python3
"""Retry catalog image candidates safely; downloaded files remain unverified."""
import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from urllib.error import HTTPError
from io import BytesIO

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs/catalog_alphabet_image_candidates.json"
OUT = ROOT / "assets/images/candidates"
STATE = ROOT / "docs/retry_download_state.json"
REPORT = ROOT / "docs/retry_download_report.json"
OUT.mkdir(parents=True, exist_ok=True)

MIN_WIDTH, MIN_HEIGHT = 800, 600
MAX_BYTES = 20_000_000
PAUSE_SECONDS = 15
ALLOWED = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
UA = "AlmendrasDeMalagaCatalogAudit/1.0 (image research; contact via repository)"

def read_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def slug(value):
    return re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "candidate")).strip("-")[:90] or "candidate"

def collect(data):
    found = []
    def add(obj, key=None, name=None):
        if not isinstance(obj, dict):
            return
        url = obj.get("url") or obj.get("original_url")
        if not isinstance(url, str) or not url.startswith("https://"):
            return
        found.append({
            "product_key": obj.get("product_key") or obj.get("key") or key,
            "product_name": obj.get("product_name") or obj.get("name") or obj.get("product") or name,
            "url": url,
            "page_url": obj.get("page_url"),
            "title": obj.get("title"),
            "license": obj.get("license"),
            "creator": obj.get("creator"),
            "credit": obj.get("credit"),
            "description": obj.get("description"),
            "source": obj.get("source"),
        })
    def walk(obj, key=None, name=None):
        if isinstance(obj, dict):
            k = obj.get("product_key") or obj.get("key") or obj.get("id") or key
            n = obj.get("product_name") or obj.get("name") or obj.get("product") or name
            if isinstance(obj.get("candidate"), dict):
                add(obj["candidate"], k, n)
            for field in ("candidates", "images", "results"):
                if isinstance(obj.get(field), list):
                    for item in obj[field]:
                        add(item, k, n)
            if isinstance(obj.get("downloads"), list):
                for item in obj["downloads"]:
                    if isinstance(item, dict):
                        add(item.get("candidate", item), k, n)
            for field, value in obj.items():
                if field not in ("candidate", "candidates", "images", "results", "downloads"):
                    walk(value, k, n)
        elif isinstance(obj, list):
            for item in obj:
                walk(item, key, name)
    walk(data)
    unique = {}
    for item in found:
        unique.setdefault(item["url"], item)
    return list(unique.values())


def fetch(url, retries=3):
    last_error = None
    host = urlparse(url).netloc.lower()

    # Wikimedia bloqueado temporalmente en esta recuperación.
    if host == "upload.wikimedia.org":
        raise RuntimeError(
            f"Fuente omitida temporalmente por rate-limit: {host}"
        )

    for attempt in range(retries):
        req = Request(
            url,
            headers={
                "User-Agent": UA,
                "Accept": "image/webp,image/jpeg,image/png,*/*",
            },
        )

        try:
            with urlopen(req, timeout=40) as response:
                ctype = (
                    response.headers.get("Content-Type", "")
                    .split(";")[0]
                    .strip()
                    .lower()
                )

                if ctype not in ALLOWED:
                    raise ValueError(
                        f"Content-Type no permitido: {ctype}"
                    )

                data = response.read(MAX_BYTES + 1)

                if len(data) > MAX_BYTES:
                    raise ValueError("Imagen supera 20 MB")

                return data, ctype

        except HTTPError as e:
            last_error = f"HTTP {e.code}"

            # NO esperar ni volver a insistir ante rate-limit.
            if e.code == 429:
                raise RuntimeError(
                    f"{last_error}: servidor limita solicitudes; "
                    "se abandona inmediatamente"
                )

            # Errores permanentes: no reintentar.
            if e.code not in (500, 502, 503, 504):
                raise RuntimeError(last_error)

            if attempt < retries - 1:
                delay = min(60, 10 * (2 ** attempt))
                print(f"  {last_error}; espera {delay}s")
                time.sleep(delay)

        except Exception as e:
            last_error = str(e)

            if attempt < retries - 1:
                delay = min(30, 5 * (2 ** attempt))
                print(f"  {last_error}; espera {delay}s")
                time.sleep(delay)

    raise RuntimeError(last_error or "Descarga fallida")

def validate(data, ctype):
    im = Image.open(BytesIO(data))
    im.verify()
    im = Image.open(BytesIO(data))
    im.load()
    w, h = im.size
    if im.format not in ("JPEG", "PNG", "WEBP"):
        raise ValueError(f"Formato no admitido: {im.format}")
    if w < MIN_WIDTH or h < MIN_HEIGHT:
        raise ValueError(f"Resolución baja: {w}x{h}")
    signatures = {
        "image/jpeg": data.startswith(b"\\xff\\xd8\\xff"),
        "image/png": data.startswith(b"\\x89PNG\\r\\n\\x1a\\n"),
        "image/webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP",
    }
    if not signatures.get(ctype, False):
        raise ValueError("Firma binaria no coincide con Content-Type")
    return w, h, im.format


def main():
    parser = argparse.ArgumentParser(
        description="Recuperación controlada de imágenes del catálogo"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula el proceso sin descargar archivos"
    )

    parser.add_argument(
        "--max-candidates",
        type=int,
        default=None,
        help="Limita el número de candidatos"
    )

    parser.add_argument(
        "--pause",
        type=int,
        default=PAUSE_SECONDS,
        help="Pausa entre candidatos"
    )

    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Reintenta candidatos que anteriormente fallaron"
    )

    args = parser.parse_args()

    candidates = collect(read_json(MANIFEST, {}))
    state = read_json(STATE, {"processed": {}})
    processed = state.setdefault("processed", {})

    original_total = len(candidates)

    if args.max_candidates is not None:
        candidates = candidates[:max(0, args.max_candidates)]

    report = {
        "total_candidates": len(candidates),
        "original_total": original_total,
        "downloaded": 0,
        "failed": 0,
        "skipped": 0,
        "dry_run": args.dry_run,
        "results": [],
    }

    print(f"Candidatos encontrados: {original_total}")
    print(f"Candidatos seleccionados: {len(candidates)}")
    print(f"Modo simulación: {args.dry_run}")

    if args.dry_run:
        print("\n===== SIMULACIÓN =====")

        for i, item in enumerate(candidates, 1):
            key = slug(
                item.get("product_key")
                or item.get("title")
                or f"candidate-{i}"
            )

            print(
                f"[{i}/{len(candidates)}] "
                f"{key} | {item.get('source')} | "
                f"{item.get('url')}"
            )

        print("\nSIMULACIÓN TERMINADA")
        print("No se han descargado archivos.")
        return

    for i, item in enumerate(candidates, 1):
        url = item["url"]

        url_id = hashlib.sha256(
            url.encode()
        ).hexdigest()[:12]

        key = slug(
            item.get("product_key")
            or item.get("title")
            or f"candidate-{i}"
        )

        state_key = f"{key}:{url_id}"
        old = processed.get(state_key, {})

        # Solo omitir una descarga si el archivo existe realmente.
        if old.get("status") == "DOWNLOADED_UNVERIFIED":
            saved_file = old.get("file")

            if saved_file:
                saved_path = ROOT / saved_file

                if saved_path.is_file():
                    report["skipped"] += 1
                    print(
                        f"\n[{i}/{len(candidates)}] "
                        f"OMITIDA: archivo existente {saved_path}"
                    )
                    continue

        print(f"\n[{i}/{len(candidates)}] {key}")

        try:
            data, ctype = fetch(url)
            w, h, fmt = validate(data, ctype)

            filename = f"{key}-{url_id}{ALLOWED[ctype]}"
            destination = OUT / filename

            destination.write_bytes(data)

            result = {
                "status": "DOWNLOADED_UNVERIFIED",
                **item,
                "file": str(destination.relative_to(ROOT)),
                "width": w,
                "height": h,
                "format": fmt,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }

            report["downloaded"] += 1

            print(
                f"  DESCARGADA {w}x{h}: "
                f"{filename}"
            )

        except Exception as e:
            result = {
                "status": "DOWNLOAD_FAILED",
                **item,
                "error": str(e),
            }

            report["failed"] += 1
            print(f"  ERROR: {e}")

        processed[state_key] = result
        report["results"].append(result)

        write_json(STATE, state)

        if args.pause > 0:
            time.sleep(args.pause)

    write_json(REPORT, report)

    print("\n===== RECUPERACIÓN TERMINADA =====")

    print(
        json.dumps(
            {
                "total_candidates": report["total_candidates"],
                "downloaded": report["downloaded"],
                "failed": report["failed"],
                "skipped": report["skipped"],
            },
            indent=2,
        )
    )

    print(f"Informe: {REPORT}")
    print(f"Estado: {STATE}")
    print(f"Imágenes: {OUT}")

if __name__ == "__main__":
    main()
