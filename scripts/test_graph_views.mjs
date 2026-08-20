import { readFileSync } from "node:fs";
import { neighborhoodOf, looksLikeDateName, looksLikeProcessorName } from "../site/graph.js";

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
const zoomHtml = readFileSync(new URL("../site/c/zoom.html", import.meta.url), "utf8");
const wires = JSON.parse(readFileSync(new URL("../site/data/subprocessors.json", import.meta.url), "utf8"));

expect("list and map are words", html.includes(">list</button>") && html.includes(">map</button>") && html.includes("|"));
expect("list is the landing", /id="view-list"[^>]*aria-selected="true"/.test(html) && /id="wires"[^>]*data-view="list"/.test(html));
expect("list stays a table", html.includes('id="wire-table"') && html.includes("Concentration") && html.includes("not a security grade"));
expect("clerk neighborhood line sits under the tabs", html.includes('id="hood-line"') && html.indexOf("view-toggle") < html.indexOf("hood-line") && js.includes("neighborhood · "));
expect("Fig. 1 names the neighborhood", js.includes("Fig. 1 · Neighborhood of ${p.name}") && html.includes('id="fig-cap"'));
expect("390 stays the list", /@media \(max-width: 390px\) \{[\s\S]*data-view="map"[\s\S]*\.fig-block[\s\S]*display: none/.test(css) && js.includes("compactPhone") && js.includes("return false"));

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
expect("aws namers stay a count not a ring", hood.namers === 71 && hood.nodes.filter((n) => n.role === "namer").length === 0);
expect(
  "every plate node is named",
  hood.nodes.every((n) => n.name && n.role !== "namer") &&
    hood.nodes.some((n) => n.role === "selected" && n.name === "Amazon Web Services") &&
    hood.others <= 8 &&
    hood.nodes.length === 1 + hood.others,
);
expect("aws siblings are labeled processors", hood.nodes.filter((n) => n.role === "other").every((n) => n.name) && hood.others >= 6);
expect("29 April 2026 is not a processor name", looksLikeDateName("29 April 2026") && !looksLikeProcessorName("29 April 2026"));
expect("01 April 2025 is not a processor name", looksLikeDateName("01 April 2025") && !looksLikeProcessorName("01 April 2025"));
expect("ISO date is not a processor name", looksLikeDateName("2026-04-29") && !looksLikeProcessorName("2026-04-29"));
expect("bare year is not a processor name", looksLikeDateName("2026") && !looksLikeProcessorName("2026"));
expect("date slug is not a processor name", looksLikeDateName("29-april-2026") && !looksLikeProcessorName("29-april-2026"));
expect("AWS still looks like a processor", looksLikeProcessorName("Amazon Web Services") && !looksLikeDateName("Amazon Web Services"));
expect("OpenAI still looks like a processor", looksLikeProcessorName("OpenAI") && !looksLikeDateName("OpenAI"));
expect(
  "published graph has no date-shaped processor nodes",
  !(wires.nodes || []).some((n) => looksLikeDateName(n && n.name) || looksLikeDateName(n && n.id)),
);
expect(
  "published graph has no date-shaped processor edges",
  !(wires.edges || []).some((e) => looksLikeDateName(e && e.to) || looksLikeDateName(e && e.evidence)),
);
expect("no anonymous ring", !hood.nodes.some((n) => n.role === "namer") && edges.length === 1186);
expect("zoom dossier dropped date processors", !zoomHtml.includes("29 April 2026") && !zoomHtml.includes("Date of change") && zoomHtml.includes("Amazon Web Services"));
