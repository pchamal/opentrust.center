# Attestations register — index

Public catalog of security, privacy, AI, and industry attestations a B2B company might hold or claim.
Clerk copy. Not a marketplace. Not legal advice.

**Entries:** 71  
**Updated:** 19 August 2026 (PT)  
**File:** `data/attestations.json`

## How to read a row

- **certification** — a named third party issued a certificate for a scope (ISO body, HITRUST, PCI listing, ENS, HDS).
- **attestation** — an independent report or approved mechanism (SOC, C5, TISAX, DPF, BCR, IRAP assessment).
- **authorization** — a government ATO / Marketplace status (FedRAMP, GovRAMP, TX-RAMP).
- **regulation** — a statute or directive. Nobody 'holds' it.
- **framework** — a control catalog you can map to. Not a cert.
- **code-of-practice** — guidance or a contractual mechanism (ISO 27017/27018, SCCs).
- **questionnaire** — SIG, CAIQ. Homework, not a mark.
- **weight** — how much a *verified* public disclosure should move a score. FedRAMP 12, SOC 2 Type II 10, GDPR 3, Privacy Shield 0.
- **retired** — do not score. Privacy Shield is the only retired row.

Look up the live artifact. A badge is not the report.

## By kind

| Key | Entries |
|---|---|
| certification | 25 |
| regulation | 15 |
| attestation | 14 |
| framework | 7 |
| authorization | 5 |
| code-of-practice | 3 |
| questionnaire | 2 |

## By geography tag (an entry may have more than one)

| Key | Entries |
|---|---|
| global | 33 |
| US | 31 |
| EU | 10 |
| GB | 3 |
| CA | 2 |
| DE | 2 |
| SG | 2 |
| AU | 1 |
| BR | 1 |
| CH | 1 |
| ES | 1 |
| FR | 1 |
| JP | 1 |
| KR | 1 |
| TH | 1 |

## By industry tag

| Key | Entries |
|---|---|
| all | 38 |
| cloud | 22 |
| public-sector | 16 |
| healthcare | 7 |
| ai | 4 |
| financial | 4 |
| payments | 3 |
| automotive | 1 |

## By family

| Key | Entries |
|---|---|
| ISO | 9 |
| SOC | 6 |
| transfers | 5 |
| CSA | 4 |
| HITRUST | 4 |
| NIST | 4 |
| privacy-national | 4 |
| EU-digital | 3 |
| GDPR | 3 |
| PCI | 3 |
| RAMP | 3 |
| US-privacy | 3 |
| CMMC | 2 |
| Cyber-Essentials | 2 |
| FedRAMP | 2 |
| AIUC | 1 |
| C5 | 1 |
| CIS | 1 |
| ENS | 1 |
| FIPS | 1 |
| HDS | 1 |
| HIPAA | 1 |
| IRAP | 1 |
| ISMAP | 1 |
| K-ISMS | 1 |
| MTCS | 1 |
| questionnaires | 1 |
| SOX | 1 |
| TISAX | 1 |

## Families, in clerk order

- **AIUC** (1): aiuc-1
- **C5** (1): c5
- **CIS** (1): cis-controls
- **CMMC** (2): cmmc-l1, cmmc-l2
- **CSA** (4): caiq, csa-ccm, csa-star-l1, csa-star-l2
- **Cyber-Essentials** (2): cyber-essentials, cyber-essentials-plus
- **ENS** (1): ens
- **EU-digital** (3): dora, eu-ai-act, nis2
- **FedRAMP** (2): fedramp, fedramp-li-saas
- **FIPS** (1): fips-140-3
- **GDPR** (3): eprivacy, gdpr, uk-gdpr
- **HDS** (1): hds
- **HIPAA** (1): hipaa
- **HITRUST** (4): hitrust-csf, hitrust-e1, hitrust-i1, hitrust-r2
- **IRAP** (1): irap
- **ISMAP** (1): ismap
- **ISO** (9): iso-13485, iso-20000-1, iso-22301, iso-27001, iso-27017, iso-27018, iso-27701, iso-42001, iso-9001
- **K-ISMS** (1): k-isms
- **MTCS** (1): mtcs
- **NIST** (4): nist-800-171, nist-800-53, nist-ai-rmf, nist-csf
- **PCI** (3): pci-3ds, pci-dss, pci-ssf
- **privacy-national** (4): lgpd, pdpa-sg, pdpa-th, pipeda
- **questionnaires** (1): sig
- **RAMP** (3): govramp, stateramp, tx-ramp
- **SOC** (6): soc-1-type-i, soc-1-type-ii, soc-2-type-i, soc-2-type-ii, soc-3, soc-supply-chain
- **SOX** (1): sox
- **TISAX** (1): tisax
- **transfers** (5): bcr, eu-us-dpf, privacy-shield, scc, swiss-us-dpf
- **US-privacy** (3): ccpa-cpra, us-state-privacy, vcdpa

## Retired

- `privacy-shield` — EU-U.S. Privacy Shield. Invalidated; do not accept as a transfer basis.

## Deliberately excluded

See the end of this page in the build notes, and the parent agent's report.
Short list: cookie/consent products; pen-test letters; bug-bounty programs;
SOC 2+HIPAA or SOC 2 Type II AI as invented hybrids; PA-DSS (retired, successor is PCI SSF);
ISO 14001 and other non-security management systems; employee training badges;
vendor GRC-platform seals (Vanta/Drata 'monitored').

## Source posture

Issuers, program names, and legal citations are those a GRC analyst would recognize.
Where a 2026 program is in motion (FedRAMP CR26 classes, CMMC Phase II pause, DPF review letters),
the row says what is still true and tells the buyer to open the live list.
Dates and mappings that were not solid were omitted or put in `note`.
