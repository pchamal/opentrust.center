#!/usr/bin/env python3
"""Paced Completeness-0 reaudit: bounded batch, ledger order, no invented fills."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from reaudit_c0 import (  # noqa: E402
    DEFAULT_LIMIT,
    FILE_KEYS,
    classify_reaudit,
    is_miss,
    is_soft_retry,
    ledger_entries,
    parse_args,
    request_soft_retry,
    select_batch,
    select_c0,
)
from verify_empty_files import file_sum  # noqa: E402


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
    check(parse_args([]) == {"apply": False, "limit": DEFAULT_LIMIT, "slugs": []}, "default dry-run 30")
    check(parse_args(["--limit", "15"])["limit"] == 15, "--limit 15")
    check(parse_args(["--limit=8"])["limit"] == 8, "--limit=8")
    check(
        parse_args(["--apply", "--limit", "4", "acme"])
        == {"apply": True, "limit": 4, "slugs": ["acme"]},
        "apply + limit + slug",
    )
    try:
        parse_args(["--invent"])
    except SystemExit:
        return
    raise SystemExit("fail: unknown flag must exit")


def test_file_sum_is_completeness() -> None:
    row = {
        "file": {"page": 0, "marks": 0, "dpa": 0, "subprocessors": 0, "years": 0},
        "disclosure": {"score": 40, "tier": "on-file"},
    }
    check(file_sum(row) == 0, "disclosure.score is not Completeness")
    row["file"]["years"] = 20
    check(file_sum(row) == 20, "years is one Completeness rule")
    check(set(FILE_KEYS) == {"page", "marks", "dpa", "subprocessors", "years"}, "five rules")


def test_select_c0_skips_domainless_and_nonzero() -> None:
    public = [
        {"slug": "filled", "domain": "filled.example", "file": {"page": 20}},
        {"slug": "ghost", "domain": "", "file": {"page": 0, "marks": 0, "dpa": 0, "subprocessors": 0, "years": 0}},
        {"slug": "open", "domain": "open.example", "name": "Open", "file": {"page": 0, "marks": 0, "dpa": 0, "subprocessors": 0, "years": 0}},
    ]
    enr = {
        "filled": {"slug": "filled", "domain": "filled.example", "name": "Filled"},
        "ghost": {"slug": "ghost", "domain": "", "name": "Ghost"},
        "open": {"slug": "open", "domain": "open.example", "name": "Open"},
    }
    zeros = select_c0(public, enr)
    check([z["slug"] for z in zeros] == ["open"], f"domain-less and filled stay out: {zeros}")
    check(zeros[0]["domain"] == "open.example", "domain comes from the register")
    none = select_c0(public, enr, slugs=["filled", "ghost"])
    check(none == [], "argv slugs still require Completeness-0 + domain")


def test_select_batch_never_then_oldest() -> None:
    zeros = [
        {"slug": "c", "index": 2},
        {"slug": "a", "index": 0},
        {"slug": "b", "index": 1},
        {"slug": "d", "index": 3},
    ]
    ledger = {
        "b": {"date": "2026-08-01"},
        "d": {"date": "2026-07-01"},
    }
    batch = select_batch(zeros, ledger, limit=3)
    check(
        [r["slug"] for r in batch] == ["a", "c", "d"],
        f"never-reaudited first, then oldest date: {[r['slug'] for r in batch]}",
    )
    again = select_batch(zeros, ledger, limit=1)
    check(again[0]["slug"] == "a", "limit 1 is the first never-reaudited")


def test_classify_soft_retry_and_miss() -> None:
    company = {"slug": "example", "name": "Example", "domain": "example.com"}
    check(
        classify_reaudit("https://example.com/trust", rec("https://example.com/trust", "<p>nope</p>", "Trust", 403), company)
        == "http-403",
        "403 is http-403",
    )
    check(is_soft_retry("http-403"), "403 is soft-retry")
    cf = rec(
        "https://example.com/security",
        "<html><title>Just a moment...</title><body>Checking your browser before accessing example.com. Cloudflare Ray ID: 123</body></html>",
        "Just a moment...",
    )
    check(classify_reaudit("https://example.com/security", cf, company) == "cloudflare", "CF challenge is cloudflare")
    check(is_soft_retry("cloudflare"), "cloudflare is soft-retry")
    shell = rec(
        "https://example.com/trust",
        "<html><head><title>Example Trust Center | Powered by ExamplePortal</title></head>"
        "<body>SOC 2 Type II<script>var manifestPreload=1</script></body></html>",
        "Example Trust Center | Powered by ExamplePortal",
    )
    check(classify_reaudit("https://example.com/trust", shell, company) == "js-shell", "empty JS shell is js-shell")
    check(is_soft_retry("js-shell"), "js-shell is soft-retry")
    login = rec(
        "https://example.com/trust",
        "<html><title>Sign in</title><body>Please log in to continue.</body></html>",
        "Sign in",
    )
    check(classify_reaudit("https://example.com/trust", login, company) == "login-wall", "login is login-wall")
    check(is_miss("login-wall"), "login is a miss")
    check(
        classify_reaudit(
            "https://example.com/trust",
            rec("https://example.com/trust", "<h1>Page not found</h1>", "404 — Page not found"),
            company,
        )
        == "soft-404",
        "soft 404",
    )
    check(is_miss("soft-404"), "soft-404 is a miss")
    check(is_miss("homepage-bounce"), "homepage bounce is a miss")
    check(not is_soft_retry("soft-404"), "a miss is not a soft-retry")


def test_tinyfish_stub_skips_without_key() -> None:
    saved = {k: os.environ.get(k) for k in ("TINYFISH_API_KEY", "MONID_API_KEY", "TINYFISH_KEY", "MONID_KEY")}
    try:
        for k in saved:
            os.environ.pop(k, None)
        check(request_soft_retry("https://example.com/trust", "http-403") is None, "no key skips the hook")
        os.environ["TINYFISH_API_KEY"] = "test-key"
        check(request_soft_retry("https://example.com/trust", "http-403") is None, "stub does not call a browser")
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_ledger_entries_accepts_wrapped_and_flat() -> None:
    wrapped = {"generated_at": "x", "entries": {"acme": {"date": "2026-09-01", "slug": "acme"}}}
    check(ledger_entries(wrapped)["acme"]["date"] == "2026-09-01", "wrapped entries")
    flat = {"acme": {"date": "2026-08-01"}, "generated_at": "x"}
    check("acme" in ledger_entries(flat) and "generated_at" not in ledger_entries(flat), "flat map drops meta")
    check(ledger_entries([]) == {}, "junk ledger is empty")


def test_live_ledger_when_present() -> None:
    path = ROOT / "data" / "render" / "c0-reaudit-ledger.json"
    if not path.exists():
        return
    payload = json.loads(path.read_text())
    entries = ledger_entries(payload)
    batch = payload.get("last_batch") or []
    summary = payload.get("summary") or {}
    # Paced cut. Do not drain the Completeness-0 queue.
    check(0 < len(batch) <= 40, f"paced last_batch, got {len(batch)}")
    check(summary.get("batch") == len(batch), "summary.batch matches last_batch")

    first = [slug for slug, rec in entries.items() if rec.get("date") == "2026-09-01"]
    check(len(first) == 30, f"first cut still has 30 rows dated 2026-09-01, got {len(first)}")
    check("imerit" in first, "first cut probed imerit")
    imerit = entries.get("imerit") or {}
    check(imerit.get("filed") is True, "imerit ledger row records the apply")
    check(imerit.get("could_fill") == ["page", "marks"], f"imerit could_fill {imerit.get('could_fill')}")
    check((imerit.get("hit") or {}).get("page", {}).get("url") == "https://imerit.ai/compliance-and-certifications/", "imerit Official page in ledger")
    added = ((imerit.get("hit") or {}).get("marks") or {}).get("added") or []
    check("GDPR" not in added, "imerit ledger does not file GDPR")
    check("HIPAA" not in added, "imerit ledger does not file HIPAA")

    second = [
        "lightdash",
        "luma-ai",
        "mutare",
        "name-com",
        "netnumber-global-data-services",
        "netsuite",
        "printfection",
        "replicate",
        "saicom-voice-services",
        "ternpro-dba-slope",
        "surveysensum-neurosensum-international-pte",
        "timekit",
        "tokenx",
        "worketics-it-solutions",
        "01-communique",
        "123-reg",
        "1366-technologies",
        "1871",
        "1c-company",
        "1qbit",
        "1spatial",
        "1x-technologies",
        "24-7-media",
        "24sevenoffice",
        "2u",
        "2wire",
        "33across",
        "360-security-technology",
        "3d-robotics",
        "3d-systems",
        "3dflow",
        "3i-infotech",
        "3pillar-global",
        "3scale",
        "4d-inc",
    ]
    check(len(second) == 35, f"second cut is 35 Completeness-0 rows, got {len(second)}")
    check(all(slug in entries for slug in second), "second cut rows stay in the ledger")
    check(not set(second) & set(first), "second cut must be never-reaudited vs 2026-09-01")
    check(all(not (entries.get(slug) or {}).get("filed") for slug in second), "second cut filed no honest fill")
    check("lightdash" in second, "second cut starts at the next never-reaudited C0 row")

    third = list(batch)
    check(len(third) == 35, f"third cut probed 35 Completeness-0 rows, got {len(third)}")
    check(not set(third) & set(first), "third cut must be never-reaudited vs 2026-09-01")
    check(not set(third) & set(second), "third cut must be never-reaudited vs the lightdash cut")
    check(third[0] == "4d-sas", "third cut starts at the next never-reaudited C0 row")
    check("accurx" in third and "ableton" in third, "third cut includes the clerk-filed rows")
    check(summary.get("batch") == 35, "third cut summary.batch is 35")
    check(summary.get("fileable") == 6, f"third cut extractor fileable, got {summary.get('fileable')}")
    check(summary.get("soft_retry") == 15, f"third cut soft-retry, got {summary.get('soft_retry')}")
    check(summary.get("filled") == 4, f"third cut clerk-approved fills, got {summary.get('filled')}")

    ableton = entries.get("ableton") or {}
    check(ableton.get("filed") is True, "ableton ledger row records the apply")
    check(set(ableton.get("filed_keys") or []) == {"dpa", "years"}, f"ableton filed_keys {ableton.get('filed_keys')}")
    check((ableton.get("hit") or {}).get("dpa", {}).get("url") == "https://www.ableton.com/en/dpa/", "ableton DPA in ledger")
    check((ableton.get("hit") or {}).get("years", {}).get("year") == 1999, "ableton year in ledger")
    check(
        (ableton.get("hit") or {}).get("page", {}).get("url")
        == "https://www.ableton.com/en/education/certification-program/",
        "ableton extractor still recorded the education lander",
    )

    absint = entries.get("absint") or {}
    check(absint.get("filed") is True, "absint ledger row records the apply")
    check(set(absint.get("filed_keys") or []) == {"marks"}, f"absint filed_keys {absint.get('filed_keys')}")
    check(((absint.get("hit") or {}).get("marks") or {}).get("added") == ["TISAX"], "absint TISAX in ledger")
    check("Phone" in (((absint.get("hit") or {}).get("subprocessors") or {}).get("names") or []), "absint extractor junk subs stay unfiled")

    accurx = entries.get("accurx") or {}
    check(accurx.get("filed") is True, "accurx ledger row records the apply")
    check(
        set(accurx.get("filed_keys") or []) == {"page", "marks", "dpa", "years"},
        f"accurx filed_keys {accurx.get('filed_keys')}",
    )
    check(
        (accurx.get("hit") or {}).get("page", {}).get("url")
        == "https://www.accurx.com/security-for-healthcare-professionals",
        "accurx Official page in ledger",
    )
    check(
        set(((accurx.get("hit") or {}).get("marks") or {}).get("added") or [])
        == {"ISO 27001", "Cyber Essentials Plus"},
        f"accurx marks {((accurx.get('hit') or {}).get('marks') or {}).get('added')}",
    )
    check((accurx.get("hit") or {}).get("years", {}).get("year") == 2016, "accurx year in ledger")

    accusoft = entries.get("accusoft") or {}
    check(accusoft.get("filed") is True, "accusoft ledger row records the apply")
    check(set(accusoft.get("filed_keys") or []) == {"years"}, f"accusoft filed_keys {accusoft.get('filed_keys')}")
    check((accusoft.get("hit") or {}).get("years", {}).get("year") == 1991, "accusoft year in ledger")

    check(not (entries.get("a-plus") or {}).get("filed"), "a-plus empty placeholder was not filed")
    check(not (entries.get("accountor") or {}).get("filed"), "accountor framework-ISO was not filed")

    public = json.loads((ROOT / "site" / "data.json").read_text())
    by_pub = {row.get("slug"): row for row in public.get("companies") or [] if row.get("slug")}

    pub_ableton = by_pub["ableton"]
    check(pub_ableton.get("found") is False, "ableton education cert lander is not Official page")
    check(not pub_ableton.get("trust_url"), "ableton Official page stays open")
    check((pub_ableton.get("file") or {}).get("dpa") == 20, "ableton DPA prints")
    check((pub_ableton.get("file") or {}).get("years") == 20, "ableton years print")
    check(pub_ableton.get("founded_year") == 1999, "ableton year is first-party about")
    check(((pub_ableton.get("instruments") or {}).get("dpa") or {}).get("url") == "https://www.ableton.com/en/dpa/", "ableton DPA URL")

    pub_absint = by_pub["absint"]
    check(pub_absint.get("certs") == ["TISAX"], f"absint marks {pub_absint.get('certs')}")
    check((pub_absint.get("file") or {}).get("marks") == 20, "absint TISAX prints")
    check((pub_absint.get("file") or {}).get("subprocessors") in (0, False, None), "absint junk Phone/Fax/Email/Web stay off file")
    check(not (pub_absint.get("processors") or []), "absint named processors stay open")

    pub_accurx = by_pub["accurx"]
    check(pub_accurx.get("found") is True, "accurx Official page is on file")
    check(
        pub_accurx.get("trust_url") == "https://www.accurx.com/security-for-healthcare-professionals",
        "accurx Official page is first-party security HTML",
    )
    check(set(pub_accurx.get("certs") or []) == {"ISO 27001", "Cyber Essentials Plus"}, f"accurx marks {pub_accurx.get('certs')}")
    check((pub_accurx.get("file") or {}).get("page") == 20, "accurx Official page prints")
    check((pub_accurx.get("file") or {}).get("marks") == 20, "accurx marks print")
    check((pub_accurx.get("file") or {}).get("dpa") == 20, "accurx DPA prints")
    check((pub_accurx.get("file") or {}).get("years") == 20, "accurx years print")
    check((pub_accurx.get("file") or {}).get("subprocessors") in (0, False, None), "accurx category-header subs stay off file")
    check(pub_accurx.get("founded_year") == 2016, "accurx year is first-party who-we-are")
    check(
        ((pub_accurx.get("instruments") or {}).get("dpa") or {}).get("url")
        == "https://www.accurx.com/data-processing-agreement",
        "accurx DPA URL",
    )

    pub_accusoft = by_pub["accusoft"]
    check(pub_accusoft.get("founded_year") == 1991, "accusoft year is first-party company history")
    check((pub_accusoft.get("file") or {}).get("years") == 20, "accusoft years print")
    check(pub_accusoft.get("found") is False, "accusoft Official page stays open")

    check((by_pub["a-plus"].get("file") or {}).get("page") in (0, False, None), "a-plus empty placeholder is not Official page")
    check(not (by_pub["accountor"].get("certs") or []), "accountor guiding-framework ISO 27001 stays open")

    for slug, rec in entries.items():
        check(rec.get("domain"), f"{slug} ledger row is missing a domain")
        check(rec.get("date"), f"{slug} ledger row is missing an ISO date")
        check(isinstance(rec.get("probed"), list), f"{slug} probed URLs missing")
        for item in rec.get("probed") or []:
            check(str(item.get("url") or "").startswith("http"), f"{slug} probed URL missing")
            check("status" in item, f"{slug} http status missing")
        could = rec.get("could_fill") or []
        check(set(could) <= set(FILE_KEYS), f"{slug} invented Completeness rule {could}")


def main() -> int:
    test_parse_args()
    test_file_sum_is_completeness()
    test_select_c0_skips_domainless_and_nonzero()
    test_select_batch_never_then_oldest()
    test_classify_soft_retry_and_miss()
    test_tinyfish_stub_skips_without_key()
    test_ledger_entries_accepts_wrapped_and_flat()
    test_live_ledger_when_present()
    print("ok c0 reaudit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
