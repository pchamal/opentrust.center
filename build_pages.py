#!/usr/bin/env python3
"""Publish the public register: dossiers, sitemap, and a vendor-free data.json."""
from __future__ import annotations

import json
import re
from collections import Counter
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
    "fedramp high": 12,
    "fedramp moderate": 12,
    "soc 2 type ii": 10,
    "iso 27001": 10,
    "pci dss": 8,
    "hitrust": 8,
    "cmmc": 8,
    "hipaa": 6,
    "iso 27701": 6,
    "iso 42001": 6,
    "soc 2 type i": 4,
    "soc 2": 4,
    "soc 1 type ii": 4,
    "soc 1": 4,
    "soc 3": 4,
    "iso 27017": 4,
    "iso 27018": 4,
    "iso 22301": 4,
    "iso 9001": 4,
    "csa star": 4,
    "tisax": 4,
    "irap": 4,
    "stateramp": 4,
    "tx-ramp": 4,
    "cyber essentials": 4,
    "nist 800-53": 4,
    "nist csf": 4,
    "c5": 4,
    "ismap": 4,
    "sox": 4,
    "gdpr": 3,
    "ccpa": 3,
}

CERT_ID = {
    "fedramp": "fedramp",
    "fedramp high": "fedramp",
    "fedramp moderate": "fedramp",
    "soc 2 type ii": "soc-2-type-ii",
    "soc 2 type i": "soc-2-type-i",
    "soc 2": "soc-2-type-ii",
    "soc 1 type ii": "soc-1-type-ii",
    "soc 1": "soc-1-type-ii",
    "soc 3": "soc-3",
    "iso 27001": "iso-27001",
    "iso 27017": "iso-27017",
    "iso 27018": "iso-27018",
    "iso 27701": "iso-27701",
    "iso 42001": "iso-42001",
    "iso 22301": "iso-22301",
    "iso 9001": "iso-9001",
    "gdpr": "gdpr",
    "ccpa": "ccpa-cpra",
    "hipaa": "hipaa",
    "hitrust": "hitrust-csf",
    "pci dss": "pci-dss",
    "csa star": "csa-star-l1",
    "nist": "nist-csf",
    "nist csf": "nist-csf",
    "nist 800-53": "nist-800-53",
    "tisax": "tisax",
    "irap": "irap",
    "stateramp": "stateramp",
    "tx-ramp": "tx-ramp",
    "cyber essentials": "cyber-essentials",
    "cmmc": "cmmc-l2",
    "c5": "c5",
    "ismap": "ismap",
    "sox": "sox",
}

LINK_TO_INSTRUMENT = {
    "trust": "trust",
    "security": "security",
    "privacy": "privacy",
    "dpa": "dpa",
    "subprocessors": "subprocessors",
    "status": "status",
    "bug_bounty": "bounty",
    "security_txt": "bounty",
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


VENDOR_HOST_RE = re.compile(
    r"(^|\.)(safebase\.us|safebase\.com|vanta\.com|conveyor\.com|wolfia\.\w+|"
    r"securitypal\.com|drata\.com|secureframe\.com|whistic\.com|"
    r"sprinto\.com|trustcloud\.com)$",
    re.I,
)


def host_of(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or parsed.netloc or "").lower().removeprefix("www.")
        if parsed.port and parsed.port not in (80, 443):
            return f"{host}:{parsed.port}"
        return host
    except Exception:
        return ""


def normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.hostname:
            return url
        netloc = parsed.hostname
        if parsed.port and parsed.port not in (80, 443):
            netloc = f"{parsed.hostname}:{parsed.port}"
        return parsed._replace(netloc=netloc).geturl()
    except Exception:
        return url


def display_host(url: str, company_domain: str = "") -> str:
    host = host_of(url)
    own = (company_domain or "").lower().removeprefix("www.")
    if own and (host == own or host.endswith("." + own)):
        return host
    if VENDOR_HOST_RE.search(host):
        return "official page"
    return host


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
    weight = CERT_WEIGHT.get(key)
    att_id = CERT_ID.get(key)
    if "fedramp" in key:
        if "li-saas" in key or "li saas" in key:
            att_id = att_id or "fedramp-li-saas"
        else:
            att_id = att_id or "fedramp"
        if weight is None:
            weight = 12
    if weight is None:
        weight = 4
    return {"id": att_id, "name": name, "weight": weight}


CLERK_KEEP = re.compile(r"^(Public trust center|Official page)\b", re.I)
MARKETING = re.compile(
    r"\b(our users|our mission|rely on us|good custodians|commitment to|"
    r"explore our|ensures security|building trusted|we are an)\b",
    re.I,
)

FACTOR_KEYS = ("page", "marks", "dpa", "processors", "status", "bounty", "privacy", "years")
FACTOR_FROM_FILE = {
    "portal": "page",
    "certs": "marks",
    "page": "page",
    "marks": "marks",
    "dpa": "dpa",
    "subprocessors": "processors",
    "processors": "processors",
    "status": "status",
    "disclosure": "bounty",
    "bounty": "bounty",
    "privacy": "privacy",
    "longevity": "years",
    "years": "years",
}


def clerk_summary(row: dict, attestations: list[dict], processors: list[dict], found: bool | None = None) -> str:
    if found is None:
        found = bool(row.get("found"))
    if not found:
        return ""
    raw = (row.get("summary") or "").strip()
    if VENDOR_WORDS.search(raw) or MARKETING.search(raw):
        raw = ""
    if raw and CLERK_KEEP.match(raw):
        parts = re.split(r"(?<=[.?!])\s+", raw)
        return " ".join(parts[:2]).strip()
    marks = [a["name"] for a in attestations]
    if marks:
        cited = ", ".join(marks[:6])
        extra = f" +{len(marks) - 6}" if len(marks) > 6 else ""
        return f"Official page on file. Marks cited from public HTML: {cited}{extra}."
    if processors:
        return "Official page on file. Named processors filed from a first-party list."
    return "Official page on file. No marks extracted from the public HTML."


def classify_official(url: str) -> str:
    host = host_of(url)
    path = path_of(url)
    blob = f"{host} {path}"
    if "trust" in blob:
        return "trust"
    if "security" in blob:
        return "security"
    return "trust"


def filed_disclosure(row: dict) -> dict:
    """Print the file’s score, factors, and tier. Cap at 100. Do not rescore."""
    raw = row.get("disclosure") or {}
    factors = {k: 0 for k in FACTOR_KEYS}
    for key, val in (raw.get("factors") or {}).items():
        dest = FACTOR_FROM_FILE.get(key)
        if dest:
            factors[dest] = int(val or 0)
    score = raw.get("score")
    score = min(100, max(0, int(score))) if score is not None else min(100, sum(factors.values()))
    tier = raw.get("tier") or "silent"
    if tier not in {"silent", "thin", "on-file", "substantial", "complete"}:
        tier = "silent"
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


def fmt_when(iso: str) -> str:
    if not iso:
        return ""
    try:
        from datetime import datetime, timezone, timedelta
        dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        pt = dt - timedelta(hours=7)  # PDT in August
        hour = pt.hour % 12 or 12
        ampm = "AM" if pt.hour < 12 else "PM"
        return f"{fmt_day(iso)}, {hour}:{pt.minute:02d} {ampm} PT"
    except Exception:
        return fmt_day(iso)


def seen_date(generated_at: str) -> str | None:
    return generated_at[:10] if generated_at else None


def file_instrument(instruments: dict, key: str, url: str, generated_at: str, company_domain: str = "") -> None:
    if not url or instruments.get(key):
        return
    url = normalize_url(url)
    instruments[key] = {
        "url": url,
        "host": display_host(url, company_domain),
        "seen": seen_date(generated_at),
    }


def processor_display_name(edge: dict, node: dict, to: str) -> str:
    """Evidence is the printed name when it is a name. A filing note is not."""
    evidence = str(edge.get("evidence") or "").strip()
    if evidence and len(evidence) <= 64 and not re.search(r"\blisted on\b", evidence, re.I):
        return evidence
    return str(edge.get("processor") or node.get("name") or to)


def register_slug_for(node: dict, by_slug: dict, by_domain: dict) -> str | None:
    nid = node.get("id")
    if nid and nid in by_slug:
        return nid
    domain = (node.get("domain") or "").lower()
    if domain in by_domain:
        return by_domain[domain]
    return None


def enrich_company(row: dict, edges: list[dict], nodes: dict, by_slug: dict, by_domain: dict, generated_at: str) -> dict:
    slug = row["slug"]
    links = row.get("links") or {}
    domain = row.get("domain") or ""
    disc = filed_disclosure(row)
    found = bool(
        row.get("found")
        or links.get("trust")
        or links.get("security")
        or disc["tier"] != "silent"
        or disc["factors"].get("page")
    )
    official = row.get("trust_url") or links.get("trust") or links.get("security") or row.get("final_url") or ""
    if not found:
        official = ""
    certs = [c for c in (row.get("certs") or []) if c]
    attestations = [map_cert(c) for c in certs]
    year = row.get("founded_year")
    year_src = row.get("founded_source")

    instruments = {k: None for k in INSTRUMENTS}
    for link_key, inst_key in LINK_TO_INSTRUMENT.items():
        url = links.get(link_key)
        if url:
            file_instrument(instruments, inst_key, url, generated_at, domain)
    if found and official:
        slot = classify_official(official)
        file_instrument(instruments, slot, official, generated_at, domain)

    # Real edges only. A subprocessors *link* is not a parsed name.
    mine = [
        e for e in edges
        if e.get("source_url") and (e.get("from") or e.get("company")) == slug
    ]
    processors = []
    for e in mine:
        to = e.get("to") or e.get("processor_slug") or ""
        node = nodes.get(to) or {}
        name = processor_display_name(e, node, to)
        proc_slug = register_slug_for(node, by_slug, by_domain)
        processors.append({
            "name": name,
            "slug": proc_slug,
            "source_url": e["source_url"],
        })
    if mine and not instruments.get("subprocessors"):
        src = mine[0]["source_url"]
        file_instrument(instruments, "subprocessors", src, generated_at, domain)

    summary = clerk_summary(row, attestations, processors, found)
    fedramp = public_fedramp(row.get("fedramp"))

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
    if fedramp:
        public["fedramp"] = fedramp
    return public


FEDRAMP_MARKET = "https://www.fedramp.gov/marketplace/products/"


def product_market_url(item: dict) -> str:
    pid = str(item.get("id") or item.get("fedramp_id") or "").strip()
    if item.get("url"):
        return str(item["url"])
    if pid:
        return f"{FEDRAMP_MARKET.rstrip('/')}/{pid}"
    return FEDRAMP_MARKET


def collapse_fedramp_level(level: str) -> str | None:
    if level in ("Low", "20x Low"):
        return "Low"
    if level in ("Moderate", "20x Moderate"):
        return "Moderate"
    if level == "High":
        return "High"
    return None


def public_fedramp(raw) -> dict | None:
    """Pass through the GSA dump as filed. Do not invent offerings."""
    if not isinstance(raw, dict):
        return None
    products = []
    for item in raw.get("products") or []:
        if not isinstance(item, dict):
            continue
        offering = str(item.get("offering") or "").strip()
        if not offering:
            continue
        pid = str(item.get("id") or item.get("fedramp_id") or "").strip() or None
        products.append({
            "id": pid,
            "offering": offering,
            "status": str(item.get("status") or "").strip() or None,
            "impact_level": str(item.get("impact_level") or "").strip() or None,
            "auth_date": item.get("auth_date") or None,
            "url": product_market_url(item),
        })
    if not products and not (raw.get("highest") or raw.get("highest_authorized")):
        return None
    raw_levels = list(raw.get("raw_levels") or raw.get("impact_levels") or [])
    if not raw_levels:
        raw_levels = [p["impact_level"] for p in products if p.get("impact_level")]
        # unique, High > 20x Moderate > Moderate > 20x Low > Low > LI-SaaS
        rank = {"High": 6, "20x Moderate": 5, "Moderate": 4, "20x Low": 3, "Low": 2, "LI-SaaS": 1}
        raw_levels = sorted(dict.fromkeys(raw_levels), key=lambda lv: (-rank.get(lv, 0), lv))
    levels = list(raw.get("levels") or [])
    if not levels:
        levels = []
        for lv in raw_levels:
            bucket = collapse_fedramp_level(lv)
            if bucket and bucket not in levels:
                levels.append(bucket)
        order = {"High": 0, "Moderate": 1, "Low": 2}
        levels.sort(key=lambda lv: order.get(lv, 9))
    authorized = raw.get("authorized")
    if authorized is None:
        authorized = raw.get("authorized_offerings") or 0
    in_process = raw.get("in_process")
    if in_process is None:
        in_process = raw.get("in_process_offerings") or 0
    highest = raw.get("highest") or raw.get("highest_authorized")
    marketplace = raw.get("marketplace")
    if not marketplace and products:
        marketplace = products[0]["url"]
    return {
        "levels": levels,
        "raw_levels": raw_levels,
        "highest": highest,
        "authorized": authorized,
        "in_process": in_process,
        "marketplace": marketplace or FEDRAMP_MARKET,
        "source": raw.get("source") or FEDRAMP_MARKET,
        "products": products,
    }


def official_a(url: str, text: str) -> str:
    return (
        f'<a class="official" href="{escape(url)}" rel="noopener noreferrer">'
        f"{escape(text)}</a>"
    )


GATE_HTML = """<div class="gate" id="gate" hidden>
      <label class="turn">
        <input type="checkbox" id="gate-box">
        <span class="turn-box" aria-hidden="true"></span>
        <span>I am human</span>
      </label>
      <p class="gate-status" id="gate-status"></p>
    </div>"""


def fedramp_block(row: dict) -> str:
    fed = row.get("fedramp") if isinstance(row.get("fedramp"), dict) else None
    products = [
        p for p in (fed or {}).get("products") or []
        if str(p.get("offering") or "").strip()
    ]
    caption = (
        f'<p class="fig-sub">Filed from the <a href="{escape(FEDRAMP_MARKET)}">'
        f"FedRAMP Marketplace</a>. Not a badge.</p>"
    )
    highest = None
    if products and fed:
        highest = fed.get("highest") or fed.get("highest_authorized")
    if products:
        rows = []
        for p in products:
            offering = str(p.get("offering") or "").strip()
            status = str(p.get("status") or "").strip() or "—"
            level = str(p.get("impact_level") or "").strip() or "—"
            auth = fmt_day(p.get("auth_date") or "") or "—"
            href = str(p.get("url") or "").strip() or FEDRAMP_MARKET
            rows.append(
                f'<tr><td class="mark"><a href="{escape(href)}">{escape(offering)}</a></td>'
                f"<td>{escape(status)}</td>"
                f"<td>{escape(level)}</td>"
                f"<td>{escape(auth)}</td></tr>"
            )
        body = "".join(rows)
    else:
        body = '<tr><td colspan="4"><span class="absent">not on file</span></td></tr>'
    lines = ['    <p class="sec-kicker">fedramp</p>']
    if highest:
        lines.append(f'    <p class="ident-meta">highest authorized · {escape(highest)}</p>')
    lines.append(f"    {caption}")
    lines.append('    <table class="inst">')
    lines.append('      <thead><tr><th>offering</th><th>status</th><th>impact level</th><th>auth date</th></tr></thead>')
    lines.append(f"      <tbody>{body}</tbody>")
    lines.append("    </table>")
    return "\n".join(lines) + "\n"


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
            shown = rec.get("host") or display_host(rec["url"], domain)
            inst_rows.append(
                f"<tr><td>{escape(label)}</td><td>{official_a(rec['url'], shown)}</td>"
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
            + f'<td>{official_a(p["source_url"], host_of(p["source_url"]))}</td></tr>'
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
    need_gate = bool(found and url) or any(
        rec and rec.get("url") for rec in inst.values()
    ) or any(p.get("source_url") for p in procs)
    gate = GATE_HTML if need_gate else ""
    claim = f'<a class="perm" href="../claim.html?slug={escape(slug)}">claim or correct this file</a>'

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

{fedramp_block(row)}
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
    <p class="probe">last probed {escape(fmt_when(generated_at))}</p>
    <div class="actions">
      {outbound}
      {gate}
      {claim}
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


def coverage_of(companies_in: list[dict], public_companies: list[dict], edges: list[dict]) -> dict:
    links = Counter()
    for row in companies_in:
        for key, url in (row.get("links") or {}).items():
            if url:
                links[key] += 1
    tiers = Counter(c["tier"] for c in public_companies)
    top = Counter(e.get("to") for e in edges if e.get("to")).most_common(3)
    return {
        "companies": len(public_companies),
        "years": sum(1 for c in companies_in if c.get("founded_year")),
        "certs_companies": sum(1 for c in companies_in if c.get("certs")),
        "edges": len(edges),
        "top_processors": [{"id": key, "n": n} for key, n in top],
        "links": {
            "security_txt": links.get("security_txt", 0),
            "dpa": links.get("dpa", 0),
            "privacy": links.get("privacy", 0),
            "status": links.get("status", 0),
            "bug_bounty": links.get("bug_bounty", 0),
            "subprocessors": links.get("subprocessors", 0),
        },
        "tiers": {
            "silent": tiers.get("silent", 0),
            "thin": tiers.get("thin", 0),
            "on-file": tiers.get("on-file", 0),
            "substantial": tiers.get("substantial", 0),
            "complete": tiers.get("complete", 0),
        },
    }


def main() -> int:
    src = SITE / "data" / "enriched.json"
    if not src.exists():
        src = ROOT / "data" / "enriched.json"
    raw = load_json(src, {})
    companies_in = raw.get("companies") or []
    generated_at = raw.get("generated_at") or ""
    sources = raw.get("sources") or [
        {"name": "Forbes Cloud 100 2025", "url": "https://www.forbes.com/lists/cloud100/"},
        {"name": "Public enterprise, security, and AI vendors", "url": None},
    ]

    wires_path = SITE / "data" / "subprocessors.json"
    if not wires_path.exists():
        wires_path = ROOT / "data" / "subprocessors.json"
    edges_doc = load_json(wires_path, {"edges": [], "nodes": []})
    edges = [e for e in (edges_doc.get("edges") or []) if e.get("source_url")]
    nodes = {n["id"]: n for n in (edges_doc.get("nodes") or []) if n.get("id")}
    by_slug = {c["slug"]: c for c in companies_in if c.get("slug")}
    by_domain = {}
    for c in companies_in:
        domain = (c.get("domain") or "").lower()
        if domain:
            by_domain[domain] = c["slug"]

    public_companies = [
        enrich_company(row, edges, nodes, by_slug, by_domain, generated_at)
        for row in companies_in
    ]
    coverage = coverage_of(companies_in, public_companies, edges)

    public = {
        "generated_at": generated_at,
        "sources": sources,
        "companies": public_companies,
        "found": sum(1 for c in public_companies if c["found"]),
        "total": len(public_companies),
        "coverage": coverage,
    }
    (SITE / "data.json").write_text(json.dumps(public, indent=2, ensure_ascii=False) + "\n")

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
        f"{CANON}/claim.html",
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
    print("coverage", json.dumps(coverage, sort_keys=True))
    print("tiers", dict(tiers))
    print("edges", len(edges))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
