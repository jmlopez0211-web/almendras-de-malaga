"""Static regression tests for the Almendras de Málaga storefront."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = "34678219755"
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
        config = (ROOT / "js" / "commercial-config.js").read_text(encoding="utf-8")
        data = json.loads((ROOT / "data" / "commercial.json").read_text(encoding="utf-8"))
        self.assertIn("DEFAULT_TIERS", config)
        self.assertIn("validateCommercialConfig", config)
        tiers = data["shipping"]["tiers"]
        self.assertEqual(len(tiers), 8)
        limits = [tier["maxGrams"] for tier in tiers]
        self.assertEqual(limits, [100, 250, 500, 1000, 5000, 10000, 20000, None])
        self.assertEqual([tier["price"] for tier in tiers], [2.5, 3.5, 4.5, 5.5, 7.5, 9.5, 12.5, 15])
        self.assertIn('almendras:commercial-config-updated', config)
        self.assertIn('almendras:shipping-updated', (ROOT / "js" / "app.js").read_text(encoding="utf-8"))


    def test_backend_requires_explicit_intent_before_cart_mutation(self):
        server = (ROOT / "server.js").read_text(encoding="utf-8")
        self.assertIn("explicitCartIntent", server)
        self.assertIn("Para modificar el carrito, el cliente debe solicitarlo expresamente", server)
        self.assertIn('AI_TOOLS.filter(tool=>tool.name!=="add_to_cart")', server)

    def test_chat_and_whatsapp_handoffs_have_mobile_safety_limits(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertIn('id="chatInput" type="text" maxlength="2000"', html)
        self.assertIn("AbortSignal.timeout(25000)", app)
        self.assertIn("message.length>3500", app)
        self.assertIn("width:min(360px,calc(100vw - 28px))", css)
        self.assertIn("height:min(500px,calc(100dvh - 190px))", css)

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
