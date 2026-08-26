#!/usr/bin/env python3
"""Walk Completeness-0 companies from domain (+ official_url).

Completeness is the sum of five 0/10/20 file rules (page · marks · DPA ·
subprocessors · years). A 0 today is almost never a verified absence — most
are usual-path misses or unwalked AITI inserts (probed==0, official_url
homepage). Existing file_company_* walkers skip rows with no stored candidate
URL, so they never touch these domain-only files.

Reuse crawl.candidate_urls / crawl.probe_company / enrich.fetch_seed_page /
file_company_* reject_reason / marks extract / DPA+processor harvest /
founded-year parse. Do not invent parsers, companies, or certs.

Default is dry-run: write only data/render/empty-file-audit.json.
--apply files fetch-checked first-party holds through existing apply_*.
Never overwrite a verified fill. Never name a portal vendor (Official page).
403 / 429 / SPA / portal stay unreadable, not an honest zero.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import crawl  # noqa: E402
import enrich  # noqa: E402
from file_company_dpa_processors import append_processor_edges  # noqa: E402
from file_company_marks import (  # noqa: E402
    ASSET_URL_RE,
    COMPLIANCE_URL_RE,
    ITEM_UID_RE,
    hold_marks,
    mark_quote,
    public_url,
)
from file_company_years import year_quote  # noqa: E402
from marks import extract_certs_from_html, mark_blob  # noqa: E402
from merge_render import rescore  # noqa: E402

SITE = ROOT / "site"
DATA = ROOT / "data"
PUBLIC = SITE / "data.json"
ENRICHED = SITE / "data" / "enriched.json"
REPORT = DATA / "render" / "empty-file-audit.json"
WORKERS = 12
FILE_KEYS = ("page", "marks", "dpa", "subprocessors", "years")
UNREADABLE = {
    "http-0",
    "http-401",
    "http-403",
    "http-429",
    "http-500",
    "http-502",
    "http-503",
    "js-shell|login-wall",
    "portal-host",
}
FOLLOW_CAP = 20
PORTAL_VENDORS = {
    "vanta", "safebase", "drata", "securitypal", "conveyor",
    "whistic", "secureframe", "trustcloud", "wolfia", "sprinto",
}


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def parse_args(argv: list[str] | None = None) -> dict:
    argv = list(sys.argv[1:] if argv is None else argv)
    flags = {a for a in argv if a.startswith("-")}
    slugs = [a.strip() for a in argv if a.strip() and not a.startswith("-")]
    unknown = sorted(flags - {"--unwalked", "--apply"})
    if unknown:
        raise SystemExit(f"unknown flag: {unknown[0]}")
    return {
        "unwalked": "--unwalked" in flags,
        "apply": "--apply" in flags,
        "slugs": slugs,
    }


def file_sum(row: dict) -> int:
    """Completeness = sum of five 0/10/20 file rules. Not disclosure.score."""
    flags = row.get("file") or {}
    return sum(int(flags.get(k) or 0) for k in FILE_KEYS)


def probed_of(public: dict, enr: dict) -> int:
    raw = public.get("probed")
    if raw is None:
        raw = enr.get("probed")
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


def walk_company(public: dict, enr: dict) -> dict:
    """Company dict the walkers already understand, plus official_url host."""
    row = dict(enr)
    official = (public.get("official_url") or enr.get("official_url") or "").strip()
    if official.startswith(("http://", "https://")):
        row["official_url"] = official
        host = enrich.host_of(official)
        aliases = list(row.get("aliases") or [])
        if host and host not in aliases:
            aliases.append(host)
            row["aliases"] = aliases
    if not row.get("name"):
        row["name"] = public.get("name") or row.get("slug")
    if not row.get("domain"):
        row["domain"] = public.get("domain") or ""
    if not row.get("slug"):
        row["slug"] = public.get("slug") or ""
    return row


def select_zeros(
    public_rows: list[dict],
    enr_by: dict[str, dict],
    *,
    unwalked: bool = False,
    slugs: list[str] | None = None,
) -> list[dict]:
    """Companies whose Completeness is 0. --unwalked keeps probed==0."""
    by_pub = {row.get("slug"): row for row in public_rows if row.get("slug")}
    wanted = [s for s in (slugs or []) if s]
    rows = [by_pub[s] for s in wanted if s in by_pub] if wanted else public_rows
    out = []
    for row in rows:
        slug = row.get("slug") or ""
        if not slug:
            continue
        if file_sum(row) != 0:
            continue
        enr = enr_by.get(slug)
        if not enr:
            continue
        if unwalked and probed_of(row, enr) != 0:
            continue
        company = walk_company(row, enr)
        if not company.get("domain") and not company.get("official_url"):
            continue
        out.append({
            "slug": slug,
            "name": company.get("name") or slug,
            "domain": company.get("domain") or "",
            "official_url": company.get("official_url") or "",
            "probed": probed_of(row, enr),
            "company": company,
        })
    return out


def kind_of(url: str) -> str:
    host = enrich.host_of(url)
    path = enrich.path_of(url)
    blob = f"{host} {path}"
    if enrich.is_portal_vendor_host(url, {"domain": "invalid.invalid"}):
        return "portal"
    if re.search(r"sub-?process|service-providers?", blob, re.I):
        return "subprocessors"
    if enrich.DPA_PATH_RE.search(blob):
        return "dpa"
    if re.search(r"privacy", path, re.I):
        return "privacy"
    if re.search(r"/(about|our-story|our-company|who-we-are|company)(?:/|$)", path, re.I):
        return "about"
    if re.search(r"trust", blob, re.I):
        return "trust"
    if re.search(r"security", blob, re.I):
        return "security"
    if re.search(r"compliance|assurance|certif|attestation", blob, re.I):
        return "compliance"
    if path in {"", "/"}:
        return "official"
    return "page"


def seed_urls(company: dict) -> list[tuple[str, str]]:
    """Start from domain + official_url. Reuse crawl.candidate_urls + well-known."""
    out, seen = [], set()

    def add(kind: str, url: str) -> None:
        u = (url or "").strip()
        if not u.startswith("http"):
            return
        if ITEM_UID_RE.search(u) or ASSET_URL_RE.search(u):
            return
        key = u.rstrip("/").lower()
        if key in seen:
            return
        seen.add(key)
        out.append((kind, u))

    official = (company.get("official_url") or "").strip()
    add("official", official)
    for url in crawl.candidate_urls(company):
        add(kind_of(url), url)
    for url in enrich.privacy_probe_urls_for(company, core_only=True):
        add("privacy", url)
    for domain in enrich.hosts_for(company)[:1]:
        for kind, path in (
            ("security", "/security"),
            ("trust", "/trust"),
            ("compliance", "/compliance"),
            ("trust", "/trust-center"),
        ):
            add(kind, f"https://{domain}{path}")
            if not domain.startswith("www."):
                add(kind, f"https://www.{domain}{path}")
    for url in enrich.about_urls_for(company)[:6]:
        add("about", url)
    return out


def looks_like_js_shell(rec: dict) -> bool:
    """SPA / portal chrome with no printed file. Same cues as enrich list skip."""
    html = rec.get("html") or rec.get("raw_head") or ""
    title = rec.get("title") or ""
    text = rec.get("text") or ""
    if enrich.VENDOR_WORDS.search(title) or enrich.VENDOR_TITLE_TAIL.search(title):
        return True
    if enrich.TABLE_RE.search(html):
        return False
    if "manifestPreload" in html and len(text) < 2000:
        return True
    if enrich.JS_JUNK.search(html[:4000]) and len(text) < 3000:
        return True
    return False


def classify_fetch(url: str, rec: dict, company: dict) -> str:
    """Terminal fetch class. Do not invent. Portal / wall stay unreadable."""
    final = rec.get("final_url") or url
    status = int(rec.get("status") or 0)
    if enrich.is_portal_vendor_host(url, company) or enrich.is_portal_vendor_host(final, company):
        return "portal-host"
    vendor = crawl.detect_vendor(final, rec.get("html") or "", {})
    if vendor in PORTAL_VENDORS:
        return "portal-host"
    if not rec.get("ok") or status != 200:
        return f"http-{status}"
    if not enrich.is_first_party_url(final, company):
        return "portal-host" if vendor else "not-first-party"
    if looks_like_js_shell(rec) or enrich.looks_like_login_wall(
        rec.get("title") or "", rec.get("text") or ""
    ):
        return "js-shell|login-wall"
    if enrich.looks_dead(rec.get("title") or "", rec.get("text") or ""):
        return "soft-404"
    if enrich.landed_on_home(url, final) and kind_of(url) not in {"official", "about"}:
        return "homepage-bounce"
    ctype = (rec.get("ctype") or "").lower()
    if "pdf" in ctype or (url or "").lower().endswith(".pdf"):
        return "pdf"
    return "200 first-party HTML"


def is_trust_page(url: str, rec: dict, company: dict) -> bool:
    """First-party self-hosted trust/security HTML. Portal vendors stay out."""
    if classify_fetch(url, rec, company) != "200 first-party HTML":
        return False
    fetched = {
        "ok": rec.get("ok"),
        "status": rec.get("status") or 0,
        "final_url": rec.get("final_url") or url,
        "body": rec.get("html") or "",
        "headers": {"content-type": rec.get("ctype") or "text/html"},
    }
    ok, vendor, _title = crawl.is_trust_hit(url, fetched)
    if vendor in PORTAL_VENDORS:
        return False
    if ok and vendor == "self_hosted":
        return True
    kind = kind_of(url)
    if kind in {"trust", "security", "compliance"} and enrich.accept_link(
        "trust" if kind != "security" else "security", url, rec
    ):
        return True
    return False


def rec_blob(rec: dict) -> str:
    return mark_blob(
        rec.get("html") or "",
        rec.get("title") or "",
        rec.get("meta") or "",
        rec.get("text") or "",
    )


def marks_from_rec(rec: dict) -> list[str]:
    html = rec.get("html") or ""
    return extract_certs_from_html(html, text=rec_blob(rec))


def harvest_follow_urls(url: str, rec: dict, company: dict) -> list[tuple[str, str]]:
    """First-party DPA / list / compliance / about hrefs. No invented paths."""
    if classify_fetch(url, rec, company) != "200 first-party HTML":
        return []
    html = rec.get("html") or ""
    base = rec.get("final_url") or url
    out, seen = [], set()

    def add(kind: str, href: str) -> None:
        u = (href or "").split("#")[0].strip()
        if not u.startswith("http"):
            return
        if ITEM_UID_RE.search(u) or ASSET_URL_RE.search(u):
            return
        key = u.rstrip("/").lower()
        if key in seen:
            return
        if not enrich.is_first_party_url(u, company):
            return
        seen.add(key)
        out.append((kind, u))

    for href in enrich.extract_dpa_candidates(html, base):
        add("dpa", href)
    for href in enrich.extract_subprocessor_candidates(html, base):
        add("subprocessors", href)
    for href in rec.get("hrefs") or []:
        if COMPLIANCE_URL_RE.search(href) or re.search(
            r"privacy|sub-?process|dpa|data-processing|about|our-story",
            href,
            re.I,
        ):
            add(kind_of(href), href)
    for href in enrich.year_follow_urls(rec, company):
        add("about", href)
    return out[:FOLLOW_CAP]


def extra_instrument_urls(company: dict) -> list[tuple[str, str]]:
    """Well-known DPA / list / about probes the file_company_* walkers already use."""
    out, seen = [], set()

    def add(kind: str, url: str) -> None:
        u = (url or "").strip()
        if not u.startswith("http"):
            return
        key = u.rstrip("/").lower()
        if key in seen:
            return
        if not enrich.is_first_party_url(u, company):
            return
        seen.add(key)
        out.append((kind, u))

    for url in enrich.dpa_probe_urls_for(company):
        add("dpa", url)
    for url in enrich.subprocessor_probe_urls_for(company):
        add("subprocessors", url)
    for url in enrich.about_urls_for(company):
        add("about", url)
    return out


def fetch_page(url: str) -> dict:
    try:
        return enrich.fetch_seed_page(url)
    except Exception:
        return {
            "ok": False, "status": 0, "final_url": url,
            "hrefs": [], "html": "", "title": "", "text": "", "meta": "", "ctype": "",
        }


def page_kind(url: str) -> str:
    return "security" if "security" in f"{enrich.host_of(url)} {enrich.path_of(url)}".lower() else "trust"


def apply_page_to_row(row: dict, url: str, kind: str) -> bool:
    """File a first-party Official page. Never overwrite. Vendor stays unknown."""
    if not url or not str(url).startswith("http"):
        return False
    if row.get("found") and (row.get("trust_url") or row.get("final_url")):
        return False
    links = dict(row.get("links") or {})
    if links.get("trust") or links.get("security"):
        return False
    row["found"] = True
    row["trust_url"] = url
    row["final_url"] = url
    row["vendor"] = "unknown"
    if kind == "security":
        links.setdefault("security", url)
    else:
        links.setdefault("trust", url)
    row["links"] = links
    if not (row.get("summary") or "").strip():
        row["summary"] = "Official page on file."
    rescore(row)
    return True


def company_readable(classes: list[str]) -> bool:
    return any(c in {"200 first-party HTML", "hit", "regulation-only", "no-named-marks"} for c in classes)


def company_unreadable_only(classes: list[str]) -> bool:
    if not classes:
        return True
    if company_readable(classes):
        return False
    return True


def inspect_company(
    rec: dict,
    pages: dict[str, tuple[str, dict]],
    register: dict[str, dict],
) -> dict:
    """Classify every fetched URL and collect fileable first-party holds."""
    company = rec["company"]
    slug = rec["slug"]
    rejected = []
    classes = []
    page_hit = None
    mark_hit = None
    dpa_hit = None
    sub_hit = None
    year_hit = None

    for url, (kind, page) in pages.items():
        final = page.get("final_url") or url
        klass = classify_fetch(url, page, company)
        if klass != "200 first-party HTML":
            classes.append(klass)
            rejected.append({
                "slug": slug,
                "url": public_url(url),
                "final": public_url(final),
                "reason": klass,
                "kind": kind,
            })
            continue
        classes.append(klass)

        if page_hit is None and is_trust_page(url, page, company):
            page_hit = {
                "url": public_url(final),
                "kind": page_kind(final),
            }
            classes.append("hit")

        mark_kind = kind if kind in {"trust", "security", "privacy", "compliance"} else ""
        if mark_kind or is_trust_page(url, page, company):
            live, hold_skip = hold_marks(marks_from_rec(page), rec_blob(page), mark_kind or "trust")
            if live:
                if mark_hit is None or len(live) > len(mark_hit.get("added") or []):
                    mark_hit = {
                        "url": public_url(final),
                        "added": live,
                        "quote": mark_quote(rec_blob(page), live),
                    }
                classes.append("hit")
            elif hold_skip:
                classes.append(hold_skip)
                rejected.append({
                    "slug": slug,
                    "url": public_url(url),
                    "final": public_url(final),
                    "reason": hold_skip,
                    "kind": kind,
                })

        if dpa_hit is None and enrich.classify_as_dpa(url, page):
            dpa_hit = {"url": public_url(final)}
            classes.append("hit")

        if sub_hit is None:
            skip = enrich.cited_list_skip_reason(url, page, company)
            if not skip:
                procs = enrich.published_processors_from_cited(company, page, url, register)
                procs = [(i, n, e) for i, n, e in procs if not enrich.looks_like_date_name(n)]
                if procs:
                    sub_hit = {
                        "url": public_url(final),
                        "names": [n for _i, n, _e in procs],
                        "procs": procs,
                    }
                    classes.append("hit")

        if year_hit is None and enrich.is_official_year_source(final, company):
            blob = " ".join(filter(None, [
                page.get("title") or "",
                page.get("meta") or "",
                page.get("text") or "",
            ]))
            year = enrich.parse_official_founded_year(blob, company.get("name") or "")
            if year:
                year_hit = {
                    "year": year,
                    "url": enrich.canon_source_url(final),
                    "quote": year_quote(blob, year, company.get("name") or ""),
                }
                classes.append("hit")

    hit = {}
    if page_hit:
        hit["page"] = page_hit
    if mark_hit:
        hit["marks"] = {k: mark_hit[k] for k in ("url", "added", "quote")}
    if dpa_hit:
        hit["dpa"] = dpa_hit
    if sub_hit:
        hit["subprocessors"] = {
            "url": sub_hit["url"],
            "names": sub_hit["names"],
            "procs": sub_hit["procs"],
        }
    if year_hit:
        hit["years"] = year_hit

    return {
        "slug": slug,
        "name": rec["name"],
        "classes": classes,
        "rejected": rejected,
        "hit": hit,
        "readable": company_readable(classes),
        "unreadable": company_unreadable_only(classes),
        "probed": len(pages),
    }


def apply_hit(row: dict, hit: dict, register: dict[str, dict]) -> dict:
    """File only missing first-party holds. Never overwrite a verified fill."""
    filed = {}
    if hit.get("page"):
        url = hit["page"]["url"]
        kind = hit["page"].get("kind") or page_kind(url)
        if apply_page_to_row(row, url, kind):
            filed["page"] = {"url": url, "kind": kind}
    if hit.get("marks"):
        added = enrich.apply_marks_to_row(row, list(hit["marks"].get("added") or []))
        if added:
            filed["marks"] = {
                "url": hit["marks"]["url"],
                "added": added,
                "quote": hit["marks"].get("quote") or "",
            }
    if hit.get("dpa"):
        url = hit["dpa"]["url"]
        if enrich.apply_dpa_to_row(row, url):
            filed["dpa"] = {"url": url}
    if hit.get("subprocessors"):
        url = hit["subprocessors"]["url"]
        procs = hit["subprocessors"].get("procs") or []
        if procs and not (row.get("subprocessors") or []):
            enrich.apply_subprocessors_to_row(row, url)
            row["subprocessors"] = [pid for pid, _n, _e in procs]
            filed["subprocessors"] = {
                "url": url,
                "names": [n for _i, n, _e in procs],
            }
            append_processor_edges(
                [{
                    "from": row.get("slug"),
                    "to": pid,
                    "source_url": url,
                    "evidence": ev or name,
                } for pid, name, ev in procs],
                register,
            )
        elif url and not (row.get("links") or {}).get("subprocessors"):
            if enrich.apply_subprocessors_to_row(row, url):
                filed["subprocessors"] = {"url": url, "names": []}
    if hit.get("years"):
        year = int(hit["years"]["year"])
        source = hit["years"]["url"]
        if enrich.apply_year_to_row(row, year, source):
            filed["years"] = {
                "year": year,
                "url": source,
                "quote": hit["years"].get("quote") or "",
            }
    return filed


def snapshot_aiti(public: dict) -> dict:
    """Copy AITI instruments / cited-list source-lines before build_pages."""
    out = {}
    for row in public.get("companies") or []:
        slug = row.get("slug")
        if not slug:
            continue
        keep = {}
        for key in ("ai_page", "ai_processors", "ai_evals", "ai_incidents", "aiti_lists", "official_url"):
            if row.get(key):
                keep[key] = row[key]
        inst = row.get("instruments") or {}
        extra = {}
        for key in ("ai", "evals", "incidents"):
            if inst.get(key):
                extra[key] = inst[key]
        if extra:
            keep["instruments"] = extra
        if keep:
            out[slug] = keep
    return out


def restore_aiti(public: dict, snap: dict) -> int:
    """Put back any AITI field build_pages dropped. Return how many were missing."""
    dropped = 0
    by = {c["slug"]: c for c in public.get("companies") or [] if c.get("slug")}
    for slug, keep in snap.items():
        row = by.get(slug)
        if not row:
            dropped += 1
            continue
        for key in ("ai_page", "ai_processors", "ai_evals", "ai_incidents", "aiti_lists", "official_url"):
            if keep.get(key) and not row.get(key):
                row[key] = keep[key]
                dropped += 1
        inst = dict(row.get("instruments") or {})
        for key, rec in (keep.get("instruments") or {}).items():
            if rec and not (inst.get(key) or {}).get("url"):
                inst[key] = rec
                row["instruments"] = inst
                dropped += 1
    return dropped


def rebuild_pages() -> int:
    """Snapshot AITI, run build_pages, restore anything the rebuild dropped."""
    public = load_json(PUBLIC, {})
    snap = snapshot_aiti(public)
    import build_pages  # noqa: WPS433

    rc = build_pages.main()
    public = load_json(PUBLIC, {})
    dropped = restore_aiti(public, snap)
    if dropped:
        write_json(PUBLIC, public)
    print(f"DROPPED_INSTRUMENTS {dropped}", flush=True)
    return rc


def main(argv: list[str] | None = None) -> int:
    opts = parse_args(argv)
    t0 = time.time()
    public = load_json(PUBLIC, {})
    enr = load_json(ENRICHED, {})
    public_rows = list(public.get("companies") or [])
    companies = list(enr.get("companies") or [])
    enr_by = {c["slug"]: c for c in companies if c.get("slug")}
    register = {c["slug"]: c for c in companies if c.get("slug")}

    batch = select_zeros(
        public_rows,
        enr_by,
        unwalked=opts["unwalked"],
        slugs=opts["slugs"],
    )
    mode = "unwalked" if opts["unwalked"] else "all-zeros"
    if opts["slugs"]:
        mode = "slugs"
    print(f"batch {len(batch)} Completeness-0 companies ({mode})", flush=True)

    seeds: list[tuple[str, str, str]] = []
    seen_seed = set()
    for rec in batch:
        for kind, url in seed_urls(rec["company"]):
            key = (rec["slug"], url.rstrip("/").lower())
            if key in seen_seed:
                continue
            seen_seed.add(key)
            seeds.append((rec["slug"], kind, url))
    print(f"phase 1: fetch {len(seeds)} domain / official / usual-path URLs", flush=True)

    pages: dict[str, dict[str, tuple[str, dict]]] = {rec["slug"]: {} for rec in batch}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(fetch_page, url): (slug, kind, url) for slug, kind, url in seeds}
        done = 0
        for fut in as_completed(futs):
            slug, kind, url = futs[fut]
            rec = fut.result()
            pages[slug][url] = (kind, rec)
            done += 1
            if done % 50 == 0 or done == len(futs):
                print(f"  seed {done}/{len(futs)}", flush=True)

    follow: list[tuple[str, str, str]] = []
    seen_follow = set(seen_seed)
    for rec in batch:
        company = rec["company"]
        live = False
        for url, (kind, page) in pages[rec["slug"]].items():
            if classify_fetch(url, page, company) != "200 first-party HTML":
                continue
            live = True
            for fkind, href in harvest_follow_urls(url, page, company):
                key = (rec["slug"], href.rstrip("/").lower())
                if key in seen_follow:
                    continue
                seen_follow.add(key)
                follow.append((rec["slug"], fkind, href))
        if live:
            for fkind, href in extra_instrument_urls(company):
                key = (rec["slug"], href.rstrip("/").lower())
                if key in seen_follow:
                    continue
                seen_follow.add(key)
                follow.append((rec["slug"], fkind, href))
    print(f"phase 2: fetch {len(follow)} harvested DPA / list / about URLs", flush=True)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(fetch_page, url): (slug, kind, url) for slug, kind, url in follow}
        done = 0
        for fut in as_completed(futs):
            slug, kind, url = futs[fut]
            rec = fut.result()
            pages[slug][url] = (kind, rec)
            done += 1
            if done % 50 == 0 or done == len(futs):
                print(f"  follow {done}/{len(futs)}", flush=True)

    hits, stayed, unreadable, rejected = [], [], [], []
    class_counts: Counter[str] = Counter()
    inspected = []
    for rec in batch:
        note = inspect_company(rec, pages[rec["slug"]], register)
        inspected.append(note)
        class_counts.update(note["classes"])
        rejected.extend(note["rejected"])
        if note["hit"]:
            item = {"slug": note["slug"], "name": note["name"], **note["hit"]}
            sub = item.get("subprocessors")
            if isinstance(sub, dict) and "procs" in sub:
                item["subprocessors"] = {
                    "url": sub.get("url"),
                    "names": sub.get("names") or [],
                }
            hits.append(item)
        elif note["unreadable"]:
            reasons = [c for c in note["classes"] if c not in {"200 first-party HTML"}]
            unreadable.append({
                "slug": note["slug"],
                "name": note["name"],
                "reason": reasons[0] if reasons else "unreadable",
            })
        else:
            stayed.append({
                "slug": note["slug"],
                "name": note["name"],
                "note": "first-party HTML names no catalog hold",
            })

    filed = []
    if opts["apply"]:
        hit_by = {h["slug"]: h for h in hits}
        note_by = {n["slug"]: n for n in inspected}
        for rec in batch:
            row = enr_by[rec["slug"]]
            note = note_by[rec["slug"]]
            row["probed"] = max(int(row.get("probed") or 0), int(note["probed"] or 0))
            hit = note["hit"]
            if not hit:
                continue
            applied = apply_hit(row, hit, register)
            if applied:
                filed.append({"slug": rec["slug"], "name": rec["name"], **applied})
        write_json(ENRICHED, enr)
        write_json(DATA / "enriched.json", enr)

    # Audit hits keep the proposed fills (dry-run) or the applied subset.
    audit_hits = filed if opts["apply"] else hits
    # Drop processor tuples from the ledger.
    clean_hits = []
    for rec in audit_hits:
        item = {k: v for k, v in rec.items() if k != "procs"}
        sub = item.get("subprocessors")
        if isinstance(sub, dict) and "procs" in sub:
            item["subprocessors"] = {"url": sub.get("url"), "names": sub.get("names") or []}
        clean_hits.append(item)

    report = {
        "generated_at": enr.get("generated_at"),
        "mode": mode,
        "apply": bool(opts["apply"]),
        "rule": (
            "Completeness-0 validator. Completeness is the sum of five "
            "0/10/20 file rules, not disclosure.score. Start from domain "
            "and official_url. Usual paths come from crawl.candidate_urls "
            "(the same set crawl.probe_company walks). Live pages are read "
            "with enrich.fetch_seed_page. Marks, DPA, named processors, and "
            "years use the existing extract / harvest / parse / apply_*. "
            "403/429/SPA/portal stay unreadable. Portal vendors are never "
            "named. Dry-run writes only this ledger."
        ),
        "batch": [rec["slug"] for rec in batch],
        "classes": dict(class_counts),
        "hits": clean_hits,
        "stayed_open": stayed,
        "unreadable": unreadable,
        "rejected": rejected,
    }
    write_json(REPORT, report)

    print(
        f"scanned={len(batch)} hits={len(clean_hits)} stayed={len(stayed)} "
        f"unreadable={len(unreadable)} rejected={len(rejected)} "
        f"in {time.time() - t0:.1f}s",
        flush=True,
    )
    for row in clean_hits:
        bits = []
        if row.get("page"):
            bits.append(f"page {row['page']['url']}")
        if row.get("marks"):
            bits.append("+" + ", ".join(row["marks"]["added"]))
        if row.get("dpa"):
            bits.append("dpa")
        if row.get("subprocessors"):
            bits.append(f"sub {len(row['subprocessors'].get('names') or [])}")
        if row.get("years"):
            bits.append(f"year {row['years']['year']}")
        print(f"  + {row['slug']} {' · '.join(bits)}", flush=True)
    if opts["apply"] and clean_hits:
        rebuild_pages()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
