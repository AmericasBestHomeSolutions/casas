"""An excluded id stays out even if a later sync writes it back into homes.js.

portal_sync.py (homes repo) and build_casas.py both call excluded_homes.apply
after they write the catalog. This test inserts an excluded id and checks that
apply removes it again.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import excluded_homes  # noqa: E402

CATALOG = """
const HOMES = [
  {
    id: "springfield-il-2949-foxbridge",
    status: "Available",
  },
  {
    id: "duquoin-il-322-cole",
    status: "Available",
  },
];
const SOLD_CARDS = [];
"""


class ExcludedStaysOut(unittest.TestCase):
    def test_apply_removes_id_twice(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "data").mkdir()
            (root / "data" / "excluded-homes.json").write_text(json.dumps([
                {"id": "duquoin-il-322-cole", "reason": "test", "added": "2026-11-25"}
            ]), encoding="utf-8")
            (root / "como-funciona.html").write_text("<html></html>", encoding="utf-8")
            js = root / "homes.js"
            js.write_text(CATALOG, encoding="utf-8")
            (root / "sitemap.xml").write_text(
                "<urlset><url><loc>https://casasconfinanciamiento.com/duquoin-il-322-cole.html</loc></url></urlset>\n",
                encoding="utf-8")
            removed = excluded_homes.apply(root, "es")
            self.assertIn("duquoin-il-322-cole", removed)
            self.assertNotIn("duquoin-il-322-cole", js.read_text(encoding="utf-8"))
            self.assertNotIn("duquoin-il-322-cole", (root / "sitemap.xml").read_text(encoding="utf-8"))
            page = (root / "duquoin-il-322-cole.html").read_text(encoding="utf-8")
            self.assertIn('http-equiv="refresh"', page)
            # A later sync pastes the id back. The next apply takes it out again.
            js.write_text(CATALOG, encoding="utf-8")
            removed_again = excluded_homes.apply(root, "es")
            self.assertIn("duquoin-il-322-cole", removed_again)
            self.assertNotIn('id: "duquoin-il-322-cole"', js.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
