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
UA = "AlmendrasDeMalagaCatalogPhotoAudit/8.0"
TIMEOUT = (8, 22)
ALLOWED = {"image/jpeg", "image/png", "image/webp"}
MIN_W, MIN_H, MAX_BYTES = 900, 700, 25 * 1024 * 1024

PRODUCT_SEARCH = {
    "mangoDeshidratado": ["dried mango slices", "dried mango pieces", "dehydrated mango fruit"],
    "almendraFritaGirasol": ["fried almonds sunflower oil","almonds fried in sunflower oil","almendras fritas aceite girasol"],
    "almendraFritaSinSal": ["unsalted fried almonds","fried almonds no salt","almendras fritas sin sal"],
    "cacahueteFritoRepeladoSinSal": ["fried blanched peanuts unsalted","unsalted fried shelled peanuts","cacahuete frito repelado sin sal"],
    "cacahueteTostadoRepeladoSinSal": ["dry roasted blanched peanuts unsalted","roasted shelled peanuts no salt","cacahuete tostado repelado sin sal"],
    "anacardoFritoSinSal": ["fried cashews unsalted","plain fried cashew kernels","anacardos fritos sin sal"],
    "macadamiaFritaSal": ["salted fried macadamia nuts","fried macadamia kernels","macadamia frita sal"],
    "macadamiaFritaSinSal": ["unsalted fried macadamia nuts","fried macadamia kernels no salt","macadamia frita sin sal"],
    "macadamiaTostadaSinSal": ["dry roasted macadamia nuts unsalted","roasted macadamia kernels","macadamia tostada sin sal"],
    "avellanaAmericanaCruda": ["raw American hazelnuts kernels","raw hazelnuts shelled","avellana americana cruda"],
    "nuezCaramelizada": ["caramelized walnuts","candied walnut halves","nuez caramelizada"],
    "revueloTostadoSinSal": ["unsalted roasted mixed nuts","dry roasted nut mix","revuelto tostado sin sal"],
    "revueloEspecial": ["mixed nuts and dried fruit assortment","special mixed nuts snack","revuelto frutos secos especial"],
    "revueloTresPasas": ["mixed nuts with three types raisins","nuts raisins mix","revuelto tres pasas"],
    "revueloPacoJose": ["Paco Jose mixed nuts","Paco José frutos secos mix","mixed nuts assortment"],
    "revueloDulceMCarmen": ["sweet nut mix candied nuts","sweet mixed nuts dried fruit","revuelto dulce"],
    "revueloDeliciasVirginia": ["Virginia nut mix","mixed nuts Virginia","Delicias Virginia frutos secos"],
    "melonDeshidratado": ["dried melon slices","dehydrated melon pieces","melon deshidratado"],
    "aloeDeshidratada": ["candied dried aloe vera pieces","dried aloe vera snack","aloe vera deshidratada"],
    "cocoDado": ["dried coconut cubes","dehydrated coconut chunks","coco dado deshidratado"],
    "pipaGarrapinada": ["candied sunflower seeds","caramelized sunflower seeds","pipas garrapiñadas"],
    "calabazaPeladaCruda": ["raw shelled pumpkin seeds","hulled pumpkin seeds raw","pipas calabaza peladas crudas"],
    "chocolateNuezLeche": ["milk chocolate covered walnuts","walnuts coated in milk chocolate","nuez chocolate leche"],
    "chocolatePistachoLeche": ["milk chocolate covered pistachios","pistachios coated in milk chocolate","pistacho chocolate leche"],
    "chocolateAvellanaNegro": ["dark chocolate covered hazelnuts","hazelnuts coated dark chocolate","avellana chocolate negro"],
    "avellanaTrufadaCanela": ["cinnamon truffle hazelnuts","cinnamon coated hazelnuts","avellana trufada canela"],
    "arandanoChocolateNegro": ["dark chocolate covered cranberries","cranberries coated dark chocolate","arándano chocolate negro"],
    "almendraChocolateLeche": ["milk chocolate covered almonds","almonds coated milk chocolate","almendra chocolate leche"],
    "almendraChocolateBlanco": ["white chocolate covered almonds","almonds coated white chocolate","almendra chocolate blanco"],
    "mixChocolatesAlmendra": ["mixed chocolate covered almonds","almond chocolate assortment","mix chocolates almendra"],
    "chocobolaBlanca": ["white chocolate balls confectionery","white chocolate candy balls","chocobola blanca"],
    "chocobolaLeche": ["milk chocolate balls confectionery","milk chocolate candy balls","chocobola leche"],
    "mangoChocolateNegro": ["dark chocolate covered dried mango","mango coated dark chocolate","mango chocolate negro"],
    "platanoChocolateLeche": ["milk chocolate covered banana chips","banana coated milk chocolate","platano chocolate leche"],
    "revueltoChocolates": ["mixed chocolate covered nuts and fruit","chocolate confectionery assortment","revuelto chocolates"],
    "cacahueteChocolateNegro": ["dark chocolate covered peanuts","peanuts coated dark chocolate","cacahuete chocolate negro"],
    "cacahueteChocolateLeche": ["milk chocolate covered peanuts","peanuts coated milk chocolate","cacahuete chocolate leche"],
    "cacahueteChocolateBlanco": ["white chocolate covered peanuts","peanuts coated white chocolate","cacahuete chocolate blanco"],
    "mixChocolatesPipa": ["mixed chocolate sunflower seeds","chocolate covered sunflower seeds mix","mix chocolates pipa"],
    "dulceLeche": ["dulce de leche candy","milk caramel confection","dulce de leche"],
    "ligeroPinones": ["pine nut confection","pine nut candy","ligero piñones"],
    "pinonesCaserio": ["pine nuts confection","pine nut sweets","piñones caserio"],
    "carachoco": ["carachoco candy","chocolate caramel candy","carachoco"],
    "toffinoChocolate": ["chocolate toffee candy","toffee chocolate sweets","toffino chocolate"],
    "toffeeNata": ["cream toffee candy","nata toffee sweets","toffee nata"],
    "picotasFresa": ["strawberry candy picotas","strawberry chewy sweets","picotas fresa"],
    "rellenoMiel": ["honey filled candy","honey confectionery","relleno miel"],
    "gajosSantos": ["gajos santos candy","orange lemon candy segments","gajos santos"],
    "rellenoFruta": ["fruit filled candy","fruit jelly filled sweets","relleno fruta"],
    "tacoMiel": ["honey candy block","honey sweets","taco miel"],
    "cafeDrySA": ["coffee hard candy sugar free","sugar free coffee sweets","cafe dry sin azúcar"],
    "cafeDryCA": ["coffee hard candy","coffee sweets","cafe dry con azúcar"],
    "werthersSA": ["Werthers sugar free candy","Werther's sugar free sweets","werthers sin azúcar"],
    "pictolinEucaliptoSA": ["Pictolin eucalyptus sugar free","eucalyptus sugar free candy","pictolin eucalipto sin azúcar"],
    "pictolinEucaliptoCA": ["Pictolin eucalyptus candy","eucalyptus hard sweets","pictolin eucalipto con azúcar"],
    "pictolinFullmintSA": ["Pictolin fullmint sugar free","mint sugar free candy","pictolin fullmint sin azúcar"],
    "pictolinFullmintCA": ["Pictolin fullmint mint candy","mint hard sweets","pictolin fullmint con azúcar"],
    "pictolinMielLimonSA": ["Pictolin honey lemon sugar free","honey lemon sugar free candy","pictolin miel limon sin azúcar"],
    "pictolinMielLimonCA": ["Pictolin honey lemon candy","honey lemon hard sweets","pictolin miel limon con azúcar"],
    "pictolinAnisSA": ["Pictolin anise sugar free","anise sugar free candy","pictolin anis sin azúcar"],
    "pictolinAnisCA": ["Pictolin anise candy","anise hard sweets","pictolin anis con azúcar"],
    "pictolinFruta": ["Pictolin fruit chewy candy sugar free","fruit sugar free chewy sweets","pictolin fruta sin azúcar"],
}

CORE_TERMS = {
    "mangoDeshidratado": ["mango", "mangos"],
    "almendraFritaGirasol": ["almond","almonds","almendra","almendras"],
    "almendraFritaSinSal": ["almond","almonds","almendra","almendras"],
    "cacahueteFritoRepeladoSinSal": ["peanut","peanuts","cacahuete","cacahuetes","groundnut"],
    "cacahueteTostadoRepeladoSinSal": ["peanut","peanuts","cacahuete","cacahuetes","groundnut"],
    "anacardoFritoSinSal": ["cashew","cashews","anacardo","anacardos","kaju"],
    "macadamiaFritaSal": ["macadamia"],
    "macadamiaFritaSinSal": ["macadamia"],
    "macadamiaTostadaSinSal": ["macadamia"],
    "avellanaAmericanaCruda": ["hazelnut","hazelnuts","avellana","avellanas"],
    "nuezCaramelizada": ["walnut","walnuts","nuez","nueces"],
    "revueloTostadoSinSal": ["mixed nuts","nut mix","nuts","frutos secos","revuelto"],
    "revueloEspecial": ["mixed nuts","nut mix","nuts","frutos secos","revuelto"],
    "revueloTresPasas": ["mixed nuts","nut mix","raisins","pasas","revuelto"],
    "revueloPacoJose": ["mixed nuts","nut mix","nuts","frutos secos","revuelto"],
    "revueloDulceMCarmen": ["mixed nuts","nut mix","candied nuts","frutos secos","revuelto"],
    "revueloDeliciasVirginia": ["mixed nuts","nut mix","nuts","frutos secos","revuelto"],
    "melonDeshidratado": ["melon","melón"],
    "aloeDeshidratada": ["aloe","aloe vera"],
    "cocoDado": ["coconut","coco"],
    "pipaGarrapinada": ["sunflower seeds","sunflower seed","pipas"],
    "calabazaPeladaCruda": ["pumpkin seed","pumpkin seeds","pepita","pipa de calabaza"],
    "chocolateNuezLeche": ["walnut","walnuts","nuez","nueces"],
    "chocolatePistachoLeche": ["pistachio","pistachos"],
    "chocolateAvellanaNegro": ["hazelnut","avellana"],
    "avellanaTrufadaCanela": ["hazelnut","avellana"],
    "arandanoChocolateNegro": ["cranberry","arándano"],
    "almendraChocolateLeche": ["almond","almendra"],
    "almendraChocolateBlanco": ["almond","almendra"],
    "mixChocolatesAlmendra": ["almond","almonds","almendra","almendras"],
    "chocobolaBlanca": ["chocolate","chocobola"],
    "chocobolaLeche": ["chocolate","chocobola"],
    "mangoChocolateNegro": ["mango"],
    "platanoChocolateLeche": ["banana","bananas","plantain","plátano"],
    "revueltoChocolates": ["mixed chocolate","chocolate assortment","chocolates","revuelto"],
    "cacahueteChocolateNegro": ["peanut","cacahuete"],
    "cacahueteChocolateLeche": ["peanut","cacahuete"],
    "cacahueteChocolateBlanco": ["peanut","cacahuete"],
    "mixChocolatesPipa": ["sunflower seeds","sunflower seed","pipas"],
    "dulceLeche": ["dulce de leche","milk caramel"],
    "ligeroPinones": ["pine nut","pine nuts","piñones"],
    "pinonesCaserio": ["pine nut","pine nuts","piñones"],
    "carachoco": ["carachoco","chocolate caramel"],
    "toffinoChocolate": ["toffino","toffee","chocolate"],
    "toffeeNata": ["toffee","cream toffee"],
    "picotasFresa": ["picotas","strawberry","fresa"],
    "rellenoMiel": ["honey","miel"],
    "gajosSantos": ["gajos santos","candy segments","gajos"],
    "rellenoFruta": ["fruit filled","fruit filling","relleno fruta"],
    "tacoMiel": ["honey","miel"],
    "cafeDrySA": ["coffee candy","coffee","café"],
    "cafeDryCA": ["coffee candy","coffee","café"],
    "werthersSA": ["werther","werthers"],
    "pictolinEucaliptoSA": ["pictolin","eucalyptus","eucalipto"],
    "pictolinEucaliptoCA": ["pictolin","eucalyptus","eucalipto"],
    "pictolinFullmintSA": ["pictolin","fullmint","mint"],
    "pictolinFullmintCA": ["pictolin","fullmint","mint"],
    "pictolinMielLimonSA": ["pictolin","honey lemon","miel limón"],
    "pictolinMielLimonCA": ["pictolin","honey lemon","miel limón"],
    "pictolinAnisSA": ["pictolin","anise","anis"],
    "pictolinAnisCA": ["pictolin","anise","anis"],
    "pictolinFruta": ["pictolin","fruit","fruta"],
}

MATCH_GROUPS = {
    "almendraFritaGirasol": [["almond","almonds","almendra","almendras"],["fried","frit","frita","fritas"]],
    "almendraFritaSinSal": [["almond","almonds","almendra","almendras"],["fried","frit","frita","fritas"]],
    "cacahueteFritoRepeladoSinSal": [["peanut","peanuts","cacahuete","cacahuetes"],["fried","frit","frita","fritas"]],
    "cacahueteTostadoRepeladoSinSal": [["peanut","peanuts","cacahuete","cacahuetes"],["roasted","tostado","tostada"]],
    "anacardoFritoSinSal": [["cashew","cashews","anacardo","anacardos"],["fried","frit","frita","fritas"]],
    "macadamiaFritaSal": [["macadamia"],["fried","frit","frita","fritas"]],
    "macadamiaFritaSinSal": [["macadamia"],["fried","frit","frita","fritas"]],
    "macadamiaTostadaSinSal": [["macadamia"],["roasted","tostada","tostado"]],
    "avellanaAmericanaCruda": [["hazelnut","hazelnuts","avellana","avellanas"],["raw","cruda","crudas"]],
    "nuezCaramelizada": [["walnut","walnuts","nuez","nueces"],["caramelized","candied","caramelizada","garrapiñada"]],
    "melonDeshidratado": [["melon","melón"],["dried","dehydrated","deshidratado"]],
    "aloeDeshidratada": [["aloe","aloe vera"],["dried","dehydrated","deshidratada"]],
    "cocoDado": [["coconut","coco"],["dried","dehydrated","deshidratado"]],
    "pipaGarrapinada": [["sunflower","pipa","pipas"],["candied","caramelized","garrapiñada"]],
    "calabazaPeladaCruda": [["pumpkin","calabaza"],["seed","seeds","pipa","pepita"]],
    "chocolateNuezLeche": [["walnut","walnuts","nuez","nueces"],["chocolate","coated","covered"]],
    "chocolatePistachoLeche": [["pistachio","pistachos"],["chocolate","coated","covered"]],
    "chocolateAvellanaNegro": [["hazelnut","avellana"],["chocolate","coated","covered"]],
    "arandanoChocolateNegro": [["cranberry","arándano"],["chocolate","coated","covered"]],
    "almendraChocolateLeche": [["almond","almendra"],["chocolate","coated","covered"]],
    "almendraChocolateBlanco": [["almond","almendra"],["white chocolate","chocolate blanco","covered","coated"]],
    "mangoChocolateNegro": [["mango"],["chocolate","coated","covered"]],
    "platanoChocolateLeche": [["banana","plantain","plátano"],["chocolate","coated","covered"]],
    "cacahueteChocolateNegro": [["peanut","cacahuete"],["chocolate","coated","covered"]],
    "cacahueteChocolateLeche": [["peanut","cacahuete"],["chocolate","coated","covered"]],
    "cacahueteChocolateBlanco": [["peanut","cacahuete"],["white chocolate","chocolate blanco","coated","covered"]],
    "avellanaTrufadaCanela": [["hazelnut","avellana"],["truffle","trufada","cinnamon","canela"]],
    "chocobolaBlanca": [["chocolate","chocobola"],["ball","balls","bola","bolas"]],
    "chocobolaLeche": [["chocolate","chocobola"],["ball","balls","bola","bolas"]],
}
# Reject food scenes, recipes, retail contexts and packaging: the catalog requires
# clean photographs of the actual food, not a dish, shop or commercial pack.
NEGATIVE_PHRASES = [
    "menu", "banquet", "breakfast", "restaurant", "chicken", "trout", "rice",
    "noodles", "eggplant", "shrimp", "prawn", "salad", "stir fry", "curry",
    "tart", "cake", "dessert", "ice cream", "yogurt", "tofu", "recipe",
    "cooking class", "food blogger", "man frying", "woman frying",
    "person cooking", "chef preparing", "farmers market", "farmer's market",
    "market stall", "market stand", "grocery store", "shop window", "storefront",
    "restaurant dish", "served with", "plated", "main course", "lunch", "dinner",
    "anchovy", "shishito", "donut", "doughnut", "candy apple", "caramel apple",
    "bottle", "bouteille", "jar", "packaging", "package", "wrapper", "wrappers",
    "label", "brand logo", "retail box", "sealed bag"
]

# High-risk variants require their distinguishing words in title, tags or description.
# If a source does not document those details, no candidate is preferred over a wrong photo.
STRICT_MATCH_GROUPS = {
    "ligeroPinones": [["pine nut", "pine nuts", "piñon", "piñones"],
                      ["candy", "confection", "praline", "praliné", "nougat", "sweet"]],
    "tacoMiel": [["honey", "miel"],
                 ["candy", "confection", "sweet", "caramel"]],
    "carachoco": [["carachoco"], ["candy", "confection", "sweet"]],
    "toffinoChocolate": [["toffino"], ["chocolate"], ["candy", "confection", "toffee"]],
    "toffeeNata": [["toffee"], ["cream", "nata", "milk"],
                   ["candy", "confection", "sweet"]],
    "cafeDrySA": [["coffee", "café"], ["candy", "sweet", "confection"],
                  ["sugar free", "sugar-free", "sugarfree", "sin azúcar", "sans sucre"]],
    "cafeDryCA": [["coffee", "café"], ["candy", "sweet", "confection"]],
    "werthersSA": [["werther"], ["sugar free", "sugar-free", "sugarfree", "sin azúcar"]],
    "dulceLeche": [["dulce de leche", "milk caramel"], ["candy", "confection", "caramel"]],
    "revueltoChocolates": [["chocolate"], ["mixed", "mix", "assorted", "assortment"],
                           ["nuts", "nut", "fruits", "fruit"]],
    "cacahueteChocolateNegro": [["peanut", "peanuts", "cacahuete"],
                                ["chocolate"], ["dark", "negro"]],
    "cacahueteChocolateLeche": [["peanut", "peanuts", "cacahuete"],
                                ["chocolate"], ["milk", "leche"]],
    "cacahueteChocolateBlanco": [["peanut", "peanuts", "cacahuete"],
                                 ["white chocolate", "chocolate blanco"]],
    "chocolateNuezLeche": [["walnut", "walnuts", "nuez"], ["chocolate"],
                           ["milk", "leche"]],
    "chocolatePistachoLeche": [["pistachio", "pistachos"], ["chocolate"],
                               ["milk", "leche"]],
    "chocolateAvellanaNegro": [["hazelnut", "avellana"], ["chocolate"],
                               ["dark", "negro"]],
    "arandanoChocolateNegro": [["cranberry", "arándano"], ["chocolate"],
                               ["dark", "negro"]],
    "almendraChocolateLeche": [["almond", "almendra"], ["chocolate"],
                               ["milk", "leche"]],
    "almendraChocolateBlanco": [["almond", "almendra"],
                                ["white chocolate", "chocolate blanco"]],
    "mangoChocolateNegro": [["mango"], ["chocolate"], ["dark", "negro"]],
    "platanoChocolateLeche": [["banana", "plantain", "plátano"], ["chocolate"],
                              ["milk", "leche"]],
    "mixChocolatesPipa": [["sunflower", "sunflower seeds", "pipas"],
                          ["chocolate"], ["mixed", "mix", "assorted", "assortment"]],
    "cacahueteTostadoRepeladoSinSal": [["peanut", "peanuts", "cacahuete"],
                                       ["roasted", "tostado", "tostada"],
                                       ["unsalted", "no salt", "without salt", "sin sal"]],
    "cacahueteFritoRepeladoSinSal": [["peanut", "peanuts", "cacahuete"],
                                     ["fried", "frit", "frita", "fritas"],
                                     ["unsalted", "no salt", "without salt", "sin sal"]],
    "almendraFritaGirasol": [["almond", "almonds", "almendra"],
                             ["fried", "frit", "frita", "fritas"],
                             ["sunflower oil", "aceite de girasol"]],
    "almendraFritaSinSal": [["almond", "almonds", "almendra"],
                            ["fried", "frit", "frita", "fritas"],
                            ["unsalted", "no salt", "without salt", "sin sal"]],
    "anacardoFritoSinSal": [["cashew", "cashews", "anacardo"],
                            ["fried", "frit", "frita", "fritas"],
                            ["unsalted", "no salt", "without salt", "sin sal"]],
    "macadamiaFritaSal": [["macadamia"], ["fried", "frit", "frita", "fritas"],
                          ["salted", "with salt", "salada", "con sal"]],
    "macadamiaFritaSinSal": [["macadamia"], ["fried", "frit", "frita", "fritas"],
                             ["unsalted", "no salt", "without salt", "sin sal"]],
    "macadamiaTostadaSinSal": [["macadamia"], ["roasted", "tostada", "tostado"],
                               ["unsalted", "no salt", "without salt", "sin sal"]],
    "avellanaAmericanaCruda": [["hazelnut", "hazelnuts", "avellana"],
                               ["raw", "cruda", "crudas"]],
    "nuezCaramelizada": [["walnut", "walnuts", "nuez"],
                         ["caramelized", "candied", "caramelizada", "garrapiñada"]],
    "melonDeshidratado": [["melon", "melón"], ["dried", "dehydrated", "deshidratado"]],
    "aloeDeshidratada": [["aloe", "aloe vera"], ["dried", "dehydrated", "deshidratada"]],
    "cocoDado": [["coconut", "coco"], ["dried", "dehydrated", "deshidratado"]],
    "pipaGarrapinada": [["sunflower", "pipa", "pipas"],
                        ["candied", "caramelized", "garrapiñada"]],
}

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
    # Retry transient DNS/TLS/socket errors, 5xx and 429 with bounded backoff.
    headers = {"User-Agent": UA, "Accept": "application/json",
               "Accept-Language": "es,en;q=0.8"}
    last_error = None
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            last_error = {"source": source, "status": "NETWORK_ERROR",
                          "attempt": attempt + 1, "error": str(e)[:500]}
            if attempt < 3:
                time.sleep(min(2 ** attempt, 8))
                continue
            return None, last_error
        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            wait = min(float(retry_after) if retry_after and retry_after.isdigit()
                       else 2 ** attempt, 30)
            last_error = {"source": source, "status": "RATE_LIMITED",
                          "http": 429, "attempt": attempt + 1,
                          "retry_after_seconds": wait}
            if attempt < 3:
                time.sleep(wait)
                continue
            return None, last_error
        if r.status_code >= 500 and attempt < 3:
            last_error = {"source": source, "status": "HTTP_ERROR",
                          "http": r.status_code, "attempt": attempt + 1,
                          "body": r.text[:180]}
            time.sleep(min(2 ** attempt, 8))
            continue
        if r.status_code in (401, 403):
            return None, {"source": source, "status": "SOURCE_BLOCKED",
                          "http": r.status_code, "body": r.text[:180]}
        if not r.ok:
            return None, {"source": source, "status": "HTTP_ERROR",
                          "http": r.status_code, "body": r.text[:180]}
        try:
            return r.json(), None
        except ValueError:
            return None, {"source": source, "status": "BAD_JSON",
                          "http": r.status_code, "body": r.text[:180]}
    return None, last_error

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
        str(candidate.get("description") or ""),
        " ".join(candidate.get("tags") or []),
        str(candidate.get("commons_title") or "")
    ]).lower()
    core = CORE_TERMS.get(key, [])
    if not any(term in text for term in core):
        return -100, ["missing_product_keyword"]

    negatives = [phrase for phrase in NEGATIVE_PHRASES if phrase in text]
    if negatives:
        return -100, ["irrelevant_or_commercial_context:" + ",".join(negatives)]

    groups = MATCH_GROUPS.get(key, [])
    if any(not any(term in text for term in group) for group in groups):
        return -100, ["missing_variant_keyword_group"]

    strict_groups = STRICT_MATCH_GROUPS.get(key, [])
    missing_strict = [group for group in strict_groups if not any(term in text for term in group)]
    if missing_strict:
        return -100, ["missing_exact_variant_evidence"]

    score = 8
    reasons = ["product_keyword_match"]
    if groups:
        score += min(3, len(groups))
        reasons.append("variant_keywords_match")
    if strict_groups:
        score += min(6, len(strict_groups))
        reasons.append("strict_variant_evidence")
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
        if any(x in text for x in ("roasted", "tostado", "tostada")):
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
                # Successful API response is source availability even if no files matched.
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
    elif not commons_available and not openverse_available:
        status = "SOURCE_ERROR"
    elif errors:
        status = "PARTIAL_SOURCE_FAILURE"
    else:
        status = "NO_RESULTS_RELEVANT"
    return ranked, errors, status, commons_blocked

def download_candidate(key, candidate):
    """Retry transient download failures and validate every downloaded image."""
    OUT.mkdir(parents=True, exist_ok=True)
    urls = []
    for u in (candidate.get("url"), candidate.get("thumbnail")):
        if u and "api.openverse.org/v1/images/" in u and u.rstrip("/").endswith("/thumb"):
            continue
        if u and u not in urls:
            urls.append(u)
    errors = []
    headers = {"User-Agent": UA, "Accept": "image/*,*/*;q=0.8", "Accept-Language": "es,en;q=0.8"}
    if candidate.get("source_page"):
        headers["Referer"] = candidate["source_page"]
    for url in urls:
        if urlparse(url).scheme not in ("http", "https"):
            errors.append({"url": url, "error": "invalid_url_scheme"})
            continue
        data = None
        content_type = ""
        final_url = url
        for attempt in range(3):
            try:
                with requests.get(url, headers=headers, stream=True, timeout=TIMEOUT, allow_redirects=True) as response:
                    final_url = response.url
                    if response.status_code == 429 or response.status_code >= 500:
                        raw = response.headers.get("Retry-After", "")
                        try:
                            wait = min(float(raw), 20) if raw else (1.5 ** attempt)
                        except ValueError:
                            wait = 1.5 ** attempt
                        errors.append({"url": url, "attempt": attempt + 1, "error": "HTTP " + str(response.status_code), "retry_after_seconds": wait})
                        if attempt < 2:
                            time.sleep(wait)
                            continue
                        break
                    if response.status_code in (401, 403, 404, 410):
                        errors.append({"url": url, "error": "HTTP " + str(response.status_code)})
                        break
                    response.raise_for_status()
                    content_type = (response.headers.get("Content-Type") or "").split(";")[0].lower()
                    parts, size = [], 0
                    for chunk in response.iter_content(65536):
                        if not chunk:
                            continue
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise ValueError("image_over_25MB")
                        parts.append(chunk)
                    data = b"".join(parts)
                if not data:
                    raise ValueError("empty_download")
                if content_type and not content_type.startswith("image/"):
                    raise ValueError("non_image_content_type:" + content_type)
                break
            except requests.RequestException as exc:
                errors.append({"url": url, "attempt": attempt + 1, "error": "NETWORK:" + str(exc)[:250]})
                if attempt < 2:
                    time.sleep(1.5 ** attempt)
                    continue
                break
            except Exception as exc:
                errors.append({"url": url, "attempt": attempt + 1, "error": str(exc)[:300]})
                break
        if not data:
            continue
        try:
            img = Image.open(BytesIO(data))
            img.verify()
            img = Image.open(BytesIO(data))
            if img.format not in ("JPEG", "PNG", "WEBP"):
                raise ValueError("unsupported_image_format:" + str(img.format))
            if img.width < MIN_W or img.height < MIN_H:
                raise ValueError("low_resolution:" + str(img.width) + "x" + str(img.height))
            ext = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[img.format]
            target = OUT / (re.sub(r"[^A-Za-z0-9_-]", "_", key) + "-candidate" + ext)
            temp = target.with_suffix(target.suffix + ".tmp")
            temp.write_bytes(data)
            temp.replace(target)
            warnings = []
            if any(x in key.lower() for x in ("sinsal", "sin_sal", "girasol", "oliva")):
                warnings.append("La foto no permite verificar ausencia de sal ni tipo de aceite; requiere confirmación documental.")
            return {"status": "DOWNLOADED_UNVERIFIED", "path": target.relative_to(ROOT).as_posix(),
                    "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                    "width": img.width, "height": img.height, "format": img.format,
                    "content_type": content_type, "used_url": url, "final_url": final_url,
                    "url_errors": errors, "variant_warnings": warnings}
        except Exception as exc:
            errors.append({"url": url, "error": "IMAGE_VALIDATION:" + str(exc)[:300]})
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
        print("Diagnóstico de conectividad del motor de imágenes", flush=True)
        print(f"Python: {sys.version.split()[0]} | Requests: {requests.__version__} | Pillow: {Image.__version__}", flush=True)
        for source, url, params in [
            ("Wikimedia Commons", COMMONS_API, {"action":"query","format":"json","meta":"siteinfo"}),
            ("Openverse", OPENVERSE_API, {"q":"dried mango","page_size":1,"mature":"false","license":"cc0,by,by-sa"})
        ]:
            data, error = request_json(url, params, source)
            if error:
                print(f"{source}: FAIL | {json.dumps(error, ensure_ascii=False)}", flush=True)
            else:
                count = len(data.get("results", [])) if source == "Openverse" else "API response"
                print(f"{source}: OK | {count}", flush=True)
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
                 "PARTIAL_SOURCE_FAILURE"}
        if args.retry_no_candidates:
            retry.add("NO_RESULTS_RELEVANT")
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
        if errors:
            for err in errors[:4]:
                print("  fuente_error=" + json.dumps(err, ensure_ascii=False), flush=True)
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
