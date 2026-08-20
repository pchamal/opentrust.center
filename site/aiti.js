import {
  $,
  escapeHtml,
  fillAitiIssue,
  dataUrl,
  selectAiFiles,
  printedAiMarks,
  hasPrintedAiMark,
  aiFileIndexHtml,
  aiFileCount,
  printedUrl,
} from "./lib.js";
import { parseFinder, stripFinderToken, echoWords } from "./finder.js";

const state = {
  rows: [],
  generatedAt: null,
  q: "",
  selected: "",
};

function cmpText(a, b) {
  return String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base" });
}

function hay(row) {
  const marks = printedAiMarks(row)
    .map((a) => [a.id, a.name, a.short].filter(Boolean).join(" "))
    .join(" ");
  return [row.name, row.domain, row.slug, marks]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

export function aiMarksCell(row) {
  const names = printedAiMarks(row);
  if (!names.length) {
    return `<span class="absent">not on file</span>`;
  }
  const line = names
    .map((a) => {
      const label = escapeHtml(String(a.short || a.name).toLowerCase());
      const id = String((a && a.id) || "").trim();
      return id
        ? `<a class="mark-chip" href="./attestations.html#${encodeURIComponent(id)}">${label}</a>`
        : `<span class="mark-chip">${label}</span>`;
    })
    .join(" · ");
  return `<span class="mark-line">${line}</span>`;
}

/* Empty and thin files first so the first screen is not a complete-file strip. */
export function defaultAiRows(rows) {
  return (rows || []).slice().sort((a, b) => {
    const c = aiFileCount(a) - aiFileCount(b);
    if (c) return c;
    const silent = Number((a && a.tier) !== "silent") - Number((b && b.tier) !== "silent");
    if (silent) return silent;
    return cmpText(a && a.name, b && b.name);
  });
}

function apply() {
  const parsed = parseFinder(state.q);
  const q = parsed.q.trim().toLowerCase();
  const found = state.rows.filter((row) => {
    if (!q) return true;
    return hay(row).includes(q);
  });
  return defaultAiRows(found);
}

function guessDomain(q) {
  const clean = q.trim().toLowerCase().replace(/[^a-z0-9.\- ]+/g, "");
  if (!clean) return "";
  if (clean.includes(".")) return clean.replace(/\s+/g, "");
  const slug = clean.replace(/\s+/g, "");
  return slug ? slug + ".com" : "";
}

function syncUrl() {
  const params = new URLSearchParams();
  const q = state.q.trim();
  if (q) params.set("q", q);
  const qs = params.toString();
  const next = (qs ? "?" + qs : "") + window.location.hash;
  const path = window.location.pathname + next;
  if (path !== window.location.pathname + window.location.search + window.location.hash) {
    history.replaceState(null, "", path || window.location.pathname);
  }
}

function renderEcho() {
  const el = $("queryline");
  if (!el) return;
  const bits = echoWords(parseFinder(state.q));
  if (!bits.length && !state.q.trim()) {
    el.hidden = true;
    el.innerHTML = "";
    return;
  }
  if (!bits.length) {
    el.hidden = true;
    el.innerHTML = "";
    return;
  }
  el.hidden = false;
  el.innerHTML = bits
    .map((b, i) => {
      const sep = i ? `<span class="sep"> · </span>` : "";
      return `${sep}<button type="button" data-clear="${escapeHtml(b.kind)}">${escapeHtml(b.label)}</button>`;
    })
    .join("");
}

function render() {
  const rows = apply();
  const typed = state.q.trim();
  const table = $("reg");
  const empty = $("empty");
  const miss = $("miss");
  const count = $("countline");
  const n = state.rows.length;
  count.textContent = n ? `showing ${rows.length} of ${n}` : "";
  renderEcho();
  syncUrl();

  if (!state.rows.length) {
    table.hidden = true;
    miss.hidden = true;
    const actions = $("miss-actions");
    if (actions) actions.hidden = true;
    empty.hidden = false;
    return;
  }
  empty.hidden = true;

  if (typed && !rows.length) {
    table.hidden = true;
    miss.hidden = false;
    $("miss-title").textContent = "Not in the index.";
    const parsed = parseFinder(state.q);
    const q = parsed.q.trim();
    const domain = guessDomain(q);
    const asked = typed || q;
    $("miss-body").textContent = asked
      ? `No public file matches “${asked}”. Missing from this index is inconclusive — a page may exist under another URL.`
      : "No public file matches this query.";
    const guesses = domain
      ? [
          `https://trust.${domain}`,
          `https://security.${domain}`,
          `https://${domain}/trust`,
          `https://${domain}/trust-center`,
          `https://${domain}/security`,
        ]
      : [];
    $("guesses").innerHTML = guesses
      .map((u) => `<li><a href="${escapeHtml(u)}" target="_blank" rel="noopener"><code>${escapeHtml(u)}</code></a></li>`)
      .join("");
    const actions = $("miss-actions");
    const look = $("miss-look");
    const req = $("miss-request");
    if (actions) actions.hidden = false;
    const brand = (domain || q || typed).replace(/\.[a-z]{2,}$/i, "");
    const query = `${q || typed} trust center OR "trust profile" OR "trust.${brand}" OR /security`;
    if (look) {
      look.href = `https://duckduckgo.com/?q=${encodeURIComponent(query)}`;
      look.hidden = false;
    }
    if (req) {
      const params = new URLSearchParams();
      params.set("title", `request: ${q || typed}`);
      params.set("labels", "request");
      req.href = `https://github.com/pchamal/opentrust.center/issues/new?${params.toString()}`;
      req.hidden = false;
    }
    return;
  }

  miss.hidden = true;
  const actions = $("miss-actions");
  if (actions) actions.hidden = true;
  table.hidden = false;
  const body = $("reg-body");
  body.innerHTML = rows
    .map((row, i) => {
      const n = String(i + 1).padStart(3, "0");
      const selected = state.selected === row.slug ? ' aria-selected="true"' : "";
      return `<tr class="folio"${selected} data-slug="${escapeHtml(row.slug)}" tabindex="0" aria-label="Open dossier: ${escapeHtml(row.name)}">
        <td class="num">${escapeHtml(n)}</td>
        <td class="name"><a href="./c/${encodeURIComponent(row.slug)}.html">${escapeHtml(row.name)}</a></td>
        <td class="domain">${printedUrl(row.domain || "", row.domain || "")}</td>
        <td class="file-cell">${aiFileIndexHtml(row)}</td>
        <td class="marks">${aiMarksCell(row)}</td>
      </tr>`;
    })
    .join("");
}

function clearToken(kind) {
  state.q = stripFinderToken(state.q, kind);
  const input = $("q");
  if (input) input.value = state.q;
  render();
}

function resetQuery() {
  state.q = "";
  const input = $("q");
  if (input) input.value = "";
  render();
}

function bind() {
  $("finder").addEventListener("submit", (e) => {
    e.preventDefault();
    state.q = $("q").value;
    render();
  });
  $("q").addEventListener("input", (e) => {
    state.q = e.target.value;
    render();
  });
  const reset = $("miss-reset");
  if (reset) reset.addEventListener("click", resetQuery);
  const echo = $("queryline");
  if (echo) {
    echo.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-clear]");
      if (!btn) return;
      clearToken(btn.getAttribute("data-clear"));
    });
  }
  $("reg-body").addEventListener("click", (e) => {
    if (e.target.closest("a") || e.target.closest("details")) return;
    const tr = e.target.closest("tr");
    if (!tr) return;
    const slug = tr.getAttribute("data-slug");
    if (slug) {
      state.selected = slug;
      window.location.href = `./c/${encodeURIComponent(slug)}.html`;
    }
  });
  $("reg-body").addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const tr = e.target.closest("tr");
    if (!tr) return;
    const slug = tr.getAttribute("data-slug");
    if (slug) window.location.href = `./c/${encodeURIComponent(slug)}.html`;
  });
}

function registerQuery(params) {
  return params.get("tier") || params.get("list") || params.get("fedramp") || params.get("page") || params.get("sort");
}

async function load() {
  bind();
  const params = new URLSearchParams(window.location.search);
  if (params.get("c")) {
    window.location.replace(`./c/${encodeURIComponent(params.get("c"))}.html`);
    return;
  }
  if (registerQuery(params)) {
    window.location.replace(`./companies.html${window.location.search}${window.location.hash}`);
    return;
  }
  if (params.get("q")) {
    state.q = params.get("q");
    $("q").value = state.q;
  }
  try {
    const res = await fetch(dataUrl("./data.json"), { cache: "no-store" });
    if (!res.ok) throw new Error(String(res.status));
    const data = await res.json();
    const companies = Array.isArray(data.companies) ? data.companies : [];
    state.rows = selectAiFiles(companies);
    state.generatedAt = data.generated_at || null;
    fillAitiIssue($("issue"), data, state.rows.length);
  } catch {
    state.rows = [];
  }
  render();
}

export { hasPrintedAiMark, state };

if (typeof window !== "undefined") {
  load();
}
