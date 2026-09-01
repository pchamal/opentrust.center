#!/usr/bin/env python3
"""Marks follow stored first-party names. No invented certs. Signed screens stay."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from enrich import apply_marks_to_row  # noqa: E402
from file_company_marks import hold_marks  # noqa: E402
from marks import MARK_PATTERNS  # noqa: E402

PUBLIC = ROOT / "site" / "data.json"
ENRICHED = ROOT / "site" / "data" / "enriched.json"
REPORT = ROOT / "data" / "render" / "company-marks.json"
CATALOG = {name for name, _p in MARK_PATTERNS}


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"fail: {msg}")


def main() -> int:
    public = json.loads(PUBLIC.read_text())
    enr = json.loads(ENRICHED.read_text())
    report = json.loads(REPORT.read_text())
    by_pub = {c["slug"]: c for c in public["companies"]}
    by_enr = {c["slug"]: c for c in enr["companies"]}

    row = {
        "found": True,
        "certs": ["SOC 2"],
        "disclosure": {
            "score": 30,
            "tier": "thin",
            "factors": {"page": 20, "marks": 4, "privacy": 6},
        },
        "links": {"privacy": "https://example.com/privacy"},
    }
    added = apply_marks_to_row(row, ["SOC 2 Type II", "ISO 27001"])
    check(added == ["SOC 2 Type II", "ISO 27001"] or "ISO 27001" in added, "apply adds named marks")
    check("SOC 2 Type II" in row["certs"], "Type II supersedes bare SOC 2 or sits beside it")
    check("ISO 27001" in row["certs"], "ISO 27001 filed")
    check(row["disclosure"]["factors"]["privacy"] == 6, "apply leaves other factors")
    check(row["disclosure"]["factors"]["page"] == 20, "apply leaves page factor")
    check(row["disclosure"]["factors"]["marks"] >= 4, "marks weight grew")
    check("Marks cited from public HTML" in (row.get("summary") or ""), "clerk summary names the hold")
    check(apply_marks_to_row(row, ["ISO 27001"]) == [], "duplicate mark is not re-filed")
    check(apply_marks_to_row(row, []) == [], "empty names stay empty")

    kept, why = hold_marks(
        ["EU-US DPF", "GDPR"],
        "Chartbeat has certified to the U.S. Department of Commerce that it adheres "
        "to the EU-U.S. Data Privacy Framework. GDPR rights are described below.",
        "privacy",
    )
    check(kept == ["EU-US DPF"], f"DPF self-cert files, privacy GDPR stays open: {kept} {why}")
    kept, why = hold_marks(
        ["EU-US DPF", "GDPR"],
        "We transfer data using standard contractual clauses and the EU-US Data Privacy Framework.",
        "privacy",
    )
    check(kept == [] and why == "regulation-only", f"DPF among SCCs stays open: {kept} {why}")
    kept, why = hold_marks(
        ["HIPAA", "CCPA"],
        "Information excluded from the CCPA, such as health information covered by HIPAA.",
        "privacy",
    )
    check(kept == [] and why in {"regulation-only", "no-named-marks"}, f"HIPAA scope sentence stays open: {kept} {why}")
    kept, why = hold_marks(
        ["HIPAA"],
        "identifiers from protected health information required under the Health Insurance "
        "Portability and Accountability Act (“HIPAA”), 45 CFR § 164.514(b)(2). This Notice "
        "is distinct from our HIPAA Notice of Privacy Practices. Certain health information "
        "governed by HIPAA is excluded.",
        "privacy",
    )
    check(kept == [], f"HIPAA de-id / notice sentence stays open: {kept} {why}")
    kept, why = hold_marks(
        ["CMMC"],
        "Tabletop Exercises CMMC Readiness Solutions VISIBL",
        "privacy",
    )
    check(kept == [], f"CMMC readiness product stays open: {kept} {why}")

    kept, why = hold_marks(
        ["ISO 27001", "ISO 27017", "SOC 1 Type II", "SOC 2 Type II", "C5", "CSA STAR"],
        "Our solutions have received multiple certifications and attestations, including: "
        "ISO 27001 certification for our Information Security Management System (ISMS). "
        "ISO 27001, ISO 27017, SOC 1 Type 2 and SOC 2 Type 2 for secure operations of cloud products. "
        "BSI C5 Type 2 attestation as well as CSA STAR Level 2 certification for security.",
        "security",
    )
    check(
        {"ISO 27001", "ISO 27017", "SOC 1 Type II", "SOC 2 Type II", "C5", "CSA STAR"} <= set(kept),
        f"Signavio holds stay: {kept} {why}",
    )
    # Regulation-only on a privacy notice stays open.
    kept, why = hold_marks(
        ["GDPR"],
        "You have a right to appeal to the data protection supervisory authorities pursuant to Art. 77 GDPR.",
        "privacy",
    )
    check(kept == [] and why == "regulation-only", f"Software AG privacy GDPR stays open: {kept} {why}")
    kept, why = hold_marks(
        ["Cyber Essentials", "ENS", "ISO 22301", "ISO 9001"],
        "Software AG UK Ltd has achieved Cyber Essentials certification. "
        "Software GmbH and SAG Deutschland GmbH are certified under the ENS MEDIUM category. "
        "Our ISO 22301-certified Business Continuity Management System. "
        "Our ISO 9001-certified Quality Management System (QMS).",
        "security",
    )
    check(
        kept == ["Cyber Essentials", "ENS", "ISO 22301", "ISO 9001"],
        f"Software AG first-party holds stay: {kept} {why}",
    )
    kept, why = hold_marks(
        ["ISO 27001", "ISO 22301", "PCI DSS"],
        "This policy defines Dubber’s commitment to protecting the Confidentiality, "
        "Integrity, and Availability (CIA) of information assets and ensuring "
        "compliance with ISO/IEC 27001, ISO 22301, PCI DSS. Maintaining Certified "
        "Management Systems Establishing, operating, monitoring, reviewing, auditing, "
        "and continually improving our Information Security Management System (ISMS) "
        "in line with ISO/IEC 27001 and its integration with the Business Continuity "
        "Management System (BCMS) under ISO 22301.",
        "security",
    )
    check(
        {"ISO 27001", "ISO 22301"} <= set(kept),
        f"Dubber ISMS/BCMS holds stay: {kept} {why}",
    )
    kept, why = hold_marks(
        ["ISO 27001"],
        "11.1 ISO/IEC 27001. We adhere to and are compliant with the ISO/IEC 27001 "
        "industry standard. We are audited by an independent body annually on the "
        "ISO/IEC 27001 standard. Our certificate is available in the Dubber Website.",
        "security",
    )
    check(kept == ["ISO 27001"], f"Dubber ISO 27001 certificate sentence stays: {kept} {why}")
    kept, why = hold_marks(
        ["GDPR"],
        "This Compliance Statement provides a general description of how Dubber "
        "processes and safeguards personal data as a processor in accordance with the GDPR.",
        "privacy",
    )
    check(kept == [] and why == "regulation-only", f"Dubber GDPR statement stays open: {kept} {why}")
    kept, why = hold_marks(
        ["ISO 27001", "SOC 2 Type II"],
        "At the company level, Sonar maintains both ISO 27001:2022 certification "
        "and SOC 2 Type II attestation for all products and services.",
        "trust",
    )
    check(
        kept == ["ISO 27001", "SOC 2 Type II"],
        f"Sonar first-party trust-center holds stay: {kept} {why}",
    )
    kept, why = hold_marks(
        ["GDPR", "CCPA"],
        "the GDPR and (ii) the EU e-Privacy Directive. CCPA means the California "
        "Consumer Privacy Act, as amended by the California Privacy Rights Act.",
        "privacy",
    )
    check(kept == [] and why == "regulation-only", f"Sonar DPA GDPR/CCPA definitions stay open: {kept} {why}")
    kept, why = hold_marks(
        ["GDPR"],
        "In SuperOffice we are committed to protect and respect your privacy in "
        "compliance with EU- General Data Protection Regulation (GDPR) 2016/679, "
        "dated April 27th 2016.",
        "privacy",
    )
    check(kept == [] and why == "regulation-only", f"SuperOffice privacy GDPR stays open: {kept} {why}")
    kept, why = hold_marks(
        ["HIPAA"],
        "you shall not provide us with any PHI (as defined in the Health Insurance "
        "Portability and Accountability Act of 1996 (“HIPAA”)) in connection with "
        "the provision of services under these terms, but to the extent that you "
        "are acting as a Covered Entity under HIPAA and there is incidental "
        "disclosure of PHI about your consumers to Trustpilot and to the extent "
        "that Trustpilot, as a result, is deemed under HIPAA to be acting as a "
        "Business Associate, the disclosure of such PHI will be governed by the "
        "HIPAA Business Associate Addendum.",
        "privacy",
    )
    check(kept == [], f"HIPAA BAA / shall-not-provide-PHI stays open: {kept} {why}")
    kept, why = hold_marks(
        ["SOC 2 Type II", "SOC 3", "PCI DSS", "CSA STAR"],
        "BigID is SOC 2 certified, demonstrating that the platform and its "
        "supporting processes, people, and controls are designed to help "
        "keep customer data secure. BigID’s SOC 3 report provides a general-use "
        "overview of the security, confidentiality, availability, and privacy "
        "controls used to protect customer data. Its PCI compliance reflects "
        "security controls that have been evaluated by an independent assessor. "
        "BigID has also published its completed CAIQ self-assessment in the "
        "CSA STAR Registry.",
        "security",
    )
    check(
        {"SOC 2 Type II", "SOC 3", "PCI DSS", "CSA STAR"} <= set(kept),
        f"BigID first-party certification holds stay: {kept} {why}",
    )
    kept, why = hold_marks(
        ["EU-US DPF", "GDPR"],
        "Commvault has certified to the U.S. Department of Commerce that it adheres "
        "to the EU-U.S. Data Privacy Framework Principles (EU-U.S. DPF Principles). "
        "Commvault manages your data in compliance with the E.U.’s General Data "
        "Protection Regulation (“GDPR”).",
        "privacy",
    )
    check(kept == ["EU-US DPF"], f"Commvault DPF self-cert files, privacy GDPR stays open: {kept} {why}")
    kept, why = hold_marks(
        ["ISO 27001", "ISO 27017", "ISO 27018", "ISO 27701", "ISO 22301", "ISO 27032"],
        "Clarivate maintains internationally recognized ISO certifications that "
        "validate our security management practices. Clarivate PLC holds ISO 27001 "
        "certification covering ISMS. Ex Libris is certified to multiple ISO "
        "standards (22301, 27001, 27017, 27018, 27032, 27701).",
        "trust",
    )
    check(
        {"ISO 27001", "ISO 27017", "ISO 27018", "ISO 27701", "ISO 22301", "ISO 27032"} <= set(kept),
        f"Clarivate first-party ISO holds stay: {kept} {why}",
    )
    from file_company_marks import reject_reason
    # Title tail is a portal product line. Catalog chrome is not a hold.
    check(
        reject_reason(
            "https://trustcenter.example.com",
            {
                "ok": True,
                "status": 200,
                "final_url": "https://trustcenter.example.com",
                "title": "Example Digital Trust Center | Powered by ExamplePortal",
                "text": "SOC 2 Type II ISO 27001 GDPR NIS2 SOX",
                "html": "<html></html>",
                "ctype": "text/html",
            },
            {"slug": "example", "domain": "example.com", "trust_url": "https://trustcenter.example.com"},
        ) == "js-portal",
        "powered-by portal title stays unread",
    )
    kept, why = hold_marks(
        ["ISO 27001", "ISO 27018"],
        "Our adherence to ISO 27018:2019 and ISO 27001:2013 certifications "
        "underscores our dedication to maintaining robust security standards.",
        "privacy",
    )
    check(kept == ["ISO 27001", "ISO 27018"], f"Alfa ISO certifications stay: {kept} {why}")
    kept, why = hold_marks(
        ["EU-US DPF"],
        "Where available, Braze, Inc. complies with the EU-U.S. Data Privacy "
        "Framework, the UK Extension to the EU-U.S. Data Privacy Framework, "
        "and the Swiss-U.S. Data Privacy Framework (collectively, the "
        "“Data Privacy Framework”) as set forth by the U.S. Department of Commerce.",
        "privacy",
    )
    check(kept == ["EU-US DPF"], f"Braze DPF compliance claim stays: {kept} {why}")
    kept, why = hold_marks(
        ["HIPAA"],
        "For HIPAA Patient Requests (All HIPPA forms)",
        "privacy",
    )
    check(kept == [], f"Abbott HIPAA patient-request link stays open: {kept} {why}")
    kept, why = hold_marks(
        ["HIPAA"],
        "HIPAA Notice of Privacy Practices. Aflac is fully committed to its "
        "compliance with the HIPAA Rules, including the Privacy Rule. For its "
        "HIPAA-covered insurance policies, Aflac is federally mandated to send "
        "a notice. Rights which differ from those granted by HIPAA.",
        "privacy",
    )
    check(kept == [], f"Aflac HIPAA notice stays open: {kept} {why}")
    kept, why = hold_marks(
        ["SOC 2 Type II", "HITRUST", "PCI DSS", "HIPAA"],
        "The data of patients/consumers is protected by HIPAA. "
        "Security & compliance HITRUST CSF, SOC 2 Type 2 and PCI Level 1 certified",
        "privacy",
    )
    check("HIPAA" not in kept, f"Phreesia HIPAA scope sentence stays open: {kept} {why}")
    check(
        {"SOC 2 Type II", "HITRUST", "PCI DSS"} <= set(kept),
        f"Phreesia first-party certification holds stay: {kept} {why}",
    )
    kept, why = hold_marks(
        ["SOC 2 Type I", "GDPR"],
        "SOC 2 Type 1 certified Audited annually GDPR compliant EU data residency "
        "by default. Your data is never used to train models.",
        "security",
    )
    check(kept == ["SOC 2 Type I"], f"LightOn GDPR-compliant copy stays open: {kept} {why}")
    kept, why = hold_marks(
        ["ISO 27001", "PCI DSS", "GDPR"],
        "We are ISO 27001 certified. All payments are managed according to PCI DSS "
        "standard by PayPal, and Stripe. We meet requirements of the General Data "
        "Protection Regulation (GDPR).",
        "security",
    )
    check(kept == ["ISO 27001"], f"SurveyLab processor PCI / GDPR requirements stay open: {kept} {why}")
    kept, why = hold_marks(
        ["HIPAA"],
        "Protected health information subject to the Health Insurance "
        "Portability and Accountability Act (“HIPAA”). In such cases, we are "
        "bound by more stringent legal and contractual obligations.",
        "privacy",
    )
    check(kept == [], f"Centene HIPAA subject-to sentence stays open: {kept} {why}")
    kept, why = hold_marks(
        ["HIPAA"],
        "In such cases, we act as a business associate to the health care "
        "provider and will comply with the requirements of HIPAA with respect "
        "to your protected health information.",
        "privacy",
    )
    check(kept == [], f"4DMedical HIPAA business-associate sentence stays open: {kept} {why}")
    kept, why = hold_marks(
        ["EU-US DPF", "GDPR", "CCPA", "PIPEDA"],
        "Cboe and its wholly-owned subsidiaries participate and comply with "
        "the EU-U.S. Data Privacy Framework. Cboe has certified to the U.S. "
        "Department of Commerce that it adheres to the DPF Principles.",
        "privacy",
    )
    check(kept == ["EU-US DPF"], f"Cboe DPF self-cert files, privacy GDPR/CCPA stay open: {kept} {why}")
    kept, why = hold_marks(
        ["HIPAA", "CCPA"],
        "This privacy notice is not applicable to our health plans. Our health "
        "plan members and applicants should refer to the HIPAA Notice of Privacy "
        "Practices. Once texted, your information may no longer be regulated "
        "under HIPAA’s Privacy Rule.",
        "privacy",
    )
    check(kept == [], f"Elevance HIPAA notice stays open: {kept} {why}")
    kept, why = hold_marks(
        ["HIPAA", "CCPA"],
        "Information covered by certain sector-specific privacy laws, including: "
        "The Fair Credit Reporting Act (FCRA); The Gramm-Leach-Bliley Act (GLBA); "
        "The Health Insurance Portability and Accountability Act of 1996 (HIPAA).",
        "privacy",
    )
    check(kept == [], f"Fannie Mae HIPAA scope list stays open: {kept} {why}")
    kept, why = hold_marks(
        ["HIPAA", "CCPA"],
        "This Privacy Policy does not apply to information that would be "
        "considered “Protected Health Information” under the Health Insurance "
        "Portability and Accountability Act of 1996 (“HIPAA”). Targeted "
        "advertising will occur with your authorization or otherwise in "
        "compliance with HIPAA and other applicable laws.",
        "privacy",
    )
    check(kept == [], f"HCA HIPAA notice / compliance sentence stays open: {kept} {why}")
    kept, why = hold_marks(
        ["EU-US DPF", "CCPA"],
        "First Solar complies with the EU-U.S. Data Privacy Framework "
        "(“EU-U.S. DPF”) as set forth by the U.S. Department of Commerce. "
        "First Solar has certified to the U.S. Department of Commerce that "
        "it adheres to the EU-U.S. Data Privacy Framework Principles.",
        "privacy",
    )
    check(kept == ["EU-US DPF"], f"First Solar DPF self-cert files, privacy CCPA stays open: {kept} {why}")
    kept, why = hold_marks(
        ["ISO 27001", "PCI DSS", "Cyber Essentials Plus", "CCPA"],
        "GBG is ISO27001 certified, with some areas of our business also "
        "covered by PCI-DSS, Cyber Essentials and/or Cyber Essentials Plus.",
        "privacy",
    )
    check(
        {"ISO 27001", "PCI DSS", "Cyber Essentials Plus"} <= set(kept),
        f"GB Group first-party certification holds stay: {kept} {why}",
    )
    kept, why = hold_marks(
        ["HIPAA"],
        "The HIPAA Privacy Practices Notice, for individuals in the United "
        "States covered under an RTX health and wellness plan.",
        "privacy",
    )
    check(kept == [], f"RTX HIPAA Privacy Practices Notice stays open: {kept} {why}")
    kept, why = hold_marks(
        ["EU-US DPF", "GDPR"],
        "Backblaze, Inc. (“Backblaze”) complies with the EU-U.S. Data Privacy "
        "Framework (EU-U.S. DPF) and the Swiss-U.S. Data Privacy Framework "
        "(Swiss-U.S. DPF) as set forth by the U.S. Department of Commerce. "
        "Backblaze has certified to the U.S. Department of Commerce that it "
        "adheres to the EU-U.S. Data Privacy Framework Principles.",
        "privacy",
    )
    check(kept == ["EU-US DPF"], f"Backblaze DPF self-cert files, privacy GDPR stays open: {kept} {why}")
    kept, why = hold_marks(
        ["PCI DSS", "CCPA"],
        "We maintain annual compliance with global Payment Card Industry Data "
        "Security Standard (PCI DSS) adopted by the payment card brands for "
        "all companies that process, store or transmit cardholder data.",
        "privacy",
    )
    check(kept == ["PCI DSS"], f"Fiserv PCI DSS compliance sentence stays: {kept} {why}")
    kept, why = hold_marks(
        ["EU-US DPF"],
        "Travelport, LP (“Travelport”) complies with the EU-U.S. Data Privacy "
        "Framework (EU-U.S. DPF). Travelport has certified to the U.S. "
        "Department of Commerce that it adheres to the EU-U.S. Data Privacy "
        "Framework Principles (EU-U.S. DPF Principles).",
        "privacy",
    )
    check(kept == ["EU-US DPF"], f"Travelport DPF self-cert stays: {kept} {why}")
    kept, why = hold_marks(
        ["SOC 2 Type II", "ISO 27001", "PCI DSS"],
        "We have obtained ISO 27001, PCI DSS, and SOC2 Type 2 certifications.",
        "privacy",
    )
    check(
        kept == ["SOC 2 Type II", "ISO 27001", "PCI DSS"],
        f"Trip.com certification sentence stays: {kept} {why}",
    )
    kept, why = hold_marks(
        ["EU-US DPF", "GDPR", "CCPA"],
        "VeriSign, Inc. complies with the EU-U.S. Data Privacy Framework "
        "(“EU-U.S. DPF”), the UK Extension to the EU-U.S. DPF, and the "
        "Swiss-U.S. Data Privacy Framework (“Swiss-U.S. DPF”) as set forth "
        "by the U.S. Department of Commerce. VeriSign, Inc. has certified "
        "to the U.S. Department of Commerce that it adheres to the EU-U.S. "
        "Data Privacy Framework Principles.",
        "privacy",
    )
    check(kept == ["EU-US DPF"], f"Verisign DPF self-cert files, privacy GDPR/CCPA stay open: {kept} {why}")

    for rec in report.get("marks_filed") or []:
        slug, url, added = rec["slug"], rec["url"], rec["added"]
        pub = by_pub[slug]
        stored = list(by_enr[slug].get("certs") or [])
        check(all(m in stored for m in added), f"{slug} stored certs missing {added}")
        check(all(m in (pub.get("certs") or []) for m in added), f"{slug} public certs missing {added}")
        check(all(m in CATALOG for m in added), f"{slug} invented cert {added}")
        check((pub.get("file") or {}).get("marks") in (True, 20), f"{slug} file.marks not filled")
        check(any((a.get("name") in added) for a in (pub.get("attestations") or [])), f"{slug} attestations missing bind")
        html = (ROOT / "site" / "c" / f"{slug}.html").read_text(encoding="utf-8")
        for name in added:
            check(name in html, f"{slug} dossier missing {name}")
            att = next((a for a in pub.get("attestations") or [] if a.get("name") == name), None)
            if att and att.get("id"):
                check(
                    f'attestations.html#{att["id"]}' in html,
                    f"{slug} {name} is not clerk-linked to the framework entry",
                )
        check("safebase" not in html.lower() and "conveyor" not in html.lower() and "vanta" not in html.lower(), f"{slug} named a portal vendor")
        check(url.startswith("http"), f"{slug} missing source URL")

    for rec in report.get("stayed_open") or []:
        pub = by_pub[rec["slug"]]
        if rec.get("thin"):
            continue
        check(not (pub.get("certs") or []), f"{rec['slug']} invented certs while open")
        marks_flag = (pub.get("file") or {}).get("marks")
        check(
            marks_flag in (0, 10, False, None) or pub.get("fedramp"),
            f"{rec['slug']} file.marks filled without a name",
        )

    # Bind: stored certs from this pass fill the glyph. Display stays clerk words.
    for row in public["companies"]:
        slug = row["slug"]
        enr_row = by_enr.get(slug) or {}
        stored = [c for c in (enr_row.get("certs") or []) if c]
        if stored:
            check((row.get("file") or {}).get("marks") in (True, 20), f"{slug} stored certs did not fill glyph")
    filed_slugs = {rec["slug"] for rec in report.get("marks_filed") or []}
    for slug in filed_slugs:
        stored = [c for c in (by_enr[slug].get("certs") or []) if c]
        check(all(c in CATALOG for c in stored), f"{slug} stored non-catalog {stored}")

    index = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    graph = (ROOT / "site" / "graph.html").read_text(encoding="utf-8")
    companies = (ROOT / "site" / "companies.html").read_text(encoding="utf-8")
    zoom = (ROOT / "site" / "c" / "zoom.html").read_text(encoding="utf-8")
    check("AI Trust Index" in index, "AITI title stays")
    check("The public file on AI systems. Not a trust score." in index, "AITI lede stays")
    check("page · standards · processors · evals · incidents" in index, "AITI legend stays")
    check("AITI is the public file on AI systems, not a trust score." in index, "AITI footer was not cut")
    method = (ROOT / "site" / "methodology.html").read_text(encoding="utf-8")
    check('<h1 class="page-title">Method</h1>' in method, "H1 Method")
    check(
        '<p class="lede">How we count a public file. Not a company grade.</p>' in method,
        "exact Method lede",
    )
    check('id="copy-rubric">copy rubric</button>' in method, "Method copy rubric word")
    check("Cite the dossier: /c/{slug}.html" in method, "copied rubric cites the dossier")
    check(
        'href="./brand.html">specimen</a> · <a href="./methodology.html">methodology</a> · <a href="./contact.html">contact</a> · <a href="https://github.com/pchamal/opentrust.center" target="_blank" rel="noopener noreferrer">code</a>'
        in index,
        "AITI footer has specimen · methodology · contact · code",
    )
    contact = (ROOT / "site" / "contact.html").read_text(encoding="utf-8")
    check('<h1 class="page-title">Contact</h1>' in contact, "H1 Contact")
    check(
        '<p class="lede">Write <a class="official" href="mailto:hello@opentrust.center">hello@opentrust.center</a>.</p>'
        in contact,
        "exact Contact lede",
    )
    check("pukar@" not in contact.lower() and "securitypalhq" not in contact.lower(), "no personal email on contact")
    check("<form" not in contact.lower(), "no contact form")
    check("See methodology" not in index and "See methodology" not in companies, "no See methodology chip")
    check(
        index.count(
            '<p class="file-method" id="file-method">20 printed · 10 on file, not extracted · 0 missing. 100 is five prints.</p>'
        )
        == 1,
        "AITI method line is the three-state sentence once",
    )
    check("Concentration" not in graph, "list dropped Concentration")
    check("Named by" in graph, "list kept Named by")
    check("toFixed(1)" not in (ROOT / "site" / "graph.js").read_text(encoding="utf-8"), "Concentration numeral left the list")
    check("Public trust register" in companies, "Companies identity stays")
    check("01 April 2025" not in zoom, "zoom still has no date processors")
    check("Amazon Web Services" in zoom, "zoom still names AWS")
    check("0–100" not in index and "0-100" not in index, "no 0-100 score on AITI")

    # This increment: latest expand silent/unread rows with a domain,
    # after leftover instrument walks and the empty-cert URL queue.
    batch = report.get("batch") or []
    want = [
        "gamecaster", "coresoft", "hanaho", "davka", "chartboost",
        "filament-games", "hitcents", "big-finish-games", "epicenter-studios",
        "cosmi-corporation", "exakt-entertainment", "gun-interactive",
        "jump-shot-media", "global-vr", "isotope-244", "laminar-research",
        "midboss", "kru-interactive", "mentez", "the-logic-factory",
        "mikengreg", "holistic-design", "limbic-software", "matrix-games",
        "mastiff", "ientertainment-network", "nyko", "mistwalker",
        "muzzy-lane", "playmotion", "naked-sky-entertainment", "reaxion",
        "open-network-entertainment", "ntn-buzztime", "movaya", "re-logic",
        "punch-entertainment", "raven-software", "nerjyzed-entertainment",
        "night-light-interactive",
    ]
    check(batch == want, f"batch is latest-expand silent 40, got {batch}")
    filed = {rec["slug"]: rec for rec in (report.get("marks_filed") or [])}
    check(filed == {}, f"filed slugs {sorted(filed)}")
    stayed = {rec["slug"] for rec in (report.get("stayed_open") or [])}
    check(stayed == set(want), f"honest zeros {sorted(stayed)}")
    from file_company_marks import PRIOR_ATTEMPTED, select_batch
    for slug in batch:
        check(slug in PRIOR_ATTEMPTED, f"{slug} is on the next-increment skip list")
    leftover = select_batch(list(public["companies"]), by_enr)
    leftover_slugs = {r["slug"] for r in leftover}
    check(not leftover_slugs & set(batch), f"this batch is not retried, got {leftover_slugs & set(batch)}")
    for slug in (
        "percona", "agility-robotics", "berkshire-grey", "sherpa-ai", "pubnub",
        "foxit-software", "opengov", "aptean", "qad-redzone", "blackboard",
        "peak", "translated", "anaplan", "sarvam-ai", "salesloft",
        "verint-systems", "thoughtspot",
        "trendrr", "lighton", "mu-sigma", "sojern", "surveylab",
    ):
        check(slug in PRIOR_ATTEMPTED, f"{slug} leftover walk stays on the skip list")
        check(slug not in leftover_slugs, f"{slug} leftover is not retried")
    check(
        {"ISO 27001", "EU-US DPF"} <= set(by_pub["mitek-systems"].get("certs") or []),
        "mitek-systems prior ISO 27001 / DPF stays",
    )
    check("SOC 2" not in (by_pub["mitek-systems"].get("certs") or []), "mitek AICPA SOC badge is not SOC 2")
    check(
        (by_pub["nagarro"].get("certs") or []) == ["ISO 27001"],
        f"nagarro prior certs stay {by_pub['nagarro'].get('certs')}",
    )
    check("CCPA" not in (by_pub["nagarro"].get("certs") or []), "nagarro privacy CCPA is not a hold")
    check("EU-US DPF" not in (by_pub["nagarro"].get("certs") or []), "nagarro internal privacy framework is not DPF")
    for slug in (
        "abbott-laboratories", "aflac", "centene", "4dmedical-limited",
        "elevance-health", "fannie-mae", "hca-healthcare", "humana", "rtx",
    ):
        pub = by_pub[slug]
        check(not (pub.get("certs") or []), f"{slug} HIPAA notice is not a filed mark")
        check((pub.get("file") or {}).get("marks") in (0, 10, False, None), f"{slug} marks glyph stays open")
    check("EU-US DPF" in (by_pub["braze"].get("certs") or []), "braze prior DPF stays")
    check("EU-US DPF" in (by_pub["cboe-global-markets"].get("certs") or []), "cboe prior DPF stays")
    check("EU-US DPF" in (by_pub["first-solar"].get("certs") or []), "first-solar prior DPF stays")
    check(
        {"ISO 27001", "ISO 27018"} <= set(by_pub["alfa-financial-software"].get("certs") or []),
        "alfa prior ISO holds stay",
    )
    check(
        {"ISO 27001", "PCI DSS", "Cyber Essentials Plus"}
        <= set(by_pub["gb-group"].get("certs") or []),
        "gb-group prior holds stay",
    )
    for slug in ("domo", "sopra-steria"):
        pub = by_pub[slug]
        check(not (pub.get("certs") or []), f"{slug} certs stay empty")
        check((pub.get("file") or {}).get("marks") in (0, 10, False, None), f"{slug} marks glyph stays open")
    for slug in ("domo", "sopra-steria", "bigid", "ctsi-global", "telestream", "seqera-labs", "walkme", "virtutech"):
        html = (ROOT / "site" / "c" / f"{slug}.html").read_text(encoding="utf-8")
        check("Official page" in html, f"{slug} still prints Official page")
        visible = re.sub(r'https?://\S+', "", html)
        visible = re.sub(r'href="[^"]+"', "", visible).lower()
        check(
            "safebase" not in visible
            and "conveyor" not in visible
            and "vanta" not in visible
            and "securitypal" not in visible
            and "sprinto" not in visible
            and "anecdotes" not in visible
            and "upguard" not in visible,
            f"{slug} named a portal vendor",
        )
    check("SOC 2 Type II" in (by_pub["bigid"].get("certs") or []), "bigid prior SOC 2 Type II stays")
    check("EU-US DPF" in (by_pub["commvault"].get("certs") or []), "commvault prior DPF stays")
    for slug in ("esko", "trustpilot", "toast", "snap", "superoffice", "genedata"):
        pub = by_pub[slug]
        check(not (pub.get("certs") or []), f"{slug} certs stay empty")
        check((pub.get("file") or {}).get("marks") in (0, 10, False, None), f"{slug} marks glyph stays open")
        html = (ROOT / "site" / "c" / f"{slug}.html").read_text(encoding="utf-8")
        check("safebase" not in html.lower() and "conveyor" not in html.lower() and "vanta" not in html.lower(), f"{slug} named a portal vendor")
    check("HIPAA" not in (by_pub["trustpilot"].get("certs") or []), "trustpilot HIPAA BAA is not a filed mark")
    sonar = by_pub["sonar"]
    check(sonar.get("certs") == ["ISO 27001", "SOC 2 Type II"], f"sonar prior certs stay {sonar.get('certs')}")
    check((sonar.get("file") or {}).get("marks") == 20, "sonar marks stay printed")
    pronto_html = (ROOT / "site" / "c" / "pronto-software.html").read_text(encoding="utf-8")
    check("Official page" in pronto_html, "Pronto Software still prints Official page")
    years = {"superoffice": 1990, "genedata": 1997, "trustpilot": 2007, "sonar": 2008}
    for slug, year in years.items():
        check(by_pub[slug].get("founded_year") == year, f"{slug} year stays {year}")
    check(
        {"SOC 2 Type II", "HITRUST", "PCI DSS"} <= set(by_pub["phreesia"].get("certs") or []),
        "phreesia prior holds stay",
    )
    check("HIPAA" not in (by_pub["phreesia"].get("certs") or []), "phreesia HIPAA scope stays open")
    check("SOC 2 Type I" in (by_pub["lighton"].get("certs") or []), "lighton SOC 2 Type I filed")
    check("GDPR" not in (by_pub["lighton"].get("certs") or []), "lighton GDPR-compliant copy stays open")
    check(
        {"SOC 2 Type II", "ISO 27001"} <= set(by_pub["mu-sigma"].get("certs") or []),
        "mu-sigma ISO / SOC 2 Type II filed",
    )
    check((by_pub["sojern"].get("certs") or []) == ["EU-US DPF"], f"sojern certs {by_pub['sojern'].get('certs')}")
    check((by_pub["surveylab"].get("certs") or []) == ["ISO 27001"], f"surveylab certs {by_pub['surveylab'].get('certs')}")
    check("PCI DSS" not in (by_pub["surveylab"].get("certs") or []), "surveylab PayPal/Stripe PCI stays open")
    check("GDPR" not in (by_pub["surveylab"].get("certs") or []), "surveylab GDPR requirements stay open")
    check("EU-US DPF" in (by_pub["backblaze"].get("certs") or []), "backblaze DPF filed")
    check("TX-RAMP" in (by_pub["backblaze"].get("certs") or []), "backblaze TX-RAMP stays")
    check("PCI DSS" in (by_pub["fiserv"].get("certs") or []), "fiserv PCI DSS filed")
    check("TX-RAMP" in (by_pub["fiserv"].get("certs") or []), "fiserv TX-RAMP stays")
    check((by_pub["travelport"].get("certs") or []) == ["EU-US DPF"], f"travelport certs {by_pub['travelport'].get('certs')}")
    check(
        {"SOC 2 Type II", "ISO 27001", "PCI DSS"} <= set(by_pub["trip-com"].get("certs") or []),
        f"trip-com certs {by_pub['trip-com'].get('certs')}",
    )
    check((by_pub["verisign"].get("certs") or []) == ["EU-US DPF"], f"verisign certs {by_pub['verisign'].get('certs')}")
    check("CCPA" not in (by_pub["fiserv"].get("certs") or []), "fiserv privacy CCPA is not a hold")
    check("GDPR" not in (by_pub["backblaze"].get("certs") or []), "backblaze privacy GDPR is not a hold")
    check("GDPR" not in (by_pub["verisign"].get("certs") or []), "verisign privacy GDPR is not a hold")
    check("CSA STAR" in (by_pub["huawei"].get("certs") or []), "huawei CSA STAR stays")
    check("TX-RAMP" in (by_pub["cognizant"].get("certs") or []), "cognizant TX-RAMP stays")
    check(
        {"ISO 27001", "ISO 27701"} <= set(by_pub["protiviti"].get("certs") or []),
        f"protiviti Italy ISO holds {by_pub['protiviti'].get('certs')}",
    )
    check("SOX" not in (by_pub["protiviti"].get("certs") or []), "protiviti 404 SOX chrome stays open")
    check((by_pub["protiviti"].get("file") or {}).get("marks") == 20, "protiviti marks print")
    check(
        {"CSA STAR", "TX-RAMP", "ISO 27001"} <= set(by_pub["accenture"].get("certs") or []),
        f"accenture keeps marketplace marks and first-party ISO 27001 {by_pub['accenture'].get('certs')}",
    )
    check("GDPR" not in (by_pub["accenture"].get("certs") or []), "accenture privacy GDPR stays open")
    check((by_pub["ookla"].get("certs") or []) == ["EU-US DPF"], f"ookla certs {by_pub['ookla'].get('certs')}")
    check("GDPR" not in (by_pub["ookla"].get("certs") or []), "ookla privacy GDPR stays open")
    check((by_pub["ookla"].get("file") or {}).get("marks") == 20, "ookla DPF prints")
    check((by_pub["responsive"].get("certs") or []) == ["EU-US DPF"], f"responsive certs {by_pub['responsive'].get('certs')}")
    check("SOC 2" not in (by_pub["responsive"].get("certs") or []), "responsive product-page SOC stays open")
    check("ISO 27001" not in (by_pub["responsive"].get("certs") or []), "responsive product-page ISO stays open")
    check("GDPR" not in (by_pub["responsive"].get("certs") or []), "responsive GDPR-compliant copy stays open")
    check((by_pub["rfpio"].get("certs") or []) == [], "empty rfpio shell does not copy Responsive marks")
    check((by_pub["aml-rightsource"].get("certs") or []) == [], "aml-rightsource 404 Q-Mark chrome is not a hold")
    check((by_pub["aml-rightsource"].get("file") or {}).get("marks") in (0, 10, False, None), "aml-rightsource marks stay open")
    check((by_pub["aml-rightsource"].get("file") or {}).get("page") == 0, "aml-rightsource Official page stays open")
    check(
        ((by_pub["aml-rightsource"].get("instruments") or {}).get("privacy") or {}).get("url")
        == "https://www.amlrightsource.com/privacy-policy",
        "aml-rightsource privacy URL stays on file",
    )
    li_certs = set(by_pub["linkedin"].get("certs") or [])
    check(
        {"SOC 2", "ISO 27001", "ISO 27018", "ISO 22301", "PCI DSS"} <= li_certs,
        f"linkedin trust-and-compliance holds {sorted(li_certs)}",
    )
    check("CCPA" not in li_certs, "linkedin DPA CCPA stays open")
    check("GDPR" not in li_certs, "linkedin DPA GDPR stays open")
    check((by_pub["linkedin"].get("file") or {}).get("marks") == 20, "linkedin marks print")
    check((by_pub["linkedin"].get("file") or {}).get("page") == 20, "linkedin Official page prints")
    check(by_pub["linkedin"].get("found") is True, "linkedin Official page is on file")
    check(
        by_pub["linkedin"].get("trust_url") == "https://security.linkedin.com/trust-and-compliance",
        "linkedin trust URL is first-party Trust and Compliance",
    )
    check("safebase" not in (by_pub["linkedin"].get("trust_url") or ""), "linkedin Official page is not the portal")
    check(
        {"ISO 27001", "ISO 9001", "ISO 22301", "ISO 20000-1"} <= set(by_pub["softcat"].get("certs") or []),
        f"softcat about-us ISO holds {by_pub['softcat'].get('certs')}",
    )
    check((by_pub["softcat"].get("file") or {}).get("marks") == 20, "softcat marks print")
    check((by_pub["softcat"].get("file") or {}).get("years") == 20, "softcat years stay")
    check((by_pub["softcat"].get("file") or {}).get("page") == 0, "softcat portal is not Official page")
    check(by_pub["softcat"].get("found") is False, "softcat Official page stays open")
    check(not by_pub["softcat"].get("trust_url"), "softcat portal is not the Official page URL")
    check(
        ((by_pub["softcat"].get("instruments") or {}).get("trust") or {}).get("url")
        == "https://trust.softcat.com",
        "softcat trust instrument keeps the portal URL as a link",
    )
    check("GDPR" not in (by_pub["softcat"].get("certs") or []), "softcat privacy GDPR stays open")
    kept, why = hold_marks(
        ["SOC 2", "ISO 27001", "ISO 27018", "ISO 22301", "PCI DSS"],
        "Our Smart Trust Center offers customers access to LinkedIn’s latest security "
        "reports and documents, including ISO certifications and our SOC 2 report. "
        "ISO 27001 The International Organization for Standardization 27001 Standard. "
        "ISO 27018 covers privacy protections. ISO 22301 is the standard for Business "
        "Continuity. PCI DSS The Payment Card Industry Data Security Standards.",
        "trust",
    )
    check(
        kept == ["SOC 2", "ISO 27001", "ISO 27018", "ISO 22301", "PCI DSS"],
        f"LinkedIn Trust and Compliance holds stay: {kept} {why}",
    )
    kept, why = hold_marks(
        ["ISO 27001", "ISO 9001", "ISO 22301", "ISO 20000-1"],
        "we also carry ISO standards 27001 (InfoSec), ISO 9001 (Quality), "
        "22301 (Business Continuity) and ISO20000 (Service Management).",
        "about",
    )
    check(
        kept == ["ISO 27001", "ISO 9001", "ISO 22301", "ISO 20000-1"],
        f"Softcat about-us four ISO holds stay: {kept} {why}",
    )
    check((by_pub["kumospace"].get("certs") or []) == ["SOC 2"], f"kumospace certs {by_pub['kumospace'].get('certs')}")
    check("HIPAA" not in (by_pub["kumospace"].get("certs") or []), "kumospace paid-plan HIPAA stays open")
    check("GDPR" not in (by_pub["kumospace"].get("certs") or []), "kumospace GDPR-compliant copy stays open")
    check((by_pub["kumospace"].get("file") or {}).get("marks") == 20, "kumospace SOC 2 prints")
    check((by_pub["kumospace"].get("file") or {}).get("page") == 20, "kumospace Official page prints")
    check(by_pub["kumospace"].get("found") is True, "kumospace Official page is on file")
    check(
        by_pub["kumospace"].get("trust_url") == "https://www.kumospace.com/security",
        "kumospace Official page is first-party /security",
    )
    check(
        ((by_pub["kumospace"].get("instruments") or {}).get("privacy") or {}).get("url")
        == "https://www.kumospace.com/privacy",
        "kumospace privacy URL stays on file",
    )
    check((by_pub["kumospace"].get("file") or {}).get("dpa") in (0, False, None), "kumospace DPA stays open")
    check((by_pub["kumospace"].get("file") or {}).get("years") in (0, False, None), "kumospace years stay open")
    check((by_pub["branch-metrics"].get("certs") or []) == [], f"branch certs {by_pub['branch-metrics'].get('certs')}")
    check("HIPAA" not in (by_pub["branch-metrics"].get("certs") or []), "branch HIPAA-eligible copy stays open")
    check("GDPR" not in (by_pub["branch-metrics"].get("certs") or []), "branch GDPR privacy-principle nav stays open")
    check("SOC 2" not in (by_pub["branch-metrics"].get("certs") or []), "branch Conveyor SOC 2 stays unread")
    check("ISO 27001" not in (by_pub["branch-metrics"].get("certs") or []), "branch Conveyor ISO stays unread")
    check((by_pub["branch-metrics"].get("file") or {}).get("marks") == 10, "branch marks stay dotted")
    check((by_pub["branch-metrics"].get("file") or {}).get("page") == 20, "branch Official page prints")
    check(by_pub["branch-metrics"].get("found") is True, "branch Official page is on file")
    check(
        by_pub["branch-metrics"].get("trust_url") == "https://www.branch.io/security",
        "branch Official page is first-party /security",
    )
    check("trust.branch.io" not in (by_pub["branch-metrics"].get("trust_url") or ""), "branch Official page is not the Conveyor portal")
    check(
        ((by_pub["branch-metrics"].get("instruments") or {}).get("privacy") or {}).get("url")
        == "https://legal.branch.io/saas/privacy-policy/",
        "branch privacy URL stays on file",
    )
    # This cut: Cloud Ace company-overview ISO holds. Homepage is not Official page.
    check(
        {"ISO 27001", "ISO 9001"} <= set(by_pub["cloud-ace"].get("certs") or []),
        f"cloud-ace first-party ISO holds {by_pub['cloud-ace'].get('certs')}",
    )
    check((by_pub["cloud-ace"].get("file") or {}).get("marks") == 20, "cloud-ace marks print")
    check((by_pub["cloud-ace"].get("file") or {}).get("page") in (0, False, None), "cloud-ace Official page stays open")
    check(by_pub["cloud-ace"].get("found") is False, "cloud-ace company overview is not Official page")
    check(not by_pub["cloud-ace"].get("trust_url"), "cloud-ace has no invented Official page")
    check((by_pub["cloud-ace"].get("file") or {}).get("years") in (0, False, None), "cloud-ace years stay open")
    ace_html = (ROOT / "site" / "c" / "cloud-ace.html").read_text(encoding="utf-8")
    check("<h1>Cloud Ace</h1>" in ace_html, "cloud-ace dossier is its own file")
    check("ISO 27001" in ace_html, "cloud-ace dossier prints ISO 27001")
    check("ISO 9001" in ace_html, "cloud-ace dossier prints ISO 9001")
    # Clerk hold: CEQUENS homepage chips / certificate img alts are not holds.
    # Official page stays open. Privacy URL stays. Completeness stays 0.
    check((by_pub["cequens-fze"].get("certs") or []) == [], f"cequens chips unread {by_pub['cequens-fze'].get('certs')}")
    check("SOC 2" not in (by_pub["cequens-fze"].get("certs") or []), "cequens SOC 2 chip stays open")
    check("SOC 2 Type II" not in (by_pub["cequens-fze"].get("certs") or []), "cequens does not invent Type II")
    check("ISO 27001" not in (by_pub["cequens-fze"].get("certs") or []), "cequens ISO 27001 chip stays open")
    check("PCI DSS" not in (by_pub["cequens-fze"].get("certs") or []), "cequens PCI DSS chip stays open")
    check("ISO 27017" not in (by_pub["cequens-fze"].get("certs") or []), "cequens ISO 27017 img alt stays open")
    check("ISO 27018" not in (by_pub["cequens-fze"].get("certs") or []), "cequens ISO 27018 img alt stays open")
    check("GDPR" not in (by_pub["cequens-fze"].get("certs") or []), "cequens GDPR Compliant stays open")
    check((by_pub["cequens-fze"].get("file") or {}).get("marks") in (0, False, None), "cequens marks stay open")
    check((by_pub["cequens-fze"].get("file") or {}).get("page") in (0, False, None), "cequens Official page stays open")
    check((by_pub["cequens-fze"].get("file") or {}).get("dpa") in (0, False, None), "cequens DPA stays open")
    check((by_pub["cequens-fze"].get("file") or {}).get("years") in (0, False, None), "cequens years stay open")
    check(by_pub["cequens-fze"].get("found") is False, "cequens homepage is not Official page")
    check(not by_pub["cequens-fze"].get("trust_url"), "cequens has no invented Official page")
    check(
        ((by_pub["cequens-fze"].get("instruments") or {}).get("privacy") or {}).get("url")
        == "https://www.cequens.com/privacy-policy",
        "cequens privacy URL stays on file",
    )
    ceq_html = (ROOT / "site" / "c" / "cequens-fze.html").read_text(encoding="utf-8")
    check("<h1>CEQUENS</h1>" in ceq_html, "cequens dossier is its own file")
    check("SOC 2" not in ceq_html, "cequens dossier does not print SOC 2")
    check("ISO 27001" not in ceq_html, "cequens dossier does not print ISO 27001")
    check("PCI DSS" not in ceq_html, "cequens dossier does not print PCI DSS")
    check("www.cequens.com/privacy-policy" in ceq_html, "cequens dossier keeps the privacy URL")
    # This cut: Virtuozzo portal is not Official page. Portal SOC 2 unread.
    # trust.site URL stays an instrument link. Years stay.
    check(by_pub["virtuozzo"].get("found") is False, "virtuozzo Official page stays open")
    check(not by_pub["virtuozzo"].get("trust_url"), "virtuozzo portal is not Official page")
    check((by_pub["virtuozzo"].get("certs") or []) == [], "virtuozzo portal SOC 2 stays unread")
    check((by_pub["virtuozzo"].get("file") or {}).get("page") in (0, False, None), "virtuozzo page stays open")
    check((by_pub["virtuozzo"].get("file") or {}).get("marks") in (0, False, None), "virtuozzo marks stay open")
    check((by_pub["virtuozzo"].get("file") or {}).get("years") == 20, "virtuozzo years stay")
    check(
        ((by_pub["virtuozzo"].get("instruments") or {}).get("trust") or {}).get("url")
        == "https://virtuozzo.trust.site",
        "virtuozzo trust instrument keeps the portal URL as a link",
    )
    vz_html = (ROOT / "site" / "c" / "virtuozzo.html").read_text(encoding="utf-8")
    check("<h1>Virtuozzo</h1>" in vz_html, "virtuozzo dossier is its own file")
    check("https://virtuozzo.trust.site" in vz_html, "virtuozzo dossier cites the portal as an instrument URL")
    check("Official page · not on file" in vz_html, "virtuozzo Official page stays open")
    check("SOC 2" not in vz_html, "virtuozzo dossier does not print portal SOC 2")
    check("sprinto" not in vz_html.lower(), "virtuozzo dossier names no portal vendor")
    check(by_pub["jack-henry"].get("found") is False, "jack-henry Official page stays open")
    check(by_pub["jack-henry-and-associates"].get("found") is False, "jack-henry-and-associates stays its own empty file")
    check(by_pub["jack-henry"]["domain"] == "jackhenry.com", "jack-henry domain stays jackhenry.com")
    check(by_pub["jack-henry-and-associates"]["domain"] == "jackhenry.com", "jack-henry-and-associates keeps the same printed domain")
    jh_html = (ROOT / "site" / "c" / "jack-henry.html").read_text(encoding="utf-8")
    check("<h1>Jack Henry</h1>" in jh_html, "jack-henry dossier is its own file")
    check(
        "<h1>Jack Henry &amp; Associates</h1>" in (ROOT / "site" / "c" / "jack-henry-and-associates.html").read_text(encoding="utf-8"),
        "jack-henry-and-associates dossier stays a separate file",
    )
    # This cut: ProWritingAid first-party Trust Center. SOC 2 Security compliance
    # prose. Do not invent Type II. Privacy URL is first-party HTML.
    check(by_pub["prowritingaid"].get("found") is True, "prowritingaid Official page is on file")
    check(
        by_pub["prowritingaid"].get("trust_url") == "https://prowritingaid.com/trust-center",
        "prowritingaid Official page is first-party /trust-center",
    )
    check((by_pub["prowritingaid"].get("certs") or []) == ["SOC 2"], f"prowritingaid certs {by_pub['prowritingaid'].get('certs')}")
    check("SOC 2 Type II" not in (by_pub["prowritingaid"].get("certs") or []), "prowritingaid does not invent Type II")
    check((by_pub["prowritingaid"].get("file") or {}).get("page") == 20, "prowritingaid Official page prints")
    check((by_pub["prowritingaid"].get("file") or {}).get("marks") == 20, "prowritingaid SOC 2 prints")
    check(
        ((by_pub["prowritingaid"].get("instruments") or {}).get("privacy") or {}).get("url")
        == "https://prowritingaid.com/en/Home/Privacy",
        "prowritingaid privacy URL is on file",
    )
    pwa_html = (ROOT / "site" / "c" / "prowritingaid.html").read_text(encoding="utf-8")
    check("<h1>ProWritingAid</h1>" in pwa_html, "prowritingaid dossier is its own file")
    check("https://prowritingaid.com/trust-center" in pwa_html, "prowritingaid dossier cites Official page")
    check("SOC 2" in pwa_html, "prowritingaid dossier prints SOC 2")
    # MaxMind commitment-to-security: SOC 2 Type II audit, own SOC 3 report,
    # DPF self-cert. ISO 27001 is "based on" the standard — not a hold.
    # GDPR/CCPA stay open. Years 2002 from first-party our-story HTML.
    check(by_pub["maxmind"].get("found") is True, "maxmind Official page is on file")
    check(
        by_pub["maxmind"].get("trust_url")
        == "https://www.maxmind.com/en/company/commitment-to-security",
        "maxmind Official page is first-party commitment-to-security",
    )
    check(
        {"SOC 2 Type II", "SOC 3", "EU-US DPF"} <= set(by_pub["maxmind"].get("certs") or []),
        f"maxmind first-party holds {by_pub['maxmind'].get('certs')}",
    )
    check("ISO 27001" not in (by_pub["maxmind"].get("certs") or []), "maxmind ISO 27001 based-on stays open")
    check("GDPR" not in (by_pub["maxmind"].get("certs") or []), "maxmind privacy GDPR stays open")
    check("CCPA" not in (by_pub["maxmind"].get("certs") or []), "maxmind privacy CCPA stays open")
    check(by_pub["maxmind"].get("founded_year") == 2002, "maxmind year 2002")
    check((by_pub["maxmind"].get("file") or {}).get("page") == 20, "maxmind Official page prints")
    check((by_pub["maxmind"].get("file") or {}).get("marks") == 20, "maxmind marks print")
    check((by_pub["maxmind"].get("file") or {}).get("years") == 20, "maxmind years print")
    mm_html = (ROOT / "site" / "c" / "maxmind.html").read_text(encoding="utf-8")
    check("<h1>MaxMind</h1>" in mm_html, "maxmind dossier is its own file")
    check("SOC 2 Type II" in mm_html, "maxmind dossier prints SOC 2 Type II")
    check("SOC 3" in mm_html, "maxmind dossier prints SOC 3")
    check("ISO 27001" not in mm_html, "maxmind dossier does not print based-on ISO 27001")
    # OTTRA about-page prose. Homepage ISO / Cyber Essentials img alts unread.
    # About is not Official page. Years stay open (since 2020).
    check(
        {"ISO 27001", "Cyber Essentials"} <= set(by_pub["ottra"].get("certs") or []),
        f"ottra first-party holds {by_pub['ottra'].get('certs')}",
    )
    check(by_pub["ottra"].get("found") is False, "ottra about is not Official page")
    check(not by_pub["ottra"].get("trust_url"), "ottra has no invented Official page")
    check((by_pub["ottra"].get("file") or {}).get("page") in (0, False, None), "ottra Official page stays open")
    check((by_pub["ottra"].get("file") or {}).get("marks") == 20, "ottra marks print")
    check((by_pub["ottra"].get("file") or {}).get("years") in (0, False, None), "ottra years stay open")
    ottra_html = (ROOT / "site" / "c" / "ottra.html").read_text(encoding="utf-8")
    check("<h1>OTTRA</h1>" in ottra_html, "ottra dossier is its own file")
    check("ISO 27001" in ottra_html, "ottra dossier prints ISO 27001")
    check("Cyber Essentials" in ottra_html, "ottra dossier prints Cyber Essentials")
    check("Official page · not on file" in ottra_html, "ottra Official page stays open")
    # ReleaseTEAM founded 1999 from first-party about HTML. Privacy URL on file.
    # Official page stays open.
    check(by_pub["releaseteam"].get("founded_year") == 1999, "releaseteam year 1999")
    check(
        by_pub["releaseteam"].get("founded_source") == "https://www.releaseteam.com/about/",
        "releaseteam year source is first-party about",
    )
    check((by_pub["releaseteam"].get("file") or {}).get("years") == 20, "releaseteam years print")
    check(by_pub["releaseteam"].get("found") is False, "releaseteam Official page stays open")
    check(
        ((by_pub["releaseteam"].get("instruments") or {}).get("privacy") or {}).get("url")
        == "https://www.releaseteam.com/privacy-policy/",
        "releaseteam privacy URL is on file",
    )
    rt_html = (ROOT / "site" / "c" / "releaseteam.html").read_text(encoding="utf-8")
    check("<h1>ReleaseTEAM</h1>" in rt_html, "releaseteam dossier is its own file")
    check("founded · 1999" in rt_html, "releaseteam dossier year")
    # This cut: HorizonIQ first-party /compliance. "We hold PCI DSS 3.0,
    # SOC 2 Type II, and ISO 27001 certifications." About-page 1996 is Internap.
    check(by_pub["horizoniq"].get("found") is True, "horizoniq Official page is on file")
    check(
        by_pub["horizoniq"].get("trust_url") == "https://www.horizoniq.com/compliance/",
        "horizoniq Official page is first-party /compliance",
    )
    check(
        {"SOC 2 Type II", "ISO 27001", "PCI DSS"} <= set(by_pub["horizoniq"].get("certs") or []),
        f"horizoniq first-party holds {by_pub['horizoniq'].get('certs')}",
    )
    check("HIPAA" not in (by_pub["horizoniq"].get("certs") or []), "horizoniq homepage HIPAA stays open")
    check(by_pub["horizoniq"].get("founded_year") in (None, 0, False), "horizoniq Internap 1996 stays open")
    check((by_pub["horizoniq"].get("file") or {}).get("page") == 20, "horizoniq Official page prints")
    check((by_pub["horizoniq"].get("file") or {}).get("marks") == 20, "horizoniq marks print")
    check((by_pub["horizoniq"].get("file") or {}).get("years") in (0, False, None), "horizoniq years stay open")
    hq_html = (ROOT / "site" / "c" / "horizoniq.html").read_text(encoding="utf-8")
    check("<h1>HorizonIQ</h1>" in hq_html, "horizoniq dossier is its own file")
    check("https://www.horizoniq.com/compliance/" in hq_html, "horizoniq dossier cites Official page")
    check("SOC 2 Type II" in hq_html, "horizoniq dossier prints SOC 2 Type II")
    check("ISO 27001" in hq_html, "horizoniq dossier prints ISO 27001")
    # Hive first-party security policy. We are SOC2 certified. Hosting ISO
    # 27001 accredited stays open. Privacy DPF is a Commerce self-cert.
    check(by_pub["hive"].get("found") is True, "hive Official page is on file")
    check(
        by_pub["hive"].get("trust_url") == "https://hive.com/policy-documents/security",
        "hive Official page is first-party /policy-documents/security",
    )
    check("SOC 2" in (by_pub["hive"].get("certs") or []), f"hive SOC 2 {by_pub['hive'].get('certs')}")
    check("SOC 2 Type II" not in (by_pub["hive"].get("certs") or []), "hive does not invent Type II")
    check("ISO 27001" not in (by_pub["hive"].get("certs") or []), "hive hosting ISO 27001 stays open")
    check("EU-US DPF" in (by_pub["hive"].get("certs") or []), "hive DPF self-cert prints")
    check(by_pub["hive"].get("founded_year") == 2016, "hive year 2016 stays")
    check((by_pub["hive"].get("file") or {}).get("page") == 20, "hive Official page prints")
    check((by_pub["hive"].get("file") or {}).get("marks") == 20, "hive marks print")
    check((by_pub["hive"].get("file") or {}).get("years") == 20, "hive years stay")
    hive_html = (ROOT / "site" / "c" / "hive.html").read_text(encoding="utf-8")
    check("<h1>Hive</h1>" in hive_html, "hive dossier is its own file")
    check("https://hive.com/policy-documents/security" in hive_html, "hive dossier cites Official page")
    check("SOC 2" in hive_html, "hive dossier prints SOC 2")
    check("ISO 27001" not in hive_html, "hive dossier does not print hosting ISO 27001")
    check("hiveage" not in hive_html.lower(), "hive is not aliased to hiveage")
    # DataMotion company-overview HITRUST + 1999. Overview is not Official page.
    # Homepage FedRAMP is Azure's. HIPAA is product / customer-quote language.
    check(by_pub["datamotion"].get("found") is False, "datamotion company overview is not Official page")
    check(not by_pub["datamotion"].get("trust_url"), "datamotion has no invented Official page")
    check((by_pub["datamotion"].get("certs") or []) == ["HITRUST"], f"datamotion certs {by_pub['datamotion'].get('certs')}")
    check("FedRAMP" not in (by_pub["datamotion"].get("certs") or []), "datamotion Azure FedRAMP stays open")
    check("HIPAA" not in (by_pub["datamotion"].get("certs") or []), "datamotion HIPAA product copy stays open")
    check("PCI DSS" not in (by_pub["datamotion"].get("certs") or []), "datamotion PCI-DSS among compliance-across stays open")
    check(by_pub["datamotion"].get("founded_year") == 1999, "datamotion year 1999")
    check(
        by_pub["datamotion"].get("founded_source") == "https://datamotion.com/company-overview/",
        "datamotion year source is first-party company overview",
    )
    check((by_pub["datamotion"].get("file") or {}).get("page") in (0, False, None), "datamotion Official page stays open")
    check((by_pub["datamotion"].get("file") or {}).get("marks") == 20, "datamotion HITRUST prints")
    check((by_pub["datamotion"].get("file") or {}).get("years") == 20, "datamotion years print")
    dm_html = (ROOT / "site" / "c" / "datamotion.html").read_text(encoding="utf-8")
    check("<h1>Datamotion</h1>" in dm_html or "<h1>DataMotion</h1>" in dm_html, "datamotion dossier is its own file")
    check("HITRUST" in dm_html, "datamotion dossier prints HITRUST")
    check("founded · 1999" in dm_html, "datamotion dossier year")
    check("Official page · not on file" in dm_html, "datamotion Official page stays open")
    # This cut: Appcues DPA SOC 2 Type 2 audit + privacy DPF self-cert.
    # Official page stays the existing portal. Years stay open.
    kept, why = hold_marks(
        ["SOC 2 Type II"],
        "Appcues has completed a SOC 2 Type 2 audit of the security of the Subscription Service.",
        "dpa",
    )
    check(kept == ["SOC 2 Type II"], f"appcues DPA Type 2 audit files: {kept} {why}")
    kept, why = hold_marks(
        ["EU-US DPF"],
        "Appcues has certified to the U.S. Department of Commerce that it adheres "
        "to the EU-U.S. Data Privacy Framework Principles.",
        "privacy",
    )
    check(kept == ["EU-US DPF"], f"appcues privacy DPF self-cert files: {kept} {why}")
    check(by_pub["appcues"].get("found") is True, "appcues Official page is on file")
    check(
        by_pub["appcues"].get("trust_url") == "https://trust.appcues.com",
        "appcues Official page stays the existing portal",
    )
    check(
        {"SOC 2 Type II", "EU-US DPF"} <= set(by_pub["appcues"].get("certs") or []),
        f"appcues first-party holds {by_pub['appcues'].get('certs')}",
    )
    check(by_pub["appcues"].get("founded_year") in (None, 0, False), "appcues years stay open")
    check((by_pub["appcues"].get("file") or {}).get("page") == 20, "appcues Official page prints")
    check((by_pub["appcues"].get("file") or {}).get("marks") == 20, "appcues marks print")
    check((by_pub["appcues"].get("file") or {}).get("years") in (0, False, None), "appcues years stay open")
    ac_html = (ROOT / "site" / "c" / "appcues.html").read_text(encoding="utf-8")
    check("<h1>Appcues</h1>" in ac_html, "appcues dossier is its own file")
    check("https://trust.appcues.com" in ac_html, "appcues dossier cites Official page")
    check("SOC 2 Type II" in ac_html, "appcues dossier prints SOC 2 Type II")
    check("EU-US DPF" in ac_html, "appcues dossier prints EU-US DPF")
    # Rollbar first-party security docs. Type I superseded. ISO "chosen to
    # become compliant" and HIPAA Compliant SaaS stay open.
    check(by_pub["rollbar"].get("found") is True, "rollbar Official page is on file")
    check(
        by_pub["rollbar"].get("trust_url") == "https://rollbar.com/security",
        "rollbar Official page stays first-party /security",
    )
    check(
        {"SOC 2 Type II", "SOC 3"} <= set(by_pub["rollbar"].get("certs") or []),
        f"rollbar first-party holds {by_pub['rollbar'].get('certs')}",
    )
    check("SOC 2 Type I" not in (by_pub["rollbar"].get("certs") or []), "rollbar Type I superseded")
    check("ISO 27001" not in (by_pub["rollbar"].get("certs") or []), "rollbar ISO pursuing stays open")
    check("HIPAA" not in (by_pub["rollbar"].get("certs") or []), "rollbar HIPAA Compliant SaaS stays open")
    check((by_pub["rollbar"].get("file") or {}).get("page") == 20, "rollbar Official page prints")
    check((by_pub["rollbar"].get("file") or {}).get("marks") == 20, "rollbar marks print")
    rb_html = (ROOT / "site" / "c" / "rollbar.html").read_text(encoding="utf-8")
    check("<h1>Rollbar, Inc</h1>" in rb_html, "rollbar dossier is its own file")
    check("https://rollbar.com/security" in rb_html, "rollbar dossier cites Official page")
    check("SOC 2 Type II" in rb_html, "rollbar dossier prints SOC 2 Type II")
    check("SOC 3" in rb_html, "rollbar dossier prints SOC 3")
    check("ISO 27001" not in rb_html, "rollbar dossier does not print pursuing ISO 27001")
    # Liveblocks first-party /security. SOC 2 Type II only. HIPAA add-on open.
    # Official page stays the existing SecureFrame portal.
    check(by_pub["liveblocks"].get("found") is True, "liveblocks Official page is on file")
    check(
        by_pub["liveblocks"].get("trust_url") == "https://liveblocks.secureframetrust.com",
        "liveblocks Official page stays the existing portal",
    )
    check((by_pub["liveblocks"].get("certs") or []) == ["SOC 2 Type II"], f"liveblocks certs {by_pub['liveblocks'].get('certs')}")
    check("HIPAA" not in (by_pub["liveblocks"].get("certs") or []), "liveblocks HIPAA add-on stays open")
    check((by_pub["liveblocks"].get("file") or {}).get("page") == 20, "liveblocks Official page prints")
    check((by_pub["liveblocks"].get("file") or {}).get("marks") == 20, "liveblocks marks print")
    lb_html = (ROOT / "site" / "c" / "liveblocks.html").read_text(encoding="utf-8")
    check("<h1>Liveblocks</h1>" in lb_html, "liveblocks dossier is its own file")
    check("https://liveblocks.secureframetrust.com" in lb_html, "liveblocks dossier cites Official page")
    check("SOC 2 Type II" in lb_html, "liveblocks dossier prints SOC 2 Type II")
    check("HIPAA" not in lb_html, "liveblocks dossier does not print HIPAA add-on")
    # This cut: first-party Completeness fills on already-on-register named processors.
    # MessageBird DPA ISO hold + privacy DPF self-cert. Official page stays the portal.
    kept, why = hold_marks(
        ["ISO 27001"],
        "We are ISO 27001 certified, the globally recognised information security "
        "standards for Information Security Management Systems (ISMS).",
        "dpa",
    )
    check(kept == ["ISO 27001"], f"messagebird DPA ISO 27001 certified files: {kept} {why}")
    kept, why = hold_marks(
        ["EU-US DPF"],
        "Bird.com Inc. (\"Bird USA\") has certified to the U.S. Department of Commerce "
        "that it adheres to the EU-U.S. Data Privacy Framework Principles.",
        "privacy",
    )
    check(kept == ["EU-US DPF"], f"messagebird privacy DPF self-cert files: {kept} {why}")
    check(by_pub["messagebird"].get("found") is True, "messagebird Official page is on file")
    check(
        by_pub["messagebird"].get("trust_url") == "https://messagebird.com/trust",
        "messagebird Official page stays the existing portal",
    )
    check(
        {"ISO 27001", "EU-US DPF"} <= set(by_pub["messagebird"].get("certs") or []),
        f"messagebird first-party holds {by_pub['messagebird'].get('certs')}",
    )
    check("HIPAA" not in (by_pub["messagebird"].get("certs") or []), "messagebird HIPAA stays open")
    check("SOC 2 Type II" not in (by_pub["messagebird"].get("certs") or []), "messagebird privacy including-SOC stays open")
    check(by_pub["messagebird"].get("founded_year") == 2011, "messagebird years stay")
    check((by_pub["messagebird"].get("file") or {}).get("page") == 20, "messagebird Official page prints")
    check((by_pub["messagebird"].get("file") or {}).get("marks") == 20, "messagebird marks print")
    check((by_pub["messagebird"].get("file") or {}).get("years") == 20, "messagebird years stay")
    mb_html = (ROOT / "site" / "c" / "messagebird.html").read_text(encoding="utf-8")
    check("<h1>MessageBird</h1>" in mb_html, "messagebird dossier is its own file")
    check("https://messagebird.com/trust" in mb_html, "messagebird dossier cites Official page")
    check("ISO 27001" in mb_html, "messagebird dossier prints ISO 27001")
    check("EU-US DPF" in mb_html, "messagebird dossier prints EU-US DPF")
    # Qualified DPA: maintain SOC 2 Type II. HIPAA is a Sensitive Data definition.
    kept, why = hold_marks(
        ["SOC 2 Type II"],
        "Qualified agrees that it will maintain a SOC2/Type II certification "
        "with respect to its Security Measures.",
        "dpa",
    )
    check(kept == ["SOC 2 Type II"], f"qualified DPA Type II files: {kept} {why}")
    check(by_pub["qualified-com"].get("found") is True, "qualified Official page is on file")
    check(
        by_pub["qualified-com"].get("trust_url") == "https://trust.qualified.com",
        "qualified Official page stays the existing portal",
    )
    check((by_pub["qualified-com"].get("certs") or []) == ["SOC 2 Type II"], f"qualified certs {by_pub['qualified-com'].get('certs')}")
    check("HIPAA" not in (by_pub["qualified-com"].get("certs") or []), "qualified HIPAA definition stays open")
    check(by_pub["qualified-com"].get("founded_year") in (None, 0, False), "qualified years stay open")
    check((by_pub["qualified-com"].get("file") or {}).get("page") == 20, "qualified Official page prints")
    check((by_pub["qualified-com"].get("file") or {}).get("marks") == 20, "qualified marks print")
    check((by_pub["qualified-com"].get("file") or {}).get("years") in (0, False, None), "qualified years stay open")
    q_html = (ROOT / "site" / "c" / "qualified-com.html").read_text(encoding="utf-8")
    check("<h1>Qualified</h1>" in q_html, "qualified dossier is its own file")
    check("https://trust.qualified.com" in q_html, "qualified dossier cites Official page")
    check("SOC 2 Type II" in q_html, "qualified dossier prints SOC 2 Type II")
    check("HIPAA" not in q_html, "qualified dossier does not print HIPAA definition")
    # OpenRouter DPA Schedule 2 lists "SOC 2 Type II control framework" as a
    # security-control bullet, not a certification. Same class as MaxMind
    # "based on the standard." Marks stay open. Official page stays /security.
    check(by_pub["openrouter"].get("found") is True, "openrouter Official page is on file")
    check(
        by_pub["openrouter"].get("trust_url") == "https://openrouter.ai/security",
        "openrouter Official page stays first-party /security",
    )
    check(not (by_pub["openrouter"].get("certs") or []), f"openrouter control-framework stays open {by_pub['openrouter'].get('certs')}")
    check("SOC 2 Type II" not in (by_pub["openrouter"].get("certs") or []), "openrouter Type II control framework stays open")
    check(by_pub["openrouter"].get("founded_year") in (None, 0, False), "openrouter years stay open")
    check((by_pub["openrouter"].get("file") or {}).get("page") == 20, "openrouter Official page prints")
    check((by_pub["openrouter"].get("file") or {}).get("marks") in (0, 10, False, None), "openrouter marks stay open")
    check((by_pub["openrouter"].get("file") or {}).get("dpa") == 20, "openrouter DPA stays")
    or_html = (ROOT / "site" / "c" / "openrouter.html").read_text(encoding="utf-8")
    check("<h1>OpenRouter</h1>" in or_html, "openrouter dossier is its own file")
    check("https://openrouter.ai/security" in or_html, "openrouter dossier cites Official page")
    check("SOC 2 Type II" not in or_html, "openrouter dossier does not print control-framework Type II")
    check("Marks cited from public HTML" not in or_html, "openrouter clerk does not cite a dropped mark")
    # Apollo DPA: datacenter SOC 2 stays open. DPF participate-and-certify files.
    kept, why = hold_marks(
        ["EU-US DPF"],
        "At the time of the execution of the Agreement, Apollo participates in and "
        "certifies compliance with the Data Privacy Framework. The Data Privacy "
        "Framework self-certification programs are operated by the U.S. Department of Commerce.",
        "dpa",
    )
    check(kept == ["EU-US DPF"], f"apollo DPA DPF certify files: {kept} {why}")
    check(by_pub["apollo-io"].get("found") is True, "apollo Official page is on file")
    check(
        by_pub["apollo-io"].get("trust_url") == "https://trust.apollo.io",
        "apollo Official page stays the existing portal",
    )
    check((by_pub["apollo-io"].get("certs") or []) == ["EU-US DPF"], f"apollo certs {by_pub['apollo-io'].get('certs')}")
    check("SOC 2 Type II" not in (by_pub["apollo-io"].get("certs") or []), "apollo datacenter SOC 2 stays open")
    check(by_pub["apollo-io"].get("founded_year") in (None, 0, False), "apollo years stay open")
    check((by_pub["apollo-io"].get("file") or {}).get("page") == 20, "apollo Official page prints")
    check((by_pub["apollo-io"].get("file") or {}).get("marks") == 20, "apollo marks print")
    ap_html = (ROOT / "site" / "c" / "apollo-io.html").read_text(encoding="utf-8")
    check("<h1>Apollo.io</h1>" in ap_html, "apollo dossier is its own file")
    check("https://trust.apollo.io" in ap_html, "apollo dossier cites Official page")
    check("EU-US DPF" in ap_html, "apollo dossier prints EU-US DPF")
    check("SOC 2" not in ap_html, "apollo dossier does not print datacenter SOC 2")
    # MaestroQA privacy DPF self-cert. Official page stays the portal.
    kept, why = hold_marks(
        ["EU-US DPF"],
        "Maestro has certified to the U.S. Department of Commerce that it adheres "
        "to the EU-U.S. Data Privacy Framework Principles.",
        "privacy",
    )
    check(kept == ["EU-US DPF"], f"maestroqa privacy DPF self-cert files: {kept} {why}")
    check(by_pub["maestroqa"].get("found") is True, "maestroqa Official page is on file")
    check(
        by_pub["maestroqa"].get("trust_url") == "https://trust.maestroqa.com",
        "maestroqa Official page stays the existing portal",
    )
    check((by_pub["maestroqa"].get("certs") or []) == ["EU-US DPF"], f"maestroqa certs {by_pub['maestroqa'].get('certs')}")
    check(by_pub["maestroqa"].get("founded_year") == 2013, "maestroqa years stay")
    check((by_pub["maestroqa"].get("file") or {}).get("page") == 20, "maestroqa Official page prints")
    check((by_pub["maestroqa"].get("file") or {}).get("marks") == 20, "maestroqa marks print")
    check((by_pub["maestroqa"].get("file") or {}).get("years") == 20, "maestroqa years stay")
    mq_html = (ROOT / "site" / "c" / "maestroqa.html").read_text(encoding="utf-8")
    check("<h1>MaestroQA</h1>" in mq_html, "maestroqa dossier is its own file")
    check("https://trust.maestroqa.com" in mq_html, "maestroqa dossier cites Official page")
    check("EU-US DPF" in mq_html, "maestroqa dossier prints EU-US DPF")
    # Validity privacy DPF self-cert. Official page stays the portal. Years stay open.
    kept, why = hold_marks(
        ["EU-US DPF"],
        "Validity has certified to the U.S. Department of Commerce that it adheres "
        "to the EU-U.S. Data Privacy Framework Principles.",
        "privacy",
    )
    check(kept == ["EU-US DPF"], f"validity privacy DPF self-cert files: {kept} {why}")
    check(by_pub["validity"].get("found") is True, "validity Official page is on file")
    check(
        by_pub["validity"].get("trust_url") == "https://trust.validity.com",
        "validity Official page stays the existing portal",
    )
    check((by_pub["validity"].get("certs") or []) == ["EU-US DPF"], f"validity certs {by_pub['validity'].get('certs')}")
    check(by_pub["validity"].get("founded_year") in (None, 0, False), "validity years stay open")
    check((by_pub["validity"].get("file") or {}).get("page") == 20, "validity Official page prints")
    check((by_pub["validity"].get("file") or {}).get("marks") == 20, "validity marks print")
    va_html = (ROOT / "site" / "c" / "validity.html").read_text(encoding="utf-8")
    check("<h1>Validity</h1>" in va_html, "validity dossier is its own file")
    check("https://trust.validity.com" in va_html, "validity dossier cites Official page")
    check("EU-US DPF" in va_html, "validity dossier prints EU-US DPF")

    check(by_pub["authzed"].get("found") is True, "authzed Official page is on file")
    check(
        by_pub["authzed"].get("trust_url") == "https://security.authzed.com",
        "authzed Official page stays the existing portal",
    )
    check((by_pub["authzed"].get("certs") or []) == [], f"authzed certs stay empty {by_pub['authzed'].get('certs')}")
    check("SOC 2" not in (by_pub["authzed"].get("certs") or []), "authzed Secure First SOC2 chip stays open")
    check("GDPR" not in (by_pub["authzed"].get("certs") or []), "authzed GDPR chip stays open")
    check("CCPA" not in (by_pub["authzed"].get("certs") or []), "authzed CCPA chip stays open")
    check((by_pub["authzed"].get("file") or {}).get("page") == 20, "authzed Official page prints")
    check((by_pub["authzed"].get("file") or {}).get("marks") == 10, "authzed marks stay dotted — page on file, none extracted")
    check((by_pub["authzed"].get("file") or {}).get("dpa") in (0, False, None), "authzed DPA stays open")
    check((by_pub["authzed"].get("file") or {}).get("years") in (0, False, None), "authzed years stay open")
    az_html = (ROOT / "site" / "c" / "authzed.html").read_text(encoding="utf-8")
    check("<h1>Authzed</h1>" in az_html, "authzed dossier is its own file")
    check("https://security.authzed.com" in az_html, "authzed dossier cites Official page")
    check("SOC 2" not in az_html, "authzed dossier does not print SOC 2 chip")
    check("SOC2" not in az_html, "authzed dossier does not print SOC2 chip")
    check("GDPR" not in az_html, "authzed dossier does not print GDPR chip")
    check("CCPA" not in az_html, "authzed dossier does not print CCPA chip")

    check("HIPAA" not in (by_pub["onesignal"].get("certs") or []), "onesignal HIPAA-compliant BAA stays open")
    check(by_pub["onesignal"].get("found") is False, "onesignal Official page stays open")
    check(not by_pub["onesignal"].get("trust_url"), "onesignal privacy is not Official page")

    # Preferred C0 left open: product cybersecurity / login dashboard.
    check(by_pub["legalinc-com"].get("found") is False, "legalinc dashboard is not Official page")
    check(not by_pub["legalinc-com"].get("trust_url"), "legalinc has no invented Official page")
    check((by_pub["filestack"].get("file") or {}).get("page") in (0, False, None), "filestack features is not Official page")
    kept, why = hold_marks(
        ["HIPAA"],
        "HIPAA compliance assistance Customers that must safeguard protected health "
        "information (PHI) can enter into a Business Associate Agreement (BAA) with "
        "Branch for HIPAA-eligible solutions. Advanced Compliance provides enhanced "
        "security configurations to support HIPAA-aligned handling.",
        "security",
    )
    check(kept == [] and why in {"regulation-only", "no-named-marks"}, f"branch HIPAA-eligible BAA stays open: {kept} {why}")
    for slug in ("canonical", "beck-technology", "world-labs", "synap", "lime-technologies", "inmobi"):
        html = (ROOT / "site" / "c" / f"{slug}.html").read_text(encoding="utf-8")
        check("Official page" in html, f"{slug} still prints Official page")
        visible = re.sub(r'https?://\S+', "", html)
        visible = re.sub(r'href="[^"]+"', "", visible).lower()
        check(
            "safebase" not in visible
            and "conveyor" not in visible
            and "vanta" not in visible
            and "securitypal" not in visible
            and "sprinto" not in visible,
            f"{slug} named a portal vendor",
        )

    print(
        "ok",
        "filed",
        len(report.get("marks_filed") or []),
        "open",
        len(report.get("stayed_open") or []),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
