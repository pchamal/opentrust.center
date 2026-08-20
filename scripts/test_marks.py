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

PLAIN = """
<h2>Certifications</h2>
<ul>
  <li>SOC 2 Type II</li>
  <li>ISO/IEC 27701</li>
  <li>PCI-DSS</li>
</ul>
<img alt="FedRAMP Moderate" src="/badges/fedramp-moderate.svg">
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
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
