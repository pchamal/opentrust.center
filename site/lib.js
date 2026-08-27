/* Shared clerk utilities. */

export const GATE_KEY = "ot_human_v1";
export const GATE_MS = 30 * 60 * 1000;
export const DATA_V = "2026-08-26T23:59:44Z";
export const FILE_KEYS = ["page", "marks", "dpa", "subprocessors", "years"];
export const FILE_LABELS = {
  page: "page",
  marks: "standards",
  dpa: "DPA",
  subprocessors: "subprocessors",
  years: "years",
};
export const AI_FILE_KEYS = ["page", "marks", "processors", "evals", "incidents"];
export const AI_FILE_LABELS = {
  page: "page",
  marks: "standards",
  processors: "processors",
  evals: "evals",
  incidents: "incidents",
};
export const AI_MARK_IDS = new Set(["aiuc-1", "iso-42001", "nist-ai-rmf", "eu-ai-act"]);
export const AI_MARK_RE = /aiuc-?1|iso(?:\/iec)?[\s-]*42001|nist[\s-]*ai[\s-]*rmf|eu[\s-]*ai[\s-]*act/i;
export const AI_PAGE_RE = /model-?card|system-?card|responsible-ai|ai-safety|ai-security/i;
const VENDOR_HOST_RE = /(^|\.)(safebase\.(us|com)|vanta\.com|conveyor\.com|wolfia\.\w+|securitypal\.com|drata\.com|secureframe\.com|whistic\.com|sprinto\.com|trustcloud\.com)$/i;
export const AI_PROCESSORS_RE = /model-processors|llm-processors|named-model/i;
/* Model/API providers. Hosting (AWS, GCP, Azure, Snowflake) does not count. */
export const AI_SYSTEM_PROCESSOR_SLUGS = new Set([
  "openai",
  "anthropic",
  "cohere",
  "mistral-ai",
  "groq",
  "fireworks-ai",
  "together-ai",
  "hugging-face",
  "scale-ai",
  "xai",
  "perplexity-ai",
  "elevenlabs",
  "runway",
  "fal-ai",
]);
const NOT_AI_SYSTEM_PROCESSOR_SLUGS = new Set([
  "amazon-web-services",
  "stripe",
  "datadog",
  "snowflake",
  "cloudflare",
  "microsoft",
  "google",
]);
const AI_SYSTEM_PROCESSOR_NAME_RE =
  /^(openai(?: opco(?: llc)?)?|anthropic(?: pbc)?|cohere|mistral(?: ai)?|groq|fireworks(?: ai(?: inc)?)?|together(?: ai)?|hugging face(?: inference)?|scale ai|xai|perplexity(?: ai)?|eleven ?labs|runway(?: ml)?|fal(?: ai)?|google gemini|vertex(?: ai)?|azure openai|amazon bedrock|openrouter|deepinfra|deepgram(?: inc)?|cartesia(?: ai(?: inc)?)?|baseten(?: labs(?: inc)?)?|kling(?: ai(?: pte ltd)?)?)$/i;
const HOSTING_PROCESSOR_NAME_RE =
  /^(amazon web services|aws|google cloud(?: platform)?|microsoft azure|azure|snowflake|datadog|stripe|google|microsoft)$/i;
export const AI_EVALS_RE = /red-?team|(?:^|\/)evals?(?:\/|$)/i;
export const AI_INCIDENTS_RE = /ai-incident|(?:^|\/)incidents?(?:\/|$)/i;
/* AI product names already on the register. .ai TLD is not membership. */
export const AI_PRODUCT_SLUGS = new Set([
  "midjourney",
  "hugging-face",
  "runway",
  "glean",
  "groq",
  "abridge",
  "openai",
  "anthropic",
  "anysphere",
  "cohere",
  "writer",
  "elevenlabs",
  "grammarly",
  "harvey",
  "synthesia",
  "xai",
  "mistral-ai",
  "character-ai",
  "stability-ai",
  "perplexity-ai",
  "together-ai",
  "fireworks-ai",
  "fal-ai",
  "sierra",
  "pika",
]);
export const AI_LIST_IDS = new Set([
  "forbes-ai-50-2026",
  "forbes-ai-50-brink-2026",
  "cb-insights-ai-100-2026",
  "arena-org",
  "openrouter-provider",
  "hugging-face-org",
]);

export function dataUrl(path) {
  const v = DATA_V ? encodeURIComponent(DATA_V) : "";
  if (!v) return path;
  return path + (path.includes("?") ? "&" : "?") + "v=" + v;
}

function instrumentUrl(row, key) {
  const rec = row && row.instruments && row.instruments[key];
  return !!(rec && rec.url);
}

function recordedWall(rec) {
  if (!rec || typeof rec !== "object") return false;
  if (Number(rec.http_status || rec.status) === 403) return true;
  const note = String(rec.note || rec.reason || rec.wall || "").toLowerCase();
  return /js shell|login wall|\b403\b/.test(note);
}

function recordedPageWall(row) {
  const crawl = row && row._crawl;
  if (crawl && Number(crawl.http_status) === 403) return true;
  const inst = (row && row.instruments) || {};
  return recordedWall(inst.trust) || recordedWall(inst.security);
}

function namedProcessorList(row) {
  const procs = (row && row.processors) || [];
  return procs.some((p) => p && String(p.name || "").trim());
}

function officialPageOnFile(row) {
  return !!(
    (row && row.found && (row.trust_url || row.final_url)) ||
    instrumentUrl(row, "trust") ||
    instrumentUrl(row, "security")
  );
}

export function hasNamedMarks(row) {
  const atts = ((row && row.attestations) || []).filter((a) => a && (a.name || a.short));
  const certs = ((row && row.certs) || []).filter(Boolean);
  if (atts.length || certs.length) return true;
  return !!(row && row.fedramp);
}

/* Per-rule 0 / 10 / 20. No secret weights. */
export function fileFlags(row) {
  const pageOn = officialPageOnFile(row);
  return {
    page: pageOn ? (recordedPageWall(row) ? 10 : 20) : 0,
    marks: hasNamedMarks(row) ? 20 : pageOn ? 10 : 0,
    dpa: instrumentUrl(row, "dpa") ? 20 : 0,
    subprocessors: namedProcessorList(row) ? 20 : instrumentUrl(row, "subprocessors") ? 10 : 0,
    years: row && row.founded_year ? 20 : 0,
  };
}

export function fileCount(row) {
  const flags = fileFlags(row);
  return FILE_KEYS.reduce((n, key) => n + (flags[key] ? 1 : 0), 0);
}

/* Sum of five 0 / 10 / 20 rules. 100 is five prints. */
export function fileScore(flags) {
  if (!flags || typeof flags !== "object") return 0;
  const keys =
    "dpa" in flags || "subprocessors" in flags || "years" in flags ? FILE_KEYS : AI_FILE_KEYS;
  return keys.reduce((n, key) => n + (Number(flags[key]) || 0), 0);
}

export function fileRuleClass(score) {
  if (score === 20 || score === true) return "file-rule on";
  if (score === 10) return "file-rule partial";
  return "file-rule";
}

export function fileCoverage(row) {
  const flags = fileFlags(row);
  const n = fileCount(row);
  const legend = "page · standards · DPA · subprocessors · years";
  const on = FILE_KEYS.filter((k) => flags[k]).map((k) => FILE_LABELS[k]);
  const spoken = on.length ? on.join(" · ") : "not on file";
  return { n, legend, spoken, title: spoken };
}

export function fileIndexHtml(row) {
  const flags = fileFlags(row);
  const c = fileCoverage(row);
  const rules = FILE_KEYS.map((key) => {
    return `<span class="${fileRuleClass(flags[key])}" aria-hidden="true"></span>`;
  }).join("");
  return `<span class="file-index" role="img" aria-label="${escapeHtml(c.spoken)}">${rules}</span>`;
}

function instrumentHref(row, key) {
  const rec = row && row.instruments && row.instruments[key];
  if (!rec) return "";
  if (typeof rec === "string") return rec;
  return (rec && rec.url) || "";
}

export function isFirstPartyUrl(url, domain) {
  const host = hostOf(url).toLowerCase();
  const own = String(domain || "")
    .replace(/^www\./i, "")
    .toLowerCase();
  if (!host || !own) return false;
  if (VENDOR_HOST_RE.test(host)) return false;
  return host === own || host.endsWith("." + own);
}

function normalizeProcessorName(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[.,]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

const DATE_HEADER_RE = /^(date(?: of change)?|effective date)$/i;
const DATE_PROCESSOR_RE =
  /^(?:(?:19|20|21)\d{2}|\d{4}-\d{2}-\d{2}|\d{1,2}[./]\d{1,2}[./](?:\d{2}|\d{4})|\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+\d{4})$/i;

function looksLikeDateProcessor(value) {
  const t = String(value || "").replace(/\s+/g, " ").trim();
  if (!t) return false;
  if (DATE_HEADER_RE.test(t)) return true;
  if (DATE_PROCESSOR_RE.test(t)) return true;
  const spaced = t.replace(/[-_]+/g, " ");
  return spaced !== t && DATE_PROCESSOR_RE.test(spaced);
}

export function isAiSystemProcessor(proc, ownerSlug) {
  if (!proc) return false;
  const slug = String(proc.slug || "").toLowerCase();
  const owner = String(ownerSlug || "").toLowerCase();
  if (slug && owner && slug === owner) return false;
  if (slug && NOT_AI_SYSTEM_PROCESSOR_SLUGS.has(slug)) return false;
  if (looksLikeDateProcessor(proc.name || proc) || looksLikeDateProcessor(slug)) return false;
  const name = normalizeProcessorName(proc.name || proc);
  if (HOSTING_PROCESSOR_NAME_RE.test(name)) return false;
  if (slug && AI_SYSTEM_PROCESSOR_SLUGS.has(slug)) return true;
  return AI_SYSTEM_PROCESSOR_NAME_RE.test(name);
}

/* Named AI processors printed on a first-party public file.
   Vanta/JS-shell names on row.processors do not fill. */
export function storedAiProcessors(row) {
  const field = row && row.ai_processors;
  const raw = Array.isArray(field) ? field : field && field.names;
  if (!Array.isArray(raw) || !raw.length) return [];
  const owner = row && row.slug;
  const seen = new Set();
  const out = [];
  for (const item of raw) {
    const name = typeof item === "string" ? item : item && item.name;
    const slug = typeof item === "string" ? "" : (item && item.slug) || "";
    const rec = { name: String(name || "").trim(), slug: String(slug || "") };
    if (!rec.name) continue;
    if (!isAiSystemProcessor(rec, owner)) continue;
    const key = (rec.slug || rec.name).toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    if (item && item.source_url) rec.source_url = item.source_url;
    out.push(rec);
  }
  return out;
}

export function storedAiPageUrl(row) {
  const field = row && row.ai_page;
  const fromField = typeof field === "string" ? field : field && field.url;
  const url = fromField || instrumentHref(row, "ai") || "";
  if (!url) return "";
  if (!isFirstPartyUrl(url, row && row.domain)) return "";
  return url;
}

function storedAiInstrumentUrl(row, key) {
  const field = row && row[`ai_${key}`];
  const fromField = typeof field === "string" ? field : field && field.url;
  const url = fromField || instrumentHref(row, key) || "";
  if (!url) return "";
  if (!isFirstPartyUrl(url, row && row.domain)) return "";
  return url;
}

export function storedAiEvalsUrl(row) {
  return storedAiInstrumentUrl(row, "evals");
}

export function storedAiIncidentsUrl(row) {
  return storedAiInstrumentUrl(row, "incidents");
}

/* AITI Domain: company domain, linked to the official homepage.
   The stored AI page stays on the dossier; it does not replace this cell. */
export function printedAitiUrl(row) {
  return printedUrl((row && row.official_url) || "", (row && row.domain) || "");
}

function collectedUrls(row) {
  const urls = [
    row && row.trust_url,
    row && row.final_url,
    instrumentHref(row, "trust"),
    instrumentHref(row, "security"),
    instrumentHref(row, "privacy"),
    instrumentHref(row, "dpa"),
    instrumentHref(row, "subprocessors"),
    instrumentHref(row, "status"),
    instrumentHref(row, "bounty"),
    instrumentHref(row, "evals"),
    instrumentHref(row, "incidents"),
    instrumentHref(row, "model_processors"),
  ];
  const extra = (row && row.processors) || [];
  for (const p of extra) {
    if (p && p.source_url) urls.push(p.source_url);
  }
  return urls.filter(Boolean);
}

export function isAiMarkLabel(value) {
  const s = String(value || "").trim();
  if (!s) return false;
  const id = s.toLowerCase().replace(/[\s_]+/g, "-");
  if (AI_MARK_IDS.has(id)) return true;
  return AI_MARK_RE.test(s);
}

export function printedAiMarks(row) {
  const seen = new Set();
  const out = [];
  const atts = ((row && row.attestations) || []).filter((a) => a && (a.name || a.short || a.id));
  const names = atts.length
    ? atts
    : ((row && row.certs) || []).map((name) => ({ name, id: null }));
  for (const a of names) {
    const id = String((a && a.id) || "").toLowerCase();
    const label = String((a && (a.short || a.name)) || "").trim();
    if (!isAiMarkLabel(id) && !isAiMarkLabel(label)) continue;
    const key = id || label.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({
      id: id || "",
      name: label || id,
      short: (a && a.short) || label || id,
    });
  }
  return out;
}

export function hasPrintedAiMark(row) {
  return printedAiMarks(row).length > 0;
}

function urlLooksAiPage(url) {
  try {
    const u = new URL(url);
    const path = (u.pathname || "") + (u.search || "");
    return AI_PAGE_RE.test(path);
  } catch {
    return AI_PAGE_RE.test(String(url || ""));
  }
}

function urlLooksAiInstrument(url, re) {
  try {
    const u = new URL(url);
    const path = (u.pathname || "") + (u.search || "");
    return re.test(path);
  } catch {
    return re.test(String(url || ""));
  }
}

export function isAiNamed(row) {
  const name = String((row && row.name) || "");
  const slug = String((row && row.slug) || "").toLowerCase();
  if (/(^|[\s./])AI([\s,]|$)/.test(name) || /\bArtificial Intelligence\b/i.test(name)) return true;
  if (slug.endsWith("-ai")) return true;
  return false;
}

/* Retired TLD heuristic. Aviatrix-class .ai hosts are not an AI file. */
export function isAiishNameOrDomain(row) {
  return isAiNamed(row);
}

export function isAiListMember(row) {
  if (!row) return false;
  if (AI_LIST_IDS.has(String(row.list || ""))) return true;
  const lists = row.aiti_lists;
  if (Array.isArray(lists) && lists.some((id) => AI_LIST_IDS.has(String(id || "")))) return true;
  return false;
}

export function isAiFile(row) {
  if (!row) return false;
  return isAiListMember(row);
}

export function printedUrl(url, text) {
  const href = String(url || "").trim();
  if (!/^https?:\/\//i.test(href)) return escapeHtml(text || href);
  const label = text == null || text === "" ? href : text;
  return `<a class="official" href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
}

export function selectAiFiles(rows) {
  return (rows || []).filter(isAiFile);
}

function storedAiFieldUrl(row, key) {
  const field = row && row[`ai_${key}`];
  const fromField = typeof field === "string" ? field : field && (field.url || field.source_url);
  return fromField || instrumentHref(row, key) || "";
}

function storedFirstPartyUrl(row, key) {
  const url = storedAiFieldUrl(row, key);
  if (!url) return "";
  if (!isFirstPartyUrl(url, row && row.domain)) return "";
  return url;
}

function storedAiProcessorListUrl(row) {
  const field = row && row.ai_processors;
  const fromField = typeof field === "string" ? field : field && (field.url || field.source_url);
  const url = fromField || instrumentHref(row, "model_processors") || instrumentHref(row, "processors") || "";
  if (!url) return "";
  if (!isFirstPartyUrl(url, row && row.domain)) return "";
  return url;
}

function storedAiMarksUrl(row) {
  return storedFirstPartyUrl(row, "marks") || storedFirstPartyUrl(row, "certs") || "";
}

function aiPrintOrUrl(printed, url, rec) {
  if (printed) return recordedWall(rec) ? 10 : 20;
  if (url) return 10;
  return 0;
}

export function aiFileFlags(row) {
  const pageUrl = storedAiPageUrl(row);
  const evalsUrl = storedAiInstrumentUrl(row, "evals");
  const incidentsUrl = storedAiInstrumentUrl(row, "incidents");
  const pageRec = row && typeof row.ai_page === "object" ? row.ai_page : null;
  const evalsRec = row && typeof row.ai_evals === "object" ? row.ai_evals : null;
  const incidentsRec = row && typeof row.ai_incidents === "object" ? row.ai_incidents : null;
  return {
    page: aiPrintOrUrl(!!pageUrl, storedFirstPartyUrl(row, "page") || storedFirstPartyUrl(row, "ai"), pageRec),
    marks: hasPrintedAiMark(row) ? 20 : storedAiMarksUrl(row) ? 10 : 0,
    processors: storedAiProcessors(row).length > 0 ? 20 : storedAiProcessorListUrl(row) ? 10 : 0,
    evals: aiPrintOrUrl(!!evalsUrl, storedFirstPartyUrl(row, "evals"), evalsRec),
    incidents: aiPrintOrUrl(!!incidentsUrl, storedFirstPartyUrl(row, "incidents"), incidentsRec),
  };
}

export function aiFileCount(row) {
  const flags = aiFileFlags(row);
  return AI_FILE_KEYS.reduce((n, key) => n + (flags[key] ? 1 : 0), 0);
}

export function aiFileOnWords(row) {
  return `${aiFileCount(row)} on file`;
}

export function aiFileCoverage(row) {
  const flags = aiFileFlags(row);
  const n = aiFileCount(row);
  const legend = "page · standards · processors · evals · incidents";
  const on = AI_FILE_KEYS.filter((k) => flags[k]).map((k) => AI_FILE_LABELS[k]);
  const spoken = on.length ? on.join(" · ") : "not on file";
  return { n, legend, spoken, title: spoken };
}

export function aiFileIndexHtml(row) {
  const flags = aiFileFlags(row);
  const c = aiFileCoverage(row);
  const rules = AI_FILE_KEYS.map((key) => {
    return `<span class="${fileRuleClass(flags[key])}" aria-hidden="true"></span>`;
  }).join("");
  return `<span class="file-index" role="img" aria-label="${escapeHtml(c.spoken)}">${rules}</span>`;
}

export function bindFileMethodToggle() {
  function setView(view, viaUser) {
    const on = view === "method" ? "method" : "file";
    const filePane = $("file-view");
    const methodPane = $("method-view");
    if (filePane) filePane.hidden = on !== "file";
    if (methodPane) methodPane.hidden = on !== "method";
    document.querySelectorAll(".view-toggle button[data-view]").forEach((btn) => {
      const live = btn.getAttribute("data-view") === on;
      btn.classList.toggle("on", live);
      btn.setAttribute("aria-selected", live ? "true" : "false");
    });
    if (viaUser && globalThis.location && globalThis.history && globalThis.history.replaceState) {
      if (on === "method") {
        if (globalThis.location.hash !== "#method") {
          globalThis.history.replaceState(null, "", "#method");
        }
      } else if (globalThis.location.hash === "#method") {
        globalThis.history.replaceState(null, "", globalThis.location.pathname + globalThis.location.search);
      }
    }
  }
  document.querySelectorAll(".view-toggle button[data-view]").forEach((btn) => {
    btn.addEventListener("click", () => setView(btn.getAttribute("data-view"), true));
  });
  if (globalThis.window) {
    globalThis.window.addEventListener("hashchange", () => {
      setView(globalThis.location.hash === "#method" ? "method" : "file", false);
    });
  }
  const start =
    globalThis.location && globalThis.location.hash === "#method" ? "method" : "file";
  setView(start, false);
}

export function fillAitiIssue(el, data, n) {
  if (!el || !data) return;
  const day = fmtDay(data.generated_at);
  const count = Number.isFinite(n) ? n : 0;
  el.textContent = [`issue ${day}`, `${count} files`].filter(Boolean).join(" · ");
}

export function $(id) {
  return document.getElementById(id);
}

export function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function inkIcon(src, prefix = "./") {
  const file = String(src || "").replace(/^\/+/, "").replace(/^favicons\//, "");
  if (!file || file.includes("..") || file.includes("/") || file.includes("\\")) return "";
  const href = `${prefix}favicons/${file}`;
  return `<img class="ink-ico" src="${escapeHtml(href)}" alt="" width="12" height="12" decoding="async" onerror="this.remove()">`;
}

export function nameWithIcon(name, src, prefix = "./") {
  return `${inkIcon(src, prefix)}${escapeHtml(name)}`;
}

export function hostOf(url) {
  try {
    return new URL(url).host.replace(/^www\./, "");
  } catch {
    return "";
  }
}

export function fmtDay(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", {
    timeZone: "America/Los_Angeles",
    day: "numeric",
    month: "short",
    year: "numeric",
  }).replace(",", "");
}

export function fmtWhen(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const day = d.toLocaleDateString("en-GB", {
    timeZone: "America/Los_Angeles",
    day: "numeric",
    month: "short",
    year: "numeric",
  }).replace(",", "");
  const time = d.toLocaleTimeString("en-US", {
    timeZone: "America/Los_Angeles",
    hour: "numeric",
    minute: "2-digit",
  });
  return `${day}, ${time} PT`;
}

export function humanOk() {
  try {
    const raw = sessionStorage.getItem(GATE_KEY);
    if (!raw) return false;
    const t = Number(raw);
    return t && Date.now() - t < GATE_MS;
  } catch {
    return false;
  }
}

export function markHuman() {
  try {
    sessionStorage.setItem(GATE_KEY, String(Date.now()));
  } catch {
    /* ignore */
  }
}

function makeGate(doc) {
  const gate = doc.createElement("div");
  gate.className = "gate";
  gate.id = "gate";
  gate.hidden = true;
  const label = doc.createElement("label");
  label.className = "turn";
  const input = doc.createElement("input");
  input.type = "checkbox";
  input.id = "gate-box";
  const turnBox = doc.createElement("span");
  turnBox.className = "turn-box";
  turnBox.setAttribute("aria-hidden", "true");
  const words = doc.createElement("span");
  words.textContent = "I am human";
  const status = doc.createElement("p");
  status.className = "gate-status";
  status.id = "gate-status";
  label.append(input, turnBox, words);
  gate.append(label, status);
  return gate;
}

function takeGate(doc) {
  const leftover = doc && doc.getElementById("gate");
  if (leftover && leftover.parentNode) leftover.remove();
  return leftover || (doc && makeGate(doc));
}

export function placeGate(gate, after) {
  if (!gate || !after) return;
  after.after(gate);
  gate.hidden = false;
}

export function shutGate(gate) {
  if (gate) gate.hidden = true;
}

export function attachGate({ button, box, status, url } = {}) {
  const doc = globalThis.document;
  let pending = url || (button && button.dataset.url) || "";
  let gate = takeGate(doc) || (box && box.closest(".gate"));
  if (!gate && doc) gate = makeGate(doc);
  box = (gate && gate.querySelector("#gate-box")) || box;
  status = (gate && gate.querySelector("#gate-status")) || status;

  function go(href) {
    if (href) globalThis.window.open(href, "_blank", "noopener,noreferrer");
  }

  function requestStamp(href, after) {
    pending = href || pending;
    if (humanOk()) {
      shutGate(gate);
      go(pending);
      return;
    }
    placeGate(gate, after || button);
    if (status) status.textContent = "";
    if (box) {
      box.checked = false;
      box.disabled = false;
    }
  }

  if (button) {
    const href = url || button.dataset.url || "";
    if (!href) {
      button.hidden = true;
    } else {
      button.hidden = false;
      button.addEventListener("click", () => requestStamp(href, button));
    }
  }

  if (doc) {
    doc.querySelectorAll("a.official").forEach((a) => {
      a.addEventListener("click", (e) => {
        if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
        requestStamp(a.getAttribute("href") || a.href, a);
      });
    });
  }

  if (box) {
    box.addEventListener("change", (e) => {
      if (!e.target.checked) return;
      if (status) status.textContent = "checking…";
      setTimeout(() => {
        markHuman();
        if (status) status.textContent = "verified · 30 min";
        if (box) {
          box.checked = true;
          box.disabled = true;
        }
        go(pending);
        shutGate(gate);
      }, 250);
    });
  }
}

export function fillIssue(el, data, extra) {
  if (!el || !data) return;
  const companies = data.companies || [];
  const onFile = companies.filter((c) => c.found).length;
  const notOn = companies.length - onFile;
  const day = fmtDay(data.generated_at);
  const when = fmtWhen(data.generated_at);
  el.textContent = [
    `issue ${day}`,
    `${onFile} on file`,
    `${notOn} not on file`,
    `last probed ${when}`,
    extra || "",
  ]
    .filter(Boolean)
    .join(" · ");
}

export function coverageLine(cov) {
  if (!cov) return "";
  const t = cov.tiers || {};
  const L = cov.links || {};
  const top = (cov.top_processors || [])
    .map((p) => `${p.id} ${p.n}`)
    .join(", ");
  const edges = top
    ? `${cov.edges} named-processor edges · top ${top}`
    : `${cov.edges} named-processor edges`;
  return [
    `${cov.companies} companies`,
    `${cov.years} founding years (Wikipedia/Wikidata)`,
    `${cov.certs_companies} with marks seen in public HTML`,
    edges,
    `${L.security_txt} security.txt`,
    `${L.dpa} DPA`,
    `${L.privacy} privacy`,
    `${L.status} status`,
    `${L.bug_bounty} bounty`,
    `${L.subprocessors} processor pages (link ≠ parsed names)`,
    `silent ${t.silent} · thin ${t.thin} · on file ${t["on-file"]} · substantial ${t.substantial} · complete ${t.complete}`,
  ].join(" · ");
}

export function tierClass(tier) {
  return tier === "silent" ? "tier-silent" : "tier-word";
}

export function displayTier(tier) {
  if (tier === "on-file") return "on file";
  if (tier === "complete") return "public file complete";
  return tier || "silent";
}

export function displayFileState(tier) {
  if (tier === "on-file") return "on file";
  return tier || "silent";
}
