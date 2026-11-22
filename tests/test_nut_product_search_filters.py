import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE_PATH = ROOT / "scripts" / "catalog_candidate_batch.py"

SPEC = importlib.util.spec_from_file_location(
    "catalog_candidate_batch_under_test",
    ENGINE_PATH
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError("No se pudo cargar el motor de imágenes.")

ENGINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENGINE)


class TestNutProductSearchFilters(unittest.TestCase):

    def test_specific_queries_have_priority(self):
        expected = {
            "cacahueteTostadoRepeladoSinSal":
                "roasted peeled peanuts isolated",
            "anacardoFritoSinSal":
                "fried cashew nuts close up",
            "macadamiaFritaSal":
                "salted fried macadamia nuts",
            "macadamiaFritaSinSal":
                "unsalted fried macadamia nuts",
            "macadamiaTostadaSinSal":
                "dry roasted macadamia nuts close up",
        }

        for key, query in expected.items():
            with self.subTest(product=key):
                queries = ENGINE.build_queries(key, key)
                self.assertTrue(queries)
                self.assertEqual(queries[0], query)

    def test_exactly_eight_products_use_scoped_filters(self):
        expected = {
            "almendraFritaGirasol",
            "almendraFritaSinSal",
            "cacahueteFritoRepeladoSinSal",
            "cacahueteTostadoRepeladoSinSal",
            "anacardoFritoSinSal",
            "macadamiaFritaSal",
            "macadamiaFritaSinSal",
            "macadamiaTostadaSinSal",
        }

        self.assertEqual(
            set(ENGINE.NUT_PRODUCT_NEGATIVE_PHRASES),
            expected
        )

    def test_rejects_unwanted_nut_product_contexts(self):
        forbidden = [
            "farm",
            "plantation",
            "historical",
            "chocolate",
            "plate",
            "bowl",
            "pan",
            "advertisement",
            "brand",
            "package",
            "packaging",
            "recipe",
        ]

        for word in forbidden:
            with self.subTest(context=word):
                candidate = {
                    "title": "Unsalted fried macadamia nuts " + word,
                    "tags": [],
                    "description": "",
                }

                score, reasons = ENGINE.candidate_score(
                    "macadamiaFritaSinSal",
                    candidate
                )

                self.assertLess(score, 0)
                self.assertTrue(reasons)

    def test_chocolate_products_are_not_given_nut_exclusions(self):
        self.assertNotIn(
            "chocolateAvellanaNegro",
            ENGINE.NUT_PRODUCT_NEGATIVE_PHRASES
        )
        self.assertNotIn(
            "chocolateNuezLeche",
            ENGINE.NUT_PRODUCT_NEGATIVE_PHRASES
        )

    def test_other_products_are_not_given_nut_exclusions(self):
        self.assertNotIn(
            "melonDeshidratado",
            ENGINE.NUT_PRODUCT_NEGATIVE_PHRASES
        )
        self.assertNotIn(
            "pictolinAnisSA",
            ENGINE.NUT_PRODUCT_NEGATIVE_PHRASES
        )


if __name__ == "__main__":
    unittest.main()
