/* Black Binding — front-page band. Numbers come from data.json at load.
   The console re-probes real register targets from the visitor's browser. */
import { $, dataUrl, escapeHtml } from "./lib.js";

const REDUCED =
  globalThis.matchMedia &&
  globalThis.matchMedia("(prefers-reduced-motion: reduce)").matches;

const PROBES = [
  { id: "b-pr-stripe", url: "https://docs.stripe.com/security" },
  { id: "b-pr-openai", url: "https://trust.openai.com" },
  { id: "b-pr-cloudflare", url: "https://www.cloudflare.com/trust-hub/" },
  { id: "b-pr-mistral", url: "https://trust.mistral.ai" },
];

const TIER_WORD = {
  silent: "silent",
  thin: "thin",
  "on-file": "on file",
  substantial: "substantial",
  complete: "public file complete",
};

function fmt(n) {
  return Number(n || 0).toLocaleString("en-US");
}

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function fmtStamp(iso) {
  const d = new Date(iso);
  if (isNaN(d)) return "";
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()} · ${hh}:${mm} UTC`;
}

function fmtDay(iso) {
  const d = new Date(iso);
  if (isNaN(d)) return "";
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}

async function getJson(path) {
  const res = await fetch(dataUrl(path), { cache: "no-store" });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

function paintStats(data, marks) {
  const scope = $("b-stat-scope");
  const found = $("b-stat-found");
  const edges = $("b-stat-edges");
  const marksEl = $("b-stat-marks");
  const note = $("b-count-note");
  if (scope) scope.textContent = fmt(data.total);
  if (found) found.textContent = fmt(data.found);
  if (edges) edges.textContent = fmt(data.coverage && data.coverage.edges);
  if (marksEl) marksEl.textContent = marks ? fmt(marks) : "not on file";
  if (note) {
    const stamp = fmtStamp(data.generated_at);
    note.textContent = stamp
      ? `counts computed from data.json at load · register generated ${stamp}. a row that cannot be fetched prints not on file — it is never dropped.`
      : note.textContent;
  }
}

function paintStatus(data) {
  const el = $("issue");
  if (!el || !data) return;
  const stamp = fmtStamp(data.generated_at);
  el.textContent = stamp
    ? [`last sweep ${stamp}`, `${fmt(data.found)} files on record of ${fmt(data.total)} in scope`].join(" · ")
    : el.textContent;
}

function paintTicker(data) {
  const track = $("b-ticker-track");
  if (!track) return;
  const rows = (data.companies || [])
    .filter((r) => r && r.found)
    .sort((a, b) => String(b.probed_at || "").localeCompare(String(a.probed_at || "")))
    .slice(0, 10);
  if (!rows.length) {
    track.hidden = true;
    return;
  }
  const items = rows.map((r) => {
    const tier = String(r.tier || "silent");
    const cls = tier === "silent" ? "off" : "ok";
    const word = TIER_WORD[tier] || "not on file";
    const day = fmtDay(r.probed_at);
    return (
      `<span class="b-tick"><i class="b-sym ${cls}" aria-hidden="true"></i>` +
      `<b>${escapeHtml(r.domain)}</b> ${escapeHtml(word)}${day ? ` · probed ${day}` : ""}</span>`
    );
  });
  const half = `<span class="b-tick-group">${items.join("")}</span>`;
  track.innerHTML = half + half;
}

function paintProbe(id, ms) {
  const el = $(id);
  if (!el) return;
  if (ms === null) {
    el.textContent = "timeout · not on file";
    el.className = "b-v warn";
    return;
  }
  el.textContent = `ok · ${fmt(ms)}ms`;
  el.className = ms > 900 ? "b-v ok slow" : "b-v ok";
}

async function sweep() {
  let answered = 0;
  for (const p of PROBES) {
    let ms = null;
    const t0 = performance.now();
    const ctl = "AbortController" in globalThis ? new AbortController() : null;
    const timer = ctl && setTimeout(() => ctl.abort(), 4000);
    try {
      await fetch(p.url, { mode: "no-cors", cache: "no-store", signal: ctl && ctl.signal });
      ms = Math.round(performance.now() - t0);
      answered += 1;
    } catch (err) {
      ms = null;
    }
    if (timer) clearTimeout(timer);
    paintProbe(p.id, ms);
  }
  const vd = $("b-verdict");
  if (vd) vd.textContent = `${answered} of ${PROBES.length} answered · sweep complete`;
}

function bindChips() {
  document.querySelectorAll(".binding-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const q = $("q");
      if (!q) return;
      q.value = chip.getAttribute("data-find") || "";
      q.dispatchEvent(new Event("input", { bubbles: true }));
      q.focus({ preventScroll: true });
      const main = $("main");
      if (main && main.scrollIntoView) main.scrollIntoView({ behavior: REDUCED ? "auto" : "smooth", block: "start" });
    });
  });
}

async function init() {
  bindChips();
  const stamp = $("b-sweep-stamp");
  try {
    const [data, att] = await Promise.all([getJson("./data.json"), getJson("./data/attestations.json").catch(() => null)]);
    paintStatus(data);
    paintStats(data, att && att.count);
    paintTicker(data);
    if (stamp) stamp.textContent = `sweep ${fmtDay(data.generated_at)}`;
  } catch (err) {
    if (stamp) stamp.textContent = "register not on file";
  }
  sweep();
}

init();
