#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Almendras de Málaga — motor de búsqueda A-Z de candidatos fotográficos.
Search: Wikimedia Commons API + Openverse API.
Binary pipeline: retry/backoff, MIME + magic + Pillow decode, dimensions,
SHA-256 dedup, safe filenames, resumable state, atomic JSON writes.
Does NOT modify data/catalog.js or approve images.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, re, time, unicodedata, mimetypes, ipaddress
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = ROOT / "scripts" / "catalog_candidate_batch.py"
OUTPUT = ROOT / "docs" / "catalog_alphabet_image_candidates.json"
STATE_PATH = ROOT / "docs" / "catalog_alphabet_image_state.json"
MANIFEST_PATH = ROOT / "photo_candidates_alphabet.json"
IMAGE_DIR = ROOT / "assets" / "images" / "candidates"
USER_AGENT = "AlmendrasDeMalagaCatalogResearch/1.0 (image research; contact repository owner)"
MAX_BYTES = 25 * 1024 * 1024
MIN_W, MIN_H = 700, 500
ALLOWED = {"image/jpeg", "image/png", "image/webp"}
MAGIC = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
}
BAD_TERMS = {
    "recipe", "menu", "restaurant", "chicken", "rice", "cake", "dessert",
    "salad", "dish", "food plate", "curry", "sauce", "soup", "bread",
    "packaging", "package", "bag", "brand", "logo", "advertisement",
}
SYNONYMS = {
    "almendra": ["almond", "almonds", "almendra kernel", "almendras"],
    "cacahuete": ["peanut", "peanuts", "groundnut", "groundnuts"],
    "anacardo": ["cashew", "cashews", "cashew kernel"],
    "pistacho": ["pistachio", "pistachios", "pistachio kernel"],
    "avellana": ["hazelnut", "hazelnuts"],
    "nuez": ["walnut", "walnuts", "walnut kernel"],
    "macadamia": ["macadamia", "macadamia nuts"],
    "pipa": ["sunflower seed", "sunflower seeds"],
    "pinon": ["pine nut", "pine nuts"],
    "mango": ["mango", "dried mango"],
    "platano": ["banana chips", "dried banana"],
    "arandano": ["cranberry", "dried cranberries"],
    "pasas": ["raisins", "dried grapes"],
    "coco": ["coconut", "dried coconut"],
    "chocolate": ["chocolate coated", "chocolate covered"],
    "deshidratado": ["dried", "dehydrated"],
}
PREP = {
    "frit": ["fried", "fried nuts", "fried kernels"],
    "tost": ["roasted", "dry roasted"],
    "crud": ["raw", "unroasted"],
    "pelad": ["shelled", "peeled", "skinless"],
    "repelad": ["blanched", "skinless", "peeled"],
    "sal": ["salted", "with salt"],
    "sin sal": ["unsalted", "no salt"],
    "chocolate blanco": ["white chocolate coated"],
    "chocolate negro": ["dark chocolate coated"],
    "chocolate leche": ["milk chocolate coated"],
    "caramel": ["caramelized", "caramel coated"],
}
def norm(s):
    s = unicodedata.normalize("NFD", str(s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def safe_key(s):
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", str(s)).strip("-")[:100] or "product"

def load_pipeline():
    spec = importlib.util.spec_from_file_location("catalog_candidate_batch", PIPELINE_PATH)
    if not spec or not spec.loader: raise RuntimeError(f"No se puede cargar {PIPELINE_PATH}")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def read_catalog(p):
    return p.read_catalog()

def atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def safe_url(url):
    try:
        u = urlparse(url)
        if u.scheme not in {"https", "http"} or not u.hostname: return False
        host = u.hostname.lower()
        if host in {"localhost"} or host.endswith(".local"): return False
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved: return False
        except ValueError: pass
        return True
    except Exception: return False

def http_json(url, timeout=25, retries=2):
    last_error = None

    for attempt in range(retries + 1):
        req = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(req, timeout=timeout) as response:
                return json.loads(
                    response.read().decode("utf-8", "replace")
                )

        except HTTPError as e:
            if e.code == 429:
                raise RuntimeError(
                    "HTTP 429: límite de solicitudes; no se reintenta"
                )

            if e.code not in (500, 502, 503, 504):
                raise

            last_error = f"HTTP {e.code}"

        except (URLError, TimeoutError) as e:
            last_error = str(e)

        if attempt < retries:
            delay = min(20, 4 * (2 ** attempt))
            print(
                f"  {last_error}; reintento en {delay}s "
                f"({attempt + 1}/{retries})",
                flush=True,
            )
            time.sleep(delay)

    raise RuntimeError(last_error or "Error HTTP sin detalle")



def commons_search(query, limit=12):
    params = "action=query&format=json&generator=search&gsrsearch=" + __import__("urllib.parse").parse.quote(query)
    params += f"&gsrnamespace=6&gsrlimit={limit}&prop=imageinfo&iiprop=url|size|mime|extmetadata"
    data = http_json("https://commons.wikimedia.org/w/api.php?" + params)
    pages = (data.get("query") or {}).get("pages") or {}
    out = []
    for p in pages.values():
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata") or {}
        out.append({
            "source": "Wikimedia Commons", "title": p.get("title", ""),
            "url": ii.get("thumburl") or ii.get("url"),
            "original_url": ii.get("url"), "page_url": "https://commons.wikimedia.org/wiki/" + __import__("urllib.parse").parse.quote(p.get("title","").replace(" ", "_")),
            "mime": ii.get("mime"), "width": ii.get("width"), "height": ii.get("height"),
            "license": (meta.get("LicenseShortName") or {}).get("value", ""),
            "creator": (meta.get("Artist") or {}).get("value", ""),
            "credit": (meta.get("Credit") or {}).get("value", ""),
            "description": (meta.get("ImageDescription") or {}).get("value", ""),
        })
    return out

def openverse_search(query, limit=12):
    url = (
        "https://api.openverse.org/v1/images/?q="
        + __import__("urllib.parse").parse.quote(query)
        + f"&page_size={limit}"
    )

    data = http_json(url)
    out = []

    mime_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "jpe": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }

    for x in data.get("results", []):
        original_url = x.get("url") or ""
        thumbnail_url = x.get("thumbnail") or ""

        filetype = str(x.get("filetype") or "").lower().strip()
        filetype = filetype.lstrip(".")

        if not filetype:
            filetype = Path(
                urlparse(original_url).path
            ).suffix.lower().lstrip(".")

        if not filetype:
            filetype = Path(
                urlparse(thumbnail_url).path
            ).suffix.lower().lstrip(".")

        mime = mime_map.get(filetype, "")

        out.append({
            "source": "Openverse",
            "title": x.get("title", ""),
            "url": original_url or thumbnail_url,
            "original_url": original_url,
            "thumbnail_url": thumbnail_url,
            "page_url": x.get("foreign_landing_url"),
            "mime": mime,
            "filetype": filetype,
            "license": x.get("license"),
            "creator": x.get("creator"),
            "credit": x.get("attribution"),
            "description": x.get("description") or x.get("title", ""),
            "width": x.get("width"),
            "height": x.get("height"),
        })

    return out


def product_queries(name, key, search_terms=None):
    product = norm(name)
    key_norm = norm(key)

    queries = []

    # Consultas específicas por producto
    SPECIAL_QUERIES = {
        "cacahuete tostado repelado sin sal": [
            "unsalted roasted blanched peanuts",
            "dry roasted peeled peanuts",
            "roasted shelled peanut kernels",
            "unsalted dry roasted peanuts",
            "blanched roasted peanuts",
            "roasted peanut kernels without skin",
            "unsalted roasted groundnuts",
        ],
    }

    for product_name, specific_queries in SPECIAL_QUERIES.items():
        if norm(product_name) == product:
            queries.extend(specific_queries)

    # Consultas originales como respaldo
    if search_terms:
        queries.extend(search_terms)

    queries.append(name)

    # Evitar búsquedas demasiado genéricas
    cleaned = []
    seen = set()

    for query in queries:
        query = str(query).strip()
        normalized = norm(query)

        if not query or normalized in seen:
            continue

        if normalized in {
            "peanut",
            "peanuts",
            "groundnut",
            "groundnuts",
            "roasted",
            "dry roasted",
        }:
            continue

        seen.add(normalized)
        cleaned.append(query)

    return cleaned[:8]

def candidate_has_contradiction(product, candidate):
    target = norm(product)
    title = norm(candidate.get("title"))
    desc = norm(candidate.get("description"))
    combined = f" {title} {desc} "

    import re

    def contains_any(text, terms):
        for term in terms:
            term = norm(term)
            pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
            if re.search(pattern, text):
                return True
        return False

    # SAL
    if "sin sal" in target:
        if contains_any(combined, ["salted", "with salt", "salty", "salado", "salada"]):
            return True, "CONTRADICCION: producto sin sal / candidato salado"

    if "con sal" in target or "salado" in target:
        if contains_any(combined, ["unsalted", "without salt", "no salt", "sin sal"]):
            return True, "CONTRADICCION: producto salado / candidato sin sal"

    # PRODUCTO CRUDO
    if contains_any(target, ["crudo", "raw"]):
        if contains_any(combined, ["roasted", "toasted", "fried", "tostado", "frito"]):
            return True, "CONTRADICCION: producto crudo / candidato procesado"

    # PRODUCTO TOSTADO
    if contains_any(target, ["tostado", "tostada", "roasted", "toasted"]):
        if contains_any(combined, ["raw", "uncooked", "unroasted", "crudo", "cruda"]):
            return True, "CONTRADICCION: producto tostado / candidato crudo"

    # PRODUCTO FRITO
    if contains_any(target, ["frito", "frita", "fried"]):
        if contains_any(combined, ["raw", "uncooked", "unroasted", "crudo", "cruda"]):
            return True, "CONTRADICCION: producto frito / candidato crudo"
        if contains_any(combined, ["roasted", "toasted", "tostado"]):
            return True, "CONTRADICCION: producto frito / candidato tostado"

    # PELADO / REPELADO / BLANQUEADO
    if contains_any(target, ["repelado", "repelada", "pelado", "pelada", "peeled", "blanched", "skinless"]):
        if contains_any(combined, ["with skin", "skin on", "unpeeled", "shell on", "con piel"]):
            return True, "CONTRADICCION: producto repelado / candidato con piel"

    # CON PIEL
    if contains_any(target, ["con piel", "skin on"]):
        if contains_any(combined, ["skinless", "peeled", "blanched", "without skin", "sin piel"]):
            return True, "CONTRADICCION: producto con piel / candidato repelado"

    # VARIANTES DE CHOCOLATE
    chocolate_variants = {
        "chocolate blanco": ["dark chocolate", "milk chocolate", "chocolate negro", "chocolate con leche"],
        "chocolate negro": ["white chocolate", "milk chocolate", "chocolate blanco", "chocolate con leche"],
        "chocolate leche": ["white chocolate", "dark chocolate", "chocolate blanco", "chocolate negro"],
    }

    for variant, incompatible in chocolate_variants.items():
        if variant in target:
            if contains_any(combined, incompatible):
                return True, f"CONTRADICCION: variante {variant}"

    # DESCARTAR ENVASES, MARCAS Y COMPOSICIONES NO DESEADAS
    forbidden = [
        "packaging", "package", "bag", "brand", "logo",
        "advertisement", "product packaging", "wrapper",
        "plastic container", "bottle", "jar", "box",
        "recipe", "menu", "restaurant", "chicken",
        "rice", "cake", "dessert", "salad", "food plate",
        "curry", "sauce", "soup", "bread",
    ]

    if contains_any(combined, forbidden):
        return True, "DESCARTADO: envase, marca, receta o plato preparado"

    return False, ""

def score_candidate(product, candidate):
    """
    Evaluación conservadora:
    1. Rechaza contradicciones.
    2. Exige evidencia de características esenciales.
    3. Puntúa calidad solo después de superar los filtros.
    """

    contradiction, reason = candidate_has_contradiction(
        product, candidate
    )

    if contradiction:
        candidate["rejection_reason"] = reason
        return -1000

    target = norm(product)
    title = norm(candidate.get("title"))
    desc = norm(candidate.get("description"))
    combined = f" {title} {desc} "

    def evidence(terms):
        for term in terms:
            term = norm(term)
            if term and term in combined:
                return True
        return False

    missing = []

    # ------------------------------------------------------------
    # 1. ALIMENTO BASE OBLIGATORIO
    # ------------------------------------------------------------

    base_found = False

    for spanish, english in SYNONYMS.items():
        spanish_norm = norm(spanish)

        if spanish_norm and spanish_norm in target:
            terms = [spanish] + list(english)

            if evidence(terms):
                base_found = True
                break

    # Para productos que no tengan sinónimo definido:
    if not base_found:
        feature_words = {
            "sin", "con", "sal", "tostado", "tostada",
            "tostar", "roasted", "toasted", "raw", "crudo",
            "cruda", "frito", "frita", "fried", "pelado",
            "pelada", "repelado", "repelada", "peeled",
            "blanched", "skinless", "piel", "blanco",
            "blanca", "negro", "negra", "leche", "chocolate",
        }

        target_base = [
            word for word in target.split()
            if len(word) > 2 and word not in feature_words
        ]

        base_found = any(
            word in title.split()
            for word in target_base
        )

    if not base_found:
        missing.append("alimento base no confirmado")

    # ------------------------------------------------------------
    # 2. PREPARACIÓN OBLIGATORIA
    # ------------------------------------------------------------

    preparation_requirements = [
        (
            ["tostado", "tostada", "roasted", "toasted"],
            ["roasted", "dry roasted", "toasted", "tostado", "tostada"],
            "tostado no confirmado",
        ),
        (
            ["crudo", "cruda", "raw"],
            ["raw", "unroasted", "uncooked", "crudo", "cruda"],
            "producto crudo no confirmado",
        ),
        (
            ["frito", "frita", "fried"],
            ["fried", "frito", "frita"],
            "producto frito no confirmado",
        ),
    ]

    for target_terms, candidate_terms, message in preparation_requirements:
        if any(norm(term) in target for term in target_terms):
            if not evidence(candidate_terms):
                missing.append(message)

    # ------------------------------------------------------------
    # 3. ESTADO DE PIEL / REPELADO
    # ------------------------------------------------------------

    peeled_target = any(
        term in target
        for term in [
            "repelado", "repelada",
            "pelado", "pelada",
        ]
    )

    if peeled_target:
        if not evidence([
            "peeled",
            "blanched",
            "skinless",
            "without skin",
            "no skin",
            "pelado",
            "pelada",
            "repelado",
            "repelada",
        ]):
            missing.append("repelado/pelado no confirmado")

    skin_target = any(
        term in target
        for term in ["con piel", "skin on"]
    )

    if skin_target:
        if not evidence([
            "with skin",
            "skin on",
            "skin-on",
            "con piel",
        ]):
            missing.append("producto con piel no confirmado")

    # ------------------------------------------------------------
    # 4. SAL
    # ------------------------------------------------------------

    unsalted_target = any(
        term in target
        for term in ["sin sal", "unsalted", "no salt"]
    )

    salted_target = (
        "con sal" in target
        or "salado" in target
        or "salada" in target
    )

    if unsalted_target:
        if not evidence([
            "unsalted",
            "without salt",
            "no salt",
            "salt free",
            "salt-free",
            "sin sal",
        ]):
            missing.append("ausencia de sal no confirmada")

    elif salted_target:
        if not evidence([
            "salted",
            "with salt",
            "salado",
            "salada",
        ]):
            missing.append("presencia de sal no confirmada")

    # ------------------------------------------------------------
    # 5. CHOCOLATE: VARIANTE OBLIGATORIA
    # ------------------------------------------------------------

    chocolate_requirements = {
        "chocolate blanco": [
            "white chocolate",
            "chocolate blanco",
        ],
        "chocolate negro": [
            "dark chocolate",
            "chocolate negro",
        ],
        "chocolate leche": [
            "milk chocolate",
            "chocolate con leche",
        ],
    }

    for variant, terms in chocolate_requirements.items():
        if variant in target:
            if not evidence(terms):
                missing.append(f"variante {variant} no confirmada")

    # ------------------------------------------------------------
    # 6. RECHAZAR SI FALTA EVIDENCIA ESENCIAL
    # ------------------------------------------------------------

    if missing:
        candidate["rejection_reason"] = (
            "EVIDENCIA INSUFICIENTE: "
            + "; ".join(missing)
        )
        return -1000

    # ------------------------------------------------------------
    # 7. PUNTUACIÓN DE CALIDAD
    # ------------------------------------------------------------

    score = 0

    target_terms = set(target.split())
    title_terms = set(title.split())

    score += 3 * len(target_terms & title_terms)

    if target and target in title:
        score += 20

    if target and target in combined:
        score += 5

    # Coincidencia del alimento base
    for spanish, english in SYNONYMS.items():
        spanish_norm = norm(spanish)

        if spanish_norm in target:
            for synonym in english:
                synonym_norm = norm(synonym)

                if synonym_norm in title:
                    score += 8
                elif synonym_norm in combined:
                    score += 4

    # Calidad de dimensiones
    width = int(candidate.get("width") or 0)
    height = int(candidate.get("height") or 0)

    if width and height:
        if width >= 1200 and height >= 900:
            score += 10
        elif width >= 900 and height >= 700:
            score += 5
        elif width < MIN_W or height < MIN_H:
            score -= 20

    # Licencia: solamente información, nunca aprobación automática
    if candidate.get("license"):
        score += 1

    candidate["evidence_verified"] = True
    candidate["rejection_reason"] = ""

    return score

def collect(product, key, delay=2, search_terms=None, source="both"):
    queries = product_queries(product, key, search_terms)
    candidates, errors = [], []
    source_map = {
        "commons": [("Wikimedia Commons", commons_search)],
        "openverse": [("Openverse", openverse_search)],
        "both": [
            ("Openverse", openverse_search),
            ("Wikimedia Commons", commons_search),
        ],
    }

    selected_sources = source_map.get(source, source_map["both"])

    for i, query in enumerate(queries):
        for source_name, fn in selected_sources:
            try:
                found = fn(query, limit=10)
                for c in found:
                    c["query"] = query

                    mime = str(c.get("mime", "")).lower().split(";")[0].strip()

                    # Solo imágenes admitidas; excluir PDF y documentos.
                    if mime not in {"image/jpeg", "image/png", "image/webp"}:
                        continue

                    # Rechazar imágenes sin dimensiones verificables.
                    width = int(c.get("width") or 0)
                    height = int(c.get("height") or 0)

                    # Rechazar dimensiones insuficientes cuando ambas
                    # estén disponibles. Si faltan, Pillow las verificará
                    # durante la descarga.
                    if width and height and (width < MIN_W or height < MIN_H):
                        continue

                    c["score"] = score_candidate(product, c)

                    # Evitar candidatos con relevancia demasiado baja.
                    if c["score"] < 8:
                        continue

                    candidates.append(c)
            except Exception as e:
                errors.append({"source": source_name, "query": query, "error": str(e)[:400]})
        if delay: time.sleep(delay)
    # dedupe by original URL, retain highest score
    unique = {}
    for c in candidates:
        url = c.get("original_url") or c.get("url")
        if not url: continue
        if url not in unique or c["score"] > unique[url]["score"]: unique[url] = c
    ranked = sorted(unique.values(), key=lambda x: (x.get("score",0), bool(x.get("license")), x.get("width",0)), reverse=True)
    status = "CANDIDATES_FOUND" if ranked else ("SOURCE_ERROR" if errors else "NO_RESULTS")
    return ranked, errors, status

def binary_download(candidate, key, index, outdir=IMAGE_DIR, retries=4):
    url = candidate.get("url") or candidate.get("original_url")
    if not safe_url(url): return {"status":"URL_REJECTED", "url":url}
    outdir.mkdir(parents=True, exist_ok=True)
    last = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept":"image/*"})
            with urlopen(req, timeout=25) as response:
                ctype = response.headers.get("Content-Type","").split(";")[0].lower()
                if ctype not in ALLOWED: raise ValueError(f"MIME no permitido: {ctype}")
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES: raise ValueError("Imagen supera 25 MB")
            if not any(data.startswith(m) for m in MAGIC[ctype]): raise ValueError("Firma binaria no coincide con MIME")
            try:
                from PIL import Image
                from io import BytesIO
                im = Image.open(BytesIO(data)); im.verify()
                im = Image.open(BytesIO(data))
                w,h = im.size; fmt=im.format
                if w < MIN_W or h < MIN_H: raise ValueError(f"Resolución insuficiente: {w}x{h}")
                if w/h > 3.2 or h/w > 3.2: raise ValueError(f"Proporción extrema: {w}x{h}")
            except ImportError: raise RuntimeError("Falta Pillow: pip install Pillow")
            digest = hashlib.sha256(data).hexdigest()
            suffix = {"image/jpeg":".jpg","image/png":".png","image/webp":".webp"}[ctype]
            path = outdir / f"{safe_key(key)}-candidate-{index}-{digest[:10]}{suffix}"
            if not path.exists(): path.write_bytes(data)
            return {"status":"DOWNLOADED_UNVERIFIED","path":path.relative_to(ROOT).as_posix(),
                    "sha256":digest,"bytes":len(data),"width":w,"height":h,"format":fmt,
                    "mime":ctype,"url":url,"attempt":attempt+1}
        except HTTPError as e:
            last = f"HTTP {e.code}"

            # No repetir descargas cuando el servidor limita solicitudes.
            if e.code == 429:
                last += ": rate limit; reintentos cancelados"
                break

            # No insistir en errores HTTP permanentes.
            if e.code not in (500, 502, 503, 504):
                break

            if attempt < retries - 1:
                time.sleep(min(2 ** attempt, 12))

        except Exception as e:
            last = str(e)
            if attempt < retries - 1:
                time.sleep(min(2 ** attempt, 12))
    return {"status":"DOWNLOAD_FAILED","url":url,"error":last}

def make_dictionary(catalog):
    letters={chr(i):[] for i in range(65,91)}
    for key, p in catalog.items():
        name=str(p.get("name") or key)
        initial=norm(name)[:1].upper() or "Z"
        if initial not in letters: initial="Z"
        letters[initial].append({
            "product_key":key,"product":name,
            "catalog_image":p.get("image") or "",
            "catalog_image_verified":bool(p.get("imageVerified",False)),
            "status":"EXISTING_IMAGE" if p.get("image") else "PENDING",
            "candidates":[],"downloads":[],"errors":[],"selected_candidate":None
        })
    for entries in letters.values(): entries.sort(key=lambda x:x["product"].casefold())
    return letters

def main():
    ap=argparse.ArgumentParser(description="Motor A-Z multi-source de búsqueda y descarga binaria")
    ap.add_argument("--delay",type=float,default=2.0)
    ap.add_argument("--resume",action="store_true")
    ap.add_argument("--retry-failed",action="store_true")
    ap.add_argument("--recheck-downloaded",action="store_true")
    ap.add_argument("--retry-empty",action="store_true")
    ap.add_argument("--letter")
    ap.add_argument("--product", help="Procesar un único producto por nombre o clave")
    ap.add_argument("--max-candidates",type=int,default=3)
    ap.add_argument("--query-limit",type=int,default=8)
    ap.add_argument("--source",choices=["both","commons","openverse"],default="both")
    ap.add_argument("--min-score",type=int,default=4)
    ap.add_argument("--dry-run", action="store_true", help="Buscar y evaluar candidatos sin descargar ni modificar archivos")
    args=ap.parse_args()
    if args.delay<0: ap.error("--delay debe ser >= 0")
    if args.max_candidates<1: ap.error("--max-candidates debe ser >= 1")
    if args.letter and args.letter.upper() not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ": ap.error("letra A-Z")
    pipeline=load_pipeline(); catalog=read_catalog(pipeline); dictionary=make_dictionary(catalog)
    old=json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {}
    state=json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else {"processed":{}}
    processed=state.setdefault("processed",{})
    if args.resume and old.get("letters"):
        dictionary=old["letters"]
        fresh=make_dictionary(catalog); known={e["product_key"] for g in dictionary.values() for e in g}
        for l in fresh:
            dictionary.setdefault(l,[])
            for e in fresh[l]:
                if e["product_key"] not in known: dictionary[l].append(e)
    letters=[args.letter.upper()] if args.letter else list(dictionary)

    # Selección de producto individual
    if args.product:
        wanted = norm(args.product)
        matches = []

        for letter, entries in dictionary.items():
            for entry in entries:
                product_name = norm(entry.get("product", ""))
                product_key = norm(entry.get("product_key", ""))

                if wanted == product_name or wanted == product_key:
                    matches.append((letter, entry))

        if not matches:
            raise SystemExit(f"ERROR: Producto no encontrado: {args.product}")

        if len(matches) > 1:
            print("AVISO: Se encontraron varias coincidencias exactas.")

        selected_letter, selected_entry = matches[0]
        dictionary = {selected_letter: [selected_entry]}
        letters = [selected_letter]
        print(f"PRODUCTO SELECCIONADO: {selected_entry['product']}", flush=True)


    # ============================================================
    # MODO SEGURO: búsqueda y evaluación sin modificar archivos
    # ============================================================
    if args.dry_run:
        print("\\n===== DRY-RUN: SIN DESCARGAS NI MODIFICACIONES =====", flush=True)
        dry_total = 0

        for letter in letters:
            entries = dictionary.get(letter, [])

            print(f"\\n===== LETRA {letter} =====", flush=True)

            for entry in entries:
                if entry.get("catalog_image"):
                    print(f"[EXISTENTE] {entry['product']}")
                    continue

                product = entry["product"]
                key = entry["product_key"]

                print(f"\\n[BUSCANDO] {product} ({key})", flush=True)

                try:
                    queries = product_queries(product, key)[:args.query_limit]
                    candidates, errors, status = collect(
                        product,
                        key,
                        args.delay,
                        queries,
                        args.source,
                    )

                    candidates = [
                        c for c in candidates
                        if c.get("score", 0) >= args.min_score
                    ]

                    print(f"  Estado: {status}")
                    print(f"  Consultas: {len(queries)}")
                    print(f"  Candidatos válidos: {len(candidates)}")

                    for index, candidate in enumerate(
                        candidates[:args.max_candidates], 1
                    ):
                        print(f"\\n  CANDIDATO {index}")
                        print(f"  Título: {candidate.get('title', '')}")
                        print(f"  Fuente: {candidate.get('source', '')}")
                        print(f"  Score: {candidate.get('score', 0)}")
                        print(f"  MIME: {candidate.get('mime', '')}")
                        print(
                            f"  Dimensiones: "
                            f"{candidate.get('width', '?')}x"
                            f"{candidate.get('height', '?')}"
                        )
                        print(f"  Licencia: {candidate.get('license', '')}")
                        print(f"  URL: {candidate.get('url', '')}")
                        print(f"  Página: {candidate.get('page_url', '')}")

                    for error in errors:
                        print(
                            f"  ERROR FUENTE: {error.get('source')} | "
                            f"{error.get('error')}"
                        )

                    dry_total += len(candidates)

                except Exception as exc:
                    print(f"  ERROR: {exc}")

        print("\\n===== DRY-RUN TERMINADO =====")
        print(f"Candidatos encontrados: {dry_total}")
        print("Descargas realizadas: 0")
        print("Archivos modificados: 0")
        print("Estado del catálogo: NO MODIFICADO")
        print("Estado de progreso: NO MODIFICADO")
        return

    total=sum(len(x) for x in dictionary.values())
    print(f"Catálogo: {total} productos | A-Z | fuentes: {args.source}",flush=True)
    for letter in letters:
        entries=dictionary.get(letter,[])
        print(f"\n{'='*55}\nLETRA {letter}: {len(entries)} productos",flush=True)
        if not entries:
            print("VACÍA — se continúa.",flush=True)
            atomic_json(OUTPUT,{"schema_version":2,"alphabet":list(dictionary),"letters":dictionary,"last_letter":letter})
            continue
        for idx,e in enumerate(entries,1):
            key,name=e["product_key"],e["product"]
            if e.get("catalog_image"): e["status"]="EXISTING_IMAGE"; continue
            oldstatus=processed.get(key,{}).get("status")
            if args.resume and oldstatus in {"DOWNLOADED_UNVERIFIED","NO_RESULTS_RELEVANT","NO_RESULTS","SOURCE_ERROR","CANDIDATES_FOUND_DOWNLOAD_FAILED"} and not (
                args.retry_failed and oldstatus in {"NO_RESULTS_RELEVANT","NO_RESULTS","SOURCE_ERROR","CANDIDATES_FOUND_DOWNLOAD_FAILED"} or
                args.recheck_downloaded and oldstatus=="DOWNLOADED_UNVERIFIED" or args.retry_empty and oldstatus in {"NO_RESULTS","NO_RESULTS_RELEVANT"}
            ):
                e["status"]=oldstatus; continue
            print(f"[{idx}/{len(entries)}] {name} ({key})",flush=True)
            try:
                qs=product_queries(name,key)[:args.query_limit]
                cand,errs,status=collect(name,key,args.delay,qs,args.source)
                cand=[c for c in cand if c.get("score",0)>=args.min_score]
                e["queries"]=qs; e["candidates"]=cand[:30]; e["errors"]=errs; e["search_status"]=status
                downloads=[]
                for ci,c in enumerate(cand[:args.max_candidates],1):
                    d=binary_download(c,key,ci)
                    d.update({"candidate_index":ci,"candidate":c})
                    downloads.append(d)
                e["downloads"]=downloads
                successful=[d for d in downloads if d["status"]=="DOWNLOADED_UNVERIFIED"]
                e["selected_candidates"]=[d["candidate"] for d in successful]
                e["selected_candidate"]=successful[0]["candidate"] if successful else None
                e["status"]="DOWNLOADED_UNVERIFIED" if successful else ("CANDIDATES_FOUND_DOWNLOAD_FAILED" if cand else status)
                processed[key]={"status":e["status"],"timestamp":time.time(),"candidate_count":len(cand),"downloaded_count":len(successful)}
                print(f"  candidatos={len(cand)} | descargas={len(successful)} | estado={e['status']}",flush=True)
            except Exception as exc:
                tb = traceback.format_exc()
                e["status"]="SCRIPT_ERROR"
                e.setdefault("errors", []).append({
                    "status":"SCRIPT_ERROR",
                    "error":str(exc)[:500],
                    "traceback":tb[-5000:]
                })
                processed[key]={
                    "status":"SCRIPT_ERROR",
                    "timestamp":time.time(),
                    "error":str(exc)[:500],
                    "traceback":tb[-5000:]
                }
                print("  ERROR aislado:",repr(exc),flush=True)
                print(tb,flush=True)
            state["last_product"]=key;state["last_letter"]=letter;state["last_run"]=time.time()
            atomic_json(OUTPUT,{"schema_version":2,"alphabet":list(dictionary),"letters":dictionary,"last_letter":letter})
            atomic_json(STATE_PATH,state)
            atomic_json(MANIFEST_PATH,[{"letter":l,**e} for l,g in dictionary.items() for e in g if e.get("candidates") or e.get("selected_candidate")])
    summary={"products":sum(map(len,dictionary.values())),
             "existing_images":sum(e["status"]=="EXISTING_IMAGE" for g in dictionary.values() for e in g),
             "downloaded_unverified":sum(e["status"]=="DOWNLOADED_UNVERIFIED" for g in dictionary.values() for e in g),
             "empty_letters":[l for l,g in dictionary.items() if not g],
             "pending_or_failed":sum(e["status"] not in {"EXISTING_IMAGE","DOWNLOADED_UNVERIFIED"} for g in dictionary.values() for e in g)}
    atomic_json(OUTPUT,{"schema_version":2,"alphabet":list(dictionary),"letters":dictionary,"summary":summary})
    atomic_json(STATE_PATH,state)
    atomic_json(MANIFEST_PATH,[{"letter":l,**e} for l,g in dictionary.items() for e in g if e.get("candidates") or e.get("selected_candidate")])
    print("\nPROCESO A-Z TERMINADO");print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
