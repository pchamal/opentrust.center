/* Finder tokens for the register. Clerk syntax, not a search product. */

const TIERS = new Set(["silent", "thin", "on-file", "substantial", "complete"]);
const LISTS = new Set(["cloud100", "enterprise"]);
const FEDRAMP = new Set(["all", "any", "low", "moderate", "high"]);

const EXACT = {
  silent: { kind: "tier", value: "silent" },
  thin: { kind: "tier", value: "thin" },
  "on file": { kind: "tier", value: "on-file" },
  "on-file": { kind: "tier", value: "on-file" },
  substantial: { kind: "tier", value: "substantial" },
  complete: { kind: "tier", value: "complete" },
  "cloud 100": { kind: "list", value: "cloud100" },
  cloud100: { kind: "list", value: "cloud100" },
  enterprise: { kind: "list", value: "enterprise" },
  fedramp: { kind: "fedramp", value: "any" },
  any: { kind: "fedramp", value: "any" },
  low: { kind: "fedramp", value: "low" },
  moderate: { kind: "fedramp", value: "moderate" },
  high: { kind: "fedramp", value: "high" },
  "fedramp any": { kind: "fedramp", value: "any" },
  "fedramp low": { kind: "fedramp", value: "low" },
  "fedramp moderate": { kind: "fedramp", value: "moderate" },
  "fedramp high": { kind: "fedramp", value: "high" },
};

/* Peel only unambiguous clerk words from a mixed clause.
   Leave enterprise / any / low / moderate / high to exact clauses
   so a name like Hewlett Packard Enterprise still searches. */
const PEEL = [
  { kind: "tier", value: "on-file", re: /\bon[\s-]+file\b/ },
  { kind: "list", value: "cloud100", re: /\bcloud[\s-]*100\b/ },
  { kind: "fedramp", value: "moderate", re: /\bfedramp\s+moderate\b/ },
  { kind: "fedramp", value: "low", re: /\bfedramp\s+low\b/ },
  { kind: "fedramp", value: "high", re: /\bfedramp\s+high\b/ },
  { kind: "fedramp", value: "any", re: /\bfedramp\s+any\b/ },
  { kind: "tier", value: "silent", re: /\bsilent\b/ },
  { kind: "tier", value: "thin", re: /\bthin\b/ },
  { kind: "tier", value: "substantial", re: /\bsubstantial\b/ },
  { kind: "tier", value: "complete", re: /\bcomplete\b/ },
];

function normClause(s) {
  return String(s || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

function splitFinder(raw) {
  let s = String(raw || "").trim();
  const slash = s.startsWith("/");
  if (slash) s = s.slice(1).trim();
  const clauses = s
    .split(",")
    .map(normClause)
    .filter(Boolean);
  return { slash, clauses };
}

function peelClause(clause, out) {
  let rest = clause;
  let changed = true;
  while (changed && rest) {
    changed = false;
    for (const spec of PEEL) {
      const m = rest.match(spec.re);
      if (!m) continue;
      out[spec.kind] = spec.value;
      rest = (rest.slice(0, m.index) + " " + rest.slice(m.index + m[0].length))
        .replace(/\s+/g, " ")
        .trim();
      changed = true;
      break;
    }
  }
  return rest;
}

export function parseFinder(raw) {
  const { clauses } = splitFinder(raw);
  const out = { q: "", tier: "all", list: "all", fedramp: "all" };
  const text = [];
  for (const clause of clauses) {
    const hit = EXACT[clause];
    if (hit) {
      out[hit.kind] = hit.value;
      continue;
    }
    const rest = peelClause(clause, out);
    if (rest) text.push(rest);
  }
  out.q = text.join(" ");
  return out;
}

export function stripFinderToken(raw, kind) {
  const { slash, clauses } = splitFinder(raw);
  const kept = [];
  for (const clause of clauses) {
    const hit = EXACT[clause];
    if (hit && hit.kind === kind) continue;
    let rest = clause;
    for (const spec of PEEL) {
      if (spec.kind !== kind) continue;
      rest = rest.replace(spec.re, " ").replace(/\s+/g, " ").trim();
    }
    if (rest) kept.push(rest);
  }
  const body = kept.join(", ");
  if (!body) return "";
  return slash ? "/ " + body : body;
}

export function normalizeTier(value) {
  const v = normClause(value).replace(/\s+/g, "-");
  if (v === "onfile") return "on-file";
  return TIERS.has(v) ? v : "all";
}

export function normalizeList(value) {
  const v = normClause(value).replace(/\s+/g, "");
  if (v === "cloud100" || v === "cloud-100") return "cloud100";
  return LISTS.has(v) ? v : "all";
}

export function normalizeFedramp(value) {
  const v = normClause(value);
  if (v === "fedramp") return "any";
  return FEDRAMP.has(v) ? v : "all";
}

export function echoWords(filters) {
  const bits = [];
  if (filters.tier && filters.tier !== "all") {
    bits.push({ kind: "tier", label: "tier " + (filters.tier === "on-file" ? "on file" : filters.tier) });
  }
  if (filters.list && filters.list !== "all") {
    bits.push({ kind: "list", label: "list " + (filters.list === "cloud100" ? "cloud 100" : filters.list) });
  }
  if (filters.fedramp && filters.fedramp !== "all") {
    bits.push({ kind: "fedramp", label: "fedramp " + filters.fedramp });
  }
  return bits;
}
