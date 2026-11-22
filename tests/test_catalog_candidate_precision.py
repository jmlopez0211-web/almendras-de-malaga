"""Precision regression tests for the product-specific image candidate scorer.

The scoring function and its declarative dictionaries are extracted from the
production script's AST so tests do not need network access, requests or Pillow.
"""
import ast
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "catalog_candidate_batch.py"
TREE = ast.parse(SCRIPT.read_text(encoding="utf-8"))

NEEDED = {
    "CORE_TERMS",
    "MATCH_GROUPS",
    "STRICT_MATCH_GROUPS",
    "STRICT_FORBIDDEN_TERMS",
    "PRODUCT_IDENTITY_GROUPS",
    "PRODUCT_FORBIDDEN_TERMS",
    "NEGATIVE_PHRASES",
    "candidate_score",
}
selected = []
for node in TREE.body:
    if isinstance(node, ast.FunctionDef) and node.name in NEEDED:
        selected.append(node)
    elif isinstance(node, ast.Assign):
        names = {target.id for target in node.targets if isinstance(target, ast.Name)}
        if names & NEEDED:
            selected.append(node)

namespace = {}
module = ast.Module(body=selected, type_ignores=[])
exec(compile(module, str(SCRIPT), "exec"), namespace)
candidate_score = namespace["candidate_score"]


class TestCatalogCandidatePrecision(unittest.TestCase):
    def score(self, key, title, description=""):
        return candidate_score(key, {"title": title, "description": description, "tags": []})

    def test_rejects_savory_pine_nut_dish(self):
        score, reasons = self.score(
            "ligeroPinones",
            "Steamed shishito pepper, candied anchovy, pine nuts, doenjang"
        )
        self.assertLess(score, 0)
        self.assertTrue(any("irrelevant" in reason for reason in reasons))

    def test_rejects_honey_dipped_donuts_as_taco_de_miel(self):
        score, _ = self.score("tacoMiel", "Honey-dipped donuts - dessert")
        self.assertLess(score, 0)

    def test_rejects_chocolate_caramel_apple_as_carachoco(self):
        score, _ = self.score("carachoco", "Chocolate Caramel Candy Apple!")
        self.assertLess(score, 0)

    def test_rejects_other_anise_brand_as_pictolin(self):
        score, _ = self.score(
            "pictolinAnisSA",
            "Les Anis de Flavigny - anise candies"
        )
        self.assertLess(score, 0)

    def test_rejects_toffee_bottle(self):
        score, _ = self.score("toffeeNata", "Bouteille de toffee au lait")
        self.assertLess(score, 0)

    def test_rejects_unspecified_coffee_treats_as_sugar_free(self):
        score, _ = self.score("cafeDrySA", "Treats for a very lucky little girl")
        self.assertLess(score, 0)

    def test_rejects_shop_scene_as_coffee_sweets(self):
        score, _ = self.score(
            "cafeDryCA",
            '"Sweets - coffee - snacks" in Arahova, Greece - panoramio'
        )
        self.assertLess(score, 0)

    def test_rejects_peanuts_without_dark_chocolate_evidence(self):
        score, _ = self.score(
            "cacahueteChocolateNegro",
            "Chocolate Covered Raisins And Peanuts"
        )
        self.assertLess(score, 0)

    def test_rejects_generic_trail_mix_as_chocolate_coated_pipas(self):
        score, _ = self.score(
            "mixChocolatesPipa",
            "Trail Mix Mountain Man dark chocolate chips dried cranberries almonds cashews sunflower seeds"
        )
        self.assertLess(score, 0)

    def test_rejects_unrelated_toffee_brand_as_toffino(self):
        score, _ = self.score(
            "toffinoChocolate",
            "Three Russell Stover Toffees covered in milk chocolate"
        )
        self.assertLess(score, 0)

    def test_rejects_farmers_market_context(self):
        score, _ = self.score(
            "cacahueteTostadoRepeladoSinSal",
            "North Charleston Farmers Market unsalted roasted peanuts"
        )
        self.assertLess(score, 0)

    def test_accepts_core_food_when_visual_variant_metadata_is_missing(self):
        score, reasons = self.score(
            "almendraFritaSinSal",
            "Almonds close-up"
        )
        self.assertGreaterEqual(score, 4)
        self.assertIn("variant_metadata_unverified", reasons)

    def test_accepts_macadamia_without_salt_metadata_for_visual_review(self):
        score, reasons = self.score(
            "macadamiaFritaSinSal",
            "Macadamia nuts"
        )
        self.assertGreaterEqual(score, 4)
        self.assertIn("variant_metadata_unverified", reasons)

    def test_rejects_space_food_as_special_mixed_nuts(self):
        score, _ = self.score("revueloEspecial", "Comida espacial.jpg")
        self.assertLess(score, 0)

    def test_rejects_bean_stew_as_sweet_nut_mix(self):
        score, _ = self.score(
            "revueloDulceMCarmen",
            "Guiso de porotos con chorizo y vegetales en olla"
        )
        self.assertLess(score, 0)

    def test_rejects_trail_mix_granola_bar_as_loose_nut_mix(self):
        score, _ = self.score(
            "revueloDeliciasVirginia",
            "A Fruit and Nut flavor Nature Valley Trail Mix Chewy Granola Bar"
        )
        self.assertLess(score, 0)

    def test_rejects_bitter_melon_as_dehydrated_melon(self):
        score, _ = self.score("melonDeshidratado", "Dried bitter melon slices")
        self.assertLess(score, 0)

    def test_rejects_rice_pudding_as_chocolate_walnuts(self):
        score, _ = self.score(
            "chocolateNuezLeche",
            "Arroz con Leche y Chocolate"
        )
        self.assertLess(score, 0)

    def test_rejects_generic_chocolate_bar_as_dark_chocolate_hazelnuts(self):
        score, _ = self.score("chocolateAvellanaNegro", "Fami suklaapatukka")
        self.assertLess(score, 0)

    def test_rejects_salted_in_shell_peanuts_for_shelled_unsalted_product(self):
        score, _ = self.score(
            "cacahueteTostadoRepeladoSinSal",
            "Cacahuetes del Collaret tostado con cáscara y sal"
        )
        self.assertLess(score, 0)

    def test_accepts_mixed_nuts_identity_without_specific_blend_claim(self):
        score, reasons = self.score("revueloEspecial", "Mixed nuts assortment")
        self.assertGreaterEqual(score, 4)
        self.assertIn("product_identity_in_title_or_tags", reasons)

    def test_accepts_only_explicit_taco_miel_candy_evidence(self):
        score, reasons = self.score("tacoMiel", "Honey candy confection")
        self.assertGreater(score, 0)
        self.assertIn("strict_variant_evidence", reasons)

    def test_accepts_exact_pictolin_anise_sugar_free_metadata(self):
        score, _ = self.score(
            "pictolinAnisSA",
            "Pictolin anis sugar-free candy"
        )
        self.assertGreater(score, 0)

    def test_accepts_almonds_fried_in_sunflower_oil(self):
        score, _ = self.score(
            "almendraFritaGirasol",
            "Fried almonds in sunflower oil"
        )
        self.assertGreater(score, 0)


if __name__ == "__main__":
    unittest.main()
