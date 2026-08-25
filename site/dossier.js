import { attachGate } from "./lib.js";
import { bindClerkTables } from "./sort.js";
import { toggle, has, count, CAP } from "./watch.js";

attachGate();

bindClerkTables(document);

/* Cite this file — a receipt assembled only from facts already printed here. */
function initCite() {
  const ident = document.querySelector(".ident");
  const main = document.getElementById("main");
  if (!ident || !main || document.querySelector(".cite-file")) return;
  const nameEl = ident.querySelector("h1");
  const name = nameEl ? nameEl.textContent.trim() : "";
  if (!name) return;
  const meta = ident.querySelector(".ident-meta");
  const domain = meta ? meta.textContent.trim().toLowerCase() : "";
  const canonLink = document.querySelector('link[rel="canonical"]');
  const url = canonLink ? canonLink.href : window.location.href;
  const issueEl = document.getElementById("issue");
  const issueLine = issueEl ? issueEl.textContent.trim() : "";
  const lines = ["opentrust.center · " + name + (domain && domain.includes(".") ? " · " + domain : "")];
  if (issueLine) lines.push(issueLine);
  lines.push(url);
  const pre = document.createElement("pre");
  pre.textContent = lines.join("\n");

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "cite-copy";
  btn.textContent = "copy citation";

  const box = document.createElement("section");
  box.className = "cite-file";
  box.setAttribute("aria-label", "Cite this file");
  box.appendChild(pre);
  box.appendChild(btn);

  const actions = main.querySelector(".actions");
  const colo = document.querySelector("footer.colo");
  if (actions) actions.insertAdjacentElement("afterend", box);
  else if (colo) colo.parentNode.insertBefore(box, colo);
  else main.appendChild(box);

  btn.addEventListener("click", () => {
    if (!navigator.clipboard) return;
    navigator.clipboard.writeText(lines.join("\n")).then(() => {
      const prev = btn.textContent;
      btn.textContent = "copied";
      setTimeout(() => { btn.textContent = prev; }, 1600);
    });
  });
}

/* Track this company — the notice list ghost in the actions line. */
function mountTrack() {
  const main = document.getElementById("main");
  if (!main || main.querySelector(".watch-toggle")) return;
  const canon = document.querySelector('link[rel="canonical"]');
  const m = canon ? canon.href.match(/\/c\/([^/]+)\.html/) : null;
  const slug = m ? decodeURIComponent(m[1]) : "";
  const nameEl = document.querySelector(".ident h1");
  const metaEl = document.querySelector(".ident .ident-meta");
  const name = nameEl ? nameEl.textContent.trim() : "";
  const domain = metaEl ? metaEl.textContent.trim().toLowerCase() : "";
  if (!slug || !domain.includes(".")) return;

  const anchor = main.querySelector(".actions") || main;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "go-out watch-toggle";
  anchor.appendChild(btn);

  function paint() {
    const tracked = has(slug);
    const full = count() >= CAP && !tracked;
    btn.disabled = full;
    btn.textContent = tracked
      ? "Stop tracking"
      : full ? "10 of 10 files — remove one to add" : "Track this company";
  }
  btn.addEventListener("click", () => {
    if (btn.disabled) return;
    toggle({ slug, domain, name });
    paint();
  });
  paint();
}

function boot() {
  initCite();
  mountTrack();
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
else boot();
