#!/usr/bin/env python3
"""Probe extra public-enterprise companies only. Does not touch Cloud 100 results."""
from __future__ import annotations

import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from crawl import ROOT, WORKERS, probe_company

def main() -> int:
    extras = json.loads((ROOT / "extra-companies.json").read_text())
    print(f"Probing {len(extras)} extras with {WORKERS} workers...", flush=True)
    results = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(probe_company, c): c for c in extras}
        for i, fut in enumerate(as_completed(futs), 1):
            row = fut.result()
            row["list"] = "enterprise"
            row["source"] = row.get("source") or "public-enterprise"
            results.append(row)
            flag = "HIT" if row["found"] else "miss"
            extra = f"  {row['vendor']}  {row['trust_url']}" if row["found"] else ""
            print(f"[{i:3}/{len(extras)}] {flag:4} {row['name']}{extra}", flush=True)
    results.sort(key=lambda r: r["name"].lower())
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "public-enterprise",
        "companies": results,
    }
    out = ROOT / "data" / "extra-results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    found = sum(1 for r in results if r["found"])
    print()
    print(f"Found {found}/{len(results)} extras in {time.time()-t0:.1f}s")
    for name, count in Counter(r["vendor"] for r in results if r["found"]).most_common():
        print(f"  {name}: {count}")
    print(f"Wrote {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
