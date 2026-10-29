"""Checks for the buyer-copy sanitizer in build_casas.py.

Run from the repo root:  python3 scripts/test_copy_sanitizer.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_casas as build

ROOT = Path(__file__).resolve().parents[1]


class SanitizerTests(unittest.TestCase):
    def test_keeps_the_words_around_the_invitation(self):
        src = (
            "Las casas a este pago no permanecen disponibles por mucho tiempo. "
            "Envíenos un texto o un mensaje ahora y pongámoslo en la agenda de visitantes."
        )
        got, n = build.sanitize_prose(src)
        self.assertEqual(n, 1)
        self.assertEqual(
            got,
            "Las casas a este pago no permanecen disponibles por mucho tiempo. "
            "Agende una visita ahora y pongámoslo en la agenda de visitantes.",
        )

    def test_mid_sentence_invitation_stays_lowercase(self):
        src = (
            "Las casas a este precio no esperan, así que mándenos un texto ahora "
            "y agendemos su cita."
        )
        got, n = build.sanitize_prose(src)
        self.assertEqual(n, 1)
        self.assertEqual(
            got,
            "Las casas a este precio no esperan, así que agende una visita ahora "
            "y agendemos su cita.",
        )

    def test_longest_phrase_wins(self):
        got, n = build.sanitize_prose(
            "Mándenos un mensaje de texto o un mensaje ahora y reserve su cita."
        )
        self.assertEqual(n, 1)
        self.assertEqual(got, "Agende una visita ahora y reserve su cita.")

        got, n = build.sanitize_prose("Llámenos o envíenos un texto hoy.")
        self.assertEqual(n, 1)
        self.assertEqual(got, "Agende una visita hoy.")

    def test_short_invitations(self):
        got, n = build.sanitize_prose("Escríbanos y coordinamos la hora.")
        self.assertEqual(got, "Agende una visita y coordinamos la hora.")
        self.assertEqual(n, 1)
        got, n = build.sanitize_prose("Si quiere verla, llámenos.")
        self.assertEqual(got, "Si quiere verla, agende una visita.")
        self.assertEqual(n, 1)

    def test_does_not_touch_ordinary_call_wording_or_consent(self):
        src = (
            "Venga a recorrerla y hacerla para llamar suya. "
            "No se preocupe por cualquier número que le mande el casero. "
            "Acepto recibir mensajes de texto de Americas Best Home Solutions LLC."
        )
        got, n = build.sanitize_prose(src)
        self.assertEqual(n, 0)
        self.assertEqual(got, src)

    def test_text_only_phone_line(self):
        src = "Lista para ver. Contacto solo por TEXTO: 757-714-3268"
        got, n = build.sanitize_prose(src)
        self.assertEqual(n, 1)
        self.assertEqual(got, "Lista para ver. Agende una visita")
        self.assertNotIn("757", got)

    def test_english_phrases_keep_the_clause(self):
        src = "Send us a text or a message now and let's get you on the showing schedule."
        got, n = build.sanitize_prose(src, "en")
        self.assertEqual(n, 1)
        self.assertEqual(
            got,
            "Book a Tour now and let's get you on the showing schedule.",
        )
        got, n = build.sanitize_prose(
            "Homes at this price don't wait, so call or text us today.",
            "en",
        )
        self.assertEqual(got, "Homes at this price don't wait, so book a Tour today.")

    def test_homes_js_fields_only(self):
        src = (
            'copy:        "Envíenos un texto ahora y reserve una cita.",\n'
            '    description: "Los cables ya no están. Llámenos.",\n'
            '    termText:       "Financiamiento del dueño a 30 años",\n'
        )
        got, fields, phrases = build.sanitize_homes_js(src)
        self.assertEqual(fields, 2)
        self.assertEqual(phrases, 2)
        self.assertIn("Agende una visita ahora y reserve una cita.", got)
        self.assertIn("Los cables ya no están. Agende una visita.", got)
        self.assertIn("Financiamiento del dueño a 30 años", got)

    def test_meta_descriptions(self):
        html = (
            '<meta name="description" content="Envíenos un texto ahora."/>'
            '<meta property="og:description" content="Solo el precio. Sin invitación."/>'
            '<meta name="twitter:description" content="Llámenos o escríbanos hoy."/>'
            "<p>Envíenos un texto ahora.</p>"
        )
        got, n = build.sanitize_meta_html(html)
        self.assertEqual(n, 2)
        self.assertIn('content="Agende una visita ahora."', got)
        self.assertIn('content="Agende una visita hoy."', got)
        self.assertIn("<p>Envíenos un texto ahora.</p>", got)


if __name__ == "__main__":
    unittest.main()
