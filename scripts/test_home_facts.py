"""Schema for data/home-facts.json and the static buyer blocks."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seo_pages as seo  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SYSTEMS = {"furnace", "plumbing", "electrical", "roof", "foundation"}
AS_IS = (
    "Todas las casas se venden tal como están, necesitan algo de trabajo y tienen el precio "
    "de acuerdo con eso. Las reparaciones corren por cuenta del comprador. Recorra la casa antes de firmar."
)


class HomeFacts(unittest.TestCase):
    def test_schema_and_reported_only(self):
        data = json.loads((ROOT / "data" / "home-facts.json").read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 1)
        self.assertIsInstance(data["homes"], dict)
        self.assertTrue(data["homes"])
        for hid, row in data["homes"].items():
            self.assertIn("condition", row)
            self.assertIn("fit", row)
            terms = row.get("terms") or {}
            for key in ("rate", "monthly_covers", "deed_transfer", "cash_before_keys"):
                self.assertNotIn(key, terms)
            for name, cond in row["condition"].items():
                self.assertIn(name, SYSTEMS)
                self.assertEqual(cond["status"], "reported")
                self.assertTrue(cond["en"].strip())
                self.assertTrue(cond["es"].strip())
                self.assertEqual(cond["source"], "listing note")
                self.assertNotIn("status", {"verified"})  # never seeded as verified
                self.assertNotEqual(cond["status"], "verified")

    def test_blocks_use_unknown_and_exact_as_is(self):
        home = {
            "id": "springfield-il-2949-foxbridge",
            "address": "2949 Foxbridge Rd",
            "city": "Springfield",
            "state": "IL",
            "beds": 3,
            "baths": 1,
            "sqft": "1100",
            "status": "Available",
            "monthlyPayment": 892,
            "moveIn": 3000,
            "lockedPrice": 89000,
            "termText": "Financiamiento del dueño a 30 años (contrato de compraventa)",
            "features": {"backyard": "yes", "garage": "yes"},
        }
        html = seo.buyer_eval_html(ROOT, home, "es")
        self.assertIn("Lo que paga antes de recibir las llaves", html)
        self.assertIn("Su mensualidad y los términos", html)
        self.assertIn("Condición: se vende tal como está", html)
        self.assertIn(AS_IS, html)
        self.assertIn("$3,000", html)
        self.assertIn("Los términos finales se confirman en sus documentos.", html)
        self.assertIn("derecho de cancelación de 3 días", html)
        self.assertIn("No necesita préstamo de banco", html)
        self.assertIn("una identificación válida", html)
        self.assertNotIn("declaraciones de impuestos", html)
        self.assertNotIn("talones de pago", html)
        self.assertNotIn("revisión de crédito", html)
        self.assertIn("Aún no se sabe", html)
        self.assertIn("Patio", html)
        self.assertIn("No son testimonios", html)
        self.assertNotIn("Tasa de interés", html)
        self.assertNotIn("Costos de cierre", html)
        self.assertNotIn("$0", html)
        self.assertNotIn("Lo reporta el vendedor", html)

    def test_reported_quote_is_spanish(self):
        home = {
            "id": "decatur-il-2132-church",
            "status": "Available",
            "monthlyPayment": 850,
            "moveIn": 2500,
            "lockedPrice": 70000,
            "termText": "Financiamiento del dueño a 30 años (contrato de compraventa)",
            "beds": 2,
            "baths": 1,
        }
        html = seo.buyer_eval_html(ROOT, home, "es")
        self.assertIn("Lo reporta el vendedor", html)
        self.assertIn("el horno necesita trabajo", html)
        self.assertIn("no tiene electricidad (se llevaron el cableado de cobre)", html)
        self.assertNotIn("Verified", html)


class Placeholders(unittest.TestCase):
    def test_hidden_without_preview(self):
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('class="joe-ph" hidden', index)
        self.assertIn("data-preview", index)
        self.assertIn("Joseph Hernandez", index)
        self.assertIn("Director Ejecutivo", index)
        self.assertIn("joe-headshot-600.webp", index)
        self.assertIn('loading="lazy"', index)
        self.assertNotIn("Gerente", index)
        self.assertIn("Logan, Decatur", index)
        # The reveal rule is gated on the preview attribute.
        css = (ROOT / "site.css").read_text(encoding="utf-8")
        self.assertIn('html[data-preview="1"] .joe-ph', css)
        self.assertIn(".joe-ph[hidden]", css)


if __name__ == "__main__":
    unittest.main()
