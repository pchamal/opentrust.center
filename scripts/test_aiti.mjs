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
  fillAitiIssue,
  isAiFile,
  isAiNamed,
  isAiListMember,
  printedUrl,
  printedAitiUrl,
  storedAiPageUrl,
  isFirstPartyUrl,
  storedAiProcessors,
  isAiSystemProcessor,
  nameWithIcon,
} from "../site/lib.js";
import { aiMarksCell, defaultAiRows, filledAiRows } from "../site/aiti.js";

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
  return [...html.matchAll(/class="file-rule(?: on)?"/g)].map((m) => m[0].includes(" on"));
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
expect("Cursor marks rule is filled", aiFileFlags(cursor).marks === true && ruleOn(cursorHtml)[1] === true);
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
const first = arranged.slice(0, 16);
const firstFilled = first.filter((r) => aiFileCount(r) > 0).length;
const firstOpen = first.filter((r) => aiFileCount(r) === 0).length;
const names = arranged.map((r) => r.name);
const byName = names.slice().sort((a, b) => String(a).localeCompare(String(b), undefined, { sensitivity: "base" }));
expect("default order is clerk name", names.join("\0") === byName.join("\0"));
expect("first screen is not a complete-file strip", firstFilled < first.length);
expect("first screen includes an open file", firstOpen > 0);
expect("first screen has mixed fills", firstFilled > 0 && firstOpen > 0);
expect("silent or Midjourney-class rows stay in the file", arranged.some((r) => r.slug === "midjourney" || aiFileCount(r) === 0));
const byFilled = filledAiRows(files);
expect("finder filled sort uses the five rules", aiFileCount(byFilled[0]) >= aiFileCount(byFilled[byFilled.length - 1]));
expect("finder filled sort is not the default", byFilled[0].slug !== arranged[0].slug || aiFileCount(arranged[0]) === aiFileCount(byFilled[0]));

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

expect("home docket is AITI Companies Map Standards", docketWords(indexHtml).join(" ") === "AITI Companies Map Standards");
expect("AITI is the active word on /", activeWord(indexHtml) === "AITI");
expect("Companies is the active word on companies", activeWord(companiesHtml) === "Companies");
expect("Map is the active word on graph", activeWord(graphHtml) === "Map");
expect("Standards is the active word on attestations", activeWord(marksHtml) === "Standards");
expect("docket links hit the signed routes", indexHtml.includes('href="./companies.html"') && indexHtml.includes('href="./graph.html"') && indexHtml.includes('href="./attestations.html"') && companiesHtml.includes('href="./"'));
expect("H1 is AI Trust Index", /<h1 class="page-title">AI Trust Index<\/h1>/.test(indexHtml));
expect("product title is AI Trust Index", indexHtml.includes("opentrust.center — AI Trust Index"));
expect("lede is the public file sentence", indexHtml.includes("The public file on AI systems. Not a trust score."));
expect("lede is unchanged", (indexHtml.match(/<p class="lede">The public file on AI systems\. Not a trust score\.<\/p>/g) || []).length === 1);
expect("docket word stays AITI", activeWord(indexHtml) === "AITI");
expect("no stars medals Elo or 0-100", !/★|☆|medal|0–100|0-100|\bElo\b|podium/i.test(aitiJs + indexHtml));
expect("AITI table has no score column", !/>\s*Score\s*</i.test(indexHtml) && !aitiJs.includes("trust score") && !aitiJs.includes("score column") && !aitiJs.includes("aitiScore") && !aitiJs.includes("file score"));
expect("AITI table has no rank column", !/>\s*Rank\s*</i.test(indexHtml) && !aitiJs.includes("who's ahead") && !aitiJs.includes("who’s ahead"));
expect("AITI has no sixth number column", /<th scope="col">#<\/th>\s*<th scope="col">Name<\/th>\s*<th scope="col">Domain<\/th>\s*<th scope="col">File<\/th>\s*<th scope="col" class="marks">Marks<\/th>/.test(indexHtml));
expect("AITI has no N of 5", !aitiJs.includes(" of 5") && !indexHtml.includes(" of 5"));
expect("showing uses the AITI N", aitiJs.includes("showing ${rows.length} of ${n}"));
expect("AITI does not paginate a second universe", !aitiJs.includes("PAGE_SIZE") && !indexHtml.includes("pager"));
expect("legend is the AI five", indexHtml.includes("page · marks · processors · evals · incidents"));
expect("wordmark unchanged", /<a class="wordmark" href="\.\/">opentrust<span class="wm-dot">\.<\/span>center<\/a>/.test(indexHtml));

expect("rules are ledger black", /\.file-rule \{[\s\S]*border-top: 1px solid var\(--ot-ledger-black\)/.test(css) && /\.file-rule\.on \{[\s\S]*background: var\(--ot-ledger-black\)/.test(css));
expect("teal does not fill the rules", !/\.file-rule[\s\S]{0,80}--ot-evidence-teal/.test(css) && !/\.file-rule\.on[\s\S]{0,80}--ot-evidence-teal/.test(css));
expect("rules are short horizontal", /\.file-rule \{[\s\S]*width: 12px;[\s\S]*height: 3px;[\s\S]*border-top: 1px solid/.test(css));
const onBlock = (css.match(/\.docket a\.on \{[^}]+\}/) || [""])[0];
expect("active docket is underline not teal type", onBlock.includes("border-bottom-color: var(--ot-evidence-teal)") && !/(?:^|[;\s{])color:\s*var\(--ot-evidence-teal\)/.test(onBlock));

const dossier = readFileSync(new URL("../site/c/anysphere.html", import.meta.url), "utf8");
expect("dossier docket names AITI", docketWords(dossier).join(" ") === "AITI Companies Map Standards");
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
  expect(`${slug} page rule is filled`, flags.page === true && ruleOn(html)[0] === true);
  expect(`${slug} URL is first-party`, isFirstPartyUrl(rec.url, row.domain) === true);
  const dossierHtml = readFileSync(new URL(`../site/c/${slug}.html`, import.meta.url), "utf8");
  expect(`${slug} dossier reaches the URL`, dossierHtml.includes(rec.url) && dossierHtml.includes(">AI page<") && dossierHtml.includes('class="official"'));
}

expect("Midjourney has no stored AI page", storedAiPageUrl(mid) === "");
expect("Midjourney page stays open", aiFileFlags(mid).page === false);
expect("Midjourney still all-open without an official AI page", ruleOn(midHtml).every((on) => on === false) && aiFileCount(mid) === 0);

expect(
  "generic trust URL does not fill page",
  aiFileFlags({
    slug: "openai",
    domain: "openai.com",
    trust_url: "https://trust.openai.com",
    instruments: { trust: { url: "https://trust.openai.com" } },
  }).page === false,
);
expect(
  "path guess on a security URL does not fill page",
  aiFileFlags({
    slug: "example",
    domain: "example.com",
    instruments: { security: { url: "https://example.com/responsible-ai" } },
  }).page === false,
);
expect(
  "evals follow stored instruments only",
  aiFileFlags({
    slug: "example",
    domain: "example.com",
    instruments: { bounty: { url: "https://example.com/evals" } },
  }).evals === false,
);
expect(
  "incidents follow stored instruments only",
  aiFileFlags({
    slug: "example",
    domain: "example.com",
    trust_url: "https://example.com/incidents",
  }).incidents === false,
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
  aiFileFlags({ ...mid, ai_page: { url: "https://www.midjourney.com/responsible-ai" } }).page === true,
);

expect("Cursor page stays open", aiFileFlags(cursor).page === false && ruleOn(cursorHtml)[0] === false);
expect("Cursor marks bind unchanged", aiFileFlags(cursor).marks === true && ruleOn(cursorHtml)[1] === true);

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
  expect(`${slug} processors rule is filled`, flags.processors === true && ruleOn(html)[2] === true);
  expect(`${slug} stored names are AI system processors`, stored.every((p) => isAiSystemProcessor(p, slug)));
  const dossierHtml = readFileSync(new URL(`../site/c/${slug}.html`, import.meta.url), "utf8");
  const src = rec.source_url || "";
  expect(`${slug} dossier cites the first-party list`, !src || dossierHtml.includes(src) || stored.some((p) => p.name && dossierHtml.includes(p.name)));
}

expect("Midjourney has no stored AI processors", storedAiProcessors(mid).length === 0);
expect("Midjourney processors stay open", aiFileFlags(mid).processors === false);
expect("Midjourney still all-open without a named AI processor", ruleOn(aiFileIndexHtml(mid)).every((on) => on === false) && aiFileCount(mid) === 0);

expect("AWS hosting does not count", isAiSystemProcessor({ name: "Amazon Web Services", slug: "amazon-web-services" }) === false);
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
  }).processors === false,
);
expect(
  "processors bind follows stored AI names",
  aiFileFlags({ ...mid, ai_processors: { names: [{ name: "OpenAI", slug: "openai" }] } }).processors === true,
);

const anthropic = bySlug.anthropic;
const anthropicHtml = aiFileIndexHtml(anthropic);
const anthropicOn = ruleOn(anthropicHtml);
const anthropicMarks = aiMarksCell(anthropic);
const anthropicFlags = aiFileFlags(anthropic);
expect("Anthropic Marks cell prints iso 42001", anthropicMarks.includes("iso 42001"));
expect("Anthropic marks filled iff printed AI mark", anthropicFlags.marks === true && hasPrintedAiMark(anthropic) === true && anthropicOn[1] === true);
expect("Anthropic page follows stored RSP URL", anthropicFlags.page === true && storedAiPageUrl(anthropic).includes("responsible-scaling-policy") && anthropicOn[0] === true);
expect("Anthropic Domain prints the stored AI page URL", printedAitiUrl(anthropic).includes("https://www.anthropic.com/responsible-scaling-policy") && printedAitiUrl(anthropic).includes("responsible-scaling-policy"));
expect("Anthropic processors stay open", anthropicFlags.processors === false && storedAiProcessors(anthropic).length === 0 && anthropicOn[2] === false);
expect("Anthropic evals stay open", anthropicFlags.evals === false && anthropicOn[3] === false);
expect("Anthropic incidents stay open", anthropicFlags.incidents === false && anthropicOn[4] === false);
expect("page bind unchanged for Midjourney", aiFileFlags(mid).page === false);
expect("Cursor processors filled and marks still bound", aiFileFlags(cursor).processors === true && aiFileFlags(cursor).marks === true && ruleOn(aiFileIndexHtml(cursor))[1] === true && ruleOn(aiFileIndexHtml(cursor))[2] === true);
expect("Cursor page still open", aiFileFlags(cursor).page === false);

for (const row of files) {
  const flags = aiFileFlags(row);
  if (flags.evals || flags.incidents) {
    expect(`no invented evals/incidents on ${row.slug}`, false);
  }
}
expect("evals incidents stay uninvented", true);

const cursorDossier = readFileSync(new URL("../site/c/anysphere.html", import.meta.url), "utf8");
const midDossier = readFileSync(new URL("../site/c/midjourney.html", import.meta.url), "utf8");
expect("open files do not grow an empty AI page row", !cursorDossier.includes(">AI page<") && !midDossier.includes(">AI page<"));
expect("AITI table is not restyled with an official page chip", !aitiJs.includes("AI page") && !aitiJs.includes("ai_page"));
expect("printed URL is an href", printedUrl("https://www.anthropic.com/responsible-scaling-policy", "anthropic.com").includes('href="https://www.anthropic.com/responsible-scaling-policy"'));
expect("bare domain stays text", printedUrl("openai.com", "openai.com") === "openai.com");
expect("AITI marks link to the framework", aitiJs.includes('href="./attestations.html#') && aitiJs.includes("mark-chip"));
expect("AITI Domain prints stored AI page or homepage", aitiJs.includes("printedAitiUrl(row)"));
expect("Midjourney Domain stays the homepage", printedAitiUrl(mid).includes("midjourney.com") && !printedAitiUrl(mid).includes("responsible"));
expect("AITI names use the icon helper", aitiJs.includes("nameWithIcon(row.name, row.favicon)"));
expect("01.AI 12px mark is name only", !bySlug["01-ai"].favicon && !nameWithIcon(bySlug["01-ai"].name, bySlug["01-ai"].favicon).includes("ink-ico"));
expect("finder example is aiuc-1", indexHtml.includes('placeholder="/ cursor, aiuc-1"') && !indexHtml.includes("aluc-1") && !aitiJs.includes("aluc-1"));
expect("AITI # is the padded index only", /<td class="num">\$\{escapeHtml\(n\)\}<\/td>/.test(aitiJs) && !/<td class="num">[^<]*<img/.test(aitiJs));
expect("AITI does not invent a globe or index placeholder", !aitiJs.includes("globe") && !aitiJs.includes("placeholder") && !aitiJs.includes("inkIcon("));
expect("AITI body scopes the first-screen nibble", indexHtml.includes('class="register aiti"'));
expect("AITI # is ledger black type", /body\.aiti \.reg td\.num \{[\s\S]*color: var\(--ot-ledger-black\)/.test(css));
expect("AITI # has no pip tile or disc", /body\.aiti \.reg td\.num \{[\s\S]*background: none;[\s\S]*border-radius: 0;[\s\S]*box-shadow: none;/.test(css));
expect("Companies # stays graphite", /\.reg td\.num \{ color: var\(--ot-graphite\)/.test(css));
expect("AITI domain and marks are clerk ink", /body\.aiti \.reg td\.domain a,[\s\S]*color: var\(--ot-ledger-black\);[\s\S]*text-decoration: none;/.test(css));
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
  if (flags.evals || flags.incidents) {
    expect(`no invented evals/incidents on new ${rec.slug}`, false);
  }
}
expect("Aviatrix is not list-sourced", !membership.slugs.aviatrix);
expect("list member helper sees 2026", isAiListMember({ aiti_lists: ["forbes-ai-50-2026"] }) === true);
expect("membership is 200 slugs", Object.keys(membership.slugs).length === 200);
expect("AITI files are exactly the membership", files.length === 200 && files.every((r) => membership.slugs[r.slug]));
expect("every AITI file has official homepage", files.every((r) => /^https?:\/\//.test(r.official_url || "")));
expect("official homepage does not fill page", files.filter((r) => r.official_url && !pagesDoc.pages[r.slug]).every((r) => storedAiPageUrl(r) === "" && aiFileFlags(r).page === false));
expect("Amazon homepage is not an AI page fill", storedAiPageUrl(bySlug.amazon) === "" && aiFileFlags(bySlug.amazon).page === false);
expect("Google homepage is not an AI page fill", storedAiPageUrl(bySlug.google) === "" && aiFileFlags(bySlug.google).page === false);
expect("Midjourney dossier homepage is a link", /<a class="official" href="https:\/\/www\.midjourney\.com\/?"/.test(midDossier));
expect("default first names are clerk-dense", arranged.slice(0, 5).map((r) => r.name).join(" · ").length > 10);

console.log("aiti files", files.length, "page", pageOn.length, "processors", procOn.length, "silent", silent.length);
if (!process.exitCode) console.log("ok aiti");
