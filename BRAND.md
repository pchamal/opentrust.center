# opentrust.center brand law

**Open Record (OT-BRAND-001).** A public evidence register, not a security product and not a luxury brand.

A GRC person or their agent opens this site the way they open Companies House or EDGAR: to read the file and leave. The page is a civic record — black binding, white paper, one mineral-teal index. It is serious without being severe.

If the wordmark is removed, the page must still look like a public record. If a screen could also sell a SaaS seat, a debit card, or an AI agent platform, it is wrong.

This file is law. The machine copy is `docs/OT-BRAND-001.yaml`. The product record is `docs/PRD.md`. Evidence semantics in the PRD outrank any visual preference: rate the file, not the company; missing private evidence is inconclusive; no portal-vendor names; no trust score.

## The one sentence

A database of each company’s public trust ledger.

We file the public record (the dossier), the map of disclosed subprocessors, and the book of marks a buyer will meet. The company’s own page stays authoritative. Disclosure tiers (`silent` / `thin` / `on file` / `substantial` / `complete`) are **file ratings**, never company trust. The file tier `complete` reads as **public file complete**.

Do not print “front pane of glass” on the site. Do not print “in one place.” The clerk already has a word: **on file**.

## How to make this agent better at design

1. **This file is law.** Do not freshen it into SaaS.
2. **Send 2–3 references you actually like** for *this* job (a gazette, a filing site, a newspaper, a good directory). They get appended under “References” below.
3. **Mark what is fake.** After a pass, say the one thing that still feels like a template. It gets added to the no-list.
4. **If you want a new color or typeface, change this file first** and say why the public-record metaphor broke. Do not sneak Inter “just for the app.”
5. **Do not alias retired tokens.** Map by role. Grep-delete rust / flame / espresso leftovers.

## Voice

Speak like the clerk who stamps the page.

- Lowercase name always: `opentrust.center`
- Short sentences. Numbers are facts, not flexes.
- Company and offering names in the editorial face. Everything else in the utility face. Tabular numbers on data.
- Sentence case for nav and buttons. Uppercase only for SOC, ISO, DPA, and IDs.
- Use: observed, source, scope, unknown, not on file, last reviewed, public evidence, silent, thin, on file, substantial, public file complete, named, filed, ledger.
- Never: trusted company, verified company, complete (without “complete for what”), AI-powered, unlock, seamless, single source of truth, empower, reimagine, next-gen, in one place, trust made simple, the future of GRC, delightful, trust score, security rating, powered by, OpenTrust.

Buttons: **Open dossier**, **View source**, **Report a correction**. Not Get started / Unlock insights.

| Surface | Aid | Deck |
|---|---|---|
| Register | A database of each company’s public trust ledger. | Public evidence, as filed. Official page, or not. |
| Processors | Named subprocessors, as published. | Filed from public lists. Not a complete supply chain. |
| Attestations | Marks a buyer will meet. | By geography and industry. ELI-5, then the long form. |

`<title>`: `opentrust.center — public trust ledger`
Meta: `A database of each company's public trust ledger. Official pages, marks, DPA, subprocessors, years. On file, or not.`

Outbound: `View source`. Never “Open SafeBase.” Never name the portal vendor on a public surface.

## Metaphor

**A civic evidence registry.** Binding, paper, and one index mark. Horizontal rules, issue date, tabular names. Paper you could file. Not a coin, not a shield, not a check.

Nearby kin (steal posture, not pixels): Companies House *company records*, SEC EDGAR *filings*, Federal Register issues, London Gazette *notices*, a clerk’s desk.

Not kin: Vanta, Drata, SafeBase, Notion, Linear, Stripe Press, VoltAgent’s “platform” homepage, Product Hunt WebGL globes, neon supply-chain graphs, rust-flame “registrar” skins, beige newsprint luxury.

## Type

Two faces only. Self-host WOFF2 in `site/fonts/`. `font-display: swap`. Prototype CDN only if self-host fails.

| Role | Face | Use |
|---|---|---|
| Editorial | [Source Serif 4](https://fonts.google.com/specimen/Source+Serif+4) | Wordmark, company names, offering names, H1 |
| Utility | [Atkinson Hyperlegible Next](https://fonts.google.com/specimen/Atkinson+Hyperlegible+Next) | Everything else. Tabular-nums on data. |

Do not add Inter, Manrope, DM Sans, Space Grotesk, Newsreader, IBM Plex Mono, Geist, Recoleta, or “a nicer grotesque.” No tiny monospace.

Minimum: 13px data, 16px body.

| Token | Face | Size / line | Tracking | Weight | Use |
|---|---|---|---|---|---|
| `--t-data` | Utility | 13 / 18 | 0 | 400 | Table cells that are not names; tabular-nums |
| `--t-meta` | Utility | 13 / 18 | 0 | 400 | Domains, dates, factor lines, snapshot |
| `--t-body` | Utility | 16 / 24 | 0 | 400 | Findings, methodology, ELI-5 |
| `--t-name` | Editorial | 17 / 22 | −0.02em | 600 | Register row name |
| `--t-lede` | Utility | 16 / 24 | 0 | 400 | One-sentence scope |
| `--t-page` | Utility | 28 / 32 | −0.025em | 600 | Page titles. Work text. |
| `--t-title` | Editorial | 28 / 32 | −0.025em | 600 | Company / offering names only |
| `--t-wordmark` | Editorial | 20 / 24 | −0.025em | 600 | Mast. Period only in Evidence Teal. |

Wordmark is always `opentrust.center`, lowercase, Source Serif 4 600, tracking −0.025em. Color **only** the period before `center` in Evidence Teal. Other letters Ledger Black on light, Record White on the dark mast.

## Color

Exact tokens. No aliases. No leftover rust.

| Token | Hex | Role |
|---|---|---|
| `--ot-ledger-black` | `#0B1411` | Binding. Mast. Ink on paper. |
| `--ot-carbon` | `#17211D` | Spine nodes with a source. |
| `--ot-record-white` | `#F8FAF9` | Page field. Type on the dark mast. |
| `--ot-sheet-white` | `#FFFFFF` | Register table, dossier sheet |
| `--ot-paper` | `#EDF2F0` | Snapshot line. Row hover. |
| `--ot-graphite` | `#51615B` | Meta, domain, marks, inactive nav |
| `--ot-rule` | `#CBD5D1` | Hairline rules |
| `--ot-rule-strong` | `#70817A` | Meter outlines, stronger rules |
| `--ot-evidence-teal` | `#00685C` | Index. Spine. Focus ring. Wordmark period. Rare. |
| `--ot-deep-teal` | `#004E46` | Hover of a teal object |
| `--ot-index-wash` | `#DDEFEA` | Selected row / selected claim |
| `--ot-bright-teal` | `#73D2C2` | Active nav rule on the dark mast only |
| `--ot-source-fg` / `--ot-source-bg` | `#245E3A` / `#E5F3EA` | A source exists |
| `--ot-attention-fg` / `--ot-attention-bg` | `#835000` / `#FFF2D2` | Needs a look |
| `--ot-conflict-fg` / `--ot-conflict-bg` | `#9A2D2A` / `#FBE9E8` | Conflict |
| `--ot-unknown-fg` / `--ot-unknown-bg` | `#4F5F59` / `#EDF1EF` | Unknown / not on file |

`--ot-spine`: 2px. `--ot-radius-control`: 3px.

Teal is at most **6%** of a routine view: the wordmark period, the 2px Evidence Spine, and one active nav underline. Mid-dot punctuation (`·`) stays ink or mute, never teal. Focus ring is the accessibility exception. Teal must not fill boxes, meters, or chrome. No gradients. No second accent. No cards. No pills.

Retired (grep-delete, do not alias): `#ff6600`, `#331400`, `#662900`, `#993D00`, `--flame`, `--espresso`, `--rust`, `--ember`, `--well` as brown.

Unknown / not on file stay the unknown pair. Never green.

## Mark

**Open Index.** Not a circle, not a shield, not a check. Do not put it on a vendor status. Do not use an OT stamp as a certification seal.

24×24. 2px Evidence Teal vertical spine at x=7, y=3–21. 2px Ledger Black top rule x=7–20 y=7. 2px Ledger Black bottom rule x=7–16 y=17.

The **Evidence Spine** is the only signature device: 2px vertical Evidence Teal. Register hover / selected: spine only, at the left edge of the row. No square node, no pip, no period by the `#`. No Index Wash as a full-row fill — it blows the teal budget. Dossier chronology / claim list: spine with 7px square nodes (filled = source exists, outline = pending/unknown, split = conflict). Every node has text. Never a progress bar or score gauge.

## Layout

- **Paper field, black mast.** Record White page to the edges. Sheet White table. No floating card. No centered “document” that looks like a marketing sheet.
- **Mast:** 64px (56px mobile), Ledger Black, Record White type. Wordmark left. Nav centered. Active = 1px Evidence Teal underline (chrome, not the signature). No CTA, no pills, no glow, no OT ring.
- **Snapshot** under the mast: Paper, 1px Rule bottom, utility type. Issue date, on file / not on file counts, last probed. No ISO dataset stamp. Not a KPI strip.
- **Gutters:** 16 / 24 / 32 / 48.
- **Search** is a ruled strip. No pill, no shadow, no icon.
- **Register** is a table. Columns: `#` · name · domain · file · marks. No probed column. 52px rows, Rule bottoms. Hover or selected: 2px Evidence Teal spine at the left edge only. Name is editorial and the loudest cell. Marks print the named marks that fit, with `·` separators. No `+N`.
- **File cell** is five short rules, one per instrument, in this order: page · marks · DPA · subprocessors · years. On file = filled Ledger Black. Not on file = open hairline Ledger Black. Missing stays empty (inconclusive), not a red X and not a hollow fail. Evidence Teal does not fill the rules. No printed N of 5. No silent / thin / substantial / complete on the row. No stars. No “trust maturity index.”
- **File legend** prints once above the grid: page · marks · DPA · subprocessors · years. Not a tooltip farm.
- **Default arrange** is last probed, newest first. File header still sorts 0–5 instruments on file (or reverse). First screen must not be twenty identical empty files.
- **Pagination or windowing.** Do not mount all 700+ rows. No infinite scroll. Preserve query, sort, and count.
- **Compact (≤639px):** each org is a ruled record (not a card): name, domain, file index, marks. The name is the link. No “More on this file.”
- **Dossier** is a page, `/c/{slug}.html`. Org name is the H1. Status describes a claim, source, or observation — never a company trust badge.
- Rhythm is 8px. Control radius 3px. Skip link. One H1. Tables with `th`/`scope`. Touch 44px. 320px: no page overflow.

## The three instruments

### Register

Find a company. See observed file state. Open the dossier.

H1: `Public trust register`. One-sentence scope: `A database of each company’s public trust ledger.` Finder, then the table. Miss state: query summary, reset, request / correction path. No “no worries.” No cute empty.

### Dossier

The product. Modeled on a Companies House record.

Always this order on the first screen. Empty rows still print italic `not on file`. Missing is inconclusive.

1. Crumb: `register / {slug}`
2. Identity: name in Source Serif 4, domain in Atkinson, then the same five file rules under the domain. 2px Evidence Spine on the left of this block (name + domain + file line). Not a boxed file-state module. No disclaimer. No coverage ratio. No stars. No apology line.
3. Instruments: a ruled table. One instrument is one unit (label, host, date), then one rule. Empty rows italic `not on file`. Labels in Atkinson, including `subprocessors`.
4. Marks: a list in Atkinson, same as instrument labels. Not chips. Not bold Source Serif. What does not fit wraps below. No `+N`.
5. Official outbound: text link `Official page`. Human-gated. No flame / teal fill button.

Dossier issue line: issue date and last probed. Do not print the register census.

Below the fold: FedRAMP marketplace table, named processors, clerk summary, last probed, Report a correction, permalink.

FedRAMP: cite the marketplace (`Filed from the FedRAMP Marketplace`, linked). No “not a badge,” no “not a score,” no disclaimer. Ruled table: offering, status, impact, auth date. Empty cells italic `not on file`. Status words are facts (authorized, in process, not yet certified, not on file), not a color grade. Not-yet-certified / initial-implementation listings stay on file. A marketplace row is never four invented misses. Missing is inconclusive.

Named processors: ruled table of names as published. If the list URL is on file and names were not extracted: `list on file · names not extracted` plus the source URL. Italic `not on file` only when the list itself is absent. Never a false miss. No smear sentences. No `+N`. What does not fit continues below. No graph, orbs, or risk coloring. Fig. 1 stays on `/graph`.

Spine stays on the identity block only. Do not add a second spine on FedRAMP or named processors.

Do not render portal vendors. Keep `vendor` in crawl data only. Nav must not mark Register as current on a dossier. Rate the file, never the company.

### Processors

A table plus a 400px inspector. The table is the authority.

- Caption: `Fig. 1 · Named processors, as published`
- Subcaption: `Filed from public subprocessor lists. This is not a complete supply chain.`
- Selected row gets the spine.
- Concentration is **exposure × thin public file**, per the PRD. Do not print RISK as a security grade.
- Fig. 1 may stay if labels are readable and it is not a glowing hairball; otherwise drop the fan and keep the table.

### Attestations

The book of marks. The list is primary.

- One hairline facet row, or finder-style facets. Sentence case. No three-row pill farm.
- Every entry: name, kind, geography, industry, issuer, weight, ELI-5 (default), elaborate, related marks
- Globe, if it remains, is a secondary desk object. **No auto-rotate.** Drag still works. `prefers-reduced-motion`: still.

## Motion

Mechanical. ≤220ms. `cubic-bezier(0.2, 0, 0, 1)`. No bounce, shimmer, glow, typing dots, or auto-rotating globe. `prefers-reduced-motion`: instant.

## Accessibility

WCAG 2.2 AA. Focus: 3px Evidence Teal ring, 2px offset. Skip link. One H1. Tables with `th`/`scope`. Touch 44px. 320px: no page overflow.

## What this site must never look like

- Rust / flame / espresso “registrar” skins
- Beige luxury newsprint or dark-gold thought leadership
- Inter / Geist, 8pt tracking, blur orbs, glass
- Vanta mint, Drata navy, SafeBase purple, a second accent
- Three feature columns with line icons
- Gradient wordmarks
- Rounded-xl card grids with badge pills
- A marketing homepage above the register
- A SaaS slide-over instead of a dossier
- A product menu (`Platform`, `Docs`, `Resources`) instead of a docket
- A Three.js glow globe (bloom, atmosphere, stars, auto-rotate)
- A neon force-directed “risk graph”
- Dashboard numbers ≥ 36px
- Teal company names or teal-as-success
- Portal-vendor chips or “powered by”
- An OT stamp that reads as certification

## UI inventory

Build only these surfaces:

- home register (`/`)
- company dossier (`/c/{slug}.html`)
- processors (`/graph.html`)
- attestations (`/attestations.html`, `#id` for an entry)
- processor stub (on processors, for names not in the register)
- miss (not on file)
- human stamp (inline)
- `llms.txt`
- this brand specimen
- `data.json` (no vendor in the rendered sense)

No blog theme, no “platform” nav, no pricing chrome, no login, no marketing homepage.

## References

- Companies House company record: labeled fields, tables, missing rows that still print. https://www.gov.uk/get-information-about-a-company
- EDGAR search: filing as the object, tape of latest, precise form. https://www.sec.gov/edgar/search-and-access
- Federal Register: issue identity (volume, number, date). https://www.federalregister.gov/
- The Gazette *notice* (type, number, date, body) — not the current marketing homepage. https://www.thegazette.co.uk/

Do not copy their CSS, green, teal, or GOV.UK blue. Our one index color is Evidence Teal, used as an index, not as a theme.

## Change control

If you want a new color or typeface, change this file and `docs/OT-BRAND-001.yaml` first. Do not sneak Geist “just for the app.” Do not alias `--rust` to `--ot-rule`.

After a visual pass, name the one fake thing that remains. Add it to the no-list.

Do not overwrite this law with a moodboard.
