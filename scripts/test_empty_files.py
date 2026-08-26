#!/usr/bin/env python3
"""Completeness-0 validator: file flags, not disclosure.score. No invented fills."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from file_company_marks import hold_marks  # noqa: E402
from marks import MARK_PATTERNS  # noqa: E402
from verify_empty_files import (  # noqa: E402
    FILE_KEYS,
    apply_page_to_row,
    classify_fetch,
    file_sum,
    is_trust_page,
    parse_args,
    probed_of,
    seed_urls,
    select_zeros,
    walk_company,
)

PUBLIC = ROOT / "site" / "data.json"
ENRICHED = ROOT / "site" / "data" / "enriched.json"
REPORT = ROOT / "data" / "render" / "empty-file-audit.json"
CATALOG = {name for name, _p in MARK_PATTERNS}


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"fail: {msg}")


def rec(url: str, html: str, title: str, status: int = 200, final: str | None = None) -> dict:
    from enrich import strip_tags

    return {
        "ok": status == 200,
        "status": status,
        "final_url": final or url,
        "title": title,
        "text": strip_tags(html)[:80000],
        "html": html,
        "meta": "",
        "ctype": "text/html",
        "hrefs": [],
    }


def test_parse_args() -> None:
    check(parse_args([]) == {"unwalked": False, "apply": False, "slugs": []}, "default dry-run all zeros")
    check(parse_args(["--unwalked"])["unwalked"], "--unwalked")
    check(parse_args(["--apply", "acme"]) == {"unwalked": False, "apply": True, "slugs": ["acme"]}, "apply + slug")
    try:
        parse_args(["--invent"])
    except SystemExit:
        return
    raise SystemExit("fail: unknown flag must exit")


def test_file_sum_is_not_disclosure() -> None:
    row = {
        "file": {"page": 0, "marks": 0, "dpa": 0, "subprocessors": 0, "years": 0},
        "disclosure": {"score": 40, "tier": "on-file", "factors": {"privacy": 6}},
    }
    check(file_sum(row) == 0, "disclosure.score is not Completeness")
    row["file"]["page"] = 20
    row["file"]["marks"] = 10
    check(file_sum(row) == 30, "Completeness is the sum of five file rules")
    check(set(FILE_KEYS) == {"page", "marks", "dpa", "subprocessors", "years"}, "five rules")


def test_select_unwalked() -> None:
    public = json.loads(PUBLIC.read_text())
    enr = json.loads(ENRICHED.read_text())
    enr_by = {c["slug"]: c for c in enr["companies"]}
    zeros = select_zeros(public["companies"], enr_by)
    unwalked = select_zeros(public["companies"], enr_by, unwalked=True)
    check(all(file_sum(r) == 0 for r in public["companies"] if r["slug"] in {x["slug"] for x in zeros}), "zeros only")
    check(len(unwalked) == 144, f"AITI silent_row probed==0 is 144, got {len(unwalked)}")
    check(all(x["probed"] == 0 for x in unwalked), "unwalked is probed==0")
    check(all(x["official_url"].startswith("http") for x in unwalked), "unwalked stores official_url")
    check(probed_of({"probed": 0}, {"probed": 4}) == 0, "public probed wins")
    one = select_zeros(public["companies"], enr_by, slugs=["7ai", "stripe"])
    check([x["slug"] for x in one] == ["7ai"], "argv slugs still require Completeness 0")


def test_classify_fetch() -> None:
    company = {"slug": "example", "name": "Example", "domain": "example.com"}
    check(
        classify_fetch("https://example.com/trust", rec("https://example.com/trust", "<p>nope</p>", "Trust", 403), company)
        == "http-403",
        "403 is http-403",
    )
    check(
        classify_fetch(
            "https://example.safebase.us",
            rec("https://example.safebase.us", "<p>SOC 2</p>", "Trust Center", 200),
            company,
        )
        == "portal-host",
        "SafeBase host is portal-host",
    )
    check(
        classify_fetch(
            "https://example.com/trust",
            rec(
                "https://example.com/trust",
                "<html><head><title>Example Trust Center | Powered by ExamplePortal</title></head>"
                "<body>SOC 2 Type II<script>var manifestPreload=1</script></body></html>",
                "Example Trust Center | Powered by ExamplePortal",
            ),
            company,
        )
        == "js-shell|login-wall",
        "powered-by / SPA chrome is js-shell|login-wall",
    )
    check(
        classify_fetch(
            "https://example.com/trust",
            rec("https://example.com/trust", "<html><title>Sign in</title><body>Please log in to continue.</body></html>", "Sign in"),
            company,
        )
        == "js-shell|login-wall",
        "login wall is js-shell|login-wall",
    )
    check(
        classify_fetch(
            "https://example.com/trust",
            rec("https://example.com/trust", "<p>Welcome</p>", "Example", 200, final="https://example.com/"),
            company,
        )
        == "homepage-bounce",
        "trust path that lands on / is homepage-bounce",
    )
    check(
        classify_fetch(
            "https://example.com/trust",
            rec("https://example.com/trust", "<h1>Page not found</h1>", "404 — Page not found"),
            company,
        )
        == "soft-404",
        "soft 404",
    )
    live = rec(
        "https://example.com/security",
        "<html><head><title>Security</title></head><body>"
        "<h1>Security</h1><p>Our information security program.</p></body></html>",
        "Security",
    )
    check(classify_fetch("https://example.com/security", live, company) == "200 first-party HTML", "live first-party HTML")
    check(is_trust_page("https://example.com/security", live, company), "self-hosted security page is a page hit")


def test_hold_marks_not_invented() -> None:
    kept, why = hold_marks(
        ["GDPR", "CCPA"],
        "You have a right to appeal under Art. 77 GDPR. CCPA rights are described below.",
        "privacy",
    )
    check(kept == [] and why == "regulation-only", f"privacy rights stay open: {kept} {why}")
    kept, why = hold_marks(
        ["SOC 2 Type II", "ISO 27001"],
        "We maintain SOC 2 Type II attestation and ISO 27001 certification for the platform.",
        "security",
    )
    check(kept == ["SOC 2 Type II", "ISO 27001"], f"named holds stay: {kept}")


def test_apply_does_not_overwrite() -> None:
    row = {
        "found": True,
        "trust_url": "https://example.com/trust",
        "final_url": "https://example.com/trust",
        "vendor": "unknown",
        "certs": ["ISO 27001"],
        "founded_year": 2014,
        "links": {"trust": "https://example.com/trust", "dpa": "https://example.com/legal/dpa"},
        "disclosure": {"score": 40, "tier": "on-file", "factors": {"portal": 20, "dpa": 8}},
    }
    check(not apply_page_to_row(row, "https://example.com/security", "security"), "verified Official page stays")
    check(row["trust_url"] == "https://example.com/trust", "trust_url not overwritten")
    check(row["vendor"] == "unknown", "vendor stays unknown")
    from enrich import apply_dpa_to_row, apply_marks_to_row, apply_year_to_row

    check(not apply_dpa_to_row(row, "https://example.com/other-dpa"), "verified DPA stays")
    added = apply_marks_to_row(row, ["ISO 27001"])
    check(added == [], "duplicate mark is not re-filed")
    check(not apply_year_to_row(row, 2010, "https://example.com/about"), "verified year stays")

    empty = {
        "slug": "example",
        "name": "Example",
        "domain": "example.com",
        "found": False,
        "trust_url": None,
        "certs": [],
        "links": {},
        "disclosure": {"score": 0, "tier": "silent", "factors": {}},
        "vendor": "unknown",
    }
    check(apply_page_to_row(empty, "https://example.com/security", "security"), "empty file takes a first-party page")
    check(empty["found"] is True, "page sets found")
    check(empty["vendor"] == "unknown", "Official page does not name a portal vendor")
    check(empty["links"]["security"] == "https://example.com/security", "security instrument filed")
    check("safebase" not in json.dumps(empty).lower(), "no portal vendor on the row")


def test_seeds_start_from_domain_and_official() -> None:
    company = walk_company(
        {"slug": "example", "name": "Example", "official_url": "https://www.example.com/"},
        {"slug": "example", "name": "Example", "domain": "example.com", "aliases": []},
    )
    urls = seed_urls(company)
    kinds = {u for _k, u in urls}
    check("https://www.example.com/" in kinds or "https://www.example.com" in kinds, "official_url is a seed")
    check(any("/trust" in u or "trust.example.com" in u for u in kinds), "crawl.candidate_urls usual paths")
    check(any(u.endswith("/privacy") or u.endswith("/privacy-policy") for u in kinds), "well-known privacy")
    check(any(".safebase.us" in u for u in kinds), "portal hosts stay in the usual-path set to classify")


def test_audit_when_present() -> None:
    if not REPORT.exists():
        return
    public = json.loads(PUBLIC.read_text())
    enr = json.loads(ENRICHED.read_text())
    report = json.loads(REPORT.read_text())
    by_pub = {c["slug"]: c for c in public["companies"]}
    by_enr = {c["slug"]: c for c in enr["companies"]}
    batch = report.get("batch") or []
    check(isinstance(batch, list) and batch, "audit names a batch")
    check(report.get("hits") is not None, "audit has hits")
    check(report.get("stayed_open") is not None, "audit has stayed_open")
    check(report.get("unreadable") is not None, "audit has unreadable")
    check(report.get("rejected") is not None, "audit has rejected")
    check(report.get("classes") is not None, "audit has classes")
    for slug in batch:
        check(slug in by_pub, f"{slug} is not an invented company")
        check(file_sum(by_pub[slug]) == 0 or slug in {h["slug"] for h in report.get("hits") or []},
              f"{slug} was not a Completeness-0 row")
    for rec in report.get("hits") or []:
        slug = rec["slug"]
        for name in ((rec.get("marks") or {}).get("added") or []):
            check(name in CATALOG, f"{slug} invented cert {name}")
        for url in (
            (rec.get("page") or {}).get("url"),
            (rec.get("marks") or {}).get("url"),
            (rec.get("dpa") or {}).get("url"),
            (rec.get("subprocessors") or {}).get("url"),
            (rec.get("years") or {}).get("url"),
        ):
            if url:
                check(str(url).startswith("http"), f"{slug} missing source URL")
        html_path = ROOT / "site" / "c" / f"{slug}.html"
        if html_path.exists() and report.get("apply"):
            html = html_path.read_text(encoding="utf-8")
            visible = html.lower()
            check("safebase" not in visible and "conveyor" not in visible and "vanta" not in visible,
                  f"{slug} named a portal vendor")
            if rec.get("page"):
                check("Official page" in html, f"{slug} Official page label")
        if report.get("apply") and rec.get("marks"):
            stored = by_enr[slug].get("certs") or []
            check(all(m in stored for m in rec["marks"]["added"]), f"{slug} stored certs missing")


def main() -> int:
    test_parse_args()
    test_file_sum_is_not_disclosure()
    test_select_unwalked()
    test_classify_fetch()
    test_hold_marks_not_invented()
    test_apply_does_not_overwrite()
    test_seeds_start_from_domain_and_official()
    test_audit_when_present()
    print("ok empty-file validator")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
