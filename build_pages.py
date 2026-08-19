#!/usr/bin/env python3
"""Publish the public register: dossiers, sitemap, and a vendor-free data.json."""
from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
CANON = "https://opentrust.center"
SCORE_YEAR = 2026

VENDOR_WORDS = re.compile(
    r"\b(safebase|vanta|conveyor|wolfia|drata|securitypal|secureframe|"
    r"sprinto|whistic|trustcloud|powered by)\b",
    re.I,
)

CERT_WEIGHT = {
    "fedramp": 12,
    "soc 2 type ii": 10,
    "iso 27001": 10,
    "pci dss": 8,
    "hitrust": 8,
    "hipaa": 6,
    "iso 27701": 6,
    "iso 42001": 6,
    "soc 3": 4,
    "gdpr": 3,
    "ccpa": 3,
}

CERT_ID = {
    "fedramp": "fedramp",
    "soc 2 type ii": "soc-2-type-ii",
    "soc 2": "soc-2-type-ii",
    "soc 1": "soc-1-type-ii",
    "soc 3": "soc-3",
    "iso 27001": "iso-27001",
    "iso 27017": "iso-27017",
    "iso 27018": "iso-27018",
    "iso 27701": "iso-27701",
    "iso 42001": "iso-42001",
    "gdpr": "gdpr",
    "ccpa": "ccpa-cpra",
    "hipaa": "hipaa",
    "hitrust": "hitrust-csf",
    "pci dss": "pci-dss",
    "csa star": "csa-star-l1",
    "nist": "nist-csf",
    "tisax": "tisax",
}

INSTRUMENTS = ("trust", "security", "privacy", "dpa", "subprocessors", "status", "bounty")

FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
    "%3Crect width='64' height='64' fill='%23331400'/%3E"
    "%3Ccircle cx='32' cy='32' r='22' fill='none' stroke='%23ff6600' stroke-width='2'/%3E"
    "%3Ccircle cx='32' cy='32' r='18' fill='none' stroke='%23ff6600' stroke-width='1'/%3E"
    "%3Ctext x='32' y='38' text-anchor='middle' font-family='Georgia,serif' "
    "font-size='16' font-weight='600' fill='%23ff6600'%3EOT%3C/text%3E%3C/svg%3E"
)

FONTS = (
    "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,400;0,500;1,400"
    "&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400"
    "&display=swap"
)


def host_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def path_of(url: str) -> str:
    try:
        return (urlparse(url).path or "/").lower()
    except Exception:
        return "/"


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


VENDOR_TITLES = {
    "safebase", "vanta", "conveyor", "wolfia", "drata", "securitypal",
    "secureframe", "sprinto", "whistic", "trustcloud",
}


def scrub_title(title: str, slug: str = "") -> str:
    t = title or ""
    t = re.sub(r"\s*\|?\s*powered by \w[\w .]*", "", t, flags=re.I)
    t = t.strip(" |-")
    if t.lower() in VENDOR_TITLES and t.lower().replace(" ", "-") != slug:
        return ""
    return t


def cert_key(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def map_cert(name: str) -> dict:
    key = cert_key(name)
    weight = CERT_WEIGHT.get(key, 4)
    att_id = CERT_ID.get(key)
    return {"id": att_id, "name": name, "weight": weight}


def clerk_summary(row: dict, attestations: list[dict], processors: list[dict]) -> str:
    raw = (row.get("summary") or "") + " " + (row.get("title") or "")
    if VENDOR_WORDS.search(raw):
        raw = ""
    if not row.get("found"):
        return ""
    if raw and not VENDOR_WORDS.search(raw) and len(raw.strip()) > 40:
        # Marketing reprint — do not keep.
        raw = ""
    marks = [a["name"] for a in attestations]
    if marks:
        cited = ", ".join(marks[:6])
        extra = f" +{len(marks) - 6}" if len(marks) > 6 else ""
        return f"Official page on file. Marks cited: {cited}{extra}."
    if processors:
        return "Official page on file. Named processors filed from a first-party list."
    return "Official page on file. No marks extracted from the public page."


def classify_official(url: str) -> str:
    host = host_of(url)
    path = path_of(url)
    blob = f"{host} {path}"
    if "trust" in blob:
        return "trust"
    if "security" in blob:
        return "security"
    return "trust"


def disclosure_of(found: bool, attestations: list[dict], instruments: dict, founded_year: int | None) -> dict:
    factors = {
        "page": 20 if found else 0,
        "marks": 0,
        "dpa": 8 if instruments.get("dpa") else 0,
        "processors": 8 if instruments.get("subprocessors") else 0,
        "status": 6 if instruments.get("status") else 0,
        "bounty": 6 if instruments.get("bounty") else 0,
        "privacy": 6 if instruments.get("privacy") else 0,
        "years": 0,
    }
    if found:
        factors["marks"] = min(40, sum(a["weight"] for a in attestations))
    if founded_year:
        factors["years"] = min(10, (SCORE_YEAR - founded_year) // 2)
    score = min(100, sum(factors.values()))
    if not found:
        tier = "silent"
        score = 0
        factors = {k: 0 for k in factors}
    elif score < 40:
        tier = "thin"
    elif score < 70:
        tier = "on-file"
    elif score < 90:
        tier = "substantial"
    else:
        tier = "complete"
    return {"score": score, "tier": tier, "factors": factors}


def factor_line(disc: dict) -> str:
    f = disc["factors"]
    bits = [
        f"page {f['page']}",
        f"marks {f['marks']}",
        f"dpa {f['dpa']}",
        f"processors {f['processors']}",
        f"status {f['status']}",
        f"bounty {f['bounty']}",
        f"privacy {f['privacy']}",
        f"years {f['years']}",
    ]
    tier = "on file" if disc["tier"] == "on-file" else disc["tier"]
    return " · ".join(bits) + f"   = {disc['score']}  {tier}"


def fmt_day(iso: str) -> str:
    if not iso:
        return ""
    # 2026-08-18T22:23:12Z → 18 Aug 2026
    try:
        date = iso[:10]
        y, m, d = date.split("-")
        months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
        return f"{int(d)} {months[int(m) - 1]} {y}"
    except Exception:
        return iso


def enrich_company(row: dict, founded: dict, edges: list[dict], generated_at: str) -> dict:
    slug = row["slug"]
    found = bool(row.get("found"))
    official = row.get("trust_url") or row.get("final_url") or ""
    certs = [c for c in (row.get("certs") or []) if c]
    attestations = [map_cert(c) for c in certs]
    year_rec = founded.get(slug) or {}
    year = year_rec.get("year")
    year_src = year_rec.get("source")

    instruments = {k: None for k in INSTRUMENTS}
    if found and official:
        slot = classify_official(official)
        instruments[slot] = {
            "url": official,
            "host": host_of(official),
            "seen": generated_at[:10] if generated_at else None,
        }

    mine = [e for e in edges if e.get("company") == slug and e.get("source_url")]
    processors = []
    for e in mine:
        processors.append({
            "name": e["processor"],
            "slug": e.get("processor_slug"),
            "source_url": e["source_url"],
        })
    if mine:
        src = mine[0]["source_url"]
        instruments["subprocessors"] = {
            "url": src,
            "host": host_of(src),
            "seen": generated_at[:10] if generated_at else None,
        }

    disc = disclosure_of(found, attestations, instruments, year)
    summary = clerk_summary(row, attestations, processors)

    public = {
        "rank": row.get("rank"),
        "name": row["name"],
        "slug": slug,
        "domain": row.get("domain") or "",
        "found": found,
        "trust_url": official if found else None,
        "final_url": row.get("final_url") if found else None,
        "list": row.get("list") or "",
        "source": row.get("source") or "",
        "probed": row.get("probed"),
        "probed_at": generated_at,
        "certs": certs,
        "attestations": attestations,
        "summary": summary,
        "founded_year": year,
        "founded_source": year_src,
        "instruments": instruments,
        "processors": processors,
        "disclosure": disc,
        "tier": disc["tier"],
        "_crawl": {
            "vendor": (row.get("_crawl") or {}).get("vendor") or (row.get("vendor") if found else None),
            "title": scrub_title((row.get("_crawl") or {}).get("title") or row.get("title") or "", slug),
            "http_status": (row.get("_crawl") or {}).get("http_status") or row.get("http_status"),
        },
    }
    return public


def mast(active: str, prefix: str) -> str:
    def link(href: str, word: str) -> str:
        cls = ' class="on"' if word == active else ""
        return f'<a href="{prefix}{href}"{cls}>{word}</a>'
    return f"""  <header class="mast">
    <a class="wordmark" href="{prefix}">opentrust.center</a>
    <nav class="docket" aria-label="instruments">
      {link("", "register")}
      {link("graph.html", "wires")}
      {link("attestations.html", "gazette")}
    </nav>
    <span class="stamp" aria-hidden="true">OT</span>
  </header>"""


def cell(value: str | None, italic_if_empty: bool = True) -> str:
    if value:
        return escape(value)
    if italic_if_empty:
        return '<span class="absent">not on file</span>'
    return "—"


def dossier_html(row: dict, generated_at: str) -> str:
    name = row["name"]
    slug = row["slug"]
    domain = row.get("domain") or ""
    found = bool(row.get("found"))
    url = row.get("trust_url") or ""
    disc = row["disclosure"]
    tier = "on file" if disc["tier"] == "on-file" else disc["tier"]
    tier_cls = "silent" if disc["tier"] == "silent" else ""
    title = f"{name} — opentrust.center"
    desc = "Official pages, attestations, years, and named processors. On file, or not."
    list_label = "cloud 100" if row.get("list") == "cloud100" else (row.get("list") or "not on file")
    year = row.get("founded_year")
    year_src = row.get("founded_source")
    if year:
        year_html = f'{year} · <a href="{escape(year_src)}">source</a>' if year_src else str(year)
    else:
        year_html = '<span class="absent">not on file</span>'

    atts = row.get("attestations") or []
    if atts:
        att_rows = "".join(
            f'<tr><td class="mark"><a href="../attestations.html#{escape(a["id"] or "")}">{escape(a["name"])}</a></td>'
            f'<td>{escape("cited")}</td><td>{a["weight"]}</td></tr>'
            if a.get("id")
            else f'<tr><td>{escape(a["name"])}</td><td>cited</td><td>{a["weight"]}</td></tr>'
            for a in atts
        )
    else:
        att_rows = '<tr><td colspan="3"><span class="absent">not on file</span></td></tr>'

    inst = row.get("instruments") or {}
    inst_rows = []
    labels = {
        "trust": "trust",
        "security": "security",
        "privacy": "privacy",
        "dpa": "dpa",
        "subprocessors": "subprocessors",
        "status": "status",
        "bounty": "bounty / security.txt",
    }
    for key in INSTRUMENTS:
        rec = inst.get(key)
        label = labels[key]
        if rec and rec.get("url"):
            inst_rows.append(
                f"<tr><td>{escape(label)}</td><td>{escape(rec.get('host') or host_of(rec['url']))}</td>"
                f"<td>{escape(fmt_day((rec.get('seen') or '') + 'T00:00:00Z') if rec.get('seen') else '—')}</td></tr>"
            )
        else:
            inst_rows.append(
                f'<tr><td>{escape(label)}</td><td><span class="absent">not on file</span></td><td>—</td></tr>'
            )

    procs = row.get("processors") or []
    if procs:
        proc_rows = "".join(
            f'<tr><td>{escape(p["name"])}</td>'
            + (
                f'<td><a href="./{escape(p["slug"])}.html">{escape(p["slug"])}</a></td>'
                if p.get("slug")
                else '<td><span class="absent">not in register</span></td>'
            )
            + f'<td><a href="{escape(p["source_url"])}">{escape(host_of(p["source_url"]))}</a></td></tr>'
            for p in procs
        )
    else:
        proc_rows = '<tr><td colspan="3"><span class="absent">not on file</span></td></tr>'

    clerk = row.get("summary") or ""
    clerk_html = f'<p class="clerk">{escape(clerk)}</p>' if clerk else ""
    outbound = (
        f'<button type="button" class="go-out" id="go-out" data-url="{escape(url)}">open official page</button>'
        if found and url
        else '<span class="absent">open official page · not on file</span>'
    )
    gate = (
        """<div class="gate" id="gate" hidden>
      <label class="turn">
        <input type="checkbox" id="gate-box">
        <span class="turn-box" aria-hidden="true"></span>
        <span>I am human</span>
      </label>
      <p class="gate-status" id="gate-status"></p>
    </div>"""
        if found and url
        else ""
    )

    about = {"@type": "Organization", "name": name}
    if domain:
        about["url"] = f"https://{domain}"
    ld = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": desc,
        "url": f"{CANON}/c/{slug}.html",
        "isPartOf": {"@type": "WebSite", "name": "opentrust.center", "url": CANON + "/"},
        "about": about,
    }
    if found and url:
        ld["significantLink"] = url
    creds = [a["name"] for a in atts if a.get("name")]
    if creds:
        ld["about"]["hasCredential"] = creds

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(desc)}">
  <link rel="canonical" href="{CANON}/c/{escape(slug)}.html">
  <meta property="og:title" content="{escape(title)}">
  <meta property="og:description" content="{escape(desc)}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{CANON}/c/{escape(slug)}.html">
  <meta name="theme-color" content="#331400">
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
  <link rel="icon" href="{FAVICON}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="{FONTS}" rel="stylesheet">
  <link rel="stylesheet" href="../styles.css">
</head>
<body>
{mast("register", "../")}
  <p class="issue">ISSUE · file c/{escape(slug)}</p>
  <main class="file">
    <p class="crumb"><a href="../">register</a> / {escape(slug)}</p>
    <section class="ident">
      <h1>{escape(name)}</h1>
      <p class="ident-meta">{escape(domain)} · {escape(list_label)}</p>
      <p class="ident-meta">founded · {year_html}</p>
    </section>
    <div class="disclosure">
      <span class="stamp" aria-hidden="true">OT</span>
      <span class="tier-label {tier_cls}">{escape(tier)}</span>
    </div>
    <p class="factor">{escape(factor_line(disc))}</p>

    <p class="sec-kicker">attestations</p>
    <table class="inst">
      <thead><tr><th>mark</th><th>on page</th><th>weight</th></tr></thead>
      <tbody>{att_rows}</tbody>
    </table>

    <p class="sec-kicker">instruments</p>
    <table class="inst">
      <thead><tr><th>instrument</th><th>host</th><th>last seen</th></tr></thead>
      <tbody>{"".join(inst_rows)}</tbody>
    </table>

    <p class="sec-kicker">named processors</p>
    <p class="fig-sub">Filed from the company’s public list. Not a complete supply chain.</p>
    <table class="inst">
      <thead><tr><th>processor</th><th>in register</th><th>source</th></tr></thead>
      <tbody>{proc_rows}</tbody>
    </table>

    {clerk_html}
    <p class="probe">last probed {escape(fmt_day(generated_at))}</p>
    <div class="actions">
      {outbound}
      {gate}
      <a class="perm" href="./{escape(slug)}.html">permalink · c/{escape(slug)}.html</a>
    </div>
  </main>
  <footer class="colo">
    <p>Disclosure rates the file, not the company. Empty rows print <i>not on file</i>.</p>
    <p><a href="../">register</a> · <a href="../graph.html">wires</a> · <a href="../attestations.html">gazette</a></p>
  </footer>
  <script type="module" src="../dossier.js"></script>
</body>
</html>
"""


def main() -> int:
    raw = {}
    for candidate in (
        ROOT / "data" / "register-source.json",
        ROOT / "data" / "results.json",
        SITE / "data.json",
    ):
        raw = load_json(candidate, {})
        companies = raw.get("companies") or []
        if companies and ("vendor" in companies[0] or companies[0].get("_crawl")):
            break
    if not raw.get("companies"):
        raw = {}
    companies_in = raw.get("companies") or []
    generated_at = raw.get("generated_at") or ""
    sources = raw.get("sources") or [
        {"name": "Forbes Cloud 100 2025", "url": "https://www.forbes.com/lists/cloud100/"},
        {"name": "Public enterprise, security, and AI vendors", "url": None},
    ]

    founded = load_json(ROOT / "data" / "founded.json", {}).get("years") or {}
    edges_doc = load_json(ROOT / "data" / "subprocessors.json", {"edges": []})
    edges = edges_doc.get("edges") or []

    public_companies = [enrich_company(row, founded, edges, generated_at) for row in companies_in]

    public = {
        "generated_at": generated_at,
        "sources": sources,
        "companies": public_companies,
        "found": sum(1 for c in public_companies if c["found"]),
        "total": len(public_companies),
    }
    (SITE / "data.json").write_text(json.dumps(public, indent=2, ensure_ascii=False) + "\n")

    (SITE / "data").mkdir(exist_ok=True)
    (SITE / "data" / "subprocessors.json").write_text(
        json.dumps(edges_doc, indent=2, ensure_ascii=False) + "\n"
    )

    out = SITE / "c"
    if out.exists():
        for old in out.glob("*.html"):
            old.unlink()
    out.mkdir(exist_ok=True)
    for row in public_companies:
        (out / f"{row['slug']}.html").write_text(dossier_html(row, generated_at), encoding="utf-8")

    urls = [
        f"{CANON}/",
        f"{CANON}/graph.html",
        f"{CANON}/attestations.html",
        f"{CANON}/brand.html",
    ]
    for row in public_companies:
        urls.append(f"{CANON}/c/{row['slug']}.html")
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sitemap.append(f"  <url><loc>{escape(u)}</loc></url>")
    sitemap.append("</urlset>\n")
    (SITE / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")

    tiers = {}
    for c in public_companies:
        tiers[c["tier"]] = tiers.get(c["tier"], 0) + 1
    print(f"Wrote {len(public_companies)} dossiers + public data.json + sitemap")
    print("tiers", tiers)
    print("edges", len(edges))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
