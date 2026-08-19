#!/usr/bin/env python3
"""Build attestations.json and attestations-index.md for opentrust.center."""
from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT.parent / "data"

ALLOWED_KIND = {
    "attestation",
    "certification",
    "regulation",
    "framework",
    "code-of-practice",
    "questionnaire",
    "authorization",  # government ATO / Marketplace programs
}

REQUIRED = [
    "id", "name", "short", "family", "kind", "geography", "industry",
    "issuer", "eli5", "elaborate", "lat", "lng", "related", "weight",
]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def words(s: str) -> int:
    return len(s.split())


def main() -> int:
    files = [
        "attestations_soc_iso_pci.py",
        "attestations_health_gov.py",
        "attestations_privacy_csa.py",
        "attestations_national_eu.py",
        "attestations_transfers.py",
    ]
    entries = []
    for f in files:
        mod = load_module(f[:-3], ROOT / f)
        entries.extend(mod.ENTRIES)
    extra_mod = load_module("attestations_expand", ROOT / "attestations_expand.py")
    extra = extra_mod.EXTRA
    for e in entries:
        if e["id"] in extra:
            e["elaborate"] = (e["elaborate"].rstrip() + extra[e["id"]]).strip()

    # Dedup by id, last wins
    by_id = {}
    for e in entries:
        by_id[e["id"]] = e
    entries = list(by_id.values())

    # Fix known self-ref
    e = by_id.get("soc-2-type-i")
    if e:
        e["related"] = ["soc-2-type-ii", "soc-3"]

    ids = {e["id"] for e in entries}
    errors = []
    warns = []

    for e in entries:
        for k in REQUIRED:
            if k not in e:
                errors.append(f"{e.get('id','?')} missing {k}")
        if e.get("kind") not in ALLOWED_KIND:
            errors.append(f"{e['id']} bad kind {e.get('kind')}")
        w = words(e.get("elaborate", ""))
        if w < 180 or w > 280:
            errors.append(f"{e['id']} elaborate {w} words (need 180-280)")
        eli = e.get("eli5", "")
        sents = [x for x in eli.replace("?", ".").split(".") if x.strip()]
        if len(sents) < 2:
            warns.append(f"{e['id']} eli5 looks short ({len(sents)} sentences)")
        if not isinstance(e.get("geography"), list) or not e["geography"]:
            errors.append(f"{e['id']} geography")
        if not isinstance(e.get("industry"), list) or not e["industry"]:
            errors.append(f"{e['id']} industry")
        if not isinstance(e.get("weight"), int) or not (0 <= e["weight"] <= 12):
            errors.append(f"{e['id']} weight {e.get('weight')}")
        if not isinstance(e.get("lat"), (int, float)) or not isinstance(e.get("lng"), (int, float)):
            errors.append(f"{e['id']} lat/lng")
        for r in e.get("related", []):
            if r not in ids:
                errors.append(f"{e['id']} related unknown {r}")
            if r == e["id"]:
                errors.append(f"{e['id']} related self")

    # Sort: name A–Z (the book is a finding aid)
    entries.sort(key=lambda x: x["name"].lower())

    # Canonical objects
    clean = []
    for e in entries:
        o = {
            "id": e["id"],
            "name": e["name"],
            "short": e["short"],
            "family": e["family"],
            "kind": e["kind"],
            "geography": e["geography"],
            "industry": e["industry"],
            "issuer": e["issuer"],
            "eli5": e["eli5"],
            "elaborate": e["elaborate"],
            "lat": float(e["lat"]),
            "lng": float(e["lng"]),
            "related": e["related"],
            "weight": int(e["weight"]),
        }
        if e.get("retired"):
            o["retired"] = True
        if e.get("note"):
            o["note"] = e["note"]
        o["_wordcount"] = words(e["elaborate"])  # stripped later
        clean.append(o)

    if errors:
        print("ERRORS:", file=sys.stderr)
        for x in errors:
            print(" -", x, file=sys.stderr)
        print(f"{len(errors)} errors, {len(entries)} entries", file=sys.stderr)
        return 1

    for w in warns:
        print("warn:", w)

    for o in clean:
        print(f"  {o['id']:28} {o['_wordcount']:3}w  {o['kind']:16} wt={o['weight']}")

    for o in clean:
        del o["_wordcount"]

    doc = {
        "register": "opentrust.center attestations and certifications encyclopedia",
        "publisher": "opentrust.center",
        "updated": "2026-08-19",
        "count": len(clean),
        "disclaimer": (
            "A public finding aid for names a B2B company might hold or claim. "
            "Listing here is not an endorsement and not legal advice. "
            "Regulations are not vendor certifications. "
            "Verify the live certificate, Marketplace listing, or statute; "
            "do not rely on a trust-page badge. "
            "kind 'authorization' is used for government ATO / Marketplace programs "
            "(FedRAMP, GovRAMP, TX-RAMP) in addition to the core kinds."
        ),
        "kinds": sorted(ALLOWED_KIND),
        "attestations": clean,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = OUT_DIR / "attestations.json"
    out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    write_index(clean, OUT_DIR / "attestations-index.md")
    print(f"Wrote {len(clean)} entries -> {out_json}")
    return 0


def write_index(entries, path: Path) -> None:
    geo = Counter()
    geo_entries = Counter()
    ind = Counter()
    kind = Counter()
    fam = Counter()
    retired = [e for e in entries if e.get("retired")]
    for e in entries:
        fam[e["family"]] += 1
        kind[e["kind"]] += 1
        seen_g = set()
        for g in e["geography"]:
            geo[g] += 1
            seen_g.add(g)
        for g in seen_g:
            geo_entries[g] += 1
        for i in e["industry"]:
            ind[i] += 1

    def table(counter, title):
        lines = [f"## {title}", "", "| Key | Entries |", "|---|---|"]
        for k, v in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0].lower())):
            lines.append(f"| {k} | {v} |")
        lines.append("")
        return lines

    lines = [
        "# Attestations register — index",
        "",
        "Public catalog of security, privacy, AI, and industry attestations a B2B company might hold or claim.",
        "Clerk copy. Not a marketplace. Not legal advice.",
        "",
        f"**Entries:** {len(entries)}  ",
        f"**Updated:** 19 August 2026 (PT)  ",
        f"**File:** `data/attestations.json`",
        "",
        "## How to read a row",
        "",
        "- **certification** — a named third party issued a certificate for a scope (ISO body, HITRUST, PCI listing, ENS, HDS).",
        "- **attestation** — an independent report or approved mechanism (SOC, C5, TISAX, DPF, BCR, IRAP assessment).",
        "- **authorization** — a government ATO / Marketplace status (FedRAMP, GovRAMP, TX-RAMP).",
        "- **regulation** — a statute or directive. Nobody 'holds' it.",
        "- **framework** — a control catalog you can map to. Not a cert.",
        "- **code-of-practice** — guidance or a contractual mechanism (ISO 27017/27018, SCCs).",
        "- **questionnaire** — SIG, CAIQ. Homework, not a mark.",
        "- **weight** — how much a *verified* public disclosure should move a score. FedRAMP 12, SOC 2 Type II 10, GDPR 3, Privacy Shield 0.",
        "- **retired** — do not score. Privacy Shield is the only retired row.",
        "",
        "Look up the live artifact. A badge is not the report.",
        "",
    ]
    lines += table(kind, "By kind")
    lines += table(geo, "By geography tag (an entry may have more than one)")
    lines += table(ind, "By industry tag")
    lines += table(fam, "By family")

    lines += [
        "## Families, in clerk order",
        "",
    ]
    for family, n in sorted(fam.items(), key=lambda kv: kv[0].lower()):
        members = [e["id"] for e in entries if e["family"] == family]
        lines.append(f"- **{family}** ({n}): {', '.join(members)}")
    lines += [
        "",
        "## Retired",
        "",
    ]
    if retired:
        for e in retired:
            lines.append(f"- `{e['id']}` — {e['name']}. Invalidated; do not accept as a transfer basis.")
    else:
        lines.append("- None.")
    lines += [
        "",
        "## Deliberately excluded",
        "",
        "See the end of this page in the build notes, and the parent agent's report.",
        "Short list: cookie/consent products; pen-test letters; bug-bounty programs;",
        "SOC 2+HIPAA or SOC 2 Type II AI as invented hybrids; PA-DSS (retired, successor is PCI SSF);",
        "ISO 14001 and other non-security management systems; employee training badges;",
        "vendor GRC-platform seals (Vanta/Drata 'monitored').",
        "",
        "## Source posture",
        "",
        "Issuers, program names, and legal citations are those a GRC analyst would recognize.",
        "Where a 2026 program is in motion (FedRAMP CR26 classes, CMMC Phase II pause, DPF review letters),",
        "the row says what is still true and tells the buyer to open the live list.",
        "Dates and mappings that were not solid were omitted or put in `note`.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
