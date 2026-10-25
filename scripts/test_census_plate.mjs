import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileFlags, fileScore } from "../site/lib.js";
import { defaultRows } from "../site/register.js";

function expect(name, cond) {
  if (!cond) {
    console.error("fail", name);
    process.exitCode = 1;
  } else {
    console.log("ok", name);
  }
}

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walk(path, out);
    else if (name.endsWith(".html")) out.push(path);
  }
  return out;
}

const site = new URL("../site/", import.meta.url);
const pages = walk(site.pathname);
const dashed = [];
for (const path of pages) {
  const text = readFileSync(path, "utf8");
  if (text.includes("\u2014") || text.includes("\u2013")) dashed.push(path);
}
expect("no em or en dash in rendered HTML", dashed.length === 0);
if (dashed.length) console.error(dashed.slice(0, 12).join("\n"));

const indexHtml = readFileSync(new URL("../site/index.html", import.meta.url), "utf8");
const companiesHtml = readFileSync(new URL("../site/companies.html", import.meta.url), "utf8");
expect("home H1 text is The AI Trust Index", /<h1>The AI Trust Index<\/h1>/.test(indexHtml));
expect("home title is The AI Trust Index", /<title>The AI Trust Index<\/title>/.test(indexHtml));
expect("register title has no dash", /<title>Public trust register: opentrust\.center<\/title>/.test(companiesHtml));

const data = JSON.parse(readFileSync(new URL("../site/data.json", import.meta.url), "utf8"));
const landing = defaultRows(data.companies);
const first = landing[0];
expect(
  "Register default order starts with 1Password at 100",
  first && first.slug === "1password" && first.name === "1Password" && fileScore(fileFlags(first)) === 100,
);
