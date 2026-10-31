#!/usr/bin/env python3
"""Layout pass for getownerfinancedhomes.com.

The master spreadsheet still lives on the owner's Mac and is what rebuilds
homes.js. This script does three things that pass must keep doing:

1. Record a listed date the first time a home id appears
   (data/listed-dates.json + listed-dates.js). Homes already in the catalog
   when dating started are stored as null, so they do not get a New badge.
   A real ISO date within the last 7 days is the only thing that badges a home.

2. Rewrite each <id>.html from home.html, keeping that page's canonical / Open
   Graph block and window.__HOME_ID__.

3. Rewrite buyer-facing invitations to text, call, or message us into
   "Agende una visita", and remove seller-to-team notes ("Hi Team, ...
   Thank you so much!", a seller's preference about who lives there,
   requests for occupants' social security numbers). Those stay internal. The daily refresh puts those words back into the
   descriptions, so this post-pass swaps only the invitation and leaves the
   rest of the sentence. Legal pages and the SMS consent checkbox are not
   touched. The seller owner-review page is left alone.

Run from the repo root:  python3 scripts/build_casas.py
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATES = ROOT / "data" / "listed-dates.json"
JS_OUT = ROOT / "listed-dates.js"
HOME = ROOT / "home.html"
HOMES_JS = ROOT / "homes.js"
DESC_JSON = ROOT / "descriptions.es.json"
TODAY = date.today().isoformat()

# Longest first, so "envíenos un texto o un mensaje" is not partly eaten by
# "envíenos un texto". These are invitations to text, call, or message us.
# "para llamar suyo" and "que le mande el casero" do not match.
_PHRASES_ES = (
    "llámenos o envíenos un texto o un mensaje",
    "llámenos o envíenos un texto o mensaje",
    "llámenos o envíenos un mensaje de texto",
    "envíenos un mensaje de texto o un mensaje",
    "mándenos un mensaje de texto o un mensaje",
    "envíenos un texto o un mensaje",
    "envíenos un texto o mensaje",
    "mándenos un texto o un mensaje",
    "mándenos un texto o mensaje",
    "envíenos un mensaje o un texto",
    "envíenos un mensaje o texto",
    "mándenos un mensaje o un texto",
    "mándenos un mensaje o texto",
    "llámenos o envíenos un texto",
    "llámenos o envíe un texto",
    "llámenos o escríbanos",
    "llame o envíe un texto",
    "llame o envíenos un texto",
    "envíenos un mensaje de texto",
    "mándenos un mensaje de texto",
    "envíe un mensaje de texto",
    "mande un mensaje de texto",
    "escríbanos un texto",
    "escríbanos un mensaje",
    "envíenos un texto",
    "mándenos un texto",
    "envíe un texto",
    "mande un texto",
    "envíenos un mensaje",
    "mándenos un mensaje",
    "envíe un mensaje",
    "mande un mensaje",
    "texto o un mensaje",
    "texto o mensaje",
    "mensaje o texto",
    "mensaje de texto",
    "escríbanos",
    "llámenos",
)
_PHRASES_EN = (
    "send us a text or a message",
    "send us a text or message",
    "send a text or a message",
    "send a text or message",
    "send us a text",
    "send us a message",
    "send a text",
    "send a message",
    "reach out by text or message",
    "reach out by text or phone",
    "reach out by phone or text",
    "reach out by text",
    "reach out by phone",
    "text or message us",
    "message or text us",
    "call or text us",
    "text or call us",
    "give us a call or a text",
    "give us a call or text",
    "give us a text or a call",
    "give us a text or call",
    "give us a call",
    "give us a text",
    "give us a ring",
    "shoot us a text",
    "shoot us a message",
    "drop us a text",
    "drop us a message",
    "drop us a line",
    "call or text",
    "text or call",
    "text us",
    "call us",
    "message us",
)
# "Contacto solo por TEXTO: 757-…" publishes a text number. The number goes with the phrase.
_TEXT_ONLY = re.compile(
    r"(?i)\b(?:contacto solo por texto|contact is text only)\b\s*:?\s*\d[\d\-]*"
)
_FIELD_RE = re.compile(r'(\b(?:copy|description):\s*")((?:\\.|[^"\\])*)(")')
_META_RE = re.compile(r"<meta\b[^>]*>", re.I)
_META_NAME_RE = re.compile(
    r'\b(?:name|property)\s*=\s*"(?:description|og:description|twitter:description)"',
    re.I,
)
_META_CONTENT_RE = re.compile(r'(content=")([^"]*)(")')


def _accent_pattern(phrase: str) -> str:
    fold = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u"}
    marks = {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú"}
    parts: list[str] = []
    for ch in phrase:
        base = fold.get(ch.lower(), ch.lower())
        if base in marks:
            parts.append("[" + base + marks[base] + "]")
        else:
            parts.append(re.escape(ch))
    return "".join(parts)


def _phrase_re(phrases: tuple[str, ...]) -> re.Pattern[str]:
    ordered = tuple(sorted(phrases, key=len, reverse=True))
    body = "|".join(_accent_pattern(p) for p in ordered)
    return re.compile(r"\b(?:" + body + r")\b", re.I)


_PHRASE_RE = {"es": _phrase_re(_PHRASES_ES), "en": _phrase_re(_PHRASES_EN)}
_TOUR = {"es": ("Agende una visita", "agende una visita"), "en": ("Book a Tour", "book a Tour")}

# Seller-to-team notes that reach the public description through the master list.
# They stay internal in the master sheet but must never show on the site: a note to
# "Hi Team" with its sign-off, a seller's preference about who lives there, or a
# request for occupants' social security numbers. Only those pieces are removed;
# the rest of the description stays word for word.
_TEAM_NOTE = re.compile(
    r"(?is)\b(?:hi|hello|hey|dear)\s+team\b[\s,.!:]*.{0,600}?"
    r"\b(?:thank you so much|thank you|thanks so much|thanks)\b[\s.!,]*"
    r"(?-i:[A-Z][a-z'-]{0,20}(?:\s+[A-Z][a-z'-]{0,20})?\.(?=\s|$)\s*)?"
)
_TEAM_GREETING = re.compile(r"(?i)\b(?:hi|hello|hey|dear)\s+team\b[\s,.!:]*|\bhola\s+equipo\b[\s,.!:]*")
_INTERNAL = re.compile(
    r"(?i)prefer to put (?:in )?a family in this house|social security|seguro social|\bSSN\b|\d{3}-\d{2}-\d{4}"
    r"|please ask for (?:these|this|them) from the buyer|\bI require answering\b"
)
_SEGMENT = re.compile(r"[^.!?\n*•]*(?:[.!?]+|\n|\*|•|$)")


def strip_internal_notes(text: str) -> tuple[str, int]:
    """Remove seller-to-team notes. Returns the text and how many pieces were removed."""
    if not text:
        return text, 0
    count = 0

    def drop(_match: re.Match) -> str:
        nonlocal count
        count += 1
        return ""

    out = _TEAM_NOTE.sub(drop, text)
    out = _TEAM_GREETING.sub(drop, out)
    kept = []
    for match in _SEGMENT.finditer(out):
        piece = match.group(0)
        if piece and _INTERNAL.search(piece):
            count += 1
            continue
        kept.append(piece)
    out = "".join(kept)
    if count:
        out = re.sub(r"[ \t]{2,}", " ", out).strip()
        out = re.sub(r"^[\s.,;:*•-]+", "", out)
        out = re.sub(r"[\s,;:*•-]+$", "", out)
    return out, count


def sanitize_prose(text: str, lang: str = "es") -> tuple[str, int]:
    """Replace each text/call/message invitation. The words around it stay.

    A capitalized invitation, or one that starts a sentence, becomes
    "Agende una visita". One in the middle of a sentence becomes
    "agende una visita".
    """
    if not text:
        return text, 0
    count = 0
    phrase_re = _PHRASE_RE[lang]
    lead, mid = _TOUR[lang]

    def apply(pattern: re.Pattern[str], src: str) -> str:
        nonlocal count

        def repl(match: re.Match[str]) -> str:
            nonlocal count
            count += 1
            raw = match.group(0)
            before = src[: match.start()]
            stripped = before.rstrip()
            sentence_start = stripped == "" or stripped[-1] in ".!?"
            if sentence_start or raw[:1].isupper():
                return lead
            return mid

        return pattern.sub(repl, src)

    out = apply(_TEXT_ONLY, text)
    out = apply(phrase_re, out)
    out, notes = strip_internal_notes(out)
    return out, count + notes


def sanitize_homes_js(text: str | None = None) -> tuple[str, int, int]:
    """Sanitize copy and description strings. Returns text, fields, phrases."""
    own_file = text is None
    if own_file:
        text = HOMES_JS.read_text(encoding="utf-8")
    fields = 0
    phrases = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal fields, phrases
        body, n = sanitize_prose(match.group(2), "es")
        body2, n2 = sanitize_prose(body, "en")
        n += n2
        if not n:
            return match.group(0)
        fields += 1
        phrases += n
        escaped = body2.replace("\\", "\\\\").replace('"', '\\"')
        return match.group(1) + escaped + match.group(3)

    cleaned = _FIELD_RE.sub(repl, text)
    if own_file and cleaned != text:
        HOMES_JS.write_text(cleaned, encoding="utf-8")
    return cleaned, fields, phrases


def sanitize_descriptions_json() -> tuple[int, int]:
    if not DESC_JSON.exists():
        return 0, 0
    raw = DESC_JSON.read_text(encoding="utf-8")
    data = json.loads(raw)
    fields = 0
    phrases = 0
    for entry in data.values():
        if not isinstance(entry, dict):
            continue
        for lang in ("es", "en"):
            value = entry.get(lang)
            if not isinstance(value, str):
                continue
            new, n = sanitize_prose(value, lang)
            if n:
                entry[lang] = new
                fields += 1
                phrases += n
    if fields:
        # indent=1 matches the file on disk, so untouched strings stay put.
        DESC_JSON.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return fields, phrases


def sanitize_meta_html(html: str) -> tuple[str, int]:
    """Sanitize description, og:description, and twitter:description."""
    phrases = 0

    def repl_tag(match: re.Match[str]) -> str:
        nonlocal phrases
        tag = match.group(0)
        if not _META_NAME_RE.search(tag):
            return tag

        def repl_content(content: re.Match[str]) -> str:
            nonlocal phrases
            body, n = sanitize_prose(content.group(2), "es")
            body, n2 = sanitize_prose(body, "en")
            n += n2
            if not n:
                return content.group(0)
            phrases += n
            escaped = body.replace("&", "&amp;").replace('"', "&quot;")
            return content.group(1) + escaped + content.group(3)

        return _META_CONTENT_RE.sub(repl_content, tag, count=1)

    return _META_RE.sub(repl_tag, html), phrases


def home_ids() -> list[str]:
    text = HOMES_JS.read_text(encoding="utf-8")
    return re.findall(r'\bid:\s*"([^"]+)"', text)


def stamp_dates(ids: list[str]) -> dict:
    DATES.parent.mkdir(exist_ok=True)
    current: dict = {}
    if DATES.exists():
        current = json.loads(DATES.read_text(encoding="utf-8"))
    first_run = not DATES.exists()
    for hid in ids:
        if hid not in current:
            # First time we see the catalog: unknown dates, no New badges.
            # After that, a brand-new id is stamped today.
            current[hid] = None if first_run else TODAY
    # Drop ids that left the catalog so the file does not grow forever.
    for hid in list(current):
        if hid not in ids:
            current.pop(hid)
    DATES.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    lines = ["/* Generated by scripts/refresh_listings.py — do not hand-edit. */",
             "const LISTED_ON = " + json.dumps({k: v for k, v in current.items() if v}, indent=2) + ";"]
    # null dates are omitted; a missing key means no badge.
    JS_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return current


def emit_pages() -> int:
    template = HOME.read_text(encoding="utf-8")
    ids = set(home_ids())
    n = 0
    for path in sorted(ROOT.glob("*.html")):
        hid = path.stem
        if hid not in ids or path.name == "home.html":
            continue
        raw = path.read_text(encoding="utf-8")
        head = ""
        block = re.search(r'(<link rel="canonical"[\s\S]*?<meta name="twitter:image"[^>]*>)', raw)
        if block:
            head = "\n" + block.group(1)
        page = template
        desc = re.search(r'<meta name="description" content="[^"]*"/>', page)
        if desc and head and 'rel="canonical"' not in page:
            page = page.replace(desc.group(0), desc.group(0) + head, 1)
        marker = '<script src="homes.js"></script>'
        if 'window.__HOME_ID__="' not in page and marker in page:
            page = page.replace(marker, f'<script>window.__HOME_ID__="{hid}";</script>\n' + marker, 1)
        page, _meta_hits = sanitize_meta_html(page)
        path.write_text(page, encoding="utf-8")
        n += 1
    return n


def main() -> None:
    _cleaned, fields, phrases = sanitize_homes_js()
    json_fields, json_phrases = sanitize_descriptions_json()
    ids = home_ids()
    stamp_dates(ids)
    n = emit_pages()
    print(
        f"sanitized {phrases} invitations in {fields} home descriptions "
        f"and {json_phrases} in {json_fields} translation strings, "
        f"recorded {len(ids)} homes, rewrote {n} listing pages"
    )


if __name__ == "__main__":
    main()
