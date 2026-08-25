// watch-subscribe — double opt-in entry point. Always answers 202.
// Body: { email, cadence, slugs: [{ slug, domain }] }
const BASE = Deno.env.get("INSFORGE_URL") ?? "https://hm3jx7vv.us-east.insforge.app";
const KEY = Deno.env.get("INSFORGE_API_KEY") ?? "";
const SITE = "https://opentrust.center";
const CADENCES = new Set(["daily", "weekly", "monthly", "quarterly", "yearly"]);
const CAP = 10;

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type",
  "Content-Type": "application/json",
};

function ok202() {
  return new Response(JSON.stringify({ ok: true }), { status: 202, headers: cors });
}
function bad(msg: string, code = 400) {
  return new Response(JSON.stringify({ ok: false, error: msg }), { status: code, headers: cors });
}

function token(): string {
  const b = new Uint8Array(24);
  crypto.getRandomValues(b);
  return btoa(String.fromCharCode(...b)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function db(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${BASE}/api/database${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json", ...(init.headers || {}) },
  });
}

export default async function (request: Request): Promise<Response> {
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
  if (request.method !== "POST") return bad("POST only", 405);

  let body: any;
  try { body = await request.json(); } catch { return bad("invalid json"); }

  const email = String(body?.email || "").trim().toLowerCase();
  if (!/^[^\s@]{1,64}@[^\s@]{1,255}\.[^\s@]{2,}$/.test(email)) return bad("invalid email");
  const cadence = CADENCES.has(body?.cadence) ? body.cadence : "weekly";
  const slugs = Array.isArray(body?.slugs) ? body.slugs.slice(0, CAP) : [];
  if (!slugs.length) return bad("no files selected");
  for (const s of slugs) {
    if (typeof s?.slug !== "string" || typeof s?.domain !== "string" || s.slug.length > 80 || s.domain.length > 100) {
      return bad("invalid file entry");
    }
  }
  if (Array.isArray(body?.slugs) && body.slugs.length > CAP) return bad("cap");

  const ipHash = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(`otsalt|${request.headers.get("cf-connecting-ip") || ""}`),
  ).then((b) => Array.from(new Uint8Array(b)).map((x) => x.toString(16).padStart(2, "0")).join(""));

  const existing = await db(`/records/ot_watchers?email=eq.${encodeURIComponent(email)}&select=email,status,attempts`);
  const found = existing.ok ? await existing.json() : [];
  const prev = found[0];
  if (prev && (prev.attempts ?? 0) > 12) return bad("slow down", 429);

  const vt = token(), ut = token();
  const row = {
    email, cadence, status: "unverified",
    verifyToken: vt, unsubToken: ut,
    ipHash, attempts: (prev?.attempts ?? 0) + 1,
    createdAt: new Date().toISOString(),
  };
  const wres = prev
    ? await db(`/records/ot_watchers?email=eq.${encodeURIComponent(email)}`, { method: "PATCH", body: JSON.stringify(row) })
    : await db("/records/ot_watchers", { method: "POST", body: JSON.stringify([row]) });
  if (!wres.ok) return bad("storage failed", 500);

  await db(`/records/ot_watch_files?watcherEmail=eq.${encodeURIComponent(email)}`, { method: "DELETE" });
  const files = slugs.map((s, i) => ({
    watcherEmail: email, slug: s.slug, domain: s.domain,
    slot: i + 1, addedAt: new Date().toISOString(),
  }));
  await db("/records/ot_watch_files", { method: "POST", body: JSON.stringify(files) });

  const list = files.map((f, i) => `  ${i + 1}. ${f.domain}`).join("\n");
  const html = `<pre style="font:14px/1.7 monospace">You asked opentrust.center to watch companies for you.

On your notice list:
${list}

Cadence: ${cadence}. Nothing prints until you confirm.

Confirm: ${SITE}/functions/watch-confirm?token=${vt}
Not you? Ignore this note. The request expires in 30 days.</pre>`;
  await fetch(`${BASE}/api/email/send-raw`, {
    method: "POST",
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      to: email,
      subject: "Confirm your notice list · opentrust.center",
      html,
    }),
  });

  return ok202();
}
