"""Photo mirror, card thumbnails, and real-photo sort order.

Run from the repo root:  python3 scripts/test_card_photos.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import card_photos as P


def _jpeg(path: Path, size=(800, 500), color=(30, 60, 120)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, "JPEG", quality=85)


def _homes(records: list[tuple[str, list[str]]]) -> str:
    blocks = []
    for hid, photos in records:
        blocks.append(
            "\n  {\n"
            f'    id: "{hid}",\n'
            '    address:     "1 Main St",\n'
            '    description: "Una casa.",\n'
            '    heroPhoto: "",\n'
            f"    photos:    {json.dumps(photos)},\n"
            "  },"
        )
    return "const HOMES = [" + "".join(blocks) + "\n];\n"


class MirrorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.es = self.root / "es"
        self.en = self.root / "homes"
        self.es.mkdir()
        self.en.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_cover_is_copied_even_though_it_is_not_in_photos(self):
        """The gallery list omits images/<id>.jpg. Copying only photos[] leaves a blank card."""
        hid = "decatur-il-305-maffit"
        gallery = [f"images/{hid}-{n}.jpg" for n in range(1, 4)]
        (self.en / "homes.js").write_text(_homes([(hid, gallery)]), encoding="utf-8")
        (self.es / "homes.js").write_text(_homes([(hid, [])]), encoding="utf-8")
        _jpeg(self.en / "images" / f"{hid}.jpg", color=(200, 30, 30))
        for rel in gallery:
            _jpeg(self.en / rel, color=(20, 80, 40))

        before = P.blank_slugs(self.es)
        report = P.mirror_english_photos(self.es, self.en)

        self.assertEqual(before, [hid])
        self.assertEqual(report["blank_before"], [hid])
        self.assertEqual(report["copied_covers"], [hid])
        self.assertEqual(report["copied_gallery"][hid], 3)
        self.assertEqual(report["photos_filled"][hid], 3)
        self.assertEqual(report["blank_after"], [])
        self.assertTrue((self.es / "images" / f"{hid}.jpg").is_file())
        text = (self.es / "homes.js").read_text(encoding="utf-8")
        self.assertIn(f"images/{hid}-1.jpg", text)
        self.assertNotIn("photos:    []", text)
        # descriptions stay word for word
        self.assertIn('description: "Una casa."', text)

    def test_street_view_is_copied_when_there_is_no_seller_photo(self):
        hid = "toledo-oh-2-riverside"
        (self.en / "homes.js").write_text(_homes([(hid, [])]), encoding="utf-8")
        (self.es / "homes.js").write_text(_homes([(hid, [])]), encoding="utf-8")
        _jpeg(self.en / "images" / "sv" / f"{hid}.jpg", color=(80, 80, 80))

        report = P.mirror_english_photos(self.es, self.en)

        self.assertEqual(report["blank_before"], [hid])
        self.assertEqual(report["copied_sv"], [hid])
        self.assertEqual(report["photos_filled"], {})
        self.assertEqual(report["blank_after"], [])
        self.assertTrue((self.es / "images" / "sv" / f"{hid}.jpg").is_file())
        self.assertFalse((self.es / "images" / f"{hid}.jpg").exists())

    def test_existing_spanish_cover_is_not_replaced(self):
        hid = "decatur-il-1527-decatur"
        (self.en / "homes.js").write_text(_homes([(hid, [f"images/{hid}-1.jpg"])]), encoding="utf-8")
        (self.es / "homes.js").write_text(_homes([(hid, [f"images/{hid}-1.jpg"])]), encoding="utf-8")
        _jpeg(self.en / "images" / f"{hid}.jpg", color=(255, 0, 0))
        _jpeg(self.es / "images" / f"{hid}.jpg", color=(0, 0, 255))
        _jpeg(self.es / "images" / f"{hid}-1.jpg", color=(0, 0, 255))
        before = (self.es / "images" / f"{hid}.jpg").read_bytes()

        report = P.mirror_english_photos(self.es, self.en)

        self.assertEqual(report["copied_covers"], [])
        self.assertEqual((self.es / "images" / f"{hid}.jpg").read_bytes(), before)

    def test_ten_blank_slugs_gain_an_image(self):
        blanks = [
            "cahokia-il-5-denovion",
            "cahokiaheights-il-6-drexel",
            "decatur-il-1010-cleveland",
            "decatur-il-1600-john",
            "decatur-il-305-maffit",
            "decatur-il-346-18th",
            "eaststlouis-il-249-61st",
            "harrisburg-il-210-park",
            "stlouis-mo-1801-engelholm",
            "toledo-oh-2-riverside",
        ]
        en_records = []
        es_records = []
        for hid in blanks:
            gallery = [f"images/{hid}-1.jpg"] if hid == "decatur-il-305-maffit" else []
            en_records.append((hid, gallery))
            es_records.append((hid, []))
            if hid == "decatur-il-305-maffit":
                _jpeg(self.en / "images" / f"{hid}.jpg")
                _jpeg(self.en / "images" / f"{hid}-1.jpg")
            else:
                _jpeg(self.en / "images" / "sv" / f"{hid}.jpg")
        (self.en / "homes.js").write_text(_homes(en_records), encoding="utf-8")
        (self.es / "homes.js").write_text(_homes(es_records), encoding="utf-8")

        report = P.mirror_english_photos(self.es, self.en)

        self.assertEqual(report["blank_before"], sorted(blanks))
        self.assertEqual(report["blank_after"], [])
        self.assertEqual(report["photos_filled"]["decatur-il-305-maffit"], 1)
        self.assertEqual(len(report["copied_sv"]), 9)


class ThumbnailAndSortTests(unittest.TestCase):
    def test_thumbnail_is_cached_and_real_photos_sort_first(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        photo = "decatur-il-1527-decatur"
        street = "toledo-oh-2-riverside"
        (root / "homes.js").write_text(
            _homes([(photo, [f"images/{photo}-1.jpg"]), (street, [])]),
            encoding="utf-8",
        )
        _jpeg(root / "images" / f"{photo}.jpg", size=(1200, 800), color=(10, 40, 90))
        _jpeg(root / "images" / f"{photo}-1.jpg", size=(1200, 800))
        _jpeg(root / "images" / "sv" / f"{street}.jpg", size=(900, 600), color=(90, 90, 90))

        index = P.write_photo_index(root)
        again = P.write_photo_index(root)

        self.assertTrue(index[photo]["real"])
        self.assertFalse(index[street]["real"])
        self.assertTrue(index[street]["sv"])
        self.assertEqual(index[photo]["count"], 1)
        self.assertLessEqual(index[photo]["w"], P.CARD_MAX_W)
        self.assertGreater(index[photo]["h"], 0)
        card = root / index[photo]["card"]
        self.assertTrue(card.is_file())
        self.assertLess(card.stat().st_size, (root / "images" / f"{photo}.jpg").stat().st_size)
        self.assertEqual(again[photo]["w"], index[photo]["w"])
        ordered = sorted([photo, street], key=lambda hid: (P.real_photo_rank(index[hid]), hid))
        self.assertEqual(ordered, [photo, street])
        text = (root / "photo-index.js").read_text(encoding="utf-8")
        self.assertIn("const PHOTO_INDEX", text)
        self.assertIn("do not hand-edit", text)


class HomepageContractTests(unittest.TestCase):
    def test_homepage_uses_the_build_index_and_does_not_probe(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("Promise.allSettled(HOMES.map", text)
        self.assertIn("PHOTO_INDEX", text)
        self.assertIn("realPhoto", text)
        self.assertIn('loading="', text)
        self.assertIn("width=", text)
        home = (root / "home.html").read_text(encoding="utf-8")
        self.assertIn('id="conditionSlot" hidden', home)
        self.assertIn("Condición", home)
        self.assertIn('id="ctaSms"', home)
        self.assertIn("sms:", home)
        self.assertIn("getownerfinancedhomes.com/${C.id}.html", home)


if __name__ == "__main__":
    unittest.main()
