(function () {
  const VENDOR_LABELS = {
    safebase: "SafeBase",
    vanta: "Vanta",
    conveyor: "Conveyor",
    wolfia: "Wolfia",
    custom: "Custom",
    self_hosted: "Custom",
    drata: "Drata",
    securitypal: "SecurityPal",
    secureframe: "Secureframe",
    sprinto: "Sprinto",
    whistic: "Whistic",
    trustcloud: "TrustCloud",
    unknown: "Unknown",
  };
  const VENDOR_CHIPS = ["safebase", "vanta", "conveyor", "wolfia", "custom"];
  const GATE_KEY = "ot_human_v1";
  const GATE_MS = 30 * 60 * 1000;

  const state = {
    rows: [],
    found: 0,
    total: 0,
    vendors: {},
    q: "",
    status: "all",
    vendor: null,
    generatedAt: null,
    openSlug: null,
    pendingUrl: null,
  };

  const $ = (id) => document.getElementById(id);

  function canonVendor(v) {
    if (v === "self_hosted") return "custom";
    return v || "";
  }
  function vendorLabel(v) {
    return VENDOR_LABELS[v] || v || "Unknown";
  }
  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function fmtTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString("en-US", {
      timeZone: "America/Los_Angeles",
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short",
    });
  }
  function hostOf(url) {
    try {
      return new URL(url).host.replace(/^www\./, "");
    } catch {
      return "";
    }
  }
  function outbound(row) {
    return row.trust_url || row.final_url || "";
  }
  function listLabel(row) {
    const src = row.list || row.source || "";
    if (src === "enterprise" || src === "public-enterprise") return "Enterprise";
    return "Cloud 100";
  }

  function humanOk() {
    try {
      const raw = sessionStorage.getItem(GATE_KEY);
      if (!raw) return false;
      const t = Number(raw);
      return t && Date.now() - t < GATE_MS;
    } catch {
      return false;
    }
  }
  function markHuman() {
    try {
      sessionStorage.setItem(GATE_KEY, String(Date.now()));
    } catch {}
  }

  function applyFilters() {
    const q = state.q.trim().toLowerCase();
    return state.rows.filter((row) => {
      if (state.status === "found" && !row.found) return false;
      if (state.status === "missing" && row.found) return false;
      if (state.vendor && canonVendor(row.vendor) !== state.vendor) return false;
      if (!q) return true;
      const hay = [row.name, row.domain, row.slug, vendorLabel(row.vendor), row.vendor, row.title]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }

  function guessDomain(q) {
    const clean = q.trim().toLowerCase().replace(/[^a-z0-9.\- ]+/g, "");
    if (!clean) return "";
    if (clean.includes(".")) return clean.replace(/\s+/g, "");
    const slug = clean.replace(/\s+/g, "");
    return slug ? slug + ".com" : "";
  }

  function renderHero() {
    const total = state.total || state.rows.length;
    const found = state.found || state.rows.filter((r) => r.found).length;
    $("stat-found").textContent = total ? String(found) : "—";
    $("stat-total").textContent = total ? String(total) : "—";
    $("stat-missing").textContent = total ? String(Math.max(total - found, 0)) : "—";

    const counts = { ...state.vendors };
    if (!Object.keys(counts).length) {
      for (const row of state.rows) {
        if (!row.found) continue;
        const key = canonVendor(row.vendor);
        counts[key] = (counts[key] || 0) + 1;
      }
    } else if (counts.self_hosted && !counts.custom) {
      counts.custom = (counts.custom || 0) + counts.self_hosted;
    }
    const chipKeys = VENDOR_CHIPS.filter((k) => counts[k]);
    $("stat-vendors").textContent = String(chipKeys.length || Object.keys(counts).length || "—");
    $("vendor-tally").innerHTML = chipKeys
      .map((k) => `<strong>${vendorLabel(k)}</strong> ${counts[k]}`)
      .join(" · ");
    for (const btn of $("vendor-filters").querySelectorAll("button")) {
      const key = btn.getAttribute("data-vendor");
      const n = counts[key];
      btn.textContent = n ? `${vendorLabel(key)} ${n}` : vendorLabel(key);
      btn.classList.toggle("on", state.vendor === key);
    }
  }

  function renderCards() {
    const rows = applyFilters();
    const q = state.q.trim();
    const cards = $("cards");
    const empty = $("empty");
    const miss = $("miss");
    $("countline").textContent = state.rows.length
      ? `Showing ${rows.length} of ${state.rows.length}`
      : "";

    if (!state.rows.length) {
      cards.hidden = true;
      miss.hidden = true;
      empty.hidden = false;
      return;
    }
    empty.hidden = true;

    if (q && !rows.length) {
      cards.hidden = true;
      miss.hidden = false;
      const domain = guessDomain(q);
      $("miss-title").textContent = `No public trust center on file for “${q}”.`;
      $("miss-body").textContent = domain
        ? `It is not in this index. If one exists, it often lives on one of these paths — we have not confirmed them.`
        : `It is not in this index. A public portal may still exist under an unusual URL.`;
      const guesses = domain
        ? [
            `https://trust.${domain}`,
            `https://security.${domain}`,
            `https://${domain}/trust`,
            `https://${domain}/trust-center`,
            `https://${domain}/security`,
          ]
        : [];
      $("guesses").innerHTML = guesses
        .map((u) => `<li><code>${escapeHtml(u)}</code></li>`)
        .join("");
      return;
    }

    miss.hidden = true;
    cards.hidden = false;
    cards.innerHTML = rows
      .map((row) => {
        const v = canonVendor(row.vendor);
        const certs = Array.isArray(row.certs) ? row.certs.slice(0, 5) : [];
        const certHtml = certs
          .map((c) => `<span class="cert">${escapeHtml(c)}</span>`)
          .join("");
        const badge = row.found
          ? `<span class="badge ${escapeHtml(v || row.vendor)}">${escapeHtml(vendorLabel(row.vendor))}</span>`
          : `<span class="badge none">Not found</span>`;
        const summary = row.found
          ? escapeHtml(row.summary || row.title || "Public trust center found.")
          : "No public trust center found on the usual paths.";
        return `<article class="card" data-slug="${escapeHtml(row.slug)}">
          <div class="card-top">
            <p class="card-name">${escapeHtml(row.name)}</p>
            ${badge}
          </div>
          <p class="card-domain">${escapeHtml(row.domain || "")} · ${escapeHtml(listLabel(row))}</p>
          <p class="card-sum">${summary}</p>
          <div class="cert-row">${certHtml}</div>
        </article>`;
      })
      .join("");
  }

  function rowBySlug(slug) {
    return state.rows.find((r) => r.slug === slug) || null;
  }

  function openDrawer(slug) {
    const row = rowBySlug(slug);
    if (!row) return;
    state.openSlug = slug;
    const href = outbound(row);
    $("drawer-kicker").textContent = listLabel(row);
    $("drawer-name").textContent = row.name;
    $("drawer-domain").textContent = row.domain || "";
    $("drawer-summary").textContent = row.found
      ? row.summary || row.title || "Public trust center found."
      : "No public trust center found on the usual paths or a “Trust Center” search.";
    const certs = Array.isArray(row.certs) ? row.certs : [];
    $("drawer-certs").innerHTML = certs
      .map((c) => `<span class="cert">${escapeHtml(c)}</span>`)
      .join("");
    $("drawer-meta").textContent = row.found
      ? `${vendorLabel(row.vendor)} portal`
      : "Not in the public index";
    $("drawer-host").textContent = row.found && href ? hostOf(href) : "";
    const openBtn = $("drawer-open");
    openBtn.hidden = !row.found || !href;
    openBtn.dataset.url = href || "";
    $("drawer-permalink").href = `./c/${encodeURIComponent(row.slug)}.html`;
    $("drawer").hidden = false;
    document.body.classList.add("locked");
    const url = new URL(window.location.href);
    url.searchParams.set("c", row.slug);
    history.replaceState(null, "", url);
  }

  function closeDrawer() {
    state.openSlug = null;
    $("drawer").hidden = true;
    document.body.classList.remove("locked");
    const url = new URL(window.location.href);
    url.searchParams.delete("c");
    history.replaceState(null, "", url);
  }

  function requestOutbound(url) {
    if (!url) return;
    if (humanOk()) {
      window.open(url, "_blank", "noopener,noreferrer");
      return;
    }
    state.pendingUrl = url;
    $("gate-box").checked = false;
    $("gate-status").textContent = "";
    $("gate").hidden = false;
  }

  function closeGate() {
    state.pendingUrl = null;
    $("gate").hidden = true;
    $("gate-box").checked = false;
    $("gate-status").textContent = "";
  }

  function render() {
    renderHero();
    renderCards();
    const gen = $("generated");
    if (state.generatedAt) gen.textContent = `Last probed ${fmtTime(state.generatedAt)}`;
  }

  function bind() {
    $("finder").addEventListener("submit", (e) => {
      e.preventDefault();
      state.q = $("q").value;
      renderCards();
    });
    $("q").addEventListener("input", (e) => {
      state.q = e.target.value;
      renderCards();
    });
    $("status-filters").querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.status = btn.getAttribute("data-status");
        $("status-filters").querySelectorAll("button").forEach((b) => {
          b.classList.toggle("on", b === btn);
        });
        render();
      });
    });
    $("vendor-filters").querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.getAttribute("data-vendor");
        state.vendor = state.vendor === key ? null : key;
        if (state.vendor && state.status === "missing") {
          state.status = "found";
          $("status-filters").querySelectorAll("button").forEach((b) => {
            b.classList.toggle("on", b.getAttribute("data-status") === "found");
          });
        }
        render();
      });
    });
    $("cards").addEventListener("click", (e) => {
      const card = e.target.closest(".card");
      if (card) openDrawer(card.getAttribute("data-slug"));
    });
    $("drawer").addEventListener("click", (e) => {
      if (e.target.closest("[data-close]")) closeDrawer();
    });
    $("drawer-open").addEventListener("click", () => {
      requestOutbound($("drawer-open").dataset.url);
    });
    $("gate-cancel").addEventListener("click", closeGate);
    $("gate-box").addEventListener("change", (e) => {
      if (!e.target.checked) return;
      $("gate-status").textContent = "Checking…";
      const start = Date.now();
      setTimeout(() => {
        if (Date.now() - start < 700) return;
        markHuman();
        $("gate-status").textContent = "Verified.";
        const url = state.pendingUrl;
        setTimeout(() => {
          closeGate();
          if (url) window.open(url, "_blank", "noopener,noreferrer");
        }, 280);
      }, 900);
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        if (!$("gate").hidden) closeGate();
        else if (!$("drawer").hidden) closeDrawer();
      }
    });
  }

  async function load() {
    bind();
    const params = new URLSearchParams(window.location.search);
    if (params.get("q")) {
      state.q = params.get("q");
      $("q").value = state.q;
    }
    try {
      const res = await fetch("./data.json", { cache: "no-store" });
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();
      const companies = Array.isArray(data.companies) ? data.companies : [];
      state.rows = companies.slice().sort((a, b) => {
        const ar = a.rank == null ? 9999 : a.rank;
        const br = b.rank == null ? 9999 : b.rank;
        if (ar !== br) return ar - br;
        return String(a.name).localeCompare(String(b.name));
      });
      const computedFound = companies.filter((c) => c.found).length;
      state.found = typeof data.found === "number" ? data.found : computedFound;
      state.total = typeof data.total === "number" ? data.total : companies.length;
      state.vendors = data.vendors && typeof data.vendors === "object" ? data.vendors : {};
      state.generatedAt = data.generated_at || null;
    } catch {
      state.rows = [];
    }
    render();
    const slug = params.get("c");
    if (slug && rowBySlug(slug)) openDrawer(slug);
  }

  load();
})();
