// watch-unsubscribe — GET ?token=… stops all prints. One click, no questions.
const BASE = Deno.env.get("INSFORGE_URL") ?? "https://hm3jx7vv.us-east.insforge.app";
const KEY = Deno.env.get("INSFORGE_API_KEY") ?? "";
const SITE = "https://opentrust.center";

export function htmlHop(kind: string, flag: string): Response {
  const url = SITE + "/watch.html?" + kind + "=" + flag;
  return new Response(
    `<!doctype html><meta charset=utf-8><meta http-equiv=refresh content="0;url=` + url + `">` +
    `<p>Returning to your notice list… <a href="` + url + `">continue</a></p>`,
    { headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } });
}

export default async function (request: Request): Promise<Response> {
  const token = new URL(request.url).searchParams.get("token") || "";
  const r = await fetch(
    `${BASE}/api/database/records/ot_watchers?unsubToken=eq.${encodeURIComponent(token)}&select=email`,
    { headers: { Authorization: `Bearer ${KEY}` } },
  );
  const rows = r.ok ? await r.json() : [];
  if (rows[0]) {
    await fetch(
      `${BASE}/api/database/records/ot_watchers?email=eq.${encodeURIComponent(rows[0].email)}`,
      {
        method: "PATCH",
        headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" },
        body: JSON.stringify({ status: "unsubscribed", nextDueAt: null }),
      },
    );
    return htmlHop("bye", "1");
  }
  return htmlHop("bye", "0");
}
