"""Stable processor-id → register-slug map.

Catalog ids and slugified legal names that are the same company as an
existing register row. Used when building the subprocessor graph so the
map and dossiers link to the existing file. Do not invent a second row
for AWS / Google / Microsoft / Mailgun / New Relic / Modal / Baseten /
Sierra / Cerebras / ElevenLabs / Oracle / Hetzner.

Portal vendors are never named and are never alias targets.
"""
from __future__ import annotations

from pathlib import Path

# slug on the wire → existing register slug. Only applied when the
# destination is already on the register.
REGISTER_ALIASES: dict[str, str] = {
    "aws": "amazon-web-services",
    "gcp": "google",
    "azure": "microsoft",
    "mailgun-technologies": "mailgun",
    "google-workspace": "google",
    "google-analytics": "google",
    "newrelic": "new-relic",
    "modal-labs": "modal",
    "baseten-labs": "baseten",
    "baseten-labs-inc": "baseten",
    "sierra-technologies": "sierra",
    "cerebras-systems": "cerebras",
    "eleven-labs": "elevenlabs",
    "oracle-america": "oracle",
    # Expand filed hetzner-online. Do not invent a second Hetzner row.
    "hetzner": "hetzner-online",
    "hetzner-finland": "hetzner-online",
    "exa-labs": "exa",
    "recaptcha": "google",
}

# Published header garbage. Not a company. Do not file or alias.
SKIP_PROCESSOR_IDS = {"entity-name"}
SKIP_PROCESSOR_NAMES = {"entity name"}


def register_slugs(register) -> set[str]:
    if register is None:
        return set()
    if isinstance(register, dict):
        return {str(k) for k in register if k}
    if isinstance(register, set):
        return {str(k) for k in register if k}
    out = set()
    for row in register:
        if isinstance(row, dict) and row.get("slug"):
            out.add(str(row["slug"]))
        elif isinstance(row, str) and row:
            out.add(row)
    return out


def active_aliases(register=None) -> dict[str, str]:
    """Alias map restricted to destinations that already have a register row."""
    slugs = register_slugs(register)
    return {src: dest for src, dest in REGISTER_ALIASES.items() if dest in slugs}


def canonical_processor_id(pid: str, register=None) -> str:
    """Return the register slug when this wire id is a known alias."""
    nid = str(pid or "").strip()
    if not nid:
        return nid
    dest = REGISTER_ALIASES.get(nid, nid)
    slugs = register_slugs(register)
    if dest in slugs:
        return dest
    if nid in slugs:
        return nid
    return nid


def skip_processor(nid: str = "", name: str = "") -> bool:
    if str(nid or "").strip().lower() in SKIP_PROCESSOR_IDS:
        return True
    if str(name or "").strip().lower() in SKIP_PROCESSOR_NAMES:
        return True
    return False


def apply_aliases_to_graph(subs: dict, register=None) -> dict:
    """Rewrite edges/nodes onto existing register slugs. Merge duplicate wires."""
    if not isinstance(subs, dict):
        return subs
    slugs = register_slugs(register)
    aliases = active_aliases(slugs)
    nodes = {n["id"]: dict(n) for n in (subs.get("nodes") or []) if n.get("id")}
    by_row = {}
    if isinstance(register, dict):
        by_row = register
    else:
        for row in register or []:
            if isinstance(row, dict) and row.get("slug"):
                by_row[row["slug"]] = row

    new_edges = []
    seen = set()
    for e in subs.get("edges") or []:
        frm = e.get("from") or e.get("company")
        to = e.get("to") or e.get("processor_slug") or e.get("processor")
        src = e.get("source_url")
        if not frm or not to or not src:
            continue
        dest = aliases.get(to, to)
        if skip_processor(dest, e.get("evidence") or ""):
            continue
        key = (frm, dest, src)
        if key in seen:
            continue
        seen.add(key)
        edge = dict(e)
        edge["from"] = frm
        edge["to"] = dest
        new_edges.append(edge)

        if dest not in nodes:
            row = by_row.get(dest) or {}
            if dest in slugs:
                nodes[dest] = {
                    "id": dest,
                    "name": row.get("name") or dest,
                    "domain": row.get("domain") or "",
                    "kind": "company",
                    "in_register": True,
                }
            else:
                old = nodes.get(to) or {}
                nodes[dest] = {
                    "id": dest,
                    "name": old.get("name") or edge.get("evidence") or dest,
                    "domain": old.get("domain") or "",
                    "kind": old.get("kind") or "processor",
                    "in_register": dest in slugs,
                }

    for src, dest in aliases.items():
        if src != dest:
            nodes.pop(src, None)
        row = by_row.get(dest) or {}
        if dest in slugs:
            node = nodes.get(dest) or {
                "id": dest,
                "name": row.get("name") or dest,
                "domain": row.get("domain") or "",
                "kind": "company",
                "in_register": True,
            }
            node["id"] = dest
            node["name"] = row.get("name") or node.get("name") or dest
            if row.get("domain"):
                node["domain"] = row["domain"]
            node["kind"] = "company"
            node["in_register"] = True
            nodes[dest] = node

    for slug, row in by_row.items():
        if slug not in nodes:
            continue
        node = nodes[slug]
        node["in_register"] = True
        node["kind"] = "company"
        if row.get("name"):
            node["name"] = row["name"]
        if row.get("domain"):
            node["domain"] = row["domain"]

    live = {e.get("from") for e in new_edges} | {e.get("to") for e in new_edges}
    if slugs:
        for slug in slugs:
            if slug in nodes:
                continue
            # Keep register companies that already sat on the map; do not
            # dump the whole register onto the wire list.
            pass
    # Drop alias leftovers that no edge names.
    kept = []
    for nid, node in nodes.items():
        if nid in aliases and aliases[nid] != nid:
            continue
        if nid in live or node.get("in_register"):
            kept.append(node)

    subs["nodes"] = kept
    subs["edges"] = new_edges
    subs["aliases"] = aliases
    return subs


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(__import__("json").dumps(obj, indent=2) + "\n", encoding="utf-8")
