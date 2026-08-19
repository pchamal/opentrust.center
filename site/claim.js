import { $ } from "./lib.js";

const REPO = "https://github.com/pchamal/opentrust.center/issues/new";

function fillSlug() {
  const params = new URLSearchParams(window.location.search);
  const slug = (params.get("slug") || "").trim();
  if (!slug) return slug;
  const field = $("slug");
  if (field && !field.value) field.value = slug;
  return slug;
}

async function fillName(slug) {
  const name = $("name");
  if (!slug || !name || name.value) return;
  try {
    const res = await fetch("./data.json", { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json();
    const row = (data.companies || []).find((c) => c.slug === slug);
    if (row && row.name) name.value = row.name;
  } catch {
    /* leave blank */
  }
}

function draftUrl(fields) {
  const q = new URLSearchParams();
  q.set("template", "claim.yml");
  q.set("title", `claim: ${fields.slug}`);
  q.set("labels", "claim");
  q.set("slug", fields.slug);
  q.set("company", fields.name);
  if (fields.email) q.set("email", fields.email);
  if (fields.role) q.set("role", fields.role);
  q.set("edits", fields.edits);
  q.set("sources", fields.sources);
  const body = [
    "This is a public register. Proposed facts must already be on a first-party page.",
    "",
    `Register slug: ${fields.slug}`,
    `Company name: ${fields.name}`,
    fields.email ? `Contact email: ${fields.email}` : null,
    fields.role ? `Who is filing: ${fields.role}` : null,
    "",
    "What should change",
    fields.edits,
    "",
    "First-party source URLs",
    fields.sources,
  ]
    .filter((line) => line !== null)
    .join("\n");
  q.set("body", body);
  return `${REPO}?${q.toString()}`;
}

function bind() {
  const slug = fillSlug();
  fillName(slug);
  const form = $("claim");
  if (!form) return;
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const fields = {
      name: $("name").value.trim(),
      email: $("email").value.trim(),
      role: $("role").value,
      slug: $("slug").value.trim(),
      edits: $("edits").value.trim(),
      sources: $("sources").value.trim(),
    };
    if (!fields.name || !fields.slug || !fields.edits || !fields.sources) return;
    window.location.href = draftUrl(fields);
  });
}

bind();
