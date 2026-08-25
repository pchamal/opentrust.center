#!/usr/bin/env python3
"""opentrust.center discovery pipeline.

Finds public trust/security files that fixed-path probing misses:
  strategy=path     extended first-party path candidates
  strategy=footer   anchor harvest from the company's own homepage
                    (browser-rendered via crawl4ai when the HTML is a JS shell)
  strategy=sitemap  robots.txt / sitemap.xml URLs matching trust keywords

A lead is NOT a finding. Every lead is re-fetched and only prints as verified
when it passes BRAND.md rules 1-3: first-party host, fetch-checked, real page.

Usage:
  .venv/bin/python pipeline/discover.py --limit 25 [--tier silent] [--deep N]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from selectolax.parser import HTMLParser

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "site" / "data.json"
REPORT = ROOT / "data" / "discovery-report.json"
INSFORGE_META = ROOT.parent / ".insforge" / "project.json"

UA = "opentrust.center-discovery/1.0 (+https://opentrust.center/bot)"
TIMEOUT = httpx.Timeout(12.0, connect=6.0)

PATH_CANDIDATES = [
    "/trust", "/trust-center", "/trustcenter", "/trust-and-compliance",
    "/trust-and-safety", "/trust-compliance", "/security", "/security-center",
    "/security-and-compliance", "/compliance", "/assurance", "/data-security",
    "/cloud-security", "/product-security", "/legal/security", "/legal/trust",
    "/legal/compliance", "/company/security", "/company/trust",
    "/about/security", "/about/trust", "/en/security", "/en/trust",
    "/security.html", "/trust.html",
]

ANCHOR_KEYWORDS = (
    "trust center", "trust portal", "trust & safety", "security", "compliance",
    "data protection", "data security", "gdpr", "privacy program",
)
HREF_KEYWORDS = (
    "trust", "security", "compliance", "assurance", "data-protection",
    "data-security", "soc-2", "soc2", "iso-27001", "gdpr",
)
DPA_HINTS = ("/dpa", "data-processing", "processing-terms", "dpas")
SUB_HINTS = ("subprocessor", "sub-processor", "third-party", "vendor-list")
SOFT_404 = ("page not found", "404", "not found", "nothing found")

MULTI_SUFFIXES = {"co.uk", "org.uk", "gov.uk", "com.au", "co.jp", "com.br",
                  "co.in", "co.nz", "com.sg", "com.tr"}


def registrable(host: str) -> str:
    host = host.lower().split(":")[0].lstrip(".")
    parts = host.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in MULTI_SUFFIXES:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def same_site(url: str, base_domain: str) -> bool:
    try:
        return registrable(urlparse(url).netloc) == registrable(base_domain)
    except Exception:
        return False


def kind_of(url: str, title: str = "") -> str | None:
    u = url.lower()
    t = (title or "").lower()
    if any(k in u for k in SUB_HINTS):
        return "subprocessors"
    if any(k in u for k in DPA_HINTS):
        return "dpa"
    if "compliance" in u or "compliance" in t:
        return "compliance"
    if "trust" in u or "trust" in t:
        return "trust"
    if "security" in u or "security" in t:
        return "security"
    if "privacy" in u:
        return None
    return None


def looks_like_shell(html: str) -> bool:
    if not html:
        return True
    tree = HTMLParser(html)
    anchors = tree.css("a[href]")
    has_root_div = bool(tree.css("#root, #__next, #app"))
    return len(anchors) < 12 and has_root_del_if_present(has_root_div)


def has_root_del_if_present(v: bool) -> bool:
    return v


def extract_anchors(html: str, base_url: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    try:
        tree = HTMLParser(html)
    except Exception:
        return out
    for node in tree.css("a[href]"):
        href = (node.attributes.get("href") or "").strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        text = re.sub(r"\s+", " ", node.text(strip=True)).lower()[:80]
        out.append((urljoin(base_url, href), text))
    return out


def anchor_is_lead(href: str, text: str) -> bool:
    low = href.lower()
    if any(h in low for h in HREF_KEYWORDS):
        return True
    return any(a in text for a in ANCHOR_KEYWORDS)


async def fetch(client: httpx.AsyncClient, url: str) -> tuple[int, str, str]:
    """GET -> (status, final_url, body)."""
    try:
        r = await client.get(url, headers={"User-Agent": UA}, follow_redirects=True)
        ctype = r.headers.get("content-type", "")
        if r.status_code == 200 and "html" not in ctype and "text" not in ctype and len(r.content) > 500_000:
            return r.status_code, str(r.url), ""
        return r.status_code, str(r.url), r.text if "charset" in ctype or "<" in r.text[:1] else r.text
    except Exception:
        return 0, url, ""


async def deep_render(url: str, sem: asyncio.Semaphore) -> tuple[int, str]:
    """crawl4ai browser render for JS shells."""
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
    except Exception:
        return 0, ""
    async with sem:
        try:
            bcfg = BrowserConfig(headless=True, user_agent=UA)
            cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=28_000,
                                   verbose=False)
            async with AsyncWebCrawler(config=bcfg) as crawler:
                r = await crawler.arun(url=url, config=cfg)
                return int(r.status_code or 0), (r.html or "")
        except Exception:
            return 0, ""


class InsForge:
    def __init__(self) -> None:
        meta = json.loads(INSFORGE_META.read_text())
        self.base = meta["oss_host"]
        self.key = meta["api_key"]
        self.headers = {"Authorization": f"Bearer {self.key}",
                        "Content-Type": "application/json"}

    async def existing_keys(self, client: httpx.AsyncClient, domain: str) -> set[str]:
        r = await client.get(
            f"{self.base}/api/database/records/ot_leads",
            params={"domain": f"eq.{domain}", "select": "leadKey"},
            headers=self.headers,
        )
        if r.status_code != 200:
            return set()
        return {row["leadKey"] for row in r.json()}

    async def insert_leads(self, client: httpx.AsyncClient, rows: list[dict]) -> int:
        if not rows:
            return 0
        r = await client.post(
            f"{self.base}/api/database/records/ot_leads",
            json=rows, headers={**self.headers, "Prefer": "return=minimal"},
        )
        return len(rows) if r.status_code in (200, 201) else 0

    async def mark_verified(self, client: httpx.AsyncClient, lead_key: str,
                            kind: str, title: str, status: int) -> None:
        await client.patch(
            f"{self.base}/api/database/records/ot_leads",
            params={"leadKey": f"eq.{lead_key}"},
            json={"verified": True, "kind": kind, "title": title[:180],
                  "httpStatus": status, "verifiedAt": now_iso()},
            headers=self.headers,
        )

    async def record_sweep(self, client: httpx.AsyncClient, stats: dict) -> None:
        await client.post(
            f"{self.base}/api/database/records/ot_sweeps",
            json=[{"startedAt": stats["startedAt"], "finishedAt": now_iso(),
                   "domainsScanned": stats["domains"], "leadsFound": stats["leads"],
                   "filesVerified": stats["verified"], "stats": stats}],
            headers=self.headers,
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def title_of(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip()[:160] if m else ""


async def verify_lead(client: httpx.AsyncClient, domain: str, url: str) -> dict | None:
    status, final_url, body = await fetch(client, url)
    if status != 200 or not body:
        return None
    if not same_site(final_url, domain):
        return None
    title = title_of(body)
    if not title or any(s in title.lower()[:60] for s in SOFT_404):
        return None
    if len(re.sub(r"<[^>]+>", " ", body)) < 400:
        return None
    kind = kind_of(final_url, title)
    if not kind:
        return None
    return {"url": final_url, "status": status, "title": title, "kind": kind}


async def discover_domain(client: httpx.AsyncClient, ig: InsForge,
                          deep_sem: asyncio.Semaphore, row: dict,
                          verify_cap: int = 10) -> dict:
    domain = row["domain"].lower()
    base_hosts = [f"https://{domain}", f"https://www.{domain}"]
    leads: dict[str, dict] = {}

    def add(url: str, strategy: str, anchor: str = "") -> None:
        url = url.split("#")[0].rstrip("/")
        if not url or not same_site(url, domain):
            return
        key = f"{domain}|{url}"
        if key not in leads:
            leads[key] = {"leadKey": key, "domain": domain, "url": url,
                          "strategy": strategy, "anchorText": anchor[:120],
                          "discoveredAt": now_iso()}

    home_status, _, home_html = await fetch(client, base_hosts[0])
    if home_status == 0 or (home_html and looks_like_shell(home_html)):
        s2, _, alt = await fetch(client, base_hosts[1])
        if s2 == 200 and alt and not looks_like_shell(alt):
            home_status, home_html = s2, alt
    if home_status == 0 or not home_html:
        s3, home_html = await deep_render(base_hosts[0], deep_sem)
        home_status = s3 or home_status

    if home_html:
        for href, text in extract_anchors(home_html, base_hosts[0]):
            if anchor_is_lead(href, text):
                add(href, "footer", text or "")

    for path in PATH_CANDIDATES:
        add(f"https://{domain}{path}", "path")

    sm_status, _, sm_body = await fetch(client, f"https://{domain}/sitemap.xml")
    if sm_status != 200:
        _, _, rb = await fetch(client, f"https://{domain}/robots.txt")
        for line in rb.splitlines():
            if line.lower().startswith("sitemap:"):
                sm_status, _, sm_body = await fetch(client, line.split(":", 1)[1].strip())
                break
    if sm_body:
        locs = re.findall(r"<loc>([^<]+)</loc>", sm_body)[:400]
        n = 0
        for loc in locs:
            if n >= 25:
                break
            if anchor_is_lead(loc, ""):
                add(loc, "sitemap")
                n += 1

    existing = await ig.existing_keys(client, domain)
    fresh = [v for k, v in leads.items() if k not in existing]
    inserted = await ig.insert_leads(client, fresh)

    def lead_priority(item: tuple[str, dict]) -> tuple[int, str]:
        _, lead = item
        u = lead["url"].lower()
        score = 0
        if "/trust" in u:
            score -= 4
        if "security" in u:
            score -= 3
        if "compliance" in u or "assurance" in u:
            score -= 2
        if u.count("/") <= 4:
            score -= 1
        anchor = (lead.get("anchorText") or "").lower()
        if any(k in anchor for k in ("trust center", "trust portal", "security", "compliance")):
            score -= 3
        return (score, lead["url"])

    verified: list[dict] = []
    ranked = sorted(leads.items(), key=lead_priority)[:verify_cap]
    for key, lead in ranked:
        res = await verify_lead(client, domain, lead["url"])
        if res:
            verified.append(res)
            await ig.mark_verified(client, key, res["kind"], res["title"], res["status"])

    print(f"  {domain:<32} leads:{len(leads):>3} new:{inserted:>3} "
          f"verified:{len(verified):>2}  {[v['kind'] for v in verified]}"
          f"{'' if verified else '  (still silent, honestly)'}")
    return {"domain": domain, "leads": len(leads), "newLeads": inserted,
            "verifiedFiles": [{"kind": v["kind"], "url": v["url"],
                               "title": v["title"]} for v in verified],
            "homepageStatus": home_status}


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--tier", default="silent")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    data = json.loads(DATA_JSON.read_text())
    only = {d.strip().lower() for d in args.only.split(",") if d.strip()}
    seen_domains: set[str] = set()
    seeds = []
    for c in data["companies"]:
        d = (c.get("domain") or "").lower()
        if not d or d in seen_domains:
            continue
        if only and d not in only:
            continue
        if c.get("tier") == args.tier:
            seen_domains.add(d)
            seeds.append(c)
    seeds = seeds[: args.limit]

    ig = InsForge()
    deep_sem = asyncio.Semaphore(2)
    started = now_iso()
    results: list[dict] = []
    limits = httpx.Limits(max_connections=10)
    async with httpx.AsyncClient(timeout=TIMEOUT, limits=limits,
                                 follow_redirects=True) as client:
        for row in seeds:
            try:
                results.append(await discover_domain(client, ig, deep_sem, row))
            except Exception as exc:
                print(f"  {row['domain']:<32} error {exc}")
        totals = {
            "startedAt": started, "domains": len(results),
            "leads": sum(r["leads"] for r in results),
            "verified": sum(len(r["verifiedFiles"]) for r in results),
            "tierFilter": args.tier,
        }
        await ig.record_sweep(client, totals)

    REPORT.write_text(json.dumps({"sweep": totals, "domains": results}, indent=2))
    print(f"\nsweep · domains {totals['domains']} · leads {totals['leads']} "
          f"· files verified {totals['verified']}")
    print(f"report → {REPORT.relative_to(ROOT)}")
    hit = sum(1 for r in results if r["verifiedFiles"])
    print(f"{hit}/{len(results)} previously-{args.tier} domains have a real file on record.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
