import { $, escapeHtml, fillIssue, dataUrl, inkIcon } from "./lib.js";
import { arrange, clickSort, cmpText, paintHeaders } from "./sort.js";

const GEO_GROUPS = {
  americas: ["US", "CA", "BR"],
  europe: ["EU", "DE", "ES", "FR", "CH"],
  uk: ["GB"],
  apac: ["SG", "AU", "JP", "KR", "TH"],
  international: ["global"],
};

const TILT = (15 * Math.PI) / 180;

const SORT_DEFAULTS = {
  name: "asc",
  files: "desc",
  kind: "asc",
  geography: "asc",
  issuer: "asc",
  weight: "desc",
  industry: "asc",
};

const state = {
  items: [],
  companies: [],
  q: "",
  geo: "all",
  industry: "all",
  kind: "all",
  sort: "files",
  dir: "desc",
  depth: new Map(),
  rot: 0,
  drag: null,
  resumeAt: 0,
  lastTs: 0,
  raf: 0,
  geom: null,
  land: [],
  icons: { companies: {}, marks: {} },
};

function markField(item, key) {
  if (!item) return "";
  if (key === "weight") return item.weight;
  if (key === "files") return item.files;
  if (key === "geography") return (item.geography || []).join(" ");
  if (key === "industry") return (item.industry || []).join(" ");
  return item[key] || "";
}

export function companyCitesMark(company, mark) {
  if (!company || !mark) return false;
  const id = mark.id;
  if ((company.attestations || []).some((a) => a && a.id === id)) return true;
  if (id === "fedramp" && company.fedramp) return true;
  return (company.certs || []).some((name) => {
    const att = (company.attestations || []).find((a) => a.name === name);
    return att && att.id === id;
  });
}

export function citeCount(companies, mark) {
  return (companies || []).reduce((n, c) => n + (companyCitesMark(c, mark) ? 1 : 0), 0);
}

export function parseMarkQuery(raw) {
  let s = String(raw || "").trim();
  if (s.startsWith("/")) s = s.slice(1).trim();
  return s
    .toLowerCase()
    .split(/[\s,]+/)
    .filter(Boolean);
}

export function markHay(item) {
  return [item && item.name, item && item.short, item && item.id]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

export function markMatchesQuery(item, tokens) {
  if (!tokens || !tokens.length) return true;
  const hay = markHay(item);
  return tokens.every((t) => hay.includes(t));
}

export function filterMarks(items, q) {
  const tokens = parseMarkQuery(q);
  return (items || []).filter((item) => markMatchesQuery(item, tokens));
}

export function compareMarks(a, b, key) {
  if (key === "files" || key === "weight") {
    return (Number(markField(a, key)) || 0) - (Number(markField(b, key)) || 0);
  }
  return cmpText(markField(a, key), markField(b, key));
}

export function arrangeMarks(rows, sort, dir) {
  return arrange(rows, sort || "files", dir || "desc", compareMarks);
}

function geosOf(item) {
  return item.geography || [];
}

function matches(item) {
  if (!markMatchesQuery(item, parseMarkQuery(state.q))) return false;
  if (state.kind !== "all" && item.kind !== state.kind) return false;
  if (state.industry !== "all") {
    const inds = item.industry || [];
    if (!inds.includes(state.industry) && !inds.includes("all")) return false;
  }
  if (state.geo !== "all") {
    const gs = geosOf(item);
    const group = GEO_GROUPS[state.geo];
    if (group) {
      if (!gs.some((g) => group.includes(g))) return false;
    } else if (!gs.includes(state.geo)) return false;
  }
  return true;
}

function citedBy(id) {
  const mark = state.items.find((x) => x.id === id) || { id };
  return state.companies.filter((c) => companyCitesMark(c, mark));
}

function syncUrl() {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams();
  const q = state.q.trim();
  if (q) params.set("q", q);
  const qs = params.toString();
  const next = (qs ? "?" + qs : "") + window.location.hash;
  const path = window.location.pathname + next;
  if (path !== window.location.pathname + window.location.search + window.location.hash) {
    history.replaceState(null, "", path || window.location.pathname);
  }
}

function renderBook() {
  const rows = arrangeMarks(state.items.filter(matches), state.sort, state.dir);
  paintHeaders($("book-sort"), state.sort, state.dir);
  $("book-count").textContent = `showing ${rows.length} of ${state.items.length}`;
  syncUrl();
  const miss = $("book-miss");
  const book = $("book");
  if (!rows.length) {
    if (miss) miss.hidden = false;
    if (book) book.innerHTML = "";
    return;
  }
  if (miss) miss.hidden = true;
  book.innerHTML = rows
    .map((item) => {
      const deep = state.depth.get(item.id) === "elaborate";
      const body = deep ? item.elaborate : item.eli5;
      const related = (item.related || [])
        .map((id) => {
          const r = state.items.find((x) => x.id === id);
          const label = r ? r.short || r.name : id;
          return `<a href="#${escapeHtml(id)}">${escapeHtml(label)}</a>`;
        })
        .join(" · ");
      const citers = citedBy(item.id);
      const files = item.files != null ? item.files : citers.length;
      const citeLine = citers.length
        ? citers
            .slice(0, 8)
            .map((c) => `<a href="./c/${encodeURIComponent(c.slug)}.html">${escapeHtml(c.name)}</a>`)
            .join(" · ") + (citers.length > 8 ? ` +${citers.length - 8}` : "")
        : `<span class="absent">none in this index</span>`;
      const geo = (item.geography || []).join(" · ");
      const ind = (item.industry || []).join(" · ");
      const markIco = inkIcon((state.icons.marks || {})[item.id]);
      return `<article class="entry" id="${escapeHtml(item.id)}">
        <h2>${markIco}${escapeHtml(item.name)}</h2>
        <p class="entry-meta">${escapeHtml(item.kind === "framework" ? "standard" : item.kind)} · ${escapeHtml(geo)} · ${escapeHtml(item.issuer)} · ${files} files</p>
        <p class="entry-meta">${escapeHtml(ind)}</p>
        <p class="entry-body">${escapeHtml(body || "")}</p>
        <button type="button" class="depth" data-id="${escapeHtml(item.id)}">${deep ? "eli-5" : "elaborate"}</button>
        <p class="related">related · ${related || "—"}</p>
        <p class="related">cited by · ${citeLine}</p>
      </article>`;
    })
    .join("");
}

function regionAt(lng, lat) {
  if (lng >= -12 && lng <= 3 && lat >= 49 && lat <= 61) return "uk";
  if (lng >= -170 && lng <= -25) return "americas";
  if (lng >= -15 && lng <= 40 && lat >= 34) return "europe";
  if (lng >= 60) return "apac";
  return "international";
}

function sph(lng, lat) {
  const λ = (lng * Math.PI) / 180 - state.rot;
  const φ = (lat * Math.PI) / 180;
  const cosφ = Math.cos(φ);
  const x = cosφ * Math.sin(λ);
  const y0 = Math.sin(φ);
  const z0 = cosφ * Math.cos(λ);
  const c = Math.cos(TILT);
  const s = Math.sin(TILT);
  return { x, y: y0 * c - z0 * s, z: y0 * s + z0 * c };
}

function toScreen(p, cx, cy, R) {
  return [cx + R * p.x, cy - R * p.y];
}

function lerpZ(a, b) {
  const t = a.z / (a.z - b.z);
  return {
    x: a.x + (b.x - a.x) * t,
    y: a.y + (b.y - a.y) * t,
    z: 0,
  };
}

function token(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

function ink() {
  return {
    land: token("--ot-paper", "#EDF2F0"),
    sea: token("--ot-sheet-white", "#FFFFFF"),
    rule: token("--ot-rule-strong", "#70817A"),
    mark: token("--ot-carbon", "#17211D"),
  };
}

/* Unwrap so a ring that crosses ±180 interpolates the short ocean, not the long way. */
function unwrapRing(ring) {
  const out = [];
  let off = 0;
  for (let i = 0; i < ring.length; i++) {
    const lng = ring[i][0];
    const lat = ring[i][1];
    if (i === 0) {
      out.push([lng, lat]);
      continue;
    }
    const prev = out[i - 1][0];
    let x = lng + off;
    if (x - prev > 180) off -= 360;
    else if (prev - x > 180) off += 360;
    out.push([lng + off, lat]);
  }
  return out;
}

/* Natural Earth 110m land, public domain. Vendored at ./data/ne-110m-land.json */
function parseLand(fc) {
  const polys = [];
  for (const f of fc.features || []) {
    const g = f.geometry;
    if (!g) continue;
    const parts = g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : [];
    for (const part of parts) {
      if (!part || !part.length) continue;
      polys.push({
        outer: unwrapRing(part[0]),
        holes: part.slice(1).map(unwrapRing),
      });
    }
  }
  return polys;
}

/* Horizon chord → short limb arc so land meets the disk, not a flat cut. */
function limbArc(a, b) {
  const t0 = Math.atan2(a.y, a.x);
  let d = Math.atan2(b.y, b.x) - t0;
  if (d > Math.PI) d -= 2 * Math.PI;
  if (d < -Math.PI) d += 2 * Math.PI;
  const n = Math.max(1, Math.ceil(Math.abs(d) / (Math.PI / 18)));
  const pts = [];
  for (let i = 1; i < n; i++) {
    const t = t0 + (d * i) / n;
    pts.push({ x: Math.cos(t), y: Math.sin(t), z: 0 });
  }
  return pts;
}

function clipFront(ring) {
  const n = ring.length;
  const closed = n > 1 && ring[0][0] === ring[n - 1][0] && ring[0][1] === ring[n - 1][1];
  const count = closed ? n - 1 : n;
  if (count < 2) return [];
  const verts = [];
  for (let i = 0; i < count; i++) verts.push(sph(ring[i][0], ring[i][1]));
  let start = -1;
  for (let i = 0; i < count; i++) {
    if (verts[i].z > 0) {
      start = i;
      break;
    }
  }
  if (start < 0) return [];
  const out = [];
  let exit = null;
  for (let k = 0; k < count; k++) {
    const i = (start + k) % count;
    const a = verts[i];
    const b = verts[(i + 1) % count];
    if (a.z > 0) out.push(a);
    if ((a.z > 0) !== (b.z > 0)) {
      const h = lerpZ(a, b);
      if (a.z > 0) {
        out.push(h);
        exit = h;
      } else {
        if (exit) out.push(...limbArc(exit, h));
        out.push(h);
        exit = null;
      }
    }
  }
  return out;
}

function invertScreen(sx, sy, geom) {
  const { cx, cy, R } = geom;
  const x = (sx - cx) / R;
  const y = (cy - sy) / R;
  const rr = x * x + y * y;
  if (rr > 1) return null;
  const z = Math.sqrt(Math.max(0, 1 - rr));
  const c = Math.cos(TILT);
  const s = Math.sin(TILT);
  const y0 = y * c + z * s;
  const z0 = -y * s + z * c;
  const φ = Math.asin(Math.max(-1, Math.min(1, y0)));
  const λ = Math.atan2(x, z0) + state.rot;
  let lng = (λ * 180) / Math.PI;
  lng = ((lng + 540) % 360) - 180;
  return { lng, lat: (φ * 180) / Math.PI };
}

function measure(wrap) {
  const w = wrap.clientWidth;
  const h = wrap.clientHeight;
  const size = Math.min(w, h);
  const R = size / 2 - 1;
  return { w, h, cx: w / 2, cy: h / 2, R };
}

function strokeFront(ctx, ring, cx, cy, R) {
  const n = ring.length;
  const closed = n > 1 && ring[0][0] === ring[n - 1][0] && ring[0][1] === ring[n - 1][1];
  const count = closed ? n - 1 : n;
  let drawing = false;
  for (let i = 0; i < count; i++) {
    const a = sph(ring[i][0], ring[i][1]);
    const nxt = ring[(i + 1) % count];
    const b = sph(nxt[0], nxt[1]);
    if (a.z > 0 && b.z > 0) {
      const [ax, ay] = toScreen(a, cx, cy, R);
      const [bx, by] = toScreen(b, cx, cy, R);
      if (!drawing) {
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        drawing = true;
      }
      ctx.lineTo(bx, by);
    } else if (a.z > 0 && b.z <= 0) {
      const p = lerpZ(a, b);
      const [ax, ay] = toScreen(a, cx, cy, R);
      const [px, py] = toScreen(p, cx, cy, R);
      if (!drawing) {
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        drawing = true;
      }
      ctx.lineTo(px, py);
      ctx.stroke();
      drawing = false;
    } else if (a.z <= 0 && b.z > 0) {
      const p = lerpZ(a, b);
      const [px, py] = toScreen(p, cx, cy, R);
      ctx.beginPath();
      ctx.moveTo(px, py);
      drawing = true;
    }
  }
  if (drawing) ctx.stroke();
}

function strokeGraticule(ctx, cx, cy, R) {
  const step = 2;
  ctx.beginPath();
  for (let lng = -180; lng < 180; lng += 30) {
    let drawing = false;
    for (let lat = -90; lat <= 90; lat += step) {
      const p = sph(lng, lat);
      if (p.z <= 0) {
        drawing = false;
        continue;
      }
      const [x, y] = toScreen(p, cx, cy, R);
      if (!drawing) {
        ctx.moveTo(x, y);
        drawing = true;
      } else ctx.lineTo(x, y);
    }
  }
  for (let lat = -60; lat <= 60; lat += 30) {
    let drawing = false;
    for (let lng = -180; lng <= 180; lng += step) {
      const p = sph(lng, lat);
      if (p.z <= 0) {
        drawing = false;
        continue;
      }
      const [x, y] = toScreen(p, cx, cy, R);
      if (!drawing) {
        ctx.moveTo(x, y);
        drawing = true;
      } else ctx.lineTo(x, y);
    }
  }
  ctx.stroke();
}

function drawMap() {
  const canvas = $("fig2");
  if (!canvas) return;
  const wrap = canvas.parentElement;
  const geom = measure(wrap);
  const { w, h, cx, cy, R } = geom;
  state.geom = geom;
  const dpr = window.devicePixelRatio || 1;
  const bw = Math.floor(w * dpr);
  const bh = Math.floor(h * dpr);
  if (canvas.width !== bw || canvas.height !== bh) {
    canvas.width = bw;
    canvas.height = bh;
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
  }
  const ctx = canvas.getContext("2d");
  const color = ink();
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = color.sea;
  ctx.fillRect(0, 0, w, h);

  ctx.beginPath();
  ctx.arc(cx, cy, R, 0, Math.PI * 2);
  ctx.fillStyle = color.sea;
  ctx.fill();

  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, R, 0, Math.PI * 2);
  ctx.clip();

  ctx.fillStyle = color.land;
  for (const poly of state.land) {
    const outer = clipFront(poly.outer);
    if (outer.length < 3) continue;
    ctx.beginPath();
    outer.forEach((p, i) => {
      const [x, y] = toScreen(p, cx, cy, R);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.closePath();
    for (const hole of poly.holes) {
      const hp = clipFront(hole);
      if (hp.length < 3) continue;
      hp.forEach((p, i) => {
        const [x, y] = toScreen(p, cx, cy, R);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.closePath();
    }
    ctx.fill("evenodd");
  }

  ctx.strokeStyle = color.rule;
  ctx.lineWidth = 1;
  ctx.globalAlpha = 0.55;
  strokeGraticule(ctx, cx, cy, R);
  ctx.globalAlpha = 1;
  for (const poly of state.land) {
    strokeFront(ctx, poly.outer, cx, cy, R);
    for (const hole of poly.holes) strokeFront(ctx, hole, cx, cy, R);
  }

  ctx.fillStyle = color.mark;
  for (const item of state.items) {
    if (item.lat == null || item.lng == null) continue;
    const p = sph(item.lng, item.lat);
    if (p.z <= 0) continue;
    const [x, y] = toScreen(p, cx, cy, R);
    ctx.fillRect(x - 1.5, y - 1.5, 3, 3);
  }
  ctx.restore();

  ctx.beginPath();
  ctx.arc(cx, cy, R, 0, Math.PI * 2);
  ctx.strokeStyle = color.rule;
  ctx.lineWidth = 1;
  ctx.stroke();
}

function setGeo(geo) {
  state.geo = geo;
  document.querySelectorAll("[data-geo]").forEach((b) => {
    b.classList.toggle("on", b.getAttribute("data-geo") === geo);
  });
  renderBook();
}

function bind() {
  const finder = $("finder");
  const input = $("q");
  if (finder && input) {
    finder.addEventListener("submit", (e) => {
      e.preventDefault();
      state.q = input.value;
      renderBook();
    });
    input.addEventListener("input", (e) => {
      state.q = e.target.value;
      renderBook();
    });
  }
  const heads = $("book-sort");
  if (heads) {
    heads.addEventListener("click", (e) => {
      const th = e.target.closest("th[data-sort]");
      if (!th) return;
      const next = clickSort(state, th.getAttribute("data-sort"), SORT_DEFAULTS);
      state.sort = next.sort;
      state.dir = next.dir;
      renderBook();
    });
  }
  $("book").addEventListener("click", (e) => {
    const btn = e.target.closest(".depth");
    if (!btn) return;
    const id = btn.getAttribute("data-id");
    state.depth.set(id, state.depth.get(id) === "elaborate" ? "eli5" : "elaborate");
    renderBook();
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ block: "nearest" });
  });
  document.querySelectorAll("[data-geo]").forEach((btn) => {
    btn.addEventListener("click", () => setGeo(btn.getAttribute("data-geo")));
  });
  document.querySelectorAll("[data-kind]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.kind = btn.getAttribute("data-kind");
      document.querySelectorAll("[data-kind]").forEach((b) => b.classList.toggle("on", b === btn));
      renderBook();
    });
  });
  document.querySelectorAll("[data-ind]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.industry = btn.getAttribute("data-ind");
      document.querySelectorAll("[data-ind]").forEach((b) => b.classList.toggle("on", b === btn));
      renderBook();
    });
  });

  const canvas = $("fig2");
  canvas.addEventListener("pointerdown", (e) => {
    canvas.setPointerCapture(e.pointerId);
    state.drag = { x: e.clientX, rot: state.rot, moved: false };
  });
  canvas.addEventListener("pointermove", (e) => {
    if (!state.drag) return;
    const dx = e.clientX - state.drag.x;
    if (Math.abs(dx) > 3) state.drag.moved = true;
    const R = (state.geom && state.geom.R) || canvas.clientWidth / 2;
    state.rot = state.drag.rot - dx / R;
    drawMap();
  });
  canvas.addEventListener("pointerup", (e) => {
    const drag = state.drag;
    state.drag = null;
    state.resumeAt = 0;
    if (!drag || drag.moved) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const geom = state.geom || measure(canvas.parentElement);
    let hit = null;
    let best = 10;
    for (const item of state.items) {
      if (item.lat == null) continue;
      const p = sph(item.lng, item.lat);
      if (p.z <= 0) continue;
      const [px, py] = toScreen(p, geom.cx, geom.cy, geom.R);
      const d = Math.hypot(px - x, py - y);
      if (d < best) {
        best = d;
        hit = item;
      }
    }
    if (hit && best <= 8) {
      location.hash = hit.id;
      const el = document.getElementById(hit.id);
      if (el) el.scrollIntoView({ block: "start" });
      return;
    }
    const ll = invertScreen(x, y, geom);
    if (!ll) return;
    setGeo(regionAt(ll.lng, ll.lat));
  });
  canvas.addEventListener("pointercancel", () => {
    state.drag = null;
    state.resumeAt = 0;
  });
  window.addEventListener("resize", drawMap);
  window.addEventListener("hashchange", () => {
    const id = location.hash.replace("#", "");
    if (id && document.getElementById(id)) document.getElementById(id).scrollIntoView({ block: "start" });
  });
}

async function load() {
  bind();
  const landP = fetch(dataUrl("./data/ne-110m-land.json"), { cache: "no-store" })
    .then((r) => {
      if (!r.ok) throw new Error("land");
      return r.json();
    })
    .then((fc) => {
      state.land = parseLand(fc);
    })
    .catch(() => {
      state.land = [];
    });
  try {
    const [gaz, reg, icons] = await Promise.all([
      fetch(dataUrl("./data/attestations.json"), { cache: "no-store" }).then((r) => r.json()),
      fetch(dataUrl("./data.json"), { cache: "no-store" }).then((r) => r.json()),
      fetch(dataUrl("./favicons/index.json"), { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : { companies: {}, marks: {} }))
        .catch(() => ({ companies: {}, marks: {} })),
      landP,
    ]);
    state.icons = icons && typeof icons === "object" ? icons : { companies: {}, marks: {} };
    state.companies = reg.companies || [];
    state.items = (gaz.attestations || []).map((item) => ({
      ...item,
      files: citeCount(state.companies, item),
    }));
    fillIssue($("issue"), reg, `${state.items.length} marks`);
    const params = new URLSearchParams(window.location.search);
    if (params.get("q")) {
      state.q = params.get("q");
      const input = $("q");
      if (input) input.value = state.q;
    }
  } catch {
    state.items = [];
    await landP;
  }
  renderBook();
  drawMap();
  if (location.hash) {
    const el = document.getElementById(location.hash.slice(1));
    if (el) el.scrollIntoView({ block: "start" });
  }
}

if (typeof window !== "undefined") {
  load();
}
