import { readFileSync } from "node:fs";
import { parseFinder } from "../site/finder.js";

const data = JSON.parse(readFileSync(new URL("../site/data.json", import.meta.url), "utf8"));
const rows = data.companies;

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

function apply(raw, url = {}) {
  const parsed = parseFinder(raw);
  const f = {
    q: parsed.q,
    tier: parsed.tier !== "all" ? parsed.tier : url.tier || "all",
    list: parsed.list !== "all" ? parsed.list : url.list || "all",
    fedramp: parsed.fedramp !== "all" ? parsed.fedramp : url.fedramp || "all",
  };
  return rows.filter((row) => {
    if (f.tier !== "all" && row.tier !== f.tier) return false;
    if (f.list === "cloud100" && row.list !== "cloud100") return false;
    if (f.list === "enterprise" && row.list !== "enterprise") return false;
    if (f.fedramp !== "all") {
      if (!row.fedramp) return false;
      if (f.fedramp !== "any") {
        const levels = (row.fedramp.levels || []).map((lv) => String(lv).toLowerCase());
        if (!levels.includes(f.fedramp)) return false;
      }
    }
    if (!f.q) return true;
    return hay(row).includes(f.q);
  });
}

function expect(name, cond) {
  if (!cond) {
    console.error("fail", name);
    process.exitCode = 1;
  } else {
    console.log("ok", name);
  }
}

const complete = apply("/ complete");
expect("complete is ordinary text", complete.every((r) => hay(r).includes("complete")));
expect("complete is not a tier token", parseFinder("/ complete").tier === "all");

const cloud = apply("/ cloud 100");
expect("cloud 100", cloud.length > 0 && cloud.every((r) => r.list === "cloud100"));

const fr = apply("/ fedramp moderate");
expect("fedramp moderate", fr.length > 0 && fr.every((r) => (r.fedramp?.levels || []).map((x) => String(x).toLowerCase()).includes("moderate")));

const stripe = apply("/ stripe");
expect("stripe name", stripe.some((r) => r.slug === "stripe"));

const mixed = apply("/ stripe, fedramp moderate");
expect("mixed is stripe-shaped", mixed.every((r) => /stripe/i.test(r.name) && r.fedramp));

const fromUrl = apply("", { fedramp: "high" });
expect("?fedramp=high", fromUrl.length > 0 && fromUrl.every((r) => (r.fedramp?.levels || []).map((x) => String(x).toLowerCase()).includes("high")));

const hpe = apply("hewlett packard enterprise");
expect("HPE is not an enterprise-list token", hpe.some((r) => /hewlett/i.test(r.name)));

console.log("rows", rows.length, "cloud100", cloud.length, "fedramp moderate", fr.length);
