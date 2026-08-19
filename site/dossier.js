import { $, attachGate, humanOk } from "./lib.js";

const button = $("go-out");
const box = $("gate-box");
const status = $("gate-status");
const gate = $("gate");

if (button) {
  if (humanOk() && gate) gate.hidden = false;
  attachGate({
    button,
    box,
    status,
    url: button.dataset.url || "",
  });
}
