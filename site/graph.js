import { $, escapeHtml, fillIssue, displayTier, dataUrl, nameWithIcon } from "./lib.js";

const state = {
  data: null,
  edges: [],
  companies: new Map(),
  processors: [],
  focus: 0,
  icons: { companies: {}, marks: {} },
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

function isSlugCase(s) {
  return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(String(s || "").trim());
}

function titleCaseSlug(to) {
  return String(to || "")
    .split(/[-_]+/)
    .filter(Boolean)
    .map((w) => {
      if (w.length <= 2 && /[a-z]/i.test(w)) {
        return w.replace(/[a-z]/g, (c) => c.toUpperCase());
      }
      let cap = true;
      return [...w]
        .map((c) => {
          if (/[a-z]/i.test(c)) {
            const out = cap ? c.toUpperCase() : c.toLowerCase();
            cap = false;
            return out;
          }
          cap = /\d/.test(c);
          return c;
        })
        .join("");
    })
    .join(" ");
}

function humanizeProcessorName(s) {
  const t = String(s || "").trim();
  if (isSlugCase(t)) return titleCaseSlug(t);
  return t;
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
  if (looksLikeProcessorName(nodeName)) return humanizeProcessorName(nodeName);
  if (to) return humanizeProcessorName(to) || titleCaseSlug(to);
  const evidence = e && e.evidence ? String(e.evidence).trim() : "";
  if (looksLikeProcessorName(evidence)) return humanizeProcessorName(evidence);
  return humanizeProcessorName((e && e.processor) || to);
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
      const domain = (node.domain || (slug && companies.get(slug) && companies.get(slug).domain) || "")
        .toLowerCase()
        .replace(/^www\./, "");
      return {
        company: from,
        processor: processorDisplayName(e, node, to),
        processor_slug: slug,
        processor_id: to,
        processor_domain: domain,
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
        domain: e.processor_domain || "",
        sources: new Set(),
        namers: [],
      });
    }
    const rec = by.get(key);
    rec.sources.add(e.source_url);
    rec.namers.push({ company: e.company, source_url: e.source_url });
    if (!rec.domain && e.processor_domain) rec.domain = e.processor_domain;
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
      domain: rec.domain || (self && self.domain) || "",
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
      return `<tr data-i="${i}" class="${state.focus === i ? "on selected" : ""}">
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

function iconForDomain(domain, row) {
  if (row && row.favicon) return row.favicon;
  const host = String(domain || (row && row.domain) || "")
    .toLowerCase()
    .replace(/^www\./, "");
  return (state.icons.companies && state.icons.companies[host]) || "";
}

function namerLine(n) {
  const co = state.companies.get(n.company);
  const label = co ? co.name : n.company;
  const href = co ? `./c/${encodeURIComponent(co.slug)}.html` : null;
  const host = n.source_url ? hostOfSafe(n.source_url) : "";
  const src = n.source_url
    ? ` <span class="muted">· <a href="${escapeHtml(n.source_url)}" rel="noopener noreferrer">${escapeHtml(host)}</a></span>`
    : "";
  const named = nameWithIcon(label, iconForDomain(co && co.domain, co));
  return href
    ? `<li><a href="${href}">${named}</a>${src}</li>`
    : `<li>${named}${src}</li>`;
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
  const status = p.inRegister
    ? `<p class="ident-meta">on file · <a href="./c/${encodeURIComponent(p.slug)}.html">dossier</a></p>`
    : `<p class="ident-meta"><span class="absent">not in register</span></p>`;
  const self = p.slug ? state.companies.get(p.slug) : null;
  el.innerHTML = `<h2>${nameWithIcon(p.name, iconForDomain(p.domain, self))}</h2>`
    ${status}
    <p class="ident-meta">exposure · ${p.exposure}</p>
    <p class="fig-sub">Who named them, as published.</p>
    <ul class="guesses">${p.namers.map(namerLine).join("")}</ul>`;
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
    ctx.strokeStyle = tokenColor("--ot-evidence-teal", "#00685C");
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

  const ink = tokenColor("--ot-ledger-black", "#0B1411");
  const rule = tokenColor("--ot-rule-strong", "#70817A");
  const index = tokenColor("--ot-evidence-teal", "#00685C");
  const mute = tokenColor("--ot-graphite", "#51615B");
  for (const { x, y } of cPos.values()) {
    square(x, y, ink, rule);
  }
  for (const { x, y, row, i } of pPos.values()) {
    const selected = state.focus === i;
    if (row.inRegister) square(x, y, ink, selected ? index : rule);
    else square(x, y, null, selected ? index : rule);
  }

  ctx.font = "13px 'Atkinson Hyperlegible Next', Arial, system-ui, sans-serif";
  const focus = state.focus != null ? state.processors[state.focus] : null;
  if (focus) {
    ctx.fillStyle = ink;
    const pos = pPos.get(focus.slug || focus.name);
    if (pos) ctx.fillText(focus.name, pos.x - 8 - ctx.measureText(focus.name).width, pos.y + 4);
    for (const n of focus.namers) {
      const c = cPos.get(n.company);
      if (!c) continue;
      ctx.fillStyle = mute;
      ctx.fillText(c.row.name, c.x + 10, c.y + 4);
    }
  } else if (procs.length <= 16) {
    ctx.fillStyle = mute;
    for (const { x, y, row } of pPos.values()) {
      ctx.fillText(row.name, x - 8 - ctx.measureText(row.name).width, y + 4);
    }
  }
}

function tokenColor(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
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
    revealFile();
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
    revealFile();
  });
  window.addEventListener("resize", drawFig);
}

function revealFile() {
  const el = $("stub");
  if (!el || el.hidden) return;
  if (!window.matchMedia("(max-width: 1100px)").matches) return;
  el.scrollIntoView({ block: "nearest", behavior: "auto" });
}

async function load() {
  bind();
  try {
    const [reg, wires, icons] = await Promise.all([
      fetch(dataUrl("./data.json"), { cache: "no-store" }).then((r) => r.json()),
      fetch(dataUrl("./data/subprocessors.json"), { cache: "no-store" }).then((r) => (r.ok ? r.json() : { edges: [] })),
      fetch(dataUrl("./favicons/index.json"), { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : { companies: {}, marks: {} }))
        .catch(() => ({ companies: {}, marks: {} })),
    ]);
    state.icons = icons && typeof icons === "object" ? icons : { companies: {}, marks: {} };
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
