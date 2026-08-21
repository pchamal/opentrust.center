import { readFileSync } from "node:fs";
import { attachGate, GATE_KEY, markHuman, placeGate } from "../site/lib.js";

function expect(name, cond) {
  if (!cond) {
    console.error("fail", name);
    process.exitCode = 1;
  } else {
    console.log("ok", name);
  }
}

function el(tag, attrs = {}, kids = []) {
  const node = {
    tagName: String(tag).toUpperCase(),
    id: attrs.id || "",
    className: attrs.class || "",
    hidden: !!attrs.hidden,
    href: attrs.href || "",
    type: attrs.type || "",
    checked: false,
    disabled: false,
    textContent: attrs.text || "",
    parentNode: null,
    childNodes: [],
    listeners: {},
    classList: {
      add(...names) {
        const set = new Set(node.className.split(/\s+/).filter(Boolean));
        names.forEach((n) => set.add(n));
        node.className = [...set].join(" ");
      },
      contains(name) {
        return node.className.split(/\s+/).includes(name);
      },
    },
    getAttribute(name) {
      if (name === "href") return node.href;
      if (name === "id") return node.id;
      return attrs[name] ?? null;
    },
    setAttribute(name, value) {
      attrs[name] = value;
    },
    closest(sel) {
      let cur = node;
      while (cur) {
        if (matches(cur, sel)) return cur;
        cur = cur.parentNode;
      }
      return null;
    },
    after(other) {
      if (!node.parentNode) return;
      const parent = node.parentNode;
      if (other.parentNode) {
        other.parentNode.childNodes = other.parentNode.childNodes.filter((c) => c !== other);
        other.parentNode = null;
      }
      const kids = parent.childNodes;
      const i = kids.indexOf(node);
      kids.splice(i + 1, 0, other);
      other.parentNode = parent;
    },
    append(...others) {
      for (const other of others) {
        if (other.parentNode) {
          other.parentNode.childNodes = other.parentNode.childNodes.filter((c) => c !== other);
        }
        other.parentNode = node;
        node.childNodes.push(other);
      }
    },
    querySelector(sel) {
      return walk(node, sel)[0] || null;
    },
    querySelectorAll(sel) {
      return walk(node, sel);
    },
    addEventListener(type, fn) {
      (node.listeners[type] ||= []).push(fn);
    },
  };
  node.append(...kids);
  return node;
}

function matches(node, sel) {
  if (sel.startsWith("#")) return node.id === sel.slice(1);
  if (sel.includes(".")) {
    const [tag, cls] = sel.split(".");
    const tagOk = !tag || node.tagName === tag.toUpperCase();
    return tagOk && node.classList.contains(cls);
  }
  return node.tagName === sel.toUpperCase();
}

function walk(root, sel) {
  const out = [];
  const stack = [...root.childNodes];
  while (stack.length) {
    const n = stack.shift();
    if (matches(n, sel)) out.push(n);
    stack.push(...n.childNodes);
  }
  return out;
}

function click(node) {
  const ev = {
    button: 0,
    metaKey: false,
    ctrlKey: false,
    shiftKey: false,
    altKey: false,
    preventDefault() {
      ev.defaultPrevented = true;
    },
    defaultPrevented: false,
  };
  for (const fn of node.listeners.click || []) fn(ev);
  return ev;
}

function change(node) {
  const ev = { target: node };
  for (const fn of node.listeners.change || []) fn(ev);
}

function store() {
  const data = new Map();
  return {
    getItem(k) {
      return data.has(k) ? data.get(k) : null;
    },
    setItem(k, v) {
      data.set(k, String(v));
    },
    removeItem(k) {
      data.delete(k);
    },
    clear() {
      data.clear();
    },
  };
}

function installDoc(root) {
  const opened = [];
  globalThis.document = {
    getElementById(id) {
      if (root.id === id) return root;
      return walk(root, `#${id}`)[0] || null;
    },
    querySelectorAll(sel) {
      return walk(root, sel);
    },
    querySelector(sel) {
      return walk(root, sel)[0] || null;
    },
    createElement(tag) {
      return el(tag);
    },
  };
  globalThis.window = {
    open(href, target, features) {
      opened.push({ href, target, features });
    },
  };
  globalThis.sessionStorage = store();
  return opened;
}

function dossier() {
  const a = el("a", { class: "official", href: "https://a.example/trust" }, []);
  a.textContent = "A";
  const b = el("a", { class: "official", href: "https://b.example/trust" }, []);
  b.textContent = "B";
  const c = el("a", { class: "official", href: "https://c.example/trust" }, []);
  c.textContent = "C";
  const cellA = el("td", {}, [a]);
  const cellB = el("td", {}, [b]);
  const cellC = el("td", {}, [c]);
  const footer = el("div", { class: "out" }, []);
  const gate = el("div", { class: "gate", id: "gate", hidden: true }, [
    el("input", { type: "checkbox", id: "gate-box" }),
    el("p", { class: "gate-status", id: "gate-status" }),
  ]);
  footer.append(gate);
  const root = el("main", {}, [cellA, cellB, cellC, footer]);
  return { root, a, b, c, cellA, cellB, cellC, footer, gate };
}

const { root, a, b, c, cellA, cellB, footer, gate } = dossier();
const opened = installDoc(root);
attachGate({
  box: gate.querySelector("#gate-box"),
  status: gate.querySelector("#gate-status"),
});

expect("page-level gate stays hidden until a click", gate.hidden === true && gate.parentNode === footer);

const evA = click(a);
expect("official click A prevents default", evA.defaultPrevented === true);
expect("stamp sits after A in the same cell", a.parentNode === cellA && a.parentNode === gate.parentNode && cellA.childNodes[1] === gate);
expect("stamp is revealed next to A", gate.hidden === false && gate.classList.contains("gate-inline"));
expect("footer no longer holds the stamp", footer.childNodes.includes(gate) === false);

click(b);
expect("stamp moved after B", b.parentNode === cellB && cellB.childNodes[1] === gate && gate.hidden === false);
expect("A no longer neighbors the stamp", cellA.childNodes.includes(gate) === false && cellA.childNodes.length === 1);

const box = gate.querySelector("#gate-box");
const status = gate.querySelector("#gate-status");
box.checked = true;
change(box);
await new Promise((r) => setTimeout(r, 300));
expect("stamp prints verified · 30 min", status.textContent === "verified · 30 min");
expect("first open is the pending B url", opened[0] && opened[0].href === "https://b.example/trust" && opened[0].target === "_blank" && opened[0].features === "noopener,noreferrer");

const before = opened.length;
const hiddenBefore = gate.hidden;
click(c);
expect("after stamp the next official click opens", opened.length === before + 1 && opened[1].href === "https://c.example/trust");
expect("after stamp the box is not moved onto C", cellB.childNodes.includes(gate) === true && c.parentNode.childNodes.includes(gate) === false);
expect("after stamp the box is not re-shown on C", hiddenBefore === gate.hidden);

const pages = readFileSync(new URL("../build_pages.py", import.meta.url), "utf8");
const lib = readFileSync(new URL("../site/lib.js", import.meta.url), "utf8");
const dossierJs = readFileSync(new URL("../site/dossier.js", import.meta.url), "utf8");
const aitiJs = readFileSync(new URL("../site/aiti.js", import.meta.url), "utf8");
const registerJs = readFileSync(new URL("../site/register.js", import.meta.url), "utf8");
const indexHtml = readFileSync(new URL("../site/index.html", import.meta.url), "utf8");
const companiesHtml = readFileSync(new URL("../site/companies.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../site/styles.css", import.meta.url), "utf8");

expect("publisher no longer injects the page-level gate", !pages.includes("{gate}"));
expect("clerk words stay I am human", lib.includes("I am human") && pages.includes("I am human"));
expect("dossier is still the only attachGate caller", dossierJs.includes("attachGate()") && !aitiJs.includes("attachGate") && !registerJs.includes("attachGate"));
expect("AITI first screen stays ungated", !indexHtml.includes('src="./dossier.js"') && !indexHtml.includes("gate-box"));
expect("Register first screen stays ungated", !companiesHtml.includes('src="./dossier.js"') && !companiesHtml.includes("gate-box"));
expect("inline stamp drops the footer rule", /\.gate\.gate-inline \{[\s\S]*?border-top:\s*0/.test(css) && /\.gate\.gate-inline \{[\s\S]*?padding:\s*0/.test(css));
expect("FedRAMP block is not restyled by the inline stamp", !/fedramp[^{]*\{[^}]*gate-inline/.test(css));
expect("no 0–100 remake", !/0–100|0-100/.test(indexHtml + aitiJs));
expect("AITI docket stays AITI Register Subprocessors Standards", /<nav class="docket"[^>]*>[\s\S]*?>AITI<\/a>[\s\S]*?>Register<\/a>[\s\S]*?>Subprocessors<\/a>[\s\S]*?>Standards<\/a>/.test(indexHtml));

const loose = el("div", {}, [el("a", { class: "official", href: "https://x.example" }), el("div", { class: "gate", id: "g2", hidden: true })]);
const link = loose.childNodes[0];
const g2 = loose.childNodes[1];
placeGate(g2, link);
expect("placeGate re-parents after the link", loose.childNodes[0] === link && loose.childNodes[1] === g2 && g2.hidden === false && g2.classList.contains("gate-inline"));

const createdRoot = el("main", {}, [
  el("td", {}, [el("a", { class: "official", href: "https://made.example" })]),
]);
const createdOpen = installDoc(createdRoot);
attachGate();
const madeLink = createdRoot.childNodes[0].childNodes[0];
click(madeLink);
const made = globalThis.document.getElementById("gate");
expect("missing page gate is created next to the link", made && made.parentNode === madeLink.parentNode && madeLink.parentNode.childNodes[1] === made && made.hidden === false);
expect("created stamp still says I am human", made.querySelector("#gate-box") && [...made.childNodes].some((n) => n.childNodes.some((c) => c.textContent === "I am human")));
expect("created stamp does not open until checked", createdOpen.length === 0);

markHuman();
expect("session key stays ot_human_v1", globalThis.sessionStorage.getItem(GATE_KEY));

if (!process.exitCode) console.log("ok gate");
