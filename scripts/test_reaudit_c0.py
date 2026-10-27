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

    third = [
        "4d-sas",
        "4info",
        "5linx",
        "8i",
        "a-plus",
        "aandd-company",
        "aandp-group",
        "a123-systems",
        "a4tech",
        "aaeon",
        "abacus-data-systems",
        "abas-erp",
        "abbvie",
        "ableton",
        "abm-intelligence",
        "absint",
        "academy-chicago-publishers",
        "acadine-technologies",
        "accelya",
        "access-is",
        "accessdata",
        "accessiway",
        "accordent-technologies",
        "accountor",
        "accton",
        "accurx",
        "accusoft",
        "acd-systems",
        "acer-inc",
        "aci-worldwide",
        "acision",
        "acn-inc",
        "aconex",
        "acquity-group",
        "acsis",
    ]
    check(len(third) == 35, f"third cut probed 35 Completeness-0 rows, got {len(third)}")
    check(all(slug in entries for slug in third), "third cut rows stay in the ledger")
    check(not set(third) & set(first), "third cut must be never-reaudited vs 2026-09-01")
    check(not set(third) & set(second), "third cut must be never-reaudited vs the lightdash cut")
    check(third[0] == "4d-sas", "third cut starts at the next never-reaudited C0 row")
    check("accurx" in third and "ableton" in third, "third cut includes the clerk-filed rows")

    fourth = [
        "addepar",
        "adder-technology",
        "addtech",
        "adf-solutions",
        "adform",
        "adguard",
        "adidas-runtastic",
        "adobe-story",
        "adtaily",
        "adtile-technologies",
        "adtran",
        "adva-optical-networking",
        "advanced-machine-intelligence",
        "advanced-micro-devices",
        "advania",
        "aeneas-internet-and-telephone",
        "aero-controls",
        "aerohive-networks",
        "aerojet",
        "aerovironment",
        "affectiva",
        "afriex",
        "afterpay",
        "aftershock-pc",
        "ag-neovo",
        "agap2it",
        "ageia",
        "agere-systems",
        "agex-therapeutics",
        "agfa",
    ]
    check(len(fourth) == 30, f"2026-10-23 batch is 30, got {len(fourth)}")
    check(all(slug in entries for slug in fourth), "2026-10-23 addepar–agfa rows stay in the ledger")
    check(fourth[0] == "addepar" and fourth[-1] == "agfa", "2026-10-23 batch is the addepar–agfa cut")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-10-23" for slug in fourth),
        "2026-10-23 cut stays dated 2026-10-23",
    )
    check(not set(fourth) & set(third), "2026-10-23 cut must be never-reaudited vs the 4d-sas cut")

    batch_1026 = [
        "24slides",
        "360i",
        "3cx",
        "abengoa-solar",
        "academy-of-robotics",
        "actifio",
        "ada-health",
        "admail-west",
        "advantest",
        "aeotec",
        "affluences",
        "aggregateiq",
        "agiloft",
        "agnitio",
        "ah-software",
        "ai21",
        "aiforia-technologies-oyj",
        "aigo",
        "ailive",
        "aimotive",
        "air-products",
        "air-tractor",
        "air-worldwide",
        "airbiquity",
        "airbnb",
        "airbus",
        "airbyte",
        "aircall",
        "airclic",
        "airpair",
    ]
    check(len(batch_1026) == 30, f"2026-10-26 batch is 30, got {len(batch_1026)}")
    check(batch_1026[0] == "24slides" and batch_1026[-1] == "airpair", "2026-10-26 batch is the 24slides–airpair cut")
    check(all(slug in entries for slug in batch_1026), "2026-10-26 rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-10-26" for slug in batch_1026),
        "2026-10-26 cut is dated 2026-10-26",
    )
    check(not set(batch_1026) & set(fourth), "2026-10-26 cut must be never-reaudited vs addepar–agfa")

    batch_1027_am = [
        "advacam",
        "airship-ai",
        "airspan-networks",
        "airtalk-wireless",
        "airtame",
        "airtel-africa",
        "airware",
        "airwave-solutions",
        "airwide-solutions",
        "airwolf-3d",
        "aixtron",
        "akai",
        "akeneo",
        "akka-io",
        "alacra",
        "aladdin-knowledge-systems",
        "alapont-group",
        "alarm-com",
        "alarmforce",
        "alaska-communications",
        "alaxala-networks",
        "alba-orbital",
        "albatron-technology",
        "albemarle-corporation",
        "albertsons",
        "alcan-systems",
        "alcatel",
        "alcatel-mobile",
        "alcatel-lucent-enterprise",
        "alchemy-cms",
    ]
    check(len(batch_1027_am) == 30, f"2026-10-27 morning batch is 30, got {len(batch_1027_am)}")
    check(
        batch_1027_am[0] == "advacam" and batch_1027_am[-1] == "alchemy-cms",
        "2026-10-27 morning batch is the advacam–alchemy-cms cut",
    )
    check(all(slug in entries for slug in batch_1027_am), "2026-10-27 morning rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-10-27" for slug in batch_1027_am),
        "2026-10-27 morning cut is dated 2026-10-27",
    )
    check(not set(batch_1027_am) & set(batch_1026), "2026-10-27 morning cut must be never-reaudited vs 24slides–airpair")

    check(len(batch) == 30, f"2026-10-27 afternoon batch is 30, got {len(batch)}")
    check(batch[0] == "21vianet" and batch[-1] == "aligned-assets", "2026-10-27 afternoon batch is the 21vianet–aligned-assets cut")
    check(summary.get("batch") == 30, "2026-10-27 afternoon summary.batch is 30")
    check(summary.get("fileable") == 2, f"2026-10-27 afternoon clerk fileable, got {summary.get('fileable')}")
    check(summary.get("soft_retry") == 6, f"2026-10-27 afternoon soft-retry, got {summary.get('soft_retry')}")
    check(summary.get("still_0") == 28, f"2026-10-27 afternoon still-0, got {summary.get('still_0')}")
    check(summary.get("filled") == 2, f"2026-10-27 afternoon last-batch clerk fills, got {summary.get('filled')}")
    october = [slug for slug, rec in entries.items() if str(rec.get("date") or "").startswith("2026-10-")]
    check(len(october) == 180, f"10/22 through 10/27 cuts stay in the ledger, got {len(october)}")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-10-27" for slug in batch),
        "2026-10-27 afternoon cut is dated 2026-10-27",
    )
    check(not set(batch) & set(batch_1026), "2026-10-27 afternoon cut must be never-reaudited vs 24slides–airpair")
    check(not set(batch) & set(batch_1027_am), "2026-10-27 afternoon cut must be never-reaudited vs advacam–alchemy-cms")

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

    shipped = {
        "meilisearch": {"marks"},
        "tandem-health": {"dpa"},
        "cielo": {"marks"},
        "datapacket": {"years"},
        "firetext-communications": {"page", "years"},
        "intech-solution": {"page"},
        "servers-com": {"marks", "dpa", "years"},
        "tremendous": {"page", "dpa"},
        "warmly-ai": {"years"},
        "wowza": {"marks", "years"},
        "xfive": {"years"},
        "3shape": {"dpa", "subprocessors"},
        "8-4": {"years"},
        "active-network-llc": {"dpa"},
        "active-space-technologies": {"years"},
        "adacel": {"marks", "years"},
        "adamworks": {"years"},
        "addepar": {"marks", "subprocessors"},
        "adguard": {"dpa"},
        "afriex": {"years"},
        "aftershock-pc": {"years"},
    }
    for slug, keys in shipped.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-10-23", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
    check(
        ((entries.get("meilisearch") or {}).get("hit") or {}).get("marks", {}).get("added") == ["SOC 2 Type II"],
        "meilisearch SOC 2 Type II in ledger",
    )
    check(
        ((entries.get("3shape") or {}).get("hit") or {}).get("subprocessors", {}).get("names")
        == ["Microsoft Ireland Operations, Ltd"],
        "3shape named list is the one printed row",
    )
    check((entries.get("tandem-health") or {}).get("filed_keys") == ["dpa"], "tandem year on /legal/ stays unfiled")
    for slug in (
        "act-on",
        "access-communications",
        "live-nation-entertainment",
        "docdelta",
        "zenlayer",
        "aero-controls",
        "agfa",
        "hca-healthcare",
    ):
        check(not (entries.get(slug) or {}).get("filed"), f"{slug} stays unfiled")

    shipped_1026 = {
        "3cx": {"page"},
        "ada-health": {"page"},
        "advantest": {"years"},
        "agiloft": {"page", "marks", "dpa", "subprocessors", "years"},
        "aiforia-technologies-oyj": {"page", "marks"},
        "airbnb": {"page"},
        "airbyte": {"page", "marks"},
        "aircall": {"page", "marks", "dpa", "subprocessors", "years"},
    }
    for slug, keys in shipped_1026.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-10-26", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
    check(
        ((entries.get("agiloft") or {}).get("hit") or {}).get("marks", {}).get("added")
        == ["SOC 2 Type II", "SOC 1", "ISO 27001", "ISO 27701", "HIPAA"],
        "agiloft marks in ledger",
    )
    check(
        ((entries.get("aircall") or {}).get("hit") or {}).get("dpa", {}).get("url") == "https://aircall.io/dpa/",
        "aircall DPA is the re-checked first-party page",
    )
    check(
        ((entries.get("aircall") or {}).get("hit") or {}).get("subprocessors", {}).get("names")
        and len(((entries.get("aircall") or {}).get("hit") or {}).get("subprocessors", {}).get("names")) == 20,
        "aircall named list is the 20 printed rows",
    )
    slides = entries.get("24slides") or {}
    check(not slides.get("filed"), "24slides 403 verification wall was not filed")
    check(slides.get("soft_retry") is True and slides.get("refusal") == "http-403", "24slides stays a 403 soft-retry")
    airbus = entries.get("airbus") or {}
    check(airbus.get("filed") is False, "airbus defence products page was not filed")
    check(
        airbus.get("refusal") == "defence products page, not a company security page",
        f"airbus refusal {airbus.get('refusal')}",
    )
    ai21 = entries.get("ai21") or {}
    check(ai21.get("filed") is False, "ai21 VDP page was not filed")
    check(ai21.get("refusal") == "VDP page now Cloudflare 403", f"ai21 refusal {ai21.get('refusal')}")
    check(ai21.get("soft_retry") is True, "ai21 stays a Cloudflare soft-retry")

    shipped_1027 = {
        "airship-ai": {"years"},
        "akai": {"years"},
    }
    for slug, keys in shipped_1027.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-10-27", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("fileable") is True, f"{slug} year stays fileable")
    check((entries.get("airship-ai") or {}).get("hit", {}).get("years", {}).get("year") == 2006, "airship-ai year in ledger")
    check(
        (entries.get("airship-ai") or {}).get("hit", {}).get("years", {}).get("url") == "https://www.airship.ai/company",
        "airship-ai year source in ledger",
    )
    check((entries.get("akai") or {}).get("hit", {}).get("years", {}).get("year") == 1929, "akai year in ledger")
    check(
        (entries.get("akai") or {}).get("hit", {}).get("years", {}).get("url") == "https://akai.com/",
        "akai year source in ledger",
    )
    refused_1027 = {
        "airtame": "/security is a blog tag archive, not a company security page",
        "aixtron": "supplier compliance page, not a company trust page",
        "alarm-com": "/for-home is a product page, not a trust page",
        "alaska-communications": "Residential page, not a trust page",
        "albemarle-corporation": "ethics page, not a company trust page",
        "alcatel-mobile": "hearing-aid compatibility page, not a trust page",
        "albertsons": "HIPAA appears only as covered-entity language in a privacy policy, not an attestation",
    }
    for slug, reason in refused_1027.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-10-27", f"{slug} reaudited 2026-10-27")
        check(row.get("filed") is False, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
    akeneo = entries.get("akeneo") or {}
    check(akeneo.get("filed") is False, "akeneo security page was not filed")
    check(akeneo.get("fileable") is False, "akeneo reads as still 0")
    check(akeneo.get("soft_retry") is True, "akeneo stays a Cloudflare soft-retry")
    check(akeneo.get("refusal") == "/security now Cloudflare 403", f"akeneo refusal {akeneo.get('refusal')}")
    check(not akeneo.get("hit"), "akeneo hit stays empty")

    shipped_1027_pm = {
        "algosec": {"page", "marks"},
        "align-aerospace": {"years"},
    }
    for slug, keys in shipped_1027_pm.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-10-27", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
    check(
        (entries.get("algosec") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.algosec.com/resources/algosec-security-center",
        "algosec security page in ledger",
    )
    check(
        (entries.get("algosec") or {}).get("hit", {}).get("page", {}).get("kind") == "security",
        "algosec page kind is security",
    )
    check(
        set((entries.get("algosec") or {}).get("hit", {}).get("marks", {}).get("added") or [])
        == {"SOC 2 Type II", "ISO 27001"},
        "algosec marks in ledger",
    )
    check(
        (entries.get("align-aerospace") or {}).get("hit", {}).get("years", {}).get("year") == 1972,
        "align-aerospace year in ledger",
    )
    check(
        (entries.get("align-aerospace") or {}).get("hit", {}).get("years", {}).get("url") == "https://alignaero.com/about/",
        "align-aerospace year source in ledger",
    )
    check(not (entries.get("align-aerospace") or {}).get("hit", {}).get("page"), "align-aerospace quality policy stays unfiled")
    check((entries.get("align-aerospace") or {}).get("soft_retry") is True, "align-aerospace oembed shell stays a soft-retry")
    refused_1027_pm = {
        "4ig": "ethics page, not a company trust page",
        "acotel-group": "product page for its security business, not a trust page",
        "alchip": "homepage bounce, not a trust page",
        "alexandria-real-estate-equities": "empty shell, not a trust page",
        "advantech": "certified-solutions page is a product page; about page copyright line is not a founded year",
    }
    for slug, reason in refused_1027_pm.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-10-27", f"{slug} reaudited 2026-10-27")
        check(row.get("filed") is False, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
    acotel = entries.get("acotel-group") or {}
    check(acotel.get("soft_retry") is True, "acotel-group oembed shell stays a soft-retry")

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
    check((pub_accurx.get("file") or {}).get("subprocessors") == 20, "accurx named list stays on file")
    check(
        any((p or {}).get("name") == "Tandem Health AB" for p in (pub_accurx.get("processors") or [])),
        "accurx named processors stay",
    )
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

    pub_meili = by_pub["meilisearch"]
    check(pub_meili.get("certs") == ["SOC 2 Type II"], f"meilisearch marks {pub_meili.get('certs')}")
    check((pub_meili.get("file") or {}).get("marks") == 20, "meilisearch marks print")
    check(pub_meili.get("found") is False, "meilisearch privacy policy is not Official page")

    pub_fire = by_pub["firetext-communications"]
    check(pub_fire.get("found") is True, "firetext Official page is on file")
    check(
        pub_fire.get("trust_url") == "https://www.firetext.co.uk/information-security-statement",
        "firetext Official page URL",
    )
    check(not (pub_fire.get("certs") or []), "firetext ISO wording stays off the marks rule")
    check(pub_fire.get("founded_year") == 2007, "firetext year is first-party about")
    check((pub_fire.get("file") or {}).get("page") == 20, "firetext Official page prints")
    check((pub_fire.get("file") or {}).get("years") == 20, "firetext years print")

    pub_tandem = by_pub["tandem-health"]
    check(
        ((pub_tandem.get("instruments") or {}).get("dpa") or {}).get("url")
        == "https://tandemhealth.ai/legal/data-processing-agreement",
        "tandem DPA URL",
    )
    check(not pub_tandem.get("founded_year"), "tandem /legal/ foundingDate stays off the years rule")
    check(pub_tandem.get("found") is False, "tandem customer story is not Official page")
    check(not (pub_tandem.get("processors") or []), "tandem JS-shell subprocessors stay off file")

    pub_3shape = by_pub["3shape"]
    check(
        [p.get("name") for p in (pub_3shape.get("processors") or [])] == ["Microsoft Ireland Operations, Ltd"],
        f"3shape processors {pub_3shape.get('processors')}",
    )
    check((pub_3shape.get("file") or {}).get("subprocessors") == 20, "3shape named list prints")
    check((pub_3shape.get("file") or {}).get("dpa") == 20, "3shape DPA prints")

    pub_addepar = by_pub["addepar"]
    check(pub_addepar.get("certs") == ["SOC 3"], f"addepar marks {pub_addepar.get('certs')}")
    check(len(pub_addepar.get("processors") or []) == 29, "addepar named list is the printed 29")
    check((pub_addepar.get("file") or {}).get("subprocessors") == 20, "addepar named list prints")

    for slug in ("act-on", "access-communications", "live-nation-entertainment", "docdelta", "zenlayer"):
        check((by_pub[slug].get("file") or {}).get("page") in (0, False, None), f"{slug} Official page stays open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")

    def completeness(row: dict) -> int:
        flags = row.get("file") or {}
        return sum(int(flags.get(k) or 0) for k in FILE_KEYS)

    pub_3cx = by_pub["3cx"]
    check(pub_3cx.get("trust_url") == "https://www.3cx.com/pbx/security/", "3cx Official page")
    check(pub_3cx.get("found") is True, "3cx Official page is on file")
    check(not (pub_3cx.get("certs") or []), "3cx marks stay open")
    check(completeness(pub_3cx) == 30, f"3cx Completeness {completeness(pub_3cx)}")

    pub_ada = by_pub["ada-health"]
    check(pub_ada.get("trust_url") == "https://ada.com/security/", "ada-health Official page")
    check(completeness(pub_ada) == 30, f"ada-health Completeness {completeness(pub_ada)}")

    pub_adv = by_pub["advantest"]
    check(pub_adv.get("founded_year") == 1954, "advantest year is first-party career page")
    check(pub_adv.get("found") is False, "advantest Official page stays open")
    check((pub_adv.get("file") or {}).get("years") == 20, "advantest years print")
    check(completeness(pub_adv) == 20, f"advantest Completeness {completeness(pub_adv)}")

    pub_agiloft = by_pub["agiloft"]
    check(pub_agiloft.get("trust_url") == "https://www.agiloft.com/terms-policies/security", "agiloft Official page")
    check(
        set(pub_agiloft.get("certs") or []) == {"SOC 2 Type II", "SOC 1", "ISO 27001", "ISO 27701", "HIPAA"},
        f"agiloft marks {pub_agiloft.get('certs')}",
    )
    check(
        ((pub_agiloft.get("instruments") or {}).get("dpa") or {}).get("url")
        == "https://www.agiloft.com/terms-policies/data-processing-addendum",
        "agiloft DPA URL",
    )
    check(len(pub_agiloft.get("processors") or []) == 13, "agiloft named list is the printed 13")
    check(pub_agiloft.get("founded_year") == 2003, "agiloft year is first-party home")
    check(completeness(pub_agiloft) == 100, f"agiloft Completeness {completeness(pub_agiloft)}")

    pub_aiforia = by_pub["aiforia-technologies-oyj"]
    check(pub_aiforia.get("trust_url") == "https://www.aiforia.com/security", "aiforia Official page")
    check(
        set(pub_aiforia.get("certs") or []) == {"SOC 2 Type II", "ISO 27001", "ISO 13485", "HIPAA"},
        f"aiforia marks {pub_aiforia.get('certs')}",
    )
    check(completeness(pub_aiforia) == 40, f"aiforia Completeness {completeness(pub_aiforia)}")

    pub_airbnb = by_pub["airbnb"]
    check(pub_airbnb.get("trust_url") == "https://www.airbnb.com/e/security", "airbnb Official page")
    check(not (pub_airbnb.get("certs") or []), "airbnb marks stay open")
    check(completeness(pub_airbnb) == 30, f"airbnb Completeness {completeness(pub_airbnb)}")

    pub_airbyte = by_pub["airbyte"]
    check(
        pub_airbyte.get("trust_url") == "https://airbyte.com/company/request-our-trust-report",
        "airbyte Official page",
    )
    check(
        set(pub_airbyte.get("certs") or []) == {"SOC 2 Type II", "ISO 27001", "CCPA"},
        f"airbyte marks {pub_airbyte.get('certs')}",
    )
    check(completeness(pub_airbyte) == 40, f"airbyte Completeness {completeness(pub_airbyte)}")

    pub_aircall = by_pub["aircall"]
    check(pub_aircall.get("trust_url") == "https://aircall.io/security/", "aircall Official page")
    check(
        set(pub_aircall.get("certs") or []) == {"SOC 2 Type II", "ISO 27001", "HIPAA", "CSA STAR", "GDPR"},
        f"aircall marks {pub_aircall.get('certs')}",
    )
    check(
        ((pub_aircall.get("instruments") or {}).get("dpa") or {}).get("url") == "https://aircall.io/dpa/",
        "aircall DPA URL",
    )
    check(len(pub_aircall.get("processors") or []) == 20, "aircall named list is the printed 20")
    check(pub_aircall.get("founded_year") == 2014, "aircall year is first-party home")
    check(completeness(pub_aircall) == 100, f"aircall Completeness {completeness(pub_aircall)}")

    for slug in ("24slides", "airbus", "ai21"):
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")

    pub_airship = by_pub["airship-ai"]
    check(pub_airship.get("founded_year") == 2006, "airship-ai year is first-party company page")
    check(pub_airship.get("founded_source") == "https://www.airship.ai/company", "airship-ai year source")
    check((pub_airship.get("file") or {}).get("years") == 20, "airship-ai years print")
    check(completeness(pub_airship) == 20, f"airship-ai Completeness {completeness(pub_airship)}")
    check(pub_airship.get("found") is False, "airship-ai Official page stays open")
    check(not (pub_airship.get("certs") or []), "airship-ai marks stay open")

    pub_akai = by_pub["akai"]
    check(pub_akai.get("founded_year") == 1929, "akai year is first-party home")
    check(pub_akai.get("founded_source") == "https://akai.com/", "akai year source")
    check((pub_akai.get("file") or {}).get("years") == 20, "akai years print")
    check(completeness(pub_akai) == 20, f"akai Completeness {completeness(pub_akai)}")
    check(pub_akai.get("found") is False, "akai Official page stays open")
    check(not (pub_akai.get("certs") or []), "akai marks stay open")

    for slug in (
        "airtame",
        "akeneo",
        "aixtron",
        "alarm-com",
        "alaska-communications",
        "albemarle-corporation",
        "alcatel-mobile",
        "albertsons",
    ):
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")

    pub_algosec = by_pub["algosec"]
    check(
        pub_algosec.get("trust_url") == "https://www.algosec.com/resources/algosec-security-center",
        "algosec Official page",
    )
    check(pub_algosec.get("found") is True, "algosec Official page is on file")
    check(
        set(pub_algosec.get("certs") or []) == {"SOC 2 Type II", "ISO 27001"},
        f"algosec marks {pub_algosec.get('certs')}",
    )
    check((pub_algosec.get("file") or {}).get("page") == 20, "algosec Official page prints")
    check((pub_algosec.get("file") or {}).get("marks") == 20, "algosec marks print")
    check(completeness(pub_algosec) == 40, f"algosec Completeness {completeness(pub_algosec)}")
    check(not pub_algosec.get("founded_year"), "algosec year stays open")

    pub_align = by_pub["align-aerospace"]
    check(pub_align.get("founded_year") == 1972, "align-aerospace year is first-party about")
    check(pub_align.get("founded_source") == "https://alignaero.com/about/", "align-aerospace year source")
    check((pub_align.get("file") or {}).get("years") == 20, "align-aerospace years print")
    check(completeness(pub_align) == 20, f"align-aerospace Completeness {completeness(pub_align)}")
    check(pub_align.get("found") is False, "align-aerospace Official page stays open")
    check(not (pub_align.get("certs") or []), "align-aerospace marks stay open")

    for slug in (
        "4ig",
        "acotel-group",
        "advantech",
        "alchip",
        "alexandria-real-estate-equities",
    ):
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")

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
