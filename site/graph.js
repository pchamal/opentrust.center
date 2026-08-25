import { $, escapeHtml, fillIssue, dataUrl, nameWithIcon, fileFlags, fileIndexHtml, fileScore } from "./lib.js";
import { arrange, clickSort, cmpText, paintHeaders } from "./sort.js";

const SORT_DEFAULTS = {
  name: "asc",
  exposure: "desc",
  file: "desc",
  source: "asc",
};

const state = {
  data: null,
  edges: [],
  companies: new Map(),
  processors: [],
  focus: 0,
  focusKey: "",
  sort: "name",
  dir: "asc",
  view: "list",
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

const MONTH_NAME =
  "january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec";
const DATE_HEADER_RE = /^(date(?: of change)?|effective date)$/i;
const DATE_NAME_RE = new RegExp(
  `^(?:(?:19|20|21)\\d{2}|\\d{4}-\\d{2}-\\d{2}|\\d{1,2}[./]\\d{1,2}[./](?:\\d{2}|\\d{4})|\\d{1,2}[\\s.\\-]+(?:${MONTH_NAME})[\\s.\\-]+\\d{4}|(?:${MONTH_NAME})[\\s.\\-]+\\d{1,2},?[\\s.\\-]+\\d{4}|(?:${MONTH_NAME})[\\s.\\-]+\\d{4})$`,
  "i",
);

export function looksLikeDateName(s) {
  const t = String(s || "").replace(/\s+/g, " ").trim();
  if (!t) return false;
  if (DATE_HEADER_RE.test(t)) return true;
  if (DATE_NAME_RE.test(t)) return true;
  const spaced = t.replace(/[-_]+/g, " ");
  return spaced !== t && DATE_NAME_RE.test(spaced);
}

export function looksLikeProcessorName(s) {
  const t = String(s || "").trim();
  if (!t) return false;
  if (/^listed on public/i.test(t)) return false;
  if (/listed on/i.test(t) || /\bpage\b/i.test(t)) return false;
  if (looksLikeDateName(t)) return false;
  return true;
}

export function namedProcessors(rows) {
  return (rows || []).filter(
    (p) => p && !looksLikeDateName(p.name) && !looksLikeDateName(p.id) && !looksLikeDateName(p.slug),
  );
}

export function defaultProcessorIndex(rows) {
  const list = rows || [];
  for (const key of ["aws", "amazon-web-services"]) {
    const i = list.findIndex((p) => p && (p.id === key || p.slug === key));
    if (i >= 0) return i;
  }
  const i = list.findIndex((p) => /amazon web services/i.test(String((p && p.name) || "")));
  return i >= 0 ? i : 0;
}

function processorDisplayName(e, node, to) {
  const nodeName = node && node.name ? String(node.name).trim() : "";
  if (looksLikeProcessorName(nodeName)) return humanizeProcessorName(nodeName);
  if (to && looksLikeProcessorName(to)) return humanizeProcessorName(to) || titleCaseSlug(to);
  const evidence = e && e.evidence ? String(e.evidence).trim() : "";
  if (looksLikeProcessorName(evidence)) return humanizeProcessorName(evidence);
  return humanizeProcessorName((e && e.processor) || to);
}

function normalizeEdges(wires, companies) {
  const nodes = new Map((wires.nodes || []).map((n) => [n.id, n]));
  return (wires.edges || [])
    .filter((e) => {
      if (!e.source_url) return false;
      const to = e.to || e.processor_slug || e.processor;
      const node = nodes.get(to) || {};
      return !looksLikeDateName(node.name) && !looksLikeDateName(to) && !looksLikeDateName(e.evidence);
    })
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

export function rankProcessors(edges, companies) {
  const by = new Map();
  for (const e of edges) {
    const key = e.processor_id || e.processor_slug || e.processor;
    if (!by.has(key)) {
      by.set(key, {
        id: key,
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
    const score = self ? fileScore(fileFlags(self)) : 0;
    rows.push({
      id: rec.id || rec.slug || rec.name,
      name: rec.name,
      slug: rec.slug,
      domain: rec.domain || (self && self.domain) || "",
      inRegister: Boolean(self),
      tier: self ? self.tier : null,
      score,
      exposure,
      thinness: t,
      risk,
      sources: [...rec.sources],
      namers: rec.namers,
    });
  }
  return rows;
}

export function sourceHost(p) {
  const url = p && p.sources && p.sources[0];
  return url ? hostOfSafe(url) : "";
}

export function compareProcessors(a, b, key) {
  switch (key) {
    case "name":
      return cmpText(a && a.name, b && b.name);
    case "exposure":
      return ((a && a.exposure) || 0) - ((b && b.exposure) || 0);
    case "file":
      return ((a && a.score) || 0) - ((b && b.score) || 0);
    case "risk":
      return ((a && a.risk) || 0) - ((b && b.risk) || 0) || ((a && a.exposure) || 0) - ((b && b.exposure) || 0);
    case "source":
      return cmpText(sourceHost(a), sourceHost(b));
    default:
      return cmpText(a && a.name, b && b.name);
  }
}

export function arrangeProcessors(rows, sort, dir) {
  return arrange(rows, sort || "name", dir || "asc", compareProcessors);
}

function syncFocus() {
  if (!state.processors.length) {
    state.focus = 0;
    return;
  }
  const i = state.focusKey
    ? state.processors.findIndex((p) => processorKey(p) === state.focusKey)
    : -1;
  state.focus = i >= 0 ? i : 0;
  state.focusKey = processorKey(state.processors[state.focus]);
}

function renderTable() {
  const body = $("wire-body");
  if (!state.processors.length) {
    $("wire-table").hidden = true;
    $("empty-wires").hidden = false;
    paintHeaders($("wire-table"), state.sort, state.dir);
    return;
  }
  $("wire-table").hidden = false;
  $("empty-wires").hidden = true;
  syncFocus();
  paintHeaders($("wire-table"), state.sort, state.dir);
  body.innerHTML = state.processors
    .map((p, i) => {
      const row = p.slug ? state.companies.get(p.slug) : null;
    const score = Number.isFinite(p.score) ? p.score : row ? fileScore(fileFlags(row)) : null;
    /* No register file is inconclusive, not zero: blank rules, never a false miss. */
    const ticks = row ? fileIndexHtml(row) : "";
    const scoreCell = row
      ? `<span class="file-num">${score}</span>${ticks}`
      : `<span class="absent">not in register</span>`;
    const src0 = p.sources[0];
    const srcCell = src0
      ? `<a href="${escapeHtml(src0)}" target="_blank" rel="noopener noreferrer">${escapeHtml(hostOfSafe(src0))}</a>`
      : `<span class="absent">not on file</span>`;
    return `<tr data-i="${i}" class="folio${state.focus === i ? " on selected" : ""}">
        <td class="name" data-label="Processor">${escapeHtml(p.name)}</td>
        <td data-label="Named by">${p.exposure}</td>
        <td class="file" data-label="Completeness">${scoreCell}</td>
        <td data-label="Source">${srcCell}</td>
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

/** Who-named-them list: same 12px ink rule as Companies. Seals / unreadable marks are name only. */
export function namerInk(src) {
  const file = String(src || "")
    .replace(/^\/+/, "")
    .replace(/^favicons\//, "")
    .toLowerCase();
  if (!file) return "";
  // Claroty is a circular C / badge. At 12px the ink pass is a solid-fill seal.
  if (file === "claroty.com.png") return "";
  // Zscaler's swoosh exists, but at 12px it is not readable as Zscaler without the name.
  if (file === "zscaler.com.png") return "";
  return src;
}

function namerLine(n) {
  const co = state.companies.get(n.company);
  const label = co ? co.name : n.company;
  const href = co ? `./c/${encodeURIComponent(co.slug)}.html` : null;
  const host = n.source_url ? hostOfSafe(n.source_url) : "";
  const src = n.source_url
    ? ` <span class="muted">· <a href="${escapeHtml(n.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(host)}</a></span>`
    : "";
  const named = nameWithIcon(label, namerInk(iconForDomain(co && co.domain, co)));
  return href
    ? `<li><a href="${href}">${named}</a>${src}</li>`
    : `<li>${named}${src}</li>`;
}

function renderStub() {
  const el = $("stub");
  if (state.focus == null) {
    el.hidden = true;
    document.title = "opentrust.center — public trust ledger";
    return;
  }
  const p = state.processors[state.focus];
  if (!p) {
    el.hidden = true;
    document.title = "opentrust.center — public trust ledger";
    return;
  }
  el.hidden = false;
  const status = p.inRegister
    ? `<p class="ident-meta">on file · <a href="./c/${encodeURIComponent(p.slug)}.html">dossier</a></p>`
    : `<p class="ident-meta"><span class="absent">not in register</span></p>`;
  const self = p.slug ? state.companies.get(p.slug) : null;
  el.innerHTML = `<h2>${nameWithIcon(p.name, iconForDomain(p.domain, self))}</h2>
    ${status}
    <p class="ident-meta">named by ${p.exposure} · exposure, not a score</p>
    <p class="fig-sub">Who named them, as published.</p>
    <ul class="guesses">${p.namers.map(namerLine).join("")}</ul>
    <button type="button" class="go-out" id="copy-permalink">copy link to this processor</button>`;
  document.title = `${p.name} · named by ${p.exposure} · opentrust.center`;
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

const NEIGHBOR_OTHERS_CAP = 8;

export function processorKey(p) {
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
  const others = [...otherVotes.entries()]
    .map(([id, votes]) => {
      let count = 0;
      for (const n of votes.values()) count += n;
      return { id, count, rec: byProc.get(id) };
    })
    .filter((o) => {
      if (looksLikeDateName(o.id)) return false;
      return !o.rec || !looksLikeDateName(o.rec.p && o.rec.p.name);
    })
    .sort((a, b) => b.count - a.count || String(a.id).localeCompare(String(b.id)))
    .slice(0, NEIGHBOR_OTHERS_CAP);
  const nodes = [];
  const index = new Map();
  function add(id, spec) {
    if (index.has(id)) return index.get(id);
    const n = { id, x: 0, y: 0, z: 0, ...spec };
    index.set(id, n);
    nodes.push(n);
    return n;
  }
  const selectedNode = add(selectedId, {
    kind: "processor",
    role: "selected",
    name: focus.name,
    slug: focus.slug,
    inRegister: focus.inRegister,
    focus: byProc.has(selectedId) ? byProc.get(selectedId).i : null,
  });
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
  for (const o of others) {
    const b = index.get(o.id);
    if (selectedNode && b) links.push({ a: selectedNode, b });
  }
  return { nodes, links, namers: namerSlugs.length, others: others.length };
}

function placeNeighborhood(nodes) {
  const selected = nodes.find((n) => n.role === "selected");
  const others = nodes.filter((n) => n.role === "other");
  if (selected) {
    selected.x = 0;
    selected.y = 0;
    selected.z = 0;
  }
  others.forEach((n, i) => {
    const a = -Math.PI / 2 + (2 * Math.PI * i) / Math.max(others.length, 1);
    n.x = Math.cos(a) * 0.68;
    n.y = Math.sin(a) * 0.68;
    n.z = 0;
  });
}

function compactPhone() {
  return typeof window !== "undefined" && window.matchMedia("(max-width: 390px)").matches;
}

function graphShouldDraw(hood) {
  if (!hood || !hood.nodes.length) return false;
  if (compactPhone()) return false;
  const focus = selectedProcessor();
  if (focus && looksLikeDateName(focus.name)) return false;
  return true;
}

function ensureNeighborhood() {
  const focus = selectedProcessor();
  const key = focus ? processorKey(focus) : null;
  if (map.focusKey === key && map.nodes.length) return;
  const hood = neighborhoodOf(focus, state.edges, state.processors, state.companies);
  placeNeighborhood(hood.nodes);
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
    const half = selected ? 5 : 3.5;
    ctx.beginPath();
    ctx.rect(s.x - half, s.y - half, half * 2, half * 2);
    ctx.fillStyle = ink;
    ctx.fill();
    ctx.strokeStyle = selected ? teal : ink;
    ctx.lineWidth = selected ? 2 : 1;
    ctx.stroke();
  }

  function placeLabel(text, x, y, font, color, prefer) {
    ctx.font = font;
    const tw = ctx.measureText(text).width;
    let lx = x + 10;
    let ly = y + 4;
    if (prefer === "above") {
      lx = x - tw / 2;
      ly = y - 14;
    } else {
      const dx = x - w / 2;
      const dy = y - h / 2;
      const len = Math.hypot(dx, dy) || 1;
      lx = x + (dx / len) * 16 - tw / 2;
      ly = y + (dy / len) * 14 + 4;
    }
    if (lx + tw > w - 8) lx = w - 8 - tw;
    if (lx < 8) lx = 8;
    if (ly < 14) ly = y + 18;
    if (ly > h - 6) ly = y - 10;
    ctx.fillStyle = color;
    ctx.fillText(text, lx, ly);
  }

  const serif = "600 17px 'Source Serif 4', Georgia, 'Times New Roman', serif";
  const utility = "13px 'Atkinson Hyperlegible Next', Arial, system-ui, sans-serif";
  for (const s of map.screen) {
    const selected = isSelectedNode(s.n);
    placeLabel(s.n.name, s.x, s.y, selected ? serif : utility, ink, selected ? "above" : "out");
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

export function focusIdFromLocation(loc = window.location) {
  const params = new URLSearchParams(loc.search || "");
  const q = params.get("p");
  if (q) return q;
  const hash = String(loc.hash || "").replace(/^#/, "");
  if (hash.startsWith("p=")) {
    try {
      return decodeURIComponent(hash.slice(2));
    } catch {
      return hash.slice(2);
    }
  }
  return "";
}

function processorIndex(id) {
  const fallback = defaultProcessorIndex(state.processors);
  if (!id) return fallback;
  const key = String(id);
  if (looksLikeDateName(key)) return fallback;
  const i = state.processors.findIndex(
    (p) => p.id === key || p.slug === key || p.name === key,
  );
  return i >= 0 ? i : fallback;
}

function renderHoodLine() {
  const el = $("hood-line");
  const cap = $("fig-cap");
  const canvas = $("fig1");
  const p = selectedProcessor();
  if (cap) {
    cap.textContent = p ? `Fig. 1 · Neighborhood of ${p.name}` : "Fig. 1 · Neighborhood";
  }
  if (canvas && p) canvas.setAttribute("aria-label", `Neighborhood of ${p.name}`);
  if (!el) return;
  if (state.view !== "map") {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  if (!p) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  const n = new Set((p.namers || []).map((x) => x.company).filter(Boolean)).size;
  el.hidden = false;
  el.textContent = `neighborhood · ${p.name} · ${n} named`;
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
  renderHoodLine();
  if (state.view === "map") requestAnimationFrame(drawMap);
}

function fileProcessor(i) {
  const p = state.processors[i];
  if (!p) return;
  state.focus = i;
  state.focusKey = processorKey(p);
  map.focusKey = null;
  renderTable();
  renderStub();
  renderHoodLine();
  if (state.view === "map") drawMap();
  const id = p.id || p.slug;
  if (id && window.history && window.history.replaceState && state.view !== "map") {
    const url = new URL(window.location.href);
    url.searchParams.delete("p");
    url.hash = "p=" + encodeURIComponent(id);
    if (url.href !== window.location.href) {
      window.history.replaceState(null, "", url);
    }
  }
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
  const head = document.querySelector("#wire-table thead");
  if (head) {
    head.addEventListener("click", (e) => {
      const th = e.target.closest("th[data-sort]");
      if (!th) return;
      const next = clickSort(state, th.getAttribute("data-sort"), SORT_DEFAULTS);
      state.sort = next.sort;
      state.dir = next.dir;
      state.processors = arrangeProcessors(state.processors, state.sort, state.dir);
      renderTable();
      renderStub();
      renderHoodLine();
      if (state.view === "map") drawMap();
    });
  }
  $("wire-body").addEventListener("click", (e) => {
    if (e.target.closest("a")) return;
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
  $("wires").addEventListener("click", (e) => {
    const btn = e.target.closest("#copy-permalink");
    if (!btn || !navigator.clipboard) return;
    navigator.clipboard.writeText(window.location.href).then(() => {
      const prev = btn.textContent;
      btn.textContent = "copied · " + window.location.href;
      setTimeout(() => { btn.textContent = prev; }, 1800);
    });
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
  window.addEventListener("hashchange", () => {
    setView(viewFromLocation(), false);
    const id = focusIdFromLocation();
    if (!id) return;
    const i = processorIndex(id);
    if (i === state.focus) return;
    state.focus = i;
    map.focusKey = null;
    renderTable();
    renderStub();
    renderHoodLine();
    if (state.view === "map") drawMap();
  });
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
    state.processors = arrangeProcessors(
      namedProcessors(rankProcessors(state.edges, state.companies)),
      state.sort,
      state.dir,
    );
    state.focus = processorIndex(focusIdFromLocation());
    const focused = state.processors[state.focus];
    if (focused) state.focusKey = processorKey(focused);
    fillIssue($("issue"), reg);
  } catch {
    state.edges = [];
  }
  renderTable();
  renderStub();
  renderHoodLine();
  if (state.view === "map") drawMap();
}

if (typeof document !== "undefined" && document.getElementById("wire-body")) {
  load();
}
