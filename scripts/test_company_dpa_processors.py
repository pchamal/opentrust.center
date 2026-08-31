#!/usr/bin/env python3
"""DPA and named subprocessors follow stored first-party URLs. Dates are not processors."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from enrich import looks_like_date_name  # noqa: E402

PUBLIC = ROOT / "site" / "data.json"
ENRICHED = ROOT / "site" / "data" / "enriched.json"
WIRES = ROOT / "site" / "data" / "subprocessors.json"
REPORT = ROOT / "data" / "render" / "company-dpa-processors.json"


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"fail: {msg}")


def instrument_url(row: dict, key: str) -> str:
    rec = (row.get("instruments") or {}).get(key) or {}
    if isinstance(rec, dict):
        return (rec.get("url") or "").strip()
    return str(rec or "").strip()


def main() -> int:
    public = json.loads(PUBLIC.read_text())
    enr = json.loads(ENRICHED.read_text())
    wires = json.loads(WIRES.read_text())
    report = json.loads(REPORT.read_text())
    by_pub = {c["slug"]: c for c in public["companies"]}
    by_enr = {c["slug"]: c for c in enr["companies"]}

    check(looks_like_date_name("01 April 2025"), "01 April 2025 is a date")
    check(looks_like_date_name("29 April 2026"), "29 April 2026 is a date")
    check(looks_like_date_name("Date of change"), "Date of change is a date")
    check(looks_like_date_name("Date"), "Date header is a date")
    check(not looks_like_date_name("Amazon Web Services"), "AWS is not a date")

    for row in public["companies"]:
        for proc in row.get("processors") or []:
            name = proc.get("name") if isinstance(proc, dict) else proc
            check(not looks_like_date_name(name), f"public processor date {row['slug']} {name}")
            pid = (proc.get("id") if isinstance(proc, dict) else "") or ""
            check(not looks_like_date_name(pid), f"public processor id date {row['slug']} {pid}")

    for edge in wires.get("edges") or []:
        check(not looks_like_date_name(edge.get("to") or ""), f"edge to date {edge}")
        check(not looks_like_date_name(edge.get("evidence") or ""), f"edge evidence date {edge}")

    for rec in report.get("dpa_filed") or []:
        slug, url = rec["slug"], rec["url"]
        pub = by_pub[slug]
        stored = (by_enr[slug].get("links") or {}).get("dpa")
        check(stored == url, f"{slug} stored DPA {stored} != {url}")
        check(instrument_url(pub, "dpa") == url, f"{slug} dossier DPA {instrument_url(pub, 'dpa')} != {url}")
        check((pub.get("file") or {}).get("dpa") in (True, 20), f"{slug} file.dpa not filled")
        html = (ROOT / "site" / "c" / f"{slug}.html").read_text(encoding="utf-8")
        check(url in html, f"{slug} dossier missing DPA URL")

    for rec in report.get("subprocessors_filed") or []:
        slug, url = rec["slug"], rec["url"]
        pub = by_pub[slug]
        stored = (by_enr[slug].get("links") or {}).get("subprocessors")
        check(stored == url, f"{slug} stored list {stored} != {url}")
        check(instrument_url(pub, "subprocessors") == url, f"{slug} instrument list != stored")
        names = [p.get("name") for p in (pub.get("processors") or [])]
        check(names, f"{slug} named processors empty")
        check(all(not looks_like_date_name(n) for n in names), f"{slug} dated processor {names}")
        check(all(n in names for n in rec["names"] if not looks_like_date_name(n)), f"{slug} missing published name {names}")
        check((pub.get("file") or {}).get("subprocessors") in (True, 20), f"{slug} file.subprocessors not filled")
        html = (ROOT / "site" / "c" / f"{slug}.html").read_text(encoding="utf-8")
        check(url in html, f"{slug} dossier missing list URL")

    for rec in report.get("stayed_open") or []:
        pub = by_pub[rec["slug"]]
        if rec["rule"] == "dpa":
            check(not instrument_url(pub, "dpa"), f"{rec['slug']} DPA should stay open")
            check(not (pub.get("file") or {}).get("dpa"), f"{rec['slug']} file.dpa filled without a URL")
        if rec["rule"] == "subprocessors":
            check(not (pub.get("processors") or []), f"{rec['slug']} invented processors")
            # A stored list URL with no printed names is dotted 10, not invented names.

    # Bind: a stored DPA or list URL fills the glyph. Display host may drop :443.
    for row in public["companies"]:
        slug = row["slug"]
        enr_row = by_enr.get(slug) or {}
        links = enr_row.get("links") or {}
        if links.get("dpa"):
            check((row.get("file") or {}).get("dpa") in (True, 20), f"{slug} stored DPA did not fill glyph")
            check(bool(instrument_url(row, "dpa")), f"{slug} stored DPA has no instrument URL")
        if links.get("subprocessors"):
            check(
                (row.get("file") or {}).get("subprocessors") in (True, 10, 20),
                f"{slug} stored subprocessors URL did not fill glyph",
            )

    zoom = (ROOT / "site" / "c" / "zoom.html").read_text(encoding="utf-8")
    check("01 April 2025" not in zoom, "zoom still has no date processors")
    check("Amazon Web Services" in zoom, "zoom still names AWS")
    check("Concentration" not in (ROOT / "site" / "graph.html").read_text(encoding="utf-8"), "list dropped Concentration")

    # Prior fill stays: Photoroom printed appendix (PR 132).
    check(
        instrument_url(by_pub["photoroom"], "dpa")
        == "https://www.photoroom.com/legal/data-processing-agreement",
        "photoroom DPA stays the stored first-party agreement",
    )
    pr_names = [p.get("name") for p in (by_pub["photoroom"].get("processors") or [])]
    check("Amazon Web Services (AWS)" in pr_names, "photoroom names Amazon Web Services (AWS)")
    check("Cloudflare Inc" in pr_names, "photoroom names Cloudflare Inc")
    check(
        "Google LLC (Google Cloud, Firebase, Workspace)" in pr_names,
        "photoroom names Google LLC",
    )
    check("Intercom" in pr_names, "photoroom names Intercom")
    check(len(pr_names) == 4, f"photoroom printed appendix has 4 names, got {len(pr_names)}")
    check(
        instrument_url(by_pub["photoroom"], "subprocessors")
        == "https://www.photoroom.com/legal/data-processing-agreement",
        "photoroom list URL stays the printed appendix",
    )
    check((by_pub["photoroom"].get("file") or {}).get("subprocessors") == 20, "photoroom list printed")

    any_names = [p.get("name") for p in (by_pub["anysphere"].get("processors") or [])]
    check(len(any_names) == 17, f"anysphere existing 17 names stay, got {len(any_names)}")
    check(instrument_url(by_pub["anysphere"], "dpa") == "https://cursor.com/terms/dpa", "anysphere DPA stays")

    # Protected prior fills stay.
    check(
        instrument_url(by_pub["ex-libris-group"], "dpa")
        == "https://knowledge.exlibrisgroup.com/Cross-Product/Security/GDPR/03GDPR_Data_Processing_Addendum",
        "ex-libris-group DPA stays",
    )
    check(
        instrument_url(by_pub["altus-group"], "dpa")
        == "https://www.altusgroup.com/downloads/legal/gdpr/data-processing-addendum.pdf",
        "altus-group DPA stays",
    )
    check(len(by_pub["altus-group"].get("processors") or []) == 17, "altus-group 17 names stay")
    check(not instrument_url(by_pub["faculty"], "dpa"), "faculty DPA stays open")

    # PR 149 fills stay.
    check(instrument_url(by_pub["navan"], "dpa") == "https://navan.com/dpa", "navan dossier DPA stays")
    check(len(by_pub["navan"].get("processors") or []) == 4, "navan existing 4 names stay")
    check(instrument_url(by_pub["vercel"], "dpa") == "https://vercel.com/legal/dpa", "vercel dossier DPA stays")
    check(len(by_pub["vercel"].get("processors") or []) == 14, "vercel existing 14 names stay")
    check(
        instrument_url(by_pub["backblaze"], "dpa")
        == "https://www.backblaze.com/company/policy/dpa-for-uk-residents",
        "backblaze dossier DPA stays",
    )
    check(not (by_pub["backblaze"].get("processors") or []), "backblaze named processors stay open")
    check(
        "itemUid=c4223a81-5840-4e11-ac9f-2b812794a67e"
        in (instrument_url(by_pub["1password"], "dpa") or ""),
        "1password portal-catalog DPA stays",
    )
    check(len(by_pub["1password"].get("processors") or []) == 1, "1password existing name stays")
    check(
        "itemUid=" in (instrument_url(by_pub["twilio"], "dpa") or ""),
        "twilio portal-catalog DPA stays",
    )
    check(len(by_pub["twilio"].get("processors") or []) == 19, "twilio existing 19 names stay")
    check(
        "itemUid=" in (instrument_url(by_pub["dialpad"], "dpa") or ""),
        "dialpad portal-catalog DPA stays",
    )
    check(len(by_pub["dialpad"].get("processors") or []) == 1, "dialpad existing name stays")

    # This increment: unread first-party privacy-page queue after PR 149.
    expected_batch = [
        "phreesia",
        "corpay",
        "huawei",
        "materialise-nv",
        "schr-dinger",
        "zensar-technologies",
        "planisware",
        "align-technology",
        "paycom",
        "on-semiconductor",
        "globant",
        "4dmedical-limited",
        "bytedance",
        "cyngn",
        "system1",
        "cellebrite",
        "applied-digital",
        "3d-systems",
        "3i-infotech",
        "a-o-smith",
        "accenture",
        "agilysys",
        "aiforia-technologies-oyj",
        "albemarle-corporation",
        "alexandria-real-estate-equities",
        "alibaba",
        "alkami",
        "alliant-energy",
        "amadeus",
        "amdocs",
        "ameren",
        "american-electric-power",
        "american-express",
        "ametek",
        "amgen",
        "aptiv",
        "arthur-j-gallagher-and-co",
        "assurant",
        "at-and-t",
        "atmos-energy",
    ]
    check(report.get("batch") == expected_batch, "batch is the unread first-party privacy-page queue")
    check(not (report.get("dpa_filed") or []), "no DPA was invented")
    check(not (report.get("subprocessors_filed") or []), "no named processors were invented")
    withdrawn = {r["slug"] for r in (report.get("withdrawn") or [])}
    check(withdrawn == {"at-and-t"}, f"AT&T CMS-shell DPA withdrawn, got {sorted(withdrawn)}")
    check(not instrument_url(by_pub["at-and-t"], "dpa"), "at-and-t withdrawn DPA stays off file")

    for slug in expected_batch:
        pub = by_pub[slug]
        check(not instrument_url(pub, "dpa"), f"{slug} DPA stays open")
        check(not (pub.get("file") or {}).get("dpa"), f"{slug} file.dpa stays open")
        check(not (pub.get("processors") or []), f"{slug} named processors stay open")

    from file_company_dpa_processors import PRIOR_ATTEMPTED, select_batch
    for slug in expected_batch:
        check(slug in PRIOR_ATTEMPTED, f"{slug} is on the next-increment skip list")
    leftover = select_batch(list(public["companies"]), by_enr)
    leftover_slugs = {r["slug"] for r in leftover}
    check(not leftover_slugs & set(expected_batch), f"this batch is not retried, got {leftover_slugs & set(expected_batch)}")
    for slug in (
        "navan", "vercel", "backblaze", "1password", "peak", "translated",
        "anaplan", "sarvam-ai", "salesloft", "verint-systems", "thoughtspot",
    ):
        check(slug in PRIOR_ATTEMPTED, f"{slug} leftover walk stays on the skip list")
        check(slug not in leftover_slugs, f"{slug} leftover is not retried")

    for slug in expected_batch:
        html = (ROOT / "site" / "c" / f"{slug}.html").read_text(encoding="utf-8")
        check('target="_blank"' in html and 'rel="noopener noreferrer"' in html, f"{slug} outbound opens a new tab")
        check("wires-scroll" in html, f"{slug} dossier keeps the swipe wrapper")
        visible = html.lower()
        check(
            "safebase" not in visible and "conveyor" not in visible and "drata" not in visible,
            f"{slug} named a portal vendor",
        )
        check("vanta" not in visible, f"{slug} dossier names no portal vendor")
    pronto_html = (ROOT / "site" / "c" / "pronto-software.html").read_text(encoding="utf-8")
    check("Official page" in pronto_html, "Pronto Software still prints Official page")
    cognition = (ROOT / "site" / "c" / "cognition.html").read_text(encoding="utf-8")
    check(
        "cognition.com/legal/data-processing-statement" in cognition,
        "AITI cognition named-processor source-line stays",
    )

    # This cut: Plume first-party subcontractor table at /legal/subprocessors/.
    plume_names = [p.get("name") for p in (by_pub["plume"].get("processors") or [])]
    check(
        instrument_url(by_pub["plume"], "subprocessors")
        == "https://www.plume.com/legal/subprocessors/",
        "plume list URL stays the first-party subcontractor table",
    )
    check((by_pub["plume"].get("file") or {}).get("subprocessors") == 20, "plume list printed")
    check("AWS, Amazon.com, Inc" in plume_names, "plume names AWS, Amazon.com, Inc")
    check("Okta Inc" in plume_names, "plume names Okta Inc")
    check("Databricks Inc" in plume_names, "plume names Databricks Inc")
    check("Mobile Apps" not in plume_names, "plume section header Mobile Apps stays off file")
    check(len(plume_names) == 19, f"plume printed 19 named processors, got {len(plume_names)}")
    plume_html = (ROOT / "site" / "c" / "plume.html").read_text(encoding="utf-8")
    check("https://www.plume.com/legal/subprocessors/" in plume_html, "plume dossier keeps the list URL")

    # This cut: Responsive first-party DPA + subprocessor table; RFPIO aliases here.
    check(
        instrument_url(by_pub["responsive"], "dpa") == "https://www.responsive.io/legal/dpa",
        "responsive DPA stays the first-party addendum",
    )
    check((by_pub["responsive"].get("file") or {}).get("dpa") == 20, "responsive DPA prints")
    check(
        instrument_url(by_pub["responsive"], "subprocessors")
        == "https://www.responsive.io/legal/dpa-sub-processor-list",
        "responsive list URL stays the first-party table",
    )
    check((by_pub["responsive"].get("file") or {}).get("subprocessors") == 20, "responsive list printed")
    responsive_names = [p.get("name") for p in (by_pub["responsive"].get("processors") or [])]
    check("Amazon Web Services (“AWS”) aws.amazon.com" in responsive_names, "responsive names AWS")
    check("MongoDB mongodb.com" in responsive_names, "responsive names MongoDB")
    check("OpenAI openai.com" in responsive_names, "responsive names OpenAI")
    check(
        "RFPIO India Private Limited Responsive.io" not in responsive_names,
        "responsive self-affiliate RFPIO India stays off file",
    )
    check(len(responsive_names) == 9, f"responsive printed 9 named processors, got {len(responsive_names)}")
    responsive_html = (ROOT / "site" / "c" / "responsive.html").read_text(encoding="utf-8")
    check("https://www.responsive.io/legal/dpa" in responsive_html, "responsive dossier keeps the DPA URL")
    check(
        "https://www.responsive.io/legal/dpa-sub-processor-list" in responsive_html,
        "responsive dossier keeps the list URL",
    )
    meltwater_html = (ROOT / "site" / "c" / "meltwater.html").read_text(encoding="utf-8")
    check("./responsive.html\">RFPIO</a>" in meltwater_html, "Meltwater RFPIO wire lands on Responsive")
    check((by_pub["rfpio"].get("file") or {}).get("dpa") in (0, False, None), "empty rfpio shell does not copy Responsive DPA")

    # This cut: Constella first-party Data Processing Amendment at /policies/dpa/.
    check(
        instrument_url(by_pub["constella-intelligence"], "dpa")
        == "https://constella.ai/policies/dpa/",
        "constella DPA stays the first-party Data Processing Amendment",
    )
    check((by_pub["constella-intelligence"].get("file") or {}).get("dpa") == 20, "constella DPA prints")
    check((by_pub["constella-intelligence"].get("file") or {}).get("page") in (0, False, None), "constella Official page stays open")
    check((by_pub["constella-intelligence"].get("file") or {}).get("marks") in (0, False, None), "constella homepage SOC 2 pitch stays open")
    check(not (by_pub["constella-intelligence"].get("processors") or []), "constella Exhibit B list stays unpublished")
    constella_html = (ROOT / "site" / "c" / "constella-intelligence.html").read_text(encoding="utf-8")
    check("https://constella.ai/policies/dpa/" in constella_html, "constella dossier keeps the DPA URL")
    check('aria-label="DPA"' in constella_html, "constella identity spoken is DPA")
    check(
        (by_enr["constella-intelligence"].get("links") or {}).get("dpa")
        == "https://constella.ai/policies/dpa/",
        "constella enriched DPA URL stays",
    )

    print(
        f"ok increment-dpa privacy-page-queue {len(expected_batch)} walked; "
        f"{len(report.get('dpa_filed') or [])} dpa {len(report.get('subprocessors_filed') or [])} lists"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
