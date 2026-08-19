# Extra paragraphs appended to elaborate texts that were under 180 words.
# Clerk voice. No marketing. Facts only.

EXTRA = {}

EXTRA["iso-27017"] = (
    " Certification bodies differ in how they print the extension: some issue a combined 27001/27017 certificate, "
    "some list 27017 only in the audit report. Ask for the page that names 27017. Shared-responsibility tables in "
    "the SoA are the useful part for a buyer; if the provider marked customer-owned controls as 'not applicable' "
    "without saying they are yours, the scope is sloppy. 27017 does not cover physical data-center tours, "
    "does not replace a CSA STAR Level 2 audit, and does not speak to model risk if the cloud service is an AI API. "
    "Surveillance audits should keep 27017 in scope each year, not only at recertification. If the certificate "
    "expired, the extension expired with it."
)

EXTRA["iso-27018"] = (
    " Read whether the certified role is processor only. A company that also decides purposes for its own marketing "
    "database is a controller for that data and 27018 does not bless that use. Deletion and return commitments in "
    "27018 still have to appear in the DPA you sign; the certificate is not the contract. Sub-processors are only "
    "in scope if the SoA and certificate say so. 27018 is silent on U.S. state consumer statutes and on sector laws "
    "such as HIPAA. Do not let a 27018 logo stand in for a BAA, an SCC module, or a transfer impact assessment. "
    "If the edition on the paper is older than 2019, ask why. Pair with 27701 when you need a full PIMS."
)

EXTRA["iso-27701"] = (
    " The 2019 edition's controller and processor annexes (A/B and the 27002 extensions) are what most audit reports "
    "still cite. The 2025 standalone edition changes the dependency story; until your certification body prints "
    "2025 on the certificate, you are looking at 2019. A PIMS certificate that names only 'the organization' and "
    "not the product you buy is easy to over-read. Ask which processing activities were in scope, whether employees "
    "and customers were both covered, and whether subprocessors were included. 27701 does not approve BCRs and does "
    "not replace a DPO appointment where the law requires one. Treat it as management-system evidence next to the "
    "legal tools, not as a substitute for them."
)

EXTRA["iso-9001"] = (
    " Procurement teams like 9001 because it is familiar from manufacturing tenders. That is also why it shows up "
    "on software trust pages that have no security certificate yet. The standard says almost nothing about "
    "access control, encryption, logging, or vulnerability management. A nonconformity on document control is not "
    "a security finding. If the same certification body issued 9001 and 27001, still read two scopes; they are "
    "often different legal entities. The 2015 edition remains the current certifiable edition as of this register. "
    "A company can lose 9001 and still have a fine ISMS, and the reverse. Do not let 9001 move a security score "
    "more than a point or two. If you are buying a medical device, stop reading this row and open ISO 13485."
)

EXTRA["iso-22301"] = (
    " A BCMS certificate should rest on a business-impact analysis that names recovery objectives. Those numbers "
    "belong in the contract, not only in the ISMS. Ask whether the last exercise was a tabletop or a full restore, "
    "which product was restored, and whether the restore met the documented RTO. Cloud customers often discover "
    "that the certified BCMS covers the provider's office network and not the multi-tenant production service. "
    "That gap is common and is why scope language matters. 22301 does not prove ransomware readiness by itself. "
    "It does not replace cyber-insurance questionnaires or DORA ICT-testing duties for financial entities. If the "
    "vendor also has SOC 2 availability, read both; they test different claims. Expired 22301 is just a plan on a shelf."
)

EXTRA["iso-20000-1"] = (
    " Service-management certificates are still written into some government and outsourcing frameworks, especially "
    "where the buyer grew up on ITIL. The useful questions are: which services, which service desk, which change "
    "advisory board, and whether production incidents on your product would even enter that SMS. A 20000-1 "
    "certificate on a professional-services unit does not cover the SaaS. It does not attest vulnerability SLAs "
    "or encryption. Overlap with ISO 27001 is organizational, not technical. If a French hosting deal mentions "
    "both 20000-1 and HDS, HDS is the legal one for health data; 20000-1 is supporting. Ask for the certificate "
    "scope page. A pink ITIL training card on an employee's wall is not this certificate."
)

EXTRA["iso-13485"] = (
    " Software as a medical device (SaMD) organizations use 13485 alongside IEC 62304 and, in the EU, MDR/IVDR "
    "conformity. A wellness or workflow SaaS that is not a device should not hide behind 13485. Conversely, a "
    "device maker that holds 13485 and no 27001 still owes you a security story if the device phones home. "
    "MDSAP and notified-body certificates can sit on top of 13485; those are regulatory, not this row. Read the "
    "device list on the certificate. A 13485 on 'design and development of software' is not a hospital security "
    "review. Typical buyer mistake is treating 13485 as HIPAA. It is not. Keep it in the catalog because health-tech "
    "trust pages list it in the same badge row as SOC 2, and a clerk has to un-mix them."
)

EXTRA["pci-dss"] = (
    " Version 4.0 introduced new requirements that became mandatory on a published timetable; 4.0.1 is a limited "
    "revision. If the AOC still says 3.2.1 after retirement, it is stale. Service-provider AOCs are not merchant "
    "AOCs. A payment facilitator, a wallet, and a checkout iframe have different scope stories. Ask whether the "
    "company stores account data or is a redirect/iframe model that shrinks scope. Compensating controls should "
    "be read, not skipped. Quarterly ASV scans and penetration tests are part of the standard; a one-year-old "
    "AOC does not prove last quarter's scan passed. PCI DSS does not equal tokenization quality. It does not "
    "cover account-data in a data-science lake if that lake was carved out. Get the AOC. Decline a logo."
)

EXTRA["pci-3ds"] = (
    " EMV 3-D Secure is a protocol. PCI 3DS is the security standard for the parties that operate its core "
    "components. Issuers, directory-server operators, and 3DS-server vendors are the usual assessed entities. "
    "A merchant that 'turned on 3DS' through an acquirer has not been assessed to PCI 3DS. Confusion with PCI DSS "
    "requirement 3 and with 3DS as a fraud-reduction feature is common on trust pages. Ask for the component "
    "type, the assessor, and the AOC date. If the company is only a merchant, this row should not appear. If the "
    "company sells a 3DS server, the listing should match the product version you would run. This is payments "
    "infrastructure assurance, scored below DSS because fewer buyers need it, but it is a real PCI SSC program."
)

EXTRA["pci-ssf"] = (
    " PA-DSS listings sunset on a PCI SSC timetable; do not accept a PA-DSS letter as current for new software. "
    "Secure Software validation is product-version specific — a new major release is a new listing. Secure SLC "
    "qualification is about the vendor's lifecycle and can allow certain delta self-attestations for already "
    "listed software; it is not a blanket license to skip product validation. Read the PCI SSC list, not a PDF "
    "the vendor designed. SSF assessors are not the same roster as QSAs, though some firms are both. SSF does "
    "not replace DSS for a service provider that stores PAN. It does not speak to ISO 42001 or application "
    "security of a non-payment product in the same company. Two standards, two listings, two questions."
)
