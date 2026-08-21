import {
  $,
  escapeHtml,
  fillIssue,
  fileCount,
  fileIndexHtml,
  dataUrl,
  nameWithIcon,
  printedUrl,
} from "./lib.js";
import {
  parseFinder,
  stripFinderToken,
  normalizeTier,
  normalizeList,
  normalizeFedramp,
  echoWords,
} from "./finder.js";

const SORTS = new Set(["rank", "name", "host", "file", "marks", "probed"]);
const SORT_ALIAS = {
  "#": "rank",
  num: "rank",
  number: "rank",
  domain: "host",
  tier: "file",
};
export const PAGE_SIZE = 50;
const DEFAULT_DIR = {
  rank: "asc",
  name: "asc",
  host: "asc",
  file: "desc",
  marks: "asc",
  probed: "desc",
};
const state = {
  rows: [],
  generatedAt: null,
  q: "",
  url: { tier: "all", list: "all", fedramp: "all" },
  sort: "name",
  dir: "asc",
  sorted: true,
  page: 1,
  selected: "",
};

export function normalizeSort(value) {
  const v = String(value || "").trim().toLowerCase();
  const key = SORT_ALIAS[v] || v;
  return SORTS.has(key) ? key : "";
}

export function normalizeDir(value, sort) {
  const v = String(value || "").trim().toLowerCase();
  if (v === "asc" || v === "ascending") return "asc";
  if (v === "desc" || v === "descending") return "desc";
  return DEFAULT_DIR[sort] || "asc";
}

export function clickSort(current, key) {
  const sort = normalizeSort(key);
  if (!sort) return { sort: current.sort, dir: current.dir, sorted: current.sorted };
  if (current.sorted && current.sort === sort) {
    return { sort, dir: current.dir === "asc" ? "desc" : "asc", sorted: true };
  }
  return { sort, dir: DEFAULT_DIR[sort], sorted: true };
}

function rankOf(row) {
  return row && row.rank != null ? row.rank : 9999;
}

function cmpText(a, b) {
  return String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base" });
}

export function marksCount(row) {
  const stamp = !!(row && row.fedramp);
  const atts = ((row && row.attestations) || []).filter((a) => a && (a.name || a.short));
  let names = (atts.length ? atts : ((row && row.certs) || []).map((name) => ({ name, id: null }))).slice();
  if (stamp) names = names.filter((a) => !isFedrampCite(a));
  return names.length + (stamp ? 1 : 0);
}

function marksSortKey(row) {
  const stamp = !!(row && row.fedramp);
  let names = namedMarks(row);
  if (stamp) names = names.filter((a) => !isFedrampCite(a));
  const labels = [];
  if (stamp) labels.push("fedramp");
  for (const a of names) {
    const label = markLabel(a);
    if (label) labels.push(label);
  }
  return labels.join(" · ");
}

function cmpMarksText(a, b) {
  const left = marksSortKey(a);
  const right = marksSortKey(b);
  if (!left && !right) return 0;
  if (!left) return 1;
  if (!right) return -1;
  return cmpText(left, right);
}

export function compareRows(a, b, key) {
  switch (key) {
    case "rank":
      return rankOf(a) - rankOf(b);
    case "name":
      return cmpText(a && a.name, b && b.name);
    case "host":
    case "domain":
      return cmpText(a && a.domain, b && b.domain);
    case "file":
    case "tier":
      return fileCount(a) - fileCount(b);
    case "marks":
      return cmpMarksText(a, b);
    case "probed":
      return probedMs(a) - probedMs(b);
    default:
      return cmpText(a && a.name, b && b.name);
  }
}

function probedMs(row) {
  const raw = row && (row.probed_at || "");
  const t = Date.parse(raw);
  return Number.isFinite(t) ? t : 0;
}

export function arrangeRows(rows, sort, dir) {
  const key = normalizeSort(sort) || "name";
  const sign = dir === "desc" ? -1 : 1;
  return rows.slice().sort((a, b) => {
    const c = compareRows(a, b, key);
    if (c) return c * sign;
    return cmpText(a && a.name, b && b.name);
  });
}

/* Default: Company A–Z. */
export function defaultRows(rows) {
  return arrangeRows(rows, "name", "asc");
}

export function pageCount(total, size = PAGE_SIZE) {
  return Math.max(1, Math.ceil((total || 0) / size));
}

export function windowRows(rows, page, size = PAGE_SIZE) {
  const pages = pageCount(rows.length, size);
  const p = Math.min(Math.max(1, page || 1), pages);
  const start = (p - 1) * size;
  return { page: p, pages, start, rows: rows.slice(start, start + size) };
}

function hay(row) {
  const marks = (row.certs || []).join(" ");
  const att = (row.attestations || []).map((a) => a.name || a.id).join(" ");
  const fr = row.fedramp;
  const fed = fr
    ? ["fedramp", fr.highest, ...(fr.levels || []), ...(fr.raw_levels || [])].filter(Boolean).join(" ")
    : "";
  return [row.name, row.domain, row.slug, marks, att, fed]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function active() {
  const parsed = parseFinder(state.q);
  return {
    q: parsed.q,
    tier: parsed.tier !== "all" ? parsed.tier : state.url.tier,
    list: parsed.list !== "all" ? parsed.list : state.url.list,
    fedramp: parsed.fedramp !== "all" ? parsed.fedramp : state.url.fedramp,
  };
}

function apply() {
  const f = active();
  const q = f.q.trim().toLowerCase();
  const found = state.rows.filter((row) => {
    if (f.tier !== "all" && row.tier !== f.tier) return false;
    if (f.list === "cloud100" && row.list !== "cloud100") return false;
    if (f.list === "enterprise" && row.list !== "enterprise") return false;
    if (f.fedramp !== "all") {
      if (!row.fedramp) return false;
      if (f.fedramp !== "any") {
        const levels = (row.fedramp.levels || []).map((lv) => String(lv).toLowerCase());
        if (!levels.includes(f.fedramp)) return false;
      }
    }
    if (!q) return true;
    return hay(row).includes(q);
  });
  if (!state.sorted) return defaultRows(found);
  return arrangeRows(found, state.sort, state.dir);
}

function guessDomain(q) {
  const clean = q.trim().toLowerCase().replace(/[^a-z0-9.\- ]+/g, "");
  if (!clean) return "";
  if (clean.includes(".")) return clean.replace(/\s+/g, "");
  const slug = clean.replace(/\s+/g, "");
  return slug ? slug + ".com" : "";
}

function isFedrampCite(a) {
  const id = String((a && a.id) || "").toLowerCase();
  const name = String((a && (a.short || a.name)) || "").toLowerCase();
  return id === "fedramp" || name.startsWith("fedramp");
}

function fedrampMark(row) {
  const fr = row.fedramp;
  if (!fr) return "";
  const url = fr.marketplace || "";
  if (!url) return `<span class="fr-mark">fedramp</span>`;
  return `<a class="fr-mark" href="${escapeHtml(url)}" target="_blank" rel="noopener">fedramp</a>`;
}

function markLabel(a) {
  return String((a && (a.short || a.name)) || "").toLowerCase();
}

function markPriority(a) {
  const s = markLabel(a);
  if (/^soc\s*2/.test(s)) return 0;
  if (/^iso\s*27001/.test(s)) return 1;
  if (/^pci/.test(s)) return 2;
  if (/^hipaa/.test(s)) return 3;
  return 20;
}

function namedMarks(row) {
  const atts = ((row && row.attestations) || []).filter((a) => a && (a.name || a.short));
  const names = (atts.length ? atts : ((row && row.certs) || []).map((name) => ({ name, id: null }))).slice();
  names.sort((a, b) => {
    const p = markPriority(a) - markPriority(b);
    if (p) return p;
    return markLabel(a).localeCompare(markLabel(b), undefined, { sensitivity: "base" });
  });
  return names;
}

export function marksCell(row) {
  const stamp = fedrampMark(row);
  let names = namedMarks(row);
  if (stamp) names = names.filter((a) => !isFedrampCite(a));
  if (!names.length) {
    return stamp || `<span class="absent">not on file</span>`;
  }
  const line = names
    .map((a) => {
      const label = escapeHtml(markLabel(a));
      const id = String((a && a.id) || "").trim();
      return id
        ? `<a class="mark-chip" href="./attestations.html#${encodeURIComponent(id)}">${label}</a>`
        : `<span class="mark-chip">${label}</span>`;
    })
    .join(" · ");
  return stamp ? stamp + (line ? " · " + line : "") : `<span class="mark-line">${line}</span>`;
}

function syncUrl() {
  const f = active();
  const params = new URLSearchParams();
  const q = state.q.trim();
  if (q) params.set("q", q);
  if (f.fedramp !== "all") params.set("fedramp", f.fedramp);
  const parsed = parseFinder(state.q);
  if (parsed.tier === "all" && f.tier !== "all") params.set("tier", f.tier);
  if (parsed.list === "all" && f.list !== "all") params.set("list", f.list);
  if (state.sorted) {
    params.set("sort", state.sort);
    params.set("dir", state.dir);
  }
  if (state.page > 1) params.set("page", String(state.page));
  const qs = params.toString();
  const next = (qs ? "?" + qs : "") + window.location.hash;
  const path = window.location.pathname + next;
  if (path !== window.location.pathname + window.location.search + window.location.hash) {
    history.replaceState(null, "", path || window.location.pathname);
  }
}

function paintHeaders() {
  const heads = document.querySelectorAll("#reg thead th[data-sort]");
  heads.forEach((th) => {
    const key = th.getAttribute("data-sort");
    const live = state.sorted && state.sort === key;
    const dir = state.dir;
    th.classList.toggle("on", live);
    th.setAttribute("aria-sort", live ? (dir === "desc" ? "descending" : "ascending") : "none");
  });
}

function renderEcho() {
  const el = $("queryline");
  if (!el) return;
  const bits = echoWords(active());
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

function renderPager(shown, total) {
  const el = $("pager");
  if (!el) return;
  if (!total) {
    el.hidden = true;
    el.innerHTML = "";
    return;
  }
  const pages = pageCount(total);
  if (state.page > pages) state.page = pages;
  el.hidden = false;
  const start = (state.page - 1) * PAGE_SIZE + 1;
  const end = start + shown - 1;
  el.innerHTML = `
    <button type="button" data-page="prev" ${state.page <= 1 ? "disabled" : ""}>Previous</button>
    <span>Page ${state.page} of ${pages} · ${start}–${end} of ${total}</span>
    <button type="button" data-page="next" ${state.page >= pages ? "disabled" : ""}>Next</button>
  `;
}

function render() {
  const rows = apply();
  const f = active();
  const q = f.q.trim();
  const typed = state.q.trim();
  const table = $("reg");
  const empty = $("empty");
  const miss = $("miss");
  const count = $("countline");
  const windowed = windowRows(rows, state.page);
  if (windowed.page !== state.page) state.page = windowed.page;
  count.textContent = state.rows.length
    ? `showing ${rows.length} of ${state.rows.length}`
    : "";
  renderEcho();
  paintHeaders();
  syncUrl();

  const legend = $("file-legend");
  if (!state.rows.length) {
    table.hidden = true;
    if (legend) legend.hidden = true;
    miss.hidden = true;
    const actions = $("miss-actions");
    if (actions) actions.hidden = true;
    empty.hidden = false;
    renderPager(0, 0);
    return;
  }
  empty.hidden = true;

  if (typed && !rows.length) {
    table.hidden = true;
    if (legend) legend.hidden = true;
    miss.hidden = false;
    renderPager(0, 0);
    $("miss-title").textContent = "Not in the index.";
    const domain = guessDomain(q);
    const asked = typed || q;
    $("miss-body").textContent = asked
      ? `No public file matches “${asked}”. Missing from this index is inconclusive — a page may exist under another URL.`
      : "No public file matches this query." ;
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
  if (legend) legend.hidden = false;
  const body = $("reg-body");
  const view = windowed.rows;
  renderPager(view.length, rows.length);
  body.innerHTML = view
    .map((row) => {
      const selected = state.selected === row.slug ? ' aria-selected="true"' : "";
      return `<tr class="folio"${selected} data-slug="${escapeHtml(row.slug)}" tabindex="0" aria-label="Open dossier: ${escapeHtml(row.name)}">
        <td class="name"><a href="./c/${encodeURIComponent(row.slug)}.html">${nameWithIcon(row.name, row.favicon)}</a></td>
        <td class="domain">${printedUrl(row.domain || "", row.domain || "")}</td>
        <td class="file">${fileIndexHtml(row)}</td>
        <td class="marks">${marksCell(row)}</td>
      </tr>`;
    })
    .join("");
}

function clearToken(kind) {
  state.q = stripFinderToken(state.q, kind);
  const input = $("q");
  if (input) input.value = state.q;
  if (kind === "tier") state.url.tier = "all";
  if (kind === "list") state.url.list = "all";
  if (kind === "fedramp") state.url.fedramp = "all";
  state.page = 1;
  render();
}

function resetQuery() {
  state.q = "";
  state.url = { tier: "all", list: "all", fedramp: "all" };
  state.page = 1;
  const input = $("q");
  if (input) input.value = "";
  render();
}

function bind() {
  $("finder").addEventListener("submit", (e) => {
    e.preventDefault();
    state.q = $("q").value;
    state.page = 1;
    render();
  });
  $("q").addEventListener("input", (e) => {
    state.q = e.target.value;
    state.page = 1;
    render();
  });
  const pager = $("pager");
  if (pager) {
    pager.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-page]");
      if (!btn || btn.disabled) return;
      const pages = pageCount(apply().length);
      if (btn.getAttribute("data-page") === "prev") state.page = Math.max(1, state.page - 1);
      if (btn.getAttribute("data-page") === "next") state.page = Math.min(pages, state.page + 1);
      render();
      const table = $("reg");
      if (table) table.scrollIntoView({ block: "start", behavior: "auto" });
    });
  }
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
  const head = document.querySelector("#reg thead");
  if (head) {
    head.addEventListener("click", (e) => {
      const th = e.target.closest("th[data-sort]");
      if (!th) return;
      const next = clickSort(state, th.getAttribute("data-sort"));
      state.sort = next.sort;
      state.dir = next.dir;
      state.sorted = next.sorted;
      state.page = 1;
      render();
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

async function load() {
  bind();
  const params = new URLSearchParams(window.location.search);
  if (params.get("c")) {
    window.location.replace(`./c/${encodeURIComponent(params.get("c"))}.html`);
    return;
  }
  if (params.get("q")) {
    state.q = params.get("q");
    $("q").value = state.q;
  }
  if (params.get("fedramp")) {
    state.url.fedramp = normalizeFedramp(params.get("fedramp"));
  }
  if (params.get("tier")) {
    state.url.tier = normalizeTier(params.get("tier"));
  }
  if (params.get("list")) {
    state.url.list = normalizeList(params.get("list"));
  }
  const sort = normalizeSort(params.get("sort"));
  if (sort) {
    state.sort = sort;
    state.dir = normalizeDir(params.get("dir"), sort);
    state.sorted = true;
  }
  const page = Number(params.get("page") || "1");
  if (Number.isFinite(page) && page >= 1) state.page = Math.floor(page);
  try {
    const res = await fetch(dataUrl("./data.json"), { cache: "no-store" });
    if (!res.ok) throw new Error(String(res.status));
    const data = await res.json();
    const companies = Array.isArray(data.companies) ? data.companies : [];
    state.rows = companies.slice().sort((a, b) => {
      const ar = a.rank == null ? 9999 : a.rank;
      const br = b.rank == null ? 9999 : b.rank;
      if (ar !== br) return ar - br;
      return String(a.name).localeCompare(String(b.name));
    });
    state.generatedAt = data.generated_at || null;
    fillIssue($("issue"), data);
  } catch {
    state.rows = [];
  }
  render();
}

if (typeof window !== "undefined") {
  load();
}
