import { readFileSync } from "node:fs";
import {
  AI_FILE_KEYS,
  FILE_KEYS,
  selectAiFiles,
  printedAiMarks,
  hasPrintedAiMark,
  aiFileFlags,
  aiFileIndexHtml,
  aiFileCount,
  aiFileOnWords,
  fileScore,
  fillAitiIssue,
  isAiFile,
  isAiNamed,
  isAiListMember,
  printedUrl,
  printedAitiUrl,
  storedAiPageUrl,
  storedAiEvalsUrl,
  storedAiIncidentsUrl,
  isFirstPartyUrl,
  storedAiProcessors,
  isAiSystemProcessor,
  nameWithIcon,
} from "../site/lib.js";
import { aiMarksCell, defaultAiRows, filledAiRows, namedAiRows, filterAiRows, aitiRowHtml, arrangeAiRows, compareAiRows } from "../site/aiti.js";
import { clickSort, paintHeaders } from "../site/sort.js";

const data = JSON.parse(readFileSync(new URL("../site/data.json", import.meta.url), "utf8"));
const bySlug = Object.fromEntries(data.companies.map((r) => [r.slug, r]));
const files = selectAiFiles(data.companies);

function expect(name, cond) {
  if (!cond) {
    console.error("fail", name);
    process.exitCode = 1;
  } else {
    console.log("ok", name);
  }
}

function ruleOn(html) {
  return [...html.matchAll(/class="file-rule(?: (on|partial))?"/g)].map((m) => m[1] === "on");
}

function ruleKind(html) {
  return [...html.matchAll(/class="file-rule(?: (on|partial))?"/g)].map((m) => m[1] || "");
}

function docketWords(html) {
  const nav = html.match(/<nav class="docket"[^>]*>([\s\S]*?)<\/nav>/);
  if (!nav) return [];
  return [...nav[1].matchAll(/>([^<]+)<\/a>/g)].map((m) => m[1].trim());
}

function activeWord(html) {
  const nav = html.match(/<nav class="docket"[^>]*>([\s\S]*?)<\/nav>/);
  if (!nav) return "";
  const on = nav[1].match(/<a[^>]*class="on"[^>]*>([^<]+)<\/a>/);
  return on ? on[1].trim() : "";
}

expect("AI keys are page marks processors evals incidents", AI_FILE_KEYS.join(" ") === "page marks processors evals incidents");
expect("register keys stay untouched", FILE_KEYS.join(" ") === "page marks dpa subprocessors years");
expect("AITI list is from the register", files.length > 0 && files.every((r) => data.companies.some((c) => c.slug === r.slug)));
expect("does not invent companies", files.every((r) => r.slug && bySlug[r.slug]));
expect("includes Midjourney", files.some((r) => r.slug === "midjourney"));
expect("includes Cursor", files.some((r) => r.slug === "anysphere"));
expect("Character.AI is not in the verified universe", !files.some((r) => r.slug === "character-ai"));
expect("Writer is not in the verified universe", !files.some((r) => r.slug === "writer"));
expect("includes Forbes AI 50 2026", files.some((r) => (r.aiti_lists || []).includes("forbes-ai-50-2026") || r.list === "forbes-ai-50-2026"));
expect("includes Brink", files.some((r) => (r.aiti_lists || []).includes("forbes-ai-50-brink-2026") || r.list === "forbes-ai-50-brink-2026"));
expect("includes arena-org", files.some((r) => (r.aiti_lists || []).includes("arena-org")));
expect("includes hugging-face-org", files.some((r) => (r.aiti_lists || []).includes("hugging-face-org")));
expect("skips airlines", !files.some((r) => /airlines/i.test(r.name)));
expect("skips Aviatrix-class TLD membership", !files.some((r) => r.slug === "aviatrix") && !files.some((r) => r.slug === "pinewood-technologies"));
expect(".ai TLD is not enough", isAiFile({ name: "Aviatrix", slug: "aviatrix", domain: "aviatrix.ai" }) === false);
expect("named AI is not membership", isAiNamed({ name: "Scale AI", slug: "scale-ai" }) === true && isAiFile({ name: "Scale AI", slug: "scale-ai" }) === false);
expect("file count is the verified universe", files.length === 200);

const mid = bySlug.midjourney;
const midHtml = aiFileIndexHtml(mid);
const midMarks = aiMarksCell(mid);
expect("Midjourney Marks cell is not on file", midMarks.includes("not on file") && midMarks.includes("absent"));
expect("Midjourney has no printed AI mark", hasPrintedAiMark(mid) === false);
expect("Midjourney all five rules open", ruleOn(midHtml).length === 5 && ruleOn(midHtml).every((on) => on === false));
expect("Midjourney glyph is not vertical ticks", !midHtml.includes("|") && midHtml.includes("file-rule") && !midHtml.includes("file-meter"));

const cursor = bySlug.anysphere;
const cursorHtml = aiFileIndexHtml(cursor);
const cursorMarks = aiMarksCell(cursor);
expect("Cursor Marks cell prints aiuc-1", cursorMarks.includes("aiuc-1"));
expect("Cursor Marks cell does not print soc 2 as the AI mark bind", /aiuc-1/.test(cursorMarks));
expect("Cursor marks rule is filled", aiFileFlags(cursor).marks === 20 && ruleOn(cursorHtml)[1] === true);
expect("printed mark is not next to an open marks rule", ruleOn(cursorHtml)[1] === true);

for (const row of files) {
  const html = aiFileIndexHtml(row);
  const cell = aiMarksCell(row);
  const flags = aiFileFlags(row);
  const on = ruleOn(html);
  const printed = hasPrintedAiMark(row);
  if (printed && (!on[1] || !flags.marks || cell.includes("not on file"))) {
    expect(`bind ${row.slug}: printed mark fills marks`, false);
  }
  if (!printed && (on[1] || flags.marks || !cell.includes("not on file"))) {
    expect(`bind ${row.slug}: empty marks stay open`, false);
  }
}
expect("every AITI row binds marks to the Marks cell", true);

const arranged = defaultAiRows(files);
const names = arranged.map((r) => r.name);
const byName = namedAiRows(files).map((r) => r.name);
expect("default order is highest Completeness then name", arranged.every((row, i) => {
  if (!i) return true;
  const prev = arranged[i - 1];
  const c = fileScore(aiFileFlags(prev)) - fileScore(aiFileFlags(row));
  if (c > 0) return true;
  if (c < 0) return false;
  return String(prev.name).localeCompare(String(row.name), undefined, { sensitivity: "base" }) <= 0;
}));
expect("open rows stay in the file below", arranged.some((r) => r.slug === "midjourney") && aiFileCount(arranged[0]) >= aiFileCount(arranged[arranged.length - 1]) && arranged.findIndex((r) => r.slug === "midjourney") > 0);
expect("default is not name A–Z", names.join("\0") !== byName.join("\0"));
const byFilled = filledAiRows(files);
expect("filled sort is the clerk default", byFilled.map((r) => r.slug).join("\0") === arranged.map((r) => r.slug).join("\0"));
expect("finder name sort is A–Z", filterAiRows(files, "name").map((r) => r.name).join("\0") === byName.join("\0"));
expect("finder still finds a name", filterAiRows(files, "anthropic").some((r) => r.slug === "anthropic"));

const issue = { textContent: "" };
fillAitiIssue(issue, data, files.length);
expect("issue is one number of files", issue.textContent === `issue 20 Aug 2026 · ${files.length} files` || /^issue .+ · \d+ files$/.test(issue.textContent));
expect("issue has no on-file census", !issue.textContent.includes("on file") && !issue.textContent.includes("not on file"));
expect("issue has no second universe", !issue.textContent.includes(" of "));

const indexHtml = readFileSync(new URL("../site/index.html", import.meta.url), "utf8");
const companiesHtml = readFileSync(new URL("../site/companies.html", import.meta.url), "utf8");
const graphHtml = readFileSync(new URL("../site/graph.html", import.meta.url), "utf8");
const marksHtml = readFileSync(new URL("../site/attestations.html", import.meta.url), "utf8");
const aitiJs = readFileSync(new URL("../site/aiti.js", import.meta.url), "utf8");
const css = readFileSync(new URL("../site/styles.css", import.meta.url), "utf8");

expect("home docket is AITI Register Subprocessors Standards", docketWords(indexHtml).join(" ") === "AITI Register Subprocessors Standards");
expect("AITI is the active word on /", activeWord(indexHtml) === "AITI");
expect("Register is the active word on companies", activeWord(companiesHtml) === "Register");
expect("Subprocessors is the active word on graph", activeWord(graphHtml) === "Subprocessors");
expect("Standards is the active word on attestations", activeWord(marksHtml) === "Standards");
expect("graph still has list | map", graphHtml.includes(">list</button>") && graphHtml.includes(">map</button>"));
expect("docket links hit the signed routes", indexHtml.includes('href="./companies.html"') && indexHtml.includes('href="./graph.html"') && indexHtml.includes('href="./attestations.html"') && companiesHtml.includes('href="./"'));
expect("H1 is AI Trust Index", /<h1 class="page-title">AI Trust Index<\/h1>/.test(indexHtml));
expect("product title is AI Trust Index", indexHtml.includes("opentrust.center — AI Trust Index"));
expect("lede is the public file sentence", indexHtml.includes("The public file on AI systems. Not a trust score."));
expect("lede is unchanged", (indexHtml.match(/<p class="lede">The public file on AI systems\. Not a trust score\.<\/p>/g) || []).length === 1);

const methodHtml = readFileSync(new URL("../site/methodology.html", import.meta.url), "utf8");
expect("H1 is Method", /<h1 class="page-title">Method<\/h1>/.test(methodHtml));
expect("lede is the count sentence", (methodHtml.match(/<p class="lede">How we count a public file\. Not a company grade\.<\/p>/g) || []).length === 1);
expect(
  "The count is the three states",
  /<h2 class="sec-kicker">The count<\/h2>\s*<p class="clerk">20 printed · 10 on file, not extracted · 0 missing\. 100 is five prints\.<\/p>/.test(methodHtml) &&
    /<h2 class="sec-kicker">The count<\/h2>\s*<p class="clerk">20 printed · 10 on file, not extracted · 0 missing\. 100 is five prints\.<\/p>/.test(indexHtml) &&
    /<h2 class="sec-kicker">The count<\/h2>\s*<p class="clerk">20 printed · 10 on file, not extracted · 0 missing\. 100 is five prints\.<\/p>/.test(companiesHtml),
);
expect("in-tab Method is the signed page", /id="method-view"[\s\S]*<h1 class="page-title">Method<\/h1>[\s\S]*How we count a public file\. Not a company grade\.[\s\S]*The count[\s\S]*AITI[\s\S]*Register[\s\S]*What counts[\s\S]*What stays open[\s\S]*Outbound/.test(indexHtml));
expect("file|method active is Ledger Black not teal", /body\.register \.view-toggle button\.on \{[\s\S]*border-bottom-color: var\(--ot-ledger-black\)/.test(css) && !/body\.register \.view-toggle button\.on \{[\s\S]{0,120}--ot-evidence-teal/.test(css));
expect("method docket is still four words", docketWords(methodHtml).join(" ") === "AITI Register Subprocessors Standards");
expect("method docket has no teal on", activeWord(methodHtml) === "" && !/<nav class="docket"[^>]*>[\s\S]*class="on"/.test(methodHtml));
expect(
  "AITI footer has specimen · methodology · contact · code",
  /<a href="\.\/brand\.html">specimen<\/a> · <a href="\.\/methodology\.html">methodology<\/a> · <a href="\.\/contact\.html">contact<\/a> · <a href="https:\/\/github.com\/pchamal\/opentrust.center">code<\/a>/.test(indexHtml),
);
expect(
  "Register footer has specimen · methodology · contact · code",
  /<a href="\.\/brand\.html">specimen<\/a> · <a href="\.\/methodology\.html">methodology<\/a> · <a href="\.\/contact\.html">contact<\/a> · <a href="https:\/\/github.com\/pchamal\/opentrust.center">code<\/a>/.test(companiesHtml),
);
const contactHtml = readFileSync(new URL("../site/contact.html", import.meta.url), "utf8");
expect("H1 is Contact", /<h1 class="page-title">Contact<\/h1>/.test(contactHtml));
expect(
  "lede is the write sentence",
  (contactHtml.match(/<p class="lede">Write <a class="official" href="mailto:hello@opentrust.center">hello@opentrust.center<\/a>\.<\/p>/g) || []).length === 1,
);
expect("contact docket is still four words", docketWords(contactHtml).join(" ") === "AITI Register Subprocessors Standards");
expect("contact docket has no teal on", activeWord(contactHtml) === "" && !/<nav class="docket"[^>]*>[\s\S]*class="on"/.test(contactHtml));
expect("contact is not a fifth docket word", !docketWords(contactHtml).includes("Contact") && !docketWords(contactHtml).includes("contact"));
expect("issue is contact", contactHtml.includes('<p class="issue">issue · contact</p>'));
expect("contact footer word is here", /<a href="\.\/contact\.html" class="here">contact<\/a>/.test(contactHtml));
expect("contact page has no personal email", !/pukar@/i.test(contactHtml) && !/securitypalhq/i.test(contactHtml));
expect("contact page has no form", !/<form\b/i.test(contactHtml));
expect("contact page is H1 + lede only", !/<h2\b/.test(contactHtml) && !/class="clerk"/.test(contactHtml) && !/class="sec-kicker"/.test(contactHtml));
expect("no See methodology chip on AITI", !/See methodology/i.test(indexHtml));
expect("no See methodology chip on Register", !/See methodology/i.test(companiesHtml));
expect("AITI method line is the three-state sentence once", (indexHtml.match(/<p class="file-method" id="file-method">20 printed · 10 on file, not extracted · 0 missing\. 100 is five prints\.<\/p>/g) || []).length === 1);
expect("Register method line is the three-state sentence once", (companiesHtml.match(/<p class="file-method" id="file-method">20 printed · 10 on file, not extracted · 0 missing\. 100 is five prints\.<\/p>/g) || []).length === 1);
expect("AITI has completeness | method", indexHtml.includes(">completeness</button>") && indexHtml.includes(">method</button>") && indexHtml.includes('class="view-toggle"'));
expect("Register has completeness | method", companiesHtml.includes(">completeness</button>") && companiesHtml.includes(">method</button>"));
expect("default view is file", /id="file-view"/.test(indexHtml) && /id="method-view"[^>]*hidden/.test(indexHtml) && /id="method-view"[^>]*hidden/.test(companiesHtml));
expect("docket is not a fifth method word", docketWords(indexHtml).join(" ") === "AITI Register Subprocessors Standards" && !docketWords(indexHtml).includes("method"));
expect("docket word stays AITI", activeWord(indexHtml) === "AITI");
expect("no stars medals Elo or 0-100", !/★|☆|medal|0–100|0-100|\bElo\b|podium/i.test(aitiJs + indexHtml));
expect("AITI table has no score column", !/>\s*Score\s*</i.test(indexHtml) && !aitiJs.includes("trust score") && !aitiJs.includes("score column") && !aitiJs.includes("aitiScore") && !aitiJs.includes("file score"));
expect("AITI table has no rank column", !/>\s*Rank\s*</i.test(indexHtml) && !aitiJs.includes("who's ahead") && !aitiJs.includes("who’s ahead"));
expect("AITI has no sixth number column", !/#<\/th>/.test(indexHtml) && !/>\s*#\s*</.test(indexHtml) && (indexHtml.match(/<th /g) || []).length === 4);
expect(
  "AITI headers are Name Domain Completeness Standards",
  /<button type="button">Name<\/button>/.test(indexHtml) &&
    /<button type="button">Domain<\/button>/.test(indexHtml) &&
    /<button type="button">Completeness<\/button>/.test(indexHtml) &&
    /<button type="button">Standards<\/button>/.test(indexHtml) &&
    !/<button type="button">System<\/button>/.test(indexHtml) &&
    !/<button type="button">Host<\/button>/.test(indexHtml) &&
    !/<button type="button">File<\/button>/.test(indexHtml) &&
    !/<button type="button">Marks<\/button>/.test(indexHtml),
);
function aitiHeads(html) {
  const block = ((html.match(/<table class="reg" id="reg"[\s\S]*?<thead>([\s\S]*?)<\/thead>/) || [])[1] || "");
  return [...block.matchAll(/<th\b([^>]*)>([\s\S]*?)<\/th>/g)].map((m) => ({
    attrs: m[1],
    word: ((m[2].match(/<button[^>]*>([^<]*)<\/button>/) || [])[1] || "").trim(),
    classes: (((m[1].match(/\bclass="([^"]*)"/) || [])[1] || "").split(/\s+/).filter(Boolean)),
  }));
}
const heads = aitiHeads(indexHtml);
const fileHead = heads.find((h) => h.word === "Completeness");
const marksHead = heads.find((h) => h.word === "Standards");
expect(
  "first paint only Completeness has the active underline",
  heads.filter((h) => h.classes.includes("on")).map((h) => h.word).join(" ") === "Completeness" &&
    fileHead &&
    /aria-sort="descending"/.test(fileHead.attrs),
);
expect(
  "first paint Standards is a plain word",
  marksHead &&
    !marksHead.classes.includes("on") &&
    /aria-sort="none"/.test(marksHead.attrs) &&
    marksHead.classes.includes("marks"),
);
expect("AITI has no N of 5", !aitiJs.includes(" of 5") && !indexHtml.includes(" of 5"));
expect("showing uses the AITI N", aitiJs.includes("showing ${rows.length} of ${n}"));
expect("AITI does not paginate a second universe", !aitiJs.includes("PAGE_SIZE") && !indexHtml.includes("pager"));
expect("legend is the AI five", indexHtml.includes("page · marks · processors · evals · incidents"));
expect(
  "method line is once under the legend",
  /id="file-legend">page · marks · processors · evals · incidents<\/p>\s*<p class="file-method" id="file-method">20 printed · 10 on file, not extracted · 0 missing\. 100 is five prints\.<\/p>/.test(indexHtml) &&
    (indexHtml.match(/<p class="file-method" id="file-method">20 printed · 10 on file, not extracted · 0 missing\. 100 is five prints\.<\/p>/g) || []).length === 1,
);
expect("wordmark unchanged", /<a class="wordmark" href="\.\/">opentrust<span class="wm-dot">\.<\/span>center<\/a>/.test(indexHtml));

expect("rules are ledger black", /\.file-rule \{[\s\S]*border-top: 1px solid var\(--ot-ledger-black\)/.test(css) && /\.file-rule\.on \{[\s\S]*background: var\(--ot-ledger-black\)/.test(css));
expect("teal does not fill the rules", !/\.file-rule[\s\S]{0,80}--ot-evidence-teal/.test(css) && !/\.file-rule\.on[\s\S]{0,80}--ot-evidence-teal/.test(css) && !/\.file-rule\.partial[\s\S]{0,80}--ot-evidence-teal/.test(css));
expect("rules are short horizontal", /\.file-rule \{[\s\S]*width: 12px;[\s\S]*height: 3px;[\s\S]*border-top: 1px solid/.test(css));
expect("partial is a dotted Ledger Black rule", /\.file-rule\.partial \{[\s\S]*border-top: 1px dotted var\(--ot-ledger-black\)/.test(css));
const onBlock = (css.match(/\.docket a\.on \{[^}]+\}/) || [""])[0];
expect("active docket is underline not teal type", onBlock.includes("border-bottom-color: var(--ot-evidence-teal)") && !/(?:^|[;\s{])color:\s*var\(--ot-evidence-teal\)/.test(onBlock));

const dossier = readFileSync(new URL("../site/c/anysphere.html", import.meta.url), "utf8");
expect("dossier docket names AITI", docketWords(dossier).join(" ") === "AITI Register Subprocessors Standards");
expect("dossier crumb keeps Companies", dossier.includes('href="../companies.html">Companies</a>'));

expect("isAiFile is conservative", isAiFile(bySlug.stripe) === false && isAiFile(mid) === true);
expect("glyph count matches keys", (midHtml.match(/file-rule/g) || []).length === 5);

const silent = files.filter((r) => aiFileCount(r) === 0);
expect("silent AI rows exist", silent.length > 0 && silent.some((r) => r.slug === "midjourney"));

const pagesDoc = JSON.parse(readFileSync(new URL("../site/data/aiti-pages.json", import.meta.url), "utf8"));
const filedSlugs = Object.keys(pagesDoc.pages);
const aitiPageSlugs = filedSlugs.filter((s) => files.some((r) => r.slug === s));
const pageOn = files.filter((r) => aiFileFlags(r).page);
const pageOpen = files.filter((r) => !aiFileFlags(r).page);
expect("AITI page fill is only curated pages on members", pageOn.length === aitiPageSlugs.length && pageOn.every((r) => aitiPageSlugs.includes(r.slug)));
expect("remaining AITI files leave page open", pageOpen.length === files.length - aitiPageSlugs.length);
expect("filed slugs are on the register", filedSlugs.every((s) => bySlug[s]));
expect("does not invent AITI page companies", pageOn.every((r) => filedSlugs.includes(r.slug)));

for (const slug of filedSlugs) {
  const row = bySlug[slug];
  const rec = pagesDoc.pages[slug];
  const flags = aiFileFlags(row);
  const html = aiFileIndexHtml(row);
  expect(`${slug} page follows the stored URL`, storedAiPageUrl(row) === rec.url);
  expect(`${slug} page rule is filled`, flags.page === 20 && ruleOn(html)[0] === true);
  expect(`${slug} URL is first-party`, isFirstPartyUrl(rec.url, row.domain) === true);
  const dossierHtml = readFileSync(new URL(`../site/c/${slug}.html`, import.meta.url), "utf8");
  expect(`${slug} dossier reaches the URL`, dossierHtml.includes(rec.url) && dossierHtml.includes(">AI page<") && dossierHtml.includes('class="official"'));
}

expect("Midjourney has no stored AI page", storedAiPageUrl(mid) === "");
expect("Midjourney page stays open", aiFileFlags(mid).page === 0);
expect("Midjourney still all-open without an official AI page", ruleOn(midHtml).every((on) => on === false) && aiFileCount(mid) === 0);

expect(
  "generic trust URL does not fill page",
  aiFileFlags({
    slug: "openai",
    domain: "openai.com",
    trust_url: "https://trust.openai.com",
    instruments: { trust: { url: "https://trust.openai.com" } },
  }).page === 0,
);
expect(
  "path guess on a security URL does not fill page",
  aiFileFlags({
    slug: "example",
    domain: "example.com",
    instruments: { security: { url: "https://example.com/responsible-ai" } },
  }).page === 0,
);
expect(
  "evals follow stored instruments only",
  aiFileFlags({
    slug: "example",
    domain: "example.com",
    instruments: { bounty: { url: "https://example.com/evals" } },
  }).evals === 0,
);
expect(
  "incidents follow stored instruments only",
  aiFileFlags({
    slug: "example",
    domain: "example.com",
    trust_url: "https://example.com/incidents",
  }).incidents === 0,
);
expect(
  "SafeBase does not fill page",
  storedAiPageUrl({ slug: "example", domain: "example.com", ai_page: { url: "https://example.safebase.us/responsible-ai" } }) === "",
);
expect(
  "third-party host does not fill page",
  storedAiPageUrl({ slug: "anthropic", domain: "anthropic.com", ai_page: { url: "https://example.com/responsible-ai" } }) === "",
);
expect(
  "page bind follows a stored first-party URL",
  aiFileFlags({ ...mid, ai_page: { url: "https://www.midjourney.com/responsible-ai" } }).page === 20,
);

expect("Cursor page stays open", aiFileFlags(cursor).page === 0 && ruleOn(cursorHtml)[0] === false);
expect("Cursor marks bind unchanged", aiFileFlags(cursor).marks === 20 && ruleOn(cursorHtml)[1] === true);

const procsDoc = JSON.parse(readFileSync(new URL("../site/data/aiti-processors.json", import.meta.url), "utf8"));
const procFiled = Object.keys(procsDoc.processors);
const aitiProcSlugs = procFiled.filter((s) => files.some((r) => r.slug === s));
const procOn = files.filter((r) => aiFileFlags(r).processors);
const procOpen = files.filter((r) => !aiFileFlags(r).processors);
expect("AITI processors fill is only curated names on members", procOn.length === aitiProcSlugs.length && procOn.every((r) => aitiProcSlugs.includes(r.slug)));
expect("remaining AITI files leave processors open", procOpen.length === files.length - aitiProcSlugs.length);
expect("does not invent AITI processor companies", procOn.every((r) => procFiled.includes(r.slug) && bySlug[r.slug]));

for (const slug of procFiled) {
  const row = bySlug[slug];
  const rec = procsDoc.processors[slug];
  const stored = storedAiProcessors(row);
  const flags = aiFileFlags(row);
  const html = aiFileIndexHtml(row);
  expect(`${slug} processors follow stored names`, stored.length === rec.names.length && stored.every((p, i) => p.name === rec.names[i].name));
  expect(`${slug} processors rule is filled`, flags.processors === 20 && ruleOn(html)[2] === true);
  expect(`${slug} stored names are AI system processors`, stored.every((p) => isAiSystemProcessor(p, slug)));
  const dossierHtml = readFileSync(new URL(`../site/c/${slug}.html`, import.meta.url), "utf8");
  const src = rec.source_url || "";
  expect(`${slug} dossier cites the first-party list`, !src || dossierHtml.includes(src) || stored.some((p) => p.name && dossierHtml.includes(p.name)));
}

expect("Midjourney has no stored AI processors", storedAiProcessors(mid).length === 0);
expect("Midjourney processors stay open", aiFileFlags(mid).processors === 0);
expect("Midjourney still all-open without a named AI processor", ruleOn(aiFileIndexHtml(mid)).every((on) => on === false) && aiFileCount(mid) === 0);

expect("AWS hosting does not count", isAiSystemProcessor({ name: "Amazon Web Services", slug: "amazon-web-services" }) === false);
expect("dates are not processors", isAiSystemProcessor({ name: "01 April 2025" }) === false && isAiSystemProcessor({ name: "29 April 2026" }) === false);
expect("Date header is not a processor", isAiSystemProcessor({ name: "Date" }) === false && isAiSystemProcessor({ name: "Date of change" }) === false);
expect("Stripe does not count", isAiSystemProcessor({ name: "Stripe", slug: "stripe" }) === false);
expect("Datadog does not count", isAiSystemProcessor({ name: "Datadog", slug: "datadog" }) === false);
expect("bare Google does not count", isAiSystemProcessor({ name: "Google", slug: "google" }) === false);
expect("Azure hosting does not count", isAiSystemProcessor({ name: "Azure" }) === false);
expect("OpenAI counts", isAiSystemProcessor({ name: "OpenAI", slug: "openai" }) === true);
expect("Google Gemini counts", isAiSystemProcessor({ name: "Google Gemini" }) === true);
expect(
  "generic named hosting does not fill processors",
  aiFileFlags({
    slug: "example",
    domain: "example.com",
    processors: [{ name: "Amazon Web Services", slug: "amazon-web-services", source_url: "https://example.com/subprocessors" }],
  }).processors === 0,
);
expect(
  "processors bind follows stored AI names",
  aiFileFlags({ ...mid, ai_processors: { names: [{ name: "OpenAI", slug: "openai" }] } }).processors === 20,
);

const anthropic = bySlug.anthropic;
const anthropicHtml = aiFileIndexHtml(anthropic);
const anthropicOn = ruleOn(anthropicHtml);
const anthropicMarks = aiMarksCell(anthropic);
const anthropicFlags = aiFileFlags(anthropic);
expect("Anthropic Marks cell prints iso 42001", anthropicMarks.includes("iso 42001"));
expect(
  "Anthropic marks print roman not italic",
  anthropicMarks.includes("iso 42001") &&
    !/<i[\s>]/.test(anthropicMarks) &&
    !/font-style:\s*italic/.test(anthropicMarks) &&
    !anthropicMarks.includes("absent"),
);
expect("Anthropic marks filled iff printed AI mark", anthropicFlags.marks === 20 && hasPrintedAiMark(anthropic) === true && anthropicOn[1] === true);
expect("Anthropic page follows stored RSP URL", anthropicFlags.page === 20 && storedAiPageUrl(anthropic).includes("responsible-scaling-policy") && anthropicOn[0] === true);
expect("Anthropic Domain prints anthropic.com", printedAitiUrl(anthropic).includes("https://www.anthropic.com/") && printedAitiUrl(anthropic).includes(">anthropic.com<") && !printedAitiUrl(anthropic).includes("responsible-scaling-policy"));
expect("Anthropic processors stay open", anthropicFlags.processors === 0 && storedAiProcessors(anthropic).length === 0 && !anthropic.ai_processors && anthropicOn[2] === false);
expect("Anthropic leftover ElevenLabs/Vanta bind does not fill processors", (anthropic.processors || []).some((p) => /elevenlabs/i.test(String((p && (p.name || p.slug)) || ""))) && storedAiProcessors(anthropic).length === 0 && anthropicFlags.processors === 0);
expect(
  "row.processors names do not fill AITI processors",
  aiFileFlags({
    slug: "anthropic",
    domain: "anthropic.com",
    processors: [{ name: "ElevenLabs", slug: "elevenlabs", source_url: "https://trust.anthropic.com/subprocessors" }],
  }).processors === 0,
);
expect("Anthropic evals stay open", anthropicFlags.evals === 0 && anthropicOn[3] === false);
expect("Anthropic incidents stay open", anthropicFlags.incidents === 0 && anthropicOn[4] === false);

function domainCell(html) {
  const m = String(html || "").match(/<td class="domain">([\s\S]*?)<\/td>/);
  return m ? m[1] : "";
}

function fileCell(html) {
  const m = String(html || "").match(/<td class="file-cell">([\s\S]*?)<\/td>/);
  return m ? m[1] : "";
}

const defaultAnthropicHtml = aitiRowHtml(defaultAiRows(files).find((r) => r.slug === "anthropic"), 0);
const finderAnthropicHtml = aitiRowHtml(filterAiRows(files, "anthropic").find((r) => r.slug === "anthropic"), 0);
const defaultAnthropicOn = ruleOn(fileCell(defaultAnthropicHtml));
const finderAnthropicOn = ruleOn(fileCell(finderAnthropicHtml));
expect("finder anthropic is the same row", filterAiRows(files, "anthropic").some((r) => r.slug === "anthropic"));
expect(
  "Anthropic flags match in default and finder render",
  defaultAnthropicOn.join(" ") === finderAnthropicOn.join(" ") &&
    defaultAnthropicOn.join(" ") === "true true false false false",
);
expect("Anthropic File is page and marks only", anthropicFlags.page === 20 && anthropicFlags.marks === 20 && anthropicFlags.processors === 0 && anthropicFlags.evals === 0 && anthropicFlags.incidents === 0);
expect("Anthropic count is 2", aiFileCount(anthropic) === 2 && aiFileOnWords(anthropic) === "2 on file");
expect("fileScore is the sum of 0/10/20", fileScore(aiFileFlags(anthropic)) === 40 && fileScore(aiFileFlags(mid)) === 0 && fileScore(aiFileFlags({ ...mid, ai_page: { url: "https://www.midjourney.com/responsible-ai" } })) === 20);
expect(
  "Anthropic File prints 40",
  /<span class="file-num">40<\/span>/.test(fileCell(defaultAnthropicHtml)) &&
    /<span class="file-num">40<\/span>/.test(fileCell(finderAnthropicHtml)) &&
    /<span class="file-num">40<\/span>/.test(fileCell(aitiRowHtml(anthropic, 0))) &&
    !/<span class="file-num">2<\/span>/.test(fileCell(defaultAnthropicHtml)) &&
    !fileCell(defaultAnthropicHtml).includes("40/100") &&
    !fileCell(defaultAnthropicHtml).includes("40%") &&
    !/\d+ on file/.test(fileCell(defaultAnthropicHtml)) &&
    !fileCell(finderAnthropicHtml).includes("2 on file") &&
    !fileCell(defaultAnthropicHtml).includes("file-on"),
);
expect("Anthropic numeral is left of the rules", /file-num[\s\S]*file-index[\s\S]*file-rule/.test(fileCell(defaultAnthropicHtml)));
expect("Midjourney File prints 0", /<span class="file-num">0<\/span>/.test(fileCell(aitiRowHtml(mid, 0))) && !/\d+ on file/.test(fileCell(aitiRowHtml(mid, 0))) && !fileCell(aitiRowHtml(mid, 0)).includes("file-on"));
expect("every row prints the file numeral", files.every((r) => {
  const cell = fileCell(aitiRowHtml(r, 0));
  const n = fileScore(aiFileFlags(r));
  return n % 10 === 0 && n <= 100 && cell.includes(`<span class="file-num">${n}</span>`) && !/\d+ on file/.test(cell) && !cell.includes("file-on");
}));
expect("caption is not a score name", !aitiJs.includes("aitiScore") && !aitiJs.includes("trust index") && !aitiJs.includes("maturity") && !aitiJs.includes("Arena") && !indexHtml.includes(">Score<"));
function hostText(html) {
  return domainCell(html).replace(/<[^>]+>/g, "").trim();
}
expect(
  "Anthropic Domain is anthropic.com in both views",
  hostText(defaultAnthropicHtml) === "anthropic.com" &&
    hostText(finderAnthropicHtml) === "anthropic.com" &&
    !domainCell(defaultAnthropicHtml).includes("responsible-scaling-policy") &&
    !domainCell(finderAnthropicHtml).includes("responsible-scaling-policy"),
);
expect("Midjourney finder render stays all-open", ruleOn(fileCell(aitiRowHtml(filterAiRows(files, "midjourney").find((r) => r.slug === "midjourney"), 0))).every((on) => on === false));
expect("page bind unchanged for Midjourney", aiFileFlags(mid).page === 0);
expect("Cursor processors filled and marks still bound", aiFileFlags(cursor).processors === 20 && aiFileFlags(cursor).marks === 20 && ruleOn(aiFileIndexHtml(cursor))[1] === true && ruleOn(aiFileIndexHtml(cursor))[2] === true);
expect("Cursor page still open", aiFileFlags(cursor).page === 0);
expect("Databricks processors follow stored legal names", storedAiProcessors(bySlug.databricks).map((p) => p.name).join("|") === "Anthropic, PBC|OpenAI, L.L.C" && aiFileFlags(bySlug.databricks).processors === 20);
expect("Glean processors follow stored legal names", storedAiProcessors(bySlug.glean).some((p) => p.name === "Anthropic PBC") && storedAiProcessors(bySlug.glean).some((p) => p.name === "OpenAI OpCo, LLC") && aiFileFlags(bySlug.glean).processors === 20);
expect("Databricks page and marks binds stay open", aiFileFlags(bySlug.databricks).page === 0 && aiFileFlags(bySlug.databricks).marks === 0);
expect("Glean page and marks binds stay open", aiFileFlags(bySlug.glean).page === 0 && aiFileFlags(bySlug.glean).marks === 0);
expect("leftover date names do not fill processors", aiFileFlags({ slug: "zoom", domain: "zoom.com", processors: [{ name: "01 April 2025" }] }).processors === 0);

const evalsDoc = JSON.parse(readFileSync(new URL("../site/data/aiti-evals.json", import.meta.url), "utf8"));
const incidentsDoc = JSON.parse(readFileSync(new URL("../site/data/aiti-incidents.json", import.meta.url), "utf8"));
const evalFiled = Object.keys(evalsDoc.evals || {});
const incidentFiled = Object.keys(incidentsDoc.incidents || {});
const aitiEvalSlugs = evalFiled.filter((s) => files.some((r) => r.slug === s));
const aitiIncidentSlugs = incidentFiled.filter((s) => files.some((r) => r.slug === s));
const evalOn = files.filter((r) => aiFileFlags(r).evals);
const evalOpen = files.filter((r) => !aiFileFlags(r).evals);
const incidentOn = files.filter((r) => aiFileFlags(r).incidents);
const incidentOpen = files.filter((r) => !aiFileFlags(r).incidents);
expect("AITI evals fill is only curated URLs on members", evalOn.length === aitiEvalSlugs.length && evalOn.every((r) => aitiEvalSlugs.includes(r.slug)));
expect("remaining AITI files leave evals open", evalOpen.length === files.length - aitiEvalSlugs.length);
expect("does not invent AITI eval companies", evalOn.every((r) => evalFiled.includes(r.slug) && bySlug[r.slug]));
expect("AITI incidents fill is only curated URLs on members", incidentOn.length === aitiIncidentSlugs.length && incidentOn.every((r) => aitiIncidentSlugs.includes(r.slug)));
expect("remaining AITI files leave incidents open", incidentOpen.length === files.length - aitiIncidentSlugs.length);
expect("does not invent AITI incident companies", incidentOn.every((r) => incidentFiled.includes(r.slug) && bySlug[r.slug]));

for (const slug of evalFiled) {
  const row = bySlug[slug];
  const rec = evalsDoc.evals[slug];
  const flags = aiFileFlags(row);
  const html = aiFileIndexHtml(row);
  expect(`${slug} evals follow the stored URL`, storedAiEvalsUrl(row) === rec.url);
  expect(`${slug} evals rule is filled`, flags.evals === 20 && ruleOn(html)[3] === true);
  expect(`${slug} evals URL is first-party`, isFirstPartyUrl(rec.url, row.domain) === true);
  const dossierHtml = readFileSync(new URL(`../site/c/${slug}.html`, import.meta.url), "utf8");
  expect(`${slug} dossier reaches the evals URL`, dossierHtml.includes(rec.url) && dossierHtml.includes(">AI evals<") && dossierHtml.includes('class="official"'));
}

for (const slug of incidentFiled) {
  const row = bySlug[slug];
  const rec = incidentsDoc.incidents[slug];
  const flags = aiFileFlags(row);
  const html = aiFileIndexHtml(row);
  expect(`${slug} incidents follow the stored URL`, storedAiIncidentsUrl(row) === rec.url);
  expect(`${slug} incidents rule is filled`, flags.incidents === 20 && ruleOn(html)[4] === true);
  expect(`${slug} incidents URL is first-party`, isFirstPartyUrl(rec.url, row.domain) === true);
  const dossierHtml = readFileSync(new URL(`../site/c/${slug}.html`, import.meta.url), "utf8");
  expect(`${slug} dossier reaches the incidents URL`, dossierHtml.includes(rec.url) && dossierHtml.includes(">AI incidents<") && dossierHtml.includes('class="official"'));
}

expect("OpenAI evals follow the stored system card", storedAiEvalsUrl(bySlug.openai) === evalsDoc.evals.openai.url && aiFileFlags(bySlug.openai).evals === 20);
expect("xAI evals follow the stored model card", storedAiEvalsUrl(bySlug.xai) === evalsDoc.evals.xai.url && aiFileFlags(bySlug.xai).evals === 20);
expect("OpenAI page bind unchanged", storedAiPageUrl(bySlug.openai) === pagesDoc.pages.openai.url && aiFileFlags(bySlug.openai).page === 20);
expect("xAI page bind unchanged", storedAiPageUrl(bySlug.xai) === pagesDoc.pages.xai.url && aiFileFlags(bySlug.xai).page === 20);

const openai = bySlug.openai;
expect("OpenAI File is 3", aiFileCount(openai) === 3 && /<span class="file-num">60<\/span>/.test(fileCell(aitiRowHtml(openai, 0))));
expect("OpenAI stays a high File", fileScore(aiFileFlags(openai)) === 60 && aiFileFlags(openai).page === 20 && aiFileFlags(openai).marks === 20 && aiFileFlags(openai).evals === 20);
expect("OpenAI File has no on-file words", !/\d+ on file/.test(fileCell(aitiRowHtml(openai, 0))) && !fileCell(aitiRowHtml(openai, 0)).includes("file-on") && !fileCell(aitiRowHtml(openai, 0)).includes("60%") && !fileCell(aitiRowHtml(openai, 0)).includes("60/100"));
const urlOnlyAi = {
  slug: "example",
  domain: "example.com",
  ai_processors: { url: "https://example.com/model-processors", names: [] },
};
expect("AITI URL-only processors is 10", aiFileFlags(urlOnlyAi).processors === 10 && fileScore(aiFileFlags(urlOnlyAi)) === 10);
expect(
  "dotted rule is the 10 state",
  ruleKind(aiFileIndexHtml(urlOnlyAi))[2] === "partial" &&
    aiFileIndexHtml(urlOnlyAi).includes('class="file-rule partial"') &&
    !aiFileIndexHtml(urlOnlyAi).includes("file-rule on"),
);
expect("dotted rule is not teal", !/\.file-rule\.partial[\s\S]{0,120}--ot-evidence-teal/.test(css));
expect("Midjourney has no dotted rule", !midHtml.includes("file-rule partial") && ruleKind(midHtml).every((k) => k === ""));

const runway = bySlug.runway;
const runwayFlags = aiFileFlags(runway);
const runwayMarks = aiMarksCell(runway);
const runwayHtml = aitiRowHtml(runway, 0);
expect("Runway File is page and processors", runwayFlags.page === 20 && runwayFlags.processors === 20 && runwayFlags.marks === 0 && runwayFlags.evals === 0 && runwayFlags.incidents === 0);
expect("Runway File prints 40", aiFileCount(runway) === 2 && /<span class="file-num">40<\/span>/.test(fileCell(runwayHtml)) && !/<span class="file-num">2<\/span>/.test(fileCell(runwayHtml)) && !/\d+ on file/.test(fileCell(runwayHtml)));
expect("Runway Marks stays italic not on file", runwayMarks.includes("not on file") && runwayMarks.includes("absent"));

const aitiDefaults = { name: "asc", host: "asc", file: "desc", marks: "asc" };
const idleFile = { sort: "file", dir: "desc" };
expect("first click Name is A–Z", clickSort(idleFile, "name", aitiDefaults).sort === "name" && clickSort(idleFile, "name", aitiDefaults).dir === "asc");
expect("second click Name reverses", clickSort({ sort: "name", dir: "asc" }, "name", aitiDefaults).dir === "desc");
expect("first click Domain is A–Z", clickSort(idleFile, "host", aitiDefaults).dir === "asc");
expect("second click Domain reverses", clickSort({ sort: "host", dir: "asc" }, "host", aitiDefaults).dir === "desc");
expect("first click Completeness is most-on-file", clickSort({ sort: "name", dir: "asc" }, "file", aitiDefaults).dir === "desc");
expect("second click Completeness reverses", clickSort({ sort: "file", dir: "desc" }, "file", aitiDefaults).dir === "asc");
expect("first click Standards is A–Z", clickSort(idleFile, "marks", aitiDefaults).dir === "asc");
expect("second click Standards reverses", clickSort({ sort: "marks", dir: "asc" }, "marks", aitiDefaults).dir === "desc");
function fakeHeader(sort, className = "") {
  const classes = className ? className.split(/\s+/).filter(Boolean) : [];
  const attrs = { "data-sort": sort, "aria-sort": "none" };
  return {
    getAttribute(name) {
      return Object.prototype.hasOwnProperty.call(attrs, name) ? attrs[name] : null;
    },
    setAttribute(name, value) {
      attrs[name] = value;
    },
    classList: {
      toggle(name, on) {
        const i = classes.indexOf(name);
        if (on) {
          if (i < 0) classes.push(name);
        } else if (i >= 0) {
          classes.splice(i, 1);
        }
      },
      contains(name) {
        return classes.includes(name);
      },
    },
  };
}
const painted = {
  name: fakeHeader("name"),
  host: fakeHeader("host"),
  file: fakeHeader("file", "on"),
  marks: fakeHeader("marks", "marks"),
};
const paintedRoot = { querySelectorAll: () => [painted.name, painted.host, painted.file, painted.marks] };
paintHeaders(paintedRoot, "file", "desc");
expect(
  "paintHeaders first paint only Completeness is on",
  painted.file.classList.contains("on") &&
    !painted.marks.classList.contains("on") &&
    !painted.name.classList.contains("on") &&
    !painted.host.classList.contains("on") &&
    painted.file.getAttribute("aria-sort") === "descending" &&
    painted.marks.getAttribute("aria-sort") === "none",
);
paintHeaders(paintedRoot, "marks", "asc");
expect(
  "after Standards click only Standards is on",
  painted.marks.classList.contains("on") &&
    !painted.file.classList.contains("on") &&
    !painted.name.classList.contains("on") &&
    !painted.host.classList.contains("on") &&
    painted.marks.getAttribute("aria-sort") === "ascending" &&
    painted.file.getAttribute("aria-sort") === "none",
);
const byHost = arrangeAiRows(files, "host", "asc");
expect("Domain sort is domain A–Z", byHost.every((r, i) => !i || String(r.domain).localeCompare(byHost[i - 1].domain, undefined, { sensitivity: "base" }) >= 0));
const byMarks = arrangeAiRows(files, "marks", "asc");
expect(
  "Standards sort is A–Z with not on file last",
  byMarks.every((r, i) => {
    if (!i) return true;
    return compareAiRows(byMarks[i - 1], r, "marks") <= 0;
  }) &&
    !hasPrintedAiMark(byMarks[byMarks.length - 1]) &&
    hasPrintedAiMark(byMarks[0]),
);
expect("AITI table has four columns", !aitiJs.includes('class="num"') && aitiJs.includes("file-num") && !aitiJs.includes("aitiScore"));

expect(
  "third-party evals URL does not fill",
  storedAiEvalsUrl({ slug: "openai", domain: "openai.com", ai_evals: { url: "https://example.com/evals" } }) === "",
);
expect(
  "SafeBase evals URL does not fill",
  storedAiEvalsUrl({ slug: "example", domain: "example.com", ai_evals: { url: "https://example.safebase.us/evals" } }) === "",
);
expect(
  "evals bind follows a stored first-party URL",
  aiFileFlags({ ...mid, ai_evals: { url: "https://www.midjourney.com/system-card" } }).evals === 20,
);
expect(
  "incidents bind follows a stored first-party URL",
  aiFileFlags({ ...mid, ai_incidents: { url: "https://www.midjourney.com/ai-incidents" } }).incidents === 20,
);
expect(
  "AIID does not fill incidents",
  storedAiIncidentsUrl({ slug: "openai", domain: "openai.com", ai_incidents: { url: "https://incidentdatabase.ai/entities/openai" } }) === "",
);

expect("Midjourney has no stored AI evals", storedAiEvalsUrl(mid) === "");
expect("Midjourney has no stored AI incidents", storedAiIncidentsUrl(mid) === "");
expect("Midjourney evals stay open", aiFileFlags(mid).evals === 0);
expect("Midjourney incidents stay open", aiFileFlags(mid).incidents === 0);

for (const row of files) {
  const flags = aiFileFlags(row);
  if (flags.evals && !evalsDoc.evals[row.slug]) {
    expect(`evals only from store on ${row.slug}`, false);
  }
  if (flags.incidents && !incidentsDoc.incidents[row.slug]) {
    expect(`incidents only from store on ${row.slug}`, false);
  }
}
expect("evals incidents follow stored URLs only", true);

const cursorDossier = readFileSync(new URL("../site/c/anysphere.html", import.meta.url), "utf8");
const midDossier = readFileSync(new URL("../site/c/midjourney.html", import.meta.url), "utf8");
expect("open files do not grow an empty AI page row", !cursorDossier.includes(">AI page<") && !midDossier.includes(">AI page<"));
expect("AITI table is not restyled with an official page chip", !aitiJs.includes("AI page") && !aitiJs.includes("ai_page"));
expect("printed URL is an href", printedUrl("https://www.anthropic.com/responsible-scaling-policy", "anthropic.com").includes('href="https://www.anthropic.com/responsible-scaling-policy"'));
expect("bare domain stays text", printedUrl("openai.com", "openai.com") === "openai.com");
expect("AITI marks link to the framework", aitiJs.includes('href="./attestations.html#') && aitiJs.includes("mark-chip"));
expect("AITI Domain prints the company domain", aitiJs.includes("printedAitiUrl(row)") && aitiJs.includes("aitiRowHtml") && aitiJs.includes("filterAiRows"));
expect("Midjourney Domain stays the homepage", printedAitiUrl(mid).includes("midjourney.com") && printedAitiUrl(mid).includes(">midjourney.com<") && !printedAitiUrl(mid).includes("responsible"));
expect("AITI names use the icon helper", aitiJs.includes("nameWithIcon(row.name, row.favicon)"));
expect("01.AI 12px mark is name only", !bySlug["01-ai"].favicon && !nameWithIcon(bySlug["01-ai"].name, bySlug["01-ai"].favicon).includes("ink-ico"));
expect("finder example is aiuc-1", indexHtml.includes('placeholder="/ cursor, aiuc-1"') && !indexHtml.includes("aluc-1") && !aitiJs.includes("aluc-1"));
expect("AITI has no medal # column", !aitiJs.includes('class="num"') && !/#<\/th>/.test(indexHtml));
expect("AITI does not invent a globe or index placeholder", !aitiJs.includes("globe") && !aitiJs.includes("placeholder") && !aitiJs.includes("inkIcon("));
expect("AITI body scopes the first-screen nibble", indexHtml.includes('class="register aiti"'));
expect("AITI File numeral is Source Serif Ledger Black", /body\.aiti \.reg td\.file-cell \.file-num \{[\s\S]*font: var\(--t-name\)[\s\S]*color: var\(--ot-ledger-black\)/.test(css));
expect("AITI File numeral has no teal", !/body\.aiti \.reg td\.file-cell \.file-num \{[\s\S]{0,180}--ot-evidence-teal/.test(css));
expect("390 stacks the File numeral above the rules", /@media \(max-width: 390px\) \{[\s\S]*body\.aiti \.reg td\.file-cell \.file-num \{[\s\S]*display: block/.test(css));
expect(
  "method line is Atkinson issue size Ledger Black",
  /\.file-method \{[\s\S]*font: var\(--t-data\)[\s\S]*color: var\(--ot-ledger-black\)/.test(css),
);
const methodCss = (css.match(/\.file-method \{[^}]+\}/) || [""])[0];
expect(
  "method line is roman with no strikethrough",
  methodCss.includes("font-style: normal") &&
    methodCss.includes("text-decoration: none") &&
    !/italic/.test(methodCss) &&
    !/line-through/.test(methodCss),
);
expect(
  "method line has no strike markup",
  !/<p class="file-method"[^>]*>[\s\S]*?<(?:s|del|strike|i)[\s>/]/.test(indexHtml) &&
    !/<p class="file-method"[^>]*>[\s\S]*?<(?:s|del|strike|i)[\s>/]/.test(companiesHtml),
);
expect(
  "method line is not a card",
  !/\.file-method \{[\s\S]{0,160}background:/.test(css) &&
    !/\.file-method \{[\s\S]{0,160}border:/.test(css) &&
    !/\.file-method \{[\s\S]{0,160}box-shadow:/.test(css),
);
expect("AITI domain and marks are clerk ink", /body\.aiti \.reg td\.domain a,[\s\S]*color: var\(--ot-ledger-black\);[\s\S]*text-decoration: none;/.test(css));
expect("AITI printed marks stay roman", /body\.aiti \.reg td\.marks \.mark-line,[\s\S]*body\.aiti \.reg td\.marks \.mark-chip \{[\s\S]*font-style: normal;/.test(css));
const regOn = (css.match(/\.reg th\.on \{[^}]+\}/) || [""])[0];
const regOnBtn = (css.match(/\.reg th\.on button \{[^}]+\}/) || [""])[0];
expect(
  "active sort underline is under the button word",
  regOnBtn.includes("border-bottom-color: var(--ot-ledger-black)") &&
    !regOn.includes("border-bottom-color") &&
    !css.includes('content: "▴"') &&
    !css.includes('content: "▾"'),
);
expect("header row hairline stays graphite", /\.reg th \{[\s\S]*border-bottom: 1px solid var\(--ot-rule\)/.test(css));
expect("companies first screen H1 stays", companiesHtml.includes('<h1 class="page-title">Public trust register</h1>') && companiesHtml.includes("A database of each company’s public trust ledger."));
expect("AITI domain and marks hover is a 1px clerk rule", /body\.aiti \.reg td\.domain a:hover,[\s\S]*text-decoration: underline;[\s\S]*text-decoration-color: var\(--ot-rule-strong\)/.test(css));
expect("AITI clerk hover matches Companies names", /\.reg td\.name a:hover \{[\s\S]*text-decoration: underline;[\s\S]*text-decoration-color: var\(--ot-rule-strong\)/.test(css));

const anthropicDossier = readFileSync(new URL("../site/c/anthropic.html", import.meta.url), "utf8");
const aiPageUrl = storedAiPageUrl(bySlug.anthropic);
expect("official AI page URL is a link", aiPageUrl && anthropicDossier.includes(`href="${aiPageUrl}"`) && /<a class="official" href="https:\/\/www\.anthropic\.com\/responsible-scaling-policy"/.test(anthropicDossier));

const listsDoc = JSON.parse(readFileSync(new URL("../site/data/aiti-lists.json", import.meta.url), "utf8"));
const membership = JSON.parse(readFileSync(new URL("../site/data/aiti-membership.json", import.meta.url), "utf8"));
const added = membership.added || [];
expect("new companies were sourced", added.length > 0);
for (const rec of added) {
  expect(`${rec.slug} has official domain`, !!rec.domain && !rec.domain.startsWith("."));
  expect(`${rec.slug} has source_url`, /^https?:\/\//.test(rec.source_url || ""));
  expect(`${rec.slug} is on the register`, !!bySlug[rec.slug]);
  const row = bySlug[rec.slug];
  expect(`${rec.slug} is an AITI file`, isAiFile(row) === true);
  const flags = aiFileFlags(row);
  if (flags.evals && !evalsDoc.evals[rec.slug]) {
    expect(`no invented evals on new ${rec.slug}`, false);
  }
  if (flags.incidents && !incidentsDoc.incidents[rec.slug]) {
    expect(`no invented incidents on new ${rec.slug}`, false);
  }
}
expect("Aviatrix is not list-sourced", !membership.slugs.aviatrix);
expect("list member helper sees 2026", isAiListMember({ aiti_lists: ["forbes-ai-50-2026"] }) === true);
expect("membership is 200 slugs", Object.keys(membership.slugs).length === 200);
expect("AITI files are exactly the membership", files.length === 200 && files.every((r) => membership.slugs[r.slug]));
expect("every AITI file has official homepage", files.every((r) => /^https?:\/\//.test(r.official_url || "")));
expect("official homepage does not fill page", files.filter((r) => r.official_url && !pagesDoc.pages[r.slug]).every((r) => storedAiPageUrl(r) === "" && aiFileFlags(r).page === 0));
expect("Amazon homepage is not the AI page fill", storedAiPageUrl(bySlug.amazon) === pagesDoc.pages.amazon.url && storedAiPageUrl(bySlug.amazon) !== bySlug.amazon.official_url && storedAiPageUrl(bySlug.amazon).includes("responsible-ai"));
expect("Google homepage is not the AI page fill", storedAiPageUrl(bySlug.google) === pagesDoc.pages.google.url && storedAiPageUrl(bySlug.google) !== bySlug.google.official_url && storedAiPageUrl(bySlug.google).includes("responsible-ai"));
expect("Midjourney dossier homepage is a link", /<a class="official" href="https:\/\/www\.midjourney\.com\/?"/.test(midDossier));
expect("default first names are clerk-dense", arranged.slice(0, 5).map((r) => r.name).join(" · ").length > 10);

console.log("aiti files", files.length, "page", pageOn.length, "processors", procOn.length, "evals", evalOn.length, "incidents", incidentOn.length, "silent", silent.length);
if (!process.exitCode) console.log("ok aiti");
