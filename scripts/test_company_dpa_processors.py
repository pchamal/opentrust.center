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

    # This increment: portal-catalog DPA upgrades + unread first-party privacy-page queue.
    expected_batch = [
        "1password",
        "navan",
        "vercel",
        "twilio",
        "dialpad",
        "check-point",
        "trip-com",
        "gb-group",
        "first-solar",
        "alfa-financial-software",
        "mitek-systems",
        "consolidated-edison",
        "brown-forman",
        "american-water-works",
        "echostar",
        "danaher-corporation",
        "synaptics",
        "blackrock",
        "tencent",
        "genius-sports",
        "klarna",
        "nagarro",
        "sea-limited",
        "character-ai",
        "fiserv",
        "stitch-fix",
        "freee-k-k",
        "backblaze",
        "cboe-global-markets",
        "travelport",
        "verisign",
        "amcor",
        "abbott-laboratories",
        "american-international-group",
        "aflac",
        "jabil",
        "micron-technology",
        "valero-energy",
        "aes-corporation",
        "centene",
    ]
    check(report.get("batch") == expected_batch, "batch is the privacy-page / portal-upgrade queue")
    filed = {r["slug"]: r["url"] for r in (report.get("dpa_filed") or [])}
    check(filed.get("navan") == "https://navan.com/dpa", "navan first-party DPA filed")
    check(filed.get("vercel") == "https://vercel.com/legal/dpa", "vercel first-party DPA filed")
    check(
        filed.get("backblaze") == "https://www.backblaze.com/company/policy/dpa-for-uk-residents",
        "backblaze first-party DPA filed",
    )
    check(len(filed) == 3, f"three DPAs filed, got {sorted(filed)}")
    check(not (report.get("subprocessors_filed") or []), "no named processors were invented")

    check(instrument_url(by_pub["navan"], "dpa") == "https://navan.com/dpa", "navan dossier DPA")
    check(len(by_pub["navan"].get("processors") or []) == 4, "navan existing 4 names stay")
    check(instrument_url(by_pub["vercel"], "dpa") == "https://vercel.com/legal/dpa", "vercel dossier DPA")
    check(len(by_pub["vercel"].get("processors") or []) == 14, "vercel existing 14 names stay")
    check(
        instrument_url(by_pub["backblaze"], "dpa")
        == "https://www.backblaze.com/company/policy/dpa-for-uk-residents",
        "backblaze dossier DPA",
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

    zeros = [
        slug
        for slug in expected_batch
        if slug not in {"navan", "vercel", "backblaze", "1password", "twilio", "dialpad"}
    ]
    for slug in zeros:
        pub = by_pub[slug]
        check(not instrument_url(pub, "dpa"), f"{slug} DPA stays open")
        check(not (pub.get("file") or {}).get("dpa"), f"{slug} file.dpa stays open")
        check(not (pub.get("processors") or []), f"{slug} named processors stay open")

    for slug in expected_batch:
        html = (ROOT / "site" / "c" / f"{slug}.html").read_text(encoding="utf-8")
        check('target="_blank"' in html and 'rel="noopener noreferrer"' in html, f"{slug} outbound opens a new tab")
        check("wires-scroll" in html, f"{slug} dossier keeps the swipe wrapper")
        visible = html.lower()
        check(
            "safebase" not in visible and "conveyor" not in visible and "drata" not in visible,
            f"{slug} named a portal vendor",
        )
        if slug != "1password":
            check("vanta" not in visible, f"{slug} dossier names no portal vendor")
    pronto_html = (ROOT / "site" / "c" / "pronto-software.html").read_text(encoding="utf-8")
    check("Official page" in pronto_html, "Pronto Software still prints Official page")
    cognition = (ROOT / "site" / "c" / "cognition.html").read_text(encoding="utf-8")
    check(
        "cognition.com/legal/data-processing-statement" in cognition,
        "AITI cognition named-processor source-line stays",
    )

    print(
        f"ok increment-dpa privacy-page-queue {len(expected_batch)} walked; "
        f"{len(report.get('dpa_filed') or [])} dpa {len(report.get('subprocessors_filed') or [])} lists"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
