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

    # This increment: DPA already on file, named processors empty (~40 slugs).
    expected_batch = [
        "clio", "freshworks", "cato-networks", "snyk", "celonis", "veriff", "brex",
        "vanta", "honeycomb", "lucidworks", "datalogics", "algolia", "pipedrive",
        "attentive", "cs-disco", "synerise", "snowflake", "imperva", "idrive-inc",
        "ramp", "evenup", "varonis-systems", "cloudflare", "sprout-social",
        "darktrace", "launchdarkly", "deel", "red-canary", "guild", "classranked",
        "mixpanel", "midjourney", "aerospike", "xai", "boomi-lp", "salt-security",
        "caspio", "diebold-nixdorf", "paylocity", "procore",
    ]
    check(report.get("batch") == expected_batch, "batch is the 40 DPA-on-file empty-processor slugs")
    check(
        instrument_url(by_pub["brex"], "dpa") == "https://www.brex.com/legal/dpa",
        "brex DPA upgraded from portal catalog to first-party HTML",
    )
    check((by_pub["brex"].get("file") or {}).get("dpa") == 20, "brex DPA printed")
    check(
        instrument_url(by_pub["freshworks"], "dpa")
        == "https://www.freshworks.com/data-processing-addendum/",
        "freshworks DPA upgraded from portal catalog to first-party HTML",
    )
    check((by_pub["freshworks"].get("file") or {}).get("dpa") == 20, "freshworks DPA printed")
    check(not (by_pub["freshworks"].get("processors") or []), "freshworks named processors stay open")
    check(not (by_pub["brex"].get("processors") or []), "brex named processors stay open")

    snyk_names = [p.get("name") for p in (by_pub["snyk"].get("processors") or [])]
    check("Amplitude, Inc" in snyk_names, "snyk names Amplitude")
    check("Datadog, Inc" in snyk_names and "OpenAI, LLC" in snyk_names, "snyk names Datadog and OpenAI")
    check(not any((n or "").startswith("Snyk") for n in snyk_names), "snyk affiliates are not subprocessors")
    check(len(snyk_names) == 30, f"snyk printed 30 third-party names, got {len(snyk_names)}")

    alg_names = [p.get("name") for p in (by_pub["algolia"].get("processors") or [])]
    check("Amazon Web Services, Inc" in alg_names, "algolia names AWS")
    check("OpenAI" in alg_names and "Anthropic, PBC" in alg_names, "algolia names OpenAI and Anthropic")
    check(not any((n or "").startswith("Algolia") for n in alg_names), "algolia affiliates are not subprocessors")

    hc_names = [p.get("name") for p in (by_pub["honeycomb"].get("processors") or [])]
    check("Amazon Web Services" in hc_names and "Anthropic" in hc_names, "honeycomb names AWS and Anthropic")
    check(len(hc_names) == 7, f"honeycomb printed table has 7 names, got {len(hc_names)}")

    id_names = [p.get("name") for p in (by_pub["idrive-inc"].get("processors") or [])]
    check("Stripe, Inc" in id_names and "Talkdesk, Inc" in id_names, "idrive names Stripe and Talkdesk")
    check("TrustCloud" not in id_names, "idrive portal vendor is not a processor")

    boomi_names = [p.get("name") for p in (by_pub["boomi-lp"].get("processors") or [])]
    check("Amazon Web Services Inc" in boomi_names, "boomi names AWS")
    check("Snowflake Inc" in boomi_names, "boomi names Snowflake")

    sprout_names = [p.get("name") for p in (by_pub["sprout-social"].get("processors") or [])]
    check("ClickHouse, Inc" in sprout_names, "sprout-social names ClickHouse")
    check("OpenAI, L.L.C" in sprout_names, "sprout-social names OpenAI")

    for slug in ("ramp", "deel", "vanta", "midjourney", "clio", "celonis", "attentive", "imperva"):
        pub = by_pub[slug]
        check(instrument_url(pub, "dpa"), f"{slug} existing DPA stays on file")
        check(not (pub.get("processors") or []), f"{slug} named processors stay open")

    filled_html = {}
    for slug in ("snyk", "algolia", "honeycomb", "idrive-inc", "boomi-lp", "sprout-social", "brex", "freshworks"):
        html = (ROOT / "site" / "c" / f"{slug}.html").read_text(encoding="utf-8")
        filled_html[slug] = html
        check('target="_blank"' in html and 'rel="noopener noreferrer"' in html, f"{slug} outbound opens a new tab")
        check("wires-scroll" in html, f"{slug} rewritten dossier keeps the swipe wrapper")
        visible = html.lower()
        check(
            "safebase" not in visible and "conveyor" not in visible and "drata" not in visible,
            f"{slug} named a portal vendor",
        )
    check("vanta" not in filled_html["snyk"].lower() and "vanta" not in filled_html["algolia"].lower(), "filed lists name no portal vendor")
    pronto_html = (ROOT / "site" / "c" / "pronto-software.html").read_text(encoding="utf-8")
    check("Official page" in pronto_html, "Pronto Software still prints Official page")

    print(
        f"ok increment-dpa brex/freshworks + "
        f"{len(snyk_names)}+{len(alg_names)}+{len(hc_names)}+{len(id_names)}+"
        f"{len(boomi_names)}+{len(sprout_names)} processors; "
        f"{len(report.get('dpa_filed') or [])} dpa {len(report.get('subprocessors_filed') or [])} lists"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
