/* Click-to-sort for clerk tables. Same header-button pattern as the register. */

export const TIER_ORDER = {
  silent: 0,
  thin: 1,
  "on-file": 2,
  substantial: 3,
  complete: 4,
};

export const IMPACT_ORDER = {
  "li-saas": 1,
  low: 2,
  "20x low": 3,
  moderate: 4,
  "20x moderate": 5,
  high: 6,
};

const MONTHS = {
  jan: 0,
  feb: 1,
  mar: 2,
  apr: 3,
  may: 4,
  jun: 5,
  jul: 6,
  aug: 7,
  sep: 8,
  oct: 9,
  nov: 10,
  dec: 11,
};

const HEADER_KEYS = {
  processor: "processor",
  processors: "processor",
  name: "name",
  exposure: "exposure",
  "public file": "file",
  file: "file",
  concentration: "risk",
  source: "source",
  instrument: "instrument",
  host: "host",
  "last seen": "seen",
  seen: "seen",
  offering: "offering",
  status: "status",
  "impact level": "impact",
  impact: "impact",
  "auth date": "date",
  date: "date",
  kind: "kind",
  geography: "geography",
  issuer: "issuer",
  weight: "weight",
  files: "files",
  count: "files",
  industry: "industry",
  "#": "rank",
  domain: "domain",
  marks: "marks",
};

export function headerKey(label) {
  const v = String(label || "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
  return HEADER_KEYS[v] || "";
}

export function clickSort(current, key, defaults = {}) {
  const sort = String(key || "").trim();
  if (!sort) return { sort: current.sort, dir: current.dir };
  if (current.sort === sort) {
    return { sort, dir: current.dir === "asc" ? "desc" : "asc" };
  }
  const fallback = defaults[sort] || "asc";
  return { sort, dir: fallback };
}

export function paintHeaders(root, sort, dir) {
  if (!root) return;
  root.querySelectorAll("th[data-sort]").forEach((th) => {
    const live = th.getAttribute("data-sort") === sort;
    th.classList.toggle("on", live);
    th.setAttribute("aria-sort", live ? (dir === "desc" ? "descending" : "ascending") : "none");
  });
}

export function cmpText(a, b) {
  return String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base" });
}

export function cmpNum(a, b) {
  const an = Number(a);
  const bn = Number(b);
  const av = Number.isFinite(an) ? an : 0;
  const bv = Number.isFinite(bn) ? bn : 0;
  return av - bv;
}

export function parseClerkDate(value) {
  const s = String(value || "").replace(/\s+/g, " ").trim();
  if (!s || s === "—" || /^not on file$/i.test(s)) return null;
  const m = s.match(/^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})$/);
  if (!m) {
    const t = Date.parse(s);
    return Number.isFinite(t) ? t : null;
  }
  const month = MONTHS[m[2].toLowerCase()];
  if (month == null) return null;
  return Date.UTC(Number(m[3]), month, Number(m[1]));
}

export function clerkDateValue(value) {
  const t = parseClerkDate(value);
  return t == null ? 0 : t;
}

export function impactValue(value) {
  const s = String(value || "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
  if (!s || s === "—" || s === "not on file") return 0;
  if (IMPACT_ORDER[s] != null) return IMPACT_ORDER[s];
  return 0;
}

export function arrange(rows, key, dir, compare, nameOf = (row) => row && row.name) {
  const sign = dir === "desc" ? -1 : 1;
  return rows.slice().sort((a, b) => {
    const c = compare(a, b, key);
    if (c) return c * sign;
    return cmpText(nameOf(a), nameOf(b));
  });
}

export function cellText(td) {
  if (!td) return "";
  return String(td.textContent || "").replace(/\s+/g, " ").trim();
}

export function isPlaceholderRow(tr) {
  if (!tr || !tr.cells || !tr.cells.length) return true;
  if (tr.cells[0].colSpan > 1) return true;
  const text = cellText(tr.cells[0]);
  if (tr.cells.length === 1 && /^not on file$/i.test(text)) return true;
  return false;
}

export function compareCellText(key, a, b) {
  const left = String(a || "");
  const right = String(b || "");
  switch (key) {
    case "exposure":
    case "risk":
    case "weight":
    case "rank":
      return cmpNum(left, right);
    case "seen":
    case "date":
      return clerkDateValue(left) - clerkDateValue(right);
    case "impact":
      return impactValue(left) - impactValue(right);
    case "file":
    case "tier": {
      const order = TIER_ORDER;
      const av = order[left] != null ? order[left] : left === "on file" ? 2 : -1;
      const bv = order[right] != null ? order[right] : right === "on file" ? 2 : -1;
      return av - bv;
    }
    default:
      return cmpText(left, right);
  }
}

export function enhanceSortHeaders(table) {
  if (!table) return;
  table.querySelectorAll("thead th").forEach((th) => {
    if (!th.getAttribute("data-sort")) {
      const key = headerKey(th.textContent);
      if (key) th.setAttribute("data-sort", key);
    }
    if (!th.getAttribute("data-sort")) return;
    if (!th.querySelector("button")) {
      const label = th.textContent.replace(/\s+/g, " ").trim();
      th.textContent = "";
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = label;
      th.appendChild(btn);
    }
    if (!th.hasAttribute("aria-sort")) th.setAttribute("aria-sort", "none");
  });
}

function prevKicker(table) {
  let el = table && table.previousElementSibling;
  while (el) {
    if (el.classList && el.classList.contains("sec-kicker")) return el.textContent.trim();
    el = el.previousElementSibling;
  }
  return "";
}

export function tableKind(table) {
  const attr = table && table.getAttribute("data-table");
  if (attr) return attr;
  const kicker = prevKicker(table);
  if (/^named processors$/i.test(kicker)) return "processors";
  if (/^fedramp$/i.test(kicker)) return "fedramp";
  if (/^instruments$/i.test(kicker)) return "instruments";
  const heads = [...((table && table.querySelectorAll("thead th")) || [])].map((th) =>
    String(th.textContent || "")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase()
  );
  if (heads[0] === "processor") return "processors";
  if (heads[0] === "offering") return "fedramp";
  if (heads[0] === "instrument") return "instruments";
  return "table";
}

function columnIndex(table, key) {
  const heads = [...table.querySelectorAll("thead th")];
  const i = heads.findIndex((th) => th.getAttribute("data-sort") === key);
  return i < 0 ? 0 : i;
}

export function sortTableBody(table, key, dir) {
  const tbody = table && table.tBodies && table.tBodies[0];
  if (!tbody) return;
  const rows = [...tbody.rows];
  const live = [];
  const held = [];
  for (const tr of rows) {
    if (isPlaceholderRow(tr)) held.push(tr);
    else live.push(tr);
  }
  const col = columnIndex(table, key);
  const sign = dir === "desc" ? -1 : 1;
  live.sort((a, b) => {
    const c = compareCellText(key, cellText(a.cells[col]), cellText(b.cells[col]));
    if (c) return c * sign;
    return cmpText(cellText(a.cells[0]), cellText(b.cells[0]));
  });
  live.concat(held).forEach((tr) => tbody.appendChild(tr));
}

export function bindClerkTable(table, options = {}) {
  if (!table || !table.tHead) return null;
  enhanceSortHeaders(table);
  const kind = options.kind || tableKind(table);
  const defaults = options.defaults || { processor: "asc", name: "asc", exposure: "desc", risk: "desc" };
  const defaultKey =
    options.defaultKey != null ? options.defaultKey : kind === "processors" ? "processor" : "";
  const state = {
    sort: defaultKey,
    dir: defaultKey ? defaults[defaultKey] || "asc" : "asc",
  };
  const apply = () => {
    if (state.sort) sortTableBody(table, state.sort, state.dir);
    paintHeaders(table, state.sort, state.dir);
    if (options.onSort) options.onSort(state);
  };
  table.tHead.addEventListener("click", (e) => {
    const th = e.target.closest("th[data-sort]");
    if (!th) return;
    const next = clickSort(state, th.getAttribute("data-sort"), defaults);
    state.sort = next.sort;
    state.dir = next.dir;
    apply();
  });
  if (state.sort) apply();
  else paintHeaders(table, "", "asc");
  return state;
}

export function bindClerkTables(root = typeof document !== "undefined" ? document : null) {
  if (!root) return [];
  return [...root.querySelectorAll("table.inst, table.reg")].map((table) => {
    if (table.id === "reg") return null;
    if (!table.tHead || !table.tHead.querySelector("th")) return null;
    return bindClerkTable(table);
  });
}
