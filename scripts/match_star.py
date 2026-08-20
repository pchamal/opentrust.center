#!/usr/bin/env python3
"""Match the first-party CSA STAR Registry onto the register.

Source is the public Cloud Security Alliance registry HTML at
https://cloudsecurityalliance.org/star/registry — not a blog, not a
member API. A row is filed only when the registry names a register
company as the CSP. We do not invent Level 1/2, attestation versus
certification, or dates that the card does not print.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SITE = ROOT / "site"

STAR_REGISTRY = "https://cloudsecurityalliance.org/star/registry"
STAR_CACHE = Path("/tmp/star/registry.html")
UA = "opentrust.center/1"
STAR_BASE = "https://cloudsecurityalliance.org"

# Same conservative stem rules as the other marketplace matchers.
LEGAL_SUFFIX = re.compile(
    r"\b(incorporated|inc|llc|ltd|limited|corporation|corp|company|co|"
    r"plc|pbc|gmbh|bv|srl|sa|ag|nv|ab|oy|as|spa|sas|kft|pty|kk)\b\.?",
    re.I,
)
HOLDING = re.compile(r"\b(holdings?|platforms)\b", re.I)
DBA = re.compile(
    r"\s*(?:,)?\s*(?:d/?b/?a|doing business as|a division of|a subsidiary of)\s+",
    re.I,
)
PAREN = re.compile(r"\s*\([^)]*\)\s*")
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

SKIP_LISTING_PATHS = {
    "/star/registry",
    "/star/registry/",
    "/star/registry/star-enabled-solutions",
    "/star/registry/star-enabled-solutions/",
}

CARD_OPEN = re.compile(
    r'<div class="c-card c-card--allow-overflow star-registry-card"',
)
VIEW_LISTING = re.compile(
    r'c-registry-cta">\s*<a[^>]+href="(/star/registry/[^"]+)"[^>]*>\s*View Listing',
    re.I,
)
DISPLAY_NAME = re.compile(r"<p><strong>([^<]+)</strong></p>")
LISTED_SINCE = re.compile(r"Listed Since:</strong>\s*([0-9]{4}-[0-9]{2}-[0-9]{2})")
ATTR = re.compile(r'\b(data-name|data-cloud-services)="([^"]*)"')


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", errors="replace")


def resolve_registry_html() -> str:
    if STAR_CACHE.exists() and STAR_CACHE.stat().st_size > 100_000:
        return STAR_CACHE.read_text(errors="replace")
    html = fetch_text(STAR_REGISTRY)
    STAR_CACHE.parent.mkdir(parents=True, exist_ok=True)
    STAR_CACHE.write_text(html)
    return html


def norm_name(text: str) -> str:
    s = (text or "").lower().replace("&", " and ")
    s = re.sub(r"[/'’™]", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = LEGAL_SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def compact_name(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", norm_name(text))


def csp_name_variants(text: str) -> list[str]:
    raw = re.sub(r"\s+", " ", unescape(text or "").strip())
    if not raw:
        return []
    parts = [p.strip(" ,") for p in DBA.split(raw) if p.strip(" ,")]
    out = []
    for part in parts:
        for cand in (part, PAREN.sub(" ", part).strip()):
            if cand and cand not in out:
                out.append(cand)
    return out or [raw]


def prefix_allowed(longer: str, shorter: str, fluff: set[str]) -> bool:
    """Allow 'Cisco Systems' for Cisco. Do not allow 'Carta Healthcare' for Carta."""
    if not shorter or not longer.startswith(shorter + " ") or len(shorter) < 3:
        return False
    rest = longer[len(shorter) :].split()
    return bool(rest) and all(tok in fluff for tok in rest)


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
                "compact": compact_name(row.get("name") or slug),
            }
            self.companies.append(rec)
            self.by_slug[slug] = rec


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


def score_match(rec: dict, csp: str) -> tuple[int, str] | None:
    """Bind only when the registry CSP name is this register company."""
    name_n = rec["norm"]
    if not name_n:
        return None
    best: tuple[int, str] | None = None
    for variant in csp_name_variants(csp):
        csp_n = norm_name(variant)
        if not csp_n:
            continue
        exact = csp_n == name_n
        compact = (
            rec["compact"]
            and compact_name(variant) == rec["compact"]
            and len(rec["compact"]) >= 6
        )
        prefix = prefix_allowed(csp_n, name_n, PREFIX_FLUFF)
        reverse = prefix_allowed(name_n, csp_n, REVERSE_FLUFF)
        alias_name = any(
            norm_name(a) and norm_name(a) == csp_n
            for a in rec["aliases"]
            if "." not in a
        )
        scored = None
        if exact:
            scored = (300, "name-exact")
        elif compact:
            scored = (280, "name-compact")
        elif prefix or reverse:
            scored = (240, "name-prefix")
        elif alias_name:
            scored = (230, "alias")
        if scored and (best is None or scored[0] > best[0]):
            best = scored
    return best


def pick_company(reg: Register, csp: str) -> tuple[dict, str] | None:
    ranked: list[tuple[int, str, dict]] = []
    for rec in reg.companies:
        scored = score_match(rec, csp)
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


def listing_url(path: str) -> str | None:
    raw = unescape(path or "").strip()
    if not raw:
        return None
    if raw in SKIP_LISTING_PATHS or raw.rstrip("/") in SKIP_LISTING_PATHS:
        return None
    if "star-enabled-solutions" in raw:
        return None
    if not raw.startswith("/star/registry/"):
        return None
    slug = raw[len("/star/registry/") :].strip("/")
    if not slug or "/" in slug.split("/")[0] and slug.split("/")[0] in {"star-enabled-solutions"}:
        return None
    return urljoin(STAR_BASE, raw)


def parse_cards(html: str) -> list[dict]:
    starts = [m.start() for m in CARD_OPEN.finditer(html)]
    listings = []
    seen = set()
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else min(len(html), start + 40_000)
        chunk = html[start:end]
        attrs = {k: unescape(v) for k, v in ATTR.findall(chunk)}
        display = ""
        m = DISPLAY_NAME.search(chunk)
        if m:
            display = unescape(m.group(1)).strip()
        csp = display or (attrs.get("data-name") or "").strip()
        if not csp:
            continue
        href = VIEW_LISTING.search(chunk)
        url = listing_url(href.group(1)) if href else None
        if not url:
            continue
        listed = None
        lm = LISTED_SINCE.search(chunk)
        if lm:
            listed = lm.group(1)
        key = url
        if key in seen:
            continue
        seen.add(key)
        listings.append(
            {
                "csp": csp,
                "offering": csp,
                "listed_since": listed,
                "url": url,
            }
        )
    return listings


def summarize(rec: dict, products: list[dict]) -> dict:
    marketplace = products[0]["url"] if products else STAR_REGISTRY
    return {
        "slug": rec["slug"],
        "name": rec["name"],
        "domain": rec["domain"],
        "offerings": len(products),
        "marketplace": marketplace,
        "source": STAR_REGISTRY,
        "products": products,
    }


def match_list(reg: Register, products: list[dict]) -> tuple[list[dict], list[tuple[str, dict]], int]:
    assigned: dict[str, list[dict]] = defaultdict(list)
    bindings: list[tuple[str, dict]] = []
    checked = 0
    for item in products:
        checked += 1
        picked = pick_company(reg, item.get("csp") or "")
        if not picked:
            continue
        rec, kind = picked
        prod = {k: v for k, v in item.items()}
        prod["match"] = kind
        assigned[rec["slug"]].append(prod)
        bindings.append((rec["slug"], prod))
    out = []
    for slug, prods in assigned.items():
        rec = reg.by_slug[slug]
        prods.sort(key=lambda p: (str(p.get("csp") or "").lower(), str(p.get("url") or "")))
        out.append(summarize(rec, prods))
    out.sort(key=lambda c: c["slug"])
    return out, bindings, checked


def main() -> int:
    register_doc = load_json(SITE / "data" / "enriched.json") or load_json(DATA / "enriched.json") or {}
    companies = register_doc.get("companies") or []
    if not companies:
        print("no register companies", file=__import__("sys").stderr)
        return 1
    reg = Register(companies, merge_aliases())

    html = resolve_registry_html()
    listings = parse_cards(html)
    if not listings:
        print("no STAR registry cards; not filing", file=__import__("sys").stderr)
        return 1

    matched, bindings, checked = match_list(reg, listings)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bound_rows = sum(c["offerings"] for c in matched)
    doc = {
        "source": STAR_REGISTRY,
        "marketplace": STAR_REGISTRY,
        "program": "CSA STAR",
        "publisher": "Cloud Security Alliance",
        "generated_at": now,
        "marketplace_products": len(listings),
        "register_checked": len(reg.companies),
        "register_matched": len(matched),
        "unmatched_marketplace": len(listings) - bound_rows,
        "companies": matched,
    }
    write_json(DATA / "csa-star.json", doc)
    write_json(SITE / "data" / "csa-star.json", doc)

    already = {
        row["slug"]
        for row in companies
        if row.get("slug")
        and any("csa star" in (c or "").lower() for c in (row.get("certs") or []))
    }
    slugs = [c["slug"] for c in matched]
    new_marks = sorted(s for s in slugs if s not in already)
    url_only = sorted(s for s in slugs if s in already)
    missed = sorted(already - set(slugs))

    print(f"star_register_checked {len(reg.companies)}")
    print(f"star_registry_listings {len(listings)}")
    print(f"star_rows_checked {checked}")
    print(f"star_register_matched {len(matched)}")
    print(f"star_new_company_bindings {len(new_marks)}")
    print(f"star_listing_url_on_existing {len(url_only)}")
    print(f"star_prior_mark_not_in_registry {len(missed)}")
    for slug in new_marks:
        rec = next(c for c in matched if c["slug"] == slug)
        urls = ", ".join(p["url"] for p in rec["products"])
        print(f"  + {rec['name']} ({slug}) {urls}")
    for slug in url_only:
        rec = next(c for c in matched if c["slug"] == slug)
        print(f"  = {rec['name']} ({slug}) {rec['products'][0]['url']}")
    for slug in missed:
        name = next((r["name"] for r in companies if r.get("slug") == slug), slug)
        print(f"  ~ {name} ({slug}) prior HTML mark, not on this registry dump")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
