#!/usr/bin/env python3
"""Compare price, down payment, monthly payment and status across the two buyer sites.

    python3 scripts/check_consistency.py --homes /path/to/homes --casas /path/to/casas

Shared home ids must match on those four fields. data/home-facts.json must match
when both checkouts have the file. Prices never live in home-facts.json.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BLOCK_RE = re.compile(r'\n  \{\n    id: "([^"]+)",[\s\S]*?\n  \},')
FIELDS = ("lockedPrice", "moveIn", "monthlyPayment", "status")


def _field(block: str, key: str):
    match = re.search(rf'\n    {key}:\s*("(?:\\.|[^"\\])*"|[^,\n]*),', block)
    if not match:
        return None
    raw = match.group(1).strip()
    if raw.startswith('"'):
        return json.loads(raw)
    if raw in {"", "null"}:
        return None
    try:
        if re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
            number = float(raw)
            return int(number) if number == int(number) else number
    except ValueError:
        pass
    return raw


def load_homes(root: Path) -> dict[str, dict]:
    text = (root / "homes.js").read_text(encoding="utf-8").split("const SOLD_CARDS", 1)[0]
    out = {}
    for match in BLOCK_RE.finditer(text):
        block = match.group(0)
        out[match.group(1)] = {key: _field(block, key) for key in FIELDS}
    return out


def _num(value):
    if value is None or value == "":
        return None
    try:
        number = float(str(value).replace(",", "").replace("$", ""))
    except ValueError:
        return str(value)
    return int(number) if number == int(number) else number


def check(homes_root: Path, casas_root: Path) -> list[str]:
    errors = []
    homes_js = Path(homes_root) / "homes.js"
    casas_js = Path(casas_root) / "homes.js"
    if not homes_js.is_file() or not casas_js.is_file():
        return ["homes.js missing in one of the checkouts"]
    en, es = load_homes(Path(homes_root)), load_homes(Path(casas_root))
    shared = sorted(set(en) & set(es))
    if not shared:
        errors.append("no shared home ids")
    for hid in shared:
        for key in FIELDS:
            left, right = en[hid].get(key), es[hid].get(key)
            if key == "status":
                same = str(left or "").strip().lower() == str(right or "").strip().lower()
            else:
                same = _num(left) == _num(right)
            if not same:
                errors.append(f"{hid} {key}: homes={left!r} casas={right!r}")
    facts_en = Path(homes_root) / "data" / "home-facts.json"
    facts_es = Path(casas_root) / "data" / "home-facts.json"
    if facts_en.is_file() and facts_es.is_file():
        if json.loads(facts_en.read_text(encoding="utf-8")) != json.loads(facts_es.read_text(encoding="utf-8")):
            errors.append("data/home-facts.json differs")
    elif facts_en.is_file() or facts_es.is_file():
        errors.append("data/home-facts.json is missing from one checkout")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--homes", type=Path, required=True)
    parser.add_argument("--casas", type=Path, required=True)
    args = parser.parse_args(argv)
    errors = check(args.homes, args.casas)
    if errors:
        print(f"{len(errors)} consistency problem(s):")
        print("\n".join(errors[:40]))
        return 1
    print("consistency ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
