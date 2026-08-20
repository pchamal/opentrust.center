#!/usr/bin/env python3
"""Hourly expand: probe the next N queued companies and file what we can verify."""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import crawl  # noqa: E402

from merge_render import rescore, canon_cert  # noqa: E402
import enrich  # noqa: E402

DATA = ROOT / "data"
QUEUE = DATA / "crawl-queue.json"
STATE = DATA / "crawl-state.json"
ENRICHED = DATA / "enriched.json"
SITE_ENRICHED = ROOT / "site" / "data" / "enriched.json"
BATCH_SIZE = 40
WORKERS = 12

CERT_RES = [
    (re.compile(r"\bSOC\s*2\s*Type\s*(?:II|2)\b", re.I), "SOC 2 Type II"),
    (re.compile(r"\bSOC\s*3\b", re.I), "SOC 3"),
    (re.compile(r"\bSOC\s*1\s*Type\s*(?:II|2)\b", re.I), "SOC 1 Type II"),
    (re.compile(r"\bISO(?:/IEC)?\s*27001\b", re.I), "ISO 27001"),
    (re.compile(r"\bISO(?:/IEC)?\s*27701\b", re.I), "ISO 27701"),
    (re.compile(r"\bISO(?:/IEC)?\s*42001\b", re.I), "ISO 42001"),
    (re.compile(r"\bAIUC-1\b", re.I), "AIUC-1"),
    (re.compile(r"\bISO(?:/IEC)?\s*27017\b", re.I), "ISO 27017"),
    (re.compile(r"\bISO(?:/IEC)?\s*27018\b", re.I), "ISO 27018"),
    (re.compile(r"\bFedRAMP\s+High\b", re.I), "FedRAMP High"),
    (re.compile(r"\bFedRAMP\b", re.I), "FedRAMP Moderate"),
    (re.compile(r"\bHIPAA\b", re.I), "HIPAA"),
    (re.compile(r"\bPCI[\s-]?DSS\b", re.I), "PCI DSS"),
    (re.compile(r"\bHITRUST\b", re.I), "HITRUST"),
    (re.compile(r"\bGDPR\b", re.I), "GDPR"),
    (re.compile(r"\bCCPA\b|\bCPRA\b", re.I), "CCPA"),
    (re.compile(r"\bCSA\s*STAR\b", re.I), "CSA STAR"),
    (re.compile(r"\bTX-?RAMP\b", re.I), "TX-RAMP"),
    (re.compile(r"\bCyber\s*Essentials\s*Plus\b", re.I), "Cyber Essentials Plus"),
    (re.compile(r"\bCyber\s*Essentials\b", re.I), "Cyber Essentials"),
]


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n")


def extract_certs(html: str) -> list[str]:
    if not html:
        return []
    out = []
    for rx, name in CERT_RES:
        if rx.search(html) and name not in out:
            n = canon_cert(name) or name
            if n and n not in out:
                out.append(n)
    return out


def next_batch(queue: dict, state: dict, n: int) -> list[dict]:
    companies = queue.get("companies") or []
    cursor = int(state.get("cursor") or 0)
    have = {c["slug"] for c in load_json(ENRICHED, {}).get("companies", [])}
    picked = []
    i = cursor
    while i < len(companies) and len(picked) < n:
        row = companies[i]
        i += 1
        if not row.get("domain") or row.get("slug") in have:
            continue
        picked.append(row)
    state["cursor"] = i
    return picked


def take_edges(rec: dict) -> list[dict]:
    return list(rec.pop("_edges", None) or [])


def has_public_page(probe: dict) -> bool:
    return bool(probe.get("found") and (probe.get("trust_url") or probe.get("final_url")))


def merge_processor_edges(edges: list[dict], register: dict[str, dict]) -> None:
    """Append sourced processor edges. No edge without source_url."""
    if not edges:
        return
    paths = (DATA / "subprocessors.json", ROOT / "site" / "data" / "subprocessors.json")
    subs = load_json(paths[0], {"nodes": [], "edges": []})
    nodes = {n["id"]: n for n in (subs.get("nodes") or []) if n.get("id")}
    existing = {(e.get("from"), e.get("to")) for e in (subs.get("edges") or [])}
    proc_meta = {i: (n, d) for i, n, d, _a in enrich.PROCESSORS}
    for e in edges:
        src = e.get("source_url")
        frm, to = e.get("from"), e.get("to")
        if not src or not frm or not to or (frm, to) in existing:
            continue
        subs.setdefault("edges", []).append({
            "from": frm,
            "to": to,
            "source_url": src,
            "evidence": e.get("evidence") or to,
        })
        existing.add((frm, to))
        if to in nodes:
            continue
        if to in register:
            nodes[to] = {
                "id": to,
                "name": register[to].get("name") or to,
                "domain": register[to].get("domain") or "",
                "kind": "company",
                "in_register": True,
            }
        else:
            name, domain = proc_meta.get(to, (e.get("evidence") or to, ""))
            nodes[to] = {
                "id": to,
                "name": name,
                "domain": domain,
                "kind": "processor",
                "in_register": False,
            }
    for slug, row in register.items():
        if slug not in nodes:
            nodes[slug] = {
                "id": slug,
                "name": row.get("name") or slug,
                "domain": row.get("domain") or "",
                "kind": "company",
                "in_register": True,
            }
    subs["nodes"] = list(nodes.values())
    for path in paths:
        write_json(path, subs)


def file_row(probe: dict, src: dict, *, do_enrich: bool = True) -> dict:
    """Probe certs, then run enrich when a first-party public page is on file."""
    certs = []
    url = probe.get("final_url") or probe.get("trust_url")
    if url and probe.get("found"):
        fetched = crawl.fetch(url)
        body = fetched.get("body") or fetched.get("text") or ""
        if isinstance(body, bytes):
            body = body.decode("utf-8", "ignore")
        certs = extract_certs(body)
    rec = to_record(probe, certs, src.get("source") or "expand")
    rec["list"] = src.get("source") or "expand"
    rec["source"] = src.get("source_url") or src.get("source") or "expand"
    if do_enrich and has_public_page(probe):
        rec = enrich.enrich_one(rec)
    return rec


def to_record(probe: dict, certs: list[str], list_name: str) -> dict:
    trust = probe.get("trust_url")
    rec = {
        "rank": None,
        "name": probe["name"],
        "slug": probe["slug"],
        "domain": probe["domain"],
        "found": bool(probe.get("found")),
        "trust_url": trust,
        "final_url": probe.get("final_url") or trust,
        "vendor": "unknown",  # never print on public surfaces
        "title": "",
        "probed": probe.get("probed") or 0,
        "source": probe.get("source") or "expand",
        "summary": "",
        "list": list_name,
        "certs": certs,
        "links": {},
        "subprocessors": [],
    }
    if trust:
        rec["links"]["trust"] = trust
    if certs:
        shown = ", ".join(certs[:6])
        extra = f" +{len(certs)-6}" if len(certs) > 6 else ""
        rec["summary"] = f"Public trust center. On file: {shown}{extra}."
    elif rec["found"]:
        rec["summary"] = "Trust portal found; marks not yet read from the public page."
    else:
        rec["summary"] = "No public trust center found on the usual paths."
    rescore(rec)
    return rec


def is_expand_found_row(row: dict) -> bool:
    """Found page that expand filed and enrich has not yet instrumented."""
    if not has_public_page(row):
        return False
    links = row.get("links") or {}
    extra = [k for k in enrich.INSTRUMENT_LINK_KEYS if links.get(k)]
    if extra or row.get("founded_year") or row.get("subprocessors"):
        return False
    return True


def re_enrich_existing_found(limit: int | None = None) -> dict:
    """Run enrich on existing expand-found rows that still have no instruments."""
    enr = load_json(ENRICHED, {"companies": []})
    targets = [c for c in enr.get("companies") or [] if is_expand_found_row(c)]
    if limit is not None:
        targets = targets[:limit]
    before = {
        "rows": len(targets),
        "with_instrument": 0,
        "with_year": 0,
        "with_processors": 0,
    }
    register = {c["slug"]: c for c in enr.get("companies") or []}
    gained_instrument = []
    new_edges = []
    print(f"Re-enriching {len(targets)} expand-found rows...", flush=True)
    for i, row in enumerate(targets, 1):
        slug = row["slug"]
        try:
            updated = enrich.enrich_one(row, register=register)
        except Exception as exc:
            print(f"  fail {slug}: {exc}", flush=True)
            continue
        new_edges.extend(take_edges(updated))
        idx = next((j for j, c in enumerate(enr["companies"]) if c["slug"] == slug), None)
        if idx is None:
            continue
        enr["companies"][idx] = updated
        register[slug] = updated
        inst = enrich.instrument_links(updated)
        if inst:
            gained_instrument.append(slug)
        print(
            f"  {i}/{len(targets)} {slug:24} inst={list(inst)} "
            f"certs={len(updated.get('certs') or [])} "
            f"procs={len(updated.get('subprocessors') or [])} "
            f"year={updated.get('founded_year') or '-'}",
            flush=True,
        )
    after_targets = [register[c["slug"]] for c in targets if c["slug"] in register]
    after = {
        "rows": len(after_targets),
        "with_instrument": sum(1 for c in after_targets if enrich.instrument_links(c)),
        "with_year": sum(1 for c in after_targets if c.get("founded_year")),
        "with_processors": sum(1 for c in after_targets if c.get("subprocessors")),
    }
    enr["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_json(ENRICHED, enr)
    write_json(SITE_ENRICHED, enr)
    if new_edges:
        merge_processor_edges(new_edges, register)
    print(
        f"expand-found instruments {before['with_instrument']} → {after['with_instrument']} "
        f"(gained {len(gained_instrument)})",
        flush=True,
    )
    return {"before": before, "after": after, "gained": gained_instrument}


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"--re-enrich-found", "--re-enrich"}:
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
        re_enrich_existing_found(limit)
        return 0
    n = BATCH_SIZE
    if len(sys.argv) > 1:
        n = int(sys.argv[1])
    queue = load_json(QUEUE, {"companies": []})
    state = load_json(STATE, {"cursor": 0, "batch_size": BATCH_SIZE})
    batch = next_batch(queue, state, n)
    if not batch:
        print("queue empty")
        write_json(STATE, state)
        return 0
    print(f"Probing {len(batch)} companies...", flush=True)
    probes = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(crawl.probe_company, c): c for c in batch}
        for fut in as_completed(futs):
            row = fut.result()
            probes.append(row)
            print(f"  {'HIT' if row.get('found') else 'miss'} {row['slug']} {row.get('trust_url') or ''}", flush=True)

    records = []
    new_edges = []
    for row in probes:
        src = next((c for c in batch if c["slug"] == row["slug"]), {})
        rec = file_row(row, src)
        new_edges.extend(take_edges(rec))
        records.append(rec)

    enr = load_json(ENRICHED, {"companies": []})
    by = {c["slug"]: i for i, c in enumerate(enr["companies"])}
    added = []
    for rec in records:
        if rec["slug"] in by:
            continue
        rec["rank"] = len(enr["companies"]) + 1
        enr["companies"].append(rec)
        added.append(rec)
    if new_edges:
        merge_processor_edges(new_edges, {c["slug"]: c for c in enr["companies"]})
    enr["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_json(ENRICHED, enr)
    write_json(SITE_ENRICHED, enr)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    write_json(DATA / "render" / f"expand-{stamp}.json", {"batch": "expand", "rows": records})
    state["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["last_added"] = [r["slug"] for r in added]
    state["last_hits"] = [r["slug"] for r in records if r.get("found")]
    write_json(STATE, state)
    write_json(QUEUE, queue)
    print(f"added {len(added)}  hits {sum(1 for r in records if r.get('found'))}/{len(records)}")
    for r in added:
        d = r.get("disclosure") or {}
        print(f"  {r['slug']:24} {d.get('tier','?'):12} certs={len(r.get('certs') or [])} {r.get('trust_url') or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
