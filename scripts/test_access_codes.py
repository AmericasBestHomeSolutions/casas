#!/usr/bin/env python3
"""Guard tests. Placeholder number is 0000. These strings are assembled so the
test file itself does not contain an access instruction the guard would flag."""

from __future__ import annotations

import contextlib
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from check_access_codes import (
    find_violations,
    main,
    scan_tree,
    strip_access_instructions,
)

PLACEHOLDER = "0000"
PHONE = "000-000-0000"
LOCKBOX = "Lock" + "box"
LOCK_BOX = "Lock" + " box"
CAJA = "caja de " + "seguridad"
CODE_WORD = "Co" + "de"
CODIGO = "Códi" + "go"


def lockbox_code_is(number: str = PLACEHOLDER) -> str:
    return f"{LOCKBOX} code is {number}"


def spanish_code_is(number: str = PLACEHOLDER) -> str:
    return f"El código de la {CAJA} es {number}"


def spanish_code_short(number: str = PLACEHOLDER) -> str:
    return f"Código de {CAJA} {number}"


class StripTests(unittest.TestCase):
    def test_negation_without_a_number_stays(self) -> None:
        english = "There is no basement. There is no lockbox. The back door is unsecured"
        spanish = "No tiene sótano. No tiene caja de seguridad. La puerta trasera no está asegurada."
        self.assertEqual(strip_access_instructions(english), english)
        self.assertEqual(strip_access_instructions(spanish), spanish)
        self.assertEqual(find_violations(english), [])
        self.assertEqual(find_violations(spanish), [])

    def test_trailing_clause_with_emoji(self) -> None:
        emoji = "".join(chr(cp) for cp in (0x1F510,))
        original = f"Photos are linked. {emoji}{lockbox_code_is()}"
        self.assertIn("lock-emoji", find_violations(original))
        self.assertIn("lockbox", find_violations(original))
        self.assertEqual(strip_access_instructions(original), "Photos are linked.")
        self.assertNotIn(PLACEHOLDER, strip_access_instructions(original))

    def test_spanish_trailing_clauses(self) -> None:
        emoji = "".join(chr(cp) for cp in (0x1F510,))
        with_is = f"Fotos. {emoji} {spanish_code_is()}"
        short = f"Fotos. {emoji} {spanish_code_short()}"
        self.assertEqual(strip_access_instructions(with_is), "Fotos.")
        self.assertEqual(strip_access_instructions(short), "Fotos.")

    def test_label_and_phone_in_the_same_clause(self) -> None:
        original = f"Tax=116.00 a month {LOCKBOX}: {PLACEHOLDER} Phone Number: {PHONE}"
        spanish = f"Impuesto=$116.00 al mes {CAJA.capitalize()}: {PLACEHOLDER} Número de teléfono: {PHONE}"
        self.assertEqual(strip_access_instructions(original), "Tax=116.00 a month")
        self.assertEqual(strip_access_instructions(spanish), "Impuesto=$116.00 al mes")
        self.assertNotIn(PHONE, strip_access_instructions(original))

    def test_mid_sentence_clause_keeps_the_condition(self) -> None:
        original = f"Boarded up, {LOCKBOX.lower()} {PLACEHOLDER} access at door. City notes remain."
        spanish = f"Tapiada, {CAJA} {PLACEHOLDER} acceso en la puerta. La ciudad sigue."
        self.assertEqual(
            strip_access_instructions(original),
            "Boarded up. City notes remain.",
        )
        self.assertEqual(
            strip_access_instructions(spanish),
            "Tapiada. La ciudad sigue.",
        )

    def test_leftover_access_sentence(self) -> None:
        self.assertEqual(
            strip_access_instructions("access at door. City notes remain."),
            "City notes remain.",
        )
        self.assertEqual(
            strip_access_instructions("acceso por la puerta. La ciudad sigue."),
            "La ciudad sigue.",
        )
        self.assertIn("access-at-door", find_violations("access at door. City notes remain."))

    def test_bare_code_sentence(self) -> None:
        original = f"Detached garage. {CODE_WORD} {PLACEHOLDER}. Wires cut throughout basement"
        spanish = f"Garaje independiente. {CODIGO} {PLACEHOLDER}. Cables cortados en todo el sótano"
        self.assertEqual(
            strip_access_instructions(original),
            "Detached garage. Wires cut throughout basement",
        )
        self.assertEqual(
            strip_access_instructions(spanish),
            "Garaje independiente. Cables cortados en todo el sótano",
        )
        self.assertIn("bare-code-sentence", find_violations(original))

    def test_other_phrases_and_ordinary_numbers(self) -> None:
        gate = "Gate" + f" code {PLACEHOLDER}."
        combo = "Combination" + f" is {PLACEHOLDER}."
        self.assertEqual(find_violations(gate), ["access-phrase"])
        self.assertEqual(strip_access_instructions(gate), "")
        self.assertEqual(strip_access_instructions("Shed. " + combo), "Shed.")
        kept = "Parcel #: 00-00-00-000-000. The house is 1344 sqft. Zip code 00000."
        self.assertEqual(strip_access_instructions(kept), kept)
        self.assertEqual(find_violations(kept), [])

    def test_spaced_lock_word(self) -> None:
        original = f"{LOCK_BOX}: {PLACEHOLDER}."
        self.assertEqual(strip_access_instructions("Vacant. " + original), "Vacant.")


class ScannerTests(unittest.TestCase):
    def test_synthetic_file_fails_and_repo_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "listing.json"
            sample.write_text(
                '{"en": "Nice house. ' + lockbox_code_is() + '"}',
                encoding="utf-8",
            )
            hits = scan_tree(Path(tmp))
            self.assertEqual([rel for rel, _line, _kind in hits], ["listing.json", "listing.json"])
            self.assertEqual([kind for _rel, _line, kind in hits], ["lockbox", "access-phrase"])
            buf = StringIO()
            with contextlib.redirect_stdout(buf):
                status = main([tmp])
            self.assertEqual(status, 1)
            self.assertNotIn(PLACEHOLDER, buf.getvalue())

        repo = Path(__file__).resolve().parents[1]
        self.assertEqual(scan_tree(repo), [])
        self.assertEqual(main([str(repo)]), 0)

    def test_failure_output_has_no_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "note.txt"
            sample.write_text("See " + lockbox_code_is(), encoding="utf-8")
            buf = StringIO()
            with contextlib.redirect_stdout(buf):
                status = main([tmp])
            output = buf.getvalue()
            self.assertEqual(status, 1)
            self.assertIn("note.txt", output)
            self.assertIn("lockbox", output)
            self.assertNotIn(PLACEHOLDER, output)
            self.assertNotIn(LOCKBOX, output)


if __name__ == "__main__":
    unittest.main()
