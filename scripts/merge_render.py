#!/usr/bin/env python3
"""Merge Chrome-rendered trust extracts into enriched.json. Honest marks only."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CERT_MAP = [
    ("iso/iec 27001 (shown as in-progress", None),
    ("soc 2 type ii", "SOC 2 Type II"),
    ("soc 2 type 2", "SOC 2 Type II"),
    ("soc 2 (type 2)", "SOC 2 Type II"),
    ("soc 2 type 1", "SOC 2 Type I"),
    ("soc 2", "SOC 2 Type II"),
    ("soc 3", "SOC 3"),
    ("soc 1 type ii", "SOC 1 Type II"),
    ("soc 1 type 2", "SOC 1 Type II"),
    ("soc 1", "SOC 1 Type II"),
    ("soc (aicpa)", "SOC 2 Type II"),
    ("iso/iec 27001:2022", "ISO 27001"),
    ("iso 27001:2022", "ISO 27001"),
    ("iso/iec 27001 soa", None),
    ("iso/iec 27001", "ISO 27001"),
    ("iso 27001", "ISO 27001"),
    ("iso/iec 27017:2015", "ISO 27017"),
    ("iso/iec 27017", "ISO 27017"),
    ("iso 27017", "ISO 27017"),
    ("iso/iec 27018:2019", "ISO 27018"),
    ("iso/iec 27018:2025", "ISO 27018"),
    ("iso/iec 27018", "ISO 27018"),
    ("iso 27018", "ISO 27018"),
    ("iso/iec 27701:2019", "ISO 27701"),
    ("iso/iec 27701", "ISO 27701"),
    ("iso 27701", "ISO 27701"),
    ("iso/iec 42001:2023", "ISO 42001"),
    ("iso/iec 42001", "ISO 42001"),
    ("iso 42001:2023", "ISO 42001"),
    ("iso 42001", "ISO 42001"),
    ("iso 22301:2019", "ISO 22301"),
    ("iso 22301", "ISO 22301"),
    ("iso 27032", "ISO 27032"),
    ("iso 9001:2015", "ISO 9001"),
    ("csa star level 2", "CSA STAR"),
    ("csa star level 1", "CSA STAR"),
    ("csa star for ai", "CSA STAR"),
    ("csa star", "CSA STAR"),
    ("hipaa eligible", None),
    ("hipaa", "HIPAA"),
    ("hitech", "HIPAA"),
    ("gdpr", "GDPR"),
    ("ccpa", "CCPA"),
    ("cpra", "CCPA"),
    ("pci dss saq", "PCI DSS"),
    ("pci dss", "PCI DSS"),
    ("pci level 1", "PCI DSS"),
    ("pci-3ds", "PCI 3DS"),
    ("pci 3ds", "PCI 3DS"),
    ("pci mpoc", None),
    ("pci pin", None),
    ("pci pts", None),
    ("pci", "PCI DSS"),
    ("tisax", "TISAX"),
    ("fedramp high", "FedRAMP High"),
    ("tx-ramp level 2", "TX-RAMP"),
    ("tx-ramp", "TX-RAMP"),
    ("cyber essentials plus", "Cyber Essentials Plus"),
    ("uk cyber essentials plus", "Cyber Essentials Plus"),
    ("cyber essentials", "Cyber Essentials"),
    ("uk cyber essentials", "Cyber Essentials"),
    ("nist 800-171", "NIST 800-171"),
    ("nist csf", "NIST CSF"),
    ("nist", "NIST CSF"),
    ("pipeda", "PIPEDA"),
    ("lgpd", "LGPD"),
    ("eu-us dpf", "EU-US DPF"),
    ("swiss-us dpf", "EU-US DPF"),
    ("uk extension to eu-us dpf", "EU-US DPF"),
    ("data privacy framework", "EU-US DPF"),
    ("dod il5", "DoD IL5"),
    ("dod il4", "DoD IL4"),
    ("hds", "HDS"),
    ("aiuc-1", "AIUC-1"),
    ("casa tier 3", "CASA"),
    ("dora eligible", None),
    ("dora", "DORA"),
    ("nis 2", "NIS2"),
    ("irap", "IRAP"),
    ("bsi c5", "C5"),
    ("c5", "C5"),
    ("ismap", "ISMAP"),
    ("eu cloud coc", "EU Cloud CoC"),
    ("slsa", "SLSA"),
    ("wcag", None),
    ("vpat", None),
    ("vapt", None),
    ("privacy shield", None),
    ("pa-dss", None),
    ("emvco", None),
    ("apec cbpr", None),
    ("bimi", None),
    ("visa service provider", None),
    ("eu ai act", None),
    ("dsa", None),
    ("nfadp", None),
    ("privo", None),
    ("truste", None),
    ("microsoft sspa", None),
    ("aws partner", None),
    ("global prp", None),
]

PROC = {
    "amazon web services": "aws",
    "aws": "aws",
    "google cloud platform": "gcp",
    "google": "google",
    "microsoft azure": "azure",
    "microsoft": "microsoft",
    "cloudflare": "cloudflare",
    "stripe": "stripe",
    "twilio": "twilio",
    "salesforce": "salesforce",
    "intercom": "intercom",
    "snowflake": "snowflake",
    "sentry": "sentry",
    "openai": "openai",
    "anthropic": "anthropic",
    "workos": "workos",
    "datadog": "datadog",
    "algolia": "algolia",
    "eleven labs": "elevenlabs",
    "elevenlabs": "elevenlabs",
    "mailgun": "mailgun",
    "sparkpost": "sparkpost",
    "planetscale": "planetscale",
    "vercel": "vercel",
    "zendesk": "zendesk",
    "amplitude": "amplitude",
    "elastic": "elastic",
    "braintrust": "braintrust",
}

WEIGHT = {
    "SOC 2 Type II": 10, "SOC 2 Type I": 4, "SOC 1 Type II": 8, "SOC 3": 4,
    "ISO 27001": 10, "ISO 27701": 6, "ISO 42001": 6, "ISO 27017": 4, "ISO 27018": 4,
    "ISO 9001": 3, "ISO 22301": 4, "ISO 27032": 4,
    "FedRAMP High": 12, "FedRAMP 20x Moderate": 12, "TX-RAMP": 9,
    "PCI DSS": 8, "PCI 3DS": 7, "HITRUST": 8, "HIPAA": 6,
    "CSA STAR": 4, "TISAX": 8, "GDPR": 3, "CCPA": 3, "PIPEDA": 3, "LGPD": 3,
    "Cyber Essentials": 4, "Cyber Essentials Plus": 6,
    "NIST 800-171": 5, "NIST CSF": 3, "EU-US DPF": 4,
    "DoD IL4": 8, "DoD IL5": 10, "HDS": 6, "AIUC-1": 4, "CASA": 3,
    "DORA": 4, "NIS2": 4, "IRAP": 6, "C5": 6, "ISMAP": 6, "EU Cloud CoC": 4, "SLSA": 4,
}

SKIP_SUBSTR = ("in-progress", "privacy shield", "eligible")


def canon_cert(s: str):
    k = re.sub(r"\s+", " ", s.strip().lower())
    if any(x in k for x in SKIP_SUBSTR):
        return None
    for a, b in CERT_MAP:
        if k.startswith(a) or a == k or (len(a) > 8 and a in k):
            return b
    return None


def canon_proc(s: str):
    k = s.strip().lower()
    if "workos" in k:
        return "workos"
    for a, b in sorted(PROC.items(), key=lambda x: -len(x[0])):
        if a in k:
            return b
    slug = re.sub(r"[^a-z0-9]+", "-", k).strip("-")
    return slug[:40] if slug else None


def http_url(v) -> str | None:
    if not isinstance(v, str):
        return None
    v = v.strip()
    if not v.startswith("http"):
        return None
    if " (" in v:
        v = v.split(" (", 1)[0].strip()
    return v if v.startswith("http") else None


def rescore(c: dict) -> None:
    factors = {}
    score = 0
    if c.get("found"):
        factors["portal"] = 20
        score += 20
    cw = min(40, sum(WEIGHT.get(x, 4) for x in (c.get("certs") or [])))
    if cw:
        factors["marks"] = cw
        score += cw
    links = c.get("links") or {}
    if links.get("dpa"):
        factors["dpa"] = 8
        score += 8
    if links.get("subprocessors"):
        factors["processors"] = 8
        score += 8
    if links.get("status"):
        factors["status"] = 6
        score += 6
    if links.get("bug_bounty") or links.get("security_txt"):
        factors["disclosure"] = 6
        score += 6
    if links.get("privacy"):
        factors["privacy"] = 6
        score += 6
    year = c.get("founded_year")
    if year:
        lon = min(10, (2026 - int(year)) // 2)
        if lon:
            factors["longevity"] = lon
            score += lon
    score = min(100, score)
    if not c.get("found"):
        tier = "silent"
    elif score < 40:
        tier = "thin"
    elif score < 70:
        tier = "on-file"
    elif score < 90:
        tier = "substantial"
    else:
        tier = "complete"
    c["disclosure"] = {"score": score, "tier": tier, "factors": factors}


def normalize_row(raw: dict) -> dict | None:
    slug = raw.get("slug") or raw.get("vendor")
    if not slug:
        return None
    certs = raw.get("certs") or raw.get("certifications_visible") or []
    links = dict(raw.get("links") or {})
    for src, dest in (
        ("dpa_link", "dpa"),
        ("subprocessor_link", "subprocessors"),
        ("status_page_link", "status"),
        ("bounty_link", "bug_bounty"),
        ("privacy_policy", "privacy"),
        ("privacy_center", "privacy"),
        ("responsible_disclosure", "bug_bounty"),
        ("security", "security"),
        ("security_page", "security"),
        ("bounty", "bug_bounty"),
        ("vulnerability_disclosure_inbound", "bug_bounty"),
        ("report_vulnerability", "bug_bounty"),
        ("report_security_issue", "bug_bounty"),
    ):
        if src in raw and dest not in links:
            links[dest] = raw.get(src)
        if src in links and dest not in links:
            links[dest] = links.get(src)
    extras = raw.get("other_first_party_links") or []
    for u in extras:
        if not http_url(u):
            continue
        lu = u.lower()
        if "privacy" in lu and not links.get("privacy"):
            links["privacy"] = u
        elif "security" in lu and not links.get("security"):
            links["security"] = u
        elif "dpa" in lu or "data-processing" in lu:
            links.setdefault("dpa", u)
        elif "sub-processor" in lu or "subprocessor" in lu:
            links.setdefault("subprocessors", u)
    procs = raw.get("subprocessors") or raw.get("named_subprocessors") or raw.get("subprocessors_named") or []
    # Visible report titles count as marks (not invented).
    extra = []
    for blob in (raw.get("certificate_artifacts_gated") or []) + (raw.get("public_resources_listed") or []):
        extra.append(blob)
    certs = list(certs) + extra
    names = []
    for p in procs:
        if isinstance(p, dict):
            names.append(p.get("name") or "")
        else:
            names.append(p)
    return {
        "slug": slug,
        "certs": [x for x in certs if x],
        "links": {k: v for k, v in links.items() if http_url(v)},
        "subprocessors": [x for x in names if x],
        "notes": raw.get("notes") or "",
    }


def load_batch(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    rows = data.get("rows") or data.get("vendors") or data
    if isinstance(rows, dict):
        rows = list(rows.values())
    out = []
    for raw in rows:
        n = normalize_row(raw)
        if n:
            out.append(n)
    return out


def merge(paths: list[Path]) -> list[tuple]:
    enr = json.loads((ROOT / "data/enriched.json").read_text())
    subs = json.loads((ROOT / "data/subprocessors.json").read_text())
    by = {c["slug"]: c for c in enr["companies"]}
    nodes = {n["id"]: n for n in subs.get("nodes", [])}
    existing_e = {(e["from"], e["to"]) for e in subs.get("edges", [])}
    updated = []
    for path in paths:
        for row in load_batch(path):
            slug = row["slug"]
            c = by.get(slug)
            if not c:
                continue
            old = c.get("certs") or []
            for x in row["certs"]:
                n = canon_cert(x)
                if n and n not in old:
                    old.append(n)
            c["certs"] = old
            links = c.get("links") or {}
            for k, v in row["links"].items():
                dest = {
                    "privacy_policy": "privacy",
                    "bounty": "bug_bounty",
                }.get(k, k)
                if dest in ("dpa", "subprocessors", "status", "bug_bounty", "privacy", "security") and v:
                    links[dest] = v
            c["links"] = links
            oldp = c.get("subprocessors") or []
            for p in row["subprocessors"]:
                pid = canon_proc(p)
                if pid and pid != slug and pid not in oldp:
                    oldp.append(pid)
                    src = links.get("subprocessors") or c.get("trust_url") or ""
                    if src and (slug, pid) not in existing_e:
                        subs.setdefault("edges", []).append({
                            "from": slug, "to": pid, "source_url": src,
                            "evidence": "listed on public trust or subprocessors page",
                        })
                        existing_e.add((slug, pid))
                    if pid not in nodes:
                        nodes[pid] = {"id": pid, "name": pid, "kind": "subprocessor", "in_register": pid in by}
            c["subprocessors"] = oldp
            if c.get("certs"):
                shown = ", ".join(c["certs"][:6])
                extra = " +" + str(len(c["certs"]) - 6) if len(c["certs"]) > 6 else ""
                c["summary"] = f"Public trust center. On file: {shown}{extra}."
            elif "gated" in row["notes"].lower() or "access-request" in row["notes"].lower():
                c["summary"] = "Trust portal found; marks sit behind an access request."
            rescore(c)
            updated.append((slug, c["disclosure"]["tier"], c["disclosure"]["score"], len(c.get("certs") or [])))
    subs["nodes"] = list(nodes.values())
    enr["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (ROOT / "data/enriched.json").write_text(json.dumps(enr, indent=2) + "\n")
    (ROOT / "site/data/enriched.json").write_text(json.dumps(enr, indent=2) + "\n")
    (ROOT / "data/subprocessors.json").write_text(json.dumps(subs, indent=2) + "\n")
    (ROOT / "site/data/subprocessors.json").write_text(json.dumps(subs, indent=2) + "\n")
    return updated


if __name__ == "__main__":
    files = [Path(p) for p in sys.argv[1:]]
    if not files:
        files = sorted((ROOT / "data/render").glob("batch-*.json"))
    updated = merge(files)
    for row in updated:
        print(f"{row[0]:16} {row[1]:12} {row[2]:3} certs={row[3]}")
    print(f"merged {len(updated)} from {len(files)} files")
