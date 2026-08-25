#!/usr/bin/env python3
"""Fill missing founded years on the next ~40 on-file companies.

Official-site years only. Fetch-check. Do not invent. When unsure, leave open.
Wikipedia, news articles, and title-only prefix matches stay off file.
Reuses enrich.py year law — does not fork a parser.
"""
from __future__ import annotations

import json
import re
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
# Companies already attempted in earlier years cuts. Do not retry.
# The live report holds the last increment; older PRs are listed here
# because those reports were overwritten.
PRIOR_ATTEMPTED = {
    # PR 63 — register walk; three first-party years filed
    "checkr",
    "fireworks-ai",
    "harvey",
    "honeycomb",
    "writer",
    "pendo",
    "vertex",
    "clay",
    "claroty",
    "dbt-labs",
    "weave",
    "cs-disco",
    "lambda",
    "benchling",
    "expel",
    "komodo-health",
    "lever",
    "megaport",
    "baseten",
    "island",
    "saviynt",
    "wiz",
    "homebase",
    "bench-accounting",
    "doubleverify",
    "deepwatch",
    "nice",
    "abridge",
    "evenup",
    "abbyy",
    "armis",
    "axonius",
    "exabeam",
    "five9",
    "red-canary",
    "collibra",
    "ironscales",
    "talkdesk",
    "canto-software",
    "certinia",
    # PR 73 — Wikipedia security/cloud names; four first-party years filed
    "privatecore",
    "optenet",
    "optiv",
    "nowsecure",
    "nec",
    "mocana",
    "nomura-research-institute",
    "mitsui-knowledge-industry",
    "pine64",
    "sendio",
    "prolexic-technologies",
    "threatconnect",
    "sony-global-solutions",
    "tiversa",
    "onelogin",
    "uniadex",
    "tufin",
    "venafi",
    "zerodium",
    "penta-security",
    "glow",
    "web-sheriff",
    "secunet-security-networks",
    "identiv",
    "titanfile",
    "yeswehack",
    "nyotron",
    "group-ib",
    "mandiant",
    "panorays",
    "kerio-technologies",
    "deflect-ca",
    "pc-tools",
    "stonesoft-corporation",
    "vmware-carbon-black",
    "riskiq",
    "trusteer",
    "anomali",
    "cyber-intelligence-house",
    "datagravity",
    # PR 84 — next 40 register walk; nothing first-party printed
    "deputy",
    "cognite",
    "blackbaud",
    # PR 98 — 24 Aug expand six; Faculty year 2014 already on file
    "aveva",
    "bromcom",
    "faculty",
    "kraken-technologies",
    "activestate",
    "altus-group",
    # PR 104 — 24 Aug 19:48 expand three; do not retry
    "intrahealth-systems-limited",
    "prontoforms",
    "versapay",
    # this cut — next 40 open years files
    "dashlane",
    "openevidence",
    "snorkel-ai",
    "kentik",
    "constellation-energy",
    "ninjaone",
    "par-technology",
    "certara",
    "eagle-eye-solutions",
    "boomi-lp",
    "huntress",
    "viant-technology",
    "zerotier",
    "decagon",
    "insightly",
    "grafana-labs",
    "salt-security",
    "activeops",
    "airship",
    "bluevoyant",
    "corelight",
    "fluid-attacks",
    "honeybook",
    "agora",
    "xylem-inc",
    "coactive-ai",
    "trusona",
    "aptitude-software",
    "crusoe",
    "docebo",
    "energycap",
    "esentire",
    "langchain",
    "appian",
    "indinero",
    "forescout",
    "luminance",
    "domo",
    "avepoint",
    "expensify",
}


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
    """Skip companies already attempted on earlier increments. Do not retry them."""
    prior = {slug for slug in (load_json(REPORT, {}).get("batch") or []) if slug}
    prior.update(PRIOR_ATTEMPTED)
    return prior


def select_batch(public_rows: list[dict], enr_by: dict[str, dict]) -> list[dict]:
    wanted = requested_slugs()
    skip = set() if wanted else previous_batch()
    by_pub = {row.get("slug"): row for row in public_rows if row.get("slug")}
    rows = [by_pub[s] for s in wanted if s in by_pub] if wanted else public_rows
    picked = []
    for row in rows:
        # Register walk stays on-file (trust portal found). Requested slugs
        # may be silent: a first-party about page can still name a year.
        if not wanted and not row.get("found"):
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


def stored_year_urls(public: dict, enr: dict) -> list[str]:
    """Wikipedia company pages, About, or other public pages already on file."""
    out, seen = [], set()

    def add(url: str) -> None:
        u = public_url(url)
        if not u.startswith("http"):
            return
        key = u.lower().rstrip("/")
        if key in seen:
            return
        seen.add(key)
        out.append(u)

    for raw in (
        public.get("source"),
        public.get("source_url"),
        enr.get("source"),
        enr.get("source_url"),
        public.get("founded_source"),
        enr.get("founded_source"),
    ):
        add(raw or "")
    links = enr.get("links") or {}
    for key in ("about", "company", "press", "newsroom"):
        add(links.get(key) or "")
    return out


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


def inspect_official_year(
    company: dict,
    extra_urls: list[str] | None = None,
) -> tuple[tuple[int, str] | None, list[dict]]:
    """Same walk as enrich.resolve_official_year, with reject notes."""
    jobs = []
    seen: set[str] = set()
    for url in list(extra_urls or []) + enrich.about_urls_for(company):
        key = (url or "").lower()
        if not key.startswith("http") or key in seen:
            continue
        seen.add(key)
        jobs.append(url)
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


def year_quote(text: str, year: int, company_name: str = "") -> str:
    """Short live-page sentence that names the filed year. Empty if none."""
    if not text or not year:
        return ""
    needle = str(year)
    for raw in (text or "").split("."):
        bit = " ".join(raw.split())
        if needle not in bit:
            continue
        if not re.search(r"\b(?:founded|established|foundingDate)\b", bit, re.I):
            continue
        if len(bit) > 220:
            i = bit.find(needle)
            bit = bit[max(0, i - 80): i + 80].strip()
        return bit.strip(" .;,:") + "."
    return ""


def patch_public_row(pub: dict, enr_row: dict) -> None:
    """Copy a newly filed year onto the public row. Leave other instruments."""
    year = enr_row.get("founded_year")
    source = enr_row.get("founded_source")
    if not year or not source:
        return
    pub["founded_year"] = year
    pub["founded_source"] = source
    disc = dict(pub.get("disclosure") or {})
    factors = dict(disc.get("factors") or {})
    enr_factors = ((enr_row.get("disclosure") or {}).get("factors") or {})
    pts = int(enr_factors.get("longevity") or enr_factors.get("years") or 0)
    if pts and not factors.get("years"):
        factors["years"] = pts
        disc["factors"] = factors
        disc["score"] = min(100, int(disc.get("score") or 0) + pts)
        pub["disclosure"] = disc
    file_flags = dict(pub.get("file") or {})
    file_flags["years"] = 20
    pub["file"] = file_flags


def patch_dossier(slug: str, year: int, source: str) -> bool:
    """Light HTML patch: years glyph on, founded line filled. No chrome remake."""
    path = SITE / "c" / f"{slug}.html"
    if not path.exists():
        return False
    html = path.read_text(encoding="utf-8")
    src = public_url(source)
    founded = (
        f'<p class="ident-meta">founded · {int(year)} · '
        f'<a href="{src}">source</a></p>'
    )
    html, n = re.subn(
        r'<p class="ident-meta">founded · <span class="absent">not on file</span></p>',
        founded,
        html,
        count=1,
    )
    if not n:
        return False

    def _on_years(match: re.Match) -> str:
        label = match.group("label") or ""
        if "years" not in label:
            label = "years" if label == "not on file" else f"{label} · years"
        parts = re.findall(
            r'<span class="file-rule[^"]*" aria-hidden="true"></span>',
            match.group("rules") or "",
        )
        if len(parts) != 5:
            return match.group(0)
        parts[4] = '<span class="file-rule on" aria-hidden="true"></span>'
        return (
            f'<span class="file-index" role="img" aria-label="{label}">'
            f'{"".join(parts)}</span>'
        )

    html, m = re.subn(
        r'<span class="file-index" role="img" aria-label="(?P<label>[^"]*)">'
        r'(?P<rules>(?:<span class="file-rule[^"]*" aria-hidden="true"></span>){5})</span>',
        _on_years,
        html,
        count=1,
    )
    if not m:
        return False
    path.write_text(html, encoding="utf-8")
    return True


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

    by_pub = {row.get("slug"): row for row in public_rows if row.get("slug")}

    def do_one(rec: dict):
        row = enr_by.get(rec["slug"])
        if not row:
            return rec["slug"], None, []
        extra = stored_year_urls(by_pub.get(rec["slug"]) or {}, row)
        try:
            return rec["slug"], *inspect_official_year(row, extra)
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
        rec = enrich.fetch_cached(source, max_body=enrich.TRUST_BODY)
        blob = " ".join(filter(None, [rec.get("title") or "", rec.get("meta") or "", rec.get("text") or ""]))
        quote = year_quote(blob, year, row.get("name") or "")
        pub = by_pub.get(slug)
        if pub:
            patch_public_row(pub, row)
        if not patch_dossier(slug, year, source):
            rejected.append({
                "slug": slug,
                "url": source,
                "reason": "dossier-patch-missed",
                "year": year,
            })
        filed.append({
            "slug": slug,
            "name": row.get("name") or slug,
            "year": year,
            "url": source,
            "quote": quote,
        })

    if filed:
        write_json(ENRICHED, enr)
        write_json(DATA / "enriched.json", enr)
        write_json(PUBLIC, public)

    reason_rank = {
        "no-founded-sentence": 1,
        "wikipedia": 2,
        "prefix-match": 3,
        "news": 4,
        "third-party": 5,
        "not-official": 6,
        "website-mismatch": 7,
        "soft-404": 8,
        "404": 9,
        "apply-rejected": 0,
        "conflicting-years": 0,
    }

    def stay_reason(slug: str) -> str:
        notes = [n for n in rejected if n.get("slug") == slug]
        if not notes:
            return "no live founded sentence"
        notes.sort(key=lambda n: reason_rank.get(n.get("reason") or "", 10))
        top = notes[0]
        why = top.get("reason") or "stayed-open"
        url = top.get("final") or top.get("url") or ""
        return f"{why} {url}".strip()

    stayed = []
    for rec in batch:
        if any(x["slug"] == rec["slug"] for x in filed):
            continue
        stayed.append({
            "slug": rec["slug"],
            "name": rec["name"],
            "rule": "years",
            "reason": stay_reason(rec["slug"]),
        })

    report = {
        "generated_at": enr.get("generated_at"),
        "rule": (
            "Next ~40 on-file companies whose years File-glyph rule was open "
            "and who already had a stored Wikipedia company page, About, or "
            "other first-party/public page. A year fills only when that live "
            "page names the company's founding year. Wikipedia category/list "
            "pages, news articles, title-only prefix matches, and 404s stay "
            "open. Prior year cuts and PR 104 are on the skip list."
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
