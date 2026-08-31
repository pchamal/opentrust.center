#!/usr/bin/env python3
"""Extractor checks: hold the mark, not the sales pitch."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from marks import extract_certs_from_html  # noqa: E402


def eq(got, want, label):
    if list(got) != list(want):
        raise SystemExit(f"{label}: got {got!r} want {want!r}")


SAFEBASE = """
<title>NetApp Trust Center | Powered by SafeBase</title>
<a aria-label="Open to SOC 2 Type 2" href="/?itemUid=1">card</a>
<a aria-label="Open to ISO/IEC 27001:2022" href="/?itemUid=2">card</a>
<a aria-label="Open to HIPAA" href="/?itemUid=3">card</a>
<a aria-label="Open to ProcessUnity" href="/?itemUid=4">card</a>
<a aria-label="Open to CSA STAR Attestation" href="/?itemUid=5">card</a>
<p>Establish control frameworks (ex. ISO, HIPAA, PCI, NIST, SSAE-18) gather evidence</p>
"""

HELP = """
<title>Get SOC 2 in weeks</title>
<p>We can help you achieve SOC 2 and automate your ISO 27001 program.</p>
<p>Prepare for FedRAMP with our platform.</p>
"""

CONVEYOR = """
<title>Arctic Wolf Trust Center | Powered by Conveyor</title>
<img alt="soc2-type-2" src="/b.png">
<img alt="iso-27001" src="/i.png">
<img alt="TX-RAMP" src="/t.png">
<script>
window.__catalog = {
  "iso-13485":{"key":"iso-13485","label":"ISO 13485"},
  "pipeda":{"key":"pipeda","label":"PIPEDA"},
  "iso 27032":{"key":"iso 27032","label":"ISO 27032"}
};
</script>
"""

CONVEYOR_NAKED = """
<title>Figma Trust Center | Powered by Conveyor</title>
<p>Trust Center</p>
{"id":"2e74f6c2-7abf-4c40-852c-a0aead25fe8a","key":"iso-13485","label":"ISO 13485","shortLabel":"ISO 13485","backgroundColor":"#021f59"}
{"id":"x","key":"pipeda","label":"PIPEDA","shortLabel":"PIPEDA","backgroundColor":"#c33625"}
{"id":"y","key":"iso 27032","label":"ISO 27032","shortLabel":"ISO 27032","backgroundColor":"#051"}
"""

CMMC_GUIDE = """
<title>Huntress Trust Center | Powered by SafeBase</title>
<a aria-label="Open to SOC 2 Type 2" href="/?itemUid=1">card</a>
<a aria-label="Open to CCPA" href="/?itemUid=2">card</a>
<a aria-label="Open to GDPR" href="/?itemUid=3">card</a>
<a aria-label="Open to 7/13/2026  CMMC Phase II Suspension Information - Supplemental" href="/?itemUid=4">card</a>
<a aria-label="Open to How to Use CMMC Resources - Start Here" href="/?itemUid=5">card</a>
"""

PLAIN = """
<h2>Certifications</h2>
<ul>
  <li>SOC 2 Type II</li>
  <li>ISO/IEC 27701</li>
  <li>PCI-DSS</li>
</ul>
<img alt="FedRAMP Moderate" src="/badges/fedramp-moderate.svg">
"""

ALIGNED = """
<p>Our cloud security practices aligned to major industry security frameworks including NIST CSF and ISO 27001.</p>
<h2>Compliance</h2>
<ul>
  <li>ISO/IEC 27001</li>
  <li>Cyber Essentials</li>
  <li>ISO 9001:2015</li>
</ul>
"""


def main() -> int:
    eq(
        extract_certs_from_html(SAFEBASE),
        ["SOC 2 Type II", "ISO 27001", "HIPAA", "CSA STAR"],
        "safebase cards",
    )
    eq(extract_certs_from_html(HELP), [], "sales pitch")
    eq(
        extract_certs_from_html(PLAIN),
        ["SOC 2 Type II", "ISO 27701", "FedRAMP Moderate", "PCI DSS"],
        "plain list",
    )
    eq(extract_certs_from_html(""), [], "empty")
    eq(
        extract_certs_from_html(CONVEYOR),
        ["SOC 2 Type II", "ISO 27001", "TX-RAMP"],
        "conveyor catalog is not a hold",
    )
    eq(extract_certs_from_html(CONVEYOR_NAKED), [], "naked conveyor dictionary")
    eq(
        extract_certs_from_html(CMMC_GUIDE),
        ["SOC 2 Type II", "GDPR", "CCPA"],
        "cmmc resource is not a hold",
    )
    eq(
        extract_certs_from_html(ALIGNED),
        ["ISO 27001", "ISO 9001", "Cyber Essentials"],
        "aligned-to is not a hold",
    )
    eq(
        extract_certs_from_html(
            "<p>Software GmbH and SAG Deutschland GmbH are certified under the "
            "ENS MEDIUM category, as attested by an independent certification "
            "body accredited by CCN.</p>"
            "<p>Software AG UK Ltd has achieved Cyber Essentials certification.</p>"
            "<p>Our ISO 22301-certified Business Continuity Management System.</p>"
            "<p>Our ISO 9001-certified Quality Management System (QMS).</p>"
        ),
        ["ISO 22301", "ISO 9001", "Cyber Essentials", "ENS"],
        "software ag first-party holds",
    )
    eq(
        extract_certs_from_html(
            "<p>This policy defines Dubber’s commitment to protecting information "
            "assets and ensuring compliance with ISO/IEC 27001, ISO 22301, PCI DSS.</p>"
            "<p>Maintaining Certified Management Systems. Establishing, operating, "
            "monitoring, reviewing, auditing, and continually improving our Information "
            "Security Management System (ISMS) in line with ISO/IEC 27001 and its "
            "integration with the Business Continuity Management System (BCMS) under "
            "ISO 22301.</p>"
        ),
        ["ISO 27001", "ISO 22301", "PCI DSS"],
        "dubber first-party ISMS/BCMS holds",
    )
    eq(
        extract_certs_from_html(
            "<p>9.4. Protiviti Italia è certificata secondo gli standard "
            "ISO/IEC 27001 e ISO/IEC 27701, nei limiti e secondo il perimetro "
            "delle rispettive certificazioni applicabili.</p>"
        ),
        ["ISO 27001", "ISO 27701"],
        "protiviti italy first-party ISO holds",
    )
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
