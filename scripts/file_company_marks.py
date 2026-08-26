#!/usr/bin/env python3
"""Fill missing marks on the next ~40 on-file companies.

First-party trust / security / compliance HTML only. Fetch-check. Do not invent.
When unsure, leave open. Portal hosts stay unread.
"""
from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import enrich  # noqa: E402
from marks import extract_certs_from_html, mark_blob  # noqa: E402

SITE = ROOT / "site"
DATA = ROOT / "data"
PUBLIC = SITE / "data.json"
ENRICHED = SITE / "data" / "enriched.json"
REPORT = DATA / "render" / "company-marks.json"
BATCH = 40
WORKERS = 12
# Register-walk PRs 49, 50, 51, and 58 already fetch-checked trust / security.
# This cut may read a stored first-party privacy page on those still-open
# files. Trust / security URLs from those slices stay unread.
REGISTER_WALKED = {
    # PR 49
    "datalogics",
    "guild",
    "classranked",
    "midjourney",
    "fastly",
    "aerospike",
    "intuit",
    "daon-inc",
    "avid-technology",
    "paypal",
    "chartbeat",
    "boomi-lp",
    "cs-disco",
    "viant-technology",
    "calm",
    "caspio",
    "thinking-machine-labs",
    "decagon",
    "nvidia",
    "brave-software",
    "apple",
    "cleo-communications",
    "eab",
    "salt-security",
    "bettercloud",
    "activeops",
    "airship",
    "bluevoyant",
    "corelight",
    "megaport",
    "deltek",
    "athenahealth",
    "deepwatch",
    "american-megatrends",
    "accesso-technology",
    "meta",
    "aptitude-software",
    "crusoe",
    "docebo",
    "energycap",
    # PR 50
    "enterprisedb",
    "extensis",
    "genesys",
    "forcepoint",
    "floqast",
    "esentire",
    "expel",
    "langchain",
    "safebreach",
    "appian",
    "baseten",
    "doubleverify",
    "huntress",
    "ironscales",
    "snorkel-ai",
    "wiz",
    "afiniti",
    "forescout",
    "luminance",
    "canto-software",
    "wells-fargo",
    "diebold-nixdorf",
    "leidos-holdings",
    "digi-international",
    "audiocodes",
    "ebay",
    "paylocity",
    "bank-of-america",
    "guidewire",
    "lightspeed-commerce",
    "phunware",
    "the-trade-desk",
    "ibotta",
    "snap",
    "lyft",
    "zerofox",
    "abbyy",
    "armis",
    "certara",
    "expensify",
    # PR 51
    "ge-aerospace",
    "iress",
    "johnson-controls",
    "kwai",
    "par-technology",
    "photoroom",
    "resmed",
    "seagate-technology",
    "stryker-corporation",
    "toast",
    "tribal-group",
    "usio",
    "xylem-inc",
    "texas-instruments",
    "newegg",
    "gen-digital",
    "craigslist",
    "nucleus-software-exports",
    "walmart",
    "attentive",
    "deel",
    "hugging-face",
    "fal-ai",
    "perplexity-ai",
    "mixpanel",
    "xai",
    "pinewood-technologies",
    "odoo",
    "mercor",
    "altium",
    "aras-corp",
    "eagle-eye-solutions",
    "coactive-ai",
    "forter",
    "pdf-solutions",
    "veritone",
    "nationwide-mutual-insurance-company",
    "fico",
    "leidos",
    "teradata",
    # PR 58
    "imperva",
    "idrive-inc",
    "insightly",
    "honeybook",
    "icims",
    "homebase",
    "inbenta",
    "instabase",
    "hyland-software",
    "bmc-software",
    "beyondtrust",
    "8x8",
    "citrix",
    "zoominfo",
    "blackline",
    "logmein",
    "coveo",
    "teamviewer",
    "checkmarx",
    "zeta-global",
    "cerebras",
    "admicom",
    "aqua-security",
    "dexcom",
    "gigamon",
    "lime-technologies",
    "malwarebytes",
    "watchguard",
    # PR 83 — remaining open trust pages fetch-checked; JS shells / no hold
    "perforce",
    "typeform",
    "zerotier",
    "kiteworks",
    "kampyle",
    "booksy",
    "alibaba-cloud",
    "comm100",
    # this cut — remaining open trust pages fetch-checked; JS shells / 403 / already on file
    "guesty",
    "indeni",
    "trusona",
}

# Expand cuts already read privacy. Do not retry those slugs.
# The live report holds the last expand increment; older expand PRs are
# listed here because those reports were overwritten.
PRIOR_ATTEMPTED = {
    # PR 60 morning expand
    "jamf",
    "jw-player",
    "ivanti",
    "kajabi",
    "kaseya",
    "kentik",
    "litera",
    "lusha",
    "lilt",
    "lever",
    "liquidplanner",
    "lucidworks",
    "lionbridge",
    # PR 62 9:46 expand
    "medallia",
    "mindbody-inc",
    "mindfire-inc",
    # PR 64 CRN expand
    "dashlane",
    # PR 65 silent CRN six
    "vulncheck",
    "recorded-future",
    "blackberry",
    "reflectiz",
    "secureworks",
    "juniper-networks",
    # PR 66 19:01 expand (also the live report batch)
    "bugcrowd",
    "crossbeam-systems",
    "druva",
    "fluid-attacks",
    "datto",
    "hackerone",
    # PR 68 19:55 expand — JS shells / 403s, nothing to file
    "netcraft",
    "synack",
    "pentera",
    "panorays",
    # Privacy pages already fetch-checked this cut; no company hold.
    "instacart",
    "baxter-international",
    "meta-platforms",
    "indinero",
    # PR 82 01:55 expand — already fetch-checked this morning.
    "bigtime-enterprise-psa",
    "avaloq",
    "mileiq",
    "alvao",
    "quickbase",
    "readdle",
    # PR 83 — 40 open files fetch-checked; nothing first-party printed
    "imperva",
    "guild",
    "classranked",
    "midjourney",
    "fastly",
    "aerospike",
    "calm",
    "perforce",
    "typeform",
    "avid-technology",
    "paypal",
    "boomi-lp",
    "viant-technology",
    "zerotier",
    "thinking-machine-labs",
    "decagon",
    "insightly",
    "nvidia",
    "kiteworks",
    "kampyle",
    "brave-software",
    "apple",
    "genesys",
    "salt-security",
    "booksy",
    "activeops",
    "airship",
    "bluevoyant",
    "corelight",
    "honeybook",
    "american-megatrends",
    "alibaba-cloud",
    "comm100",
    "docebo",
    "esentire",
    "langchain",
    "appian",
    "wells-fargo",
    "diebold-nixdorf",
    "leidos-holdings",
    # PR 90 16:53 expand — already fetch-checked; next walk should not retry
    "lightricks",
    "optimove",
    "sapiens-international-corporation",
    "sisense",
    "snappy-gifts",
    "rollout-io",
    # PR 98 — 24 Aug expand six; trust/privacy already fetch-checked
    "aveva",
    "bromcom",
    "faculty",
    "kraken-technologies",
    "activestate",
    "altus-group",
    # PR 104 — 24 Aug 19:48 expand three; JS shells, closed without merge
    "intrahealth-systems-limited",
    "prontoforms",
    "versapay",
    # this cut — 40 open/thin files fetch-checked
    "guesty",
    "indeni",
    "audiocodes",
    "ebay",
    "paylocity",
    "bank-of-america",
    "lightspeed-commerce",
    "phunware",
    "the-trade-desk",
    "ibotta",
    "lyft",
    "zerofox",
    "expensify",
    "photoroom",
    "tribal-group",
    "texas-instruments",
    "nucleus-software-exports",
    "walmart",
    "attentive",
    "idrive-inc",
    "deel",
    "eab",
    "hugging-face",
    "fal-ai",
    "perplexity-ai",
    "mixpanel",
    "xai",
    "intuit",
    "pinewood-technologies",
    "odoo",
    "chartbeat",
    "mercor",
    "huntress",
    "altium",
    "aras-corp",
    "coactive-ai",
    "trusona",
    "forter",
    "guidewire",
    "veritone",
    # this cut — 19 remaining open/thin files fetch-checked
    "mckesson-corporation",
    "pfizer",
    "sendio",
    "vast-data",
    "fico",
    "teradata",
    "nationwide-mutual-insurance-company",
    "leidos",
    "bmc-software",
    "zoominfo",
    "blackline",
    "coveo",
    "teamviewer",
    "cerebras",
    "admicom",
    "dexcom",
    "gigamon",
    "malwarebytes",
    "watchguard",
    # this cut — 40 open/thin files fetch-checked; portal shells / no hold
    "superoffice",
    "extensis",
    "frosmo",
    "projectmanager-com",
    "trustpilot",
    "caspio",
    "genedata",
    "bettercloud",
    "deltek",
    "athenahealth",
    "crusoe",
    "esko",
    "meta",
    "aptitude-software",
    "energycap",
    "forescout",
    "luminance",
    "stryker-corporation",
    "snap",
    "ge-aerospace",
    "iress",
    "johnson-controls",
    "kwai",
    "resmed",
    "seagate-technology",
    "toast",
    "usio",
    "newegg",
    "gen-digital",
    "craigslist",
    "meltwater",
    "trustly",
    "pdf-solutions",
    "beyondtrust",
    "8x8",
    "citrix",
    "logmein",
    "checkmarx",
    "zeta-global",
    "aqua-security",
    # this cut — leftover open trust-URL files after PRIOR
    "bigid",
    "commvault",
    "clarivate",
    "domo",
    "sopra-steria",
    # this cut — unread empty-cert files with a stored first-party
    # trust / security / privacy URL. Trust-URL leftovers exhausted.
    "braze",
    "glossgenius",
    "brown-forman",
    "american-water-works",
    "character-ai",
    "amcor",
    "abbott-laboratories",
    "american-international-group",
    "aflac",
    "jabil",
    "micron-technology",
    "valero-energy",
    "aes-corporation",
    "centene",
    "corpay",
    "materialise-nv",
    "schr-dinger",
    "zensar-technologies",
    "on-semiconductor",
    "globant",
    "4dmedical-limited",
    "bytedance",
    "cyngn",
    "system1",
    "applied-digital",
    "3d-systems",
    "3i-infotech",
    "a-o-smith",
    "aiforia-technologies-oyj",
    "albemarle-corporation",
    "alexandria-real-estate-equities",
    "alfa-financial-software",
    "alkami",
    "alliant-energy",
    "amadeus",
    "ameren",
    "american-electric-power",
    "american-express",
    "ametek",
    "amgen",
    # this cut — 40 unread empty-cert files with a stored first-party
    # trust / security / privacy URL. Four leftover trust-URL files
    # (codesignal, earnin, renaissance-learning, zafin) plus the next
    # privacy-page empty-cert files.
    "codesignal",
    "earnin",
    "renaissance-learning",
    "zafin",
    "aptiv",
    "arthur-j-gallagher-and-co",
    "assurant",
    "atmos-energy",
    "aurora-innovation",
    "baker-hughes",
    "becton-dickinson",
    "beyond",
    "blue-yonder",
    "bristol-myers-squibb",
    "builders-firstsource",
    "c-h-robinson",
    "camden-property-trust",
    "carrier-global",
    "cboe-global-markets",
    "cdk-global",
    "cencora",
    "centerpoint-energy",
    "cf-industries",
    "charles-schwab-corporation",
    "chipotle-mexican-grill",
    "chubb-limited",
    "church-and-dwight",
    "cincinnati-financial",
    "cognizant-technology-solutions",
    "cognyte",
    "coherent-corp",
    "comfort-systems-usa",
    "concentrix",
    "conocophillips",
    "consolidated-edison",
    "constellation-brands",
    "constellation-software",
    "copart",
    "corteva",
    "cox-enterprises",
    # this cut — 40 unread empty-cert files with a stored first-party
    # trust / security / privacy URL. One leftover trust-URL file
    # (sap-ariba) plus the next privacy-page empty-cert files.
    "sap-ariba",
    "echostar",
    "danaher-corporation",
    "crh-plc",
    "crown-castle",
    "cvs-health",
    "d-r-horton",
    "darden-restaurants",
    "davita",
    "deckers-brands",
    "delta-air-lines",
    "devon-energy",
    "digimarc",
    "dollar-general",
    "dollar-tree",
    "dte-energy",
    "dye-and-durham",
    "elevance-health",
    "energy-transfer-partners",
    "enterprise-mobility",
    "enterprise-products-partners",
    "epic-games",
    "exasol-ag",
    "exxon-mobil",
    "fanatics",
    "fannie-mae",
    "fedex",
    "figure-ai",
    "first-solar",
    "fox-corporation",
    "freddie-mac",
    "freee-k-k",
    "freightos",
    "gb-group",
    "genius-sports",
    "grab",
    "grubhub",
    "h-e-b-grocery-company",
    "hbx-group-international-plc",
    "hca-healthcare",
    # this cut — leftover empty-cert trust-URL files plus the next
    # unread empty-cert files with a stored first-party privacy URL.
    "ctsi-global",
    "telestream",
    "klarna",
    "hcl-tech",
    "humana",
    "infotel",
    "intel",
    "intershop-communications",
    "jack-henry",
    "johnson-and-johnson",
    "kakao",
    "kla",
    "kpit-technologies",
    "kyndryl",
    "kyndryl-holdings",
    "ltts",
    "lectra",
    "lg-electronics",
    "liberty-mutual-insurance-group",
    "linedata",
    "live-nation-entertainment",
    "magic-software",
    "mapmyindia",
    "marin-software",
    "mercadolibre",
    "micro-systemation",
    "mitek-systems",
    "money-forward",
    "monolithic-power-systems",
    "msci",
    "nagarro",
    "netcall",
    "netflix",
    "news-corp",
    "nextnav",
    "nxp-semiconductors",
    "one-software-technologies",
    "opendoor",
    "opera",
    "perfect-corp",
    # this cut — leftover empty-cert trust-URL files plus the next
    # unread empty-cert files with a stored first-party privacy URL.
    "seqera-labs",
    "walkme",
    "virtutech",
    "performance-food-group",
    "phillips-66",
    "porch-group",
    "pro-medicus",
    "publix-super-markets",
    "quick-heal",
    "ramco-systems",
    "raysearch-laboratories",
    "robinhood",
    "rtx",
    "sandisk",
    "sanmina",
    "science-applications-international",
    "sea-limited",
    "serko-limited",
    "serviceware",
    "silvaco",
    "simulations-plus",
    "smith-micro-software",
    "sonata-software",
    "southern-glazer-s-wine-and-spirits",
    "spotify",
    "stitch-fix",
    "super-micro-computer",
    "synaptics",
    "synchronoss",
    "sysco",
    "take-two-interactive",
    "tally-solutions",
    "target",
    "td-synnex",
    "tech-mahindra",
    "teledyne-technologies",
    "tencent",
    "tietoevry",
    "tko-group-holdings",
    "tose-software",
}

# Regulation-only lists stay thin. Real certs (SOC / ISO / FedRAMP / …) fill out.
REG_MARKS = {"GDPR", "CCPA", "DORA", "NIS2", "PIPEDA", "LGPD"}
COMPLIANCE_URL_RE = re.compile(
    r"(trust|security|compliance|certif|attestation|assurance)",
    re.I,
)
ITEM_UID_RE = re.compile(r"itemUid=|itemName=", re.I)
ASSET_URL_RE = re.compile(r"\.(?:ico|png|jpe?g|gif|svg|webp|css|js|woff2?|map)(?:\?|$)", re.I)
DPF_PHRASE_RE = re.compile(
    r"data[\s/_-]*privacy[\s/_-]*framework|eu[\s/_-]*u\.?s\.?[\s/_-]*dpf|"
    r"eu[\s/_-]*us[\s/_-]*dpf",
    re.I,
)
DPF_SELF_CERT_RE = re.compile(
    r"self[- ]?certif|"
    r"certif(?:ied|ication)\s+to\s+the\s+u\.?s\.?\s+department\s+of\s+commerce|"
    r"compli(?:es|ant|ance)\s+with\s+the\s+"
    r"(?:eu[- /]*u\.?s\.?|swiss[- /]*u\.?s\.?)\s+data\s+privacy\s+framework|"
    r"notice of certification under|"
    r"data privacy framework policy certification",
    re.I,
)
CMMC_PRODUCT_RE = re.compile(
    r"cmmc\s+(?:readiness|consult|services?|solutions?|training)",
    re.I,
)
PCI_PROCESSOR_RE = re.compile(
    r"(?:payment|third[- ]party|our)\s+process(?:or|ors|ing)",
    re.I,
)
HIPAA_NOT_HOLD_RE = re.compile(
    r"notice of privacy practices|rights?\s+under\s+hipaa|"
    r"protected\s+under\s+hipaa|applicable\s+law,?\s+including\s+hipaa|"
    r"including\s+(?:the\s+)?(?:health insurance portability|hipaa)|"
    r"covered\s+by\s+(?:the\s+)?(?:health insurance portability|hipaa)|"
    r"subject\s+to\s+(?:the\s+)?(?:health insurance portability|hipaa)|"
    r"related\s+to\s+hipaa|"
    r"hipaa\s+notice|"
    r"hipaa\s+patient|"
    r"hipaa\s+forms|"
    r"hipaa\s+rules|"
    r"granted\s+by\s+hipaa|"
    r"governed\s+by\s+hipaa|"
    r"hipaa-covered|"
    r"required\s+under\s+(?:the\s+)?(?:health insurance portability|hipaa)|"
    r"de-identif|"
    r"45\s+cfr|"
    r"business\s+associate|"
    r"deemed\s+under\s+hipaa\s+to\s+be\s+acting\s+as\s+a\s+business\s+associate|"
    r"shall\s+not\s+provide\s+us\s+with\s+any\s+phi|"
    r"regulated\s+under\s+(?:the\s+)?(?:health insurance portability|hipaa)|"
    r"(?:complian[ct]e|comply)\s+with\s+(?:the\s+)?(?:health insurance portability|hipaa)|"
    r"hipaa.?s?\s+privacy\s+rule|"
    r"hipaa\s+privacy\s+practices|"
    r"privacy\s+practices\s+notice|"
    r"health\s+and\s+wellness\s+plan|"
    r"sector[- ]specific\s+privacy\s+laws|"
    r"health\s+insurance\s+portability\s+and\s+accountability\s+act\s+of\s+1996|"
    r"does\s+not\s+apply\s+to.{0,160}protected\s+health\s+information",
    re.I,
)


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def instrument_url(row: dict, key: str) -> str:
    rec = (row.get("instruments") or {}).get(key) or {}
    if isinstance(rec, dict):
        return (rec.get("url") or "").strip()
    return str(rec or "").strip()


def named_certs(public: dict, enr: dict) -> list[str]:
    certs = [c for c in (public.get("certs") or []) if c]
    if not certs:
        certs = [c for c in (enr.get("certs") or []) if isinstance(c, str) and c]
    return certs


def named_marks_on_file(public: dict, enr: dict) -> bool:
    atts = [a for a in (public.get("attestations") or []) if a and (a.get("name") or a.get("short"))]
    if atts or named_certs(public, enr):
        return True
    return bool(public.get("fedramp") or enr.get("fedramp"))


def marks_are_thin(certs: list[str]) -> bool:
    real = [c for c in certs if c not in REG_MARKS]
    return len(real) <= 1 and len(certs) <= 3


def marks_are_substantial(certs: list[str]) -> bool:
    real = [c for c in certs if c not in REG_MARKS]
    return len(real) >= 3 or len(certs) >= 5


def public_url(url: str) -> str:
    u = (url or "").split("#")[0].strip()
    if "itemUid=" in u or "inviteToken=" in u or "loginRequest=" in u:
        return u.split("?", 1)[0]
    return u


def first_party_candidates(public: dict, enr: dict) -> list[tuple[str, str]]:
    """URLs already on the file that we may read. Portal hosts stay out."""
    out, seen = [], set()

    def add(kind: str, url: str) -> None:
        u = (url or "").strip()
        if not u.startswith("http"):
            return
        if ITEM_UID_RE.search(u) or ASSET_URL_RE.search(u):
            return
        key = u.lower()
        if key in seen:
            return
        if not enrich.is_first_party_url(u, enr):
            return
        path = enrich.path_of(u)
        host = enrich.host_of(u)
        if kind not in {"trust", "security", "trust_url", "enr_trust", "privacy", "dpa", "subprocessors"}:
            # final_url / extra links must themselves be a trust or compliance page
            if not COMPLIANCE_URL_RE.search(f"{host} {path}"):
                return
        seen.add(key)
        out.append((kind, u))

    links = enr.get("links") or {}
    # Trust-URL-only leftovers are exhausted after PRIOR. This cut reads
    # unread empty-cert files that already store a first-party trust,
    # security, or privacy URL. Skip lists keep PRIOR_ATTEMPTED off queue.
    kinds = ("trust", "security", "privacy")
    extra_kinds = ("dpa", "subprocessors") if requested_slugs() else ()
    for kind in (*kinds, *extra_kinds):
        add(kind, links.get(kind) or "")
    add("trust_url", public.get("trust_url") or "")
    add("enr_trust", enr.get("trust_url") or "")
    add("final_url", public.get("final_url") or "")
    add("enr_final", enr.get("final_url") or "")
    for key in (*kinds, *extra_kinds):
        add(key, instrument_url(public, key))
    return out


def requested_slugs() -> list[str]:
    """Optional argv slugs. Empty means the next ~40 open/thin files."""
    return [a.strip() for a in sys.argv[1:] if a.strip() and not a.startswith("-")]


def previous_batch() -> set[str]:
    prior = {slug for slug in (load_json(REPORT, {}).get("batch") or []) if slug}
    prior.update(PRIOR_ATTEMPTED)
    return prior


def select_batch(public_rows: list[dict], enr_by: dict[str, dict]) -> list[dict]:
    wanted = requested_slugs()
    skip = set() if wanted else previous_batch()
    by_pub = {row.get("slug"): row for row in public_rows if row.get("slug")}
    rows = [by_pub[s] for s in wanted if s in by_pub] if wanted else public_rows
    open_rows, thin_rows = [], []
    for row in rows:
        slug = row.get("slug") or ""
        if slug in skip:
            continue
        enr = enr_by.get(slug)
        if not enr:
            continue
        certs = named_certs(row, enr)
        if marks_are_substantial(certs):
            continue
        on_file = named_marks_on_file(row, enr)
        if on_file and not marks_are_thin(certs):
            continue
        cands = first_party_candidates(row, enr)
        if not cands:
            continue
        rec = {
            "slug": slug,
            "name": row.get("name") or slug,
            "thin": on_file,
            "have": certs,
            "candidates": cands,
        }
        (thin_rows if on_file else open_rows).append(rec)
    if wanted:
        return open_rows + thin_rows
    # Trust-URL-only leftovers are exhausted. Prefer empty-cert files.
    return (open_rows + thin_rows)[:BATCH]


def fetch_page(url: str) -> dict:
    try:
        return enrich.fetch_seed_page(url)
    except Exception:
        return {
            "ok": False, "status": 0, "final_url": url,
            "hrefs": [], "html": "", "title": "", "text": "", "meta": "", "ctype": "",
        }


def reject_reason(url: str, rec: dict, row: dict) -> str | None:
    final = rec.get("final_url") or url
    if not rec.get("ok") or rec.get("status") != 200:
        return f"http-{rec.get('status') or 0}"
    if not enrich.is_first_party_url(final, row):
        return "not-first-party"
    if enrich.is_portal_vendor_host(url, row) or enrich.is_portal_vendor_host(final, row):
        return "portal-vendor"
    title, text = rec.get("title") or "", rec.get("text") or ""
    if enrich.VENDOR_WORDS.search(title) or enrich.VENDOR_TITLE_TAIL.search(title):
        return "js-portal"
    if enrich.looks_like_login_wall(title, text):
        return "login-wall"
    if enrich.looks_dead(title, text):
        return "soft-404"
    if enrich.landed_on_home(url, final):
        return "homepage-bounce"
    ctype = (rec.get("ctype") or "").lower()
    if "pdf" in ctype or (url or "").lower().endswith(".pdf"):
        return "pdf"
    return None


def marks_from_rec(rec: dict) -> list[str]:
    html = rec.get("html") or ""
    title = rec.get("title") or ""
    text = rec.get("text") or ""
    meta = rec.get("meta") or ""
    blob = mark_blob(html, title, meta, text)
    return extract_certs_from_html(html, text=blob)


def rec_blob(rec: dict) -> str:
    return mark_blob(
        rec.get("html") or "",
        rec.get("title") or "",
        rec.get("meta") or "",
        rec.get("text") or "",
    )


def dpf_is_self_cert(blob: str) -> bool:
    """DPF fills only on a self-cert / compliance claim, not as an SCC among others."""
    if not blob:
        return False
    for m in DPF_PHRASE_RE.finditer(blob):
        window = blob[max(0, m.start() - 220): min(len(blob), m.end() + 220)]
        if DPF_SELF_CERT_RE.search(window):
            return True
    return False


def pci_is_processor(blob: str) -> bool:
    """Third-party processor PCI is not this company's hold."""
    if not blob:
        return False
    for m in re.finditer(r"\bpci(?:[\s/_-]*dss|\s+dss|\s+level)\b", blob, re.I):
        window = blob[max(0, m.start() - 160): min(len(blob), m.end() + 160)]
        if PCI_PROCESSOR_RE.search(window):
            return True
    return False


def cmmc_is_hold(blob: str) -> bool:
    """A CMMC readiness product pitch is not the company holding CMMC."""
    if not blob:
        return False
    hold = False
    for m in re.finditer(r"\bcmmc\b", blob, re.I):
        window = blob[max(0, m.start() - 80): min(len(blob), m.end() + 80)]
        if CMMC_PRODUCT_RE.search(window):
            continue
        hold = True
    return hold


def hipaa_is_hold(blob: str) -> bool:
    """A HIPAA notice, BAA, or rights sentence is not a certification hold."""
    if not blob:
        return False
    if re.search(
        r"business\s+associate\s+addendum|"
        r"shall\s+not\s+provide\s+us\s+with\s+any\s+phi|"
        r"deemed\s+under\s+hipaa\s+to\s+be\s+acting\s+as\s+a\s+business\s+associate",
        blob,
        re.I,
    ):
        return False
    hold = False
    for m in re.finditer(r"\bhipaa\b", blob, re.I):
        window = blob[max(0, m.start() - 160): min(len(blob), m.end() + 160)]
        if HIPAA_NOT_HOLD_RE.search(window):
            continue
        hold = True
    return hold


def hold_marks(named: list[str], blob: str, kind: str = "") -> tuple[list[str], str | None]:
    """Keep the company's own holds. Regulation-as-rights and DPF-as-SCC stay out."""
    kept = []
    privacy_page = kind == "privacy"
    for name in named:
        if name == "EU-US DPF" and not dpf_is_self_cert(blob):
            continue
        if name == "PCI DSS" and pci_is_processor(blob):
            continue
        if name == "HIPAA" and not hipaa_is_hold(blob):
            continue
        if name == "CMMC" and not cmmc_is_hold(blob):
            continue
        if privacy_page and name in REG_MARKS:
            # Privacy-page rights / legal-grounds mentions stay open.
            continue
        kept.append(name)
    real = [m for m in kept if m not in REG_MARKS]
    if not real:
        if any(m in REG_MARKS for m in named) or "EU-US DPF" in named:
            return [], "regulation-only"
        return [], "no-named-marks"
    return kept, None


def main() -> int:
    t0 = time.time()
    public = load_json(PUBLIC, {})
    enr = load_json(ENRICHED, {})
    public_rows = list(public.get("companies") or [])
    companies = list(enr.get("companies") or [])
    enr_by = {c["slug"]: c for c in companies if c.get("slug")}

    batch = select_batch(public_rows, enr_by)
    print(f"batch {len(batch)} companies with an open or thin marks rule", flush=True)
    for rec in batch:
        kind = "thin" if rec["thin"] else "open"
        print(
            f"  {rec['slug']} {kind} have={len(rec['have'])} urls={len(rec['candidates'])}",
            flush=True,
        )

    jobs = []
    seen = set()
    for rec in batch:
        for kind, url in rec["candidates"]:
            key = (rec["slug"], url.lower())
            if key in seen:
                continue
            seen.add(key)
            jobs.append((rec["slug"], kind, url))

    print(f"fetch-check {len(jobs)} on-file first-party pages", flush=True)
    accepted: dict[str, dict] = {}
    rejected: list[dict] = []

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(fetch_page, url): (slug, kind, url) for slug, kind, url in jobs}
        done = 0
        for fut in as_completed(futs):
            slug, kind, url = futs[fut]
            rec = fut.result()
            done += 1
            if done % 10 == 0 or done == len(futs):
                print(f"  read {done}/{len(futs)}", flush=True)
            row = enr_by.get(slug)
            if not row:
                continue
            final = rec.get("final_url") or url
            skip = reject_reason(url, rec, row)
            if skip:
                rejected.append({
                    "slug": slug,
                    "url": public_url(url),
                    "final": public_url(final),
                    "reason": skip,
                    "kind": kind,
                })
                continue
            live, hold_skip = hold_marks(marks_from_rec(rec), rec_blob(rec), kind)
            if not live:
                rejected.append({
                    "slug": slug,
                    "url": public_url(url),
                    "final": public_url(final),
                    "reason": hold_skip or "no-named-marks",
                    "kind": kind,
                })
                continue
            have = named_certs(next((r for r in public_rows if r.get("slug") == slug), {}), row)
            added = [m for m in live if m not in have]
            if not added:
                rejected.append({
                    "slug": slug,
                    "url": public_url(url),
                    "final": public_url(final),
                    "reason": "already-on-file",
                    "kind": kind,
                    "seen": live,
                })
                continue
            prev = accepted.get(slug)
            if prev and len(prev.get("added") or []) >= len(added):
                continue
            source = public_url(url) if not ITEM_UID_RE.search(url) else public_url(final)
            if ITEM_UID_RE.search(source) or ASSET_URL_RE.search(source):
                source = public_url(url).split("?")[0]
            accepted[slug] = {
                "url": source,
                "named": live,
                "added": added,
            }

    filed = []
    for slug, hit in sorted(accepted.items()):
        row = enr_by[slug]
        added = enrich.apply_marks_to_row(row, hit["added"])
        if not added:
            continue
        filed.append({
            "slug": slug,
            "name": row.get("name") or slug,
            "url": hit["url"],
            "added": added,
            "certs": list(row.get("certs") or []),
        })

    write_json(ENRICHED, enr)
    write_json(DATA / "enriched.json", enr)

    stayed = []
    for rec in batch:
        if any(x["slug"] == rec["slug"] for x in filed):
            continue
        stayed.append({
            "slug": rec["slug"],
            "name": rec["name"],
            "rule": "marks",
            "thin": rec["thin"],
        })

    report = {
        "generated_at": enr.get("generated_at"),
        "rule": (
            "Next ~40 unread empty-cert companies that already store a "
            "first-party trust / security / privacy URL. The trust-URL-only "
            "queue is exhausted after PRIOR. Marks fill only when that live "
            "page names the company's own hold. Regulation mentions "
            "(GDPR/CCPA as rights) and DPF as a transfer mechanism among "
            "SCCs stay open. Login walls, soft-404s, homepage bounces, "
            "PDFs, JS shells, and portal hosts stay open."
        ),
        "batch": [rec["slug"] for rec in batch],
        "marks_filed": filed,
        "stayed_open": stayed,
        "rejected": rejected,
    }
    write_json(REPORT, report)

    print(
        f"filed marks={len(filed)} stayed={len(stayed)} rejected={len(rejected)} "
        f"in {time.time() - t0:.1f}s",
        flush=True,
    )
    for row in filed:
        print(f"  + marks {row['slug']} +{', '.join(row['added'])} {row['url']}", flush=True)
    for row in stayed:
        print(f"  - open {row['slug']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
