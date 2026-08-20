import { readFileSync } from "node:fs";
import {
  arrange,
  clickSort,
  cmpText,
  compareCellText,
  headerKey,
  impactValue,
  parseClerkDate,
} from "../site/sort.js";
import { arrangeProcessors, compareProcessors } from "../site/graph.js";
import { arrangeMarks, compareMarks } from "../site/gazette.js";
import { arrangeRows, clickSort as registerClick, normalizeSort } from "../site/register.js";

const graphHtml = readFileSync(new URL("../site/graph.html", import.meta.url), "utf8");
const attestHtml = readFileSync(new URL("../site/attestations.html", import.meta.url), "utf8");
const stripeHtml = readFileSync(new URL("../site/c/stripe.html", import.meta.url), "utf8");
const pages = readFileSync(new URL("../build_pages.py", import.meta.url), "utf8");
const dossierJs = readFileSync(new URL("../site/dossier.js", import.meta.url), "utf8");
const css = readFileSync(new URL("../site/styles.css", import.meta.url), "utf8");
const data = JSON.parse(readFileSync(new URL("../site/data.json", import.meta.url), "utf8"));

function expect(name, cond) {
  if (!cond) {
    console.error("fail", name);
    process.exitCode = 1;
  } else {
    console.log("ok", name);
  }
}

const idle = { sort: "name", dir: "asc" };
expect("first click same key flips", clickSort(idle, "name").dir === "desc");
expect("first click exposure is high to low", clickSort(idle, "exposure", { exposure: "desc" }).dir === "desc");
expect("concentration click is risk desc", clickSort(idle, "risk", { risk: "desc" }).sort === "risk" && clickSort(idle, "risk", { risk: "desc" }).dir === "desc");

const procs = [
  { name: "Zebra", exposure: 9, risk: 8.1, inRegister: true, tier: "silent", sources: ["https://z.example/x"] },
  { name: "alpha", exposure: 2, risk: 1.2, inRegister: true, tier: "complete", sources: ["https://a.example/x"] },
  { name: "Mid", exposure: 4, risk: 9.0, inRegister: false, tier: null, sources: ["https://m.example/x"] },
];
const az = arrangeProcessors(procs, "name", "asc");
expect("graph default A–Z is case-insensitive", az[0].name === "alpha" && az[1].name === "Mid" && az[2].name === "Zebra");

const byRisk = arrangeProcessors(procs, "risk", "desc");
expect("concentration restores risk ranking", byRisk[0].name === "Mid" && byRisk[1].name === "Zebra" && byRisk[2].name === "alpha");
expect("exposure click is count high to low", arrangeProcessors(procs, "exposure", "desc")[0].name === "Zebra");
expect("public file uses tier order", compareProcessors(procs[0], procs[1], "file") < 0);
expect("graph compare is exported", compareProcessors(procs[1], procs[0], "name") < 0);

expect("graph list has Processor sort", /data-sort="name"/.test(graphHtml) && /Processor/.test(graphHtml));
expect("graph list has Exposure sort", /data-sort="exposure"/.test(graphHtml));
expect("graph list has Public file sort", /data-sort="file"/.test(graphHtml));
expect("graph list has Concentration sort", /data-sort="risk"/.test(graphHtml));
expect("graph list has Source sort", /data-sort="source"/.test(graphHtml));
expect("graph default header is Processor A–Z", /data-sort="name" aria-sort="ascending"/.test(graphHtml));
expect("graph figure is still a canvas", /<canvas id="fig1"/.test(graphHtml));

expect("instruments headers are in the publisher", /sort_th\("instrument", "Instrument"\)/.test(pages) && /sort_th\("host", "Host"\)/.test(pages) && /sort_th\("seen", "Last seen"\)/.test(pages));
expect("fedramp headers are in the publisher", /sort_th\("offering", "Offering"\)/.test(pages) && /sort_th\("impact", "Impact level"\)/.test(pages));
expect("named processors default A–Z in publisher", /sort_th\("processor", "Processor", "asc"\)/.test(pages));
expect("named processors sort by name in publisher", /sorted\(procs, key=lambda p: str\(p.get\("name"\)/.test(pages));
expect("dossier binds clerk tables", /bindClerkTables/.test(dossierJs));
expect("stripe instruments headers sort", /data-table="instruments"/.test(stripeHtml) && /data-sort="instrument"/.test(stripeHtml) && /data-sort="host"/.test(stripeHtml));
expect("stripe fedramp headers sort", /data-table="fedramp"/.test(stripeHtml) && /data-sort="offering"/.test(stripeHtml));
const stripeProcs = [...stripeHtml.match(/data-table="processors"[\s\S]*?<tbody>([\s\S]*?)<\/tbody>/)[1].matchAll(/<td>([^<]+)<\/td>/g)].map((m) => m[1]);
expect("stripe named processors land A–Z", stripeProcs.length > 5 && stripeProcs[0] === "Adish" && stripeProcs.join("\0") === [...stripeProcs].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" })).join("\0"));
expect("marks stay a list", /<ul class="mark-list">/.test(stripeHtml) && !/data-table="marks"/.test(stripeHtml));

expect("host header key", headerKey("Host") === "host");
expect("last seen header key", headerKey("Last seen") === "seen");
expect("impact header key", headerKey("Impact level") === "impact");
expect("auth date header key", headerKey("Auth date") === "date");
expect("processor header key", headerKey("Processor") === "processor");

expect("dates parse clerk day", parseClerkDate("27 May 2020") < parseClerkDate("20 Aug 2026"));
expect("empty date is missing", parseClerkDate("—") == null);
expect("impact High beats Low", impactValue("High") > impactValue("Low"));
expect("impact 20x Moderate beats Moderate", impactValue("20x Moderate") > impactValue("Moderate"));
expect("text cells A–Z", compareCellText("processor", "Twilio", "Amazon Web Services") > 0);
expect("seen cells by day", compareCellText("seen", "20 Aug 2026", "1 Jan 2020") > 0);

const inst = [
  { name: "status", host: "status.example", seen: "1 Jan 2020" },
  { name: "DPA", host: "legal.example", seen: "20 Aug 2026" },
];
const byInst = arrange(inst, "name", "asc", (a, b) => cmpText(a.name, b.name));
expect("instruments can arrange A–Z", byInst[0].name === "DPA" && byInst[1].name === "status");

const marks = [
  { name: "SOC 2 Type II", kind: "attestation", geography: ["US"], issuer: "AICPA", weight: 10, industry: ["cloud"] },
  { name: "FedRAMP", kind: "authorization", geography: ["US"], issuer: "GSA", weight: 12, industry: ["public-sector"] },
];
expect("frameworks default A–Z", arrangeMarks(marks, "name", "asc")[0].name === "FedRAMP");
expect("frameworks weight high first", arrangeMarks(marks, "weight", "desc")[0].name === "FedRAMP");
expect("frameworks kind compare", compareMarks(marks[0], marks[1], "kind") < 0);
expect("frameworks list has sort headers", /id="book-sort"/.test(attestHtml) && /data-sort="name"/.test(attestHtml) && /data-sort="kind"/.test(attestHtml));
expect("frameworks globe stays a canvas", /<canvas id="fig2"/.test(attestHtml));

const rows = data.companies;
expect("register File sort still 0–5 internal order", arrangeRows(rows, "tier", "asc")[0].tier === "silent" && arrangeRows(rows, "tier", "desc")[0].tier === "complete");
expect("register File header is still tier", normalizeSort("tier") === "tier");
const firstFile = registerClick({ sort: "rank", dir: "asc", sorted: false }, "tier");
expect("register File first click stays silent-to-complete", firstFile.sort === "tier" && firstFile.dir === "asc");
expect("register caret CSS stayed on .reg", css.includes('.reg th[data-sort][aria-sort="ascending"] button::after { content: "▴"; }') && css.includes('.reg th[data-sort][aria-sort="descending"] button::after { content: "▾"; }'));
expect("inst caret matches register", css.includes('.inst th[data-sort][aria-sort="ascending"] button::after { content: "▴"; }') && css.includes('.inst th[data-sort][aria-sort="descending"] button::after { content: "▾"; }'));
expect("inst active header is a 1px rule not a chip", /\.inst th\.on \{[^}]*border-bottom-color: var\(--ot-ledger-black\)/.test(css) && !/\.inst th\.on \{[^}]*background:/.test(css));
expect("no third palette added", !/--ot-sort|--ot-chip-fill|#DDEFEA/.test(css.split(".inst th[data-sort]")[1] || ""));

if (!process.exitCode) console.log("ok clerk sort");
