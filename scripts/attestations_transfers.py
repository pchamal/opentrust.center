ENTRIES = []

def add(**kw):
    ENTRIES.append(kw)

add(
    id="privacy-shield",
    name="EU-U.S. Privacy Shield",
    short="Privacy Shield",
    family="transfers",
    kind="attestation",
    geography=["US", "EU"],
    industry=["all"],
    issuer="U.S. Department of Commerce (invalidated as an EU transfer basis)",
    eli5="A dead transfer deal. Europe's top court struck it down in 2020. A company that still says it 'holds Privacy Shield' is showing an expired badge. Do not rely on it.",
    elaborate="The EU-U.S. Privacy Shield was a European Commission adequacy arrangement plus a U.S. Department of Commerce self-certification list. The Court of Justice of the European Union invalidated the adequacy decision in Case C-311/18 (Schrems II) on 16 July 2020. The Swiss-U.S. Privacy Shield was also discontinued as a transfer basis. Commerce later stood up the Data Privacy Framework, which is a different instrument. Privacy Shield is not a current lawful EU-to-US transfer mechanism. A trust page that still lists it is either historical or wrong. Typical evidence today is none that a buyer should accept. If a vendor cites Privacy Shield, ask for SCCs, BCRs, or a current DPF listing instead. This entry exists so the register can mark the name retired rather than pretend it never existed. Weight is zero for scoring.",
    lat=38.9072,
    lng=-77.0369,
    related=["eu-us-dpf", "swiss-us-dpf", "scc", "bcr"],
    weight=0,
    retired=True,
)

add(
    id="eu-us-dpf",
    name="EU-U.S. Data Privacy Framework",
    short="EU-US DPF",
    family="transfers",
    kind="attestation",
    geography=["US", "EU"],
    industry=["all"],
    issuer="U.S. Department of Commerce; EU adequacy decision of the European Commission",
    eli5="The current EU-to-US transfer list. A US company self-certifies at Commerce and must stay on the public list. It is a transfer tool, not a security audit. Courts have not killed it; people are watching it.",
    elaborate="The EU-U.S. Data Privacy Framework is a Department of Commerce self-certification program backed by a European Commission adequacy decision (July 2023) for certified organizations. Participants appear on the public Data Privacy Framework List and recertify annually. The UK Extension to the EU-U.S. DPF is a related UK transfer route; check the listing for which frameworks the organization joined. DPF is not SOC 2 and not a security certification. It addresses whether a US participant's commitments plus US legal safeguards were adequate for EU personal-data transfers. The General Court upheld the adequacy decision in Latombe (appeal status can change). As of August 2026 the adequacy decision remains in force; the EDPB has asked the Commission to review implications of U.S. Supreme Court developments on FTC independence. No court has invalidated DPF. Buyers should open the live list, check the active status and which principles apply, and still prefer SCCs as a fallback. Typical evidence is the listing URL. A logo is not enough. Privacy Shield is not DPF.",
    lat=38.9072,
    lng=-77.0369,
    related=["swiss-us-dpf", "scc", "bcr", "privacy-shield", "gdpr"],
    weight=4,
)

add(
    id="swiss-us-dpf",
    name="Swiss-U.S. Data Privacy Framework",
    short="Swiss-US DPF",
    family="transfers",
    kind="attestation",
    geography=["US", "CH"],
    industry=["all"],
    issuer="U.S. Department of Commerce; Swiss Federal Administration / FDPIC adequacy recognition",
    eli5="The Switzerland-to-US cousin of the EU Data Privacy Framework. Separate box to tick on the Commerce list. Not the same as the EU one and not Privacy Shield.",
    elaborate="The Swiss-U.S. Data Privacy Framework is the Commerce self-certification program for transfers from Switzerland to participating US organizations, recognized by Swiss authorities as an adequacy route. Organizations join it as a distinct framework on the Data Privacy Framework List; joining the EU-U.S. DPF does not automatically include Switzerland. It is not Privacy Shield. It is not a security audit. Typical evidence is the Commerce listing showing Swiss-U.S. DPF as Active. Buyers moving Swiss personal data should check that box, not only the EU box. Weight is slightly below the EU DPF because fewer pages claim it and the buyer set is smaller, but the verification method is the same.",
    lat=46.9480,
    lng=7.4474,
    related=["eu-us-dpf", "privacy-shield", "scc", "gdpr"],
    weight=3,
)

add(
    id="scc",
    name="Standard Contractual Clauses",
    short="SCCs",
    family="transfers",
    kind="code-of-practice",
    geography=["EU", "global"],
    industry=["all"],
    issuer="European Commission (Implementing Decision (EU) 2021/914)",
    eli5="A model contract the European Commission wrote so companies can send personal data to countries without an adequacy decision. It is paperwork, not a certificate. Anyone can sign it; the work is doing the transfer assessment.",
    elaborate="Standard Contractual Clauses are a transfer mechanism under GDPR Article 46. The current modular set was adopted by Commission Implementing Decision (EU) 2021/914. Parties execute the modules that match controller-to-controller, controller-to-processor, processor-to-processor, or processor-to-controller. SCCs are not a certification. Executing them does not prove security controls. Schrems II still requires a transfer impact assessment and, where needed, supplementary measures. The UK uses the IDTA or the UK Addendum rather than treating the EU decision as automatic UK law. Typical evidence is the executed SCC modules (often inside a DPA) plus a TIA. A trust page that says 'we use SCCs' is a mechanism claim, which is correct vocabulary, not an audit. Do not score SCCs as if they were ISO 27001. This register includes them because they are one of the actual legal artifacts behind 'GDPR compliant' marketing.",
    lat=50.8503,
    lng=4.3517,
    related=["bcr", "eu-us-dpf", "gdpr", "uk-gdpr"],
    weight=3,
)

add(
    id="bcr",
    name="Binding Corporate Rules",
    short="BCRs",
    family="transfers",
    kind="attestation",
    geography=["EU", "global"],
    industry=["all"],
    issuer="Lead supervisory authority / EDPB cooperation under GDPR Articles 46–47",
    eli5="A company's own internal privacy rules, approved by a European regulator, so the group can move personal data among its affiliates. Rare, slow, and real. Not a product certificate for a SaaS you buy.",
    elaborate="Binding Corporate Rules are a GDPR Article 47 transfer mechanism: a group's legally binding internal policies for international transfers, approved through the cooperation procedure with a lead supervisory authority and the EDPB. There are controller BCRs and processor BCRs. Approval is public enough that a buyer can often verify the group and the lead authority. BCRs are not a security certification of a named SaaS product. They authorize intra-group transfers that match the approved scope. They do not replace a DPA with the customer and do not approve transfers to unaffiliated subprocessors — those still need another Article 46 tool. Typical evidence is the approval and the BCR summary. BCRs are uncommon relative to SCCs; their presence is meaningful for large groups and meaningless if the product's subprocessors sit outside the group. Score them as a real, regulator-reviewed mechanism, not as FedRAMP.",
    lat=50.8503,
    lng=4.3517,
    related=["scc", "eu-us-dpf", "gdpr", "iso-27701"],
    weight=5,
)

add(
    id="fips-140-3",
    name="FIPS 140-3",
    short="FIPS 140-3",
    family="FIPS",
    kind="certification",
    geography=["US", "CA"],
    industry=["all", "public-sector"],
    issuer="NIST Cryptographic Module Validation Program (with Canadian CSEC)",
    eli5="A test of a cryptographic module — a library or a hardware box — not of a whole company. Look up the module certificate number. A vendor that says 'we are FIPS certified' is usually stretching.",
    elaborate="FIPS 140-3 is the U.S. government standard for cryptographic module security, aligned with ISO/IEC 19790, validated under the NIST Cryptographic Module Validation Program (CMVP), jointly with the Canadian Centre for Cyber Security. Certificates attach to a named module and version, at a security level, with a certificate number in the CMVP listing. FIPS 140-2 certificates exist as legacy; new validations are 140-3. This is not a company certification. A SaaS vendor may use a validated module (for example a HSMs or an OpenSSL FIPS provider) inside a service. That does not put the company on the CMVP list. Federal buyers often require validated modules for cryptographic protection of federal data, which is a different demand than FedRAMP, though FedRAMP baselines expect validated cryptography. Typical evidence is the CMVP certificate number and the exact module version used in the product. A trust-page sentence without a number is a claim. Score a verified module listing as specialized crypto evidence, not as an ISMS.",
    lat=39.1403,
    lng=-77.2200,
    related=["fedramp", "nist-800-53"],
    weight=6,
)
