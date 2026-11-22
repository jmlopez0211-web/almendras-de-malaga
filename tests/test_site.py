"""Static regression tests for the Almendras de Málaga storefront."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = "34666068765"
SECONDARY = "34744602855"
LANDING_PAGES = (
    "almendras-garrapinadas-malaga.html",
    "almendras-fritas-aove-malaga.html",
    "frutos-secos-centro-malaga.html",
    "frutos-secos-profesionales-malaga.html",
    "visitar-almendras-catedral-malaga.html",
)


def read_catalog():
    source = (ROOT / "data" / "catalog.js").read_text(encoding="utf-8")
    match = re.search(r"window\.PRODUCTS\s*=\s*(\{.*\})\s*;?\s*$", source, re.S)
    if not match:
        raise AssertionError("Could not extract window.PRODUCTS JSON object")
    return json.loads(match.group(1))


class StorefrontReleaseTests(unittest.TestCase):
    def test_release_validator_passes(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_site.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_catalog_has_expected_151_items(self):
        self.assertEqual(len(read_catalog()), 151)

    def test_every_landing_page_uses_primary_whatsapp_and_retains_secondary_phone(self):
        for filename in LANDING_PAGES:
            with self.subTest(page=filename):
                html = (ROOT / filename).read_text(encoding="utf-8")
                self.assertIn("wa.me/" + PRIMARY, html)
                self.assertNotIn("wa.me/" + SECONDARY, html)
                self.assertIn("tel:+" + PRIMARY, html)
                self.assertIn("tel:+" + SECONDARY, html)

    def test_cart_sends_to_primary_number_and_limits_quantities(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="sendCartWhatsApp666"', html)
        self.assertIn("wa.me/" + PRIMARY, app)
        self.assertIn("found.quantity+quantity>50", app)
        self.assertIn("Number(x.quantity)<=50", app)

    def test_customer_notes_have_a_reasonable_length_limit(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="cartNotes" rows="3" maxlength="1000"', html)

    def test_cart_totals_and_order_message_are_explicitly_indicative(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("Total orientativo (productos + envío)", html)
        self.assertIn("TOTAL ORIENTATIVO", app)
        self.assertIn("no confirma pedido", app)
        self.assertNotIn("Una vez recibido el pago, prepararemos y enviaremos el pedido", app)
        self.assertNotIn("Una vez recibido el pago, se preparará y enviará el pedido", html)

    def test_catalog_dynamic_content_is_escaped(self):
        app = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("const escapeHTML=", app)
        self.assertIn("escapeHTML(p.name)", app)
        self.assertIn("renderProductImageCredit", app)
        self.assertIn("const hasProductId=", app)
        self.assertIn("image.addEventListener('error'", app)
        self.assertIn("remove.setAttribute('aria-label'", app)

    def test_modal_focus_management_exists(self):
        app = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("modalFocusSelector", app)
        self.assertIn("if(e.key==='Tab'&&opened)", app)
        self.assertIn('aria-hidden="true"', html)

    def test_shipping_tiers_are_editable_and_cover_all_weight_breakpoints(self):
        app = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
        match = re.search(r"const SHIPPING_TIERS = \[(.*?)\];", app, re.S)
        self.assertIsNotNone(match, "Shipping tier configuration missing")
        tiers = re.findall(r"maxGrams:(\d+|Infinity),label:\"([^\"]+)\",price:([0-9.]+)", match.group(1))
        self.assertEqual(len(tiers), 8)
        limits = [int(x[0]) if x[0] != "Infinity" else float("inf") for x in tiers]
        self.assertEqual(limits, [100, 250, 500, 1000, 5000, 10000, 20000, float("inf")])
        self.assertEqual([float(x[2]) for x in tiers], [2.5, 3.5, 4.5, 5.5, 7.5, 9.5, 12.5, 15.0])
        def tier_for(weight):
            return next(i for i,limit in enumerate(limits) if weight <= limit)
        self.assertEqual([tier_for(w) for w in [100,101,250,251,500,501,1000,1001,5000,5001,10000,10001,20000,20001]], [0,1,1,2,2,3,3,4,4,5,5,6,6,7])

    def test_cart_supports_large_pack_formats_and_shipping_summary(self):
        app = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        for grams in (5000, 10000, 20000):
            self.assertIn(str(grams), app)
            self.assertIn(f'value="{grams}"', html)
        for element_id in ("cartSubtotal", "cartWeight", "cartShipping", "cartTotal"):
            self.assertIn(f'id="{element_id}"', html)
        for phrase in ("getCartWeightGrams", "calculateShipping", "PESO TOTAL", "ENVÍO", "TOTAL ORIENTATIVO"):
            self.assertIn(phrase, app)
        self.assertIn("wa.me/" + PRIMARY, app)
        self.assertNotRegex(app, r"DNI|CIF")


if __name__ == "__main__":
    unittest.main(verbosity=2)
