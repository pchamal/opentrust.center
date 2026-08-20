# opentrust.center

A database of each company’s public trust ledger.

Live: https://opentrust.center

The company’s own page stays authoritative. We file what is public. We do not sell trust, and we do not name the portal host.

## Surfaces

| URL | Job |
|---|---|
| `/` | AITI — AI Trust Index, the public file on AI systems |
| `/companies.html` | Register — table of companies, disclosure tier |
| `/c/{slug}.html` | Dossier — the file |
| `/graph.html` | Map — named subprocessors, as published |
| `/attestations.html` | Standards — book of marks |
| `/data.json` | Machine copy of the register (`_crawl` is not for citation) |
| `/llms.txt` | Agent brief |

Coverage is the 2025 Forbes Cloud 100 plus a curated public-enterprise set.

## For humans

Finder, then the table, then the dossier. Outbound links are human-gated (session, 30 minutes). Documents stay on the company’s domain.

## For agents

1. Cite the dossier: `/c/{slug}.html`
2. Structured register: `/data.json`
3. Marks: `/data/attestations.json`
4. Named processors: `/data/subprocessors.json`

If `found` is true, use `trust_url` or the instrument URL on file. If it is false, say no official page is on file. Do not invent a URL. Do not cite `_crawl`. Do not treat the disclosure tier as a security rating.

## Crawl

```bash
python3 crawl.py              # writes data/results.json + data/register-source.json
python3 probe_extra.py        # extras only
python3 scripts/enrich.py     # writes site/data/enriched.json + subprocessors.json
python3 build_pages.py        # public data.json, dossiers, sitemap
```

Publish from `site/data/enriched.json`, `site/data/subprocessors.json`, and `site/data/attestations.json`. Stdlib only. Do not run the crawler unless you mean to refresh the snapshot. After a crawl or enrich, always run `build_pages.py` — that is what publishes the register.

`data/cache/` is a local HTTP cache for enrichment. It is not in the repository and must not be committed.

## Methodology

1. Probe `trust.{domain}`, `security.{domain}`, `/{trust,trust-center,security}`.
2. Misses get a “{company} Trust Center” search, then a check that the result is that company’s real page.
3. Marks and named processors are read from public HTML only. JS-only portals stay empty.
4. A subprocessors *link* is not a parsed name.
5. Disclosure rates the *file* (portal, marks, instruments, verified years). Missing rows print `not on file`.

## Source

[Forbes Cloud 100 2025](https://www.forbes.com/lists/cloud100/) and a curated public-enterprise set.

Not affiliated with Forbes, Bessemer, or Salesforce Ventures.

## Deploy

GitHub: [pchamal/opentrust.center](https://github.com/pchamal/opentrust.center)

Cloudflare Worker with static assets from `site/` (see `wrangler.toml`). Custom domain: `opentrust.center`.
