"""Parser surface that scripts/card_photos.py imports.

The full sheet sync lives in the homes repo. This module only exposes the
block reader that file calls, copied from that parser so the shared
card_photos.py stays byte-identical.
"""
from __future__ import annotations

import json
import re

BLOCK_RE = re.compile(r"\n  \{\n    id: \"([^\"]+)\",[\s\S]*?\n  \},")


def blocks(text: str) -> dict[str, re.Match]:
    return {m.group(1): m for m in BLOCK_RE.finditer(text)}


def field(block: str, key: str):
    m = re.search(rf"\n    {key}:\s*(\"(?:\\.|[^\"\\])*\"|[^,\n]*),", block)
    if not m:
        return None
    raw = m.group(1).strip()
    return json.loads(raw) if raw.startswith('"') else raw
