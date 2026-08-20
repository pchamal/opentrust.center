#!/usr/bin/env python3
"""Rematch the FedRAMP Marketplace dump onto the current register.

Source of truth is the public GSA dump (marketplace-fedramp-gov-data).
We file FR ids, offering names, status, and marketplace links when a
listing actually matches a register company. We do not invent
authorizations, impact levels, or auth dates.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SITE = ROOT / "site"
MARKET = "https://www.fedramp.gov/marketplace/products/"
DUMP_URL = "https://raw.githubusercontent.com/FedRAMP/marketplace-fedramp-gov-data/main/data.json"
FRC_URL = "https://raw.githubusercontent.com/FedRAMP/marketplace-fedramp-gov-data/main/fedramp-frc-cso-pkg.json"
CURSOR_ID = "FR2631054484"

LEGAL_SUFFIX = re.compile(
    r"\b(incorporated|inc|llc|ltd|limited|corporation|corp|company|co|plc)\b\.?",
    re.I,
)
HOLDING = re.compile(r"\b(holdings?|platforms)\b", re.I)
PLACEHOLDER_ID = re.compile(
    r"^(tbd|todo|xx-|not yet|pending|interim|$)",
    re.I,
)
WORD = re.compile(r"[a-z0-9]+")


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "opentrust.center/1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


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


def norm_name(text: str) -> str:
    s = (text or "").lower().replace("&", " and ")
    s = re.sub(r"[/'’]", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = LEGAL_SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(text: str) -> list[str]:
    return WORD.findall(norm_name(text))


def parse_date(raw) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in {"not active", "n/a", "none", "no frr date", "not in process"}:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return text[:10]
    return None


def clean_level(raw) -> str | None:
    text = str(raw or "").strip()
    if not text or text.lower() in {"not active", "n/a", "none", "unknown"}:
        return None
    return text


def clean_auth_type(raw) -> str | None:
    text = str(raw or "").strip()
    if not text or text.lower() in {"not active", "n/a", "none", "not in process"}:
        return None
    return text


def collapse_level(level: str) -> str | None:
    if level in ("Low", "20x Low"):
        return "Low"
    if level in ("Moderate", "20x Moderate"):
        return "Moderate"
    if level == "High":
        return "High"
    return None


def status_bucket(status: str) -> str:
    low = (status or "").lower()
    if "authoriz" in low:
        return "authorized"
    if any(
        key in low
        for key in (
            "in process",
            "in-process",
            "ready",
            "not yet certified",
            "initial implementation",
        )
    ):
        return "in_process"
    return "other"


def usable_product_id(pid: str) -> bool:
    """Only ids the marketplace can actually list. Do not invent FR numbers."""
    text = (pid or "").strip()
    if not text or PLACEHOLDER_ID.search(text):
        return False
    if " " in text or "/" in text:
        return False
    # Live marketplace product ids look like FR2631054484, F1603047866, AGENCYAMAZONEW.
    if re.match(r"^FR?\d+[A-Za-z0-9]*$", text):
        return True
    if re.match(r"^[A-Z][A-Z0-9]{5,}$", text) and text in {"AGENCYAMAZONEW", "MSO365MTA", "MSO365MT", "SOCRATA"}:
        return True
    return False


def marketplace_url(pid: str, trailing_slash: bool = False) -> str:
    base = f"{MARKET.rstrip('/')}/{pid}"
    return base + ("/" if trailing_slash else "")


def host_matches(host: str, domain: str) -> bool:
    host = (host or "").lower().removeprefix("www.")
    domain = (domain or "").lower().removeprefix("www.")
    if not host or not domain:
        return False
    if host == domain or host.endswith("." + domain):
        return True
    # company domain is a host under the product site (aws.amazon.com vs amazon.com)
    if domain.endswith("." + host):
        return True
    return False


def prefer_operating_company(cands: list[dict]) -> list[dict]:
    if len(cands) <= 1:
        return cands
    operating = [c for c in cands if not HOLDING.search(c["name"]) and not c["slug"].endswith("-holdings") and not c["slug"].endswith("-holding")]
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


def score_match(reg: Register, rec: dict, csp: str, offering: str, website: str) -> tuple[int, str] | None:
    host = host_of(website)
    csp_n = norm_name(csp)
    offer_n = norm_name(offering)
    name_n = rec["norm"]
    if not name_n:
        return None

    website_hit = any(host_matches(host, d) for d in reg.domains_of(rec))
    exact = bool(csp_n and csp_n == name_n)
    prefix = bool(csp_n and name_n and csp_n.startswith(name_n + " ") and len(name_n) >= 3)
    offer_exact = bool(offer_n and (offer_n == name_n or offer_n.startswith(name_n + " ")))
    alias_host = any(host_matches(host, a) for a in rec["aliases"] if "." in a)
    alias_name = any(norm_name(a) and norm_name(a) == csp_n for a in rec["aliases"] if "." not in a)

    # Whole-word CSP contains, for longer names only ("A Trimble Company").
    # Do not scan the offering — "Managed Microsoft 365" is not a Microsoft CSP.
    contains = False
    if not exact and not prefix and len(name_n) >= 5:
        pat = re.compile(rf"\b{re.escape(name_n)}\b")
        contains = bool(pat.search(csp_n))

    if website_hit and (exact or prefix or offer_exact or len(name_n) >= 4):
        kind = "alias" if alias_host and not host_matches(host, rec["domain"]) else "website"
        return (400 if exact or prefix else 360, kind)
    if exact:
        return (300, "name-exact")
    if prefix:
        return (240, "name-prefix")
    if alias_name:
        return (230, "alias")
    if website_hit and len(name_n) >= 3:
        return (220, "website")
    if contains:
        return (160, "name-prefix")
    if offer_exact and len(name_n) >= 5:
        return (140, "name-exact")
    return None


def pick_company(reg: Register, csp: str, offering: str, website: str, locked_slug: str | None) -> tuple[dict, str] | None:
    if locked_slug and locked_slug in reg.by_slug:
        rec = reg.by_slug[locked_slug]
        scored = score_match(reg, rec, csp, offering, website)
        return rec, (scored[1] if scored else "vendor")

    ranked: list[tuple[int, str, dict]] = []
    for rec in reg.companies:
        scored = score_match(reg, rec, csp, offering, website)
        if scored:
            ranked.append((scored[0], scored[1], rec))
    if not ranked:
        return None
    ranked.sort(key=lambda row: (-row[0], row[2]["slug"]))
    top = ranked[0][0]
    tied = [row for row in ranked if row[0] == top]
    # Same-domain holding company vs operating company.
    domains = {row[2]["domain"] for row in tied if row[2]["domain"]}
    if len(tied) > 1 and len(domains) == 1:
        preferred = prefer_operating_company([row[2] for row in tied])
        if len(preferred) == 1:
            rec = preferred[0]
            kind = next(row[1] for row in tied if row[2]["slug"] == rec["slug"])
            return rec, kind
    if len(tied) > 1:
        # Ambiguous: do not invent a binding.
        return None
    return tied[0][2], tied[0][1]


def product_from_marketplace(item: dict, match: str) -> dict:
    pid = str(item.get("id") or "").strip()
    offering = str(item.get("service_offering") or item.get("cso") or item.get("name") or "").strip()
    return {
        "fedramp_id": pid,
        "offering": offering,
        "csp": str(item.get("csp") or "").strip(),
        "status": str(item.get("status") or "").strip() or None,
        "impact_level": clean_level(item.get("impact_level")),
        "auth_type": clean_auth_type(item.get("auth_type")),
        "auth_date": parse_date(item.get("auth_date") or item.get("fedramp_auth")),
        "website": str(item.get("website") or "").strip() or None,
        "match": match,
    }


def product_from_frc(row: dict, match: str) -> dict | None:
    sid = row.get("serviceIdentification") or {}
    pid = str(sid.get("fedRampPackageId") or row.get("id") or "").strip()
    if not usable_product_id(pid):
        return None
    offering = str(sid.get("serviceName") or "").strip()
    if not offering:
        return None
    docs = row.get("documentationOverview") or {}
    phase_raw = str(docs.get("status") or "").strip()
    phase = None
    if "initial implementation" in phase_raw.lower():
        phase = "Initial Implementation"
    cert = str(sid.get("certificationType") or "").strip()
    out = {
        "fedramp_id": pid,
        "offering": offering,
        "csp": str(sid.get("providerName") or "").strip(),
        "status": "Not yet certified",
        "impact_level": None,
        "auth_type": None,
        "auth_date": None,
        "website": str(sid.get("website") or "").strip() or None,
        "match": match,
        "url": marketplace_url(pid, trailing_slash=(pid == CURSOR_ID)),
    }
    if phase:
        out["phase"] = phase
        out["authorizations"] = 0
    if cert:
        out["certification_profile"] = f"Type {cert}; Path Unknown; Class Unknown"
    return out


def summarize(rec: dict, products: list[dict]) -> dict:
    authorized = in_process = other = 0
    raw_levels: list[str] = []
    auth_levels: list[str] = []
    for p in products:
        bucket = status_bucket(p.get("status") or "")
        if bucket == "authorized":
            authorized += 1
        elif bucket == "in_process":
            in_process += 1
        else:
            other += 1
        lv = clean_level(p.get("impact_level"))
        if lv and lv not in raw_levels:
            raw_levels.append(lv)
        if bucket == "authorized" and lv and lv not in auth_levels:
            auth_levels.append(lv)
    rank = {"High": 6, "20x Moderate": 5, "Moderate": 4, "20x Low": 3, "Low": 2, "LI-SaaS": 1}
    raw_levels.sort(key=lambda lv: (-rank.get(lv, 0), lv))
    levels = []
    for lv in raw_levels:
        bucket = collapse_level(lv)
        if bucket and bucket not in levels:
            levels.append(bucket)
    order = {"High": 0, "Moderate": 1, "Low": 2}
    levels.sort(key=lambda lv: order.get(lv, 9))
    highest_authorized = auth_levels[0] if auth_levels else None
    if highest_authorized:
        highest_authorized = max(auth_levels, key=lambda lv: rank.get(lv, 0))
        # Prefer the collapsed marketplace word when it is a classic level,
        # keep 20x when that is the only authorized level.
        if highest_authorized.startswith("20x ") and any(not x.startswith("20x ") for x in auth_levels):
            highest_authorized = max(
                (x for x in auth_levels if not x.startswith("20x ")),
                key=lambda lv: rank.get(lv, 0),
            )
    highest = highest_authorized or (raw_levels[0] if raw_levels else None)
    first = products[0]
    pid = first.get("fedramp_id") or ""
    market = first.get("url") or marketplace_url(pid, trailing_slash=(pid == CURSOR_ID))
    return {
        "slug": rec["slug"],
        "name": rec["name"],
        "domain": rec["domain"],
        "offerings": len(products),
        "authorized_offerings": authorized,
        "in_process_offerings": in_process,
        "impact_levels": list(raw_levels),
        "highest_authorized": highest_authorized if authorized else None,
        "status_summary": {
            "authorized": authorized,
            "in_process": in_process,
            "other": other,
        },
        "levels": levels,
        "raw_levels": raw_levels,
        "highest": highest,
        "authorized": authorized,
        "in_process": in_process,
        "marketplace": market,
        "products": products,
    }


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


def load_marketplace(path: Path | None) -> tuple[list[dict], str]:
    if path and path.exists():
        doc = load_json(path, {})
    else:
        cached = Path("/tmp/fedramp/data.json")
        doc = load_json(cached, None) or fetch_json(DUMP_URL)
    products = ((doc.get("data") or {}).get("Products") or []) if isinstance(doc, dict) else []
    last = ((doc.get("meta") or {}).get("last_change")) if isinstance(doc, dict) else None
    return products, str(last or "")


def load_frc(path: Path | None) -> list[dict]:
    if path and path.exists():
        doc = load_json(path, {})
    else:
        cached = Path("/tmp/fedramp/fedramp-frc-cso-pkg.json")
        doc = load_json(cached, None) or fetch_json(FRC_URL)
    return ((doc.get("data") or {}).get("frc-cso-pkg") or []) if isinstance(doc, dict) else []


def keep_cursor_product(existing: dict | None, built: dict) -> dict:
    if existing and existing.get("fedramp_id") == CURSOR_ID:
        return existing
    built.setdefault("url", marketplace_url(CURSOR_ID, trailing_slash=True))
    built["match"] = "vendor"
    built.setdefault("status", "Not yet certified")
    built.setdefault("phase", "Initial Implementation")
    built.setdefault("authorizations", 0)
    built.setdefault("impact_level", None)
    built.setdefault("auth_date", None)
    return built


def main() -> int:
    register_doc = load_json(SITE / "data" / "enriched.json") or load_json(DATA / "enriched.json") or {}
    companies = register_doc.get("companies") or []
    if not companies:
        print("no register companies", file=sys.stderr)
        return 1
    existing = load_json(DATA / "fedramp.json") or load_json(SITE / "data" / "fedramp.json") or {}
    existing_by_slug = {c["slug"]: c for c in existing.get("companies") or [] if c.get("slug")}
    locked_by_id = {}
    existing_products_by_id = {}
    for rec in existing.get("companies") or []:
        for prod in rec.get("products") or []:
            pid = str(prod.get("fedramp_id") or "").strip()
            if pid:
                locked_by_id[pid] = rec["slug"]
                existing_products_by_id[pid] = prod

    reg = Register(companies, merge_aliases())
    products, last_change = load_marketplace(None)
    frc_rows = load_frc(None)

    assigned: dict[str, list[dict]] = defaultdict(list)
    seen_ids: set[str] = set()
    new_bindings: list[tuple[str, dict]] = []
    checked = 0

    for item in products:
        checked += 1
        pid = str(item.get("id") or "").strip()
        if not pid or pid in seen_ids:
            continue
        offering = str(item.get("service_offering") or item.get("cso") or item.get("name") or "").strip()
        if not offering:
            continue
        locked = locked_by_id.get(pid)
        picked = pick_company(reg, str(item.get("csp") or ""), offering, str(item.get("website") or ""), locked)
        if not picked:
            continue
        rec, kind = picked
        if locked and rec["slug"] != locked:
            rec = reg.by_slug[locked]
            kind = existing_products_by_id[pid].get("match") or kind
        prod = product_from_marketplace(item, kind)
        if pid == CURSOR_ID:
            prod = keep_cursor_product(existing_products_by_id.get(pid), prod)
        assigned[rec["slug"]].append(prod)
        seen_ids.add(pid)
        if rec["slug"] not in existing_by_slug:
            new_bindings.append((rec["slug"], prod))
        elif pid not in {p.get("fedramp_id") for p in existing_by_slug[rec["slug"]].get("products") or []}:
            new_bindings.append((rec["slug"], prod))

    for row in frc_rows:
        checked += 1
        sid = row.get("serviceIdentification") or {}
        pid = str(sid.get("fedRampPackageId") or row.get("id") or "").strip()
        if pid in seen_ids:
            continue
        locked = locked_by_id.get(pid)
        picked = pick_company(
            reg,
            str(sid.get("providerName") or ""),
            str(sid.get("serviceName") or ""),
            str(sid.get("website") or ""),
            locked,
        )
        if not picked and pid == CURSOR_ID and "anysphere" in reg.by_slug:
            picked = (reg.by_slug["anysphere"], "vendor")
        if not picked:
            continue
        rec, kind = picked
        prod = product_from_frc(row, kind)
        if not prod:
            continue
        if pid == CURSOR_ID:
            prod = keep_cursor_product(existing_products_by_id.get(pid), prod)
        assigned[rec["slug"]].append(prod)
        seen_ids.add(pid)
        if rec["slug"] not in existing_by_slug:
            new_bindings.append((rec["slug"], prod))
        elif pid not in {p.get("fedramp_id") for p in existing_by_slug[rec["slug"]].get("products") or []}:
            new_bindings.append((rec["slug"], prod))

    # Preserve any locked product that vanished from the live dump (Cursor).
    for pid, slug in locked_by_id.items():
        if pid in seen_ids or slug not in reg.by_slug:
            continue
        old = existing_products_by_id.get(pid)
        if old:
            assigned[slug].append(old)
            seen_ids.add(pid)

    out_companies = []
    for slug, prods in assigned.items():
        rec = reg.by_slug[slug]
        # Keep prior product order, then append new ids.
        prior_ids = [p.get("fedramp_id") for p in (existing_by_slug.get(slug) or {}).get("products") or []]
        by_id = {p["fedramp_id"]: p for p in prods if p.get("fedramp_id")}
        ordered = []
        for pid in prior_ids:
            if pid in by_id:
                ordered.append(by_id.pop(pid))
        ordered.extend(by_id[k] for k in sorted(by_id))
        out_companies.append(summarize(rec, ordered))
    out_companies.sort(key=lambda c: c["slug"])

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc = {
        "source": "https://github.com/FedRAMP/marketplace-fedramp-gov-data",
        "marketplace": MARKET,
        "source_last_change": last_change or existing.get("source_last_change"),
        "generated_at": now,
        "marketplace_products": len(products),
        "register_matched": len(out_companies),
        "unmatched_marketplace": max(0, len(products) - sum(c["offerings"] for c in out_companies if True)),
        "companies": out_companies,
    }
    # Unmatched counts only data.json products, not FRC extras.
    matched_market_ids = {
        p["fedramp_id"]
        for c in out_companies
        for p in c["products"]
        if p.get("fedramp_id") in {item.get("id") for item in products}
    }
    doc["unmatched_marketplace"] = len(products) - len(matched_market_ids)

    write_json(DATA / "fedramp.json", doc)
    write_json(SITE / "data" / "fedramp.json", doc)

    new_slugs = sorted({slug for slug, _ in new_bindings})
    print(f"register_checked {len(reg.companies)}")
    print(f"marketplace_products {len(products)}")
    print(f"frc_packages {len(frc_rows)}")
    print(f"rows_checked {checked}")
    print(f"register_matched {len(out_companies)} (was {len(existing_by_slug)})")
    print(f"new_company_bindings {len(new_slugs)}")
    print(f"new_product_bindings {len(new_bindings)}")
    for slug in new_slugs:
        rec = next(c for c in out_companies if c["slug"] == slug)
        ids = ", ".join(p["fedramp_id"] for p in rec["products"])
        print(f"  + {rec['name']} ({slug}) {ids}")
    extra_on_old = [(s, p) for s, p in new_bindings if s in existing_by_slug]
    if extra_on_old:
        print(f"new_offerings_on_existing {len(extra_on_old)}")
        for slug, prod in extra_on_old[:20]:
            print(f"  + {slug} {prod.get('fedramp_id')} {prod.get('offering')}")
    cursor = next((c for c in out_companies if c["slug"] == "anysphere"), None)
    if not cursor or not any(p.get("fedramp_id") == CURSOR_ID for p in cursor["products"]):
        print("ERROR: Cursor FR2631054484 binding missing", file=sys.stderr)
        return 1
    print(f"cursor {CURSOR_ID} kept")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
