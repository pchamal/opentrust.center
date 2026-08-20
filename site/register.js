import {
  $,
  escapeHtml,
  fillIssue,
  displayTier,
  tierClass,
  dataUrl,
  fileMeterHtml,
} from "./lib.js";
import {
  parseFinder,
  stripFinderToken,
  normalizeTier,
  normalizeList,
  normalizeFedramp,
  echoWords,
} from "./finder.js";

const SORTS = new Set(["rank", "name", "domain", "tier", "marks"]);
const DEFAULT_DIR = {
  rank: "asc",
  name: "asc",
  domain: "asc",
  tier: "desc",
  marks: "desc",
};
const TIER_ORDER = {
  silent: 0,
  thin: 1,
  "on-file": 2,
  substantial: 3,
  complete: 4,
};

const state = {
  rows: [],
  generatedAt: null,
  q: "",
  url: { tier: "all", list: "all", fedramp: "all" },
  sort: "rank",
  dir: "asc",
  sorted: false,
};

export function normalizeSort(value) {
  const v = String(value || "").trim().toLowerCase();
  if (v === "#" || v === "num" || v === "number") return "rank";
  return SORTS.has(v) ? v : "";
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

export function compareRows(a, b, key) {
  switch (key) {
    case "rank":
      return rankOf(a) - rankOf(b);
    case "name":
      return cmpText(a && a.name, b && b.name);
    case "domain":
      return cmpText(a && a.domain, b && b.domain);
    case "tier":
      return (TIER_ORDER[(a && a.tier) || "silent"] || 0) - (TIER_ORDER[(b && b.tier) || "silent"] || 0);
    case "marks":
      return marksCount(a) - marksCount(b);
    default:
      return rankOf(a) - rankOf(b);
  }
}

export function arrangeRows(rows, sort, dir) {
  const key = normalizeSort(sort) || "rank";
  const sign = dir === "desc" ? -1 : 1;
  return rows.slice().sort((a, b) => {
    const c = compareRows(a, b, key);
    if (c) return c * sign;
    const r = rankOf(a) - rankOf(b);
    if (r) return r;
    return cmpText(a && a.name, b && b.name);
  });
}

/* Default: silent → thin → on file → substantial → complete. Files that need a look first. */
export function defaultRows(rows) {
  return arrangeRows(rows, "tier", "asc");
}

function hay(row) {
  const marks = (row.certs || []).join(" ");
  const att = (row.attestations || []).map((a) => a.name || a.id).join(" ");
  const fr = row.fedramp;
  const fed = fr
    ? ["fedramp", fr.highest, ...(fr.levels || []), ...(fr.raw_levels || [])].filter(Boolean).join(" ")
    : "";
  return [row.name, row.domain, row.slug, row.tier, displayTier(row.tier), marks, att, fed]
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
  const head = names
    .slice(0, 3)
    .map((a) => `<span class="mark-chip">${escapeHtml(markLabel(a))}</span>`)
    .join(" · ");
  const extra = names.length > 3 ? ` · <span class="mark-more">+${names.length - 3}</span>` : "";
  const line = `<span class="mark-line">${head}${extra}</span>`;
  return stamp ? stamp + " · " + line : line;
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
    const implicit = !state.sorted && key === "tier";
    const live = implicit || (state.sorted && state.sort === key);
    const dir = implicit ? "asc" : state.dir;
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

function render() {
  const rows = apply();
  const f = active();
  const q = f.q.trim();
  const typed = state.q.trim();
  const table = $("reg");
  const empty = $("empty");
  const miss = $("miss");
  const count = $("countline");
  count.textContent = state.rows.length
    ? `showing ${rows.length} of ${state.rows.length}`
    : "";
  renderEcho();
  paintHeaders();
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
    const domain = guessDomain(q);
    $("miss-body").textContent = domain
      ? "It is not in this index. If a page exists, it often lives on one of these paths — we have not confirmed them."
      : "It is not in this index. A public page may still exist under an unusual URL.";
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
    .map((row) => {
      const n = row.rank == null ? "—" : String(row.rank).padStart(3, "0");
      const tier = displayTier(row.tier);
      return `<tr class="folio" data-slug="${escapeHtml(row.slug)}" tabindex="0" aria-label="open dossier: ${escapeHtml(row.name)}">
        <td class="num">${escapeHtml(n)}</td>
        <td class="name"><a href="./c/${encodeURIComponent(row.slug)}.html">${escapeHtml(row.name)}</a></td>
        <td>${escapeHtml(row.domain || "")}</td>
        <td class="${tierClass(row.tier)}">${fileMeterHtml(row)}${escapeHtml(tier)}</td>
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
      render();
    });
  }
  $("reg-body").addEventListener("click", (e) => {
    if (e.target.closest("a")) return;
    const tr = e.target.closest("tr");
    if (!tr) return;
    const slug = tr.getAttribute("data-slug");
    if (slug) window.location.href = `./c/${encodeURIComponent(slug)}.html`;
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
