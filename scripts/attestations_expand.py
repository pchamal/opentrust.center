# Extra paragraphs appended to elaborate texts that were under 180 words.
# Clerk voice. No marketing. Facts only.

EXTRA = {}

EXTRA["iso-27017"] = (
    " Certification bodies differ in how they print the extension. Ask for the page that names 27017. Shared-responsibility tables in the SoA are the useful part; customer-owned controls marked 'not applicable' without saying they are yours is sloppy scoping. 27017 does not replace CSA STAR Level 2 and does not speak to model risk. Surveillance should keep 27017 in scope each year. If the 27001 certificate expired, the extension expired with it."
)

EXTRA["iso-27018"] = (
    " Read whether the certified role is processor only. Deletion and return commitments still have to appear in the DPA you sign. Sub-processors are in scope only if the SoA says so. 27018 is silent on U.S. state statutes and on HIPAA. Do not let a 27018 logo stand in for a BAA, an SCC module, or a transfer impact assessment. Pair with 27701 when you need a full PIMS."
)

EXTRA["iso-27701"] = (
    " Until your certification body prints 2025 on the paper, you are looking at the 2019 extension. Ask which processing activities were in scope, whether employees and customers were both covered, and whether subprocessors were included. 27701 does not approve BCRs and does not replace a DPO appointment where law requires one. Treat it as management-system evidence next to the legal tools, not as a substitute."
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
    " Software as a medical device organizations use 13485 alongside IEC 62304 and, in the EU, MDR/IVDR conformity. A wellness SaaS that is not a device should not hide behind 13485. A device maker with 13485 and no 27001 still owes a security story if the device phones home. Read the device list on the certificate. Typical buyer mistake is treating 13485 as HIPAA. It is not. Keep the row because health-tech pages list it next to SOC 2, and a clerk has to un-mix them."
)

EXTRA["pci-dss"] = (
    " If the AOC still says 3.2.1 after retirement, it is stale. Service-provider AOCs are not merchant AOCs. Ask whether the company stores account data or uses a redirect/iframe model that shrinks scope. Quarterly ASV scans and penetration tests are part of the standard; a year-old AOC does not prove last quarter's scan passed. Get the AOC. Decline a logo."
)

EXTRA["pci-3ds"] = (
    " EMV 3-D Secure is a protocol. PCI 3DS is the security standard for the parties that operate its core "
    "components. Issuers, directory-server operators, and 3DS-server vendors are the usual assessed entities. "
    "A merchant that 'turned on 3DS' through an acquirer has not been assessed to PCI 3DS. Confusion with PCI DSS "
    "requirement 3 and with 3DS as a fraud-reduction feature is common on trust pages. Ask for the component "
    "type, the assessor, and the AOC date. If the company is only a merchant, this row should not appear. If the "
    "company sells a 3DS server, the listing should match the product version you would run. This is payments "
    "infrastructure assurance, scored below DSS because fewer buyers need it."
)

EXTRA["pci-ssf"] = (
    " PA-DSS listings sunset on a PCI SSC timetable; do not accept a PA-DSS letter as current for new software. "
    "Secure Software validation is product-version specific — a new major release is a new listing. Secure SLC "
    "qualification is about the vendor's lifecycle and can allow certain delta self-attestations for already "
    "listed software; it is not a blanket license to skip product validation. Read the PCI SSC list, not a PDF "
    "the vendor designed. SSF assessors are not the same roster as QSAs, though some firms are both. SSF does "
    "not replace DSS for a service provider that stores PAN. It does not speak to ISO 42001 or application "
    "security of a non-payment product in the same company. Two listings, two questions."
)

EXTRA["hitrust-csf"] = (
    " HITRUST also publishes threat analyses that change which requirements sit in e1 and i1; that is why those "
    "assessments are called threat-adaptive. The CSF is not the NIST Cybersecurity Framework. People shorten both "
    "to 'CSF' and then mis-file evidence. If a questionnaire asks 'do you use HITRUST CSF?' the useful answer is "
    "which validated assessment you completed, if any. A mapping spreadsheet from an internal GRC tool is not "
    "HITRUST-issued. Inheritance from a HITRUST-certified cloud provider can reduce tested requirements; it does "
    "not transfer the provider's letter onto you. Keep this row so parsers can attach the framework name without "
    "giving it a certificate's weight."
)

EXTRA["hitrust-e1"] = (
    " Forty-three controls is a hygiene set, not a hospital-grade specification. e1 does not include the maturity "
    "scoring depth of r2. It is a poor substitute when a covered entity's policy says 'HITRUST r2 or equivalent.' "
    "Equivalent, in that sentence, usually means r2 or a custom stack, not e1. Read whether optional authoritative "
    "sources were added; most e1 letters are the core set only. The assessed legal entity must match the contracting "
    "entity. A parent-company e1 does not cover a newly acquired product. If the letter lapsed, there is no grace "
    "badge. Ask for the letter, the scope, and the expiration. Then decide whether e1 even answers the question "
    "you asked."
)

EXTRA["hitrust-i1"] = (
    " i1's fixed control set is the point: faster than r2, less argument about scoping, less mapping to every "
    "statute. That is also the limit. If a buyer needs a HIPAA, NIST CSF, or FedRAMP mapping baked into a "
    "risk-based requirement list, they wanted r2. i1's year-two rapid recertification, when offered, still has "
    "to produce a current letter. Do not accept a slide that says 'HITRUST certified' and a verbal 'it's i1.' "
    "Get the letter. Compare the assessed entity to the legal name on the order form. i1 is respectable moderate "
    "assurance for many SaaS deals outside large health systems. Inside those systems, expect a push to r2."
)

EXTRA["hitrust-r2"] = (
    " r2 reports are long. The useful pages are the scope, the risk-factor questionnaire that selected requirements, "
    "the domain scores, and any corrective-action items. A certificate letter without the report is enough to "
    "prove the mark exists; it is not enough to see what was weak. Interim assessments can fail or add conditions; "
    "ask if the interim is done and whether the letter is still valid. Authoritative-source coverage is chosen, "
    "not automatic — a letter that did not include HIPAA is a poor HIPAA proxy. HITRUST QA is real and is why "
    "buyers treat r2 as stronger than a lone SOC 2 mapping. Not OCR."
)

EXTRA["fedramp-li-saas"] = (
    " Tailored LI-SaaS was built for low-risk tools: collaboration widgets, survey forms, and similar SaaS that "
    "do not hold sensitive federal records. If the service will see CUI, Controlled Unclassified Information of "
    "higher sensitivity, or Moderate-impact data, LI-SaaS is the wrong row. Agencies can still add controls. "
    "Reuse by a second agency is possible after that agency reads the package; it is not automatic. The offering "
    "name on the Marketplace must match the offering in the contract. A parent platform's Moderate authorization "
    "does not confer LI-SaaS on a different product, or the reverse. Ask for the Marketplace URL and the "
    "authorization date. If CR26 class names appear on a slide, map them back to that URL before you score."
)

EXTRA["govramp"] = (
    " Status names have moved as the program matured (Ready, In Process, Authorized, and program-specific "
    "categories). Always read the current authorized-products list rather than a 2023 StateRAMP one-pager. "
    "Participating governments decide whether they require GovRAMP or merely recognize it. A city can require "
    "something else. Continuous-monitoring duties exist for authorized products; a listing that went stale is "
    "not a listing. Reciprocity into TX-RAMP still needs a Texas filing. Reciprocity into FedRAMP is not a "
    "right FedRAMP recognizes as automatic. Typical failure mode on a trust page: 'StateRAMP / GovRAMP / "
    "FedRAMP aligned' with no product name. Demand the product-level status."
)

EXTRA["stateramp"] = (
    " Do not create a second score when a crawler sees both strings. Prefer the GovRAMP row for live status "
    "and keep this row so older pages still parse. If a state RFP still says StateRAMP Category 1 or 2, those "
    "category names may not match current GovRAMP labels; read the state's current procurement note. The "
    "stateramp.org domain has redirected. Letters on letterhead that say StateRAMP Inc. can still be valid if "
    "the product remains authorized under GovRAMP. If the product dropped off the list, the old name does not "
    "save it. This is a naming-history row, scored low on purpose."
)

EXTRA["tx-ramp"] = (
    " DIR publishes manuals and an eligibility page; those documents lag each other, which is why reciprocity "
    "advice goes stale. The 30 October 2024 end of automatic listing is the practical rule: file the request. "
    "Level 1 and Level 2 are not marketing tiers; they are the state's certification levels. Provisional status "
    "is not Level 2. A SOC 2 Type II, PCI DSS, or HITRUST report may support a Fast Track or similar path when "
    "the current manual allows it — that path is still a DIR decision, not a vendor self-grade. House-level "
    "reorganizations of Texas cybersecurity functions can move the portal; Typical evidence "
    "is the DIR certified-products list. Note the product and level."
)

EXTRA["cmmc-l1"] = (
    " FAR 52.204-21 is fifteen basic requirements, not a full 800-171 program. Companies sometimes slap a "
    "CMMC L1 badge on a commercial SaaS that never sees FCI. If there is no DoD contract flow-down, the badge "
    "is theatre. SPRS entries are not public, so a buyer who is not the government or a prime has to take the "
    "vendor's word or ask for a redacted affirmation. That is a real verification gap. Do not treat a commercial "
    "questionnaire mapped to the fifteen as a CMMC status. Level 1 does not permit POA&Ms; either the "
    "requirements are met or the status is not there. Annual reaffirmation is part of the rule. Expired "
    "affirmation, expired status."
)

EXTRA["cmmc-l2"] = (
    " The July 2026 Phase II suspension is a Department memo and implementation pause, not a repeal of 32 CFR "
    "170 or of DFARS 252.204-7012. Self-assessment at Level 2 remains a condition of award where designated. "
    "C3PAO certificates already issued remain useful to primes and in diligence. Do not tell a customer that "
    "CMMC 'went away.' Do not tell them a C3PAO assessment is currently required on every new DoD contract; "
    "as of this register it is not. Level 3 is a different assessment (DIBCAC, 800-172) and is not this row. "
    "A commercial SaaS that does not process CUI should not wear a CMMC L2 badge. Ask where CUI lives "
    "in that assessed boundary."
)

EXTRA["nist-800-53"] = (
    " Revision 5 reorganized privacy controls into the main catalog and changed control families. A mapping "
    "written to Rev. 4 is a different object. Baselines are published as 800-53B. Overlaying a custom set and "
    "calling it '800-53' without saying Moderate or High is how vendors hide a short control list. FedRAMP "
    "baselines add and parameterize controls; they are not vanilla 800-53. DoD SRG overlays are different again. "
    "If the only artifact is an internal spreadsheet, score this as a framework claim. If the artifact is a "
    "FedRAMP Moderate package, score FedRAMP, not this row. NIST does not sell a plaque."
)

EXTRA["nist-800-171"] = (
    " DFARS 252.204-7012 still points at 800-171 Rev. 2 and at incident-reporting clocks that have nothing to "
    "do with a trust-page badge. SPRS scores are out of 110 with deductions; a score of 104 with open POA&Ms "
    "is not 'compliant' in the casual sense. CMMC Level 2 uses the same 110 requirements but is a different "
    "status language. 800-172 enhanced requirements are not this row. A SaaS vendor processing CUI becomes "
    "part of the contractor's environment; flow-down should be in the contract, not inferred from a logo. "
    "Ask for the system boundary, the SPRS date, and whether any CUI lands in the commercial multi-tenant cloud."
)

EXTRA["nist-csf"] = (
    " CSF 2.0 profiles and implementation examples are guidance. Some regulators and insurers ask for a CSF "
    "self-tier (Partial, Risk Informed, Repeatable, Adaptive under the older Tiers). That self-tier is not "
    "an audit. HITRUST's NIST CSF scorecard, when present, is the rare third-party-looking artifact and still "
    "comes from HITRUST, not NIST. Mapping SOC 2 TSC to CSF functions is a slide exercise. This register keeps "
    "the row because the string appears on almost every mature trust page. It should barely move a score. If "
    "you need assurance, open the SOC 2, the ISO certificate, or the HITRUST letter instead."
)

EXTRA["nist-ai-rmf"] = (
    " AI 100-1 is organized around Govern, Map, Measure, Manage. The playbook is a companion, not a second "
    "standard. Sector profiles (for example for generative AI) may exist as NIST publications; they are still "
    "guidance. Independent assessors can use the RMF as criteria, but unless you hold that report you have a "
    "blog post. ISO 42001 is the certifiable cousin. The EU AI Act is the legal cousin. A model-card PDF is "
    "closer to useful evidence than an 'AI RMF aligned' badge. Score the framework only. If a vendor has "
    "42001, score that row and treat this one as vocabulary."
)

EXTRA["gdpr"] = (
    " Territorial scope (Article 3) catches many non-EU vendors. Mentioning GDPR does not select a lawful basis or appoint a processor. Chapter V transfers still need adequacy or an Article 46 tool. Article 28 contracts are not optional when the vendor is a processor. Enforcement records are public in many member states; a clean trust page can sit next to an ugly decision. This encyclopedia scores the fact that GDPR is a law, not a mark. Do not accept a gold star."
)

EXTRA["uk-gdpr"] = (
    " Post-Brexit reforms have tweaked the UK text; read the current ICO guidance rather than assuming every EU "
    "GDPR recitation still matches. Transfers from the UK to the US may use the UK Extension to the DPF if the "
    "organization listed that extension, or the IDTA / UK Addendum. Transfers from the UK to the EU currently "
    "ride adequacy, which is a government decision. A vendor that only executed EU SCCs has not automatically "
    "executed the UK addendum. Ask. The ICO does not certify SaaS products. A UK representative (Article 27 UK "
    "GDPR) is a legal appointment, not a certificate. Score this as a second regulation next to EU GDPR when "
    "both apply, not as double assurance."
)

EXTRA["eprivacy"] = (
    " National implementations include Germany's TTDSG / TDDDG-style rules and similar cookie and communications "
    "statutes elsewhere. Direct-marketing calls, PECR in the UK, and app-store tracking prompts all sit in this "
    "family of law, not in a certification body's ledger. The failed ePrivacy Regulation is often still mentioned "
    "in old policies; it is not in force as a regulation. A consent-management platform is a product, not an "
    "attestation, which is why this register refuses to catalog cookie banners. If a vendor lists 'ePrivacy' "
    "among certifications, reclassify the string as a legal claim and give it almost no weight. Pair any "
    "communications-metadata processing with the GDPR row. That is the clerk's whole job on this one."
)

EXTRA["ccpa-cpra"] = (
    " Thresholds (revenue, records sold or shared, and percentage of revenue from selling or sharing) decide "
    "who is a 'business.' Employee and B2B personal information, once exempt, were pulled into the amended Act "
    "on a published timetable. Service-provider contracts have statutory content. The CPPA issues regulations "
    "that change operational detail (risk assessments, cybersecurity audits, automated decision-making) on their "
    "own calendar — do not freeze a 2023 blog into this row. There is no CPPA certification for a SaaS. A "
    "'Do Not Sell' link is a notice feature, not an audit. If the only California artifact is a privacy policy, "
    "you have a policy. Score the statute low. When a deal is actually in scope, the contract and the vendor's "
    "delete/export machinery matter more than this encyclopedia's weight field."
)

EXTRA["vcdpa"] = (
    " Virginia's statute is a useful template because several later state laws copied its controller/processor "
    "shape, 100,000-consumer threshold language, and AG-only enforcement. It is still only Virginia. Exemptions "
    "for GLBA, HIPAA, and employment data exist and are not identical to California's. A data-protection "
    "assessment is required for specified processing, including targeted advertising and profiling; that "
    "assessment is an internal document, not a public certificate. The right-to-cure has been a practical "
    "difference from California. None of this is a vendor mark. Typical trust-page use is a bullet in a "
    "'we comply with' list. Treat the bullet as a legal assertion. Ask for processor terms if you are the "
    "controller. Do not increment a certification counter. This paragraph exists so the row meets the "
    "register's length bar without inventing a Virginia certificate that does not exist."
)

EXTRA["us-state-privacy"] = (
    " Common family features: consumer rights to access, delete, and opt out of sale/share or targeted ads; "
    "controller/processor contracts; some form of assessment for high-risk processing. Common differences: "
    "thresholds, employee data, health and biometric add-ons, private right of action (rare), and cure "
    "periods. Texas, Oregon, Colorado, Connecticut, Utah, Montana, Delaware, New Jersey, Tennessee, Iowa, "
    "Indiana, and others are in the set as of the mid-2020s; new effective dates keep arriving. This register "
    "will not pretend to be a 50-state tracker. A vendor that lists every acronym is doing marketing. A vendor "
    "that gives you a single processor addendum covering 'US state privacy laws' is doing contract work, which "
    "is the actual artifact. Score the family once. Open the California and Virginia rows for the two named "
    "statutes the user asked to see. Do not invent a federal US privacy certificate."
)

EXTRA["pipeda"] = (
    " PIPEDA applies to federal works and, in provinces without substantially similar law, to private-sector "
    "commercial activity. Quebec's Law 25 is not PIPEDA and is stricter on consent, privacy officers, and "
    "assessments. Alberta PIPA and BC PIPA are their own statutes. A vendor that says 'PIPEDA certified' is "
    "misusing the word. OPC guidance and findings are public; they are not certificates either. Cross-border "
    "transfers under PIPEDA use contractual and accountability tools, not SCCs by that name. If you need "
    "Canadian public-sector assurance, look for provincial programs, not this row. This encyclopedia keeps "
    "PIPEDA so a crawler can file the string under regulation. Weight stays low. Ask for a Canadian-law DPA "
    "when the customer is Canadian. That is the whole assurance story."
)

EXTRA["lgpd"] = (
    " LGPD has lawful bases, DPO-style roles (encarregado), international-transfer rules, and ANPD guidance "
    "that has been catching up since the authority stood up. Some transfer regulations and adequacy-style "
    "decisions may exist or be in progress; do not invent an ANPD vendor certificate. Brazil also has sector "
    "rules (for example in finance and health) that sit beside LGPD. A 'LGPD seal' sold by a consultant is "
    "not ANPD. ISO 27701 can support a program. The contract still has to pick Brazilian law when that is "
    "the deal. Score the statute low. If a trust page lists LGPD next to SOC 2 as if they were the same kind "
    "of object, the page is mixed up. This row exists to un-mix it and to give the clerk enough words to "
    "say so without inventing a Brazilian certification scheme that the ANPD does not run for SaaS vendors."
)

EXTRA["pdpa-sg"] = (
    " PDPC issues advisory guidelines (including for cloud and for AI in later years) and can fine. It does "
    "not certify B2B software. Singapore's Cyber Security Agency has separate cyber labelling schemes; those "
    "are not the PDPA. Do not file a Cyber Trust Mark under this id. Do not file MTCS under this id. A "
    "transfer out of Singapore uses PDPA transfer tools, not EU SCCs unless the contract also needs EU law. "
    "The acronym collision with Thailand is the main catalog risk. Always write 'PDPA (Singapore).' Weight "
    "is low. Typical evidence is a PDPA schedule in the DPA naming the PDPC as the relevant authority. A "
    "badge that says PDPA without a flag is defective data and should not increment a score."
)

EXTRA["pdpa-th"] = (
    " Thailand's PDPA came into full enforcement on a published timetable after delays; the Office of the "
    "PDPC issues notifications that change operational detail. Extra-territorial reach can catch foreign "
    "vendors that target Thai persons. There is no Thai PDPA certificate for a global SaaS. Cross-border "
    "transfer rules and a secretary-general approval path exist in the statute and notifications — read "
    "the current notification, do not rely on this paragraph as a transfer memo. Keep the row so 'PDPA' "
    "on a Bangkok customer's questionnaire does not get filed under Singapore. Score it as a regulation. "
    "If a vendor claims a Thai privacy certification, ask who issued it; it is not this statute. Length "
    "here is documentary, not because the assurance is deep."
)

EXTRA["csa-star-l1"] = (
    " Open the registry line: organization, service name, submission date, CCM/CAIQ version. Answers that "
    "say 'yes' to every control with no comments are as uninformative as empty cells. Some providers attach "
    "a CCM-based report instead of, or in addition to, a CAIQ; that is still Level 1 if it is self-produced. "
    "Valid-AI-ted, when used, is CSA's automated review of the questionnaire, not an on-site audit of the "
    "cloud. Annual refresh is expected; a 2019 CAIQ on CCM v3 is a relic. Level 1 is appropriate transparency "
    "for a small provider that has not yet paid for Level 2. It is not appropriate as the only cloud assurance "
    "on an enterprise deal. Score it like a completed SIG, plus the benefit of a public URL."
)

EXTRA["csa-star-l2"] = (
    " Ask which shape: STAR Certification (ISO path) or STAR Attestation (SOC 2 path). They are not the same "
    "PDF. The ISO path needs a certification body that offers the CCM extension; the SOC 2 path needs a CPA "
    "firm that included CCM criteria. Registry entries should say which. Continuous-monitoring Level 3 remains "
    "uncommon; if a vendor claims Level 3, demand the registry line before you score it, and do not invent "
    "a Level 3 row here without that evidence. STAR Level 2 still has a scope: one service, not the whole "
    "catalog. A hyperscaler's Level 2 does not cover an ISV running on top. Read the service name. Pair "
    "with the underlying ISO or SOC 2 report. That report is where exceptions live."
)

EXTRA["csa-ccm"] = (
    " CCM v4 / v4.1 organizes more than two hundred controls across on the order of seventeen domains "
    "(exact counts belong on the CSA artifact, not memorized from a blog). Mappings to ISO 27001, SOC 2, "
    "FedRAMP, and others are included in the download bundle and are CSA's mappings, not an auditor's "
    "opinion. Implementation and auditing guidelines exist. None of that is a certificate. A customer "
    "can require a vendor to complete CAIQ against CCM; that is procurement, not CSA STAR Level 2. "
    "This row lets a crawler attach the string 'CCM' without giving it STAR Level 2's weight. If both "
    "strings appear, score Level 2 when the registry says Level 2, and treat CCM as the library behind it."
)

EXTRA["caiq"] = (
    " CAIQ versions and STAR-submissible versions have been split in CSA's downloads: the reference CAIQ "
    "in the CCM bundle is not always the file CSA wants in the registry. Use the STAR Level 1 Security "
    "Questionnaire if the point is publication. Question IDs change between v3 and v4; an old completed "
    "CAIQ is painful to map. Shared Assessments SIG is a different taxonomy — do not merge answer files. "
    "Some GRC platforms ingest CAIQ as a standard. That convenience is not assurance. Typical buyer use "
    "is to pre-fill a questionnaire. Typical misuse is to call the completed file a certification. This "
    "register's kind field exists so that misuse can be detected. Weight stays at questionnaire level."
)

EXTRA["sig"] = (
    " Shared Assessments is an industry membership program. Banks and large enterprises often mandate SIG "
    "Core or SIG Lite on a calendar. A vendor that says 'SIG available in our trust portal' is offering "
    "a filled workbook, sometimes with attachments to policies. Read the version year. A 2018 SIG Lite "
    "does not answer 2024 questions about production-AI or modern identity. SIG does not have a pass mark. "
    "Some buyers score it internally; that score is theirs, not Shared Assessments'. Do not confuse SIG "
    "with SIG Lite, CAIQ, or a SOC 2. If a portal only offers SIG and refuses SOC 2, you are in a "
    "questionnaire relationship, not an attested one. Weight is low by design."
)

EXTRA["tisax"] = (
    " Labels are the object, not a single pass/fail. A participant can hold Info high at AL2 and lack prototype "
    "protection at AL3. OEMs specify which labels they want. Assessment providers must be ENX-approved. The "
    "ISA catalog version (for example ISA 6) is specified in the handbook for contracts signed after a cutover "
    "date; an old ISA 5.x result eventually ages out. Validity is typically three years from the assessment. "
    "Sharing is permissioned: a buyer who is not a TISAX participant may not see the portal result. In that "
    "case ask for a scope ID and a screenshot or a shared result, not a designed badge. It does not replace "
    "a customer security questionnaire for non-automotive data. Score it when the "
    "deal is automotive and the labels match the OEM list."
)

EXTRA["c5"] = (
    " Type 1 versus Type 2 is the same idea as SOC: prefer Type 2 covering a period. Combined C5 + SOC 2 reports are common and still have to be read as two criteria sets. Additional criteria above the basic set matter when the customer has a higher protection need. A report that carved out the region you will use is the wrong report. If a vendor only has ISO 27001 and says 'equivalent to C5,' that is a mapping claim. Score the attestation, not the mapping. C5:2020 is the edition most reports still name."
)

EXTRA["ens"] = (
    " CCN-STIC-800 series guides tell you how to interpret ENS for specific technologies. Cloud offerings "
    "often certify at Medio; Alto is a different conversation about classification and additional measures. "
    "A certificate issued to a reseller is not the SaaS provider's certificate. Spanish public tenders will "
    "name the required category. ENS is not EU Cybersecurity Act certification (EUCC / EUCS), which is a "
    "different European scheme family. Do not file those here. Typical evidence is the certificate PDF and, "
    "where published, a listing. If the vendor says 'ENS aligned' because they have ISO 27001, file that "
    "under ISO 27001 and leave this row empty. Score a real Alto or Medio certificate as national public-sector "
    "assurance, next to C5 in weight, not next to GDPR."
)

EXTRA["cyber-essentials"] = (
    " The five themes are deliberately basic. Home-worker devices and cloud admin paths are common scope "
    "fights. A certificate that scoped only the London office network does not cover the AWS organization "
    "that runs the product. UK government supplier guidance has required CE for many contracts; some require "
    "Plus. IASME's registry is the lookup. A PDF without a registry match is suspect. CE is not Cyber "
    "Essentials Plus, not ISO 27001, not Cyber Essentials (Singapore), and not CIS IG1, though the hygiene "
    "ideas overlap. This register keeps the UK scheme only under this family. Score it as a small, real "
    "certificate. Do not let it stand in for SOC 2 on a U.S. enterprise questionnaire."
)

EXTRA["cyber-essentials-plus"] = (
    " The technical assessment will fail on missing patches, weak passwords, and unmanaged endpoints in "
    "scope. That is the value. It will not test application authorization logic or a multi-tenant isolation "
    "bug. Plus is still the five themes, tested. Some insurers and UK public buyers treat Plus as the "
    "minimum. A Plus certificate on a sister company is not yours. Check the legal name and the scope "
    "statement. One year, then reassess. If a vendor holds both CE and Plus, score Plus and do not double "
    "count. If they hold Plus and ISO 27001, score both; they answer different questions. This row is the "
    "hands-on UK hygiene mark. It is not a substitute for a Type II report."
)

EXTRA["irap"] = (
    " Classifications you will actually see on commercial cloud are Official and Protected. Secret and above "
    "are a different hosting world. ASD publishes guidance and the ISM; the consumer agency still owns the "
    "risk acceptance. Hyperscalers list IRAP-assessed services per region; an ISV on top needs its own story. "
    "Essential Eight maturity is a separate ASD model often asked in the same breath; it is not IRAP. A "
    "consultant 'IRAP-aligned' workshop is not an assessment. Ask for the assessor's name (they are on the "
    "ASD endorsed list), the classification, the date, and which services. Score a current Protected "
    "assessment in the same band as other national cloud authorizations. Score a slide deck as zero."
)

EXTRA["ismap"] = (
    " The official list is the only source of truth. Japanese-government procurement of public cloud has "
    "increasingly pointed at ISMAP-registered services. ISMAP-LIU exists for lower-impact use and must "
    "not be sold as full ISMAP. Audit bodies are registered; a random ISO auditor is not automatically "
    "an ISMAP auditor. Listings expire and must be maintained. A global ISO 27001 on a US entity does "
    "not put a Tokyo region on the ISMAP list. Ask for the list URL and the service name in Japanese and "
    "English if both exist. Score a live full listing high for Japanese public-sector deals. Score 'planning "
    "to apply' as nothing. This is Japan's FedRAMP-shaped object, not Japan's PDPA."
)

EXTRA["mtcs"] = (
    " SS 584 tiers are cumulative in spirit: a Level 3 service has met a stricter set than Level 1. Public "
    "sector and regulated buyers in Singapore may name a tier. The certificate is issued by an accredited "
    "certification body, not by a blog. Scope can be IaaS, PaaS, or SaaS; read it. MTCS is sometimes "
    "discussed next to Singapore's Cyber Trust marks; those are different CSA Singapore schemes. PDPA "
    "remains the privacy law. A vendor that holds MTCS Level 2 and ISO 27001 is showing two real marks. "
    "A vendor that holds neither and writes 'aligned to MTCS' is mapping. Score the certificate at the "
    "stated level. If the level is missing, ask. Do not guess Level 3."
)

EXTRA["k-isms"] = (
    " Korean public and large internet services have statutory or practical K-ISMS duties that do not apply "
    "to a random global SaaS. If the customer is not Korean, this row rarely matters. If the customer is "
    "a Korean government cloud buyer, they may also mention CSAP (cloud security assurance). CSAP is not "
    "filed under this id. Certificates are in Korean; get a translation of the scope, not only a logo. "
    "ISO 27001 can be used as input but the K-ISMS certificate is the object. Score it when present and "
    "in scope. Do not treat a global 27001 as a substitute for a Korean buyer who asked for K-ISMS by name. "
    "That substitution is a common trust-page hope and a common failed questionnaire answer."
)

EXTRA["dora"] = (
    " Regulatory technical standards (RTS/ITS) under DORA fill in registers of information, incident "
    "classification, and testing detail. Critical ICT third-party providers are designated; designation "
    "is public-ish and rare. Most SaaS vendors are 'ICT third-party providers' to financial entities "
    "without being designated critical. The artifact is the contract: access, audit, exit, location, "
    "sub-outsourcing. A 'DORA ready' badge is sales language. Threat-led penetration testing duties "
    "sit on the financial entity, with cooperation from providers. ISO 22301 and SOC 2 can be exhibits. "
    "They are not a DORA certificate because none exists. Score the badge low. Score the contract "
    "separately, outside this encyclopedia."
)

EXTRA["nis2"] = (
    " Essential and important entities are defined by sector annexes and size tests in national law. "
    "Management accountability, incident reporting, and supply-chain security are the headline duties. "
    "A SaaS vendor may be in scope as a digital provider or only as a supplier. Member-state registers "
    "and competent authorities differ. There is talk of certification schemes under the Cybersecurity "
    "Act helping with NIS2; that is not a NIS2 certificate and not this row. A trust page that lists "
    "NIS2 next to ISO 27001 as two certificates is wrong. File NIS2 as regulation. If the vendor has "
    "C5, ENS, or Cyber Essentials, those are the national artifacts that might actually sit on disk."
)

EXTRA["eu-ai-act"] = (
    " Phased application means some bans and GPAI duties arrive before high-risk product rules. Providers, "
    "deployers, importers, and distributors are different roles. A B2B SaaS that lets a customer build "
    "high-risk systems may be a provider or a deployer depending on facts; this encyclopedia will not "
    "decide that. Conformity assessment, CE marking for high-risk AI, and fundamental-rights impact "
    "assessments are regulated processes. None of them is a SOC 2. ISO 42001 may help a management "
    "system. It does not produce an AI Act certificate. A 'we comply with the AI Act' badge in 2026 is "
    "usually early and unspecific. Ask which role, which system, and which title of the Regulation. "
    "Score the badge as a regulation claim."
)

EXTRA["cis-controls"] = (
    " IG1 is basic hygiene, IG2 is an operational security program, IG3 is a more mature set. CIS "
    "Benchmarks are configuration recommendations for named platforms and are independently listed "
    "when a product is certified against a Benchmark — that is a product hardening mark, not an "
    "organization CIS Controls certificate. Do not file a CIS-CAT score as a company certification. "
    "Do not file 'we implement CIS' as equal to ISO 27001. This row exists because the string is "
    "everywhere. Typical evidence, if any, is an internal score or a third-party gap assessment "
    "naming the version and IG. Without that, weight is a mapping claim. Pair with SOC 2 or 27001 "
    "when those exist and treat CIS as the vocabulary of prioritized safeguards."
)

EXTRA["sox"] = (
    " Emerging-growth-company and non-accelerated-filer rules have affected whether an auditor's 404(b) "
    "attestation is required in a given year; that is a securities-law detail, not a vendor badge. "
    "PCAOB AS 2201 is the audit standard the financial auditor uses. None of it produces a PDF you "
    "should accept as product security evidence. The recurring mix-up is a public cloud vendor saying "
    "'SOX compliant' because they are a public company. That sentence is about their 10-K, not your "
    "tenant. Ask for SOC 1 Type II if your auditors need ICFR evidence, and SOC 2 Type II if you are "
    "doing security review. File SOX as regulation with a low weight so a crawler has somewhere to "
    "put the string without inflating a security score."
)

EXTRA["hds"] = (
    " Six activity types appear in the référentiel (from physical hosting through managed platform). "
    "The certificate must name which activities were certified. A certificate for physical datacenter "
    "housing is not a certificate for a SaaS application layer. HDS v2 référentiels tightened "
    "sovereignty language; read the edition on the paper. ISO 27001 is a prerequisite ingredient, "
    "not a substitute. SecNumCloud is ANSSI's cloud qualification and is a different, often stricter "
    "sovereignty scheme — not merged into this id. A U.S. region of a hyperscaler may be HDS-certified "
    "when the hyperscaler completed the process; an ISV on top still needs its own analysis of whether "
    "it is 'hosting' under French law. Score a matching HDS certificate high for French health deals."
)

EXTRA["privacy-shield"] = (
    " Commerce stopped treating Privacy Shield as a live EU transfer program after Schrems II. Some "
    "organizations left leftover seals on footers for years. Those seals are harmful because they "
    "teach buyers the wrong mechanism. Safe Harbor, Privacy Shield's predecessor, was invalidated "
    "in Schrems I (2015). The pattern is the point: self-certification adequacy deals with the US "
    "have been struck down twice. DPF is the third attempt and is still in force as of this register, "
    "with active legal and political watch items. This row's only job is to mark the name retired "
    "and to point at DPF, SCCs, and BCRs. Weight is zero. If a crawler sees Privacy Shield, do not "
    "add points. Subtract confidence in the page's clerkship."
)

EXTRA["eu-us-dpf"] = (
    " The listing shows organization name, remaining-in-effect date, and which frameworks (EU-U.S., UK Extension, Swiss-U.S.) are active. An inactive line is not a transfer basis. Supplementary measures and a transfer map are still wise; many counsel run SCCs in parallel. A DPF listing does not attest product security and does not replace a DPA. Recheck the list on the day you sign. Adequacy can end on a court calendar you do not control."
)

EXTRA["swiss-us-dpf"] = (
    " Switzerland is not an EU member state. EU adequacy does not automatically cover Swiss transfers. "
    "The Swiss-U.S. DPF is the matching self-certification box on the same Commerce list. FDPIC "
    "communications describe the Swiss recognition. If the listing shows EU-U.S. Active and Swiss-U.S. "
    "not participated, you do not have the Swiss mechanism. SCCs as adopted in Switzerland, or the "
    "Swiss addendum practice your counsel uses, are the fallback. This row is short in novelty and "
    "long in the need to stop people merging it with the EU box. Score a live Swiss-U.S. Active line "
    "as a mechanism. Score a EU-only listing as zero for Swiss personal data. Privacy Shield (Swiss) "
    "is retired. Do not accept it."
)

EXTRA["scc"] = (
    " Commission Decision 2021/914 replaced the 2010 controller clauses and the 2010 processor clauses. "
    "Old clauses had a sunset; new modules should be what you see in a 2026 DPA. Docking clauses let "
    "another party join. Module 3 (processor to processor) is the one a subprocessor should sign with "
    "the processor. A vendor that says 'we sign SCCs' should show which modules and whether they will "
    "sign Module 2 as processor. Transfer impact assessments are not optional after Schrems II just "
    "because the clauses are signed. UK and Swiss variants are separate paperwork. SCCs are kind "
    "code-of-practice in this register because they are a prescribed contractual mechanism, not a "
    "certificate and not a statute. Weight is low as a badge, high as a document you actually need "
    "in the file."
)

EXTRA["bcr"] = (
    " The EDPB publishes information on approved BCRs. Approval takes time and political coordination "
    "among authorities; that cost is why BCRs are a large-group tool. Processor BCRs help a group "
    "that offers processing to many controllers. They still need a controller-processor contract with "
    "the customer. Intra-group subprocessors inside the BCR perimeter are the win. Outside processors "
    "need SCCs or another tool. A BCR application 'in progress' is not an approval. Do not accept a "
    "draft policy. Score an approved BCR as a meaningful transfer mechanism, stronger than a bare "
    "SCC claim because a supervisor reviewed it, still far below a security authorization. If the "
    "product's data leaves the group, the BCR does not follow it."
)

EXTRA["fips-140-3"] = (
    " Levels 1 through 4 describe increasing physical and physical-security expectations of the module, "
    "not the maturity of the vendor's ISMS. Most software libraries land at Level 1; hardware security "
    "modules often at Level 3. A certificate can be historical, revoked, or sunset; CMVP states those "
    "statuses. 'FIPS validated' and 'FIPS compliant' are different sentences. Compliant often means "
    "'we used algorithms from the approved list' without a module certificate. Federal buyers who "
    "require validated modules mean the first sentence. Ask for the certificate number and whether "
    "the service runs in FIPS mode (a flag many products expose and some leave off). Score a live "
    "CMVP number as crypto-module evidence. Do not score it as company security certification."
)
