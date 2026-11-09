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

    batch_1027_pm = [
        "21vianet",
        "2rn",
        "3d-maker-technologies",
        "4ig",
        "a1-telekom-austria-group",
        "abertis",
        "acotel-group",
        "adinstruments",
        "advantech",
        "advista",
        "afrihost",
        "alchip",
        "alcot",
        "aldec",
        "aleph-alpha",
        "alerton",
        "alestra",
        "alexa-internet",
        "alexandria-real-estate-equities",
        "alfresco-software",
        "algar-telecom",
        "algoryx-simulation-ab",
        "algosec",
        "alice",
        "alicesoft",
        "alida",
        "alienware",
        "alight",
        "align-aerospace",
        "aligned-assets",
    ]
    check(len(batch_1027_pm) == 30, f"2026-10-27 afternoon batch is 30, got {len(batch_1027_pm)}")
    check(
        batch_1027_pm[0] == "21vianet" and batch_1027_pm[-1] == "aligned-assets",
        "2026-10-27 afternoon batch is the 21vianet–aligned-assets cut",
    )
    check(all(slug in entries for slug in batch_1027_pm), "2026-10-27 afternoon rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-10-27" for slug in batch_1027_pm),
        "2026-10-27 afternoon cut is dated 2026-10-27",
    )
    check(not set(batch_1027_pm) & set(batch_1026), "2026-10-27 afternoon cut must be never-reaudited vs 24slides–airpair")
    check(not set(batch_1027_pm) & set(batch_1027_am), "2026-10-27 afternoon cut must be never-reaudited vs advacam–alchemy-cms")

    batch_1028 = [
        "a1-hrvatska",
        "africell-uganda",
        "airtel-kenya",
        "airtel-sri-lanka",
        "akhali-kselebi",
        "al-yah-satellite-communications",
        "alfa",
        "alinean",
        "alkami",
        "allbusiness-com",
        "allegiance",
        "allego",
        "allegorithmic",
        "allegro-development-corporation",
        "allen-brothers",
        "allen-institute-for-ai",
        "allgeier-se",
        "alliant-energy",
        "alliantis",
        "allied-van-lines",
        "allo",
        "allot",
        "allstate",
        "allstream-inc",
        "almawave",
        "alpes-lasers",
        "alphabet",
        "alphabet-energy",
        "alphawest",
        "altacast",
    ]
    check(len(batch_1028) == 30, f"2026-10-28 batch is 30, got {len(batch_1028)}")
    check(
        batch_1028[0] == "a1-hrvatska" and batch_1028[-1] == "altacast",
        "2026-10-28 batch is the a1-hrvatska–altacast cut",
    )
    check(all(slug in entries for slug in batch_1028), "2026-10-28 rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-10-28" for slug in batch_1028),
        "2026-10-28 cut is dated 2026-10-28",
    )
    check(not set(batch_1028) & set(batch_1026), "2026-10-28 cut must be never-reaudited vs 24slides–airpair")
    check(not set(batch_1028) & set(batch_1027_am), "2026-10-28 cut must be never-reaudited vs advacam–alchemy-cms")
    check(not set(batch_1028) & set(batch_1027_pm), "2026-10-28 cut must be never-reaudited vs 21vianet–aligned-assets")

    batch_1029_am = [
        "altair-engineering",
        "alterface",
        "alterg",
        "altergeo",
        "altexchange",
        "althio",
        "altice",
        "altice-portugal",
        "alticom",
        "altinity",
        "altor-networks",
        "altoros",
        "altos-design-automation",
        "altova",
        "altria",
        "altspacevr",
        "alvaria",
        "alvarion",
        "alvion",
        "amalto",
        "amazon-lab126",
        "ambu",
        "amco-burglar-alarm-company",
        "amebis",
        "ameren",
        "american-airlines-group",
        "american-book-company",
        "american-electric-power",
        "american-express",
        "american-sammy",
    ]
    check(len(batch_1029_am) == 30, f"2026-10-29 morning batch is 30, got {len(batch_1029_am)}")
    check(
        batch_1029_am[0] == "altair-engineering" and batch_1029_am[-1] == "american-sammy",
        "2026-10-29 morning batch is the altair-engineering–american-sammy cut",
    )
    check(all(slug in entries for slug in batch_1029_am), "2026-10-29 morning rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-10-29" for slug in batch_1029_am),
        "2026-10-29 morning cut is dated 2026-10-29",
    )
    check(not set(batch_1029_am) & set(batch_1026), "2026-10-29 morning cut must be never-reaudited vs 24slides–airpair")
    check(not set(batch_1029_am) & set(batch_1027_am), "2026-10-29 morning cut must be never-reaudited vs advacam–alchemy-cms")
    check(not set(batch_1029_am) & set(batch_1027_pm), "2026-10-29 morning cut must be never-reaudited vs 21vianet–aligned-assets")
    check(not set(batch_1029_am) & set(batch_1028), "2026-10-29 morning cut must be never-reaudited vs a1-hrvatska–altacast")

    batch_1029_pm = [
        "american-tower",
        "ameriprise-financial",
        "ametek",
        "amey",
        "amgen",
        "amis",
        "amita-health",
        "amkette",
        "amlogic",
        "amnezia-vpn",
        "amoco",
        "amoi",
        "ampere-computing",
        "amphenol",
        "amplidata",
        "alexander-mann-solutions",
        "amtd-digital",
        "amtel",
        "amtelco",
        "amwell",
        "amy-s-candy-bar",
        "am-rica-m-vil",
        "anacomp",
        "analog-devices",
        "analogue",
        "ancestry-com",
        "anchorfree",
        "ancient",
        "andesite-ai",
        "andor-technology",
    ]
    check(len(batch_1029_pm) == 30, f"2026-10-29 afternoon batch is 30, got {len(batch_1029_pm)}")
    check(
        batch_1029_pm[0] == "american-tower" and batch_1029_pm[-1] == "andor-technology",
        "2026-10-29 afternoon batch is the american-tower–andor-technology cut",
    )
    check("amgen" in batch_1029_pm and "andor-technology" in batch_1029_pm, "afternoon cut covers amgen..andor-technology")
    check(all(slug in entries for slug in batch_1029_pm), "2026-10-29 afternoon rows stay in the ledger")
    october = [slug for slug, rec in entries.items() if str(rec.get("date") or "").startswith("2026-10-")]
    check(len(october) == 330, f"10/22 through 10/30 afternoon cuts stay in the ledger, got {len(october)}")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-10-29" for slug in batch_1029_pm),
        "2026-10-29 afternoon cut is dated 2026-10-29",
    )
    check(not set(batch_1029_pm) & set(batch_1026), "2026-10-29 afternoon cut must be never-reaudited vs 24slides–airpair")
    check(not set(batch_1029_pm) & set(batch_1027_am), "2026-10-29 afternoon cut must be never-reaudited vs advacam–alchemy-cms")
    check(not set(batch_1029_pm) & set(batch_1027_pm), "2026-10-29 afternoon cut must be never-reaudited vs 21vianet–aligned-assets")
    check(not set(batch_1029_pm) & set(batch_1028), "2026-10-29 afternoon cut must be never-reaudited vs a1-hrvatska–altacast")
    check(not set(batch_1029_pm) & set(batch_1029_am), "2026-10-29 afternoon cut must be never-reaudited vs altair-engineering–american-sammy")
    soft_classes = {"http-403", "js-shell", "cloudflare"}
    for slug in batch_1029_pm:
        row = entries.get(slug) or {}
        if row.get("soft_retry"):
            probed_classes = {item.get("class") for item in (row.get("probed") or [])}
            check(bool(probed_classes & soft_classes), f"{slug} soft-retry is marked")
        if slug in {"amgen", "ancestry-com"}:
            check(row.get("filed") is True, f"{slug} ledger row records the apply")
            continue
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")

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

    shipped_1028 = {
        "alkami": {"years"},
        "allied-van-lines": {"marks"},
    }
    for slug, keys in shipped_1028.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-10-28", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
    check((entries.get("alkami") or {}).get("hit", {}).get("years", {}).get("year") == 2009, "alkami year in ledger")
    check(
        (entries.get("alkami") or {}).get("hit", {}).get("years", {}).get("url") == "https://www.alkami.com/press-room",
        "alkami year source in ledger",
    )
    check(
        (entries.get("alkami") or {}).get("hit", {}).get("years", {}).get("quote")
        == "Founded in 2009 by current Chief Strategy Officer, Stephen Bohanon and partners, Alkami Technology, Inc.",
        "alkami year quote is the press-room sentence",
    )
    check(not (entries.get("alkami") or {}).get("hit", {}).get("page"), "alkami demo marketing page stays unfiled")
    check((entries.get("alkami") or {}).get("soft_retry") is True, "alkami shell stays a soft-retry")
    check(
        ((entries.get("allied-van-lines") or {}).get("hit") or {}).get("marks", {}).get("added") == ["EU-US DPF"],
        "allied-van-lines EU-US DPF in ledger",
    )
    check(
        ((entries.get("allied-van-lines") or {}).get("hit") or {}).get("marks", {}).get("url")
        == "https://www.allied.com/privacy-policy",
        "allied-van-lines mark source in ledger",
    )
    refused_1028 = {
        "allbusiness-com": "third-party article, not a company security page",
        "allego": "/trust/ now Cloudflare 403",
        "allot": "log4j advisory PDF, not a company security page",
    }
    for slug, reason in refused_1028.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-10-28", f"{slug} reaudited 2026-10-28")
        check(row.get("filed") is False, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
    allego = entries.get("allego") or {}
    check(allego.get("soft_retry") is True, "allego /trust/ stays a Cloudflare soft-retry")

    shipped_1029 = {
        "ambu": {"years"},
        "american-express": {"years"},
    }
    for slug, keys in shipped_1029.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-10-29", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
    check((entries.get("ambu") or {}).get("hit", {}).get("years", {}).get("year") == 1937, "ambu year in ledger")
    check(
        (entries.get("ambu") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://www.ambu.com/about/our-history",
        "ambu year source in ledger",
    )
    check(
        (entries.get("ambu") or {}).get("hit", {}).get("years", {}).get("quote")
        == "That man was engineer Holger Hesse, who founded Ambu in 1937.",
        "ambu year quote is the history sentence",
    )
    check(
        (entries.get("american-express") or {}).get("hit", {}).get("years", {}).get("year") == 1850,
        "american-express year in ledger",
    )
    check(
        (entries.get("american-express") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://ir.americanexpress.com/investor-relations/default.aspx",
        "american-express year source in ledger",
    )
    check(
        (entries.get("american-express") or {}).get("hit", {}).get("years", {}).get("quote")
        == "Founded in 1850 and headquartered in New York, American Express has a heritage built on service and sustained by innovation.",
        "american-express year quote is the investor-relations sentence",
    )
    check(
        not (entries.get("american-express") or {}).get("hit", {}).get("page"),
        "american-express consumer security center stays unfiled",
    )
    check(
        (entries.get("american-express") or {}).get("soft_retry") is True,
        "american-express shell stays a soft-retry",
    )
    refused_1029 = {
        "altice": "site maintenance placeholder",
        "alvion": "empty body",
        "altinity": "SIEM product page",
        "amco-burglar-alarm-company": "product page",
        "alterg": "our-story now Cloudflare 403",
        "altova": "healthcare-compliance page and HIPAA mark are product marketing, not an attestation; DPA re-fetch did not return 200",
    }
    for slug, reason in refused_1029.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-10-29", f"{slug} reaudited 2026-10-29")
        check(row.get("filed") is False, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
    alterg = entries.get("alterg") or {}
    check(alterg.get("soft_retry") is True, "alterg our-story stays a Cloudflare soft-retry")

    shipped_1029_pm = {
        "amgen": {"years"},
        "ancestry-com": {"page"},
    }
    for slug, keys in shipped_1029_pm.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-10-29", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
    check((entries.get("amgen") or {}).get("hit", {}).get("years", {}).get("year") == 1980, "amgen year in ledger")
    check(
        (entries.get("amgen") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://www.amgen.com/about/amgen-history",
        "amgen year source in ledger",
    )
    check(
        (entries.get("amgen") or {}).get("hit", {}).get("years", {}).get("quote")
        == ") is established in Thousand Oaks, California, on April 8, 1980, as the brainchild of venture capitalists William K.",
        "amgen year quote is the history sentence",
    )
    check(
        "established in Thousand Oaks, California, on April 8, 1980"
        in ((entries.get("amgen") or {}).get("hit", {}).get("years", {}).get("quote") or ""),
        "amgen quote names the April 8, 1980 establishment",
    )
    check(not (entries.get("amgen") or {}).get("hit", {}).get("page"), "amgen Official page stays unfiled")
    check(
        (entries.get("ancestry-com") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.ancestry.com/c/legal/security",
        "ancestry security page in ledger",
    )
    check(
        (entries.get("ancestry-com") or {}).get("hit", {}).get("page", {}).get("kind") == "security",
        "ancestry page kind is security",
    )
    check(
        (entries.get("ancestry-com") or {}).get("soft_retry") is True,
        "ancestry shell stays a soft-retry",
    )
    check(not (entries.get("ancestry-com") or {}).get("hit", {}).get("marks"), "ancestry marks stay unfiled")
    check(not (entries.get("ancestry-com") or {}).get("hit", {}).get("years"), "ancestry year stays unfiled")
    refused_1029_pm = {
        "am-rica-m-vil": "overview page is not a security page",
        "amkette": "about-us founding year left unfiled; not in this cut's vetted holds",
        "anacomp": "HIPAA on the zero-trust product page is a product marketing claim, not an attestation",
    }
    for slug, reason in refused_1029_pm.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-10-29", f"{slug} reaudited 2026-10-29")
        check(row.get("filed") is False, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
    check((entries.get("am-rica-m-vil") or {}).get("soft_retry") is True, "am-rica-m-vil stays a soft-retry")
    check((entries.get("anacomp") or {}).get("soft_retry") is True, "anacomp oembed shell stays a soft-retry")
    check((entries.get("amkette") or {}).get("soft_retry") is not True, "amkette about page was readable")

    batch_1030_am = [
        "anduril-industries",
        "angel-learning",
        "angelpad",
        "angi-homeservices-inc",
        "angoss",
        "animoca-brands",
        "animoto",
        "animusic",
        "ankama",
        "anomali",
        "anonymizer",
        "anoto",
        "anro",
        "answerconnect",
        "answerdash",
        "antec",
        "antel",
        "antithesis",
        "anybots",
        "anystream",
        "aoc-international",
        "aol",
        "aon-plc",
        "aopen",
        "apa-corporation",
        "apacer",
        "apadmi-ltd",
        "apc-by-schneider-electric",
        "apcera",
        "apex-learning",
    ]
    check(len(batch_1030_am) == 30, f"2026-10-30 morning batch is 30, got {len(batch_1030_am)}")
    check(
        batch_1030_am[0] == "anduril-industries" and batch_1030_am[-1] == "apex-learning",
        "2026-10-30 morning batch is the anduril-industries–apex-learning cut",
    )
    check("animoca-brands" in batch_1030_am and "apex-learning" in batch_1030_am, "morning cut covers animoca-brands..apex-learning")
    check(all(slug in entries for slug in batch_1030_am), "2026-10-30 morning rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-10-30" for slug in batch_1030_am),
        "2026-10-30 morning cut is dated 2026-10-30",
    )
    check(not set(batch_1030_am) & set(batch_1026), "2026-10-30 morning cut must be never-reaudited vs 24slides–airpair")
    check(not set(batch_1030_am) & set(batch_1027_am), "2026-10-30 morning cut must be never-reaudited vs advacam–alchemy-cms")
    check(not set(batch_1030_am) & set(batch_1027_pm), "2026-10-30 morning cut must be never-reaudited vs 21vianet–aligned-assets")
    check(not set(batch_1030_am) & set(batch_1028), "2026-10-30 morning cut must be never-reaudited vs a1-hrvatska–altacast")
    check(not set(batch_1030_am) & set(batch_1029_am), "2026-10-30 morning cut must be never-reaudited vs altair-engineering–american-sammy")
    check(not set(batch_1030_am) & set(batch_1029_pm), "2026-10-30 morning cut must be never-reaudited vs american-tower–andor-technology")
    for slug in batch_1030_am:
        row = entries.get(slug) or {}
        if row.get("soft_retry"):
            probed_classes = {item.get("class") for item in (row.get("probed") or [])}
            check(bool(probed_classes & soft_classes) or slug == "animoca-brands", f"{slug} soft-retry is marked")
        if slug in {"anomali", "anro", "antec", "antithesis"}:
            check(row.get("filed") is True, f"{slug} ledger row records the apply")
            continue
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")

    shipped_1030 = {
        "anomali": {"page"},
        "anro": {"marks"},
        "antec": {"years"},
        "antithesis": {"page"},
    }
    for slug, keys in shipped_1030.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-10-30", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
    check(
        (entries.get("anomali") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.anomali.com/security",
        "anomali security page in ledger",
    )
    check(
        (entries.get("anomali") or {}).get("hit", {}).get("page", {}).get("kind") == "security",
        "anomali page kind is security",
    )
    check(not (entries.get("anomali") or {}).get("hit", {}).get("marks"), "anomali marks stay unfiled")
    check(not (entries.get("anomali") or {}).get("hit", {}).get("years"), "anomali year stays unfiled")
    check(
        ((entries.get("anro") or {}).get("hit") or {}).get("marks", {}).get("added")
        == ["SOC 2 Type II", "PCI DSS"],
        "anro marks in ledger",
    )
    check(
        ((entries.get("anro") or {}).get("hit") or {}).get("marks", {}).get("url")
        == "https://www.anro.com/privacy-policy",
        "anro mark source in ledger",
    )
    check(
        "SOC 2 Type II certified PCI DSS compliant"
        in (((entries.get("anro") or {}).get("hit") or {}).get("marks", {}).get("quote") or ""),
        "anro quote names SOC 2 Type II and PCI DSS",
    )
    check("HIPAA" not in (((entries.get("anro") or {}).get("hit") or {}).get("marks", {}).get("added") or []), "anro HIPAA stays off the filed marks")
    check((entries.get("antec") or {}).get("hit", {}).get("years", {}).get("year") == 1986, "antec year in ledger")
    check(
        (entries.get("antec") or {}).get("hit", {}).get("years", {}).get("url") == "https://antec.com/aboutus",
        "antec year source in ledger",
    )
    check(
        (entries.get("antec") or {}).get("hit", {}).get("years", {}).get("quote")
        == "Founded in 1986, Antec is recognized as a pioneer in the industry and has maintained its position as a worldwide market leader and international provider of quiet, efficient and innovative products.",
        "antec year quote is the about sentence",
    )
    check(not (entries.get("antec") or {}).get("hit", {}).get("page"), "antec Official page stays unfiled")
    check(
        (entries.get("antithesis") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://antithesis.com/security/manifesto/",
        "antithesis security page in ledger",
    )
    check(
        (entries.get("antithesis") or {}).get("hit", {}).get("page", {}).get("kind") == "security",
        "antithesis page kind is security",
    )
    check(not (entries.get("antithesis") or {}).get("hit", {}).get("marks"), "antithesis marks stay unfiled")
    check(not (entries.get("antithesis") or {}).get("hit", {}).get("years"), "antithesis year stays unfiled")
    refused_1030 = {
        "animoca-brands": "homepage now Cloudflare 403",
        "aon-plc": "homepage bounce on every path",
        "apex-learning": "/trust is a JS redirect to edmentum.com, not first-party content",
    }
    for slug, reason in refused_1030.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-10-30", f"{slug} reaudited 2026-10-30")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
    check((entries.get("animoca-brands") or {}).get("soft_retry") is True, "animoca-brands homepage stays a Cloudflare soft-retry")
    check((entries.get("aon-plc") or {}).get("soft_retry") is not True, "aon-plc homepage bounce is a miss")
    check((entries.get("apex-learning") or {}).get("soft_retry") is not True, "apex-learning redirect is a miss")

    batch_1030_pm = [
        "apigee",
        "apilayer",
        "apm-automation-solutions",
        "apollo-global-management",
        "appcelerator",
        "appcircle",
        "appdynamics",
        "apperian",
        "appfolio",
        "appirio",
        "appland",
        "applied-industrial-technologies",
        "applied-instruments",
        "applied-materials",
        "applied-predictive-technologies",
        "applied-spectral-imaging",
        "applovin",
        "applyboard",
        "appneta",
        "appnexus",
        "appnovation",
        "appota-corporation",
        "appsbuilder",
        "apptio",
        "appy-entertainment",
        "apricity-group",
        "aprimo",
        "aptech",
        "apteligent",
        "aptilo-networks",
    ]
    check(len(batch_1030_pm) == 30, f"2026-10-30 afternoon batch is 30, got {len(batch_1030_pm)}")
    check(
        batch_1030_pm[0] == "apigee" and batch_1030_pm[-1] == "aptilo-networks",
        "2026-10-30 afternoon batch is the apigee–aptilo-networks cut",
    )
    check("apollo-global-management" in batch_1030_pm and "aptilo-networks" in batch_1030_pm, "afternoon cut covers apollo-global-management..aptilo-networks")
    check(all(slug in entries for slug in batch_1030_pm), "2026-10-30 afternoon rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-10-30" for slug in batch_1030_pm),
        "2026-10-30 afternoon cut is dated 2026-10-30",
    )
    check(not set(batch_1030_pm) & set(batch_1026), "2026-10-30 afternoon cut must be never-reaudited vs 24slides–airpair")
    check(not set(batch_1030_pm) & set(batch_1027_am), "2026-10-30 afternoon cut must be never-reaudited vs advacam–alchemy-cms")
    check(not set(batch_1030_pm) & set(batch_1027_pm), "2026-10-30 afternoon cut must be never-reaudited vs 21vianet–aligned-assets")
    check(not set(batch_1030_pm) & set(batch_1028), "2026-10-30 afternoon cut must be never-reaudited vs a1-hrvatska–altacast")
    check(not set(batch_1030_pm) & set(batch_1029_am), "2026-10-30 afternoon cut must be never-reaudited vs altair-engineering–american-sammy")
    check(not set(batch_1030_pm) & set(batch_1029_pm), "2026-10-30 afternoon cut must be never-reaudited vs american-tower–andor-technology")
    check(not set(batch_1030_pm) & set(batch_1030_am), "2026-10-30 afternoon cut must be never-reaudited vs anduril-industries–apex-learning")
    for slug in batch_1030_pm:
        row = entries.get(slug) or {}
        if row.get("soft_retry"):
            probed_classes = {item.get("class") for item in (row.get("probed") or [])}
            check(bool(probed_classes & soft_classes), f"{slug} soft-retry is marked")
        if slug in {"apollo-global-management", "appcircle", "applyboard", "apptio"}:
            check(row.get("filed") is True, f"{slug} ledger row records the apply")
            continue
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")

    shipped_1030_pm = {
        "apollo-global-management": {"years"},
        "appcircle": {"page"},
        "applyboard": {"page"},
        "apptio": {"page"},
    }
    for slug, keys in shipped_1030_pm.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-10-30", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
    check((entries.get("apollo-global-management") or {}).get("hit", {}).get("years", {}).get("year") == 1990, "apollo year in ledger")
    check(
        (entries.get("apollo-global-management") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://www.apollo.com/aboutus",
        "apollo year source in ledger",
    )
    check(
        (entries.get("apollo-global-management") or {}).get("hit", {}).get("years", {}).get("quote")
        == "Since our founding in 1990, we have believed that adhering to our values is integral to our success.",
        "apollo year quote is the about sentence",
    )
    check(not (entries.get("apollo-global-management") or {}).get("hit", {}).get("page"), "apollo Official page stays unfiled")
    check(not (entries.get("apollo-global-management") or {}).get("hit", {}).get("marks"), "apollo marks stay unfiled")
    check(
        (entries.get("appcircle") or {}).get("hit", {}).get("page", {}).get("url") == "https://appcircle.io/security",
        "appcircle security page in ledger",
    )
    check(
        (entries.get("appcircle") or {}).get("hit", {}).get("page", {}).get("kind") == "security",
        "appcircle page kind is security",
    )
    check(not (entries.get("appcircle") or {}).get("hit", {}).get("marks"), "appcircle marks stay unfiled")
    check(not (entries.get("appcircle") or {}).get("hit", {}).get("years"), "appcircle year stays unfiled")
    check(
        (entries.get("applyboard") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.applyboard.com/security",
        "applyboard security page in ledger",
    )
    check(
        (entries.get("applyboard") or {}).get("hit", {}).get("page", {}).get("kind") == "security",
        "applyboard page kind is security",
    )
    check(not (entries.get("applyboard") or {}).get("hit", {}).get("marks"), "applyboard SOC 2 stays unfiled")
    check(not (entries.get("applyboard") or {}).get("hit", {}).get("years"), "applyboard year stays unfiled")
    check((entries.get("applyboard") or {}).get("soft_retry") is True, "applyboard shell paths stay a soft-retry")
    check(
        (entries.get("apptio") or {}).get("hit", {}).get("page", {}).get("url") == "https://www.apptio.com/company/trust/",
        "apptio trust page in ledger",
    )
    check(
        (entries.get("apptio") or {}).get("hit", {}).get("page", {}).get("kind") == "trust",
        "apptio page kind is trust",
    )
    check(not (entries.get("apptio") or {}).get("hit", {}).get("marks"), "apptio marks stay unfiled")
    check(not (entries.get("apptio") or {}).get("hit", {}).get("years"), "apptio year stays unfiled")
    refused_1030_pm = {
        "applovin": "every path bounces to the homepage https://applovin.com/en",
        "appota-corporation": (
            '/trust is a ~5 KB SPA shell titled "Appota - Entertainment Ecosystem"; '
            "every path returns 200, catch-all"
        ),
        "aprimo": "/dpa timed out, site returns 500 on most paths; soft-retry",
    }
    for slug, reason in refused_1030_pm.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-10-30", f"{slug} reaudited 2026-10-30")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
    check((entries.get("applovin") or {}).get("soft_retry") is not True, "applovin homepage bounce is a miss")
    check((entries.get("appota-corporation") or {}).get("soft_retry") is not True, "appota catch-all shell is not a fetch soft-retry")
    check((entries.get("aprimo") or {}).get("soft_retry") is True, "aprimo stays a soft-retry")

    batch_1102_am = [
        "aptiv",
        "aptos-labs",
        "aptum-technologies",
        "aquaplus",
        "aquaver",
        "aquria",
        "arab-satellite-communications-organization",
        "arbitersports",
        "arcade1up",
        "arcee-ai",
        "arch-capital-group",
        "archax",
        "archer-daniels-midland",
        "archon-information-systems",
        "archos",
        "arcor",
        "arcos-llc",
        "arcserve",
        "arcsoft",
        "arctic-gmbh",
        "arctic-silver",
        "arctic-trucks",
        "ardence",
        "area-1-security",
        "arecont-vision",
        "ares-management",
        "argela",
        "argentonia",
        "argon-st",
        "argonide",
    ]
    check(len(batch_1102_am) == 30, f"2026-11-02 morning batch is 30, got {len(batch_1102_am)}")
    check(
        batch_1102_am[0] == "aptiv" and batch_1102_am[-1] == "argonide",
        "2026-11-02 morning batch is the aptiv–argonide cut",
    )
    check("aptos-labs" in batch_1102_am and "argonide" in batch_1102_am, "morning cut covers aptiv..argonide")
    check(all(slug in entries for slug in batch_1102_am), "2026-11-02 morning rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-11-02" for slug in batch_1102_am),
        "2026-11-02 morning cut is dated 2026-11-02",
    )
    check(not set(batch_1102_am) & set(batch_1026), "2026-11-02 morning cut must be never-reaudited vs 24slides–airpair")
    check(not set(batch_1102_am) & set(batch_1027_am), "2026-11-02 morning cut must be never-reaudited vs advacam–alchemy-cms")
    check(not set(batch_1102_am) & set(batch_1027_pm), "2026-11-02 morning cut must be never-reaudited vs 21vianet–aligned-assets")
    check(not set(batch_1102_am) & set(batch_1028), "2026-11-02 morning cut must be never-reaudited vs a1-hrvatska–altacast")
    check(not set(batch_1102_am) & set(batch_1029_am), "2026-11-02 morning cut must be never-reaudited vs altair-engineering–american-sammy")
    check(not set(batch_1102_am) & set(batch_1029_pm), "2026-11-02 morning cut must be never-reaudited vs american-tower–andor-technology")
    check(not set(batch_1102_am) & set(batch_1030_am), "2026-11-02 morning cut must be never-reaudited vs anduril-industries–apex-learning")
    check(not set(batch_1102_am) & set(batch_1030_pm), "2026-11-02 morning cut must be never-reaudited vs apigee–aptilo-networks")
    shipped_1102 = {
        "aptiv": {"page", "marks"},
        "aptos-labs": {"years"},
        "arcserve": {"years"},
        "arctic-gmbh": {"years"},
        "argonide": {"page"},
    }
    for slug in batch_1102_am:
        row = entries.get(slug) or {}
        if row.get("soft_retry"):
            probed_classes = {item.get("class") for item in (row.get("probed") or [])}
            check(bool(probed_classes & soft_classes), f"{slug} soft-retry is marked")
        if slug in shipped_1102:
            check(row.get("filed") is True, f"{slug} ledger row records the apply")
            continue
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
    for slug, keys in shipped_1102.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-11-02", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
    check(
        (entries.get("aptiv") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://win.aptiv.com/locations-and-certifications",
        "aptiv certifications page in ledger",
    )
    check(
        (entries.get("aptiv") or {}).get("hit", {}).get("page", {}).get("kind") == "trust",
        "aptiv page kind is trust",
    )
    check(
        ((entries.get("aptiv") or {}).get("hit") or {}).get("marks", {}).get("added")
        == ["ISO 13485", "ISO 9001"],
        "aptiv marks in ledger",
    )
    check(
        ((entries.get("aptiv") or {}).get("hit") or {}).get("marks", {}).get("url")
        == "https://win.aptiv.com/locations-and-certifications",
        "aptiv mark source in ledger",
    )
    check(
        "ISO 13485:2016" in (((entries.get("aptiv") or {}).get("hit") or {}).get("marks", {}).get("quote") or ""),
        "aptiv quote names ISO 13485",
    )
    check(
        "ISO 9001:2015" in (((entries.get("aptiv") or {}).get("hit") or {}).get("marks", {}).get("quote") or ""),
        "aptiv quote names ISO 9001",
    )
    check(not (entries.get("aptiv") or {}).get("hit", {}).get("years"), "aptiv year stays unfiled")
    check((entries.get("aptos-labs") or {}).get("hit", {}).get("years", {}).get("year") == 2022, "aptos-labs year in ledger")
    check(
        (entries.get("aptos-labs") or {}).get("hit", {}).get("years", {}).get("url") == "https://aptoslabs.com/",
        "aptos-labs year source in ledger",
    )
    check(
        (entries.get("aptos-labs") or {}).get("hit", {}).get("years", {}).get("quote")
        == "January 2022 Aptos Labs was founded to fulfill the vision of bringing fair access to decentralization to all.",
        "aptos-labs year quote is the home sentence",
    )
    check(not (entries.get("aptos-labs") or {}).get("hit", {}).get("page"), "aptos-labs Official page stays unfiled")
    check((entries.get("arcserve") or {}).get("hit", {}).get("years", {}).get("year") == 1983, "arcserve year in ledger")
    check(
        (entries.get("arcserve") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://www.arcserve.com/privacy-notice",
        "arcserve year source in ledger",
    )
    check(
        (entries.get("arcserve") or {}).get("hit", {}).get("years", {}).get("quote")
        == "Founded in 1983, Arcserve provides comprehensive solutions for virtual and physical environments, on premise or in the cloud.",
        "arcserve year quote is the privacy-notice sentence",
    )
    check(not (entries.get("arcserve") or {}).get("hit", {}).get("page"), "arcserve Official page stays unfiled")
    check((entries.get("arctic-gmbh") or {}).get("hit", {}).get("years", {}).get("year") == 2001, "arctic-gmbh year in ledger")
    check(
        (entries.get("arctic-gmbh") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://www.arctic.de/us/about-arctic/locations",
        "arctic-gmbh year source in ledger",
    )
    check(
        (entries.get("arctic-gmbh") or {}).get("hit", {}).get("years", {}).get("quote")
        == "Since its founding in 2001, ARCTIC has continually evolved, and this growth is reflected in its locations.",
        "arctic-gmbh year quote is the locations sentence",
    )
    check(not (entries.get("arctic-gmbh") or {}).get("hit", {}).get("page"), "arctic-gmbh homepage bounce stays unfiled")
    check(not (entries.get("arctic-gmbh") or {}).get("hit", {}).get("marks"), "arctic-gmbh marks stay unfiled")
    check(
        (entries.get("argonide") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.argonide.com/about-argonide-water-filter-manufacturing/iso-9001-certified",
        "argonide certifications page in ledger",
    )
    check(
        (entries.get("argonide") or {}).get("hit", {}).get("page", {}).get("kind") == "trust",
        "argonide page kind is trust",
    )
    check(not (entries.get("argonide") or {}).get("hit", {}).get("marks"), "argonide marks stay unfiled")
    check(not (entries.get("argonide") or {}).get("hit", {}).get("years"), "argonide year stays unfiled")
    refused_1102 = {
        "aptum-technologies": "security services product page and marketing compliance claim, not own posture",
        "archax": "/security is a 1.5KB JS shell",
        "archer-daniels-midland": "supplier non-compliance procedure, not a trust page",
        "arecont-vision": "2018 is founding of successor entity Arecont Vision Costar, ambiguous",
    }
    for slug, reason in refused_1102.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-11-02", f"{slug} reaudited 2026-11-02")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
    check((entries.get("aptum-technologies") or {}).get("soft_retry") is True, "aptum-technologies probe stays a Cloudflare soft-retry")
    check((entries.get("archax") or {}).get("soft_retry") is not True, "archax JS shell was not a fetch soft-retry class")
    check((entries.get("archer-daniels-midland") or {}).get("soft_retry") is not True, "archer-daniels-midland supplier page is a miss")
    check((entries.get("arecont-vision") or {}).get("soft_retry") is not True, "arecont-vision successor year is a miss")

    batch_1102_pm = [
        "argotec",
        "aricent",
        "ariel-investments",
        "aries-telecoms",
        "arika",
        "arise-india",
        "arkeia-software",
        "arkova",
        "armslist",
        "arqiva",
        "array-networks",
        "arraycomm",
        "arrayfire",
        "artec-3d",
        "artemis-technologies",
        "artepiazza",
        "arteris",
        "arthur-j-gallagher-and-co",
        "artis-llc",
        "aruba-s-p-a",
        "arx",
        "arxan-technologies",
        "as-starman",
        "asahi-kasei",
        "asbis",
        "ascend-integrated-technology-solutions",
        "ascii-group",
        "ascon",
        "aselsan",
        "asg-technologies",
    ]
    check(len(batch_1102_pm) == 30, f"2026-11-02 afternoon batch is 30, got {len(batch_1102_pm)}")
    check(
        batch_1102_pm[0] == "argotec" and batch_1102_pm[-1] == "asg-technologies",
        "2026-11-02 afternoon batch is the argotec–asg-technologies cut",
    )
    check("ariel-investments" in batch_1102_pm and "ascon" in batch_1102_pm, "afternoon cut covers argotec..asg-technologies")
    check(all(slug in entries for slug in batch_1102_pm), "2026-11-02 afternoon rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-11-02" for slug in batch_1102_pm),
        "2026-11-02 afternoon cut is dated 2026-11-02",
    )
    check(not set(batch_1102_pm) & set(batch_1026), "2026-11-02 afternoon cut must be never-reaudited vs 24slides–airpair")
    check(not set(batch_1102_pm) & set(batch_1027_am), "2026-11-02 afternoon cut must be never-reaudited vs advacam–alchemy-cms")
    check(not set(batch_1102_pm) & set(batch_1027_pm), "2026-11-02 afternoon cut must be never-reaudited vs 21vianet–aligned-assets")
    check(not set(batch_1102_pm) & set(batch_1028), "2026-11-02 afternoon cut must be never-reaudited vs a1-hrvatska–altacast")
    check(not set(batch_1102_pm) & set(batch_1029_am), "2026-11-02 afternoon cut must be never-reaudited vs altair-engineering–american-sammy")
    check(not set(batch_1102_pm) & set(batch_1029_pm), "2026-11-02 afternoon cut must be never-reaudited vs american-tower–andor-technology")
    check(not set(batch_1102_pm) & set(batch_1030_am), "2026-11-02 afternoon cut must be never-reaudited vs anduril-industries–apex-learning")
    check(not set(batch_1102_pm) & set(batch_1030_pm), "2026-11-02 afternoon cut must be never-reaudited vs apigee–aptilo-networks")
    check(not set(batch_1102_pm) & set(batch_1102_am), "2026-11-02 afternoon cut must be never-reaudited vs aptiv–argonide")
    shipped_1102_pm = {
        "argotec": {"marks", "years"},
        "ariel-investments": {"years"},
        "aruba-s-p-a": {"marks", "years"},
        "asbis": {"page", "marks"},
        "ascon": {"years"},
    }
    clerk_soft_1102_pm = {"array-networks", "arthur-j-gallagher-and-co"}
    for slug in batch_1102_pm:
        row = entries.get(slug) or {}
        if row.get("soft_retry") and slug not in clerk_soft_1102_pm:
            probed_classes = {item.get("class") for item in (row.get("probed") or [])}
            check(bool(probed_classes & soft_classes), f"{slug} soft-retry is marked")
        if slug in shipped_1102_pm:
            check(row.get("filed") is True, f"{slug} ledger row records the apply")
            continue
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
    for slug, keys in shipped_1102_pm.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-11-02", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
    check(
        ((entries.get("argotec") or {}).get("hit") or {}).get("marks", {}).get("added") == ["ISO 9001"],
        "argotec marks in ledger",
    )
    check(
        "ISO 27001" not in (((entries.get("argotec") or {}).get("hit") or {}).get("marks", {}).get("added") or []),
        "argotec ISO 27001 stays unfiled",
    )
    check(
        ((entries.get("argotec") or {}).get("hit") or {}).get("marks", {}).get("url")
        == "https://www.argotecgroup.com/privacy-policy",
        "argotec mark source in ledger",
    )
    check(
        "ISO 9001:2015" in (((entries.get("argotec") or {}).get("hit") or {}).get("marks", {}).get("quote") or ""),
        "argotec quote names ISO 9001",
    )
    check((entries.get("argotec") or {}).get("hit", {}).get("years", {}).get("year") == 2008, "argotec year in ledger")
    check(
        (entries.get("argotec") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://www.argotecgroup.com/privacy-policy",
        "argotec year source in ledger",
    )
    check(
        (entries.get("argotec") or {}).get("hit", {}).get("years", {}).get("quote") == '"foundingDate":"2008"',
        "argotec year quote is the JSON-LD foundingDate",
    )
    check(not (entries.get("argotec") or {}).get("hit", {}).get("page"), "argotec Official page stays unfiled")
    check((entries.get("ariel-investments") or {}).get("hit", {}).get("years", {}).get("year") == 1983, "ariel year in ledger")
    check(
        (entries.get("ariel-investments") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://www.arielinvestments.com/",
        "ariel year source in ledger",
    )
    check(
        (entries.get("ariel-investments") or {}).get("hit", {}).get("years", {}).get("quote")
        == "Home - Ariel Investments Ariel Investments is a global asset management firm founded in 1983.",
        "ariel year quote is the home sentence",
    )
    check(not (entries.get("ariel-investments") or {}).get("hit", {}).get("page"), "ariel Official page stays unfiled")
    check(not (entries.get("ariel-investments") or {}).get("hit", {}).get("marks"), "ariel marks stay unfiled")
    check(not (entries.get("aruba-s-p-a") or {}).get("hit", {}).get("page"), "aruba SSL product page stays unfiled")
    check(
        ((entries.get("aruba-s-p-a") or {}).get("hit") or {}).get("marks", {}).get("url")
        == "https://www.aruba.it/en/certifications.aspx",
        "aruba mark source in ledger",
    )
    check(
        ((entries.get("aruba-s-p-a") or {}).get("hit") or {}).get("marks", {}).get("added")
        == [
            "SOC 2 Type II",
            "SOC 1 Type II",
            "ISO 27001",
            "ISO 27017",
            "ISO 27018",
            "ISO 27701",
            "ISO 22301",
            "ISO 20000-1",
            "ISO 9001",
            "CSA STAR",
        ],
        "aruba marks in ledger",
    )
    for dropped_mark in ("GDPR", "DORA", "NIS2"):
        check(
            dropped_mark not in (((entries.get("aruba-s-p-a") or {}).get("hit") or {}).get("marks", {}).get("added") or []),
            f"aruba {dropped_mark} stays unfiled",
        )
    check((entries.get("aruba-s-p-a") or {}).get("hit", {}).get("years", {}).get("year") == 1994, "aruba year in ledger")
    check(
        (entries.get("aruba-s-p-a") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://www.aruba.it/en/about-us.aspx",
        "aruba year source in ledger",
    )
    check(
        (entries.get("asbis") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.asbis.com/documents-and-certificates",
        "asbis documents page in ledger",
    )
    check(
        (entries.get("asbis") or {}).get("hit", {}).get("page", {}).get("kind") == "trust",
        "asbis page kind is trust",
    )
    check(
        ((entries.get("asbis") or {}).get("hit") or {}).get("marks", {}).get("added") == ["ISO 9001"],
        "asbis marks in ledger",
    )
    check(
        "ISO 14001" not in (((entries.get("asbis") or {}).get("hit") or {}).get("marks", {}).get("added") or []),
        "asbis ISO 14001 stays unfiled",
    )
    check(not (entries.get("asbis") or {}).get("hit", {}).get("years"), "asbis year stays unfiled")
    check(not (entries.get("ascon") or {}).get("hit", {}).get("page"), "ascon product certification page stays unfiled")
    check((entries.get("ascon") or {}).get("hit", {}).get("years", {}).get("year") == 1989, "ascon year in ledger")
    check(
        (entries.get("ascon") or {}).get("hit", {}).get("years", {}).get("url") == "https://ascon.net/company",
        "ascon year source in ledger",
    )
    check(
        (entries.get("ascon") or {}).get("hit", {}).get("years", {}).get("quote")
        == "ry now About company Overview Solutions Customers Overview ASCON was founded in 1989 as a private company, becoming one of the first CAD/AEC/PLM developers and.",
        "ascon year quote is the company sentence",
    )
    check(not (entries.get("ascon") or {}).get("hit", {}).get("marks"), "ascon marks stay unfiled")
    refused_1102_pm = {
        "arkova": "CSA STAR Level 1 self-assessment, page says not a certification",
        "array-networks": "/security is an empty JS shell",
        "arthur-j-gallagher-and-co": "/security returns Incapsula block page (soft-retry)",
        "aselsan": "page is /tr homepage",
    }
    for slug, reason in refused_1102_pm.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-11-02", f"{slug} reaudited 2026-11-02")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
    check((entries.get("arkova") or {}).get("soft_retry") is not True, "arkova self-assessment is a refusal")
    check((entries.get("array-networks") or {}).get("soft_retry") is True, "array-networks empty JS shell stays a soft-retry")
    check(
        (entries.get("arthur-j-gallagher-and-co") or {}).get("soft_retry") is True,
        "gallagher Incapsula block stays a soft-retry",
    )
    check((entries.get("aselsan") or {}).get("soft_retry") is not True, "aselsan homepage is a miss")

    batch_1103_am = [
        "ashmanov-and-partners",
        "asian-vision",
        "asiasat",
        "asiatech-data-transmission",
        "asix-s-r-o",
        "ask-com",
        "asmik-ace",
        "asml",
        "asocs",
        "asora",
        "asoriba",
        "asos-com",
        "aspen-technology",
        "aspiegel-se",
        "asrock",
        "asseco",
        "asseco-business-solutions",
        "assessio",
        "assurant",
        "astera-labs",
        "astound-broadband",
        "astraqom",
        "astridbio",
        "astrolabs",
        "astronautics-corporation-of-america",
        "astrotech-corporation",
        "asure-software",
        "asustor",
        "at-conference-inc",
        "atands",
    ]
    check(len(batch_1103_am) == 30, f"2026-11-03 morning batch is 30, got {len(batch_1103_am)}")
    check(
        batch_1103_am[0] == "ashmanov-and-partners" and batch_1103_am[-1] == "atands",
        "2026-11-03 morning batch is the ashmanov-and-partners–atands cut",
    )
    check("asian-vision" in batch_1103_am and "astrolabs" in batch_1103_am, "morning cut covers ashmanov-and-partners..atands")
    check(all(slug in entries for slug in batch_1103_am), "2026-11-03 morning rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-11-03" for slug in batch_1103_am),
        "2026-11-03 morning cut is dated 2026-11-03",
    )
    check(not set(batch_1103_am) & set(batch_1026), "2026-11-03 morning cut must be never-reaudited vs 24slides–airpair")
    check(not set(batch_1103_am) & set(batch_1027_am), "2026-11-03 morning cut must be never-reaudited vs advacam–alchemy-cms")
    check(not set(batch_1103_am) & set(batch_1027_pm), "2026-11-03 morning cut must be never-reaudited vs 21vianet–aligned-assets")
    check(not set(batch_1103_am) & set(batch_1028), "2026-11-03 morning cut must be never-reaudited vs a1-hrvatska–altacast")
    check(not set(batch_1103_am) & set(batch_1029_am), "2026-11-03 morning cut must be never-reaudited vs altair-engineering–american-sammy")
    check(not set(batch_1103_am) & set(batch_1029_pm), "2026-11-03 morning cut must be never-reaudited vs american-tower–andor-technology")
    check(not set(batch_1103_am) & set(batch_1030_am), "2026-11-03 morning cut must be never-reaudited vs anduril-industries–apex-learning")
    check(not set(batch_1103_am) & set(batch_1030_pm), "2026-11-03 morning cut must be never-reaudited vs apigee–aptilo-networks")
    check(not set(batch_1103_am) & set(batch_1102_am), "2026-11-03 morning cut must be never-reaudited vs aptiv–argonide")
    check(not set(batch_1103_am) & set(batch_1102_pm), "2026-11-03 morning cut must be never-reaudited vs argotec–asg-technologies")
    shipped_1103 = {
        "asian-vision": {"years"},
        "asseco-business-solutions": {"page", "marks"},
        "assessio": {"page", "marks", "years"},
        "astraqom": {"years"},
        "atands": {"years"},
        "astrolabs": {"years"},
    }
    clerk_soft_1103 = {"asix-s-r-o", "asrock"}
    for slug in batch_1103_am:
        row = entries.get(slug) or {}
        if row.get("soft_retry") and slug not in clerk_soft_1103:
            probed_classes = {item.get("class") for item in (row.get("probed") or [])}
            check(bool(probed_classes & soft_classes), f"{slug} soft-retry is marked")
        if slug in shipped_1103:
            check(row.get("filed") is True, f"{slug} ledger row records the apply")
            continue
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
    for slug, keys in shipped_1103.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-11-03", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("could_fill") == [k for k in FILE_KEYS if k in keys], f"{slug} could_fill {row.get('could_fill')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
    check((entries.get("asian-vision") or {}).get("hit", {}).get("years", {}).get("year") == 1973, "asian-vision year in ledger")
    check(
        (entries.get("asian-vision") or {}).get("hit", {}).get("years", {}).get("url") == "https://www.asianvision.com.ph/",
        "asian-vision year source in ledger",
    )
    check(
        (entries.get("asian-vision") or {}).get("hit", {}).get("years", {}).get("quote") == '"foundingDate": "1973"',
        "asian-vision year quote is the JSON-LD foundingDate",
    )
    check(not (entries.get("asian-vision") or {}).get("hit", {}).get("page"), "asian-vision Official page stays unfiled")
    check(
        (entries.get("asseco-business-solutions") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://assecobs.pl/certificates/?lang=en",
        "asseco certificates page in ledger",
    )
    check(
        (entries.get("asseco-business-solutions") or {}).get("hit", {}).get("page", {}).get("kind") == "trust",
        "asseco page kind is trust",
    )
    check(
        ((entries.get("asseco-business-solutions") or {}).get("hit") or {}).get("marks", {}).get("added") == ["ISO 27001"],
        "asseco marks in ledger",
    )
    check(
        ((entries.get("asseco-business-solutions") or {}).get("hit") or {}).get("marks", {}).get("url")
        == "https://assecobs.pl/certificates/?lang=en",
        "asseco mark source in ledger",
    )
    check(
        ((entries.get("asseco-business-solutions") or {}).get("hit") or {}).get("marks", {}).get("quote") == "",
        "asseco quote stays empty; the page writes ISO/IEC 27001",
    )
    check(not (entries.get("asseco-business-solutions") or {}).get("hit", {}).get("years"), "asseco year stays unfiled")
    check(
        (entries.get("assessio") or {}).get("hit", {}).get("page", {}).get("url") == "https://assessio.com/trust-center/",
        "assessio trust center in ledger",
    )
    check(
        (entries.get("assessio") or {}).get("hit", {}).get("page", {}).get("kind") == "trust",
        "assessio page kind is trust",
    )
    check(
        ((entries.get("assessio") or {}).get("hit") or {}).get("marks", {}).get("added") == ["ISO 27001"],
        "assessio marks in ledger",
    )
    check(
        "GDPR" not in (((entries.get("assessio") or {}).get("hit") or {}).get("marks", {}).get("added") or []),
        "assessio GDPR stays unfiled",
    )
    check(
        "ISO 27001" in (((entries.get("assessio") or {}).get("hit") or {}).get("marks", {}).get("quote") or ""),
        "assessio quote names ISO 27001",
    )
    check((entries.get("assessio") or {}).get("hit", {}).get("years", {}).get("year") == 1954, "assessio year in ledger")
    check(
        (entries.get("assessio") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://assessio.com/trust-center/privacy-notice-sweden/",
        "assessio year source in ledger",
    )
    check(
        (entries.get("assessio") or {}).get("hit", {}).get("years", {}).get("quote") == '"foundingDate":"1954"',
        "assessio year quote is the JSON-LD foundingDate",
    )
    check(not (entries.get("assessio") or {}).get("hit", {}).get("dpa"), "assessio DPA stays unfiled")
    check((entries.get("astraqom") or {}).get("hit", {}).get("years", {}).get("year") == 2008, "astraqom year in ledger")
    check(
        (entries.get("astraqom") or {}).get("hit", {}).get("years", {}).get("url") == "https://astraqom.com/en",
        "astraqom year source in ledger",
    )
    check(
        (entries.get("astraqom") or {}).get("hit", {}).get("years", {}).get("quote") == '"foundingDate":"2008"',
        "astraqom year quote is the JSON-LD foundingDate",
    )
    check(not (entries.get("astraqom") or {}).get("hit", {}).get("page"), "astraqom Official page stays unfiled")
    check(not (entries.get("atands") or {}).get("hit", {}).get("page"), "atands /security page stays unfiled")
    check((entries.get("atands") or {}).get("hit", {}).get("years", {}).get("year") == 1987, "atands year in ledger")
    check(
        (entries.get("atands") or {}).get("hit", {}).get("years", {}).get("url") == "https://ats.net/en/company",
        "atands year source in ledger",
    )
    check(
        (entries.get("atands") or {}).get("hit", {}).get("years", {}).get("quote")
        == "Company | AT&S Since AT&S was founded in 1987, we have grown to become a leading supplier of high-end PCBs and IC substrates.",
        "atands year quote is the company sentence",
    )
    check(not (entries.get("astrolabs") or {}).get("hit", {}).get("page"), "astrolabs construction article stays unfiled")
    check((entries.get("astrolabs") or {}).get("hit", {}).get("years", {}).get("year") == 2013, "astrolabs year in ledger")
    check(
        (entries.get("astrolabs") or {}).get("hit", {}).get("years", {}).get("url") == "https://astrolabs.com/about-us",
        "astrolabs year source in ledger",
    )
    check(
        (entries.get("astrolabs") or {}).get("hit", {}).get("years", {}).get("quote")
        == "usiness Expansion Platform Empowering companies to thrive across the Gulf since 2013 Partner with us Contact us Our Story Our Origin Founded in 2013, AstroLabs.",
        "astrolabs year quote is the about sentence",
    )
    check(not (entries.get("astrolabs") or {}).get("hit", {}).get("marks"), "astrolabs marks stay unfiled")
    refused_1103 = {
        "asix-s-r-o": "homepage returns 466 Access Forbidden on spot-check (soft-retry)",
        "aspen-technology": "page is Sitecore filenotfound",
        "asrock": "/security is an Incapsula block page (soft-retry)",
        "astound-broadband": "page is error404.html",
        "asure-software": "page is an unrelated blog post; DPA returns Cloudflare 403 (soft-retry)",
        "asustor": "page is off-domain rog.asus.com campaign page",
    }
    for slug, reason in refused_1103.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-11-03", f"{slug} reaudited 2026-11-03")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
    check((entries.get("asix-s-r-o") or {}).get("soft_retry") is True, "asix homepage 466 stays a soft-retry")
    check((entries.get("aspen-technology") or {}).get("soft_retry") is not True, "aspen filenotfound is a miss")
    check((entries.get("asrock") or {}).get("soft_retry") is True, "asrock Incapsula block stays a soft-retry")
    check((entries.get("astound-broadband") or {}).get("soft_retry") is not True, "astound error404 is a miss")
    check((entries.get("asure-software") or {}).get("soft_retry") is True, "asure DPA Cloudflare block stays a soft-retry")
    check((entries.get("asustor") or {}).get("soft_retry") is not True, "asustor off-domain page is a miss")

    batch_1103_pm = [
        "atandt-alascom",
        "atandt-latin-america",
        "atari",
        "atavist-magazine",
        "atcom",
        "ateam-inc",
        "atego",
        "ateme",
        "aten-international",
        "atlus",
        "atm-mobilis",
        "atmos-energy",
        "atom-computing",
        "atomic-canyon",
        "atomic-object",
        "atommash",
        "atomstroyexport",
        "attabotics",
        "attachmate",
        "attensity",
        "atto-technology",
        "atypon",
        "au",
        "audible-magic",
        "audio-analytic",
        "audiokinetic",
        "augmentus",
        "aumovio",
        "auo-corporation",
        "aura-sonic",
    ]
    check(len(batch_1103_pm) == 30, f"2026-11-03 afternoon batch is 30, got {len(batch_1103_pm)}")
    check(
        batch_1103_pm[0] == "atandt-alascom" and batch_1103_pm[-1] == "aura-sonic",
        "2026-11-03 afternoon batch is the atandt-alascom–aura-sonic cut",
    )
    check("ateam-inc" in batch_1103_pm and "atomic-object" in batch_1103_pm, "afternoon cut covers atandt-alascom..aura-sonic")
    check(all(slug in entries for slug in batch_1103_pm), "2026-11-03 afternoon rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-11-03" for slug in batch_1103_pm),
        "2026-11-03 afternoon cut is dated 2026-11-03",
    )
    check(not set(batch_1103_pm) & set(batch_1026), "2026-11-03 afternoon cut must be never-reaudited vs 24slides–airpair")
    check(not set(batch_1103_pm) & set(batch_1027_am), "2026-11-03 afternoon cut must be never-reaudited vs advacam–alchemy-cms")
    check(not set(batch_1103_pm) & set(batch_1027_pm), "2026-11-03 afternoon cut must be never-reaudited vs 21vianet–aligned-assets")
    check(not set(batch_1103_pm) & set(batch_1028), "2026-11-03 afternoon cut must be never-reaudited vs a1-hrvatska–altacast")
    check(not set(batch_1103_pm) & set(batch_1029_am), "2026-11-03 afternoon cut must be never-reaudited vs altair-engineering–american-sammy")
    check(not set(batch_1103_pm) & set(batch_1029_pm), "2026-11-03 afternoon cut must be never-reaudited vs american-tower–andor-technology")
    check(not set(batch_1103_pm) & set(batch_1030_am), "2026-11-03 afternoon cut must be never-reaudited vs anduril-industries–apex-learning")
    check(not set(batch_1103_pm) & set(batch_1030_pm), "2026-11-03 afternoon cut must be never-reaudited vs apigee–aptilo-networks")
    check(not set(batch_1103_pm) & set(batch_1102_am), "2026-11-03 afternoon cut must be never-reaudited vs aptiv–argonide")
    check(not set(batch_1103_pm) & set(batch_1102_pm), "2026-11-03 afternoon cut must be never-reaudited vs argotec–asg-technologies")
    check(not set(batch_1103_pm) & set(batch_1103_am), "2026-11-03 afternoon cut must be never-reaudited vs ashmanov-and-partners–atands")
    shipped_1103_pm = {
        "ateam-inc": {"page"},
        "ateme": {"page", "marks", "years"},
        "atomic-object": {"years"},
    }
    clerk_soft_1103_pm = {"atm-mobilis"}
    for slug in batch_1103_pm:
        row = entries.get(slug) or {}
        if row.get("soft_retry") and slug not in clerk_soft_1103_pm:
            probed_classes = {item.get("class") for item in (row.get("probed") or [])}
            check(bool(probed_classes & soft_classes), f"{slug} soft-retry is marked")
        if slug in shipped_1103_pm:
            check(row.get("filed") is True, f"{slug} ledger row records the apply")
            continue
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
    for slug, keys in shipped_1103_pm.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-11-03", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("could_fill") == [k for k in FILE_KEYS if k in keys], f"{slug} could_fill {row.get('could_fill')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
    check(
        (entries.get("ateam-inc") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.a-tm.co.jp/securitypolicy/",
        "ateam-inc security policy in ledger",
    )
    check(
        (entries.get("ateam-inc") or {}).get("hit", {}).get("page", {}).get("kind") == "security",
        "ateam-inc page kind is security",
    )
    check(not (entries.get("ateam-inc") or {}).get("hit", {}).get("marks"), "ateam-inc marks stay unfiled")
    check(not (entries.get("ateam-inc") or {}).get("hit", {}).get("years"), "ateam-inc year stays unfiled")
    check(
        (entries.get("ateme") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.ateme.com/quality-certifications/",
        "ateme quality page in ledger",
    )
    check(
        (entries.get("ateme") or {}).get("hit", {}).get("page", {}).get("kind") == "trust",
        "ateme page kind is trust",
    )
    check(
        ((entries.get("ateme") or {}).get("hit") or {}).get("marks", {}).get("added") == ["ISO 9001"],
        "ateme marks in ledger",
    )
    check(
        ((entries.get("ateme") or {}).get("hit") or {}).get("marks", {}).get("url")
        == "https://www.ateme.com/quality-certifications/",
        "ateme mark source in ledger",
    )
    check(
        ((entries.get("ateme") or {}).get("hit") or {}).get("marks", {}).get("quote")
        == "Ateme is compliant with the ISO 9001: 2015 quality standard.",
        "ateme quote is the ISO 9001:2015 sentence",
    )
    check((entries.get("ateme") or {}).get("hit", {}).get("years", {}).get("year") == 1991, "ateme year in ledger")
    check(
        (entries.get("ateme") or {}).get("hit", {}).get("years", {}).get("url") == "https://www.ateme.com/about-us",
        "ateme year source in ledger",
    )
    check(
        (entries.get("ateme") or {}).get("hit", {}).get("years", {}).get("quote")
        == "Founded in 1991, Ateme counts 580 employees spread over its headquarters in France and 20 o.",
        "ateme year quote is the about sentence",
    )
    check(not (entries.get("atomic-object") or {}).get("hit", {}).get("page"), "atomic-object Official page stays unfiled")
    check((entries.get("atomic-object") or {}).get("hit", {}).get("years", {}).get("year") == 2001, "atomic-object year in ledger")
    check(
        (entries.get("atomic-object") or {}).get("hit", {}).get("years", {}).get("url") == "https://atomicobject.com/",
        "atomic-object year source in ledger",
    )
    check(
        (entries.get("atomic-object") or {}).get("hit", {}).get("years", {}).get("quote") == '"foundingDate": "2001-01-01"',
        "atomic-object year quote is the JSON-LD foundingDate",
    )
    check(not (entries.get("atomic-object") or {}).get("hit", {}).get("marks"), "atomic-object marks stay unfiled")
    check(
        (entries.get("atm-mobilis") or {}).get("refusal")
        == "/security returns an F5 'Request Rejected' WAF page (soft-retry)",
        "atm-mobilis refusal is the WAF page",
    )
    check((entries.get("atm-mobilis") or {}).get("soft_retry") is True, "atm-mobilis WAF page stays a soft-retry")
    check((entries.get("atm-mobilis") or {}).get("fileable") is False, "atm-mobilis reads as still 0")
    check((entries.get("atari") or {}).get("soft_retry") is True, "atari stays a Cloudflare soft-retry")
    check((entries.get("atego") or {}).get("soft_retry") is not True, "atego http-0 is a miss")

    batch_1104_am = [
        "aurascape",
        "aurora-innovation",
        "authentec",
        "authorize-net",
        "autodoc",
        "autoform",
        "autoliv",
        "automated-insights",
        "automatic-duck",
        "automatic-systems",
        "automotion",
        "autozone",
        "avantos",
        "avast",
        "avaya",
        "aventri",
        "aver-information",
        "avery-dennison",
        "avg-technologies",
        "avi-networks",
        "aviat-networks",
        "aviatrix",
        "avibras",
        "avid-audio",
        "avid-telecom",
        "avidyne-corporation",
        "avira",
        "awa-technology-services",
        "awardwallet",
        "awareness-technologies",
    ]
    check(len(batch_1104_am) == 30, f"2026-11-04 morning batch is 30, got {len(batch_1104_am)}")
    check(
        batch_1104_am[0] == "aurascape" and batch_1104_am[-1] == "awareness-technologies",
        "2026-11-04 morning batch is the aurascape–awareness-technologies cut",
    )
    check("authorize-net" in batch_1104_am and "awardwallet" in batch_1104_am, "morning cut covers aurascape..awareness-technologies")
    check(all(slug in entries for slug in batch_1104_am), "2026-11-04 morning rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-11-04" for slug in batch_1104_am),
        "2026-11-04 morning cut is dated 2026-11-04",
    )
    check(not set(batch_1104_am) & set(batch_1026), "2026-11-04 morning cut must be never-reaudited vs 24slides–airpair")
    check(not set(batch_1104_am) & set(batch_1027_am), "2026-11-04 morning cut must be never-reaudited vs advacam–alchemy-cms")
    check(not set(batch_1104_am) & set(batch_1027_pm), "2026-11-04 morning cut must be never-reaudited vs 21vianet–aligned-assets")
    check(not set(batch_1104_am) & set(batch_1028), "2026-11-04 morning cut must be never-reaudited vs a1-hrvatska–altacast")
    check(not set(batch_1104_am) & set(batch_1029_am), "2026-11-04 morning cut must be never-reaudited vs altair-engineering–american-sammy")
    check(not set(batch_1104_am) & set(batch_1029_pm), "2026-11-04 morning cut must be never-reaudited vs american-tower–andor-technology")
    check(not set(batch_1104_am) & set(batch_1030_am), "2026-11-04 morning cut must be never-reaudited vs anduril-industries–apex-learning")
    check(not set(batch_1104_am) & set(batch_1030_pm), "2026-11-04 morning cut must be never-reaudited vs apigee–aptilo-networks")
    check(not set(batch_1104_am) & set(batch_1102_am), "2026-11-04 morning cut must be never-reaudited vs aptiv–argonide")
    check(not set(batch_1104_am) & set(batch_1102_pm), "2026-11-04 morning cut must be never-reaudited vs argotec–asg-technologies")
    check(not set(batch_1104_am) & set(batch_1103_am), "2026-11-04 morning cut must be never-reaudited vs ashmanov-and-partners–atands")
    check(not set(batch_1104_am) & set(batch_1103_pm), "2026-11-04 morning cut must be never-reaudited vs atandt-alascom–aura-sonic")
    shipped_1104 = {
        "authorize-net": {"dpa"},
        "avaya": {"page", "marks"},
        "awardwallet": {"years"},
    }
    for slug in batch_1104_am:
        row = entries.get(slug) or {}
        if row.get("soft_retry"):
            probed_classes = {item.get("class") for item in (row.get("probed") or [])}
            check(bool(probed_classes & soft_classes), f"{slug} soft-retry is marked")
        if slug in shipped_1104:
            check(row.get("filed") is True, f"{slug} ledger row records the apply")
            continue
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
    for slug, keys in shipped_1104.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-11-04", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("could_fill") == [k for k in FILE_KEYS if k in keys], f"{slug} could_fill {row.get('could_fill')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
    check(
        (entries.get("authorize-net") or {}).get("hit", {}).get("dpa", {}).get("url")
        == "https://www.authorize.net/about-us/dpa.html",
        "authorize-net DPA in ledger",
    )
    check(not (entries.get("authorize-net") or {}).get("hit", {}).get("page"), "authorize-net Official page stays unfiled")
    check(not (entries.get("authorize-net") or {}).get("hit", {}).get("marks"), "authorize-net marks stay unfiled")
    check(not (entries.get("authorize-net") or {}).get("hit", {}).get("years"), "authorize-net year stays unfiled")
    check(
        (entries.get("avaya") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.avaya.com/en/trust-center/",
        "avaya trust center in ledger",
    )
    check(
        (entries.get("avaya") or {}).get("hit", {}).get("page", {}).get("kind") == "trust",
        "avaya page kind is trust",
    )
    check(
        ((entries.get("avaya") or {}).get("hit") or {}).get("marks", {}).get("added") == ["FedRAMP"],
        "avaya marks in ledger",
    )
    check(
        "GDPR" not in (((entries.get("avaya") or {}).get("hit") or {}).get("marks", {}).get("added") or []),
        "avaya GDPR stays unfiled",
    )
    check(
        ((entries.get("avaya") or {}).get("hit") or {}).get("marks", {}).get("url")
        == "https://www.avaya.com/en/trust-center/",
        "avaya mark source in ledger",
    )
    check(
        ((entries.get("avaya") or {}).get("hit") or {}).get("marks", {}).get("quote")
        == "Avaya Government Cloud FedRAMP-authorized cloud communications for mission continuity.",
        "avaya quote is the FedRAMP sentence",
    )
    check(not (entries.get("avaya") or {}).get("hit", {}).get("years"), "avaya year stays unfiled")
    check(not (entries.get("avaya") or {}).get("hit", {}).get("dpa"), "avaya DPA stays unfiled")
    check((entries.get("awardwallet") or {}).get("hit", {}).get("years", {}).get("year") == 2004, "awardwallet year in ledger")
    check(
        (entries.get("awardwallet") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://awardwallet.com/page/about",
        "awardwallet year source in ledger",
    )
    check(
        (entries.get("awardwallet") or {}).get("hit", {}).get("years", {}).get("quote")
        == "544 billion in value Quick History 2004 AwardWallet was founded by Alexi Vereschaga (on the right) and Todd Mera (on the left) who were co-workers at the time.",
        "awardwallet year quote is the about sentence",
    )
    check(not (entries.get("awardwallet") or {}).get("hit", {}).get("page"), "awardwallet Official page stays unfiled")
    check(not (entries.get("awardwallet") or {}).get("hit", {}).get("marks"), "awardwallet marks stay unfiled")
    refused_1104 = {
        "aurora-innovation": "manage-your-data is a cookie/privacy preferences page",
        "autoform": "/en/error/ error page",
        "autoliv": "corporate compliance/integrity page; TISAX only in nav menu text",
        "aviat-networks": "product page",
        "aviatrix": "marketing explainer, compliance names not certifications",
        "avidyne-corporation": "shop product page",
    }
    for slug, reason in refused_1104.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-11-04", f"{slug} reaudited 2026-11-04")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
    check((entries.get("avidyne-corporation") or {}).get("soft_retry") is True, "avidyne shop page stays a soft-retry")
    check((entries.get("aurascape") or {}).get("soft_retry") is True, "aurascape stays a js-shell soft-retry")
    check((entries.get("autodoc") or {}).get("soft_retry") is True, "autodoc stays a Cloudflare soft-retry")


    batch_1104_pm = [
        "aws-elemental",
        "axact",
        "axceler",
        "axcient",
        "axia-netmedia",
        "axiata",
        "axiom",
        "axis-telecom",
        "axium",
        "axonic-informationssysteme-gmbh",
        "axtel",
        "axway-software",
        "axxess-technology-solutions",
        "ayotle",
        "azenta",
        "azercell",
        "azerconnect-group",
        "azercosmos",
        "azimo",
        "azimuth-systems",
        "azuro",
        "b-scada",
        "b-net",
        "b2w",
        "babylon-health",
        "backbone-labs",
        "backupassist",
        "bactrack",
        "bacula",
        "badoinkvr",
    ]
    check(len(batch_1104_pm) == 30, f"2026-11-04 afternoon batch is 30, got {len(batch_1104_pm)}")
    check(
        batch_1104_pm[0] == "aws-elemental" and batch_1104_pm[-1] == "badoinkvr",
        "2026-11-04 afternoon batch is the aws-elemental to badoinkvr cut",
    )
    check("axiata" in batch_1104_pm and "azercosmos" in batch_1104_pm, "afternoon cut covers aws-elemental..badoinkvr")
    check(all(slug in entries for slug in batch_1104_pm), "2026-11-04 afternoon rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-11-04" for slug in batch_1104_pm),
        "2026-11-04 afternoon cut is dated 2026-11-04",
    )
    check(not set(batch_1104_pm) & set(batch_1026), "2026-11-04 afternoon cut must be never-reaudited vs 24slides-airpair")
    check(not set(batch_1104_pm) & set(batch_1027_am), "2026-11-04 afternoon cut must be never-reaudited vs advacam-alchemy-cms")
    check(not set(batch_1104_pm) & set(batch_1027_pm), "2026-11-04 afternoon cut must be never-reaudited vs 21vianet-aligned-assets")
    check(not set(batch_1104_pm) & set(batch_1028), "2026-11-04 afternoon cut must be never-reaudited vs a1-hrvatska-altacast")
    check(not set(batch_1104_pm) & set(batch_1029_am), "2026-11-04 afternoon cut must be never-reaudited vs altair-engineering-american-sammy")
    check(not set(batch_1104_pm) & set(batch_1029_pm), "2026-11-04 afternoon cut must be never-reaudited vs american-tower-andor-technology")
    check(not set(batch_1104_pm) & set(batch_1030_am), "2026-11-04 afternoon cut must be never-reaudited vs anduril-industries-apex-learning")
    check(not set(batch_1104_pm) & set(batch_1030_pm), "2026-11-04 afternoon cut must be never-reaudited vs apigee-aptilo-networks")
    check(not set(batch_1104_pm) & set(batch_1102_am), "2026-11-04 afternoon cut must be never-reaudited vs aptiv-argonide")
    check(not set(batch_1104_pm) & set(batch_1102_pm), "2026-11-04 afternoon cut must be never-reaudited vs argotec-asg-technologies")
    check(not set(batch_1104_pm) & set(batch_1103_am), "2026-11-04 afternoon cut must be never-reaudited vs ashmanov-and-partners-atands")
    check(not set(batch_1104_pm) & set(batch_1103_pm), "2026-11-04 afternoon cut must be never-reaudited vs atandt-alascom-aura-sonic")
    check(not set(batch_1104_pm) & set(batch_1104_am), "2026-11-04 afternoon cut must be never-reaudited vs aurascape-awareness-technologies")
    shipped_1104_pm = {
        "axiata": {"page"},
        "azercosmos": {"page", "marks", "years"},
    }
    clerk_soft_1104_pm = {"axact", "azercell"}
    for slug in batch_1104_pm:
        row = entries.get(slug) or {}
        if row.get("soft_retry") and slug not in clerk_soft_1104_pm:
            probed_classes = {item.get("class") for item in (row.get("probed") or [])}
            check(bool(probed_classes & soft_classes), f"{slug} soft-retry is marked")
        if slug in shipped_1104_pm:
            check(row.get("filed") is True, f"{slug} ledger row records the apply")
            continue
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
    for slug, keys in shipped_1104_pm.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-11-04", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("could_fill") == [k for k in FILE_KEYS if k in keys], f"{slug} could_fill {row.get('could_fill')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
    check(
        (entries.get("axiata") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.axiata.com/digital-trust/cybersecurity",
        "axiata security page in ledger",
    )
    check(
        (entries.get("axiata") or {}).get("hit", {}).get("page", {}).get("kind") == "security",
        "axiata page kind is security",
    )
    check(not (entries.get("axiata") or {}).get("hit", {}).get("marks"), "axiata ISO 27001 stays unfiled")
    check(not (entries.get("axiata") or {}).get("hit", {}).get("years"), "axiata year stays unfiled")
    check(not (entries.get("axiata") or {}).get("hit", {}).get("dpa"), "axiata DPA stays unfiled")
    check(
        (entries.get("azercosmos") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://azercosmos.az/en/quality-and-information-security-policy",
        "azercosmos security policy in ledger",
    )
    check(
        (entries.get("azercosmos") or {}).get("hit", {}).get("page", {}).get("kind") == "security",
        "azercosmos page kind is security",
    )
    check(
        ((entries.get("azercosmos") or {}).get("hit") or {}).get("marks", {}).get("added") == ["ISO 27001", "ISO 9001"],
        "azercosmos marks in ledger",
    )
    check(
        ((entries.get("azercosmos") or {}).get("hit") or {}).get("marks", {}).get("url")
        == "https://azercosmos.az/en/quality-and-information-security-policy",
        "azercosmos mark source in ledger",
    )
    check(
        ((entries.get("azercosmos") or {}).get("hit") or {}).get("marks", {}).get("quote")
        == "The company holds the ISO 9001 Quality Management Systems and ISO 27001 Information Security Management Systems standards conformity certificates.",
        "azercosmos quote is the conformity-certificate sentence",
    )
    check((entries.get("azercosmos") or {}).get("hit", {}).get("years", {}).get("year") == 2010, "azercosmos year in ledger")
    check(
        (entries.get("azercosmos") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://azercosmos.az/en/about-us/our-story",
        "azercosmos year source is the about page",
    )
    check(
        (entries.get("azercosmos") or {}).get("hit", {}).get("years", {}).get("quote")
        == "mand for satellite-driven services and solutions, Azercosmos was established in 2010 as the premier satellite operator in the region.",
        "azercosmos year quote is the established sentence",
    )
    check(not (entries.get("azercosmos") or {}).get("hit", {}).get("dpa"), "azercosmos DPA stays unfiled")
    refused_1104_pm = {
        "axact": "/security is a 3 KB JS shell",
        "axcient": "white paper marketing page; DPF not a cert hit",
        "axxess-technology-solutions": "/certification/ is training and certification for customers",
        "azercell": "/trust returns F5 'Request Rejected' WAF page (soft-retry)",
        "badoinkvr": "adult video page matched 'trust' in title",
    }
    for slug, reason in refused_1104_pm.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-11-04", f"{slug} reaudited 2026-11-04")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
    check((entries.get("axact") or {}).get("soft_retry") is True, "axact JS shell stays a soft-retry")
    check((entries.get("azercell") or {}).get("soft_retry") is True, "azercell WAF page stays a soft-retry")
    check((entries.get("axcient") or {}).get("soft_retry") is True, "axcient stays a soft-retry")
    check((entries.get("badoinkvr") or {}).get("soft_retry") is True, "badoinkvr stays a Cloudflare soft-retry")
    check((entries.get("aws-elemental") or {}).get("soft_retry") is True, "aws-elemental stays an http-403 soft-retry")
    check((entries.get("axxess-technology-solutions") or {}).get("soft_retry") is not True, "axxess training page is a miss")

    batch_1105_am = [
        "baker-hughes",
        "barracuda",
        "balsamiq",
        "batchmaster-software",
        "bandlab-technologies",
        "bae-systems-electronic-systems",
        "banham-group",
        "balfour-beatty",
        "bandai-namco-holdings",
        "batliboi",
    ]
    check(len(batch_1105_am) == 10, f"2026-11-05 morning batch is 10, got {len(batch_1105_am)}")
    check(all(slug in entries for slug in batch_1105_am), "2026-11-05 morning rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-11-05" for slug in batch_1105_am),
        "2026-11-05 morning cut is dated 2026-11-05",
    )
    check(not set(batch_1105_am) & set(batch_1104_pm), "2026-11-05 morning cut must be never-reaudited vs aws-elemental to badoinkvr")
    check(not set(batch_1105_am) & set(batch_1104_am), "2026-11-05 morning cut must be never-reaudited vs aurascape to awareness-technologies")
    shipped_1105 = {
        "balsamiq": {"marks", "dpa", "subprocessors"},
        "barracuda": {"page"},
        "batliboi": {"years"},
    }
    for slug, keys in shipped_1105.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-11-05", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("could_fill") == [k for k in FILE_KEYS if k in keys], f"{slug} could_fill {row.get('could_fill')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
        check(row.get("soft_retry") is not True, f"{slug} is not a soft-retry")
    for slug in batch_1105_am:
        if slug in shipped_1105:
            continue
        row = entries.get(slug) or {}
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
    check(
        (entries.get("barracuda") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://trust.barracuda.com/",
        "barracuda trust page in ledger",
    )
    check(
        (entries.get("barracuda") or {}).get("hit", {}).get("page", {}).get("kind") == "trust",
        "barracuda page kind is trust",
    )
    check(not (entries.get("barracuda") or {}).get("hit", {}).get("marks"), "barracuda marks stay unfiled")
    check(not (entries.get("barracuda") or {}).get("hit", {}).get("dpa"), "barracuda DPA stays unfiled")
    check(not (entries.get("barracuda") or {}).get("hit", {}).get("years"), "barracuda year stays unfiled")
    bal_hit = (entries.get("balsamiq") or {}).get("hit") or {}
    check(bal_hit.get("dpa", {}).get("url") == "https://balsamiq.com/legal/dpa/", "balsamiq DPA in ledger")
    check(
        bal_hit.get("subprocessors", {}).get("url") == "https://balsamiq.com/legal/subprocessors/",
        "balsamiq subprocessors URL in ledger",
    )
    check(
        bal_hit.get("subprocessors", {}).get("names") == [
            "Amazon Web Services (AWS)",
            "Atlassian",
            "Cookiebot (Usercentrics)",
            "Customer.io",
            "Google (Ads)",
            "Google (Analytics)",
            "Google (Gemini)",
            "Google (Workspace)",
            "Help Scout",
            "PostHog",
            "Postmark",
            "Stripe",
        ],
        "balsamiq subprocessors names in ledger",
    )
    check(bal_hit.get("marks", {}).get("added") == ["EU-US DPF", "SOC 2 Type II"], "balsamiq marks in ledger")
    check(
        bal_hit.get("marks", {}).get("url") == "https://balsamiq.com/legal/privacy/",
        "balsamiq mark source in ledger",
    )
    check(not bal_hit.get("page"), "balsamiq Official page stays unfiled")
    check(not bal_hit.get("years"), "balsamiq year stays unfiled")
    check((entries.get("batliboi") or {}).get("hit", {}).get("years", {}).get("year") == 1892, "batliboi year in ledger")
    check(
        (entries.get("batliboi") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://batliboi.com/about-us/overview/",
        "batliboi year source in ledger",
    )
    check(not (entries.get("batliboi") or {}).get("hit", {}).get("page"), "batliboi Official page stays unfiled")
    check(not (entries.get("batliboi") or {}).get("hit", {}).get("marks"), "batliboi marks stay unfiled")
    check(not (entries.get("batliboi") or {}).get("hit", {}).get("dpa"), "batliboi DPA stays unfiled")
    refused_1105 = {
        "bae-systems-electronic-systems": "Incapsula WAF 403 on /trust (soft-retry)",
        "baker-hughes": "flow-assurance product marketing page; wrong 'trust' keyword match",
        "balfour-beatty": "2018 is digital-transformation date on Digital-first page, not founding year",
        "bandai-namco-holdings": "/err/403forbid.html Access Denied page",
        "bandlab-technologies": "/trust is empty JS/CloudFront shell (~1.6KB) soft-retry",
        "banham-group": "locks product marketing page ('Additional Locks & Security')",
        "batchmaster-software": "regulatory-compliance-software ERP product marketing page",
    }
    for slug, reason in refused_1105.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-11-05", f"{slug} reaudited 2026-11-05")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
    check((entries.get("bae-systems-electronic-systems") or {}).get("soft_retry") is True, "bae systems WAF 403 stays a soft-retry")
    check((entries.get("bandai-namco-holdings") or {}).get("soft_retry") is True, "bandai namco 403 page stays a soft-retry")
    check((entries.get("bandlab-technologies") or {}).get("soft_retry") is True, "bandlab JS shell stays a soft-retry")
    check((entries.get("baker-hughes") or {}).get("soft_retry") is not True, "baker hughes marketing page is a miss")
    check((entries.get("balfour-beatty") or {}).get("soft_retry") is not True, "balfour beatty year miss is not a soft-retry")
    check((entries.get("banham-group") or {}).get("soft_retry") is not True, "banham product page is a miss")
    check((entries.get("batchmaster-software") or {}).get("soft_retry") is not True, "batchmaster product page is a miss")

    batch_1105_pm = [
        "batm",
        "bayan-telecommunications",
        "bayanat",
        "bazaarvoice",
        "bce-inc",
        "bdo-pay",
        "bdo-usa",
        "bdt-msd-partners",
        "be-inc",
        "be-quiet",
        "be-tv",
        "bea-systems",
        "beamly",
        "beca-group",
        "bechtle",
        "beckhoff-automation",
        "beddit",
        "bee-engineering",
        "beelink",
        "behavior-tech-computer",
        "behringer",
        "beijer-electronics",
        "belarc",
        "belkart",
        "belkin",
        "bell-aliant",
        "bell-canada",
        "bell-id",
        "bell-mts",
        "bellperre",
    ]
    check(len(batch_1105_pm) == 30, f"2026-11-05 afternoon batch is 30, got {len(batch_1105_pm)}")
    check(
        batch_1105_pm[0] == "batm" and batch_1105_pm[-1] == "bellperre",
        "2026-11-05 afternoon batch is the batm to bellperre cut",
    )
    check(all(slug in entries for slug in batch_1105_pm), "2026-11-05 afternoon rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-11-05" for slug in batch_1105_pm),
        "2026-11-05 afternoon cut is dated 2026-11-05",
    )
    check(not set(batch_1105_pm) & set(batch_1105_am), "2026-11-05 afternoon cut must be never-reaudited vs the morning holds")
    check(not set(batch_1105_pm) & set(batch_1104_pm), "2026-11-05 afternoon cut must be never-reaudited vs aws-elemental to badoinkvr")
    shipped_1105_pm = {
        "batm": {"years"},
        "bazaarvoice": {"page"},
        "behringer": {"years"},
    }
    for slug in batch_1105_pm:
        row = entries.get(slug) or {}
        if row.get("soft_retry") and slug != "bazaarvoice":
            probed_classes = {item.get("class") for item in (row.get("probed") or [])}
            check(bool(probed_classes & soft_classes), f"{slug} soft-retry is marked")
        if slug in shipped_1105_pm:
            check(row.get("filed") is True, f"{slug} ledger row records the apply")
            continue
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
    for slug, keys in shipped_1105_pm.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-11-05", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("could_fill") == [k for k in FILE_KEYS if k in keys], f"{slug} could_fill {row.get('could_fill')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
    check((entries.get("batm") or {}).get("soft_retry") is not True, "batm year hold is not a soft-retry")
    check((entries.get("behringer") or {}).get("soft_retry") is not True, "behringer year hold is not a soft-retry")
    check((entries.get("bazaarvoice") or {}).get("soft_retry") is True, "bazaarvoice stays a js-shell soft-retry")
    check(
        (entries.get("batm") or {}).get("hit", {}).get("years", {}).get("year") == 1992,
        "batm year in ledger",
    )
    check(
        (entries.get("batm") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://www.batm.com/company-governance/about-batm",
        "batm year source in ledger",
    )
    check(
        (entries.get("batm") or {}).get("hit", {}).get("years", {}).get("quote")
        == "Established in 1992, BATM is headquartered in Israel with offices in North America, Europe and the Far East, and it is listed on the Main Market of the London Stock Exchange.",
        "batm year quote is the about sentence",
    )
    check(not (entries.get("batm") or {}).get("hit", {}).get("page"), "batm accessibility page stays unfiled")
    check(not (entries.get("batm") or {}).get("hit", {}).get("marks"), "batm marks stay unfiled")
    check(not (entries.get("batm") or {}).get("hit", {}).get("dpa"), "batm DPA stays unfiled")
    check(
        (entries.get("batm") or {}).get("refusal")
        == "dropped page: accessibility statement is not a trust/security Completeness page; kept years 1992 from about",
        "batm accessibility page drop stays on the row",
    )
    check(
        (entries.get("bazaarvoice") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.bazaarvoice.com/company/trust/",
        "bazaarvoice trust page in ledger",
    )
    check(
        (entries.get("bazaarvoice") or {}).get("hit", {}).get("page", {}).get("kind") == "trust",
        "bazaarvoice page kind is trust",
    )
    check(not (entries.get("bazaarvoice") or {}).get("hit", {}).get("marks"), "bazaarvoice marks stay unfiled")
    check(not (entries.get("bazaarvoice") or {}).get("hit", {}).get("dpa"), "bazaarvoice DPA stays unfiled")
    check(not (entries.get("bazaarvoice") or {}).get("hit", {}).get("years"), "bazaarvoice year stays unfiled")
    check((entries.get("behringer") or {}).get("hit", {}).get("years", {}).get("year") == 1989, "behringer year in ledger")
    check(
        (entries.get("behringer") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://behringer.com/en/about",
        "behringer year source in ledger",
    )
    check(
        (entries.get("behringer") or {}).get("hit", {}).get("years", {}).get("quote")
        == "Our Story Born from a Passion for Music Founded in 1989, as a struggling musician and sound engineer, Uli Behringer couldn't afford the necessary equipment for his own studio.",
        "behringer year quote is the about sentence",
    )
    check(not (entries.get("behringer") or {}).get("hit", {}).get("page"), "behringer Official page stays unfiled")
    check(not (entries.get("behringer") or {}).get("hit", {}).get("marks"), "behringer marks stay unfiled")
    check(not (entries.get("behringer") or {}).get("hit", {}).get("dpa"), "behringer DPA stays unfiled")
    refused_1105_pm = {
        "bayan-telecommunications": "trust URL HTTP 500; /data-processing-addendum is empty JS 'Loading...' shell (~498B)",
        "bce-inc": "/security serves Newsroom content (wrong page), not a security/trust center",
        "bdo-usa": "audit-assurance and third-party-attestation are client services marketing (BDO selling SOC2), not BDO's own trust; 2023 is ESOP date not founding",
        "bdt-msd-partners": "only evidence is privacy JSON-LD foundingDate 2023 (merger year of BDT+MSD); no about-page founding prose — too weak",
        "bechtle": "IT security solutions product/services marketing page, not first-party trust/security disclosure",
        "beckhoff-automation": "2006 is Beckhoff South Africa subsidiary founding, not company founding year",
        "bee-engineering": "ética-compliance-old anticorruption/ethics page, not Completeness trust/security/DPA hold",
        "behavior-tech-computer": "/trust returns company About/EMS homepage content (LED manufacturing), not a trust center",
        "belkin": "Secure KVM product marketing page (NIAP PP4.0), not company trust/security disclosure",
    }
    for slug, reason in refused_1105_pm.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-11-05", f"{slug} reaudited 2026-11-05")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
        check(row.get("soft_retry") is not True, f"{slug} drop is not a soft-retry")
    check((entries.get("be-quiet") or {}).get("soft_retry") is True, "be-quiet stays a Cloudflare soft-retry")
    check((entries.get("be-tv") or {}).get("soft_retry") is True, "be-tv JS shell stays a soft-retry")
    check((entries.get("belkart") or {}).get("soft_retry") is True, "belkart http-403 stays a soft-retry")
    check((entries.get("bellperre") or {}).get("soft_retry") is True, "bellperre JS shell stays a soft-retry")
    check((entries.get("be-quiet") or {}).get("refusal") == "cloudflare", "be-quiet refusal is cloudflare")
    check((entries.get("be-tv") or {}).get("refusal") == "js-shell", "be-tv refusal is js-shell")
    check((entries.get("belkart") or {}).get("refusal") == "http-403", "belkart refusal is http-403")
    check((entries.get("bellperre") or {}).get("refusal") == "js-shell", "bellperre refusal is js-shell")

    batch_1106_am = [
        "bellsouth",
        "belly",
        "benchprep",
        "bending-spoons",
        "bendix-corporation",
        "benefon",
        "bennett-environmental",
        "benq",
        "benq-mobile",
        "berkshire-hathaway",
        "bermad",
        "bes-utilities",
        "best-buy",
        "beta-systems",
        "better-online-solutions",
        "beurer",
        "beyond",
        "beyond-verbal",
        "bezeq",
        "bharti-airtel",
        "bias",
        "big-finish-games",
        "big-fish-games",
        "bigchampagne",
        "billdesk",
        "billguard",
        "billion-electric",
        "binatone",
        "bio-rad-laboratories",
        "bio-techne",
    ]
    check(len(batch_1106_am) == 30, f"2026-11-06 morning batch is 30, got {len(batch_1106_am)}")
    check(
        batch_1106_am[0] == "bellsouth" and batch_1106_am[-1] == "bio-techne",
        "2026-11-06 morning batch is the bellsouth to bio-techne cut",
    )
    check(all(slug in entries for slug in batch_1106_am), "2026-11-06 morning rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-11-06" for slug in batch_1106_am),
        "2026-11-06 morning cut is dated 2026-11-06",
    )
    check(not set(batch_1106_am) & set(batch_1105_pm), "2026-11-06 morning cut must be never-reaudited vs the afternoon holds")
    check(not set(batch_1106_am) & set(batch_1105_am), "2026-11-06 morning cut must be never-reaudited vs the morning holds")
    shipped_1106_am = {
        "benchprep": {"page"},
        "billion-electric": {"years"},
    }
    for slug in batch_1106_am:
        row = entries.get(slug) or {}
        if row.get("soft_retry"):
            probed_classes = {item.get("class") for item in (row.get("probed") or [])}
            check(bool(probed_classes & soft_classes), f"{slug} soft-retry is marked")
        if slug in shipped_1106_am:
            check(row.get("filed") is True, f"{slug} ledger row records the apply")
            continue
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
    for slug, keys in shipped_1106_am.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-11-06", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("could_fill") == [k for k in FILE_KEYS if k in keys], f"{slug} could_fill {row.get('could_fill')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
    check((entries.get("benchprep") or {}).get("soft_retry") is not True, "benchprep security page is not a soft-retry")
    check((entries.get("billion-electric") or {}).get("soft_retry") is not True, "billion-electric year hold is not a soft-retry")
    check(
        (entries.get("benchprep") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.benchprep.com/security",
        "benchprep security page in ledger",
    )
    check(
        (entries.get("benchprep") or {}).get("hit", {}).get("page", {}).get("kind") == "security",
        "benchprep page kind is security",
    )
    check(not (entries.get("benchprep") or {}).get("hit", {}).get("marks"), "benchprep marks stay unfiled")
    check(not (entries.get("benchprep") or {}).get("hit", {}).get("dpa"), "benchprep DPA stays unfiled")
    check(not (entries.get("benchprep") or {}).get("hit", {}).get("years"), "benchprep year stays unfiled")
    check(
        (entries.get("billion-electric") or {}).get("hit", {}).get("years", {}).get("year") == 1973,
        "billion-electric year in ledger",
    )
    check(
        (entries.get("billion-electric") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://www.billion.com/About-Billion",
        "billion-electric year source in ledger",
    )
    check(
        (entries.get("billion-electric") or {}).get("hit", {}).get("years", {}).get("quote")
        == "Founded in 1973, Billion Electric Co., Ltd. (TSE: 3027) began with power supply and ICT technologies and has since evolved into",
        "billion-electric year quote is the about sentence",
    )
    check(not (entries.get("billion-electric") or {}).get("hit", {}).get("page"), "billion-electric Official page stays unfiled")
    check(not (entries.get("billion-electric") or {}).get("hit", {}).get("marks"), "billion-electric marks stay unfiled")
    check(not (entries.get("billion-electric") or {}).get("hit", {}).get("dpa"), "billion-electric DPA stays unfiled")
    refused_1106_am = {
        "bending-spoons": "support.bendingspoons.com/compliance is Modern Slavery / Code of Ethics / Organizational Model / whistleblowing legal-compliance hub, not Completeness trust/security/DPA",
        "bendix-corporation": "about-us/certifications is manufacturing quality/environmental (ISO 9001, IATF 16949, ISO 14001), not info-security trust/security disclosure",
        "benq": "import-export-compliance is trade/customs policy, not trust/security/DPA",
        "beyond": "Report-Vulnerability is Overstock VDP form only; not a Completeness trust/security/privacy/DPA page (privacy URL already on file separately)",
        "beyond-verbal": "CPR employee-training blog post, not Completeness trust/security/DPA",
    }
    for slug, reason in refused_1106_am.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-11-06", f"{slug} reaudited 2026-11-06")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
        check(row.get("soft_retry") is not True, f"{slug} drop is not a soft-retry")
        check(row.get("dropped") is True, f"{slug} drop is clerked")
    check((entries.get("belly") or {}).get("soft_retry") is True, "belly JS shell stays a soft-retry")
    check((entries.get("bermad") or {}).get("soft_retry") is True, "bermad stays a Cloudflare soft-retry")
    check((entries.get("big-finish-games") or {}).get("soft_retry") is True, "big-finish-games JS shell stays a soft-retry")
    check((entries.get("billdesk") or {}).get("soft_retry") is True, "billdesk JS shell stays a soft-retry")
    check((entries.get("bio-rad-laboratories") or {}).get("soft_retry") is True, "bio-rad-laboratories http-403 stays a soft-retry")
    check((entries.get("belly") or {}).get("hit") is None, "belly hit stays null")
    check((entries.get("bermad") or {}).get("hit") is None, "bermad hit stays null")
    check((entries.get("big-finish-games") or {}).get("hit") is None, "big-finish-games hit stays null")
    check((entries.get("billdesk") or {}).get("hit") is None, "billdesk hit stays null")
    check((entries.get("bio-rad-laboratories") or {}).get("hit") is None, "bio-rad-laboratories hit stays null")
    check((entries.get("belly") or {}).get("refusal") == "js-shell", "belly refusal is js-shell")
    check((entries.get("bermad") or {}).get("refusal") == "cloudflare", "bermad refusal is cloudflare")
    check((entries.get("big-finish-games") or {}).get("refusal") == "js-shell", "big-finish-games refusal is js-shell")
    check((entries.get("billdesk") or {}).get("refusal") == "js-shell", "billdesk refusal is js-shell")
    check((entries.get("bio-rad-laboratories") or {}).get("refusal") == "http-403", "bio-rad-laboratories refusal is http-403")

    batch_1106_pm = [
        "biobam-bioinformatics",
        "bioclipse",
        "biogen",
        "biostar",
        "biotronik",
        "birdstep-technology",
        "birlasoft",
        "biscom",
        "bitbucket",
        "bitcasa",
        "bitdeer",
        "bitium",
        "bitsight",
        "bitstream-inc",
        "bittium",
        "bitvavo",
        "bitwala",
        "biw-technologies",
        "bixbee",
        "bizagi",
        "bkash",
        "black-box-corporation",
        "black-duck-software",
        "black-sesame-technologies",
        "black-swan-data",
        "blackmagic-design",
        "blackpoint-cyber",
        "blackstone-inc",
        "blausen-medical",
        "blend",
    ]
    check(len(batch_1106_pm) == 30, f"2026-11-06 afternoon batch is 30, got {len(batch_1106_pm)}")
    check(
        batch_1106_pm[0] == "biobam-bioinformatics" and batch_1106_pm[-1] == "blend",
        "2026-11-06 afternoon batch is the biobam-bioinformatics to blend cut",
    )
    check(all(slug in entries for slug in batch_1106_pm), "2026-11-06 afternoon rows stay in the ledger")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-11-06" for slug in batch_1106_pm),
        "2026-11-06 afternoon cut is dated 2026-11-06",
    )
    check(not set(batch_1106_pm) & set(batch_1106_am), "2026-11-06 afternoon cut must be never-reaudited vs the morning holds")
    check(not set(batch_1106_pm) & set(batch_1105_pm), "2026-11-06 afternoon cut must be never-reaudited vs the afternoon holds")
    shipped_1106_pm = {
        "biogen": {"years"},
        "biostar": {"years"},
        "bizagi": {"page", "years"},
        "black-box-corporation": {"page", "marks"},
        "blend": {"page"},
    }
    for slug in batch_1106_pm:
        row = entries.get(slug) or {}
        if row.get("soft_retry"):
            probed_classes = {item.get("class") for item in (row.get("probed") or [])}
            check(bool(probed_classes & soft_classes), f"{slug} soft-retry is marked")
        if slug in shipped_1106_pm:
            check(row.get("filed") is True, f"{slug} ledger row records the apply")
            continue
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
    for slug, keys in shipped_1106_pm.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-11-06", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("could_fill") == [k for k in FILE_KEYS if k in keys], f"{slug} could_fill {row.get('could_fill')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
    check((entries.get("biogen") or {}).get("soft_retry") is not True, "biogen year hold is not a soft-retry")
    check((entries.get("biostar") or {}).get("soft_retry") is not True, "biostar year hold is not a soft-retry")
    check((entries.get("bizagi") or {}).get("soft_retry") is not True, "bizagi holds are not a soft-retry")
    check((entries.get("black-box-corporation") or {}).get("soft_retry") is not True, "black-box trust center is not a soft-retry")
    check((entries.get("blend") or {}).get("soft_retry") is not True, "blend security page is not a soft-retry")
    check(
        (entries.get("biogen") or {}).get("hit", {}).get("years", {}).get("year") == 1978,
        "biogen year in ledger",
    )
    check(
        (entries.get("biogen") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://www.biogen.com/company.html",
        "biogen year source in ledger",
    )
    check(
        (entries.get("biogen") or {}).get("hit", {}).get("years", {}).get("quote")
        == "Founded in 1978, Biogen is a leading biotechnology company that pioneers innovative science",
        "biogen year quote is the company sentence",
    )
    check(not (entries.get("biogen") or {}).get("hit", {}).get("page"), "biogen Official page stays unfiled")
    check(not (entries.get("biogen") or {}).get("hit", {}).get("marks"), "biogen marks stay unfiled")
    check(not (entries.get("biogen") or {}).get("hit", {}).get("dpa"), "biogen DPA stays unfiled")
    check(
        (entries.get("biostar") or {}).get("hit", {}).get("years", {}).get("year") == 1986,
        "biostar year in ledger",
    )
    check(
        (entries.get("biostar") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://www.biostar.com.tw/app/en/about/about_aboutus.php",
        "biostar year source in ledger",
    )
    check(
        (entries.get("biostar") or {}).get("hit", {}).get("years", {}).get("quote")
        == "Established In 1986 The founder of BIOSTAR GROUP,established BIOSTAR MICROTECH INTERNATIONAL CORP in 1986.",
        "biostar year quote is the about sentence",
    )
    check(not (entries.get("biostar") or {}).get("hit", {}).get("page"), "biostar security.php stays unfiled")
    check(not (entries.get("biostar") or {}).get("hit", {}).get("marks"), "biostar marks stay unfiled")
    check(not (entries.get("biostar") or {}).get("hit", {}).get("dpa"), "biostar DPA stays unfiled")
    check(
        (entries.get("bizagi") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.bizagi.com/en/platform/trust",
        "bizagi trust page in ledger",
    )
    check(
        (entries.get("bizagi") or {}).get("hit", {}).get("page", {}).get("kind") == "trust",
        "bizagi page kind is trust",
    )
    check(
        (entries.get("bizagi") or {}).get("hit", {}).get("years", {}).get("year") == 1989,
        "bizagi year in ledger",
    )
    check(
        (entries.get("bizagi") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://www.bizagi.com/en/about/the-team",
        "bizagi year source in ledger",
    )
    check(
        (entries.get("bizagi") or {}).get("hit", {}).get("years", {}).get("quote")
        == "In 1989 he founded Bizagi, short for business agility.",
        "bizagi year quote is the team sentence",
    )
    check(not (entries.get("bizagi") or {}).get("hit", {}).get("marks"), "bizagi marks stay unfiled")
    check(not (entries.get("bizagi") or {}).get("hit", {}).get("dpa"), "bizagi DPA stays unfiled")
    check(
        (entries.get("black-box-corporation") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.blackbox.com/discover-bb/trust-center",
        "black-box trust page in ledger",
    )
    check(
        (entries.get("black-box-corporation") or {}).get("hit", {}).get("page", {}).get("kind") == "trust",
        "black-box page kind is trust",
    )
    check(
        (entries.get("black-box-corporation") or {}).get("hit", {}).get("marks", {}).get("added")
        == [
            "SOC 2 Type II",
            "ISO 27001",
            "ISO 20000-1",
            "ISO 9001",
            "HIPAA",
            "Cyber Essentials",
            "CMMC L2",
        ],
        "black-box marks in ledger",
    )
    check(
        (entries.get("black-box-corporation") or {}).get("hit", {}).get("marks", {}).get("url")
        == "https://www.blackbox.com/discover-bb/trust-center",
        "black-box marks source in ledger",
    )
    check(not (entries.get("black-box-corporation") or {}).get("hit", {}).get("years"), "black-box year stays unfiled")
    check(not (entries.get("black-box-corporation") or {}).get("hit", {}).get("dpa"), "black-box DPA stays unfiled")
    check(
        (entries.get("blend") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://blend.com/security-and-compliance/",
        "blend security page in ledger",
    )
    check(
        (entries.get("blend") or {}).get("hit", {}).get("page", {}).get("kind") == "security",
        "blend page kind is security",
    )
    check(not (entries.get("blend") or {}).get("hit", {}).get("marks"), "blend marks stay unfiled")
    check(not (entries.get("blend") or {}).get("hit", {}).get("dpa"), "blend DPA stays unfiled")
    check(not (entries.get("blend") or {}).get("hit", {}).get("years"), "blend year stays unfiled")
    refused_1106_pm = {
        "birlasoft": "cybersecurity-services is Security-as-a-Service / client services marketing, not Birlasoft's own trust/security disclosure",
        "bitdeer": "security-vulnerability-submissions is VDP/bug-bounty form only, not Completeness trust/security/privacy/DPA",
        "bittium": "defence-security/ is Defence & Security product solutions marketing, not company trust/security disclosure",
        "bkash": "bkash.com/security returns WAF 'Request Rejected' page (~246B), not a real Completeness security page",
        "black-duck-software": "interactive-application-security-testing.html is Seeker IAST product marketing, not company trust/security disclosure",
        "blackpoint-cyber": "media Log4Shell news article, not Completeness trust/security/DPA",
        "blausen-medical": "sitesecurityaccess.aspx is library login/access wall; year blurb is not an official About founding page",
    }
    for slug, reason in refused_1106_pm.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-11-06", f"{slug} reaudited 2026-11-06")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
        check(row.get("soft_retry") is not True, f"{slug} drop is not a soft-retry")
        check(row.get("dropped") is True, f"{slug} drop is clerked")
    check((entries.get("bitsight") or {}).get("soft_retry") is True, "bitsight stays a Cloudflare soft-retry")
    check((entries.get("bitvavo") or {}).get("soft_retry") is True, "bitvavo stays a Cloudflare soft-retry")
    check((entries.get("blackstone-inc") or {}).get("soft_retry") is True, "blackstone-inc JS shell stays a soft-retry")
    check((entries.get("bitsight") or {}).get("hit") is None, "bitsight hit stays null")
    check((entries.get("bitvavo") or {}).get("hit") is None, "bitvavo hit stays null")
    check((entries.get("blackstone-inc") or {}).get("hit") is None, "blackstone-inc hit stays null")
    check((entries.get("bitsight") or {}).get("refusal") == "cloudflare", "bitsight refusal is cloudflare")
    check((entries.get("bitvavo") or {}).get("refusal") == "cloudflare", "bitvavo refusal is cloudflare")
    check((entries.get("blackstone-inc") or {}).get("refusal") == "js-shell", "blackstone-inc refusal is js-shell")

    batch_1109_am = [
        "blizoo",
        "blockstream",
        "bloomberg",
        "bloomfire",
        "blu-products",
        "blu-telecommunications",
        "blue-coat-systems",
        "blue-marble-geographics",
        "blue-ocean-contact-centres",
        "blue-origin",
        "blue-prism",
        "blue-star-infotech",
        "blue-systems",
        "blue-water-autonomy",
        "bluedot",
        "bluedot-innovation",
        "bluefish",
        "bluehost",
        "bluespace-federal",
        "bluespice",
        "bluetalon",
        "blueware",
        "bny-mellon",
        "board-international",
        "bodycote",
        "boe-technology",
        "boeing",
        "boeing-uk",
        "boku-inc",
        "boldon-james",
    ]
    check(batch == batch_1109_am, f"2026-11-09 morning batch {batch}")
    check(payload.get("batch_label") == "2026-11-09-am", f"batch_label {payload.get('batch_label')}")
    check(len(batch_1109_am) == 30, f"2026-11-09 morning batch is 30, got {len(batch_1109_am)}")
    check(
        batch_1109_am[0] == "blizoo" and batch_1109_am[-1] == "boldon-james",
        "2026-11-09 morning batch is the blizoo to boldon-james cut",
    )
    check(all(slug in entries for slug in batch_1109_am), "2026-11-09 morning rows stay in the ledger")
    check(summary.get("batch") == 30, "2026-11-09 morning summary.batch is 30")
    check(summary.get("fileable") == 7, f"2026-11-09 morning clerk fileable, got {summary.get('fileable')}")
    check(summary.get("soft_retry") == 10, f"2026-11-09 morning soft-retry, got {summary.get('soft_retry')}")
    check(summary.get("still_0") == 13, f"2026-11-09 morning still-0, got {summary.get('still_0')}")
    check(summary.get("filled") == 7, f"2026-11-09 morning clerk fills, got {summary.get('filled')}")
    check(summary.get("vetted_keep") == 7, f"2026-11-09 morning vetted keep, got {summary.get('vetted_keep')}")
    check(
        summary.get("vetted_drop_fileable") == 1,
        f"2026-11-09 morning vetted drops, got {summary.get('vetted_drop_fileable')}",
    )
    check(
        all((entries.get(slug) or {}).get("date") == "2026-11-09" for slug in batch_1109_am),
        "2026-11-09 morning cut is dated 2026-11-09",
    )
    check(not set(batch_1109_am) & set(batch_1106_pm), "2026-11-09 morning cut must be never-reaudited vs the afternoon holds")
    check(not set(batch_1109_am) & set(batch_1106_am), "2026-11-09 morning cut must be never-reaudited vs the morning holds")
    shipped_1109_am = {
        "blockstream": {"years"},
        "blu-products": {"years"},
        "blue-marble-geographics": {"years"},
        "blue-ocean-contact-centres": {"years"},
        "blue-prism": {"page", "marks"},
        "board-international": {"page"},
        "boeing": {"marks"},
    }
    for slug in batch_1109_am:
        row = entries.get(slug) or {}
        if row.get("soft_retry"):
            probed_classes = {item.get("class") for item in (row.get("probed") or [])}
            check(bool(probed_classes & soft_classes), f"{slug} soft-retry is marked")
        if slug in shipped_1109_am:
            check(row.get("filed") is True, f"{slug} ledger row records the apply")
            continue
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
    for slug, keys in shipped_1109_am.items():
        row = entries.get(slug) or {}
        check(row.get("filed") is True, f"{slug} ledger row records the apply")
        check(row.get("date") == "2026-11-09", f"{slug} filed date {row.get('date')}")
        check(set(row.get("filed_keys") or []) == keys, f"{slug} filed_keys {row.get('filed_keys')}")
        check(row.get("could_fill") == [k for k in FILE_KEYS if k in keys], f"{slug} could_fill {row.get('could_fill')}")
        check(row.get("fileable") is True, f"{slug} stays fileable")
        check(row.get("soft_retry") is not True, f"{slug} filed hold is not a soft-retry")
    check(
        (entries.get("blockstream") or {}).get("hit", {}).get("years", {}).get("year") == 2014,
        "blockstream year in ledger",
    )
    check(
        (entries.get("blockstream") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://blockstream.com/about/us",
        "blockstream year source in ledger",
    )
    check(
        (entries.get("blockstream") or {}).get("hit", {}).get("years", {}).get("quote")
        == "Store Support Help Center Bitcoin Education Glossary Local About Us Founded in 2014, Blockstream has been the leading provider of blockchain technologies and h.",
        "blockstream year quote is the about sentence",
    )
    check(not (entries.get("blockstream") or {}).get("hit", {}).get("page"), "blockstream Official page stays unfiled")
    check(not (entries.get("blockstream") or {}).get("hit", {}).get("marks"), "blockstream marks stay unfiled")
    check(not (entries.get("blockstream") or {}).get("hit", {}).get("dpa"), "blockstream DPA stays unfiled")
    check(
        (entries.get("blu-products") or {}).get("hit", {}).get("years", {}).get("year") == 2009,
        "blu-products year in ledger",
    )
    check(
        (entries.get("blu-products") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://www.bluproducts.com/home",
        "blu-products year source in ledger",
    )
    check(
        (entries.get("blu-products") or {}).get("hit", {}).get("years", {}).get("quote")
        == "BLU Products, founded in 2009, designs and manufacturers affordable, unlocked Android devices to suit a wide variety of consumer needs.",
        "blu-products year quote is the home sentence",
    )
    check(not (entries.get("blu-products") or {}).get("hit", {}).get("page"), "blu-products homepage stays unfiled")
    check(not (entries.get("blu-products") or {}).get("hit", {}).get("marks"), "blu-products marks stay unfiled")
    check(
        (entries.get("blue-marble-geographics") or {}).get("hit", {}).get("years", {}).get("year") == 1993,
        "blue-marble year in ledger",
    )
    check(
        (entries.get("blue-marble-geographics") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://www.bluemarblegeo.com/",
        "blue-marble year source in ledger",
    )
    check(
        (entries.get("blue-marble-geographics") or {}).get("hit", {}).get("years", {}).get("quote")
        == '"foundingDate":"1993"',
        "blue-marble year quote is the JSON-LD foundingDate",
    )
    check(not (entries.get("blue-marble-geographics") or {}).get("hit", {}).get("page"), "blue-marble Official page stays unfiled")
    check(
        (entries.get("blue-ocean-contact-centres") or {}).get("hit", {}).get("years", {}).get("year") == 1994,
        "blue-ocean year in ledger",
    )
    check(
        (entries.get("blue-ocean-contact-centres") or {}).get("hit", {}).get("years", {}).get("url")
        == "https://blueocean.ca/",
        "blue-ocean year source in ledger",
    )
    check(
        (entries.get("blue-ocean-contact-centres") or {}).get("hit", {}).get("years", {}).get("quote")
        == '"foundingDate": "1994"',
        "blue-ocean year quote is the JSON-LD foundingDate",
    )
    check(not (entries.get("blue-ocean-contact-centres") or {}).get("hit", {}).get("page"), "blue-ocean Official page stays unfiled")
    check(
        (entries.get("blue-prism") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.blueprism.com/blue-prism-security/",
        "blue-prism security page in ledger",
    )
    check(
        (entries.get("blue-prism") or {}).get("hit", {}).get("page", {}).get("kind") == "security",
        "blue-prism page kind is security",
    )
    check(
        (entries.get("blue-prism") or {}).get("hit", {}).get("marks", {}).get("added") == ["Cyber Essentials"],
        "blue-prism Cyber Essentials in ledger",
    )
    check(
        (entries.get("blue-prism") or {}).get("hit", {}).get("marks", {}).get("quote")
        == "Our policies and procedures are built on ISO270001 and Cyber Essentials guidelines.",
        "blue-prism marks quote is the security sentence",
    )
    check(not (entries.get("blue-prism") or {}).get("hit", {}).get("years"), "blue-prism year stays unfiled")
    check(not (entries.get("blue-prism") or {}).get("hit", {}).get("dpa"), "blue-prism DPA stays unfiled")
    check(
        (entries.get("board-international") or {}).get("hit", {}).get("page", {}).get("url")
        == "https://www.board.com/governance-and-compliance",
        "board governance page in ledger",
    )
    check(
        (entries.get("board-international") or {}).get("hit", {}).get("page", {}).get("kind") == "trust",
        "board page kind is trust",
    )
    check(not (entries.get("board-international") or {}).get("hit", {}).get("marks"), "board marks stay unfiled")
    check(not (entries.get("board-international") or {}).get("hit", {}).get("years"), "board year stays unfiled")
    check(
        (entries.get("boeing") or {}).get("hit", {}).get("marks", {}).get("added") == ["EU-US DPF"],
        "boeing EU-US DPF in ledger",
    )
    check(
        (entries.get("boeing") or {}).get("hit", {}).get("marks", {}).get("url")
        == "https://www.boeing.com/privacy-and-cookie-policy",
        "boeing marks source in ledger",
    )
    check(
        (entries.get("boeing") or {}).get("hit", {}).get("marks", {}).get("quote")
        == "(for the purposes of this section, collectively referred to as &quot;Boeing DPF Companies&quot;) participate in the EU-U.S. Data Privacy Framework (“EU-U.",
        "boeing marks quote is the DPF participation sentence",
    )
    check(not (entries.get("boeing") or {}).get("hit", {}).get("page"), "boeing FAA feature stays unfiled")
    check(not (entries.get("boeing") or {}).get("hit", {}).get("years"), "boeing year stays unfiled")
    check(not (entries.get("boeing") or {}).get("hit", {}).get("dpa"), "boeing DPA stays unfiled")
    refused_1109_am = {
        "bluespice": "en.wiki.bluespice.com/wiki/Info:Trust_and_Safety is the BlueSpice helpdesk wiki, not the company's trust/security disclosure",
    }
    for slug, reason in refused_1109_am.items():
        row = entries.get(slug) or {}
        check(row.get("date") == "2026-11-09", f"{slug} reaudited 2026-11-09")
        check(row.get("filed") is not True, f"{slug} was not filed")
        check(row.get("fileable") is False, f"{slug} reads as still 0")
        check(not row.get("could_fill"), f"{slug} could_fill stays empty")
        check(not row.get("hit"), f"{slug} hit stays empty")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
        check(row.get("soft_retry") is not True, f"{slug} drop is not a soft-retry")
        check(row.get("dropped") is True, f"{slug} drop is clerked")
    for slug, reason in {
        "bloomberg": "http-403",
        "bloomfire": "http-403",
        "blue-star-infotech": "js-shell",
        "blue-systems": "js-shell",
        "bluehost": "http-403",
        "blueware": "http-403",
        "bodycote": "cloudflare",
        "boeing-uk": "http-403",
        "boku-inc": "js-shell",
        "boldon-james": "http-403",
    }.items():
        row = entries.get(slug) or {}
        check(row.get("soft_retry") is True, f"{slug} stays a soft-retry")
        check(row.get("hit") is None, f"{slug} hit stays null")
        check(row.get("refusal") == reason, f"{slug} refusal {row.get('refusal')}")
        check(row.get("filed") is not True, f"{slug} was not filed")

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

    pub_alkami = by_pub["alkami"]
    check(pub_alkami.get("founded_year") == 2009, "alkami year is first-party press room")
    check(pub_alkami.get("founded_source") == "https://www.alkami.com/press-room", "alkami year source")
    check((pub_alkami.get("file") or {}).get("years") == 20, "alkami years print")
    check(completeness(pub_alkami) == 20, f"alkami Completeness {completeness(pub_alkami)}")
    check(pub_alkami.get("found") is False, "alkami Official page stays open")
    check(not pub_alkami.get("trust_url"), "alkami demo page is not Official page")
    check(not (pub_alkami.get("certs") or []), "alkami marks stay open")

    pub_allied = by_pub["allied-van-lines"]
    check(pub_allied.get("certs") == ["EU-US DPF"], f"allied-van-lines marks {pub_allied.get('certs')}")
    check((pub_allied.get("file") or {}).get("marks") == 20, "allied-van-lines marks print")
    check(completeness(pub_allied) == 20, f"allied-van-lines Completeness {completeness(pub_allied)}")
    check(pub_allied.get("found") is False, "allied-van-lines Official page stays open")
    check(not pub_allied.get("founded_year"), "allied-van-lines year stays open")

    for slug in (
        "a1-hrvatska",
        "allbusiness-com",
        "allego",
        "allot",
        "altacast",
    ):
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")

    pub_ambu = by_pub["ambu"]
    check(pub_ambu.get("founded_year") == 1937, "ambu year is first-party history")
    check(pub_ambu.get("founded_source") == "https://www.ambu.com/about/our-history", "ambu year source")
    check((pub_ambu.get("file") or {}).get("years") == 20, "ambu years print")
    check(completeness(pub_ambu) == 20, f"ambu Completeness {completeness(pub_ambu)}")
    check(pub_ambu.get("found") is False, "ambu Official page stays open")
    check(not pub_ambu.get("trust_url"), "ambu Official page stays open")
    check(not (pub_ambu.get("certs") or []), "ambu marks stay open")

    pub_amex = by_pub["american-express"]
    check(pub_amex.get("founded_year") == 1850, "american-express year is first-party investor relations")
    check(
        pub_amex.get("founded_source") == "https://ir.americanexpress.com/investor-relations/default.aspx",
        "american-express year source",
    )
    check((pub_amex.get("file") or {}).get("years") == 20, "american-express years print")
    check(completeness(pub_amex) == 20, f"american-express Completeness {completeness(pub_amex)}")
    check(pub_amex.get("found") is False, "american-express Official page stays open")
    check(not pub_amex.get("trust_url"), "american-express consumer security center is not Official page")
    check(not (pub_amex.get("certs") or []), "american-express marks stay open")
    check(not ((pub_amex.get("instruments") or {}).get("dpa") or {}).get("url"), "american-express DPA stays open")

    for slug in (
        "altair-engineering",
        "alterg",
        "altice",
        "altinity",
        "altova",
        "alvion",
        "amco-burglar-alarm-company",
        "american-sammy",
    ):
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    pub_amgen = by_pub["amgen"]
    check(pub_amgen.get("founded_year") == 1980, "amgen year is first-party history")
    check(pub_amgen.get("founded_source") == "https://www.amgen.com/about/amgen-history", "amgen year source")
    check((pub_amgen.get("file") or {}).get("years") == 20, "amgen years print")
    check(completeness(pub_amgen) == 20, f"amgen Completeness {completeness(pub_amgen)}")
    check(pub_amgen.get("found") is False, "amgen Official page stays open")
    check(not pub_amgen.get("trust_url"), "amgen Official page stays open")
    check(not (pub_amgen.get("certs") or []), "amgen marks stay open")

    pub_anc = by_pub["ancestry-com"]
    check(pub_anc.get("found") is True, "ancestry Official page is on file")
    check(
        pub_anc.get("trust_url") == "https://www.ancestry.com/c/legal/security",
        "ancestry Official page is the first-party security page",
    )
    check((pub_anc.get("file") or {}).get("page") == 20, "ancestry Official page prints")
    check(not (pub_anc.get("certs") or []), "ancestry marks stay open")
    check(completeness(pub_anc) == 30, f"ancestry Completeness {completeness(pub_anc)}")
    check(not pub_anc.get("founded_year"), "ancestry year stays open")
    check(not ((pub_anc.get("instruments") or {}).get("dpa") or {}).get("url"), "ancestry DPA stays open")

    for slug in batch_1029_pm:
        if slug in {"amgen", "ancestry-com"}:
            continue
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    pub_anomali = by_pub["anomali"]
    check(pub_anomali.get("found") is True, "anomali Official page is on file")
    check(
        pub_anomali.get("trust_url") == "https://www.anomali.com/security",
        "anomali Official page is the first-party security page",
    )
    check((pub_anomali.get("file") or {}).get("page") == 20, "anomali Official page prints")
    check((pub_anomali.get("file") or {}).get("marks") == 10, "anomali page-without-marks partial prints")
    check(not (pub_anomali.get("certs") or []), "anomali marks stay open")
    check(completeness(pub_anomali) == 30, f"anomali Completeness {completeness(pub_anomali)}")
    check(not pub_anomali.get("founded_year"), "anomali year stays open")
    check(not ((pub_anomali.get("instruments") or {}).get("dpa") or {}).get("url"), "anomali DPA stays open")

    pub_anro = by_pub["anro"]
    check(
        set(pub_anro.get("certs") or []) == {"SOC 2 Type II", "PCI DSS"},
        f"anro marks {pub_anro.get('certs')}",
    )
    check("HIPAA" not in (pub_anro.get("certs") or []), "anro HIPAA stays off the marks rule")
    check((pub_anro.get("file") or {}).get("marks") == 20, "anro marks print")
    check(completeness(pub_anro) == 20, f"anro Completeness {completeness(pub_anro)}")
    check(pub_anro.get("found") is False, "anro privacy policy is not Official page")
    check(not pub_anro.get("trust_url"), "anro Official page stays open")
    check(not pub_anro.get("founded_year"), "anro year stays open")

    pub_antec = by_pub["antec"]
    check(pub_antec.get("founded_year") == 1986, "antec year is first-party about")
    check(pub_antec.get("founded_source") == "https://antec.com/aboutus", "antec year source")
    check((pub_antec.get("file") or {}).get("years") == 20, "antec years print")
    check(completeness(pub_antec) == 20, f"antec Completeness {completeness(pub_antec)}")
    check(pub_antec.get("found") is False, "antec Official page stays open")
    check(not pub_antec.get("trust_url"), "antec Official page stays open")
    check(not (pub_antec.get("certs") or []), "antec marks stay open")

    pub_anti = by_pub["antithesis"]
    check(pub_anti.get("found") is True, "antithesis Official page is on file")
    check(
        pub_anti.get("trust_url") == "https://antithesis.com/security/manifesto/",
        "antithesis Official page is the first-party security manifesto",
    )
    check((pub_anti.get("file") or {}).get("page") == 20, "antithesis Official page prints")
    check((pub_anti.get("file") or {}).get("marks") == 10, "antithesis page-without-marks partial prints")
    check(not (pub_anti.get("certs") or []), "antithesis marks stay open")
    check(completeness(pub_anti) == 30, f"antithesis Completeness {completeness(pub_anti)}")
    check(not pub_anti.get("founded_year"), "antithesis year stays open")
    check(not ((pub_anti.get("instruments") or {}).get("dpa") or {}).get("url"), "antithesis DPA stays open")

    for slug in ("animoca-brands", "aon-plc", "apex-learning"):
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    for slug in batch_1030_am:
        if slug in shipped_1030:
            continue
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    pub_apollo = by_pub["apollo-global-management"]
    check(pub_apollo.get("founded_year") == 1990, "apollo year is first-party about")
    check(pub_apollo.get("founded_source") == "https://www.apollo.com/aboutus", "apollo year source")
    check((pub_apollo.get("file") or {}).get("years") == 20, "apollo years print")
    check(completeness(pub_apollo) == 20, f"apollo Completeness {completeness(pub_apollo)}")
    check(pub_apollo.get("found") is False, "apollo Official page stays open")
    check(not pub_apollo.get("trust_url"), "apollo Official page stays open")
    check(not (pub_apollo.get("certs") or []), "apollo marks stay open")

    pub_circle = by_pub["appcircle"]
    check(pub_circle.get("found") is True, "appcircle Official page is on file")
    check(
        pub_circle.get("trust_url") == "https://appcircle.io/security",
        "appcircle Official page is the first-party security page",
    )
    check((pub_circle.get("file") or {}).get("page") == 20, "appcircle Official page prints")
    check((pub_circle.get("file") or {}).get("marks") == 10, "appcircle page-without-marks partial prints")
    check(not (pub_circle.get("certs") or []), "appcircle marks stay open")
    check(completeness(pub_circle) == 30, f"appcircle Completeness {completeness(pub_circle)}")
    check(not pub_circle.get("founded_year"), "appcircle year stays open")
    check(not ((pub_circle.get("instruments") or {}).get("dpa") or {}).get("url"), "appcircle DPA stays open")

    pub_apply = by_pub["applyboard"]
    check(pub_apply.get("found") is True, "applyboard Official page is on file")
    check(
        pub_apply.get("trust_url") == "https://www.applyboard.com/security",
        "applyboard Official page is the first-party security page",
    )
    check((pub_apply.get("file") or {}).get("page") == 20, "applyboard Official page prints")
    check((pub_apply.get("file") or {}).get("marks") == 10, "applyboard page-without-marks partial prints")
    check(not (pub_apply.get("certs") or []), "applyboard has not pursued SOC 2; marks stay open")
    check(completeness(pub_apply) == 30, f"applyboard Completeness {completeness(pub_apply)}")
    check(not pub_apply.get("founded_year"), "applyboard year stays open")
    check(not ((pub_apply.get("instruments") or {}).get("dpa") or {}).get("url"), "applyboard DPA stays open")

    pub_apptio = by_pub["apptio"]
    check(pub_apptio.get("found") is True, "apptio Official page is on file")
    check(
        pub_apptio.get("trust_url") == "https://www.apptio.com/company/trust/",
        "apptio Official page is the first-party trust page",
    )
    check((pub_apptio.get("file") or {}).get("page") == 20, "apptio Official page prints")
    check((pub_apptio.get("file") or {}).get("marks") == 10, "apptio page-without-marks partial prints")
    check(not (pub_apptio.get("certs") or []), "apptio marks stay open")
    check(completeness(pub_apptio) == 30, f"apptio Completeness {completeness(pub_apptio)}")
    check(not pub_apptio.get("founded_year"), "apptio year stays open")
    check(not ((pub_apptio.get("instruments") or {}).get("dpa") or {}).get("url"), "apptio DPA stays open")

    for slug in ("applovin", "appota-corporation", "aprimo"):
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    for slug in batch_1030_pm:
        if slug in shipped_1030_pm:
            continue
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    pub_aptiv = by_pub["aptiv"]
    check(pub_aptiv.get("found") is True, "aptiv Official page is on file")
    check(
        pub_aptiv.get("trust_url") == "https://win.aptiv.com/locations-and-certifications",
        "aptiv Official page is the certifications page",
    )
    check(
        set(pub_aptiv.get("certs") or []) == {"ISO 13485", "ISO 9001"},
        f"aptiv marks {pub_aptiv.get('certs')}",
    )
    check((pub_aptiv.get("file") or {}).get("page") == 20, "aptiv Official page prints")
    check((pub_aptiv.get("file") or {}).get("marks") == 20, "aptiv marks print")
    check(completeness(pub_aptiv) == 40, f"aptiv Completeness {completeness(pub_aptiv)}")
    check(not pub_aptiv.get("founded_year"), "aptiv year stays open")
    check(not ((pub_aptiv.get("instruments") or {}).get("dpa") or {}).get("url"), "aptiv DPA stays open")

    pub_aptos = by_pub["aptos-labs"]
    check(pub_aptos.get("founded_year") == 2022, "aptos-labs year is first-party home")
    check(pub_aptos.get("founded_source") == "https://aptoslabs.com/", "aptos-labs year source")
    check((pub_aptos.get("file") or {}).get("years") == 20, "aptos-labs years print")
    check(completeness(pub_aptos) == 20, f"aptos-labs Completeness {completeness(pub_aptos)}")
    check(pub_aptos.get("found") is False, "aptos-labs Official page stays open")
    check(not pub_aptos.get("trust_url"), "aptos-labs Official page stays open")
    check(not (pub_aptos.get("certs") or []), "aptos-labs marks stay open")

    pub_arcserve = by_pub["arcserve"]
    check(pub_arcserve.get("founded_year") == 1983, "arcserve year is first-party privacy notice")
    check(
        pub_arcserve.get("founded_source") == "https://www.arcserve.com/privacy-notice",
        "arcserve year source",
    )
    check((pub_arcserve.get("file") or {}).get("years") == 20, "arcserve years print")
    check(completeness(pub_arcserve) == 20, f"arcserve Completeness {completeness(pub_arcserve)}")
    check(pub_arcserve.get("found") is False, "arcserve Official page stays open")
    check(not pub_arcserve.get("trust_url"), "arcserve Official page stays open")
    check(not (pub_arcserve.get("certs") or []), "arcserve marks stay open")

    pub_arctic = by_pub["arctic-gmbh"]
    check(pub_arctic.get("founded_year") == 2001, "arctic-gmbh year is first-party locations")
    check(
        pub_arctic.get("founded_source") == "https://www.arctic.de/us/about-arctic/locations",
        "arctic-gmbh year source",
    )
    check((pub_arctic.get("file") or {}).get("years") == 20, "arctic-gmbh years print")
    check(completeness(pub_arctic) == 20, f"arctic-gmbh Completeness {completeness(pub_arctic)}")
    check(pub_arctic.get("found") is False, "arctic-gmbh homepage bounce is not Official page")
    check(not pub_arctic.get("trust_url"), "arctic-gmbh Official page stays open")
    check(not (pub_arctic.get("certs") or []), "arctic-gmbh marks stay open")

    pub_argonide = by_pub["argonide"]
    check(pub_argonide.get("found") is True, "argonide Official page is on file")
    check(
        pub_argonide.get("trust_url")
        == "https://www.argonide.com/about-argonide-water-filter-manufacturing/iso-9001-certified",
        "argonide Official page is the ISO 9001 page",
    )
    check((pub_argonide.get("file") or {}).get("page") == 20, "argonide Official page prints")
    check((pub_argonide.get("file") or {}).get("marks") == 10, "argonide page-without-marks partial prints")
    check(not (pub_argonide.get("certs") or []), "argonide marks stay open")
    check(completeness(pub_argonide) == 30, f"argonide Completeness {completeness(pub_argonide)}")
    check(not pub_argonide.get("founded_year"), "argonide year stays open")
    check(not ((pub_argonide.get("instruments") or {}).get("dpa") or {}).get("url"), "argonide DPA stays open")

    for slug in ("aptum-technologies", "archax", "archer-daniels-midland", "arecont-vision"):
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    for slug in batch_1102_am:
        if slug in shipped_1102:
            continue
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    pub_argotec = by_pub["argotec"]
    check(pub_argotec.get("certs") == ["ISO 9001"], f"argotec marks {pub_argotec.get('certs')}")
    check("ISO 27001" not in (pub_argotec.get("certs") or []), "argotec ISO 27001 stays off the marks rule")
    check(pub_argotec.get("founded_year") == 2008, "argotec year is first-party privacy policy JSON-LD")
    check(
        pub_argotec.get("founded_source") == "https://www.argotecgroup.com/privacy-policy",
        "argotec year source",
    )
    check((pub_argotec.get("file") or {}).get("marks") == 20, "argotec marks print")
    check((pub_argotec.get("file") or {}).get("years") == 20, "argotec years print")
    check(completeness(pub_argotec) == 40, f"argotec Completeness {completeness(pub_argotec)}")
    check(pub_argotec.get("found") is False, "argotec Official page stays open")
    check(not pub_argotec.get("trust_url"), "argotec Official page stays open")

    pub_ariel = by_pub["ariel-investments"]
    check(pub_ariel.get("founded_year") == 1983, "ariel year is first-party home")
    check(pub_ariel.get("founded_source") == "https://www.arielinvestments.com/", "ariel year source")
    check((pub_ariel.get("file") or {}).get("years") == 20, "ariel years print")
    check(completeness(pub_ariel) == 20, f"ariel Completeness {completeness(pub_ariel)}")
    check(pub_ariel.get("found") is False, "ariel Official page stays open")
    check(not pub_ariel.get("trust_url"), "ariel Official page stays open")
    check(not (pub_ariel.get("certs") or []), "ariel marks stay open")

    pub_aruba = by_pub["aruba-s-p-a"]
    check(
        set(pub_aruba.get("certs") or [])
        == {
            "SOC 2 Type II",
            "SOC 1 Type II",
            "ISO 27001",
            "ISO 27017",
            "ISO 27018",
            "ISO 27701",
            "ISO 22301",
            "ISO 20000-1",
            "ISO 9001",
            "CSA STAR",
        },
        f"aruba marks {pub_aruba.get('certs')}",
    )
    for dropped_mark in ("GDPR", "DORA", "NIS2"):
        check(dropped_mark not in (pub_aruba.get("certs") or []), f"aruba {dropped_mark} stays off the marks rule")
    check(pub_aruba.get("founded_year") == 1994, "aruba year is first-party about")
    check(pub_aruba.get("founded_source") == "https://www.aruba.it/en/about-us.aspx", "aruba year source")
    check((pub_aruba.get("file") or {}).get("marks") == 20, "aruba marks print")
    check((pub_aruba.get("file") or {}).get("years") == 20, "aruba years print")
    check(completeness(pub_aruba) == 40, f"aruba Completeness {completeness(pub_aruba)}")
    check(pub_aruba.get("found") is False, "aruba SSL product page is not Official page")
    check(not pub_aruba.get("trust_url"), "aruba Official page stays open")

    pub_asbis = by_pub["asbis"]
    check(pub_asbis.get("found") is True, "asbis Official page is on file")
    check(
        pub_asbis.get("trust_url") == "https://www.asbis.com/documents-and-certificates",
        "asbis Official page is the documents and certificates page",
    )
    check(pub_asbis.get("certs") == ["ISO 9001"], f"asbis marks {pub_asbis.get('certs')}")
    check("ISO 14001" not in (pub_asbis.get("certs") or []), "asbis ISO 14001 stays off the marks rule")
    check((pub_asbis.get("file") or {}).get("page") == 20, "asbis Official page prints")
    check((pub_asbis.get("file") or {}).get("marks") == 20, "asbis marks print")
    check(completeness(pub_asbis) == 40, f"asbis Completeness {completeness(pub_asbis)}")
    check(not pub_asbis.get("founded_year"), "asbis year stays open")

    pub_ascon = by_pub["ascon"]
    check(pub_ascon.get("founded_year") == 1989, "ascon year is first-party company page")
    check(pub_ascon.get("founded_source") == "https://ascon.net/company", "ascon year source")
    check((pub_ascon.get("file") or {}).get("years") == 20, "ascon years print")
    check(completeness(pub_ascon) == 20, f"ascon Completeness {completeness(pub_ascon)}")
    check(pub_ascon.get("found") is False, "ascon product certification page is not Official page")
    check(not pub_ascon.get("trust_url"), "ascon Official page stays open")
    check(not (pub_ascon.get("certs") or []), "ascon marks stay open")

    for slug in ("arkova", "array-networks", "arthur-j-gallagher-and-co", "aselsan"):
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    for slug in batch_1102_pm:
        if slug in shipped_1102_pm:
            continue
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    pub_asian = by_pub["asian-vision"]
    check(pub_asian.get("founded_year") == 1973, "asian-vision year is first-party home JSON-LD")
    check(pub_asian.get("founded_source") == "https://www.asianvision.com.ph/", "asian-vision year source")
    check((pub_asian.get("file") or {}).get("years") == 20, "asian-vision years print")
    check(completeness(pub_asian) == 20, f"asian-vision Completeness {completeness(pub_asian)}")
    check(pub_asian.get("found") is False, "asian-vision Official page stays open")
    check(not pub_asian.get("trust_url"), "asian-vision Official page stays open")
    check(not (pub_asian.get("certs") or []), "asian-vision marks stay open")

    pub_asseco = by_pub["asseco-business-solutions"]
    check(pub_asseco.get("found") is True, "asseco Official page is on file")
    check(
        pub_asseco.get("trust_url") == "https://assecobs.pl/certificates/?lang=en",
        "asseco Official page is the certificates page",
    )
    check(pub_asseco.get("certs") == ["ISO 27001"], f"asseco marks {pub_asseco.get('certs')}")
    check((pub_asseco.get("file") or {}).get("page") == 20, "asseco Official page prints")
    check((pub_asseco.get("file") or {}).get("marks") == 20, "asseco marks print")
    check(completeness(pub_asseco) == 40, f"asseco Completeness {completeness(pub_asseco)}")
    check(not pub_asseco.get("founded_year"), "asseco year stays open")

    pub_assessio = by_pub["assessio"]
    check(pub_assessio.get("found") is True, "assessio Official page is on file")
    check(
        pub_assessio.get("trust_url") == "https://assessio.com/trust-center/",
        "assessio Official page is the trust center",
    )
    check(pub_assessio.get("certs") == ["ISO 27001"], f"assessio marks {pub_assessio.get('certs')}")
    check("GDPR" not in (pub_assessio.get("certs") or []), "assessio GDPR stays off the marks rule")
    check(pub_assessio.get("founded_year") == 1954, "assessio year is first-party privacy notice")
    check(
        pub_assessio.get("founded_source") == "https://assessio.com/trust-center/privacy-notice-sweden/",
        "assessio year source",
    )
    check((pub_assessio.get("file") or {}).get("page") == 20, "assessio Official page prints")
    check((pub_assessio.get("file") or {}).get("marks") == 20, "assessio marks print")
    check((pub_assessio.get("file") or {}).get("years") == 20, "assessio years print")
    check(completeness(pub_assessio) == 60, f"assessio Completeness {completeness(pub_assessio)}")
    check(not ((pub_assessio.get("instruments") or {}).get("dpa") or {}).get("url"), "assessio DPA stays open")

    pub_astra = by_pub["astraqom"]
    check(pub_astra.get("founded_year") == 2008, "astraqom year is first-party home JSON-LD")
    check(pub_astra.get("founded_source") == "https://astraqom.com/en", "astraqom year source")
    check((pub_astra.get("file") or {}).get("years") == 20, "astraqom years print")
    check(completeness(pub_astra) == 20, f"astraqom Completeness {completeness(pub_astra)}")
    check(pub_astra.get("found") is False, "astraqom Official page stays open")
    check(not pub_astra.get("trust_url"), "astraqom Official page stays open")
    check(not (pub_astra.get("certs") or []), "astraqom marks stay open")

    pub_atands = by_pub["atands"]
    check(pub_atands.get("founded_year") == 1987, "atands year is first-party company page")
    check(pub_atands.get("founded_source") == "https://ats.net/en/company", "atands year source")
    check((pub_atands.get("file") or {}).get("years") == 20, "atands years print")
    check(completeness(pub_atands) == 20, f"atands Completeness {completeness(pub_atands)}")
    check(pub_atands.get("found") is False, "atands /security page is not Official page")
    check(not pub_atands.get("trust_url"), "atands Official page stays open")
    check(not (pub_atands.get("certs") or []), "atands marks stay open")

    pub_astro = by_pub["astrolabs"]
    check(pub_astro.get("founded_year") == 2013, "astrolabs year is first-party about")
    check(pub_astro.get("founded_source") == "https://astrolabs.com/about-us", "astrolabs year source")
    check((pub_astro.get("file") or {}).get("years") == 20, "astrolabs years print")
    check(completeness(pub_astro) == 20, f"astrolabs Completeness {completeness(pub_astro)}")
    check(pub_astro.get("found") is False, "astrolabs construction article is not Official page")
    check(not pub_astro.get("trust_url"), "astrolabs Official page stays open")
    check(not (pub_astro.get("certs") or []), "astrolabs marks stay open")

    for slug in (
        "asix-s-r-o",
        "aspen-technology",
        "asrock",
        "astound-broadband",
        "asure-software",
        "asustor",
    ):
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    for slug in batch_1103_am:
        if slug in shipped_1103:
            continue
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    pub_ateam = by_pub["ateam-inc"]
    check(pub_ateam.get("found") is True, "ateam-inc Official page is on file")
    check(
        pub_ateam.get("trust_url") == "https://www.a-tm.co.jp/securitypolicy/",
        "ateam-inc Official page is the security policy",
    )
    check((pub_ateam.get("file") or {}).get("page") == 20, "ateam-inc Official page prints")
    check((pub_ateam.get("file") or {}).get("marks") == 10, "ateam-inc page-without-marks partial prints")
    check(not (pub_ateam.get("certs") or []), "ateam-inc marks stay open")
    check(completeness(pub_ateam) == 30, f"ateam-inc Completeness {completeness(pub_ateam)}")
    check(not pub_ateam.get("founded_year"), "ateam-inc year stays open")
    check(not ((pub_ateam.get("instruments") or {}).get("dpa") or {}).get("url"), "ateam-inc DPA stays open")

    pub_ateme = by_pub["ateme"]
    check(pub_ateme.get("found") is True, "ateme Official page is on file")
    check(
        pub_ateme.get("trust_url") == "https://www.ateme.com/quality-certifications/",
        "ateme Official page is the quality certifications page",
    )
    check(pub_ateme.get("certs") == ["ISO 9001"], f"ateme marks {pub_ateme.get('certs')}")
    check(pub_ateme.get("founded_year") == 1991, "ateme year is first-party about")
    check(pub_ateme.get("founded_source") == "https://www.ateme.com/about-us", "ateme year source")
    check((pub_ateme.get("file") or {}).get("page") == 20, "ateme Official page prints")
    check((pub_ateme.get("file") or {}).get("marks") == 20, "ateme marks print")
    check((pub_ateme.get("file") or {}).get("years") == 20, "ateme years print")
    check(completeness(pub_ateme) == 60, f"ateme Completeness {completeness(pub_ateme)}")
    check(not ((pub_ateme.get("instruments") or {}).get("dpa") or {}).get("url"), "ateme DPA stays open")

    pub_atomic = by_pub["atomic-object"]
    check(pub_atomic.get("founded_year") == 2001, "atomic-object year is first-party home JSON-LD")
    check(pub_atomic.get("founded_source") == "https://atomicobject.com/", "atomic-object year source")
    check((pub_atomic.get("file") or {}).get("years") == 20, "atomic-object years print")
    check(completeness(pub_atomic) == 20, f"atomic-object Completeness {completeness(pub_atomic)}")
    check(pub_atomic.get("found") is False, "atomic-object Official page stays open")
    check(not pub_atomic.get("trust_url"), "atomic-object Official page stays open")
    check(not (pub_atomic.get("certs") or []), "atomic-object marks stay open")

    check(completeness(by_pub["atm-mobilis"]) == 0, "atm-mobilis Completeness stays 0")
    check(by_pub["atm-mobilis"].get("found") is False, "atm-mobilis WAF page is not Official page")
    check(not by_pub["atm-mobilis"].get("trust_url"), "atm-mobilis Official page stays open")
    check(not (by_pub["atm-mobilis"].get("certs") or []), "atm-mobilis marks stay open")
    check(not by_pub["atm-mobilis"].get("founded_year"), "atm-mobilis year stays open")

    for slug in batch_1103_pm:
        if slug in shipped_1103_pm:
            continue
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    pub_auth = by_pub["authorize-net"]
    check(pub_auth.get("found") is False, "authorize-net Official page stays open")
    check(not pub_auth.get("trust_url"), "authorize-net Official page stays open")
    check(not (pub_auth.get("certs") or []), "authorize-net marks stay open")
    check(not pub_auth.get("founded_year"), "authorize-net year stays open")
    check(
        ((pub_auth.get("instruments") or {}).get("dpa") or {}).get("url")
        == "https://www.authorize.net/about-us/dpa.html",
        "authorize-net DPA URL",
    )
    check((pub_auth.get("file") or {}).get("dpa") == 20, "authorize-net DPA prints")
    check(completeness(pub_auth) == 20, f"authorize-net Completeness {completeness(pub_auth)}")

    pub_avaya = by_pub["avaya"]
    check(pub_avaya.get("found") is True, "avaya Official page is on file")
    check(
        pub_avaya.get("trust_url") == "https://www.avaya.com/en/trust-center/",
        "avaya Official page is the trust center",
    )
    check(pub_avaya.get("certs") == ["FedRAMP"], f"avaya marks {pub_avaya.get('certs')}")
    check("GDPR" not in (pub_avaya.get("certs") or []), "avaya GDPR stays off the marks rule")
    check((pub_avaya.get("file") or {}).get("page") == 20, "avaya Official page prints")
    check((pub_avaya.get("file") or {}).get("marks") == 20, "avaya marks print")
    check(completeness(pub_avaya) == 40, f"avaya Completeness {completeness(pub_avaya)}")
    check(not pub_avaya.get("founded_year"), "avaya year stays open")
    check(not ((pub_avaya.get("instruments") or {}).get("dpa") or {}).get("url"), "avaya DPA stays open")

    pub_award = by_pub["awardwallet"]
    check(pub_award.get("founded_year") == 2004, "awardwallet year is first-party about")
    check(pub_award.get("founded_source") == "https://awardwallet.com/page/about", "awardwallet year source")
    check((pub_award.get("file") or {}).get("years") == 20, "awardwallet years print")
    check(completeness(pub_award) == 20, f"awardwallet Completeness {completeness(pub_award)}")
    check(pub_award.get("found") is False, "awardwallet Official page stays open")
    check(not pub_award.get("trust_url"), "awardwallet Official page stays open")
    check(not (pub_award.get("certs") or []), "awardwallet marks stay open")
    check(not ((pub_award.get("instruments") or {}).get("dpa") or {}).get("url"), "awardwallet DPA stays open")

    for slug in batch_1104_am:
        if slug in shipped_1104:
            continue
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")


    pub_axiata = by_pub["axiata"]
    check(pub_axiata.get("found") is True, "axiata Official page is on file")
    check(
        pub_axiata.get("trust_url") == "https://www.axiata.com/digital-trust/cybersecurity",
        "axiata Official page is the cybersecurity page",
    )
    check(not (pub_axiata.get("certs") or []), "axiata marks stay open")
    check("ISO 27001" not in (pub_axiata.get("certs") or []), "axiata ISO 27001 stays off the marks rule")
    check((pub_axiata.get("file") or {}).get("page") == 20, "axiata Official page prints")
    check((pub_axiata.get("file") or {}).get("marks") == 10, "axiata marks stay the looked-none partial")
    check(completeness(pub_axiata) == 30, f"axiata Completeness {completeness(pub_axiata)}")
    check(not pub_axiata.get("founded_year"), "axiata year stays open")
    check(not ((pub_axiata.get("instruments") or {}).get("dpa") or {}).get("url"), "axiata DPA stays open")

    pub_azer = by_pub["azercosmos"]
    check(pub_azer.get("found") is True, "azercosmos Official page is on file")
    check(
        pub_azer.get("trust_url") == "https://azercosmos.az/en/quality-and-information-security-policy",
        "azercosmos Official page is the security policy",
    )
    check(pub_azer.get("certs") == ["ISO 27001", "ISO 9001"], f"azercosmos marks {pub_azer.get('certs')}")
    check(pub_azer.get("founded_year") == 2010, "azercosmos year is first-party about")
    check(
        pub_azer.get("founded_source") == "https://azercosmos.az/en/about-us/our-story",
        "azercosmos year source",
    )
    check((pub_azer.get("file") or {}).get("page") == 20, "azercosmos Official page prints")
    check((pub_azer.get("file") or {}).get("marks") == 20, "azercosmos marks print")
    check((pub_azer.get("file") or {}).get("years") == 20, "azercosmos years print")
    check(completeness(pub_azer) == 60, f"azercosmos Completeness {completeness(pub_azer)}")
    check(not ((pub_azer.get("instruments") or {}).get("dpa") or {}).get("url"), "azercosmos DPA stays open")

    for slug in batch_1104_pm:
        if slug in shipped_1104_pm:
            continue
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    pub_bal = by_pub["balsamiq"]
    check(pub_bal.get("found") is False, "balsamiq Official page stays open")
    check(not pub_bal.get("trust_url"), "balsamiq Official page stays open")
    check(pub_bal.get("certs") == ["EU-US DPF", "SOC 2 Type II"], f"balsamiq marks {pub_bal.get('certs')}")
    check(
        ((pub_bal.get("instruments") or {}).get("dpa") or {}).get("url") == "https://balsamiq.com/legal/dpa/",
        "balsamiq DPA URL",
    )
    check(
        ((pub_bal.get("instruments") or {}).get("subprocessors") or {}).get("url")
        == "https://balsamiq.com/legal/subprocessors/",
        "balsamiq subprocessors URL",
    )
    check(
        [p.get("name") for p in (pub_bal.get("processors") or [])] == [
            "Amazon Web Services (AWS)",
            "Atlassian",
            "Cookiebot (Usercentrics)",
            "Customer.io",
            "Google (Ads)",
            "Google (Analytics)",
            "Google (Gemini)",
            "Google (Workspace)",
            "Help Scout",
            "PostHog",
            "Postmark",
            "Stripe",
        ],
        "balsamiq named list is the vetted 12",
    )
    check((pub_bal.get("file") or {}).get("marks") == 20, "balsamiq marks print")
    check((pub_bal.get("file") or {}).get("dpa") == 20, "balsamiq DPA prints")
    check((pub_bal.get("file") or {}).get("subprocessors") == 20, "balsamiq subprocessors print")
    check((pub_bal.get("file") or {}).get("page") == 0, "balsamiq Official page stays the open rule")
    check(completeness(pub_bal) == 60, f"balsamiq Completeness {completeness(pub_bal)}")
    check(not pub_bal.get("founded_year"), "balsamiq year stays open")

    pub_bar = by_pub["barracuda"]
    check(pub_bar.get("found") is True, "barracuda Official page is on file")
    check(pub_bar.get("trust_url") == "https://trust.barracuda.com/", "barracuda Official page is the trust center")
    check(not (pub_bar.get("certs") or []), "barracuda marks stay open")
    check((pub_bar.get("file") or {}).get("page") == 20, "barracuda Official page prints")
    check((pub_bar.get("file") or {}).get("marks") == 10, "barracuda marks stay the looked-none partial")
    check(completeness(pub_bar) == 30, f"barracuda Completeness {completeness(pub_bar)}")
    check(not pub_bar.get("founded_year"), "barracuda year stays open")
    check(not ((pub_bar.get("instruments") or {}).get("dpa") or {}).get("url"), "barracuda DPA stays open")

    pub_bat = by_pub["batliboi"]
    check(pub_bat.get("found") is False, "batliboi Official page stays open")
    check(pub_bat.get("founded_year") == 1892, "batliboi year is first-party about")
    check(
        pub_bat.get("founded_source") == "https://batliboi.com/about-us/overview/",
        "batliboi year source",
    )
    check((pub_bat.get("file") or {}).get("years") == 20, "batliboi years print")
    check(completeness(pub_bat) == 20, f"batliboi Completeness {completeness(pub_bat)}")
    check(not (pub_bat.get("certs") or []), "batliboi marks stay open")
    check(not ((pub_bat.get("instruments") or {}).get("dpa") or {}).get("url"), "batliboi DPA stays open")

    for slug in batch_1105_am:
        if slug in shipped_1105:
            continue
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    pub_batm = by_pub["batm"]
    check(pub_batm.get("found") is False, "batm Official page stays open")
    check(not pub_batm.get("trust_url"), "batm accessibility page is not Official page")
    check(pub_batm.get("founded_year") == 1992, "batm year is first-party about")
    check(
        pub_batm.get("founded_source") == "https://www.batm.com/company-governance/about-batm",
        "batm year source",
    )
    check((pub_batm.get("file") or {}).get("years") == 20, "batm years print")
    check(completeness(pub_batm) == 20, f"batm Completeness {completeness(pub_batm)}")
    check(not (pub_batm.get("certs") or []), "batm marks stay open")
    check(not ((pub_batm.get("instruments") or {}).get("dpa") or {}).get("url"), "batm DPA stays open")

    pub_bv = by_pub["bazaarvoice"]
    check(pub_bv.get("found") is True, "bazaarvoice Official page is on file")
    check(
        pub_bv.get("trust_url") == "https://www.bazaarvoice.com/company/trust/",
        "bazaarvoice Official page is the trust page",
    )
    check(not (pub_bv.get("certs") or []), "bazaarvoice marks stay open")
    check((pub_bv.get("file") or {}).get("page") == 20, "bazaarvoice Official page prints")
    check((pub_bv.get("file") or {}).get("marks") == 10, "bazaarvoice marks stay the looked-none partial")
    check(completeness(pub_bv) == 30, f"bazaarvoice Completeness {completeness(pub_bv)}")
    check(not pub_bv.get("founded_year"), "bazaarvoice year stays open")
    check(not ((pub_bv.get("instruments") or {}).get("dpa") or {}).get("url"), "bazaarvoice DPA stays open")

    pub_beh = by_pub["behringer"]
    check(pub_beh.get("found") is False, "behringer Official page stays open")
    check(pub_beh.get("founded_year") == 1989, "behringer year is first-party about")
    check(
        pub_beh.get("founded_source") == "https://behringer.com/en/about",
        "behringer year source",
    )
    check((pub_beh.get("file") or {}).get("years") == 20, "behringer years print")
    check(completeness(pub_beh) == 20, f"behringer Completeness {completeness(pub_beh)}")
    check(not (pub_beh.get("certs") or []), "behringer marks stay open")
    check(not ((pub_beh.get("instruments") or {}).get("dpa") or {}).get("url"), "behringer DPA stays open")

    for slug in batch_1105_pm:
        if slug in shipped_1105_pm:
            continue
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    pub_bp = by_pub["benchprep"]
    check(pub_bp.get("found") is True, "benchprep Official page is on file")
    check(
        pub_bp.get("trust_url") == "https://www.benchprep.com/security",
        "benchprep Official page is the security page",
    )
    check(not (pub_bp.get("certs") or []), "benchprep marks stay open")
    check((pub_bp.get("file") or {}).get("page") == 20, "benchprep Official page prints")
    check((pub_bp.get("file") or {}).get("marks") == 10, "benchprep marks stay the looked-none partial")
    check(completeness(pub_bp) == 30, f"benchprep Completeness {completeness(pub_bp)}")
    check(not pub_bp.get("founded_year"), "benchprep year stays open")
    check(not ((pub_bp.get("instruments") or {}).get("dpa") or {}).get("url"), "benchprep DPA stays open")
    check(
        ((pub_bp.get("instruments") or {}).get("security") or {}).get("url")
        == "https://www.benchprep.com/security",
        "benchprep security instrument URL",
    )

    pub_bil = by_pub["billion-electric"]
    check(pub_bil.get("found") is False, "billion-electric Official page stays open")
    check(not pub_bil.get("trust_url"), "billion-electric Official page URL stays open")
    check(pub_bil.get("founded_year") == 1973, "billion-electric year is first-party about")
    check(
        pub_bil.get("founded_source") == "https://www.billion.com/About-Billion",
        "billion-electric year source",
    )
    check((pub_bil.get("file") or {}).get("years") == 20, "billion-electric years print")
    check(completeness(pub_bil) == 20, f"billion-electric Completeness {completeness(pub_bil)}")
    check(not (pub_bil.get("certs") or []), "billion-electric marks stay open")
    check(not ((pub_bil.get("instruments") or {}).get("dpa") or {}).get("url"), "billion-electric DPA stays open")

    for slug in batch_1106_am:
        if slug in shipped_1106_am:
            continue
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    pub_biogen = by_pub["biogen"]
    check(pub_biogen.get("found") is False, "biogen Official page stays open")
    check(not pub_biogen.get("trust_url"), "biogen Official page URL stays open")
    check(pub_biogen.get("founded_year") == 1978, "biogen year is first-party company page")
    check(
        pub_biogen.get("founded_source") == "https://www.biogen.com/company.html",
        "biogen year source",
    )
    check((pub_biogen.get("file") or {}).get("years") == 20, "biogen years print")
    check(completeness(pub_biogen) == 20, f"biogen Completeness {completeness(pub_biogen)}")
    check(not (pub_biogen.get("certs") or []), "biogen marks stay open")
    check(not ((pub_biogen.get("instruments") or {}).get("dpa") or {}).get("url"), "biogen DPA stays open")

    pub_biostar = by_pub["biostar"]
    check(pub_biostar.get("found") is False, "biostar Official page stays open")
    check(not pub_biostar.get("trust_url"), "biostar Official page URL stays open")
    check(pub_biostar.get("founded_year") == 1986, "biostar year is first-party about")
    check(
        pub_biostar.get("founded_source") == "https://www.biostar.com.tw/app/en/about/about_aboutus.php",
        "biostar year source",
    )
    check((pub_biostar.get("file") or {}).get("years") == 20, "biostar years print")
    check(completeness(pub_biostar) == 20, f"biostar Completeness {completeness(pub_biostar)}")
    check(not (pub_biostar.get("certs") or []), "biostar marks stay open")
    check(not ((pub_biostar.get("instruments") or {}).get("dpa") or {}).get("url"), "biostar DPA stays open")
    check(not ((pub_biostar.get("instruments") or {}).get("security") or {}).get("url"), "biostar security.php stays off the file")

    pub_bizagi = by_pub["bizagi"]
    check(pub_bizagi.get("found") is True, "bizagi Official page is on file")
    check(
        pub_bizagi.get("trust_url") == "https://www.bizagi.com/en/platform/trust",
        "bizagi Official page is the trust page",
    )
    check(not (pub_bizagi.get("certs") or []), "bizagi marks stay open")
    check((pub_bizagi.get("file") or {}).get("page") == 20, "bizagi Official page prints")
    check((pub_bizagi.get("file") or {}).get("marks") == 10, "bizagi marks stay the looked-none partial")
    check((pub_bizagi.get("file") or {}).get("years") == 20, "bizagi years print")
    check(completeness(pub_bizagi) == 50, f"bizagi Completeness {completeness(pub_bizagi)}")
    check(pub_bizagi.get("founded_year") == 1989, "bizagi year is first-party about")
    check(
        pub_bizagi.get("founded_source") == "https://www.bizagi.com/en/about/the-team",
        "bizagi year source",
    )
    check(not ((pub_bizagi.get("instruments") or {}).get("dpa") or {}).get("url"), "bizagi DPA stays open")
    check(
        ((pub_bizagi.get("instruments") or {}).get("trust") or {}).get("url")
        == "https://www.bizagi.com/en/platform/trust",
        "bizagi trust instrument URL",
    )

    pub_bb = by_pub["black-box-corporation"]
    check(pub_bb.get("found") is True, "black-box Official page is on file")
    check(
        pub_bb.get("trust_url") == "https://www.blackbox.com/discover-bb/trust-center",
        "black-box Official page is the trust center",
    )
    check(
        set(pub_bb.get("certs") or []) == {
            "SOC 2 Type II",
            "ISO 27001",
            "ISO 20000-1",
            "ISO 9001",
            "HIPAA",
            "Cyber Essentials",
            "CMMC L2",
        },
        f"black-box marks {pub_bb.get('certs')}",
    )
    check((pub_bb.get("file") or {}).get("page") == 20, "black-box Official page prints")
    check((pub_bb.get("file") or {}).get("marks") == 20, "black-box marks print")
    check(completeness(pub_bb) == 40, f"black-box Completeness {completeness(pub_bb)}")
    check(not pub_bb.get("founded_year"), "black-box year stays open")
    check(not ((pub_bb.get("instruments") or {}).get("dpa") or {}).get("url"), "black-box DPA stays open")
    check(
        ((pub_bb.get("instruments") or {}).get("trust") or {}).get("url")
        == "https://www.blackbox.com/discover-bb/trust-center",
        "black-box trust instrument URL",
    )

    pub_blend = by_pub["blend"]
    check(pub_blend.get("found") is True, "blend Official page is on file")
    check(
        pub_blend.get("trust_url") == "https://blend.com/security-and-compliance/",
        "blend Official page is the security page",
    )
    check(not (pub_blend.get("certs") or []), "blend marks stay open")
    check((pub_blend.get("file") or {}).get("page") == 20, "blend Official page prints")
    check((pub_blend.get("file") or {}).get("marks") == 10, "blend marks stay the looked-none partial")
    check(completeness(pub_blend) == 30, f"blend Completeness {completeness(pub_blend)}")
    check(not pub_blend.get("founded_year"), "blend year stays open")
    check(not ((pub_blend.get("instruments") or {}).get("dpa") or {}).get("url"), "blend DPA stays open")
    check(
        ((pub_blend.get("instruments") or {}).get("security") or {}).get("url")
        == "https://blend.com/security-and-compliance/",
        "blend security instrument URL",
    )

    for slug in batch_1106_pm:
        if slug in shipped_1106_pm:
            continue
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

    pub_bs = by_pub["blockstream"]
    check(pub_bs.get("found") is False, "blockstream Official page stays open")
    check(not pub_bs.get("trust_url"), "blockstream Official page URL stays open")
    check(pub_bs.get("founded_year") == 2014, "blockstream year is first-party about")
    check(pub_bs.get("founded_source") == "https://blockstream.com/about/us", "blockstream year source")
    check((pub_bs.get("file") or {}).get("years") == 20, "blockstream years print")
    check(completeness(pub_bs) == 20, f"blockstream Completeness {completeness(pub_bs)}")
    check(not (pub_bs.get("certs") or []), "blockstream marks stay open")
    check(not ((pub_bs.get("instruments") or {}).get("dpa") or {}).get("url"), "blockstream DPA stays open")

    pub_blu = by_pub["blu-products"]
    check(pub_blu.get("found") is False, "blu-products homepage is not Official page")
    check(not pub_blu.get("trust_url"), "blu-products Official page stays open")
    check(pub_blu.get("founded_year") == 2009, "blu-products year is first-party home")
    check(pub_blu.get("founded_source") == "https://www.bluproducts.com/home", "blu-products year source")
    check((pub_blu.get("file") or {}).get("years") == 20, "blu-products years print")
    check(completeness(pub_blu) == 20, f"blu-products Completeness {completeness(pub_blu)}")
    check(not (pub_blu.get("certs") or []), "blu-products marks stay open")

    pub_bmg = by_pub["blue-marble-geographics"]
    check(pub_bmg.get("found") is False, "blue-marble Official page stays open")
    check(pub_bmg.get("founded_year") == 1993, "blue-marble year is first-party JSON-LD")
    check(pub_bmg.get("founded_source") == "https://www.bluemarblegeo.com/", "blue-marble year source")
    check((pub_bmg.get("file") or {}).get("years") == 20, "blue-marble years print")
    check(completeness(pub_bmg) == 20, f"blue-marble Completeness {completeness(pub_bmg)}")
    check(not (pub_bmg.get("certs") or []), "blue-marble marks stay open")

    pub_boc = by_pub["blue-ocean-contact-centres"]
    check(pub_boc.get("found") is False, "blue-ocean Official page stays open")
    check(pub_boc.get("founded_year") == 1994, "blue-ocean year is first-party JSON-LD")
    check(pub_boc.get("founded_source") == "https://blueocean.ca/", "blue-ocean year source")
    check((pub_boc.get("file") or {}).get("years") == 20, "blue-ocean years print")
    check(completeness(pub_boc) == 20, f"blue-ocean Completeness {completeness(pub_boc)}")
    check(not (pub_boc.get("certs") or []), "blue-ocean marks stay open")

    pub_bpr = by_pub["blue-prism"]
    check(pub_bpr.get("found") is True, "blue-prism Official page is on file")
    check(
        pub_bpr.get("trust_url") == "https://www.blueprism.com/blue-prism-security/",
        "blue-prism Official page is the security page",
    )
    check(pub_bpr.get("certs") == ["Cyber Essentials"], f"blue-prism marks {pub_bpr.get('certs')}")
    check((pub_bpr.get("file") or {}).get("page") == 20, "blue-prism Official page prints")
    check((pub_bpr.get("file") or {}).get("marks") == 20, "blue-prism marks print")
    check(completeness(pub_bpr) == 40, f"blue-prism Completeness {completeness(pub_bpr)}")
    check(not pub_bpr.get("founded_year"), "blue-prism year stays open")
    check(not ((pub_bpr.get("instruments") or {}).get("dpa") or {}).get("url"), "blue-prism DPA stays open")
    check(
        ((pub_bpr.get("instruments") or {}).get("security") or {}).get("url")
        == "https://www.blueprism.com/blue-prism-security/",
        "blue-prism security instrument URL",
    )

    pub_board = by_pub["board-international"]
    check(pub_board.get("found") is True, "board Official page is on file")
    check(
        pub_board.get("trust_url") == "https://www.board.com/governance-and-compliance",
        "board Official page is the governance page",
    )
    check(not (pub_board.get("certs") or []), "board marks stay open")
    check((pub_board.get("file") or {}).get("page") == 20, "board Official page prints")
    check((pub_board.get("file") or {}).get("marks") == 10, "board marks stay the looked-none partial")
    check(completeness(pub_board) == 30, f"board Completeness {completeness(pub_board)}")
    check(not pub_board.get("founded_year"), "board year stays open")
    check(not ((pub_board.get("instruments") or {}).get("dpa") or {}).get("url"), "board DPA stays open")
    check(
        ((pub_board.get("instruments") or {}).get("trust") or {}).get("url")
        == "https://www.board.com/governance-and-compliance",
        "board trust instrument URL",
    )

    pub_boeing = by_pub["boeing"]
    check(pub_boeing.get("found") is False, "boeing Official page stays open")
    check(not pub_boeing.get("trust_url"), "boeing FAA feature is not Official page")
    check(pub_boeing.get("certs") == ["EU-US DPF"], f"boeing marks {pub_boeing.get('certs')}")
    check((pub_boeing.get("file") or {}).get("marks") == 20, "boeing marks print")
    check((pub_boeing.get("file") or {}).get("page") == 0, "boeing Official page stays the open rule")
    check(completeness(pub_boeing) == 20, f"boeing Completeness {completeness(pub_boeing)}")
    check(not pub_boeing.get("founded_year"), "boeing year stays open")
    check(not ((pub_boeing.get("instruments") or {}).get("dpa") or {}).get("url"), "boeing DPA stays open")
    check(
        ((pub_boeing.get("instruments") or {}).get("bounty") or {}).get("url")
        == "https://www.boeing.com/vulnerabilitydisclosure",
        "boeing bounty stays",
    )

    for slug in batch_1109_am:
        if slug in shipped_1109_am:
            continue
        check(completeness(by_pub[slug]) == 0, f"{slug} Completeness stays 0")
        check(by_pub[slug].get("found") is False, f"{slug} Official page stays open")
        check(not (by_pub[slug].get("certs") or []), f"{slug} marks stay open")
        check(not by_pub[slug].get("founded_year"), f"{slug} year stays open")
        check(not ((by_pub[slug].get("instruments") or {}).get("dpa") or {}).get("url"), f"{slug} DPA stays open")

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
