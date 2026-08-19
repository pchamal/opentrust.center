import { $, escapeHtml, fillIssue } from "./lib.js";

const GEO_GROUPS = {
  americas: ["US", "CA", "BR"],
  europe: ["EU", "DE", "ES", "FR", "CH"],
  uk: ["GB"],
  apac: ["SG", "AU", "JP", "KR", "TH"],
  international: ["global"],
};

const state = {
  items: [],
  companies: [],
  geo: "all",
  industry: "all",
  kind: "all",
  depth: new Map(),
  rot: 0,
  drag: null,
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
  const rows = state.items.filter(matches);
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

function project(lng, lat, w, h) {
  const x = ((lng - state.rot + 540) % 360) - 180;
  return [((x + 180) / 360) * w, ((90 - lat) / 180) * h];
}

function regionAt(lng, lat) {
  if (lng >= -12 && lng <= 3 && lat >= 49 && lat <= 61) return "uk";
  if (lng >= -170 && lng <= -25) return "americas";
  if (lng >= -15 && lng <= 40 && lat >= 34) return "europe";
  if (lng >= 60) return "apac";
  return "international";
}

/* Printed equirectangular land. Simplified continents, clerk ink. */
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

function drawMap() {
  const canvas = $("fig2");
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
  ctx.fillStyle = "#331400";
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = "#993d00";
  ctx.lineWidth = 1;
  ctx.globalAlpha = 0.55;
  for (let lng = -180; lng <= 180; lng += 30) {
    const [x] = project(lng, 0, w, h);
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  for (let lat = -60; lat <= 60; lat += 30) {
    const [, y] = project(0, lat, w, h);
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }
  ctx.globalAlpha = 1;

  ctx.fillStyle = "#662900";
  ctx.strokeStyle = "#993d00";
  for (const ring of LAND) {
    ctx.beginPath();
    ring.forEach(([lng, lat], i) => {
      const [x, y] = project(lng, lat, w, h);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }

  const seen = new Set();
  for (const item of state.items) {
    if (item.lat == null || item.lng == null) continue;
    if (state.geo !== "all" && !matches(item) && state.geo !== "international") {
      /* still plot; filter is on the book */
    }
    const key = `${Math.round(item.lat)}:${Math.round(item.lng)}`;
    const [x, y] = project(item.lng, item.lat, w, h);
    ctx.fillStyle = "#ff6600";
    ctx.fillRect(x - 1.5, y - 1.5, 3, 3);
    seen.add(key);
  }
}

function setGeo(geo) {
  state.geo = geo;
  $("geo-legend").querySelectorAll("button").forEach((b) => {
    b.classList.toggle("on", b.getAttribute("data-geo") === geo);
  });
  const bar = $("geo-filters");
  if (bar) {
    bar.querySelectorAll("button").forEach((b) => {
      b.classList.toggle("on", b.getAttribute("data-geo") === geo);
    });
  }
  renderBook();
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
    state.rot = state.drag.rot - (dx / canvas.clientWidth) * 360;
    drawMap();
  });
  canvas.addEventListener("pointerup", (e) => {
    const drag = state.drag;
    state.drag = null;
    if (!drag || drag.moved) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const w = rect.width;
    const h = rect.height;
    let hit = null;
    let best = 10;
    for (const item of state.items) {
      if (item.lat == null) continue;
      const [px, py] = project(item.lng, item.lat, w, h);
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
    const lng = ((x / w) * 360 - 180 + state.rot + 540) % 360 - 180;
    const lat = 90 - (y / h) * 180;
    setGeo(regionAt(lng, lat));
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
    state.items = gaz.attestations || [];
    state.companies = reg.companies || [];
    fillIssue($("issue"), reg, `${state.items.length} marks`);
  } catch {
    state.items = [];
  }
  renderBook();
  drawMap();
  if (location.hash) {
    const el = document.getElementById(location.hash.slice(1));
    if (el) el.scrollIntoView({ block: "start" });
  }
}

load();
