#!/usr/bin/env python3
"""Match first-party StateRAMP (GovRAMP APL) and TX-RAMP lists onto the register.

Sources are the live GovRAMP Authorized Product List and the Texas DIR
TX-RAMP certified-products workbook. A row is filed only when the
marketplace names a register company as the CSP. We do not invent
authorizations, levels, or dates.
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from collections import defaultdict
from datetime import datetime, timezone, date
from html import unescape
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SITE = ROOT / "site"

GOVRAMP_URL = "https://govramp.org/program-participants"
GOVRAMP_CACHE = Path("/tmp/ramp/govramp.html")
TXRAMP_PAGE = "https://dir.texas.gov/resource-library-item/tx-ramp-certified-cloud-products"
TXRAMP_XLSX_RE = re.compile(
    r'href=["\']([^"\']+TX-RAMP[^"\']+\.xlsx)["\']',
    re.I,
)
TXRAMP_CACHE = Path("/tmp/ramp/txramp.xlsx")
TXRAMP_PAGE_CACHE = Path("/tmp/ramp/txramp-page.html")

UA = "opentrust.center/1"

LEGAL_SUFFIX = re.compile(
    r"\b(incorporated|inc|llc|ltd|limited|corporation|corp|company|co|plc)\b\.?",
    re.I,
)
HOLDING = re.compile(r"\b(holdings?|platforms)\b", re.I)
DBA = re.compile(
    r"\s*(?:,)?\s*(?:d/?b/?a|doing business as|a division of|a subsidiary of)\s+",
    re.I,
)
PAREN = re.compile(r"\s*\([^)]*\)\s*")
# Remainder when the marketplace name is longer than the register name.
PREFIX_FLUFF = {
    "ai",
    "america",
    "analytics",
    "cloud",
    "com",
    "communication",
    "communications",
    "digital",
    "federal",
    "global",
    "gov",
    "government",
    "group",
    "hq",
    "information",
    "international",
    "io",
    "lab",
    "labs",
    "net",
    "network",
    "networks",
    "north",
    "payroll",
    "platform",
    "platforms",
    "public",
    "sector",
    "security",
    "service",
    "services",
    "software",
    "solution",
    "solutions",
    "system",
    "systems",
    "tech",
    "technologies",
    "technology",
    "us",
    "usa",
}
# Remainder when the register name is longer. Tight: "Together" is not Together AI.
REVERSE_FLUFF = {
    "com",
    "communications",
    "group",
    "hq",
    "io",
    "net",
    "networks",
    "software",
    "systems",
    "tech",
    "technologies",
    "technology",
}
GENERIC_HOST = {
    "gmail.com",
    "googlemail.com",
    "outlook.com",
    "hotmail.com",
    "yahoo.com",
    "icloud.com",
    "aol.com",
    "govramp.org",
    "stateramp.org",
    "dir.texas.gov",
    "texas.gov",
}

XLSX_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def fetch_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=90) as resp:
        return resp.read()


def fetch_text(url: str) -> str:
    return fetch_bytes(url).decode("utf-8", errors="replace")


def host_of(url: str) -> str:
    text = (url or "").strip()
    if not text:
        return ""
    if "://" not in text:
        text = "https://" + text
    try:
        host = (urlparse(text).hostname or "").lower()
    except Exception:
        return ""
    return host.removeprefix("www.")


def host_matches(host: str, domain: str) -> bool:
    host = (host or "").lower().removeprefix("www.")
    domain = (domain or "").lower().removeprefix("www.")
    if not host or not domain:
        return False
    if host == domain or host.endswith("." + domain):
        return True
    if domain.endswith("." + host):
        return True
    return False


def norm_name(text: str) -> str:
    s = (text or "").lower().replace("&", " and ")
    s = re.sub(r"[/'’]", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = LEGAL_SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def csp_name_variants(text: str) -> list[str]:
    """CSP legal line plus a d/b/a, if the marketplace printed one."""
    raw = re.sub(r"\s+", " ", (text or "").strip())
    if not raw:
        return []
    parts = [p.strip(" ,") for p in DBA.split(raw) if p.strip(" ,")]
    out = []
    for part in parts:
        for cand in (part, PAREN.sub(" ", part).strip()):
            if cand and cand not in out:
                out.append(cand)
    return out or [raw]


def parse_date(raw) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in {"n/a", "none", "null", "not active", "-"}:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        return text
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", text)
    if m:
        month, day, year = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None
    if re.match(r"^\d+(\.\d+)?$", text):
        try:
            serial = float(text)
            if 20000 <= serial <= 80000:
                origin = date(1899, 12, 30)
                return date.fromordinal(origin.toordinal() + int(serial)).isoformat()
        except ValueError:
            return None
    return None


def clean_level(raw) -> str | None:
    text = re.sub(r"\s+", " ", str(raw or "").strip())
    if not text or text.lower() in {"n/a", "none", "null", "unknown", "-"}:
        return None
    return text


def prefer_operating_company(cands: list[dict]) -> list[dict]:
    if len(cands) <= 1:
        return cands
    operating = [
        c
        for c in cands
        if not HOLDING.search(c["name"])
        and not c["slug"].endswith("-holdings")
        and not c["slug"].endswith("-holding")
    ]
    return operating or cands


class Register:
    def __init__(self, companies: list[dict], aliases_by_slug: dict[str, list[str]]):
        self.companies = []
        self.by_slug = {}
        for row in companies:
            slug = row.get("slug")
            if not slug:
                continue
            domain = (row.get("domain") or "").lower().removeprefix("www.")
            aliases = []
            for alias in list(row.get("aliases") or []) + list(aliases_by_slug.get(slug) or []):
                a = str(alias).lower().removeprefix("www.")
                if a and a not in aliases:
                    aliases.append(a)
            rec = {
                "slug": slug,
                "name": row.get("name") or slug,
                "domain": domain,
                "aliases": aliases,
                "norm": norm_name(row.get("name") or slug),
            }
            self.companies.append(rec)
            self.by_slug[slug] = rec

    def domains_of(self, rec: dict) -> list[str]:
        out = []
        for item in [rec["domain"], *rec["aliases"]]:
            if item and item not in out and "." in item:
                out.append(item)
        return out


def prefix_allowed(longer: str, shorter: str, website_hit: bool, fluff: set[str]) -> bool:
    """Allow 'Cisco Systems' for Cisco. Do not allow 'Carta Healthcare' for Carta."""
    if not shorter or not longer.startswith(shorter + " ") or len(shorter) < 3:
        return False
    rest = longer[len(shorter) :].split()
    if website_hit:
        return True
    return bool(rest) and all(tok in fluff for tok in rest)


def score_match(reg: Register, rec: dict, csp: str, website: str) -> tuple[int, str] | None:
    """Bind only when the marketplace CSP is this register company."""
    host = host_of(website)
    name_n = rec["norm"]
    if not name_n:
        return None

    website_hit = any(host_matches(host, d) for d in reg.domains_of(rec))
    alias_host = any(host_matches(host, a) for a in rec["aliases"] if "." in a)

    best: tuple[int, str] | None = None
    for variant in csp_name_variants(csp):
        csp_n = norm_name(variant)
        if not csp_n:
            continue
        exact = csp_n == name_n
        prefix = prefix_allowed(csp_n, name_n, website_hit, PREFIX_FLUFF)
        # CSP "Varonis" for register "Varonis Systems". Not "Together" for Together AI.
        reverse = prefix_allowed(name_n, csp_n, website_hit, REVERSE_FLUFF)
        alias_name = any(
            norm_name(a) and norm_name(a) == csp_n
            for a in rec["aliases"]
            if "." not in a
        )

        scored = None
        # A contact-email host is not enough. Vexcel is not Microsoft.
        if exact:
            scored = (420 if website_hit else 300, "website" if website_hit else "name-exact")
        elif prefix or reverse:
            scored = (400 if website_hit else 240, "website" if website_hit else "name-prefix")
        elif alias_name:
            scored = (230, "alias")
        if scored and website_hit and alias_host and not host_matches(host, rec["domain"]):
            scored = (scored[0], "alias")
        if scored and (best is None or scored[0] > best[0]):
            best = scored
    return best


def pick_company(reg: Register, csp: str, website: str) -> tuple[dict, str] | None:
    ranked: list[tuple[int, str, dict]] = []
    for rec in reg.companies:
        scored = score_match(reg, rec, csp, website)
        if scored:
            ranked.append((scored[0], scored[1], rec))
    if not ranked:
        return None
    ranked.sort(key=lambda row: (-row[0], row[2]["slug"]))
    top = ranked[0][0]
    tied = [row for row in ranked if row[0] == top]
    domains = {row[2]["domain"] for row in tied if row[2]["domain"]}
    if len(tied) > 1 and len(domains) == 1:
        preferred = prefer_operating_company([row[2] for row in tied])
        if len(preferred) == 1:
            rec = preferred[0]
            kind = next(row[1] for row in tied if row[2]["slug"] == rec["slug"])
            return rec, kind
    if len(tied) > 1:
        return None
    return tied[0][2], tied[0][1]


def merge_aliases() -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for path in (ROOT / "companies.json", ROOT / "extra-companies.json"):
        for row in load_json(path, []) or []:
            slug = row.get("slug")
            if not slug:
                continue
            for alias in row.get("aliases") or []:
                if alias not in out[slug]:
                    out[slug].append(alias)
    return out


def email_website(email: str) -> str:
    text = unescape(email or "").strip()
    m = re.search(r"([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})", text, re.I)
    if not m:
        return ""
    host = m.group(1).rsplit("@", 1)[-1].lower().removeprefix("www.")
    if host in GENERIC_HOST or host.endswith(".gov") or host.endswith(".edu"):
        return ""
    return "https://" + host


def parse_govramp_meta(td_html: str) -> dict:
    text = unescape(td_html)
    meta = {}
    m = re.search(r"Authorization Date</strong>:\s*([^<]+)", text, re.I)
    if m:
        meta["auth_date"] = parse_date(m.group(1))
    m = re.search(r"SRID#</strong>:\s*([^<]+)", text, re.I)
    if m:
        srid = re.sub(r"\s+", "", m.group(1))
        if re.match(r"^SR\w+$", srid, re.I):
            meta["srid"] = srid
    m = re.search(r"Contact Email</strong>:\s*(.*?)</p>", text, re.I | re.S)
    if m:
        meta["website"] = email_website(m.group(1))
    return meta


def cell_attr(td: str, name: str) -> str:
    m = re.search(rf'{name}="([^"]*)"', td)
    return unescape(m.group(1)) if m else ""


def load_govramp(html: str) -> list[dict]:
    tables = re.findall(
        r'(<table class="govramp-table(?:(?!partner-directory)[^"])*"[^>]*>.*?</table>)',
        html,
        re.S | re.I,
    )
    if not tables:
        raise SystemExit("GovRAMP APL table not found")
    # First product table is the Authorized Product List.
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tables[0], re.S | re.I)[1:]
    products = []
    seen = set()
    for row in rows:
        tds = re.findall(r"<td[^>]*>.*?</td>", row, re.S | re.I)
        rec = {}
        for td in tds:
            col = cell_attr(td, "data-column")
            val = cell_attr(td, "data-value")
            if col:
                rec[col] = val
        csp = (rec.get("organization_name") or "").strip()
        offering = (rec.get("service_offering") or "").strip()
        if not csp or not offering:
            continue
        meta = parse_govramp_meta(tds[0]) if tds else {}
        srid = meta.get("srid")
        key = srid or f"{norm_name(csp)}|{norm_name(offering)}"
        if key in seen:
            continue
        seen.add(key)
        products.append(
            {
                "id": srid,
                "offering": offering,
                "csp": csp,
                "status": clean_level(rec.get("status")),
                "impact_level": clean_level(rec.get("impact_level")),
                "auth_date": meta.get("auth_date"),
                "website": meta.get("website") or None,
                "service_model": clean_level(rec.get("service_model")),
            }
        )
    return products


def colrow(ref: str) -> tuple[str, int]:
    m = re.match(r"([A-Z]+)(\d+)", ref)
    if not m:
        return "", 0
    return m.group(1), int(m.group(2))


def xlsx_shared_strings(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    out = []
    for si in root.findall("m:si", XLSX_NS):
        out.append("".join(t.text or "" for t in si.findall(".//m:t", XLSX_NS)))
    return out


def xlsx_cell_value(cell, shared: list[str]) -> str:
    kind = cell.attrib.get("t")
    v = cell.find("m:v", XLSX_NS)
    if v is None or v.text is None:
        inline = cell.find("m:is", XLSX_NS)
        if inline is not None:
            return "".join(t.text or "" for t in inline.findall(".//m:t", XLSX_NS))
        return ""
    if kind == "s":
        return shared[int(v.text)]
    return v.text


def load_txramp(xlsx_bytes: bytes) -> list[dict]:
    z = zipfile.ZipFile(io.BytesIO(xlsx_bytes))
    shared = xlsx_shared_strings(z)
    sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows: dict[int, dict[str, str]] = {}
    for cell in sheet.findall(".//m:c", XLSX_NS):
        ref = cell.attrib.get("r")
        if not ref:
            continue
        col, row = colrow(ref)
        if not col or not row:
            continue
        rows.setdefault(row, {})[col] = xlsx_cell_value(cell, shared)
    header = rows.get(1) or {}
    labels = {col: re.sub(r"\s+", " ", (val or "").strip()) for col, val in header.items()}
    needed = {
        "offering": "Engagement Name",
        "id": "TX-RAMP Certification ID",
        "csp": "3rd party",
        "status": "Certification Status",
        "expiration": "Certification Expiration Date",
    }
    # Header in the workbook has a double space in the ID column.
    col_of = {}
    for key, label in needed.items():
        for col, got in labels.items():
            compact = re.sub(r"\s+", " ", got)
            if compact.lower() == label.lower() or compact.lower() == "tx-ramp certification id":
                if key == "id" and "certification" in compact.lower() and "id" in compact.lower():
                    col_of[key] = col
                elif key != "id" and compact.lower() == label.lower():
                    col_of[key] = col
    missing = [k for k in needed if k not in col_of]
    if missing:
        raise SystemExit(f"TX-RAMP workbook missing columns: {missing} got {labels}")
    products = []
    seen = set()
    for r in sorted(rows):
        if r == 1:
            continue
        rec = rows[r]
        offering = (rec.get(col_of["offering"]) or "").strip()
        csp = (rec.get(col_of["csp"]) or "").strip()
        pid = re.sub(r"\s+", "", rec.get(col_of["id"]) or "")
        if not offering or not csp:
            continue
        key = pid or f"{norm_name(csp)}|{norm_name(offering)}"
        if key in seen:
            continue
        seen.add(key)
        status = clean_level(rec.get(col_of["status"]))
        level = None
        if status and re.match(r"^level\s*[12]$", status, re.I):
            level = status
        products.append(
            {
                "id": pid or None,
                "offering": offering,
                "csp": csp,
                "status": status,
                "level": level,
                "auth_date": None,
                "expiration_date": parse_date(rec.get(col_of["expiration"])),
                "website": None,
            }
        )
    return products


def resolve_txramp_xlsx() -> tuple[bytes, str]:
    if TXRAMP_CACHE.exists():
        page = TXRAMP_PAGE_CACHE.read_text(errors="replace") if TXRAMP_PAGE_CACHE.exists() else ""
        href = None
        m = TXRAMP_XLSX_RE.search(page)
        if m:
            href = m.group(1)
        url = TXRAMP_PAGE
        if href:
            url = href if href.startswith("http") else "https://dir.texas.gov" + href
        return TXRAMP_CACHE.read_bytes(), url
    page = fetch_text(TXRAMP_PAGE)
    TXRAMP_PAGE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TXRAMP_PAGE_CACHE.write_text(page)
    m = TXRAMP_XLSX_RE.search(page)
    if not m:
        raise SystemExit("TX-RAMP xlsx href not found on DIR page")
    href = m.group(1)
    url = href if href.startswith("http") else "https://dir.texas.gov" + href
    blob = fetch_bytes(url)
    TXRAMP_CACHE.write_bytes(blob)
    return blob, url


def resolve_govramp_html() -> str:
    if GOVRAMP_CACHE.exists():
        return GOVRAMP_CACHE.read_text(errors="replace")
    html = fetch_text(GOVRAMP_URL)
    GOVRAMP_CACHE.parent.mkdir(parents=True, exist_ok=True)
    GOVRAMP_CACHE.write_text(html)
    return html


def summarize(rec: dict, products: list[dict], marketplace: str, source: str) -> dict:
    levels = []
    for p in products:
        lv = p.get("impact_level") or p.get("level")
        if lv and lv not in levels:
            levels.append(lv)
    return {
        "slug": rec["slug"],
        "name": rec["name"],
        "domain": rec["domain"],
        "offerings": len(products),
        "levels": levels,
        "marketplace": marketplace,
        "source": source,
        "products": products,
    }


def match_list(
    reg: Register,
    products: list[dict],
    marketplace: str,
    source: str,
    match_field_website: bool,
) -> tuple[list[dict], list[tuple[str, dict]], int]:
    assigned: dict[str, list[dict]] = defaultdict(list)
    new_bindings: list[tuple[str, dict]] = []
    checked = 0
    for item in products:
        checked += 1
        website = item.get("website") or "" if match_field_website else ""
        picked = pick_company(reg, item.get("csp") or "", website)
        if not picked:
            continue
        rec, kind = picked
        prod = {k: v for k, v in item.items()}
        prod["match"] = kind
        prod["url"] = marketplace
        assigned[rec["slug"]].append(prod)
        new_bindings.append((rec["slug"], prod))
    out = []
    for slug, prods in assigned.items():
        rec = reg.by_slug[slug]
        prods.sort(key=lambda p: (str(p.get("offering") or "").lower(), str(p.get("id") or "")))
        out.append(summarize(rec, prods, marketplace, source))
    out.sort(key=lambda c: c["slug"])
    return out, new_bindings, checked


def report(label: str, products: int, matched: list[dict], bindings: list[tuple[str, dict]], checked: int, register_n: int) -> None:
    slugs = sorted({slug for slug, _ in bindings})
    print(f"{label}_register_checked {register_n}")
    print(f"{label}_marketplace_products {products}")
    print(f"{label}_rows_checked {checked}")
    print(f"{label}_register_matched {len(matched)}")
    print(f"{label}_new_company_bindings {len(slugs)}")
    print(f"{label}_new_product_bindings {len(bindings)}")
    for slug in slugs:
        rec = next(c for c in matched if c["slug"] == slug)
        ids = ", ".join(str(p.get("id") or p.get("offering")) for p in rec["products"])
        print(f"  + {rec['name']} ({slug}) {ids}")


def main() -> int:
    register_doc = load_json(SITE / "data" / "enriched.json") or load_json(DATA / "enriched.json") or {}
    companies = register_doc.get("companies") or []
    if not companies:
        print("no register companies", file=__import__("sys").stderr)
        return 1
    reg = Register(companies, merge_aliases())

    gov_html = resolve_govramp_html()
    st_products = load_govramp(gov_html)
    if not st_products:
        print("no StateRAMP/GovRAMP APL rows; not filing", file=__import__("sys").stderr)
        return 1

    tx_bytes, tx_xlsx_url = resolve_txramp_xlsx()
    tx_products = load_txramp(tx_bytes)
    if not tx_products:
        print("no TX-RAMP workbook rows; not filing", file=__import__("sys").stderr)
        return 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    st_matched, st_new, st_checked = match_list(
        reg, st_products, GOVRAMP_URL, GOVRAMP_URL, match_field_website=True
    )
    tx_matched, tx_new, tx_checked = match_list(
        reg, tx_products, TXRAMP_PAGE, tx_xlsx_url, match_field_website=False
    )

    st_doc = {
        "source": GOVRAMP_URL,
        "marketplace": GOVRAMP_URL,
        "program": "StateRAMP",
        "publisher": "GovRAMP (StateRAMP Inc., d/b/a GovRAMP)",
        "generated_at": now,
        "marketplace_products": len(st_products),
        "register_matched": len(st_matched),
        "unmatched_marketplace": len(st_products) - sum(c["offerings"] for c in st_matched),
        "companies": st_matched,
    }
    tx_doc = {
        "source": tx_xlsx_url,
        "marketplace": TXRAMP_PAGE,
        "program": "TX-RAMP",
        "publisher": "Texas Department of Information Resources",
        "generated_at": now,
        "marketplace_products": len(tx_products),
        "register_matched": len(tx_matched),
        "unmatched_marketplace": len(tx_products) - sum(c["offerings"] for c in tx_matched),
        "companies": tx_matched,
    }

    write_json(DATA / "stateramp.json", st_doc)
    write_json(SITE / "data" / "stateramp.json", st_doc)
    write_json(DATA / "txramp.json", tx_doc)
    write_json(SITE / "data" / "txramp.json", tx_doc)

    report("stateramp", len(st_products), st_matched, st_new, st_checked, len(reg.companies))
    report("txramp", len(tx_products), tx_matched, tx_new, tx_checked, len(reg.companies))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
