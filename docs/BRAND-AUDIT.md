# Brand audit — opentrust.center

Issue: 18 Aug 2026 (PT)
Live read: https://opentrust.center/ (same markup as `/workspace/trust-index/site/index.html` + `styles.css`)
Law read: `/workspace/trust-index/BRAND.md`
Product record: `/workspace/trust-index/docs/PRD.md`
References opened: voltagent.dev, volta.sh, oxide.computer, gov.uk company search, federalregister.gov, sec.gov/edgar/search-and-access, thegazette.co.uk

This is a visual and structural audit, not a moodboard. Steal structure. Do not steal teal, green, or GOV.UK blue.

Verdict: the live site is a competent dark directory. It is not yet a register. The gap to 10–20× is not polish. It is that we still present a *list of URLs* in the costume of a clerk, instead of filing a *record* (dossier), a *map of named processors* (wires), and a *book of marks* (gazette). The costume is already better than Vanta. The architecture is still a landing page.

---

## 1. What the live site actually is

Honest, harsh.

It is a single-column marketing-adjacent homepage for a JSON directory of Cloud 100 and enterprise trust URLs. A GRC person can search a name, skim a two-line scrape summary, open a 420px slide-over, and click out through a human checkbox. That is the whole product.

What a stranger sees, in order:

1. A 32px Newsreader wordmark, a 28px flame ring that says `OT`, and a magazine kicker (`register` / `Cloud 100 + enterprise`).
2. A 24px lede and a muted deck. This is a hero. Registers do not have heroes.
3. A hairline search strip. This is the one honest object on the page.
4. A 52px census (`found` of `total`, plus `missing` and `vendors`). This is a SaaS dashboard stat, not a clerk’s tally.
5. Two segmented bars: All / Found / Missing, then SafeBase / Vanta / Conveyor / Wolfia / Custom. We are counting portal vendors. We have become a channel.
6. A column of “cards” that are not cards only because the CSS removed the radius. Each row is still a card: name, vendor badge, domain · list, two-line clamp of marketing copy the vendor wrote, cert fragments.
7. A three-column footer (Methodology / Source / Code). Magazine layout. Oxide would caption one figure. Companies House would put this on an About page.
8. A right drawer. Linear / Notion / every AI console. Not a file.
9. A modal that says “Before you leave” and “Verify you are human.” The checkbox is right. The chrome is a dialog.

The page is a 920px `.sheet` centered on a brown field. Law asked for a canvas. What shipped is a column on a wallpaper. The wallpaper is a 32px engineering grid plus fractal grain at **0.28 opacity**. You notice both. Law said: if you notice either, turn it down.

Color on the live CSS is already off-law:

| Token | Law | Live CSS | What it does |
|---|---|---|---|
| `--ground` | `#331400` | `#2a1408` | Muddy espresso. Reads as “warm dark template,” not the swatch. |
| `--ink` | law contradicts itself (`#ffc091` then `#f4ebe0`) | `#f4ebe0` | Cream. Beige by another name. |
| `--mute` | not specified | `#cbb49a` | Manila. The thing we banned. |
| `--flame` | stamp, outbound, found | go, code, host, hover, seal | Too many jobs. Starts to menace. |

The `<title>` on the live homepage is still the banned line:

> opentrust.center — Company security, trust, and GRC pages **in one place**

Twitter description repeats it. Meta description is a pitch to “GRC and security teams — and their agents.” A register’s title is the name of the register. EDGAR does not say “filings in one place.”

`/c/{slug}.html` (the permalinks) are a second, older site. Stripe’s folio still loads **Source Serif 4 + IBM Plex Sans**, a gold `#d4a24a` seal, theme-color `#12110e`, and a `cobalt-quartz-nx3z.here.now` canonical. That is the first look — dark paper + gold foil — sitting on the same domain as the flame homepage. A stranger who search-lands on a company page never sees the new law.

The drawer, when it does open, is: kicker, 32px name, domain, scraped summary (often the vendor’s own marketing, sometimes truncated mid-word), a cert row that is still a chip row without borders, “SafeBase portal,” host, and two actions. There is no founded year, no instrument list, no subprocessors, no factor line, no “not on file” rows. It is a preview card.

Motion: the gate waits 900ms, prints `Checking…`, then `Verified.` That is the only theatre, and it is already too much.

What is *good*, so we do not throw it out:

- Two faces only on the homepage (Newsreader + Plex Mono). Correct.
- Hairline rules, no radius on controls, no glow orb, no glass. Correct.
- Search is a command strip, not a pill. Correct.
- Rows, not a bento. Directionally correct.
- Clerk words in the lede (“Public register… Official URL on file, or not.”). Correct, and then the title tag undoes it.
- Human gate is a stamp box, not Cloudflare cosplay. Correct idea, wrong container (modal).

The site is a skin. The skin is 60% of the way to the metaphor. The information is still “here is a URL we found.”

---

## 2. What still feels like a template

### The one fake thing

**The 52px census.**

`#stat-found` at `clamp(36px, 6vw, 52px)` is the tell. Every AI/SaaS dark landing of the last three years opens with a big number and two side stats. Linear does it. Vercel does it. VoltAgent does it. We did it in clerk type, so it felt earned. It is not. A register prints the count in the mast, in mono, at 11–12px, next to the issue date:

```
issue 18 Aug 2026 PT · 184 on file · 22 not on file · last probed 18 Aug 2026, 3:23 PM PT
```

That one change — kill the hero census — does more than any type tweak. It is the thing a staff engineer would delete.

### Then the rest, in order of damage

1. **A hero above the register.** Lede 24px + deck + rule + census is a magazine opening. Companies House is a heading and a search. EDGAR is a form. We need a one-line finding aid, then the strip, then rows.

2. **Vendor chips as a first-class facet.** SafeBase / Vanta / Conveyor / Wolfia / Custom is a marketplace taxonomy. It trains the visitor to care about the host product. PRD Decision 1 already kills this. The live site still leads with it. The tally line under the census (`SafeBase 40 · Vanta 22 · …`) is the same sin in sentence form.

3. **The drawer.** A fixed right sheet with a dimmed back-scrim is the 2022–2026 SaaS pattern for “we didn’t want to build a page.” The dossier is the product (PRD Decision 3). It must be a URL. `/c/stripe.html` already exists and is the wrong page.

4. **Card-shaped rows.** `.card-name` 20px, `.card-sum` two-line clamp, `.cert-row` wrap, `.badge` in the top-right. That is a card. A register row is a table line: rank or file no., name, domain, disclosure tier, two or three marks, date. One line. No paragraph.

5. **Scraped marketing as body copy.** OpenAI’s summary on file is SafeBase’s sentence (“win enterprise deals”). Notion’s is Wolfia’s. Sierra’s is a subprocessor press note used as a description. A clerk writes two sentences or writes nothing. We currently reprint the vendor.

6. **Three-column footer.** Feature-column energy. Methodology belongs under the register as a 12px mono block, or on its own `/methodology` we do not need yet. Not a marketing triptych.

7. **Visible grain + grid.** `feTurbulence` at 0.28 and a 32px lattice at 7% cream. Volta’s field is *empty*. Ours is decorated. Decoration is the template.

8. **Ground drift and cream ink.** `#2a1408` + `#f4ebe0` + `#cbb49a` is “premium dark with warm paper type.” That is the beige we banned, composited onto brown. Law’s swatch is `#331400`. Body ink must not read as newsprint.

9. **Flame doing too much.** Seal, `go`, `<code>`, drawer host, outbound fill-on-hover, footer links. User already said full-flame headlines menace. A page of flame links is the same feeling at a smaller size. Flame is the stamp and the outbound rule. Everything else is ink or rust.

10. **Company permalinks are the old brand.** Gold seal, Source Serif 4, Plex Sans, `here.now` canonical. The one fake thing *on those pages* is that they are a 2023 “dark luxury AI” one-pager. They must be rebuilt as dossiers or taken down.

11. **Brand specimen contradicts law.** `brand.html` sets the wordmark at 56px and says body ink is `#ffc091` while the homepage paints `#f4ebe0`. Display type on a specimen may be large. Display type on the product may not. Law already capped product display at ~28–32px. Keep that.

12. **`.sheet` as a floating measure.** A 920px centered column with 64px bottom padding is a document. Oxide and VoltAgent go edge-to-edge; the *instrument* has a measure, the *field* does not. Our field should hit the viewport. The register table can be 1080–1200px. The dossier can be 720px. They sit on the same ground.

13. **No docket.** There is nothing to navigate because there is only one surface. The moment we add wires and gazette, the default instinct is a SaaS product menu (`Product`, `Platform`, `Docs`). That is the next template, and we can see it coming.

14. **Banned words still in the HTML head.** `in one place` in `<title>` and Twitter. “directory for GRC and security teams” in description. Law was not applied to metadata.

---

## 3. What the references actually do (steal this, not their paint)

We opened the pages. Several of them are worse than their reputations. Steal the *structure that still works*, not the current marketing layer.

### VoltAgent (voltagent.dev) — field, not page

**Steal**

- The canvas is the window. No sheet, no card, no beige document. Hairlines do all the elevation.
- Code is an object with a caption, not a screenshot in a browser chrome.
- Type is small until it is the one line that matters.
- Dark is a work surface, not a mood.

**Do not steal**

- “The end-to-end AI Agent Engineering Platform.”
- Logo clouds, testimonial carousels, integration marquee, purple/teal product shots.
- A homepage that is a pitch. They became the generic AI SaaS we are trying not to be. The *canvas* is still good. The *page architecture* is now a warning.

### Volta (volta.sh) — command as the product

volta.sh is not the dark canvas (that was a memory of VoltAgent). It is a docs-site with a wordmark, three short claims, and an install block.

**Steal**

- The product is a command you can type. Our equivalent is `/ stripe` in the finder, and `register · wires · gazette` in the mast.
- Three claims, then the instrument. No lede essay.
- Nav is Guide / Reference / GitHub — a docket of documents, not a product suite.

**Do not steal** Lato, Montserrat, the lightning emoji, or the green.

### Oxide (oxide.computer) — instrument chrome

This is the staff-engineer reference. Their CSS tells on them:

- Chrome face: **GT America Mono**, 11px (`text-mono-xs` = 0.6875rem) and 12px (`text-mono-sm` = 0.75rem), tracked ~0.04em, uppercase, for *almost all UI*.
- Reading face: Suisse Intl, used for sentences, not for labels.
- Hero line is one sentence. The rack is `Fig. 1`. The console is `Fig. 2`.
- The console figure is a **table**: Name, CPU, Memory, State, Created. State is a word (`running` / `stopped`). That table *is* the brand.
- Nav is `CLI` `API` `Console` — three instruments. Not `Platform` `Solutions` `Resources`.
- Captions are part of the layout, not an afterthought.

**Steal**

- Mono as the operating system of the UI; serif only for names and findings.
- Every picture is a figure with a number.
- Tables over cards. State as a word. Columns with unit-like headers.
- Product nav as a short list of instruments.
- One sentence, then the object.

**Do not steal**

- Suisse / GT America (we already picked Newsreader + Plex Mono).
- Full-viewport product hero with a 3D rack.
- “Talk to our team” / “Try it now” marketing closer.
- Their green. Their photography.

Oxide’s homepage has grown a feature grid and a CTA. The *console table* and the *Fig. n* habit are the parts that still feel like a machine. We steal those.

### Companies House (gov.uk / find-and-update)

The search page is a heading, a list of what you can get, and a search. The company page (the thing we are actually stealing) is a **dossier**:

- Identifier in the title (company number).
- Status as a word (`Active`, `Dissolved`) — not a pill, not a score.
- A definition list of facts: incorporated, office, type, SIC.
- Filing history as a **table of documents**, newest first: date, description, link.
- Officers as a table. Charges as a table.
- Empty sections still exist. They say there is nothing on file.

**Steal**

- Search is the page.
- The company view is a file of labeled fields and tables, not a summary card.
- Missing is a row that says missing.
- Identifiers are visible (we will use slug + domain; we do not invent a fake company number).
- No hero. No vendor. No rating of the *company* — only what is on the file.

**Do not steal** GOV.UK blue, the crown, or the light-mode gov.uk Design System. We stay on ground.

### Federal Register

We were served the anti-bot wall. The structure we still take from the public journal:

- Volume / number / date as the identity of an issue.
- Documents listed by agency, type, and action.
- A document has a number, a heading, and a body. It does not have a hero.

**Steal** the issue line and the idea that a notice has a number. Our gazette entries get a stable id (`soc-2-type-ii`, `iso-27001`, `gdpr`) and an issue date on the page.

### EDGAR (sec.gov/edgar/search-and-access)

Ugly on purpose. Authoritative because of that.

**Steal**

- Search is a form with precise fields, not a magic bar.
- Latest filings as a **tape**: form type, company, date.
- The filing is the object. The company is reached *through* filings.
- Accession-style identifiers. We can show `file` as `c/stripe` and `att/soc-2-type-ii` in mono.

**Do not steal** the 1998 visual system, the light-blue links, or the wall of advanced options as the first screen. Our finder stays one strip. Advanced filters (tier, geography, kind) are a hairline bar under it.

### The Gazette (thegazette.co.uk)

The live homepage is a disappointment: data-service ads, commemorative editions, surveys. The *notice* is still the thing.

**Steal from the notice, not the homepage**

- A notice has: type (insolvency, deceased estates, company), number, publication date, body.
- The archive is searchable by notice type and date.
- Language is official. “Notice is hereby given…” is too much for us. “On file” / “Filed from…” is enough.
- Place vs search: they have two verbs. We have one verb, *file*, and three instruments that show the file.

**Do not steal** the current marketing homepage, the navy, or the shop.

### Synthesis — the structural moves we actually take

| Move | From | Our version |
|---|---|---|
| Continuous dark field, hairline elevation | VoltAgent canvas | `--ground` to the edges. No `.sheet` card. |
| Command as the object | Volta | Finder strip + docket words. |
| Mono chrome, serif for names | Oxide | Plex Mono 11–13 for UI; Newsreader 17–28 for names/findings. |
| Fig. n on every picture | Oxide | Graph is Fig. 1. Globe is Fig. 2. Stamp is a mark, not a figure. |
| Table as the product | Oxide console, CH, EDGAR | Register is a table. Dossier instruments are a table. Wires have a ranked table *and* a figure. |
| Status as a word | CH, Oxide | `silent` `thin` `on file` `substantial` `complete` — not pills. |
| Missing rows still print | CH | `not on file` in italic Newsreader, rust. |
| Issue line | Gazette, Federal Register | Date + counts in the mast, 11px mono. |
| Notice as the unit | Gazette, EDGAR | Attestation entries; probe events. |
| Search is the page | CH, EDGAR | No hero. Finder under the docket. |

---

## 4. How to take this 10–20× and remain a registrar

The 10–20× is not “more premium.” It is: the visitor can *use* three instruments that feel like they belong on one desk, and none of them could be reskinned into a GRC app.

Internal metaphor (do not print on the site): we are the front pane of glass. The company’s page stays the original. We file what is public.

Public one-sentence (print this):

> Public record of what a company discloses — official pages, marks, years, and named processors.

Not “in one place.” The clerk already has a word for that: **on file**.

### 4.1 Information architecture

Four public surfaces, one register. Names are lowercase docket words.

```
/                      register     find a company; open a dossier
/c/{slug}.html         dossier      the file
/graph.html            wires        named subprocessors
/attestations.html     gazette      book of marks + desk globe
/brand.html            specimen     law, not a landing
/llms.txt              agent brief
/data.json             machine copy of the register
```

Mast on every surface, one line, full width, hairline under:

```
opentrust.center          register    wires    gazette                         OT
```

Active word gets a 1px `--flame` underline, 2px down. No pill, no fill, no icon.

Under the mast, an issue line (Plex Mono 11, `--mute` as defined in §7):

```
issue 18 Aug 2026 PT · 184 on file · 22 not on file · last probed 18 Aug 2026, 3:23 PM PT
```

No other global nav. No `Product`. No `Docs`. `brand` is not in the docket; it is a link in the colophon. GitHub is a colophon link.

URLs stay file-like (`graph.html`, `attestations.html`, `c/stripe.html`). We are a static register, not an app router.

### 4.2 Type scale (specific px)

Two faces. Optical size on Newsreader. No third face, including no Plex Sans.

Product surfaces never exceed 28px. The 32px wordmark on the live site is already loud; drop it.

| Token | Face | Size / line | Tracking | Weight | Use |
|---|---|---|---|---|---|
| `--t-kicker` | Plex Mono | 11 / 14 | 0.12em | 500 | Docket words, issue line labels, `REGISTER` |
| `--t-meta` | Plex Mono | 12 / 16 | 0.02em | 400 | Domains, dates, hosts, factor lines, table headers |
| `--t-row` | Plex Mono | 13 / 18 | 0 | 400 | Table cells that are not names |
| `--t-body` | Newsreader | 16 / 24 | 0 | 400 | Findings, ELI-5, methodology |
| `--t-name` | Newsreader | 17 / 22 | −0.02em | 500 | Register row company name |
| `--t-lede` | Newsreader | 20 / 26 | −0.02em | 400 | One-line finding aid under the mast (optional; prefer none) |
| `--t-title` | Newsreader | 28 / 32 | −0.03em | 500 | Dossier name, gazette entry name, miss title |
| `--t-wordmark` | Newsreader | 20 / 24 | −0.03em | 500 | `opentrust.center` in the mast |
| `--t-stamp` | Newsreader | 12 / 12 | 0 | 600 | `OT` inside the 28px ring |
| `--t-figure` | Plex Mono | 11 / 14 | 0.08em | 400 | `Fig. 1 · Named processors` |

Uppercase is allowed only on 1-line kickers (`ISSUE`, `REGISTER`, `WIRES`, `GAZETTE`) and table headers (`NAME`, `TIER`, `MARKS`, `PROBED`). Never uppercase a company name.

Italic Newsreader is the voice of absence: `not on file`, `silent`, a finding that is a caution.

Do not set any product text at 36–56px. The live 52px census and the 56px brand.html display are both magazine. Specimen page may show the wordmark at 40px *once*, as a sample, labeled `specimen — not product`.

### 4.3 Color use (ink vs flame)

Pukar’s five swatches are the only brand colors. Derived inks are washes of those swatches, not a sixth hue, and not beige.

| Token | Hex | Role |
|---|---|---|
| `--flame` | `#ff6600` | Stamp ring, outbound underline, docket underline, official URL. Rare. |
| `--ember` | `#cc5100` | Hover of a flame object. Secondary stamp. |
| `--rust` | `#993d00` | Rules, kickers, `not on file`, table grid. |
| `--well` | `#662900` | Row hover, figure well, globe land. |
| `--ground` | `#331400` | Page. Always. Revert the live `#2a1408`. |
| `--ink` | `#ffc091` | Body and names. Washed flame. Readable. Not cream. |
| `--mute` | `#e09a60` | Meta, issue line, inactive docket. Ember washed toward ink. |
| `--hair` | `rgba(255, 192, 145, 0.06)` | Grid, if any. |

Rules:

- Page is `--ground` to the edges. `theme-color` is `#331400`.
- Names, findings, ELI-5, dossier titles: `--ink`. Never `--flame`. Flame headlines menace.
- Labels, ranks, dates: `--mute` or `--rust`.
- `--flame` appears on a screen in at most three places: the OT ring, the current docket underline, and one outbound. If you need a fourth, you are decorating.
- Links in running text: `--ink` with a 1px `--rust` underline; hover `--flame`.
- Official outbound: `--flame` text, 1px `--flame` rule under, no fill. Hover may fill `--flame` with `--ground` type. That is the only fill-on-hover.
- No gold. No navy. No mint. No `#f4ebe0`, `#efe6d2`, `#cbb49a`, `#d4a24a`. Those are the last two looks.
- No gradient. No glow. No blur.

Grain: drop it, or cap at **0.06** opacity. Grid: 32px, `--hair` only, and only on empty field (behind the globe well or the graph well). Not over tables. If a screenshot makes the grid obvious, delete the grid.

### 4.4 Company folio as a filed dossier

Kill the drawer. `/c/{slug}.html` *is* the folio. Opening a register row goes there (same tab). A `?c=` peek is a fallback for agents, not the design.

The page is a file, modeled on a Companies House record plus an EDGAR header, not on a SaaS customer drawer.

**Measure:** 720px column, left-aligned inside a 1200px canvas with 48px side gutters. Stamp sits in the right margin on viewports ≥1100px (200px wide), or stacks under the title on small screens.

**Order of the file** (always this order; empty sections still print):

1. **Docket crumb** — `register / {slug}` in `--t-kicker`.
2. **Identity** — name at 28px Newsreader `--ink`. Domain and list in `--t-meta`. Founded year + source URL, or `founded · not on file`.
3. **Disclosure stamp** — the OT ring, the tier word (`silent` / `thin` / `on file` / `substantial` / `complete`) in Newsreader italic or Plex Mono 12, and a factor line in `--t-meta`:

   ```
   page 20 · marks 18 · dpa 0 · processors 8 · status 0 · bounty 6 · privacy 6 · years 4   = 62  on file
   ```

   A score without this line is a lie. Never letter-grade. Never “trust score.”

4. **Attestations** — a table, not chips.

   | mark | kind | geography | on page |
   |---|---|---|---|
   | SOC 2 Type II | attestation | US | cited |
   | ISO 27001 | certification | international | cited |

   Mark links to `/attestations.html#{id}`. If none: one row, `not on file`.

5. **Instruments** — a table of public links we actually have.

   | instrument | host | last seen |
   |---|---|---|
   | trust | trust.stripe.com | 18 Aug 2026 |
   | security | stripe.com | 18 Aug 2026 |
   | privacy | not on file | — |
   | dpa | not on file | — |
   | subprocessors | stripe.com | 18 Aug 2026 |
   | status | not on file | — |
   | bounty / security.txt | stripe.com | 18 Aug 2026 |

   Always print all seven rows. Absence is information.

6. **Named processors** — a table of names + source URL, each name linking to wires focused on that node (and to a dossier if the processor is in the register). Caption: `Filed from the company’s public list. Not a complete supply chain.`

7. **Clerk summary** — two sentences, Newsreader 16. No vendor. No marketing. If we cannot write two true sentences, print nothing.

8. **Probe** — `last probed {datetime PT}` in mono 12.

9. **Actions** — `open official page` (flame, human-gated) and the permalink, which *is this page*.

Human gate: not a modal. An inline stamp box that appears under the outbound the first time, in the dossier column. Checkbox + `I am human`. On pass, the same box reads `verified · 30 min` and the outbound proceeds. No `Before you leave`. No 900ms fake check. A 200–300ms pause is enough so a bot cannot flip it in one tick.

### 4.5 Graph as a wire instrument

This is a filing of edges, not a “network visualization.”

**Layout (desktop):** 1200px canvas. Left 420px: ranked table. Right: the figure. Caption above the figure, Oxide-style:

```
Fig. 1 · Named processors, as published
Filed from public subprocessor lists. This is not a complete supply chain.
```

**Table columns:** processor · exposure (how many register companies name them) · their tier (or `not in register`) · risk (the PRD formula) · source.

Sort by risk. Risk is `exposure × (0.4 + 0.6 × thinness)`. Print the formula in 11px under the table. Do not color rows red.

**The figure**

- 2D. Hairline rust edges. Nodes are 5–7px squares or short ticks, not orbs, not avatars, not logos.
- In-register nodes: `--ink` fill, 1px `--rust` stroke.
- Processor-only stubs: empty square, `--rust` stroke.
- Selected: `--flame` stroke, 1px. No halo.
- Edges: 1px `--rust` at 50–70% opacity. No arrows, or a 3px rust tick for direction `company → processor`.
- Labels: Plex Mono 11, `--ink` for selected, `--mute` otherwise. Hide labels under a density threshold; the table remains the authority.
- Hover on a table row highlights the node and its edges. Hover on a node highlights the table row. No tooltips in glass.
- Background of the figure well: `--ground`. Optional 32px grid at `--hair`. No vignette, no fog, no force-directed party.

**How to avoid the generic graph**

- No dark-navy canvas with neon edges (the “supply-chain risk” look every GRC vendor ships).
- No bloom, no particles, no animated dashes.
- No 3D tilt.
- No community-coloring (modularity palettes). One ink, one rust, one flame.
- If a library defaults to bezier “hair” and node glow (e.g. typical sigma/cytoscape demos), turn those off in the first commit or do not use the library.
- Prefer a static SVG of the current focus plus a table, over a physics sim. A force layout is allowed only if it settles and then *stops*. No idle motion.

Click a register node → dossier. Click a stub → a short stub file on the same page (who named them, source URLs), not a fake dossier.

### 4.6 Globe as a desk cartographic object

The gazette is a list. The globe is a **control** and a **figure**, not a hero. If we shipped the list without the globe, the product would still be true. The globe is how a clerk points at a region.

**Layout:** gazette is 1200px. Left 360px: the figure. Right: the book (filters + entries). On small screens the globe stacks above, 280px tall, and is allowed to become a flat region list if WebGL is a fool’s errand.

Caption:

```
Fig. 2 · Geography of marks
Drag. Click a region to filter the book. This is not a threat map.
```

**How to look like a desk globe, not a Three.js product-hunt bauble**

Do these:

- Sphere sits in a square well (`--ground`, 1px `--rust`). Size 280–360px. It looks like an object on the desk, not Earth from orbit.
- Land: `--well` (`#662900`). Sea: `--ground` (`#331400`). Graticule: `--rust` hairlines, 15° or 30°, like engraved meridians. Coastlines: 1px `--rust` or `--ember`, no fill gradient.
- Marks: 2–3px `--flame` ticks (or 4px for a family with many entries). No pulses. No ping rings. No hover-scale bounce.
- Rotation: **user drag only**. Default is still. If you must idle, one revolution per 4 minutes, and it stops on interaction. `autoRotate: true` at demo speed is banned.
- Projection: orthographic, or a very slight perspective (focal length long). A desk globe is a ball in a room, not a planet in a void.
- Lighting: flat / unlit / MeshBasic, or a single dim Lambert with no specular. No envmap. No reflections. No city lights. No night texture. No clouds. No atmosphere.
- Click region → filters the book to that geography. Click a tick → opens that family in the book (`#id`, ELI-5). The list is the authority; the globe is the pointer.
- A mono legend beside the well: `americas · europe · uk · apac · international · industry`. These are our geographies, not UN regions we cannot defend.

Do not do these (this is the generic Three.js glow globe):

- `EffectComposer` + UnrealBloom, or any bloom.
- Fresnel / atmosphere rim (the blue halo everyone copies from threejs-earth examples).
- Starfield, nebula, or any scene background other than `--ground`.
- `earth-night.jpg`, satellite imagery, or NASA Blue Marble. We are not a space company.
- Fog, SSAO, camera dolly-in from space, whoosh on load.
- Auto-rotate as the first impression.
- Pulsing `Sprite` markers, HTML/CSS glass tooltips over the canvas.
- A 3D wooden stand, brass meridian, or any skeuomorphic furniture. The *page* is the desk. A stand is a souvenir shop.
- Full-bleed WebGL behind the mast. If the globe is the first thing you see, it is a hero. It is not allowed to be a hero.

Implementation preference, in order:

1. **Best:** a small canvas 2D (or SVG) orthographic globe, geojson land, our own two-color paint. No Three.js.
2. **Acceptable:** Three.js with `MeshBasicMaterial`, custom 2-color texture, `OrbitControls` with `enableZoom: false`, no composer, no lights, contained in the 360px well.
3. **Forbidden:** any demo that began as “threejs earth glow” on GitHub.

If WebGL is a risk for the first ship, ship Fig. 2 as a **printed map**: equirectangular, rust land, ground sea, rust graticule, flame ticks, same caption. That is more clerk than a bad globe.

### 4.7 Nav as a docket, not a SaaS product menu

The mast is a filing stamp, not a product bar.

```
[opentrust.center]     register    wires    gazette                      (OT)
```

Rules:

- Three words. Always these three. Never add `Platform`, `Docs`, `Blog`, `Login`, `Pricing`.
- Lowercase. Plex Mono 11, tracking 0.12em.
- Current page: `--ink` + 1px `--flame` underline. Others: `--mute`. Hover: `--ink`.
- Wordmark is the home of the register. It is not a logo lockup with a mark to its left (the live site’s mark-on-the-right is fine; keep the ring on the right, 28px, `--flame` on `--ground`).
- No icons. No hamburger on desktop. On <800px the three words wrap onto a second line; they do not collapse into a burger if they still fit.
- No hover megamenu. No “product” dropdown that reveals the three instruments — they *are* the nav.
- Issue line sits directly under the hairline, full measure, not in a utility corner like an app.

If we ever need a fourth public surface, it earns a fourth docket word or it does not ship. It does not go in a `More` menu.

---

## 5. Revised hard no’s

Keep every no from the current law. Add the ones this pass proved.

**Color**

- Beige, cream, newsprint, manila, `#f4ebe0`, `#efe6d2`, `#cbb49a`, `#e8dcc8`
- Gold / foil / `#d4a24a` (still live on `/c/*`)
- Ground any color other than `#331400` (the live `#2a1408` is a no)
- Navy, mint, purple, teal, VoltAgent green, Vanta mint
- Gradient, glow, blur, glass, mesh blob, orb
- Flame as a headline color or as the color of every company name

**Type**

- Inter, Geist, Recoleta, Source Serif 4, IBM Plex Sans, Suisse, GT America, Lato, Montserrat
- Product type ≥ 36px (52px census, 56px specimen-as-product)
- 8pt tracking as a style
- A third face “just for the app”

**Layout / chrome**

- Hero + lede + deck above the register
- Dashboard census (big number + two side stats)
- Vendor chips, vendor tallies, “powered by”
- Slide-over drawer as the dossier
- Rounded-xl card grids, badge pills, 2-line clamp cards
- Three-column marketing footer
- Three feature columns with line icons
- Bento, pricing chrome, platform nav, blog theme
- Visible grain (opacity > 0.08) or a grid you can see in a screenshot
- Modal as the default container (gate is inline)

**Product language**

- empower, seamless, reimagine, next-gen, **in one place**, trust made simple, the future of GRC, unlock, delightful
- trust score, security rating, letter grade (A–F)
- powered by, front pane of glass (internal only), directory for GRC teams (meta)
- OpenTrust, OPEN TRUST, any camel-case of the wordmark

**Pictures**

- Stock locks, shields, checkmarks
- Generated hero illustrations
- Three.js glow globe (bloom, atmosphere, starfield, Blue Marble, auto-rotate demo)
- Neon force-graph (bloom edges, avatars, idle physics)
- Logo clouds, testimonial rails, integration marquees

**If it could sell a debit card, a GRC seat, or an AI agent platform, it is wrong.**

---

## 6. Recommended UI inventory

Build only these. If a screen is not on this list, it is not this issue.

| Surface | URL | Objects on it |
|---|---|---|
| Register | `/` | Docket mast, issue line, finder strip, tier filter (silent/thin/on file/substantial/complete — words, not chips of vendors), register **table**, miss block, colophon |
| Dossier | `/c/{slug}.html` | Crumb, identity, disclosure stamp + factor line, attestations table, instruments table, processors table, clerk summary, probe line, inline human stamp, outbound |
| Processor stub | on `/graph.html` or `/c/{slug}` if later | Who named them, source URLs, `not in register` |
| Wires | `/graph.html` | Docket, issue line, one-line finding aid (`Named subprocessors, as published.`), Fig. 1, ranked table, focus stub |
| Gazette | `/attestations.html` | Docket, issue line, finding aid (`Marks a buyer will meet.`), kind/geography/industry hairline filters, Fig. 2 globe or printed map, book of entries |
| Gazette entry | `/attestations.html#{id}` | Name, kind, geography, industry, issuer, weight, ELI-5, elaborate (toggle, not a modal), related marks, companies in the register that cite it |
| Miss | on `/` | `Not in the index.` + unconfirmed guess paths in mono. No live AI search this issue. |
| Human stamp | inline on dossier (and any later outbound) | Checkbox, `I am human`, `verified · 30 min` |
| Specimen | `/brand.html` | Law, scale, mark, one folio sample, type specimens at the *product* sizes. Label large type as specimen. |
| Agent brief | `/llms.txt` | Cite the dossier; do not invent URLs; tier is not a security rating; do not name portal vendors |
| Machine register | `/data.json` | Public fields only; vendor in `_crawl` or omitted |
| Colophon | foot of each surface, one column | Methodology in 12px, source, code link, last probed. Not a 3-col grid. |

Explicitly **not** in inventory: blog, changelog UI, pricing, login, settings, “platform,” comparison pages, vendor pages, a marketing homepage sitting above the register.

---

## 7. Tokens, type, and layout a frontend can implement without guessing

### 7.1 CSS variables (paste)

```css
:root {
  --flame: #ff6600;
  --ember: #cc5100;
  --rust: #993d00;
  --well: #662900;
  --ground: #331400;
  --ink: #ffc091;
  --mute: #e09a60;
  --hair: rgba(255, 192, 145, 0.06);

  --font-register: "Newsreader", "Times New Roman", serif;
  --font-docket: "IBM Plex Mono", ui-monospace, monospace;

  --t-kicker: 500 11px/14px var(--font-docket);
  --t-meta: 400 12px/16px var(--font-docket);
  --t-row: 400 13px/18px var(--font-docket);
  --t-body: 400 16px/24px var(--font-register);
  --t-name: 500 17px/22px var(--font-register);
  --t-lede: 400 20px/26px var(--font-register);
  --t-title: 500 28px/32px var(--font-register);
  --t-wordmark: 500 20px/24px var(--font-register);

  --gutter: 48px;
  --gutter-s: 24px;
  --canvas: 1200px;
  --dossier: 720px;
  --rhythm: 8px;
  --rule: 1px solid var(--rust);
  --stamp: 28px;
}
```

Google fonts query (unchanged faces, include italic for absence):

```
IBM+Plex+Mono:ital,wght@0,400;0,500;1,400
Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400
```

### 7.2 Layout

- `html, body`: `background: var(--ground)`; no `.sheet` wrapper as a card.
- Mast: `height: 48px`; `padding: 0 var(--gutter)`; `border-bottom: var(--rule)`; wordmark left; docket centered or 24px right of wordmark; stamp right. Max width none — full viewport.
- Issue line: `padding: 8px var(--gutter) 0`; `--t-kicker`; `--mute`.
- Register / wires / gazette content: `width: min(var(--canvas), calc(100% - 2*var(--gutter)))`; `margin: 0 auto`; `padding: 24px 0 80px`.
- Dossier content: `width: min(var(--dossier), calc(100% - 2*var(--gutter)))`.
- Radius: `0` everywhere except the stamp (`50%`).
- Shadow: `none`.
- Focus: `outline: 1px solid var(--flame); outline-offset: 2px`.

### 7.3 Finder

```
[  / company, domain, mark                                         ][ go ]
```

- Height 40px. `border: var(--rule)`. Background `rgba(51, 20, 0, 0.4)` (ground at 40%, not a new color).
- Input: `--font-docket` 13px, `--ink`, placeholder `--rust` (`/ stripe, microsoft, soc 2`).
- `go`: 12px kicker, `--flame`, 1px rust left rule, hover `--well`.
- No pill, no shadow, no magnifying-glass icon.

### 7.4 Register table

One table. Not articles. Header row `--t-kicker` `--rust`. Body `--t-name` on the name cell, `--t-row` elsewhere.

| # | name | domain | tier | marks | probed |
|---|---|---|---|---|---|
| 003 | Stripe | stripe.com | substantial | SOC 2 · PCI DSS | 18 Aug 2026 |

- Row height ~44px. `border-bottom: var(--rule)`.
- Hover: `background: var(--well)`. Cursor pointer. Whole row is the hit target to `/c/{slug}.html`.
- Tier is a word in `--t-meta`. `silent` and `not on file` are italic Newsreader `--rust`. Others `--ink`.
- Marks: first three, ` · ` separated, `--t-meta`. Overflow `+2`.
- No vendor column. No summary paragraph. No badge.
- Filters: one hairline segmented bar of **tiers**, same construction as today’s chip-row but fed by tiers. A second bar for **list** (Cloud 100 / enterprise) is allowed. Vendor bar is deleted.

Countline under the finder, `--t-meta` `--mute`:

```
showing 184 of 206 · tier substantial · list all
```

### 7.5 Disclosure stamp (object)

- 28px double-ring circle, `--flame` on `--ground`, `OT` at 12px Newsreader 600. Slight irregularity allowed (dry pad). No shadow, no metal, no wax.
- Tier word to the right of the ring, `--t-meta` or Newsreader 16 italic.
- Factor line under, full measure, `--t-meta` `--mute`.
- Never a squircle app icon. Never a shield.

### 7.6 Gazette entry (object)

Default shows ELI-5 (Newsreader 16). A text control `elaborate` / `eli-5` toggles depth. Not an accordion animation; instant swap.

Header of an entry:

```
SOC 2 Type II
attestation · US · AICPA · weight 10
```

Related marks are a mono line of links. Companies that cite it are a table (name · tier), not avatars.

### 7.7 Motion

- Instant. No fade-slide, no page transition, no number count-up.
- Globe: drag only (see §4.6).
- Wires: no idle physics.
- Gate: ≤300ms.
- Wait states: a mono line, `checking…` / `filing…`.

### 7.8 Copy deck (clerk, ready to paste)

| Slot | Use this | Not this |
|---|---|---|
| `<title>` | `opentrust.center — public record of company disclosures` | `…in one place` |
| meta | `Official pages, attestations, years, and named processors. On file, or not.` | `A directory for GRC and security teams…` |
| Register aid | `Public record of what a company discloses.` | `Find every trust center in one place.` |
| Register deck | `Attestations, instruments, years. Official page, or not.` | `Cloud 100 and the public vendors people actually type.` |
| Wires aid | `Named subprocessors, as published.` | `Map your vendor risk in one place.` |
| Gazette aid | `Marks a buyer will meet.` | `The complete compliance encyclopedia.` |
| Outbound | `open official page` | `Open official trust center` / `Open SafeBase` |
| Miss | `Not in the index.` | `We couldn’t find a match.` |
| Absence | `not on file` | `N/A`, `—` as a cute dash with no label, `Unknown` |
| Tier | `silent` `thin` `on file` `substantial` `complete` | `A+`, `82/100`, `High trust` |

Wordmark is always `opentrust.center`, lowercase, no tracking-out, never `OpenTrust`.

### 7.9 Metadata and old pages

- Rebuild every `/c/{slug}.html` against this law in the same issue as the homepage. Do not leave Source Serif / gold / `here.now` live.
- `theme-color`: `#331400`.
- Favicon: ground square, flame ring, `OT` in a serif. No gold.
- JSON-LD: WebSite on `/`; WebPage about Organization on each dossier; `hasCredential` only when a mark is on file.
- `llms.txt`: cite the dossier; do not invent URLs; do not treat the tier as a security rating; do not name portal vendors.

### 7.10 Acceptance (visual)

A stranger can tell this from Linear, Vanta, VoltAgent’s marketing page, and the 2023 dark-gold AI template, without reading the about text.

Concrete checks:

1. Screenshot `/` at 1440px: no number larger than 28px; no vendor word; rows are one line; mast is three docket words.
2. `/c/stripe.html` is a file with empty rows printed as `not on file`. No drawer. No SafeBase. No gold. No Source Serif.
3. `/graph.html` has a table you can use with the figure hidden. Fig. 1 caption is visible. No neon.
4. `/attestations.html` globe (or printed map) sits in a rust well ≤360px. No bloom, no stars, no auto-spin on load. Drag filters the book.
5. View-source title has no `in one place`.
6. `--ground` computed style is `#331400`. `--ink` is `#ffc091`. `#f4ebe0` and `#2a1408` do not appear.

---

## Appendix — law vs live (so the next agent does not re-litigate)

| Law said | Live did |
|---|---|
| Canvas, not a sheet | `.sheet` 920px |
| Display ~28–32 | Census 52, brand.html 56, drawer h2 32 |
| Flame rare | Flame on go, code, host, links, seal |
| `--ground` `#331400` | `#2a1408` |
| Ink washed flame | Cream `#f4ebe0` + beige mute |
| Grain/grid unnoticeable | Grain 0.28 |
| Register is rows | Rows are cards with summaries |
| Folio is a side panel on the same canvas | SaaS drawer + stale gold permalinks |
| No marketing homepage above the register | Hero + census + vendor chips |
| Banned: `in one place` | In `<title>` and Twitter |
| Hide the portal vendor (PRD) | First-class facet |
| Dossier is the product (PRD) | Drawer preview |

The next visual pass should implement this file and `BRAND.md.new`. Do not “freshen.” If a new color or face is tempting, change the law first and say why the registrar metaphor broke.
