import {
  parseFinder,
  stripFinderToken,
  normalizeFedramp,
  normalizeTier,
  echoWords,
} from "../site/finder.js";

const cases = [
  ["", { q: "", tier: "all", list: "all", fedramp: "all" }],
  ["/ stripe", { q: "stripe", tier: "all", list: "all", fedramp: "all" }],
  ["/ complete", { q: "complete", tier: "all", list: "all", fedramp: "all" }],
  ["on file", { q: "", tier: "on-file", list: "all", fedramp: "all" }],
  ["on-file", { q: "", tier: "on-file", list: "all", fedramp: "all" }],
  ["/ cloud 100", { q: "", tier: "all", list: "cloud100", fedramp: "all" }],
  ["cloud100", { q: "", tier: "all", list: "cloud100", fedramp: "all" }],
  ["/ enterprise", { q: "", tier: "all", list: "enterprise", fedramp: "all" }],
  ["/ fedramp", { q: "", tier: "all", list: "all", fedramp: "any" }],
  ["/ fedramp moderate", { q: "", tier: "all", list: "all", fedramp: "moderate" }],
  ["low", { q: "", tier: "all", list: "all", fedramp: "low" }],
  ["high", { q: "", tier: "all", list: "all", fedramp: "high" }],
  ["/ stripe, complete, fedramp moderate", { q: "stripe complete", tier: "all", list: "all", fedramp: "moderate" }],
  ["stripe complete", { q: "stripe complete", tier: "all", list: "all", fedramp: "all" }],
  ["hewlett packard enterprise", { q: "hewlett packard enterprise", tier: "all", list: "all", fedramp: "all" }],
  ["fedramp 20x moderate", { q: "fedramp 20x moderate", tier: "all", list: "all", fedramp: "all" }],
  ["highspot", { q: "highspot", tier: "all", list: "all", fedramp: "all" }],
  ["soc 2", { q: "soc 2", tier: "all", list: "all", fedramp: "all" }],
  ["/ silent", { q: "silent", tier: "all", list: "all", fedramp: "all" }],
  ["/ thin", { q: "thin", tier: "all", list: "all", fedramp: "all" }],
  ["/ substantial", { q: "substantial", tier: "all", list: "all", fedramp: "all" }],
];

let failed = 0;
for (const [raw, want] of cases) {
  const got = parseFinder(raw);
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) {
    failed += 1;
    console.error("parseFinder", JSON.stringify(raw), "got", got, "want", want);
  }
}

const stripped = stripFinderToken("/ stripe, complete, fedramp moderate", "tier");
if (stripped !== "/ stripe, complete, fedramp moderate") {
  failed += 1;
  console.error("strip retired tier stays text", stripped);
}
if (stripFinderToken("complete", "tier") !== "complete") {
  failed += 1;
  console.error("strip only retired word stays text");
}
if (normalizeFedramp("Moderate") !== "moderate") {
  failed += 1;
  console.error("normalizeFedramp");
}
if (normalizeTier("complete") !== "all" || normalizeTier("silent") !== "all" || normalizeTier("thin") !== "all") {
  failed += 1;
  console.error("retired tier tokens are not current");
}
const echo = echoWords({ tier: "complete", list: "all", fedramp: "moderate" })
  .map((b) => b.label)
  .join(" · ");
if (echo !== "fedramp moderate") {
  failed += 1;
  console.error("echo", echo);
}
const echoOn = echoWords({ tier: "on-file", list: "all", fedramp: "all" })
  .map((b) => b.label)
  .join(" · ");
if (echoOn !== "tier on file") {
  failed += 1;
  console.error("echo on file", echoOn);
}

if (failed) {
  console.error(failed, "failed");
  process.exit(1);
}
console.log("ok", cases.length, "parse cases");
