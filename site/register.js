import {
  $,
  escapeHtml,
  fillIssue,
  coverageLine,
  fmtDay,
  displayTier,
  tierClass,
} from "./lib.js";

const FEDRAMP_FILTERS = new Set(["all", "any", "low", "moderate", "high"]);

const state = {
  rows: [],
  generatedAt: null,
  q: "",
  tier: "all",
  list: "all",
  fedramp: "all",
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

function apply() {
  const q = state.q.trim().toLowerCase();
  return state.rows.filter((row) => {
    if (state.tier !== "all" && row.tier !== state.tier) return false;
    if (state.list === "cloud100" && row.list !== "cloud100") return false;
    if (state.list === "enterprise" && row.list !== "enterprise") return false;
    if (state.fedramp !== "all") {
      if (!row.fedramp) return false;
      if (state.fedramp !== "any") {
        const levels = (row.fedramp.levels || []).map((lv) => String(lv).toLowerCase());
        if (!levels.includes(state.fedramp)) return false;
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

function fedrampMark(row) {
  const fr = row.fedramp;
  if (!fr) return "";
  const url = fr.marketplace || "";
  const highest = fr.highest || "file";
  if (!url) return `<span class="fr-mark">FedRAMP ${escapeHtml(highest)}</span>`;
  return `<a class="fr-mark" href="${escapeHtml(url)}" target="_blank" rel="noopener">FedRAMP ${escapeHtml(highest)}</a>`;
}

function marksCell(row) {
  const stamp = fedrampMark(row);
  const atts = (row.attestations || []).filter((a) => a && (a.name || a.short));
  const names = atts.length
    ? atts
    : (row.certs || []).map((name) => ({ name, id: null }));
  if (!names.length) {
    return stamp || `<span class="absent">not on file</span>`;
  }
  const head = names
    .slice(0, 3)
    .map((a) => {
      const label = escapeHtml(a.short || a.name);
      return a.id
        ? `<a href="./attestations.html#${encodeURIComponent(a.id)}">${label}</a>`
        : label;
    })
    .join(" · ");
  const extra = names.length > 3 ? ` +${names.length - 3}` : "";
  return (stamp ? stamp + " " : "") + head + extra;
}

function render() {
  const rows = apply();
  const q = state.q.trim();
  const table = $("reg");
  const empty = $("empty");
  const miss = $("miss");
  const count = $("countline");
  const tierLabel = state.tier === "all" ? "all" : displayTier(state.tier);
  const listLabel = state.list === "all" ? "all" : state.list === "cloud100" ? "cloud 100" : "enterprise";
  const frLabel = state.fedramp === "all" ? "" : ` · fedramp ${state.fedramp}`;
  count.textContent = state.rows.length
    ? `showing ${rows.length} of ${state.rows.length} · tier ${tierLabel} · list ${listLabel}${frLabel}`
    : "";

  if (!state.rows.length) {
    table.hidden = true;
    miss.hidden = true;
    empty.hidden = false;
    return;
  }
  empty.hidden = true;

  if (q && !rows.length) {
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
      .map((u) => `<li><code>${escapeHtml(u)}</code></li>`)
      .join("");
    return;
  }

  miss.hidden = true;
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

function setFedramp(value) {
  const next = FEDRAMP_FILTERS.has(value) ? value : "all";
  state.fedramp = next;
  const bar = $("fedramp-filters");
  if (!bar) return;
  bar.querySelectorAll("button").forEach((b) => {
    b.classList.toggle("on", b.getAttribute("data-fedramp") === next);
  });
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
  $("tier-filters").querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.tier = btn.getAttribute("data-tier");
      $("tier-filters").querySelectorAll("button").forEach((b) => {
        b.classList.toggle("on", b === btn);
      });
      render();
    });
  });
  $("list-filters").querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.list = btn.getAttribute("data-list");
      $("list-filters").querySelectorAll("button").forEach((b) => {
        b.classList.toggle("on", b === btn);
      });
      render();
    });
  });
  const frBar = $("fedramp-filters");
  if (frBar) {
    frBar.querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", () => {
        setFedramp(btn.getAttribute("data-fedramp"));
        render();
      });
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
    setFedramp(String(params.get("fedramp")).toLowerCase());
  }
  try {
    const res = await fetch("./data.json", { cache: "no-store" });
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
    const cov = $("coverage");
    if (cov) cov.textContent = coverageLine(data.coverage);
  } catch {
    state.rows = [];
  }
  render();
}

load();
