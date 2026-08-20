import { readFileSync } from "node:fs";
import { FILE_KEYS, fileCoverage, fileCoverageHtml } from "../site/lib.js";

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

const empty = fileCoverageHtml({});
expect("empty has no boxes", !empty.includes("file-meter") && !empty.includes('class="on"') && !/<span[^>]*title="page"/.test(empty));
expect("empty prints 0 of 5", empty.includes("0 of 5"));
expect("empty sentence names the categories", fileCoverage({}).title.includes("checked categories") && fileCoverage({}).title.includes("page, marks, DPA"));

const full = fileCoverageHtml({
  file: { page: true, marks: true, dpa: true, subprocessors: true, years: true },
});
expect("full prints 5 of 5", full.includes("5 of 5"));
expect("full is text not squares", !full.includes("file-meter") && (full.match(/<span/g) || []).length === 1);

const mixed = fileCoverage({
  file: { page: true, marks: false, dpa: true, subprocessors: false, years: true },
});
expect("mixed counts three", mixed.n === 3 && mixed.den === "3 of 5");
expect("mixed sentence has the denominator", mixed.sentence.includes("3 of 5"));

const src = readFileSync(new URL("../site/register.js", import.meta.url), "utf8");
expect("register imports fileCoverageHtml", src.includes("fileCoverageHtml"));
expect("register puts coverage text in the tier cell", src.includes("fileCoverageHtml(row)"));
expect("register does not restyle the dossier stamp", !src.includes("disclosure"));
expect("register has no file-meter markup", !src.includes("file-meter") && !src.includes("fileMeterHtml"));
