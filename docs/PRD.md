# opentrust.center — product record

Issue date: 2026-08-19
Status: build from this
Owner: Pukar Hamal
Site: https://opentrust.center
Code: https://github.com/pchamal/opentrust.center

This is the product law for the front-pane rebuild. If a screen disagrees with this file, the screen is wrong.

---

## The job

A GRC or security person (or their agent) opens opentrust.center the way they open Companies House.

They do not want to know that Stripe’s portal is “powered by SafeBase.” They want to know what Stripe publishes: which attestations, which security and privacy pages, how long the firm has been operating, who they name as subprocessors, and whether that public file is thin or complete.

Those asks are buyer jobs already written in law and guidance. The spine below is that map. The company’s own pages stay authoritative. We file what is public, rate the file, and show the wires between firms. We do not sell trust. We do not replace a questionnaire. We do not name the portal vendor.

One-liner: `A database of each company’s public trust ledger.`

---

## Buyer jobs (spine)

A GRC, security, trust, or assurance lead arrives with a vendor name and about ninety seconds. The jobs below are why the register exists. Each job cites an authority. The public ledger files only what a first-party page, a named marketplace, or a cited instrument actually published. Missing private evidence is inconclusive, not a fail.

One-liner stays: `A database of each company’s public trust ledger.`

### Job 1 — Pre-contract due diligence

The buyer is deciding whether this vendor can even enter the file.

**On file (public).** Official trust or security page. Named attestations, with the mark book next to them. Instruments (DPA, status, bounty / security.txt, privacy). Founded year when sourced. FedRAMP marketplace lifecycle when matched. Human-gated outbound to the official page.

**Not on file (do not invent).** Full SOC 2 / C5 / IRAP report text. Questionnaire answers. Contract markups. Criticality of *this* supplier to *this* buyer. Concentration against the buyer’s own estate.

**Surface.** Register finder → dossier. Marks for “what is this stamp.”

**Cites.** [SRC-NIST-SP-1305] [SRC-DORA] [SRC-NCSC-QUESTIONS] [SRC-CISA-SECURE-BY-DEMAND] [SRC-GDPR-28]

NIST SP 1305 is the C-SCRM quick-start: identify suppliers, set requirements that match criticality, ask for evidence (self-attestation, standard, certification, inspection) before acquisition. DORA makes pre-contract risk, due diligence, and concentration a duty for in-scope financial entities. NCSC’s question set is the English of that homework (governance, incidents, network and data, offshoring, personal data, people, physical, testing, contracts). CISA Secure by Demand splits *product* security from the vendor’s *enterprise* security — a trust page that only talks ISMS has not answered the product question. GDPR 28 is the processor-contract floor, not a logo.

### Job 2 — Ongoing monitoring

The buyer already bought. They need to see whether the public file moved.

**On file.** Last probed. Disclosure tier and the five-box meter (page, marks, DPA, subprocessors, years). New or dropped marks. Subprocessor edges with source URLs. FedRAMP status if the marketplace listing changed.

**Not on file.** Continuous control monitoring. Pen-test cadence. SLA breach history. Buyer-side watchers, alerts, or login.

**Surface.** Register issue line. Dossier “last probed.” Later: watch-when-the-file-changes (proposed, not built).

**Cites.** [SRC-NIST-SP-1305] [SRC-DORA] [SRC-NCSC-CRITICALITY]

SP 1305 tells the acquirer to monitor supplier performance through the life of the relationship (GV.SC-03 / GV.SC-09). DORA requires ongoing ICT-third-party monitoring, not a one-time pack. NCSC says the evidence burden follows criticality — a silent row on a critical vendor is a different fact than a silent row on a low-impact tool.

### Job 3 — Incident and termination / exit

The buyer is planning for the day the vendor fails, is sold, or is exited.

**On file.** Status page, if published. Named subprocessors (who else is in the blast radius). Public incident or status history only when the company published it. DPA clauses we can *see* (often none).

**Not on file.** RTO, RPO, substitutability scores, exit runbooks, escrow, data-return formats, joint incident roles. DORA register-of-information fields of this kind are buyer-private. Do not scrape them. Do not infer them from a status-page URL.

**Surface.** Dossier instruments. Subprocessor graph for concentration. Print-this-file and watch-the-file are later instruments, not current capabilities.

**Cites.** [SRC-NIST-SP-1305] [SRC-DORA] [SRC-DORA-TEMPLATES]

SP 1305 puts suppliers inside incident planning, response, and recovery (GV.SC-08). DORA names transition and exit as first-class duties. The 2024 templates show the *shape* of a register of information. They do not authorize us to invent RTO/RPO on a public dossier.

### Job 4 — Requirements that vary with criticality and data

The same vendor is not the same review twice. Criticality and data class change the burden.

**On file.** What the vendor published, at one depth, for every name. The five boxes and the mark list. Geography and industry of marks (the book). Product-security artifacts when they exist (security.txt, bounty, status) versus enterprise marks (ISO 27001, SOC 2).

**Not on file.** *This buyer’s* criticality rating of *this* vendor. Data classification of the tenant. Target profiles per criticality tier (NIST’s method). We do not run the buyer’s C-SCRM program.

**Surface.** Register (same columns, different files). Marks filtered by geography / industry / kind. Finder tokens (`/ complete`, `/ fedramp moderate`).

**Cites.** [SRC-NIST-SP-1305] [SRC-NCSC-CRITICALITY] [SRC-CISA-SECURE-BY-DEMAND]

SP 1305: robustness of supplier requirements corresponds to supplier criticality; Target Profiles are how a serious acquirer says that. NCSC: have confidence *in proportion*. CISA: do not let an enterprise SOC 2 stand in for product-security outcomes you should have contracted.

### Job 5 — Authorization boundary and the system as filed

The buyer needs to know *what* was assessed: which system, which environment, which data flow.

**On file.** Scope we can quote from a public page or a marketplace listing (service name, FedRAMP offering, region if stated). Instrument URLs. Clerk summary that does not invent a boundary.

**Not on file.** The system security plan. Data-flow diagrams. Control implementation statements. Assessment plans, results, findings, POA&M. Those are OSCAL assessment-layer objects and 800-18r2 SSP contents. They are almost never public. A trust-page sentence is not a boundary.

**Surface.** Dossier instruments and FedRAMP row. OSCAL is a future interchange, not a current import.

**Cites.** [SRC-NIST-800-18R2] [SRC-OSCAL-LAYERS] [SRC-OSCAL-ASSESSMENT]

SP 800-18 Revision 2 is how a U.S. system owner writes the authorization boundary, components, environments, data flows, controls, and risk decisions. OSCAL is the machine-readable layering (catalog → profile → implementation → assessment). We cite them so we do not pretend a five-box meter is an SSP.

### Job 6 — Processor, subprocessor, notice, audit support

The buyer is under GDPR 28 (or a cousin). They need processor guarantees, a way to hear about subprocessor change, and a path to information and audit.

**On file.** Public DPA or DPA addendum URL. Public subprocessor list, each edge sourced. Graph of who named whom. “Not on file” when the list is behind a login.

**Not on file.** The signed DPA. Thirty-day notice terms. Audit-right markups. Private SafeBase / NDA packs. A login wall is not a public ledger.

**Surface.** Dossier (DPA + named processors). `/graph` (exposure, source, file on the right).

**Cites.** [SRC-GDPR-28]

Article 28 is the spine of the processor file: guarantees, onward processor authorization and notice, and assistance with information and audits. We file the *public traces* of those duties. We do not certify that Article 28 is met.

### Job 7 — How to read a mark

The buyer is looking at a stamp and must not be lied to.

**On file.** The mark book: kind (attestation / certification / authorization / regulation / framework / questionnaire / code of practice). ELI-5 then long form. Issuer. Geography. Related marks. Weight as a *disclosure* weight, not a security grade. CSA STAR as self-assessment versus independent. FedRAMP as marketplace lifecycle, “not a badge.” ISO named with version awareness. SOC 3 called general-use; SOC 2 treated as restricted-use unless a public SOC 3 exists.

**Not on file.** The report. The accreditation of the certification body on that engagement. A letter grade.

**Surface.** `/attestations` (marks). Dossier attestation table. Register marks column.

**Cites.** [SRC-AICPA-TSC] [SRC-AICPA-SOC3] [SRC-ISO-CERTIFICATION] [SRC-ISO-27001] [SRC-CSA-STAR]

TSC are the criteria *inside* a SOC 2 (security, availability, processing integrity, confidentiality, privacy). SOC 3 is the general-use cousin; a public SOC 3 is not a SOC 2. ISO does not certify organizations — accredited bodies do. ISO/IEC 27001 is a named, versioned standard, not a synonym for “has a certificate.” STAR Registry is where self-assessment and independent layers must be told apart.

### Job 8 — Schema inspiration, not a scrape (DORA register of information)

The EU templates show what a serious *buyer-side* register holds: service, countries, locations, criticality, RTO, RPO, substitutability, audit, exit, subcontractor rank.

**On file.** Only the public shadows of that schema: service name, public country/region claims, named subcontractor / subprocessor rank as published, public audit *marks* (not the audit).

**Not on file.** The rest. Limitation on [SRC-DORA-TEMPLATES]: many of these fields are buyer-private and must not be presumed public.

**Surface.** None as a DORA RoI. Do not add RTO/RPO columns to the register.

**Cites.** [SRC-DORA-TEMPLATES]

### Build cite (not a buyer job)

Extensionless canonical routes on the Worker follow [SRC-CLOUDFLARE-HTML]. That is plumbing. It is not a GRC job.

---

## Cited authorities

This register files **public** ledgers only. Buyer-private fields (RTO/RPO, exit plans, full audit rights, private SOC reports) must not be presumed on file. Missing private evidence is inconclusive, not a fail.

| id | authority | title | url | used_for | limitation |
|---|---|---|---|---|---|
| SRC-NIST-SP-1305 | NIST | NIST Cybersecurity Framework 2.0: Quick-Start Guide for Cybersecurity Supply Chain Risk Management (C-SCRM) (NIST SP 1305) | https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=958604 | pre-contract due diligence; ongoing monitoring; incident and termination planning; requirements that vary with criticality and data | |
| SRC-NIST-800-18R2 | NIST | NIST releases SP 800-18 Revision 2 | https://csrc.nist.gov/News/2026/nist-releases-sp-800-18r2 | authorization boundary; components, environments, data flows, controls, and risk decisions | |
| SRC-DORA | European Union | Regulation (EU) 2022/2554, Digital Operational Resilience Act | https://eur-lex.europa.eu/eli/reg/2022/2554/oj | pre-contract risk, due diligence, concentration, monitoring, transition, and exit | |
| SRC-DORA-TEMPLATES | European Union | Commission Implementing Regulation (EU) 2024/2956 | https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX%3A32024R2956 | register fields and relationship structure; service, countries, locations, criticality, RTO, RPO, substitutability, audit, exit, and subcontractor rank as schema inspiration | Many of these are buyer-private and must not be presumed public. This register files public ledgers only. Buyer-private fields (RTO/RPO, exit plans, full audit rights, private SOC reports) must not be presumed on file. Missing private evidence is inconclusive, not a fail. |
| SRC-GDPR-28 | European Union | GDPR Article 28 | https://eur-lex.europa.eu/legal-content/EN/TXT/?qid=1590424137028&uri=CELEX%3A32016R0679 | processor guarantees; subprocessor change notice; information and audit support | |
| SRC-NCSC-QUESTIONS | UK National Cyber Security Centre | Supplier assurance questions | https://www.ncsc.gov.uk/guidance/supplier-assurance-questions | governance, incidents, network and data, offshoring, personal data, people, physical controls, testing, and contracts | |
| SRC-NCSC-CRITICALITY | UK National Cyber Security Centre | Supplier assurance: having confidence in your suppliers | https://www.ncsc.gov.uk/blog-post/supplier-assurance-having-confidence-in-your-suppliers | varying the evidence burden with supplier criticality and risk | |
| SRC-CISA-SECURE-BY-DEMAND | CISA | Secure by Demand Guide | https://www.cisa.gov/sites/default/files/2024-08/SecureByDemandGuide_080624_508c.pdf | product security versus enterprise security; procurement, contracting, and ongoing product-security outcomes | |
| SRC-AICPA-TSC | AICPA and CIMA | 2017 Trust Services Criteria with revised points of focus 2022 | https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022 | security, availability, processing integrity, confidentiality, and privacy criteria | |
| SRC-AICPA-SOC3 | AICPA and CIMA | SOC 3 information | https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-3 | general-use versus restricted-use assurance material | |
| SRC-ISO-CERTIFICATION | ISO | Certification | https://www.iso.org/certification.html | ISO does not certify organizations; external certification bodies and accreditation distinction | |
| SRC-ISO-27001 | ISO | ISO/IEC 27001 | https://www.iso.org/standard/27001 | precise standard naming and version awareness | |
| SRC-CSA-STAR | Cloud Security Alliance | STAR Registry | https://cloudsecurityalliance.org/star/ | self-assessment versus independent certification or attestation | |
| SRC-OSCAL-LAYERS | NIST | OSCAL layers and models | https://pages.nist.gov/OSCAL/learn/concepts/layer/ | machine-readable controls, implementation, and assessment architecture | |
| SRC-OSCAL-ASSESSMENT | NIST | OSCAL assessment layer | https://pages.nist.gov/OSCAL/learn/concepts/layer/assessment/ | assessment plans, results, evidence, findings, and POA&M relationships | |
| SRC-CLOUDFLARE-HTML | Cloudflare | Workers static assets advanced HTML handling | https://developers.cloudflare.com/workers/static-assets/routing/advanced/html-handling/ | extensionless canonical route recommendation | |

---

## Observed product patterns (not law)

Patterns are observed product behavior, not authorities. We still hide portal-vendor names on the public site.

This register files **public** ledgers only. Buyer-private fields (RTO/RPO, exit plans, full audit rights, private SOC reports) must not be presumed on file. Missing private evidence is inconclusive, not a fail.

| id | title | url | observed | limitation |
|---|---|---|---|---|
| PATTERN-VANTA | Vanta Trust Center documentation | https://help.vanta.com/en/articles/11345469-vanta-trust-center | public versus requestable evidence, updates, resources, subprocessors, and access workflows | Observed pattern, not law. Do not name this portal vendor on the public site. |
| PATTERN-DRATA-SAFEBASE | Drata SafeBase integration for TPRM reviews | https://help.drata.com/en/articles/14446304-safebase-integration-for-tprm-reviews | public-only evidence versus fuller private review; missing private evidence as inconclusive | Observed pattern, not law. Missing private evidence is inconclusive, not a fail. This register files public ledgers only. Buyer-private fields (RTO/RPO, exit plans, full audit rights, private SOC reports) must not be presumed on file. Do not name this portal vendor on the public site. |
| PATTERN-DRATA-REVIEW | Drata security review | https://help.drata.com/en/articles/14447644-conducting-a-security-review | criterion citations, overrides, follow-up questions, risks, and activity trail | Observed pattern, not law. Buyer-private review fields must not be presumed on file. Do not name this portal vendor on the public site. |
| PATTERN-FEDRAMP | FedRAMP Marketplace | https://www.fedramp.gov/marketplace/ | offering-level public lifecycle metadata with controlled authorization package access | Observed pattern, not law. Controlled authorization packages are not public ledger rows. |

---

## Live and repository sources

As of the 2026-08-19 snapshot. Counts may change.

- https://opentrust.center/
- https://opentrust.center/c/openai
- https://opentrust.center/c/wipro
- https://opentrust.center/graph
- https://opentrust.center/attestations
- https://opentrust.center/claim?slug=openai
- https://github.com/pchamal/opentrust.center

---

## Audit / spine limitations

- Live audit was read-only; no correction form, GitHub issue, outbound evidence submission, or deployment was completed as part of that audit.
- Responsive tests used browser emulation and screenshots, not a physical device lab.
- Accessibility checks included DOM, contrast, focus, and keyboard-semantics inspection, not a complete assistive-technology certification.
- Performance timings were a single lab observation, not field Core Web Vitals.
- Live counts and dates are an observed 2026-08-19 snapshot and may change.
- Future buyer workspace, monitoring, private evidence access, and incident features are proposed product architecture, not verified current capabilities.
- The exact palette and spacing should be visually QA'd in implementation; token contrast was measured, but design quality still requires rendered review.

---

## What this spine forbids

- Treating disclosure tier as a security rating, trust score, or letter grade.
- Presuming DORA RoI fields (RTO, RPO, exit, substitutability, buyer criticality) from a public page.
- Calling a company “ISO certified” without a body and a scope, or implying ISO the organization issued the paper.
- Equating a public SOC 3 (or a TSC name on a page) with a restricted-use SOC 2 report.
- Equating CSA STAR Level 1 with independent certification.
- Importing OSCAL assessment objects we do not have.
- Naming portal vendors on the public file.
- Filling empty processor, DPA, or mark rows to look complete.

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

No blog. No pricing. No “platform” nav. The mast is a docket: `register · subprocessors · marks`.

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
  graph.html              subprocessors
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
opentrust.center          register   subprocessors   marks     OT
```

Active item is a hairline underline. Not a pill.

---

## Voice (from BRAND.md)

Clerk. Lowercase wordmark. Short sentences. Numbers are facts.

Allowed: found, missing, on file, not on file, silent, thin, substantial, complete, last probed, named, filed, ledger.

Banned: empower, seamless, reimagine, next-gen, in one place, trust made simple, the future of GRC, unlock, delightful, front pane of glass (that is our internal metaphor, not the headline), trust score, powered by.

One-liner: `A database of each company’s public trust ledger.`
Register aid (if printed): `A database of each company’s public trust ledger.`
Deck: `Attestations, instruments, years. Official page, or not.`
The register prints finder, then the table. Do not add a homepage lede.

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
