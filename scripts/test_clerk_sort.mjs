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
import { arrangeMarks, citeCount, compareMarks, filterMarks, parseMarkQuery } from "../site/gazette.js";
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
expect("named-by click is exposure desc", clickSort(idle, "exposure", { exposure: "desc" }).sort === "exposure" && clickSort(idle, "exposure", { exposure: "desc" }).dir === "desc");

const procs = [
  { name: "Zebra", exposure: 9, risk: 8.1, inRegister: true, tier: "silent", sources: ["https://z.example/x"] },
  { name: "alpha", exposure: 2, risk: 1.2, inRegister: true, tier: "complete", sources: ["https://a.example/x"] },
  { name: "Mid", exposure: 4, risk: 9.0, inRegister: false, tier: null, sources: ["https://m.example/x"] },
];
const az = arrangeProcessors(procs, "name", "asc");
expect("graph default A–Z is case-insensitive", az[0].name === "alpha" && az[1].name === "Mid" && az[2].name === "Zebra");

expect("named by is count high to low", arrangeProcessors(procs, "exposure", "desc")[0].name === "Zebra");
expect("exposure click is count high to low", arrangeProcessors(procs, "exposure", "desc")[0].name === "Zebra");
expect("public file uses tier order", compareProcessors(procs[0], procs[1], "file") < 0);
expect("graph compare is exported", compareProcessors(procs[1], procs[0], "name") < 0);

expect("graph list has Processor sort", /data-sort="name"/.test(graphHtml) && /Processor/.test(graphHtml));
expect("graph list has Named by sort", /data-sort="exposure"/.test(graphHtml) && /Named by/.test(graphHtml));
expect("graph list has File sort", /data-sort="file"/.test(graphHtml) && /<button type="button">File<\/button>/.test(graphHtml));
expect("graph list dropped Concentration", !/Concentration/.test(graphHtml) && !/data-sort="risk"/.test(graphHtml));
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
const stripeProcs = [...stripeHtml.match(/data-table="processors"[\s\S]*?<tbody>([\s\S]*?)<\/tbody>/)[1].matchAll(/<td>(.*?)<\/td>/g)].map((m) => m[1].replace(/<[^>]+>/g, ""));
expect("stripe named processors land A–Z", stripeProcs.length > 5 && stripeProcs[0] === "Adish" && stripeProcs.join("\0") === [...stripeProcs].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" })).join("\0"));
expect("marks stay a list", /<ul class="mark-list">/.test(stripeHtml) && !/data-table="marks"/.test(stripeHtml));

expect("system header key", headerKey("System") === "name");
expect("company header key", headerKey("Company") === "name");
expect("mark header key", headerKey("Mark") === "name");
expect("named by header key", headerKey("Named by") === "exposure");
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

const gaz = JSON.parse(readFileSync(new URL("../site/data/attestations.json", import.meta.url), "utf8"));
const marks = (gaz.attestations || []).map((item) => ({
  ...item,
  files: citeCount(data.companies, item),
}));
const byFiles = arrangeMarks(marks, "files", "desc");
const byName = arrangeMarks(marks, "name", "asc");
expect("frameworks File click is popularity", byFiles[0].files >= byFiles[1].files && byFiles[0].files > byFiles[byFiles.length - 1].files);
expect("frameworks File lands a high-count mark first", byFiles[0].files >= byFiles[byFiles.length - 1].files);
expect("frameworks popularity tie-breaks A–Z", byFiles.every((r, i) => {
  if (i === 0) return true;
  const prev = byFiles[i - 1];
  if (prev.files !== r.files) return prev.files >= r.files;
  return String(prev.name).localeCompare(String(r.name), undefined, { sensitivity: "base" }) <= 0;
}));
expect("frameworks Name click is A–Z", byName[0].name.localeCompare(byName[byName.length - 1].name, undefined, { sensitivity: "base" }) < 0 && byName[0].id !== byFiles[0].id);
expect("frameworks default is Mark A–Z", arrangeMarks(marks).map((r) => r.id).join("\0") === byName.map((r) => r.id).join("\0"));
expect("frameworks Files click returns popularity", clickSort({ sort: "name", dir: "asc" }, "files", { files: "desc" }).sort === "files" && clickSort({ sort: "name", dir: "asc" }, "files", { files: "desc" }).dir === "desc");
expect("frameworks Files compare", compareMarks(byFiles[0], byFiles[byFiles.length - 1], "files") > 0);
const soc = filterMarks(marks, "soc");
expect("frameworks soc tokens parse", parseMarkQuery("/ soc, 2").join(" ") === "soc 2");
expect("frameworks typing soc filters", soc.length > 0 && soc.length < marks.length && soc.every((r) => markHayOk(r, "soc")));
expect("frameworks empty query invents nothing", filterMarks(marks, "zzzz-not-a-filed-mark").length === 0);
expect("frameworks finder is the quiet input", /id="finder"/.test(attestHtml) && /id="q"/.test(attestHtml) && /Find a mark/.test(attestHtml));
expect("frameworks miss is italic not on file", /id="book-miss"/.test(attestHtml) && /not on file/.test(attestHtml));
expect(
  "frameworks headers are Mark Issuer File",
  /id="book-sort"/.test(attestHtml) &&
    /<button type="button">Mark<\/button>/.test(attestHtml) &&
    /<button type="button">Issuer<\/button>/.test(attestHtml) &&
    /<button type="button">File<\/button>/.test(attestHtml) &&
    /data-sort="name" aria-sort="ascending"/.test(attestHtml) &&
    /data-sort="issuer"/.test(attestHtml) &&
    /data-sort="files"/.test(attestHtml),
);
expect("frameworks globe stays a canvas", /<canvas id="fig2"/.test(attestHtml));
expect("frameworks has no seal icons", !/framework-icon|mark-seal|badge-svg/.test(attestHtml) && !/framework-icon|mark-seal/.test(css));

function markHayOk(item, token) {
  return [item.name, item.short, item.id].filter(Boolean).join(" ").toLowerCase().includes(token);
}

const rows = data.companies;
expect("register File sort still 0–5 internal order", arrangeRows(rows, "file", "asc")[0].tier === "silent" && arrangeRows(rows, "file", "desc")[0].tier === "complete");
expect("register File header is file", normalizeSort("file") === "file" && normalizeSort("tier") === "file");
const firstFile = registerClick({ sort: "name", dir: "asc", sorted: true }, "file");
expect("register File first click is most-on-file", firstFile.sort === "file" && firstFile.dir === "desc");
expect("register sort chrome has no chevron", !css.includes('content: "▴"') && !css.includes('content: "▾"'));
expect("inst active header is a 1px rule not a chip", /\.inst th\.on \{[^}]*border-bottom-color: var\(--ot-ledger-black\)/.test(css) && !/\.inst th\.on \{[^}]*background:/.test(css));
expect("no third palette added", !/--ot-sort|--ot-chip-fill|#DDEFEA/.test(css.split(".inst th[data-sort]")[1] || ""));

if (!process.exitCode) console.log("ok clerk sort");
