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

    check(len(batch) == 30, f"2026-10-30 afternoon batch is 30, got {len(batch)}")
    check(
        batch[0] == "apigee" and batch[-1] == "aptilo-networks",
        "2026-10-30 afternoon batch is the apigee–aptilo-networks cut",
    )
    check("apollo-global-management" in batch and "aptilo-networks" in batch, "afternoon cut covers apollo-global-management..aptilo-networks")
    check(all(slug in entries for slug in batch), "2026-10-30 afternoon rows stay in the ledger")
    check(summary.get("batch") == 30, "2026-10-30 afternoon summary.batch is 30")
    check(summary.get("fileable") == 4, f"2026-10-30 afternoon clerk fileable, got {summary.get('fileable')}")
    check(summary.get("soft_retry") == 9, f"2026-10-30 afternoon soft-retry, got {summary.get('soft_retry')}")
    check(summary.get("still_0") == 26, f"2026-10-30 afternoon still-0, got {summary.get('still_0')}")
    check(summary.get("filled") == 4, f"2026-10-30 afternoon clerk fills, got {summary.get('filled')}")
    check(
        all((entries.get(slug) or {}).get("date") == "2026-10-30" for slug in batch),
        "2026-10-30 afternoon cut is dated 2026-10-30",
    )
    check(not set(batch) & set(batch_1026), "2026-10-30 afternoon cut must be never-reaudited vs 24slides–airpair")
    check(not set(batch) & set(batch_1027_am), "2026-10-30 afternoon cut must be never-reaudited vs advacam–alchemy-cms")
    check(not set(batch) & set(batch_1027_pm), "2026-10-30 afternoon cut must be never-reaudited vs 21vianet–aligned-assets")
    check(not set(batch) & set(batch_1028), "2026-10-30 afternoon cut must be never-reaudited vs a1-hrvatska–altacast")
    check(not set(batch) & set(batch_1029_am), "2026-10-30 afternoon cut must be never-reaudited vs altair-engineering–american-sammy")
    check(not set(batch) & set(batch_1029_pm), "2026-10-30 afternoon cut must be never-reaudited vs american-tower–andor-technology")
    check(not set(batch) & set(batch_1030_am), "2026-10-30 afternoon cut must be never-reaudited vs anduril-industries–apex-learning")
    for slug in batch:
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

    for slug in batch:
        if slug in shipped_1030_pm:
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
