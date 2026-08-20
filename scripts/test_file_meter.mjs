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
expect("dossier file is a clerk line", dossier.includes("substantial") && dossier.includes("file-line") && dossier.includes("file-word") && !dossier.includes("file-state") && !dossier.includes("tier-label") && !dossier.includes('class="disclosure"'));
expect("dossier has no rating disclaimer", !dossier.includes("File rating, not a company trust badge") && !dossier.includes("not a company trust badge"));
expect("dossier has no coverage ratio", !dossier.includes(" of 5") && !dossier.includes("public evidence located"));
expect("dossier issue has no register census", !dossier.includes(" on file · ") && !dossier.includes(" not on file · last probed"));
expect("dossier marks are a list", dossier.includes('class="mark-list"') && !dossier.includes("mark-chip") && !dossier.includes("+N"));
expect("dossier outbound is Official page", dossier.includes('class="official"') && dossier.includes("Official page") && !dossier.includes("View source") && !dossier.includes("go-out") && !dossier.includes("file-go"));
expect("dossier nav does not current Register", !dossier.includes('class="on"'));
expect("dossier body is dossier", dossier.includes('class="dossier"'));
expect("dossier empty rows stay italic not on file", dossier.includes('class="absent">not on file'));
expect("dossier FedRAMP cites marketplace, not a badge", dossier.includes("Source") && dossier.includes("FedRAMP Marketplace") && !dossier.includes("Not a badge") && !dossier.includes("not a badge"));
expect("dossier processors missing have no supply-chain apology", !dossier.includes("Not a complete supply chain") && !dossier.includes("not a complete supply chain") && !dossier.includes("Filed from the company’s public list"));
expect("dossier FedRAMP missing is italic not on file", /sec-kicker">FedRAMP[\s\S]*class="absent">not on file/.test(dossier));
expect("dossier processors missing is italic not on file", /sec-kicker">Named processors[\s\S]*class="absent">not on file/.test(dossier));
expect("dossier has no highest-authorized badge line", !dossier.includes("highest authorized"));

const box = readFileSync(new URL("../site/c/box.html", import.meta.url), "utf8");
expect("on-file FedRAMP is a table with marketplace link", box.includes("Source") && box.includes("FedRAMP Marketplace") && box.includes("fedramp.gov/marketplace") && box.includes("<table class=\"inst\">") && !box.includes("Not a badge") && !box.includes("highest authorized") && !box.includes('td class="mark"'));
expect("on-file processors cite the source URL", box.includes("box.com/legal/subprocessors") && !box.includes("Not a complete supply chain") && !box.includes("Filed from the company’s public list"));

const css = readFileSync(new URL("../site/styles.css", import.meta.url), "utf8");
expect("identity block wears the spine", /\.ident \{[\s\S]*border-left: var\(--ot-spine\) solid var\(--ot-evidence-teal\)/.test(css));
expect("no boxed file-state module", !css.includes(".file-state") && !css.includes(".state-word"));
expect("marks stay Atkinson data", /\.mark-list li \{[\s\S]*font: var\(--t-data\)/.test(css) && /\.mark-list li \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
expect("instrument cells stay Atkinson", /\.inst td \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
expect("Official page stays Atkinson", /\.out \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css) && /a\.official \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
expect("Official page stays Atkinson on compact", /\.dossier \.file \.out a\.official \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
