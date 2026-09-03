#!/usr/bin/env python3
"""Fill missing DPA and named subprocessors on the next ~40 on-file companies.

First-party only. Fetch-check. Do not invent. When unsure, leave open.
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import enrich  # noqa: E402
from processor_aliases import canonical_processor_id, skip_processor  # noqa: E402

SITE = ROOT / "site"
DATA = ROOT / "data"
PUBLIC = SITE / "data.json"
ENRICHED = SITE / "data" / "enriched.json"
REPORT = DATA / "render" / "company-dpa-processors.json"
BATCH = 40
WORKERS = 12
# Companies already attempted in earlier DPA/subprocessor cuts. Do not retry.
# The live report holds the last expand increment; older PRs are listed here
# because those reports were overwritten.
PRIOR_ATTEMPTED = {
    # PR 47
    "palo-alto-networks",
    "dropbox",
    "motive",
    "clickup",
    "alteryx",
    "cvent",
    "dynatrace",
    "amazon-web-services",
    "cloudera",
    "automation-anywhere",
    "splunk",
    "asana",
    "calendly",
    "dataiku",
    "sierra",
    "checkr",
    "varonis",
    "workday",
    "grammarly",
    "slack",
    "airwallex",
    "clickhouse",
    "scale-ai",
    "cohere",
    "infor",
    "automattic",
    "checkout",
    "canva",
    "hubspot",
    "vertex",
    "elastic",
    "monday",
    "samsara",
    "notion",
    "shopify",
    "carta",
    "papaya-global",
    "lambda",
    "cornerstone-ondemand",
    "fortinet",
    # PR 48
    "amplitude",
    "block",
    "chainguard",
    "komodo-health",
    "deepl",
    "unity",
    "fivetran",
    "netlify",
    "island",
    "saviynt",
    "adobe",
    "azul-systems",
    "miro",
    "bench-accounting",
    "tenable",
    "uipath",
    "new-relic",
    "digitalocean",
    "zendesk",
    "benchling",
    "nice",
    "microsoft",
    "adeptia",
    "runway",
    "abridge",
    "zoho",
    "salesforce",
    "stability-ai",
    "caplinked",
    "cohesity",
    "glean",
    "gusto",
    "sap",
    "sumo-logic",
    "harness",
    "axonius",
    "five9",
    "zoom",
    "netskope",
    "cisco",
    # PR 57
    "instructure",
    "greenhouse-software",
    "imply-data",
    "daon-inc",
    "cleo-communications",
    "forcepoint",
    "enterprisedb",
    "expel",
    "megaport",
    "hackerearth",
    "baseten",
    "wiz",
    "doubleverify",
    "deepwatch",
    "safebreach",
    "accesso-technology",
    "afiniti",
    "abbyy",
    "armis",
    "eab",
    "sailpoint",
    "okta",
    "plaid",
    "confluent",
    "hugging-face",
    "rippling",
    "perplexity-ai",
    "collibra",
    "ironscales",
    "talkdesk",
    "qualtrics",
    "maintainx",
    "canto-software",
    "sentinelone",
    "alphasense",
    "ibm",
    "pinewood-technologies",
    "google",
    "docusign",
    "box",
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
    # PR 62
    "medallia",
    "mindbody-inc",
    "mindfire-inc",
    # PR 64
    "dashlane",
    # PR 65 CRN six
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
    # PR 69 register-walk DPA cut (~13:23 PT)
    "icims",
    "homebase",
    "inbenta",
    "lever",
    "lionbridge",
    "hyland-software",
    "certinia",
    "browserstack",
    "coreweave",
    "openevidence",
    "nemetschek",
    "odoo",
    "floqast",
    "flock-safety",
    "abnormal-ai",
    "snorkel-ai",
    "crowdstrike",
    "instabase",
    "blackbaud",
    "intuit",
    "extensis",
    "akamai",
    "mercor",
    "ninjaone",
    "par-technology",
    "brightwheel",
    "certara",
    "eagle-eye-solutions",
    "avid-technology",
    "paypal",
    "cyberark",
    "palantir",
    "chartbeat",
    "personio",
    "huntress",
    "manhattan-associates",
    "liveperson",
    "calm",
    "bamboohr",
    "thinking-machine-labs",
    # PR 71 21:00 expand
    "trusona",
    # PR 72 21:53 expand
    "zerotier",
    "cloudbees",
    "cognite",
    "deputy",
    "alibaba-cloud",
    "diligent-corporation",
    # PR 75 22:59 expand
    "global-relay",
    "outsystems",
    "perforce",
    # PR 77 00:00 expand
    "smartbear-software",
    "scaleway",
    "sinch-ab",
    "surveymonkey",
    "ukg",
    "booksy",
    "zuora",
    # PR 79 00:54 expand (also the live report batch)
    "activecampaign",
    "kiteworks",
    "mailgun",
    "kampyle",
    "comm100",
    "planview",
    "powtoon",
    "typeform",
    # PR 80 register-walk leftover + this cut (report previously overwritten by expand)
    "bigtime-enterprise-psa",
    "readdle",
    "quickbase",
    "decagon",
    "insightly",
    "altium",
    "progress-software",
    "avaloq",
    "nvidia",
    "bill",
    "grafana-labs",
    "brave-software",
    "apple",
    "autodesk",
    "digi-international",
    "genesys",
    "servicenow",
    "liquidplanner",
    "bettercloud",
    "aras-corp",
    "mileiq",
    "sambanova",
    "activeops",
    "airship",
    "bluevoyant",
    "corelight",
    "honeybook",
    "agora",
    "deltek",
    "athenahealth",
    "xylem-inc",
    "american-megatrends",
    "meta",
    "coactive-ai",
    "forter",
    "aptitude-software",
    "crusoe",
    "docebo",
    "energycap",
    "esentire",
    # PR 88 02:53 expand
    "indeni",
    "guesty",
    "ex-libris-group",
    # PR 90 16:53 expand
    "lightricks",
    "optimove",
    "sapiens-international-corporation",
    "sisense",
    "snappy-gifts",
    "rollout-io",
    # PR 98 24 Aug expand (also the live report batch)
    "aveva",
    "bromcom",
    "faculty",
    "kraken-technologies",
    "activestate",
    "altus-group",
    # PR 99 / expand overwrite (live report before this cut)
    "langchain",
    "appian",
    "indinero",
    "forescout",
    "luminance",
    "guidewire",
    "lightspeed-commerce",
    "zerofox",
    "avepoint",
    "expensify",
    "pdf-solutions",
    "veritone",
    "wells-fargo",
    "nationwide-mutual-insurance-company",
    "koch",
    "fico",
    "leidos",
    "leidos-holdings",
    "trimble",
    "teradata",
    "bmc-software",
    "dassault-systemes",
    "cigna",
    "cdw",
    "cisco-systems",
    "beyondtrust",
    "sophos",
    "kainos",
    "8x8",
    "sps-commerce",
    "citrix",
    "sonicwall",
    "eset",
    "netapp",
    "audiocodes",
    "ebay",
    "bank-of-america",
    "on24",
    "infoblox",
    "nuix",
    # PR 104 JS shells — do not retry
    "intrahealth-systems-limited",
    "prontoforms",
    "versapay",
    # PR 106 (also the previous live report batch)
    "qualys",
    "zoominfo",
    "mckesson-corporation",
    "pfizer",
    "bitdefender",
    "blackline",
    "acronis",
    "logmein",
    "mimecast",
    "ringcentral",
    "sendio",
    "arista-networks",
    "nebius",
    "coveo",
    "checkmarx",
    "veracode",
    "yext",
    "broadridge",
    "extrahop",
    "similarweb",
    "zeta-global",
    "phunware",
    "sprinklr",
    "the-trade-desk",
    "snap",
    "zoom-video",
    "doordash",
    "instacart",
    "ncino",
    "riskified",
    "illumio",
    "lyft",
    "vast-data",
    "cerebras",
    "clarivate",
    "admicom",
    "allegion",
    "aqua-security",
    "audioeye",
    "axon-enterprise",
    # PR 108 / 110 expand fills — do not retry
    "software-ag",
    "signavio",
    "dubber",
    # PR 112 (previous live report batch)
    "baxter-international",
    "commvault",
    "csg-international",
    "dexcom",
    "digital-turbine",
    "donnelley-financial-solutions",
    "eplus",
    "ge-aerospace",
    "gigamon",
    "iress",
    "johnson-controls",
    "kinaxis",
    "knowbe4",
    "kwai",
    "lime-technologies",
    "netscout",
    "orca-security",
    "pexip",
    "pulsar-group",
    "rekor-systems",
    "resmed",
    "sage",
    "seagate-technology",
    "servicetitan",
    "stryker-corporation",
    "t-mobile-us",
    "toast",
    "tribal-group",
    "usio",
    "vtex",
    "withsecure",
    "watchguard",
    "texas-instruments",
    "opentext",
    "newegg",
    "malwarebytes",
    "gen-digital",
    "craigslist",
    "f5",
    "meta-platforms",
    # PR 113 Episerver / Qlik / Pronto — do not retry
    "episerver",
    "qlik",
    "pronto-software",
    # this cut — unread first-party queue after PR 112/113 (honest zeros)
    "nucleus-software-exports",
    "walmart",
    # leftover open files with only portal / CMP hosts — no first-party HTML to read
    "onetrust",
    "epic-systems",
    "exabeam",
    "constellation-energy",
    "sopra-steria",
    "domo",
    # PR 123 — unread first-party queue after PR 114/122 (fills + honest zeros)
    "y-soft",
    "tricentis",
    "trustly",
    "frosmo",
    "projectmanager-com",
    "esko",
    # PR 119 / 125 trust-URL leftovers — honest DPA/processor zeros; no new first-party HTML
    "superoffice",
    "genedata",
    "eleks",
    # this cut — DPA on file, named processors empty (fills + honest zeros)
    "clio",
    "freshworks",
    "cato-networks",
    "snyk",
    "celonis",
    "veriff",
    "brex",
    "vanta",
    "honeycomb",
    "lucidworks",
    "datalogics",
    "algolia",
    "pipedrive",
    "attentive",
    "cs-disco",
    "synerise",
    "snowflake",
    "imperva",
    "idrive-inc",
    "ramp",
    "evenup",
    "varonis-systems",
    "cloudflare",
    "sprout-social",
    "darktrace",
    "launchdarkly",
    "deel",
    "red-canary",
    "guild",
    "classranked",
    "mixpanel",
    "midjourney",
    "aerospike",
    "xai",
    "boomi-lp",
    "salt-security",
    "caspio",
    "diebold-nixdorf",
    "paylocity",
    "procore",
    # PR 132 — leftover DPA-on-file empty named-processor lists
    "anysphere",
    "glossgenius",
    "braze",
    "photoroom",
    "pagaya",
    "teamviewer",
    "ibotta",
    # PR 136 — leftover DPA-on-file empty list + unread first-party DPA queue
    "synap",
    "blackboard",
    "foxit-software",
    "codesignal",
    "earnin",
    "renaissance-learning",
    "inmobi",
    "zafin",
    # PR 131 instrument leftover — AfterShip DPA already on file; named processors filed
    "aftership",
    # PR 137 / 139 / 142 / 145 / 148 instrument leftovers — DPA/processors already walked
    "opengov",
    "aptean",
    "sap-ariba",
    "qad-redzone",
    "telestream",
    "ctsi-global",
    "seqera-labs",
    "beck-technology",
    "sherpa-ai",
    "walkme",
    "virtutech",
    "pubnub",
    "canonical",
    "percona",
    "agility-robotics",
    "berkshire-grey",
    # PR 149 — portal-catalog DPA upgrades + unread first-party privacy-page queue
    "1password",
    "navan",
    "vercel",
    "twilio",
    "dialpad",
    "check-point",
    "trip-com",
    "gb-group",
    "first-solar",
    "alfa-financial-software",
    "mitek-systems",
    "consolidated-edison",
    "brown-forman",
    "american-water-works",
    "echostar",
    "danaher-corporation",
    "synaptics",
    "blackrock",
    "tencent",
    "genius-sports",
    "klarna",
    "nagarro",
    "sea-limited",
    "character-ai",
    "fiserv",
    "stitch-fix",
    "freee-k-k",
    "backblaze",
    "cboe-global-markets",
    "travelport",
    "verisign",
    "amcor",
    "abbott-laboratories",
    "american-international-group",
    "aflac",
    "jabil",
    "micron-technology",
    "valero-energy",
    "aes-corporation",
    "centene",
    # PR 151 / 153 instrument leftovers — DPA/processors already walked
    "peak",
    "translated",
    "anaplan",
    "sarvam-ai",
    "salesloft",
    "verint-systems",
    "thoughtspot",
    # this cut — unread first-party privacy-page queue after PR 149 (honest zeros)
    "phreesia",
    "corpay",
    "huawei",
    "materialise-nv",
    "schr-dinger",
    "zensar-technologies",
    "planisware",
    "align-technology",
    "paycom",
    "on-semiconductor",
    "globant",
    "4dmedical-limited",
    "bytedance",
    "cyngn",
    "system1",
    "cellebrite",
    "applied-digital",
    "3d-systems",
    "3i-infotech",
    "a-o-smith",
    "accenture",
    "agilysys",
    "aiforia-technologies-oyj",
    "albemarle-corporation",
    "alexandria-real-estate-equities",
    "alibaba",
    "alkami",
    "alliant-energy",
    "amadeus",
    "amdocs",
    "ameren",
    "american-electric-power",
    "american-express",
    "ametek",
    "amgen",
    "aptiv",
    "arthur-j-gallagher-and-co",
    "assurant",
    "at-and-t",
    "atmos-energy",
    # this cut — upper-quadrant subprocessors batch (40 attempted, 9 filed)
    "uniphore",
    "logic-monitor",
    "sentry",
    "modsquad",
    "linear",
    "mux",
    "ory-corp",
    "ovhcloud",
    "workos",
    "teleport",
    "captionhub",
    "zerobounce",
    "matillion",
    "scalekit",
    "clerk",
    "appcues",
    "arkose-labs",
    "front",
    "incident-io",
    "moveworks",
    "sendmarc",
    "stream-io",
    "messagebird",
    "inworld",
    "clari",
    "nium",
    "g2",
    "daily",
    "day-ai",
    "wizy-io",
    "pypestream",
    "clazar",
    "assemblyai",
    "trello",
    "qualified-com",
    "tinybird",
    "mapbox",
    "clearfeed",
    "opensesame-inc",
    "cognition-ai",
    # this cut — upper-quadrant subprocessors batch (40 attempted, 8 filed)
    "sam-labs",
    "databank",
    "ideogram-ai",
    "ironclad",
    "lovable",
    "plain",
    "rollbar",
    "supportlogic",
    "veed",
    "sportradar",
    "riverbed-technology",
    "liveblocks",
    "susea",
    "bluebeam-software-inc",
    "forethought-technologies",
    "deepjudge",
    "84codes-cloudamqp",
    "intershop-communications",
    "playerzero",
    "6sense",
    "edinvent-accredible",
    "cartesia",
    "cognition",
    "jasper-ai",
    "posthog",
    "sigma",
    "upwind",
    "ziflow",
    "hostinger",
    "trulioo",
    "apideck",
    "lumana",
    "ably",
    "astronomer",
    "smallestai",
    "synadia-cloud",
    "yellowai",
    "recall-ai",
    "apollo-io",
    "client-success",
    # this cut — upper-quadrant subprocessors batch (40 attempted, 4 filed)
    "heygen",
    "skilljar",
    "turbopuffer",
    "ketch",
    "braintrust",
    "gladia",
    "level-ai",
    "partnerstack",
    "lambdatest",
    "latitude-sh",
    "obsidian-security",
    "openrouter",
    "pinecone",
    "surveysparrow",
    "zello",
    "modal",
    "smint-io",
    "forest-admin",
    "postmark",
    "accelq",
    "adaptavist",
    "giga",
    "hg-insights",
    "uber",
    "uber-technologies",
    "browser-use",
    "wasabi",
    "eficode",
    "totango",
    "simbian",
    "anam",
    "eliseai",
    "lg-electronics",
    "reflection",
    "serval",
    "spycloud",
    "straiker",
    "tally-solutions",
    "swan",
    "coralogix",
    # this cut — upper-quadrant subprocessors batch (40 attempted, 4 filed)
    "tensorwave",
    "freightos",
    "serko-limited",
    "planet-labs",
    "help-scout",
    "vyond",
    "naseej",
    "beamery",
    "nylas",
    "wingify",
    "gandi",
    "formstack",
    "wrike",
    "morning-consult",
    "lastpass",
    "maven-agi",
    "elastic-io",
    "model-n",
    "infobip",
    "incountry",
    "macstadium",
    "segment",
    "matterport",
    "ant-international",
    "identity-automation-lp",
    "markmonitor",
    "gmo-globalsign",
    "digital-realty",
    "iterable",
    "omni-analytics",
    "rackspace",
    "recurly-com",
    "relx-d-b-a-lexisnexis",
    "bitpay",
    "shortcut-software",
    "orum",
    "spotdraft",
    "bandwidth-inc",
    "lyzr",
    "speechmatics",
    # this cut — upper-quadrant subprocessors batch (40 attempted, 2 filed)
    "rime",
    "bigpanda",
    "cognism",
    "descope",
    "geordie-ai",
    "heroku",
    "lumen-technologies",
    "workvivo",
    "dash0",
    "blue-yonder",
    "panther-labs",
    "tietoevry",
    "impartner",
    "smarsh",
    "cronofy",
    "productboard",
    "scylladb",
    "temporal",
    "youmail",
    "maxmind",
    "intuition-machines-hcaptcha",
    "imerit",
    "voltage-park",
    "flatfile",
    "plume",
    "dwolla",
    "wealthsimple",
    "metabase",
    "stytch",
    "actively-ai",
    "appen",
    "lightspeed-systems",
    "shippo",
    "cesiumastro",
    "krisp",
    "bright-data",
    "enterpret",
    "lob-com",
    "neon",
    "nightfall",
}


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


def first_party_candidates(public: dict, enr: dict) -> list[tuple[str, str]]:
    """URLs already on the file that we may read. Portal hosts stay out."""
    out, seen = [], set()

    def add(kind: str, url: str) -> None:
        u = (url or "").strip()
        if not u.startswith("http"):
            return
        key = u.lower()
        if key in seen:
            return
        if not enrich.is_first_party_url(u, enr):
            return
        seen.add(key)
        out.append((kind, u))

    links = enr.get("links") or {}
    for kind in ("trust", "security", "privacy", "dpa", "subprocessors"):
        add(kind, links.get(kind) or "")
    add("trust_url", public.get("trust_url") or "")
    add("final_url", public.get("final_url") or "")
    add("enr_trust", enr.get("trust_url") or "")
    add("enr_final", enr.get("final_url") or "")
    for key in ("trust", "security", "privacy", "dpa", "subprocessors"):
        add(key, instrument_url(public, key))
    return out


def requested_slugs() -> list[str]:
    """Optional argv slugs. Empty means the next ~40 open DPA/subprocessor files."""
    return [a.strip() for a in sys.argv[1:] if a.strip() and not a.startswith("-")]


def previous_batch() -> set[str]:
    """Skip companies already attempted on the last increment. Do not retry them."""
    prior = {slug for slug in (load_json(REPORT, {}).get("batch") or []) if slug}
    prior.update(PRIOR_ATTEMPTED)
    return prior


def dpa_is_portal_catalog(url: str) -> bool:
    """SafeBase-style itemUid / itemName catalogs are not a printed first-party DPA."""
    return bool(enrich.ITEM_UID_RE.search(url or ""))


def stored_dpa_url(row: dict, enr: dict) -> str:
    """Public instrument first, then the enriched links.dpa the queue is keyed on."""
    return instrument_url(row, "dpa") or ((enr.get("links") or {}).get("dpa") or "").strip()


def has_trust_privacy_security(cands: list[tuple[str, str]]) -> bool:
    return any(kind in {"trust", "security", "privacy", "trust_url", "enr_trust"} for kind, _ in cands)


def select_batch(public_rows: list[dict], enr_by: dict[str, dict]) -> list[dict]:
    wanted = requested_slugs()
    skip = set() if wanted else previous_batch()
    by_pub = {row.get("slug"): row for row in public_rows if row.get("slug")}
    rows = [by_pub[s] for s in wanted if s in by_pub] if wanted else public_rows
    picked = []
    picked_slugs: set[str] = set()

    def consider(row: dict, *, force_sub_open: bool | None = None) -> dict | None:
        slug = row.get("slug") or ""
        if not slug or slug in skip or slug in picked_slugs:
            return None
        enr = enr_by.get(slug)
        if not enr:
            return None
        cands = first_party_candidates(row, enr)
        if not cands:
            return None
        # Found-company DPA queue is exhausted after PRIOR. Silent rows with a
        # stored first-party trust/privacy/security URL are the next unread file.
        if not row.get("found") and not has_trust_privacy_security(cands):
            return None
        dpa_url = stored_dpa_url(row, enr)
        dpa_open = not dpa_url
        # Portal catalog DPA may be upgraded to a printed first-party DPA. Never drop.
        dpa_upgrade = bool(dpa_url and dpa_is_portal_catalog(dpa_url))
        sub_open = not (row.get("processors") or []) if force_sub_open is None else force_sub_open
        if not (dpa_open or dpa_upgrade or sub_open):
            return None
        return {
            "slug": slug,
            "name": row.get("name") or slug,
            "dpa_open": dpa_open,
            "dpa_upgrade": dpa_upgrade,
            "sub_open": sub_open,
            "candidates": cands,
        }

    if wanted:
        for row in rows:
            rec = consider(row)
            if rec:
                picked.append(rec)
                picked_slugs.add(rec["slug"])
        return picked

    # (a) links.dpa on file, named processors empty, not in PRIOR.
    for row in public_rows:
        enr = enr_by.get(row.get("slug") or "")
        if not enr:
            continue
        dpa_url = stored_dpa_url(row, enr)
        if not dpa_url or (row.get("processors") or []):
            continue
        rec = consider(row, force_sub_open=True)
        if rec:
            picked.append(rec)
            picked_slugs.add(rec["slug"])
            if len(picked) >= BATCH:
                return picked

    # (b) portal-catalog DPA that may upgrade to printed first-party HTML.
    # Existing named processors stay; only the DPA URL is in scope.
    for row in public_rows:
        if len(picked) >= BATCH:
            return picked
        enr = enr_by.get(row.get("slug") or "")
        if not enr:
            continue
        dpa_url = stored_dpa_url(row, enr)
        if not (dpa_url and dpa_is_portal_catalog(dpa_url)):
            continue
        rec = consider(row)
        if rec:
            picked.append(rec)
            picked_slugs.add(rec["slug"])

    # (c) trust/privacy/security first-party URLs, no DPA link yet, not in PRIOR.
    # Includes silent rows: found-company open-DPA queue is exhausted.
    for row in public_rows:
        enr = enr_by.get(row.get("slug") or "")
        if not enr:
            continue
        if stored_dpa_url(row, enr):
            continue
        rec = consider(row)
        if not rec or not has_trust_privacy_security(rec["candidates"]):
            continue
        picked.append(rec)
        picked_slugs.add(rec["slug"])
        if len(picked) >= BATCH:
            break
    return picked


def fetch_seed(url: str) -> dict:
    try:
        return enrich.fetch_seed_page(url)
    except Exception:
        return {"ok": False, "status": 0, "final_url": url, "hrefs": [], "html": "", "title": "", "text": ""}


def fetch_verify(url: str, *, list_page: bool) -> dict:
    try:
        if list_page:
            return enrich.fetch_processor_page(url)
        body = enrich.TRUST_BODY if str(url).lower().endswith(".pdf") else enrich.PROBE_BODY
        return enrich.fetch_uncached(url, body)
    except Exception:
        return {"ok": False, "status": 0, "final_url": url, "title": "", "text": "", "html": "", "ctype": ""}


def append_processor_edges(edges: list[dict], register: dict[str, dict]) -> None:
    """Append sourced edges and only the nodes those edges name. Do not dump the register."""
    paths = (DATA / "subprocessors.json", SITE / "data" / "subprocessors.json")
    src = paths[0] if paths[0].exists() else paths[1]
    subs = load_json(src, {"nodes": [], "edges": []})
    nodes = {n["id"]: n for n in (subs.get("nodes") or []) if n.get("id")}
    existing = {(e.get("from"), e.get("to")) for e in (subs.get("edges") or [])}
    proc_meta = {i: (n, d) for i, n, d, _a in enrich.PROCESSORS}
    for e in edges:
        src_url, frm, to = e.get("source_url"), e.get("from"), canonical_processor_id(e.get("to"), register)
        if not src_url or not frm or not to or (frm, to) in existing:
            continue
        subs.setdefault("edges", []).append({
            "from": frm,
            "to": to,
            "source_url": src_url,
            "evidence": e.get("evidence") or to,
        })
        existing.add((frm, to))
        if to in nodes:
            continue
        if to in register:
            nodes[to] = {
                "id": to,
                "name": register[to].get("name") or to,
                "domain": register[to].get("domain") or "",
                "kind": "company",
                "in_register": True,
            }
        else:
            name, domain = proc_meta.get(to, (e.get("evidence") or to, ""))
            nodes[to] = {
                "id": to,
                "name": name,
                "domain": domain,
                "kind": "processor",
                "in_register": False,
            }
        if frm not in nodes and frm in register:
            nodes[frm] = {
                "id": frm,
                "name": register[frm].get("name") or frm,
                "domain": register[frm].get("domain") or "",
                "kind": "company",
                "in_register": True,
            }
    subs["nodes"] = list(nodes.values())
    for path in paths:
        write_json(path, subs)


def public_url(url: str) -> str:
    """Drop login tokens and itemUids from the reject ledger."""
    u = (url or "").split("#")[0].strip()
    if "itemUid=" in u or "inviteToken=" in u or "loginRequest=" in u:
        return u.split("?", 1)[0]
    return u


def uniq_urls(urls: list[str]) -> list[str]:
    out, seen = [], set()
    for u in urls:
        key = (u or "").rstrip("/").lower()
        if not key.startswith("http") or key in seen:
            continue
        seen.add(key)
        out.append(u)
    return out


def main() -> int:
    t0 = time.time()
    public = load_json(PUBLIC, {})
    enr = load_json(ENRICHED, {})
    public_rows = list(public.get("companies") or [])
    companies = list(enr.get("companies") or [])
    enr_by = {c["slug"]: c for c in companies if c.get("slug")}
    register = {c["slug"]: c for c in companies if c.get("slug")}

    batch = select_batch(public_rows, enr_by)
    print(f"batch {len(batch)} companies with an open DPA or subprocessors rule", flush=True)
    for rec in batch:
        print(
            f"  {rec['slug']} dpa_open={rec['dpa_open']} dpa_upgrade={rec.get('dpa_upgrade')} "
            f"sub_open={rec['sub_open']} urls={len(rec['candidates'])}",
            flush=True,
        )

    seed_jobs = []
    seen_seed = set()
    for rec in batch:
        row = enr_by[rec["slug"]]
        for kind, url in rec["candidates"]:
            key = (rec["slug"], url.lower())
            if key in seen_seed:
                continue
            seen_seed.add(key)
            seed_jobs.append((rec["slug"], kind, url))

    print(f"phase 1: read {len(seed_jobs)} on-file first-party pages", flush=True)
    dpa_cands: dict[str, list[str]] = {
        rec["slug"]: [] for rec in batch if rec["dpa_open"] or rec.get("dpa_upgrade")
    }
    sub_cands: dict[str, list[str]] = {rec["slug"]: [] for rec in batch if rec["sub_open"]}
    rejected: list[dict] = []

    def take_dpa(slug: str, url: str) -> None:
        bucket = dpa_cands.get(slug)
        if bucket is None:
            return
        if url not in bucket:
            bucket.append(url)

    def take_sub(slug: str, url: str) -> None:
        bucket = sub_cands.get(slug)
        if bucket is None:
            return
        if url not in bucket:
            bucket.append(url)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(fetch_seed, url): (slug, kind, url) for slug, kind, url in seed_jobs}
        done = 0
        for fut in as_completed(futs):
            slug, kind, url = futs[fut]
            rec = fut.result()
            done += 1
            if done % 20 == 0 or done == len(futs):
                print(f"  seed {done}/{len(futs)}", flush=True)
            row = enr_by.get(slug)
            if not row:
                continue
            final = rec.get("final_url") or url
            if rec.get("ok") and rec.get("status") == 200 and enrich.is_first_party_url(final, row):
                html = rec.get("html") or ""
                base = final
                if slug in dpa_cands:
                    for href in enrich.extract_dpa_candidates(html, base):
                        if enrich.is_first_party_url(href, row) and not dpa_is_portal_catalog(href):
                            take_dpa(slug, href)
                    for href in rec.get("hrefs") or []:
                        if (
                            enrich.DPA_PATH_RE.search(href)
                            and enrich.is_first_party_url(href, row)
                            and not dpa_is_portal_catalog(href)
                        ):
                            take_dpa(slug, href)
                    if kind == "dpa" and not dpa_is_portal_catalog(final):
                        take_dpa(slug, final)
                if slug in sub_cands:
                    for href in enrich.extract_subprocessor_candidates(html, base):
                        if enrich.is_first_party_url(href, row) and not dpa_is_portal_catalog(href):
                            take_sub(slug, href)
                    if kind == "subprocessors" and not dpa_is_portal_catalog(final):
                        take_sub(slug, final)
            elif kind in {"dpa", "subprocessors"}:
                rejected.append({"slug": slug, "url": public_url(url), "reason": "seed-not-live", "kind": kind})

    for rec in batch:
        row = enr_by[rec["slug"]]
        if rec["dpa_open"] or rec.get("dpa_upgrade"):
            for url in enrich.dpa_probe_urls_for(row):
                if enrich.is_first_party_url(url, row) and not dpa_is_portal_catalog(url):
                    take_dpa(rec["slug"], url)
        if rec["sub_open"]:
            stored_dpa = (row.get("links") or {}).get("dpa") or ""
            if (
                stored_dpa
                and enrich.is_first_party_url(stored_dpa, row)
                and not dpa_is_portal_catalog(stored_dpa)
            ):
                take_sub(rec["slug"], stored_dpa)
            for url in enrich.subprocessor_probe_urls_for(row):
                if enrich.is_first_party_url(url, row) and not dpa_is_portal_catalog(url):
                    take_sub(rec["slug"], url)

    dpa_jobs, sub_jobs = [], []
    for slug, urls in dpa_cands.items():
        row = enr_by[slug]
        for url in uniq_urls(urls):
            if enrich.is_first_party_url(url, row):
                dpa_jobs.append((slug, url))
    for slug, urls in sub_cands.items():
        row = enr_by[slug]
        for url in uniq_urls(urls):
            if enrich.is_first_party_url(url, row):
                sub_jobs.append((slug, url))

    print(f"phase 2: verify {len(dpa_jobs)} DPA candidates, {len(sub_jobs)} list candidates", flush=True)
    accepted_dpa: dict[str, str] = {}
    accepted_sub: dict[str, tuple[str, list]] = {}

    def do_dpa(job):
        slug, url = job
        rec = fetch_verify(url, list_page=False)
        return slug, url, rec

    def do_sub(job):
        slug, url = job
        rec = fetch_verify(url, list_page=True)
        return slug, url, rec

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(do_dpa, job) for job in dpa_jobs]
        done = 0
        for fut in as_completed(futs):
            slug, url, rec = fut.result()
            done += 1
            if done % 20 == 0 or done == len(futs):
                print(f"  dpa {done}/{len(futs)}", flush=True)
            if slug in accepted_dpa:
                continue
            row = enr_by.get(slug)
            if not row:
                continue
            final = rec.get("final_url") or url
            if not enrich.is_first_party_url(final, row) or dpa_is_portal_catalog(final):
                rejected.append({"slug": slug, "url": public_url(url), "final": public_url(final), "reason": "not-first-party", "kind": "dpa"})
                continue
            if not enrich.classify_as_dpa(url, rec):
                reason = "not-a-dpa"
                if not rec.get("ok") or rec.get("status") != 200:
                    reason = f"http-{rec.get('status') or 0}"
                elif enrich.looks_like_login_wall(rec.get("title") or "", rec.get("text") or ""):
                    reason = "login-wall"
                elif enrich.looks_dead(rec.get("title") or "", rec.get("text") or ""):
                    reason = "soft-404"
                elif enrich.landed_on_home(url, final):
                    reason = "homepage-bounce"
                rejected.append({"slug": slug, "url": public_url(url), "final": public_url(final), "reason": reason, "kind": "dpa"})
                continue
            accepted_dpa[slug] = final

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(do_sub, job) for job in sub_jobs]
        done = 0
        for fut in as_completed(futs):
            slug, url, rec = fut.result()
            done += 1
            if done % 20 == 0 or done == len(futs):
                print(f"  sub {done}/{len(futs)}", flush=True)
            if slug in accepted_sub:
                continue
            row = enr_by.get(slug)
            if not row:
                continue
            final = rec.get("final_url") or url
            skip = enrich.cited_list_skip_reason(url, rec, row)
            if skip:
                rejected.append({"slug": slug, "url": public_url(url), "final": public_url(final), "reason": skip, "kind": "subprocessors"})
                continue
            procs = enrich.published_processors_from_cited(row, rec, url, register)
            if not procs:
                rejected.append({"slug": slug, "url": public_url(url), "final": public_url(final), "reason": "no-printed-names", "kind": "subprocessors"})
                continue
            dated = [n for _i, n, _e in procs if enrich.looks_like_date_name(n)]
            procs = [
                (i, n, e)
                for i, n, e in procs
                if not enrich.looks_like_date_name(n) and not skip_processor(i, n)
            ]
            if dated:
                rejected.append({"slug": slug, "url": public_url(url), "reason": "date-shaped-names", "kind": "subprocessors", "dropped": dated})
            if not procs:
                rejected.append({"slug": slug, "url": public_url(url), "reason": "only-dates", "kind": "subprocessors"})
                continue
            accepted_sub[slug] = (final, procs)

    def file_dpa_url(row: dict, url: str) -> bool:
        """File a new DPA, or upgrade a portal catalog. Never drop a stored DPA."""
        if not url:
            return False
        links = dict(row.get("links") or {})
        existing = (links.get("dpa") or "").strip()
        if not existing:
            return enrich.apply_dpa_to_row(row, url)
        if existing.rstrip("/") == url.rstrip("/"):
            return False
        if not dpa_is_portal_catalog(existing):
            return False
        if dpa_is_portal_catalog(url):
            return False
        links["dpa"] = url
        row["links"] = links
        return True

    def file_list_url(row: dict, url: str) -> None:
        """Point at the first-party page that printed names. Never clear a stored list URL."""
        if not url:
            return
        links = dict(row.get("links") or {})
        existing = (links.get("subprocessors") or "").strip()
        if not existing:
            enrich.apply_subprocessors_to_row(row, url)
            return
        if existing.rstrip("/") == url.rstrip("/"):
            return
        if dpa_is_portal_catalog(url) and not dpa_is_portal_catalog(existing):
            return
        links["subprocessors"] = url
        row["links"] = links

    filed_dpa, filed_sub = [], []
    new_edges = []
    for slug, url in sorted(accepted_dpa.items()):
        row = enr_by[slug]
        if file_dpa_url(row, url):
            filed_dpa.append({"slug": slug, "name": row.get("name") or slug, "url": url})

    for slug, (url, procs) in sorted(accepted_sub.items()):
        row = enr_by[slug]
        file_list_url(row, url)
        row["subprocessors"] = [pid for pid, _n, _e in procs]
        filed_sub.append({
            "slug": slug,
            "name": row.get("name") or slug,
            "url": url,
            "names": [n for _i, n, _e in procs],
        })
        for pid, name, ev in procs:
            new_edges.append({
                "from": slug,
                "to": pid,
                "source_url": url,
                "evidence": ev or name,
            })

    if new_edges:
        append_processor_edges(new_edges, register)

    write_json(ENRICHED, enr)
    write_json(DATA / "enriched.json", enr)

    stayed = []
    for rec in batch:
        dpa_filed = any(x["slug"] == rec["slug"] for x in filed_dpa)
        sub_filed = any(x["slug"] == rec["slug"] for x in filed_sub)
        if rec["dpa_open"] and not dpa_filed:
            stayed.append({"slug": rec["slug"], "name": rec["name"], "rule": "dpa"})
        if rec["sub_open"] and not sub_filed:
            stayed.append({"slug": rec["slug"], "name": rec["name"], "rule": "subprocessors"})

    report = {
        "generated_at": enr.get("generated_at"),
        "rule": (
            "Next ~40 companies: first those with links.dpa on file and an empty "
            "named-processor list, then portal-catalog DPAs that may upgrade to "
            "printed first-party HTML, then those with first-party trust/privacy/"
            "security URLs and no DPA link yet (including silent rows once the "
            "found-company queue is exhausted). Named subprocessors fill only "
            "from printed organization names in live first-party HTML tables or "
            "labeled spans. A stored list URL with no printed names stays open. "
            "A DPA is filed only when a printed first-party DPA is newly found; "
            "an existing DPA is never dropped. Dates, JS shells, login walls, "
            "PDF-only lists, affiliate-only rows, and portal catalogs stay open."
        ),
        "batch": [rec["slug"] for rec in batch],
        "dpa_filed": filed_dpa,
        "subprocessors_filed": filed_sub,
        "stayed_open": stayed,
        "rejected": rejected,
    }
    write_json(REPORT, report)

    print(f"filed dpa={len(filed_dpa)} named-subprocessors={len(filed_sub)} "
          f"stayed={len(stayed)} rejected={len(rejected)} in {time.time() - t0:.1f}s", flush=True)
    for row in filed_dpa:
        print(f"  + dpa {row['slug']} {row['url']}", flush=True)
    for row in filed_sub:
        print(f"  + sub {row['slug']} {len(row['names'])} {row['url']}", flush=True)
    for row in stayed:
        print(f"  - open {row['slug']} {row['rule']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
