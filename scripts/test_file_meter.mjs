import { readFileSync } from "node:fs";
import { FILE_KEYS, fileMeterHtml } from "../site/lib.js";

function expect(name, cond) {
  if (!cond) {
    console.error("fail", name);
    process.exitCode = 1;
  } else {
    console.log("ok", name);
  }
}

expect("five keys", FILE_KEYS.length === 5);
expect(
  "keys stay page marks dpa subprocessors years",
  FILE_KEYS.join(" ") === "page marks dpa subprocessors years",
);

const empty = fileMeterHtml({});
const emptyBoxes = empty.match(/<span(?: class="on")? title="/g) || [];
expect("empty has five boxes", emptyBoxes.length === 5);
expect("empty has no filled boxes", !empty.includes('class="on"'));
expect("empty says none on file", empty.includes("none on file"));
expect("empty prints 0 of 5", empty.includes("0 of 5"));

const full = fileMeterHtml({
  file: { page: true, marks: true, dpa: true, subprocessors: true, years: true },
});
const filled = (full.match(/class="on"/g) || []).length;
expect("full has five filled boxes", filled === 5);
expect("full prints 5 of 5", full.includes("5 of 5"));
expect("full does not invent a sixth box", (full.match(/<span(?: class="on")? title="/g) || []).length === 5);

const mixed = fileMeterHtml({
  file: { page: true, marks: false, dpa: true, subprocessors: false, years: true },
});
expect("mixed fills three", (mixed.match(/class="on"/g) || []).length === 3);

const src = readFileSync(new URL("../site/register.js", import.meta.url), "utf8");
expect("register imports fileMeterHtml", src.includes("fileMeterHtml"));
expect("register puts the meter in the tier cell", src.includes("fileMeterHtml(row)}${escapeHtml(tier)}"));
expect("register does not restyle the dossier stamp", !src.includes("disclosure"));
