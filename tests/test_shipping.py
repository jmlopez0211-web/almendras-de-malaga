import re
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "js" / "app.js"
HTML = Path(__file__).resolve().parents[1] / "index.html"

class ShippingTests(unittest.TestCase):
    def test_weight_thresholds_and_over_20kg_tier(self):
        source = APP.read_text(encoding="utf-8")
        for grams in (100, 250, 500, 1000, 5000, 10000, 20000):
            self.assertRegex(source, rf"maxGrams\s*:\s*{grams}\b")
        self.assertIn('label:"Más de 20 kg"', source)

    def test_rates_are_editable_and_marked_provisional(self):
        source = APP.read_text(encoding="utf-8")
        self.assertIn("Importes provisionales", source)
        self.assertIn("modifica únicamente los valores price", source)
        self.assertEqual(len(re.findall(r"price\s*:\s*\d+\.\d+", source[:source.index("const products")])), 8)

    def test_zero_weight_has_no_shipping_charge(self):
        source = APP.read_text(encoding="utf-8")
        self.assertIn('if(grams===0)return {maxGrams:0,label:"Sin productos",price:0}', source)

    def test_cart_breakdown_displays_weight_subtotal_shipping_and_total(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertIn("Envío · tramo de peso aplicado", html)
        for selector in ('id="cartWeight"', 'id="cartSubtotal"', 'id="cartShipping"', 'id="cartTotal"'):
            self.assertIn(selector, html)

    def test_whatsapp_uses_primary_phone_and_includes_shipping_breakdown(self):
        source = APP.read_text(encoding="utf-8")
        for required in ("wa.me/34666068765", "🚚 *ENVÍO:*", "🧾 *SUBTOTAL PRODUCTOS:*", "💰 *TOTAL FINAL:*", "encodeURIComponent(message)"):
            self.assertIn(required, source)

    def test_no_dni_or_cif_fields_added(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertNotRegex(html, r"(?i)\b(DNI|CIF|NIF)\b")

if __name__ == "__main__":
    unittest.main()
