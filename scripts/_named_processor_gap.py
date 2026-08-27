#!/usr/bin/env python3
"""Named processors first-party files already name, but the register lacks.

Prints the gap list (named-by desc). expand_batch.next_batch prefers
crawl-queue rows with source `named-processor-gap` over Wikipedia leftover
walks, so a cited processor that is not on the register jumps the queue.

Usage:
  python3 scripts/_named_processor_gap.py
  python3 scripts/_named_processor_gap.py --min 1
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from processor_aliases import (  # noqa: E402
    active_aliases,
    canonical_processor_id,
    skip_processor,
)

DATA = ROOT / "data"
ENRICHED = DATA / "enriched.json"
SUB = DATA / "subprocessors.json"
QUEUE_SOURCE = "named-processor-gap"


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def gap_rows(subs: dict | None = None, register=None, *, min_named: int = 1) -> list[dict]:
    """Processors named on a sourced edge that have no register row after aliases."""
    if subs is None:
        subs = load_json(SUB, {"nodes": [], "edges": []})
    if register is None:
        enr = load_json(ENRICHED, {"companies": []})
        register = {c["slug"]: c for c in enr.get("companies") or [] if c.get("slug")}
    slugs = set(register)
    aliases = active_aliases(slugs)
    nodes = {n["id"]: n for n in (subs.get("nodes") or []) if n.get("id")}
    named_by = defaultdict(int)
    sources = defaultdict(list)
    evidence = {}
    for e in subs.get("edges") or []:
        if not e.get("source_url"):
            continue
        raw = e.get("to") or e.get("processor_slug") or e.get("processor")
        if not raw:
            continue
        dest = aliases.get(raw, raw)
        dest = canonical_processor_id(dest, slugs)
        node = nodes.get(raw) or nodes.get(dest) or {}
        if skip_processor(dest, node.get("name") or e.get("evidence") or ""):
            continue
        named_by[dest] += 1
        src = e.get("source_url")
        if src and src not in sources[dest]:
            sources[dest].append(src)
        if dest not in evidence and e.get("evidence"):
            evidence[dest] = e["evidence"]

    rows = []
    for dest, count in named_by.items():
        if count < min_named:
            continue
        if dest in slugs:
            continue
        node = nodes.get(dest) or {}
        rows.append({
            "slug": dest,
            "name": node.get("name") or evidence.get(dest) or dest,
            "domain": node.get("domain") or "",
            "named_by": count,
            "source_url": (sources.get(dest) or [""])[0],
            "source_urls": sources.get(dest) or [],
            "source": QUEUE_SOURCE,
        })
    rows.sort(key=lambda r: (-int(r["named_by"]), str(r["slug"])))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min", type=int, default=1, help="minimum named-by count")
    args = ap.parse_args()
    rows = gap_rows(min_named=args.min)
    print(f"# named processor not on register  count={len(rows)}  min={args.min}")
    print("# named_by\tslug\tname\tdomain\tsource_url")
    for r in rows:
        print(
            f"{r['named_by']}\t{r['slug']}\t{r['name']}\t{r['domain']}\t{r['source_url']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
