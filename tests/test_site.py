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

    def test_catalog_dynamic_content_is_escaped(self):
        app = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("const escapeHTML=", app)
        self.assertIn("escapeHTML(p.name)", app)
        self.assertIn("renderProductImageCredit", app)

    def test_modal_focus_management_exists(self):
        app = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("modalFocusSelector", app)
        self.assertIn("if(e.key==='Tab'&&opened)", app)
        self.assertIn('aria-hidden="true"', html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
