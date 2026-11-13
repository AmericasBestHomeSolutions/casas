#!/usr/bin/env python3
"""Fail if a publicly served file still contains an access instruction.

descriptions.es.json is keyed by the SHA-1 of the English source text.
The generator that writes it (scripts/refresh_listings.py on the maintainer
machine) is not in this repo. Strip the instruction from the English source
before hashing or translating, then strip the Spanish text the same way
before writing it. This script is the backstop: it does not print matched
text, so a failure log cannot repeat a code.

What to delete, and what to keep, is described in the pull request. In short:
delete the instruction clause (and a phone number in that same clause), keep
every other sentence, and keep a negation that does not give a number.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Built from code points so this file does not itself contain the emoji.
_LOCK_EMOJI = "".join(chr(cp) for cp in (0x1F510, 0x1F512))
_CANDADO = "canda" + "do"

_KEYWORD = (
    r"(?:"
    r"c[oó]digo\s+de\s+la\s+caja\s+de\s+seguridad"
    r"|c[oó]digo\s+de\s+caja\s+de\s+seguridad"
    r"|\block\s*-?\s*box\b"
    r"|\bcaja\s+de\s+seguridad\b"
    r"|access\s+code"
    r"|gate\s+code"
    r"|key\s+code"
    r"|door\s+code"
    r"|c[oó]digo\s+de\s+(?:la\s+)?acceso"
    r"|c[oó]digo\s+de\s+(?:la\s+)?llave"
    r"|c[oó]digo\s+de\s+(?:el\s+|la\s+)?port[oó]n"
    r"|c[oó]digo\s+de\s+(?:la\s+)?reja"
    r"|c[oó]digo\s+de\s+(?:la\s+)?puerta"
    r"|(?:combination|combo)\s+(?:code|is|:)"
    r"|\b" + _CANDADO + r"\b"
    r")"
)

_CLAUSE = re.compile(
    r"(?i)"
    r"(?P<lead>,[ \t]*)?"
    r"[ \t]*"
    r"(?:[" + _LOCK_EMOJI + r"][ \t]*)?"
    r"(?:(?:el|la|the)[ \t]+)?"
    + _KEYWORD
    + r"(?P<rest>[^.!?\n]*)"
    r"(?P<end>[.!?])?"
)

_BARE_CODE = re.compile(
    r"(?i)(?:(?<=^)|(?<=[.!?]\s))(?<![A-Za-z])(?:code|c[oó]digo)\s*[:#-]?\s*\d{3,8}\.?\s*"
)

_ACCESS_AT_DOOR = re.compile(
    r"(?i)(?:(?<=^)|(?<=[.!?]\s))"
    r"(?:access\s+at\s+door|acceso\s+(?:por|en)\s+la\s+puerta)"
    r"\.(?:\s+|$)"
)

_EMOJI_RE = re.compile("[" + _LOCK_EMOJI + "]")
_LOCKBOX_WORD = re.compile(
    r"(?i)\block\s*-?\s*box\b|\bcaja\s+de\s+seguridad\b|\b" + _CANDADO + r"\b"
)
_ACCESS_PHRASE = re.compile(
    r"(?i)(?:"
    r"access\s+code|gate\s+code|key\s+code|door\s+code"
    r"|c[oó]digo\s+de\s+(?:la\s+)?(?:acceso|llave|puerta|reja)"
    r"|c[oó]digo\s+de\s+(?:el\s+|la\s+)?port[oó]n"
    r"|(?:combination|combo)\s+(?:code|is|:)"
    r"|code\s+is\s+\d{3,8}"
    r")"
)
_CODE_NUM = re.compile(r"\d{3,8}")

_SKIP_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".ico", ".pdf",
    ".zip", ".gz", ".woff", ".woff2", ".ttf", ".mp4", ".webp",
}
_TEXT_SUFFIXES = {
    ".html", ".js", ".json", ".css", ".txt", ".xml", ".md",
    ".svg", ".yml", ".yaml", ".py", ".csv",
}


def _has_code_number(text: str) -> bool:
    return _CODE_NUM.search(text) is not None


def _strip_clauses(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        if not _has_code_number(match.group("rest") or ""):
            return match.group(0)
        if match.group("lead") and match.group("end"):
            return match.group("end")
        return ""

    return _CLAUSE.sub(repl, text)


def _tidy_boundary(text: str) -> str:
    """Clean only the join left where an instruction was removed."""
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+\.", ".", text)
    return text.strip()


def strip_access_instructions(text: str) -> str:
    """Remove access instructions. Leave the rest of the description."""
    if not text:
        return text
    current = text
    for _ in range(6):
        updated = _strip_clauses(current)
        updated = _BARE_CODE.sub("", updated)
        updated = _ACCESS_AT_DOOR.sub("", updated)
        if updated == current:
            break
        current = updated
    if current == text:
        return text
    return _tidy_boundary(current)


def _sentence_has_code_after(text: str, start: int) -> bool:
    end = len(text)
    for mark in ".!?\n":
        found = text.find(mark, start)
        if found != -1:
            end = min(end, found)
    return _has_code_number(text[start:end])


def find_violations(text: str) -> list[str]:
    """Return pattern ids. Never return the matched text."""
    if not text:
        return []
    found: list[str] = []

    def add(kind: str) -> None:
        if kind not in found:
            found.append(kind)

    if _EMOJI_RE.search(text):
        add("lock-emoji")
    for match in _LOCKBOX_WORD.finditer(text):
        # A mention with no number in the same sentence is not a disclosure.
        # "There is no lockbox." stays. A number after the word does not.
        if not _sentence_has_code_after(text, match.end()):
            continue
        add("lockbox")
        break
    if _ACCESS_PHRASE.search(text):
        add("access-phrase")
    if _BARE_CODE.search(text):
        add("bare-code-sentence")
    if _ACCESS_AT_DOOR.search(text):
        add("access-at-door")
    return found


def _line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _first_index(text: str, kind: str) -> int:
    if kind == "lock-emoji":
        match = _EMOJI_RE.search(text)
    elif kind == "lockbox":
        match = None
        for candidate in _LOCKBOX_WORD.finditer(text):
            if not _sentence_has_code_after(text, candidate.end()):
                continue
            match = candidate
            break
    elif kind == "access-phrase":
        match = _ACCESS_PHRASE.search(text)
    elif kind == "bare-code-sentence":
        match = _BARE_CODE.search(text)
    elif kind == "access-at-door":
        match = _ACCESS_AT_DOOR.search(text)
    else:
        match = None
    return match.start() if match else 0


def iter_served_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if "images" in path.relative_to(root).parts:
            continue
        suffix = path.suffix.lower()
        if suffix in _SKIP_SUFFIXES:
            continue
        if suffix and suffix not in _TEXT_SUFFIXES:
            continue
        yield path


def scan_tree(root: Path) -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for path in iter_served_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for kind in find_violations(text):
            rel = path.relative_to(root).as_posix()
            line = _line_number(text, _first_index(text, kind))
            hits.append((rel, line, kind))
    return hits


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]) if args else Path(__file__).resolve().parents[1]
    hits = scan_tree(root)
    for rel, line, kind in hits:
        print(f"{rel}:{line}: {kind}")
    if hits:
        print(f"{len(hits)} access-instruction match(es). No code values are printed.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
