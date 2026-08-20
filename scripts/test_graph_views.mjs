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
expect("list is the landing", /id="view-list"[^>]*aria-selected="true"/.test(html) && /id="wires"[^>]*data-view="list"/.test(html) && html.includes('id="wires-map"') && html.includes("hidden"));
expect("list stays a table", html.includes('id="wire-table"') && html.includes("<th scope=\"col\">Processor</th>") && html.includes("Concentration") && html.includes("not a security grade"));
expect("map is a field", html.includes('class="map-field"') && html.includes('id="fig1"'));

const mapChunk = html.slice(html.indexOf('id="wires-map"'), html.indexOf('id="stub"'));
expect(
  "Fig. 1 caption once",
  mapChunk.includes("Fig. 1 · Named processors, as published.") &&
    !mapChunk.includes("not a complete supply chain") &&
    !mapChunk.includes("Filed from public lists"),
);
expect("page still states the limit", html.includes("Filed from public lists. Not a complete supply chain."));
expect("right-hand file remains", html.includes('id="stub"') && html.includes("Who named them") === false && js.includes("Who named them, as published."));

const toggle = css.slice(css.indexOf(".view-toggle"), css.indexOf(".wires-grid"));
expect("toggle is Atkinson ink words", toggle.includes("var(--t-meta)") && toggle.includes("var(--ot-ledger-black)") && !toggle.includes("background: var(--ot-evidence-teal)"));
expect("active view is 1px teal underline", toggle.includes("border-bottom: 1px solid transparent") && toggle.includes("border-bottom-color: var(--ot-evidence-teal)"));
expect("map field is Record White", /map-field \{[\s\S]*background: var\(--ot-record-white\)/.test(css));
expect("390 list stays a table", /@media \(max-width: 390px\) \{[\s\S]*\.wires-table \.inst \{ display: table; \}/.test(css));
expect("390 can hide the graph", css.includes('data-graph="off"') && js.includes("max-width: 390px") && js.includes("Who named them, as published."));

expect("map is a neighborhood crop", js.includes("neighborhoodOf") && js.includes('role: "selected"') && js.includes("NEIGHBOR_MAX") && !js.includes("layoutNetwork"));
expect("click processor files the pane", js.includes("fileProcessor") && js.includes("renderStub") && /kind === "processor"[\s\S]*fileProcessor/.test(js));
expect("click company goes to dossier", js.includes('kind === "company"') && js.includes("./c/${encodeURIComponent(n.slug)}.html"));
expect("selected node is 2px teal", js.includes("selected ? teal : ink") && js.includes("selected ? 2 : 1"));
expect("no dark canvas or glow", !js.includes("shadowBlur") && !js.includes("#111") && js.includes("#F8FAF9") && !js.includes("autoRotate") && !js.includes("bloom"));
expect("reduced motion stays still", js.includes("prefers-reduced-motion") && js.includes("Drag still works"));
expect("issue line still counts edges", js.includes("${state.edges.length} edges"));
expect("no rust espresso flame", !js.includes("--rust") && !js.includes("--espresso") && !js.includes("--flame"));

expect("register first screen untouched", index.includes('class="register"') && index.includes("Public trust register") && !index.includes("view-toggle"));
expect("dossier identity untouched", dossier.includes('class="ident"') && dossier.includes("file-line") && !dossier.includes("view-toggle"));
expect("FedRAMP block untouched", dossier.includes("FedRAMP") && dossier.includes("Filed from the"));

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
const companies = new Map();
const aws = processors.find((p) => p.id === "aws");
const hood = neighborhoodOf(aws, edges, processors, companies);
expect("aws neighborhood exists", Boolean(aws) && hood.namers === 37);
expect(
  "aws is a crop not the plate",
  hood.nodes.length < 80 &&
    hood.nodes.length === 1 + hood.namers + hood.others &&
    hood.others <= 12 &&
    hood.nodes.some((n) => n.role === "selected" && n.id === "aws"),
);
expect("aws keeps the namers", hood.nodes.filter((n) => n.role === "namer").length === 37);
expect("aws is a star not a mesh", hood.links.length === hood.namers + hood.others && edges.length === 386);
