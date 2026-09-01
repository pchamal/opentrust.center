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
    check(len(batch) <= DEFAULT_LIMIT, f"paced batch stays at {DEFAULT_LIMIT}, got {len(batch)}")
    check(len(batch) > 0, "first batch wrote last_batch")
    for slug in batch:
        rec = entries.get(slug) or {}
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
