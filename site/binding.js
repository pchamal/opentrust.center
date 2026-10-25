/* Home plate. Counts come from data.json through lib.js. No ticker, no console. */
import {
  $,
  dataUrl,
  fmtDay,
  fmtNum,
  figureHtml,
  instrumentCensus,
  selectAiFiles,
  aiFileFlags,
  AI_FILE_KEYS,
} from "./lib.js";

const AI_LABELS = {
  page: "AI page",
  marks: "AI standards",
  processors: "AI processors",
  evals: "evals",
  incidents: "incidents",
};

function fmtClock(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return (
    d.toLocaleTimeString("en-US", {
      timeZone: "America/Los_Angeles",
      hour: "numeric",
      minute: "2-digit",
    }) + " PT"
  );
}

function paintIssue(data) {
  const el = $("issue");
  if (!el || !data || !data.generated_at) {
    if (el) el.textContent = "issue not on file";
    return;
  }
  el.textContent = `issue ${fmtDay(data.generated_at)}, swept ${fmtClock(data.generated_at)}`;
}

function paintFigure(data) {
  const rows = selectAiFiles(data.companies || []);
  const census = instrumentCensus(rows, aiFileFlags, AI_FILE_KEYS);
  const page = census.by.page;
  const cap = $("cap");
  const src = $("src");
  const fig = $("fig");
  const leg = $("leg");
  if (cap) cap.textContent = `${fmtNum(page.on)} of ${fmtNum(census.total)} AI systems print an AI page.`;
  if (src) {
    src.textContent = `Each line counts one disclosure across ${fmtNum(census.total)} AI systems. Issue of ${fmtDay(data.generated_at)}.`;
  }
  if (fig) {
    fig.innerHTML = figureHtml(
      AI_FILE_KEYS.map((key) => ({
        label: AI_LABELS[key],
        on: census.by[key].on,
        partial: census.by[key].partial,
      })),
      census.total,
    );
  }
  const anyPartial = AI_FILE_KEYS.some((key) => census.by[key].partial > 0);
  if (leg && anyPartial) {
    leg.textContent =
      "Thick line: systems that publish it. Dotted: on file, not extracted. Thin line: not on file, which is inconclusive. Counted from data.json at load.";
  }
  const heading = $("aiti-heading");
  if (heading) heading.textContent = `All ${fmtNum(census.total)} AI systems`;
  return census;
}

function paintCounts(data) {
  const el = $("counts");
  if (!el || !data) return;
  const total = Number(data.total) || (data.companies || []).length;
  const found = Number(data.found);
  const tiers = data.coverage && data.coverage.tiers;
  const complete = tiers ? Number(tiers.complete) : null;
  const edges = data.coverage ? Number(data.coverage.edges) : null;
  const foundWords = Number.isFinite(found)
    ? `<b>${fmtNum(found)}</b> publish a trust file`
    : "trust files are counted at load";
  const completeWords =
    complete == null || Number.isNaN(complete)
      ? ""
      : ` and <b>${fmtNum(complete)}</b> of those are complete`;
  const edgeWords =
    edges == null || Number.isNaN(edges)
      ? ""
      : ` Together they name <b>${fmtNum(edges)}</b> subprocessor relationships.`;
  el.innerHTML = `The Register covers <b>${fmtNum(total)}</b> domains. ${foundWords}${completeWords}.${edgeWords}`;
}

function probe() {
  const hosts = document.querySelectorAll("#probe [data-u]");
  hosts.forEach((node) => {
    const value = node.querySelector(".v");
    if (!value) return;
    const started = performance.now();
    const ctl = "AbortController" in globalThis ? new AbortController() : null;
    const timer = ctl && setTimeout(() => ctl.abort(), 4000);
    fetch(node.getAttribute("data-u"), {
      mode: "no-cors",
      cache: "no-store",
      signal: ctl && ctl.signal,
    })
      .then(() => {
        value.textContent = `${Math.round(performance.now() - started)} ms`;
      })
      .catch(() => {
        value.innerHTML = "<em>not on file</em>";
      })
      .finally(() => {
        if (timer) clearTimeout(timer);
      });
  });
}

function bindChips() {
  const reduced =
    globalThis.matchMedia && globalThis.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.querySelectorAll(".binding-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const q = $("q");
      if (!q) return;
      q.value = chip.getAttribute("data-find") || "";
      q.dispatchEvent(new Event("input", { bubbles: true }));
      q.focus({ preventScroll: true });
      const main = $("main");
      if (main && main.scrollIntoView) {
        main.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
      }
    });
  });
}

async function init() {
  bindChips();
  try {
    const res = await fetch(dataUrl("./data.json"), { cache: "no-store" });
    if (!res.ok) throw new Error(String(res.status));
    const data = await res.json();
    paintIssue(data);
    paintFigure(data);
    paintCounts(data);
  } catch (err) {
    const issue = $("issue");
    if (issue) issue.textContent = "issue not on file";
    const cap = $("cap");
    if (cap) cap.textContent = "The AI file count is not on file.";
  }
  probe();
}

init();
