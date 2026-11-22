#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Almendras de Málaga — image candidate batch pipeline v12.

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
UA = "AlmendrasDeMalagaCatalogPhotoAudit/14.0"
ENGINE_VERSION = "14.0"
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
    "revueloTresPasas": ["three varieties of raisins","three types of raisins mix","mixed raisin varieties","mezcla de pasas de tres variedades"],
    "revueloPacoJose": ["Paco Jose mixed nuts","Paco José frutos secos mix","mixed nuts assortment"],
    "revueloDulceMCarmen": ["sweet mix assortment","sweet confectionery mix","mezcla dulce frutos secos"],
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

SEARCH_RECOVERY_TERMS = {
    # Broad ingredient-first queries run only after the exact catalog phrases.
    # They widen retrieval; candidate_score still enforces product identity
    # and rejects contradictory evidence before a file can be downloaded.
    "almendraFritaGirasol": ["almonds", "almond kernels", "almendras"],
    "almendraFritaSinSal": ["almonds", "almond kernels", "almendras"],
    "cacahueteFritoRepeladoSinSal": ["blanched peanuts", "shelled peanuts", "peanut kernels", "cacahuetes pelados"],
    "cacahueteTostadoRepeladoSinSal": ["roasted peanuts", "shelled peanuts", "peanut kernels", "cacahuetes pelados"],
    "anacardoFritoSinSal": ["cashew nuts", "cashew kernels", "cashews", "anacardos"],
    "macadamiaFritaSal": ["macadamia nuts", "macadamia kernels", "macadamia"],
    "macadamiaFritaSinSal": ["macadamia nuts", "macadamia kernels", "macadamia"],
    "macadamiaTostadaSinSal": ["roasted macadamia nuts", "macadamia nuts", "macadamia kernels"],
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
    "revueloTresPasas": ["raisin","raisins","pasas"],
    "revueloPacoJose": ["mixed nuts","nut mix","nuts","frutos secos","revuelto"],
    "revueloDulceMCarmen": ["sweet mix","sweet assortment","candy mix","mezcla dulce","mixed sweets","sweet snack mix"],
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
    "revueloTresPasas": [["three varieties", "three types", "varieties", "variety", "tres variedades", "tres tipos"]],
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
    "market", "market stall", "market stand", "grocery store", "shop window", "storefront", "shop", "store", "retail", "panoramio", "arahova",
    "restaurant dish", "served with", "plated", "main course", "lunch", "dinner",
    "anchovy", "shishito", "donut", "doughnut", "candy apple", "caramel apple",
    "bottle", "bouteille", "jar", "packaging", "package", "wrapper", "wrappers",
    "label", "brand logo", "retail box", "sealed bag", "trader joe", "russell stover", "milkaut", "les anis de flavigny", "north charleston"
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
                          ["chocolate"], ["mixed", "mix", "assorted", "assortment"],
                          ["covered", "coated", "chocolate covered", "chocolate-coated"]],
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
    "pictolinEucaliptoSA": [["pictolin"], ["eucalyptus", "eucalipto"], ["sugar free", "sugar-free", "sugarfree", "sin azúcar"]],
    "pictolinEucaliptoCA": [["pictolin"], ["eucalyptus", "eucalipto"], ["with sugar", "sugared", "con azúcar", "con azucar"]],
    "pictolinFullmintSA": [["pictolin"], ["fullmint", "mint", "menta"], ["sugar free", "sugar-free", "sugarfree", "sin azúcar"]],
    "pictolinFullmintCA": [["pictolin"], ["fullmint", "mint", "menta"], ["with sugar", "sugared", "con azúcar", "con azucar"]],
    "pictolinMielLimonSA": [["pictolin"], ["honey lemon", "miel limón", "miel limon"], ["sugar free", "sugar-free", "sugarfree", "sin azúcar"]],
    "pictolinMielLimonCA": [["pictolin"], ["honey lemon", "miel limón", "miel limon"], ["with sugar", "sugared", "con azúcar", "con azucar"]],
    "pictolinAnisSA": [["pictolin"], ["anise", "anis", "anís"], ["sugar free", "sugar-free", "sugarfree", "sin azúcar"]],
    "pictolinAnisCA": [["pictolin"], ["anise", "anis", "anís"], ["with sugar", "sugared", "con azúcar", "con azucar"]],
    "pictolinFruta": [["pictolin"], ["fruit", "fruta"], ["sugar free", "sugar-free", "sugarfree", "sin azúcar"]],
}

PRODUCT_IDENTITY_GROUPS = {
    # Product families that were false-positive in the v11 Termux audit.
    "revueloTostadoSinSal": [["mixed nuts", "nuts mix", "nut mix", "assorted nuts", "trail mix"]],
    "revueloEspecial": [["mixed nuts", "nuts mix", "nut mix", "assorted nuts", "trail mix"]],
    "revueloTresPasas": [["raisins", "raisin", "pasas"]],
    "revueloPacoJose": [["mixed nuts", "nuts mix", "nut mix", "assorted nuts", "trail mix"]],
    "revueloDulceMCarmen": [["sweet mix", "sweet assortment", "candy mix", "mezcla dulce", "mixed sweets", "sweet snack mix"]],
    "revueloDeliciasVirginia": [["mixed nuts", "nuts mix", "nut mix", "assorted nuts", "trail mix"]],
    "revueltoChocolates": [["mixed chocolate", "chocolate assortment", "assorted chocolates"],
                          ["nuts", "nut", "fruit", "fruits"]],
    "nuezCaramelizada": [["walnut", "walnuts", "nuez", "nueces"],
                         ["caramelized", "caramelised", "candied", "caramel", "garrapiñada"]],
    "melonDeshidratado": [["melon", "melón"], ["dried", "dehydrated", "deshidratado"]],
    "chocolateNuezLeche": [["walnut", "walnuts", "nuez", "nueces"],
                           ["chocolate"], ["milk chocolate", "chocolate con leche", "chocolate with milk"]],
    "chocolatePistachoLeche": [["pistachio", "pistachios", "pistacho", "pistachos"],
                               ["chocolate"], ["milk chocolate", "chocolate con leche", "chocolate with milk"]],
    "chocolateAvellanaNegro": [["hazelnut", "hazelnuts", "avellana", "avellanas"],
                               ["chocolate"], ["dark chocolate", "chocolate negro", "chocolate amargo"]],
    "arandanoChocolateNegro": [["cranberry", "cranberries", "arándano", "arándanos"],
                               ["chocolate"], ["dark chocolate", "chocolate negro", "chocolate amargo"]],
    "almendraChocolateLeche": [["almond", "almonds", "almendra", "almendras"],
                               ["chocolate"], ["milk chocolate", "chocolate con leche", "chocolate with milk"]],
    "almendraChocolateBlanco": [["almond", "almonds", "almendra", "almendras"],
                                ["white chocolate", "chocolate blanco"]],
    "mangoChocolateNegro": [["mango", "mangos"], ["chocolate"],
                            ["dark chocolate", "chocolate negro", "chocolate amargo"]],
    "platanoChocolateLeche": [["banana", "bananas", "plantain", "plátano", "plátanos"],
                              ["chocolate"], ["milk chocolate", "chocolate con leche", "chocolate with milk"]],
    "cacahueteChocolateNegro": [["peanut", "peanuts", "cacahuete", "cacahuetes"],
                                ["chocolate"], ["dark chocolate", "chocolate negro", "chocolate amargo"]],
    "cacahueteChocolateLeche": [["peanut", "peanuts", "cacahuete", "cacahuetes"],
                                ["chocolate"], ["milk chocolate", "chocolate con leche", "chocolate with milk"]],
    "cacahueteChocolateBlanco": [["peanut", "peanuts", "cacahuete", "cacahuetes"],
                                 ["white chocolate", "chocolate blanco"]],
    "mixChocolatesPipa": [["sunflower seeds", "sunflower seed", "pipas"],
                          ["chocolate"], ["mixed", "mix", "assorted", "assortment"],
                          ["covered", "coated", "chocolate covered", "chocolate-coated"]],
}
PRODUCT_FORBIDDEN_TERMS = {
    "almendraFritaGirasol": ["olive oil", "aceite de oliva", "peanut oil", "aceite de cacahuete"],
    "almendraFritaSinSal": ["salt", "salted", "with salt", "salty", "con sal", "salado", "salada"],
    "cacahueteFritoRepeladoSinSal": ["salt", "salted", "with salt", "salty", "con sal", "salado", "salada", "in shell", "with shell", "con cáscara", "con cascara"],
    "cacahueteTostadoRepeladoSinSal": [
        "salt", "salted", "salt-roasted", "salt roasted", "with salt", "salty", "con sal", "salado", "salada", "in shell", "with shell",
        "con cáscara", "con cascara", "cáscara y sal", "cascara y sal"
    ],
    "anacardoFritoSinSal": ["salt", "salted", "with salt", "salty", "con sal", "salado", "salada"],
    "macadamiaFritaSal": ["unsalted", "no salt", "without salt", "sin sal"],
    "macadamiaFritaSinSal": ["salt", "salted", "with salt", "salty", "con sal", "salado", "salada"],
    "macadamiaTostadaSinSal": ["salt", "salted", "with salt", "salty", "con sal", "salado", "salada"],
    "melonDeshidratado": ["bitter melon", "melón amargo", "melon amargo", "momordica", "goya"],
    "nuezCaramelizada": ["pain au chocolat", "pain au choc", "pastry", "croissant", "bakery"],
    "revueloEspecial": ["space food", "comida espacial"],
    "revueloDulceMCarmen": ["stew", "guiso", "porotos", "chorizo", "soup"],
    "revueloTresPasas": ["trail mix", "nut mix", "mixed nuts", "peanuts", "walnuts", "almonds", "sunflower seeds", "pumpkin seeds", "cranberries", "cranberry"],
    "revueloDeliciasVirginia": ["granola bar", "cereal bar", "chewy bar", "nature valley", "barrita", "granola"],
    "chocolateNuezLeche": ["rice pudding", "arroz con leche", "arroz"],
    "chocolateAvellanaNegro": ["chocolate bar", "suklaapatukka", "barrita", "bar of chocolate", "chocolate tablet"],
}

STRICT_FORBIDDEN_TERMS = {
    "cafeDryCA": ["sugar free", "sugar-free", "sugarfree", "sin azúcar", "sans sucre"],
    "pictolinEucaliptoCA": ["sugar free", "sugar-free", "sugarfree", "sin azúcar"],
    "pictolinFullmintCA": ["sugar free", "sugar-free", "sugarfree", "sin azúcar"],
    "pictolinMielLimonCA": ["sugar free", "sugar-free", "sugarfree", "sin azúcar"],
    "pictolinAnisCA": ["sugar free", "sugar-free", "sugarfree", "sin azúcar"],
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
        "srsearch": query, "srnamespace": 6, "srlimit": 30
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
            "description": re.sub(r"<[^>]+>", " ", (meta.get("ImageDescription") or {}).get("value", "")),
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
        "q": query, "page_size": 30, "mature": "false",
        "license": "cc0,by,by-sa"
    }, "Openverse")
    if err:
        return [], err
    found = []
    for item in data.get("results", []):
        found.append({
            "source": "Openverse", "title": item.get("title", ""),
            "description": item.get("description") or "",
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
    """Require product identity in title/tags; keep unseen preparation details as warnings."""
    title = str(candidate.get("title") or "")
    tags = " ".join(str(x) for x in (candidate.get("tags") or []))
    description = str(candidate.get("description") or "")
    # Descriptions can mention incidental ingredients or unrelated scene context.
    # They may help reject a recipe, but cannot independently prove product identity.
    identity_text = " ".join([title, tags]).lower()
    full_text = " ".join([identity_text, description.lower()])

    def has_term(haystack, term):
        pattern = r"(?<!\w)" + re.escape(str(term).lower()).replace(r"\ ", r"\s+") + r"(?!\w)"
        return re.search(pattern, haystack, flags=re.IGNORECASE) is not None

    core = CORE_TERMS.get(key, [])
    if not any(has_term(identity_text, term) for term in core):
        return -100, ["missing_product_identity_in_title_or_tags"]

    negatives = [phrase for phrase in NEGATIVE_PHRASES if has_term(full_text, phrase)]
    if negatives:
        return -100, ["irrelevant_or_commercial_context:" + ",".join(negatives)]

    product_forbidden = [term for term in PRODUCT_FORBIDDEN_TERMS.get(key, [])
                         if has_term(full_text, term)]
    if product_forbidden:
        return -100, ["wrong_product_or_preparation:" + ",".join(product_forbidden)]

    identity_groups = PRODUCT_IDENTITY_GROUPS.get(key, [])
    missing_identity = [group for group in identity_groups
                        if not any(has_term(identity_text, term) for term in group)]
    if missing_identity:
        return -100, ["missing_product_family_identity"]

    BLEND_COMPOSITION_KEYS = {
        "revueloEspecial", "revueloTresPasas", "revueloPacoJose",
        "revueloDulceMCarmen", "revueloDeliciasVirginia", "revueltoChocolates"
    }

    SOFT_VARIANT_KEYS = {
        "almendraFritaGirasol", "almendraFritaSinSal",
        "cacahueteFritoRepeladoSinSal", "cacahueteTostadoRepeladoSinSal",
        "anacardoFritoSinSal", "macadamiaFritaSal", "macadamiaFritaSinSal",
        "macadamiaTostadaSinSal", "avellanaAmericanaCruda", "nuezCaramelizada",
        "revueloTostadoSinSal", "revueloEspecial", "revueloTresPasas",
        "revueloPacoJose", "revueloDulceMCarmen", "revueloDeliciasVirginia",
        "melonDeshidratado", "aloeDeshidratada", "cocoDado",
        "pipaGarrapinada", "calabazaPeladaCruda"
    }

    score = 6
    reasons = ["product_identity_in_title_or_tags"]
    if key in BLEND_COMPOSITION_KEYS:
        reasons.append("blend_composition_unverified")
    groups = MATCH_GROUPS.get(key, [])
    missing_groups = []
    for group in groups:
        if any(has_term(identity_text, term) for term in group):
            score += 2
            reasons.append("variant_keyword_match")
        else:
            missing_groups.append(group)
            if key in SOFT_VARIANT_KEYS:
                score -= 1
            else:
                return -100, ["missing_variant_keyword_group"]

    strict_groups = STRICT_MATCH_GROUPS.get(key, [])
    missing_strict = []
    for group in strict_groups:
        if any(has_term(identity_text, term) for term in group):
            score += 2
            reasons.append("strict_variant_evidence")
        else:
            missing_strict.append(group)
            if key in SOFT_VARIANT_KEYS:
                score -= 1
            else:
                return -100, ["missing_exact_variant_evidence"]

    forbidden_variants = [term for term in STRICT_FORBIDDEN_TERMS.get(key, [])
                          if has_term(full_text, term)]
    if forbidden_variants:
        return -100, ["contradictory_product_variant:" + ",".join(forbidden_variants)]

    if missing_groups or missing_strict:
        reasons.append("variant_metadata_unverified")
    if any(has_term(identity_text, x) for x in ("close up", "close-up", "isolated", "kernels", "nuts")):
        score += 1
        reasons.append("product_focus_term")
    if key == "mangoDeshidratado" and any(has_term(identity_text, x) for x in ("dried", "dehydrated", "sun-dried")):
        score += 2
        reasons.append("dried_match")
    if any(token in key.lower() for token in ("frita", "frito")):
        if any(has_term(identity_text, x) for x in ("fried", "frying", "fritas", "fritos")):
            score += 1
            reasons.append("fried_match")
        elif key not in SOFT_VARIANT_KEYS:
            score -= 1
            reasons.append("preparation_not_confirmed")
    if "tostado" in key.lower():
        if any(has_term(identity_text, x) for x in ("roasted", "tostado", "tostada")):
            score += 1
            reasons.append("roasted_match")
        elif key not in SOFT_VARIANT_KEYS:
            score -= 1
            reasons.append("preparation_not_confirmed")
    return score, reasons


def build_queries(key, name):
    # Phase order: broad visual identity first, then precise variant phrases,
    # then the original catalog label. Some APIs interpret multiword queries
    # as AND, so long exact strings alone often produce empty result sets.
    terms = []
    terms.extend(SEARCH_RECOVERY_TERMS.get(key, []))
    terms.extend(PRODUCT_SEARCH.get(key, []))
    terms.append(name)
    seen, result = set(), []
    for term in terms:
        term = term.strip()
        normalized = re.sub(r"\\s+", " ", term.lower())
        if normalized and normalized not in seen:
            result.append(term)
            seen.add(normalized)
    return result[:6]

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

def filter_and_rank(key, candidates, audit=None):
    ranked, seen = [], set()
    if audit is not None:
        audit.setdefault("raw_candidates", 0)
        audit.setdefault("accepted_candidates", 0)
        audit.setdefault("rejection_reasons", {})
        audit.setdefault("rejected_samples", [])
        audit["raw_candidates"] += len(candidates)
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
            if audit is not None:
                audit["accepted_candidates"] += 1
        elif audit is not None:
            for reason in reasons:
                audit["rejection_reasons"][reason] = audit["rejection_reasons"].get(reason, 0) + 1
            if len(audit["rejected_samples"]) < 20:
                audit["rejected_samples"].append({
                    "source": candidate.get("source"),
                    "title": candidate.get("title"),
                    "reasons": reasons
                })
    ranked.sort(key=lambda x: x.get("relevance_score", -100), reverse=True)
    return ranked

def search_product(key, name, delay, commons_blocked):
    all_candidates, errors = [], []
    commons_available = False
    openverse_available = False
    queries = build_queries(key, name)
    audit = {
        "engine_version": ENGINE_VERSION,
        "queries": [],
        "raw_candidates": 0,
        "accepted_candidates": 0,
        "rejection_reasons": {},
        "rejected_samples": []
    }
    if commons_blocked:
        errors.append({"source": "Wikimedia Commons", "status": "COOLDOWN",
                       "error": "Commons se omite temporalmente tras HTTP 429 previo"})

    # Ingredient-first fallback expands recall without weakening candidate checks.
    if not commons_blocked:
        for query in queries:
            found, err = [], None
            try:
                found, err = commons_search(query)
            except RateLimited as exc:
                errors.append({"source": "Wikimedia Commons", "status": "RATE_LIMITED", "error": str(exc)})
                commons_blocked = True
                break
            query_record = {"source": "Wikimedia Commons", "query": query,
                            "raw_count": len(found), "error": err}
            audit["queries"].append(query_record)
            if err:
                errors.append(err)
                if err.get("status") in ("NETWORK_ERROR", "SOURCE_BLOCKED"):
                    break
            else:
                commons_available = True
                all_candidates.extend(found)
            if delay:
                time.sleep(delay)
            # Do not stop at a single marginal hit; gather a few independent choices.
            if len(filter_and_rank(key, all_candidates)) >= 4:
                break

    # Always give Openverse a chance unless Commons already yielded enough candidates.
    if len(filter_and_rank(key, all_candidates)) < 4:
        for query in queries:
            try:
                found, err = openverse_search(query)
            except RateLimited as exc:
                errors.append({"source": "Openverse", "status": "RATE_LIMITED", "error": str(exc)})
                break
            audit["queries"].append({
                "source": "Openverse", "query": query,
                "raw_count": len(found), "error": err
            })
            if err:
                errors.append(err)
                if err.get("status") in ("NETWORK_ERROR", "SOURCE_BLOCKED"):
                    break
            else:
                openverse_available = True
                all_candidates.extend(found)
            if delay:
                time.sleep(delay)
            if len(filter_and_rank(key, all_candidates)) >= 4:
                break

    ranked = filter_and_rank(key, all_candidates, audit)
    if ranked:
        status = "CANDIDATES_FOUND"
    elif not commons_available and not openverse_available:
        status = "SOURCE_ERROR"
    elif errors:
        status = "PARTIAL_SOURCE_FAILURE"
    else:
        status = "NO_RESULTS_RELEVANT"
    return ranked, errors, status, commons_blocked, audit

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

def select_resume_products(products, processed, retry_no_candidates=False,
                           recheck_downloaded=False, force_retry=False):
    """Select each retryable product once per engine version unless forced.

    This prevents --resume from repeatedly selecting the same failed/no-result
    products and starving later entries in the missing-image list.
    """
    retry_statuses = {
        "SOURCE_ERROR", "INCOMPLETE_SEARCH", "DOWNLOAD_FAILED",
        "CANDIDATES_FOUND_DOWNLOAD_FAILED", "RATE_LIMITED",
        "NO_CANDIDATES", "PARTIAL_SOURCE_FAILURE"
    }
    selected = []
    for key, name in products:
        previous = processed.get(key)
        if previous is None:
            selected.append((key, name))
            continue
        status = previous.get("status")
        already_retried_this_version = (
            previous.get("last_resume_engine_version") == ENGINE_VERSION
        )
        retryable = status in retry_statuses
        retryable = retryable or (retry_no_candidates and status == "NO_RESULTS_RELEVANT")
        retryable = retryable or (recheck_downloaded and status == "DOWNLOADED_UNVERIFIED")
        if retryable and (force_retry or not already_retried_this_version):
            selected.append((key, name))
    return selected


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
    ap.add_argument("--force-retry", action="store_true",
                    help="Ignorar la marca de reintento de esta versión y volver a intentar estados fallidos")
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
        products = select_resume_products(
            products,
            processed,
            retry_no_candidates=args.retry_no_candidates,
            recheck_downloaded=args.recheck_downloaded,
            force_retry=args.force_retry
        )
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
    batch_records = []
    for index, (key, name) in enumerate(batch, 1):
        print(f"[{index}/{len(batch)}] {name} ({key})", flush=True)
        # Reuse previously found candidates when retrying a failed download.
        old_record = report_map.get(key, {})
        old_candidates = old_record.get("candidates", [])
        old_status = old_record.get("status")
        errors = []
        search_audit = {"engine_version": ENGINE_VERSION, "queries": [],
                        "raw_candidates": 0,
                        "accepted_candidates": 0, "rejection_reasons": {},
                        "rejected_samples": [], "reused_cached_candidates": False}
        if old_candidates and old_status in ("CANDIDATES_FOUND_DOWNLOAD_FAILED", "DOWNLOAD_FAILED",
                                              "CANDIDATES_FOUND", "SOURCE_ERROR"):
            search_audit["reused_cached_candidates"] = True
            candidates = filter_and_rank(key, old_candidates, search_audit)
            status = "CANDIDATES_FOUND" if candidates else "SEARCH_REQUIRED"
        else:
            candidates, errors, status, commons_blocked, search_audit = search_product(
                key, name, args.delay, commons_blocked
            )
        if status == "SEARCH_REQUIRED":
            candidates, errors, status, commons_blocked, search_audit = search_product(
                key, name, args.delay, commons_blocked
            )

        record = {"product_key": key, "product": name, "status": status,
                  "search_status": status, "engine_version": ENGINE_VERSION,
                  "processed_at": time.time(), "search_audit": search_audit,
                  "candidates": candidates[:12], "errors": errors}
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

        previous_progress = processed.get(key, {})
        processed[key] = {
            "status": record["status"],
            "timestamp": time.time(),
            "candidate_count": len(candidates),
            "search_engine_version": ENGINE_VERSION,
            "last_resume_engine_version": (
                ENGINE_VERSION if args.resume
                else previous_progress.get("last_resume_engine_version")
            )
        }
        if any(e.get("status") == "RATE_LIMITED" and e.get("source") == "Wikimedia Commons" for e in errors):
            state["commons_blocked_until"] = time.time() + 900
        elif not commons_blocked:
            state["commons_blocked_until"] = 0
        state["last_run"] = time.time()
        state["last_product"] = key
        report_map[key] = record
        batch_records.append(record)
        save_json(STATE, state)
        save_json(REPORT, list(report_map.values()))
        save_json(MANIFEST, list(manifest_map.values()))
        print(f"  búsqueda={status}; candidatos relevantes={len(candidates)}; resultado={record['status']}", flush=True)
        if search_audit:
            print(f"  consultas={len(search_audit.get('queries', []))}; candidatos_brutos={search_audit.get('raw_candidates', 0)}; aceptados={search_audit.get('accepted_candidates', 0)}", flush=True)
            if search_audit.get("rejection_reasons"):
                print("  descartes=" + json.dumps(search_audit["rejection_reasons"], ensure_ascii=False), flush=True)
            for sample in search_audit.get("rejected_samples", [])[:3]:
                print("  descartado=" + json.dumps(sample, ensure_ascii=False), flush=True)
        if errors:
            for err in errors[:4]:
                print("  fuente_error=" + json.dumps(err, ensure_ascii=False), flush=True)
        if index < len(batch):
            time.sleep(max(0, args.delay))

    print("\nLote terminado.")
    print(f"\nResumen de este lote — motor {ENGINE_VERSION}:")
    status_counts = {}
    for item in batch_records:
        status_key = item.get("status", "UNKNOWN")
        status_counts[status_key] = status_counts.get(status_key, 0) + 1
    for status_key, count in sorted(status_counts.items()):
        print(f"  {status_key}: {count}")
    print(f"\nInforme acumulado: {REPORT.relative_to(ROOT)}")
    print(f"Informe del lote actual: {len(batch_records)} productos")
    print(f"Manifiesto: {MANIFEST.relative_to(ROOT)}")
    print(f"Estado: {STATE.relative_to(ROOT)}")
    print("Ninguna imagen ha sido aprobada; data/catalog.js permanece intacto.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
