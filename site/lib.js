/* Shared clerk utilities. */

export const GATE_KEY = "ot_human_v1";
export const GATE_MS = 30 * 60 * 1000;
export const DATA_V = "2026-08-20T21:50:00Z";
export const FILE_KEYS = ["page", "marks", "dpa", "subprocessors", "years"];
export const AI_FILE_KEYS = ["page", "marks", "processors", "evals", "incidents"];
export const AI_FILE_LABELS = {
  page: "page",
  marks: "marks",
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
/* AI product names already on the register that are not .ai / “AI” / AI-50. */
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
]);

export function dataUrl(path) {
  const v = DATA_V ? encodeURIComponent(DATA_V) : "";
  if (!v) return path;
  return path + (path.includes("?") ? "&" : "?") + "v=" + v;
}

export function fileFlags(row) {
  if (row && row.file && typeof row.file === "object") {
    return {
      page: !!row.file.page,
      marks: !!row.file.marks,
      dpa: !!row.file.dpa,
      subprocessors: !!row.file.subprocessors,
      years: !!row.file.years,
    };
  }
  const f = (row && row.disclosure && row.disclosure.factors) || (row && row.factors) || {};
  return {
    page: !!f.page,
    marks: !!(f.marks || (row && row.certs && row.certs.length) || (row && row.attestations && row.attestations.length)),
    dpa: !!f.dpa,
    subprocessors: !!(f.processors || f.subprocessors),
    years: !!(row && (row.founded_year || f.years)),
  };
}

export function fileCoverage(row) {
  const flags = fileFlags(row);
  const n = FILE_KEYS.filter((k) => flags[k]).length;
  const den = `${n} of 5`;
  const legend = "page, marks, DPA, subprocessors, years";
  const sentence = `public evidence located in ${den} checked categories`;
  return { n, den, legend, sentence, title: `${sentence} (${legend})` };
}

export function fileCoverageHtml(row) {
  const c = fileCoverage(row);
  return `<span class="file-cov" title="${escapeHtml(c.title)}">${escapeHtml(c.den)}</span>`;
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

export function isAiSystemProcessor(proc, ownerSlug) {
  if (!proc) return false;
  const slug = String(proc.slug || "").toLowerCase();
  const owner = String(ownerSlug || "").toLowerCase();
  if (slug && owner && slug === owner) return false;
  if (slug && NOT_AI_SYSTEM_PROCESSOR_SLUGS.has(slug)) return false;
  const name = normalizeProcessorName(proc.name || proc);
  if (HOSTING_PROCESSOR_NAME_RE.test(name)) return false;
  if (slug && AI_SYSTEM_PROCESSOR_SLUGS.has(slug)) return true;
  return AI_SYSTEM_PROCESSOR_NAME_RE.test(name);
}

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

export function isAiishNameOrDomain(row) {
  const name = String((row && row.name) || "");
  const domain = String((row && row.domain) || "").toLowerCase();
  const slug = String((row && row.slug) || "").toLowerCase();
  if (domain.endsWith(".ai")) return true;
  if (/(^|[\s/])AI([\s,]|$)/.test(name) || /\bArtificial Intelligence\b/i.test(name)) return true;
  if (slug.endsWith("-ai")) return true;
  return false;
}

export function isAiFile(row) {
  if (!row) return false;
  if (hasPrintedAiMark(row)) return true;
  if ((row.list || "") === "forbes-ai-50-2025") return true;
  if (isAiishNameOrDomain(row)) return true;
  if (AI_PRODUCT_SLUGS.has(String(row.slug || ""))) return true;
  return false;
}

export function selectAiFiles(rows) {
  return (rows || []).filter(isAiFile);
}

export function aiFileFlags(row) {
  const urls = collectedUrls(row);
  return {
    page: !!storedAiPageUrl(row),
    marks: hasPrintedAiMark(row),
    processors: storedAiProcessors(row).length > 0,
    evals: urls.some((u) => urlLooksAiInstrument(u, AI_EVALS_RE)),
    incidents: urls.some((u) => urlLooksAiInstrument(u, AI_INCIDENTS_RE)),
  };
}

export function aiFileCount(row) {
  const flags = aiFileFlags(row);
  return AI_FILE_KEYS.reduce((n, key) => n + (flags[key] ? 1 : 0), 0);
}

export function aiFileCoverage(row) {
  const flags = aiFileFlags(row);
  const n = aiFileCount(row);
  const legend = "page · marks · processors · evals · incidents";
  const on = AI_FILE_KEYS.filter((k) => flags[k]).map((k) => AI_FILE_LABELS[k]);
  const spoken = on.length ? on.join(" · ") : "not on file";
  return { n, legend, spoken, title: spoken };
}

export function aiFileIndexHtml(row) {
  const flags = aiFileFlags(row);
  const c = aiFileCoverage(row);
  const rules = AI_FILE_KEYS.map((key) => {
    const cls = flags[key] ? "file-rule on" : "file-rule";
    return `<span class="${cls}" aria-hidden="true"></span>`;
  }).join("");
  return `<span class="file-index" role="img" aria-label="${escapeHtml(c.spoken)}">${rules}</span>`;
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

export function attachGate({ button, box, status, url }) {
  let pending = url || (button && button.dataset.url) || "";

  function reveal() {
    const gate = box && box.closest(".gate");
    if (gate) gate.hidden = false;
  }

  function showVerified() {
    reveal();
    if (status) status.textContent = "verified · 30 min";
    if (box) {
      box.checked = true;
      box.disabled = true;
    }
  }

  function go(href) {
    if (href) window.open(href, "_blank", "noopener,noreferrer");
  }

  function requestStamp(href) {
    pending = href || pending;
    if (humanOk()) {
      go(pending);
      return;
    }
    reveal();
    if (status) status.textContent = "";
    if (box) {
      box.checked = false;
      box.disabled = false;
    }
  }

  if (humanOk()) showVerified();

  if (button) {
    const href = url || button.dataset.url || "";
    if (!href) {
      button.hidden = true;
    } else {
      button.hidden = false;
      button.addEventListener("click", () => requestStamp(href));
    }
  }

  document.querySelectorAll("a.official").forEach((a) => {
    a.addEventListener("click", (e) => {
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      requestStamp(a.getAttribute("href") || a.href);
    });
  });

  if (box) {
    box.addEventListener("change", (e) => {
      if (!e.target.checked) return;
      if (status) status.textContent = "checking…";
      setTimeout(() => {
        markHuman();
        showVerified();
        go(pending);
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
