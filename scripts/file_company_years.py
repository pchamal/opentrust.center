#!/usr/bin/env python3
"""Fill missing founded years on the next ~40 on-file companies.

Official-site years only. Fetch-check. Do not invent. When unsure, leave open.
Wikipedia, news articles, and title-only prefix matches stay off file.
Reuses enrich.py year law — does not fork a parser.
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
from enrich import (  # noqa: E402
    apply_year_to_row,
    is_news_article_url,
    is_official_year_source,
    parse_official_founded_year,
    title_close,
    website_matches,
)

SITE = ROOT / "site"
DATA = ROOT / "data"
PUBLIC = SITE / "data.json"
ENRICHED = SITE / "data" / "enriched.json"
REPORT = DATA / "render" / "company-years.json"
BATCH = 40
WORKERS = 8


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def public_url(url: str) -> str:
    return (url or "").split("#")[0].strip()


def requested_slugs() -> list[str]:
    """Optional argv slugs. Empty means the next ~40 open years files."""
    return [a.strip() for a in sys.argv[1:] if a.strip() and not a.startswith("-")]


def previous_batch() -> set[str]:
    """Skip companies already attempted on the last increment. Do not retry them."""
    return {slug for slug in (load_json(REPORT, {}).get("batch") or []) if slug}


def select_batch(public_rows: list[dict], enr_by: dict[str, dict]) -> list[dict]:
    wanted = requested_slugs()
    skip = set() if wanted else previous_batch()
    by_pub = {row.get("slug"): row for row in public_rows if row.get("slug")}
    rows = [by_pub[s] for s in wanted if s in by_pub] if wanted else public_rows
    picked = []
    for row in rows:
        if not row.get("found"):
            continue
        slug = row.get("slug") or ""
        if slug in skip:
            continue
        enr = enr_by.get(slug)
        if not enr:
            continue
        if row.get("founded_year") or enr.get("founded_year"):
            continue
        if not enrich.has_official_domain(enr) and not enrich.has_official_domain(row):
            continue
        picked.append({
            "slug": slug,
            "name": row.get("name") or enr.get("name") or slug,
            "domain": row.get("domain") or enr.get("domain") or "",
        })
        if not wanted and len(picked) >= BATCH:
            break
    return picked[:BATCH] if not wanted else picked


def reject_host_reason(url: str, company_name: str = "") -> str | None:
    h = enrich.host_of(url) or ""
    if "wikipedia.org" in h or "wikidata.org" in h:
        wiki_title = (url.rsplit("/", 1)[-1] or "").replace("_", " ")
        if company_name and wiki_title and not title_close(wiki_title, company_name):
            return "prefix-match"
        return "wikipedia"
    if enrich.is_third_party_year_host(url):
        return "third-party"
    if is_news_article_url(url):
        return "news"
    return None


def inspect_official_year(company: dict) -> tuple[tuple[int, str] | None, list[dict]]:
    """Same walk as enrich.resolve_official_year, with reject notes."""
    jobs = enrich.about_urls_for(company)
    seen = {u.lower() for u in jobs}
    found: list[tuple[int, str]] = []
    rejected: list[dict] = []
    i = 0
    while i < len(jobs) and i < 24:
        url = jobs[i]
        i += 1
        rec = enrich.fetch_cached(url, max_body=enrich.TRUST_BODY)
        final = rec.get("final_url") or url
        status = rec.get("status") or 0
        name = company.get("name") or ""
        skip = reject_host_reason(url, name) or reject_host_reason(final, name)
        if skip:
            rejected.append({
                "slug": company.get("slug"),
                "url": public_url(url),
                "final": public_url(final),
                "reason": skip,
            })
            continue
        if not rec.get("ok") or status != 200:
            rejected.append({
                "slug": company.get("slug"),
                "url": public_url(url),
                "final": public_url(final),
                "reason": "404" if status == 404 else f"http-{status}",
            })
            continue
        title, text = rec.get("title") or "", rec.get("text") or ""
        if enrich.looks_dead(title, text):
            rejected.append({
                "slug": company.get("slug"),
                "url": public_url(url),
                "final": public_url(final),
                "reason": "soft-404",
            })
            continue
        hosts = enrich.hosts_for(company)
        if not website_matches([final], hosts):
            rejected.append({
                "slug": company.get("slug"),
                "url": public_url(url),
                "final": public_url(final),
                "reason": "website-mismatch",
            })
            continue
        if not is_official_year_source(final, company):
            rejected.append({
                "slug": company.get("slug"),
                "url": public_url(url),
                "final": public_url(final),
                "reason": "not-official",
            })
            continue
        blob = " ".join(filter(None, [title, rec.get("meta") or "", text]))
        year = parse_official_founded_year(blob, company.get("name") or "")
        if year:
            found.append((year, final))
        else:
            rejected.append({
                "slug": company.get("slug"),
                "url": public_url(url),
                "final": public_url(final),
                "reason": "no-founded-sentence",
            })
        if len(jobs) >= 24:
            continue
        for extra in enrich.year_follow_urls(rec, company):
            if extra.lower() in seen:
                continue
            seen.add(extra.lower())
            jobs.append(extra)
            if len(jobs) >= 24:
                break
    if not found:
        return None, rejected
    years = {y for y, _s in found}
    if len(years) != 1:
        rejected.append({
            "slug": company.get("slug"),
            "url": public_url(found[0][1]),
            "reason": "conflicting-years",
            "years": sorted(years),
        })
        return None, rejected
    year, source = found[0]
    return (year, enrich.canon_source_url(source)), rejected


def main() -> int:
    t0 = time.time()
    public = load_json(PUBLIC, {})
    enr = load_json(ENRICHED, {})
    public_rows = list(public.get("companies") or [])
    companies = list(enr.get("companies") or [])
    enr_by = {c["slug"]: c for c in companies if c.get("slug")}

    batch = select_batch(public_rows, enr_by)
    print(f"batch {len(batch)} on-file companies with an open years rule", flush=True)
    for rec in batch:
        print(f"  {rec['slug']} {rec['domain']}", flush=True)

    accepted: dict[str, tuple[int, str]] = {}
    rejected: list[dict] = []

    def do_one(rec: dict):
        row = enr_by.get(rec["slug"])
        if not row:
            return rec["slug"], None, []
        try:
            return rec["slug"], *inspect_official_year(row)
        except Exception as exc:
            return rec["slug"], None, [{
                "slug": rec["slug"],
                "url": "",
                "reason": f"error:{exc.__class__.__name__}",
            }]

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(do_one, rec) for rec in batch]
        done = 0
        for fut in as_completed(futs):
            slug, hit, notes = fut.result()
            done += 1
            if done % 5 == 0 or done == len(futs):
                print(f"  checked {done}/{len(futs)}", flush=True)
            rejected.extend(notes)
            if hit:
                accepted[slug] = hit

    filed = []
    for slug, (year, source) in sorted(accepted.items()):
        row = enr_by[slug]
        if not apply_year_to_row(row, year, source):
            rejected.append({
                "slug": slug,
                "url": source,
                "reason": "apply-rejected",
                "year": year,
            })
            continue
        filed.append({
            "slug": slug,
            "name": row.get("name") or slug,
            "year": year,
            "url": source,
        })

    write_json(ENRICHED, enr)
    write_json(DATA / "enriched.json", enr)

    stayed = []
    for rec in batch:
        if any(x["slug"] == rec["slug"] for x in filed):
            continue
        stayed.append({
            "slug": rec["slug"],
            "name": rec["name"],
            "rule": "years",
        })

    report = {
        "generated_at": enr.get("generated_at"),
        "rule": (
            "Next ~40 on-file companies whose years File-glyph rule was open "
            "and who already had an official domain. A year fills only from a "
            "first-party about / company / history page that states founded or "
            "established. Wikipedia, news articles, title-only prefix matches, "
            "and 404s stay open."
        ),
        "batch": [rec["slug"] for rec in batch],
        "years_filed": filed,
        "stayed_open": stayed,
        "rejected": rejected,
    }
    write_json(REPORT, report)

    print(
        f"filed years={len(filed)} stayed={len(stayed)} rejected={len(rejected)} "
        f"in {time.time() - t0:.1f}s",
        flush=True,
    )
    for row in filed:
        print(f"  + years {row['slug']} {row['year']} {row['url']}", flush=True)
    for row in stayed:
        print(f"  - open {row['slug']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
