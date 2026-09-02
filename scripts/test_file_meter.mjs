import { readFileSync } from "node:fs";
import { FILE_KEYS, fileCount, fileCoverage, fileFlags, fileIndexHtml, fileScore } from "../site/lib.js";
import { marksCell, registerRowHtml } from "../site/register.js";

const data = JSON.parse(readFileSync(new URL("../site/data.json", import.meta.url), "utf8"));
const bySlug = Object.fromEntries(data.companies.map((r) => [r.slug, r]));

function ruleOn(html) {
  return [...html.matchAll(/class="file-rule(?: (on|partial))?"/g)].map((m) => m[1] === "on");
}

function ruleKind(html) {
  return [...html.matchAll(/class="file-rule(?: (on|partial))?"/g)].map((m) => m[1] || "");
}

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

const fullRow = {
  found: true,
  trust_url: "https://trust.example",
  attestations: [{ name: "SOC 2" }],
  instruments: { dpa: { url: "https://example/dpa" }, subprocessors: { url: "https://example/subs" } },
  processors: [{ name: "Acme" }],
  founded_year: 2012,
};
const full = fileIndexHtml(fullRow);
expect("full fills five rules", (full.match(/file-rule on/g) || []).length === 5);
expect("full does not print N of 5", !full.includes(" of 5") && !full.includes("5 of 5"));
expect("full is not a sixth score", !full.includes("trust maturity") && !full.includes("file · 5"));
expect("full spoken is the instruments", fileCoverage(fullRow).spoken === "page · standards · DPA · subprocessors · years");

const mixedRow = {
  found: true,
  trust_url: "https://trust.example",
  instruments: { dpa: { url: "https://example/dpa" } },
  founded_year: 2010,
};
const mixed = fileCoverage(mixedRow);
const mixedHtml = fileIndexHtml(mixedRow);
expect("mixed counts four", mixed.n === 4 && fileCount(mixedRow) === 4);
expect("mixed does not print the count", !mixedHtml.includes("3 of 5") && !mixedHtml.includes("file · 3"));
expect("mixed speaks instruments on file", mixed.spoken === "page · standards · DPA · years");
expect("mixed fills three prints", (mixedHtml.match(/file-rule on/g) || []).length === 3);
expect("mixed marks is dotted 10", ruleKind(mixedHtml)[1] === "partial" && fileFlags(mixedRow).marks === 10);
expect("mixed binds DPA not a filled marks rule", ruleOn(mixedHtml)[2] === true && ruleOn(mixedHtml)[1] === false);

const staleFilled = {
  found: true,
  trust_url: "https://trust.8x8.com",
  file: { page: true, marks: true, dpa: false, subprocessors: false, years: false },
  disclosure: { factors: { page: 20, marks: 40 } },
  certs: [],
  attestations: [],
};
expect("stale factors.marks do not print marks", fileFlags(staleFilled).marks === 10 && ruleKind(fileIndexHtml(staleFilled))[1] === "partial");
expect("stale file.marks do not fill marks", fileFlags(staleFilled).page === 20 && ruleOn(fileIndexHtml(staleFilled))[0] === true);

const staleEmpty = {
  found: true,
  trust_url: "https://trust.abridge.com",
  file: { page: false, marks: false, dpa: false, subprocessors: false, years: false },
  disclosure: { factors: { marks: 0 } },
  attestations: [{ name: "SOC 2 Type II" }, { name: "HIPAA" }],
};
expect("named marks fill even if file.marks is false", fileFlags(staleEmpty).marks === 20 && ruleOn(fileIndexHtml(staleEmpty))[1] === true);

const eight = bySlug["8x8"];
const eightHtml = fileIndexHtml(eight);
const eightMarks = marksCell(eight);
expect("8x8 page is on file", eight.found && eight.trust_url && fileFlags(eight).page === 20);
expect("8x8 Marks cell lists csa star", /csa star/.test(eightMarks));
expect("8x8 marks rule is filled", fileFlags(eight).marks === 20 && ruleOn(eightHtml)[1] === true);
expect("8x8 subprocessors URL-only is 10", fileFlags(eight).subprocessors === 10 && ruleKind(eightHtml)[3] === "partial");

const abridge = bySlug.abridge;
const abridgeHtml = fileIndexHtml(abridge);
const abridgeMarks = marksCell(abridge);
expect("Abridge Marks cell lists names", /soc 2/.test(abridgeMarks) && abridgeMarks.includes("hipaa") && abridgeMarks.includes("ccpa") && abridgeMarks.includes("tx-ramp"));
expect("Abridge marks rule is filled", fileFlags(abridge).marks === 20 && ruleOn(abridgeHtml)[1] === true);
expect("Abridge is not five open hairlines", ruleOn(abridgeHtml).some(Boolean));
expect("Abridge page stays filled", fileFlags(abridge).page === 20 && ruleOn(abridgeHtml)[0] === true);

const softcat = bySlug.softcat;
expect(
  "softcat portal trust URL is not Official page",
  softcat &&
    softcat.found === false &&
    !softcat.trust_url &&
    ((softcat.instruments || {}).trust || {}).url === "https://trust.softcat.com" &&
    fileFlags(softcat).page === 0 &&
    fileFlags(softcat).marks === 20 &&
    fileFlags(softcat).years === 20 &&
    fileScore(fileFlags(softcat)) === 40,
);

const constella = bySlug["constella-intelligence"];
const constellaHtml = fileIndexHtml(constella);
expect(
  "constella DPA · processors Completeness is 40",
  constella &&
    ((constella.instruments || {}).dpa || {}).url === "https://constella.ai/policies/dpa/" &&
    fileFlags(constella).dpa === 20 &&
    fileFlags(constella).subprocessors === 20 &&
    fileFlags(constella).page === 0 &&
    fileFlags(constella).marks === 0 &&
    fileFlags(constella).years === 0 &&
    fileScore(fileFlags(constella)) === 40 &&
    ruleOn(constellaHtml)[2] === true &&
    ruleOn(constellaHtml)[3] === true,
);
expect("constella Official page stays open", constella && constella.found === false && !constella.trust_url);
expect(
  "constella Exhibit B names AWS and Arsys",
  constella &&
    (constella.processors || []).some((p) => p.slug === "amazon-web-services") &&
    (constella.processors || []).some((p) => p.slug === "arsys") &&
    (constella.processors || []).length === 2,
);

const arsys = bySlug.arsys;
expect(
  "arsys is a domain-only Completeness-0 row on arsys.es",
  arsys &&
    arsys.domain === "arsys.es" &&
    arsys.found === false &&
    !arsys.trust_url &&
    fileScore(fileFlags(arsys)) === 0,
);
expect("arsys is not ionos", arsys && arsys.slug === "arsys" && bySlug.ionos && bySlug.ionos.domain === "ionos.com");

const branch = bySlug["branch-metrics"];
const branchHtml = fileIndexHtml(branch);
expect(
  "branch page · DPA · processors Completeness is 60",
  branch &&
    branch.found === true &&
    branch.trust_url === "https://www.branch.io/security" &&
    ((branch.instruments || {}).dpa || {}).url === "https://legal.branch.io/saas/branch-saas-dpa/" &&
    ((branch.instruments || {}).subprocessors || {}).url === "https://legal.branch.io/saas/subprocessor-list/" &&
    fileFlags(branch).page === 20 &&
    fileFlags(branch).marks === 10 &&
    fileFlags(branch).dpa === 20 &&
    fileFlags(branch).subprocessors === 20 &&
    fileFlags(branch).years === 0 &&
    fileScore(fileFlags(branch)) === 70 &&
    ruleOn(branchHtml)[0] === true &&
    ruleOn(branchHtml)[2] === true &&
    ruleOn(branchHtml)[3] === true,
);
expect("branch Conveyor portal is not Official page", branch && !String(branch.trust_url || "").includes("trust.branch.io"));
expect(
  "branch named processors cross-link existing slugs",
  branch &&
    (branch.processors || []).some((p) => p.slug === "amazon-web-services") &&
    (branch.processors || []).some((p) => p.slug === "zendesk") &&
    (branch.processors || []).some((p) => p.slug === "software-mind") &&
    (branch.processors || []).length === 8,
);
expect("branch marks stay unread", branch && !(branch.certs || []).length);

const cloudAce = bySlug["cloud-ace"];
expect(
  "cloud-ace marks Completeness is 20",
  cloudAce &&
    cloudAce.found === false &&
    !cloudAce.trust_url &&
    (cloudAce.certs || []).includes("ISO 27001") &&
    (cloudAce.certs || []).includes("ISO 9001") &&
    fileFlags(cloudAce).page === 0 &&
    fileFlags(cloudAce).marks === 20 &&
    fileFlags(cloudAce).years === 0 &&
    fileScore(fileFlags(cloudAce)) === 20,
);

const cequens = bySlug["cequens-fze"];
expect(
  "cequens Completeness stays 0",
  cequens &&
    cequens.found === false &&
    !cequens.trust_url &&
    !(cequens.certs || []).length &&
    ((cequens.instruments || {}).privacy || {}).url === "https://www.cequens.com/privacy-policy" &&
    fileFlags(cequens).page === 0 &&
    fileFlags(cequens).marks === 0 &&
    fileFlags(cequens).dpa === 0 &&
    fileFlags(cequens).years === 0 &&
    fileScore(fileFlags(cequens)) === 0,
);

const virtuozzo = bySlug.virtuozzo;
expect(
  "virtuozzo portal is not Official page",
  virtuozzo &&
    virtuozzo.found === false &&
    !virtuozzo.trust_url &&
    !(virtuozzo.certs || []).length &&
    ((virtuozzo.instruments || {}).trust || {}).url === "https://virtuozzo.trust.site" &&
    virtuozzo.founded_year === 1997 &&
    fileFlags(virtuozzo).page === 0 &&
    fileFlags(virtuozzo).marks === 0 &&
    fileFlags(virtuozzo).years === 20 &&
    fileScore(fileFlags(virtuozzo)) === 20,
);

const prowritingaid = bySlug.prowritingaid;
expect(
  "prowritingaid Trust Center Completeness is page · marks = 40",
  prowritingaid &&
    prowritingaid.found === true &&
    prowritingaid.trust_url === "https://prowritingaid.com/trust-center" &&
    (prowritingaid.certs || []).includes("SOC 2") &&
    !(prowritingaid.certs || []).includes("SOC 2 Type II") &&
    fileFlags(prowritingaid).page === 20 &&
    fileFlags(prowritingaid).marks === 20 &&
    fileFlags(prowritingaid).years === 0 &&
    fileScore(fileFlags(prowritingaid)) === 40,
);

const maxmind = bySlug.maxmind;
expect(
  "maxmind security page Completeness is page · marks · years = 60",
  maxmind &&
    maxmind.found === true &&
    maxmind.trust_url === "https://www.maxmind.com/en/company/commitment-to-security" &&
    (maxmind.certs || []).includes("SOC 2 Type II") &&
    (maxmind.certs || []).includes("SOC 3") &&
    (maxmind.certs || []).includes("EU-US DPF") &&
    !(maxmind.certs || []).includes("ISO 27001") &&
    maxmind.founded_year === 2002 &&
    fileFlags(maxmind).page === 20 &&
    fileFlags(maxmind).marks === 20 &&
    fileFlags(maxmind).years === 20 &&
    fileScore(fileFlags(maxmind)) === 60,
);

const ottra = bySlug.ottra;
expect(
  "ottra about-page marks Completeness is 20",
  ottra &&
    ottra.found === false &&
    !ottra.trust_url &&
    (ottra.certs || []).includes("ISO 27001") &&
    (ottra.certs || []).includes("Cyber Essentials") &&
    fileFlags(ottra).page === 0 &&
    fileFlags(ottra).marks === 20 &&
    fileFlags(ottra).years === 0 &&
    fileScore(fileFlags(ottra)) === 20,
);

const releaseteam = bySlug.releaseteam;
expect(
  "releaseteam year Completeness is 20",
  releaseteam &&
    releaseteam.found === false &&
    !releaseteam.trust_url &&
    releaseteam.founded_year === 1999 &&
    fileFlags(releaseteam).page === 0 &&
    fileFlags(releaseteam).marks === 0 &&
    fileFlags(releaseteam).years === 20 &&
    fileScore(fileFlags(releaseteam)) === 20,
);

const routeMobile = bySlug["route-mobile"];
expect(
  "route-mobile DPA Completeness is 20",
  routeMobile &&
    routeMobile.found === false &&
    !routeMobile.trust_url &&
    !(routeMobile.certs || []).length &&
    ((routeMobile.instruments || {}).dpa || {}).url === "https://routemobile.com/dpa/" &&
    fileFlags(routeMobile).page === 0 &&
    fileFlags(routeMobile).marks === 0 &&
    fileFlags(routeMobile).dpa === 20 &&
    fileScore(fileFlags(routeMobile)) === 20,
);

const filestack = bySlug.filestack;
expect(
  "filestack /features is not Official page",
  filestack &&
    filestack.found === false &&
    !filestack.trust_url &&
    fileFlags(filestack).page === 0 &&
    fileScore(fileFlags(filestack)) === 0,
);

const horizoniq = bySlug.horizoniq;
expect(
  "horizoniq compliance Completeness is page · marks = 40",
  horizoniq &&
    horizoniq.found === true &&
    horizoniq.trust_url === "https://www.horizoniq.com/compliance/" &&
    (horizoniq.certs || []).includes("SOC 2 Type II") &&
    (horizoniq.certs || []).includes("ISO 27001") &&
    (horizoniq.certs || []).includes("PCI DSS") &&
    !(horizoniq.certs || []).includes("HIPAA") &&
    !horizoniq.founded_year &&
    fileFlags(horizoniq).page === 20 &&
    fileFlags(horizoniq).marks === 20 &&
    fileFlags(horizoniq).years === 0 &&
    fileScore(fileFlags(horizoniq)) === 40,
);

const hive = bySlug.hive;
expect(
  "hive security policy Completeness is page · marks · years = 60",
  hive &&
    hive.found === true &&
    hive.trust_url === "https://hive.com/policy-documents/security" &&
    (hive.certs || []).includes("SOC 2") &&
    !(hive.certs || []).includes("SOC 2 Type II") &&
    !(hive.certs || []).includes("ISO 27001") &&
    (hive.certs || []).includes("EU-US DPF") &&
    hive.founded_year === 2016 &&
    fileFlags(hive).page === 20 &&
    fileFlags(hive).marks === 20 &&
    fileFlags(hive).years === 20 &&
    fileScore(fileFlags(hive)) === 60,
);

const datamotion = bySlug.datamotion;
expect(
  "datamotion company-overview Completeness is marks · years = 40",
  datamotion &&
    datamotion.found === false &&
    !datamotion.trust_url &&
    (datamotion.certs || []).includes("HITRUST") &&
    !(datamotion.certs || []).includes("FedRAMP") &&
    !(datamotion.certs || []).includes("HIPAA") &&
    datamotion.founded_year === 1999 &&
    fileFlags(datamotion).page === 0 &&
    fileFlags(datamotion).marks === 20 &&
    fileFlags(datamotion).years === 20 &&
    fileScore(fileFlags(datamotion)) === 40,
);

const appcues = bySlug.appcues;
expect(
  "appcues Completeness is page · marks · DPA · subprocessors = 70",
  appcues &&
    appcues.found === true &&
    appcues.trust_url === "https://trust.appcues.com" &&
    (appcues.certs || []).includes("SOC 2 Type II") &&
    (appcues.certs || []).includes("EU-US DPF") &&
    !appcues.founded_year &&
    fileFlags(appcues).page === 20 &&
    fileFlags(appcues).marks === 20 &&
    fileFlags(appcues).dpa === 20 &&
    fileFlags(appcues).subprocessors === 10 &&
    fileFlags(appcues).years === 0 &&
    fileScore(fileFlags(appcues)) === 70,
);

const rollbar = bySlug.rollbar;
expect(
  "rollbar Completeness is page · marks · DPA = 60",
  rollbar &&
    rollbar.found === true &&
    rollbar.trust_url === "https://rollbar.com/security" &&
    (rollbar.certs || []).includes("SOC 2 Type II") &&
    (rollbar.certs || []).includes("SOC 3") &&
    !(rollbar.certs || []).includes("ISO 27001") &&
    !(rollbar.certs || []).includes("HIPAA") &&
    fileFlags(rollbar).page === 20 &&
    fileFlags(rollbar).marks === 20 &&
    fileFlags(rollbar).dpa === 20 &&
    fileFlags(rollbar).years === 0 &&
    fileScore(fileFlags(rollbar)) === 60,
);

const liveblocks = bySlug.liveblocks;
expect(
  "liveblocks Completeness is page · marks · DPA · subprocessors = 70",
  liveblocks &&
    liveblocks.found === true &&
    liveblocks.trust_url === "https://liveblocks.secureframetrust.com" &&
    (liveblocks.certs || []).includes("SOC 2 Type II") &&
    !(liveblocks.certs || []).includes("HIPAA") &&
    fileFlags(liveblocks).page === 20 &&
    fileFlags(liveblocks).marks === 20 &&
    fileFlags(liveblocks).dpa === 20 &&
    fileFlags(liveblocks).subprocessors === 10 &&
    fileFlags(liveblocks).years === 0 &&
    fileScore(fileFlags(liveblocks)) === 70,
);

const messagebird = bySlug.messagebird;
expect(
  "messagebird Completeness is page · marks · DPA · years = 80",
  messagebird &&
    messagebird.found === true &&
    messagebird.trust_url === "https://messagebird.com/trust" &&
    (messagebird.certs || []).includes("ISO 27001") &&
    (messagebird.certs || []).includes("EU-US DPF") &&
    messagebird.founded_year === 2011 &&
    fileFlags(messagebird).page === 20 &&
    fileFlags(messagebird).marks === 20 &&
    fileFlags(messagebird).dpa === 20 &&
    fileFlags(messagebird).years === 20 &&
    fileScore(fileFlags(messagebird)) === 80,
);

const qualified = bySlug["qualified-com"];
expect(
  "qualified Completeness is page · marks · DPA · subprocessors = 70",
  qualified &&
    qualified.found === true &&
    qualified.trust_url === "https://trust.qualified.com" &&
    (qualified.certs || []).includes("SOC 2 Type II") &&
    !(qualified.certs || []).includes("HIPAA") &&
    !qualified.founded_year &&
    fileFlags(qualified).page === 20 &&
    fileFlags(qualified).marks === 20 &&
    fileFlags(qualified).dpa === 20 &&
    fileFlags(qualified).subprocessors === 10 &&
    fileFlags(qualified).years === 0 &&
    fileScore(fileFlags(qualified)) === 70,
);

const openrouter = bySlug.openrouter;
expect(
  "openrouter Completeness is page · DPA (marks open)",
  openrouter &&
    openrouter.found === true &&
    openrouter.trust_url === "https://openrouter.ai/security" &&
    !(openrouter.certs || []).includes("SOC 2 Type II") &&
    !(openrouter.certs || []).length &&
    !openrouter.founded_year &&
    fileFlags(openrouter).page === 20 &&
    fileFlags(openrouter).marks === 10 &&
    fileFlags(openrouter).dpa === 20 &&
    fileFlags(openrouter).subprocessors === 0 &&
    fileFlags(openrouter).years === 0 &&
    fileScore(fileFlags(openrouter)) === 50,
);

const apollo = bySlug["apollo-io"];
expect(
  "apollo Completeness is page · marks · DPA = 60",
  apollo &&
    apollo.found === true &&
    apollo.trust_url === "https://trust.apollo.io" &&
    (apollo.certs || []).includes("EU-US DPF") &&
    !(apollo.certs || []).includes("SOC 2 Type II") &&
    !apollo.founded_year &&
    fileFlags(apollo).page === 20 &&
    fileFlags(apollo).marks === 20 &&
    fileFlags(apollo).dpa === 20 &&
    fileFlags(apollo).years === 0 &&
    fileScore(fileFlags(apollo)) === 60,
);

const maestroqa = bySlug.maestroqa;
expect(
  "maestroqa Completeness is page · marks · years = 60",
  maestroqa &&
    maestroqa.found === true &&
    maestroqa.trust_url === "https://trust.maestroqa.com" &&
    (maestroqa.certs || []).includes("EU-US DPF") &&
    maestroqa.founded_year === 2013 &&
    fileFlags(maestroqa).page === 20 &&
    fileFlags(maestroqa).marks === 20 &&
    fileFlags(maestroqa).years === 20 &&
    fileScore(fileFlags(maestroqa)) === 60,
);

const validity = bySlug.validity;
expect(
  "validity Completeness is page · marks · subprocessors = 60",
  validity &&
    validity.found === true &&
    validity.trust_url === "https://trust.validity.com" &&
    (validity.certs || []).includes("EU-US DPF") &&
    !validity.founded_year &&
    fileFlags(validity).page === 20 &&
    fileFlags(validity).marks === 20 &&
    fileFlags(validity).subprocessors === 20 &&
    fileFlags(validity).years === 0 &&
    fileScore(fileFlags(validity)) === 60,
);

const onesignal = bySlug.onesignal;
expect(
  "onesignal Completeness is marks · DPA · subprocessors = 60",
  onesignal &&
    onesignal.found === false &&
    !onesignal.trust_url &&
    (onesignal.certs || []).includes("SOC 2 Type II") &&
    (onesignal.certs || []).includes("ISO 27001") &&
    (onesignal.certs || []).includes("ISO 27701") &&
    !(onesignal.certs || []).includes("HIPAA") &&
    ((onesignal.instruments || {}).dpa || {}).url === "https://onesignal.com/dpa" &&
    ((onesignal.instruments || {}).subprocessors || {}).url === "https://onesignal.com/list-of-subprocessors" &&
    !onesignal.founded_year &&
    fileFlags(onesignal).page === 0 &&
    fileFlags(onesignal).marks === 20 &&
    fileFlags(onesignal).dpa === 20 &&
    fileFlags(onesignal).subprocessors === 20 &&
    fileFlags(onesignal).years === 0 &&
    fileScore(fileFlags(onesignal)) === 60,
);

const authzed = bySlug.authzed;
expect(
  "authzed Completeness is page only (marks open)",
  authzed &&
    authzed.found === true &&
    authzed.trust_url === "https://security.authzed.com" &&
    !(authzed.certs || []).length &&
    !(authzed.certs || []).includes("SOC 2") &&
    !(authzed.certs || []).includes("GDPR") &&
    !(authzed.certs || []).includes("CCPA") &&
    !authzed.founded_year &&
    fileFlags(authzed).page === 20 &&
    fileFlags(authzed).marks === 10 &&
    fileFlags(authzed).dpa === 0 &&
    fileFlags(authzed).subprocessors === 0 &&
    fileFlags(authzed).years === 0 &&
    fileScore(fileFlags(authzed)) === 30,
);

const linkedin = bySlug.linkedin;
expect(
  "linkedin Completeness is page · marks · DPA · subprocessors = 80",
  linkedin &&
    linkedin.found === true &&
    linkedin.trust_url === "https://security.linkedin.com/trust-and-compliance" &&
    ((linkedin.instruments || {}).dpa || {}).url === "https://www.linkedin.com/legal/l/dpa" &&
    ((linkedin.instruments || {}).subprocessors || {}).url ===
      "https://www.linkedin.com/legal/l/customer-subprocessors" &&
    (linkedin.processors || []).length === 34 &&
    (linkedin.processors || []).some((p) => p.slug === "microsoft") &&
    (linkedin.processors || []).some((p) => p.slug === "messagebird") &&
    (linkedin.processors || []).some((p) => p.slug === "surveymonkey") &&
    (linkedin.processors || []).some((p) => p.slug === "tdcx") &&
    !(linkedin.processors || []).some((p) => p.name === "Talent/Hire") &&
    !linkedin.founded_year &&
    fileFlags(linkedin).page === 20 &&
    fileFlags(linkedin).marks === 20 &&
    fileFlags(linkedin).dpa === 20 &&
    fileFlags(linkedin).subprocessors === 20 &&
    fileFlags(linkedin).years === 0 &&
    fileScore(fileFlags(linkedin)) === 80,
);

const teleport = bySlug.teleport;
expect(
  "teleport Completeness is page · marks · DPA · years = 80",
  teleport &&
    teleport.found === true &&
    teleport.trust_url === "https://goteleport.com/security/" &&
    ((teleport.instruments || {}).dpa || {}).url === "https://goteleport.com/legal/dpa/" &&
    !((teleport.instruments || {}).subprocessors || {}).url &&
    (teleport.certs || []).includes("SOC 2 Type II") &&
    (teleport.certs || []).includes("ISO 27001") &&
    (teleport.certs || []).includes("HIPAA") &&
    !(teleport.certs || []).includes("ISO 27701") &&
    !(teleport.certs || []).includes("PCI DSS") &&
    teleport.founded_year === 2015 &&
    teleport.founded_source === "https://goteleport.com/about" &&
    fileFlags(teleport).page === 20 &&
    fileFlags(teleport).marks === 20 &&
    fileFlags(teleport).dpa === 20 &&
    fileFlags(teleport).subprocessors === 0 &&
    fileFlags(teleport).years === 20 &&
    fileScore(fileFlags(teleport)) === 80,
);

const ketch = bySlug.ketch;
expect(
  "ketch Completeness is marks · DPA · years = 60",
  ketch &&
    ketch.found === false &&
    !ketch.trust_url &&
    ((ketch.instruments || {}).dpa || {}).url === "https://www.ketch.com/data-processing-addendum" &&
    !((ketch.instruments || {}).subprocessors || {}).url &&
    (ketch.certs || []).includes("SOC 2 Type II") &&
    (ketch.certs || []).includes("ISO 27001") &&
    ketch.founded_year === 2020 &&
    ketch.founded_source === "https://www.ketch.com/about" &&
    fileFlags(ketch).page === 0 &&
    fileFlags(ketch).marks === 20 &&
    fileFlags(ketch).dpa === 20 &&
    fileFlags(ketch).subprocessors === 0 &&
    fileFlags(ketch).years === 20 &&
    fileScore(fileFlags(ketch)) === 60,
);

const inkeep = bySlug.inkeep;
expect(
  "inkeep Completeness is page · marks · years = 60",
  inkeep &&
    inkeep.found === true &&
    inkeep.trust_url === "https://inkeep.com/security" &&
    !((inkeep.instruments || {}).dpa || {}).url &&
    !((inkeep.instruments || {}).subprocessors || {}).url &&
    (inkeep.certs || []).includes("SOC 2 Type II") &&
    inkeep.founded_year === 2023 &&
    inkeep.founded_source === "https://inkeep.com/about" &&
    fileFlags(inkeep).page === 20 &&
    fileFlags(inkeep).marks === 20 &&
    fileFlags(inkeep).dpa === 0 &&
    fileFlags(inkeep).subprocessors === 0 &&
    fileFlags(inkeep).years === 20 &&
    fileScore(fileFlags(inkeep)) === 60,
);

const spekit = bySlug.spekit;
expect(
  "spekit Completeness is DPA · years = 40",
  spekit &&
    spekit.found === false &&
    !spekit.trust_url &&
    ((spekit.instruments || {}).dpa || {}).url === "https://www.spekit.com/legal/dpa" &&
    !((spekit.instruments || {}).subprocessors || {}).url &&
    !(spekit.certs || []).length &&
    spekit.founded_year === 2018 &&
    spekit.founded_source === "https://www.spekit.com/about-us" &&
    fileFlags(spekit).page === 0 &&
    fileFlags(spekit).marks === 0 &&
    fileFlags(spekit).dpa === 20 &&
    fileFlags(spekit).subprocessors === 0 &&
    fileFlags(spekit).years === 20 &&
    fileScore(fileFlags(spekit)) === 40,
);

const cyberhaven = bySlug.cyberhaven;
expect(
  "cyberhaven Completeness is years = 20",
  cyberhaven &&
    cyberhaven.found === false &&
    !cyberhaven.trust_url &&
    cyberhaven.founded_year === 2016 &&
    cyberhaven.founded_source === "https://www.cyberhaven.com/about" &&
    fileFlags(cyberhaven).page === 0 &&
    fileFlags(cyberhaven).marks === 0 &&
    fileFlags(cyberhaven).dpa === 0 &&
    fileFlags(cyberhaven).years === 20 &&
    fileScore(fileFlags(cyberhaven)) === 20,
);

const woopra = bySlug.woopra;
expect(
  "woopra Completeness is years = 20",
  woopra &&
    woopra.found === false &&
    !woopra.trust_url &&
    woopra.founded_year === 2012 &&
    woopra.founded_source === "https://www.woopra.com/company/about" &&
    fileFlags(woopra).page === 0 &&
    fileFlags(woopra).marks === 0 &&
    fileFlags(woopra).years === 20 &&
    fileScore(fileFlags(woopra)) === 20,
);

const accesspay = bySlug["access-systems-uk-accesspay"];
expect(
  "accesspay Completeness is years = 20",
  accesspay &&
    accesspay.found === false &&
    !accesspay.trust_url &&
    accesspay.founded_year === 2012 &&
    accesspay.founded_source === "https://accesspay.com/about" &&
    fileFlags(accesspay).page === 0 &&
    fileFlags(accesspay).marks === 0 &&
    fileFlags(accesspay).dpa === 0 &&
    fileFlags(accesspay).years === 20 &&
    fileScore(fileFlags(accesspay)) === 20,
);

const xrd = bySlug["x-rd"];
expect(
  "x-rd Completeness is years = 20",
  xrd &&
    xrd.found === false &&
    !xrd.trust_url &&
    xrd.founded_year === 2019 &&
    xrd.founded_source === "https://www.x-rd.com.au/about-us" &&
    fileFlags(xrd).page === 0 &&
    fileFlags(xrd).marks === 0 &&
    fileFlags(xrd).years === 20 &&
    fileScore(fileFlags(xrd)) === 20,
);

const invoka = bySlug["invoka-consulting"];
expect(
  "invoka Completeness is years = 20",
  invoka &&
    invoka.found === false &&
    !invoka.trust_url &&
    invoka.founded_year === 2022 &&
    invoka.founded_source === "https://invokaconsulting.com/about" &&
    fileFlags(invoka).page === 0 &&
    fileFlags(invoka).marks === 0 &&
    fileFlags(invoka).years === 20 &&
    fileScore(fileFlags(invoka)) === 20,
);

const primeConsulting = bySlug["prime-consulting-group-solutions"];
expect(
  "prime-consulting Completeness is years = 20",
  primeConsulting &&
    primeConsulting.found === false &&
    !primeConsulting.trust_url &&
    primeConsulting.founded_year === 2022 &&
    primeConsulting.founded_source === "https://primeconsulting.com/about-us" &&
    fileFlags(primeConsulting).page === 0 &&
    fileFlags(primeConsulting).marks === 0 &&
    fileFlags(primeConsulting).years === 20 &&
    fileScore(fileFlags(primeConsulting)) === 20,
);

const carahsoft = bySlug["carahsoft-technology"];
expect(
  "carahsoft Completeness is years = 20",
  carahsoft &&
    carahsoft.found === false &&
    !carahsoft.trust_url &&
    carahsoft.founded_year === 2004 &&
    carahsoft.founded_source === "https://www.carahsoft.com/about" &&
    fileFlags(carahsoft).page === 0 &&
    fileFlags(carahsoft).marks === 0 &&
    fileFlags(carahsoft).years === 20 &&
    fileScore(fileFlags(carahsoft)) === 20,
);

const tropic = bySlug.tropic;
expect(
  "tropic Completeness is subprocessors = 20",
  tropic &&
    tropic.found === false &&
    !tropic.trust_url &&
    ((tropic.instruments || {}).subprocessors || {}).url ===
      "https://www.tropicapp.io/legal/subprocessors" &&
    (tropic.processors || []).length === 16 &&
    (tropic.processors || []).some((p) => p.slug === "amazon-web-services") &&
    (tropic.processors || []).some((p) => p.slug === "google") &&
    (tropic.processors || []).some((p) => p.slug === "omni-analytics" && p.name === "Omni") &&
    !tropic.founded_year &&
    fileFlags(tropic).page === 0 &&
    fileFlags(tropic).marks === 0 &&
    fileFlags(tropic).dpa === 0 &&
    fileFlags(tropic).subprocessors === 20 &&
    fileFlags(tropic).years === 0 &&
    fileScore(fileFlags(tropic)) === 20,
);

const adish = bySlug.adish;
expect(
  "adish Completeness is years = 20",
  adish &&
    adish.found === false &&
    !adish.trust_url &&
    adish.founded_year === 2014 &&
    adish.founded_source === "https://adish.biz/about/overview" &&
    fileFlags(adish).page === 0 &&
    fileFlags(adish).marks === 0 &&
    fileFlags(adish).dpa === 0 &&
    fileFlags(adish).subprocessors === 0 &&
    fileFlags(adish).years === 20 &&
    fileScore(fileFlags(adish)) === 20,
);

const datamato = bySlug["datamato-technologies-private"];
expect(
  "datamato Completeness is years = 20",
  datamato &&
    datamato.found === false &&
    !datamato.trust_url &&
    datamato.founded_year === 2012 &&
    datamato.founded_source === "https://datamato.com/about/overview" &&
    fileFlags(datamato).page === 0 &&
    fileFlags(datamato).marks === 0 &&
    fileFlags(datamato).dpa === 0 &&
    fileFlags(datamato).subprocessors === 0 &&
    fileFlags(datamato).years === 20 &&
    fileScore(fileFlags(datamato)) === 20,
);

const kickbox = bySlug.kickbox;
expect(
  "kickbox Completeness is subprocessors = 20",
  kickbox &&
    kickbox.found === false &&
    !kickbox.trust_url &&
    ((kickbox.instruments || {}).subprocessors || {}).url ===
      "https://docs.kickbox.com/docs/subprocessors" &&
    (kickbox.processors || []).some((p) => p.slug === "stripe" && p.name === "Stripe") &&
    (kickbox.processors || []).some((p) => p.slug === "sift" && p.name === "Sift Science") &&
    (kickbox.processors || []).some((p) => p.slug === "amazon-web-services" && p.name === "Amazon AWS") &&
    !(kickbox.processors || []).some((p) => p.id === "sift-science") &&
    !(kickbox.certs || []).length &&
    !kickbox.founded_year &&
    fileFlags(kickbox).page === 0 &&
    fileFlags(kickbox).marks === 0 &&
    fileFlags(kickbox).dpa === 0 &&
    fileFlags(kickbox).subprocessors === 20 &&
    fileFlags(kickbox).years === 0 &&
    fileScore(fileFlags(kickbox)) === 20,
);

const rootly = bySlug.rootly;
expect(
  "rootly Completeness is subprocessors = 20",
  rootly &&
    rootly.found === false &&
    !rootly.trust_url &&
    ((rootly.instruments || {}).subprocessors || {}).url ===
      "https://docs.rootly.com/configuration/subprocessors" &&
    (rootly.processors || []).some((p) => p.slug === "amazon-web-services" && p.name === "Amazon Web Services") &&
    (rootly.processors || []).some((p) => p.slug === "mailgun" && p.name === "Mailgun (Sinch AB)") &&
    (rootly.processors || []).some((p) => p.slug === "google" && p.name === "Firebase Cloud Messaging") &&
    (rootly.processors || []).some((p) => p.slug === "quotaguard" && p.name === "QuotaGuard") &&
    !(rootly.processors || []).some((p) => p.id === "mailgun-sinch") &&
    !(rootly.processors || []).some((p) => p.id === "aws") &&
    !(rootly.certs || []).length &&
    !rootly.founded_year &&
    fileFlags(rootly).page === 0 &&
    fileFlags(rootly).marks === 0 &&
    fileFlags(rootly).dpa === 0 &&
    fileFlags(rootly).subprocessors === 20 &&
    fileFlags(rootly).years === 0 &&
    fileScore(fileFlags(rootly)) === 20,
);

const quotaguard = bySlug.quotaguard;
expect(
  "quotaguard Completeness is years = 20",
  quotaguard &&
    quotaguard.found === false &&
    !quotaguard.trust_url &&
    quotaguard.domain === "quotaguard.com" &&
    quotaguard.founded_year === 2013 &&
    quotaguard.founded_source === "https://www.quotaguard.com/about" &&
    fileFlags(quotaguard).page === 0 &&
    fileFlags(quotaguard).marks === 0 &&
    fileFlags(quotaguard).dpa === 0 &&
    fileFlags(quotaguard).subprocessors === 0 &&
    fileFlags(quotaguard).years === 20 &&
    fileScore(fileFlags(quotaguard)) === 20,
);

const pushy = bySlug.pushy;
expect(
  "pushy Completeness is DPA = 20",
  pushy &&
    pushy.found === false &&
    !pushy.trust_url &&
    ((pushy.instruments || {}).dpa || {}).url ===
      "https://pushy.me/data-processing-addendum" &&
    !(pushy.certs || []).length &&
    !pushy.founded_year &&
    fileFlags(pushy).page === 0 &&
    fileFlags(pushy).marks === 0 &&
    fileFlags(pushy).dpa === 20 &&
    fileFlags(pushy).subprocessors === 0 &&
    fileFlags(pushy).years === 0 &&
    fileScore(fileFlags(pushy)) === 20,
);

const pganalyze = bySlug["pganalyze-duboce-labs"];
expect(
  "pganalyze Completeness is page = 20 (marks dotted)",
  pganalyze &&
    pganalyze.found === true &&
    pganalyze.trust_url === "https://pganalyze.com/security" &&
    !(pganalyze.certs || []).length &&
    !pganalyze.founded_year &&
    fileFlags(pganalyze).page === 20 &&
    fileFlags(pganalyze).marks === 10 &&
    fileFlags(pganalyze).dpa === 0 &&
    fileFlags(pganalyze).subprocessors === 0 &&
    fileFlags(pganalyze).years === 0 &&
    fileScore(fileFlags(pganalyze)) === 30,
);

const shortIo = bySlug["short-io"];
expect(
  "short-io Completeness is subprocessors = 20",
  shortIo &&
    shortIo.found === false &&
    !shortIo.trust_url &&
    ((shortIo.instruments || {}).subprocessors || {}).url ===
      "https://short.io/privacy" &&
    (shortIo.processors || []).some((p) => p.slug === "amazon-web-services" && p.name === "Amazon Web Services") &&
    (shortIo.processors || []).some((p) => p.slug === "google" && p.name === "Google (Sign-In)") &&
    (shortIo.processors || []).some((p) => p.slug === "google" && p.name === "Google Ads") &&
    (shortIo.processors || []).some((p) => p.slug === "hivelocity" && p.name === "Hivelocity") &&
    (shortIo.processors || []).some((p) => p.slug === "telegram" && p.name === "Telegram") &&
    (shortIo.processors || []).some((p) => p.slug === "surbl" && p.name === "SURBL") &&
    (shortIo.processors || []).some((p) => p.slug === "let-s-encrypt" && p.name === "Let's Encrypt") &&
    !(shortIo.processors || []).some((p) => p.id === "aws") &&
    !(shortIo.processors || []).some((p) => p.id === "google-sign-in") &&
    !(shortIo.certs || []).length &&
    !shortIo.founded_year &&
    fileFlags(shortIo).page === 0 &&
    fileFlags(shortIo).marks === 0 &&
    fileFlags(shortIo).dpa === 0 &&
    fileFlags(shortIo).subprocessors === 20 &&
    fileFlags(shortIo).years === 0 &&
    fileScore(fileFlags(shortIo)) === 20,
);

const clari = bySlug.clari;
expect(
  "clari Completeness is page · marks · DPA = 60",
  clari &&
    clari.found === true &&
    clari.trust_url === "https://www.clari.com/security/" &&
    ((clari.instruments || {}).dpa || {}).url === "https://www.clari.com/dpa/2026-02-10/" &&
    !(clari.processors || []).length &&
    !clari.founded_year &&
    fileFlags(clari).page === 20 &&
    fileFlags(clari).marks === 20 &&
    fileFlags(clari).dpa === 20 &&
    fileFlags(clari).subprocessors === 0 &&
    fileFlags(clari).years === 0 &&
    fileScore(fileFlags(clari)) === 60,
);

const livekit = bySlug.livekit;
expect(
  "livekit Completeness is page · marks · DPA · subprocessors = 80",
  livekit &&
    livekit.found === true &&
    livekit.trust_url === "https://livekit.com/security" &&
    ((livekit.instruments || {}).dpa || {}).url ===
      "https://livekit.com/legal/data-processing-addendum" &&
    ((livekit.instruments || {}).subprocessors || {}).url ===
      "https://livekit.com/legal/sub-processors" &&
    (livekit.processors || []).length === 30 &&
    (livekit.processors || []).some((p) => p.id === "spacexai" && !p.slug && p.name === "SpaceXAI") &&
    (livekit.processors || []).some((p) => p.slug === "cockroach-labs" && p.name === "Cockroach Labs") &&
    !livekit.founded_year &&
    fileFlags(livekit).page === 20 &&
    fileFlags(livekit).marks === 20 &&
    fileFlags(livekit).dpa === 20 &&
    fileFlags(livekit).subprocessors === 20 &&
    fileFlags(livekit).years === 0 &&
    fileScore(fileFlags(livekit)) === 80,
);

const retool = bySlug.retool;
expect(
  "retool Completeness is page · DPA · subprocessors · years = 90",
  retool &&
    retool.found === true &&
    ((retool.instruments || {}).dpa || {}).url === "https://docs.retool.com/legal/dpa" &&
    ((retool.instruments || {}).subprocessors || {}).url ===
      "https://docs.retool.com/legal/subprocessors" &&
    retool.founded_year === 2017 &&
    retool.founded_source === "https://retool.com/about" &&
    (retool.processors || []).some((p) => p.slug === "amazon-web-services") &&
    (retool.processors || []).some((p) => p.slug === "neon" && p.name === "Neon, Inc") &&
    !(retool.processors || []).some((p) => p.slug === "databricks" && p.name === "Neon, Inc") &&
    !(retool.processors || []).some((p) => p.id === "aws") &&
    !(retool.certs || []).length &&
    fileFlags(retool).page === 20 &&
    fileFlags(retool).marks === 10 &&
    fileFlags(retool).dpa === 20 &&
    fileFlags(retool).subprocessors === 20 &&
    fileFlags(retool).years === 20 &&
    fileScore(fileFlags(retool)) === 90,
);

const rocketlane = bySlug.rocketlane;
expect(
  "rocketlane Completeness is page · DPA · subprocessors · years = 90",
  rocketlane &&
    rocketlane.found === true &&
    ((rocketlane.instruments || {}).dpa || {}).url ===
      "https://www.rocketlane.com/legal/data-processing-agreement" &&
    ((rocketlane.instruments || {}).subprocessors || {}).url ===
      "https://www.rocketlane.com/legal/sub-processors" &&
    rocketlane.founded_year === 2020 &&
    rocketlane.founded_source === "https://www.rocketlane.com/privacy-policy" &&
    (rocketlane.processors || []).some((p) => p.slug === "twilio" && p.name === "SendGrid / Twilio") &&
    (rocketlane.processors || []).some((p) => p.slug === "langchain" && p.name === "Langsmith") &&
    (rocketlane.processors || []).some((p) => p.slug === "weaviate" && p.name === "Weaviate") &&
    (rocketlane.processors || []).some((p) => p.slug === "scalekit" && p.name === "Scalekit") &&
    !(rocketlane.processors || []).some((p) => p.id === "aws") &&
    !(rocketlane.certs || []).length &&
    fileFlags(rocketlane).page === 20 &&
    fileFlags(rocketlane).marks === 10 &&
    fileFlags(rocketlane).dpa === 20 &&
    fileFlags(rocketlane).subprocessors === 20 &&
    fileFlags(rocketlane).years === 20 &&
    fileScore(fileFlags(rocketlane)) === 90,
);

const cockroachLabs = bySlug["cockroach-labs"];
expect(
  "cockroach-labs Completeness is page · marks · DPA · subprocessors = 80",
  cockroachLabs &&
    cockroachLabs.found === true &&
    cockroachLabs.domain === "cockroachlabs.com" &&
    cockroachLabs.trust_url === "https://cockroachlabs.com/trust-center" &&
    ((cockroachLabs.instruments || {}).dpa || {}).url ===
      "https://www.cockroachlabs.com/cloud-terms-and-conditions/data-processing-addendum/" &&
    (cockroachLabs.processors || []).some((p) => p.slug === "amazon-web-services") &&
    !cockroachLabs.founded_year &&
    fileFlags(cockroachLabs).page === 20 &&
    fileFlags(cockroachLabs).marks === 20 &&
    fileFlags(cockroachLabs).dpa === 20 &&
    fileFlags(cockroachLabs).subprocessors === 20 &&
    fileFlags(cockroachLabs).years === 0 &&
    fileScore(fileFlags(cockroachLabs)) === 80,
);
expect(
  "cockroach-labs marks stay SOC/ISO/PCI — HIPAA/GDPR/CCPA open",
  cockroachLabs &&
    (cockroachLabs.certs || []).includes("SOC 2 Type II") &&
    (cockroachLabs.certs || []).includes("SOC 3") &&
    (cockroachLabs.certs || []).includes("ISO 27001") &&
    (cockroachLabs.certs || []).includes("ISO 42001") &&
    (cockroachLabs.certs || []).includes("PCI DSS") &&
    !(cockroachLabs.certs || []).includes("HIPAA") &&
    !(cockroachLabs.certs || []).includes("GDPR") &&
    !(cockroachLabs.certs || []).includes("CCPA"),
);

const scalekit = bySlug.scalekit;
expect(
  "scalekit Completeness is page · marks · DPA = 60",
  scalekit &&
    scalekit.found === true &&
    scalekit.trust_url === "https://www.scalekit.com/trust-center" &&
    !String(scalekit.trust_url || "").includes("trust.site") &&
    ((scalekit.instruments || {}).dpa || {}).url ===
      "https://www.scalekit.com/legal/data-processing-agreement" &&
    !(scalekit.processors || []).length &&
    fileFlags(scalekit).page === 20 &&
    fileFlags(scalekit).marks === 20 &&
    fileFlags(scalekit).dpa === 20 &&
    fileFlags(scalekit).subprocessors === 0 &&
    fileFlags(scalekit).years === 0 &&
    fileScore(fileFlags(scalekit)) === 60,
);
expect(
  "scalekit marks stay SOC 2 Type II and ISO 27001 — HIPAA/GDPR/CCPA open",
  scalekit &&
    (scalekit.certs || []).includes("SOC 2 Type II") &&
    (scalekit.certs || []).includes("ISO 27001") &&
    !(scalekit.certs || []).includes("HIPAA") &&
    !(scalekit.certs || []).includes("GDPR") &&
    !(scalekit.certs || []).includes("CCPA"),
);

const inworld = bySlug.inworld;
expect(
  "inworld Completeness is page · marks · DPA · subprocessors(10) = 70",
  inworld &&
    inworld.found === true &&
    inworld.trust_url === "https://inworld.ai/security" &&
    !String(inworld.trust_url || "").includes("trust.inworld.ai") &&
    ((inworld.instruments || {}).dpa || {}).url === "https://inworld.ai/data-processing-addendum" &&
    ((inworld.instruments || {}).subprocessors || {}).url === "https://trust.inworld.ai/subprocessors" &&
    !(inworld.processors || []).length &&
    fileFlags(inworld).page === 20 &&
    fileFlags(inworld).marks === 20 &&
    fileFlags(inworld).dpa === 20 &&
    fileFlags(inworld).subprocessors === 10 &&
    fileFlags(inworld).years === 0 &&
    fileScore(fileFlags(inworld)) === 70,
);
expect(
  "inworld marks stay SOC 2 Type II — GDPR/CCPA/HIPAA open",
  inworld &&
    (inworld.certs || []).includes("SOC 2 Type II") &&
    !(inworld.certs || []).includes("GDPR") &&
    !(inworld.certs || []).includes("CCPA") &&
    !(inworld.certs || []).includes("HIPAA"),
);

const weaviate = bySlug.weaviate;
expect(
  "weaviate Completeness is page · marks(10) · DPA · subprocessors = 70",
  weaviate &&
    weaviate.found === true &&
    weaviate.trust_url === "https://weaviate.io/security" &&
    ((weaviate.instruments || {}).dpa || {}).url === "https://weaviate.io/dpa" &&
    ((weaviate.instruments || {}).subprocessors || {}).url === "https://weaviate.io/subprocessors" &&
    (weaviate.processors || []).some((p) => p.slug === "voyage-ai") &&
    fileFlags(weaviate).page === 20 &&
    fileFlags(weaviate).marks === 10 &&
    fileFlags(weaviate).dpa === 20 &&
    fileFlags(weaviate).subprocessors === 20 &&
    fileFlags(weaviate).years === 0 &&
    fileScore(fileFlags(weaviate)) === 70,
);
expect(
  "weaviate stay-compliant SOC 2 / HIPAA stay open",
  weaviate &&
    !(weaviate.certs || []).length &&
    !(weaviate.certs || []).includes("SOC 2") &&
    !(weaviate.certs || []).includes("HIPAA"),
);

const metabase = bySlug.metabase;
expect(
  "metabase Completeness is page · marks = 40",
  metabase &&
    metabase.found === true &&
    metabase.trust_url === "https://www.metabase.com/security" &&
    fileFlags(metabase).page === 20 &&
    fileFlags(metabase).marks === 20 &&
    fileFlags(metabase).dpa === 0 &&
    fileFlags(metabase).subprocessors === 0 &&
    fileFlags(metabase).years === 0 &&
    fileScore(fileFlags(metabase)) === 40,
);
expect(
  "metabase marks stay SOC 2 Type II and SOC 1 Type II — GDPR/CCPA open",
  metabase &&
    (metabase.certs || []).includes("SOC 2 Type II") &&
    (metabase.certs || []).includes("SOC 1 Type II") &&
    !(metabase.certs || []).includes("GDPR") &&
    !(metabase.certs || []).includes("CCPA"),
);

const rime = bySlug.rime;
expect(
  "rime Completeness is page · marks · subprocessors = 60",
  rime &&
    rime.found === true &&
    rime.trust_url === "https://rime.ai/trust" &&
    ((rime.instruments || {}).subprocessors || {}).url === "https://www.rime.ai/rime-subprocessors" &&
    fileFlags(rime).page === 20 &&
    fileFlags(rime).marks === 20 &&
    fileFlags(rime).dpa === 0 &&
    fileFlags(rime).subprocessors === 20 &&
    fileFlags(rime).years === 0 &&
    fileScore(fileFlags(rime)) === 60,
);
expect(
  "rime marks stay SOC 2 Type II — HIPAA/GDPR/CCPA open",
  rime &&
    (rime.certs || []).includes("SOC 2 Type II") &&
    !(rime.certs || []).includes("HIPAA") &&
    !(rime.certs || []).includes("GDPR") &&
    !(rime.certs || []).includes("CCPA"),
);

const loops = bySlug.loops;
expect(
  "loops Completeness is DPA on loops.so",
  loops &&
    loops.domain === "loops.so" &&
    loops.found === false &&
    !loops.trust_url &&
    loops.instruments.dpa.url === "https://loops.so/dpa" &&
    fileFlags(loops).page === 0 &&
    fileFlags(loops).marks === 0 &&
    fileFlags(loops).dpa === 20 &&
    fileFlags(loops).subprocessors === 0 &&
    fileFlags(loops).years === 0 &&
    fileScore(fileFlags(loops)) === 20,
);

const voyageAi = bySlug["voyage-ai"];
expect(
  "voyage-ai Completeness stays 0 on voyageai.com",
  voyageAi &&
    voyageAi.domain === "voyageai.com" &&
    voyageAi.found === false &&
    fileScore(fileFlags(voyageAi)) === 0,
);

const levelAi = bySlug["level-ai"];
expect(
  "level-ai Completeness is page · marks(10) · DPA · subprocessors(10) = 60",
  levelAi &&
    levelAi.found === true &&
    levelAi.domain === "thelevel.ai" &&
    levelAi.trust_url === "https://thelevel.ai/security" &&
    !String(levelAi.trust_url || "").includes("trust.thelevel.ai") &&
    ((levelAi.instruments || {}).dpa || {}).url === "https://thelevel.ai/legal/dpa" &&
    ((levelAi.instruments || {}).subprocessors || {}).url === "https://thelevel.ai/legal/subprocessors" &&
    !(levelAi.processors || []).length &&
    !(levelAi.certs || []).length &&
    fileFlags(levelAi).page === 20 &&
    fileFlags(levelAi).marks === 10 &&
    fileFlags(levelAi).dpa === 20 &&
    fileFlags(levelAi).subprocessors === 10 &&
    fileFlags(levelAi).years === 0 &&
    fileScore(fileFlags(levelAi)) === 60,
);

const amx = bySlug.amx;
expect(
  "amx Completeness is years = 20",
  amx &&
    amx.domain === "amxconsulting.com" &&
    amx.found === false &&
    amx.founded_year === 2017 &&
    fileFlags(amx).page === 0 &&
    fileFlags(amx).marks === 0 &&
    fileFlags(amx).dpa === 0 &&
    fileFlags(amx).subprocessors === 0 &&
    fileFlags(amx).years === 20 &&
    fileScore(fileFlags(amx)) === 20,
);

for (const slug of [
  "apricity-group",
  "mako-it-lab",
  "fwd-deploy",
  "software-mind",
  "marketstar",
  "ai-data-innovations",
  "cloud-support-technologies",
  "mosse-security",
]) {
  const row = bySlug[slug];
  expect(
    `${slug} Completeness stays 0`,
    row && row.found === false && fileScore(fileFlags(row)) === 0,
  );
}

const vector = bySlug.vector;
expect(
  "vector Completeness is page · marks(10) · subprocessors(10) = 40",
  vector &&
    vector.found === true &&
    vector.domain === "vector.co" &&
    vector.trust_url === "https://www.vector.co/security" &&
    !String(vector.trust_url || "").includes("trust.vector.co") &&
    ((vector.instruments || {}).subprocessors || {}).url ===
      "https://trust.vector.co/subprocessors" &&
    !((vector.instruments || {}).dpa || {}).url &&
    !(vector.processors || []).length &&
    !(vector.certs || []).length &&
    !(vector.certs || []).includes("GDPR") &&
    !(vector.certs || []).includes("CCPA") &&
    !(vector.certs || []).includes("PIPEDA") &&
    !(vector.certs || []).includes("LGPD") &&
    !(vector.certs || []).includes("SOC 2 Type I") &&
    fileFlags(vector).page === 20 &&
    fileFlags(vector).marks === 10 &&
    fileFlags(vector).dpa === 0 &&
    fileFlags(vector).subprocessors === 10 &&
    fileFlags(vector).years === 0 &&
    fileScore(fileFlags(vector)) === 40,
);

const supportlogic = bySlug.supportlogic;
expect(
  "supportlogic Completeness is page · marks · DPA = 60",
  supportlogic &&
    supportlogic.found === true &&
    supportlogic.trust_url === "https://www.supportlogic.com/security/" &&
    ((supportlogic.instruments || {}).dpa || {}).url ===
      "https://www.supportlogic.com/data-processing-addendum/" &&
    !(supportlogic.processors || []).length &&
    !supportlogic.founded_year &&
    fileFlags(supportlogic).page === 20 &&
    fileFlags(supportlogic).marks === 20 &&
    fileFlags(supportlogic).dpa === 20 &&
    fileFlags(supportlogic).subprocessors === 0 &&
    fileFlags(supportlogic).years === 0 &&
    fileScore(fileFlags(supportlogic)) === 60,
);

const neon = bySlug.neon;
expect(
  "neon Completeness is page · marks = 40",
  neon &&
    neon.domain === "neon.tech" &&
    neon.found === true &&
    neon.trust_url === "https://neon.com/security" &&
    !String(neon.trust_url || "").includes("trust.neon.com") &&
    (neon.certs || []).includes("SOC 2 Type II") &&
    (neon.certs || []).includes("SOC 3") &&
    (neon.certs || []).includes("ISO 27001") &&
    (neon.certs || []).includes("ISO 27701") &&
    !(neon.certs || []).includes("GDPR") &&
    !(neon.certs || []).includes("CCPA") &&
    !(neon.certs || []).includes("HIPAA") &&
    !(neon.certs || []).includes("FedRAMP") &&
    !(neon.certs || []).includes("PCI DSS") &&
    !neon.founded_year &&
    fileFlags(neon).page === 20 &&
    fileFlags(neon).marks === 20 &&
    fileFlags(neon).dpa === 0 &&
    fileFlags(neon).subprocessors === 0 &&
    fileFlags(neon).years === 0 &&
    fileScore(fileFlags(neon)) === 40,
);
expect("neon is not databricks", neon && neon.slug === "neon" && bySlug.databricks && bySlug.databricks.domain === "databricks.com");

const nylas = bySlug.nylas;
expect(
  "nylas Completeness is page · marks · subprocessors = 60",
  nylas &&
    nylas.found === true &&
    nylas.trust_url === "https://www.nylas.com/security" &&
    ((nylas.instruments || {}).subprocessors || {}).url ===
      "https://www.nylas.com/security/subprocessors/" &&
    (nylas.processors || []).length === 40 &&
    (nylas.processors || []).some((p) => p.slug === "segment" && p.name === "Twilio Segment") &&
    (nylas.processors || []).some((p) => p.slug === "google") &&
    (nylas.processors || []).some((p) => p.slug === "gong") &&
    !(nylas.processors || []).some((p) => p.slug === "twilio") &&
    !((nylas.instruments || {}).dpa || {}).url &&
    !nylas.founded_year &&
    fileFlags(nylas).page === 20 &&
    fileFlags(nylas).marks === 20 &&
    fileFlags(nylas).dpa === 0 &&
    fileFlags(nylas).subprocessors === 20 &&
    fileFlags(nylas).years === 0 &&
    fileScore(fileFlags(nylas)) === 60,
);

const src = readFileSync(new URL("../site/register.js", import.meta.url), "utf8");
expect("register draws the file index", src.includes("fileIndexHtml"));
expect("register has no N of 5 markup", !src.includes("file-cov") && !src.includes("file-meter") && !src.includes(" of 5"));
expect("register does not print tier words in the cell", !src.includes("displayFileState") && !src.includes("tierClass"));
expect("register has no stars", !src.includes("★") && !src.includes("☆") && !src.includes("star-rating") && !src.includes("trust maturity"));
expect("register does not restyle the dossier stamp", !src.includes("disclosure"));
expect("register has no More on this file", !src.includes("More on this file") && !src.includes("record-extra"));

const indexHtml = readFileSync(new URL("../site/index.html", import.meta.url), "utf8");
const companiesHtml = readFileSync(new URL("../site/companies.html", import.meta.url), "utf8");
function registerFileCell(html) {
  const m = String(html || "").match(/<td class="file">([\s\S]*?)<\/td>/);
  return m ? m[1] : "";
}

expect(
  "legend is once above the grid",
  indexHtml.includes('id="file-legend"') && indexHtml.includes("page · standards · processors · evals · incidents"),
);
expect(
  "register legend is the five Companies rules",
  companiesHtml.includes('id="file-legend"') && companiesHtml.includes("page · standards · DPA · subprocessors · years"),
);
expect(
  "register method line is once under the legend",
  /id="file-legend">page · standards · DPA · subprocessors · years<\/p>\s*<p class="file-method" id="file-method">20 printed · 10 on file, not extracted · 0 missing\. 100 is five prints\.<\/p>/.test(companiesHtml) &&
    (companiesHtml.match(/<p class="file-method" id="file-method">20 printed · 10 on file, not extracted · 0 missing\. 100 is five prints\.<\/p>/g) || []).length === 1,
);
expect(
  "register method line has no strike markup",
  !/<(?:s|del|strike|i)[\s>/]/.test(((companiesHtml.match(/<p class="file-method"[^>]*>([\s\S]*?)<\/p>/) || [])[1] || "")),
);

const onePass = bySlug["1password"];
const onePassCell = registerFileCell(registerRowHtml(onePass));
expect("1Password count is five", fileCount(onePass) === 5 && fileScore(fileFlags(onePass)) === 100);
expect(
  "1Password File prints 100",
  /<span class="file-num">100<\/span>/.test(onePassCell) &&
    /file-num[\s\S]*file-index[\s\S]*file-rule/.test(onePassCell) &&
    !onePassCell.includes("100/100") &&
    !onePassCell.includes("100%") &&
    !/\d+ on file/.test(onePassCell),
);

const twoFilled = {
  slug: "two-filled",
  name: "Two",
  domain: "two.example",
  instruments: { dpa: { url: "https://two.example/dpa" } },
  founded_year: 2014,
};
const twoCell = registerFileCell(registerRowHtml(twoFilled));
expect("two-filled count is two", fileCount(twoFilled) === 2 && fileScore(fileFlags(twoFilled)) === 40);
expect(
  "two-filled File prints 40",
  /<span class="file-num">40<\/span>/.test(twoCell) &&
    !/<span class="file-num">2<\/span>/.test(twoCell) &&
    !twoCell.includes("40/100") &&
    !twoCell.includes("40%"),
);

const silentCell = registerFileCell(registerRowHtml({ slug: "silent", name: "Silent", domain: "silent.example" }));
expect("silent File prints 0", /<span class="file-num">0<\/span>/.test(silentCell) && fileCount({}) === 0);

expect("register has no Score header", !/>\s*Score\s*</i.test(companiesHtml) && (companiesHtml.match(/<th /g) || []).length === 4);
expect("register Completeness header stays Completeness", /<button type="button">Completeness<\/button>/.test(companiesHtml));
expect(
  "finder placeholder dropped old tier words",
  companiesHtml.includes('placeholder="/ stripe, on file, fedramp moderate"') &&
    !/placeholder="[^"]*\b(silent|thin|substantial|complete)\b/.test(companiesHtml),
);
expect("legend is not a tooltip farm", !src.includes("title=") || !/file-rule[^>]*title=/.test(src));

const dossier = readFileSync(new URL("../site/c/anysphere.html", import.meta.url), "utf8");
expect("dossier names Cursor in the h1", /<h1>(?:<img class="ink-ico"[^>]*>)?Cursor<\/h1>/.test(dossier));
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
expect("dossier clerk mark words are links", /<p class="clerk">[\s\S]*<a href="\.\.\/attestations.html#soc-2-type-ii">SOC 2 Type II<\/a>[\s\S]*<a href="\.\.\/attestations.html#aiuc-1">AIUC-1<\/a>/.test(dossier));
expect("dossier clerk has no mark icons", !/<p class="clerk">[\s\S]*<(img|svg)/.test(dossier));
expect("dossier outbound is Official page", dossier.includes('class="official"') && dossier.includes("Official page") && !dossier.includes("View source") && !dossier.includes("go-out") && !dossier.includes("file-go"));
expect("dossier nav does not current Register", !dossier.includes('class="on"'));
expect("dossier body is dossier", dossier.includes('class="dossier"'));
expect("dossier empty rows stay italic not on file", dossier.includes('class="absent">not on file'));
expect("dossier FedRAMP cites marketplace, not a badge", dossier.includes("Filed from the") && dossier.includes("FedRAMP Marketplace") && !dossier.includes("Not a badge") && !dossier.includes("not a badge") && !dossier.includes("not a score") && !dossier.includes("Not a score"));
expect("anysphere FedRAMP is the Cursor marketplace row", dossier.includes("FR2631054484") && /<a href="https:\/\/www\.fedramp\.gov\/marketplace\/products\/FR2631054484\/?"[^>]*target="_blank"[^>]*>Cursor<\/a>/.test(dossier) && dossier.includes("not yet certified") && dossier.includes("initial implementation") && dossier.includes("authorizations 0"));
expect("anysphere FedRAMP does not borrow Box words", !dossier.includes("authorized") && !dossier.includes(">High<") && !dossier.includes("25 Mar 2025") && !dossier.includes("Box Enterprise"));
expect("anysphere FedRAMP is not four invented misses", !/<tr><td[^>]*>[\s\S]*not on file[\s\S]*not on file[\s\S]*not on file[\s\S]*not on file/.test(dossier.split('sec-kicker">FedRAMP')[1].split("Named processors")[0]));
const cursorNames = [
  "Amazon Web Services", "Fireworks", "OpenAI", "Anthropic", "Google Gemini",
  "Turbopuffer", "Exa", "Datadog", "Databricks", "Vercel", "Azure", "Baseten",
  "Cloudflare", "Google Cloud Platform", "Together", "SpaceXAI", "WorkOS",
];
const procChunk = dossier.split("Named processors")[1] || "";
const procCells = [...procChunk.matchAll(/<tr><td>(.*?)<\/td><\/tr>/g)].map((m) => m[1]);
const procNames = procCells.map((cell) => cell.replace(/<[^>]+>/g, ""));
expect(
  "anysphere processors are the published list",
  cursorNames.every((n) => procChunk.includes(n)) &&
    procNames.length === cursorNames.length &&
    procNames.join() === [...procNames].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" })).join(),
);
const dossierHref = {
  "Amazon Web Services": "./amazon-web-services.html",
  Fireworks: "./fireworks-ai.html",
  OpenAI: "./openai.html",
  Anthropic: "./anthropic.html",
  Datadog: "./datadog.html",
  Databricks: "./databricks.html",
  Vercel: "./vercel.html",
  Cloudflare: "./cloudflare.html",
  Together: "./together-ai.html",
  Azure: "./microsoft.html",
  Baseten: "./baseten.html",
  "Google Cloud Platform": "./google.html",
  "Google Gemini": "./google.html",
  Exa: "./exa.html",
  WorkOS: "./workos.html",
  Turbopuffer: "./turbopuffer.html",
  SpaceXAI: "./xai.html",
};
const graphHref = {};
expect(
  "anysphere processors that have a file are links",
  procCells.every((cell, i) => {
    const name = procNames[i];
    const want = dossierHref[name] || graphHref[name];
    return want && cell.includes(`href="${want}"`) && cell.includes(name);
  }),
);
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

const cvent = bySlug.cvent;
const vertex = bySlug.vertex;
const checkr = bySlug.checkr;
const clickup = bySlug.clickup;
const monday = bySlug.monday;
const miro = bySlug.miro;
const unity = bySlug.unity;
const amplitude = bySlug.amplitude;
const benchling = bySlug.benchling;
const digitalocean = bySlug.digitalocean;
expect("cvent DPA follows the stored addendum", cvent.instruments.dpa.url === "https://www.cvent.com/en/data-processing-addendum" && fileFlags(cvent).dpa === 20 && ruleOn(fileIndexHtml(cvent))[2] === true);
expect("vertex DPA follows the stored addendum", vertex.instruments.dpa.url === "https://www.vertexinc.com/legal/data-processing-addendum" && fileFlags(vertex).dpa === 20 && ruleOn(fileIndexHtml(vertex))[2] === true);
expect("miro DPA follows the stored addendum", miro.instruments.dpa.url === "https://miro.com/legal/customer-data-processing-addendum/" && fileFlags(miro).dpa === 20 && ruleOn(fileIndexHtml(miro))[2] === true);
expect("unity DPA follows the stored addendum", unity.instruments.dpa.url === "https://unity.com/legal/unity-data-processing-addendum-dpa" && fileFlags(unity).dpa === 20 && ruleOn(fileIndexHtml(unity))[2] === true);
expect("checkr subprocessors follow the stored list", checkr.instruments.subprocessors.url === "https://checkr.com/legal/sub-processor-list" && checkr.processors.length > 0 && fileFlags(checkr).subprocessors === 20);
expect("clickup subprocessors follow the stored list", clickup.instruments.subprocessors.url === "https://clickup.com/terms/dpa/subprocessors" && clickup.processors.length > 0 && fileFlags(clickup).subprocessors === 20);
expect("monday subprocessors follow the stored list", monday.instruments.subprocessors.url === "https://monday.com/l/privacy/sub-processors-subsidiaries-support/" && monday.processors.length > 0 && fileFlags(monday).subprocessors === 20);
expect("amplitude subprocessors follow the stored list", amplitude.instruments.subprocessors.url === "https://www.amplitude.com/subprocessor-list" && amplitude.processors.length > 0 && fileFlags(amplitude).subprocessors === 20);
expect("benchling subprocessors follow the stored list", benchling.instruments.subprocessors.url === "https://www.benchling.com/subprocessors" && benchling.processors.length > 0 && fileFlags(benchling).subprocessors === 20);
expect("digitalocean subprocessors follow the stored list", digitalocean.instruments.subprocessors.url === "https://www.digitalocean.com/trust/subprocessors" && digitalocean.processors.length > 0 && fileFlags(digitalocean).subprocessors === 20);
const swan = bySlug.swan;
expect(
  "swan Completeness is DPA · years",
  swan.founded_year === 2024 &&
    swan.instruments.dpa.url === "https://www.getswan.com/legal/dpa" &&
    fileFlags(swan).dpa === 20 &&
    fileFlags(swan).years === 20 &&
    fileFlags(swan).page === 0 &&
    fileFlags(swan).marks === 0 &&
    fileFlags(swan).subprocessors === 0 &&
    fileScore(fileFlags(swan)) === 40 &&
    ruleOn(fileIndexHtml(swan))[2] === true &&
    ruleOn(fileIndexHtml(swan))[4] === true,
);
const pdfCo = bySlug.pdf;
expect(
  "pdf Completeness is page · marks",
  pdfCo.found === true &&
    pdfCo.trust_url === "https://pdf.co/security" &&
    (pdfCo.certs || []).includes("SOC 2 Type II") &&
    fileFlags(pdfCo).page === 20 &&
    fileFlags(pdfCo).marks === 20 &&
    fileFlags(pdfCo).dpa === 0 &&
    fileFlags(pdfCo).subprocessors === 0 &&
    fileFlags(pdfCo).years === 0 &&
    fileScore(fileFlags(pdfCo)) === 40 &&
    ruleOn(fileIndexHtml(pdfCo))[0] === true &&
    ruleOn(fileIndexHtml(pdfCo))[1] === true,
);
const cloudamqp = bySlug["84codes-cloudamqp"];
expect(
  "cloudamqp Completeness is page · marks · DPA",
  cloudamqp.found === true &&
    cloudamqp.trust_url === "https://www.cloudamqp.com/legal/security_and_compliance.html" &&
    cloudamqp.instruments.dpa.url === "https://www.cloudamqp.com/legal/terms_of_service.html#data-processing-agreement" &&
    fileFlags(cloudamqp).page === 20 &&
    fileFlags(cloudamqp).marks === 20 &&
    fileFlags(cloudamqp).dpa === 20 &&
    fileFlags(cloudamqp).subprocessors === 0 &&
    fileFlags(cloudamqp).years === 0 &&
    fileScore(fileFlags(cloudamqp)) === 60 &&
    ruleOn(fileIndexHtml(cloudamqp))[0] === true &&
    ruleOn(fileIndexHtml(cloudamqp))[1] === true &&
    ruleOn(fileIndexHtml(cloudamqp))[2] === true,
);
const hivelocity = bySlug.hivelocity;
expect(
  "hivelocity Completeness is marks · years; legal index is not Official page",
  hivelocity.found === false &&
    !hivelocity.trust_url &&
    hivelocity.founded_year === 2002 &&
    (hivelocity.certs || []).includes("PCI DSS") &&
    (hivelocity.certs || []).includes("EU-US DPF") &&
    !(hivelocity.certs || []).includes("CCPA") &&
    fileFlags(hivelocity).page === 0 &&
    fileFlags(hivelocity).marks === 20 &&
    fileFlags(hivelocity).dpa === 0 &&
    fileFlags(hivelocity).subprocessors === 0 &&
    fileFlags(hivelocity).years === 20 &&
    fileScore(fileFlags(hivelocity)) === 40 &&
    ruleOn(fileIndexHtml(hivelocity))[0] === false &&
    ruleOn(fileIndexHtml(hivelocity))[1] === true &&
    ruleOn(fileIndexHtml(hivelocity))[4] === true,
);
const e2open = bySlug.e2open;
expect(
  "e2open Completeness stays 0; title-only cert pages are not marks",
  e2open.found === false &&
    !e2open.trust_url &&
    !(e2open.certs || []).length &&
    fileFlags(e2open).page === 0 &&
    fileFlags(e2open).marks === 0 &&
    fileFlags(e2open).dpa === 0 &&
    fileFlags(e2open).subprocessors === 0 &&
    fileFlags(e2open).years === 0 &&
    fileScore(fileFlags(e2open)) === 0 &&
    ruleOn(fileIndexHtml(e2open))[0] === false &&
    ruleOn(fileIndexHtml(e2open))[1] === false,
);
const tanla = bySlug["tanla-platforms"];
expect(
  "tanla Completeness is years; LBS article is not Official page",
  tanla.found === false &&
    !tanla.trust_url &&
    tanla.founded_year === 1999 &&
    tanla.founded_source === "https://www.tanla.com/lbs-trust-imperative" &&
    fileFlags(tanla).page === 0 &&
    fileFlags(tanla).marks === 0 &&
    fileFlags(tanla).dpa === 0 &&
    fileFlags(tanla).subprocessors === 0 &&
    fileFlags(tanla).years === 20 &&
    fileScore(fileFlags(tanla)) === 20 &&
    ruleOn(fileIndexHtml(tanla))[0] === false &&
    ruleOn(fileIndexHtml(tanla))[4] === true,
);
const e2b = bySlug.e2b;
expect(
  "e2b Completeness is marks; Vanta portal is not Official page",
  e2b &&
    e2b.domain === "e2b.dev" &&
    e2b.found === false &&
    !e2b.trust_url &&
    (e2b.certs || []).includes("SOC 2 Type II") &&
    !(e2b.certs || []).includes("HIPAA") &&
    fileFlags(e2b).page === 0 &&
    fileFlags(e2b).marks === 20 &&
    fileFlags(e2b).dpa === 0 &&
    fileFlags(e2b).subprocessors === 0 &&
    fileFlags(e2b).years === 0 &&
    fileScore(fileFlags(e2b)) === 20 &&
    ruleOn(fileIndexHtml(e2b))[0] === false &&
    ruleOn(fileIndexHtml(e2b))[1] === true,
);
const codecentric = bySlug.codecentric;
expect(
  "codecentric Completeness is marks; product IT-security page is not Official page",
  codecentric &&
    codecentric.domain === "codecentric.de" &&
    codecentric.found === false &&
    !codecentric.trust_url &&
    (codecentric.certs || []).includes("ISO 27001") &&
    (codecentric.certs || []).includes("TISAX") &&
    fileFlags(codecentric).page === 0 &&
    fileFlags(codecentric).marks === 20 &&
    fileFlags(codecentric).dpa === 0 &&
    fileFlags(codecentric).subprocessors === 0 &&
    fileFlags(codecentric).years === 0 &&
    fileScore(fileFlags(codecentric)) === 20 &&
    ruleOn(fileIndexHtml(codecentric))[0] === false &&
    ruleOn(fileIndexHtml(codecentric))[1] === true,
);
const payu = bySlug.payu;
expect(
  "payu Completeness is page · marks · years = 60",
  payu &&
    payu.domain === "payu.pl" &&
    payu.found === true &&
    payu.trust_url === "https://poland.payu.com/security/" &&
    (payu.certs || []).includes("PCI DSS") &&
    !(payu.certs || []).includes("SOC 1") &&
    payu.founded_year === 2002 &&
    payu.founded_source === "https://poland.payu.com/o-nas/" &&
    fileFlags(payu).page === 20 &&
    fileFlags(payu).marks === 20 &&
    fileFlags(payu).dpa === 0 &&
    fileFlags(payu).subprocessors === 0 &&
    fileFlags(payu).years === 20 &&
    fileScore(fileFlags(payu)) === 60 &&
    ruleOn(fileIndexHtml(payu))[0] === true &&
    ruleOn(fileIndexHtml(payu))[1] === true &&
    ruleOn(fileIndexHtml(payu))[4] === true,
);
const devopsEnabler = bySlug["devops-enabler"];
expect(
  "devops-enabler Completeness is marks; About is not Official page",
  devopsEnabler &&
    devopsEnabler.domain === "devopsenabler.com" &&
    devopsEnabler.found === false &&
    !devopsEnabler.trust_url &&
    (devopsEnabler.certs || []).includes("ISO 27001") &&
    !(devopsEnabler.certs || []).includes("DORA") &&
    !(devopsEnabler.certs || []).includes("SOC 2 Type II") &&
    !(devopsEnabler.certs || []).includes("HIPAA") &&
    fileFlags(devopsEnabler).page === 0 &&
    fileFlags(devopsEnabler).marks === 20 &&
    fileFlags(devopsEnabler).dpa === 0 &&
    fileFlags(devopsEnabler).subprocessors === 0 &&
    fileFlags(devopsEnabler).years === 0 &&
    fileScore(fileFlags(devopsEnabler)) === 20 &&
    ruleOn(fileIndexHtml(devopsEnabler))[0] === false &&
    ruleOn(fileIndexHtml(devopsEnabler))[1] === true,
);
const nextlink = bySlug["jsaunders-solutions-d-b-a-nextlink-labs"];
expect(
  "ai-data-innovations Completeness is marks; homepage is not Official page",
  (() => {
    const row = bySlug["ai-data-innovations"];
    return (
      row &&
      row.domain === "aidatainnovations.com" &&
      row.found === false &&
      !row.trust_url &&
      (row.certs || []).includes("ISO 27001") &&
      (row.certs || []).includes("SOC 2 Type I") &&
      !(row.certs || []).includes("GDPR") &&
      fileFlags(row).page === 0 &&
      fileFlags(row).marks === 20 &&
      fileFlags(row).dpa === 0 &&
      fileFlags(row).subprocessors === 0 &&
      fileFlags(row).years === 0 &&
      fileScore(fileFlags(row)) === 20 &&
      ruleOn(fileIndexHtml(row))[0] === false &&
      ruleOn(fileIndexHtml(row))[1] === true
    );
  })(),
);
expect(
  "ltx Completeness is years; About is not Official page",
  (() => {
    const row = bySlug.ltx;
    return (
      row &&
      row.domain === "ltx.io" &&
      row.found === false &&
      !row.trust_url &&
      row.founded_year === 2024 &&
      row.founded_source === "https://ltx.io/about-us" &&
      fileFlags(row).page === 0 &&
      fileFlags(row).marks === 0 &&
      fileFlags(row).dpa === 0 &&
      fileFlags(row).subprocessors === 0 &&
      fileFlags(row).years === 20 &&
      fileScore(fileFlags(row)) === 20 &&
      ruleOn(fileIndexHtml(row))[4] === true
    );
  })(),
);
expect(
  "jt-jersey Completeness is years; About is not Official page",
  (() => {
    const row = bySlug["jt-jersey"];
    return (
      row &&
      row.domain === "jtglobal.com" &&
      row.found === false &&
      !row.trust_url &&
      row.founded_year === 1888 &&
      row.founded_source === "https://www.jtglobal.com/about-us/" &&
      fileFlags(row).page === 0 &&
      fileFlags(row).marks === 0 &&
      fileFlags(row).dpa === 0 &&
      fileFlags(row).subprocessors === 0 &&
      fileFlags(row).years === 20 &&
      fileScore(fileFlags(row)) === 20 &&
      ruleOn(fileIndexHtml(row))[4] === true
    );
  })(),
);
expect(
  "nextlink Completeness is marks; HIPAA-compliant engineering stays open",
  nextlink &&
    nextlink.domain === "nextlinklabs.com" &&
    nextlink.found === false &&
    !nextlink.trust_url &&
    (nextlink.certs || []).includes("SOC 2 Type I") &&
    !(nextlink.certs || []).includes("HIPAA") &&
    fileFlags(nextlink).page === 0 &&
    fileFlags(nextlink).marks === 20 &&
    fileFlags(nextlink).dpa === 0 &&
    fileFlags(nextlink).subprocessors === 0 &&
    fileFlags(nextlink).years === 0 &&
    fileScore(fileFlags(nextlink)) === 20 &&
    ruleOn(fileIndexHtml(nextlink))[0] === false &&
    ruleOn(fileIndexHtml(nextlink))[1] === true,
);
const coralogix = bySlug.coralogix;
expect(
  "coralogix Completeness is DPA; SafeBase portal is not Official page",
  coralogix.found === false &&
    !coralogix.trust_url &&
    ((coralogix.instruments || {}).trust || {}).url === "https://trust.coralogix.com" &&
    coralogix.instruments.dpa.url === "https://coralogix.com/data-processing-agreement/" &&
    !(coralogix.certs || []).length &&
    fileFlags(coralogix).page === 0 &&
    fileFlags(coralogix).marks === 0 &&
    fileFlags(coralogix).dpa === 20 &&
    fileFlags(coralogix).subprocessors === 0 &&
    fileFlags(coralogix).years === 0 &&
    fileScore(fileFlags(coralogix)) === 20 &&
    ruleOn(fileIndexHtml(coralogix))[0] === false &&
    ruleOn(fileIndexHtml(coralogix))[2] === true,
);
const planview = bySlug.planview;
expect(
  "URL-only subprocessors is 10 not 20",
  planview.processors.length === 0 &&
    !!planview.instruments.subprocessors.url &&
    fileFlags(planview).subprocessors === 10 &&
    fileScore(fileFlags(planview)) === 90 &&
    ruleKind(fileIndexHtml(planview))[3] === "partial" &&
    fileIndexHtml(planview).includes('class="file-rule partial"'),
);
const urlOnlySubs = { instruments: { subprocessors: { url: "https://example.com/subprocessors" } } };
expect("synthetic URL-only subprocessors is 10", fileFlags(urlOnlySubs).subprocessors === 10 && fileScore(fileFlags(urlOnlySubs)) === 10);
expect("dotted rule is Ledger Black not a pip", fileIndexHtml(urlOnlySubs).includes('class="file-rule partial"') && ruleKind(fileIndexHtml(urlOnlySubs))[3] === "partial");
expect("filed processor names are not dates", [checkr, clickup, monday, amplitude, benchling, digitalocean].every((row) => (row.processors || []).every((p) => !/^\d{1,2}\s+[A-Za-z]+\s+\d{4}$/.test(p.name) && p.name !== "Date" && p.name !== "Date of change" && p.name !== "AUS" && p.name !== "Data Center Services")));

const box = readFileSync(new URL("../site/c/box.html", import.meta.url), "utf8");
expect("on-file FedRAMP is a table with marketplace cite", box.includes("Filed from the") && box.includes("FedRAMP Marketplace") && box.includes("fedramp.gov/marketplace") && box.includes('class="inst filed"') && box.includes("authorized") && !box.includes("Not a badge") && !box.includes("highest authorized") && !box.includes('td class="mark"') && !box.includes("sem-source") && !box.includes("sem-conflict"));
expect("on-file processors are published names", box.includes("GitHub") && box.includes("New Relic") && !box.includes("+N") && !box.includes("Not a complete supply chain") && /sec-kicker">Named processors[\s\S]*Filed from/.test(box));

const vercel = readFileSync(new URL("../site/c/vercel.html", import.meta.url), "utf8");
expect("vercel mark words with a file are links", vercel.includes('href="../attestations.html#dora">DORA</a>') && vercel.includes('href="../attestations.html#eu-us-dpf">EU-US DPF</a>') && vercel.includes('href="../attestations.html#nis2">NIS2</a>') && vercel.includes('href="../attestations.html#pipeda">PIPEDA</a>'));
const chain = readFileSync(new URL("../site/c/chainguard.html", import.meta.url), "utf8");
expect("mark without a file stays words", chain.includes("<li>SLSA</li>") && !chain.includes("attestations.html#slsa") && !chain.includes("<img"));

const css = readFileSync(new URL("../site/styles.css", import.meta.url), "utf8");
expect("identity block wears the spine", /\.ident \{[\s\S]*border-left: var\(--ot-spine\) solid var\(--ot-evidence-teal\)/.test(css));
expect("no boxed file-state module", !css.includes(".file-state") && !css.includes(".state-word"));
expect("rules are ledger black", /\.file-rule \{[\s\S]*border-top: 1px solid var\(--ot-ledger-black\)/.test(css) && /\.file-rule\.on \{[\s\S]*background: var\(--ot-ledger-black\)/.test(css));
expect("teal does not fill the rules", !/\.file-rule[\s\S]{0,80}--ot-evidence-teal/.test(css) && !/\.file-rule\.on[\s\S]{0,80}--ot-evidence-teal/.test(css) && !/\.file-rule\.partial[\s\S]{0,80}--ot-evidence-teal/.test(css));
expect("no star styles", !css.includes("★") && !css.includes("☆") && !css.includes("star-rating") && !css.includes("trust-maturity"));
expect("marks stay Atkinson data", /\.mark-list li \{[\s\S]*font: var\(--t-data\)/.test(css) && /\.mark-list li \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
expect("instrument cells stay Atkinson", /\.inst td \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
expect("Official page stays Atkinson", /\.out \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css) && /a\.official \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
expect("Official page stays Atkinson on compact", /\.dossier \.file \.out a\.official \{[\s\S]*font-family: var\(--ot-font-utility\)/.test(css));
expect("filed tables have no second spine", /\.inst\.filed td:first-child \{[\s\S]*border-left: 0/.test(css) && /\.inst\.filed tbody tr:hover td:first-child[\s\S]*border-left: 0/.test(css));
expect("phone keeps FedRAMP columns as a table", !/\.dossier \.file \.inst thead \{ display: none/.test(css) && !/\.dossier \.file \.inst\.filed td\.empty \{[\s\S]*display: none/.test(css));
