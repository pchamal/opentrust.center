#!/usr/bin/env python3
"""DPA and named subprocessors follow stored first-party URLs. Dates are not processors."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from enrich import cell_text, looks_like_date_name, match_processor  # noqa: E402

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
    check(cell_text("Google Inc. UPDATED") == "Google Inc", "CMS UPDATED badge is not the published name")
    check(match_processor("Twilio Segment")[0] == "segment", "Twilio Segment is Segment, not Twilio")
    check(match_processor("Twilio")[0] == "twilio", "Twilio alone stays Twilio")

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
    check("SamKnows LTD" in plume_names, "plume names SamKnows LTD")
    plume_slugs = [p.get("slug") for p in (by_pub["plume"].get("processors") or [])]
    check("cisco" in plume_slugs, "plume SamKnows uses the Cisco file")
    check("samknows" not in plume_slugs, "plume does not invent a second SamKnows dossier")
    plume_html = (ROOT / "site" / "c" / "plume.html").read_text(encoding="utf-8")
    check("https://www.plume.com/legal/subprocessors/" in plume_html, "plume dossier keeps the list URL")
    check("./cisco.html" in plume_html, "plume SamKnows cross-links to Cisco")

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
    # Exhibit B on that same page names two Authorized Sub-Processors.
    check(
        instrument_url(by_pub["constella-intelligence"], "dpa")
        == "https://constella.ai/policies/dpa/",
        "constella DPA stays the first-party Data Processing Amendment",
    )
    check((by_pub["constella-intelligence"].get("file") or {}).get("dpa") == 20, "constella DPA prints")
    check((by_pub["constella-intelligence"].get("file") or {}).get("subprocessors") == 20, "constella Exhibit B processors print")
    check((by_pub["constella-intelligence"].get("file") or {}).get("page") in (0, False, None), "constella Official page stays open")
    check((by_pub["constella-intelligence"].get("file") or {}).get("marks") in (0, False, None), "constella homepage SOC 2 pitch stays open")
    check((by_pub["constella-intelligence"].get("file") or {}).get("years") in (0, False, None), "constella years stay open")
    constella_names = [p.get("name") for p in (by_pub["constella-intelligence"].get("processors") or [])]
    constella_slugs = [p.get("slug") for p in (by_pub["constella-intelligence"].get("processors") or [])]
    check(
        "Amazon Web Services (Web/Hosting services)" in constella_names,
        "constella names Amazon Web Services from Exhibit B",
    )
    check("Arsys (Web/Hosting services)" in constella_names, "constella names Arsys from Exhibit B")
    check(constella_slugs == ["amazon-web-services", "arsys"], f"constella processor slugs {constella_slugs}")
    check(len(constella_names) == 2, f"constella printed 2 Exhibit B processors, got {len(constella_names)}")
    constella_html = (ROOT / "site" / "c" / "constella-intelligence.html").read_text(encoding="utf-8")
    check("https://constella.ai/policies/dpa/" in constella_html, "constella dossier keeps the DPA URL")
    check("./amazon-web-services.html\">Amazon Web Services" in constella_html, "constella AWS cross-links to the existing file")
    check("./arsys.html\">Arsys" in constella_html, "constella Arsys cross-links to its own file")
    check("ionos" not in constella_html.lower(), "constella does not send Arsys to IONOS")
    check(
        (by_enr["constella-intelligence"].get("links") or {}).get("dpa")
        == "https://constella.ai/policies/dpa/",
        "constella enriched DPA URL stays",
    )
    check(by_pub["arsys"]["domain"] == "arsys.es", "arsys official domain is arsys.es")
    check((by_pub["arsys"].get("file") or {}).get("page") in (0, False, None), "arsys Official page stays open")
    check(sum(int((by_pub["arsys"].get("file") or {}).get(k) or 0) for k in ("page", "marks", "dpa", "subprocessors", "years")) == 0, "arsys Completeness is 0")
    check(by_pub["arsys"].get("found") is False, "arsys usual paths did not invent Official page")
    check((by_pub["ionos"].get("domain") or "") == "ionos.com", "ionos row stays ionos.com")
    arsys_html = (ROOT / "site" / "c" / "arsys.html").read_text(encoding="utf-8")
    check("<h1>Arsys</h1>" in arsys_html, "arsys dossier is its own file")
    check("ionos" not in arsys_html.lower(), "arsys dossier does not copy IONOS")
    check("https://www.arsys.es/" in arsys_html, "arsys dossier keeps arsys.es")

    # This cut: Namely first-party Data Processing Addendum. Annex III names four
    # EU/UK sub-processors. Official page stays open. Conversocial is not Verint.
    check(
        instrument_url(by_pub["namely"], "dpa")
        == "https://namely.com/legal/data-processing-addendum/",
        "namely DPA stays the first-party Data Processing Addendum",
    )
    check((by_pub["namely"].get("file") or {}).get("dpa") == 20, "namely DPA prints")
    check((by_pub["namely"].get("file") or {}).get("subprocessors") == 20, "namely Annex III processors print")
    check((by_pub["namely"].get("file") or {}).get("page") in (0, False, None), "namely Official page stays open")
    check((by_pub["namely"].get("file") or {}).get("marks") in (0, False, None), "namely marks stay open")
    check((by_pub["namely"].get("file") or {}).get("years") in (0, False, None), "namely years stay open")
    namely_names = [p.get("name") for p in (by_pub["namely"].get("processors") or [])]
    namely_slugs = [p.get("slug") for p in (by_pub["namely"].get("processors") or [])]
    check("Amazon Web Services, Inc." in namely_names, "namely names Amazon Web Services, Inc.")
    check("HubSpot, Inc." in namely_names, "namely names HubSpot, Inc.")
    check("Google (Alphabet, Inc.)" in namely_names, "namely names Google (Alphabet, Inc.)")
    check("Salesforce, Inc." in namely_names, "namely names Salesforce, Inc.")
    check(
        namely_slugs == ["amazon-web-services", "hubspot", "google", "salesforce"],
        f"namely processor slugs {namely_slugs}",
    )
    check(len(namely_names) == 4, f"namely printed 4 Annex III processors, got {len(namely_names)}")
    namely_html = (ROOT / "site" / "c" / "namely.html").read_text(encoding="utf-8")
    check(
        "https://namely.com/legal/data-processing-addendum/" in namely_html,
        "namely dossier keeps the DPA URL",
    )
    check("./amazon-web-services.html\">Amazon Web Services" in namely_html, "namely AWS cross-links to the existing file")
    check("./hubspot.html\">HubSpot" in namely_html, "namely HubSpot cross-links to the existing file")
    check("./google.html\">Google" in namely_html, "namely Google cross-links to the existing file")
    check("./salesforce.html\">Salesforce" in namely_html, "namely Salesforce cross-links to the existing file")
    check(
        (by_enr["namely"].get("links") or {}).get("dpa")
        == "https://namely.com/legal/data-processing-addendum/",
        "namely enriched DPA URL stays",
    )
    check(by_pub["conversocial"]["domain"] == "conversocial.com", "conversocial official domain stays conversocial.com")
    check(by_pub["conversocial"].get("found") is False, "conversocial Verint product page is not Official page")
    check(
        sum(int((by_pub["conversocial"].get("file") or {}).get(k) or 0) for k in ("page", "marks", "dpa", "subprocessors", "years")) == 0,
        "conversocial Completeness is 0",
    )
    conversocial_html = (ROOT / "site" / "c" / "conversocial.html").read_text(encoding="utf-8")
    check("<h1>Conversocial</h1>" in conversocial_html, "conversocial dossier is its own file")
    check("verint" not in conversocial_html.lower(), "conversocial dossier does not copy Verint")
    check((by_pub["verint-systems"].get("found") is True), "verint-systems file stays on its own row")
    for slug in ("emplifi", "letgo", "digital-assembly"):
        check(by_pub[slug].get("found") is False, f"{slug} usual paths did not invent Official page")
        check(
            sum(int((by_pub[slug].get("file") or {}).get(k) or 0) for k in ("page", "marks", "dpa", "subprocessors", "years")) == 0,
            f"{slug} Completeness is 0",
        )

    # This cut: Branch Metrics leftover. First-party /security is Official page.
    # legal.branch.io DPA and Subprocessor List print. Conveyor stays off Official page.
    check(
        instrument_url(by_pub["branch-metrics"], "dpa")
        == "https://legal.branch.io/saas/branch-saas-dpa/",
        "branch DPA stays the first-party Branch SaaS DPA",
    )
    check(
        instrument_url(by_pub["branch-metrics"], "subprocessors")
        == "https://legal.branch.io/saas/subprocessor-list/",
        "branch list stays the first-party Subprocessor List",
    )
    check((by_pub["branch-metrics"].get("file") or {}).get("dpa") == 20, "branch DPA prints")
    check((by_pub["branch-metrics"].get("file") or {}).get("subprocessors") == 20, "branch processors print")
    check((by_pub["branch-metrics"].get("file") or {}).get("page") == 20, "branch Official page prints")
    check((by_pub["branch-metrics"].get("file") or {}).get("marks") == 10, "branch marks stay dotted — page on file, none extracted")
    check((by_pub["branch-metrics"].get("file") or {}).get("years") in (0, False, None), "branch years stay open")
    check(by_pub["branch-metrics"].get("found") is True, "branch Official page is on file")
    check(
        by_pub["branch-metrics"].get("trust_url") == "https://www.branch.io/security",
        "branch Official page is first-party /security",
    )
    check("conveyor" not in (by_pub["branch-metrics"].get("trust_url") or "").lower(), "branch Official page is not the Conveyor portal")
    check(by_pub["branch-metrics"]["domain"] == "branch.io", "branch official domain is branch.io")
    branch_names = [p.get("name") for p in (by_pub["branch-metrics"].get("processors") or [])]
    branch_slugs = [p.get("slug") for p in (by_pub["branch-metrics"].get("processors") or [])]
    check("Amazon Web Services, Inc" in branch_names, "branch names Amazon Web Services, Inc")
    check("Zendesk" in branch_names, "branch names Zendesk")
    check("Atlassian" in branch_names, "branch names Atlassian")
    check("Software Minds, Inc" in branch_names, "branch names Software Minds, Inc")
    check("DataGrail, Inc" in branch_names, "branch names DataGrail, Inc")
    check("Auth0" in branch_names, "branch names Auth0")
    check("Anthropic" in branch_names, "branch names Anthropic")
    check("Thoughtspot, LLC" in branch_names, "branch names Thoughtspot, LLC")
    check(
        set(s for s in branch_slugs if s)
        == {
            "amazon-web-services",
            "zendesk",
            "atlassian",
            "datagrail",
            "auth0",
            "anthropic",
            "thoughtspot",
        },
        f"branch processor slugs {branch_slugs}",
    )
    check(None in branch_slugs, "software-minds stays off the register")
    check(len(branch_names) == 8, f"branch printed 8 named processors, got {len(branch_names)}")
    branch_html = (ROOT / "site" / "c" / "branch-metrics.html").read_text(encoding="utf-8")
    check("https://legal.branch.io/saas/branch-saas-dpa/" in branch_html, "branch dossier keeps the DPA URL")
    check("https://legal.branch.io/saas/subprocessor-list/" in branch_html, "branch dossier keeps the list URL")
    check("./amazon-web-services.html\">Amazon Web Services, Inc" in branch_html, "branch AWS cross-links to the existing file")
    check("./zendesk.html\">Zendesk" in branch_html, "branch Zendesk cross-links to the existing file")
    check("./atlassian.html\">Atlassian" in branch_html, "branch Atlassian cross-links to the existing file")
    check("./datagrail.html\">DataGrail, Inc" in branch_html, "branch DataGrail cross-links to the existing file")
    check("./auth0.html\">Auth0" in branch_html, "branch Auth0 cross-links to the existing file")
    check("./anthropic.html\">Anthropic" in branch_html, "branch Anthropic cross-links to the existing file")
    check("./thoughtspot.html\">Thoughtspot, LLC" in branch_html, "branch Thoughtspot cross-links to the existing file")
    check("../graph.html#p=software-minds\">Software Minds, Inc" in branch_html, "software-minds stays a graph leftover")
    check("conveyor" not in branch_html.lower(), "branch dossier does not name Conveyor")
    check("trust.branch.io" not in branch_html, "branch dossier does not cite the Conveyor portal")
    check("<h1>Branch Metrics</h1>" in branch_html, "branch dossier is its own file")
    plume_html = (ROOT / "site" / "c" / "plume.html").read_text(encoding="utf-8")
    check("./branch-metrics.html\">Branch Metrics, Inc" in plume_html, "Plume Branch Metrics wire lands on the new file")
    check(
        (by_enr["branch-metrics"].get("links") or {}).get("dpa")
        == "https://legal.branch.io/saas/branch-saas-dpa/",
        "branch enriched DPA URL stays",
    )
    # This cut: Route Mobile first-party DPA HTML. ISO 27001 is contractor
    # language on that DPA, not Route Mobile's own hold.
    check(
        instrument_url(by_pub["route-mobile"], "dpa") == "https://routemobile.com/dpa/",
        "route-mobile DPA is first-party HTML",
    )
    check((by_pub["route-mobile"].get("file") or {}).get("dpa") == 20, "route-mobile DPA prints")
    check((by_pub["route-mobile"].get("file") or {}).get("page") in (0, False, None), "route-mobile Official page stays open")
    check((by_pub["route-mobile"].get("certs") or []) == [], "route-mobile DPA contractor ISO stays unread")
    check("ISO 27001" not in (by_pub["route-mobile"].get("certs") or []), "route-mobile does not file contractor ISO 27001")
    check(by_pub["route-mobile"].get("found") is False, "route-mobile DPA is not Official page")
    rm_html = (ROOT / "site" / "c" / "route-mobile.html").read_text(encoding="utf-8")
    check("<h1>Route Mobile</h1>" in rm_html, "route-mobile dossier is its own file")
    check("https://routemobile.com/dpa/" in rm_html, "route-mobile dossier keeps the DPA URL")
    check("ISO 27001" not in rm_html, "route-mobile dossier does not print contractor ISO 27001")

    # This cut: OneSignal first-party list-of-subprocessors table. Official page
    # stays open. Privacy-page HIPAA-compliant + BAA stays unread. Census Inc is
    # the standing Fivetran alias (Fivetran acquired Census).
    check(
        instrument_url(by_pub["onesignal"], "dpa") == "https://onesignal.com/dpa",
        "onesignal DPA stays the first-party addendum",
    )
    check(
        instrument_url(by_pub["onesignal"], "subprocessors")
        == "https://onesignal.com/list-of-subprocessors",
        "onesignal list is the first-party List of subprocessors",
    )
    check((by_pub["onesignal"].get("file") or {}).get("dpa") == 20, "onesignal DPA prints")
    check((by_pub["onesignal"].get("file") or {}).get("subprocessors") == 20, "onesignal processors print")
    check((by_pub["onesignal"].get("file") or {}).get("page") in (0, False, None), "onesignal Official page stays open")
    check((by_pub["onesignal"].get("file") or {}).get("marks") == 20, "onesignal marks stay")
    check((by_pub["onesignal"].get("file") or {}).get("years") in (0, False, None), "onesignal years stay open")
    check(by_pub["onesignal"].get("found") is False, "onesignal privacy is not Official page")
    check("HIPAA" not in (by_pub["onesignal"].get("certs") or []), "onesignal HIPAA-compliant BAA stays unread")
    onesignal_names = [p.get("name") for p in (by_pub["onesignal"].get("processors") or [])]
    onesignal_slugs = [p.get("slug") for p in (by_pub["onesignal"].get("processors") or [])]
    check("Intercom Inc" in onesignal_names, "onesignal names Intercom Inc")
    check("Cloudflare Inc" in onesignal_names, "onesignal names Cloudflare Inc")
    check("Census Inc" in onesignal_names, "onesignal names Census Inc")
    check("Google Inc" in onesignal_names, "onesignal names Google Inc")
    check("Rollbar Inc" in onesignal_names, "onesignal names Rollbar Inc")
    check("Filestack Inc" in onesignal_names, "onesignal names Filestack Inc")
    check("Mailgun Inc" in onesignal_names, "onesignal names Mailgun Inc")
    check("Twilio Inc" in onesignal_names, "onesignal names Twilio Inc")
    check(
        onesignal_slugs
        == ["intercom", "cloudflare", "fivetran", "google", "rollbar", "filestack", "mailgun", "twilio"],
        f"onesignal processor slugs {onesignal_slugs}",
    )
    check(len(onesignal_names) == 8, f"onesignal printed 8 named processors, got {len(onesignal_names)}")
    os_html = (ROOT / "site" / "c" / "onesignal.html").read_text(encoding="utf-8")
    check("<h1>OneSignal</h1>" in os_html, "onesignal dossier is its own file")
    check("https://onesignal.com/dpa" in os_html, "onesignal dossier keeps the DPA URL")
    check("https://onesignal.com/list-of-subprocessors" in os_html, "onesignal dossier keeps the list URL")
    check("./intercom.html\">Intercom Inc" in os_html, "onesignal Intercom cross-links to the existing file")
    check("./cloudflare.html\">Cloudflare Inc" in os_html, "onesignal Cloudflare cross-links to the existing file")
    check("./fivetran.html\">Census Inc" in os_html, "onesignal Census Inc uses the standing Fivetran alias")
    check("./google.html\">Google Inc" in os_html, "onesignal Google cross-links to the existing file")
    check("./rollbar.html\">Rollbar Inc" in os_html, "onesignal Rollbar cross-links to the existing file")
    check("./filestack.html\">Filestack Inc" in os_html, "onesignal Filestack cross-links to the existing file")
    check("./mailgun.html\">Mailgun Inc" in os_html, "onesignal Mailgun cross-links to the existing file")
    check("./twilio.html\">Twilio Inc" in os_html, "onesignal Twilio cross-links to the existing file")
    check("HIPAA" not in os_html, "onesignal dossier does not print HIPAA-compliant BAA")
    check("Official page · not on file" in os_html, "onesignal Official page stays not on file")
    check(
        (by_enr["onesignal"].get("links") or {}).get("subprocessors")
        == "https://onesignal.com/list-of-subprocessors",
        "onesignal enriched list URL stays",
    )

    # This cut: LinkedIn first-party customer-subprocessors table. DPA product
    # lines (Talent/Hire, Learning, Sales Solutions) stay unread. Sparkpost /
    # Momentive / TDCX / Code 42 / Microsoft affiliates land on existing files.
    check(
        instrument_url(by_pub["linkedin"], "dpa") == "https://www.linkedin.com/legal/l/dpa",
        "linkedin DPA stays the first-party addendum",
    )
    check(
        instrument_url(by_pub["linkedin"], "subprocessors")
        == "https://www.linkedin.com/legal/l/customer-subprocessors",
        "linkedin list is the first-party customer-subprocessors table",
    )
    check((by_pub["linkedin"].get("file") or {}).get("dpa") == 20, "linkedin DPA prints")
    check((by_pub["linkedin"].get("file") or {}).get("subprocessors") == 20, "linkedin processors print")
    check((by_pub["linkedin"].get("file") or {}).get("page") == 20, "linkedin Official page stays")
    check((by_pub["linkedin"].get("file") or {}).get("marks") == 20, "linkedin marks stay")
    check((by_pub["linkedin"].get("file") or {}).get("years") in (0, False, None), "linkedin years stay open")
    linkedin_names = [p.get("name") for p in (by_pub["linkedin"].get("processors") or [])]
    linkedin_slugs = [p.get("slug") for p in (by_pub["linkedin"].get("processors") or [])]
    check("Microsoft Corporation and its Affiliates" in linkedin_names, "linkedin names Microsoft affiliates")
    check("Amazon Web Services, Inc" in linkedin_names, "linkedin names AWS")
    check("Box.com, Inc" in linkedin_names, "linkedin names Box")
    check("Message Systems, Inc. dba Sparkpost" in linkedin_names, "linkedin names Sparkpost")
    check("Momentive, Inc. (fka SurveyMonkey, Inc.)" in linkedin_names, "linkedin names Momentive")
    check("Code 42 Software Inc" in linkedin_names, "linkedin names Code 42")
    check("TDCX Digilab India Private Limited" in linkedin_names, "linkedin names TDCX")
    check("Talent/Hire" not in linkedin_names, "linkedin DPA Talent/Hire product line stays unread")
    check("Learning" not in linkedin_names, "linkedin DPA Learning product line stays unread")
    check("Sales Solutions" not in linkedin_names, "linkedin DPA Sales Solutions product line stays unread")
    check("Marketing Solutions" not in linkedin_names, "linkedin DPA Marketing Solutions product line stays unread")
    check("microsoft" in linkedin_slugs, "linkedin Microsoft affiliates use the Microsoft file")
    check("amazon-web-services" in linkedin_slugs, "linkedin AWS uses the existing file")
    check("box" in linkedin_slugs, "linkedin Box uses the existing file")
    check("messagebird" in linkedin_slugs, "linkedin Sparkpost uses the MessageBird file")
    check("surveymonkey" in linkedin_slugs, "linkedin Momentive uses the SurveyMonkey file")
    check("code42" in linkedin_slugs, "linkedin Code 42 uses the Code42 file")
    check("tdcx" in linkedin_slugs, "linkedin TDCX uses the existing file")
    check("concentrix" in linkedin_slugs, "linkedin Concentrix uses the existing file")
    check("tata-communications" in linkedin_slugs, "linkedin Tata Communications Ireland uses the Tata Communications file")
    check("hcl-tech" in linkedin_slugs, "linkedin HCL America uses the HCLTech file")
    check("teleperformance-colombia" in linkedin_slugs, "linkedin Ypiresia 800 uses the Teleperformance file")
    check("ibm" in linkedin_slugs, "linkedin NSONE uses the IBM file")
    check("ai-media" in linkedin_slugs, "linkedin Ai-Media uses the new file")
    check(linkedin_slugs.count("teleperformance-colombia") == 2, "linkedin Ypiresia 800 and CRM Services India land on Teleperformance")
    check(linkedin_slugs.count("ai-media") == 2, "linkedin Ai-Media and EEG Enterprises land on Ai-Media")
    check("crm-services-india-private" not in linkedin_slugs, "linkedin does not invent a second Teleperformance dossier")
    check("eeg-enterprises" not in linkedin_slugs, "linkedin does not invent a second Ai-Media dossier")
    check("tata-communications-ireland" not in linkedin_slugs, "linkedin does not invent a second Tata dossier")
    check("hcl-america" not in linkedin_slugs, "linkedin does not invent a second HCL dossier")
    check("nsone" not in linkedin_slugs, "linkedin does not invent a second NS1 dossier")
    check(linkedin_slugs.count("tdcx") == 1, "linkedin TDCX regional rows collapse to one file")
    check(linkedin_slugs.count("concentrix") == 1, "linkedin Concentrix regional rows collapse to one file")
    check(len(linkedin_names) == 34, f"linkedin printed 34 named processors, got {len(linkedin_names)}")
    li_html = (ROOT / "site" / "c" / "linkedin.html").read_text(encoding="utf-8")
    check("<h1>LinkedIn</h1>" in li_html, "linkedin dossier is its own file")
    check("https://www.linkedin.com/legal/l/dpa" in li_html, "linkedin dossier keeps the DPA URL")
    check("https://www.linkedin.com/legal/l/customer-subprocessors" in li_html, "linkedin dossier keeps the list URL")
    check("./microsoft.html\">Microsoft Corporation and its Affiliates" in li_html, "linkedin Microsoft cross-links to the existing file")
    check("./amazon-web-services.html\">Amazon Web Services, Inc" in li_html, "linkedin AWS cross-links to the existing file")
    check("./box.html\">Box.com, Inc" in li_html, "linkedin Box cross-links to the existing file")
    check("./messagebird.html\">Message Systems, Inc. dba Sparkpost" in li_html, "linkedin Sparkpost uses the MessageBird alias")
    check("./surveymonkey.html\">Momentive, Inc. (fka SurveyMonkey, Inc.)" in li_html, "linkedin Momentive uses the SurveyMonkey alias")
    check("./code42.html\">Code 42 Software Inc" in li_html, "linkedin Code 42 cross-links to the existing file")
    check("./tdcx.html\">TDCX Digilab India Private Limited" in li_html, "linkedin TDCX cross-links to the existing file")
    check("Talent/Hire" not in li_html, "linkedin dossier does not print DPA product lines")

    # This cut: Nylas first-party /security/subprocessors table. URL-only list
    # upgrades to printed names. Twilio Segment is Segment. GCP / Gemini / Looker
    # land on Google. Gong.io lands on Gong. DPA stays open.
    check(
        instrument_url(by_pub["nylas"], "subprocessors")
        == "https://www.nylas.com/security/subprocessors/",
        "nylas list is the first-party Subprocessors table",
    )
    check((by_pub["nylas"].get("file") or {}).get("subprocessors") == 20, "nylas processors print")
    check((by_pub["nylas"].get("file") or {}).get("dpa") in (0, False, None), "nylas DPA stays open")
    check((by_pub["nylas"].get("file") or {}).get("page") == 20, "nylas Official page stays")
    check((by_pub["nylas"].get("file") or {}).get("marks") == 20, "nylas marks stay")
    check((by_pub["nylas"].get("file") or {}).get("years") in (0, False, None), "nylas years stay open")
    nylas_names = [p.get("name") for p in (by_pub["nylas"].get("processors") or [])]
    nylas_slugs = [p.get("slug") for p in (by_pub["nylas"].get("processors") or [])]
    check("Amazon Web Services" in nylas_names, "nylas names AWS")
    check("Google Cloud Platform" in nylas_names, "nylas names GCP")
    check("Twilio Segment" in nylas_names, "nylas names Twilio Segment")
    check("Gong.io" in nylas_names, "nylas names Gong.io")
    check("MadKudu" in nylas_names, "nylas names MadKudu")
    check("hg-insights" in nylas_slugs, "nylas MadKudu uses the HG Insights file")
    check("madkudu" not in nylas_slugs, "nylas does not invent a second MadKudu dossier")
    check("amazon-web-services" in nylas_slugs, "nylas AWS uses the existing file")
    check("google" in nylas_slugs, "nylas GCP uses the Google file")
    check("segment" in nylas_slugs, "nylas Twilio Segment uses the Segment file")
    check("gong" in nylas_slugs, "nylas Gong.io uses the Gong file")
    check("apollo-io" in nylas_slugs, "nylas Apollo uses the Apollo.io file")
    check("teleport" in nylas_slugs, "nylas Gravitational uses the Teleport file")
    check("ordway" in nylas_slugs, "nylas Ordway uses the new file")
    check("apollo" not in nylas_slugs, "nylas does not invent a second Apollo dossier")
    check("gravitational-teleport" not in nylas_slugs, "nylas does not invent a second Teleport dossier")
    check("twilio" not in nylas_slugs, "nylas Twilio Segment is not filed as Twilio")
    check(nylas_slugs.count("google") == 1, "nylas GCP / Gemini / Looker collapse to one Google file")
    check(len(nylas_names) == 40, f"nylas printed 40 named processors, got {len(nylas_names)}")
    ny_html = (ROOT / "site" / "c" / "nylas.html").read_text(encoding="utf-8")
    check("<h1>Nylas</h1>" in ny_html, "nylas dossier is its own file")
    check("https://www.nylas.com/security/subprocessors/" in ny_html, "nylas dossier keeps the list URL")
    check("./amazon-web-services.html\">Amazon Web Services" in ny_html, "nylas AWS cross-links to the existing file")
    check("./google.html\">Google Cloud Platform" in ny_html, "nylas GCP cross-links to the Google file")
    check("./segment.html\">Twilio Segment" in ny_html, "nylas Twilio Segment uses the Segment alias")
    check("./gong.html\">Gong.io" in ny_html, "nylas Gong.io uses the Gong alias")
    check("./apollo-io.html\">Apollo" in ny_html, "nylas Apollo cross-links to Apollo.io")
    check("./teleport.html" in ny_html, "nylas Gravitational cross-links to Teleport")
    check("./hg-insights.html\">MadKudu" in ny_html, "nylas MadKudu cross-links to HG Insights")

    check(
        instrument_url(by_pub["hg-insights"], "dpa") == "https://hginsights.com/dpa/",
        "hg-insights DPA is first-party HTML",
    )
    check((by_pub["hg-insights"].get("file") or {}).get("dpa") == 20, "hg-insights DPA prints")
    check(
        ((by_pub["hg-insights"].get("instruments") or {}).get("privacy") or {}).get("url")
        == "https://hginsights.com/privacy-policy/",
        "hg-insights privacy is first-party HTML",
    )
    dashlane_names = [p.get("name") for p in (by_pub["dashlane"].get("processors") or [])]
    dashlane_slugs = [p.get("slug") for p in (by_pub["dashlane"].get("processors") or [])]
    check(any("Intersections" in (n or "") for n in dashlane_names), "dashlane names Intersections")
    check("aura-previously-pango-anchorfree" in dashlane_slugs, "dashlane Intersections uses the Aura file")
    check("intersections" not in dashlane_slugs, "dashlane does not invent a second Aura dossier")

    check(
        instrument_url(by_pub["teleport"], "dpa") == "https://goteleport.com/legal/dpa/",
        "teleport DPA is first-party HTML",
    )
    check((by_pub["teleport"].get("file") or {}).get("dpa") == 20, "teleport DPA prints")
    check((by_enr["teleport"].get("links") or {}).get("subprocessors") in (None, ""), "teleport Vanta list stays unread")
    check(by_pub["teleport"].get("founded_year") == 2015, "teleport year is first-party foundingDate")
    check(by_pub["teleport"].get("founded_source") == "https://goteleport.com/about", "teleport year source is /about")
    check((by_pub["teleport"].get("file") or {}).get("years") == 20, "teleport years print")
    check(
        instrument_url(by_pub["ketch"], "dpa") == "https://www.ketch.com/data-processing-addendum",
        "ketch DPA is first-party HTML",
    )
    check((by_pub["ketch"].get("file") or {}).get("dpa") == 20, "ketch DPA prints")
    check(by_pub["ketch"].get("found") is False, "ketch Vanta portal is not Official page")
    check(not by_pub["ketch"].get("trust_url"), "ketch has no invented Official page")
    check(by_pub["ketch"].get("founded_year") == 2020, "ketch year is first-party foundingDate")
    check(by_pub["ketch"].get("founded_source") == "https://www.ketch.com/about", "ketch year source is /about")
    check((by_pub["ketch"].get("file") or {}).get("years") == 20, "ketch years print")
    check(by_pub["inkeep"].get("founded_year") == 2023, "inkeep year is first-party foundingDate")
    check(by_pub["inkeep"].get("founded_source") == "https://inkeep.com/about", "inkeep year source is /about")
    check((by_pub["inkeep"].get("file") or {}).get("years") == 20, "inkeep years print")
    check(instrument_url(by_pub["inkeep"], "dpa") in (None, ""), "inkeep DPA PDF stays unread")

    check(
        ((by_pub["ai-media"].get("instruments") or {}).get("privacy") or {}).get("url")
        == "https://www.ai-media.tv/privacy-policy/",
        "ai-media privacy is first-party HTML",
    )
    check(by_pub["ai-media"].get("found") is False, "ai-media Vanta portal is not Official page")
    check(
        ((by_pub["ordway"].get("instruments") or {}).get("privacy") or {}).get("url")
        == "https://ordwaylabs.com/privacy/",
        "ordway privacy is first-party HTML",
    )
    check(
        ((by_pub["thorn"].get("instruments") or {}).get("privacy") or {}).get("url")
        == "https://www.thorn.org/privacy-policy/",
        "thorn privacy is first-party HTML",
    )
    check(
        instrument_url(by_pub["capacity"], "dpa") in (None, ""),
        "capacity DPA stays open",
    )

    print(
        f"ok increment-dpa privacy-page-queue {len(expected_batch)} walked; "
        f"{len(report.get('dpa_filed') or [])} dpa {len(report.get('subprocessors_filed') or [])} lists"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
