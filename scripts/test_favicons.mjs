import { existsSync, readFileSync, readdirSync } from "node:fs";
import { inkIcon, nameWithIcon } from "../site/lib.js";
import { marksCell } from "../site/register.js";

function expect(name, cond) {
  if (!cond) {
    console.error("fail", name);
    process.exitCode = 1;
  } else {
    console.log("ok", name);
  }
}

expect("no src prints nothing", inkIcon("") === "" && inkIcon(null) === "");
expect("path traversal is refused", inkIcon("../secret.png") === "" && inkIcon("a/b.png") === "");
expect("real file name emits 12px img", /class="ink-ico"/.test(inkIcon("stripe.com.png")) && /width="12"/.test(inkIcon("stripe.com.png")) && /height="12"/.test(inkIcon("stripe.com.png")));
expect("missing name is name only", nameWithIcon("Stripe", "") === "Stripe");
expect("name follows the icon", nameWithIcon("Stripe", "stripe.com.png").endsWith("Stripe") && nameWithIcon("Stripe", "stripe.com.png").startsWith("<img"));
expect("broken-image handler removes the node", inkIcon("stripe.com.png").includes("onerror=\"this.remove()\""));
expect("icon has empty alt", /alt=""/.test(inkIcon("stripe.com.png")));

const marks = marksCell({
  attestations: [
    { name: "SOC 2 Type II", short: "SOC 2 Type II", id: "soc-2-type-ii" },
    { name: "ISO 27001", short: "ISO 27001", id: "iso-27001" },
  ],
});
expect("marks cell stays words", marks.includes("soc 2 type ii") && marks.includes("iso 27001"));
expect("marks cell is not a chip pile of icons", !marks.includes("ink-ico") && !marks.includes("<img"));

const registerSrc = readFileSync(new URL("../site/register.js", import.meta.url), "utf8");
expect("register names use the icon helper", registerSrc.includes("nameWithIcon(row.name, row.favicon)"));
expect("register file cell has no icon", /displayFileState\(row\.tier\)/.test(registerSrc) && !/inkIcon\(.*tier/.test(registerSrc));
expect("register does not invent a globe", !registerSrc.includes("globe") && !registerSrc.includes("placeholder"));

const graphSrc = readFileSync(new URL("../site/graph.js", import.meta.url), "utf8");
expect("map stub names can take an icon", graphSrc.includes("nameWithIcon(p.name") && graphSrc.includes("nameWithIcon(label"));
expect("processor table stays name-only", /<td class="name">\$\{escapeHtml\(p\.name\)\}<\/td>/.test(graphSrc));

const gazSrc = readFileSync(new URL("../site/gazette.js", import.meta.url), "utf8");
expect("gazette title can take a mark icon", gazSrc.includes("markIco") && gazSrc.includes("inkIcon"));
expect("gazette cited-by stays names", /\$\{escapeHtml\(c\.name\)\}/.test(gazSrc));

const buildSrc = readFileSync(new URL("../build_pages.py", import.meta.url), "utf8");
expect("dossier h1 uses ink_icon", buildSrc.includes("ink_icon") && /<h1>\{ink_icon/.test(buildSrc));
expect("dossier marks still link to attestations", buildSrc.includes("attestations.html#"));
expect("build never invents a seal", !buildSrc.includes("shield") && !buildSrc.includes("checkmark") && !/certificate clipart/i.test(buildSrc));

const css = readFileSync(new URL("../site/styles.css", import.meta.url), "utf8");
expect("icon is 12px ink", /img\.ink-ico \{[\s\S]*width: 12px;[\s\S]*height: 12px;/.test(css));
expect("icon is desaturated", /img\.ink-ico \{[\s\S]*filter: grayscale\(1\) contrast\(1\.15\)/.test(css));
expect("no third palette on the icon", !/ink-ico \{[\s\S]*#[0-9A-Fa-f]{3,8}/.test(css));

const indexHtml = readFileSync(new URL("../site/index.html", import.meta.url), "utf8");
expect("nav has no company icons", !/class="docket"[\s\S]*ink-ico/.test(indexHtml));
expect("file rules are still words", !indexHtml.includes("ink-ico"));

const indexPath = new URL("../site/favicons/index.json", import.meta.url);
if (existsSync(indexPath)) {
  const index = JSON.parse(readFileSync(indexPath, "utf8"));
  const files = readdirSync(new URL("../site/favicons/", import.meta.url)).filter((f) => f.endsWith(".png"));
  const companyHits = Object.keys(index.companies || {});
  expect("a few company icons were vendored", companyHits.length >= 8 && files.length >= 8);
  expect("index only lists files on disk", companyHits.every((d) => files.includes(index.companies[d])));
  expect("no google s2 hotlink", !JSON.stringify(index).includes("google.com/s2"));
} else {
  expect("favicon index is present after fetch", false);
}

if (!process.exitCode) console.log("ok favicons");
