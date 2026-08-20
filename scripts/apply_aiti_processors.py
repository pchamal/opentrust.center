#!/usr/bin/env python3
"""Merge curated first-party AI-processor names into data.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PAGES = SITE / "data" / "aiti-processors.json"
DATA = SITE / "data.json"


def main() -> int:
    doc = json.loads(PAGES.read_text())
    recs = doc.get("processors") or {}
    data = json.loads(DATA.read_text())
    by_slug = {c["slug"]: c for c in data["companies"]}
    filed = set(recs)
    for row in data["companies"]:
        if row.get("slug") not in filed and "ai_processors" in row:
            del row["ai_processors"]
    for slug, rec in recs.items():
        row = by_slug.get(slug)
        if not row:
            raise SystemExit(f"unknown slug {slug}")
        names = rec.get("names") or []
        if not names:
            raise SystemExit(f"empty names for {slug}")
        row["ai_processors"] = {
            "names": names,
            "source_url": rec.get("source_url"),
            "via": rec.get("via"),
        }
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("filed", len(recs), "open", len(doc.get("open") or []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
