#!/usr/bin/env python3
"""Pull verified discovery files out of InsForge into a build-time merge doc.

Output: data/discovered-files.json
  { "<domain>": { "page": url|null, "dpa": url|null,
                  "subprocessors": url|null, "verifiedAt": iso } }

Only verified=true leads are eligible. Best page candidate wins by kind
priority trust > security > compliance, then shallowest path.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parent.parent
INSFORGE_META = ROOT.parent / ".insforge" / "project.json"
OUT = ROOT / "data" / "discovered-files.json"

KIND_PRIORITY = {"trust": 0, "security": 1, "compliance": 2}


def main() -> int:
    import os
    env_key, env_url = os.environ.get("INSFORGE_API_KEY", ""), os.environ.get("INSFORGE_URL", "")
    if env_key and env_url:
        base, key = env_url, env_key
    else:
        meta = json.loads(INSFORGE_META.read_text())
        base, key = meta["oss_host"], meta["api_key"]
    headers = {"Authorization": f"Bearer {key}"}

    rows: list[dict] = []
    offset = 0
    while True:
        r = httpx.get(
            f"{base}/api/database/records/ot_leads",
            params={"verified": "eq.true", "select": "domain,url,kind,verifiedAt",
                    "limit": 500, "offset": offset},
            headers=headers, timeout=30,
        )
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < 500:
            break
        offset += 500

    grouped: dict[str, dict] = {}
    for row in rows:
        domain = str(row.get("domain") or "").lower()
        kind = row.get("kind")
        url = row.get("url") or ""
        if not domain or not url:
            continue
        slot = grouped.setdefault(domain, {"page": None, "dpa": None,
                                            "subprocessors": None,
                                            "verifiedAt": None})
        if kind == "dpa" and not slot["dpa"]:
            slot["dpa"] = url
        elif kind == "subprocessors" and not slot["subprocessors"]:
            slot["subprocessors"] = url
        elif kind in KIND_PRIORITY and not slot["page"]:
            slot["page"] = url
        elif kind in KIND_PRIORITY and slot["page"]:
            cur = KIND_PRIORITY.get(kind_of(slot["page"]), 9)
            new = KIND_PRIORITY[kind]
            depth_cur = len(urlparse(slot["page"]).path.strip("/").split("/"))
            depth_new = len(urlparse(url).path.strip("/").split("/"))
            if (new, depth_new) < (cur, depth_cur):
                slot["page"] = url
        va = row.get("verifiedAt")
        if va and (not slot["verifiedAt"] or va > slot["verifiedAt"]):
            slot["verifiedAt"] = va

    OUT.write_text(json.dumps(grouped, indent=2, sort_keys=True) + "\n")
    pages = sum(1 for v in grouped.values() if v["page"])
    print(f"domains with verified files: {len(grouped)} · page slots: {pages}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


def kind_of(url: str) -> int:
    u = url.lower()
    if "/trust" in u:
        return KIND_PRIORITY["trust"]
    if "security" in u:
        return KIND_PRIORITY["security"]
    return KIND_PRIORITY["compliance"]


if __name__ == "__main__":
    sys.exit(main())
