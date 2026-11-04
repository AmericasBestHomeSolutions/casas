"""python3 scripts/test_book_links.py"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import book_links as B


def homes_js(*homes):
    blocks = []
    for hid, addr, status in homes:
        blocks.append(f'''  {{
    id: "{hid}",
    address:     "{addr}",
    city:  "Decatur",
    state: "IL",
    status: "{status}",
    lockbox: "1234",
  }}''')
    return (
        "/* --- the homes (x live, y) --- */\nconst HOMES = [\n"
        + ",\n".join(blocks)
        + "\n];\nconst SOLD_CARDS = [\n  {id: \"sold-xx-1-gone\"}\n];\n"
    )


def redirect_crm_url(html: str) -> str:
    """First URL passed to new URL(...) in the redirect script (JSON string)."""
    m = re.search(r"new URL\(([^)]+)\)", html)
    assert m, "expected CRM redirect script"
    return json.loads(m.group(1))


class T(unittest.TestCase):
    def site(self, d, *homes, es=False):
        r = Path(d)
        (r / "data").mkdir(exist_ok=True)
        (r / "images").mkdir(exist_ok=True)
        (r / "homes.js").write_text(homes_js(*homes), encoding="utf-8")
        if es:
            (r / "como-funciona.html").write_text("x")
        return r

    def test_short_slug(self):
        self.assertEqual(B.short_slug("decatur-il-905-olive"), "905-olive")
        self.assertEqual(B.short_slug("eaststlouis-il-6000-old"), "6000-old")
        self.assertEqual(B.short_slug("nolocation"), "")

    def test_agendar_redirect_and_og_image(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.site(d, ("decatur-il-905-olive", "905 W. Olive St.", "Available"), es=True)
            (r / "images" / "decatur-il-905-olive.jpg").write_bytes(b"x")
            B.build(r)
            page = (r / "agendar" / "905-olive" / "index.html").read_text()
            self.assertIn("location.replace", page)
            self.assertNotIn("<iframe", page)
            self.assertNotIn("embed", page.lower())
            self.assertEqual(
                redirect_crm_url(page),
                "https://owner.getownerfinancedhomes.com/book?home=decatur-il-905-olive&lang=es",
            )
            self.assertIn('property="og:image" content="https://casasconfinanciamiento.com/images/decatur-il-905-olive.jpg"', page)
            self.assertIn('property="og:url" content="https://casasconfinanciamiento.com/agendar/905-olive"', page)
            self.assertIn("905 W. Olive St., Decatur, IL", page)
            self.assertNotIn("1234", page)

    def test_opinion_redirect_matches_main_behavior(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.site(d, ("decatur-il-905-olive", "905 W. Olive St.", "Available"), es=True)
            B.build(r)
            page = (r / "opinion" / "905-olive" / "index.html").read_text()
            self.assertIn("location.replace", page)
            self.assertNotIn("<iframe", page)
            self.assertEqual(
                redirect_crm_url(page),
                "https://owner.getownerfinancedhomes.com/feedback/decatur-il-905-olive?lang=es",
            )
            self.assertIn("location.search", page)

    def test_cuenta_redirect_whitelist_only_lang(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.site(d, ("decatur-il-905-olive", "905 W. Olive St.", "Available"), es=True)
            B.build(r)
            page = (r / "cuenta" / "index.html").read_text()
            self.assertIn("location.replace", page)
            self.assertNotIn("<iframe", page)
            self.assertEqual(redirect_crm_url(page), "https://owner.getownerfinancedhomes.com/account?lang=es")
            self.assertIn(json.dumps(list(B.ACCOUNT_KEEP)), page)
            self.assertNotIn("q.forEach", page)
            self.assertNotIn("next", page.lower())

    def test_book_href_fallback_to_crm_not_agendar_404(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.site(d, ("decatur-il-905-olive", "905 W. Olive St.", "Available"), es=True)
            B.build(r)
            js = (r / "book-links.js").read_text()
            self.assertIn('"/agendar/905-olive"', js)
            self.assertIn("BOOK_CRM", js)
            self.assertIn("function bookHref", js)
            self.assertIn(
                "return BOOK_CRM+'?home='+encodeURIComponent(homeId)+'&lang='+BOOK_LANG",
                js,
            )
            self.assertNotIn("'/agendar/'+encodeURIComponent", js)

    def test_collision_falls_back_to_full_id_and_slug_is_stable(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.site(d, ("decatur-il-905-olive", "905 Olive", "Available"),
                          ("peoria-il-905-olive", "905 Olive", "Available"))
            B.build(r, "en")
            self.assertFalse((r / "book" / "905-olive").exists())
            self.assertTrue((r / "book" / "decatur-il-905-olive" / "index.html").is_file())

    def test_pending_home_shows_note_instead_of_booking(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.site(d, ("granitecity-il-2539-28th", "2539 E. 28th St.", "Available"), es=True)
            B.build(r)
            (r / "homes.js").write_text(homes_js(("granitecity-il-2539-28th", "2539 E. 28th St.", "Pending")))
            B.build(r)
            for key in ("2539-28th", "granitecity-il-2539-28th"):
                page = (r / "agendar" / key / "index.html").read_text()
                self.assertIn("Esta casa está pendiente", page)
                self.assertIn("no se agendan visitas nuevas", page)
                self.assertNotIn("owner.getownerfinancedhomes.com", page)
                self.assertNotIn("location.replace", page)
            js = (r / "book-links.js").read_text()
            self.assertIn("granitecity-il-2539-28th", js)
            self.assertIn("BOOK_CLOSED", js)
            self.assertNotIn('"/agendar/2539-28th"', js)
            live = json.loads((r / "data" / "book-links.json").read_text())["live"]
            self.assertNotIn("granitecity-il-2539-28th", live)
            opinion = (r / "opinion" / "2539-28th" / "index.html").read_text()
            self.assertIn("2539 E. 28th St.", opinion)
            self.assertIn("location.replace", opinion)

    def test_removed_home_redirects_to_home_page(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.site(d, ("decatur-il-905-olive", "905 Olive", "Available"), ("decatur-il-1-a", "1 A", "Available"))
            B.build(r, "en")
            (r / "homes.js").write_text(homes_js(("decatur-il-1-a", "1 A", "Available"),
                                                 ("decatur-il-2-sold", "2 Sold", "Sold")))
            B.build(r, "en")
            page = (r / "book" / "905-olive" / "index.html").read_text()
            self.assertIn('location.replace("/")', page)

    def test_feedback_link_needs_a_crm_token(self):
        token = "eyJ0IjoiVGFiY2RlZjAxMjM0NSJ9.aaaaaa.bbbbbbbbbbbbbbbbbbbbbbbbbbb"
        self.assertEqual(
            B.feedback_link("905-olive", token, "es"),
            f"{B.SITES['es']['domain']}/opinion/905-olive?t={token}",
        )
        with self.assertRaises(ValueError):
            B.feedback_link("905-olive", "3095550148", "es")

    def test_real_site_has_905_olive(self):
        root = Path(__file__).resolve().parents[1]
        lang = "es" if (root / "como-funciona.html").is_file() else "en"
        out = root / B.SITES[lang]["dir"]
        page = out / "905-olive" / "index.html"
        if not page.is_file():
            self.skipTest("booking links not generated in this checkout")
        text = page.read_text()
        self.assertIn(f"home=decatur-il-905-olive&lang={lang}", text)
        self.assertIn("location.replace", text)
        self.assertNotIn("<iframe", text)
        for s in B.links(root).values():
            self.assertNotRegex((out / s / "index.html").read_text().lower(), r"lockbox|combo|\bcode\b")


if __name__ == "__main__":
    unittest.main()
