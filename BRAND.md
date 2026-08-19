# opentrust.center brand law

This is a **public register**, not a security product and not a luxury brand.

A GRC person or their agent comes here the way they open Companies House or EDGAR: to read the file and leave. We look like a clerk’s desk with three instruments on it. We do not look like Vanta, Linear, Stripe, VoltAgent’s marketing page, or a “dark gold thought leadership” template.

If a screen could also sell a SaaS debit card, a GRC seat, or an AI agent platform, it is wrong. If it sits on beige newsprint, it is wrong. If the headline is painted flame, it is wrong.

This file is law. Read it before any visual change. The audit that produced this revision is `docs/BRAND-AUDIT.md`. The product record is `docs/PRD.md`. If a screen disagrees with those two and this file, the screen is wrong.

## The one sentence

A database of each company’s public trust ledger.

We are no longer only a URL index. We file the public record (the dossier), the map of disclosed subprocessors (the processors), and the book of marks a buyer will meet (the attestations). The company’s own page stays authoritative. We still never look like a GRC SaaS.

The register is the database. Each dossier is that company’s public ledger (official pages, marks, DPA, subprocessors, years).

Do not print “front pane of glass” on the site. That is an internal metaphor. Do not print “in one place.” The clerk already has a word: **on file**.

## How to make this agent better at design

1. **This file is law.** Do not “freshen” it into SaaS.
2. **Send 2–3 references you actually like** for *this* job (a gazette, a filing site, a newspaper, a good directory). They get appended under “References” below. Taste cannot be inferred from “make it nicer.”
3. **Mark what is fake.** After a pass, say the one thing that still feels like a template. It gets added to the no-list.
4. **Do not ask for a moodboard.** Ask for a verdict: registrar, newspaper, or notary. We already picked registrar.
5. **If you want a new color or typeface, change this file first** and say why the registrar metaphor broke. Do not sneak Geist “just for the app.”

## Voice

Speak like the clerk who stamps the page.

- Lowercase name always: `opentrust.center`
- Short sentences. Numbers are facts, not flexes.
- Company names in the register face. URLs, ranks, dates, ids in mono.
- Allowed: found, missing, official, on file, not on file, last probed, silent, thin, substantial, complete, named, filed, cited, ledger.
- Banned: empower, seamless, reimagine, next-gen, in one place, trust made simple, the future of GRC, unlock, delightful, trust score, security rating, powered by, front pane of glass (on-site), OpenTrust.

Hero copy is a finding aid, not a pitch.

| Surface | Aid | Deck |
|---|---|---|
| Register | A database of each company’s public trust ledger. | Attestations, instruments, years. Official page, or not. |
| Processors | Named subprocessors, as published. | Filed from public lists. Not a complete supply chain. |
| Attestations | Marks a buyer will meet. | By geography and industry. ELI-5, then the long form. |

Bad: “Find every trust center in one place.”
Good: “A database of each company’s public trust ledger.”

`<title>`: `opentrust.center — public trust ledger`
Meta: `A database of each company's public trust ledger. Official pages, marks, DPA, subprocessors, years. On file, or not.`

Outbound: `open official page`. Never “Open SafeBase.” Never name the portal vendor on a public surface.

## Metaphor (use this, not gold coins, not a globe-from-orbit)

**A gazette / registrar issue, with three instruments on one desk.**

The register is the index. The dossier is the file. The processors are a hairline map of names the file already gave us. The globe is a desk cartographic object for pointing at a region of marks. Horizontal rules, issue date, stamped mark, tabular names. Paper you could file. A seal that looks pressed in ink, not a 3D medallion.

Nearby kin (steal posture, not pixels): London Gazette *notices*, Federal Register issues, Companies House *company records*, SEC EDGAR *filings*, Oxide’s console table and `Fig. n` habit, VoltAgent’s empty dark field.

Not kin: Vanta, Drata, SafeBase, Notion, Linear, Stripe Press, VoltAgent’s “platform” homepage, “editorial dark mode” agency sites, Product Hunt WebGL globes, neon supply-chain graphs.

## Type

Two faces only.

| Role | Face | Use |
|---|---|---|
| Register | [Newsreader](https://fonts.google.com/specimen/Newsreader) | Company names, the wordmark, findings, ELI-5, dossier titles |
| Docket | [IBM Plex Mono](https://fonts.google.com/specimen/IBM+Plex+Mono) | ranks, domains, URLs, kickers, labels, dates, ids, code, table chrome |

Do not add IBM Plex Sans, Source Serif 4, Inter, Geist, Recoleta, Suisse, GT America, or “a nicer grotesque.” The old site used Source Serif + Plex Sans. That pairing is retired. It is the default “thoughtful AI” stack. It is still live on `/c/*` and must be burned down.

Names are slightly tight (−0.02 to −0.03em). Meta is small, tracked a little, never uppercase-for-style except 1-line kickers (`REGISTER`, `SUBPROCESSORS`, `ATTESTATIONS`, `ISSUE`) and table headers.

### Product scale (px). Do not invent others.

| Token | Face | Size / line | Tracking | Weight | Use |
|---|---|---|---|---|---|
| `--t-kicker` | Plex Mono | 11 / 14 | 0.12em | 500 | Docket, issue line, uppercase headers |
| `--t-meta` | Plex Mono | 12 / 16 | 0.02em | 400 | Domains, dates, factor lines, hosts |
| `--t-row` | Plex Mono | 13 / 18 | 0 | 400 | Table cells that are not names |
| `--t-body` | Newsreader | 16 / 24 | 0 | 400 | Findings, ELI-5, methodology |
| `--t-name` | Newsreader | 17 / 22 | −0.02em | 500 | Register row name |
| `--t-lede` | Newsreader | 20 / 26 | −0.02em | 400 | One-line finding aid (optional) |
| `--t-title` | Newsreader | 28 / 32 | −0.03em | 500 | Dossier / entry / miss title |
| `--t-wordmark` | Newsreader | 20 / 24 | −0.03em | 500 | Mast |
| `--t-stamp` | Newsreader | 12 / 12 | 0 | 600 | `OT` in the ring |
| `--t-figure` | Plex Mono | 11 / 14 | 0.08em | 400 | `Fig. 1 · …` |

Product text never exceeds 28px. No 52px census. No 56px homepage display. The specimen may show 40px once, labeled `specimen — not product`.

Italic Newsreader is absence: `not on file`, `silent`.

## Color

Pukar’s flame scale, sampled from the supplied swatches. Five steps, no beige. Flame is an accent, not a headline.

| Token | Hex | Role |
|---|---|---|
| `--flame` | `#ff6600` | stamp ring, outbound, current docket underline. Rare. |
| `--ember` | `#cc5100` | hover of a flame object, secondary stamp |
| `--rust` | `#993d00` | rules, kickers, `not on file`, table grid |
| `--well` | `#662900` | row hover, figure well, globe land |
| `--ground` | `#331400` | page. Always. |

Derived (washes of the scale, not a sixth brand color):

| Token | Hex | Role |
|---|---|---|
| `--ink` | `#ffc091` | body and names. Washed flame. Not cream. |
| `--mute` | `#e09a60` | meta, issue line, inactive docket |
| `--hair` | `rgba(255, 192, 145, 0.06)` | grid, if any |

- Page is `--ground` `#331400`. Always. The live `#2a1408` is retired.
- Body and names are `--ink` `#ffc091`. The live `#f4ebe0` and `#cbb49a` are beige and retired.
- `--flame` appears at most three times on a screen: OT ring, docket underline, one outbound. Never paint the wordmark or every company name in it. That reads as a warning. The user already found full-flame headlines menacing.
- Do not invert this into a light beige register. That direction is closed.
- No gold. No navy. No mint. No gradient. No glow orb. No `#efe6d2`, `#f4ebe0`, `#cbb49a`, `#d4a24a`.

Links in running text: `--ink`, 1px `--rust` underline, hover `--flame`.
Official outbound: `--flame` text, 1px `--flame` underline. Hover may fill `--flame` / `--ground`. That is the only fill-on-hover.
Missing is `--rust`, italic Newsreader — not a gray pill.

## Mark

A dry **ink stamp**, not a coin.

- Circle, double ring, `OT` in Newsreader 12 / 600.
- 28px. `--flame` on `--ground`, or reversed (`--ground` on a `--flame` block).
- Slight irregularity is fine (as if the pad was dry). Drop shadows, metallic gradients, and skeuomorphic wax are not.
- Never put the mark in a rounded app-icon squircle.
- Never gold.

Wordmark is always `opentrust.center` in Newsreader 20px, lowercase, no tracking out, no “OpenTrust.”

The **disclosure stamp** on a dossier is this ring plus a tier word (`silent` `thin` `on file` `substantial` `complete`) and a factor line in mono. A number without the factor line is a lie. Never a letter grade. Never “trust score.” We rate the *file*, not the company.

## Layout

High-taste staff-engineer product, not a magazine and not a SaaS marketing page.

- **Canvas, not a sheet.** The page is one continuous `--ground` field to the edges (VoltAgent posture). No floating paper card. No centered “document.” No `.sheet` as a card.
- **Surface:** optional 32px grid at `--hair`, only in figure wells. Grain at 0.06 or off. If you notice either, delete it. No glow orb, no mesh blob, no illustration.
- **Docket mast:** 48px high, full width, hairline under. Wordmark left (20px). Instruments as words: `register` `subprocessors` `marks` (Plex Mono 11, tracking 0.12em). Active word: `--ink` + 1px `--flame` underline. OT ring right. No icons. No hamburger if the three words fit. No `Product` / `Docs` / `More`.
- **Issue line** under the mast, Plex Mono 11:

  `issue 18 Aug 2026 PT · 184 on file · 22 not on file · last probed 18 Aug 2026, 3:23 PM PT`

  This replaces the 52px census. The census is banned.

- **Search is a command strip:** 40px, hairline box, Plex Mono 13, `/ stripe, microsoft, soc 2`. No pill, no shadow, no icon.
- **Register is a table.** Columns: `#` · name · domain · tier · marks · probed. One line, ~44px, rust hairline. No card, no summary paragraph, no vendor column, no badge pills.
- **Filters** are a segmented hairline bar of *tiers* (and optionally list). Not vendor chips.
- **Dossier is a page**, `/c/{slug}.html`, 720px measure. Not a drawer. Not a side panel pretending to be a file.
- **Processors** and **attestations** sit on a 1200px measure. Figures have `Fig. n` captions.
- Rhythm is 8px. Gutters 48px (24px on small screens). Radius 0 except the stamp.

## The three instruments

### Register

Find a company. See the disclosure tier. Open the dossier.

No hero. Finder, then the table. Miss state: `Not in the index.` plus unconfirmed guess paths in mono. Do not invent a live search backend in this issue.

### Dossier

The product. Modeled on a Companies House record, not a SaaS drawer.

Always this order. Empty sections still print `not on file`.

1. Crumb: `register / {slug}`
2. Identity: name 28px, domain, list, founded year + source (or `not on file`)
3. Disclosure stamp + factor line
4. Attestations table → `/attestations.html#{id}`
5. Instruments table (trust, security, privacy, DPA, subprocessors, status, bounty / security.txt) — all seven rows, always
6. Named processors table → processors
7. Clerk summary: two sentences, or nothing. No vendor. No marketing reprint.
8. Last probed
9. `open official page` (human-gated, inline) + permalink (this page)

Do not render portal vendors. Keep `vendor` in crawl data only.

### Processors

A processor instrument plus a ranked table. The table is the authority.

- Caption: `Fig. 1 · Named processors, as published`
- Subcaption: `Filed from public subprocessor lists. This is not a complete supply chain.`
- 2D. Hairline rust edges. Nodes are 5–7px squares, not orbs or logos.
- Selected: 1px flame stroke, no halo.
- No bloom, no particles, no neon, no idle physics, no 3D tilt, no community colors.
- Risk is concentration × thin public file, per the PRD. Print the formula. Do not color rows red.
- Edges without a first-party public `source_url` do not ship.

### Attestations

The book of marks. The globe is a pointer, not the product.

- Caption: `Fig. 2 · Geography of marks`
- Filters: geography, industry, kind — hairline bar
- Every entry: name, kind, geography, industry, issuer, weight, ELI-5 (default), elaborate (instant toggle), related marks
- Desk globe (canvas 2D orthographic sphere). No Three.js. No earth texture.
  - 360px square well, rust hairline, on the desk (the page), not full-bleed
  - Sea `--ground` disk, land `--well`, graticule `--rust` 15° or 30°, coast 1px rust, limb 1px rust
  - Marks: 2–3px flame ticks. No pulse, no ping
  - Slight axial tilt. Slow idle spin (~0.1 rad/s). Pause while dragging; resume after a beat. `prefers-reduced-motion`: still; drag still works. No zoom-from-space
  - No bloom, no atmosphere, no starfield, no Blue Marble, no city lights, no clouds, no envmap, no wooden stand
  - Click region → filter the book. Click tick → `#id`

## Motion

Almost none. The register does not bounce, fade-slide, or shimmer. Instant open. If you need a wait state, a mono line is enough: `checking…`

The human gate is a **stamp box** inline under the outbound (checkbox + “I am human”), not a Cloudflare cosplay and not a modal. ≤300ms. On pass: `verified · 30 min`. No “Before you leave.”

Globe: slow idle spin; pause on drag. Processors: settle, then stop.

## Imagery

We do not use stock “locks on blue.” We do not generate hero illustrations. If an image exists, it is a scan, a stamp, a figure of our own instrument, or a screenshot of a real portal — captioned `Fig. n`.

No logo clouds. No testimonial rails. No integration marquees.

## What this site must never look like

- Beige, cream, newsprint, manila, or any light-paper register
- Dark paper + gold foil + serif (the first look; also every “premium AI” landing page)
- Cream ink (`#f4ebe0`) or beige mute (`#cbb49a`) on espresso (the second look’s leftover)
- Inter / Geist, 8pt tracking, blur orbs, glass
- Vanta mint, Drata navy, SafeBase purple, VoltAgent teal
- Three feature columns with line icons
- Gradient wordmarks
- Rounded-xl card grids with badge pills
- A marketing homepage above the register (lede + 52px census + vendor chips)
- A SaaS slide-over instead of a dossier
- A product menu (`Platform`, `Docs`, `Resources`) instead of a docket
- A Three.js glow globe (bloom, atmosphere, stars, auto-rotate, Blue Marble)
- A neon force-directed “risk graph”
- Dashboard numbers ≥ 36px
- Flame headlines or flame company names
- Portal-vendor chips or “powered by”

## UI inventory

Build only these surfaces:

- home register (`/`)
- company dossier (`/c/{slug}.html`)
- processors (`/graph.html`)
- attestations + globe (`/attestations.html`, `#id` for an entry)
- processor stub (on processors, for names not in the register)
- miss (not on file)
- human stamp (inline)
- `llms.txt`
- this brand specimen
- `data.json` (no vendor in the rendered sense)

No blog theme, no “platform” nav, no pricing chrome, no login, no marketing homepage.

## References

- Volta / VoltAgent *canvas*: continuous dark field, hairlines, no orb. https://voltagent.dev/ and https://volta.sh (field and command posture only — not VoltAgent’s platform pitch).
- Oxide.computer: mono chrome, `Fig. n`, console as a table, nav as instruments. https://oxide.computer/
- Companies House company record: labeled fields, tables, missing rows that still print. https://www.gov.uk/get-information-about-a-company
- EDGAR search: filing as the object, tape of latest, precise form. https://www.sec.gov/edgar/search-and-access
- Federal Register: issue identity (volume, number, date). https://www.federalregister.gov/
- The Gazette *notice* (type, number, date, body) — not the current marketing homepage. https://www.thegazette.co.uk/

Do not copy their CSS, green, teal, or GOV.UK blue.

## Change control

If you want a new color or typeface, change this file first and say why the registrar metaphor broke. Do not sneak Geist “just for the app.”

After a visual pass, name the one fake thing that remains. Add it to the no-list.

Do not overwrite this law with a moodboard.
