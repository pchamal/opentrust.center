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
  yaw: 0.4,
  pitch: 0.22,
  laid: false,
  drag: null,
};

function hash01(s) {
  let h = 2166136261;
  const str = String(s || "");
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967296;
}

function processorKey(p) {
  return p.id || p.slug || p.name;
}

function buildNetwork() {
  const nodes = [];
  const index = new Map();
  function add(id, spec) {
    if (index.has(id)) return index.get(id);
    const n = { id, vx: 0, vy: 0, vz: 0, x: 0, y: 0, z: 0, ...spec };
    index.set(id, n);
    nodes.push(n);
    return n;
  }
  state.processors.forEach((p, i) => {
    add(processorKey(p), {
      kind: "processor",
      name: p.name,
      slug: p.slug,
      inRegister: p.inRegister,
      exposure: p.exposure,
      focus: i,
    });
  });
  for (const e of state.edges) {
    const co = state.companies.get(e.company);
    add("co:" + e.company, {
      kind: "company",
      name: co ? co.name : e.company,
      slug: e.company,
    });
  }
  const links = [];
  for (const e of state.edges) {
    const a = index.get("co:" + e.company);
    const b = index.get(e.processor_id || e.processor_slug || e.processor);
    if (!a || !b) continue;
    links.push({ a, b });
  }
  return { nodes, links };
}

function layoutNetwork(nodes, links, ticks) {
  const n = nodes.length;
  if (!n) return;
  for (let i = 0; i < n; i++) {
    const a = hash01(nodes[i].id);
    const b = hash01(nodes[i].id + "#");
    const u = Math.acos(Math.min(1, Math.max(-1, 2 * a - 1)));
    const v = 2 * Math.PI * b;
    nodes[i].x = Math.sin(u) * Math.cos(v);
    nodes[i].y = Math.sin(u) * Math.sin(v);
    nodes[i].z = Math.cos(u);
    nodes[i].vx = 0;
    nodes[i].vy = 0;
    nodes[i].vz = 0;
  }
  const kRep = 0.32;
  const kSpring = 0.04;
  const rest = 0.52;
  const kCenter = 0.018;
  const damp = 0.86;
  for (let t = 0; t < ticks; t++) {
    const alpha = 1 - t / ticks;
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        let dx = nodes[i].x - nodes[j].x;
        let dy = nodes[i].y - nodes[j].y;
        let dz = nodes[i].z - nodes[j].z;
        const d2 = dx * dx + dy * dy + dz * dz + 0.02;
        const f = (kRep * alpha) / d2;
        dx *= f;
        dy *= f;
        dz *= f;
        nodes[i].vx += dx;
        nodes[i].vy += dy;
        nodes[i].vz += dz;
        nodes[j].vx -= dx;
        nodes[j].vy -= dy;
        nodes[j].vz -= dz;
      }
    }
    for (const L of links) {
      let dx = L.b.x - L.a.x;
      let dy = L.b.y - L.a.y;
      let dz = L.b.z - L.a.z;
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) + 1e-6;
      const f = (dist - rest) * kSpring * alpha;
      dx = (dx / dist) * f;
      dy = (dy / dist) * f;
      dz = (dz / dist) * f;
      L.a.vx += dx;
      L.a.vy += dy;
      L.a.vz += dz;
      L.b.vx -= dx;
      L.b.vy -= dy;
      L.b.vz -= dz;
    }
    for (const p of nodes) {
      p.vx += -p.x * kCenter;
      p.vy += -p.y * kCenter;
      p.vz += -p.z * kCenter;
      p.vx *= damp;
      p.vy *= damp;
      p.vz *= damp;
      p.x += p.vx;
      p.y += p.vy;
      p.z += p.vz;
    }
  }
  let max = 1e-6;
  for (const p of nodes) max = Math.max(max, Math.hypot(p.x, p.y, p.z));
  for (const p of nodes) {
    p.x /= max;
    p.y /= max;
    p.z /= max;
  }
}

function ensureLayout() {
  if (map.laid) return;
  const net = buildNetwork();
  map.nodes = net.nodes;
  map.links = net.links;
  // Compute once, then stop. prefers-reduced-motion: still. Drag still works.
  layoutNetwork(map.nodes, map.links, 160);
  map.laid = true;
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
  const focus = selectedProcessor();
  if (!focus || n.kind !== "processor") return false;
  return n.focus === state.focus;
}

function drawMap() {
  const canvas = $("fig1");
  if (!canvas || state.view !== "map") return;
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
  if (!state.processors.length) return;
  ensureLayout();

  const ink = tokenColor("--ot-ledger-black", "#0B1411");
  const teal = tokenColor("--ot-evidence-teal", "#00685C");
  const mute = tokenColor("--ot-graphite", "#51615B");
  const focus = selectedProcessor();
  const named = new Set();
  if (focus) {
    named.add(processorKey(focus));
    for (const n of focus.namers) named.add("co:" + n.company);
  }

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
    const half = s.n.kind === "processor" ? 3.5 : 2.5;
    const fill = s.n.kind === "company" || s.n.inRegister;
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
  function placeLabel(text, x, y, font, color) {
    ctx.font = font;
    const tw = ctx.measureText(text).width;
    let lx = x + 8;
    let ly = y + 4;
    if (lx + tw > w - 8) lx = x - 8 - tw;
    if (ly < 14) ly = y + 16;
    if (ly > h - 6) ly = y - 8;
    const box = { x: lx, y: ly - 12, w: tw, h: 16 };
    for (const p of placed) {
      if (box.x < p.x + p.w && box.x + box.w > p.x && box.y < p.y + p.h && box.y + box.h > p.y) {
        return;
      }
    }
    placed.push(box);
    ctx.fillStyle = color;
    ctx.fillText(text, lx, ly);
  }

  const serif = "600 17px 'Source Serif 4', Georgia, 'Times New Roman', serif";
  const utility = "13px 'Atkinson Hyperlegible Next', Arial, system-ui, sans-serif";
  const ambient = map.screen
    .filter((s) => s.n.kind === "processor")
    .sort((a, b) => (b.n.exposure || 0) - (a.n.exposure || 0))
    .slice(0, 8);

  if (focus) {
    for (const s of map.screen) {
      if (!named.has(s.n.id)) continue;
      placeLabel(s.n.name, s.x, s.y, serif, ink);
    }
  } else {
    for (const s of ambient) {
      placeLabel(s.n.name, s.x, s.y, utility, mute);
    }
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

load();
