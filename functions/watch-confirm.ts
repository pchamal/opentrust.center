// watch-confirm — GET ?token=… activates the watcher and starts the cadence clock.
const BASE = Deno.env.get("INSFORGE_URL") ?? "https://hm3jx7vv.us-east.insforge.app";
const KEY = Deno.env.get("INSFORGE_API_KEY") ?? "";
const SITE = "https://opentrust.center";

function nextDue(cadence: string, from = new Date()): string {
  const d = new Date(from);
  // Print window 09:00 America/Los_Angeles == 16:00Z (PDT) / 17:00Z (PST).
  const H = 16;
  d.setUTCHours(H, 0, 0, 0);
  if (cadence === "daily") { if (d <= from) d.setUTCDate(d.getUTCDate() + 1); }
  else if (cadence === "weekly") {
    do { d.setUTCDate(d.getUTCDate() + 1); } while (d.getUTCDay() !== 1);
    if (d <= from) d.setUTCDate(d.getUTCDate() + 7);
  } else if (cadence === "monthly") {
    do { d.setUTCMonth(d.getUTCMonth() + 1); d.setUTCDate(1); } while (d <= from);
  } else if (cadence === "quarterly") {
    do { d.setUTCMonth(d.getUTCMonth() + 3); d.setUTCDate(1); } while (d <= from);
  } else {
    do { d.setUTCFullYear(d.getUTCFullYear() + 1); d.setUTCMonth(0, 1); } while (d <= from);
  }
  return d.toISOString();
}

async function db(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${BASE}/api/database${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json", ...(init.headers || {}) },
  });
}

export default async function (request: Request): Promise<Response> {
  const token = new URL(request.url).searchParams.get("token") || "";
  const r = await db(`/records/ot_watchers?verifyToken=eq.${encodeURIComponent(token)}&select=email,status,cadence`);
  const rows = r.ok ? await r.json() : [];
  const w = rows[0];
  const hop = (flag: string) => {
    const url = SITE + "/watch.html?confirmed=" + flag;
    return new Response(
      `<!doctype html><meta charset=utf-8><meta http-equiv=refresh content="0;url=` + url + `">` +
      `<p>Returning to your notice list… <a href="` + url + `">continue</a></p>`,
      { headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } });
  };
  if (!w || w.status === "unsubscribed") {
    return hop("0");
  }
  await db(`/records/ot_watchers?email=eq.${encodeURIComponent(w.email)}`, {
    method: "PATCH",
    body: JSON.stringify({
      status: "active", verifiedAt: new Date().toISOString(),
      nextDueAt: nextDue(w.cadence), attempts: 0,
    }),
  });
  return hop("1");
}
