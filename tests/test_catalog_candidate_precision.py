"""Precision regression tests for the product-specific image candidate scorer.

The scoring function and its declarative dictionaries are extracted from the
production script's AST so tests do not need network access, requests or Pillow.
"""
import ast
import re
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "catalog_candidate_batch.py"
TREE = ast.parse(SCRIPT.read_text(encoding="utf-8"))

NEEDED = {
    "CORE_TERMS",
    "PRODUCT_SEARCH",
    "SEARCH_RECOVERY_TERMS",
    "build_queries",
    "MATCH_GROUPS",
    "STRICT_MATCH_GROUPS",
    "STRICT_FORBIDDEN_TERMS",
    "PRODUCT_IDENTITY_GROUPS",
    "PRODUCT_FORBIDDEN_TERMS",
    "NEGATIVE_PHRASES",
    "NUT_PRODUCT_KEYS",
    "NUT_PRODUCT_NEGATIVE_TERMS",
    "NUT_PRODUCT_NEGATIVE_PHRASES",
    "BLEND_COMPOSITION_KEYS",
    "SOFT_VARIANT_KEYS",
    "candidate_score",
    "candidate_identity_is_confirmed",
    "candidate_variant_evidence_status",
    "candidate_rights_are_documented",
    "candidate_can_download",
    "candidate_identity_is_confirmed",
    "candidate_passes_gates",
    "approval_passes_gates",
}
selected = []
for node in TREE.body:
    if isinstance(node, ast.FunctionDef) and node.name in NEEDED:
        selected.append(node)
    elif isinstance(node, ast.Assign):
        names = {target.id for target in node.targets if isinstance(target, ast.Name)}
        if names & NEEDED:
            selected.append(node)

namespace = {"re": re}
module = ast.Module(body=selected, type_ignores=[])
exec(compile(module, str(SCRIPT), "exec"), namespace)
candidate_score = namespace["candidate_score"]


class TestCatalogCandidatePrecision(unittest.TestCase):
    def score(self, key, title, description=""):
        return candidate_score(key, {"title": title, "description": description, "tags": []})

    def test_exact_almond_oil_variant_is_required_before_download(self):
        gate = namespace["candidate_identity_is_confirmed"]
        self.assertTrue(gate("almendraFritaGirasol", {
            "title": "Fried almonds in sunflower oil",
            "tags": ["almonds", "fried", "sunflower oil"],
        }))
        unspecified = {"title": "Almonds close-up", "tags": ["almonds"]}
        self.assertTrue(gate("almendraFritaGirasol", unspecified))
        self.assertEqual(namespace["candidate_variant_evidence_status"]("almendraFritaGirasol", unspecified), "VARIANT_UNSPECIFIED")

    def test_exact_salted_macadamia_variant_is_required_before_download(self):
        gate = namespace["candidate_identity_is_confirmed"]
        self.assertTrue(gate("macadamiaFritaSal", {
            "title": "Salted fried macadamia nuts",
            "tags": ["macadamia", "fried", "salted"],
        }))
        conflicting = {"title": "Unsalted macadamia kernels", "tags": ["macadamia", "unsalted"]}
        self.assertTrue(gate("macadamiaFritaSal", conflicting))
        self.assertEqual(namespace["candidate_variant_evidence_status"]("macadamiaFritaSal", conflicting), "CONTRADICTORY_VARIANT")


    def test_pre_download_gate_requires_exact_variant_and_documented_commercial_rights(self):
        gate = namespace["candidate_can_download"]
        base = {
            "title": "Unsalted fried macadamia nuts",
            "tags": ["macadamia", "unsalted", "fried"],
            "license": "CC BY-SA 4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "artist": "Photographer Name",
            "source_page": "https://commons.wikimedia.org/wiki/File:Example.jpg",
        }
        self.assertTrue(gate("macadamiaFritaSinSal", base))
        missing_variant = dict(base, title="Macadamia nuts", tags=["macadamia"])
        self.assertFalse(gate("macadamiaFritaSinSal", missing_variant))
        missing_creator = dict(base, artist="")
        self.assertFalse(gate("macadamiaFritaSinSal", missing_creator))
        noncommercial = dict(base, license="CC BY-NC 4.0")
        self.assertFalse(gate("macadamiaFritaSinSal", noncommercial))
        mixed_blend = {
            "title": "Mixed nuts assortment",
            "tags": ["mixed nuts", "assortment"],
            "description": "Walnuts, almonds, peanuts and macadamia",
            "license": "CC BY-SA 4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "artist": "Photographer Name",
            "source_page": "https://commons.wikimedia.org/wiki/File:Example.jpg",
        }
        self.assertFalse(gate("revueloPacoJose", mixed_blend))

    def test_core_identity_dictionary_has_no_duplicate_keys(self):
        assignment = next(
            node for node in TREE.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "CORE_TERMS"
                    for target in node.targets)
        )
        keys = [key.value for key in assignment.value.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)]
        self.assertEqual(len(keys), len(set(keys)))

    def test_recovery_queries_start_with_broad_almond_terms(self):
        from_main = namespace["build_queries"]("almendraFritaSinSal", "Almendra frita sin sal")
        self.assertIn("almonds", from_main)
        self.assertIn("almond kernels", from_main)
        self.assertIn("fried almonds no salt", from_main)

    def test_recovery_queries_cover_shelled_peanuts(self):
        queries = namespace["build_queries"](
            "cacahueteTostadoRepeladoSinSal",
            "Cacahuete tostado repelado sin sal"
        )
        self.assertIn("roasted peanuts", queries)
        self.assertIn("shelled peanuts", queries)
        self.assertLessEqual(len(queries), 6)

    def test_recovery_queries_cover_macadamia_kernel_synonyms(self):
        queries = namespace["build_queries"](
            "macadamiaFritaSinSal",
            "Macadamia frita sin sal"
        )
        self.assertIn("macadamia nuts", queries)
        self.assertIn("macadamia kernels", queries)

    def test_recovery_dictionary_has_no_duplicate_product_keys(self):
        assignment = next(
            node for node in TREE.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name)
                    and target.id == "SEARCH_RECOVERY_TERMS"
                    for target in node.targets)
        )
        keys = [key.value for key in assignment.value.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)]
        self.assertEqual(len(keys), len(set(keys)))

    def test_salted_macadamia_recovery_terms_are_merged(self):
        queries = namespace["build_queries"](
            "macadamiaFritaSal",
            "Macadamia frita con sal"
        )
        self.assertIn("macadamia kernels", queries)
        self.assertIn("salted fried macadamia nuts", queries)
        self.assertIn("fried salted macadamia kernels", queries)
        self.assertIn("macadamia nuts with salt", queries)

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

    def test_identity_and_variant_evidence_are_separate(self):
        candidate = {"title": "Macadamia nuts", "tags": []}
        self.assertTrue(namespace["candidate_identity_is_confirmed"]("macadamiaFritaSinSal", candidate))
        self.assertEqual(namespace["candidate_variant_evidence_status"]("macadamiaFritaSinSal", candidate), "VARIANT_UNSPECIFIED")

    def test_explicit_salted_variant_conflicts_with_unsalted_target(self):
        candidate = {"title": "Salted macadamia nuts", "tags": []}
        self.assertTrue(namespace["candidate_identity_is_confirmed"]("macadamiaFritaSinSal", candidate))
        self.assertEqual(namespace["candidate_variant_evidence_status"]("macadamiaFritaSinSal", candidate), "CONTRADICTORY_VARIANT")

    def test_exact_variant_metadata_is_marked_exact(self):
        candidate = {"title": "Unsalted fried macadamia nuts", "tags": []}
        self.assertEqual(namespace["candidate_variant_evidence_status"]("macadamiaFritaSinSal", candidate), "EXACT_VARIANT_EVIDENCE")

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
        self.assertIn("blend_composition_unverified", reasons)

    def test_rejects_pastry_as_caramelized_walnuts(self):
        score, _ = self.score(
            "nuezCaramelizada",
            "Roasted walnut and honey caramel pain au chocolat"
        )
        self.assertLess(score, 0)

    def test_rejects_product_word_only_in_description(self):
        score, _ = self.score(
            "chocolateNuezLeche",
            "Dessert plate",
            "Walnuts and milk chocolate"
        )
        self.assertLess(score, 0)

    def test_rejects_unsalted_macadamia_for_salted_product(self):
        score, _ = self.score("macadamiaFritaSal", "Unsalted macadamia nuts")
        self.assertLess(score, 0)

    def test_sweet_mix_requires_sweet_mix_identity(self):
        score, _ = self.score(
            "revueloDulceMCarmen",
            "Guiso de porotos con chorizo y vegetales"
        )
        self.assertLess(score, 0)

    def test_rejects_salt_roasted_peanut_for_unsalted_product(self):
        score, reasons = self.score(
            "cacahueteTostadoRepeladoSinSal",
            "Salt Roasted Peanut"
        )
        self.assertLess(score, 0)
        self.assertTrue(any("wrong_product_or_preparation" in x for x in reasons))

    def test_accepts_roasted_peanuts_when_salt_is_not_documented(self):
        score, reasons = self.score(
            "cacahueteTostadoRepeladoSinSal",
            "Roasted peanuts"
        )
        self.assertGreaterEqual(score, 4)
        self.assertIn("variant_metadata_unverified", reasons)

    def test_rejects_trail_mix_for_three_variety_raisins(self):
        score, _ = self.score(
            "revueloTresPasas",
            "Cranberry trail mix with peanuts, raisins, walnuts and almonds"
        )
        self.assertLess(score, 0)

    def test_accepts_explicit_three_variety_raisins(self):
        score, reasons = self.score(
            "revueloTresPasas",
            "Three varieties of raisins mix"
        )
        self.assertGreaterEqual(score, 4)
        self.assertIn("variant_keyword_match", reasons)

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


    def test_rejects_spiced_rosemary_cashews_for_unsalted_fried_cashews(self):
        score, reasons = self.score(
            "anacardoFritoSinSal",
            "Roasted and spiced cashews with olive-rosemary flavour"
        )
        self.assertLess(score, 0)
        self.assertTrue(any("wrong_product_or_preparation" in x for x in reasons))


    def test_pilot_identity_gate_separates_product_from_variant(self):
        gate = namespace["candidate_identity_is_confirmed"]
        variant = namespace["candidate_variant_evidence_status"]
        truffles = {"title": "Raw Vegan Coconut Almond Truffles (7669980264).jpg"}
        self.assertTrue(gate("almendraCrudaPiel", truffles))
        self.assertEqual(variant("almendraCrudaPiel", truffles), "CONTRADICTORY_VARIANT")
        self.assertLess(self.score("almendraCrudaPiel", "Raw Vegan Coconut Almond Truffles (7669980264).jpg")[0], 0)
        almond_milk = {"title": "Raw almond milk.jpg"}
        self.assertTrue(gate("almendraCrudaPiel", almond_milk))
        self.assertEqual(variant("almendraCrudaPiel", almond_milk), "CONTRADICTORY_VARIANT")
        self.assertTrue(gate("almendraCrudaPiel", {
            "title": "Raw almonds with skin"
        }))
        fried_almonds = {"title": "Almendras fritas.jpg"}
        self.assertTrue(gate("almendraFritaOliva", fried_almonds))
        self.assertEqual(variant("almendraFritaOliva", fried_almonds), "VARIANT_UNSPECIFIED")
        self.assertTrue(gate("almendraFritaOliva", {"title": "Fried almonds in olive oil"}))
        almond = {"title": "Almond with two kernels.jpg"}
        self.assertTrue(gate("almendraFritaSinSal", almond))
        self.assertEqual(variant("almendraFritaSinSal", almond), "VARIANT_UNSPECIFIED")
        self.assertTrue(gate("almendraFritaSinSal", {"title": "Unsalted fried almonds"}))

    def test_candidate_requires_identity_and_technical_validation(self):
        gate = namespace["candidate_passes_gates"]
        self.assertTrue(gate(True, True))
        self.assertFalse(gate(False, True))
        self.assertFalse(gate(True, False))
        self.assertFalse(gate(False, False))

    def test_final_approval_requires_complete_rights_and_visual_review(self):
        gate = namespace["approval_passes_gates"]
        complete = ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0",
                    "Creator Name", "https://commons.wikimedia.org/wiki/File:Example.jpg")
        self.assertTrue(gate(True, *complete, True))
        self.assertFalse(gate(True, *complete, False))
        self.assertFalse(gate(True, complete[0], "", complete[2], complete[3], True))
        self.assertFalse(gate(False, *complete, True))

    def test_accepts_almonds_fried_in_sunflower_oil(self):
        score, _ = self.score(
            "almendraFritaGirasol",
            "Fried almonds in sunflower oil"
        )
        self.assertGreater(score, 0)


if __name__ == "__main__":
    unittest.main()

    def test_rejects_branded_product_packaging(self):
        score, reasons = self.score(
            "almendraFritaGirasol",
            "Almonds in branded retail pouch with product label"
        )
        self.assertLess(score, 0)
        self.assertTrue(any("irrelevant_or_commercial_context" in reason for reason in reasons))

    def test_rejects_packaged_nuts_in_spanish(self):
        score, reasons = self.score(
            "almendraFritaSinSal",
            "Almendras fritas sin sal en bolsa con etiqueta y logotipo"
        )
        self.assertLess(score, 0)
        self.assertTrue(any("irrelevant_or_commercial_context" in reason for reason in reasons))

    def test_accepts_clean_unbranded_product_photo(self):
        score, reasons = self.score(
            "almendraFritaSinSal",
            "Unsalted fried almonds isolated on clean white background"
        )
        self.assertGreaterEqual(score, 4)
        self.assertIn("product_identity_in_title_or_tags", reasons)
