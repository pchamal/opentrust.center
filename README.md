# opentrust.center

An open directory of **company security pages, customer trust centers, and managed trust portals**.

Built for GRC and security people — and for agents acting on their behalf. Look up a company, see whether they publish a public portal, read what it says (vendor, certifications, summary), then open the official URL.

Coverage is the **2025 Forbes Cloud 100** plus public enterprise, security, and AI vendors people actually search (Microsoft, Salesforce, Okta, CrowdStrike, and peers).

Live: the here.now URL in this repo’s latest publish notes.

## For humans

Open the site, search a name, read the card, then click out. Outbound links are human-gated so automated walkers do not hammer vendor portals.

## For agents

1. Company page: `/c/{slug}.html` (title, JSON-LD, facts)
2. Structured index: `/data.json`
3. Agent brief: `/llms.txt`

If `found` is true, use `trust_url`. If it is false, say no public portal is on file — do not invent a URL. A missing portal is not the same as “no security program.”

## What counts as a hit

- A first-party security / trust / compliance page
- A customer trust center
- A managed portal (SafeBase, Vanta, Conveyor, Wolfia, Drata, SecurityPal, and similar)

A hit is HTTP 200 plus a trust-center signature. Homepages, soft 404s, and parked domains are rejected.

## Crawl

```bash
python3 crawl.py          # Cloud 100 + extras if extra-companies.json exists
python3 probe_extra.py    # extras only
python3 build_pages.py    # SEO pages + sitemap
```

Stdlib only. Writes `site/data.json` and `data/results.json`.

Do not run the crawler unless you mean to refresh the snapshot.

## Methodology

1. Probe `trust.{domain}`, `security.{domain}`, `/{trust,trust-center,security}`, and vendor hosts.
2. Misses get a “{company} Trust Center” search, then a check that the result is that company’s real portal.
3. Certifications are read from the public page text.

## Source

[Forbes Cloud 100 2025](https://www.forbes.com/lists/cloud100/) and a curated public-enterprise set.

Not affiliated with Forbes, Bessemer, or Salesforce Ventures.
