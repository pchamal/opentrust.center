#!/usr/bin/env python3
"""Found page → enrich attempted. Walled lists stay empty. No invented names."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import expand_batch  # noqa: E402
from enrich import (  # noqa: E402
    cited_list_skip_reason,
    enrich_one,
    has_public_page,
    published_processors_from_cited,
    strip_tags,
    website_matches,
)


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"fail: {msg}")


AIRTABLE_TABLE = """
<html><head><title>Airtable Subprocessors</title></head><body>
<h1>Airtable Subprocessors</h1>
<table>
  <tr><th>Entity</th><th>Description/Purpose</th><th>Countries</th></tr>
  <tr><td>Amazon Web Services, Inc</td><td>Cloud infrastructure</td><td>USA</td></tr>
  <tr><td>Mailgun Technologies, Inc</td><td>Transactional email</td><td>USA</td></tr>
  <tr><td>SafeBase</td><td>Trust portal host</td><td>USA</td></tr>
  <tr><td>Airtable, Inc</td><td>Ourselves</td><td>USA</td></tr>
</table>
</body></html>
"""

VANTA_SHELL = """
<html><head><title>Algolia Trust Center</title></head>
<body>Algolia Trust Center
<script>var manifestPreload = document.createElement('link');</script>
<nav><ul><li>Home</li><li>Overview</li></ul></nav>
</body></html>
"""

LOGIN_HTML = """
<html><head><title>Sign in</title></head>
<body>Please log in to continue.</body></html>
"""


def rec(url: str, html: str, title: str, status: int = 200, ctype: str = "text/html") -> dict:
    return {
        "ok": status == 200,
        "status": status,
        "final_url": url,
        "title": title,
        "text": strip_tags(html)[:80000],
        "html": html,
        "ctype": ctype,
    }


def test_found_page_calls_enrich() -> None:
    calls = []

    def fake_enrich(company, **_kw):
        calls.append(company["slug"])
        out = dict(company)
        out["links"] = dict(company.get("links") or {})
        out["links"]["dpa"] = "https://example.com/legal/dpa"
        return out

    def fake_fetch(_url, **_kw):
        return {"ok": True, "body": "<html>SOC 2 Type II</html>", "text": "SOC 2 Type II"}

    saved_enrich = expand_batch.enrich.enrich_one
    saved_fetch = expand_batch.crawl.fetch
    expand_batch.enrich.enrich_one = fake_enrich
    expand_batch.crawl.fetch = fake_fetch
    try:
        hit = {
            "name": "Example",
            "slug": "example",
            "domain": "example.com",
            "found": True,
            "trust_url": "https://trust.example.com",
            "final_url": "https://trust.example.com",
            "probed": 1,
            "source": "expand",
        }
        miss = {
            "name": "Silent Co",
            "slug": "silent-co",
            "domain": "silent.example",
            "found": False,
            "trust_url": None,
            "final_url": None,
            "probed": 3,
            "source": "expand",
        }
        src = {"source": "expand", "source_url": "https://example.net/list"}
        filed = expand_batch.file_row(hit, src)
        silent = expand_batch.file_row(miss, src)
        check(calls == ["example"], f"enrich attempted only for the found page: {calls}")
        check(filed.get("links", {}).get("dpa") == "https://example.com/legal/dpa", "enrich result landed")
        check(silent.get("found") is False, "miss stays not-found")
        check(not silent.get("links"), f"miss has no invented instruments: {silent.get('links')}")
        check((silent.get("certs") or []) == [], "miss has no invented marks")
        check("No public trust center" in (silent.get("summary") or ""), "miss keeps silent clerk line")
        check(expand_batch.has_public_page(hit), "found + URL is a public page")
        check(not expand_batch.has_public_page(miss), "not-found is not a public page")
        no_url = dict(hit, trust_url=None, final_url=None)
        check(not expand_batch.has_public_page(no_url), "found without a URL is not a page")
        skipped = expand_batch.file_row(no_url, src)
        check(calls == ["example"], f"no-page found does not call enrich: {calls}")
        check(not (skipped.get("links") or {}).get("dpa"), "no-page found stays unenriched")
    finally:
        expand_batch.enrich.enrich_one = saved_enrich
        expand_batch.crawl.fetch = saved_fetch


def test_walled_list_no_invented_names() -> None:
    airtable = {"slug": "airtable", "name": "Airtable", "domain": "airtable.com"}
    algolia = {"slug": "algolia", "name": "Algolia", "domain": "algolia.com"}
    url = "https://www.airtable.com/company/subprocessors"
    filed = published_processors_from_cited(
        airtable,
        rec(url, AIRTABLE_TABLE, "Airtable Subprocessors"),
        url,
        {"airtable": airtable},
    )
    names = [n for _i, n, _e in filed]
    ids = [i for i, _n, _e in filed]
    check(any(i == "aws" for i in ids), f"aws id from table: {filed}")
    check(any("Amazon Web Services" in n for n in names), f"verbatim AWS: {names}")
    check(any("Mailgun" in n for n in names), f"verbatim Mailgun: {names}")
    check(not any("SafeBase" in n or i == "safebase" for i, n, _e in filed), f"no portal vendor: {filed}")
    check(not any("Airtable" in n for n in names), f"no self: {names}")

    wall = "https://security.attentive.com/?itemUid=e3fae2ca-94a9-416b-b577-5c90e382df57"
    check(
        cited_list_skip_reason(wall, rec(wall, "<html></html>", "Attentive"), airtable) == "safebase-itemuid",
        "itemUid stays empty",
    )
    vanta_url = "https://trust.algolia.com/subprocessors"
    vanta_rec = rec(vanta_url, VANTA_SHELL, "Algolia Trust Center")
    check(
        cited_list_skip_reason(vanta_url, vanta_rec, algolia) == "js-portal",
        f"vanta shell stays empty: {cited_list_skip_reason(vanta_url, vanta_rec, algolia)}",
    )
    check(
        published_processors_from_cited(algolia, vanta_rec, vanta_url) == [],
        "js-only listed names stay empty",
    )
    pdf = "https://assets.confluent.io/m/227f69dc22168130/original/list.pdf"
    check(
        cited_list_skip_reason(
            pdf,
            rec(pdf, "", "PDF", ctype="application/pdf"),
            {"slug": "confluent", "name": "Confluent", "domain": "confluent.io"},
        ) == "pdf",
        "pdf stays empty",
    )
    login_url = "https://example.com/legal/subprocessors"
    login_rec = rec(login_url, LOGIN_HTML, "Sign in")
    check(
        cited_list_skip_reason(
            login_url,
            login_rec,
            {"slug": "example", "name": "Example", "domain": "example.com"},
        ) == "login-wall",
        "login wall stays empty",
    )
    check(
        published_processors_from_cited(
            {"slug": "example", "name": "Example", "domain": "example.com"},
            login_rec,
            login_url,
        ) == [],
        "login wall does not invent names",
    )
    other = "https://www.paloaltonetworks.com/resources/datasheets/palo-alto-networks-sub-processor-list"
    check(
        cited_list_skip_reason(
            other,
            rec(other, AIRTABLE_TABLE, "Sub-processor list"),
            {"slug": "cyberark", "name": "CyberArk", "domain": "cyberark.com"},
        ) == "not-first-party",
        "do not file another company's list",
    )


def test_enrich_one_lands_published_facts_only() -> None:
    company = {
        "rank": None,
        "name": "Example",
        "slug": "example",
        "domain": "example.com",
        "found": True,
        "trust_url": "https://trust.example.com",
        "final_url": "https://trust.example.com",
        "vendor": "unknown",
        "title": "",
        "probed": 1,
        "source": "expand",
        "summary": "Trust portal found; marks not yet read from the public page.",
        "list": "expand",
        "certs": [],
        "links": {"trust": "https://trust.example.com"},
        "subprocessors": [],
    }
    list_url = "https://example.com/legal/subprocessors"
    probed = {
        "links": {
            "trust": "https://trust.example.com",
            "dpa": "https://example.com/legal/dpa",
            "subprocessors": list_url,
        },
        "pages": {
            "trust": {
                "title": "Example Trust",
                "meta": "Example publishes SOC 2 Type II and ISO 27001.",
                "text": "SOC 2 Type II ISO 27001 public trust center.",
            },
            "subprocessors": rec(list_url, AIRTABLE_TABLE, "Example Subprocessors"),
        },
        "probed": 4,
    }
    out = enrich_one(
        company,
        resolve_year=True,
        probed=probed,
        year=(2014, "https://en.wikipedia.org/wiki/Example"),
    )
    check(out["links"].get("dpa") == "https://example.com/legal/dpa", "DPA landed")
    check("SOC 2 Type II" in (out.get("certs") or []), f"marks from the page: {out.get('certs')}")
    check(out.get("founded_year") == 2014, "year landed")
    check("aws" in (out.get("subprocessors") or []), f"named processor from HTML: {out.get('subprocessors')}")
    check("safebase" not in (out.get("subprocessors") or []), "no portal vendor")
    edges = out.get("_edges") or []
    check(edges and all(e.get("source_url") == list_url for e in edges), f"source_url on filed names: {edges}")
    check(has_public_page(company), "seed is a public page")

    silent = dict(company, found=False, trust_url=None, final_url=None, links={})
    unchanged = enrich_one(silent, probed=probed, year=(2014, "https://example"))
    check(unchanged is silent or not unchanged.get("links"), "silent row is not enriched")
    check(not (unchanged.get("certs") or []), "silent row keeps empty marks")

    walled = dict(company)
    wall_url = "https://security.example.com/?itemUid=e3fae2ca-94a9-416b-b577-5c90e382df57"
    walled_probe = {
        "links": {"trust": "https://trust.example.com", "subprocessors": wall_url},
        "pages": {"subprocessors": rec(wall_url, AIRTABLE_TABLE, "Example Subprocessors")},
        "probed": 2,
    }
    empty = enrich_one(walled, resolve_year=False, probed=walled_probe)
    check((empty.get("subprocessors") or []) == [], f"itemUid does not invent names: {empty.get('subprocessors')}")
    check(not empty.get("_edges"), "itemUid has no edges")


def test_wrong_company_pairs_stay_rejected() -> None:
    """Expand / gap-resolve must not refile the four 190b4c2 collisions."""
    from resolve_queue_domains import verify_domain

    pairs = (
        ("maxio", "Maxio", "maxionwheels.com"),
        ("fathom-analytics", "Fathom Analytics, Inc", "fathom.video"),
        ("aircall", "Aircall", "aircall.se"),
        ("voyager", "Voyager", "voyager.nz"),
    )
    for slug, name, domain in pairs:
        check(
            expand_batch.rejected_mapping(slug, domain),
            f"{slug}→{domain} is on the expand reject list",
        )
        check(
            not expand_batch.rejected_mapping(slug, "example.com"),
            f"{slug} does not reject an unrelated domain",
        )
        ok, why, home = verify_domain(name, domain, slug, require_page=False)
        check(not ok, f"{slug}→{domain} verify stays rejected")
        check(why == "rejected-collision", f"{slug} reason is rejected-collision, got {why}")
        check(home == {}, f"{slug} reject does not fetch a homepage")

    check(
        not expand_batch.rejected_mapping("other", "fathom.video"),
        "fathom.video is not a global domain ban",
    )

    queue = {
        "companies": [
            {"slug": "maxio", "domain": "maxionwheels.com", "source": expand_batch.GAP_SOURCE},
            {"slug": "fathom-analytics", "domain": "fathom.video", "source": expand_batch.GAP_SOURCE},
            {"slug": "aircall", "domain": "aircall.se", "source": expand_batch.GAP_SOURCE},
            {"slug": "voyager", "domain": "voyager.nz", "source": expand_batch.GAP_SOURCE},
            {"slug": "sentry", "domain": "sentry.io", "source": expand_batch.GAP_SOURCE},
        ]
    }
    state = {"cursor": 0}
    saved = expand_batch.load_json
    expand_batch.load_json = lambda path, default=None: {"companies": []}
    try:
        picked = expand_batch.next_batch(queue, state, 4)
    finally:
        expand_batch.load_json = saved
    check(picked and [r["slug"] for r in picked] == ["sentry"], f"rejected pairs stay off the batch: {picked}")
    check(state["cursor"] == 0, "rejected gap pairs do not burn the leftover cursor")


def test_year_needs_website_match() -> None:
    """One-shot years cannot ride a loose title prefix (Manhattan / Sage Publishing)."""
    check(
        not website_matches(["https://en.wikipedia.org/wiki/Manhattan"], ["manh.com"]),
        "borough page is not Manhattan Associates",
    )
    check(
        not website_matches(["https://sagepub.com"], ["sage.com"]),
        "Sage Publishing is not Sage Group",
    )
    check(
        website_matches(["https://www.fico.com"], ["fico.com"]),
        "FICO official site matches",
    )


def main() -> int:
    test_found_page_calls_enrich()
    test_walled_list_no_invented_names()
    test_enrich_one_lands_published_facts_only()
    test_wrong_company_pairs_stay_rejected()
    test_year_needs_website_match()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
