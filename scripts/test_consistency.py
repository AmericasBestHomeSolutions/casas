"""python3 scripts/test_consistency.py"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_consistency as cc  # noqa: E402

HOMES = """
const HOMES = [
  {
    id: "springfield-il-2949-foxbridge",
    lockedPrice: 89000,
    moveIn: 3000,
    monthlyPayment: 892,
    status: "Available",
  },
];
const SOLD_CARDS = [];
"""


def tree(root: Path, price=89000, facts=None):
    text = HOMES.replace("89000", str(price))
    (root / "homes.js").write_text(text, encoding="utf-8")
    data = root / "data"
    data.mkdir()
    (data / "home-facts.json").write_text(json.dumps(facts or {"version": 1, "homes": {}}), encoding="utf-8")


class Consistency(unittest.TestCase):
    def test_match(self):
        with tempfile.TemporaryDirectory() as d:
            homes, casas = Path(d) / "homes", Path(d) / "casas"
            homes.mkdir(); casas.mkdir()
            tree(homes)
            tree(casas)
            self.assertEqual(cc.check(homes, casas), [])

    def test_price_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as d:
            homes, casas = Path(d) / "homes", Path(d) / "casas"
            homes.mkdir(); casas.mkdir()
            tree(homes, price=89000)
            tree(casas, price=1)
            errors = cc.check(homes, casas)
            self.assertTrue(any("lockedPrice" in e for e in errors))

    def test_facts_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as d:
            homes, casas = Path(d) / "homes", Path(d) / "casas"
            homes.mkdir(); casas.mkdir()
            tree(homes, facts={"version": 1, "homes": {}})
            tree(casas, facts={"version": 1, "homes": {"x": {}}})
            errors = cc.check(homes, casas)
            self.assertTrue(any("home-facts" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
