import { focusIdFromLocation } from "../site/graph.js";

function loc(href) {
  const u = new URL(href, "https://opentrust.center/graph.html");
  return { search: u.search, hash: u.hash };
}

const cases = [
  ["https://opentrust.center/graph.html", ""],
  ["https://opentrust.center/graph.html#p=aws", "aws"],
  ["https://opentrust.center/graph.html?p=workos", "workos"],
  ["https://opentrust.center/graph.html?p=aws#p=ignored", "aws"],
  ["https://opentrust.center/graph.html#p=google-gemini", "google-gemini"],
];

let failed = 0;
for (const [href, want] of cases) {
  const got = focusIdFromLocation(loc(href));
  if (got !== want) {
    failed += 1;
    console.error("focusIdFromLocation", href, "got", got, "want", want);
  }
}

if (failed) process.exit(1);
console.log("ok");
