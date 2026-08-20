import { readFileSync } from "node:fs";
import { neighborhoodOf } from "../site/graph.js";

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
const dossier = readFileSync(new URL("../site/c/anysphere.html", import.meta.url), "utf8");
const wires = JSON.parse(readFileSync(new URL("../site/data/subprocessors.json", import.meta.url), "utf8"));

expect("list and map are words", html.includes(">list</button>") && html.includes(">map</button>") && html.includes("|"));
expect("list is the landing", /id="view-list"[^>]*aria-selected="true"/.test(html) && /id="wires"[^>]*data-view="list"/.test(html));
expect("list stays a table", html.includes('id="wire-table"') && html.includes("Concentration") && html.includes("not a security grade"));
expect("clerk neighborhood line sits under the tabs", html.includes('id="hood-line"') && html.indexOf("view-toggle") < html.indexOf("hood-line") && js.includes("neighborhood · "));
expect("Fig. 1 caption once", html.includes("Fig. 1 · Named processors, as published.") && html.includes("Filed from public lists. Not a complete supply chain."));
expect("390 stays the list", /@media \(max-width: 390px\) \{[\s\S]*data-view="map"[\s\S]*\.fig-block[\s\S]*display: none/.test(css) && js.includes("compactPhone") && js.includes("return false"));

const toggle = css.slice(css.indexOf(".view-toggle"), css.indexOf(".wires-grid"));
expect("toggle is Atkinson ink words", toggle.includes("var(--t-meta)") && toggle.includes("var(--ot-ledger-black)"));
expect("active view is 1px teal underline", toggle.includes("border-bottom: 1px solid transparent") && toggle.includes("border-bottom-color: var(--ot-evidence-teal)"));
expect("selected is ink fill teal stroke", js.includes("ctx.fillStyle = ink") && js.includes("selected ? teal : ink") && js.includes("selected ? 2 : 1") && /placeLabel\([\s\S]*ink/.test(js));
expect("no teal type on the selected name", !js.includes("placeLabel") || !/placeLabel\([^)]*teal/.test(js));
expect("issue line still counts edges", js.includes("${state.edges.length} edges"));
expect("register first screen untouched", index.includes("Public trust register") && !index.includes("view-toggle"));
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
expect("aws namers stay a count not a ring", hood.namers === 37 && hood.nodes.filter((n) => n.role === "namer").length === 0);
expect(
  "every plate node is named",
  hood.nodes.every((n) => n.name && n.role !== "namer") &&
    hood.nodes.some((n) => n.role === "selected" && n.name === "Amazon Web Services") &&
    hood.others <= 8 &&
    hood.nodes.length === 1 + hood.others,
);
expect("aws siblings are labeled processors", hood.nodes.filter((n) => n.role === "other").every((n) => n.name) && hood.others >= 6);
expect("no anonymous ring", !hood.nodes.some((n) => n.role === "namer") && edges.length === 386);
