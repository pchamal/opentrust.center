import { readFileSync } from "node:fs";
import { FILE_KEYS, fileCount, fileCoverage, fileIndexHtml } from "../site/lib.js";

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

const empty = fileIndexHtml({});
expect("empty draws five rules", (empty.match(/file-rule/g) || []).length === 5);
expect("empty has no filled rule", !empty.includes("file-rule on"));
expect("empty does not print N of 5", !empty.includes(" of 5") && !empty.includes("0 of 5"));
expect("empty is not a star", !empty.includes("star") && !empty.includes("★") && !empty.includes("☆"));
expect("empty spoken is inconclusive", fileCoverage({}).spoken === "not on file");

const full = fileIndexHtml({
  file: { page: true, marks: true, dpa: true, subprocessors: true, years: true },
});
expect("full fills five rules", (full.match(/file-rule on/g) || []).length === 5);
expect("full does not print N of 5", !full.includes(" of 5") && !full.includes("5 of 5"));
expect("full is not a sixth score", !full.includes("trust maturity") && !full.includes("file · 5"));
expect("full spoken is the instruments", fileCoverage({
  file: { page: true, marks: true, dpa: true, subprocessors: true, years: true },
}).spoken === "page · marks · DPA · subprocessors · years");

const mixedRow = { file: { page: true, marks: false, dpa: true, subprocessors: false, years: true } };
const mixed = fileCoverage(mixedRow);
const mixedHtml = fileIndexHtml(mixedRow);
expect("mixed counts three", mixed.n === 3 && fileCount(mixedRow) === 3);
expect("mixed does not print the count", !mixedHtml.includes("3 of 5") && !mixedHtml.includes("file · 3"));
expect("mixed speaks instruments on file", mixed.spoken === "page · DPA · years");
expect("mixed fills three rules", (mixedHtml.match(/file-rule on/g) || []).length === 3);
expect("mixed keeps two open rules", (mixedHtml.match(/file-rule/g) || []).length - (mixedHtml.match(/file-rule on/g) || []).length === 2);

const src = readFileSync(new URL("../site/register.js", import.meta.url), "utf8");
expect("register draws the file index", src.includes("fileIndexHtml"));
expect("register has no N of 5 markup", !src.includes("file-cov") && !src.includes("file-meter") && !src.includes(" of 5"));
expect("register does not print tier words in the cell", !src.includes("displayFileState") && !src.includes("tierClass"));
expect("register has no stars", !src.includes("★") && !src.includes("☆") && !src.includes("star-rating") && !src.includes("trust maturity"));
expect("register does not restyle the dossier stamp", !src.includes("disclosure"));
expect("register has no More on this file", !src.includes("More on this file") && !src.includes("record-extra"));

const indexHtml = readFileSync(new URL("../site/index.html", import.meta.url), "utf8");
expect(
  "legend is once above the grid",
  indexHtml.includes('id="file-legend"') && indexHtml.includes("page · marks · DPA · subprocessors · years"),
);
expect("legend is not a tooltip farm", !src.includes("title=") || !/file-rule[^>]*title=/.test(src));

const dossier = readFileSync(new URL("../site/c/anysphere.html", import.meta.url), "utf8");
expect("dossier names Cursor in the h1", /<h1>Cursor<\/h1>/.test(dossier));
expect(
  "dossier file is five rules",
  dossier.includes("file-index") && dossier.includes("file-rule on") && !dossier.includes("file-word") && !dossier.includes("file-state") && !dossier.includes("tier-label") && !dossier.includes('class="disclosure"'),
);
expect("dossier has no stars", !dossier.includes("star") && !dossier.includes("★") && !dossier.includes("☆"));
expect("dossier has no trust maturity index", !dossier.includes("trust maturity") && !dossier.includes(" of 5"));
expect("dossier has no rating disclaimer", !dossier.includes("File rating, not a company trust badge") && !dossier.includes("not a company trust badge"));
expect("dossier has no coverage ratio", !dossier.includes(" of 5") && !dossier.includes("public evidence located"));
const issueLine = (dossier.match(/<p class="issue">([^<]+)/) || [])[1] || "";
expect("dossier issue has no register census", !issueLine.includes(" on file · ") && !issueLine.includes(" not on file · last probed"));
expect("dossier marks are a list", dossier.includes('class="mark-list"') && !dossier.includes("mark-chip") && !dossier.includes("+N"));
expect("dossier outbound is Official page", dossier.includes('class="official"') && dossier.includes("Official page") && !dossier.includes("View source") && !dossier.includes("go-out") && !dossier.includes("file-go"));
expect("dossier nav does not current Register", !dossier.includes('class="on"'));
expect("dossier body is dossier", dossier.includes('class="dossier"'));
expect("dossier empty rows stay italic not on file", dossier.includes('class="absent">not on file'));
expect("dossier FedRAMP cites marketplace, not a badge", dossier.includes("Filed from the") && dossier.includes("FedRAMP Marketplace") && !dossier.includes("Not a badge") && !dossier.includes("not a badge") && !dossier.includes("not a score") && !dossier.includes("Not a score"));
expect("anysphere FedRAMP is the Cursor marketplace row", dossier.includes("FR2631054484") && /<a href="https:\/\/www\.fedramp\.gov\/marketplace\/products\/FR2631054484\/?">Cursor<\/a>/.test(dossier) && dossier.includes("not yet certified") && dossier.includes("initial implementation") && dossier.includes("authorizations 0"));
expect("anysphere FedRAMP does not borrow Box words", !dossier.includes("authorized") && !dossier.includes(">High<") && !dossier.includes("25 Mar 2025") && !dossier.includes("Box Enterprise"));
expect("anysphere FedRAMP is not four invented misses", !/<tr><td[^>]*>[\s\S]*not on file[\s\S]*not on file[\s\S]*not on file[\s\S]*not on file/.test(dossier.split('sec-kicker">FedRAMP')[1].split("Named processors")[0]));
const cursorNames = [
  "Amazon Web Services", "Fireworks", "OpenAI", "Anthropic", "Google Gemini",
  "Turbopuffer", "Exa", "Datadog", "Databricks", "Vercel", "Azure", "Baseten",
  "Cloudflare", "Google Cloud Platform", "Together", "SpaceXAI", "WorkOS",
];
const procChunk = dossier.split("Named processors")[1] || "";
expect("anysphere processors are the published list", cursorNames.every((n) => procChunk.includes(n)) && cursorNames.join() === [...procChunk.matchAll(/<tr><td>([^<]+)<\/td><\/tr>/g)].map((m) => m[1]).join());
expect("anysphere processors cite the list", /Filed from[\s\S]*trust\.cursor\.com\/subprocessors/.test(procChunk) && !procChunk.includes("names not extracted") && !/<span class="absent">not on file/.test(procChunk.split("<p class=\"clerk\">")[0]));
expect("anysphere processors are not Box names", !procChunk.includes("GitHub") && !procChunk.includes("New Relic"));
expect("dossier has no highest-authorized badge line", !dossier.includes("highest authorized"));
expect("dossier below-fold tables have no spine class on identity", dossier.includes('class="inst filed"') && dossier.includes('class="ident"'));

const ident = dossier.split('class="ident"')[1].split("</section>")[0];
expect("cursor identity has five rules", (ident.match(/file-rule/g) || []).length === 5);
expect("cursor identity fills the on-file instruments", (ident.match(/file-rule on/g) || []).length === 5);
expect("cursor identity has no tier word", !/silent|thin|substantial|complete/.test(ident) && !ident.includes("file ·"));

const aws = readFileSync(new URL("../site/c/amazon-web-services.html", import.meta.url), "utf8");
const awsIdent = aws.split('class="ident"')[1].split("</section>")[0];
expect("aws identity has five rules", (awsIdent.match(/file-rule/g) || []).length === 5);
expect("aws DPA stays an open rule", (awsIdent.match(/file-rule on/g) || []).length === 4);
expect("aws identity has no complete word", !awsIdent.includes("complete") && !awsIdent.includes("substantial") && !awsIdent.includes("file-word"));

const box = readFileSync(new URL("../site/c/box.html", import.meta.url), "utf8");
expect("on-file FedRAMP is a table with marketplace cite", box.includes("Filed from the") && box.includes("FedRAMP Marketplace") && box.includes("fedramp.gov/marketplace") && box.includes('class="inst filed"') && box.includes("authorized") && !box.includes("Not a badge") && !box.includes("highest authorized") && !box.includes('td class="mark"') && !box.includes("sem-source") && !box.includes("sem-conflict"));
expect("on-file processors are published names", box.includes("GitHub") && box.includes("New Relic") && !box.includes("+N") && !box.includes("Not a complete supply chain") && /sec-kicker">Named processors[\s\S]*Filed from/.test(box));

const css = readFileSync(new URL("../site/styles.css", import.meta.url), "utf8");
expect("identity block wears the spine", /\.ident \{[\s\S]*border-left: var\(--ot-spine\) solid var\(--ot-evidence-teal\)/.test(css));
expect("no boxed file-state module", !css.includes(".file-state") && !css.includes(".state-word"));
expect("rules are ledger black", /\.file-rule \{[\s\S]*border-top: 1px solid var\(--ot-ledger-black\)/.test(css) && /\.file-rule\.on \{[\s\S]*background: var\(--ot-ledger-black\)/.test(css));
expect("teal does not fill the rules", !/\.file-rule[\s\S]{0,80}--ot-evidence-teal/.test(css) && !/\.file-rule\.on[\s\S]{0,80}--ot-evidence-teal/.test(css));
expect("no star styles", !css.includes("★") && !css.includes("☆") && !css.includes("star-rating") && !css.includes("trust-maturity"));
expect("marks stay Atkinson data", /\.mark-list li \{[\s\S]*font: var\(--t-data\)/.test(css) && /\.mark-list li \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
expect("instrument cells stay Atkinson", /\.inst td \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
expect("Official page stays Atkinson", /\.out \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css) && /a\.official \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
expect("Official page stays Atkinson on compact", /\.dossier \.file \.out a\.official \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
expect("filed tables have no second spine", /\.inst\.filed td:first-child \{[\s\S]*border-left: 0/.test(css) && /\.inst\.filed tbody tr:hover td:first-child[\s\S]*border-left: 0/.test(css));
expect("390 hides empty FedRAMP cells", css.includes(".inst.filed td.empty") && css.includes("display: none"));
