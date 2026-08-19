import { $, escapeHtml, fillIssue } from "./lib.js";

const GEO_GROUPS = {
  americas: ["US", "CA", "BR"],
  europe: ["EU", "DE", "ES", "FR", "CH"],
  uk: ["GB"],
  apac: ["SG", "AU", "JP", "KR", "TH"],
  international: ["global"],
};

const TILT = (15 * Math.PI) / 180;
const SPIN = 0.1;
const RESUME_MS = 1200;

const state = {
  items: [],
  companies: [],
  geo: "all",
  industry: "all",
  kind: "all",
  depth: new Map(),
  rot: 0,
  drag: null,
  resumeAt: 0,
  lastTs: 0,
  raf: 0,
  geom: null,
};

function geosOf(item) {
  return item.geography || [];
}

function matches(item) {
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
  return state.companies.filter((c) =>
    (c.attestations || []).some((a) => a.id === id) ||
    (c.certs || []).some((name) => {
      const att = (c.attestations || []).find((a) => a.name === name);
      return att && att.id === id;
    })
  );
}

function renderBook() {
  const rows = state.items.filter(matches).slice().sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""), undefined, { sensitivity: "base" }));
  $("book-count").textContent = `showing ${rows.length} of ${state.items.length}`;
  $("book").innerHTML = rows
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
      const citeLine = citers.length
        ? citers
            .slice(0, 8)
            .map((c) => `<a href="./c/${encodeURIComponent(c.slug)}.html">${escapeHtml(c.name)}</a>`)
            .join(" · ") + (citers.length > 8 ? ` +${citers.length - 8}` : "")
        : `<span class="absent">none in this index</span>`;
      const geo = (item.geography || []).join(" · ");
      const ind = (item.industry || []).join(" · ");
      return `<article class="entry" id="${escapeHtml(item.id)}">
        <h2>${escapeHtml(item.name)}</h2>
        <p class="entry-meta">${escapeHtml(item.kind)} · ${escapeHtml(geo)} · ${escapeHtml(item.issuer)} · weight ${item.weight}</p>
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

/* Printed land. Simplified continents, clerk ink. */
const LAND = [
  /* Americas */
  [[-168, 71], [-141, 70], [-130, 55], [-125, 49], [-95, 49], [-66, 51], [-55, 47], [-67, 44], [-74, 40], [-76, 35], [-80, 25], [-97, 26], [-97, 16], [-87, 14], [-83, 9], [-77, 8], [-62, 10], [-35, -5], [-35, -22], [-40, -23], [-48, -28], [-53, -35], [-68, -55], [-76, -52], [-71, -18], [-81, -5], [-80, 8], [-106, 22], [-117, 32], [-124, 40], [-124, 48], [-130, 54], [-153, 59], [-166, 64], [-168, 71]],
  /* Greenland */
  [[-73, 78], [-20, 81], [-12, 70], [-44, 60], [-53, 67], [-68, 76], [-73, 78]],
  /* Europe / Africa */
  [[-10, 36], [-9, 43], [-8, 52], [0, 54], [5, 53], [8, 58], [12, 66], [25, 71], [32, 70], [40, 65], [40, 45], [36, 36], [32, 31], [34, 27], [43, 12], [51, 12], [43, -1], [40, -15], [32, -30], [20, -35], [18, -34], [12, -17], [9, 4], [0, 5], [-10, 6], [-17, 15], [-16, 21], [-10, 29], [-10, 36]],
  /* UK */
  [[-6, 50], [-5, 58], [-1, 58], [1, 52], [1, 51], [-5, 50], [-6, 50]],
  /* Asia */
  [[40, 65], [60, 70], [80, 72], [100, 70], [140, 70], [180, 65], [180, 8], [140, 8], [120, 5], [105, 2], [100, 8], [98, 22], [108, 21], [109, 12], [104, 1], [98, 8], [80, 6], [68, 23], [60, 25], [48, 25], [44, 40], [40, 45], [40, 65]],
  /* Australia */
  [[113, -22], [129, -14], [142, -11], [153, -28], [146, -39], [115, -35], [113, -22]],
  /* NZ */
  [[166, -41], [178, -37], [177, -47], [167, -47], [166, -41]],
];

function preferReduced() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
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

function clipFront(ring) {
  const out = [];
  const n = ring.length;
  const closed = n > 1 && ring[0][0] === ring[n - 1][0] && ring[0][1] === ring[n - 1][1];
  const count = closed ? n - 1 : n;
  for (let i = 0; i < count; i++) {
    const a = sph(ring[i][0], ring[i][1]);
    const nxt = ring[(i + 1) % count];
    const b = sph(nxt[0], nxt[1]);
    if (a.z > 0) out.push(a);
    if ((a.z > 0) !== (b.z > 0)) out.push(lerpZ(a, b));
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
  for (let lng = -180; lng < 180; lng += 15) {
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
  for (let lat = -75; lat <= 75; lat += 15) {
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
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#331400";
  ctx.fillRect(0, 0, w, h);

  ctx.beginPath();
  ctx.arc(cx, cy, R, 0, Math.PI * 2);
  ctx.fillStyle = "#331400";
  ctx.fill();

  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, R, 0, Math.PI * 2);
  ctx.clip();

  ctx.fillStyle = "#4a1e00";
  for (const ring of LAND) {
    const pts = clipFront(ring);
    if (pts.length < 3) continue;
    ctx.beginPath();
    pts.forEach((p, i) => {
      const [x, y] = toScreen(p, cx, cy, R);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.fill();
  }

  ctx.strokeStyle = "#993d00";
  ctx.lineWidth = 1;
  ctx.globalAlpha = 0.55;
  strokeGraticule(ctx, cx, cy, R);
  ctx.globalAlpha = 1;
  for (const ring of LAND) strokeFront(ctx, ring, cx, cy, R);

  ctx.fillStyle = "#ff6600";
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
  ctx.strokeStyle = "#993d00";
  ctx.lineWidth = 1;
  ctx.stroke();
}

function setGeo(geo) {
  state.geo = geo;
  const legend = $("geo-legend");
  if (legend) {
    legend.querySelectorAll("button").forEach((b) => {
      b.classList.toggle("on", b.getAttribute("data-geo") === geo);
    });
  }
  const bar = $("geo-filters");
  if (bar) {
    bar.querySelectorAll("button").forEach((b) => {
      b.classList.toggle("on", b.getAttribute("data-geo") === geo);
    });
  }
  renderBook();
}

function tick(ts) {
  if (!state.drag && !preferReduced() && ts >= state.resumeAt) {
    const dt = state.lastTs ? (ts - state.lastTs) / 1000 : 0;
    if (dt > 0 && dt < 0.25) {
      state.rot += SPIN * dt;
      drawMap();
    }
  }
  state.lastTs = ts;
  state.raf = requestAnimationFrame(tick);
}

function startSpin() {
  if (state.raf) return;
  if (preferReduced()) return;
  state.lastTs = 0;
  state.raf = requestAnimationFrame(tick);
}

function bind() {
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
  $("kind-filters").querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.kind = btn.getAttribute("data-kind");
      $("kind-filters").querySelectorAll("button").forEach((b) => b.classList.toggle("on", b === btn));
      renderBook();
    });
  });
  $("ind-filters").querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.industry = btn.getAttribute("data-ind");
      $("ind-filters").querySelectorAll("button").forEach((b) => b.classList.toggle("on", b === btn));
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
    state.resumeAt = performance.now() + RESUME_MS;
    startSpin();
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
    state.resumeAt = performance.now() + RESUME_MS;
    startSpin();
  });
  window.addEventListener("resize", drawMap);
  window.addEventListener("hashchange", () => {
    const id = location.hash.replace("#", "");
    if (id && document.getElementById(id)) document.getElementById(id).scrollIntoView({ block: "start" });
  });
}

async function load() {
  bind();
  try {
    const [gaz, reg] = await Promise.all([
      fetch("./data/attestations.json", { cache: "no-store" }).then((r) => r.json()),
      fetch("./data.json", { cache: "no-store" }).then((r) => r.json()),
    ]);
    state.items = (gaz.attestations || []).slice().sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""), undefined, { sensitivity: "base" }));
    state.companies = reg.companies || [];
    fillIssue($("issue"), reg, `${state.items.length} marks`);
  } catch {
    state.items = [];
  }
  renderBook();
  drawMap();
  startSpin();
  if (location.hash) {
    const el = document.getElementById(location.hash.slice(1));
    if (el) el.scrollIntoView({ block: "start" });
  }
}

load();
