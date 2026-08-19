import { readFileSync } from "node:fs";
import { parseFinder } from "../site/finder.js";
import {
  normalizeSort,
  normalizeDir,
  clickSort,
  marksCount,
  arrangeRows,
} from "../site/register.js";

const data = JSON.parse(readFileSync(new URL("../site/data.json", import.meta.url), "utf8"));
const rows = data.companies;

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
const order = { silent: 0, thin: 1, "on-file": 2, substantial: 3, complete: 4 };
const tierOk = byTier.every((r, i) => {
  if (i === 0) return true;
  return (order[r.tier] || 0) <= (order[byTier[i - 1].tier] || 0);
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

const byProbed = arrangeRows(rows, "probed", "desc", data.generated_at);
const probedOk = byProbed.every((r, i) => {
  if (i === 0) return true;
  const a = Date.parse(r.probed_at || data.generated_at || "") || 0;
  const b = Date.parse(byProbed[i - 1].probed_at || data.generated_at || "") || 0;
  return a <= b;
});
expect("probed is by date", probedOk);

const complete = apply("/ complete");
const completeByName = arrangeRows(complete, "name", "asc");
expect("sort keeps finder set", completeByName.length === complete.length && completeByName.every((r) => r.tier === "complete"));
expect("sorted finder is A–Z", completeByName[0].name.localeCompare(completeByName[completeByName.length - 1].name, undefined, { sensitivity: "base" }) < 0);

const stripe = apply("/ stripe");
const stripeByDomain = arrangeRows(stripe, "domain", "asc");
expect("stripe still found", stripeByDomain.some((r) => r.slug === "stripe"));

if (!process.exitCode) console.log("ok sort");
