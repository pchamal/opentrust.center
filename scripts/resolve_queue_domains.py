#!/usr/bin/env python3
"""Fill missing first-party domains on queued names, then expand/enrich those rows.

Does not add new lists. Wikipedia / Crunchbase / news hosts are never filed as
the company domain. Unverified names stay null.
"""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urlencode, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import crawl  # noqa: E402
import enrich  # noqa: E402
from expand_batch import extract_certs, to_record  # noqa: E402
from merge_render import rescore  # noqa: E402

DATA = ROOT / "data"
QUEUE = DATA / "crawl-queue.json"
ENRICHED = DATA / "enriched.json"
SITE_ENRICHED = ROOT / "site" / "data" / "enriched.json"
SUB = DATA / "subprocessors.json"
SITE_SUB = ROOT / "site" / "data" / "subprocessors.json"
LOG = DATA / "queue-domain-resolve.json"
WORKERS = 10
WD_WORKERS = 2

DIRECTORY_HOSTS = {
    "wikipedia.org", "wikimedia.org", "wikidata.org", "crunchbase.com",
    "linkedin.com", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "youtube.com", "forbes.com", "bloomberg.com", "reuters.com", "nytimes.com",
    "wsj.com", "techcrunch.com", "pitchbook.com", "trustradius.com", "g2.com",
    "glassdoor.com", "medium.com", "substack.com", "google.com", "bing.com",
    "yahoo.com", "apple.com", "play.google.com", "apps.apple.com",
    "github.com", "gitlab.com", "aiworld.lat", "companiesmarketcap.com",
    "crn.com", "cloudindex.bvp.com", "bvp.com", "sec.gov", "marketwatch.com",
    "businesswire.com", "prnewswire.com", "owler.com", "zoominfo.com",
    "dnb.com", "opencorporates.com", "fandom.com", "reddit.com",
    "amazon.com", "amazonaws.com", "shopify.com", "squarespace.com",
    "wix.com", "wordpress.com", "blogspot.com", "tumblr.com",
}

FOR_SALE = re.compile(
    r"(for sale|domain (is )?for sale|buy this domain|parked free|"
    r"this domain (is parked|may be for sale)|spaceship\.com|"
    r"hugedomains|afternic|sedo\.com|dan\.com)",
    re.I,
)
MARKETPLACE_HOSTS = {
    "dynadot.com", "godaddy.com", "sedo.com", "dan.com", "hugedomains.com",
    "afternic.com", "namecheap.com", "spaceship.com", "domainmarket.com",
    "atom.com", "squadhelp.com",
}

REJECT_DOMAINS = {
    "technology-one.com",  # portable surveillance, not Technology One
    "vertex.com",  # not Vertex Inc
    "topicus.ai",  # Topicus N.V. is topicus.com
}

EXTRA_GUESSES = {
    "bytes-technology": ["bytes.co.uk"],
    "domo": ["domo.com"],
    "expel": ["expel.com"],
    "forge-global": ["forgeglobal.com"],
    "gmo-internet": ["gmo.jp"],
    "kfin-technologies": ["kfintech.com"],
    "n-able": ["n-able.com"],
    "saic": ["saic.com"],
    "sopra-steria": ["soprasteria.com"],
    "soundhound-ai": ["soundhound.com"],
    "technology-one": ["technologyone.com"],
    "topicus": ["topicus.com"],
    "varonis": ["varonis.com"],
    "vertex": ["vertexinc.com"],
    "weave": ["getweave.com"],
    "z-ai": ["z.ai"],
    "zeta": ["zetaglobal.com"],
    "armis": ["armis.com"],
    "barracuda": ["barracuda.com"],
    "alight": ["alight.com"],
    "certara": ["certara.com"],
    "siteminder": ["siteminder.com"],
    "menlo-security": ["menlosecurity.com"],
    "exabeam": ["exabeam.com"],
    "forescout": ["forescout.com"],
    "safebreach": ["safebreach.com"],
    "salt-security": ["salt.security"],
    "intapp": ["intapp.com"],
    "vectra-ai": ["vectra.ai"],
    "devo": ["devo.com"],
    "torq": ["torq.io"],
    "airship-ai": ["airship.ai"],
    "ccc-intelligent-solutions": ["cccis.com"],
    "cs-disco": ["csdisco.com"],
    "cigniti-technologies": ["cigniti.com"],
    "i3-verticals": ["i3verticals.com"],
    "qoria": ["qoria.com"],
    "red-violet": ["redviolet.com"],
    "research-solutions": ["researchsolutions.com"],
    "rimini-street": ["riministreet.com"],
    "shift": ["shiftinc.jp"],
    "m3": ["m3.com"],
    "pinewood-technologies": ["pinewood.co.uk"],
    "acceso-technology": ["accesso.com"],
    "accesso-technology": ["accesso.com"],
    "kellton-tech": ["kellton.com"],
    "accelya": ["accelya.com"],
    "allot": ["allot.com"],
    "almawave": ["almawave.com"],
    "aptitude-software": ["aptitudesoftware.com"],
    "coheris": ["coheris.com"],
    "eagle-eye-solutions": ["eagleeye.com"],
    "emudhra": ["emudhra.com"],
    "freee": ["freee.co.jp"],
    "hansen-technologies": ["hansentec.com"],
    "kneat": ["kneat.com"],
    "lemonsoft": ["lemonsoft.fi"],
    "lumine-group": ["luminegroup.com"],
    "mntn": ["mntn.com"],
    "par-technology": ["partech.com"],
    "viant-technology": ["viantinc.com"],
    "wiit": ["wiit.cloud"],
    "cyberhaven": ["cyberhaven.com"],
    "inkeep": ["inkeep.com"],
    "ketch": ["ketch.com"],
    "kickbox": ["kickbox.com"],
    "rootly": ["rootly.com"],
    "spekit": ["spekit.com"],
    "tropic": ["tropicapp.io"],
    "teleport": ["goteleport.com"],
    "gravitational-teleport": ["goteleport.com"],
    "syniverse-technologies": ["syniverse.com"],
    "language-i-o": ["languageio.com"],
    "imerit": ["imerit.ai"],
    "ai-media": ["ai-media.tv"],
    "ordway": ["ordwaylabs.com"],
    "telecom-italia-sparkle-spa": ["tisparkle.com"],
    "thorn": ["thorn.org"],
    "capacity": ["capacity.com"],
    "textel": ["capacity.com"],
    "summit": ["summithq.com"],
    "deft": ["summithq.com"],
    "enea": ["enea.com"],
    "adaptive-mobile": ["enea.com"],
    "gmi-cloud": ["gmicloud.ai"],
    "gmi": ["gmicloud.ai"],
    "hg-insights": ["hginsights.com"],
    "madkudu": ["hginsights.com"],
    "shenzhen-montnets-technology-development": ["montnets.com"],
    "blackpoint-cyber": ["blackpointcyber.com"],
    "cynomi": ["cynomi.com"],
    "securonix": ["securonix.com"],
    "empyrean-technology": ["empyrean.com.cn"],
    "computer-modelling-group": ["cmgl.ca"],
    "consensus-cloud-solutions": ["consensus.com"],
    "evercommerce": ["evercommerce.com"],
    "shoper": ["shoper.pl"],
    "cockroach-labs": ["cockroachlabs.com"],
    "metabase": ["metabase.com"],
    "lightdash": ["lightdash.com"],
    "loops": ["loops.so"],
    "inworld": ["inworld.ai"],
    "rime": ["rime.ai"],
    "weaviate": ["weaviate.io"],
    "scalekit": ["scalekit.com"],
    "voyage-ai": ["voyageai.com"],
    "apricity-group": ["apricitygroup.com"],
    "apricity": ["apricitygroup.com"],
    "swan": ["getswan.com"],
    "mako-it-lab": ["makoitlab.com"],
    "mako-it-lab-pvt": ["makoitlab.com"],
    "fwd-deploy": ["fwddeploy.ai"],
    "saasgenie": ["fwddeploy.ai"],
    "software-mind": ["softwaremind.com"],
    "software-minds": ["softwaremind.com"],
    "marketstar": ["marketstar.com"],
    "regalix": ["marketstar.com"],
    "codecentric": ["codecentric.de"],
    "cc-cloud": ["codecentric.de"],
    "level-ai": ["thelevel.ai"],
    "ujwal": ["thelevel.ai"],
    "ai-data-innovations": ["aidatainnovations.com"],
    "ai-data-innovation": ["aidatainnovations.com"],
    "cloud-support-technologies": ["cloudsupport.co.in"],
    "amx": ["amxconsulting.com"],
    "agile-management-experts": ["amxconsulting.com"],
    "avertech": ["e2open.com"],
    "mosse-security": ["mosse-security.com"],
    "benjamin-mosse-consulting": ["mosse-security.com"],
    "vector": ["vector.co"],
}

PORTAL_HOSTS = (
    ".safebase.us", ".safebase.io", ".safebase.com",
    ".vantatrust.com", ".trust.site", ".secureframetrust.com",
    ".securitypal.com",
)

# Wikipedia/Wikidata title hints for short or ambiguous queue names only.
HINTS = {
    "360-security-technology": ["Qihoo 360", "360 Security Technology"],
    "agora": ["Agora Inc.", "Agora.io"],
    "alight": ["Alight Solutions"],
    "armis": ["Armis (company)"],
    "barracuda": ["Barracuda Networks"],
    "blend": ["Blend Labs"],
    "bytes-technology": ["Bytes Technology Group"],
    "captions": ["Captions (company)"],
    "certara": ["Certara"],
    "devo": ["Devo (company)", "Devo Inc."],
    "docebo": ["Docebo"],
    "domo": ["Domo, Inc."],
    "empyrean-technology": ["Empyrean Technology"],
    "exabeam": ["Exabeam"],
    "expel": ["Expel (company)"],
    "forge-global": ["Forge Global"],
    "forescout": ["Forescout"],
    "gmo-internet": ["GMO Internet"],
    "infor": ["Infor"],
    "intapp": ["Intapp"],
    "kfin-technologies": ["KFin Technologies"],
    "m3": ["M3, Inc."],
    "n-able": ["N-able"],
    "nice": ["NICE Ltd.", "NICE (company)"],
    "ncr-voyix": ["NCR Voyix"],
    "ovhcloud": ["OVHcloud"],
    "pinewood-technologies": ["Pinewood Technologies"],
    "pinduoduo": ["Pinduoduo", "PDD Holdings"],
    "pinterest": ["Pinterest"],
    "q2": ["Q2 Holdings"],
    "saic": ["Science Applications International Corporation"],
    "salt-security": ["Salt Security"],
    "siteminder": ["SiteMinder"],
    "shift": ["SHIFT Inc."],
    "speak": ["Speak (app)"],
    "technology-one": ["Technology One"],
    "thinking-machine-labs": ["Thinking Machines Lab", "Thinking Machine Labs"],
    "varonis": ["Varonis"],
    "vertex": ["Vertex, Inc.", "Vertex Inc."],
    "waystar": ["Waystar"],
    "weave": ["Weave Communications"],
    "wiz": ["Wiz (company)", "Wiz Inc"],
    "z-ai": ["Zhipu AI", "Z.AI"],
    "zeta": ["Zeta Global"],
}

STOP = {
    "inc", "inc.", "ltd", "llc", "corp", "the", "ai", "group", "technologies",
    "technology", "software", "labs", "lab", "company", "co", "com", "holdings",
    "solutions", "systems", "global", "international", "limited",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n")


def host_of(url: str) -> str:
    return urlparse(url).netloc.lower().split(":")[0].removeprefix("www.")


def registrable(host: str) -> str:
    return enrich.registrable(host)


def domain_of(url: str) -> str | None:
    host = host_of(url or "")
    if not host or "." not in host:
        return None
    parts = host.split(".")
    if len(parts) >= 3 and parts[0] in {
        "trust", "security", "compliance", "assurance", "trustcenter",
        "status", "app", "www", "docs", "blog", "api", "cloud", "us", "uk",
        "eu", "www2",
    }:
        host = ".".join(parts[1:])
    return registrable(host)


def is_directory_host(host: str) -> bool:
    h = (host or "").lower().removeprefix("www.")
    if not h:
        return True
    for blocked in DIRECTORY_HOSTS | MARKETPLACE_HOSTS:
        if h == blocked or h.endswith("." + blocked):
            return True
    if h.startswith("forsale.") or ".forsale." in h:
        return True
    return False


def sld_matches(domain: str, name: str, slug: str) -> bool:
    host = (domain or "").lower().removeprefix("www.")
    sld = host.split(".")[0].replace("-", "")
    compact = compact_name(name)
    slugc = (slug or "").replace("-", "")
    toks = name_tokens(name)
    if not sld:
        return False
    if sld in {compact, slugc, slug} or sld in toks:
        return True
    joined = "".join(toks)

    def stem(s: str) -> str:
        s = re.sub(r"(labs|lab|group|holdings|inc|llc|ltd|tech|software|company)$", "", s)
        return s.rstrip("s")

    if stem(sld) and stem(sld) in {stem(compact), stem(slugc), stem(joined)}:
        return True
    if joined and sld == joined:
        return True
    long = [t for t in toks if len(t) >= 4]
    if any(sld.startswith(t) and 0 < len(sld) - len(t) <= 6 for t in long):
        return True
    if len(long) == 1 and sld == long[0]:
        return True
    return False


def name_tokens(name: str) -> list[str]:
    toks = [t for t in re.findall(r"[a-z0-9]+", (name or "").lower()) if t not in STOP]
    toks = [t for t in toks if len(t) >= 3]
    if toks:
        return toks
    return [t for t in re.findall(r"[a-z0-9]+", (name or "").lower()) if len(t) >= 2]


def page_names_company(name: str, title: str, text: str) -> bool:
    blob = f"{title} {text[:5000]}".lower()
    if not blob.strip():
        return False
    if crawl.PARKING.search(blob) or crawl.SOFT_404.search(blob):
        return False
    toks = name_tokens(name)
    if not toks:
        return bool(re.search(rf"\b{re.escape(name.strip())}\b", blob, re.I))
    return all(t in blob for t in toks)


def compact_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def title_brand(name: str, title: str) -> bool:
    """Guesses: the page title has to lead with this company's name."""
    phrase = re.sub(r"\s+(inc\.?|ltd\.?|llc|corp\.?|co\.?)$", "", (name or "").strip(), flags=re.I)
    t = unescape(re.sub(r"\s+", " ", title or "")).strip()
    if not phrase or not t:
        return False
    if " " in phrase:
        return bool(re.match(rf"{re.escape(phrase)}\b(\s*[|\-–—,:]|s\b|$)", t, re.I))
    return bool(re.search(rf"\b{re.escape(phrase)}\b", t, re.I))


def taken_domains() -> dict[str, str]:
    taken = {}
    for path in (
        ROOT / "companies.json",
        ROOT / "extra-companies.json",
        ENRICHED,
        QUEUE,
    ):
        raw = load_json(path, [])
        rows = raw.get("companies", raw) if isinstance(raw, dict) else raw
        for row in rows or []:
            dom = (row.get("domain") or "").lower().removeprefix("www.")
            slug = row.get("slug") or ""
            if dom and slug:
                taken.setdefault(dom, slug)
                taken.setdefault(registrable(dom), slug)
    return taken


def fetch_home(domain: str) -> dict:
    old = crawl.TIMEOUT
    crawl.TIMEOUT = 15
    try:
        rec = None
        for url in (f"https://{domain}", f"https://www.{domain}"):
            got = crawl.fetch(url, max_body=24576)
            rec = got
            if got.get("ok") and got.get("status") == 200:
                html = got.get("body") or ""
                title = crawl.extract_title(html)
                text = enrich.strip_tags(html)[:8000]
                final = domain_of(got.get("final_url") or url) or domain
                return {
                    "ok": True,
                    "status": got.get("status") or 200,
                    "title": title,
                    "text": text,
                    "final_domain": final,
                    "final_url": got.get("final_url") or url,
                }
        status = (rec or {}).get("status") or 0
        return {
            "ok": False,
            "status": status,
            "title": "",
            "text": "",
            "final_domain": domain,
            "final_url": f"https://{domain}",
        }
    finally:
        crawl.TIMEOUT = old


def verify_domain(name: str, domain: str, slug: str, *, require_page: bool, skip_sld: bool = False) -> tuple[bool, str, dict]:
    domain = (domain or "").lower().removeprefix("www.")
    if domain in REJECT_DOMAINS or registrable(domain) in REJECT_DOMAINS:
        return False, "rejected-collision", {}
    if not domain or is_directory_host(domain):
        return False, "directory-or-empty", {}
    if any(domain.endswith(sfx) for sfx in PORTAL_HOSTS):
        return False, "portal-host", {}
    if not skip_sld and not sld_matches(domain, name, slug):
        return False, "sld-mismatch", {}
    home = fetch_home(domain)
    live = home.get("final_domain") or domain
    if is_directory_host(live):
        return False, "redirect-directory", home
    if not skip_sld and not sld_matches(live, name, slug):
        return False, f"redirect-sld-mismatch:{live}", home
    title = home.get("title") or ""
    text = home.get("text") or ""
    blob = f"{title} {text}"
    if FOR_SALE.search(blob):
        return False, "for-sale", home
    named = page_names_company(name, title, text)
    if home.get("ok") and named:
        if require_page and not title_brand(name, re.sub(re.escape(domain), " ", title, flags=re.I)):
            return False, "title-brand-mismatch", home
        if require_page and len(compact_name(name)) <= 5 and not re.search(
            r"software|security|cloud|saas|platform|cyber|data|ai\b|bank|lending", title, re.I
        ):
            return False, "short-name-weak-title", home
        return True, "homepage", home
    if home.get("ok") and not named:
        if crawl.PARKING.search(blob) or crawl.SOFT_404.search(blob):
            return False, "parked-or-404", home
        if require_page:
            return False, "homepage-name-mismatch", home
        return True, "live-sourced-sld", home
    if require_page:
        return False, f"fetch-{home.get('status') or 0}", home
    if home.get("status") in {401, 403, 405, 429, 503}:
        return True, f"walled-or-unreachable:{home.get('status')}", home
    return False, f"fetch-{home.get('status')}", home


def wd_search(query: str) -> list[dict]:
    data = enrich.wikidata_api({
        "action": "wbsearchentities",
        "search": query,
        "language": "en",
        "uselang": "en",
        "type": "item",
        "limit": "8",
        "format": "json",
    })
    if not data:
        return []
    return list(data.get("search") or [])


def wd_entity(qid: str) -> dict:
    data = enrich.wikidata_api({
        "action": "wbgetentities",
        "ids": qid,
        "props": "claims|labels|aliases|descriptions|sitelinks",
        "languages": "en",
        "format": "json",
    })
    if not data:
        return {}
    return (data.get("entities") or {}).get(qid) or {}


def label_of(ent: dict) -> str:
    return ((ent.get("labels") or {}).get("en") or {}).get("value") or ""


def aliases_of(ent: dict) -> list[str]:
    return [a.get("value") or "" for a in ((ent.get("aliases") or {}).get("en") or [])]


def name_close(label: str, name: str) -> bool:
    if enrich.title_close(label, name):
        return True
    a = re.sub(r"\.(io|ai|com|co|net)$", "", (label or "").strip().lower())
    b = (name or "").strip().lower()
    return bool(a) and a == b


def score_entity(name: str, hit: dict, ent: dict) -> int:
    if not ent or ent.get("missing"):
        return 0
    claims = ent.get("claims") or {}
    p31 = enrich.parse_p31(claims)
    if "Q4167410" in p31:  # disambiguation
        return 0
    if "Q5" in p31 and not (set(p31) & enrich.ORG_QIDS):
        return 0
    sites = enrich.parse_p856(claims)
    if not sites:
        return 0
    label = label_of(ent)
    aliases = aliases_of(ent)
    score = 0
    if name_close(label, name) or label.lower() == name.lower():
        score += 10
    elif any(name_close(a, name) or a.lower() == name.lower() for a in aliases):
        score += 8
    elif name_close(hit.get("label") or "", name):
        score += 6
    else:
        return 0
    desc = ((ent.get("descriptions") or {}).get("en") or {}).get("value") or ""
    org = bool(set(p31) & enrich.ORG_QIDS)
    if not org and not re.search(r"compan|software|startup|business|enterprise|vendor", desc, re.I):
        return 0
    if set(p31) & enrich.ORG_QIDS:
        score += 3
    elif p31:
        score += 1
    if re.search(r"software|security|cloud|saas|technolog|cyber|internet|fintech", desc, re.I):
        score += 2
    if re.search(r"\b(pharma|biotech|rock band|football|radio station|weaving|newspaper|media conglomerate)\b", desc, re.I):
        return 0
    return score


def wikidata_domain(company: dict) -> tuple[str | None, str, str]:
    queries = [company["name"], *HINTS.get(company["slug"], [])]
    extra = f"{company['name']} company"
    if extra not in queries:
        queries.append(extra)
    best = None
    best_score = 0
    best_qid = ""
    best_url = ""
    seen = set()
    for q in queries:
        for hit in wd_search(q):
            qid = hit.get("id")
            if not qid or qid in seen:
                continue
            seen.add(qid)
            ent = wd_entity(qid)
            sc = score_entity(company["name"], hit, ent)
            if sc < 8:
                continue
            src = (company.get("source") or "")
            desc = ((ent.get("descriptions") or {}).get("en") or {}).get("value") or ""
            if re.search(r"software|security|ai-|forbes-ai|emcloud", src):
                if not re.search(r"software|security|cloud|saas|technolog|cyber|internet|data|ai\b", desc, re.I):
                    continue
            sites = enrich.parse_p856(ent.get("claims") or {})
            url = next((u for u in sites if domain_of(u) and not is_directory_host(domain_of(u) or "")), None)
            if not url:
                continue
            host = domain_of(url)
            if not host or not sld_matches(host, company["name"], company["slug"]):
                continue
            if sc > best_score:
                best_score = sc
                best = ent
                best_qid = qid
                best_url = url
    if not best or not best_url:
        return None, "", "wikidata-miss"
    return domain_of(best_url), best_qid, f"wikidata-p856:{best_qid}:score={best_score}"


def wiki_title_domain(company: dict) -> tuple[str | None, str, str]:
    titles = [company["name"], *HINTS.get(company["slug"], [])]
    data = enrich.wiki_api({
        "action": "query",
        "prop": "pageprops",
        "ppprop": "wikibase_item",
        "redirects": "1",
        "titles": "|".join(titles[:4]),
        "format": "json",
    })
    if not data:
        return None, "", "enwiki-miss"
    for page in ((data.get("query") or {}).get("pages") or {}).values():
        if "missing" in page:
            continue
        title = page.get("title") or ""
        if not (
            enrich.title_close(title, company["name"])
            or any(enrich.title_close(title, h) for h in HINTS.get(company["slug"], []))
        ):
            continue
        qid = (page.get("pageprops") or {}).get("wikibase_item")
        if not qid:
            continue
        ent = wd_entity(qid)
        desc = ((ent.get("descriptions") or {}).get("en") or {}).get("value") or ""
        src = company.get("source") or ""
        if re.search(r"software|security|ai-|forbes-ai|emcloud", src):
            if not re.search(r"software|security|cloud|saas|technolog|cyber|internet|data|ai\b", desc, re.I):
                continue
        url = next(
            (u for u in enrich.parse_p856(ent.get("claims") or {})
             if domain_of(u) and not is_directory_host(domain_of(u) or "")),
            None,
        )
        if url:
            host = domain_of(url)
            if host and sld_matches(host, company["name"], company["slug"]):
                return host, qid, f"enwiki-title-p856:{qid}:{title}"
    return None, "", "enwiki-miss"


def guess_domains(company: dict) -> list[str]:
    slug = company["slug"]
    compact = compact_name(company["name"])
    out, seen = [], set()
    tlds = ["com", "ai", "io", "co"]

    def add(host: str) -> None:
        host = host.lower().strip(".")
        if host and host not in seen and "." in host:
            seen.add(host)
            out.append(host)

    for tld in tlds:
        add(f"{compact}.{tld}")
        add(f"{slug}.{tld}")
        add(f"{slug.replace('-', '')}.{tld}")
    for extra in EXTRA_GUESSES.get(company["slug"], []):
        add(extra)
    return out[:12]


def forbes_source_map() -> dict[str, str]:
    """Pull first-party hrefs from the Forbes AI 50 mirror page."""
    rec = crawl.fetch("https://www.aiworld.lat/forbes-50.html", max_body=200000)
    html = rec.get("body") or ""
    hrefs = re.findall(r"""href\s*=\s*['"](https?://[^'"]+)['"]""", html, re.I)
    mapped = {}
    for href in hrefs:
        host = domain_of(href)
        if not host or is_directory_host(host):
            continue
        sld = host.split(".")[0]
        mapped.setdefault(sld, host)
    return mapped


def source_candidate(company: dict, forbes: dict[str, str]) -> str | None:
    if company.get("source") != "forbes-ai-50-2025":
        return None
    slug = company["slug"].replace("-ai", "").replace("-labs", "").replace("-lab", "")
    compact = compact_name(company["name"])
    for key in (company["slug"], slug, compact, company["slug"].split("-")[0]):
        if key in forbes:
            return forbes[key]
    # SLD contains a distinctive token.
    toks = name_tokens(company["name"])
    for sld, host in forbes.items():
        if any(t == sld or sld.startswith(t) for t in toks if len(t) >= 4):
            return host
    return None


def resolve_one(company: dict, forbes: dict[str, str], taken: dict[str, str]) -> dict:
    slug = company["slug"]
    name = company["name"]
    result = {
        "name": name,
        "slug": slug,
        "domain": None,
        "reason": "unresolved",
        "qid": "",
        "source": company.get("source"),
    }

    def accept(domain: str, reason: str, require_page: bool) -> bool:
        domain = (domain or "").lower().removeprefix("www.")
        if not domain:
            return False
        owner = taken.get(domain) or taken.get(registrable(domain))
        if owner and owner != slug:
            result["reason"] = f"taken-by:{owner}:{domain}"
            return False
        extras = {d.lower() for d in EXTRA_GUESSES.get(slug, [])}
        ok, why, home = verify_domain(
            name, domain, slug,
            require_page=require_page,
            skip_sld=domain in extras,
        )
        live = (home.get("final_domain") or domain).lower().removeprefix("www.")
        if ok and live and live != domain:
            owner2 = taken.get(live) or taken.get(registrable(live))
            if owner2 and owner2 != slug:
                result["reason"] = f"taken-by:{owner2}:{live}"
                return False
            if is_directory_host(live):
                result["reason"] = f"redirect-directory:{live}"
                return False
            domain = live
        if not ok:
            result["reason"] = f"{reason}:{why}"
            return False
        result["domain"] = domain
        result["reason"] = f"{reason}:{why}"
        result["title"] = (home.get("title") or "")[:160]
        return True

    src = source_candidate(company, forbes)
    if src and accept(src, "source-page", require_page=False):
        return result

    wd, qid, why = wikidata_domain(company)
    result["qid"] = qid
    if wd and accept(wd, why, require_page=False):
        return result

    wiki, qid2, why2 = wiki_title_domain(company)
    if qid2:
        result["qid"] = qid2
    if wiki and accept(wiki, why2, require_page=False):
        return result

    extras = {d.lower() for d in EXTRA_GUESSES.get(slug, [])}
    for guess in guess_domains(company):
        sourced = guess.lower() in extras
        if accept(guess, "extra" if sourced else "guess", require_page=not sourced):
            return result

    if result["reason"] == "unresolved":
        result["reason"] = "no-verified-official-site"
    return result


def resolve_queue() -> dict:
    queue = load_json(QUEUE, {"companies": []})
    nulls = [c for c in queue["companies"] if not c.get("domain")]
    taken = taken_domains()
    print(f"Domain-null before: {len(nulls)} / {len(queue['companies'])}", flush=True)
    print("Loading Forbes AI 50 source hrefs…", flush=True)
    forbes = forbes_source_map()
    print(f"  source hosts: {len(forbes)}", flush=True)

    resolved = []
    with ThreadPoolExecutor(max_workers=WD_WORKERS) as pool:
        futs = {pool.submit(resolve_one, c, forbes, taken): c for c in nulls}
        done = 0
        for fut in as_completed(futs):
            rec = fut.result()
            resolved.append(rec)
            done += 1
            flag = rec.get("domain") or "null"
            print(f"  [{done}/{len(nulls)}] {rec['slug']:28} {flag:28} {rec['reason']}", flush=True)

    by_slug = {r["slug"]: r for r in resolved}
    filled = 0
    claimed: dict[str, str] = {}
    reason_rank = lambda r: (
        0 if str(r.get("reason") or "").startswith("source-page") else
        1 if "wikidata" in str(r.get("reason") or "") else
        2 if "enwiki" in str(r.get("reason") or "") else 3
    )
    for rec in sorted(resolved, key=reason_rank):
        dom = rec.get("domain")
        if not dom:
            continue
        owner = claimed.get(dom) or claimed.get(registrable(dom)) or taken.get(dom) or taken.get(registrable(dom))
        if owner and owner != rec["slug"]:
            rec["domain"] = None
            rec["reason"] = f"taken-after:{owner}:{dom}"
            continue
        claimed[dom] = rec["slug"]
        claimed[registrable(dom)] = rec["slug"]
    for row in queue["companies"]:
        rec = by_slug.get(row["slug"])
        if rec and rec.get("domain"):
            row["domain"] = rec["domain"]
            filled += 1

    still = [c for c in queue["companies"] if not c.get("domain")]
    queue["domain_resolve_at"] = utc_now()
    write_json(QUEUE, queue)
    report = {
        "generated_at": utc_now(),
        "method": (
            "source-page first-party hrefs; wikidata wbsearchentities P856; "
            "enwiki title P856; homepage-verified guesses. "
            "Wikipedia/Crunchbase/news hosts rejected. Unverified stay null."
        ),
        "before_null": len(nulls),
        "resolved": filled,
        "after_null": len(still),
        "still_null": [{"name": c["name"], "slug": c["slug"], "source": c.get("source")} for c in still],
        "rows": sorted(resolved, key=lambda r: r["slug"]),
    }
    write_json(LOG, report)
    print(f"Resolved {filled}; still null {len(still)}", flush=True)
    return report


def portal_or_pdf_or_wall(url: str, rec: dict | None) -> bool:
    if not url:
        return True
    host = host_of(url)
    if any(host.endswith(sfx) for sfx in PORTAL_HOSTS):
        return True
    ctype = ((rec or {}).get("ctype") or "").lower()
    if "pdf" in ctype or url.lower().endswith(".pdf"):
        return True
    title = (rec or {}).get("title") or ""
    text = (rec or {}).get("text") or ""
    if enrich.looks_like_login_wall(title, text):
        return True
    # JS shell: almost no readable HTML text.
    if rec is not None and len(re.sub(r"\s+", " ", text)) < 180:
        return True
    return False


def first_party(url: str, domain: str) -> bool:
    if not url or not domain:
        return False
    h = host_of(url)
    d = domain.lower().removeprefix("www.")
    if not h:
        return False
    if h == d or h.endswith("." + d):
        return True
    return registrable(h) == registrable(d)


def enrich_found(row: dict):
    """Fill DPA/years/processors only from public first-party HTML (PR 21–22 rules)."""
    probed = enrich.probe_company(row)
    links = dict(probed.get("links") or {})
    pages = probed.get("pages") or {}
    if row.get("trust_url"):
        links.setdefault("trust", row["trust_url"])
    # Drop non-first-party instrument URLs except status/bounty marketplaces.
    kept = {}
    for kind, url in links.items():
        if not url:
            continue
        if kind in {"status", "bug_bounty"}:
            kept[kind] = url
            continue
        if first_party(url, row.get("domain") or "") or kind == "trust":
            kept[kind] = url
    links = kept
    certs = enrich.certs_from_pages(row, pages, links)
    if certs:
        merged = []
        for item in (row.get("certs") or []) + certs:
            if item not in merged:
                merged.append(item)
        row["certs"] = merged
    sub_url = links.get("subprocessors")
    sub_rec = pages.get("subprocessors")
    procs = []
    if (
        sub_url
        and first_party(sub_url, row.get("domain") or "")
        and not portal_or_pdf_or_wall(sub_url, sub_rec)
        and enrich.is_subprocessor_page(sub_url, (sub_rec or {}).get("title") or "", (sub_rec or {}).get("text") or "")
    ):
        procs = enrich.processors_from_company(row, pages, links)
    else:
        links.pop("subprocessors", None)
    row["links"] = {k: v for k, v in links.items() if v}
    row["subprocessors"] = [pid for pid, _n, _e in procs]
    page_text = ""
    for key in ("trust", "security"):
        if pages.get(key):
            page_text = pages[key].get("meta") or pages[key].get("text") or ""
            break
    row["summary"] = enrich.clerk_summary(bool(row.get("found")), row.get("certs") or [], row.get("summary") or "", page_text)
    if row.get("title"):
        row["title"] = enrich.clean_title(row["title"], row.get("name") or "")
    rescore(row)
    return row, procs, sub_url if procs else None


def expand_resolved(report: dict) -> dict:
    queue = load_json(QUEUE, {"companies": []})
    enr = load_json(ENRICHED, {"companies": []})
    have = {c["slug"] for c in enr.get("companies") or []}
    import subprocess
    raw = subprocess.check_output(["git", "show", "main:data/crawl-queue.json"], cwd=ROOT)
    was_null = {c["slug"] for c in json.loads(raw).get("companies") or [] if not c.get("domain")}
    newly = [
        row for row in queue.get("companies") or []
        if row.get("slug") in was_null and row.get("domain") and row.get("slug") not in have
    ]
    print(f"Expand-probing {len(newly)} newly resolved names…", flush=True)
    probes = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(crawl.probe_company, c): c for c in newly}
        done = 0
        for fut in as_completed(futs):
            row = fut.result()
            probes.append(row)
            done += 1
            print(
                f"  [{done}/{len(newly)}] {'HIT' if row.get('found') else 'miss':4} "
                f"{row['slug']:28} {row.get('trust_url') or ''}",
                flush=True,
            )

    records = []
    for row in probes:
        src = next((c for c in newly if c["slug"] == row["slug"]), {})
        certs = []
        url = row.get("final_url") or row.get("trust_url")
        if url and row.get("found"):
            fetched = crawl.fetch(url)
            body = fetched.get("body") or ""
            certs = extract_certs(body)
        rec = to_record(row, certs, src.get("source") or "expand")
        rec["list"] = src.get("source") or "expand"
        rec["source"] = src.get("source_url") or src.get("source") or "expand"
        rec["vendor"] = "unknown"
        records.append(rec)

    found_rows = [r for r in records if r.get("found") and (r.get("trust_url") or r.get("final_url"))]
    print(f"Enriching {len(found_rows)} found pages (first-party HTML only)…", flush=True)
    print("  founding years for found rows…", flush=True)
    years_map = enrich.resolve_founding_years(found_rows, []) if found_rows else {}
    new_edges = []
    for rec in found_rows:
        rec, procs, sub_url = enrich_found(rec)
        if rec["slug"] in years_map:
            rec["founded_year"], rec["founded_source"] = years_map[rec["slug"]]
            rescore(rec)
        for pid, name, ev in procs:
            if not sub_url:
                continue
            new_edges.append({
                "from": rec["slug"],
                "to": pid,
                "source_url": sub_url,
                "evidence": ev or name,
            })
        print(
            f"  {rec['slug']:28} tier={(rec.get('disclosure') or {}).get('tier')} "
            f"certs={len(rec.get('certs') or [])} "
            f"links={list((rec.get('links') or {}).keys())} "
            f"procs={len(rec.get('subprocessors') or [])}",
            flush=True,
        )

    by = {c["slug"]: i for i, c in enumerate(enr["companies"])}
    added = []
    for rec in records:
        if rec["slug"] in by:
            continue
        rec["rank"] = len(enr["companies"]) + 1
        enr["companies"].append(rec)
        added.append(rec)
    enr["generated_at"] = utc_now()
    write_json(ENRICHED, enr)
    write_json(SITE_ENRICHED, enr)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    write_json(DATA / "render" / f"expand-{stamp}.json", {"batch": "resolve-queue-domains", "rows": records})

    if new_edges:
        graph = load_json(SUB, {"nodes": [], "edges": []})
        node_ids = {n.get("id") for n in graph.get("nodes") or []}
        proc_meta = {i: (n, d) for i, n, d, _a in enrich.PROCESSORS}
        register = {c["slug"]: c for c in enr["companies"]}

        def add_node(nid, name, domain, in_register, kind):
            if nid in node_ids:
                return
            node_ids.add(nid)
            graph.setdefault("nodes", []).append({
                "id": nid,
                "name": name,
                "domain": domain,
                "kind": kind,
                "in_register": bool(in_register),
            })

        for e in new_edges:
            src = register.get(e["from"])
            if src:
                add_node(src["slug"], src["name"], src.get("domain") or "", True, "company")
            pid = e["to"]
            if pid in register:
                add_node(pid, register[pid]["name"], register[pid].get("domain") or "", True, "company")
            elif pid in proc_meta:
                add_node(pid, proc_meta[pid][0], proc_meta[pid][1], False, "processor")
            else:
                add_node(pid, pid, "", False, "processor")
            graph.setdefault("edges", []).append(e)
        graph["generated_at"] = utc_now()
        write_json(SUB, graph)
        write_json(SITE_SUB, graph)

    hits = [r for r in added if r.get("found")]
    print(f"added {len(added)}  pages {len(hits)}/{len(records)}", flush=True)
    return {
        "added": len(added),
        "pages": len(hits),
        "probed": len(records),
        "hit_slugs": [r["slug"] for r in hits],
        "silent_slugs": [r["slug"] for r in added if not r.get("found")],
        "processor_edges": len(new_edges),
        "render": f"expand-{stamp}.json",
    }


def main() -> int:
    (DATA / "cache" / "http").mkdir(parents=True, exist_ok=True)
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    report = load_json(LOG, {})
    if phase in {"resolve", "all"}:
        report = resolve_queue()
    if phase in {"expand", "all"}:
        if not report:
            report = load_json(LOG, {})
        expand = expand_resolved(report)
        report["expand"] = expand
        write_json(LOG, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
