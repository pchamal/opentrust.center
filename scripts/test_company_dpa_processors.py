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

    check(
        instrument_url(by_pub["swan"], "dpa") == "https://www.getswan.com/legal/dpa",
        "swan DPA is first-party HTML",
    )
    check((by_pub["swan"].get("file") or {}).get("dpa") == 20, "swan DPA prints")
    check((by_pub["swan"].get("file") or {}).get("years") == 20, "swan years print")
    check(by_pub["swan"].get("found") is False, "swan Official page stays open")
    check(not (by_pub["swan"].get("processors") or []), "swan Notion list stays unread")
    check((by_pub["swan"].get("file") or {}).get("subprocessors") in (0, False, None), "swan processors stay open")
    swan_html = (ROOT / "site" / "c" / "swan.html").read_text(encoding="utf-8")
    check("https://www.getswan.com/legal/dpa" in swan_html, "swan dossier cites the DPA")
    check("notion.site" not in swan_html, "swan dossier does not file the Notion processor shell")
    check(
        instrument_url(by_pub["84codes-cloudamqp"], "dpa")
        == "https://www.cloudamqp.com/legal/terms_of_service.html#data-processing-agreement",
        "cloudamqp DPA is the first-party ToS exhibit",
    )
    check((by_pub["84codes-cloudamqp"].get("file") or {}).get("dpa") == 20, "cloudamqp DPA prints")
    check(
        by_pub["84codes-cloudamqp"].get("trust_url")
        == "https://www.cloudamqp.com/legal/security_and_compliance.html",
        "cloudamqp Official page stays first-party security",
    )
    check(not (by_pub["84codes-cloudamqp"].get("processors") or []), "cloudamqp DPA annex headers stay unread")
    check(
        (by_pub["84codes-cloudamqp"].get("file") or {}).get("subprocessors") in (0, False, None),
        "cloudamqp processors stay open",
    )
    check(by_pub["84codes-cloudamqp"].get("founded_year") in (None, 0, False), "cloudamqp launched-in year stays open")
    ca_html = (ROOT / "site" / "c" / "84codes-cloudamqp.html").read_text(encoding="utf-8")
    check("<h1>CloudAMQP</h1>" in ca_html, "cloudamqp dossier is its own file")
    check(
        "https://www.cloudamqp.com/legal/terms_of_service.html#data-processing-agreement" in ca_html,
        "cloudamqp dossier cites the DPA exhibit",
    )
    check("trust.84codes.com" not in ca_html, "cloudamqp dossier does not file the portal as Official page")
    check(
        instrument_url(by_pub["loops"], "dpa") == "https://loops.so/dpa",
        "loops DPA is first-party HTML",
    )
    check((by_pub["loops"].get("file") or {}).get("dpa") == 20, "loops DPA prints")
    check(by_pub["loops"].get("found") is False, "loops Official page stays open")
    check(not (by_pub["loops"].get("processors") or []), "loops named processors stay open")
    check((by_pub["loops"].get("file") or {}).get("subprocessors") in (0, False, None), "loops processors stay open")
    check(by_pub["loops"].get("founded_year") in (None, 0, False), "loops years stay open")
    loops_html = (ROOT / "site" / "c" / "loops.html").read_text(encoding="utf-8")
    check("<h1>Loops</h1>" in loops_html, "loops dossier is its own file")
    check("https://loops.so/dpa" in loops_html, "loops dossier cites the DPA")
    check("Official page · not on file" in loops_html, "loops Official page stays open")
    check(
        instrument_url(by_pub["coralogix"], "dpa")
        == "https://coralogix.com/data-processing-agreement/",
        "coralogix DPA is first-party HTML",
    )
    check((by_pub["coralogix"].get("file") or {}).get("dpa") == 20, "coralogix DPA prints")
    check(by_pub["coralogix"].get("found") is False, "coralogix SafeBase portal is not Official page")
    check(not by_pub["coralogix"].get("trust_url"), "coralogix portal is not the Official page URL")
    check(
        ((by_pub["coralogix"].get("instruments") or {}).get("trust") or {}).get("url")
        == "https://trust.coralogix.com",
        "coralogix trust instrument keeps the portal URL as a link",
    )
    check(not (by_pub["coralogix"].get("certs") or []), "coralogix footer chips stay unread")
    check((by_pub["coralogix"].get("file") or {}).get("marks") in (0, False, None), "coralogix marks stay open")

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
    graph_html = (ROOT / "site" / "graph.html").read_text(encoding="utf-8")
    check('data-sort="risk"' not in graph_html, "list dropped Concentration risk sort")
    check('>Concentration</button>' not in graph_html, "list dropped Concentration column")

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

    # This increment: upper-quadrant DPA-on-file / subprocessors queue (~40).
    expected_batch = [
        "accordance",
        "acorns",
        "acquire-asia-pacific-philippines",
        "actian",
        "actionstep",
        "acumatica",
        "ada",
        "adacore",
        "adp",
        "agentsmyth",
        "aha",
        "airbrake",
        "anytech365",
        "armo-security",
        "blogvault",
        "bluesnap",
        "bugsnag",
        "chargebee",
        "clickatell",
        "cloudwave",
        "common-room",
        "crypto-com",
        "customer-dynamics",
        "datagrail",
        "datalab",
        "adjiva-pte-aka-deltax",
        "devo",
        "discord",
        "dstny-automate-formerly-qunifi",
        "create-without-limits-technologies-dba-enhancor",
        "exoscale",
        "fieldai",
        "filestack",
        "flapping-airplanes",
        "foundever-operating",
        "grab",
        "happyfox",
        "hiddenlayer",
        "hoodwink-consulting",
        "hp",
    ]
    check(report.get("batch") == expected_batch, "batch is the upper-quadrant subprocessors queue")
    filed_dpa = {r["slug"]: r for r in (report.get("dpa_filed") or [])}
    check(set(filed_dpa) == {"exoscale", "hiddenlayer"}, f"DPA links filed, got {sorted(filed_dpa)}")
    filed_sub = {r["slug"]: r for r in (report.get("subprocessors_filed") or [])}
    check(set(filed_sub) == {"aha"}, f"named-processor lists filed, got {sorted(filed_sub)}")
    stayed = {r["slug"] for r in (report.get("stayed_open") or [])}
    stayed_dpa = {r["slug"] for r in (report.get("stayed_open") or []) if r.get("rule") == "dpa"}
    stayed_sub = {r["slug"] for r in (report.get("stayed_open") or []) if r.get("rule") == "subprocessors"}
    check("exoscale" not in stayed_dpa, "Exoscale DPA was filed")
    check("exoscale" in stayed_sub, "Exoscale named list stayed open")
    check("hiddenlayer" not in stayed_dpa, "HiddenLayer DPA was filed")
    check("hiddenlayer" in stayed_sub, "HiddenLayer named list stayed open")
    check("aha" in stayed_dpa, "Aha! DPA probes stayed open")
    check("aha" not in stayed_sub, "Aha! named list was filed")
    check("chargebee" in stayed_dpa, "Chargebee Nuxt JS-shell DPA stayed open")
    check("chargebee" in stayed_sub, "Chargebee named list stayed open")
    check(len(report.get("stayed_open") or []) == 77, f"77 open DPA/subprocessors slots, got {len(report.get('stayed_open') or [])}")
    check(len(stayed_dpa) == 38, f"38 DPA slots stayed open, got {len(stayed_dpa)}")
    check(len(stayed_sub) == 39, f"39 subprocessors slots stayed open, got {len(stayed_sub)}")
    # This-cut review drops stay unread.
    check("dpa" not in ((by_enr["chargebee"].get("links") or {})), "Chargebee links.dpa stays off the Nuxt JS-shell")
    check(not instrument_url(by_pub["chargebee"], "dpa"), "Chargebee DPA stays open")
    check("dpa" not in ((by_enr["aha"].get("links") or {})), "Aha! links.dpa stays off the 404 probes")
    check(not instrument_url(by_pub["aha"], "dpa"), "Aha! DPA stays open")
    check("dpa" not in ((by_enr["discord"].get("links") or {})), "Discord links.dpa stays off the privacy-policy bounce")
    check("subprocessors" not in ((by_enr["ada"].get("links") or {})), "Ada links.subprocessors stays off the SafeBase portal")
    # Prior-cut review drops stay unread.
    check("unbounce" not in expected_batch, "Unbounce is not retried")
    check("subprocessors" not in ((by_enr["unbounce"].get("links") or {})), "Unbounce links.subprocessors stays off the CSS-grid page")
    check(not (by_pub["unbounce"].get("processors") or []), "Unbounce names no CSS-grid processors")
    check(
        "subprocessors" not in ((by_enr["link-mobility"].get("links") or {})),
        "LINK Mobility links.subprocessors stays off the PDF catalog",
    )
    check("dpa" not in ((by_enr["e2open"].get("links") or {})), "E2open links.dpa stays off the WiseTech parent page")
    check("inkeep" not in expected_batch, "Inkeep is not retried")
    check("dpa" not in ((by_enr["inkeep"].get("links") or {})), "Inkeep links.dpa stays off the PDF")
    check("dpa" not in ((by_enr["kyndryl"].get("links") or {})), "Kyndryl links.dpa stays off the PDF")
    check(
        "dpa" not in ((by_enr["kyndryl-holdings"].get("links") or {})),
        "Kyndryl Holdings links.dpa stays off the parent PDF",
    )
    check("browserbase" not in {r["slug"] for r in (report.get("dpa_filed") or [])}, "Browserbase DPA was not filed")
    check(
        "dpa" not in ((by_enr["browserbase"].get("links") or {})),
        "Browserbase links.dpa stays off the sign-in wall",
    )
    check(
        "dpa" not in ((by_enr["tableau"].get("links") or {})),
        "Tableau links.dpa stays off the Salesforce parent PDF",
    )
    check(
        "dpa" not in ((by_enr["panther-labs"].get("links") or {})),
        "Panther links.dpa stays off the Framer JS-shell",
    )
    check("neon" not in filed_sub, "Neon is not a filed named-processor list")
    check(not (by_pub["neon"].get("processors") or []), "Neon names no processors")
    check(
        "subprocessors" not in ((by_enr["neon"].get("links") or {})),
        "Neon links.subprocessors stays off the Databricks parent-company list",
    )
    check("smarsh" not in filed_sub, "Smarsh Cloudflare 403 list was not filed")
    check(not (by_pub["smarsh"].get("processors") or []), "Smarsh names no processors")
    check((by_pub["smarsh"].get("file") or {}).get("subprocessors") == 10, "Smarsh list URL stays dotted, names unread")
    check(
        (by_enr["smarsh"].get("links") or {}).get("subprocessors")
        == "https://www.smarsh.com/subprocessors",
        "Smarsh stored list URL stays, names stay unread",
    )
    check("dpa" not in ((by_enr["kombo-technologies"].get("links") or {})), "Kombo links.dpa stays off the PDF wrapper")
    check(
        "subprocessors" not in ((by_enr["litmus"].get("links") or {})),
        "Litmus links.subprocessors stays off the Validity parent-company list",
    )
    check(not (by_pub["viatel"].get("processors") or []), "Viatel PDF-only list stays unread")

    for slug in stayed_sub:
        pub = by_pub[slug]
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
        "uniphore", "arkose-labs", "clazar", "cognition-ai",
        "sam-labs", "apideck", "client-success", "84codes-cloudamqp",
        "heygen", "modal", "surveysparrow", "coralogix",
        "help-scout", "lastpass", "recurly-com", "segment",
        "lob-com", "productboard", "dash0", "temporal", "neon", "smarsh",
        "panther-labs", "plume", "contentsquare", "uploadcare",
        "browserbase", "tableau", "accurx", "inkeep", "kyndryl",
        "data-zoo", "hightouch", "plivo", "smartrecruiters", "sms-magic",
        "cloudinary", "langfuse",
        "artie", "discourse", "pluralsight", "brightcove",
        "kombo-technologies", "litmus",
        "unbounce", "e2open", "krea", "boltz", "link-mobility", "arsys",
        "ask-ai", "sublime-security", "monetate", "protiviti",
        "telesign", "alphasights", "scoro", "absolute-security", "crowdin",
        "chargebee", "discord", "ada", "bugsnag",
    ):
        check(slug in PRIOR_ATTEMPTED, f"{slug} leftover walk stays on the skip list")
        check(slug not in leftover_slugs, f"{slug} leftover is not retried")

    for slug, rec in filed_dpa.items():
        html = (ROOT / "site" / "c" / f"{slug}.html").read_text(encoding="utf-8")
        check(rec["url"] in html, f"{slug} dossier cites the DPA URL")
        check('rel="noopener noreferrer"' in html, f"{slug} outbound links use noopener")
    for slug, rec in filed_sub.items():
        html = (ROOT / "site" / "c" / f"{slug}.html").read_text(encoding="utf-8")
        check(rec["url"] in html, f"{slug} dossier cites the list URL")
        check('rel="noopener noreferrer"' in html, f"{slug} outbound links use noopener")
    # This cut: first-party Completeness DPA on Exoscale and HiddenLayer.
    # Aha! first-party HTML table. Chargebee Nuxt JS-shell titled DPA stays
    # unread. Discord /privacy/dpa is the privacy policy. Ada SafeBase
    # catalog stays unread. Bugsnag /legal/dpa parent-bounces to SmartBear.
    # Functional Software aliases onto Sentry. O+ZWSP+penAI aliases onto
    # OpenAI. Duo Security aliases onto Cisco. Rocket Science Group already
    # lands on Mailchimp. OOPSpam and Pipedream stay leftover graph nodes.
    check(
        instrument_url(by_pub["exoscale"], "dpa") == "https://www.exoscale.com/dpa/",
        "exoscale DPA is first-party HTML",
    )
    check((by_pub["exoscale"].get("file") or {}).get("dpa") == 20, "exoscale DPA prints")
    check(not (by_pub["exoscale"].get("processors") or []), "exoscale named list stays unread")
    check((by_pub["exoscale"].get("file") or {}).get("subprocessors") in (0, False, None), "exoscale processors stay open")
    check(
        instrument_url(by_pub["hiddenlayer"], "dpa") == "https://www.hiddenlayer.com/dpa",
        "hiddenlayer DPA is first-party HTML",
    )
    check((by_pub["hiddenlayer"].get("file") or {}).get("dpa") == 20, "hiddenlayer DPA prints")
    check(not (by_pub["hiddenlayer"].get("processors") or []), "hiddenlayer named list stays unread")
    check((by_pub["hiddenlayer"].get("file") or {}).get("subprocessors") in (0, False, None), "hiddenlayer processors stay open")
    aha_names = [p.get("name") for p in (by_pub["aha"].get("processors") or [])]
    aha_slugs = [p.get("slug") for p in (by_pub["aha"].get("processors") or [])]
    check(
        instrument_url(by_pub["aha"], "subprocessors")
        == "https://www.aha.io/legal/subprocessors",
        "aha list URL is first-party HTML",
    )
    check((by_pub["aha"].get("file") or {}).get("subprocessors") == 20, "aha processors print")
    check(len(aha_names) == 14, f"aha printed 14 named processors, got {len(aha_names)}")
    check("Amazon Web Services, Inc" in aha_names, "aha names AWS")
    check("Functional Software, Inc" in aha_names, "aha names Functional Software")
    check("Duo Security, Inc" in aha_names, "aha names Duo Security")
    check("The Rocket Science Group, LLC" in aha_names, "aha names Rocket Science Group")
    check("amazon-web-services" in aha_slugs, "aha AWS uses the Amazon Web Services file")
    check("sentry" in aha_slugs, "aha Functional Software uses the Sentry file")
    check("cisco" in aha_slugs, "aha Duo Security uses the Cisco file")
    check("openai" in aha_slugs, "aha OpenAI uses the OpenAI file")
    check("mailchimp" in aha_slugs, "aha Rocket Science Group uses the Mailchimp file")
    check("oopspam" not in by_pub, "aha does not invent an OOPSpam dossier")
    check("pipedream" not in by_pub, "aha does not invent a Pipedream dossier")
    check("o-penai" not in by_pub, "aha does not invent an o-penai dossier")
    check("duo-security" not in by_pub, "aha does not invent a Duo Security dossier")
    check("functional-software" not in by_pub, "aha does not invent a Functional Software dossier")
    # Prior cut: first-party Completeness DPA on Absolute Security and
    # AlphaSights. AlphaSights and Scoro first-party HTML tables. Crowdin
    # privacy-policy glossary (Client / User / Visitor) stays unread. Gemini
    # aliases onto Google. ZipDX / PlanHat / Squadcast stay leftover graph
    # nodes. Scoro DPA homepage-bounce stays open.
    check(
        instrument_url(by_pub["absolute-security"], "dpa")
        == "https://www.absolute.com/company/legal/data-processing-addendum",
        "absolute-security DPA is first-party HTML",
    )
    check((by_pub["absolute-security"].get("file") or {}).get("dpa") == 20, "absolute-security DPA prints")
    check(not (by_pub["absolute-security"].get("processors") or []), "absolute-security named list stays unread")
    check((by_pub["absolute-security"].get("file") or {}).get("subprocessors") in (0, False, None), "absolute-security processors stay open")
    check(
        instrument_url(by_pub["alphasights"], "dpa") == "https://www.alphasights.com/dpa/",
        "alphasights DPA is first-party HTML",
    )
    check((by_pub["alphasights"].get("file") or {}).get("dpa") == 20, "alphasights DPA prints")
    as_names = [p.get("name") for p in (by_pub["alphasights"].get("processors") or [])]
    as_slugs = [p.get("slug") for p in (by_pub["alphasights"].get("processors") or [])]
    check(
        instrument_url(by_pub["alphasights"], "subprocessors")
        == "https://www.alphasights.com/sub-processors/",
        "alphasights list URL is first-party HTML",
    )
    check((by_pub["alphasights"].get("file") or {}).get("subprocessors") == 20, "alphasights processors print")
    check(len(as_names) == 18, f"alphasights printed 18 named processors, got {len(as_names)}")
    check("Amazon Web Services" in as_names, "alphasights names AWS")
    check("Twilio Inc" in as_names, "alphasights names Twilio")
    check("Zoom Video Communications, Inc" in as_names, "alphasights names Zoom")
    check("Google Cloud EMEA Limited" in as_names, "alphasights names Google Cloud EMEA")
    check("amazon-web-services" in as_slugs, "alphasights AWS uses the Amazon Web Services file")
    check("twilio" in as_slugs, "alphasights Twilio uses the Twilio file")
    check("zoom" in as_slugs, "alphasights Zoom uses the Zoom file")
    check("google" in as_slugs, "alphasights Google Cloud EMEA uses the Google file")
    check("zipdx" not in by_pub, "alphasights does not invent a ZipDX dossier")
    check(
        instrument_url(by_pub["scoro"], "subprocessors")
        == "https://www.scoro.com/subprocessor-list/",
        "scoro list URL is first-party HTML",
    )
    check((by_pub["scoro"].get("file") or {}).get("subprocessors") == 20, "scoro processors print")
    sc_names = [p.get("name") for p in (by_pub["scoro"].get("processors") or [])]
    sc_slugs = [p.get("slug") for p in (by_pub["scoro"].get("processors") or [])]
    check(len(sc_names) == 15, f"scoro printed 15 named processors, got {len(sc_names)}")
    check("Amazon Web Services" in sc_names, "scoro names AWS")
    check("Gemini" in sc_names, "scoro names Gemini")
    check("Google Cloud Platform" in sc_names, "scoro names Google Cloud Platform")
    check("Google Workspace" in sc_names, "scoro names Google Workspace")
    check("Hetzner" in sc_names, "scoro names Hetzner")
    check("amazon-web-services" in sc_slugs, "scoro AWS uses the Amazon Web Services file")
    check("google" in sc_slugs, "scoro Gemini / GCP / Workspace use the Google file")
    check("hetzner-online" in sc_slugs, "scoro Hetzner uses the Hetzner Online file")
    check("planhat" not in by_pub, "scoro does not invent a PlanHat dossier")
    check("squadcast" not in by_pub, "scoro does not invent a Squadcast dossier")
    check("gemini" not in by_pub, "scoro does not invent a Gemini dossier")
    # Prior cut: first-party Completeness DPA on strongDM. Koala first-party
    # HTML list. SendGrid aliases onto Twilio. Mode stays a leftover graph
    # node. Kombo PDF-download DPA and Litmus→Validity parent list stay open.
    check(
        instrument_url(by_pub["strongdm"], "dpa")
        == "https://www.strongdm.com/legal/data-processing-agreement",
        "strongdm DPA is first-party HTML",
    )
    check((by_pub["strongdm"].get("file") or {}).get("dpa") == 20, "strongdm DPA prints")
    check(not (by_pub["strongdm"].get("processors") or []), "strongdm SafeBase list stays unread")
    koala_names = [p.get("name") for p in (by_pub["konfetti-koala"].get("processors") or [])]
    koala_slugs = [p.get("slug") for p in (by_pub["konfetti-koala"].get("processors") or [])]
    check(
        instrument_url(by_pub["konfetti-koala"], "subprocessors")
        == "https://getkoala.com/legal/subprocessors",
        "konfetti-koala list URL is first-party HTML",
    )
    check((by_pub["konfetti-koala"].get("file") or {}).get("subprocessors") == 20, "konfetti-koala processors print")
    check(len(koala_names) == 4, f"konfetti-koala printed 4 named processors, got {len(koala_names)}")
    check("Amazon Web Services" in koala_names, "konfetti-koala names AWS")
    check("Cloudflare" in koala_names, "konfetti-koala names Cloudflare")
    check("SendGrid" in koala_names, "konfetti-koala names SendGrid")
    check("Mode" in koala_names, "konfetti-koala names Mode")
    check("amazon-web-services" in koala_slugs, "konfetti-koala AWS uses the Amazon Web Services file")
    check("cloudflare" in koala_slugs, "konfetti-koala Cloudflare uses the Cloudflare file")
    check("twilio" in koala_slugs, "konfetti-koala SendGrid uses the Twilio file")
    check("mode" not in by_pub, "konfetti-koala does not invent a Mode dossier")
    check("dpa" not in ((by_enr["kombo-technologies"].get("links") or {})), "Kombo PDF DPA stays off file")
    check(not (by_pub["litmus"].get("processors") or []), "Litmus names no parent-company processors")
    # Prior cut: first-party Completeness DPA on Artie, Discourse, Pluralsight.
    # Brightcove first-party HTML list. Bending Spoons parent-affiliate row
    # stays unread. Cloudfront / Elastic Search / Google Ad Manager alias
    # onto existing register slugs. PDF DPA and CSS-grid / JS-shell lists
    # stay open.
    check(
        instrument_url(by_pub["artie"], "dpa")
        == "https://www.artie.com/docs/legal/data-processing-addendum",
        "artie DPA is first-party HTML",
    )
    check((by_pub["artie"].get("file") or {}).get("dpa") == 20, "artie DPA prints")
    check(not (by_pub["artie"].get("processors") or []), "artie portal list stays unread")
    check(
        instrument_url(by_pub["discourse"], "dpa")
        == "https://www.discourse.org/data-processing-addendum",
        "discourse DPA is first-party HTML",
    )
    check((by_pub["discourse"].get("file") or {}).get("dpa") == 20, "discourse DPA prints")
    check(
        instrument_url(by_pub["pluralsight"], "dpa") == "https://www.pluralsight.com/terms/dpa",
        "pluralsight DPA is first-party HTML",
    )
    check((by_pub["pluralsight"].get("file") or {}).get("dpa") == 20, "pluralsight DPA prints")
    check(not (by_pub["pluralsight"].get("processors") or []), "pluralsight JS-shell list stays unread")
    bc_names = [p.get("name") for p in (by_pub["brightcove"].get("processors") or [])]
    bc_slugs = [p.get("slug") for p in (by_pub["brightcove"].get("processors") or [])]
    check(
        instrument_url(by_pub["brightcove"], "subprocessors")
        == "https://www.brightcove.com/legal/services-subprocessors",
        "brightcove list URL is first-party HTML",
    )
    check((by_pub["brightcove"].get("file") or {}).get("subprocessors") == 20, "brightcove processors print")
    check(len(bc_names) == 31, f"brightcove printed 31 named processors, got {len(bc_names)}")
    check("Amazon Web Services" in bc_names, "brightcove names AWS")
    check("Cloudfront" in bc_names, "brightcove names Cloudfront")
    check("Elastic Search" in bc_names, "brightcove names Elastic Search")
    check("Google Ad Manager" in bc_names, "brightcove names Google Ad Manager")
    check("Google Cloud Platform" in bc_names, "brightcove names Google Cloud Platform")
    check("MessageBird (Pusher)" in bc_names, "brightcove names MessageBird (Pusher)")
    check("Bending Spoons and its affiliates" not in bc_names, "brightcove parent-affiliate stays off file")
    check("amazon-web-services" in bc_slugs, "brightcove Cloudfront uses the Amazon Web Services file")
    check("elastic" in bc_slugs, "brightcove Elastic Search uses the Elastic file")
    check("google" in bc_slugs, "brightcove Google Ad Manager uses the Google file")
    check("messagebird" in bc_slugs, "brightcove MessageBird uses the MessageBird file")
    check("mongodb" in bc_slugs, "brightcove MongoDB / Atlas uses the MongoDB file")
    check("openai" in bc_slugs, "brightcove OpenAI Ireland uses the OpenAI file")
    check("castlabs" not in by_pub, "brightcove does not invent a CastLabs dossier")
    check("keen-io" not in by_pub, "brightcove does not invent a Keen.io dossier")
    check("last9" not in by_pub, "brightcove does not invent a Last9 dossier")
    check(by_pub["wowza"].get("domain") == "wowza.com", "brightcove Wowza uses the existing Wowza file")
    check("pigeonlab" not in by_pub, "brightcove does not invent a PigeonLab dossier")
    check("bending-spoons-and-its-affiliates" not in by_pub, "brightcove does not invent a Bending Spoons affiliates dossier")
    # Prior cut: first-party HTML lists. Combined / unnamed / parent / PDF rows
    # stay unread. Same-company leftovers alias onto existing register slugs.
    datazoo_names = [p.get("name") for p in (by_pub["data-zoo"].get("processors") or [])]
    datazoo_slugs = [p.get("slug") for p in (by_pub["data-zoo"].get("processors") or [])]
    check(
        instrument_url(by_pub["data-zoo"], "subprocessors")
        == "https://datazoo.com/policy/data-sub-processor-list",
        "data-zoo list URL is the first-party policy page",
    )
    check((by_pub["data-zoo"].get("file") or {}).get("subprocessors") == 20, "data-zoo processors print")
    check(len(datazoo_names) == 16, f"data-zoo printed 16 named processors, got {len(datazoo_names)}")
    check("Aha!" in datazoo_names, "data-zoo names Aha!")
    check("Google Cloud Platform" in datazoo_names, "data-zoo names Google Cloud Platform")
    check("Microsoft Office" in datazoo_names, "data-zoo names Microsoft Office")
    check("Vanta" not in datazoo_names, "data-zoo portal vendor Vanta stays off file")
    check("google" in datazoo_slugs, "data-zoo GCP uses the Google file")
    check("microsoft" in datazoo_slugs, "data-zoo Microsoft Office uses the Microsoft file")
    check("sentry" in datazoo_slugs, "data-zoo Sentry uses the Sentry file")
    check(by_pub["crushftp"].get("domain") == "crushftp.com", "data-zoo CrushFTP uses the existing CrushFTP file")
    check("voyager" not in by_pub, "data-zoo does not invent a Voyager dossier")
    check("voyager" not in by_enr, "voyager stays a domain-less leftover after the wrong-company revert")
    check(
        by_pub["employment-hero"].get("domain") == "employmenthero.com",
        "data-zoo Employment Hero uses the existing Employment Hero file",
    )
    ht_names = [p.get("name") for p in (by_pub["hightouch"].get("processors") or [])]
    ht_slugs = [p.get("slug") for p in (by_pub["hightouch"].get("processors") or [])]
    check(
        instrument_url(by_pub["hightouch"], "subprocessors") == "https://hightouch.com/subprocessors",
        "hightouch list URL is first-party HTML",
    )
    check((by_pub["hightouch"].get("file") or {}).get("subprocessors") == 20, "hightouch processors print")
    check(len(ht_names) == 14, f"hightouch printed 14 named processors, got {len(ht_names)}")
    check("Amazon Web Services, Inc" in ht_names, "hightouch names AWS")
    check("HotJar, Ltd" in ht_names, "hightouch names HotJar")
    check("amazon-web-services" in ht_slugs, "hightouch AWS uses the Amazon Web Services file")
    check("contentsquare" in ht_slugs, "hightouch HotJar uses the Contentsquare file")
    check("chili-piper" not in by_pub, "hightouch does not invent a Chili Piper dossier")
    plivo_names = [p.get("name") for p in (by_pub["plivo"].get("processors") or [])]
    plivo_slugs = [p.get("slug") for p in (by_pub["plivo"].get("processors") or [])]
    check(
        instrument_url(by_pub["plivo"], "subprocessors") == "https://www.plivo.com/legal/subprocessors/",
        "plivo list URL is first-party HTML",
    )
    check((by_pub["plivo"].get("file") or {}).get("subprocessors") == 20, "plivo processors print")
    check(len(plivo_names) == 31, f"plivo printed 31 named processors, got {len(plivo_names)}")
    check("Open AI" in plivo_names, "plivo names Open AI")
    check("openai" in plivo_slugs, "plivo Open AI uses the OpenAI file")
    check("linkedin" in plivo_slugs, "plivo LinkedIn Sales Navigator uses the LinkedIn file")
    check("Grok, Perplexity" not in plivo_names, "plivo combined Grok/Perplexity stays off file")
    check("PunHub" not in plivo_names, "plivo PunHub stays off file")
    check("punhub" not in by_pub, "plivo does not invent a PunHub dossier")
    sr_names = [p.get("name") for p in (by_pub["smartrecruiters"].get("processors") or [])]
    sr_slugs = [p.get("slug") for p in (by_pub["smartrecruiters"].get("processors") or [])]
    check(
        instrument_url(by_pub["smartrecruiters"], "subprocessors")
        == "https://www.smartrecruiters.com/legal/subprocessors/",
        "smartrecruiters list URL is first-party HTML",
    )
    check((by_pub["smartrecruiters"].get("file") or {}).get("subprocessors") == 20, "smartrecruiters processors print")
    check(len(sr_names) == 41, f"smartrecruiters printed 41 named processors, got {len(sr_names)}")
    check("SendGrid Inc" in sr_names, "smartrecruiters names SendGrid")
    check("twilio" in sr_slugs, "smartrecruiters SendGrid uses the Twilio file")
    check("microsoft" in sr_slugs, "smartrecruiters Microsoft Ireland uses the Microsoft file")
    check("deepl" in sr_slugs, "smartrecruiters DeepL SE uses the DeepL file")
    check("dispatch" not in by_pub, "smartrecruiters does not invent a Dispatch dossier")
    sms_names = [p.get("name") for p in (by_pub["sms-magic"].get("processors") or [])]
    sms_slugs = [p.get("slug") for p in (by_pub["sms-magic"].get("processors") or [])]
    check(
        instrument_url(by_pub["sms-magic"], "subprocessors")
        == "https://trust.sms-magic.com/subprocessors/",
        "sms-magic list URL is the first-party trust page",
    )
    check((by_pub["sms-magic"].get("file") or {}).get("subprocessors") == 20, "sms-magic processors print")
    check(len(sms_names) == 17, f"sms-magic printed 17 named processors, got {len(sms_names)}")
    check("Fresh Desk" in sms_names, "sms-magic names Fresh Desk")
    check("Pardot" in sms_names, "sms-magic names Pardot")
    check("Quick Books" in sms_names, "sms-magic names Quick Books")
    check("freshworks" in sms_slugs, "sms-magic Fresh Desk uses the Freshworks file")
    check("salesforce" in sms_slugs, "sms-magic Pardot uses the Salesforce file")
    check("intuit" in sms_slugs, "sms-magic Quick Books uses the Intuit file")
    check("Telecom Partners (Aus)" not in sms_names, "sms-magic unnamed telecom rows stay off file")
    check("match-my-email" not in by_pub, "sms-magic does not invent a Match My Email dossier")
    check("aircall" not in by_pub, "sms-magic does not invent an Aircall dossier")
    check("aircall" not in by_enr, "aircall stays a domain-less leftover after the wrong-company revert")
    # Prior cut: Accurx first-party support-article table. DPA annex headings
    # stay unread. Azure / SendGrid / TeamViewer UK alias onto existing rows.
    accurx_names = [p.get("name") for p in (by_pub["accurx"].get("processors") or [])]
    accurx_slugs = [p.get("slug") for p in (by_pub["accurx"].get("processors") or [])]
    check(
        instrument_url(by_pub["accurx"], "subprocessors")
        == "https://support.accurx.com/en/articles/768787-privacy-security-accurx-sub-processors",
        "accurx list URL is the first-party support article",
    )
    check((by_pub["accurx"].get("file") or {}).get("subprocessors") == 20, "accurx processors print")
    check(len(accurx_names) == 13, f"accurx printed 13 named processors, got {len(accurx_names)}")
    check("Tandem Health AB" in accurx_names, "accurx names Tandem Health AB")
    check("Microsoft Azure" in accurx_names, "accurx names Microsoft Azure")
    check("Sendgrid Inc" in accurx_names, "accurx names Sendgrid Inc")
    check("TeamViewer UK Ltd" in accurx_names, "accurx names TeamViewer UK Ltd")
    check("Service category" not in accurx_names, "accurx DPA Service category stays off file")
    check("Security Measure" not in accurx_names, "accurx DPA Security Measure stays off file")
    check("Core Services" not in accurx_names, "accurx DPA Core Services stays off file")
    check("microsoft" in accurx_slugs, "accurx Azure uses the Microsoft file")
    check("twilio" in accurx_slugs, "accurx Sendgrid uses the Twilio file")
    check("teamviewer" in accurx_slugs, "accurx TeamViewer UK uses the TeamViewer file")
    check("intercom" in accurx_slugs, "accurx Intercom uses the Intercom file")
    check("google" in accurx_slugs, "accurx Google LLC uses the Google file")
    check("tandem-health" not in by_pub, "accurx does not invent a Tandem Health dossier")
    check("whereby" not in by_pub, "accurx does not invent a Whereby dossier")
    check("aircall-sas" not in by_pub, "accurx does not invent an Aircall dossier")
    accurx_html = (ROOT / "site" / "c" / "accurx.html").read_text(encoding="utf-8")
    check(
        "https://support.accurx.com/en/articles/768787-privacy-security-accurx-sub-processors" in accurx_html,
        "accurx dossier cites the support-article list",
    )
    check("./microsoft.html" in accurx_html, "accurx Azure cross-links to Microsoft")
    check("./twilio.html" in accurx_html, "accurx Sendgrid cross-links to Twilio")
    check("./teamviewer.html" in accurx_html, "accurx TeamViewer UK cross-links to TeamViewer")
    check("Service category" not in accurx_html, "accurx dossier does not print DPA Service category")
    check("Security Measure" not in accurx_html, "accurx dossier does not print DPA Security Measure")
    # PR 269 filings stay on file. Browserbase / Tableau review drops stay unread.
    check(len(by_pub["contentsquare"].get("processors") or []) == 24, "contentsquare 24 names stay")
    check(len(by_pub["uploadcare"].get("processors") or []) == 25, "uploadcare 25 names stay")
    check(len(by_pub["lob-com"].get("processors") or []) == 37, "lob-com 37 names print")
    check((by_pub["lob-com"].get("file") or {}).get("subprocessors") == 20, "lob-com processors print")
    check(len(by_pub["productboard"].get("processors") or []) == 15, "productboard 15 names print")
    check((by_pub["productboard"].get("file") or {}).get("subprocessors") == 20, "productboard processors print")
    check(not (by_pub["smarsh"].get("processors") or []), "smarsh named processors stay unread")
    check((by_pub["smarsh"].get("file") or {}).get("subprocessors") == 10, "smarsh Completeness is not bumped")
    lob_html = (ROOT / "site" / "c" / "lob-com.html").read_text(encoding="utf-8")
    check("./mailchimp.html" in lob_html, "lob Rocket Science Group cross-links to Mailchimp")
    check("./shutterfly.html" in lob_html, "lob Shutterfly cross-links to Shutterfly")
    pb_html = (ROOT / "site" / "c" / "productboard.html").read_text(encoding="utf-8")
    check("./twilio.html" in pb_html, "productboard SendGrid cross-links to Twilio")
    check("./foundry-labs.html" in pb_html, "productboard FoundryLabs cross-links to Foundry Labs")
    check("./google.html" in pb_html, "productboard Google Vertex AI cross-links to Google")
    sm_html = (ROOT / "site" / "c" / "smarsh.html").read_text(encoding="utf-8")
    check("Named processors filed from a first-party list" not in sm_html, "smarsh clerk line is not a named-list fill")
    check("410 Terry Ave" not in sm_html, "smarsh does not print the unread Cloudflare-wall names")
    cloud_html = (ROOT / "site" / "c" / "84codes-cloudamqp.html").read_text(encoding="utf-8")
    check(">Topic<" not in cloud_html, "CloudAMQP does not print DPA Topic as a processor")
    check("Retention period" not in cloud_html, "CloudAMQP does not print Retention period")
    # PR 267 filings stay on file. LastPass / Recurly / Segment review drops stay unread.
    check(len(by_pub["help-scout"].get("processors") or []) == 20, "help-scout 20 names stay")
    check(len(by_pub["shortcut-software"].get("processors") or []) == 33, "shortcut 33 names stay")
    check(len(by_pub["wingify"].get("processors") or []) == 6, "wingify 6 names stay")
    check(len(by_pub["wrike"].get("processors") or []) == 21, "wrike 21 names stay")
    check("dpa" not in ((by_enr["lastpass"].get("links") or {})), "LastPass JS-shell DPA stays off file")
    check("dpa" not in ((by_enr["recurly-com"].get("links") or {})), "Recurly Marketo PDF DPA stays off file")
    check(not (by_pub["segment"].get("processors") or []), "Segment names no processors")
    check(
        (by_enr["segment"].get("links") or {}).get("subprocessors")
        == "https://www.twilio.com/en-us/legal/sub-processors",
        "Segment stored list URL stays the Twilio page, names stay unread",
    )
    help_html = (ROOT / "site" / "c" / "help-scout.html").read_text(encoding="utf-8")
    check("./pusher.html" in help_html, "help-scout Pusher.io cross-links to Pusher")
    check("./fivetran.html" in help_html, "help-scout Census cross-links to Fivetran")
    short_html = (ROOT / "site" / "c" / "shortcut-software.html").read_text(encoding="utf-8")
    check("./ketch.html" in short_html, "shortcut Ketch Kloud cross-links to Ketch")
    check("./plain.html" in short_html, "shortcut Not Just Tickets cross-links to Plain")
    wrike_html = (ROOT / "site" / "c" / "wrike.html").read_text(encoding="utf-8")
    check("./maestroqa.html" in wrike_html, "wrike Adtrib/MaestroQA cross-links to MaestroQA")
    check("./ada.html" in wrike_html, "wrike Ada Support cross-links to Ada")
    # PR 266 filings stay on file. Modal / SurveySparrow DPA annex drops stay unread.
    check(len(by_pub["coralogix"].get("processors") or []) == 13, "coralogix 13 names stay")
    check(len(by_pub["lambdatest"].get("processors") or []) == 34, "lambdatest 34 names stay")
    check(len(by_pub["postmark"].get("processors") or []) == 2, "postmark 2 names stay")
    check(len(by_pub["turbopuffer"].get("processors") or []) == 17, "turbopuffer 17 names stay")
    check(not (by_pub["modal"].get("processors") or []), "Modal names no processors")
    check(
        "subprocessors" not in ((by_enr["modal"].get("links") or {})),
        "Modal links.subprocessors stays off the DPA URL",
    )
    check(not (by_pub["surveysparrow"].get("processors") or []), "SurveySparrow names no processors")
    check(
        (by_enr["surveysparrow"].get("links") or {}).get("dpa") == "https://surveysparrow.com/legal/dpa/",
        "SurveySparrow DPA stays on file",
    )
    check(
        "subprocessors" not in ((by_enr["surveysparrow"].get("links") or {})),
        "SurveySparrow links.subprocessors stays off the DPA URL",
    )
    # PR 265 filings stay on file. CloudAMQP DPA annex drop stays unread.
    check(len(by_pub["apideck"].get("processors") or []) == 11, "apideck 11 names stay")
    check("fathom-analytics" not in by_pub, "apideck does not invent a Fathom Analytics dossier")
    check("fathom-analytics" not in by_enr, "fathom-analytics stays a domain-less leftover after the wrong-company revert")
    check(len(by_pub["client-success"].get("processors") or []) == 10, "client-success 10 names stay")
    check(len(by_pub["forethought-technologies"].get("processors") or []) == 21, "forethought 21 names stay")
    check(len(by_pub["jasper-ai"].get("processors") or []) == 31, "jasper 31 names stay")
    check("maxio" not in by_pub, "jasper does not invent a Maxio dossier")
    check("maxio" not in by_enr, "maxio stays a domain-less leftover after the wrong-company revert")
    leftover_nodes = {n.get("id"): n for n in (wires.get("nodes") or [])}
    for slug, bad_domain in (
        ("maxio", "maxionwheels.com"),
        ("aircall", "aircall.se"),
        ("voyager", "voyager.nz"),
        ("fathom-analytics", "fathom.video"),
    ):
        node = leftover_nodes.get(slug) or {}
        check(node, f"{slug} leftover graph node stays")
        check(not (node.get("domain") or ""), f"{slug} leftover stays domain-less, got {node.get('domain')!r}")
        check(bad_domain not in (node.get("domain") or ""), f"{slug} leftover does not keep {bad_domain}")
        check(not node.get("in_register"), f"{slug} leftover stays off the register")
        check(not (ROOT / "site" / "c" / f"{slug}.html").exists(), f"{slug} dossier page is gone")
    datazoo_html = (ROOT / "site" / "c" / "data-zoo.html").read_text(encoding="utf-8")
    sms_html = (ROOT / "site" / "c" / "sms-magic.html").read_text(encoding="utf-8")
    jasper_html = (ROOT / "site" / "c" / "jasper-ai.html").read_text(encoding="utf-8")
    apideck_html = (ROOT / "site" / "c" / "apideck.html").read_text(encoding="utf-8")
    check('../graph.html#p=voyager">Voyager' in datazoo_html, "data-zoo Voyager stays a leftover map node")
    check("./voyager.html" not in datazoo_html, "data-zoo does not link a Voyager dossier")
    check("voyager.nz" not in datazoo_html, "data-zoo does not cite voyager.nz")
    check('../graph.html#p=aircall">Aircall' in sms_html, "sms-magic Aircall stays a leftover map node")
    check("./aircall.html" not in sms_html, "sms-magic does not link an Aircall dossier")
    check("aircall.se" not in sms_html, "sms-magic does not cite aircall.se")
    check('../graph.html#p=maxio">Maxio' in jasper_html, "jasper Maxio stays a leftover map node")
    check("./maxio.html" not in jasper_html, "jasper does not link a Maxio dossier")
    check("maxionwheels.com" not in jasper_html, "jasper does not cite maxionwheels.com")
    check('../graph.html#p=fathom-analytics">Fathom Analytics, Inc' in apideck_html, "apideck Fathom Analytics stays a leftover map node")
    check("./fathom-analytics.html" not in apideck_html, "apideck does not link a Fathom Analytics dossier")
    check("fathom.video" not in apideck_html, "apideck does not cite fathom.video")
    check("fathom.ai" not in apideck_html, "apideck does not cite fathom.ai")
    check(len(by_pub["liveblocks"].get("processors") or []) == 14, "liveblocks 14 names stay")
    check(len(by_pub["rollbar"].get("processors") or []) == 14, "rollbar 14 names stay")
    check(len(by_pub["sigma"].get("processors") or []) == 20, "sigma 20 names stay")
    check(len(by_pub["synadia-cloud"].get("processors") or []) == 13, "synadia 13 names stay")
    check(not (by_pub["84codes-cloudamqp"].get("processors") or []), "CloudAMQP names no processors")
    modal_html = (ROOT / "site" / "c" / "modal.html").read_text(encoding="utf-8")
    check("Technical and Organizational Security Measure" not in modal_html, "Modal does not print DPA TOM headings")
    check("Measures of pseudonymisation" not in modal_html, "Modal does not print SCC annex measures")
    # PR 263 filings stay on file. Annex/cookie/data-category drops stay unread.
    check(len(by_pub["clazar"].get("processors") or []) == 17, "clazar 17 names stay")
    check(len(by_pub["daily"].get("processors") or []) == 22, "daily 22 names stay")
    check(len(by_pub["front"].get("processors") or []) == 9, "front 9 names stay")
    check(len(by_pub["sentry"].get("processors") or []) == 7, "sentry 7 names stay")
    check(len(by_pub["stream-io"].get("processors") or []) == 15, "stream-io 15 names stay")
    for slug in ("arkose-labs", "qualified-com", "incident-io", "mapbox"):
        check(not (by_pub[slug].get("processors") or []), f"{slug} names no processors")
        check((by_pub[slug].get("file") or {}).get("subprocessors") in (0, 10, False, None), f"{slug} processors glyph is not printed")
    check("subprocessors" not in ((by_enr["arkose-labs"].get("links") or {})), "arkose-labs links.subprocessors stays off file")
    check(
        (by_enr["incident-io"].get("links") or {}).get("subprocessors")
        == "https://incident.io/legal/sub-processors",
        "incident-io list URL stays the first-party sub-processors page",
    )
    check(
        (by_enr["qualified-com"].get("links") or {}).get("subprocessors")
        == "https://www.qualified.com/legal/subprocessors",
        "qualified-com stored list URL stays, names stay unread",
    )
    check(
        (by_enr["mapbox"].get("links") or {}).get("subprocessors")
        == "https://www.mapbox.com/legal/subprocessors",
        "mapbox stored list URL stays, names stay unread",
    )
    arkose_html = (ROOT / "site" / "c" / "arkose-labs.html").read_text(encoding="utf-8")
    check("Data Subjects" not in arkose_html, "arkose-labs does not print SCC annex headings")
    check("UK GDPR" not in arkose_html, "arkose-labs does not print UK GDPR as a processor")
    q_html = (ROOT / "site" / "c" / "qualified-com.html").read_text(encoding="utf-8")
    check("qualified_session" not in q_html, "qualified-com does not print cookie names")
    check("my_onetrust_groups" not in q_html, "qualified-com does not print OneTrust cookie rows")
    inc_html = (ROOT / "site" / "c" / "incident-io.html").read_text(encoding="utf-8")
    check("company-number-or-equivalent" not in inc_html, "incident-io does not print DPA annex headings")
    check("Role (controller/processor)" not in inc_html, "incident-io does not print Role heading")
    mapbox_html = (ROOT / "site" / "c" / "mapbox.html").read_text(encoding="utf-8")
    check("Geolocation Data" not in mapbox_html, "mapbox does not print data-category rows")
    check("Commercial Information" not in mapbox_html, "mapbox does not print Commercial Information")
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
    check((by_pub["arsys"].get("file") or {}).get("page") == 20, "arsys Official page prints")
    check(sum(int((by_pub["arsys"].get("file") or {}).get(k) or 0) for k in ("page", "marks", "dpa", "subprocessors", "years")) == 40, "arsys Completeness is page + marks")
    check(by_pub["arsys"].get("found") is True, "arsys Official page is on file")
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
    check((by_pub["namely"].get("file") or {}).get("page") == 20, "namely Official page prints")
    check((by_pub["namely"].get("file") or {}).get("marks") == 10, "namely marks stay dotted")
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

    # This cut: Contentsquare first-party affiliate + third-party table.
    # Content Square / Hotjar / Loris group rows stay off file (same company).
    cs_names = [p.get("name") for p in (by_pub["contentsquare"].get("processors") or [])]
    cs_slugs = [p.get("slug") for p in (by_pub["contentsquare"].get("processors") or [])]
    check(
        instrument_url(by_pub["contentsquare"], "subprocessors")
        == "https://contentsquare.com/privacy-center/subprocessors/",
        "contentsquare list URL stays the first-party privacy-center table",
    )
    check((by_pub["contentsquare"].get("file") or {}).get("subprocessors") == 20, "contentsquare list printed")
    check((by_pub["contentsquare"].get("file") or {}).get("dpa") in (0, False, None), "contentsquare DPA stays open")
    check("Atlassian Pty Ltd (Jira)" in cs_names, "contentsquare names Atlassian Pty Ltd (Jira)")
    check("Amazon Web Services, Inc" in cs_names, "contentsquare names Amazon Web Services, Inc")
    check("Microsoft Azure" in cs_names, "contentsquare names Microsoft Azure")
    check("Ada Support, Inc" in cs_names, "contentsquare names Ada Support, Inc")
    check("OpenAI OpCo, LLC" in cs_names, "contentsquare names OpenAI OpCo, LLC")
    check("Turbopuffer Inc" in cs_names, "contentsquare names Turbopuffer Inc")
    check("Content Square SAS" not in cs_names, "contentsquare self-affiliate Content Square SAS stays off file")
    check("Hotjar Germany GmbH" not in cs_names, "contentsquare Hotjar group row stays off file")
    check("Loris Technologies, Ltd" not in cs_names, "contentsquare Loris group row stays off file")
    check(len(cs_names) == 24, f"contentsquare printed 24 third-party names, got {len(cs_names)}")
    check("amazon-web-services" in cs_slugs, "contentsquare AWS uses the Amazon Web Services file")
    check("microsoft" in cs_slugs, "contentsquare Azure uses the Microsoft file")
    check("ada" in cs_slugs, "contentsquare Ada Support uses the Ada file")
    check("content-square-sas" not in cs_slugs, "contentsquare does not invent a Content Square dossier")
    check("hotjar-germany" not in cs_slugs, "contentsquare does not invent a Hotjar Germany dossier")
    cs_html = (ROOT / "site" / "c" / "contentsquare.html").read_text(encoding="utf-8")
    check(
        "https://contentsquare.com/privacy-center/subprocessors/" in cs_html,
        "contentsquare dossier keeps the list URL",
    )
    check("./amazon-web-services.html" in cs_html, "contentsquare AWS cross-links to Amazon Web Services")
    check("./microsoft.html" in cs_html, "contentsquare Azure cross-links to Microsoft")
    check("./ada.html" in cs_html, "contentsquare Ada Support cross-links to Ada")
    check("Content Square SAS" not in cs_html, "contentsquare dossier does not print Content Square SAS")
    check("Hotjar Germany" not in cs_html, "contentsquare dossier does not print Hotjar Germany")

    # This cut: Uploadcare first-party /about/sub-processors/ table. Portal
    # catalog URL upgraded to printed HTML. Product cells alias to existing files.
    uc_names = [p.get("name") for p in (by_pub["uploadcare"].get("processors") or [])]
    uc_slugs = [p.get("slug") for p in (by_pub["uploadcare"].get("processors") or [])]
    check(
        instrument_url(by_pub["uploadcare"], "subprocessors")
        == "https://uploadcare.com/about/sub-processors/",
        "uploadcare list URL is the first-party printed table",
    )
    check((by_pub["uploadcare"].get("file") or {}).get("subprocessors") == 20, "uploadcare list printed")
    check((by_pub["uploadcare"].get("file") or {}).get("dpa") in (0, False, None), "uploadcare DPA stays open")
    check("Amazon Web Services" in uc_names, "uploadcare names Amazon Web Services")
    check("Zencoder" in uc_names, "uploadcare names Zencoder")
    check("Facebook for Business" in uc_names, "uploadcare names Facebook for Business")
    check("Google Cloud" in uc_names, "uploadcare names Google Cloud")
    check("Google Workspace" in uc_names, "uploadcare names Google Workspace")
    check("Google Marketing Platform" in uc_names, "uploadcare names Google Marketing Platform")
    check("Microsoft Advertising" in uc_names, "uploadcare names Microsoft Advertising")
    check("Talend" in uc_names, "uploadcare names Talend")
    check(len(uc_names) == 25, f"uploadcare printed 25 named processors, got {len(uc_names)}")
    check("amazon-web-services" in uc_slugs, "uploadcare AWS uses the Amazon Web Services file")
    check("brightcove" in uc_slugs, "uploadcare Zencoder uses the Brightcove file")
    check("meta" in uc_slugs, "uploadcare Facebook for Business uses the Meta file")
    check("google" in uc_slugs, "uploadcare Google cells use the Google file")
    check("microsoft" in uc_slugs, "uploadcare Microsoft Advertising uses the Microsoft file")
    check("qlik" in uc_slugs, "uploadcare Talend uses the Qlik file")
    check("facebook-for-business" not in uc_slugs, "uploadcare does not invent a Facebook for Business dossier")
    check("talend" not in uc_slugs, "uploadcare does not invent a Talend dossier")
    check("kaleido" not in by_pub, "kaleido leftover does not invent a dossier")
    check("fern" not in by_pub, "fern leftover does not invent a dossier")
    # Expand on main promoted Zamzar / Mezmo from leftover nodes to silent
    # register rows. This cut does not invent a first-party file for them.
    check(by_pub["zamzar"].get("found") is False, "zamzar Official page stays open")
    check((by_pub["zamzar"].get("file") or {}).get("page") in (0, False, None), "zamzar Official page stays unread")
    check(by_pub["mezmo"].get("found") is False, "mezmo Official page stays open")
    check((by_pub["mezmo"].get("file") or {}).get("page") in (0, False, None), "mezmo Official page stays unread")
    uc_html = (ROOT / "site" / "c" / "uploadcare.html").read_text(encoding="utf-8")
    check("https://uploadcare.com/about/sub-processors/" in uc_html, "uploadcare dossier keeps the list URL")
    check("./amazon-web-services.html" in uc_html, "uploadcare AWS cross-links to Amazon Web Services")
    check("./brightcove.html" in uc_html, "uploadcare Zencoder cross-links to Brightcove")
    check("./meta.html" in uc_html, "uploadcare Facebook for Business cross-links to Meta")
    check("./google.html" in uc_html, "uploadcare Google cells cross-link to Google")
    check("./qlik.html" in uc_html, "uploadcare Talend cross-links to Qlik")
    check("trust.uploadcare.com/subprocessors" not in uc_html, "uploadcare dossier dropped the portal list URL")

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
            "software-mind",
        },
        f"branch processor slugs {branch_slugs}",
    )
    check("software-mind" in branch_slugs, "software-minds lands on the Software Mind file")
    check(None not in branch_slugs, "branch leftover Software Minds is gone")
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
    check("./software-mind.html\">Software Minds, Inc" in branch_html, "branch Software Minds cross-links to Software Mind")
    check("../graph.html#p=software-minds" not in branch_html, "software-minds is no longer a leftover map node")
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
    check(by_pub["ketch"].get("found") is True, "ketch Official page is on file")
    check(by_pub["ketch"].get("trust_url") == "https://trust.ketch.com", "ketch Official page is the Vanta trust portal")
    check(by_pub["ketch"].get("founded_year") == 2020, "ketch year is first-party foundingDate")
    check(by_pub["ketch"].get("founded_source") == "https://www.ketch.com/about", "ketch year source is /about")
    check((by_pub["ketch"].get("file") or {}).get("years") == 20, "ketch years print")
    check(by_pub["inkeep"].get("founded_year") == 2023, "inkeep year is first-party foundingDate")
    check(by_pub["inkeep"].get("founded_source") == "https://inkeep.com/about", "inkeep year source is /about")
    check((by_pub["inkeep"].get("file") or {}).get("years") == 20, "inkeep years print")
    check(instrument_url(by_pub["inkeep"], "dpa") in (None, ""), "inkeep DPA PDF stays unread")
    check(
        instrument_url(by_pub["spekit"], "dpa") == "https://www.spekit.com/legal/dpa",
        "spekit DPA is first-party HTML",
    )
    check((by_pub["spekit"].get("file") or {}).get("dpa") == 20, "spekit DPA prints")
    check(by_pub["spekit"].get("found") is False, "spekit Official page stays open")
    check(not by_pub["spekit"].get("trust_url"), "spekit has no invented Official page")
    check(by_pub["spekit"].get("founded_year") == 2018, "spekit year is first-party foundingDate")
    check(by_pub["spekit"].get("founded_source") == "https://www.spekit.com/about-us", "spekit year source is /about-us")
    check((by_pub["spekit"].get("file") or {}).get("years") == 20, "spekit years print")
    check(
        instrument_url(by_pub["tropic"], "subprocessors")
        == "https://www.tropicapp.io/legal/subprocessors",
        "tropic list is first-party HTML",
    )
    check((by_pub["tropic"].get("file") or {}).get("subprocessors") == 20, "tropic processors print")
    tropic_names = [p.get("name") for p in (by_pub["tropic"].get("processors") or [])]
    tropic_slugs = [p.get("slug") for p in (by_pub["tropic"].get("processors") or [])]
    tropic_ids = [p.get("id") for p in (by_pub["tropic"].get("processors") or [])]
    check("Amazon Web Services" in tropic_names, "tropic names AWS")
    check("Google Cloud Platform" in tropic_names, "tropic names GCP")
    check("Omni" in tropic_names, "tropic names Omni")
    check("amazon-web-services" in tropic_slugs, "tropic AWS uses the existing file")
    check("google" in tropic_slugs, "tropic GCP uses the Google file")
    check("aws" not in tropic_ids, "tropic does not keep a raw aws wire id")
    check("gcp" not in tropic_ids, "tropic does not keep a raw gcp wire id")
    check("omni-analytics" in tropic_slugs, "tropic Omni uses the existing Omni Analytics file")
    check("omni" not in tropic_ids, "tropic does not keep a raw omni wire id")
    check("omni" not in tropic_slugs, "tropic does not invent a second Omni dossier")
    check(len(tropic_names) == 16, f"tropic printed 16 named processors, got {len(tropic_names)}")
    tropic_html = (ROOT / "site" / "c" / "tropic.html").read_text(encoding="utf-8")
    check("<h1>Tropic</h1>" in tropic_html, "tropic dossier is its own file")
    check("https://www.tropicapp.io/legal/subprocessors" in tropic_html, "tropic dossier cites the list")
    check("./amazon-web-services.html\">Amazon Web Services" in tropic_html, "tropic AWS cross-links")
    check("./google.html\">Google Cloud Platform" in tropic_html, "tropic GCP cross-links")
    check("./omni-analytics.html\">Omni" in tropic_html, "tropic Omni cross-links to Omni Analytics")
    check("../graph.html#p=omni" not in tropic_html, "tropic Omni is no longer a leftover map node")
    check(
        instrument_url(by_pub["kickbox"], "subprocessors")
        == "https://docs.kickbox.com/docs/subprocessors",
        "kickbox list is first-party docs HTML",
    )
    check((by_pub["kickbox"].get("file") or {}).get("subprocessors") == 20, "kickbox processors print")
    kickbox_names = [p.get("name") for p in (by_pub["kickbox"].get("processors") or [])]
    kickbox_slugs = [p.get("slug") for p in (by_pub["kickbox"].get("processors") or [])]
    kickbox_ids = [p.get("id") for p in (by_pub["kickbox"].get("processors") or [])]
    check("Stripe" in kickbox_names, "kickbox names Stripe")
    check("Sift Science" in kickbox_names, "kickbox names Sift Science")
    check("Amazon AWS" in kickbox_names, "kickbox names Amazon AWS")
    check("sift" in kickbox_slugs, "kickbox Sift Science uses the existing Sift file")
    check("amazon-web-services" in kickbox_slugs, "kickbox AWS uses the existing file")
    check("sift-science" not in kickbox_ids, "kickbox does not keep a raw sift-science wire id")
    check("aws" not in kickbox_ids, "kickbox does not keep a raw aws wire id")
    check(by_pub["kickbox"].get("found") is True, "kickbox Official page is on file")
    check((by_pub["kickbox"].get("certs") or []) == [], "kickbox DPF / Vanta marks stay unread")
    kickbox_html = (ROOT / "site" / "c" / "kickbox.html").read_text(encoding="utf-8")
    check("<h1>Kickbox</h1>" in kickbox_html, "kickbox dossier is its own file")
    check("https://docs.kickbox.com/docs/subprocessors" in kickbox_html, "kickbox dossier cites the list")
    check("./sift.html\">Sift Science" in kickbox_html, "kickbox Sift Science cross-links to Sift")
    check("../graph.html#p=sift-science" not in kickbox_html, "kickbox Sift Science is no longer a leftover map node")
    check(
        instrument_url(by_pub["rootly"], "subprocessors")
        == "https://docs.rootly.com/configuration/subprocessors",
        "rootly list is first-party docs HTML",
    )
    check((by_pub["rootly"].get("file") or {}).get("subprocessors") == 20, "rootly processors print")
    rootly_names = [p.get("name") for p in (by_pub["rootly"].get("processors") or [])]
    rootly_slugs = [p.get("slug") for p in (by_pub["rootly"].get("processors") or [])]
    rootly_ids = [p.get("id") for p in (by_pub["rootly"].get("processors") or [])]
    check("Amazon Web Services" in rootly_names, "rootly names AWS")
    check("Mailgun (Sinch AB)" in rootly_names, "rootly names Mailgun (Sinch AB)")
    check("Firebase Cloud Messaging" in rootly_names, "rootly names Firebase Cloud Messaging")
    check("ClickHouse Cloud" in rootly_names, "rootly names ClickHouse Cloud")
    check("AssemblyAI (via Recall.ai)" in rootly_names, "rootly names AssemblyAI")
    check("Apple Push Notification service" in rootly_names, "rootly names APNs")
    check("QuotaGuard" in rootly_names, "rootly names QuotaGuard")
    check("mailgun" in rootly_slugs, "rootly Mailgun uses the existing file")
    check("google" in rootly_slugs, "rootly Firebase uses the Google file")
    check("clickhouse" in rootly_slugs, "rootly ClickHouse Cloud uses the existing file")
    check("assemblyai" in rootly_slugs, "rootly AssemblyAI uses the existing file")
    check("apple" in rootly_slugs, "rootly APNs uses the Apple file")
    check("amazon-web-services" in rootly_slugs, "rootly AWS uses the existing file")
    check("quotaguard" in rootly_slugs, "rootly QuotaGuard uses the new file")
    check("mailgun-sinch" not in rootly_ids, "rootly does not keep a raw mailgun-sinch wire id")
    check("firebase-cloud-messaging" not in rootly_ids, "rootly does not keep a raw firebase wire id")
    check("clickhouse-cloud" not in rootly_ids, "rootly does not keep a raw clickhouse-cloud wire id")
    check("assemblyai-via-recall-ai" not in rootly_ids, "rootly does not keep a raw assemblyai-via wire id")
    check("apple-push-notification-service" not in rootly_ids, "rootly does not keep a raw APNs wire id")
    check("aws" not in rootly_ids, "rootly does not keep a raw aws wire id")
    check("sendgrid" not in rootly_ids, "rootly SendGrid lands on Twilio")
    check(len(rootly_names) == 19, f"rootly printed 19 named processors, got {len(rootly_names)}")
    check(by_pub["rootly"].get("found") is True, "rootly Official page is on file")
    check((by_pub["rootly"].get("certs") or []) == [], "rootly product-page marks stay unread")
    rootly_html = (ROOT / "site" / "c" / "rootly.html").read_text(encoding="utf-8")
    check("<h1>Rootly</h1>" in rootly_html, "rootly dossier is its own file")
    check("https://docs.rootly.com/configuration/subprocessors" in rootly_html, "rootly dossier cites the list")
    check("./mailgun.html\">Mailgun (Sinch AB)" in rootly_html, "rootly Mailgun cross-links")
    check("./google.html\">Firebase Cloud Messaging" in rootly_html, "rootly Firebase cross-links to Google")
    check("./clickhouse.html\">ClickHouse Cloud" in rootly_html, "rootly ClickHouse Cloud cross-links")
    check("./assemblyai.html\">AssemblyAI (via Recall.ai)" in rootly_html, "rootly AssemblyAI cross-links")
    check("./apple.html\">Apple Push Notification service" in rootly_html, "rootly APNs cross-links")
    check("./quotaguard.html\">QuotaGuard" in rootly_html, "rootly QuotaGuard cross-links to the new file")
    check("./pushy.html\">Pushy" in rootly_html, "rootly Pushy cross-links to the new file")
    check("./pganalyze-duboce-labs.html\">pganalyze (Duboce Labs, Inc.)" in rootly_html, "rootly pganalyze cross-links")
    check("./short-io.html\">Short.io" in rootly_html, "rootly Short.io cross-links")
    check("../graph.html#p=quotaguard" not in rootly_html, "rootly QuotaGuard is no longer a leftover map node")
    check("safebase" not in rootly_html.lower(), "rootly dossier does not name a portal vendor")
    check(by_pub["quotaguard"].get("domain") == "quotaguard.com", "quotaguard domain is first-party proven")
    check(by_pub["pushy"].get("domain") == "pushy.me", "pushy domain is first-party proven")
    check(by_pub["pganalyze-duboce-labs"].get("domain") == "pganalyze.com", "pganalyze domain is first-party proven")
    check(by_pub["short-io"].get("domain") == "short.io", "short-io domain is first-party proven")
    check(by_pub["quotaguard"].get("found") is True, "quotaguard Official page is on file")
    check(by_pub["pushy"].get("found") is False, "pushy Official page stays open")
    check((by_pub["quotaguard"].get("file") or {}).get("years") == 20, "quotaguard years print")
    check(
        instrument_url(by_pub["pushy"], "dpa") == "https://pushy.me/data-processing-addendum",
        "pushy DPA is first-party HTML",
    )
    check((by_pub["pushy"].get("file") or {}).get("dpa") == 20, "pushy DPA prints")
    pushy_html = (ROOT / "site" / "c" / "pushy.html").read_text(encoding="utf-8")
    check("https://pushy.me/data-processing-addendum" in pushy_html, "pushy dossier cites the DPA")
    check(by_pub["pganalyze-duboce-labs"].get("found") is True, "pganalyze Official page is /security")
    check(
        by_pub["pganalyze-duboce-labs"].get("trust_url") == "https://pganalyze.com/security",
        "pganalyze Official page URL is first-party security HTML",
    )
    check((by_pub["pganalyze-duboce-labs"].get("certs") or []) == [], "pganalyze AWS data-center marks stay unread")
    check((by_pub["pganalyze-duboce-labs"].get("file") or {}).get("page") == 20, "pganalyze page prints")
    pga_html = (ROOT / "site" / "c" / "pganalyze-duboce-labs.html").read_text(encoding="utf-8")
    check("https://pganalyze.com/security" in pga_html, "pganalyze dossier cites /security")
    check(
        instrument_url(by_pub["short-io"], "subprocessors") == "https://short.io/privacy",
        "short-io list is first-party privacy HTML",
    )
    check((by_pub["short-io"].get("file") or {}).get("subprocessors") == 20, "short-io processors print")
    short_names = [p.get("name") for p in (by_pub["short-io"].get("processors") or [])]
    short_slugs = [p.get("slug") for p in (by_pub["short-io"].get("processors") or [])]
    short_ids = [p.get("id") for p in (by_pub["short-io"].get("processors") or [])]
    check("Amazon Web Services" in short_names, "short-io names AWS")
    check("Google (Sign-In)" in short_names, "short-io names Google (Sign-In)")
    check("Google Ads" in short_names, "short-io names Google Ads")
    check("Google Web Risk" in short_names, "short-io names Google Web Risk")
    check("Google (Gemini)" in short_names, "short-io names Google (Gemini)")
    check("Hivelocity" in short_names, "short-io names Hivelocity")
    check("Telegram" in short_names, "short-io names Telegram")
    check("SURBL" in short_names, "short-io names SURBL")
    check("Let's Encrypt" in short_names, "short-io names Let's Encrypt")
    check("amazon-web-services" in short_slugs, "short-io AWS uses the existing file")
    check("google" in short_slugs, "short-io Google products use the Google file")
    check("hivelocity" in short_slugs, "short-io Hivelocity uses the new file")
    check("telegram" in short_slugs, "short-io Telegram uses the new file")
    check("surbl" in short_slugs, "short-io SURBL uses the new file")
    check("let-s-encrypt" in short_slugs, "short-io Let's Encrypt uses the new file")
    check("aws" not in short_ids, "short-io does not keep a raw aws wire id")
    check("google-sign-in" not in short_ids, "short-io does not keep a raw google-sign-in wire id")
    check("google-ads" not in short_ids, "short-io does not keep a raw google-ads wire id")
    check("google-web-risk" not in short_ids, "short-io does not keep a raw google-web-risk wire id")
    check("google-gemini" not in short_ids, "short-io does not keep a raw google-gemini wire id")
    check(by_pub["short-io"].get("found") is False, "short-io Official page stays open")
    check(not by_pub["short-io"].get("founded_year"), "short-io years stay open (2015 vs 2016)")
    short_html = (ROOT / "site" / "c" / "short-io.html").read_text(encoding="utf-8")
    check("https://short.io/privacy" in short_html, "short-io dossier cites the list")
    check("./google.html\">Google (Sign-In)" in short_html, "short-io Google Sign-In cross-links")
    check("./google.html\">Google Ads" in short_html, "short-io Google Ads cross-links")
    check("./hivelocity.html\">Hivelocity" in short_html, "short-io Hivelocity cross-links to the new file")
    check("./telegram.html\">Telegram" in short_html, "short-io Telegram cross-links to the new file")
    check("./surbl.html\">SURBL" in short_html, "short-io SURBL cross-links to the new file")
    check("./let-s-encrypt.html\">Let&#x27;s Encrypt" in short_html, "short-io Let's Encrypt cross-links to the new file")
    check(by_pub["hivelocity"].get("domain") == "hivelocity.net", "hivelocity domain is first-party proven")
    check(by_pub["telegram"].get("domain") == "telegram.org", "telegram domain is first-party proven")
    check(by_pub["surbl"].get("domain") == "surbl.org", "surbl domain is first-party proven")
    check(by_pub["let-s-encrypt"].get("domain") == "letsencrypt.org", "let-s-encrypt domain is first-party proven")
    check(by_pub["hivelocity"].get("found") is False, "hivelocity Official page stays open")
    check(by_pub["telegram"].get("found") is True, "telegram Official page is on file")

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

    check(
        instrument_url(by_pub["clari"], "dpa") == "https://www.clari.com/dpa/2026-02-10/",
        "clari DPA is first-party HTML",
    )
    check((by_pub["clari"].get("file") or {}).get("dpa") == 20, "clari DPA prints")
    check(not (by_pub["clari"].get("processors") or []), "clari named processors stay open")
    clari_html = (ROOT / "site" / "c" / "clari.html").read_text(encoding="utf-8")
    check("https://www.clari.com/dpa/2026-02-10/" in clari_html, "clari dossier cites the DPA")
    check(
        instrument_url(by_pub["supportlogic"], "dpa")
        == "https://www.supportlogic.com/data-processing-addendum/",
        "supportlogic DPA is first-party HTML",
    )
    check((by_pub["supportlogic"].get("file") or {}).get("dpa") == 20, "supportlogic DPA prints")
    check(not (by_pub["supportlogic"].get("processors") or []), "supportlogic named processors stay open")
    sl_html = (ROOT / "site" / "c" / "supportlogic.html").read_text(encoding="utf-8")
    check(
        "https://www.supportlogic.com/data-processing-addendum/" in sl_html,
        "supportlogic dossier cites the DPA",
    )
    check(
        instrument_url(by_pub["livekit"], "dpa")
        == "https://livekit.com/legal/data-processing-addendum",
        "livekit DPA is first-party HTML",
    )
    check(
        instrument_url(by_pub["livekit"], "subprocessors")
        == "https://livekit.com/legal/sub-processors",
        "livekit list is first-party HTML",
    )
    check((by_pub["livekit"].get("file") or {}).get("dpa") == 20, "livekit DPA prints")
    check((by_pub["livekit"].get("file") or {}).get("subprocessors") == 20, "livekit processors print")
    livekit_names = [p.get("name") for p in (by_pub["livekit"].get("processors") or [])]
    livekit_slugs = [p.get("slug") for p in (by_pub["livekit"].get("processors") or [])]
    livekit_ids = [p.get("id") for p in (by_pub["livekit"].get("processors") or [])]
    check("DigitalOcean" in livekit_names, "livekit names DigitalOcean")
    check("SpaceXAI" in livekit_names, "livekit names SpaceXAI")
    check("Cockroach Labs" in livekit_names, "livekit names Cockroach Labs")
    check("digitalocean" in livekit_slugs, "livekit DigitalOcean uses the existing file")
    check("spacexai" in livekit_ids, "livekit SpaceXAI stays a leftover wire id")
    check("xai" not in livekit_slugs, "livekit does not force-alias SpaceXAI to xAI")
    check(len(livekit_names) == 30, f"livekit printed 30 named processors, got {len(livekit_names)}")
    check(not by_pub["livekit"].get("founded_year"), "livekit years stay open")
    livekit_html = (ROOT / "site" / "c" / "livekit.html").read_text(encoding="utf-8")
    check("https://livekit.com/legal/data-processing-addendum" in livekit_html, "livekit dossier cites the DPA")
    check("https://livekit.com/legal/sub-processors" in livekit_html, "livekit dossier cites the list")
    check("../graph.html#p=spacexai\">SpaceXAI" in livekit_html, "livekit SpaceXAI stays a leftover map node")
    check("./xai.html\">SpaceXAI" not in livekit_html, "livekit does not send SpaceXAI to xAI")
    check("./cockroach-labs.html\">Cockroach Labs" in livekit_html, "livekit Cockroach Labs cross-links to the filed row")
    check("../graph.html#p=cockroach-labs" not in livekit_html, "livekit Cockroach Labs is no longer a leftover map node")
    check("./metabase.html\">Metabase" in livekit_html, "livekit Metabase cross-links to the filed row")
    check("./lightdash.html\">Lightdash" in livekit_html, "livekit Lightdash cross-links to the filed row")
    check("./loops.html\">Loops" in livekit_html, "livekit Loops cross-links to the filed row")
    check("./inworld.html\">Inworld" in livekit_html, "livekit Inworld cross-links to the filed row")
    check("./rime.html\">Rime" in livekit_html, "livekit Rime cross-links to the filed row")
    check(
        instrument_url(by_pub["retool"], "dpa") == "https://docs.retool.com/legal/dpa",
        "retool DPA is first-party docs HTML",
    )
    check(
        instrument_url(by_pub["retool"], "subprocessors")
        == "https://docs.retool.com/legal/subprocessors",
        "retool list is first-party docs HTML",
    )
    check((by_pub["retool"].get("file") or {}).get("dpa") == 20, "retool DPA prints")
    check((by_pub["retool"].get("file") or {}).get("subprocessors") == 20, "retool processors print")
    retool_names = [p.get("name") for p in (by_pub["retool"].get("processors") or [])]
    retool_slugs = [p.get("slug") for p in (by_pub["retool"].get("processors") or [])]
    retool_ids = [p.get("id") for p in (by_pub["retool"].get("processors") or [])]
    check("Amazon Web Services, Inc" in retool_names, "retool names AWS")
    check("Neon, Inc" in retool_names, "retool names Neon, Inc")
    check("Temporal Technologies, Inc" in retool_names, "retool names Temporal")
    check("amazon-web-services" in retool_slugs, "retool AWS uses the existing file")
    check("neon" in retool_slugs, "retool Neon uses the Neon file")
    check("databricks" not in retool_slugs, "retool Neon is not Databricks")
    check("temporal" in retool_slugs, "retool Temporal uses the existing file")
    check("tavily" in retool_slugs, "retool Tavily uses the existing file")
    check("aws" not in retool_ids, "retool does not keep a raw aws wire id")
    check("neon" not in retool_ids or "neon" in retool_slugs, "retool Neon wire lands on the neon row")
    check(len(retool_names) == 11, f"retool printed 11 named processors, got {len(retool_names)}")
    retool_html = (ROOT / "site" / "c" / "retool.html").read_text(encoding="utf-8")
    check("https://docs.retool.com/legal/dpa" in retool_html, "retool dossier cites the DPA")
    check("https://docs.retool.com/legal/subprocessors" in retool_html, "retool dossier cites the list")
    check("./amazon-web-services.html\">Amazon Web Services, Inc" in retool_html, "retool AWS cross-links")
    check("./neon.html\">Neon, Inc" in retool_html, "retool Neon cross-links to the Neon file")
    check("./databricks.html\">Neon, Inc" not in retool_html, "retool Neon does not cross-link to Databricks")
    check(by_pub["neon"]["domain"] == "neon.tech", "neon domain is neon.tech")
    check(by_pub["neon"].get("found") is True, "neon Official page is on file")
    check(
        sum(int((by_pub["neon"].get("file") or {}).get(k) or 0) for k in ("page", "marks", "dpa", "subprocessors", "years"))
        == 40,
        "neon Completeness is page + marks",
    )
    check("./temporal.html\">Temporal Technologies, Inc" in retool_html, "retool Temporal cross-links")
    check(
        instrument_url(by_pub["rocketlane"], "dpa")
        == "https://www.rocketlane.com/legal/data-processing-agreement",
        "rocketlane DPA is first-party HTML",
    )
    check(
        instrument_url(by_pub["rocketlane"], "subprocessors")
        == "https://www.rocketlane.com/legal/sub-processors",
        "rocketlane list is first-party HTML",
    )
    check((by_pub["rocketlane"].get("file") or {}).get("dpa") == 20, "rocketlane DPA prints")
    check((by_pub["rocketlane"].get("file") or {}).get("subprocessors") == 20, "rocketlane processors print")
    rocket_names = [p.get("name") for p in (by_pub["rocketlane"].get("processors") or [])]
    rocket_slugs = [p.get("slug") for p in (by_pub["rocketlane"].get("processors") or [])]
    rocket_ids = [p.get("id") for p in (by_pub["rocketlane"].get("processors") or [])]
    check("Amazon Web Services" in rocket_names, "rocketlane names AWS")
    check("SendGrid / Twilio" in rocket_names, "rocketlane names SendGrid / Twilio")
    check("Langsmith" in rocket_names, "rocketlane names Langsmith")
    check("amazon-web-services" in rocket_slugs, "rocketlane AWS uses the existing file")
    check("twilio" in rocket_slugs, "rocketlane SendGrid uses the Twilio file")
    check("langchain" in rocket_slugs, "rocketlane Langsmith uses the LangChain file")
    check("aws" not in rocket_ids, "rocketlane does not keep a raw aws wire id")
    check("langsmith" not in rocket_ids, "rocketlane does not keep a raw langsmith wire id")
    check(len(rocket_names) == 19, f"rocketlane printed 19 named processors, got {len(rocket_names)}")
    rocket_html = (ROOT / "site" / "c" / "rocketlane.html").read_text(encoding="utf-8")
    check(
        "https://www.rocketlane.com/legal/data-processing-agreement" in rocket_html,
        "rocketlane dossier cites the DPA",
    )
    check("https://www.rocketlane.com/legal/sub-processors" in rocket_html, "rocketlane dossier cites the list")
    check("./twilio.html\">SendGrid / Twilio" in rocket_html, "rocketlane SendGrid cross-links to Twilio")
    check("./langchain.html\">Langsmith" in rocket_html, "rocketlane Langsmith cross-links to LangChain")
    check("./weaviate.html\">Weaviate" in rocket_html, "rocketlane Weaviate cross-links to the filed row")
    check("../graph.html#p=weaviate" not in rocket_html, "rocketlane Weaviate is no longer a leftover map node")
    check("./scalekit.html\">Scalekit" in rocket_html, "rocketlane Scalekit cross-links to the filed row")
    check("./fwd-deploy.html\">SaasGenie" in rocket_html, "rocketlane SaasGenie cross-links to fwdDeploy")
    check("../graph.html#p=saasgenie" not in rocket_html, "rocketlane SaasGenie is no longer a leftover map node")
    check("./apricity-group.html\">Apricity" in rocket_html, "rocketlane Apricity cross-links to Apricity Group")
    check("./mako-it-lab.html\">Mako IT Lab Pvt Ltd" in rocket_html, "rocketlane Mako IT Lab cross-links to the filed row")

    # This cut: leftover product vendors from LiveKit / Rocketlane / Weaviate lists.
    check(by_pub["cockroach-labs"]["domain"] == "cockroachlabs.com", "cockroach-labs domain is cockroachlabs.com")
    check(
        instrument_url(by_pub["cockroach-labs"], "dpa")
        == "https://www.cockroachlabs.com/cloud-terms-and-conditions/data-processing-addendum/",
        "cockroach-labs DPA is first-party HTML",
    )
    check(
        instrument_url(by_pub["cockroach-labs"], "subprocessors")
        == "https://www.cockroachlabs.com/cloud-terms-and-conditions/data-processing-addendum/cockroach-labs-sub-processors/",
        "cockroach-labs list is first-party HTML",
    )
    check((by_pub["cockroach-labs"].get("file") or {}).get("dpa") == 20, "cockroach-labs DPA prints")
    check((by_pub["cockroach-labs"].get("file") or {}).get("subprocessors") == 20, "cockroach-labs processors print")
    crdb_slugs = [p.get("slug") for p in (by_pub["cockroach-labs"].get("processors") or [])]
    check(crdb_slugs == ["amazon-web-services", "microsoft", "google", "stripe"], f"cockroach-labs slugs {crdb_slugs}")
    check(by_pub["weaviate"]["domain"] == "weaviate.io", "weaviate domain is weaviate.io")
    check(instrument_url(by_pub["weaviate"], "dpa") == "https://weaviate.io/dpa", "weaviate DPA is first-party HTML")
    check(
        instrument_url(by_pub["weaviate"], "subprocessors") == "https://weaviate.io/subprocessors",
        "weaviate list is first-party HTML",
    )
    check((by_pub["weaviate"].get("file") or {}).get("dpa") == 20, "weaviate DPA prints")
    check((by_pub["weaviate"].get("file") or {}).get("subprocessors") == 20, "weaviate processors print")
    weav_slugs = [p.get("slug") for p in (by_pub["weaviate"].get("processors") or [])]
    check("voyage-ai" in weav_slugs, "weaviate Voyage AI uses the filed row")
    check("amazon-web-services" in weav_slugs, "weaviate AWS uses the existing file")
    check(by_pub["scalekit"]["domain"] == "scalekit.com", "scalekit domain is scalekit.com")
    check(
        instrument_url(by_pub["scalekit"], "dpa")
        == "https://www.scalekit.com/legal/data-processing-agreement",
        "scalekit DPA is first-party HTML",
    )
    check((by_pub["scalekit"].get("file") or {}).get("dpa") == 20, "scalekit DPA prints")
    check(not (by_pub["scalekit"].get("processors") or []), "scalekit named processors stay open")
    check(instrument_url(by_pub["inworld"], "dpa") == "https://inworld.ai/data-processing-addendum", "inworld DPA is first-party HTML")
    check((by_pub["inworld"].get("file") or {}).get("dpa") == 20, "inworld DPA prints")
    check(
        by_pub["inworld"].get("trust_url") == "https://inworld.ai/security",
        "inworld Official page is first-party /security",
    )
    check("trust.inworld.ai" not in (by_pub["inworld"].get("trust_url") or ""), "inworld Official page is not the portal")
    check(
        instrument_url(by_pub["inworld"], "subprocessors") == "https://trust.inworld.ai/subprocessors",
        "inworld subprocessors stay portal URL-only",
    )
    check((by_pub["inworld"].get("file") or {}).get("subprocessors") == 10, "inworld processors stay dotted")
    check(
        instrument_url(by_pub["rime"], "subprocessors") == "https://www.rime.ai/rime-subprocessors",
        "rime list is first-party HTML",
    )
    check((by_pub["rime"].get("file") or {}).get("subprocessors") == 20, "rime processors print")
    check(by_pub["loops"]["domain"] == "loops.so", "loops domain is loops.so email product")
    check(by_pub["lightdash"]["domain"] == "lightdash.com", "lightdash domain is lightdash.com")
    check(by_pub["voyage-ai"]["domain"] == "voyageai.com", "voyage-ai domain is voyageai.com")
    check(by_pub["loops"].get("found") is False, "loops Official page stays open")
    check((by_pub["loops"].get("file") or {}).get("dpa") == 20, "loops DPA prints")
    check(
        sum(int((by_pub["loops"].get("file") or {}).get(k) or 0) for k in ("page", "marks", "dpa", "subprocessors", "years"))
        == 20,
        "loops Completeness is DPA only",
    )
    check(by_pub["lightdash"].get("found") is False, "lightdash Official page stays open")
    check(
        sum(int((by_pub["lightdash"].get("file") or {}).get(k) or 0) for k in ("page", "marks", "dpa", "subprocessors", "years"))
        == 0,
        "lightdash Completeness is 0",
    )
    check("regalix" not in by_pub, "regalix does not invent a second dossier")
    check("saasgenie" not in by_pub, "saasgenie does not invent a second dossier")
    check(by_pub["fwd-deploy"]["domain"] == "fwddeploy.ai", "fwd-deploy domain is fwddeploy.ai")
    check(by_pub["apricity-group"]["domain"] == "apricitygroup.com", "apricity-group domain is apricitygroup.com")
    check(by_pub["mako-it-lab"]["domain"] == "makoitlab.com", "mako-it-lab domain is makoitlab.com")
    check(by_pub["software-mind"]["domain"] == "softwaremind.com", "software-mind domain is softwaremind.com")
    check(by_pub["marketstar"]["domain"] == "marketstar.com", "marketstar domain is marketstar.com")
    check(by_pub["codecentric"]["domain"] == "codecentric.de", "codecentric domain is codecentric.de")
    check(by_pub["level-ai"]["domain"] == "thelevel.ai", "level-ai domain is thelevel.ai")
    check(by_pub["level-ai"].get("trust_url") == "https://thelevel.ai/security", "level-ai Official page is first-party /security")
    check("trust.thelevel.ai" not in (by_pub["level-ai"].get("trust_url") or ""), "level-ai Official page is not the Secureframe portal")
    check(instrument_url(by_pub["level-ai"], "dpa") == "https://thelevel.ai/legal/dpa", "level-ai DPA URL is first-party")
    check(instrument_url(by_pub["level-ai"], "subprocessors") == "https://thelevel.ai/legal/subprocessors", "level-ai subprocessors URL is first-party")
    check((by_pub["level-ai"].get("file") or {}).get("page") == 20, "level-ai Official page prints")
    check((by_pub["level-ai"].get("file") or {}).get("marks") == 10, "level-ai marks stay dotted — portal request labels unread")
    check((by_pub["level-ai"].get("file") or {}).get("dpa") == 20, "level-ai DPA prints")
    check((by_pub["level-ai"].get("file") or {}).get("subprocessors") == 10, "level-ai processors stay dotted")
    check(not (by_pub["level-ai"].get("certs") or []), "level-ai portal GDPR/HIPAA stay off the mark list")
    check(by_pub["ai-data-innovations"]["domain"] == "aidatainnovations.com", "ai-data-innovations domain is aidatainnovations.com")
    check(by_pub["cloud-support-technologies"]["domain"] == "cloudsupport.co.in", "cloud-support-technologies domain is cloudsupport.co.in")
    check(by_pub["amx"]["domain"] == "amxconsulting.com", "amx domain is amxconsulting.com")
    check(by_pub["amx"].get("founded_year") == 2017, "amx year is the first-party 2017 press sentence")
    check((by_pub["amx"].get("file") or {}).get("years") == 20, "amx years print")
    check(by_pub["swan"]["domain"] == "getswan.com", "swan domain is getswan.com")
    check(
        instrument_url(by_pub["swan"], "dpa") == "https://www.getswan.com/legal/dpa",
        "swan DPA is first-party HTML",
    )
    check((by_pub["swan"].get("file") or {}).get("dpa") == 20, "swan DPA prints")
    check((by_pub["swan"].get("file") or {}).get("years") == 20, "swan years print")
    check(by_pub["swan"].get("found") is False, "swan Official page stays open")
    check(not (by_pub["swan"].get("processors") or []), "swan Notion list stays unread")
    check((by_pub["swan"].get("file") or {}).get("subprocessors") in (0, False, None), "swan processors stay open")
    swan_html = (ROOT / "site" / "c" / "swan.html").read_text(encoding="utf-8")
    check("https://www.getswan.com/legal/dpa" in swan_html, "swan dossier cites the DPA")
    check("notion.site" not in swan_html, "swan dossier does not file the Notion processor shell")
    # Prior cut: first-party Completeness DPA on Coralogix. SafeBase
    # trust.coralogix.com is not Official page — URL-only instrument.
    # Footer SOC/ISO/PCI/HIPAA chips stay unread. This cut files the
    # first-party authorized-sub-processors list; Official page stays open.
    check(
        instrument_url(by_pub["coralogix"], "dpa")
        == "https://coralogix.com/data-processing-agreement/",
        "coralogix DPA is first-party HTML",
    )
    check((by_pub["coralogix"].get("file") or {}).get("dpa") == 20, "coralogix DPA prints")
    check(by_pub["coralogix"].get("found") is False, "coralogix SafeBase portal is not Official page")
    check(not by_pub["coralogix"].get("trust_url"), "coralogix portal is not the Official page URL")
    check(
        ((by_pub["coralogix"].get("instruments") or {}).get("trust") or {}).get("url")
        == "https://trust.coralogix.com",
        "coralogix trust instrument keeps the portal URL as a link",
    )
    check(not (by_pub["coralogix"].get("certs") or []), "coralogix footer chips stay unread")
    check((by_pub["coralogix"].get("file") or {}).get("marks") in (0, False, None), "coralogix marks stay open")
    check((by_pub["coralogix"].get("file") or {}).get("page") in (0, False, None), "coralogix Official page stays open")
    check(len(by_pub["coralogix"].get("processors") or []) == 13, "coralogix 13 names print")
    check((by_pub["coralogix"].get("file") or {}).get("subprocessors") == 20, "coralogix processors print")
    check(
        instrument_url(by_pub["coralogix"], "subprocessors")
        == "https://coralogix.com/authorized-sub-processors/",
        "coralogix list URL is the first-party authorized-sub-processors page",
    )
    check(by_pub["coralogix"].get("founded_year") in (None, 0, False), "coralogix years stay open")
    coralogix_html = (ROOT / "site" / "c" / "coralogix.html").read_text(encoding="utf-8")
    check("<h1>Coralogix</h1>" in coralogix_html, "coralogix dossier is its own file")
    check(
        "https://coralogix.com/data-processing-agreement/" in coralogix_html,
        "coralogix dossier cites the DPA",
    )
    check(
        "https://coralogix.com/authorized-sub-processors/" in coralogix_html,
        "coralogix dossier cites the authorized-sub-processors list",
    )
    check("https://trust.coralogix.com" in coralogix_html, "coralogix dossier cites the portal as an instrument URL")
    check("Official page · not on file" in coralogix_html, "coralogix Official page stays open")
    check("SOC 2" not in coralogix_html, "coralogix dossier does not print footer SOC 2")
    check("ISO 27001" not in coralogix_html, "coralogix dossier does not print footer ISO 27001")
    check("vanta" not in coralogix_html.lower(), "coralogix dossier names no portal vendor")
    check("safebase" not in coralogix_html.lower(), "coralogix dossier names no portal vendor")
    linkedin_html = (ROOT / "site" / "c" / "linkedin.html").read_text(encoding="utf-8")
    check("./marketstar.html\">Regalix, Inc" in linkedin_html, "linkedin Regalix cross-links to MarketStar")
    check("./ai-data-innovations.html\">AI Data Innovation Corporation" in linkedin_html, "linkedin AI Data Innovation cross-links to the filed row")
    gitlab_html = (ROOT / "site" / "c" / "gitlab.html").read_text(encoding="utf-8")
    check("./codecentric.html\">cc cloud GmbH" in gitlab_html, "gitlab cc cloud GmbH cross-links to codecentric")
    smart_html = (ROOT / "site" / "c" / "smartsheet.html").read_text(encoding="utf-8")
    check("./level-ai.html\">Ujwal Inc" in smart_html, "smartsheet Ujwal cross-links to Level AI")
    check("./amx.html\">Agile Management Experts" in smart_html, "smartsheet Agile Management Experts cross-links to AMX")
    sonic_html = (ROOT / "site" / "c" / "sonicwall.html").read_text(encoding="utf-8")
    check("./e2open.html\">Avertech" in sonic_html, "sonicwall Avertech cross-links to E2open")
    rime_html = (ROOT / "site" / "c" / "rime.html").read_text(encoding="utf-8")
    check("./swan.html\">Swan" in rime_html, "rime Swan cross-links to the filed row")
    check("./vector.html\">Vector" in rime_html, "rime Vector cross-links to the filed row")
    check("benjamin-mosse-consulting" not in by_pub, "benjamin-mosse-consulting does not invent a second dossier")
    check(by_pub["mosse-security"]["domain"] == "mosse-security.com", "mosse-security domain is mosse-security.com")
    check(by_pub["mosse-security"].get("found") is False, "mosse-security Official page stays open")
    check(by_pub["vector"]["domain"] == "vector.co", "vector domain is vector.co")
    check(by_pub["vector"].get("trust_url") == "https://www.vector.co/security", "vector Official page is first-party /security")
    check("trust.vector.co" not in (by_pub["vector"].get("trust_url") or ""), "vector Official page is not the portal")
    check(instrument_url(by_pub["vector"], "subprocessors") == "https://trust.vector.co/subprocessors", "vector subprocessors stay portal URL-only")
    check((by_pub["vector"].get("file") or {}).get("subprocessors") == 10, "vector processors stay dotted")
    check((by_pub["vector"].get("certs") or []) == [], "vector regulation-only GDPR/CCPA/PIPEDA/LGPD stay off file")
    check("GDPR" not in (by_pub["vector"].get("certs") or []), "vector GDPR stays open")
    check("CCPA" not in (by_pub["vector"].get("certs") or []), "vector CCPA stays open")
    check("PIPEDA" not in (by_pub["vector"].get("certs") or []), "vector PIPEDA stays open")
    check("LGPD" not in (by_pub["vector"].get("certs") or []), "vector LGPD stays open")
    check("SOC 2 Type I" not in (by_pub["vector"].get("certs") or []), "vector SOC 2 Type I stays unread — preparing for audit")
    check((by_pub["vector"].get("file") or {}).get("marks") in (0, 10), "vector marks stay dotted — no Completeness 20 from privacy-law names")
    check((by_pub["vector"].get("file") or {}).get("page") == 20, "vector Official page stays on")
    sophos_html = (ROOT / "site" / "c" / "sophos.html").read_text(encoding="utf-8")
    check("./mosse-security.html\">Benjamin Mosse Consulting Pty Ltd" in sophos_html, "sophos Benjamin Mosse Consulting cross-links to Mossé Security")
    after_html = (ROOT / "site" / "c" / "aftership.html").read_text(encoding="utf-8")
    check("./cloud-support-technologies.html\">Cloud Support Technologies" in after_html, "aftership Cloud Support Technologies cross-links to the filed row")
    # This cut: first-party Completeness DPA on CloudAMQP (84codes).
    # The ToS exhibit is the printed DPA. Annex headers stay unread.
    check(
        instrument_url(by_pub["84codes-cloudamqp"], "dpa")
        == "https://www.cloudamqp.com/legal/terms_of_service.html#data-processing-agreement",
        "cloudamqp DPA is the first-party ToS exhibit",
    )
    check((by_pub["84codes-cloudamqp"].get("file") or {}).get("dpa") == 20, "cloudamqp DPA prints")
    check(not (by_pub["84codes-cloudamqp"].get("processors") or []), "cloudamqp DPA annex headers stay unread")
    # This cut: first-party Completeness DPA on Loops. Framer page prints
    # the agreement opening. Official page stays open.
    check(
        instrument_url(by_pub["loops"], "dpa") == "https://loops.so/dpa",
        "loops DPA is first-party HTML",
    )
    check((by_pub["loops"].get("file") or {}).get("dpa") == 20, "loops DPA prints")
    check(not (by_pub["loops"].get("processors") or []), "loops named processors stay open")
    # This cut: first-party Completeness DPA on Voyage AI. Footer SOC 2 /
    # HIPAA chips stay unread. DPA annex headers stay unread as processors.
    # Do not alias to MongoDB. Official page stays open.
    check(
        instrument_url(by_pub["voyage-ai"], "dpa") == "https://www.voyageai.com/dpa",
        "voyage-ai DPA is first-party HTML",
    )
    check((by_pub["voyage-ai"].get("file") or {}).get("dpa") == 20, "voyage-ai DPA prints")
    check(by_pub["voyage-ai"].get("found") is False, "voyage-ai Official page stays open")
    check(not by_pub["voyage-ai"].get("trust_url"), "voyage-ai homepage is not Official page")
    check(not (by_pub["voyage-ai"].get("certs") or []), "voyage-ai footer chips stay unread")
    check((by_pub["voyage-ai"].get("file") or {}).get("marks") in (0, False, None), "voyage-ai marks stay open")
    check((by_pub["voyage-ai"].get("file") or {}).get("page") in (0, False, None), "voyage-ai Official page stays open")
    check(not (by_pub["voyage-ai"].get("processors") or []), "voyage-ai DPA annex headers stay unread")
    check(
        (by_pub["voyage-ai"].get("file") or {}).get("subprocessors") in (0, False, None),
        "voyage-ai processors stay open",
    )
    check(by_pub["voyage-ai"].get("founded_year") in (None, 0, False), "voyage-ai years stay open")
    check(
        sum(int((by_pub["voyage-ai"].get("file") or {}).get(k) or 0) for k in ("page", "marks", "dpa", "subprocessors", "years"))
        == 20,
        "voyage-ai Completeness is DPA only",
    )
    voyage_html = (ROOT / "site" / "c" / "voyage-ai.html").read_text(encoding="utf-8")
    check("<h1>Voyage AI</h1>" in voyage_html, "voyage-ai dossier is its own file")
    check("https://www.voyageai.com/dpa" in voyage_html, "voyage-ai dossier cites the DPA")
    check("Official page · not on file" in voyage_html, "voyage-ai Official page stays open")
    check("SOC 2" not in voyage_html, "voyage-ai dossier does not print footer SOC 2")
    check("HIPAA" not in voyage_html, "voyage-ai dossier does not print footer HIPAA")
    check("mongodb" not in voyage_html.lower(), "voyage-ai is not aliased to MongoDB")
    check("vanta" not in voyage_html.lower(), "voyage-ai dossier names no portal vendor")

    print(
        f"ok increment-dpa upper-quadrant-queue {len(expected_batch)} walked; "
        f"{len(report.get('dpa_filed') or [])} dpa {len(report.get('subprocessors_filed') or [])} lists"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
