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
        "tensorwave",
        "freightos",
        "serko-limited",
        "planet-labs",
        "help-scout",
        "vyond",
        "naseej",
        "beamery",
        "nylas",
        "wingify",
        "gandi",
        "formstack",
        "wrike",
        "morning-consult",
        "lastpass",
        "maven-agi",
        "elastic-io",
        "model-n",
        "infobip",
        "incountry",
        "macstadium",
        "segment",
        "matterport",
        "ant-international",
        "identity-automation-lp",
        "markmonitor",
        "gmo-globalsign",
        "digital-realty",
        "iterable",
        "omni-analytics",
        "rackspace",
        "recurly-com",
        "relx-d-b-a-lexisnexis",
        "bitpay",
        "shortcut-software",
        "orum",
        "spotdraft",
        "bandwidth-inc",
        "lyzr",
        "speechmatics",
    ]
    check(report.get("batch") == expected_batch, "batch is the upper-quadrant subprocessors queue")
    check(not (report.get("dpa_filed") or []), "no DPA was newly filed")
    filed_sub = {r["slug"]: r for r in (report.get("subprocessors_filed") or [])}
    check(len(filed_sub) == 4, f"four named-processor lists filed, got {sorted(filed_sub)}")
    check(
        set(filed_sub)
        == {
            "help-scout",
            "shortcut-software",
            "wingify",
            "wrike",
        },
        f"kept filings {sorted(filed_sub)}",
    )
    check(
        filed_sub["help-scout"]["url"] == "https://www.helpscout.com/company/legal/sub-processors/",
        "help-scout list URL",
    )
    check(len(filed_sub["help-scout"]["names"]) == 20, "help-scout 20 names")
    check(
        filed_sub["shortcut-software"]["url"] == "https://www.shortcut.com/gdpr-subprocessors/",
        "shortcut list URL",
    )
    check(len(filed_sub["shortcut-software"]["names"]) == 33, "shortcut 33 names")
    check(
        filed_sub["wingify"]["url"] == "https://wingify.com/compliance/subprocessors/",
        "wingify list URL",
    )
    check(len(filed_sub["wingify"]["names"]) == 6, "wingify 6 names")
    check(
        filed_sub["wrike"]["url"] == "https://www.wrike.com/legal/subprocessors-list/",
        "wrike list URL",
    )
    check(len(filed_sub["wrike"]["names"]) == 21, "wrike 21 names")
    stayed = {r["slug"] for r in (report.get("stayed_open") or [])}
    stayed_dpa = {r["slug"] for r in (report.get("stayed_open") or []) if r.get("rule") == "dpa"}
    stayed_sub = {r["slug"] for r in (report.get("stayed_open") or []) if r.get("rule") == "subprocessors"}
    check(stayed == set(expected_batch), f"stayed-open covers the batch, got {sorted(stayed ^ set(expected_batch))}")
    check(len(report.get("stayed_open") or []) == 64, f"64 open DPA/subprocessors slots, got {len(report.get('stayed_open') or [])}")
    check(len(stayed_dpa) == 37, f"37 DPA slots stayed open, got {len(stayed_dpa)}")
    check(len(stayed_sub) == 27, f"27 subprocessors slots stayed open, got {len(stayed_sub)}")
    check(not (set(filed_sub) & stayed_sub), "kept filings are not in subprocessors stayed-open")
    check("lastpass" in stayed, "LastPass JS-shell DPA stayed open")
    check("lastpass" not in {r["slug"] for r in (report.get("dpa_filed") or [])}, "LastPass DPA was not filed")
    check(
        "dpa" not in ((by_enr["lastpass"].get("links") or {})),
        "LastPass links.dpa stays off the JS-shell addendum URL",
    )
    check("recurly-com" in stayed, "Recurly PDF DPA stayed open")
    check(
        "dpa" not in ((by_enr["recurly-com"].get("links") or {})),
        "Recurly links.dpa stays off the Marketo PDF",
    )
    check("segment" in stayed, "Segment Twilio list stayed open")
    check("segment" not in filed_sub, "Segment is not a filed named-processor list")
    check(not (by_pub["segment"].get("processors") or []), "Segment names no processors")
    check(
        (by_enr["segment"].get("links") or {}).get("subprocessors")
        == "https://www.twilio.com/en-us/legal/sub-processors",
        "Segment stored list URL stays the Twilio page, names stay unread",
    )

    for slug in stayed_sub:
        if slug == "recurly-com":
            continue
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
    ):
        check(slug in PRIOR_ATTEMPTED, f"{slug} leftover walk stays on the skip list")
        check(slug not in leftover_slugs, f"{slug} leftover is not retried")

    for slug, rec in filed_sub.items():
        html = (ROOT / "site" / "c" / f"{slug}.html").read_text(encoding="utf-8")
        check(rec["url"] in html, f"{slug} dossier cites the list URL")
        check('rel="noopener noreferrer"' in html, f"{slug} outbound links use noopener")
    check(len(by_pub["help-scout"].get("processors") or []) == 20, "help-scout 20 names print")
    check((by_pub["help-scout"].get("file") or {}).get("subprocessors") == 20, "help-scout processors print")
    check(len(by_pub["shortcut-software"].get("processors") or []) == 33, "shortcut 33 names print")
    check((by_pub["shortcut-software"].get("file") or {}).get("subprocessors") == 20, "shortcut processors print")
    check(len(by_pub["wingify"].get("processors") or []) == 6, "wingify 6 names print")
    check((by_pub["wingify"].get("file") or {}).get("subprocessors") == 20, "wingify processors print")
    check(len(by_pub["wrike"].get("processors") or []) == 21, "wrike 21 names print")
    check((by_pub["wrike"].get("file") or {}).get("subprocessors") == 20, "wrike processors print")
    help_html = (ROOT / "site" / "c" / "help-scout.html").read_text(encoding="utf-8")
    check("./pusher.html" in help_html, "help-scout Pusher.io cross-links to Pusher")
    check("./fivetran.html" in help_html, "help-scout Census cross-links to Fivetran")
    short_html = (ROOT / "site" / "c" / "shortcut-software.html").read_text(encoding="utf-8")
    check("./ketch.html" in short_html, "shortcut Ketch Kloud cross-links to Ketch")
    check("./plain.html" in short_html, "shortcut Not Just Tickets cross-links to Plain")
    wrike_html = (ROOT / "site" / "c" / "wrike.html").read_text(encoding="utf-8")
    check("./maestroqa.html" in wrike_html, "wrike Adtrib/MaestroQA cross-links to MaestroQA")
    check("./ada.html" in wrike_html, "wrike Ada Support cross-links to Ada")
    cloud_html = (ROOT / "site" / "c" / "84codes-cloudamqp.html").read_text(encoding="utf-8")
    check(">Topic<" not in cloud_html, "CloudAMQP does not print DPA Topic as a processor")
    check("Retention period" not in cloud_html, "CloudAMQP does not print Retention period")
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
    check(len(by_pub["client-success"].get("processors") or []) == 10, "client-success 10 names stay")
    check(len(by_pub["forethought-technologies"].get("processors") or []) == 21, "forethought 21 names stay")
    check(len(by_pub["jasper-ai"].get("processors") or []) == 31, "jasper 31 names stay")
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
