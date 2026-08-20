import { $, attachGate } from "./lib.js";
import { bindClerkTables } from "./sort.js";

attachGate({
  box: $("gate-box"),
  status: $("gate-status"),
});

bindClerkTables(document);
