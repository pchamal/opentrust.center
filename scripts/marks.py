#!/usr/bin/env python3
"""File marks a company names on its own first-party trust/security HTML.

A logo farm or “we can help you get SOC 2” sentence is not the company holding
the mark. Login walls stay empty. Names map to the attestations catalog.
"""
from __future__ import annotations

import re
from html import unescape

# Display names already used on the register. Ids live in build_pages.CERT_ID.
# Longest phrases first so Type II wins over SOC 2, FedRAMP High over FedRAMP.
MARK_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("SOC 2 Type II", re.compile(r"\bsoc[\s/_-]*2[\s/_-]*(?:type[\s/_-]*)?(?:ii|2)\b", re.I)),
    ("SOC 2 Type I", re.compile(r"\bsoc[\s/_-]*2[\s/_-]*(?:type[\s/_-]*)?(?:i|1)\b", re.I)),
    ("SOC 1 Type II", re.compile(r"\bsoc[\s/_-]*1[\s/_-]*(?:type[\s/_-]*)?(?:ii|2)\b", re.I)),
    ("SOC 1 Type I", re.compile(r"\bsoc[\s/_-]*1[\s/_-]*(?:type[\s/_-]*)?(?:i|1)\b", re.I)),
    ("SOC 2", re.compile(r"\bsoc[\s/_-]*2\b", re.I)),
    ("SOC 1", re.compile(r"\bsoc[\s/_-]*1\b", re.I)),
    ("SOC 3", re.compile(r"\bsoc[\s/_-]*3\b", re.I)),
    ("ISO 27001", re.compile(r"\biso(?:[\s/_-]*iec)?[\s/_-]*27001\b", re.I)),
    ("ISO 27017", re.compile(r"\biso(?:[\s/_-]*iec)?[\s/_-]*27017\b", re.I)),
    ("ISO 27018", re.compile(r"\biso(?:[\s/_-]*iec)?[\s/_-]*27018\b", re.I)),
    ("ISO 27701", re.compile(r"\biso(?:[\s/_-]*iec)?[\s/_-]*27701\b", re.I)),
    ("ISO 42001", re.compile(r"\biso(?:[\s/_-]*iec)?[\s/_-]*42001\b", re.I)),
    ("ISO 22301", re.compile(r"\biso(?:[\s/_-]*iec)?[\s/_-]*22301\b", re.I)),
    ("ISO 20000-1", re.compile(r"\biso(?:[\s/_-]*iec)?[\s/_-]*20000(?:-1)?\b", re.I)),
    ("ISO 13485", re.compile(r"\biso(?:[\s/_-]*iec)?[\s/_-]*13485\b", re.I)),
    ("ISO 9001", re.compile(r"\biso[\s/_-]*9001\b", re.I)),
    ("FedRAMP 20x Moderate", re.compile(r"\bfed[\s_-]*ramp[\s_-]*20x[\s_-]*moderate\b", re.I)),
    ("FedRAMP 20x Low", re.compile(r"\bfed[\s_-]*ramp[\s_-]*20x[\s_-]*low\b", re.I)),
    ("FedRAMP LI-SaaS", re.compile(r"\bfed[\s_-]*ramp[\s_-]*(?:tailored[\s_-]*)?li[\s_-]*saas\b", re.I)),
    ("FedRAMP High", re.compile(r"\bfed[\s_-]*ramp[\s_-]*high\b", re.I)),
    ("FedRAMP Moderate", re.compile(r"\bfed[\s_-]*ramp[\s_-]*moderate\b", re.I)),
    ("FedRAMP Low", re.compile(r"\bfed[\s_-]*ramp[\s_-]*low\b", re.I)),
    ("FedRAMP", re.compile(r"\bfed[\s_-]*ramp\b", re.I)),
    ("HITRUST r2", re.compile(r"\bhitrust[\s/_-]*r2\b", re.I)),
    ("HITRUST i1", re.compile(r"\bhitrust[\s/_-]*i1\b", re.I)),
    ("HITRUST e1", re.compile(r"\bhitrust[\s/_-]*e1\b", re.I)),
    ("HITRUST", re.compile(r"\bhitrust\b", re.I)),
    ("PCI 3DS", re.compile(r"\bpci[\s/_-]*3ds\b", re.I)),
    ("PCI DSS", re.compile(r"\bpci(?:[\s/_-]*dss|\s+dss|\s+level\s*[1-4])\b", re.I)),
    ("HIPAA", re.compile(r"\bhipaa\b", re.I)),
    ("CSA STAR", re.compile(r"\bcsa[\s/_-]*star\b", re.I)),
    ("Cyber Essentials Plus", re.compile(r"\b(?:uk\s+)?cyber[\s/_-]*essentials[\s/_-]*plus\b", re.I)),
    ("Cyber Essentials", re.compile(r"\b(?:uk\s+)?cyber[\s/_-]*essentials\b", re.I)),
    ("TX-RAMP", re.compile(r"\btx[\s/_-]*ramp\b", re.I)),
    ("StateRAMP", re.compile(r"\bstate[\s/_-]*ramp\b", re.I)),
    ("GovRAMP", re.compile(r"\bgov[\s/_-]*ramp\b", re.I)),
    ("CMMC L2", re.compile(r"\bcmmc[\s/_-]*(?:level[\s/_-]*)?(?:2|l2)\b", re.I)),
    ("CMMC L1", re.compile(r"\bcmmc[\s/_-]*(?:level[\s/_-]*)?(?:1|l1)\b", re.I)),
    ("CMMC", re.compile(r"\bcmmc\b", re.I)),
    ("NIST 800-53", re.compile(r"\bnist[\s/_-]*800[\s/_-]*53\b", re.I)),
    ("NIST 800-171", re.compile(r"\bnist[\s/_-]*800[\s/_-]*171\b", re.I)),
    ("NIST CSF", re.compile(r"\bnist[\s/_-]*csf\b", re.I)),
    ("AIUC-1", re.compile(r"\baiuc[\s/_-]*1\b", re.I)),
    ("EU-US DPF", re.compile(
        r"\b(?:eu[\s/_-]*u\.?s\.?[\s/_-]*(?:data[\s/_-]*)?privacy[\s/_-]*framework|"
        r"eu[\s/_-]*us[\s/_-]*dpf|data[\s/_-]*privacy[\s/_-]*framework)\b",
        re.I,
    )),
    ("TISAX", re.compile(r"\btisax\b", re.I)),
    ("IRAP", re.compile(r"\birap\b", re.I)),
    ("ISMAP", re.compile(r"\bismap\b", re.I)),
    ("C5", re.compile(r"\b(?:bsi[\s/_-]+c5|c5[\s/_-]+(?:type|attestation|catalogue|catalog))\b", re.I)),
    ("HDS", re.compile(r"\b(?:h[ée]bergement[\s/_-]*de[\s/_-]*donn[ée]es[\s/_-]*de[\s/_-]*sant[ée]|hds[\s/_-]*(?:certif|h[ée]bergeur))\b", re.I)),
    ("GDPR", re.compile(r"\bgdpr\b", re.I)),
    ("CCPA", re.compile(r"\b(?:ccpa|cpra)\b", re.I)),
    ("DORA", re.compile(r"\bdora\b", re.I)),
    ("NIS2", re.compile(r"\bnis[\s/_-]*2\b", re.I)),
    ("PIPEDA", re.compile(r"\bpipeda\b", re.I)),
    ("LGPD", re.compile(r"\blgpd\b", re.I)),
    ("SOX", re.compile(r"\bsarbanes[\s/_-]*oxley\b", re.I)),
    ("FIPS 140-3", re.compile(r"\bfips[\s/_-]*140[\s/_-]*3\b", re.I)),
    ("ISO 27032", re.compile(r"\biso(?:[\s/_-]*iec)?[\s/_-]*27032\b", re.I)),
]

# Phrase → catalog display name. Longer keys first.
LABEL_MAP: list[tuple[str, str | None]] = [
    ("iso/iec 27001 soa", "ISO 27001"),
    ("iso/iec 27001:2022", "ISO 27001"),
    ("iso/iec 27001", "ISO 27001"),
    ("iso 27001:2022", "ISO 27001"),
    ("iso 27001", "ISO 27001"),
    ("soc 2 type ii", "SOC 2 Type II"),
    ("soc 2 type 2", "SOC 2 Type II"),
    ("soc 2 (type 2)", "SOC 2 Type II"),
    ("soc 2 type i", "SOC 2 Type I"),
    ("soc 2 type 1", "SOC 2 Type I"),
    ("soc 2 report", "SOC 2"),
    ("soc 2", "SOC 2"),
    ("soc 3", "SOC 3"),
    ("soc 1 type ii", "SOC 1 Type II"),
    ("soc 1 type 2", "SOC 1 Type II"),
    ("soc 1", "SOC 1"),
    ("iso/iec 27017", "ISO 27017"),
    ("iso 27017", "ISO 27017"),
    ("iso/iec 27018", "ISO 27018"),
    ("iso 27018", "ISO 27018"),
    ("iso/iec 27701", "ISO 27701"),
    ("iso 27701", "ISO 27701"),
    ("iso/iec 42001", "ISO 42001"),
    ("iso 42001", "ISO 42001"),
    ("iso 22301", "ISO 22301"),
    ("iso 20000-1", "ISO 20000-1"),
    ("iso 20000", "ISO 20000-1"),
    ("iso 13485", "ISO 13485"),
    ("iso 9001", "ISO 9001"),
    ("csa star attestation", "CSA STAR"),
    ("csa star certification", "CSA STAR"),
    ("csa star level 2", "CSA STAR"),
    ("csa star level 1", "CSA STAR"),
    ("csa star", "CSA STAR"),
    ("hipaa report", "HIPAA"),
    ("hipaa", "HIPAA"),
    ("hitrust r2", "HITRUST r2"),
    ("hitrust i1", "HITRUST i1"),
    ("hitrust e1", "HITRUST e1"),
    ("hitrust csf", "HITRUST"),
    ("hitrust", "HITRUST"),
    ("pci dss", "PCI DSS"),
    ("pci-dss", "PCI DSS"),
    ("pci 3ds", "PCI 3DS"),
    ("fedramp 20x moderate", "FedRAMP 20x Moderate"),
    ("fedramp 20x low", "FedRAMP 20x Low"),
    ("fedramp li-saas", "FedRAMP LI-SaaS"),
    ("fedramp high", "FedRAMP High"),
    ("fedramp moderate", "FedRAMP Moderate"),
    ("fedramp low", "FedRAMP Low"),
    ("fedramp", "FedRAMP"),
    ("tx-ramp", "TX-RAMP"),
    ("stateramp", "StateRAMP"),
    ("govramp", "GovRAMP"),
    ("cyber essentials plus", "Cyber Essentials Plus"),
    ("cyber essentials", "Cyber Essentials"),
    ("gdpr", "GDPR"),
    ("ccpa", "CCPA"),
    ("cpra", "CCPA"),
    ("eu-us dpf", "EU-US DPF"),
    ("eu-u.s. data privacy framework", "EU-US DPF"),
    ("data privacy framework", "EU-US DPF"),
    ("cmmc level 2", "CMMC L2"),
    ("cmmc l2", "CMMC L2"),
    ("cmmc level 1", "CMMC L1"),
    ("cmmc l1", "CMMC L1"),
    ("cmmc", "CMMC"),
    ("nist 800-53", "NIST 800-53"),
    ("nist 800-171", "NIST 800-171"),
    ("nist csf", "NIST CSF"),
    ("aiuc-1", "AIUC-1"),
    ("tisax", "TISAX"),
    ("irap", "IRAP"),
    ("ismap", "ISMAP"),
    ("bsi c5", "C5"),
    ("c5", "C5"),
    ("hds", "HDS"),
    ("dora", "DORA"),
    ("nis 2", "NIS2"),
    ("nis2", "NIS2"),
    ("pipeda", "PIPEDA"),
    ("lgpd", "LGPD"),
    ("sarbanes-oxley", "SOX"),
    ("sox", "SOX"),
    ("fips 140-3", "FIPS 140-3"),
    ("iso 27032", "ISO 27032"),
]

SUPERSEDE = {
    "SOC 2": ["SOC 2 Type II", "SOC 2 Type I"],
    "SOC 1": ["SOC 1 Type II", "SOC 1 Type I"],
    "FedRAMP": [
        "FedRAMP High", "FedRAMP Moderate", "FedRAMP Low",
        "FedRAMP 20x Moderate", "FedRAMP 20x Low", "FedRAMP LI-SaaS",
    ],
    "Cyber Essentials": ["Cyber Essentials Plus"],
    "HITRUST": ["HITRUST r2", "HITRUST i1", "HITRUST e1"],
    "CMMC": ["CMMC L2", "CMMC L1"],
}

SKIP_PHRASE = (
    "in-progress", "in progress", "privacy shield", "eligible",
    "not yet certified", "coming soon", "planned",
)

# Sales / homework language — the company is not stating it holds the mark.
HELP_YOU = re.compile(
    r"(help(?:s|ing)? you (?:get|achieve|earn|obtain|prepare|automate)|"
    r"get your (?:company |organization |org )?(?:soc|iso|hipaa|pci)|"
    r"automate (?:your )?(?:soc|iso|pci|hipaa|fedramp|compliance)|"
    r"we can help you|"
    r"achieve soc\s*2 in|"
    r"soc\s*2 (?:made (?:easy|simple)|in (?:days|weeks|minutes)|faster)|"
    r"prepare for (?:soc|iso|fedramp|pci|hipaa)|"
    r"control frameworks?\s*\(|"
    r"\bex\.?\s*(?:iso|hipaa|pci|nist|soc)|"
    r"such as (?:soc|iso|hipaa|pci)|"
    r"including (?:soc|iso|hipaa|pci|gdpr)(?!\s+report))",
    re.I,
)

ATTR_RE = re.compile(
    r"""(?:aria-label|title|alt)\s*=\s*["']([^"']{2,120})["']""",
    re.I,
)
OPEN_TO_RE = re.compile(r"(?i)^open to\s+(.+)$")
TAG_RE = re.compile(r"<[^>]+>")


def _norm(s: str) -> str:
    s = unescape(s or "")
    s = s.replace("&amp;", "&")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def canon_mark(raw: str) -> str | None:
    """Map a page phrase to a catalog display name, or None if it is not a mark."""
    k = _norm(raw)
    if not k or any(x in k for x in SKIP_PHRASE):
        return None
    k = OPEN_TO_RE.sub(r"\1", k).strip(" .,:;")
    k = re.sub(r"\s+(report|attestation|certification|certificate|soa|so a)\s*$", "", k)
    for key, name in LABEL_MAP:
        if k == key or k.startswith(key + " ") or k.startswith(key + ":") or k.startswith(key + "("):
            return name
        if len(key) >= 10 and key in k:
            return name
    return None


def apply_supersede(names: list[str]) -> list[str]:
    have = set(names)
    out = []
    for name in names:
        supers = SUPERSEDE.get(name)
        if supers and any(s in have for s in supers):
            continue
        if name not in out:
            out.append(name)
    return out


def _context_ok(blob: str, start: int, end: int) -> bool:
    window = blob[max(0, start - 90): min(len(blob), end + 90)]
    return not HELP_YOU.search(window)


def extract_certs_from_html(html: str, text: str = "") -> list[str]:
    """Return catalog marks the first-party HTML actually names."""
    if not html and not text:
        return []
    found: list[str] = []
    seen: set[str] = set()

    def add(name: str | None) -> None:
        if name and name not in seen:
            seen.add(name)
            found.append(name)

    # Structured document cards (SafeBase “Open to …”, badge alt text).
    for raw in ATTR_RE.findall(html or ""):
        add(canon_mark(raw))

    blob = text or ""
    if html:
        visible = unescape(re.sub(r"\s+", " ", TAG_RE.sub(" ", html))).strip()
        attrs = " ".join(ATTR_RE.findall(html))
        blob = f"{blob} {visible} {attrs}".strip()

    if blob:
        for name, pat in MARK_PATTERNS:
            for m in pat.finditer(blob):
                if _context_ok(blob, m.start(), m.end()):
                    add(name)
                    break

    order = {name: i for i, (name, _p) in enumerate(MARK_PATTERNS)}
    found.sort(key=lambda n: order.get(n, 999))
    return apply_supersede(found)


def mark_blob(html: str, title: str = "", meta: str = "", text: str = "") -> str:
    """Text + attribute labels, for callers that already stripped tags."""
    attrs = " ".join(ATTR_RE.findall(html or ""))
    return " ".join(p for p in (title, meta, text, attrs) if p)
