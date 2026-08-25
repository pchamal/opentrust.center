/* Notice list — a local cart that becomes an emailed issue.
   No account. No password. Ten files, free forever. */
const KEY = "ot-notice-list";
export const CAP = 10;

export const CADENCES = ["daily", "weekly", "monthly", "quarterly", "yearly"];
export let cadence = "weekly";

const API_BASE = "https://hm3jx7vv.us-east.insforge.app";
const SUBSCRIBE_URL = API_BASE + "/functions/watch-subscribe";

function load() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || { files: [], email: "", confirmed: false };
  } catch {
    return { files: [], email: "", confirmed: false };
  }
}
function save(state) {
  localStorage.setItem(KEY, JSON.stringify(state));
}

export function list() { return load().files.slice(); }
export function count() { return load().files.length; }
export function has(slug) { return load().files.some((f) => f.slug === slug); }
export function getEmail() { return load().email || ""; }

/* Returns "added", "removed", or "full". */
export function toggle(file) {
  const state = load();
  const i = state.files.findIndex((f) => f.slug === file.slug);
  let verdict;
  if (i >= 0) {
    state.files.splice(i, 1);
    save(state);
    verdict = "removed";
  } else if (state.files.length >= CAP) {
    return "full";
  } else {
    state.files.push({ slug: file.slug, domain: file.domain, name: file.name || "", addedAt: Date.now() });
    save(state);
    verdict = "added";
  }
  document.dispatchEvent(new Event("ot-notice-changed"));
  return verdict;
}

export function remove(slug) {
  const state = load();
  state.files = state.files.filter((f) => f.slug !== slug);
  save(state);
  document.dispatchEvent(new Event("ot-notice-changed"));
}

export function setCadence(c) {
  if (!CADENCES.includes(c)) return;
  cadence = c;
  const state = load();
  state.cadence = c;
  save(state);
}

/* Posts the cart to the subscribe endpoint. Resolves { ok } regardless of
   server verdict — the clerk never confirms an address in-page. */
export async function subscribe(email) {
  const state = load();
  const clean = String(email || "").trim().toLowerCase();
  if (!clean || !state.files.length) return { ok: false };
  state.email = clean;
  save(state);
  try {
    const res = await fetch(SUBSCRIBE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: clean,
        cadence: state.cadence || cadence,
        slugs: state.files.map((f) => ({ slug: f.slug, domain: f.domain })),
      }),
    });
    return { ok: res.status === 202 };
  } catch {
    return { ok: false };
  }
}

/* ---------- watch.html ---------- */
export function mountWatchPage() {
  const root = document.getElementById("watch-root");
  if (!root) return;

  const params = new URLSearchParams(location.search);
  render();

  if (params.get("confirmed") === "1") flash("Confirmed. Your issues will print on schedule.");
  else if (params.get("confirmed") === "0") flash("That request was not found or already expired. File again below.");
  else if (params.get("bye") === "1") flash("All notices stopped. The list itself is deleted.");
  else if (params.get("bye") === "0") flash("That stop link was not found. Nothing changed.");

  function flash(text) {
    const el = document.getElementById("watch-flash");
    if (!el) return;
    el.textContent = text;
    el.hidden = false;
  }

  function render() {
    const state = load();
    const files = state.files;
    document.getElementById("watch-count").textContent =
      `${files.length} of ${CAP} files`;
    document.getElementById("watch-body").hidden = false;

    const emailKnown = state.email ? state.email : "";
    const pending = emailKnown && !state.confirmed;
    document.getElementById("watch-pending").hidden = !pending;
    if (pending) {
      document.getElementById("watch-pending-email").textContent = emailKnown;
    }

    const tbody = document.getElementById("watch-rows");
    const emptyEl = document.getElementById("watch-empty");
    tbody.innerHTML = "";
    emptyEl.hidden = files.length > 0;
    document.getElementById("watch-table").hidden = files.length === 0;

    for (const f of files) {
      const tr = document.createElement("tr");
      tr.className = "folio";
      tr.innerHTML =
        `<td class="name"><a href="./c/${encodeURIComponent(f.slug)}.html">${escapeHtml(f.name || f.domain)}</a></td>` +
        `<td>${escapeHtml(f.domain)}</td>` +
        `<td><span class="absent">as filed</span></td>` +
        `<td class="watch-remove-cell"><button type="button" class="go-out watch-remove" data-slug="${escapeHtml(f.slug)}">Remove</button></td>`;
      tbody.appendChild(tr);
    }

    const full = files.length >= CAP;
    document.getElementById("watch-cap-note").hidden = !full;
    document.querySelectorAll("[data-track]").forEach((btn) => {
      btn.disabled = full && !has(btn.getAttribute("data-track"));
    });

    const form = document.getElementById("watch-form");
    form.hidden = files.length === 0;
    const input = document.getElementById("watch-email");
    if (!input.value) input.value = state.email || "";

    const activeCadence = state.cadence || "weekly";
    document.querySelectorAll("#cadence-strip button").forEach((b) => {
      const on = b.getAttribute("data-cadence") === activeCadence;
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    document.getElementById("cadence-note").textContent =
      `prints ${activeCadence}. nothing prints until the address above is confirmed.`;
  }

  document.getElementById("cadence-strip").addEventListener("click", (e) => {
    const b = e.target.closest("[data-cadence]");
    if (!b) return;
    setCadence(b.getAttribute("data-cadence"));
    render();
  });

  document.getElementById("watch-rows").addEventListener("click", (e) => {
    const b = e.target.closest(".watch-remove");
    if (!b) return;
    remove(b.getAttribute("data-slug"));
    render();
  });

  document.getElementById("watch-resend").addEventListener("click", () => {
    const state = load();
    if (state.email && state.files.length) subscribe(state.email).then(() => {
      flash("Sent again. One note, to " + state.email + ".");
    });
  });

  document.getElementById("watch-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = document.getElementById("watch-email");
    subscribe(input.value).then(({ ok }) => {
      if (ok) {
        const st = load();
        st.confirmed = false;
        save(st);
        flash("Filed. A confirmation note is on its way — nothing prints until you confirm.");
        render();
      } else {
        flash("The filing did not take. Check the address and try again.");
      }
    });
  });
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
