#!/usr/bin/env python3
"""Generate per-company SEO pages, sitemap, and JSON-LD from data.json."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
CANON = "https://cobalt-quartz-nx3z.here.now"

VENDOR = {
    "safebase": "SafeBase",
    "vanta": "Vanta",
    "conveyor": "Conveyor",
    "wolfia": "Wolfia",
    "custom": "Custom",
    "self_hosted": "Custom",
    "drata": "Drata",
    "securitypal": "SecurityPal",
    "secureframe": "Secureframe",
    "sprinto": "Sprinto",
    "whistic": "Whistic",
    "trustcloud": "TrustCloud",
}


def host_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def vendor_label(v: str) -> str:
    return VENDOR.get(v, v or "Unknown")


def page_html(row: dict) -> str:
    name = row["name"]
    slug = row["slug"]
    domain = row.get("domain") or ""
    found = bool(row.get("found"))
    url = row.get("trust_url") or row.get("final_url") or ""
    title = f"{name} trust center — opentrust.center"
    if found:
        desc = row.get("summary") or row.get("title") or f"Public trust center for {name}."
    else:
        desc = f"No public trust center found for {name} on the usual paths."
    certs = row.get("certs") or []
    vendor = vendor_label(row.get("vendor") or "")
    host = host_of(url) if found else ""
    cert_html = "".join(f'<span class="cert">{escape(c)}</span>' for c in certs)
    ld = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": desc,
        "url": f"{CANON}/c/{slug}.html",
        "isPartOf": {"@type": "WebSite", "name": "opentrust.center", "url": CANON + "/"},
        "about": {"@type": "Organization", "name": name, "url": f"https://{domain}" if domain else None},
    }
    if found and url:
        ld["significantLink"] = url
        ld["mainEntity"] = {
            "@type": "WebPage",
            "name": f"{name} Trust Center",
            "url": url,
        }
    status = (
        f'<p class="drawer-summary">{escape(desc)}</p>'
        f'<div class="cert-row">{cert_html}</div>'
        f'<p class="drawer-meta">{escape(vendor)} portal</p>'
        f'<p class="drawer-host">{escape(host)}</p>'
        if found
        else f'<p class="drawer-summary">{escape(desc)}</p><p class="missing-label">Not found</p>'
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(desc[:220])}">
  <link rel="canonical" href="{CANON}/c/{escape(slug)}.html">
  <meta property="og:title" content="{escape(title)}">
  <meta property="og:description" content="{escape(desc[:220])}">
  <meta property="og:type" content="article">
  <meta name="theme-color" content="#12110e">
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%2312110e' stroke='%23d4a24a' stroke-width='2'/%3E%3Ctext x='32' y='39' text-anchor='middle' font-family='Georgia,serif' font-size='20' font-weight='700' fill='%23d4a24a'%3EOT%3C/text%3E%3C/svg%3E">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../styles.css">
</head>
<body>
  <div class="sheet">
    <header class="mast">
      <div class="mast-brand">
        <a href="../" style="text-decoration:none;color:inherit">
          <div class="seal" aria-hidden="true">
            <span class="seal-outer"></span>
            <span class="seal-inner"></span>
            <span class="seal-mark">OT</span>
          </div>
        </a>
        <div class="mast-titles">
          <p class="kicker"><a href="../" style="color:inherit;text-decoration:none">opentrust.center</a></p>
          <h1>{escape(name)}</h1>
        </div>
      </div>
      <p class="mast-issue">{escape(domain)}</p>
    </header>
    <section class="hero">
      {status}
      <p style="margin-top:28px"><a class="open" href="../?c={escape(slug)}">Open in the directory</a></p>
    </section>
  </div>
</body>
</html>
"""


def main() -> int:
    data = json.loads((SITE / "data.json").read_text())
    companies = data.get("companies") or []
    out = SITE / "c"
    if out.exists():
        for old in out.glob("*.html"):
            old.unlink()
    out.mkdir(exist_ok=True)
    urls = [f"{CANON}/"]
    for row in companies:
        slug = row.get("slug")
        if not slug:
            continue
        (out / f"{slug}.html").write_text(page_html(row), encoding="utf-8")
        urls.append(f"{CANON}/c/{slug}.html")
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sitemap.append(f"  <url><loc>{escape(u)}</loc></url>")
    sitemap.append("</urlset>\n")
    (SITE / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")
    print(f"Wrote {len(urls) - 1} company pages + sitemap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
