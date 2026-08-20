#!/usr/bin/env python3
"""Every Standards entry has one clerk reading sentence."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATHS = [
    ROOT / "data" / "attestations.json",
    ROOT / "site" / "data" / "attestations.json",
]
BANNED = ("trusted", "trust score", "security rating", "maturity index")


def check(path: Path) -> list[str]:
    errors = []
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("attestations") or []
    if len(rows) != 71:
        errors.append(f"{path.name}: expected 71 entries, got {len(rows)}")
    seen = set()
    for row in rows:
        i = row.get("id", "?")
        seen.add(i)
        read = (row.get("read") or "").strip()
        if not read:
            errors.append(f"{i}: missing read")
            continue
        if not read.endswith("."):
            errors.append(f"{i}: read must end with a period")
        if read.count(".") != 1:
            errors.append(f"{i}: read is not one sentence")
        low = read.lower()
        if "not a company score" not in low or "not a badge we issued" not in low:
            errors.append(f"{i}: read must say not a company score and not a badge we issued")
        for bad in BANNED:
            if bad in low:
                errors.append(f"{i}: banned {bad!r}")
        if not (row.get("eli5") or "").strip():
            errors.append(f"{i}: missing eli5")
    return errors


def main() -> int:
    errors = []
    for path in PATHS:
        if not path.exists():
            errors.append(f"missing {path}")
            continue
        errors.extend(check(path))
    if errors:
        print("FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print("ok: 71 entries each have one clerk reading sentence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
