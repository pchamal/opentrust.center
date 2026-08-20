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
expect("register file cell has no icon", /fileIndexHtml\(row\)/.test(registerSrc) && !/inkIcon\(.*tier/.test(registerSrc));
expect("register does not invent a globe", !registerSrc.includes("globe") && !registerSrc.includes("placeholder"));

const graphSrc = readFileSync(new URL("../site/graph.js", import.meta.url), "utf8");
expect("map stub names can take an icon", graphSrc.includes("nameWithIcon(p.name") && graphSrc.includes("nameWithIcon(label"));
expect("processor table stays name-only", /data-label="Processor">\$\{escapeHtml\(p\.name\)\}/.test(graphSrc));
expect("who-named-them drops claroty and zscaler seals", graphSrc.includes('file === "claroty.com.png"') && graphSrc.includes('file === "zscaler.com.png"'));

const gazSrc = readFileSync(new URL("../site/gazette.js", import.meta.url), "utf8");
expect("gazette title can take a mark icon", gazSrc.includes("markIco") && gazSrc.includes("inkIcon"));
expect("gazette cited-by stays names", /\$\{escapeHtml\(c\.name\)\}/.test(gazSrc));
expect("gazette h2 is inside one template", /<h2>\$\{markIco\}\$\{escapeHtml\(item\.name\)\}<\/h2>\s*<p class="entry-meta">/.test(gazSrc));
expect("gazette has no stray h2 backtick", !/<h2>\$\{markIco\}\$\{escapeHtml\(item\.name\)\}<\/h2>`/.test(gazSrc));

const buildSrc = readFileSync(new URL("../build_pages.py", import.meta.url), "utf8");
expect("dossier h1 uses ink_icon", buildSrc.includes("ink_icon") && /<h1>\{ink_icon/.test(buildSrc));
expect("dossier marks still link to attestations", buildSrc.includes("attestations.html#"));
expect("build never invents a seal", !buildSrc.includes("shield") && !buildSrc.includes("checkmark") && !/certificate clipart/i.test(buildSrc));

const css = readFileSync(new URL("../site/styles.css", import.meta.url), "utf8");
expect("icon is 12px ink", /img\.ink-ico \{[\s\S]*width: 12px;[\s\S]*height: 12px;/.test(css));
expect("icon prints as ledger black ink", /img\.ink-ico \{[\s\S]*brightness\(0\) invert\(4%\) sepia\(29%\)/.test(css));
expect("icon is not a grey wash", !/img\.ink-ico \{[\s\S]*filter: grayscale\(1\) contrast\(1\.15\)/.test(css));
expect("name gap is 4px", /td\.name a \{[\s\S]*gap: 4px;/.test(css) && /h1 img\.ink-ico,[\s\S]*margin-right: 4px;/.test(css));
expect("icon does not enlarge on hover", /img\.ink-ico:hover,[\s\S]*transform: none;/.test(css));
expect("no third palette token on the icon", !/--ot-[a-z-]+:/.test((css.match(/img\.ink-ico \{[\s\S]*?\n\}/) || [""])[0]));

const indexHtml = readFileSync(new URL("../site/index.html", import.meta.url), "utf8");
const docket = (indexHtml.match(/<nav class="docket"[\s\S]*?<\/nav>/) || [""])[0];
expect("companies docket is Companies / Subprocessor Map / Standards", /Companies/.test(docket) && /Subprocessor Map/.test(docket) && />Standards</.test(docket));
expect("docket word is Standards, not Frameworks", />Standards</.test(docket) && !/Frameworks/.test(docket));
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
  const markFiles = Object.values(index.marks || {});
  const sealish = [
    "aicpa-cima.com.png",
    "pcisecuritystandards.org.png",
    "fedramp.gov.png",
    "nist.gov.png",
    "hitrustalliance.net.png",
    "cloudsecurityalliance.org.png",
    "ncsc.gov.uk.png",
    "bsi.bund.de.png",
    "cisecurity.org.png",
    "dataprivacyframework.gov.png",
    "ismap.go.jp.png",
  ];
  expect("seal and circled wordmarks are not used as marks", !markFiles.some((f) => sealish.includes(f)));
  const stampMarks = ["cmmc-l1", "cmmc-l2", "k-isms", "mtcs", "tisax"];
  expect("stamp marks are not indexed", stampMarks.every((id) => !(index.marks || {})[id]));
  const password = readFileSync(new URL("../site/c/1password.html", import.meta.url), "utf8");
  expect("tisax is the word", /attestations.html#tisax">TISAX</.test(password) && !/attestations.html#tisax"><img/.test(password));
  const stripe = readFileSync(new URL("../site/c/stripe.html", import.meta.url), "utf8");
  expect("stripe stamp is name only", /<h1>Stripe<\/h1>/.test(stripe));
  expect("stripe framework words stay words", /attestations.html#soc-2-type-ii">SOC 2 Type II</.test(stripe) && !/attestations.html#soc-2-type-ii"><img/.test(stripe));
  const fresh = readFileSync(new URL("../site/c/freshworks.html", import.meta.url), "utf8");
  expect("missing company icon is name only", /<h1>Freshworks<\/h1>/.test(fresh));
  const stamps = ["1password", "1spatial", "abnormal-ai", "abridge", "acronis", "aci-worldwide", "admicom", "a10-networks", "3i-infotech", "adobe"];
  for (const slug of stamps) {
    const html = readFileSync(new URL(`../site/c/${slug}.html`, import.meta.url), "utf8");
    const h1 = (html.match(/<h1>[\s\S]*?<\/h1>/) || [""])[0];
    expect(`${slug} has no stamp icon`, !h1.includes("<img") && !h1.includes("ink-ico"));
  }
  const abridge = readFileSync(new URL("../site/c/abridge.html", import.meta.url), "utf8");
  expect("abridge is not A Abridge", /<h1>Abridge<\/h1>/.test(abridge));
  const keep = [
    ["accenture", "Accenture"],
    ["3d-systems", "3D Systems"],
  ];
  for (const [slug, name] of keep) {
    const html = readFileSync(new URL(`../site/c/${slug}.html`, import.meta.url), "utf8");
    expect(`${slug} keeps a distinctive mark`, new RegExp(`<h1><img class="ink-ico"[^>]*>${name}</h1>`).test(html));
  }
  const eight = readFileSync(new URL("../site/c/8x8.html", import.meta.url), "utf8");
  const abbvie = readFileSync(new URL("../site/c/abbvie.html", import.meta.url), "utf8");
  expect("8x8 stays name only", /<h1>8x8<\/h1>/.test(eight));
  expect("abbvie stays name only", /<h1>AbbVie<\/h1>/.test(abbvie));
} else {
  expect("favicon index is present after fetch", false);
}

if (!process.exitCode) console.log("ok favicons");
