// digest-send — hourly tick. Prints issues for watchers whose nextDueAt is due.
// Cadence cursor: nextDueAt. No-change periods still print a two-line issue.
const BASE = Deno.env.get("INSFORGE_URL") ?? "https://hm3jx7vv.us-east.insforge.app";
const KEY = Deno.env.get("INSFORGE_API_KEY") ?? "";
const SITE = "https://opentrust.center";
const BATCH = 40;

const PERIOD_DAYS: Record<string, number> = {
  daily: 1, weekly: 7, monthly: 30, quarterly: 91, yearly: 365,
};

async function db(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${BASE}/api/database${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json", ...(init.headers || {}) },
  });
}

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export default async function (): Promise<Response> {
  const now = new Date().toISOString();
  const wr = await db(`/records/ot_watchers?status=eq.active&nextDueAt=lte.${now}&select=email,cadence,issueNo,lastSentAt&limit=${BATCH}`);
  const due = wr.ok ? await wr.json() : [];
  let printed = 0;

  for (const w of due) {
    try {
      const since = w.lastSentAt ?? new Date(Date.now() - 8 * 864e5).toISOString();
      const files = await db(`/records/ot_watch_files?watcherEmail=eq.${encodeURIComponent(w.email)}&select=slug,domain&order=slot.asc`);
      const list: { slug: string; domain: string }[] = files.ok ? await files.json() : [];
      const domainsFilter = list.map((f) => `domain.eq."${f.domain}"`).join(",");
      const cr = await db(`/records/ot_changes?observedAt=gt.${since}&or=(${domainsFilter})&select=domain,field,oldValue,newValue,observedAt&order=observedAt.desc`);
      const changes = cr.ok ? await cr.json() : [];

      const fullReprint = w.cadence === "quarterly" || w.cadence === "yearly";
      const issueNo = (w.issueNo ?? 0) + 1;
      const blocks: string[] = [];
      const byDomain: Record<string, any[]> = {};
      for (const c of changes) (byDomain[c.domain] ||= []).push(c);

      for (const f of list) {
        const cs = byDomain[f.domain] || [];
        if (!cs.length && !fullReprint) continue;
        const lines = cs.map((c) => {
          if (c.field === "tier") return `  tier: ${esc(String(c.oldValue))} -> ${esc(String(c.newValue))}`;
          if (c.field.startsWith("instrument_")) return `  instrument ${c.field === "instrument_filed" ? "filed" : "removed"}: ${esc(JSON.stringify(c.newValue?.key || ""))}`;
          if (c.field === "mark_added") return `  marks: ${esc(JSON.stringify(c.newValue?.name || ""))} named`;
          if (c.field === "mark_removed") return `  marks: ${esc(JSON.stringify(c.oldValue?.name || ""))} no longer printed`;
          return "";
        }).filter(Boolean);
        if (!lines.length && fullReprint) lines.push("  unchanged this period");
        blocks.push(
          `${f.domain.toUpperCase()}\n` + lines.join("\n") +
          `\n  ${SITE}/c/${encodeURIComponent(f.slug)}.html`,
        );
      }

      const changedCount = Object.keys(byDomain).length;
      const bodyHtml =
        `<pre style="font:14px/1.7 monospace">opentrust.center — public trust ledger\n` +
        `issue ${issueNo} · ${w.cadence} · observed through ${now.slice(0, 10)}\n` +
        `${changedCount} of ${list.length} files changed\n\n` +
        (blocks.length ? blocks.join("\n\n") : "No changes on file this period.") +
        `\n\n—\nYou track ${list.length} companies. Cadence: ${w.cadence}.\n` +
        `Change cadence or files: ${SITE}/watch.html\n` +
        `Stop all notices: ${SITE}/functions/watch-unsubscribe?token=SENTINEL_UNSUB\nNo account. No password.</pre>`;
      // Unsub link uses the watcher's stored token; fetch it without exposing others'.
      const selfRow = await db(`/records/ot_watchers?email=eq.${encodeURIComponent(w.email)}&select=unsubToken`);
      const sr = selfRow.ok ? (await selfRow.json())[0] : null;
      const finalHtml = sr ? bodyHtml.replace("SENTINEL_UNSUB", sr.unsubToken ?? "") : bodyHtml;

      const sent = await fetch(`${BASE}/api/email/send-raw`, {
        method: "POST",
        headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          to: w.email,
          subject: `opentrust.center · issue ${issueNo} · ${changedCount} change${changedCount === 1 ? "" : "s"}`,
          html: finalHtml,
        }),
      });

      if (sent.ok) {
        const nd = new Date(Date.now() + (PERIOD_DAYS[w.cadence] ?? 7) * 864e5);
        await db(`/records/ot_watchers?email=eq.${encodeURIComponent(w.email)}`, {
          method: "PATCH",
          body: JSON.stringify({ lastSentAt: now, nextDueAt: nd.toISOString(), issueNo, attempts: 0 }),
        });
        printed += 1;
      } else {
        const attempts = (w.attempts ?? 0) + 1;
        const backoffMs = attempts >= 3
          ? (PERIOD_DAYS[w.cadence] ?? 7) * 864e5
          : [5, 25, 125][Math.min(attempts - 1, 2)] * 60_000;
        await db(`/records/ot_watchers?email=eq.${encodeURIComponent(w.email)}`, {
          method: "PATCH",
          body: JSON.stringify({ attempts, nextDueAt: new Date(Date.now() + backoffMs).toISOString() }),
        });
      }
    } catch (_) {
      /* idempotent tick: a failed watcher simply stays due */
    }
  }
  return new Response(JSON.stringify({ ok: true, due: due.length, printed }), {
    headers: { "Content-Type": "application/json" },
  });
}
