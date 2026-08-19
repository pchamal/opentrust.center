/* Shared clerk utilities. */

export const GATE_KEY = "ot_human_v1";
export const GATE_MS = 30 * 60 * 1000;
export const DATA_V = "2026-08-19T22:51:33Z";
export const FILE_KEYS = ["page", "marks", "dpa", "subprocessors", "years"];

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

export function fileMeterHtml(row) {
  const flags = fileFlags(row);
  const on = FILE_KEYS.filter((k) => flags[k]);
  const legend = FILE_KEYS.join(" · ");
  const listed = on.length ? on.join(" · ") + " on file" : "none on file";
  const aria = `${legend} · ${listed}`;
  const boxes = FILE_KEYS.map((k) => {
    const cls = flags[k] ? ' class="on"' : "";
    return `<span${cls} title="${k}"></span>`;
  }).join("");
  return `<span class="file-meter" title="${escapeHtml(aria)}" aria-label="${escapeHtml(aria)}">${boxes}</span>`;
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
  el.textContent = `issue ${day} PT · ${onFile} on file · ${notOn} not on file · last probed ${when}${extra ? " · " + extra : ""}`;
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
  return tier === "on-file" ? "on file" : tier || "silent";
}
