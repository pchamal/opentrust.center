#!/usr/bin/env python3
"""Apply gap-resolve report domains onto crawl-queue. Never invent."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/workspace/trust-index")
QUEUE = ROOT / "data" / "crawl-queue.json"
ENR = ROOT / "data" / "enriched.json"
REPORT = ROOT / "data" / "render" / "named-processor-gap-resolve-hour.json"

queue = json.loads(QUEUE.read_text())
enr = json.loads(ENR.read_text())
have = {c["slug"] for c in enr.get("companies") or [] if c.get("slug")}
report = json.loads(REPORT.read_text())
cands = report.get("enqueued_candidates") or []
by_slug = {c["slug"]: i for i, c in enumerate(queue.get("companies") or []) if c.get("slug")}
updated = 0
appended = 0
skipped = 0
for r in cands:
    slug = r.get("slug")
    domain = (r.get("domain") or "").strip()
    if not slug or not domain or slug in have:
        skipped += 1
        continue
    if slug.lower() in {"entity-name", "entity name"} or (r.get("name") or "").strip().lower() == "entity name":
        skipped += 1
        continue
    row = {
        "name": r.get("name") or slug,
        "slug": slug,
        "domain": domain,
        "source": "named-processor-gap",
        "source_url": r.get("source_url") or "",
        "named_by": r.get("named_by") or 1,
        "priority": 0,
        "reason": r.get("reason") or "",
    }
    if slug in by_slug:
        existing = queue["companies"][by_slug[slug]]
        if existing.get("domain"):
            skipped += 1
            continue
        existing["domain"] = domain
        if r.get("source_url") and not existing.get("source_url"):
            existing["source_url"] = r["source_url"]
        if r.get("reason"):
            existing["reason"] = r["reason"]
        updated += 1
        print(f"UPDATE {slug} {domain} {r.get('reason')}")
    else:
        queue["companies"].append(row)
        by_slug[slug] = len(queue["companies"]) - 1
        appended += 1
        print(f"APPEND {slug} {domain} {r.get('reason')}")

queue["queued"] = len(queue["companies"])
queue["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
QUEUE.write_text(json.dumps(queue, indent=2) + "\n")
ready = sum(1 for c in queue["companies"] if c.get("domain") and c.get("slug") not in have)
print(f"DONE updated={updated} appended={appended} skipped={skipped} ready={ready} queued={queue['queued']}")
