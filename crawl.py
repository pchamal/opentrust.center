#!/usr/bin/env python3
"""Pattern-probe public trust centers for the Forbes Cloud 100 (2025)."""

from __future__ import annotations

import json
import re
import ssl
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
UA = "opentrust.center/1.0 (+https://opentrust.center)"
TIMEOUT = 8
WORKERS = 12
MAX_BODY = 32768

SEED_URLS = {
    "anthropic": ["https://trust.anthropic.com/"],
    "ramp": ["https://trust.ramp.com/"],
    "notion": ["https://trust.notion.com/"],
    "abnormal-ai": ["https://security.abnormal.ai/"],
    "attentive": ["https://security.attentive.com/"],
    "arctic-wolf": ["https://trust.arcticwolf.com/"],
    "alphasense": ["https://trust.alpha-sense.com/"],
    "1password": ["https://trust.1password.io/"],
    "vercel": ["https://security.vercel.com/"],
    "airwallex": ["https://security.airwallex.com/"],
    "zapier": ["https://trust.zapier.com/"],
    "algolia": ["https://trust.algolia.com/"],
    "abridge": ["https://trust.abridge.com/"],
    "stripe": ["https://stripe.com/docs/security"],
    "airtable": ["https://airtable.com/company/trust-and-security"],
    "carta": ["https://trust.carta.com/"],
    "postman": ["https://security.postman.com/", "https://trust.postman.com/"],
    "checkr": ["https://trust.checkr.com/", "https://security.checkr.com/"],
    "vanta": ["https://trust.vanta.com/"],
    "microsoft": ["https://www.microsoft.com/en-us/trust-center"],
    "google": ["https://cloud.google.com/security/compliance"],
    "amazon-web-services": ["https://aws.amazon.com/compliance/"],
    "salesforce": ["https://trust.salesforce.com"],
    "oracle": ["https://www.oracle.com/trust/"],
    "sap": ["https://www.sap.com/about/trust-center.html"],
    "ibm": ["https://www.ibm.com/trust"],
    "atlassian": ["https://www.atlassian.com/trust"],
    "slack": ["https://slack.com/trust"],
    "zoom": ["https://www.zoom.com/en/trust-center/"],
    "okta": ["https://trust.okta.com"],
    "cloudflare": ["https://www.cloudflare.com/trust-hub/"],
    "github": ["https://github.com/security"],
    "gitlab": ["https://about.gitlab.com/security/"],
    "snowflake": ["https://www.snowflake.com/en/trust-center/"],
    "box": ["https://www.box.com/trust"],
    "docusign": ["https://www.docusign.com/trust"],
    "twilio": ["https://www.twilio.com/en-us/security"],
    "cisco": ["https://www.cisco.com/c/en/us/about/trust-center.html"],
    "adobe": ["https://www.adobe.com/trust.html"],
    "servicenow": ["https://www.servicenow.com/company/trust.html"],
    # First-party security-commitment HTML. /security is a product lander.
    "language-i-o": ["https://languageio.com/security-commitment/"],
}

VENDOR_RANK = [
    "vanta", "safebase", "drata", "securitypal", "conveyor", "whistic",
    "secureframe", "trustcloud", "wolfia", "sprinto", "self_hosted",
    "custom", "unknown",
]

SOFT_404 = re.compile(
    r"(page not found|doesn['\u2019]t exist|do not exist|404 error|"
    r"we can['\u2019]t find|can['\u2019]t find (this|the) page|"
    r"this page (could not|doesn['\u2019]t)|no longer (exists|available)|"
    r"sorry,? we (couldn['\u2019]t|cannot) find)",
    re.I,
)
PARKING = re.compile(
    r"(domain is for sale|buy this domain|parked domain|"
    r"this domain (is parked|may be for sale)|coming soon|"
    r"under construction|website is currently unavailable|"
    r"welcome to nginx|apache2 default)",
    re.I,
)
TRUST_TITLE = re.compile(
    r"\b(trust center|trust centre|trust report|trust portal|"
    r"trust and security|trust & security|"
    r"security (center|centre|portal|hub)|"
    r"compliance (center|centre|portal)|assurance profile|"
    r"security (and|&) compliance|trust overview)\b",
    re.I,
)
TRUST_WORDS = re.compile(
    r"\b(soc\s*2|iso\s*27001|gdpr|hipaa|pci[-\s]?dss|"
    r"trust center|trust report|subprocessors?|sub-processors?|"
    r"data processing|security questionnaire|penetration test)\b",
    re.I,
)
TAG_RE = re.compile(r"<[^>]+>")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)

CTX = ssl.create_default_context()


def sld(domain: str) -> str:
    host = domain.lower().strip().lstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host.split(".")[0]


def slugs_for(company: dict) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    def add(value: str) -> None:
        v = (value or "").strip().lower()
        if v and v not in seen:
            seen.add(v)
            out.append(v)
        compact = v.replace("-", "")
        if compact and compact not in seen:
            seen.add(compact)
            out.append(compact)

    add(company["slug"])
    add(sld(company["domain"]))
    for alias in company.get("aliases") or []:
        add(sld(alias))
    return out


def domains_for(company: dict) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in [company["domain"], *(company.get("aliases") or [])]:
        host = raw.lower().strip()
        host = host.removeprefix("http://").removeprefix("https://")
        if host.startswith("www."):
            host = host[4:]
        host = host.rstrip("/")
        if host and host not in seen:
            seen.add(host)
            out.append(host)
    return out


def candidate_urls(company: dict) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    def add(url: str) -> None:
        u = url.rstrip("/")
        key = u.lower()
        if key not in seen:
            seen.add(key)
            urls.append(u)

    for seed in SEED_URLS.get(company["slug"], []):
        add(seed)
    for domain in domains_for(company):
        add(f"https://trust.{domain}")
        add(f"https://security.{domain}")
        add(f"https://compliance.{domain}")
        add(f"https://assurance.{domain}")
        add(f"https://trustcenter.{domain}")
        add(f"https://{domain}/trust")
        add(f"https://{domain}/trust-center")
        add(f"https://{domain}/security")
    for slug in slugs_for(company):
        add(f"https://{slug}.safebase.us")
        add(f"https://{slug}.safebase.io")
        add(f"https://{slug}.secureframetrust.com")
        add(f"https://{slug}.trust.site")
        add(f"https://{slug}.securitypal.com")
    return urls


def strip_tags(html: str) -> str:
    return unescape(re.sub(r"\s+", " ", TAG_RE.sub(" ", html)).strip())


def extract_title(html: str) -> str:
    m = TITLE_RE.search(html)
    return strip_tags(m.group(1))[:200] if m else ""


def extract_h1(html: str) -> str:
    m = H1_RE.search(html)
    return strip_tags(m.group(1))[:200] if m else ""


def host_of(url: str) -> str:
    return urlparse(url).netloc.lower().split(":")[0]


def path_of(url: str) -> str:
    return urlparse(url).path or "/"


def fetch(url: str, max_body: int | None = None) -> dict:
    limit = MAX_BODY if max_body is None else max_body
    req = Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=TIMEOUT, context=CTX) as resp:
            status = getattr(resp, "status", 200) or 200
            final_url = resp.geturl()
            headers = {k.lower(): v for k, v in resp.headers.items()}
            body = resp.read(limit)
    except HTTPError as exc:
        try:
            body = exc.read(limit) if exc.fp else b""
        except Exception:
            body = b""
        return {
            "ok": False,
            "status": exc.code,
            "final_url": url,
            "headers": {},
            "body": body.decode("utf-8", "replace") if body else "",
        }
    except (URLError, TimeoutError, ssl.SSLError, OSError):
        return {"ok": False, "status": 0, "final_url": url, "headers": {}, "body": ""}

    return {
        "ok": True,
        "status": status,
        "final_url": final_url,
        "headers": headers,
        "body": body.decode("utf-8", "replace"),
    }


def detect_vendor(final_url: str, body: str, headers: dict) -> str | None:
    host = host_of(final_url)
    header_blob = "\n".join(f"{k}:{v}" for k, v in headers.items())
    low = f"{body}\n{final_url}\n{header_blob}".lower()

    if host.endswith((".safebase.us", ".safebase.io", ".safebase.com")):
        return "safebase"
    if host.endswith(".trust.site"):
        return "sprinto"
    if host.endswith(".secureframetrust.com"):
        return "secureframe"
    if "securitypal" in host:
        return "securitypal"
    if host.endswith(".vantatrust.com"):
        return "vanta"

    if "powered by conveyor" in low or "cdn.conveyor.com" in low or "conveyorhq.com" in low:
        return "conveyor"
    if "powered by wolfia" in low:
        return "wolfia"
    if "wolfia.com" in low and ("trust" in low or "powered by" in low):
        return "wolfia"
    if "powered by safebase" in low or "powered by safe base" in low:
        return "safebase"
    if "assurance profile" in low:
        return "securitypal"
    if "static.vanta.com" in low or "entry-trust-report" in low or "vantatrust" in low:
        return "vanta"
    if re.search(r"\bdata-slug=", low) and "vanta" in low and "static.vanta" in low:
        return "vanta"
    if "safebase.us" in low or "safebase.io" in low:
        return "safebase"
    if "powered by drata" in low or "cdn.drata.com" in low or "app.drata.com/trust" in low:
        return "drata"
    if "powered by secureframe" in low or "secureframetrust.com" in low:
        return "secureframe"
    if "powered by whistic" in low or "public-profile.whistic.com" in low:
        return "whistic"
    if "trustshare overview" in low or "powered by trustcloud" in low or "trustcloud.ai" in low:
        return "trustcloud"
    if "trustshare" in low and "conveyor" in low:
        return "conveyor"
    return None


def looks_like_homepage(requested: str, final_url: str, title: str, body: str) -> bool:
    req = urlparse(requested)
    fin = urlparse(final_url)
    fin_host = fin.netloc.lower().split(":")[0].removeprefix("www.")
    fin_path = (fin.path or "/").rstrip("/") or "/"
    if fin_host.startswith(("trust.", "security.", "compliance.", "assurance.", "trustcenter.")):
        return False
    if any(fin_host.endswith(sfx) for sfx in (
        ".safebase.us", ".safebase.io", ".safebase.com",
        ".secureframetrust.com", ".trust.site", ".securitypal.com",
        ".vantatrust.com",
    )):
        return False
    req_path = (req.path or "/").rstrip("/")
    if fin_path == "/" and req_path in {"/trust", "/trust-center", "/security", "/docs/security"}:
        if TRUST_TITLE.search(title or "") or TRUST_TITLE.search(body[:2000] or ""):
            return False
        return True
    return False


def is_seed(url: str) -> bool:
    target = url.rstrip("/").lower()
    for seeds in SEED_URLS.values():
        for seed in seeds:
            if target == seed.rstrip("/").lower():
                return True
    return False


def is_trust_hit(requested: str, fetched: dict) -> tuple[bool, str, str]:
    if not fetched.get("ok") or fetched.get("status") != 200:
        return False, "unknown", ""
    body = fetched.get("body") or ""
    headers = fetched.get("headers") or {}
    final_url = fetched.get("final_url") or requested
    title = extract_title(body)
    h1 = extract_h1(body)
    heading = f"{title} {h1}"
    ctype = (headers.get("content-type") or "").lower()

    if PARKING.search(title) or PARKING.search(body[:2500]):
        return False, "unknown", title
    if SOFT_404.search(title) or SOFT_404.search(h1) or SOFT_404.search(body[:2500]):
        return False, "unknown", title

    vendor = detect_vendor(final_url, body, headers)
    if vendor:
        return True, vendor, title

    if "application/pdf" in ctype:
        host = host_of(final_url)
        path = path_of(final_url).lower()
        if any(tok in path or tok in host for tok in ("trust", "security", "compliance")):
            return True, "self_hosted", title or "PDF"
        return False, "unknown", title

    if looks_like_homepage(requested, final_url, title, body):
        return False, "unknown", title

    if TRUST_TITLE.search(heading) or TRUST_TITLE.search(body[:4000]):
        return True, "self_hosted", title

    if is_seed(requested):
        path = path_of(final_url).lower()
        if TRUST_WORDS.search(body) or "security" in path or "trust" in path:
            if len(body) > 400:
                return True, "self_hosted", title

    fin_host = host_of(final_url)
    if fin_host.startswith(("trust.", "security.", "compliance.", "assurance.", "trustcenter.")):
        if TRUST_WORDS.search(body) or TRUST_TITLE.search(heading):
            return True, "self_hosted", title
    return False, "unknown", title


def score_hit(vendor: str, url: str) -> tuple[int, int]:
    try:
        vscore = VENDOR_RANK.index(vendor)
    except ValueError:
        vscore = len(VENDOR_RANK)
    host = host_of(url)
    if any(host.endswith(sfx) for sfx in (
        ".safebase.us", ".safebase.io", ".secureframetrust.com",
        ".trust.site", ".securitypal.com",
    )) or host.startswith(("trust.", "trustcenter.")):
        host_score = 0
    elif host.startswith(("security.", "compliance.", "assurance.")):
        host_score = 1
    else:
        host_score = 2
    return (vscore, host_score)


def probe_company(company: dict) -> dict:
    urls = candidate_urls(company)
    hits: list[tuple[str, str, str, str]] = []
    probed = 0
    last_title = ""
    for url in urls:
        probed += 1
        fetched = fetch(url)
        ok, vendor, title = is_trust_hit(url, fetched)
        if title:
            last_title = title
        if ok:
            hits.append((url, fetched.get("final_url") or url, vendor, title))
            host = host_of(fetched.get("final_url") or url)
            if vendor in {
                "vanta", "safebase", "drata", "securitypal", "conveyor",
                "whistic", "secureframe", "trustcloud", "wolfia", "sprinto",
            } or host.startswith("trust."):
                break

    if hits:
        hits.sort(key=lambda h: score_hit(h[2], h[1]))
        trust_url, final_url, vendor, title = hits[0]
        found = True
    else:
        trust_url = final_url = None
        vendor = "unknown"
        title = last_title or ""
        found = False

    return {
        "rank": company.get("rank"),
        "name": company["name"],
        "slug": company["slug"],
        "domain": company["domain"],
        "found": found,
        "trust_url": trust_url,
        "final_url": final_url,
        "vendor": vendor if found else "unknown",
        "title": title,
        "probed": probed,
        "source": company.get("source") or "forbes-cloud-100-2025",
    }


def load_companies() -> list[dict]:
    companies = json.loads((ROOT / "companies.json").read_text())
    extra_path = ROOT / "extra-companies.json"
    if extra_path.exists():
        extras = json.loads(extra_path.read_text())
        seen = {c["slug"] for c in companies}
        for row in extras:
            slug = row.get("slug")
            if slug and slug not in seen:
                companies.append(row)
                seen.add(slug)
    return companies


def main() -> int:
    companies = load_companies()
    print(f"Probing {len(companies)} companies with {WORKERS} workers...", flush=True)
    results: list[dict] = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(probe_company, c): c for c in companies}
        for i, fut in enumerate(as_completed(futs), 1):
            row = fut.result()
            results.append(row)
            flag = "HIT" if row["found"] else "miss"
            extra = f"  {row['vendor']}  {row['trust_url']}" if row["found"] else ""
            print(f"[{i:3}/{len(companies)}] {flag:4} #{row['rank']:>3} {row['name']}{extra}", flush=True)

    results.sort(key=lambda r: (r["rank"] is None, r["rank"] or 0, r["name"]))
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Forbes Cloud 100 2025",
        "source_url": "https://www.forbes.com/lists/cloud100/",
        "companies": results,
    }
    text = json.dumps(payload, indent=2) + "\n"
    data_path = ROOT / "data" / "results.json"
    source_path = ROOT / "data" / "register-source.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(text)
    source_path.write_text(text)

    found = sum(1 for r in results if r["found"])
    vendors = Counter(r["vendor"] for r in results if r["found"])
    print()
    print(f"Found {found}/{len(results)}  in {time.time() - t0:.1f}s")
    print("Vendors:")
    for name, count in vendors.most_common():
        print(f"  {name}: {count}")
    print(f"Wrote {data_path}")
    print(f"Wrote {source_path}")
    print("Run python3 build_pages.py to publish the public register.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
