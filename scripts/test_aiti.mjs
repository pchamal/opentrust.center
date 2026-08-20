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
  storedAiPageUrl,
  isFirstPartyUrl,
} from "../site/lib.js";
import { aiMarksCell, defaultAiRows } from "../site/aiti.js";

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
expect("includes Character.AI", files.some((r) => r.slug === "character-ai"));
expect("includes Cursor", files.some((r) => r.slug === "anysphere"));
expect("includes AI-50", files.some((r) => r.list === "forbes-ai-50-2025"));
expect("skips airlines", !files.some((r) => /airlines/i.test(r.name)));

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
expect("first screen is not a filled podium", firstFilled < first.length);
expect("first screen includes an open file", first.some((r) => aiFileCount(r) === 0));
expect("silent or Midjourney-class rows are present", arranged.some((r) => r.slug === "midjourney" || r.tier === "silent"));

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
expect("H1 is AI files", /<h1 class="page-title">AI files<\/h1>/.test(indexHtml));
expect("lede is the public file sentence", indexHtml.includes("The public file on AI systems. Not a trust score."));
expect("no AI Trust Index as H1", !/<h1[^>]*>\s*AI Trust Index/i.test(indexHtml));
expect("no stars medals or scores", !/★|☆|medal|0–100|0-100|trust score/i.test(aitiJs) && !indexHtml.includes("AI Trust Index"));
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
expect("silent AI rows exist", silent.length > 0 && silent.some((r) => r.slug === "midjourney" || r.slug === "character-ai"));

const pagesDoc = JSON.parse(readFileSync(new URL("../site/data/aiti-pages.json", import.meta.url), "utf8"));
const filedSlugs = Object.keys(pagesDoc.pages);
const pageOn = files.filter((r) => aiFileFlags(r).page);
const pageOpen = files.filter((r) => !aiFileFlags(r).page);
expect("page fill count is the curated list", pageOn.length === filedSlugs.length && pageOn.length === 7);
expect("46 files leave page open", pageOpen.length === 46 && pagesDoc.open.length === 46);
expect("filed slugs are on the register", filedSlugs.every((s) => bySlug[s]));
expect("does not invent page companies", filedSlugs.every((s) => files.some((r) => r.slug === s)));

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

for (const row of files) {
  const flags = aiFileFlags(row);
  if (flags.processors || flags.evals || flags.incidents) {
    expect(`no invented processors/evals/incidents on ${row.slug}`, false);
  }
}
expect("processors evals incidents stay uninvented", true);

const cursorDossier = readFileSync(new URL("../site/c/anysphere.html", import.meta.url), "utf8");
const midDossier = readFileSync(new URL("../site/c/midjourney.html", import.meta.url), "utf8");
expect("open files do not grow an empty AI page row", !cursorDossier.includes(">AI page<") && !midDossier.includes(">AI page<"));
expect("AITI table domain stays plain text", aitiJs.includes('<td class="domain">${escapeHtml(row.domain || "")}</td>'));
expect("AITI table is not restyled with an official page chip", !aitiJs.includes("AI page") && !aitiJs.includes("ai_page"));

console.log("aiti files", files.length, "page", pageOn.length, "open", pageOpen.length, "silent", silent.length);
if (!process.exitCode) console.log("ok aiti");
