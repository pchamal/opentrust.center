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
    "aiuc-1": 8,
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
    "aiuc-1": "aiuc-1",
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

FAVICON = "../favicon.svg"


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


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def pretty_subprocessor_nodes(doc: dict) -> None:
    for node in doc.get("nodes") or []:
        name = str(node.get("name") or "").strip()
        if is_slug_case(name):
            node["name"] = title_case_slug(name)


def stamp_data_v(generated_at: str) -> None:
    path = SITE / "lib.js"
    if not generated_at or not path.exists():
        return
    original = path.read_text()
    updated, n = re.subn(
        r'export const DATA_V = "[^"]*";',
        f'export const DATA_V = "{generated_at}";',
        original,
        count=1,
    )
    if n:
        path.write_text(updated)


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


_ATTESTATION_IDS: dict[str, str] | None = None


def attestation_id_book() -> dict[str, str]:
    """Existing framework entries only. Do not invent a mark page."""
    global _ATTESTATION_IDS
    if _ATTESTATION_IDS is not None:
        return _ATTESTATION_IDS
    path = SITE / "data" / "attestations.json"
    if not path.exists():
        path = ROOT / "data" / "attestations.json"
    book: dict[str, str] = {}
    for item in load_json(path, {}).get("attestations") or []:
        aid = str(item.get("id") or "").strip()
        if not aid:
            continue
        for label in (aid, item.get("name"), item.get("short")):
            key = cert_key(label or "")
            if key and key not in book:
                book[key] = aid
    _ATTESTATION_IDS = book
    return book


def map_cert(name: str) -> dict:
    key = cert_key(name)
    weight = CERT_WEIGHT.get(key)
    att_id = CERT_ID.get(key) or attestation_id_book().get(key)
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


def link_mark_words(text: str, attestations: list[dict], href_base: str = "../attestations.html") -> str:
    """Link mark words that already have a framework entry. Words only."""
    out = escape(text)
    labels: list[tuple[str, str]] = []
    seen: set[str] = set()
    for a in attestations:
        aid = str(a.get("id") or "").strip()
        if not aid:
            continue
        for lab in (a.get("name"), a.get("short")):
            t = str(lab or "").strip()
            if t and t not in seen:
                seen.add(t)
                labels.append((t, aid))
    labels.sort(key=lambda x: len(x[0]), reverse=True)
    for lab, aid in labels:
        needle = escape(lab)
        if not needle:
            continue
        link = f'<a href="{escape(href_base)}#{escape(aid)}">{needle}</a>'
        parts: list[str] = []
        i = 0
        while i < len(out):
            j = out.find(needle, i)
            if j < 0:
                parts.append(out[i:])
                break
            before = out[:j]
            in_link = before.rfind("<a ") > before.rfind("</a>")
            parts.append(out[i:j])
            parts.append(needle if in_link else link)
            i = j + len(needle)
        out = "".join(parts)
    return out


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


FILE_METER_KEYS = ("page", "marks", "dpa", "subprocessors", "years")


def file_flags(row: dict, disc: dict) -> dict:
    """Five instruments a buyer can see. Not a score."""
    f = disc.get("factors") or {}
    return {
        "page": bool(f.get("page")),
        "marks": bool(f.get("marks") or row.get("certs") or row.get("attestations")),
        "dpa": bool(f.get("dpa")),
        "subprocessors": bool(f.get("processors") or f.get("subprocessors")),
        "years": bool(row.get("founded_year") or f.get("years")),
    }


def file_coverage_text(flags: dict) -> str:
    """Text coverage with a denominator. Not a meter and not a score."""
    n = sum(1 for k in FILE_METER_KEYS if flags.get(k))
    return (
        f"public evidence located in {n} of 5 checked categories "
        "(page, marks, DPA, subprocessors, years)"
    )


def factor_line(disc: dict) -> str:
    f = disc["factors"]
    bits = [
        f"page {f['page']}",
        f"marks {f['marks']}",
        f"dpa {f['dpa']}",
        f"subprocessors {f['processors']}",
        f"years {f['years']}",
    ]
    return " · ".join(bits)


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


SLUG_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_slug_case(s: str) -> bool:
    t = str(s or "").strip()
    return bool(t) and bool(SLUG_NAME.fullmatch(t))


def title_case_slug(to: str) -> str:
    parts = [part for part in re.split(r"[-_]+", str(to or "")) if part]
    out = []
    for part in parts:
        if len(part) <= 2 and any(c.isalpha() for c in part):
            out.append("".join(c.upper() if c.isalpha() else c for c in part))
            continue
        chars = []
        cap_next = True
        for c in part:
            if c.isalpha():
                chars.append(c.upper() if cap_next else c.lower())
                cap_next = False
            else:
                chars.append(c)
                cap_next = c.isdigit()
        out.append("".join(chars) if chars else part)
    return " ".join(out) if out else str(to or "")


def humanize_processor_name(s: str) -> str:
    t = str(s or "").strip()
    if is_slug_case(t):
        return title_case_slug(t)
    return t


def looks_like_processor_name(s: str) -> bool:
    """A filing note or page sentence is not a processor name."""
    t = str(s or "").strip()
    if not t:
        return False
    if re.match(r"^listed on public", t, re.I):
        return False
    if re.search(r"listed on", t, re.I) or re.search(r"\bpage\b", t, re.I):
        return False
    return True


def processor_display_name(edge: dict, node: dict, to: str) -> str:
    """Print the published name. Do not replace a filed string with a catalog label."""
    evidence = str(edge.get("evidence") or edge.get("processor") or "").strip()
    if looks_like_processor_name(evidence):
        return humanize_processor_name(evidence)
    node_name = str(node.get("name") or "").strip()
    if looks_like_processor_name(node_name):
        return humanize_processor_name(node_name)
    if to:
        return humanize_processor_name(to) or title_case_slug(to)
    return humanize_processor_name(str(edge.get("processor") or to))


def register_slug_for(node: dict, by_slug: dict, by_domain: dict, by_name: dict | None = None) -> str | None:
    """Reuse an existing dossier slug. Do not invent a page."""
    nid = node.get("id")
    if nid and nid in by_slug:
        return nid
    domain = (node.get("domain") or "").lower()
    if domain in by_domain:
        return by_domain[domain]
    if by_name:
        name = str(node.get("name") or "").strip().lower()
        if name and name in by_name:
            return by_name[name]
    return None


def enrich_company(
    row: dict,
    edges: list[dict],
    nodes: dict,
    by_slug: dict,
    by_domain: dict,
    generated_at: str,
    by_name: dict | None = None,
) -> dict:
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
    certs = sorted((c for c in (row.get("certs") or []) if c), key=lambda x: str(x).lower())
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
        proc_slug = register_slug_for(node, by_slug, by_domain, by_name)
        processors.append({
            "name": name,
            "slug": proc_slug,
            "id": to or None,
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
        "file": file_flags(row, disc),
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
        if not keep_marketplace_product(item):
            continue
        offering = str(item.get("offering") or "").strip()
        pid = str(item.get("id") or item.get("fedramp_id") or "").strip() or None
        products.append({
            "id": pid,
            "offering": offering,
            "status": str(item.get("status") or "").strip() or None,
            "impact_level": str(item.get("impact_level") or "").strip() or None,
            "auth_date": item.get("auth_date") or None,
            "phase": str(item.get("phase") or raw.get("phase") or "").strip() or None,
            "authorizations": item.get("authorizations") if item.get("authorizations") is not None else raw.get("authorizations"),
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
        "phase": raw.get("phase") or next((p.get("phase") for p in products if p.get("phase")), None),
        "authorizations": raw.get("authorizations") if raw.get("authorizations") is not None else next((p.get("authorizations") for p in products if p.get("authorizations") is not None), None),
        "products": products,
    }


def official_a(url: str, text: str) -> str:
    return (
        f'<a class="official" href="{escape(url)}" rel="noopener noreferrer">'
        f"{escape(text)}</a>"
    )


def fedramp_status_word(status: str) -> str:
    """Marketplace facts. Not-yet-certified stays on file; do not coerce to authorized."""
    s = re.sub(r"^fedramp\s+", "", (status or "").strip(), flags=re.I)
    s = re.sub(r"^agency\s+", "", s, flags=re.I).strip()
    if not s:
        return ""
    low = s.lower()
    if "not yet certified" in low:
        return "not yet certified"
    if "authoriz" in low:
        return "authorized"
    if "in process" in low or "in-process" in low:
        return "in process"
    if "initial implementation" in low:
        return "initial implementation"
    return low


def filed_cell(value: str | None) -> str:
    text = cell(value)
    if not value:
        return f'<td class="empty">{text}</td>'
    return f"<td>{text}</td>"


def keep_marketplace_product(item: dict) -> bool:
    """A marketplace listing with an offering is on file, authorized or not."""
    if not isinstance(item, dict):
        return False
    return bool(str(item.get("offering") or "").strip())


def merge_fedramp(existing, dump) -> dict | None:
    """Join the dump onto the file. Do not drop not-yet-certified rows."""
    if not isinstance(dump, dict) or not dump:
        return existing if isinstance(existing, dict) else None
    if not isinstance(existing, dict) or not existing:
        return dump
    seen: dict[str, dict] = {}
    for item in list(existing.get("products") or []) + list(dump.get("products") or []):
        if not keep_marketplace_product(item):
            continue
        pid = str(item.get("id") or item.get("fedramp_id") or item.get("offering") or "").strip()
        if pid not in seen:
            seen[pid] = item
        else:
            seen[pid] = {**seen[pid], **item}
    out = {**existing, **dump}
    out["products"] = list(seen.values())
    return out


def attach_fedramp_dump(companies: list[dict]) -> None:
    """Rematch marketplace rows by slug, including initial-implementation listings."""
    path = SITE / "data" / "fedramp.json"
    if not path.exists():
        path = ROOT / "data" / "fedramp.json"
    doc = load_json(path, {})
    by_slug = {
        rec["slug"]: rec
        for rec in (doc.get("companies") or [])
        if rec.get("slug")
    }
    for row in companies:
        slug = row.get("slug")
        dump = by_slug.get(slug)
        if not dump:
            continue
        row["fedramp"] = merge_fedramp(row.get("fedramp"), dump)


def cite_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().removeprefix("www.")
        path = parsed.path or ""
        if path == "/" and not parsed.query:
            path = ""
        query = f"?{parsed.query}" if parsed.query else ""
        return f"{host}{path}{query}" or url
    except Exception:
        return url


GATE_HTML = """<div class="gate" id="gate" hidden>
      <label class="turn">
        <input type="checkbox" id="gate-box">
        <span class="turn-box" aria-hidden="true"></span>
        <span>I am human</span>
      </label>
      <p class="gate-status" id="gate-status"></p>
    </div>"""


def fedramp_block(row: dict, generated_at: str = "") -> str:
    fed = row.get("fedramp") if isinstance(row.get("fedramp"), dict) else None
    products = [
        p for p in (fed or {}).get("products") or []
        if str(p.get("offering") or "").strip()
    ]
    extras = []
    phase = ""
    authz = None
    if fed:
        phase = str(fed.get("phase") or "").strip()
        authz = fed.get("authorizations")
        if products and not phase:
            phase = str(products[0].get("phase") or "").strip()
        if products and authz is None:
            authz = products[0].get("authorizations")
    if phase:
        extras.append(escape(phase.lower()))
    if authz is not None:
        extras.append(f"authorizations {escape(str(authz))}")
    cite = (
        f'Filed from the <a href="{escape(FEDRAMP_MARKET)}">FedRAMP Marketplace</a>'
    )
    if extras:
        cite = cite + " · " + " · ".join(extras)
    caption = f'<p class="src-line">{cite}.</p>'
    if products:
        rows = []
        for p in products:
            offering = str(p.get("offering") or "").strip()
            href = str(p.get("url") or "").strip() or FEDRAMP_MARKET
            rows.append(
                f'<tr><td><a href="{escape(href)}">{escape(offering)}</a></td>'
                f"<td>{cell(fedramp_status_word(p.get('status') or ''))}</td>"
                f"{filed_cell(str(p.get('impact_level') or '').strip())}"
                f"{filed_cell(fmt_day(p.get('auth_date') or ''))}</tr>"
            )
        body = "".join(rows)
    else:
        body = f"<tr><td colspan=\"4\">{cell(None)}</td></tr>"
    lines = [
        '    <p class="sec-kicker">FedRAMP</p>',
        f"    {caption}",
        '    <table class="inst filed">',
        '      <thead><tr><th scope="col">Offering</th><th scope="col">Status</th><th scope="col">Impact level</th><th scope="col">Auth date</th></tr></thead>',
        f"      <tbody>{body}</tbody>",
        "    </table>",
    ]
    return "\n".join(lines) + "\n"


def processor_href(p: dict) -> str | None:
    """Dossier if on the register; else the map node. Never invent a page."""
    slug = str(p.get("slug") or "").strip()
    if slug:
        return f"./{slug}.html"
    nid = str(p.get("id") or "").strip()
    if nid:
        return f"../graph.html#p={nid}"
    return None


def processor_cell(p: dict) -> str:
    name = escape(p["name"])
    href = processor_href(p)
    if href:
        return f'<a href="{escape(href)}">{name}</a>'
    return name


def processors_block(procs: list[dict], generated_at: str = "", list_url: str = "") -> str:
    if procs:
        proc_rows = "".join(f"<tr><td>{processor_cell(p)}</td></tr>" for p in procs)
        urls = []
        for p in procs:
            u = str(p.get("source_url") or "").strip()
            if u and u not in urls:
                urls.append(u)
        if not urls and list_url:
            urls.append(list_url)
        cite = ""
        if urls:
            cites = " · ".join(official_a(u, cite_url(u)) for u in urls)
            cite = f'    <p class="src-line">Filed from {cites}.</p>\n'
        return (
            '    <p class="sec-kicker">Named processors</p>\n'
            f"{cite}"
            '    <table class="inst filed">\n'
            '      <thead><tr><th scope="col">Processor</th></tr></thead>\n'
            f"      <tbody>{proc_rows}</tbody>\n"
            "    </table>"
        )
    if list_url:
        shown = cite_url(list_url)
        return (
            '    <p class="sec-kicker">Named processors</p>\n'
            f'    <p class="src-line">list on file · names not extracted · '
            f'{official_a(list_url, shown)}</p>'
        )
    return (
        '    <p class="sec-kicker">Named processors</p>\n'
        '    <table class="inst filed">\n'
        '      <thead><tr><th scope="col">Processor</th></tr></thead>\n'
        f"      <tbody><tr><td>{cell(None)}</td></tr></tbody>\n"
        "    </table>"
    )


def fedramp_spine(row: dict) -> str:
    fed = row.get("fedramp") if isinstance(row.get("fedramp"), dict) else None
    products = [
        p for p in (fed or {}).get("products") or []
        if str(p.get("offering") or "").strip()
    ]
    if not products:
        return spine_item("FedRAMP", "not on file · unknown · marketplace observation only", "unknown")
    items = []
    for p in products:
        offering = str(p.get("offering") or "").strip()
        status = str(p.get("status") or "").strip() or "unknown"
        level = str(p.get("impact_level") or "").strip() or "unknown"
        auth = fmt_day(p.get("auth_date") or "") or "date not on file"
        href = str(p.get("url") or "").strip() or FEDRAMP_MARKET
        items.append(
            spine_item(
                escape(offering),
                f"FedRAMP marketplace · {escape(status)} · {escape(level)} · last reviewed {escape(auth)} · "
                f'<a href="{escape(href)}">View source</a>',
                "source",
            )
        )
    return "".join(items)


def mast(active: str, prefix: str) -> str:
    def link(href: str, word: str, key: str) -> str:
        cls = ' class="on"' if key == active else ""
        return f'<a href="{prefix}{href}"{cls}>{word}</a>'
    nav_label = "Pages" if not active else "Companies"
    return f"""  <a class="skip" href="#main">Skip to the record</a>
  <header class="mast">
    <a class="wordmark" href="{prefix}">opentrust<span class="wm-dot">.</span>center</a>
    <nav class="docket" aria-label="{nav_label}">
      {link("", "Companies", "register")}
      {link("graph.html", "Subprocessor Map", "subprocessors")}
      {link("attestations.html", "Frameworks", "marks")}
    </nav>
  </header>"""


def cell(value: str | None, italic_if_empty: bool = True) -> str:
    if value:
        return escape(value)
    if italic_if_empty:
        return '<span class="absent">not on file</span>'
    return "—"


def dossier_issue_line(generated_at: str, slug: str = "") -> str:
    day = fmt_day(generated_at) or "—"
    when = fmt_when(generated_at) or "—"
    bits = [f"issue {day}", f"last probed {when}"]
    return " · ".join(bits)


def snapshot_line(generated_at: str, on_file: int, not_on: int, extra: str = "") -> str:
    day = fmt_day(generated_at) or "—"
    when = fmt_when(generated_at) or "—"
    bits = [
        f"issue {day}",
        f"{on_file} on file",
        f"{not_on} not on file",
        f"last probed {when}",
        extra,
    ]
    return " · ".join(b for b in bits if b)


def spine_item(title: str, meta: str, kind: str = "source") -> str:
    return (
        f'<li class="spine-item {escape(kind)}">'
        f'<span class="spine-node" aria-hidden="true"></span>'
        f'<p class="claim-name">{title}</p>'
        f'<p class="claim-meta">{meta}</p>'
        f"</li>"
    )


def display_file_tier(tier: str) -> str:
    if tier == "on-file":
        return "on file"
    return tier or "silent"


def dossier_html(row: dict, generated_at: str, snapshot: str = "") -> str:
    name = row["name"]
    slug = row["slug"]
    domain = row.get("domain") or ""
    found = bool(row.get("found"))
    url = row.get("trust_url") or ""
    disc = row["disclosure"]
    tier = display_file_tier(disc["tier"])
    file_cls = "file-word silent" if disc["tier"] == "silent" else "file-word"
    title = f"{name} — opentrust.center"
    desc = "A database of each company's public trust ledger. Official pages, marks, DPA, subprocessors, years. On file, or not."
    year = row.get("founded_year")
    year_src = row.get("founded_source")
    if year:
        year_html = f'{year} · <a href="{escape(year_src)}">source</a>' if year_src else str(year)
    else:
        year_html = '<span class="absent">not on file</span>'

    atts = row.get("attestations") or []
    if atts:
        mark_list = (
            '<ul class="mark-list">'
            + "".join(
                f'<li><a href="../attestations.html#{escape(a["id"] or "")}">{escape(a["name"])}</a></li>'
                if a.get("id")
                else f"<li>{escape(a['name'])}</li>"
                for a in atts
            )
            + "</ul>"
        )
    else:
        mark_list = '<p class="absent">not on file</p>'

    inst = row.get("instruments") or {}
    inst_rows = []
    labels = {
        "trust": "trust",
        "security": "security",
        "privacy": "privacy",
        "dpa": "DPA",
        "subprocessors": "subprocessors",
        "status": "status",
        "bounty": "bounty / security.txt",
    }
    for key in INSTRUMENTS:
        rec = inst.get(key)
        label = labels[key]
        if rec and rec.get("url"):
            shown = rec.get("host") or display_host(rec["url"], domain)
            seen = fmt_day((rec.get("seen") or "") + "T00:00:00Z") if rec.get("seen") else "—"
            inst_rows.append(
                f"<tr><td>{escape(label)}</td><td>{official_a(rec['url'], shown)}</td>"
                f"<td>{escape(seen)}</td></tr>"
            )
        else:
            inst_rows.append(
                f'<tr><td>{escape(label)}</td><td><span class="absent">not on file</span></td><td>—</td></tr>'
            )

    procs = row.get("processors") or []
    list_url = ""
    sub = inst.get("subprocessors")
    if isinstance(sub, dict) and sub.get("url"):
        list_url = sub["url"]
    clerk = row.get("summary") or ""
    clerk_html = f'<p class="clerk">{link_mark_words(clerk, atts)}</p>' if clerk else ""
    outbound = (
        f'<a class="official" href="{escape(url)}" rel="noopener noreferrer">Official page</a>'
        if found and url
        else '<span class="absent">Official page · not on file</span>'
    )
    need_gate = bool(found and url) or any(
        rec and rec.get("url") for rec in inst.values()
    ) or any(p.get("source_url") for p in procs) or bool(list_url)
    gate = GATE_HTML if need_gate else ""
    claim = f'<a class="perm" href="../claim.html?slug={escape(slug)}">Report a correction</a>'
    issue = dossier_issue_line(generated_at, slug)

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
  <meta name="theme-color" content="#0B1411">
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
  <link rel="icon" href="{FAVICON}" type="image/svg+xml">
  <link rel="stylesheet" href="../styles.css">
</head>
<body class="dossier">
{mast("", "../")}
  <p class="issue">{escape(issue)}</p>
  <main class="file" id="main">
    <p class="crumb"><a href="../">Companies</a> / {escape(slug)}</p>
    <section class="ident">
      <h1>{escape(name)}</h1>
      <p class="ident-meta">{escape(domain)}</p>
      <p class="ident-meta file-line">file <span class="sep">·</span> <span class="{file_cls}">{escape(tier)}</span></p>
      <p class="ident-meta">founded · {year_html}</p>
    </section>

    <p class="sec-kicker">Instruments</p>
    <table class="inst">
      <thead><tr><th scope="col">Instrument</th><th scope="col">Host</th><th scope="col">Last seen</th></tr></thead>
      <tbody>{"".join(inst_rows)}</tbody>
    </table>

    <p class="sec-kicker">Marks</p>
    {mark_list}

    <p class="out">{outbound}</p>
    {gate}

{fedramp_block(row, generated_at)}

{processors_block(procs, generated_at, list_url)}

    {clerk_html}
    <p class="probe">last probed {escape(fmt_when(generated_at))}</p>
    <div class="actions">
      {claim}
      <a class="perm" href="./{escape(slug)}.html">Permalink · c/{escape(slug)}</a>
    </div>
  </main>
  <footer class="colo">
    <p>Disclosure rates the file, not the company. Empty rows print <i>not on file</i>. File tiers are public-file ratings, never company trust.</p>
    <p><a href="../">Companies</a> · <a href="../graph.html">Subprocessor Map</a> · <a href="../attestations.html">Frameworks</a></p>
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


def file_rank_key(row: dict) -> tuple:
    """Transparency first, then years on file. Missing founded_year sorts last."""
    score = int((row.get("disclosure") or {}).get("score") or 0)
    year = row.get("founded_year")
    if year:
        years = SCORE_YEAR - int(year)
        maturity = (0, -years)
    else:
        maturity = (1, 0)
    return (-score, maturity, (row.get("name") or "").lower())


def assign_file_ranks(public_companies: list[dict]) -> None:
    """# is file order. Cloud 100 number stays on list_rank. Do not rewrite enriched.json."""
    for row in public_companies:
        row["list_rank"] = row.get("rank")
    public_companies.sort(key=file_rank_key)
    for i, row in enumerate(public_companies, start=1):
        row["rank"] = i



def name_to_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


def dossier_aliases(row: dict) -> list[str]:
    """Only when the filed slug is not the name people type (Cursor / anysphere)."""
    slug = row.get("slug") or ""
    if slug != "anysphere":
        return []
    alias = name_to_slug(row.get("name") or "")
    if alias and alias != slug:
        return [alias]
    return []

def redirect_dossier_html(row: dict) -> str:
    slug = row["slug"]
    name = row["name"]
    dest = f"{CANON}/c/{slug}.html"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0;url=./{escape(slug)}.html">
  <link rel="canonical" href="{escape(dest)}">
  <title>{escape(name)} — opentrust.center</title>
  <script>location.replace("./{escape(slug)}.html"+location.search+location.hash)</script>
</head>
<body>
  <p><a href="./{escape(slug)}.html">{escape(name)} file · c/{escape(slug)}</a></p>
</body>
</html>
"""


def main() -> int:
    src = SITE / "data" / "enriched.json"
    if not src.exists():
        src = ROOT / "data" / "enriched.json"
    raw = load_json(src, {})
    companies_in = raw.get("companies") or []
    attach_fedramp_dump(companies_in)
    generated_at = raw.get("generated_at") or ""
    sources = raw.get("sources") or [
        {"name": "Forbes Cloud 100 2025", "url": "https://www.forbes.com/lists/cloud100/"},
        {"name": "Public enterprise, security, and AI vendors", "url": None},
    ]

    wires_path = SITE / "data" / "subprocessors.json"
    if not wires_path.exists():
        wires_path = ROOT / "data" / "subprocessors.json"
    edges_doc = load_json(wires_path, {"edges": [], "nodes": []})
    pretty_subprocessor_nodes(edges_doc)
    write_json(wires_path, edges_doc)
    data_wires = ROOT / "data" / "subprocessors.json"
    if data_wires.resolve() != wires_path.resolve() and data_wires.exists():
        other = load_json(data_wires, {"edges": [], "nodes": []})
        pretty_subprocessor_nodes(other)
        write_json(data_wires, other)
    stamp_data_v(generated_at)
    edges = [e for e in (edges_doc.get("edges") or []) if e.get("source_url")]
    nodes = {n["id"]: n for n in (edges_doc.get("nodes") or []) if n.get("id")}
    by_slug = {c["slug"]: c for c in companies_in if c.get("slug")}
    by_domain = {}
    by_name = {}
    for c in companies_in:
        domain = (c.get("domain") or "").lower()
        if domain:
            by_domain[domain] = c["slug"]
        name = str(c.get("name") or "").strip().lower()
        if name and name not in by_name:
            by_name[name] = c["slug"]

    public_companies = [
        enrich_company(row, edges, nodes, by_slug, by_domain, generated_at, by_name)
        for row in companies_in
    ]
    assign_file_ranks(public_companies)
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
    snapshot = snapshot_line(
        generated_at,
        public["found"],
        public["total"] - public["found"],
    )

    out = SITE / "c"
    if out.exists():
        for old in out.glob("*.html"):
            old.unlink()
    out.mkdir(exist_ok=True)
    taken = {row["slug"] for row in public_companies if row.get("slug")}
    extra_urls = []
    for row in public_companies:
        (out / f"{row['slug']}.html").write_text(
            dossier_html(row, generated_at, snapshot),
            encoding="utf-8",
        )
        for alias in dossier_aliases(row):
            if alias in taken:
                continue
            taken.add(alias)
            (out / f"{alias}.html").write_text(redirect_dossier_html(row), encoding="utf-8")
            extra_urls.append(f"{CANON}/c/{alias}.html")

    urls = [
        f"{CANON}/",
        f"{CANON}/graph.html",
        f"{CANON}/attestations.html",
        f"{CANON}/brand.html",
        f"{CANON}/claim.html",
    ]
    for row in public_companies:
        urls.append(f"{CANON}/c/{row['slug']}.html")
    urls.extend(extra_urls)
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
