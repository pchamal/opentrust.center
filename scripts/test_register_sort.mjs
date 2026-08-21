import { readFileSync } from "node:fs";
import { parseFinder } from "../site/finder.js";
import { fileCount, fillIssue } from "../site/lib.js";
import {
  normalizeSort,
  normalizeDir,
  clickSort,
  marksCount,
  arrangeRows,
  defaultRows,
  marksCell,
  windowRows,
  pageCount,
  PAGE_SIZE,
} from "../site/register.js";

const data = JSON.parse(readFileSync(new URL("../site/data.json", import.meta.url), "utf8"));
const rows = data.companies;
const registerSrc = readFileSync(new URL("../site/register.js", import.meta.url), "utf8");

function expect(name, cond) {
  if (!cond) {
    console.error("fail", name);
    process.exitCode = 1;
  } else {
    console.log("ok", name);
  }
}

function hay(row) {
  const marks = (row.certs || []).join(" ");
  const att = (row.attestations || []).map((a) => a.name || a.id).join(" ");
  const fr = row.fedramp;
  const fed = fr
    ? ["fedramp", fr.highest, ...(fr.levels || []), ...(fr.raw_levels || [])].filter(Boolean).join(" ")
    : "";
  return [row.name, row.domain, row.slug, marks, att, fed]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function apply(raw) {
  const parsed = parseFinder(raw);
  return rows.filter((row) => {
    if (parsed.tier !== "all" && row.tier !== parsed.tier) return false;
    if (parsed.list === "cloud100" && row.list !== "cloud100") return false;
    if (parsed.fedramp !== "all") {
      if (!row.fedramp) return false;
      if (parsed.fedramp !== "any") {
        const levels = (row.fedramp.levels || []).map((lv) => String(lv).toLowerCase());
        if (!levels.includes(parsed.fedramp)) return false;
      }
    }
    if (!parsed.q) return true;
    return hay(row).includes(parsed.q);
  });
}

expect("register is past 700", rows.length > 700);
expect("file cell is the five-rule index", /fileIndexHtml\(row\)/.test(registerSrc) && !/fileCoverageHtml/.test(registerSrc) && !/displayFileState/.test(registerSrc));
expect("file count is 0–5", fileCount({}) === 0 && fileCount({
  found: true,
  trust_url: "https://trust.example",
  attestations: [{ name: "SOC 2" }],
  instruments: { dpa: { url: "https://example/dpa" }, subprocessors: { url: "https://example/subs" } },
  founded_year: 2011,
}) === 5);

expect("normalize #", normalizeSort("#") === "rank");
expect("normalize junk", normalizeSort("score") === "");
expect("normalize host alias", normalizeSort("domain") === "host");
expect("normalize file alias", normalizeSort("tier") === "file");
expect("dir default for marks", normalizeDir("", "marks") === "asc");
expect("dir default for name", normalizeDir(null, "name") === "asc");
expect("dir default for file", normalizeDir("", "file") === "desc");

const idle = { sort: "name", dir: "asc", sorted: true };
const firstName = clickSort({ sort: "file", dir: "desc", sorted: false }, "name");
expect("first click Company is A–Z", firstName.sort === "name" && firstName.dir === "asc");
expect("second click Company is Z–A", clickSort(firstName, "name").dir === "desc");

const firstHost = clickSort(idle, "host");
expect("first click Host is A–Z", firstHost.sort === "host" && firstHost.dir === "asc");
expect("second click Host reverses", clickSort(firstHost, "host").dir === "desc");

const firstFile = clickSort(idle, "file");
expect("first click File is most-on-file", firstFile.sort === "file" && firstFile.dir === "desc");
expect("second click File reverses", clickSort(firstFile, "file").dir === "asc");
const firstMarks = clickSort(idle, "marks");
expect("first click marks is A–Z", firstMarks.sort === "marks" && firstMarks.dir === "asc");
expect("second click marks reverses", clickSort(firstMarks, "marks").dir === "desc");

const byRank = arrangeRows(rows, "rank", "asc");
expect("rank order still works", byRank[0].rank === 1 && byRank.every((r, i) => i === 0 || r.rank >= byRank[i - 1].rank));

const byRankDesc = arrangeRows(rows, "rank", "desc");
expect("rank high-to-low is 001 last", byRankDesc[0].rank === byRank[byRank.length - 1].rank && byRankDesc[byRankDesc.length - 1].rank === 1);

const byName = arrangeRows(rows, "name", "asc");
const nameOk = byName.every((r, i) => {
  if (i === 0) return true;
  return String(r.name).localeCompare(byName[i - 1].name, undefined, { sensitivity: "base" }) >= 0;
});
expect("name is case-insensitive alpha", nameOk);
expect("name is not rank order", byName[0].slug !== byRank[0].slug || byName[1].slug !== byRank[1].slug);

const mixedCase = arrangeRows(
  [
    { rank: 2, name: "zeta", domain: "z.example", tier: "thin" },
    { rank: 1, name: "Alpha", domain: "a.example", tier: "silent" },
  ],
  "name",
  "asc",
);
expect("name ignores case", mixedCase[0].name === "Alpha" && mixedCase[1].name === "zeta");

const byDomain = arrangeRows(rows, "host", "asc");
const domainOk = byDomain.every((r, i) => {
  if (i === 0) return true;
  return String(r.domain || "").localeCompare(byDomain[i - 1].domain || "", undefined, { sensitivity: "base" }) >= 0;
});
expect("host is case-insensitive alpha", domainOk);

const byTier = arrangeRows(rows, "file", "desc");
const fileOk = byTier.every((r, i) => {
  if (i === 0) return true;
  return fileCount(r) <= fileCount(byTier[i - 1]);
});
expect("file sort uses 0–5 on file", fileOk);
expect("file high is five instruments", fileCount(byTier[0]) === 5);
expect("file low is empty", fileCount(byTier[byTier.length - 1]) === 0);

const english = [...byTier].sort((a, b) => {
  const aw = a.tier === "on-file" ? "on file" : a.tier;
  const bw = b.tier === "on-file" ? "on file" : b.tier;
  return aw.localeCompare(bw);
});
expect(
  "file sort is not English alpha",
  byTier.map((r) => r.slug).join() !== english.map((r) => r.slug).join(),
);

const byMarks = arrangeRows(rows, "marks", "asc");
const emptyMarks = (row) => marksCount(row) === 0;
expect("marks A–Z leaves empty last", emptyMarks(byMarks[byMarks.length - 1]) && !emptyMarks(byMarks[0]));
expect("marks count helper still works", marksCount(rows.find((r) => (r.attestations || []).length)) > 0);

expect("probed still a sort key", normalizeSort("probed") === "probed");

const landing = defaultRows(rows);
const nameOkLanding = landing.every((r, i) => {
  if (i === 0) return true;
  return String(r.name).localeCompare(landing[i - 1].name, undefined, { sensitivity: "base" }) >= 0;
});
expect("default keeps every company", landing.length === rows.length);
expect("default does not drop a slug", new Set(landing.map((r) => r.slug)).size === rows.length);
expect("default is Company A–Z", nameOkLanding && landing[0].name.localeCompare(landing[landing.length - 1].name, undefined, { sensitivity: "base" }) < 0);
expect("complete stays in the table", landing.some((r) => r.tier === "complete"));
expect("file header still sorts the state", fileCount(arrangeRows(rows, "file", "asc")[0]) === 0 && fileCount(arrangeRows(rows, "file", "desc")[0]) === 5);

const indexHtml = readFileSync(new URL("../site/companies.html", import.meta.url), "utf8");
expect("register grid dropped probed", !/data-sort="probed"/.test(indexHtml) && !/>probed</.test(indexHtml));
expect("register dropped the # medal", !/data-sort="rank"/.test(indexHtml) && !/>#</.test(indexHtml));
expect(
  "register headers are Company Host File Marks",
  /<button type="button">Company<\/button>/.test(indexHtml) &&
    /<button type="button">Host<\/button>/.test(indexHtml) &&
    /<button type="button">File<\/button>/.test(indexHtml) &&
    /<button type="button">Marks<\/button>/.test(indexHtml),
);
expect("register file cell has no coverage count", !/file-cov|fileCoverageHtml| of 5/.test(registerSrc));
expect("register has no More on this file", !/More on this file|record-extra/.test(registerSrc));
expect("folio row is a dossier click-through", /class="folio"/.test(registerSrc));

const css = readFileSync(new URL("../site/styles.css", import.meta.url), "utf8");
expect("sort chrome has no chevron", !css.includes('content: "▴"') && !css.includes('content: "▾"'));
expect(
  "active header is a 1px Ledger Black underline on the word",
  /\.reg th\.on button \{[^}]*border-bottom-color: var\(--ot-ledger-black\)/.test(css) &&
    !/\.reg th\.on \{[^}]*border-bottom-color/.test(css),
);
expect("headers stay graphite", /\.reg th \{[\s\S]*color: var\(--ot-graphite\)/.test(css));
expect("row ink is graphite", /\.reg td \{[\s\S]*color: var\(--ot-graphite\)/.test(css) && /\.reg td\.marks,/.test(css));
expect("names stay ledger black", /\.reg td\.name \{[\s\S]*color: var\(--ot-ledger-black\)/.test(css));
expect("coverage is not on the register", !css.includes(".file-meter") && !css.includes(".file-cov"));
expect("hover and selected share the spine", /tr\.folio:hover td\.name,[\s\S]*border-left-color: var\(--ot-evidence-teal\)/.test(css));
expect("register row has no mint wash", !/\.reg tbody tr[\s\S]{0,80}--ot-index-wash/.test(css) && !/\.reg tbody tr[\s\S]{0,120}#DDEFEA/.test(css));
expect("register row has no box-shadow pip", !/\.reg tbody tr[\s\S]{0,200}box-shadow: inset var\(--ot-spine\)/.test(css));
expect("nav underline is 1px teal", /\.docket a \{[\s\S]*border-bottom: 1px solid transparent/.test(css) && /\.docket a\.on \{[\s\S]*border-bottom-color: var\(--ot-evidence-teal\)/.test(css));
expect("wordmark period is a 2px square", /\.wordmark \.wm-dot::after \{[\s\S]*width: 2px;[\s\S]*height: 2px;[\s\S]*background: var\(--ot-evidence-teal\)/.test(css));

const issue = { textContent: "" };
fillIssue(issue, data);
expect("issue line has no ISO stamp", !/20\d\d-\d\d-\d\dT/.test(issue.textContent) && !/dataset /.test(issue.textContent));
expect("issue line keeps the clerk facts", /issue /.test(issue.textContent) && /on file/.test(issue.textContent) && /last probed/.test(issue.textContent));
expect("no rust leftover in css", !/#ff6600|#331400|#662900|#993[Dd]00|--flame|--espresso|--rust|--ember|--well/.test(css));
expect("open record tokens are exact", css.includes("--ot-ledger-black: #0B1411") && css.includes("--ot-evidence-teal: #00685C") && css.includes("--ot-font-editorial: \"Source Serif 4\""));
expect("pagination windows rows", pageCount(734) === 15 && windowRows(rows, 1).rows.length === PAGE_SIZE && windowRows(rows, 1).rows.length < rows.length);
expect("last page is a remainder", windowRows(rows, pageCount(rows.length)).rows.length === ((rows.length % PAGE_SIZE) || PAGE_SIZE));
expect("window preserves order", windowRows(defaultRows(rows), 1).rows[0].slug === defaultRows(rows)[0].slug);

const buyer = marksCell({
  attestations: [
    { name: "CCPA", short: "CCPA" },
    { name: "SOC 2 Type II", short: "SOC 2 Type II" },
    { name: "ISO 27001", short: "ISO 27001" },
    { name: "PCI DSS", short: "PCI DSS" },
    { name: "GDPR", short: "GDPR" },
  ],
});
expect("marks are clerk chips", buyer.includes('class="mark-chip">soc 2 type ii<') && buyer.includes(" · "));
expect("marks cell has no icons", !buyer.includes("<img") && !buyer.includes("ink-ico"));
expect("buyer mark is named first", buyer.indexOf("soc 2") < buyer.indexOf("iso 27001"));
expect("marks have no plus-n", !/\+\d/.test(buyer) && !buyer.includes("mark-more"));
expect("named marks that fit stay listed", /mark-chip">soc 2/.test(buyer) && buyer.includes("ccpa") && buyer.includes("gdpr"));
const filedMarks = marksCell({
  attestations: [{ name: "SOC 2 Type II", id: "soc-2-type-ii", short: "SOC 2 Type II" }],
});
expect(
  "mark words go to the framework entry",
  filedMarks.includes('href="./attestations.html#soc-2-type-ii"')
    && filedMarks.includes("soc 2 type ii")
    && !filedMarks.includes("<img")
    && !filedMarks.includes("<svg"),
);

const fed = marksCell({
  fedramp: { marketplace: "https://marketplace.fedramp.gov/products/FR123" },
  attestations: [{ name: "FedRAMP", id: "fedramp" }, { name: "SOC 2", short: "SOC 2" }],
});
expect("fedramp keeps marketplace underline", fed.includes('class="fr-mark"') && fed.includes("marketplace.fedramp.gov") && fed.includes(" · "));

const fedSet = apply("/ fedramp moderate");
const fedByName = arrangeRows(fedSet, "name", "asc");
expect("sort keeps finder set", fedByName.length === fedSet.length && fedByName.every((r) => (r.fedramp?.levels || []).map((x) => String(x).toLowerCase()).includes("moderate")));
expect("sorted finder is A–Z", fedByName[0].name.localeCompare(fedByName[fedByName.length - 1].name, undefined, { sensitivity: "base" }) < 0);

const stripe = apply("/ stripe");
const stripeByDomain = arrangeRows(stripe, "host", "asc");
expect("stripe still found", stripeByDomain.some((r) => r.slug === "stripe"));

if (!process.exitCode) console.log("ok sort");
