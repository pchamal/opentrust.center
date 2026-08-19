import { $, attachGate } from "./lib.js";

const button = $("go-out");

attachGate({
  button,
  box: $("gate-box"),
  status: $("gate-status"),
  url: (button && button.dataset.url) || "",
});
