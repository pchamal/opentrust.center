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

    # This increment: SuperOffice, Genedata, Sonar, Trustpilot.
    check(report.get("batch") == ["superoffice", "genedata", "sonar", "trustpilot"], "batch is the four expand slugs")
    sonar = by_pub["sonar"]
    tp = by_pub["trustpilot"]
    check(
        instrument_url(sonar, "dpa") == "https://www.sonarsource.com/legal/data-processing-addendum/",
        "sonar DPA stays the stored first-party addendum",
    )
    check(
        instrument_url(tp, "dpa")
        == "https://corporate.trustpilot.com/legal/for-businesses/data-processing-agreement/nov-2025",
        "trustpilot DPA filed from first-party HTML",
    )
    check((tp.get("file") or {}).get("dpa") == 20, "trustpilot DPA printed")
    sonar_names = [p.get("name") for p in (sonar.get("processors") or [])]
    tp_names = [p.get("name") for p in (tp.get("processors") or [])]
    check("Amazon Web Services EMEA SARL" in sonar_names, "sonar names AWS EMEA")
    check("Okta, Inc" in sonar_names and "Clerk" in sonar_names, "sonar names Okta and Clerk")
    check(not any("SonarSource" in (n or "") for n in sonar_names), "sonar affiliates are not subprocessors")
    check("Service Delivery" not in sonar_names, "sonar section headers are not processors")
    check("Sendgrid (Twilio, Inc.)" in tp_names, "trustpilot names Sendgrid")
    check("Amazon Web Services" in tp_names and "ClickHouse Inc" in tp_names, "trustpilot names AWS and ClickHouse")
    check(not any("Trustpilot" in (n or "") for n in tp_names), "trustpilot affiliates are not subprocessors")
    for slug in ("superoffice", "genedata"):
        pub = by_pub[slug]
        check(not instrument_url(pub, "dpa"), f"{slug} DPA stays open")
        check(not (pub.get("processors") or []), f"{slug} named processors stay open")
        check((pub.get("file") or {}).get("subprocessors") == 10, f"{slug} list URL stays dotted 10")
    sonar_html = (ROOT / "site" / "c" / "sonar.html").read_text(encoding="utf-8")
    tp_html = (ROOT / "site" / "c" / "trustpilot.html").read_text(encoding="utf-8")
    check('target="_blank"' in sonar_html and 'rel="noopener noreferrer"' in sonar_html, "sonar outbound opens a new tab")
    check('target="_blank"' in tp_html and 'rel="noopener noreferrer"' in tp_html, "trustpilot outbound opens a new tab")
    check("wires-scroll" in sonar_html and "wires-scroll" in tp_html, "rewritten dossiers keep the swipe wrapper")
    check("vanta" not in sonar_html.lower() and "vanta" not in tp_html.lower(), "filed dossiers name no portal vendor")

    print(
        f"ok increment-dpa sonar/trustpilot {len(sonar_names)}+{len(tp_names)} processors; "
        f"{len(report.get('dpa_filed') or [])} dpa {len(report.get('subprocessors_filed') or [])} lists"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
