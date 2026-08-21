import { readFileSync } from "node:fs";
import {
  defaultProcessorIndex,
  looksLikeDateName,
  looksLikeProcessorName,
  namedProcessors,
  namerInk,
  neighborhoodOf,
} from "../site/graph.js";

function expect(name, cond) {
  if (!cond) {
    console.error("fail", name);
    process.exitCode = 1;
  } else {
    console.log("ok", name);
  }
}

const html = readFileSync(new URL("../site/graph.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../site/styles.css", import.meta.url), "utf8");
const js = readFileSync(new URL("../site/graph.js", import.meta.url), "utf8");
const index = readFileSync(new URL("../site/index.html", import.meta.url), "utf8");
const companies = readFileSync(new URL("../site/companies.html", import.meta.url), "utf8");
const dossier = readFileSync(new URL("../site/c/anysphere.html", import.meta.url), "utf8");
const wires = JSON.parse(readFileSync(new URL("../site/data/subprocessors.json", import.meta.url), "utf8"));

expect("list and map are words", html.includes(">list</button>") && html.includes(">map</button>") && html.includes("|"));
expect("list is the landing", /id="view-list"[^>]*aria-selected="true"/.test(html) && /id="wires"[^>]*data-view="list"/.test(html));
expect("list stays a table", html.includes('id="wire-table"') && html.includes("Concentration") && html.includes("not a security grade"));
expect("clerk neighborhood line sits under the tabs", html.includes('id="hood-line"') && html.indexOf("view-toggle") < html.indexOf("hood-line") && js.includes("neighborhood · "));
expect("Fig. 1 names the neighborhood", js.includes("Fig. 1 · Neighborhood of ${p.name}") && html.includes('id="fig-cap"'));
const phone = css.slice(css.lastIndexOf("@media (max-width: 390px)"));
expect("390 stays the list", /data-view="map"[\s\S]*\.fig-block[\s\S]*display: none/.test(phone) && js.includes("compactPhone") && js.includes("return false"));
expect("390 hides the neighborhood canvas", /#fig1 \{ display: none/.test(phone) && /\.map-field[\s\S]*display: none/.test(phone) && /if \(compactPhone\(\)\) return false/.test(js));
expect("390 stacks the wire list", /\.wires-table \.inst thead \{ display: none/.test(phone) && /\.wires-table \.inst td \{[\s\S]*display: block/.test(phone));
expect("390 kills the inner table scroll", /\.wires-scroll \{[\s\S]*max-height: none/.test(phone) && /\.wires-scroll \{[\s\S]*overflow-x: hidden/.test(phone) && /\.wires-table \.inst \{[\s\S]*min-width: 0/.test(phone));
expect("390 list fields stay labeled", js.includes('data-label="Processor"') && js.includes('data-label="Exposure"') && js.includes('data-label="Public file"') && js.includes('data-label="Concentration"') && js.includes('data-label="Source"'));
expect("1440 wire table stays a table", !/@media \(min-width: 1440px\)/.test(css) && /\.wires-table \.inst \{ display: table/.test(css) && /\.wires-table \.inst \{ display: table; min-width: min\(640px, 100%\)/.test(css));

const toggle = css.slice(css.indexOf(".view-toggle"), css.indexOf(".wires-grid"));
expect("toggle is Atkinson ink words", toggle.includes("var(--t-meta)") && toggle.includes("var(--ot-ledger-black)"));
expect("active view is 1px underline not teal type", toggle.includes("border-bottom: 1px solid transparent") && toggle.includes("border-bottom-color: var(--ot-evidence-teal)") && /\.view-toggle button\.on \{[\s\S]*color: var\(--ot-ledger-black\)/.test(toggle));
expect("selected is ink fill teal stroke", js.includes("ctx.fillStyle = ink") && js.includes("selected ? teal : ink") && js.includes("selected ? 2 : 1") && /placeLabel\([\s\S]*ink/.test(js));
expect("no teal type on the selected name", !js.includes("placeLabel") || !/placeLabel\([^)]*teal/.test(js));
expect("issue line has no edge count", js.includes("fillIssue($(\"issue\"), reg)") && !js.includes("${state.edges.length} edges"));
expect("register first screen untouched", companies.includes("Public trust register") && !index.includes("view-toggle"));
expect("dossier identity untouched", dossier.includes('class="ident"') && dossier.includes("file-line"));

const edges = (wires.edges || [])
  .filter((e) => e.source_url)
  .map((e) => ({ company: e.from || e.company, processor_id: e.to || e.processor, processor: e.to }));
const by = new Map();
for (const e of edges) {
  const id = e.processor_id;
  if (!by.has(id)) by.set(id, { id, name: id, namers: [] });
  by.get(id).namers.push({ company: e.company });
}
const processors = [...by.values()];
const aws = processors.find((p) => p.id === "aws");
aws.name = "Amazon Web Services";
const hood = neighborhoodOf(aws, edges, processors, new Map());
expect("aws namers stay a count not a ring", hood.namers === 77 && hood.nodes.filter((n) => n.role === "namer").length === 0);
expect(
  "every plate node is named",
  hood.nodes.every((n) => n.name && n.role !== "namer") &&
    hood.nodes.some((n) => n.role === "selected" && n.name === "Amazon Web Services") &&
    hood.others <= 8 &&
    hood.nodes.length === 1 + hood.others,
);
expect("aws siblings are labeled processors", hood.nodes.filter((n) => n.role === "other").every((n) => n.name) && hood.others >= 6);
expect("no anonymous ring", !hood.nodes.some((n) => n.role === "namer") && edges.length === 1344);
expect("01 April 2025 is not a processor name", looksLikeDateName("01 April 2025") && !looksLikeProcessorName("01 April 2025"));
expect("29 April 2026 is not a processor name", looksLikeDateName("29 April 2026") && !looksLikeProcessorName("29 April 2026"));
expect("date slug is not a processor name", looksLikeDateName("01-april-2025") && !looksLikeProcessorName("01-april-2025"));
expect("AWS still looks like a processor", looksLikeProcessorName("Amazon Web Services") && !looksLikeDateName("Amazon Web Services"));
const mixed = [
  { id: "01-april-2025", name: "01 April 2025" },
  { id: "stripe", name: "Stripe", slug: "stripe" },
  { id: "aws", name: "Amazon Web Services", slug: "amazon-web-services" },
];
const named = namedProcessors(mixed);
expect("date-shaped names drop from the map list", named.length === 2 && named.every((p) => !looksLikeDateName(p.name) && !looksLikeDateName(p.id)));
expect("default neighborhood is AWS when on file", named[defaultProcessorIndex(named)].id === "aws");
expect("claroty namer is name only", namerInk("claroty.com.png") === "" && namerInk("favicons/claroty.com.png") === "");
expect("zscaler namer is name only", namerInk("zscaler.com.png") === "" && namerInk("favicons/zscaler.com.png") === "");
expect("airtable namer may keep a mark", namerInk("airtable.com.png") === "airtable.com.png");
expect("workday namer may keep a mark", namerInk("workday.com.png") === "workday.com.png");
expect("who-named-them uses namerInk", js.includes("namerInk(iconForDomain") && js.includes("nameWithIcon(label"));
expect("map list names stay name-only", /data-label="Processor">\$\{escapeHtml\(p\.name\)\}/.test(js));
expect(
  "neighborhood skips date-shaped siblings",
  neighborhoodOf(
    aws,
    [...edges, { company: aws.namers[0].company, processor_id: "01-april-2025", processor: "01 April 2025" }],
    [...processors, { id: "01-april-2025", name: "01 April 2025", namers: [] }],
    new Map(),
  ).nodes.every((n) => !looksLikeDateName(n.name) && !looksLikeDateName(n.id)),
);
const zoomHtml = readFileSync(new URL("../site/c/zoom.html", import.meta.url), "utf8");
expect("zoom dossier dropped date-shaped processors", !zoomHtml.includes("01 April 2025") && !zoomHtml.includes("29 April 2026") && zoomHtml.includes("Amazon Web Services"));
