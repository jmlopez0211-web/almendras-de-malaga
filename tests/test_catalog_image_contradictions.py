import importlib.util
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "catalog_alphabet_image_batch.py"
)

spec = importlib.util.spec_from_file_location("catalog_batch", SCRIPT)
catalog_batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog_batch)


class TestCatalogImageContradictions(unittest.TestCase):

    TEST_CASES = [
        # SAL
        ("Cacahuete tostado repelado sin sal",
         "Roasted Salted Peanuts", True),

        ("Cacahuete tostado repelado sin sal",
         "Unsalted Roasted Blanched Peanuts", False),

        # CRUDOS / TOSTADOS
        ("Cacahuete crudo",
         "Roasted Peanuts", True),

        ("Almendra tostada",
         "Raw Almonds", True),

        ("Almendra tostada",
         "Roasted Almonds", False),

        # FRITOS
        ("Anacardo frito",
         "Raw Cashews", True),

        ("Anacardo frito",
         "Fried Cashews", False),

        # PIEL
        ("Almendra repelada",
         "Almonds with Skin", True),

        ("Almendra repelada",
         "Blanched Almonds", False),

        ("Almendra pelada",
         "Almonds with Skin", True),

        ("Almendra pelada",
         "Peeled Almonds", False),

        ("Almendra con piel",
         "Peeled Almonds", True),

        # CHOCOLATE
        ("Chocolate blanco",
         "Dark Chocolate Almonds", True),

        ("Chocolate blanco",
         "White Chocolate Almonds", False),

        ("Chocolate negro",
         "White Chocolate Almonds", True),

        # ENVASES
        ("Almendras",
         "Almonds in a plastic bag", True),

        ("Almendras",
         "Almonds in a jar", True),

        ("Almendras",
         "Almonds in a box", True),

        # CONTENIDO NO DESEADO
        ("Almendras",
         "Almond cake recipe", True),

        ("Almendras",
         "Almond salad", True),

        # IMAGEN LIMPIA
        ("Almendras",
         "Loose almonds on a clean background", False),
    ]

    def test_contradiction_matrix(self):
        for product, title, expected in self.TEST_CASES:
            with self.subTest(product=product, candidate=title):
                candidate = {
                    "title": title,
                    "description": "",
                    "width": 1200,
                    "height": 1000,
                    "license": "cc0",
                }

                actual, reason = (
                    catalog_batch.candidate_has_contradiction(
                        product,
                        candidate
                    )
                )

                self.assertEqual(
                    actual,
                    expected,
                    msg=(
                        f"Producto: {product}\\n"
                        f"Candidato: {title}\\n"
                        f"Esperado: {expected}\\n"
                        f"Obtenido: {actual}\\n"
                        f"Motivo: {reason}"
                    ),
                )


if __name__ == "__main__":
    unittest.main()
