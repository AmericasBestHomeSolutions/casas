#!/usr/bin/env python3
"""Photo facts for the Spanish site, recorded at build time.

The English clone (../homes on the Mac, _homes in the daily sync) is the photo
source. Slugs match 1:1. The layout pass used to leave a home's photos array
alone, so a home the portal added with photos: [] never received the English
files. Two paths are easy to drop:

* the cover images/<id>.jpg is not inside photos[] (that array is the gallery,
  images/<id>-1.jpg onward), and
* Street View lives at images/sv/<id>.jpg and is not in photos[] at all.

The homepage then asked for images/<id>.jpg on every home. A miss is a 404,
then another request for the Street View file. Homes with neither file draw a
blank tile.

mirror_english_photos copies those files when this site is missing them and
fills an empty photos array from the English list. It does not replace a file
that is already here, and it does not touch descriptions.

write_photo_index writes photo-index.js and a cached card thumbnail
(images/cards/<id>.jpg, Pillow, max width 640). The homepage reads that index
instead of probing full-size files.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

CARD_MAX_W = 640
CARD_QUALITY = 72

_BLOCK_RE = re.compile(r'\n  \{\n    id: "([^"]+)",[\s\S]*?\n  \},')
_PHOTOS_RE = re.compile(r"(\n    photos:\s*)(\[[\s\S]*?\])(\s*,)")


def english_roots(root: Path) -> list[Path]:
    """Sibling clones the layout pass already knows about. First hit wins."""
    found = []
    for path in (root.parent / "homes", root / "_homes"):
        if (path / "homes.js").is_file():
            found.append(path)
    return found


def parse_homes(text: str) -> dict[str, dict]:
    """id -> {photos, hero, block} from a homes.js HOMES array."""
    out: dict[str, dict] = {}
    for match in _BLOCK_RE.finditer(text):
        hid, block = match.group(1), match.group(0)
        photos = _photos_list(block)
        hero = re.search(r'\n    heroPhoto:\s*"([^"]*)"', block)
        out[hid] = {
            "photos": photos,
            "hero": hero.group(1) if hero else "",
            "start": match.start(),
            "end": match.end(),
            "block": block,
        }
    return out


def _photos_list(block: str) -> list[str]:
    match = _PHOTOS_RE.search(block)
    if not match:
        return []
    raw = match.group(2).strip()
    if raw == "[]":
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [p for p in data if isinstance(p, str)]


def _has_cover(root: Path, hid: str, hero: str = "") -> bool:
    if (root / "images" / f"{hid}.jpg").is_file():
        return True
    return bool(hero) and (root / hero).is_file()


def _has_streetview(root: Path, hid: str) -> bool:
    return (root / "images" / "sv" / f"{hid}.jpg").is_file()


def blank_slugs(root: Path, homes: dict[str, dict] | None = None) -> list[str]:
    """Homes with no seller cover, no gallery file, and no Street View image."""
    if homes is None:
        homes = parse_homes((root / "homes.js").read_text(encoding="utf-8"))
    blank = []
    for hid, rec in homes.items():
        gallery = any((root / rel).is_file() for rel in rec["photos"])
        if not _has_cover(root, hid, rec["hero"]) and not gallery and not _has_streetview(root, hid):
            blank.append(hid)
    return sorted(blank)


def _copy_missing(src: Path, dest: Path) -> bool:
    """Copy src to dest when dest is absent. Never replace a file already here."""
    if not src.is_file() or dest.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def _set_photos(block: str, files: list[str]) -> str:
    rendered = json.dumps(files)
    return _PHOTOS_RE.sub(lambda m: m.group(1) + rendered + m.group(3), block, count=1)


def mirror_english_photos(root: Path, english: Path | None = None) -> dict:
    """Copy missing seller photos and Street View files from the English site.

    Returns a report the build prints and the tests assert on. Descriptions
    are not read or written.
    """
    root = Path(root)
    report = {
        "english": "",
        "blank_before": [],
        "copied_covers": [],
        "copied_gallery": {},
        "copied_sv": [],
        "photos_filled": {},
        "blank_after": [],
    }
    js_path = root / "homes.js"
    if not js_path.is_file():
        return report
    text = js_path.read_text(encoding="utf-8")
    spanish = parse_homes(text)
    report["blank_before"] = blank_slugs(root, spanish)
    if english is None:
        roots = english_roots(root)
        english = roots[0] if roots else None
    if english is None or not (Path(english) / "homes.js").is_file():
        report["blank_after"] = report["blank_before"]
        return report
    english = Path(english)
    report["english"] = str(english)
    source = parse_homes((english / "homes.js").read_text(encoding="utf-8"))
    # Replace blocks from the end so earlier offsets stay valid.
    edits: list[tuple[int, int, str]] = []
    for hid, rec in spanish.items():
        en = source.get(hid)
        if not en:
            continue
        if _copy_missing(english / "images" / f"{hid}.jpg", root / "images" / f"{hid}.jpg"):
            report["copied_covers"].append(hid)
        gallery_src = list(en["photos"])
        if not gallery_src:
            n = 1
            while (english / "images" / f"{hid}-{n}.jpg").is_file():
                gallery_src.append(f"images/{hid}-{n}.jpg")
                n += 1
        copied = 0
        for rel in gallery_src:
            if _copy_missing(english / rel, root / rel):
                copied += 1
        if copied:
            report["copied_gallery"][hid] = copied
        # Street View is the stand-in only when there is still no seller cover.
        if not _has_cover(root, hid, rec["hero"]):
            if _copy_missing(english / "images" / "sv" / f"{hid}.jpg", root / "images" / "sv" / f"{hid}.jpg"):
                report["copied_sv"].append(hid)
        if rec["photos"]:
            continue
        files = [rel for rel in gallery_src if (root / rel).is_file()]
        if not files:
            continue
        edits.append((rec["start"], rec["end"], _set_photos(rec["block"], files)))
        report["photos_filled"][hid] = len(files)
    if edits:
        for start, end, block in sorted(edits, key=lambda item: item[0], reverse=True):
            text = text[:start] + block + text[end:]
        js_path.write_text(text, encoding="utf-8")
        spanish = parse_homes(text)
    report["copied_covers"].sort()
    report["copied_sv"].sort()
    report["blank_after"] = blank_slugs(root, spanish)
    return report


def real_photo_rank(meta: dict | None) -> int:
    """0 for a seller photo, 1 for Street View or no image. Lower sorts first."""
    return 0 if meta and meta.get("real") else 1


def _thumbnail(src: Path, dest: Path) -> tuple[int, int]:
    """Resize to CARD_MAX_W. Skip when dest is already newer than src."""
    from PIL import Image

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_mtime >= src.stat().st_mtime and dest.stat().st_size > 0:
        with Image.open(dest) as existing:
            return existing.size
    with Image.open(src) as im:
        im = im.convert("RGB")
        width, height = im.size
        if width > CARD_MAX_W:
            height = max(1, round(height * CARD_MAX_W / width))
            width = CARD_MAX_W
            im = im.resize((width, height), Image.Resampling.LANCZOS)
        im.save(dest, "JPEG", quality=CARD_QUALITY, optimize=True, progressive=True)
        return width, height


def write_photo_index(root: Path) -> dict:
    """photo-index.js plus images/cards/<id>.jpg for every home that has a picture."""
    root = Path(root)
    text = (root / "homes.js").read_text(encoding="utf-8")
    homes = parse_homes(text)
    index: dict[str, dict] = {}
    for hid, rec in homes.items():
        cover = root / "images" / f"{hid}.jpg"
        hero = root / rec["hero"] if rec["hero"] else None
        sv = root / "images" / "sv" / f"{hid}.jpg"
        real_src = cover if cover.is_file() else (hero if hero and hero.is_file() else None)
        src = real_src or (sv if sv.is_file() else None)
        count = len([rel for rel in rec["photos"] if (root / rel).is_file()])
        if real_src and count == 0:
            count = 1
        entry = {"real": bool(real_src), "count": count if real_src else 0, "card": "", "w": 0, "h": 0, "sv": bool(sv.is_file()) and not real_src}
        if src is not None:
            try:
                width, height = _thumbnail(src, root / "images" / "cards" / f"{hid}.jpg")
            except Exception:
                width = height = 0
            if width and height:
                entry["card"] = f"images/cards/{hid}.jpg"
                entry["w"] = width
                entry["h"] = height
        index[hid] = entry
    payload = json.dumps(index, ensure_ascii=False, separators=(",", ":"))
    out = root / "photo-index.js"
    out.write_text(
        "/* Generated by scripts/build_casas.py — do not hand-edit. */\n"
        f"const PHOTO_INDEX = {payload};\n",
        encoding="utf-8",
    )
    return index
