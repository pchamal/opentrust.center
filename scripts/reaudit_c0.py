#!/usr/bin/env python3
"""Paced Completeness-0 reaudit. One bounded cut. Do not drain the queue.

Selects Completeness-0 register rows that have a domain. Prefers slugs that
have never been written to data/render/c0-reaudit-ledger.json, then the
oldest ledger date. Probes first-party Completeness paths through the
existing enrich / file_company_* helpers. Concurrent HTTP only. Cache
bodies. Soft-404 / login / homepage bounce is a miss. 403 / empty JS
shell / Cloudflare is a ledger soft-retry. TinyFish/Monid is stubbed
behind env and skipped when no key. Never call a browser from this cut.

Default is dry-run: update the ledger and print a short summary.
--apply files fetch-checked first-party holds through existing apply_*.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import enrich  # noqa: E402
from file_company_marks import ASSET_URL_RE, public_url  # noqa: E402
from marks import extract_certs_from_html  # noqa: E402
from verify_empty_files import (  # noqa: E402
    FILE_KEYS,
    ITEM_UID_RE,
    apply_hit,
    classify_fetch,
    clear_hit,
    extra_instrument_urls,
    file_sum,
    harvest_follow_urls,
    inspect_company,
    kind_of,
    looks_like_js_shell,
    rebuild_pages,
    walk_company,
)

SITE = ROOT / "site"
DATA = ROOT / "data"
PUBLIC = SITE / "data.json"
ENRICHED = SITE / "data" / "enriched.json"
LEDGER = DATA / "render" / "c0-reaudit-ledger.json"
DEFAULT_LIMIT = 30
WORKERS = 12
FOLLOW_CAP = 12
COMPLETENESS_HINTS = {"privacy", "subprocessors", "dpa", "security", "trust"}
SOFT_RETRY_CLASSES = {"http-403", "js-shell", "cloudflare"}
MISS_CLASSES = {"soft-404", "login-wall", "homepage-bounce"}
BROWSER_ENV_KEYS = (
    "TINYFISH_API_KEY",
    "MONID_API_KEY",
    "TINYFISH_KEY",
    "MONID_KEY",
)
CF_CHALLENGE_RE = re.compile(
    r"just a moment|attention required(?:\s*!)?(?:\s*\|\s*cloudflare)?"
    r"|cf-browser-verification|challenge-platform|cdn-cgi/challenge"
    r"|cloudflare ray id|checking your browser before accessing"
    r"|enable javascript and cookies to continue",
    re.I,
)

_BODY_CACHE: dict[str, dict] = {}


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def parse_args(argv: list[str] | None = None) -> dict:
    argv = list(sys.argv[1:] if argv is None else argv)
    apply = False
    limit = DEFAULT_LIMIT
    slugs: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--apply":
            apply = True
        elif arg == "--limit":
            i += 1
            if i >= len(argv):
                raise SystemExit("--limit needs a positive integer")
            try:
                limit = int(argv[i])
            except ValueError as exc:
                raise SystemExit("--limit needs a positive integer") from exc
            if limit < 1:
                raise SystemExit("--limit needs a positive integer")
        elif arg.startswith("--limit="):
            try:
                limit = int(arg.split("=", 1)[1])
            except ValueError as exc:
                raise SystemExit("--limit needs a positive integer") from exc
            if limit < 1:
                raise SystemExit("--limit needs a positive integer")
        elif arg.startswith("-"):
            raise SystemExit(f"unknown flag: {arg}")
        elif arg.strip():
            slugs.append(arg.strip())
        i += 1
    return {"apply": apply, "limit": limit, "slugs": slugs}


def iso_date() -> str:
    return date.today().isoformat()


def ledger_entries(raw) -> dict[str, dict]:
    """Accept {entries: {slug: rec}} or a flat {slug: rec} map."""
    if not isinstance(raw, dict):
        return {}
    inner = raw.get("entries")
    if isinstance(inner, dict):
        return {k: v for k, v in inner.items() if isinstance(v, dict)}
    return {
        k: v
        for k, v in raw.items()
        if isinstance(v, dict) and k not in {"generated_at", "rule", "last_batch", "summary"}
    }


def select_c0(
    public_rows: list[dict],
    enr_by: dict[str, dict],
    *,
    slugs: list[str] | None = None,
) -> list[dict]:
    """Completeness-0 rows that already have a domain. Do not invent one."""
    by_pub = {row.get("slug"): row for row in public_rows if row.get("slug")}
    wanted = [s for s in (slugs or []) if s]
    rows = [by_pub[s] for s in wanted if s in by_pub] if wanted else public_rows
    out = []
    for index, row in enumerate(rows):
        slug = row.get("slug") or ""
        if not slug:
            continue
        if file_sum(row) != 0:
            continue
        enr = enr_by.get(slug)
        if not enr:
            continue
        domain = (row.get("domain") or enr.get("domain") or "").strip()
        if not domain:
            continue
        company = walk_company(row, enr)
        if not (company.get("domain") or "").strip():
            continue
        out.append({
            "slug": slug,
            "name": company.get("name") or slug,
            "domain": company.get("domain") or domain,
            "official_url": company.get("official_url") or "",
            "company": company,
            "index": index,
        })
    return out


def select_batch(
    zeros: list[dict],
    ledger: dict[str, dict],
    *,
    limit: int = DEFAULT_LIMIT,
) -> list[dict]:
    """Never-reaudited first, then oldest ledger date, then register order."""

    def sort_key(rec: dict) -> tuple:
        entry = ledger.get(rec["slug"]) or {}
        if not entry:
            return (0, "", rec.get("index") or 0)
        return (1, entry.get("date") or "9999-99-99", rec.get("index") or 0)

    ordered = sorted(zeros, key=sort_key)
    return ordered[: max(1, int(limit))]


def looks_like_cloudflare(rec: dict) -> bool:
    """Challenge / interstitial HTML. Not the Cloudflare company file."""
    title = rec.get("title") or ""
    text = rec.get("text") or ""
    html = rec.get("html") or rec.get("raw_head") or ""
    blob = f"{title}\n{text[:2500]}\n{html[:2500]}"
    return bool(CF_CHALLENGE_RE.search(blob))


def classify_reaudit(url: str, rec: dict, company: dict) -> str:
    """Ledger class. Soft-404 / login / homepage bounce is a miss."""
    if looks_like_cloudflare(rec):
        return "cloudflare"
    klass = classify_fetch(url, rec, company)
    if klass != "js-shell|login-wall":
        return klass
    login = enrich.looks_like_login_wall(rec.get("title") or "", rec.get("text") or "")
    if login:
        return "login-wall"
    if looks_like_js_shell(rec):
        return "js-shell"
    return "login-wall"


def is_soft_retry(klass: str) -> bool:
    return klass in SOFT_RETRY_CLASSES


def is_miss(klass: str) -> bool:
    return klass in MISS_CLASSES


def browser_hook_key() -> str:
    for key in BROWSER_ENV_KEYS:
        if (os.environ.get(key) or "").strip():
            return key
    return ""


def request_soft_retry(url: str, reason: str) -> dict | None:
    """TinyFish/Monid hook. Skip when no key. Never call computerUse."""
    if not url or not browser_hook_key():
        return None
    # Stub only. A later cut may POST `url` / `reason` to the vendor.
    return None


def probe_urls_for_company(company: dict) -> list[tuple[str, str]]:
    """enrich.probe_urls_for plus the same first-party Completeness paths."""
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
    add(kind_of(official) if official else "official", official)
    for url, hint in enrich.probe_urls_for(company):
        if hint in COMPLETENESS_HINTS:
            add(hint, url)
    for url in enrich.privacy_probe_urls_for(company, core_only=True)[:6]:
        add("privacy", url)
    for url in enrich.dpa_probe_urls_for(company)[:8]:
        add("dpa", url)
    for url in enrich.subprocessor_probe_urls_for(company)[:8]:
        add("subprocessors", url)
    for url in enrich.about_urls_for(company)[:6]:
        add("about", url)
    for domain in enrich.hosts_for(company)[:1]:
        for kind, path in (
            ("security", "/security"),
            ("trust", "/trust"),
            ("privacy", "/privacy"),
            ("dpa", "/dpa"),
        ):
            add(kind, f"https://{domain}{path}")
            if not domain.startswith("www."):
                add(kind, f"https://www.{domain}{path}")
    return out


def fetch_page(url: str) -> dict:
    """Concurrent-safe body cache around enrich.fetch_seed_page."""
    key = (url or "").rstrip("/").lower()
    hit = _BODY_CACHE.get(key)
    if hit is not None:
        return hit
    path = enrich.cache_path("c0-reaudit:" + key)
    if path.exists():
        try:
            rec = json.loads(path.read_text())
            if isinstance(rec, dict) and "status" in rec:
                _BODY_CACHE[key] = rec
                return rec
        except Exception:
            pass
    try:
        rec = enrich.fetch_seed_page(url)
    except Exception:
        rec = {
            "ok": False, "status": 0, "final_url": url,
            "hrefs": [], "html": "", "title": "", "text": "", "meta": "", "ctype": "",
        }
    _BODY_CACHE[key] = rec
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        slim = dict(rec)
        html = slim.get("html") or ""
        if len(html) > 200000:
            slim["html"] = html[:200000]
        path.write_text(json.dumps(slim, ensure_ascii=False))
    except Exception:
        pass
    return rec


def prose_marks(rec: dict) -> list[str]:
    """Marks named in visible prose. Badge alt text stays out."""
    blob = " ".join(filter(None, [
        rec.get("title") or "",
        rec.get("meta") or "",
        rec.get("text") or "",
    ]))
    return extract_certs_from_html("", text=blob)


def drop_badge_only_marks(hit: dict, pages: dict[str, tuple[str, dict]]) -> dict:
    """Keep marks that the live prose names. Alt-only chips stay open."""
    marks = hit.get("marks") or {}
    added = list(marks.get("added") or [])
    if not added:
        return hit
    want = marks.get("url") or ""
    page = None
    for url, (_kind, rec) in pages.items():
        final = public_url(rec.get("final_url") or url)
        if final == want or public_url(url) == want:
            page = rec
            break
    if page is None:
        hit = dict(hit)
        hit.pop("marks", None)
        return hit
    keep = [name for name in added if name in prose_marks(page)]
    if not keep:
        hit = dict(hit)
        hit.pop("marks", None)
        return hit
    if keep == added:
        return hit
    hit = dict(hit)
    hit["marks"] = {**marks, "added": keep}
    return hit


def primary_refusal(classes: list[str], hit: dict) -> str:
    if hit:
        return ""
    retry = [c for c in classes if is_soft_retry(c)]
    if retry:
        return retry[0]
    miss = [c for c in classes if is_miss(c)]
    if miss:
        return miss[0]
    for klass in classes:
        if klass not in {"200 first-party HTML", "hit", "regulation-only", "no-named-marks"}:
            return klass
    return "no-named-holds"


def ledger_row(
    rec: dict,
    pages: dict[str, tuple[str, dict]],
    note: dict,
    *,
    today: str,
) -> dict:
    probed = []
    classes = []
    company = rec["company"]
    for url, (kind, page) in pages.items():
        klass = classify_reaudit(url, page, company)
        classes.append(klass)
        probed.append({
            "url": public_url(url),
            "final": public_url(page.get("final_url") or url),
            "status": int(page.get("status") or 0),
            "kind": kind,
            "class": klass,
        })
    hit = drop_badge_only_marks(clear_hit(note.get("hit") or {}), pages)
    could = [k for k in FILE_KEYS if hit.get(k)]
    retry = any(is_soft_retry(c) for c in classes)
    if retry:
        for item in probed:
            if is_soft_retry(item["class"]):
                request_soft_retry(item["url"], item["class"])
    return {
        "slug": rec["slug"],
        "name": rec["name"],
        "domain": rec["domain"],
        "date": today,
        "probed": probed,
        "could_fill": could,
        "refusal": primary_refusal(classes, hit),
        "soft_retry": retry,
        "fileable": bool(could),
        "hit": {
            k: ({kk: vv for kk, vv in v.items() if kk != "procs"} if isinstance(v, dict) else v)
            for k, v in hit.items()
        } if hit else None,
    }


def fetch_batch(jobs: list[tuple[str, str, str]]) -> dict[str, dict[str, tuple[str, dict]]]:
    pages: dict[str, dict[str, tuple[str, dict]]] = {}
    if not jobs:
        return pages
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(fetch_page, url): (slug, kind, url) for slug, kind, url in jobs}
        done = 0
        for fut in as_completed(futs):
            slug, kind, url = futs[fut]
            rec = fut.result()
            pages.setdefault(slug, {})[url] = (kind, rec)
            done += 1
            if done % 40 == 0 or done == len(futs):
                print(f"  fetch {done}/{len(futs)}", flush=True)
    return pages


def merge_pages(
    dest: dict[str, dict[str, tuple[str, dict]]],
    extra: dict[str, dict[str, tuple[str, dict]]],
) -> None:
    for slug, urls in extra.items():
        dest.setdefault(slug, {}).update(urls)


def apply_fileable(
    enr: dict,
    batch: list[dict],
    rows: list[dict],
    register: dict[str, dict],
) -> list[dict]:
    enr_by = {c["slug"]: c for c in enr.get("companies") or [] if c.get("slug")}
    filed = []
    for rec, row in zip(batch, rows):
        hit = row.get("hit") or {}
        if not hit:
            continue
        company = enr_by.get(rec["slug"])
        if not company:
            continue
        applied = apply_hit(company, hit, register)
        if applied:
            filed.append({"slug": rec["slug"], "name": rec["name"], **applied})
    if filed:
        write_json(ENRICHED, enr)
        write_json(DATA / "enriched.json", enr)
    return filed


def print_summary(batch: list[dict], rows: list[dict], filed: list[dict]) -> None:
    fileable = sum(1 for r in rows if r.get("fileable"))
    retry = sum(1 for r in rows if r.get("soft_retry"))
    still = sum(1 for r in rows if not r.get("fileable"))
    print(
        f"C0 reaudit batch={len(batch)} fileable={fileable} "
        f"soft-retry={retry} still-0={still} filled={len(filed)}",
        flush=True,
    )
    for row in rows:
        if not row.get("fileable"):
            continue
        bits = []
        hit = row.get("hit") or {}
        if hit.get("page"):
            bits.append(f"page {hit['page']['url']}")
        if hit.get("marks"):
            bits.append("+" + ", ".join(hit["marks"]["added"]))
        if hit.get("dpa"):
            bits.append("dpa")
        if hit.get("subprocessors"):
            bits.append(f"sub {len(hit['subprocessors'].get('names') or [])}")
        if hit.get("years"):
            bits.append(f"year {hit['years']['year']}")
        print(f"  + {row['slug']} {' · '.join(bits)}", flush=True)


def main(argv: list[str] | None = None) -> int:
    opts = parse_args(argv)
    t0 = time.time()
    public = load_json(PUBLIC, {})
    enr = load_json(ENRICHED, {})
    public_rows = list(public.get("companies") or [])
    companies = list(enr.get("companies") or [])
    enr_by = {c["slug"]: c for c in companies if c.get("slug")}
    register = dict(enr_by)
    raw_ledger = load_json(LEDGER, {})
    ledger = ledger_entries(raw_ledger)

    zeros = select_c0(public_rows, enr_by, slugs=opts["slugs"])
    batch = select_batch(zeros, ledger, limit=opts["limit"])
    print(
        f"batch {len(batch)} Completeness-0 companies "
        f"(limit {opts['limit']}, pool {len(zeros)})",
        flush=True,
    )

    seeds: list[tuple[str, str, str]] = []
    seen_seed = set()
    for rec in batch:
        for kind, url in probe_urls_for_company(rec["company"]):
            key = (rec["slug"], url.rstrip("/").lower())
            if key in seen_seed:
                continue
            seen_seed.add(key)
            seeds.append((rec["slug"], kind, url))
    print(f"phase 1: fetch {len(seeds)} Completeness paths", flush=True)
    pages = fetch_batch(seeds)

    follow: list[tuple[str, str, str]] = []
    seen_follow = set(seen_seed)
    for rec in batch:
        company = rec["company"]
        live = False
        for url, (_kind, page) in pages.get(rec["slug"], {}).items():
            klass = classify_reaudit(url, page, company)
            if klass != "200 first-party HTML":
                continue
            live = True
            for fkind, href in harvest_follow_urls(url, page, company)[:FOLLOW_CAP]:
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
    merge_pages(pages, fetch_batch(follow))

    today = iso_date()
    rows = []
    for rec in batch:
        slug_pages = pages.get(rec["slug"]) or {}
        note = inspect_company(rec, slug_pages, register)
        rows.append(ledger_row(rec, slug_pages, note, today=today))

    filed = []
    if opts["apply"]:
        filed = apply_fileable(enr, batch, rows, register)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for row in rows:
        ledger[row["slug"]] = row
    payload = {
        "generated_at": now,
        "rule": (
            "Paced Completeness-0 reaudit. Completeness is the sum of five "
            "0/10/20 file rules, not disclosure.score. Domain required. "
            "Never-reaudited first, then oldest ledger date. HTTP only. "
            "Soft-404 / login / homepage bounce = miss. 403 / empty JS "
            "shell / Cloudflare = soft-retry. Portal hosts stay URL-only."
        ),
        "last_batch": [rec["slug"] for rec in batch],
        "summary": {
            "batch": len(batch),
            "fileable": sum(1 for r in rows if r.get("fileable")),
            "soft_retry": sum(1 for r in rows if r.get("soft_retry")),
            "still_0": sum(1 for r in rows if not r.get("fileable")),
            "filled": len(filed),
        },
        "entries": ledger,
    }
    write_json(LEDGER, payload)
    print_summary(batch, rows, filed)
    print(f"ledger {LEDGER.relative_to(ROOT)} in {time.time() - t0:.1f}s", flush=True)
    if opts["apply"] and filed:
        rebuild_pages()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
