import { $, escapeHtml, fillIssue, displayTier } from "./lib.js";

const state = {
  data: null,
  edges: [],
  companies: new Map(),
  processors: [],
  focus: 0,
};

function thinness(row) {
  if (!row) return 1;
  if (row.tier === "silent" || row.tier === "thin") return 1;
  const score = row.disclosure && typeof row.disclosure.score === "number" ? row.disclosure.score : 0;
  return (100 - score) / 100;
}

function registerSlug(node, companies) {
  if (!node) return null;
  if (node.id && companies.has(node.id)) return node.id;
  if (node.domain) {
    for (const c of companies.values()) {
      if ((c.domain || "").toLowerCase() === String(node.domain).toLowerCase()) return c.slug;
    }
  }
  return null;
}

function titleCaseSlug(to) {
  return String(to || "")
    .split(/[-_]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function looksLikeProcessorName(s) {
  const t = String(s || "").trim();
  if (!t) return false;
  if (/^listed on public/i.test(t)) return false;
  if (/listed on/i.test(t) || /\bpage\b/i.test(t)) return false;
  return true;
}

function processorDisplayName(e, node, to) {
  const nodeName = node && node.name ? String(node.name).trim() : "";
  if (looksLikeProcessorName(nodeName)) return nodeName;
  if (to) return titleCaseSlug(to);
  const evidence = e && e.evidence ? String(e.evidence).trim() : "";
  if (looksLikeProcessorName(evidence)) return evidence;
  return (e && e.processor) || to;
}

function normalizeEdges(wires, companies) {
  const nodes = new Map((wires.nodes || []).map((n) => [n.id, n]));
  return (wires.edges || [])
    .filter((e) => e.source_url)
    .map((e) => {
      const from = e.from || e.company;
      const to = e.to || e.processor_slug || e.processor;
      const node = nodes.get(to) || {};
      const slug = registerSlug(node, companies) || (companies.has(to) ? to : e.processor_slug || null);
      return {
        company: from,
        processor: processorDisplayName(e, node, to),
        processor_slug: slug,
        processor_id: to,
        source_url: e.source_url,
      };
    });
}

function rankProcessors(edges, companies) {
  const by = new Map();
  for (const e of edges) {
    const key = e.processor_id || e.processor_slug || e.processor;
    if (!by.has(key)) {
      by.set(key, {
        name: e.processor,
        slug: e.processor_slug || null,
        sources: new Set(),
        namers: [],
      });
    }
    const rec = by.get(key);
    rec.sources.add(e.source_url);
    rec.namers.push({ company: e.company, source_url: e.source_url });
  }
  const rows = [];
  for (const rec of by.values()) {
    const self = rec.slug ? companies.get(rec.slug) : null;
    const exposure = rec.namers.length;
    const t = thinness(self);
    const risk = exposure * (0.4 + 0.6 * t);
    rows.push({
      name: rec.name,
      slug: rec.slug,
      inRegister: Boolean(self),
      tier: self ? self.tier : null,
      exposure,
      thinness: t,
      risk,
      sources: [...rec.sources],
      namers: rec.namers,
    });
  }
  rows.sort((a, b) => b.risk - a.risk || b.exposure - a.exposure || a.name.localeCompare(b.name));
  return rows;
}

function renderTable() {
  const body = $("wire-body");
  if (!state.processors.length) {
    $("wire-table").hidden = true;
    $("empty-wires").hidden = false;
    return;
  }
  $("wire-table").hidden = false;
  $("empty-wires").hidden = true;
  body.innerHTML = state.processors
    .map((p, i) => {
      const tier = p.inRegister ? displayTier(p.tier) : "not in register";
      const src = p.sources[0] ? hostOfSafe(p.sources[0]) : "not on file";
      return `<tr data-i="${i}" class="${state.focus === i ? "on" : ""}">
        <td class="name">${escapeHtml(p.name)}</td>
        <td>${p.exposure}</td>
        <td class="${p.inRegister ? "" : "absent"}">${escapeHtml(tier)}</td>
        <td>${p.risk.toFixed(1)}</td>
        <td>${escapeHtml(src)}</td>
      </tr>`;
    })
    .join("");
}

function hostOfSafe(url) {
  try {
    return new URL(url).host.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function renderStub() {
  const el = $("stub");
  if (state.focus == null) {
    el.hidden = true;
    return;
  }
  const p = state.processors[state.focus];
  if (!p) {
    el.hidden = true;
    return;
  }
  el.hidden = false;
  const namers = p.namers
    .map((n) => {
      const co = state.companies.get(n.company);
      const label = co ? co.name : n.company;
      const href = co ? `./c/${encodeURIComponent(co.slug)}.html` : null;
      const src = n.source_url
        ? ` <span class="muted">· ${escapeHtml(hostOfSafe(n.source_url))}</span>`
        : "";
      return href
        ? `<li><a href="${href}">${escapeHtml(label)}</a>${src}</li>`
        : `<li>${escapeHtml(label)}${src}</li>`;
    })
    .join("");
  const self = p.inRegister
    ? `<p class="ident-meta"><a href="./c/${encodeURIComponent(p.slug)}.html">dossier</a></p>`
    : `<p class="ident-meta absent">not in register</p>`;
  el.innerHTML = `<h2>${escapeHtml(p.name)}</h2>
    ${self}
    <p class="fig-sub">Who named them, as published.</p>
    <ul class="guesses">${namers}</ul>`;
}

function drawFig() {
  const canvas = $("fig1");
  if (!canvas) return;
  const wrap = canvas.parentElement;
  const w = wrap.clientWidth;
  const h = wrap.clientHeight;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.floor(w * dpr);
  canvas.height = Math.floor(h * dpr);
  canvas.style.width = w + "px";
  canvas.style.height = h + "px";
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  if (!state.processors.length) return;

  const procs = state.processors;
  const companies = [...new Set(state.edges.map((e) => e.company))]
    .map((slug) => state.companies.get(slug))
    .filter(Boolean);

  const leftX = 48;
  const rightX = w - 48;
  const top = 28;
  const bot = h - 28;
  function stack(n, i) {
    if (n <= 1) return (top + bot) / 2;
    return top + ((bot - top) * i) / (n - 1);
  }

  const cPos = new Map();
  companies.forEach((c, i) => cPos.set(c.slug, { x: leftX, y: stack(companies.length, i), row: c }));
  const pPos = new Map();
  procs.forEach((p, i) => pPos.set(p.slug || p.name, { x: rightX, y: stack(procs.length, i), row: p, i }));

  ctx.lineWidth = 1;
  const focused = state.focus != null ? state.processors[state.focus] : null;
  const focusKey = focused ? focused.slug || focused.name : null;
  if (focusKey) {
    ctx.strokeStyle = "#cc5100";
    for (const e of state.edges) {
      const a = cPos.get(e.company);
      const b = pPos.get(e.processor_slug || e.processor);
      if (!a || !b) continue;
      if ((e.processor_slug || e.processor) !== focusKey) continue;
      ctx.beginPath();
      ctx.moveTo(a.x + 4, a.y);
      ctx.lineTo(b.x - 4, b.y);
      ctx.stroke();
    }
  }

  function square(x, y, fill, stroke) {
    ctx.beginPath();
    ctx.rect(x - 3, y - 3, 6, 6);
    if (fill) {
      ctx.fillStyle = fill;
      ctx.fill();
    }
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  for (const { x, y } of cPos.values()) {
    square(x, y, "#ffc091", "#993d00");
  }
  for (const { x, y, row, i } of pPos.values()) {
    const selected = state.focus === i;
    if (row.inRegister) square(x, y, "#ffc091", selected ? "#cc5100" : "#993d00");
    else square(x, y, null, selected ? "#cc5100" : "#993d00");
  }

  ctx.font = "11px 'IBM Plex Mono', ui-monospace, monospace";
  const focus = state.focus != null ? state.processors[state.focus] : null;
  if (focus) {
    ctx.fillStyle = "#ffc091";
    const pos = pPos.get(focus.slug || focus.name);
    if (pos) ctx.fillText(focus.name, pos.x - 8 - ctx.measureText(focus.name).width, pos.y + 4);
    for (const n of focus.namers) {
      const c = cPos.get(n.company);
      if (!c) continue;
      ctx.fillStyle = "#e09a60";
      ctx.fillText(c.row.name, c.x + 10, c.y + 4);
    }
  } else if (procs.length <= 16) {
    ctx.fillStyle = "#e09a60";
    for (const { x, y, row } of pPos.values()) {
      ctx.fillText(row.name, x - 8 - ctx.measureText(row.name).width, y + 4);
    }
  }
}

function bind() {
  $("wire-body").addEventListener("click", (e) => {
    const tr = e.target.closest("tr");
    if (!tr) return;
    const i = Number(tr.getAttribute("data-i"));
    const p = state.processors[i];
    if (!p) return;
    if (p.inRegister && p.slug && e.detail === 2) {
      window.location.href = `./c/${encodeURIComponent(p.slug)}.html`;
      return;
    }
    state.focus = i;
    renderTable();
    renderStub();
    drawFig();
  });
  $("fig1").addEventListener("click", (e) => {
    const canvas = e.currentTarget;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const w = rect.width;
    const h = rect.height;
    const procs = state.processors;
    const top = 28;
    const bot = h - 28;
    const rightX = w - 48;
    let hit = null;
    procs.forEach((p, i) => {
      const py = procs.length <= 1 ? (top + bot) / 2 : top + ((bot - top) * i) / (procs.length - 1);
      if (Math.abs(x - rightX) < 16 && Math.abs(y - py) < 10) hit = i;
    });
    if (hit == null) return;
    const p = procs[hit];
    if (p.inRegister && p.slug && e.detail === 2) {
      window.location.href = `./c/${encodeURIComponent(p.slug)}.html`;
      return;
    }
    state.focus = hit;
    renderTable();
    renderStub();
    drawFig();
  });
  window.addEventListener("resize", drawFig);
}

async function load() {
  bind();
  try {
    const [reg, wires] = await Promise.all([
      fetch("./data.json", { cache: "no-store" }).then((r) => r.json()),
      fetch("./data/subprocessors.json", { cache: "no-store" }).then((r) => (r.ok ? r.json() : { edges: [] })),
    ]);
    state.data = reg;
    (reg.companies || []).forEach((c) => state.companies.set(c.slug, c));
    state.edges = normalizeEdges(wires, state.companies);
    state.processors = rankProcessors(state.edges, state.companies);
    fillIssue($("issue"), reg, `${state.edges.length} edges`);
  } catch {
    state.edges = [];
  }
  renderTable();
  renderStub();
  drawFig();
}

load();
