#!/usr/bin/env python3
"""File verified AI-page discoveries into site/data/aiti-pages.json.

Reads ot_leads where verified=true and kind='ai-page', resolves each domain
to a register slug via site/data.json, and appends pages entries the build
already merges into public ai_page. Existing curated entries are never
overwritten. Run: .venv/bin/python pipeline/export_ai.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parent.parent
INSFORGE_META = ROOT.parent / ".insforge" / "project.json"
DATA_JSON = ROOT / "site" / "data.json"
AITI_PAGES = ROOT / "site" / "data" / "aiti-pages.json"


def creds() -> tuple[str, str]:
    import os
    if os.environ.get("INSFORGE_API_KEY") and os.environ.get("INSFORGE_URL"):
        return os.environ["INSFORGE_URL"], os.environ["INSFORGE_API_KEY"]
    meta = json.loads(INSFORGE_META.read_text())
    return meta["oss_host"], meta["api_key"]


def main() -> int:
    base, key = creds()
    headers = {"Authorization": f"Bearer {key}"}
    rows: list[dict] = []
    offset = 0
    while True:
        r = httpx.get(
            f"{base}/api/database/records/ot_leads",
            params={"verified": "eq.true", "kind": "eq.ai-page",
                    "select": "domain,url,title,verifiedAt", "limit": 500,
                    "offset": offset},
            headers=headers, timeout=30,
        )
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < 500:
            break
        offset += 500

    data = json.loads(DATA_JSON.read_text())
    slug_by_domain = {}
    for c in data.get("companies", []):
        d = (c.get("domain") or "").lower()
        if d and c.get("slug"):
            slug_by_domain[d] = c["slug"]

    doc = json.loads(AITI_PAGES.read_text())
    pages = doc.get("pages") or {}
    added = 0
    for row in rows:
        domain = str(row.get("domain") or "").lower()
        url = row.get("url") or ""
        slug = slug_by_domain.get(domain)
        if not slug or not url or slug in pages:
            continue
        host = urlparse(url).netloc.lower().lstrip("www.")
        seen = str(row.get("verifiedAt") or "")[:10]
        pages[slug] = {
            "url": url,
            "host": host,
            "title": (row.get("title") or "")[:160],
            "kind": "discovered-first-party",
            "via": "discovery-pipeline",
        }
        if seen:
            pages[slug]["seen"] = seen
        added += 1

    doc["pages"] = pages
    doc["count"] = len(pages)
    AITI_PAGES.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(f"ai pages filed: {added} new · {len(pages)} total in aiti-pages.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
