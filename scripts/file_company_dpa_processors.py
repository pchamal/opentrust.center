#!/usr/bin/env python3
"""Fill missing DPA and named subprocessors on the next ~40 on-file companies.

First-party only. Fetch-check. Do not invent. When unsure, leave open.
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import enrich  # noqa: E402

SITE = ROOT / "site"
DATA = ROOT / "data"
PUBLIC = SITE / "data.json"
ENRICHED = SITE / "data" / "enriched.json"
REPORT = DATA / "render" / "company-dpa-processors.json"
BATCH = 40
WORKERS = 12
# Companies already attempted in PR 47. Do not retry this cut.
# The live report holds the immediately previous batch (PR 48); PR 47 is listed
# here because that report was overwritten.
PRIOR_ATTEMPTED = {
    "palo-alto-networks",
    "dropbox",
    "motive",
    "clickup",
    "alteryx",
    "cvent",
    "dynatrace",
    "amazon-web-services",
    "cloudera",
    "automation-anywhere",
    "splunk",
    "asana",
    "calendly",
    "dataiku",
    "sierra",
    "checkr",
    "varonis",
    "workday",
    "grammarly",
    "slack",
    "airwallex",
    "clickhouse",
    "scale-ai",
    "cohere",
    "infor",
    "automattic",
    "checkout",
    "canva",
    "hubspot",
    "vertex",
    "elastic",
    "monday",
    "samsara",
    "notion",
    "shopify",
    "carta",
    "papaya-global",
    "lambda",
    "cornerstone-ondemand",
    "fortinet",
}


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def instrument_url(row: dict, key: str) -> str:
    rec = (row.get("instruments") or {}).get(key) or {}
    if isinstance(rec, dict):
        return (rec.get("url") or "").strip()
    return str(rec or "").strip()


def first_party_candidates(public: dict, enr: dict) -> list[tuple[str, str]]:
    """URLs already on the file that we may read. Portal hosts stay out."""
    out, seen = [], set()

    def add(kind: str, url: str) -> None:
        u = (url or "").strip()
        if not u.startswith("http"):
            return
        key = u.lower()
        if key in seen:
            return
        if not enrich.is_first_party_url(u, enr):
            return
        seen.add(key)
        out.append((kind, u))

    links = enr.get("links") or {}
    for kind in ("trust", "security", "privacy", "dpa", "subprocessors"):
        add(kind, links.get(kind) or "")
    add("trust_url", public.get("trust_url") or "")
    add("final_url", public.get("final_url") or "")
    add("enr_trust", enr.get("trust_url") or "")
    add("enr_final", enr.get("final_url") or "")
    for key in ("trust", "security", "privacy", "dpa", "subprocessors"):
        add(key, instrument_url(public, key))
    return out


def previous_batch() -> set[str]:
    """Skip companies already attempted on the last increment. Do not retry them."""
    prior = {slug for slug in (load_json(REPORT, {}).get("batch") or []) if slug}
    prior.update(PRIOR_ATTEMPTED)
    return prior


def select_batch(public_rows: list[dict], enr_by: dict[str, dict]) -> list[dict]:
    skip = previous_batch()
    picked = []
    for row in public_rows:
        if not row.get("found"):
            continue
        slug = row.get("slug") or ""
        if slug in skip:
            continue
        enr = enr_by.get(slug)
        if not enr:
            continue
        dpa_open = not instrument_url(row, "dpa")
        sub_open = not (row.get("processors") or instrument_url(row, "subprocessors"))
        if not (dpa_open or sub_open):
            continue
        cands = first_party_candidates(row, enr)
        if not cands:
            continue
        picked.append({
            "slug": slug,
            "name": row.get("name") or slug,
            "dpa_open": dpa_open,
            "sub_open": sub_open,
            "candidates": cands,
        })
        if len(picked) >= BATCH:
            break
    return picked


def fetch_seed(url: str) -> dict:
    try:
        return enrich.fetch_seed_page(url)
    except Exception:
        return {"ok": False, "status": 0, "final_url": url, "hrefs": [], "html": "", "title": "", "text": ""}


def fetch_verify(url: str, *, list_page: bool) -> dict:
    try:
        if list_page:
            return enrich.fetch_processor_page(url)
        body = enrich.TRUST_BODY if str(url).lower().endswith(".pdf") else enrich.PROBE_BODY
        return enrich.fetch_uncached(url, body)
    except Exception:
        return {"ok": False, "status": 0, "final_url": url, "title": "", "text": "", "html": "", "ctype": ""}


def append_processor_edges(edges: list[dict], register: dict[str, dict]) -> None:
    """Append sourced edges and only the nodes those edges name. Do not dump the register."""
    paths = (DATA / "subprocessors.json", SITE / "data" / "subprocessors.json")
    src = paths[0] if paths[0].exists() else paths[1]
    subs = load_json(src, {"nodes": [], "edges": []})
    nodes = {n["id"]: n for n in (subs.get("nodes") or []) if n.get("id")}
    existing = {(e.get("from"), e.get("to")) for e in (subs.get("edges") or [])}
    proc_meta = {i: (n, d) for i, n, d, _a in enrich.PROCESSORS}
    for e in edges:
        src_url, frm, to = e.get("source_url"), e.get("from"), e.get("to")
        if not src_url or not frm or not to or (frm, to) in existing:
            continue
        subs.setdefault("edges", []).append({
            "from": frm,
            "to": to,
            "source_url": src_url,
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
        if frm not in nodes and frm in register:
            nodes[frm] = {
                "id": frm,
                "name": register[frm].get("name") or frm,
                "domain": register[frm].get("domain") or "",
                "kind": "company",
                "in_register": True,
            }
    subs["nodes"] = list(nodes.values())
    for path in paths:
        write_json(path, subs)


def public_url(url: str) -> str:
    """Drop login tokens and itemUids from the reject ledger."""
    u = (url or "").split("#")[0].strip()
    if "itemUid=" in u or "inviteToken=" in u or "loginRequest=" in u:
        return u.split("?", 1)[0]
    return u


def uniq_urls(urls: list[str]) -> list[str]:
    out, seen = [], set()
    for u in urls:
        key = (u or "").rstrip("/").lower()
        if not key.startswith("http") or key in seen:
            continue
        seen.add(key)
        out.append(u)
    return out


def main() -> int:
    t0 = time.time()
    public = load_json(PUBLIC, {})
    enr = load_json(ENRICHED, {})
    public_rows = list(public.get("companies") or [])
    companies = list(enr.get("companies") or [])
    enr_by = {c["slug"]: c for c in companies if c.get("slug")}
    register = {c["slug"]: c for c in companies if c.get("slug")}

    batch = select_batch(public_rows, enr_by)
    print(f"batch {len(batch)} companies with an open DPA or subprocessors rule", flush=True)
    for rec in batch:
        print(
            f"  {rec['slug']} dpa_open={rec['dpa_open']} sub_open={rec['sub_open']} "
            f"urls={len(rec['candidates'])}",
            flush=True,
        )

    seed_jobs = []
    seen_seed = set()
    for rec in batch:
        row = enr_by[rec["slug"]]
        for kind, url in rec["candidates"]:
            key = (rec["slug"], url.lower())
            if key in seen_seed:
                continue
            seen_seed.add(key)
            seed_jobs.append((rec["slug"], kind, url))

    print(f"phase 1: read {len(seed_jobs)} on-file first-party pages", flush=True)
    dpa_cands: dict[str, list[str]] = {rec["slug"]: [] for rec in batch if rec["dpa_open"]}
    sub_cands: dict[str, list[str]] = {rec["slug"]: [] for rec in batch if rec["sub_open"]}
    rejected: list[dict] = []

    def take_dpa(slug: str, url: str) -> None:
        bucket = dpa_cands.get(slug)
        if bucket is None:
            return
        if url not in bucket:
            bucket.append(url)

    def take_sub(slug: str, url: str) -> None:
        bucket = sub_cands.get(slug)
        if bucket is None:
            return
        if url not in bucket:
            bucket.append(url)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(fetch_seed, url): (slug, kind, url) for slug, kind, url in seed_jobs}
        done = 0
        for fut in as_completed(futs):
            slug, kind, url = futs[fut]
            rec = fut.result()
            done += 1
            if done % 20 == 0 or done == len(futs):
                print(f"  seed {done}/{len(futs)}", flush=True)
            row = enr_by.get(slug)
            if not row:
                continue
            final = rec.get("final_url") or url
            if rec.get("ok") and rec.get("status") == 200 and enrich.is_first_party_url(final, row):
                html = rec.get("html") or ""
                base = final
                if slug in dpa_cands:
                    for href in enrich.extract_dpa_candidates(html, base):
                        if enrich.is_first_party_url(href, row):
                            take_dpa(slug, href)
                    for href in rec.get("hrefs") or []:
                        if enrich.DPA_PATH_RE.search(href) and enrich.is_first_party_url(href, row):
                            take_dpa(slug, href)
                    if kind == "dpa":
                        take_dpa(slug, final)
                if slug in sub_cands:
                    for href in enrich.extract_subprocessor_candidates(html, base):
                        if enrich.is_first_party_url(href, row):
                            take_sub(slug, href)
                    if kind == "subprocessors":
                        take_sub(slug, final)
            elif kind in {"dpa", "subprocessors"}:
                rejected.append({"slug": slug, "url": public_url(url), "reason": "seed-not-live", "kind": kind})

    for rec in batch:
        row = enr_by[rec["slug"]]
        if rec["dpa_open"] and not dpa_cands.get(rec["slug"]):
            for url in enrich.dpa_probe_urls_for(row):
                if enrich.is_first_party_url(url, row):
                    take_dpa(rec["slug"], url)
        if rec["sub_open"] and not sub_cands.get(rec["slug"]):
            for url in enrich.subprocessor_probe_urls_for(row):
                if enrich.is_first_party_url(url, row):
                    take_sub(rec["slug"], url)

    dpa_jobs, sub_jobs = [], []
    for slug, urls in dpa_cands.items():
        row = enr_by[slug]
        for url in uniq_urls(urls):
            if enrich.is_first_party_url(url, row):
                dpa_jobs.append((slug, url))
    for slug, urls in sub_cands.items():
        row = enr_by[slug]
        for url in uniq_urls(urls):
            if enrich.is_first_party_url(url, row):
                sub_jobs.append((slug, url))

    print(f"phase 2: verify {len(dpa_jobs)} DPA candidates, {len(sub_jobs)} list candidates", flush=True)
    accepted_dpa: dict[str, str] = {}
    accepted_sub: dict[str, tuple[str, list]] = {}

    def do_dpa(job):
        slug, url = job
        rec = fetch_verify(url, list_page=False)
        return slug, url, rec

    def do_sub(job):
        slug, url = job
        rec = fetch_verify(url, list_page=True)
        return slug, url, rec

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(do_dpa, job) for job in dpa_jobs]
        done = 0
        for fut in as_completed(futs):
            slug, url, rec = fut.result()
            done += 1
            if done % 20 == 0 or done == len(futs):
                print(f"  dpa {done}/{len(futs)}", flush=True)
            if slug in accepted_dpa:
                continue
            row = enr_by.get(slug)
            if not row:
                continue
            final = rec.get("final_url") or url
            if not enrich.is_first_party_url(final, row):
                rejected.append({"slug": slug, "url": public_url(url), "final": public_url(final), "reason": "not-first-party", "kind": "dpa"})
                continue
            if not enrich.classify_as_dpa(url, rec):
                reason = "not-a-dpa"
                if not rec.get("ok") or rec.get("status") != 200:
                    reason = f"http-{rec.get('status') or 0}"
                elif enrich.looks_like_login_wall(rec.get("title") or "", rec.get("text") or ""):
                    reason = "login-wall"
                elif enrich.looks_dead(rec.get("title") or "", rec.get("text") or ""):
                    reason = "soft-404"
                elif enrich.landed_on_home(url, final):
                    reason = "homepage-bounce"
                rejected.append({"slug": slug, "url": public_url(url), "final": public_url(final), "reason": reason, "kind": "dpa"})
                continue
            accepted_dpa[slug] = final

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(do_sub, job) for job in sub_jobs]
        done = 0
        for fut in as_completed(futs):
            slug, url, rec = fut.result()
            done += 1
            if done % 20 == 0 or done == len(futs):
                print(f"  sub {done}/{len(futs)}", flush=True)
            if slug in accepted_sub:
                continue
            row = enr_by.get(slug)
            if not row:
                continue
            final = rec.get("final_url") or url
            skip = enrich.cited_list_skip_reason(url, rec, row)
            if skip:
                rejected.append({"slug": slug, "url": public_url(url), "final": public_url(final), "reason": skip, "kind": "subprocessors"})
                continue
            procs = enrich.published_processors_from_cited(row, rec, url, register)
            if not procs:
                rejected.append({"slug": slug, "url": public_url(url), "final": public_url(final), "reason": "no-printed-names", "kind": "subprocessors"})
                continue
            dated = [n for _i, n, _e in procs if enrich.looks_like_date_name(n)]
            procs = [(i, n, e) for i, n, e in procs if not enrich.looks_like_date_name(n)]
            if dated:
                rejected.append({"slug": slug, "url": public_url(url), "reason": "date-shaped-names", "kind": "subprocessors", "dropped": dated})
            if not procs:
                rejected.append({"slug": slug, "url": public_url(url), "reason": "only-dates", "kind": "subprocessors"})
                continue
            accepted_sub[slug] = (final, procs)

    filed_dpa, filed_sub = [], []
    new_edges = []
    for slug, url in sorted(accepted_dpa.items()):
        row = enr_by[slug]
        if enrich.apply_dpa_to_row(row, url):
            filed_dpa.append({"slug": slug, "name": row.get("name") or slug, "url": url})

    for slug, (url, procs) in sorted(accepted_sub.items()):
        row = enr_by[slug]
        enrich.apply_subprocessors_to_row(row, url)
        row["subprocessors"] = [pid for pid, _n, _e in procs]
        filed_sub.append({
            "slug": slug,
            "name": row.get("name") or slug,
            "url": url,
            "names": [n for _i, n, _e in procs],
        })
        for pid, name, ev in procs:
            new_edges.append({
                "from": slug,
                "to": pid,
                "source_url": url,
                "evidence": ev or name,
            })

    if new_edges:
        append_processor_edges(new_edges, register)

    write_json(ENRICHED, enr)
    write_json(DATA / "enriched.json", enr)

    stayed = []
    for rec in batch:
        dpa_filed = any(x["slug"] == rec["slug"] for x in filed_dpa)
        sub_filed = any(x["slug"] == rec["slug"] for x in filed_sub)
        if rec["dpa_open"] and not dpa_filed:
            stayed.append({"slug": rec["slug"], "name": rec["name"], "rule": "dpa"})
        if rec["sub_open"] and not sub_filed:
            stayed.append({"slug": rec["slug"], "name": rec["name"], "rule": "subprocessors"})

    report = {
        "generated_at": enr.get("generated_at"),
        "rule": (
            "Next ~40 on-file companies whose DPA or subprocessors rule was open "
            "and who already had a first-party public URL. DPA fills only from a "
            "real first-party DPA. Named subprocessors fill only from a printed "
            "first-party list of organization names. Dates, JS shells, login walls, "
            "and portal hosts stay open."
        ),
        "batch": [rec["slug"] for rec in batch],
        "dpa_filed": filed_dpa,
        "subprocessors_filed": filed_sub,
        "stayed_open": stayed,
        "rejected": rejected,
    }
    write_json(REPORT, report)

    print(f"filed dpa={len(filed_dpa)} named-subprocessors={len(filed_sub)} "
          f"stayed={len(stayed)} rejected={len(rejected)} in {time.time() - t0:.1f}s", flush=True)
    for row in filed_dpa:
        print(f"  + dpa {row['slug']} {row['url']}", flush=True)
    for row in filed_sub:
        print(f"  + sub {row['slug']} {len(row['names'])} {row['url']}", flush=True)
    for row in stayed:
        print(f"  - open {row['slug']} {row['rule']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
