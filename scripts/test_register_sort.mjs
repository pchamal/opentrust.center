import { readFileSync } from "node:fs";
import { parseFinder } from "../site/finder.js";
import { fileMeterHtml } from "../site/lib.js";
import {
  normalizeSort,
  normalizeDir,
  clickSort,
  marksCount,
  arrangeRows,
  defaultRows,
  marksCell,
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
  const tier = row.tier === "on-file" ? "on file" : row.tier || "silent";
  return [row.name, row.domain, row.slug, row.tier, tier, marks, att, fed]
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
expect("tier cell still files the five-box meter", /fileMeterHtml\(row\)/.test(registerSrc));
expect(
  "meter is five rust boxes",
  (fileMeterHtml(rows[0]).match(/title="(?:page|marks|dpa|subprocessors|years)"/g) || []).length === 5,
);

expect("normalize #", normalizeSort("#") === "rank");
expect("normalize junk", normalizeSort("score") === "");
expect("dir default for marks", normalizeDir("", "marks") === "desc");
expect("dir default for name", normalizeDir(null, "name") === "asc");

const idle = { sort: "rank", dir: "asc", sorted: false };
const firstRank = clickSort(idle, "rank");
expect("first click # stays 001 first", firstRank.sort === "rank" && firstRank.dir === "asc" && firstRank.sorted);
const flipRank = clickSort(firstRank, "rank");
expect("second click # reverses", flipRank.dir === "desc");

const firstName = clickSort(idle, "name");
expect("first click name is A–Z", firstName.sort === "name" && firstName.dir === "asc");
expect("second click name is Z–A", clickSort(firstName, "name").dir === "desc");

const firstTier = clickSort(idle, "tier");
expect("first click tier is complete first", firstTier.sort === "tier" && firstTier.dir === "desc");
const firstMarks = clickSort(idle, "marks");
expect("first click marks is high count", firstMarks.sort === "marks" && firstMarks.dir === "desc");

const byRank = arrangeRows(rows, "rank", "asc");
expect("default rank order", byRank[0].rank === 1 && byRank.every((r, i) => i === 0 || r.rank >= byRank[i - 1].rank));

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

const byDomain = arrangeRows(rows, "domain", "asc");
const domainOk = byDomain.every((r, i) => {
  if (i === 0) return true;
  return String(r.domain || "").localeCompare(byDomain[i - 1].domain || "", undefined, { sensitivity: "base" }) >= 0;
});
expect("domain is case-insensitive alpha", domainOk);

const byTier = arrangeRows(rows, "tier", "desc");
const tierRank = { silent: 0, thin: 1, "on-file": 2, substantial: 3, complete: 4 };
const tierOk = byTier.every((r, i) => {
  if (i === 0) return true;
  return (tierRank[r.tier] || 0) <= (tierRank[byTier[i - 1].tier] || 0);
});
expect("tier uses disclosure order", tierOk);
expect("tier high is complete", byTier[0].tier === "complete");
expect("tier low is silent", byTier[byTier.length - 1].tier === "silent");

const english = [...byTier].sort((a, b) => {
  const aw = a.tier === "on-file" ? "on file" : a.tier;
  const bw = b.tier === "on-file" ? "on file" : b.tier;
  return aw.localeCompare(bw);
});
const firstSubstantial = byTier.findIndex((r) => r.tier === "substantial");
const firstOnFile = byTier.findIndex((r) => r.tier === "on-file");
const englishSub = english.findIndex((r) => r.tier === "substantial");
const englishOn = english.findIndex((r) => r.tier === "on-file");
expect("tier is not English alpha", firstSubstantial < firstOnFile && englishOn < englishSub);

const byMarks = arrangeRows(rows, "marks", "desc");
const marksOk = byMarks.every((r, i) => {
  if (i === 0) return true;
  return marksCount(r) <= marksCount(byMarks[i - 1]);
});
expect("marks is count high to low", marksOk);
expect("marks count is a number", marksCount(byMarks[0]) > marksCount(byMarks[byMarks.length - 1]));

expect("probed is not a sort key", normalizeSort("probed") === "");

const landing = defaultRows(rows);
const firstScreen = landing.slice(0, 20);
const order = ["silent", "thin", "on-file", "substantial", "complete"];
const landingOk = landing.every((r, i) => {
  if (i === 0) return true;
  return order.indexOf(r.tier || "silent") >= order.indexOf(landing[i - 1].tier || "silent");
});
expect("default keeps every company", landing.length === rows.length);
expect("default does not drop a slug", new Set(landing.map((r) => r.slug)).size === rows.length);
expect("default order is silent thin on-file substantial complete", landingOk);
expect("default opens on silent", landing[0].tier === "silent");
expect("default ends on complete", landing[landing.length - 1].tier === "complete");
expect("first screen is not a complete stripe", firstScreen.every((r) => r.tier !== "complete"));
expect("complete stays in the table", landing.some((r) => r.tier === "complete"));

const indexHtml = readFileSync(new URL("../site/index.html", import.meta.url), "utf8");
expect("register grid dropped probed", !/data-sort="probed"/.test(indexHtml) && !/>probed</.test(indexHtml));
expect("register still files the meter on each row", /fileMeterHtml\(row\)/.test(registerSrc));
expect("folio row is a dossier click-through", /class="folio"/.test(registerSrc));

const css = readFileSync(new URL("../site/styles.css", import.meta.url), "utf8");
expect("sort caret is plex rust triangles", css.includes('content: "▴"') && css.includes('content: "▾"') && /th\[data-sort\] button::after \{[\s\S]*font-family: var\(--font-docket\)/.test(css) && /th\[data-sort\] button::after \{[\s\S]*color: var\(--rust\)/.test(css));
expect("headers stay rust", /\.reg th \{[\s\S]*color: var\(--rust\)/.test(css));
expect("row ink is mute", /\.reg td \{[\s\S]*color: var\(--mute\)/.test(css) && /\.reg td\.num \{ color: var\(--mute\)/.test(css) && /\.reg td\.marks \{[\s\S]*color: var\(--mute\)/.test(css));
expect("names stay ink", /\.reg td\.name \{[\s\S]*color: var\(--ink\)/.test(css));
expect("meter boxes stay rust", /file-meter > span \{[\s\S]*border: 1px solid var\(--rust\)/.test(css));

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
expect("buyer mark is named first", buyer.indexOf("soc 2") < buyer.indexOf("iso 27001"));
expect("plus-n is quiet", buyer.includes('class="mark-more">+2<') && !buyer.includes('class="mark-chip">+2'));
expect("plus-n does not hide soc 2", /mark-chip">soc 2/.test(buyer));

const fed = marksCell({
  fedramp: { marketplace: "https://marketplace.fedramp.gov/products/FR123" },
  attestations: [{ name: "FedRAMP", id: "fedramp" }, { name: "SOC 2", short: "SOC 2" }],
});
expect("fedramp keeps marketplace underline", fed.includes('class="fr-mark"') && fed.includes("marketplace.fedramp.gov") && fed.includes(" · "));

const complete = apply("/ complete");
const completeByName = arrangeRows(complete, "name", "asc");
expect("sort keeps finder set", completeByName.length === complete.length && completeByName.every((r) => r.tier === "complete"));
expect("sorted finder is A–Z", completeByName[0].name.localeCompare(completeByName[completeByName.length - 1].name, undefined, { sensitivity: "base" }) < 0);

const stripe = apply("/ stripe");
const stripeByDomain = arrangeRows(stripe, "domain", "asc");
expect("stripe still found", stripeByDomain.some((r) => r.slug === "stripe"));

if (!process.exitCode) console.log("ok sort");
