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
expect("empty has no boxes", !empty.includes("file-meter") && !empty.includes('class="on"'));
expect("empty prints 0 of 5", empty.includes("0 of 5"));
expect("empty sentence names the categories", fileCoverage({}).title.includes("checked categories"));

const full = fileCoverageHtml({
  file: { page: true, marks: true, dpa: true, subprocessors: true, years: true },
});
expect("full prints 5 of 5", full.includes("5 of 5"));
expect("full is text not squares", !full.includes("file-meter"));

const mixed = fileCoverage({
  file: { page: true, marks: false, dpa: true, subprocessors: false, years: true },
});
expect("mixed counts three", mixed.n === 3 && mixed.den === "3 of 5");

const src = readFileSync(new URL("../site/register.js", import.meta.url), "utf8");
expect("register does not import fileCoverageHtml", !src.includes("fileCoverageHtml"));
expect("register has no N of 5 markup", !src.includes("file-cov") && !src.includes("file-meter") && !src.includes(" of 5"));
expect("register does not restyle the dossier stamp", !src.includes("disclosure"));
expect("register has no More on this file", !src.includes("More on this file") && !src.includes("record-extra"));

const dossier = readFileSync(new URL("../site/c/anysphere.html", import.meta.url), "utf8");
expect("dossier names Cursor in the h1", /<h1>Cursor<\/h1>/.test(dossier));
expect("dossier file state is the word only", dossier.includes('class="file-state"') && dossier.includes("substantial") && !dossier.includes("tier-label") && !dossier.includes('class="disclosure"'));
expect("dossier has no coverage ratio", !dossier.includes(" of 5") && !dossier.includes("public evidence located"));
expect("dossier marks are a list", dossier.includes('class="mark-list"') && !dossier.includes("mark-chip") && !dossier.includes("+N"));
expect("dossier outbound is a text link", dossier.includes('class="official"') && dossier.includes("View source") && !dossier.includes("go-out") && !dossier.includes("file-go"));
expect("dossier nav does not current Register", !dossier.includes('class="on"'));
expect("dossier body is dossier", dossier.includes('class="dossier"'));
expect("dossier empty rows stay italic not on file", dossier.includes('class="absent">not on file'));
