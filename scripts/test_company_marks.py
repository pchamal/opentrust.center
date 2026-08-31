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
