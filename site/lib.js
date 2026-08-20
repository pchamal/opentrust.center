/* Shared clerk utilities. */

export const GATE_KEY = "ot_human_v1";
export const GATE_MS = 30 * 60 * 1000;
export const DATA_V = "2026-08-20T19:50:26Z";
export const FILE_KEYS = ["page", "marks", "dpa", "subprocessors", "years"];
export const FILE_LABELS = {
  page: "page",
  marks: "marks",
  dpa: "DPA",
  subprocessors: "subprocessors",
  years: "years",
};

export function dataUrl(path) {
  const v = DATA_V ? encodeURIComponent(DATA_V) : "";
  if (!v) return path;
  return path + (path.includes("?") ? "&" : "?") + "v=" + v;
}

function instrumentUrl(row, key) {
  const rec = row && row.instruments && row.instruments[key];
  return !!(rec && rec.url);
}

export function hasNamedMarks(row) {
  const atts = ((row && row.attestations) || []).filter((a) => a && (a.name || a.short));
  const certs = ((row && row.certs) || []).filter(Boolean);
  if (atts.length || certs.length) return true;
  return !!(row && row.fedramp);
}

export function fileFlags(row) {
  const page = !!(
    (row && row.found && (row.trust_url || row.final_url)) ||
    instrumentUrl(row, "trust") ||
    instrumentUrl(row, "security")
  );
  const procs = (row && row.processors) || [];
  return {
    page,
    marks: hasNamedMarks(row),
    dpa: instrumentUrl(row, "dpa"),
    subprocessors: procs.length > 0 || instrumentUrl(row, "subprocessors"),
    years: !!(row && row.founded_year),
  };
}

export function fileCount(row) {
  const flags = fileFlags(row);
  return FILE_KEYS.reduce((n, key) => n + (flags[key] ? 1 : 0), 0);
}

export function fileCoverage(row) {
  const flags = fileFlags(row);
  const n = fileCount(row);
  const legend = "page · marks · DPA · subprocessors · years";
  const on = FILE_KEYS.filter((k) => flags[k]).map((k) => FILE_LABELS[k]);
  const spoken = on.length ? on.join(" · ") : "not on file";
  return { n, legend, spoken, title: spoken };
}

export function fileIndexHtml(row) {
  const flags = fileFlags(row);
  const c = fileCoverage(row);
  const rules = FILE_KEYS.map((key) => {
    const cls = flags[key] ? "file-rule on" : "file-rule";
    return `<span class="${cls}" aria-hidden="true"></span>`;
  }).join("");
  return `<span class="file-index" role="img" aria-label="${escapeHtml(c.spoken)}">${rules}</span>`;
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
