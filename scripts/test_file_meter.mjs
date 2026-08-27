import { readFileSync } from "node:fs";
import { FILE_KEYS, fileCount, fileCoverage, fileFlags, fileIndexHtml, fileScore } from "../site/lib.js";
import { marksCell, registerRowHtml } from "../site/register.js";

const data = JSON.parse(readFileSync(new URL("../site/data.json", import.meta.url), "utf8"));
const bySlug = Object.fromEntries(data.companies.map((r) => [r.slug, r]));

function ruleOn(html) {
  return [...html.matchAll(/class="file-rule(?: (on|partial))?"/g)].map((m) => m[1] === "on");
}

function ruleKind(html) {
  return [...html.matchAll(/class="file-rule(?: (on|partial))?"/g)].map((m) => m[1] || "");
}

function expect(name, cond) {
  if (!cond) {
    console.error("fail", name);
    process.exitCode = 1;
  } else {
    console.log("ok", name);
  }
}

expect("five keys", FILE_KEYS.length === 5);
expect(
  "keys stay page marks dpa subprocessors years",
  FILE_KEYS.join(" ") === "page marks dpa subprocessors years",
);

const empty = fileIndexHtml({});
expect("empty draws five rules", (empty.match(/file-rule/g) || []).length === 5);
expect("empty has no filled rule", !empty.includes("file-rule on"));
expect("empty does not print N of 5", !empty.includes(" of 5") && !empty.includes("0 of 5"));
expect("empty is not a star", !empty.includes("star") && !empty.includes("★") && !empty.includes("☆"));
expect("empty spoken is inconclusive", fileCoverage({}).spoken === "not on file");

const fullRow = {
  found: true,
  trust_url: "https://trust.example",
  attestations: [{ name: "SOC 2" }],
  instruments: { dpa: { url: "https://example/dpa" }, subprocessors: { url: "https://example/subs" } },
  processors: [{ name: "Acme" }],
  founded_year: 2012,
};
const full = fileIndexHtml(fullRow);
expect("full fills five rules", (full.match(/file-rule on/g) || []).length === 5);
expect("full does not print N of 5", !full.includes(" of 5") && !full.includes("5 of 5"));
expect("full is not a sixth score", !full.includes("trust maturity") && !full.includes("file · 5"));
expect("full spoken is the instruments", fileCoverage(fullRow).spoken === "page · standards · DPA · subprocessors · years");

const mixedRow = {
  found: true,
  trust_url: "https://trust.example",
  instruments: { dpa: { url: "https://example/dpa" } },
  founded_year: 2010,
};
const mixed = fileCoverage(mixedRow);
const mixedHtml = fileIndexHtml(mixedRow);
expect("mixed counts four", mixed.n === 4 && fileCount(mixedRow) === 4);
expect("mixed does not print the count", !mixedHtml.includes("3 of 5") && !mixedHtml.includes("file · 3"));
expect("mixed speaks instruments on file", mixed.spoken === "page · standards · DPA · years");
expect("mixed fills three prints", (mixedHtml.match(/file-rule on/g) || []).length === 3);
expect("mixed marks is dotted 10", ruleKind(mixedHtml)[1] === "partial" && fileFlags(mixedRow).marks === 10);
expect("mixed binds DPA not a filled marks rule", ruleOn(mixedHtml)[2] === true && ruleOn(mixedHtml)[1] === false);

const staleFilled = {
  found: true,
  trust_url: "https://trust.8x8.com",
  file: { page: true, marks: true, dpa: false, subprocessors: false, years: false },
  disclosure: { factors: { page: 20, marks: 40 } },
  certs: [],
  attestations: [],
};
expect("stale factors.marks do not print marks", fileFlags(staleFilled).marks === 10 && ruleKind(fileIndexHtml(staleFilled))[1] === "partial");
expect("stale file.marks do not fill marks", fileFlags(staleFilled).page === 20 && ruleOn(fileIndexHtml(staleFilled))[0] === true);

const staleEmpty = {
  found: true,
  trust_url: "https://trust.abridge.com",
  file: { page: false, marks: false, dpa: false, subprocessors: false, years: false },
  disclosure: { factors: { marks: 0 } },
  attestations: [{ name: "SOC 2 Type II" }, { name: "HIPAA" }],
};
expect("named marks fill even if file.marks is false", fileFlags(staleEmpty).marks === 20 && ruleOn(fileIndexHtml(staleEmpty))[1] === true);

const eight = bySlug["8x8"];
const eightHtml = fileIndexHtml(eight);
const eightMarks = marksCell(eight);
expect("8x8 page is on file", eight.found && eight.trust_url && fileFlags(eight).page === 20);
expect("8x8 Marks cell lists csa star", /csa star/.test(eightMarks));
expect("8x8 marks rule is filled", fileFlags(eight).marks === 20 && ruleOn(eightHtml)[1] === true);
expect("8x8 subprocessors URL-only is 10", fileFlags(eight).subprocessors === 10 && ruleKind(eightHtml)[3] === "partial");

const abridge = bySlug.abridge;
const abridgeHtml = fileIndexHtml(abridge);
const abridgeMarks = marksCell(abridge);
expect("Abridge Marks cell lists names", /soc 2/.test(abridgeMarks) && abridgeMarks.includes("hipaa") && abridgeMarks.includes("ccpa") && abridgeMarks.includes("tx-ramp"));
expect("Abridge marks rule is filled", fileFlags(abridge).marks === 20 && ruleOn(abridgeHtml)[1] === true);
expect("Abridge is not five open hairlines", ruleOn(abridgeHtml).some(Boolean));
expect("Abridge page stays filled", fileFlags(abridge).page === 20 && ruleOn(abridgeHtml)[0] === true);

const src = readFileSync(new URL("../site/register.js", import.meta.url), "utf8");
expect("register draws the file index", src.includes("fileIndexHtml"));
expect("register has no N of 5 markup", !src.includes("file-cov") && !src.includes("file-meter") && !src.includes(" of 5"));
expect("register does not print tier words in the cell", !src.includes("displayFileState") && !src.includes("tierClass"));
expect("register has no stars", !src.includes("★") && !src.includes("☆") && !src.includes("star-rating") && !src.includes("trust maturity"));
expect("register does not restyle the dossier stamp", !src.includes("disclosure"));
expect("register has no More on this file", !src.includes("More on this file") && !src.includes("record-extra"));

const indexHtml = readFileSync(new URL("../site/index.html", import.meta.url), "utf8");
const companiesHtml = readFileSync(new URL("../site/companies.html", import.meta.url), "utf8");
function registerFileCell(html) {
  const m = String(html || "").match(/<td class="file">([\s\S]*?)<\/td>/);
  return m ? m[1] : "";
}

expect(
  "legend is once above the grid",
  indexHtml.includes('id="file-legend"') && indexHtml.includes("page · standards · processors · evals · incidents"),
);
expect(
  "register legend is the five Companies rules",
  companiesHtml.includes('id="file-legend"') && companiesHtml.includes("page · standards · DPA · subprocessors · years"),
);
expect(
  "register method line is once under the legend",
  /id="file-legend">page · standards · DPA · subprocessors · years<\/p>\s*<p class="file-method" id="file-method">20 printed · 10 on file, not extracted · 0 missing\. 100 is five prints\.<\/p>/.test(companiesHtml) &&
    (companiesHtml.match(/<p class="file-method" id="file-method">20 printed · 10 on file, not extracted · 0 missing\. 100 is five prints\.<\/p>/g) || []).length === 1,
);
expect(
  "register method line has no strike markup",
  !/<(?:s|del|strike|i)[\s>/]/.test(((companiesHtml.match(/<p class="file-method"[^>]*>([\s\S]*?)<\/p>/) || [])[1] || "")),
);

const onePass = bySlug["1password"];
const onePassCell = registerFileCell(registerRowHtml(onePass));
expect("1Password count is five", fileCount(onePass) === 5 && fileScore(fileFlags(onePass)) === 100);
expect(
  "1Password File prints 100",
  /<span class="file-num">100<\/span>/.test(onePassCell) &&
    /file-num[\s\S]*file-index[\s\S]*file-rule/.test(onePassCell) &&
    !onePassCell.includes("100/100") &&
    !onePassCell.includes("100%") &&
    !/\d+ on file/.test(onePassCell),
);

const twoFilled = {
  slug: "two-filled",
  name: "Two",
  domain: "two.example",
  instruments: { dpa: { url: "https://two.example/dpa" } },
  founded_year: 2014,
};
const twoCell = registerFileCell(registerRowHtml(twoFilled));
expect("two-filled count is two", fileCount(twoFilled) === 2 && fileScore(fileFlags(twoFilled)) === 40);
expect(
  "two-filled File prints 40",
  /<span class="file-num">40<\/span>/.test(twoCell) &&
    !/<span class="file-num">2<\/span>/.test(twoCell) &&
    !twoCell.includes("40/100") &&
    !twoCell.includes("40%"),
);

const silentCell = registerFileCell(registerRowHtml({ slug: "silent", name: "Silent", domain: "silent.example" }));
expect("silent File prints 0", /<span class="file-num">0<\/span>/.test(silentCell) && fileCount({}) === 0);

expect("register has no Score header", !/>\s*Score\s*</i.test(companiesHtml) && (companiesHtml.match(/<th /g) || []).length === 4);
expect("register Completeness header stays Completeness", /<button type="button">Completeness<\/button>/.test(companiesHtml));
expect(
  "finder placeholder dropped old tier words",
  companiesHtml.includes('placeholder="/ stripe, on file, fedramp moderate"') &&
    !/placeholder="[^"]*\b(silent|thin|substantial|complete)\b/.test(companiesHtml),
);
expect("legend is not a tooltip farm", !src.includes("title=") || !/file-rule[^>]*title=/.test(src));

const dossier = readFileSync(new URL("../site/c/anysphere.html", import.meta.url), "utf8");
expect("dossier names Cursor in the h1", /<h1>(?:<img class="ink-ico"[^>]*>)?Cursor<\/h1>/.test(dossier));
expect(
  "dossier file is five rules",
  dossier.includes("file-index") && dossier.includes("file-rule on") && !dossier.includes("file-word") && !dossier.includes("file-state") && !dossier.includes("tier-label") && !dossier.includes('class="disclosure"'),
);
expect("dossier has no stars", !dossier.includes("star") && !dossier.includes("★") && !dossier.includes("☆"));
expect("dossier has no trust maturity index", !dossier.includes("trust maturity") && !dossier.includes(" of 5"));
expect("dossier has no rating disclaimer", !dossier.includes("File rating, not a company trust badge") && !dossier.includes("not a company trust badge"));
expect("dossier has no coverage ratio", !dossier.includes(" of 5") && !dossier.includes("public evidence located"));
const issueLine = (dossier.match(/<p class="issue">([^<]+)/) || [])[1] || "";
expect("dossier issue has no register census", !issueLine.includes(" on file · ") && !issueLine.includes(" not on file · last probed"));
expect("dossier marks are a list", dossier.includes('class="mark-list"') && !dossier.includes("mark-chip") && !dossier.includes("+N"));
expect("dossier clerk mark words are links", /<p class="clerk">[\s\S]*<a href="\.\.\/attestations.html#soc-2-type-ii">SOC 2 Type II<\/a>[\s\S]*<a href="\.\.\/attestations.html#aiuc-1">AIUC-1<\/a>/.test(dossier));
expect("dossier clerk has no mark icons", !/<p class="clerk">[\s\S]*<(img|svg)/.test(dossier));
expect("dossier outbound is Official page", dossier.includes('class="official"') && dossier.includes("Official page") && !dossier.includes("View source") && !dossier.includes("go-out") && !dossier.includes("file-go"));
expect("dossier nav does not current Register", !dossier.includes('class="on"'));
expect("dossier body is dossier", dossier.includes('class="dossier"'));
expect("dossier empty rows stay italic not on file", dossier.includes('class="absent">not on file'));
expect("dossier FedRAMP cites marketplace, not a badge", dossier.includes("Filed from the") && dossier.includes("FedRAMP Marketplace") && !dossier.includes("Not a badge") && !dossier.includes("not a badge") && !dossier.includes("not a score") && !dossier.includes("Not a score"));
expect("anysphere FedRAMP is the Cursor marketplace row", dossier.includes("FR2631054484") && /<a href="https:\/\/www\.fedramp\.gov\/marketplace\/products\/FR2631054484\/?"[^>]*target="_blank"[^>]*>Cursor<\/a>/.test(dossier) && dossier.includes("not yet certified") && dossier.includes("initial implementation") && dossier.includes("authorizations 0"));
expect("anysphere FedRAMP does not borrow Box words", !dossier.includes("authorized") && !dossier.includes(">High<") && !dossier.includes("25 Mar 2025") && !dossier.includes("Box Enterprise"));
expect("anysphere FedRAMP is not four invented misses", !/<tr><td[^>]*>[\s\S]*not on file[\s\S]*not on file[\s\S]*not on file[\s\S]*not on file/.test(dossier.split('sec-kicker">FedRAMP')[1].split("Named processors")[0]));
const cursorNames = [
  "Amazon Web Services", "Fireworks", "OpenAI", "Anthropic", "Google Gemini",
  "Turbopuffer", "Exa", "Datadog", "Databricks", "Vercel", "Azure", "Baseten",
  "Cloudflare", "Google Cloud Platform", "Together", "SpaceXAI", "WorkOS",
];
const procChunk = dossier.split("Named processors")[1] || "";
const procCells = [...procChunk.matchAll(/<tr><td>(.*?)<\/td><\/tr>/g)].map((m) => m[1]);
const procNames = procCells.map((cell) => cell.replace(/<[^>]+>/g, ""));
expect(
  "anysphere processors are the published list",
  cursorNames.every((n) => procChunk.includes(n)) &&
    procNames.length === cursorNames.length &&
    procNames.join() === [...procNames].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" })).join(),
);
const dossierHref = {
  "Amazon Web Services": "./amazon-web-services.html",
  Fireworks: "./fireworks-ai.html",
  OpenAI: "./openai.html",
  Anthropic: "./anthropic.html",
  Datadog: "./datadog.html",
  Databricks: "./databricks.html",
  Vercel: "./vercel.html",
  Cloudflare: "./cloudflare.html",
  Together: "./together-ai.html",
  Azure: "./microsoft.html",
  Baseten: "./baseten.html",
  "Google Cloud Platform": "./google.html",
  "Google Gemini": "./google.html",
  Exa: "./exa.html",
  WorkOS: "./workos.html",
  Turbopuffer: "./turbopuffer.html",
};
const graphHref = {
  SpaceXAI: "../graph.html#p=spacexai",
};
expect(
  "anysphere processors that have a file are links",
  procCells.every((cell, i) => {
    const name = procNames[i];
    const want = dossierHref[name] || graphHref[name];
    return want && cell.includes(`href="${want}"`) && cell.includes(name);
  }),
);
expect("anysphere processors cite the list", /Filed from[\s\S]*trust\.cursor\.com\/subprocessors/.test(procChunk) && !procChunk.includes("names not extracted") && !/<span class="absent">not on file/.test(procChunk.split("<p class=\"clerk\">")[0]));
expect("anysphere processors are not Box names", !procChunk.includes("GitHub") && !procChunk.includes("New Relic"));
expect("dossier has no highest-authorized badge line", !dossier.includes("highest authorized"));
expect("dossier below-fold tables have no spine class on identity", dossier.includes('class="inst filed"') && dossier.includes('class="ident"'));

const ident = dossier.split('class="ident"')[1].split("</section>")[0];
expect("cursor identity has five rules", (ident.match(/file-rule/g) || []).length === 5);
expect("cursor identity fills the on-file instruments", (ident.match(/file-rule on/g) || []).length === 5);
expect("cursor identity has no tier word", !/silent|thin|substantial|complete/.test(ident) && !ident.includes("file ·"));

const aws = readFileSync(new URL("../site/c/amazon-web-services.html", import.meta.url), "utf8");
const awsIdent = aws.split('class="ident"')[1].split("</section>")[0];
expect("aws identity has five rules", (awsIdent.match(/file-rule/g) || []).length === 5);
expect("aws DPA stays an open rule", (awsIdent.match(/file-rule on/g) || []).length === 4);
expect("aws identity has no complete word", !awsIdent.includes("complete") && !awsIdent.includes("substantial") && !awsIdent.includes("file-word"));

const cvent = bySlug.cvent;
const vertex = bySlug.vertex;
const checkr = bySlug.checkr;
const clickup = bySlug.clickup;
const monday = bySlug.monday;
const miro = bySlug.miro;
const unity = bySlug.unity;
const amplitude = bySlug.amplitude;
const benchling = bySlug.benchling;
const digitalocean = bySlug.digitalocean;
expect("cvent DPA follows the stored addendum", cvent.instruments.dpa.url === "https://www.cvent.com/en/data-processing-addendum" && fileFlags(cvent).dpa === 20 && ruleOn(fileIndexHtml(cvent))[2] === true);
expect("vertex DPA follows the stored addendum", vertex.instruments.dpa.url === "https://www.vertexinc.com/legal/data-processing-addendum" && fileFlags(vertex).dpa === 20 && ruleOn(fileIndexHtml(vertex))[2] === true);
expect("miro DPA follows the stored addendum", miro.instruments.dpa.url === "https://miro.com/legal/customer-data-processing-addendum/" && fileFlags(miro).dpa === 20 && ruleOn(fileIndexHtml(miro))[2] === true);
expect("unity DPA follows the stored addendum", unity.instruments.dpa.url === "https://unity.com/legal/unity-data-processing-addendum-dpa" && fileFlags(unity).dpa === 20 && ruleOn(fileIndexHtml(unity))[2] === true);
expect("checkr subprocessors follow the stored list", checkr.instruments.subprocessors.url === "https://checkr.com/legal/sub-processor-list" && checkr.processors.length > 0 && fileFlags(checkr).subprocessors === 20);
expect("clickup subprocessors follow the stored list", clickup.instruments.subprocessors.url === "https://clickup.com/terms/dpa/subprocessors" && clickup.processors.length > 0 && fileFlags(clickup).subprocessors === 20);
expect("monday subprocessors follow the stored list", monday.instruments.subprocessors.url === "https://monday.com/l/privacy/sub-processors-subsidiaries-support/" && monday.processors.length > 0 && fileFlags(monday).subprocessors === 20);
expect("amplitude subprocessors follow the stored list", amplitude.instruments.subprocessors.url === "https://www.amplitude.com/subprocessor-list" && amplitude.processors.length > 0 && fileFlags(amplitude).subprocessors === 20);
expect("benchling subprocessors follow the stored list", benchling.instruments.subprocessors.url === "https://www.benchling.com/subprocessors" && benchling.processors.length > 0 && fileFlags(benchling).subprocessors === 20);
expect("digitalocean subprocessors follow the stored list", digitalocean.instruments.subprocessors.url === "https://www.digitalocean.com/trust/subprocessors" && digitalocean.processors.length > 0 && fileFlags(digitalocean).subprocessors === 20);
const planview = bySlug.planview;
expect(
  "URL-only subprocessors is 10 not 20",
  planview.processors.length === 0 &&
    !!planview.instruments.subprocessors.url &&
    fileFlags(planview).subprocessors === 10 &&
    fileScore(fileFlags(planview)) === 90 &&
    ruleKind(fileIndexHtml(planview))[3] === "partial" &&
    fileIndexHtml(planview).includes('class="file-rule partial"'),
);
const urlOnlySubs = { instruments: { subprocessors: { url: "https://example.com/subprocessors" } } };
expect("synthetic URL-only subprocessors is 10", fileFlags(urlOnlySubs).subprocessors === 10 && fileScore(fileFlags(urlOnlySubs)) === 10);
expect("dotted rule is Ledger Black not a pip", fileIndexHtml(urlOnlySubs).includes('class="file-rule partial"') && ruleKind(fileIndexHtml(urlOnlySubs))[3] === "partial");
expect("filed processor names are not dates", [checkr, clickup, monday, amplitude, benchling, digitalocean].every((row) => (row.processors || []).every((p) => !/^\d{1,2}\s+[A-Za-z]+\s+\d{4}$/.test(p.name) && p.name !== "Date" && p.name !== "Date of change" && p.name !== "AUS" && p.name !== "Data Center Services")));

const box = readFileSync(new URL("../site/c/box.html", import.meta.url), "utf8");
expect("on-file FedRAMP is a table with marketplace cite", box.includes("Filed from the") && box.includes("FedRAMP Marketplace") && box.includes("fedramp.gov/marketplace") && box.includes('class="inst filed"') && box.includes("authorized") && !box.includes("Not a badge") && !box.includes("highest authorized") && !box.includes('td class="mark"') && !box.includes("sem-source") && !box.includes("sem-conflict"));
expect("on-file processors are published names", box.includes("GitHub") && box.includes("New Relic") && !box.includes("+N") && !box.includes("Not a complete supply chain") && /sec-kicker">Named processors[\s\S]*Filed from/.test(box));

const vercel = readFileSync(new URL("../site/c/vercel.html", import.meta.url), "utf8");
expect("vercel mark words with a file are links", vercel.includes('href="../attestations.html#dora">DORA</a>') && vercel.includes('href="../attestations.html#eu-us-dpf">EU-US DPF</a>') && vercel.includes('href="../attestations.html#nis2">NIS2</a>') && vercel.includes('href="../attestations.html#pipeda">PIPEDA</a>'));
const chain = readFileSync(new URL("../site/c/chainguard.html", import.meta.url), "utf8");
expect("mark without a file stays words", chain.includes("<li>SLSA</li>") && !chain.includes("attestations.html#slsa") && !chain.includes("<img"));

const css = readFileSync(new URL("../site/styles.css", import.meta.url), "utf8");
expect("identity block wears the spine", /\.ident \{[\s\S]*border-left: var\(--ot-spine\) solid var\(--ot-evidence-teal\)/.test(css));
expect("no boxed file-state module", !css.includes(".file-state") && !css.includes(".state-word"));
expect("rules are ledger black", /\.file-rule \{[\s\S]*border-top: 1px solid var\(--ot-ledger-black\)/.test(css) && /\.file-rule\.on \{[\s\S]*background: var\(--ot-ledger-black\)/.test(css));
expect("teal does not fill the rules", !/\.file-rule[\s\S]{0,80}--ot-evidence-teal/.test(css) && !/\.file-rule\.on[\s\S]{0,80}--ot-evidence-teal/.test(css) && !/\.file-rule\.partial[\s\S]{0,80}--ot-evidence-teal/.test(css));
expect("no star styles", !css.includes("★") && !css.includes("☆") && !css.includes("star-rating") && !css.includes("trust-maturity"));
expect("marks stay Atkinson data", /\.mark-list li \{[\s\S]*font: var\(--t-data\)/.test(css) && /\.mark-list li \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
expect("instrument cells stay Atkinson", /\.inst td \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
expect("Official page stays Atkinson", /\.out \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css) && /a\.official \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
expect("Official page stays Atkinson on compact", /\.dossier \.file \.out a\.official \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
expect("filed tables have no second spine", /\.inst\.filed td:first-child \{[\s\S]*border-left: 0/.test(css) && /\.inst\.filed tbody tr:hover td:first-child[\s\S]*border-left: 0/.test(css));
expect("phone keeps FedRAMP columns as a table", !/\.dossier \.file \.inst thead \{ display: none/.test(css) && !/\.dossier \.file \.inst\.filed td\.empty \{[\s\S]*display: none/.test(css));
