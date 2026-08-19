import {
  $,
  escapeHtml,
  fillIssue,
  fmtDay,
  displayTier,
  tierClass,
  dataUrl,
} from "./lib.js";
import {
  parseFinder,
  stripFinderToken,
  normalizeTier,
  normalizeList,
  normalizeFedramp,
  echoWords,
} from "./finder.js";

const state = {
  rows: [],
  generatedAt: null,
  q: "",
  url: { tier: "all", list: "all", fedramp: "all" },
};

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
  return state.rows.filter((row) => {
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

function marksCell(row) {
  const stamp = fedrampMark(row);
  const atts = (row.attestations || []).filter((a) => a && (a.name || a.short));
  let names = (atts.length ? atts : (row.certs || []).map((name) => ({ name, id: null })))
    .slice()
    .sort((a, b) => String(a.short || a.name || "").localeCompare(String(b.short || b.name || ""), undefined, { sensitivity: "base" }));
  if (stamp) names = names.filter((a) => !isFedrampCite(a));
  if (!names.length) {
    return stamp || `<span class="absent">not on file</span>`;
  }
  const head = names
    .slice(0, 3)
    .map((a) => escapeHtml(String(a.short || a.name).toLowerCase()))
    .join(" · ");
  const extra = names.length > 3 ? ` · +${names.length - 3}` : "";
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
      return `<tr data-slug="${escapeHtml(row.slug)}">
        <td class="num">${escapeHtml(n)}</td>
        <td class="name"><a href="./c/${encodeURIComponent(row.slug)}.html">${escapeHtml(row.name)}</a></td>
        <td>${escapeHtml(row.domain || "")}</td>
        <td class="${tierClass(row.tier)}">${escapeHtml(tier)}</td>
        <td class="marks">${marksCell(row)}</td>
        <td>${escapeHtml(fmtDay(row.probed_at || state.generatedAt))}</td>
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

load();
