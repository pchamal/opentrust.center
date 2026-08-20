import { readFileSync } from "node:fs";

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

expect("list and map are words", html.includes(">list</button>") && html.includes(">map</button>") && html.includes("|"));
expect("list is the landing", /id="view-list"[^>]*aria-selected="true"/.test(html) && /id="wires"[^>]*data-view="list"/.test(html) && html.includes('id="wires-map"') && html.includes("hidden"));
expect("list stays a table", html.includes('id="wire-table"') && html.includes("<th scope=\"col\">Processor</th>") && html.includes('id="wire-body"'));
expect("map is a field", html.includes('class="map-field"') && html.includes('id="fig1"') && !html.includes("card-stack"));
expect("Fig. 1 caption", html.includes("Fig. 1 · Named processors, as published.") && html.includes("Filed from public lists. Not a complete supply chain."));
expect("right-hand file remains", html.includes('id="stub"') && html.includes("aria-live"));

const toggle = css.slice(css.indexOf(".view-toggle"), css.indexOf(".wires-grid"));
expect("toggle is Atkinson ink words", toggle.includes("var(--t-meta)") && toggle.includes("var(--ot-ledger-black)") && !toggle.includes("border-radius: var(--ot-radius-control)") && !toggle.includes("background: var(--ot-evidence-teal)"));
expect("active view is 1px teal underline", toggle.includes("border-bottom: 1px solid transparent") && toggle.includes("border-bottom-color: var(--ot-evidence-teal)"));
expect("map field is Record White", css.includes(".map-field") && /map-field \{[\s\S]*background: var\(--ot-record-white\)/.test(css));
expect("390 list stays a table", /@media \(max-width: 390px\) \{[\s\S]*\.wires-table \.inst \{ display: table; \}/.test(css));
expect("390 map stays a field", /@media \(max-width: 390px\) \{[\s\S]*\.map-field \{[\s\S]*display: block;/.test(css));

expect("map reads the same graph", js.includes("data/subprocessors.json") && js.includes("normalizeEdges") && js.includes("rankProcessors") && js.includes("drawMap"));
expect("click processor files the pane", js.includes("fileProcessor") && js.includes("renderStub") && /kind === "processor"[\s\S]*fileProcessor/.test(js));
expect("click company goes to dossier", js.includes('kind === "company"') && js.includes("./c/${encodeURIComponent(n.slug)}.html"));
expect("selected node is 2px teal", js.includes('selected ? teal : ink') && js.includes("selected ? 2 : 1") && js.includes("--ot-evidence-teal"));
expect("no dark canvas or glow", !js.includes("shadowBlur") && !js.includes("#0a0") && !js.includes("#111") && js.includes("#F8FAF9") && !js.includes("autoRotate") && !js.includes("bloom"));
expect("layout settles once", js.includes("layoutNetwork") && js.includes("map.laid") && !js.includes("requestAnimationFrame(tick"));
expect("reduced motion stays still", js.includes("prefers-reduced-motion") && js.includes("Drag still works"));
expect("no rust espresso flame", !js.includes("--rust") && !js.includes("--espresso") && !js.includes("--flame") && !css.includes("--rust") && !css.includes("--espresso"));
expect("tokens stay --ot-", !/#[0-9a-fA-F]{3,8}/.test(toggle.replace(/#map/g, "")) || toggle.includes("--ot-"));

expect("register first screen untouched", index.includes('class="register"') && index.includes("Public trust register") && !index.includes("view-toggle"));
expect("dossier identity untouched", dossier.includes('class="ident"') && dossier.includes("file-line") && !dossier.includes("view-toggle"));
expect("FedRAMP block untouched", dossier.includes("FedRAMP") && dossier.includes("Filed from the"));
