import { $, escapeHtml, fillIssue, displayTier, dataUrl } from "./lib.js";

const state = {
  data: null,
  edges: [],
  companies: new Map(),
  processors: [],
  focus: 0,
  view: "list",
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
        id: key,
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
      id: rec.id || rec.slug || rec.name,
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

function namerLine(n) {
  const co = state.companies.get(n.company);
  const label = co ? co.name : n.company;
  const href = co ? `./c/${encodeURIComponent(co.slug)}.html` : null;
  const host = n.source_url ? hostOfSafe(n.source_url) : "";
  const src = n.source_url
    ? ` <span class="muted">· <a href="${escapeHtml(n.source_url)}" rel="noopener noreferrer">${escapeHtml(host)}</a></span>`
    : "";
  return href
    ? `<li><a href="${href}">${escapeHtml(label)}</a>${src}</li>`
    : `<li>${escapeHtml(label)}${src}</li>`;
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
  el.innerHTML = `<h2>${escapeHtml(p.name)}</h2>
    ${status}
    <p class="ident-meta">exposure · ${p.exposure}</p>
    <p class="fig-sub">Who named them, as published.</p>
    <ul class="guesses">${p.namers.map(namerLine).join("")}</ul>`;
}

const map = {
  nodes: [],
  links: [],
  screen: [],
  yaw: 0,
  pitch: 0,
  focusKey: null,
  drag: null,
};

const NEIGHBOR_MAX = 40;
const NEIGHBOR_OTHERS_CAP = 12;
const COMPACT_NAMER_CAP = 12;

function processorKey(p) {
  return p && (p.id || p.slug || p.name);
}

function edgeProcessorId(e) {
  return e.processor_id || e.processor_slug || e.processor;
}

export function neighborhoodOf(focus, edges, processors, companies) {
  if (!focus) return { nodes: [], links: [], namers: 0, others: 0 };
  const selectedId = processorKey(focus);
  const namerSlugs = [];
  const seenNamer = new Set();
  for (const n of focus.namers || []) {
    if (!n.company || seenNamer.has(n.company)) continue;
    seenNamer.add(n.company);
    namerSlugs.push(n.company);
  }
  const byProc = new Map((processors || []).map((p, i) => [processorKey(p), { p, i }]));
  const otherVotes = new Map();
  for (const e of edges || []) {
    if (!seenNamer.has(e.company)) continue;
    const pid = edgeProcessorId(e);
    if (!pid || pid === selectedId) continue;
    if (!otherVotes.has(pid)) otherVotes.set(pid, new Map());
    const votes = otherVotes.get(pid);
    votes.set(e.company, (votes.get(e.company) || 0) + 1);
  }
  let others = [...otherVotes.entries()]
    .map(([id, votes]) => {
      let count = 0;
      let best = null;
      let bestN = -1;
      for (const [co, n] of votes) {
        count += n;
        if (n > bestN) {
          best = co;
          bestN = n;
        }
      }
      return { id, count, best, rec: byProc.get(id) };
    })
    .sort((a, b) => b.count - a.count || String(a.id).localeCompare(String(b.id)));
  const allFit = 1 + namerSlugs.length + others.length <= NEIGHBOR_MAX;
  if (!allFit) {
    others = others.filter((o) => o.count >= 2).slice(0, NEIGHBOR_OTHERS_CAP);
  }
  const nodes = [];
  const index = new Map();
  function add(id, spec) {
    if (index.has(id)) return index.get(id);
    const n = { id, x: 0, y: 0, z: 0, ...spec };
    index.set(id, n);
    nodes.push(n);
    return n;
  }
  add(selectedId, {
    kind: "processor",
    role: "selected",
    name: focus.name,
    slug: focus.slug,
    inRegister: focus.inRegister,
    focus: byProc.has(selectedId) ? byProc.get(selectedId).i : null,
  });
  for (const slug of namerSlugs) {
    const co = companies && companies.get ? companies.get(slug) : null;
    add("co:" + slug, {
      kind: "company",
      role: "namer",
      name: co ? co.name : slug,
      slug,
    });
  }
  for (const o of others) {
    const rec = o.rec;
    add(o.id, {
      kind: "processor",
      role: "other",
      name: rec ? rec.p.name : o.id,
      slug: rec ? rec.p.slug : null,
      inRegister: rec ? rec.p.inRegister : false,
      focus: rec ? rec.i : null,
      shared: o.count,
    });
  }
  const links = [];
  const selectedNode = index.get(selectedId);
  for (const slug of namerSlugs) {
    const a = index.get("co:" + slug);
    if (a && selectedNode) links.push({ a, b: selectedNode });
  }
  for (const o of others) {
    const a = o.best ? index.get("co:" + o.best) : null;
    const b = index.get(o.id);
    if (a && b) links.push({ a, b });
  }
  return { nodes, links, namers: namerSlugs.length, others: others.length };
}

function placeNeighborhood(nodes, links) {
  const selected = nodes.find((n) => n.role === "selected");
  const namers = nodes.filter((n) => n.role === "namer");
  const others = nodes.filter((n) => n.role === "other");
  if (selected) {
    selected.x = 0;
    selected.y = 0;
    selected.z = 0;
  }
  namers.forEach((n, i) => {
    const a = -Math.PI / 2 + (2 * Math.PI * i) / Math.max(namers.length, 1);
    n.x = Math.cos(a) * 0.46;
    n.y = Math.sin(a) * 0.46;
    n.z = 0;
    n.angle = a;
  });
  const byId = new Map(nodes.map((n) => [n.id, n]));
  others.forEach((n, i) => {
    const angles = [];
    for (const L of links) {
      if (L.b.id !== n.id) continue;
      const co = byId.get(L.a.id);
      if (co && typeof co.angle === "number") angles.push(co.angle);
    }
    let a;
    if (angles.length) {
      const cx = angles.reduce((s, x) => s + Math.cos(x), 0) / angles.length;
      const cy = angles.reduce((s, x) => s + Math.sin(x), 0) / angles.length;
      a = Math.atan2(cy, cx);
    } else {
      a = -Math.PI / 2 + (2 * Math.PI * i) / Math.max(others.length, 1);
    }
    a += (i % 2 === 0 ? -1 : 1) * 0.04 * Math.min(i, 6);
    n.x = Math.cos(a) * 0.84;
    n.y = Math.sin(a) * 0.84;
    n.z = 0;
  });
}

function compactPhone() {
  return typeof window !== "undefined" && window.matchMedia("(max-width: 390px)").matches;
}

function graphShouldDraw(hood) {
  if (!hood || !hood.nodes.length) return false;
  if (compactPhone() && hood.namers > COMPACT_NAMER_CAP) return false;
  return true;
}

function ensureNeighborhood() {
  const focus = selectedProcessor();
  const key = focus ? processorKey(focus) : null;
  if (map.focusKey === key && map.nodes.length) return;
  const hood = neighborhoodOf(focus, state.edges, state.processors, state.companies);
  placeNeighborhood(hood.nodes, hood.links);
  map.nodes = hood.nodes;
  map.links = hood.links;
  map.namers = hood.namers;
  map.others = hood.others;
  map.focusKey = key;
  // 2D plate. prefers-reduced-motion: still. Drag still works.
  if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    map.yaw = 0;
    map.pitch = 0;
  }
}

function projectNode(p, w, h) {
  const cy = Math.cos(map.yaw);
  const sy = Math.sin(map.yaw);
  const cp = Math.cos(map.pitch);
  const sp = Math.sin(map.pitch);
  const x1 = p.x * cy - p.z * sy;
  const z1 = p.x * sy + p.z * cy;
  const y1 = p.y * cp - z1 * sp;
  const z2 = p.y * sp + z1 * cp;
  const persp = 3.4;
  const s = persp / (persp + z2);
  const R = Math.min(w, h) * 0.42;
  return {
    x: w / 2 + x1 * s * R,
    y: h / 2 + y1 * s * R,
    z: z2,
    s,
  };
}

function selectedProcessor() {
  return state.focus != null ? state.processors[state.focus] : null;
}

function isSelectedNode(n) {
  return n && n.role === "selected";
}

function setGraphVisible(on) {
  const pane = $("wires-map");
  if (pane) pane.setAttribute("data-graph", on ? "on" : "off");
}

function drawMap() {
  const canvas = $("fig1");
  if (!canvas || state.view !== "map") return;
  if (!state.processors.length) {
    setGraphVisible(false);
    return;
  }
  ensureNeighborhood();
  const hood = { nodes: map.nodes, namers: map.namers, others: map.others };
  const show = graphShouldDraw(hood);
  setGraphVisible(show);
  if (!show) {
    map.screen = [];
    return;
  }
  const wrap = canvas.parentElement;
  const w = wrap.clientWidth;
  const h = wrap.clientHeight;
  if (w < 8 || h < 8) return;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.floor(w * dpr);
  canvas.height = Math.floor(h * dpr);
  canvas.style.width = w + "px";
  canvas.style.height = h + "px";
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = tokenColor("--ot-record-white", "#F8FAF9");
  ctx.fillRect(0, 0, w, h);

  const ink = tokenColor("--ot-ledger-black", "#0B1411");
  const teal = tokenColor("--ot-evidence-teal", "#00685C");
  const mute = tokenColor("--ot-graphite", "#51615B");

  map.screen = map.nodes.map((n) => {
    const q = projectNode(n, w, h);
    return { n, ...q };
  });
  map.screen.sort((a, b) => a.z - b.z);

  const byId = new Map(map.screen.map((s) => [s.n.id, s]));
  ctx.lineWidth = 1;
  ctx.strokeStyle = ink;
  ctx.beginPath();
  for (const L of map.links) {
    const a = byId.get(L.a.id);
    const b = byId.get(L.b.id);
    if (!a || !b) continue;
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
  }
  ctx.stroke();

  for (const s of map.screen) {
    const selected = isSelectedNode(s.n);
    const half = s.n.role === "selected" ? 5 : s.n.kind === "processor" ? 3.5 : 2.5;
    const fill = s.n.kind === "company" || s.n.inRegister || s.n.role === "selected";
    ctx.beginPath();
    ctx.rect(s.x - half, s.y - half, half * 2, half * 2);
    if (fill) {
      ctx.fillStyle = ink;
      ctx.fill();
    }
    ctx.strokeStyle = selected ? teal : ink;
    ctx.lineWidth = selected ? 2 : 1;
    ctx.stroke();
  }

  const placed = [];
  function placeLabel(text, x, y, font, color, prefer) {
    ctx.font = font;
    const tw = ctx.measureText(text).width;
    let lx = x + 10;
    let ly = y + 4;
    if (prefer === "above") {
      lx = x - tw / 2;
      ly = y - 12;
    } else if (prefer === "out") {
      const dx = x - w / 2;
      const dy = y - h / 2;
      const len = Math.hypot(dx, dy) || 1;
      lx = x + (dx / len) * 16 - tw / 2;
      ly = y + (dy / len) * 14 + 4;
    }
    if (lx + tw > w - 8) lx = x - 8 - tw;
    if (lx < 8) lx = 8;
    if (ly < 14) ly = y + 18;
    if (ly > h - 6) ly = y - 10;
    const box = { x: lx, y: ly - 12, w: tw, h: 16 };
    for (const p of placed) {
      if (box.x < p.x + p.w && box.x + box.w > p.x && box.y < p.y + p.h && box.y + box.h > p.y) {
        return false;
      }
    }
    placed.push(box);
    ctx.fillStyle = color;
    ctx.fillText(text, lx, ly);
    return true;
  }

  const serif = "600 17px 'Source Serif 4', Georgia, 'Times New Roman', serif";
  const utility = "13px 'Atkinson Hyperlegible Next', Arial, system-ui, sans-serif";
  const phone = compactPhone();
  const selected = map.screen.find((s) => s.n.role === "selected");
  if (selected) placeLabel(selected.n.name, selected.x, selected.y, serif, ink, "above");
  if (phone) return;
  if (map.namers <= 14) {
    for (const s of map.screen) {
      if (s.n.role !== "namer") continue;
      placeLabel(s.n.name, s.x, s.y, utility, mute, "out");
    }
  }
  const siblings = map.screen
    .filter((s) => s.n.role === "other")
    .sort((a, b) => (b.n.shared || 0) - (a.n.shared || 0));
  for (const s of siblings.slice(0, 8)) {
    placeLabel(s.n.name, s.x, s.y, utility, mute, "out");
  }
}

function tokenColor(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

function viewFromLocation() {
  const q = new URLSearchParams(location.search).get("view");
  if (q === "map" || location.hash === "#map") return "map";
  return "list";
}

function setView(view, viaUser) {
  state.view = view === "map" ? "map" : "list";
  const grid = $("wires");
  if (grid) grid.dataset.view = state.view;
  const list = $("wires-list");
  const mapPane = $("wires-map");
  if (list) list.hidden = state.view !== "list";
  if (mapPane) mapPane.hidden = state.view !== "map";
  const listBtn = $("view-list");
  const mapBtn = $("view-map");
  if (listBtn) {
    listBtn.classList.toggle("on", state.view === "list");
    listBtn.setAttribute("aria-selected", state.view === "list" ? "true" : "false");
  }
  if (mapBtn) {
    mapBtn.classList.toggle("on", state.view === "map");
    mapBtn.setAttribute("aria-selected", state.view === "map" ? "true" : "false");
  }
  if (viaUser) {
    if (state.view === "map") {
      if (location.hash !== "#map") history.replaceState(null, "", "#map");
    } else if (location.hash === "#map") {
      history.replaceState(null, "", location.pathname + location.search);
    }
  }
  if (state.view === "map") requestAnimationFrame(drawMap);
}

function fileProcessor(i) {
  const p = state.processors[i];
  if (!p) return;
  state.focus = i;
  map.focusKey = null;
  renderTable();
  renderStub();
  if (state.view === "map") drawMap();
  revealFile();
}

function hitNode(sx, sy) {
  let best = null;
  let bestD = 16;
  for (const s of map.screen) {
    const d = Math.hypot(s.x - sx, s.y - sy);
    if (d < bestD) {
      bestD = d;
      best = s.n;
    }
  }
  return best;
}

function onMapPointer(e) {
  if (e.button != null && e.button !== 0) return;
  const canvas = $("fig1");
  map.drag = {
    x: e.clientX,
    y: e.clientY,
    yaw: map.yaw,
    pitch: map.pitch,
    moved: false,
    id: e.pointerId,
  };
  if (canvas && e.pointerId != null) canvas.setPointerCapture(e.pointerId);
}

function onMapMove(e) {
  if (!map.drag) return;
  const dx = e.clientX - map.drag.x;
  const dy = e.clientY - map.drag.y;
  if (Math.abs(dx) + Math.abs(dy) > 4) map.drag.moved = true;
  map.yaw = map.drag.yaw + dx * 0.008;
  map.pitch = Math.max(-1.15, Math.min(1.15, map.drag.pitch + dy * 0.008));
  drawMap();
}

function onMapUp(e) {
  const drag = map.drag;
  map.drag = null;
  if (!drag || drag.moved) return;
  const canvas = $("fig1");
  const rect = canvas.getBoundingClientRect();
  const n = hitNode(e.clientX - rect.left, e.clientY - rect.top);
  if (!n) return;
  if (n.kind === "company" && n.slug) {
    window.location.href = `./c/${encodeURIComponent(n.slug)}.html`;
    return;
  }
  if (n.kind === "processor" && n.focus != null) fileProcessor(n.focus);
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
    fileProcessor(i);
  });
  $("view-list").addEventListener("click", () => setView("list", true));
  $("view-map").addEventListener("click", () => setView("map", true));
  const canvas = $("fig1");
  canvas.addEventListener("pointerdown", onMapPointer);
  canvas.addEventListener("pointermove", onMapMove);
  canvas.addEventListener("pointerup", onMapUp);
  canvas.addEventListener("pointercancel", () => {
    map.drag = null;
  });
  window.addEventListener("hashchange", () => setView(viewFromLocation(), false));
  window.addEventListener("resize", () => {
    if (state.view === "map") drawMap();
  });
  if (typeof ResizeObserver === "function") {
    const field = canvas.parentElement;
    if (field) {
      new ResizeObserver(() => {
        if (state.view === "map") drawMap();
      }).observe(field);
    }
  }
}

function revealFile() {
  const el = $("stub");
  if (!el || el.hidden) return;
  if (!window.matchMedia("(max-width: 1100px)").matches) return;
  el.scrollIntoView({ block: "nearest", behavior: "auto" });
}

async function load() {
  bind();
  setView(viewFromLocation(), false);
  try {
    const [reg, wires] = await Promise.all([
      fetch(dataUrl("./data.json"), { cache: "no-store" }).then((r) => r.json()),
      fetch(dataUrl("./data/subprocessors.json"), { cache: "no-store" }).then((r) => (r.ok ? r.json() : { edges: [] })),
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
  if (state.view === "map") drawMap();
}

if (typeof document !== "undefined" && document.getElementById("wire-body")) {
  load();
}
