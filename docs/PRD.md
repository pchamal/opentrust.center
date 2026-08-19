# opentrust.center — product record

Issue date: 2026-08-18
Status: build from this
Owner: Pukar Hamal
Site: https://opentrust.center
Code: https://github.com/pchamal/opentrust.center

This is the product law for the front-pane rebuild. If a screen disagrees with this file, the screen is wrong.

---

## The job

A GRC or security person (or their agent) opens opentrust.center the way they open Companies House.

They do not want to know that Stripe’s portal is “powered by SafeBase.” They want to know what Stripe publishes: which attestations, which security and privacy pages, how long the firm has been operating, who they name as subprocessors, and whether that public file is thin or complete.

We are the front pane of glass. The company’s own pages stay authoritative. We file what is public, rate the file, and show the wires between firms. We do not sell trust. We do not replace a questionnaire. We do not name the portal vendor.

---

## What we are not

- Not a GRC SaaS (Vanta, Drata, Secureframe, Sprinto)
- Not a trust-center host (SafeBase, Conveyor, Whistic)
- Not a security rating agency (BitSight, SecurityScorecard, RiskRecon)
- Not a procurement chatbot
- Not a vendor comparison shop

If a sentence could appear on a Vanta homepage, delete it.

---

## Three surfaces (one register)

| Surface | URL | Job |
|---|---|---|
| Register | `/` | Find a company. See disclosure tier. Open the dossier. |
| Dossier | `/c/{slug}.html` | Every public security and compliance link we have on file, plus certs, years, subprocessors. |
| Processors | `/graph.html` | Disclosed subprocessors. Who depends on whom. Which named processors sit under the most of the index with the thinnest public file. |
| Attestations | `/attestations.html` | Every attestation a buyer will meet, ELI-5 and long form, by geography and industry, on a desk globe. |

Also: `/brand.html` (specimen), `/llms.txt`, `/data.json`, `/sitemap.xml`.

No blog. No pricing. No “platform” nav. The mast is a docket: `register · processors · attestations`.

---

## Decision 1 — Hide the portal vendor

The current home page counts SafeBase / Vanta / Conveyor / Wolfia / Custom. That makes us a channel for those products.

Law:

- Do not render vendor names, vendor chips, vendor tallies, or “powered by” titles.
- Keep `vendor` in crawl data only (so the probe can find the page again).
- Public JSON for agents (`data.json`) may omit `vendor` or leave it in a `_crawl` object that `llms.txt` tells agents not to cite.
- Rewrite any summary that mentions a host vendor.
- The outbound button is “Open the official page”, never “Open SafeBase”.

---

## Decision 2 — Rate the file, not the company

We do not know if a company is secure. We know what they published.

Name: **disclosure tier**
Voice: stamped, not scored like a consumer report.

| Tier | Score | Meaning |
|---|---|---|
| silent | — | No public trust or security page on file. |
| thin | 1–39 | A page exists. Little else (no certs, no DPA, no subprocessors). |
| on file | 40–69 | Portal plus some attestations or supporting pages. |
| substantial | 70–89 | Portal, several hard attestations, and supporting instruments (DPA / subprocessors / status / disclosure). |
| complete | 90–100 | The public file a serious buyer expects, including longevity. |

Score (cap 100):

```
+20  public trust or security page found
+    sum(cert weights), cap 40
+8   public DPA / DPA addendum
+8   public subprocessor list
+6   public status page
+6   bug bounty or security.txt / VDP
+6   privacy policy
+    min(10, floor((2026 − founded_year) / 2))   if year verified
```

Cert weights (gazette is source of truth; these are the common ones):

| Attestation | Weight |
|---|---|
| FedRAMP (any authorized) | 12 |
| CMMC L2+, HITRUST r2, PCI DSS | 8–10 |
| SOC 2 Type II, ISO 27001 | 10 |
| ISO 27701, ISO 42001, HIPAA, StateRAMP | 6 |
| SOC 3, CSA STAR, C5, IRAP, ISMAP | 4–6 |
| GDPR, CCPA/CPRA, UK GDPR | 3 |
| Other listed cert | 4 |

Rules:

- Print the factors next to the stamp. A score without a legend is a lie.
- GDPR/CCPA are legal regimes, not certificates. Weight them lightly so a marketing page that says “we are GDPR” cannot buy a complete stamp.
- Years of operation are a stability signal, not a virtue. Cap at 10.
- Missing data is missing, not zero pretending to be measured.
- Never call this a “trust score”, “security rating”, or letter grade (A–F).

---

## Decision 3 — The dossier is the product

The current drawer is a summary, a few cert chips, and a click-out. That is a card, not a file.

A company dossier must show, when on file:

1. Name, domain, list (Cloud 100 / enterprise), founded year + source
2. Disclosure stamp + factor line
3. Attestations claimed on the public page (link each to `/attestations.html#{id}`)
4. Instruments: trust, security, privacy, DPA, subprocessors, status, bounty / security.txt
5. Named subprocessors (link into the graph)
6. Clerk summary (two sentences, no vendor, no marketing)
7. Last probed
8. Human-gated outbound to the official page
9. Permalink `/c/{slug}.html` (SEO, GEO, agents)

If a field is not on file, say `not on file`. Do not hide the row.

Empty-state for a name not in the index: keep the guess URLs. Do not invent a live search backend in this issue.

---

## Decision 4 — Wires (subprocessor graph)

Only edges we saw on a first-party public list (or the company’s own trust-center subprocessor document). Incomplete by nature. Say so on the page.

- Nodes: companies in the register + named processors
- Edges: `company → processor`, with `source_url`
- Risk on this map is **concentration × thin public file**, not CVE drama

**Highest-risk processor** (among those we can see):

```
exposure  = how many register companies name them
thinness  = 1 if the processor is silent/thin or not in the register
          = (100 − their disclosure score) / 100 if we have them
risk      = exposure × (0.4 + 0.6 × thinness)
```

The page:

- A wire instrument (hairline graph on the espresso field). Not a neon network toy.
- A ranked table of processors: name, exposure, their own tier if known, risk
- Click a node: dossier if in-register, else a stub that lists who named them
- Caption: “Filed from public subprocessor lists. This is not a complete supply chain.”

Do not scrape private SafeBase documents. If the list is behind a login, it is not on file.

---

## Decision 5 — Gazette of attestations

A separate page. This is the book of marks.

Each entry: name, kind (attestation / certification / regulation / framework / questionnaire / retired), geography, industry, issuer, ELI-5, elaborate, related marks, weight.

UI:

- Filters: geography, industry, kind
- Two depths on every card: `eli-5` (default) and `elaborate`
- Interactive globe: a desk instrument, not a product-hunt WebGL bauble
  - Espresso sphere, rust graticule, land in `--well`, flame points for families
  - Slow or no auto-rotate (user drags)
  - Click a region: the list filters to that geography
  - Click a point: open that family
  - No atmosphere glow, no starfield, no camera whoosh

---

## Information architecture

```
opentrust.center/
  index.html              register
  graph.html              processors
  attestations.html       attestations + globe
  brand.html              specimen
  c/{slug}.html           dossier
  data.json               register (public, no vendor in the rendered sense)
  data/attestations.json
  data/subprocessors.json
  llms.txt
  robots.txt
  sitemap.xml
```

Mast on every surface:

```
opentrust.center          register   processors   attestations     OT
```

Active item is a hairline underline. Not a pill.

---

## Voice (from BRAND.md)

Clerk. Lowercase wordmark. Short sentences. Numbers are facts.

Allowed: found, missing, on file, not on file, silent, thin, substantial, complete, last probed, named, filed.

Banned: empower, seamless, reimagine, next-gen, in one place, trust made simple, the future of GRC, unlock, delightful, front pane of glass (that is our internal metaphor, not the headline), trust score, powered by.

Hero (register): `Public record of what a company discloses.`
Deck: `Attestations, instruments, years. Official page, or not.`

Hero (processors): `Named subprocessors, as published.`
Hero (attestations): `Marks a buyer will meet.`

---

## SEO / GEO / agents

- Canonical `https://opentrust.center/` and `/c/{slug}.html`
- JSON-LD: WebSite + Organization (us) + for each dossier a `WebPage` about that Organization, `hasCredential` when we have certs
- `llms.txt` tells agents: cite the dossier; do not invent URLs; do not treat the disclosure tier as a security rating; do not name portal vendors from crawl leftovers
- Sitemap includes register, graph, attestations, every dossier
- Human gate remains on outbound only. Agents may read on-page facts.

---

## Data we will not ship if we cannot verify

- A cert the page did not state
- A founding year without a source URL
- A subprocessor edge without a source URL
- A live “AI search” for unknown names (still a later issue)

Partial honest data is the product. A complete fiction is a different product.

---

## Build order

1. This PRD and the brand audit (this issue)
2. Attestations catalog (static, editorial)
3. Enrichment pass (certs, years, instruments, subprocessors) — repeatable script
4. Rebuild surfaces against the new data
5. Hide vendors everywhere public
6. Push `main` → Cloudflare Worker

---

## Acceptance

A stranger can:

1. Open `/`, search `stripe`, see a disclosure stamp, open the dossier, and not see the word SafeBase or Vanta anywhere.
2. From Stripe’s dossier, jump to SOC 2 in the attestations, read ELI-5, press elaborate.
3. Open `/graph.html`, see AWS (or whoever the public lists actually name) as a high-exposure node, with a source URL on the edge.
4. Open `/attestations.html`, drag the globe to Europe, see GDPR / ISO / C5 / DORA, not a starfield.
5. View-source or `data.json` and still not be taught that “custom” vs “vanta” is the point of the site.
6. Someone who has never seen a YC landing page can tell this from Linear, Vanta, and a dark-gold AI template.

---

## Later (not this issue)

- Live AI lookup for names not in the index
- Login-gated document text (never; out of scope forever unless the company publishes it)
- User-submitted corrections with a clerk queue
- EMCLOUD / WCLD / CRN / Forbes AI 50 expansion to ~300
- Historical probe diffs
