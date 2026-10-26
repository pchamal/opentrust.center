#!/usr/bin/env python3
"""Append verified CRN Security 100 2023 leftovers, then Wikipedia cloud providers.

Domains via Wikidata P856 only. Never invent names or domains.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path("/workspace/trust-index")
sys.path.insert(0, "/workspace")
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts"))
import resolve_wikidata_domains as wd  # noqa: E402
from processor_aliases import REGISTER_ALIASES, skip_processor  # noqa: E402

QUEUE_PATH = ROOT / "data" / "crawl-queue.json"
ENRICHED_PATH = ROOT / "data" / "enriched.json"
LOG_PATH = ROOT / "data" / "crawl-domains-log.json"
STATE_PATH = ROOT / "data" / "crawl-state.json"

UA = "opentrust.center/1.0 (+https://opentrust.center)"
WIKI_API = "https://en.wikipedia.org/w/api.php"
MAX_APPEND = 150
TARGET_READY = 80

CRN_PAGES = [
    (
        "/tmp/crn2023/endpoint.html",
        "https://www.crn.com/news/security/the-20-coolest-endpoint-and-managed-security-companies-of-2023-the-security-100",
    ),
    (
        "/tmp/crn2023/identity.html",
        "https://www.crn.com/news/security/the-20-coolest-identity-access-management-and-data-protection-companies-of-2023-the-security-100",
    ),
    (
        "/tmp/crn2023/network.html",
        "https://www.crn.com/news/networking/the-20-coolest-network-security-companies-of-2023-the-security-100",
    ),
    (
        "/tmp/crn2023/secops.html",
        "https://www.crn.com/news/security/the-20-coolest-risk-threat-intelligence-and-security-operations-companies-of-2023-the-security-100",
    ),
    (
        "/tmp/crn2023/web.html",
        "https://www.crn.com/news/security/the-20-coolest-web-application-and-email-security-companies-of-2023-the-security-100",
    ),
]
SKIP_CRN_NAMES = {
    "google cloud",  # google already on file
    "opentext cybersecurity",  # opentext already on file
    "microsoft",
    "ibm security",
    "cynet",  # P856 hit cynet.co.jp, not the CRN Israeli company
    "lightspin",  # P856 hit lightspintech.com, not CRN Lightspin
}

WIKI_CATS = [
    ("Category:Computer_hardware_companies", "wikipedia-computer-hardware-companies", "https://en.wikipedia.org/wiki/Category:Computer_hardware_companies", 3),
    ("Category:Cloud_computing_providers", "wikipedia-cloud-computing-providers", "https://en.wikipedia.org/wiki/Category:Cloud_computing_providers", 3),
    ("Category:Artificial_intelligence_companies", "wikipedia-ai-companies", "https://en.wikipedia.org/wiki/Category:Artificial_intelligence_companies", 3),
    ("Category:Business_intelligence_companies", "wikipedia-business-intelligence-companies", "https://en.wikipedia.org/wiki/Category:Business_intelligence_companies", 3),
    ("Category:Mobile_phone_manufacturers", "wikipedia-mobile-phone-manufacturers", "https://en.wikipedia.org/wiki/Category:Mobile_phone_manufacturers", 3),
    ("Category:Telecommunications_companies_of_Canada", "wikipedia-telecom-canada", "https://en.wikipedia.org/wiki/Category:Telecommunications_companies_of_Canada", 3),
    ("Category:Telecommunications_companies_of_the_United_Kingdom", "wikipedia-telecom-uk", "https://en.wikipedia.org/wiki/Category:Telecommunications_companies_of_the_United_Kingdom", 3),
    ("Category:Telecommunications_companies_of_Germany", "wikipedia-telecom-germany", "https://en.wikipedia.org/wiki/Category:Telecommunications_companies_of_Germany", 3),
    ("Category:Technology_companies_of_Israel", "wikipedia-tech-israel", "https://en.wikipedia.org/wiki/Category:Technology_companies_of_Israel", 3),
    ("Category:Software_companies_of_China", "wikipedia-software-china", "https://en.wikipedia.org/wiki/Category:Software_companies_of_China", 3),
    ("Category:Software_companies_of_Ukraine", "wikipedia-software-ukraine", "https://en.wikipedia.org/wiki/Category:Software_companies_of_Ukraine", 3),
    ("Category:Software_companies_of_Romania", "wikipedia-software-romania", "https://en.wikipedia.org/wiki/Category:Software_companies_of_Romania", 3),
    ("Category:Software_companies_of_Hungary", "wikipedia-software-hungary", "https://en.wikipedia.org/wiki/Category:Software_companies_of_Hungary", 3),
    ("Category:Software_companies_of_Greece", "wikipedia-software-greece", "https://en.wikipedia.org/wiki/Category:Software_companies_of_Greece", 3),
    ("Category:Software_companies_based_in_the_San_Francisco_Bay_Area", "wikipedia-software-sf-bay-area", "https://en.wikipedia.org/wiki/Category:Software_companies_based_in_the_San_Francisco_Bay_Area", 3),
    ("Category:Software_companies_based_in_New_York_City", "wikipedia-software-nyc", "https://en.wikipedia.org/wiki/Category:Software_companies_based_in_New_York_City", 3),
    ("Category:Software_companies_based_in_Seattle", "wikipedia-software-seattle", "https://en.wikipedia.org/wiki/Category:Software_companies_based_in_Seattle", 3),
    ("Category:Video_game_companies_of_Japan", "wikipedia-video-game-japan", "https://en.wikipedia.org/wiki/Category:Video_game_companies_of_Japan", 3),
    ("Category:Data_companies", "wikipedia-data-companies", "https://en.wikipedia.org/wiki/Category:Data_companies", 3),
    ("Category:Online_companies_of_the_United_States", "wikipedia-online-companies-us", "https://en.wikipedia.org/wiki/Category:Online_companies_of_the_United_States", 3),
    ("Category:Web_service_providers", "wikipedia-web-service-providers", "https://en.wikipedia.org/wiki/Category:Web_service_providers", 3),
    ("Category:Technology_companies_of_India", "wikipedia-tech-india", "https://en.wikipedia.org/wiki/Category:Technology_companies_of_India", 3),
    ("Category:Software_companies_of_Australia", "wikipedia-software-australia", "https://en.wikipedia.org/wiki/Category:Software_companies_of_Australia", 3),
    ("Category:Software_companies_of_Canada", "wikipedia-software-canada", "https://en.wikipedia.org/wiki/Category:Software_companies_of_Canada", 3),
    ("Category:Software_companies_of_France", "wikipedia-software-france", "https://en.wikipedia.org/wiki/Category:Software_companies_of_France", 3),
    ("Category:Software_companies_of_Germany", "wikipedia-software-germany", "https://en.wikipedia.org/wiki/Category:Software_companies_of_Germany", 3),
    ("Category:Software_companies_of_the_Netherlands", "wikipedia-software-netherlands", "https://en.wikipedia.org/wiki/Category:Software_companies_of_the_Netherlands", 3),
    ("Category:Software_companies_of_Sweden", "wikipedia-software-sweden", "https://en.wikipedia.org/wiki/Category:Software_companies_of_Sweden", 3),
    ("Category:Software_companies_of_Finland", "wikipedia-software-finland", "https://en.wikipedia.org/wiki/Category:Software_companies_of_Finland", 3),
    ("Category:Software_companies_of_Poland", "wikipedia-software-poland", "https://en.wikipedia.org/wiki/Category:Software_companies_of_Poland", 3),
    ("Category:Software_companies_of_Spain", "wikipedia-software-spain", "https://en.wikipedia.org/wiki/Category:Software_companies_of_Spain", 3),
    ("Category:Software_companies_of_Italy", "wikipedia-software-italy", "https://en.wikipedia.org/wiki/Category:Software_companies_of_Italy", 3),
    ("Category:Software_companies_of_Brazil", "wikipedia-software-brazil", "https://en.wikipedia.org/wiki/Category:Software_companies_of_Brazil", 3),
    ("Category:Software_companies_of_South_Korea", "wikipedia-software-south-korea", "https://en.wikipedia.org/wiki/Category:Software_companies_of_South_Korea", 3),
    ("Category:Software_companies_of_Singapore", "wikipedia-software-singapore", "https://en.wikipedia.org/wiki/Category:Software_companies_of_Singapore", 3),
    ("Category:Cybersecurity_companies", "wikipedia-cybersecurity-companies", "https://en.wikipedia.org/wiki/Category:Cybersecurity_companies", 3),
    ("Category:Network_security_companies", "wikipedia-network-security-companies", "https://en.wikipedia.org/wiki/Category:Network_security_companies", 3),
    ("Category:Enterprise_software_companies", "wikipedia-enterprise-software-companies", "https://en.wikipedia.org/wiki/Category:Enterprise_software_companies", 3),
    ("Category:Cloud_storage_providers", "wikipedia-cloud-storage-providers", "https://en.wikipedia.org/wiki/Category:Cloud_storage_providers", 3),
    ("Category:Database_companies", "wikipedia-database-companies", "https://en.wikipedia.org/wiki/Category:Database_companies", 3),
    ("Category:Identity_management_vendors", "wikipedia-identity-management-vendors", "https://en.wikipedia.org/wiki/Category:Identity_management_vendors", 3),
    ("Category:DevOps_companies", "wikipedia-devops-companies", "https://en.wikipedia.org/wiki/Category:DevOps_companies", 3),
]

NEVER_DOMAINS = {
    "castellum.se", "powersteeringsoftware.com", "bloomz.com.mx",
    "holdings.panasonic", "martiag.ch", "readyforzero.com", "ygfamily.com", "daj.jp",
    "zero-n.jp",
}
EXTRA_BLOCKED = (
    "archive.org", "web.archive", "wikipedia.", "wikimedia.", "wikidata.",
    "fandom.com", "blogspot.", "wordpress.com", "twitter.com", "x.com",
    "facebook.com", "linkedin.com", "youtube.com", "crunchbase.com", "instagram.com",
)
PAREN_RE = re.compile(r"\s*\([^)]*\)\s*")
LEGAL_TAIL = {
    "inc", "incorporated", "ltd", "limited", "llc", "corp", "corporation",
    "plc", "gmbh", "company", "holdings", "holding", "group", "se",
    "nv", "bv", "the", "lp", "ag", "ab", "co", "sa", "spa", "kk",
    "technologies", "technology", "networks", "security", "software", "systems",
}
WEAK_TOKENS = {
    "zero", "one", "net", "network", "networks", "security", "cloud", "data",
    "systems", "system", "group", "global", "digital", "tech", "the", "inc",
    "labs", "lab", "ai", "io", "app", "hq", "solutions", "solution", "cyber",
    "computer", "software", "computing", "providers",
}
SKIP_PREFIX = ("file:", "image:", "category:", "list of", "template:", "wikipedia:")
SKIP_TITLES = {
    "cloud computing", "software as a service", "platform as a service",
    "infrastructure as a service", "amazon web services", "google cloud",
    "microsoft azure", "ibm cloud",
}
STRONG_TRIPLE = re.compile(
    r"<p><strong>([^<]+)</strong></p>\s*"
    r"<p><strong>([^<]+)</strong></p>\s*"
    r"<p><strong>([^<]+)</strong></p>",
    re.I,
)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(name: str) -> str:
    s = name.lower().replace("&", "and").replace("+", "plus")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def nkey(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def core_slug(name: str) -> str:
    stripped = PAREN_RE.sub(" ", name)
    parts = [p for p in slugify(stripped).split("-") if p]
    while parts and parts[-1] in LEGAL_TAIL:
        parts.pop()
    while parts and parts[0] in LEGAL_TAIL:
        parts.pop(0)
    return "-".join(parts)


def clean_name(name: str) -> str:
    return re.sub(r"\s+", " ", unescape(name or "").replace("\xa0", " ")).strip()


def display_name(title: str, display: str | None = None) -> str:
    raw = clean_name(display or title)
    stripped = PAREN_RE.sub(" ", raw).strip()
    return stripped or raw


def is_dup(name, slug, have_slugs, have_nkeys, have_cores) -> bool:
    if slug in have_slugs or nkey(name) in have_nkeys:
        return True
    stripped = PAREN_RE.sub(" ", name).strip()
    if nkey(stripped) in have_nkeys or slugify(stripped) in have_slugs:
        return True
    core = core_slug(name)
    if core and (core in have_slugs or core in have_cores):
        return True
    if slug in have_cores:
        return True
    return False


def host_ok(host: str | None) -> bool:
    if not host or "." not in host:
        return False
    h = host.lower()
    if h.startswith("www."):
        h = h[4:]
    if h in NEVER_DOMAINS:
        return False
    # Exact/suffix for host-like parts (avoid "x.com" matching magix.com);
    # substring only for markers that end with "." (blogspot., wikipedia.).
    for part in EXTRA_BLOCKED:
        if part.endswith("."):
            if part in h:
                return False
        elif h == part or h.endswith("." + part):
            return False
    if wd.is_blocked_host(h):
        return False
    if h.endswith(".pdf") or h.endswith(".html"):
        return False
    return True


def domain_label(host: str) -> str:
    parts = host.split(".")
    sld = {"co", "com", "ne", "or", "ac", "gov", "org", "net"}
    if len(parts) >= 3 and parts[-2] in sld:
        return parts[-3]
    return parts[-2] if len(parts) >= 2 else parts[0]


def domain_plausible(name: str, host: str) -> bool:
    if not host_ok(host):
        return False
    label = domain_label(host)
    nt = set(wd.strip_legal(wd.tokens(name)))
    ht = set(wd.tokens(label.replace("-", " ")))
    distinctive = (nt & ht) - WEAK_TOKENS
    if distinctive:
        return True
    cn, ch = wd.compact(name), wd.compact(label)
    if cn and ch:
        if cn == ch:
            return True
        for part in re.split(r"[()]", name):
            cp = wd.compact(part)
            if cp and len(cp) >= 4 and (cp == ch or (len(cp) >= 5 and (cp in ch or ch in cp))):
                return True
        if len(cn) >= 5 and (cn in ch or ch in cn):
            return True
        initials = "".join(t[0] for t in wd.strip_legal(wd.tokens(name)) if t)
        if initials and initials == ch and len(initials) >= 3:
            return True
    # Distinctive token is a prefix/substring of the registrable label
    # (Valve → valvesoftware, Vicor → vicorpower). Still P856-only.
    if ch:
        for tok in nt - WEAK_TOKENS:
            if len(tok) >= 4 and (tok in ch or ch.startswith(tok)):
                return True
    return False


def http_json(url: str) -> dict:
    last = None
    for attempt in range(6):
        wd.polite_wait(0.18)
        req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2.0 * (attempt + 1))
                continue
            raise
        except (URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed {url} ({last})")


def fetch_category(cat: str) -> list[str]:
    members = []
    cont = None
    while True:
        url = (
            f"{WIKI_API}?action=query&list=categorymembers"
            f"&cmtitle={quote(cat)}&cmlimit=500&cmtype=page&format=json&formatversion=2"
        )
        if cont:
            url += f"&cmcontinue={quote(cont)}"
        data = http_json(url)
        for m in (data.get("query") or {}).get("categorymembers") or []:
            t = m.get("title") or ""
            if t:
                members.append(t)
        cont = (data.get("continue") or {}).get("cmcontinue")
        if not cont:
            break
    return members


def wiki_titles_to_qids(titles: list[str]) -> dict[str, str]:
    mapping = {}
    if not titles:
        return mapping
    for i in range(0, len(titles), 40):
        chunk = titles[i : i + 40]
        joined = "|".join(chunk)
        url = (
            f"{WIKI_API}?action=query&prop=pageprops&ppprop=wikibase_item"
            f"&redirects=1&format=json&formatversion=2&titles={quote(joined, safe='|')}"
        )
        data = http_json(url)
        query = data.get("query") or {}
        canon = {}
        for n in query.get("normalized") or []:
            canon[n.get("from")] = n.get("to")
        for r in query.get("redirects") or []:
            canon[r.get("from")] = r.get("to")
        title_to_qid = {}
        for page in query.get("pages") or []:
            if page.get("missing"):
                continue
            qid = (page.get("pageprops") or {}).get("wikibase_item")
            t = page.get("title")
            if qid and t:
                title_to_qid[t] = qid
        for orig in chunk:
            t = orig
            seen = set()
            while t in canon and t not in seen:
                seen.add(t)
                t = canon[t]
            qid = title_to_qid.get(t)
            if qid:
                mapping[orig] = qid
        print(f"  wiki titles {min(i+40, len(titles))}/{len(titles)} qids={len(mapping)}", flush=True)
    return mapping


def parse_crn_names() -> list[dict]:
    rows, seen = [], set()
    for path, url in CRN_PAGES:
        fp = Path(path)
        if not fp.exists():
            print(f"  skip missing CRN cache {path}", flush=True)
            continue
        html = fp.read_text(errors="ignore")
        for company, _person, _title in STRONG_TRIPLE.findall(html):
            name = clean_name(company)
            key = name.lower()
            if not name or key in seen or key in SKIP_CRN_NAMES:
                continue
            seen.add(key)
            rows.append({
                "name": name,
                "slug": slugify(name),
                "source": "crn-security-100-2023",
                "source_url": url,
                "priority": 1,
            })
    return rows


def usable_title(title: str) -> bool:
    tl = title.lower()
    if not title or tl.startswith(SKIP_PREFIX) or title.startswith("Category:"):
        return False
    if tl in SKIP_TITLES:
        return False
    return True


def count_ready(queue, enr) -> int:
    enr_slugs = {c["slug"] for c in enr.get("companies") or []}
    return sum(1 for c in queue["companies"] if c.get("domain") and c["slug"] not in enr_slugs)


def main() -> int:
    queue = json.loads(QUEUE_PATH.read_text())
    enr = json.loads(ENRICHED_PATH.read_text())
    have_slugs, have_nkeys, have_cores, have_domains = set(), set(), set(), set()
    for c in list(enr.get("companies") or []) + queue["companies"]:
        have_slugs.add(c["slug"])
        have_nkeys.add(nkey(c.get("name") or ""))
        have_cores.add(core_slug(c.get("name") or ""))
        have_cores.add(c["slug"])
        d = (c.get("domain") or "").lower().strip()
        if d.startswith("www."):
            d = d[4:]
        if d:
            have_domains.add(d)

    ready0 = count_ready(queue, enr)
    print(f"register {len(enr.get('companies') or [])} domain-ready {ready0}", flush=True)

    crn_all = parse_crn_names()
    crn_cands = []
    for row in crn_all:
        if is_dup(row["name"], row["slug"], have_slugs, have_nkeys, have_cores):
            continue
        crn_cands.append(row)
    print(f"CRN 2023 leftover candidates {len(crn_cands)}/{len(crn_all)}", flush=True)
    for r in crn_cands:
        print(f"  CRN {r['name']}", flush=True)

    wiki_cands = []
    seen_titles, seen_slugs = set(), {r["slug"] for r in crn_cands}
    for cat, source, source_url, prio in WIKI_CATS:
        titles = fetch_category(cat)
        print(f"{cat} pages {len(titles)}", flush=True)
        added = 0
        for title in titles:
            if not usable_title(title):
                continue
            name = display_name(title)
            slug = slugify(name)
            if not slug or title.lower() in seen_titles or slug in seen_slugs:
                continue
            if is_dup(name, slug, have_slugs, have_nkeys, have_cores):
                continue
            if is_dup(title, slugify(title), have_slugs, have_nkeys, have_cores):
                continue
            seen_titles.add(title.lower())
            seen_slugs.add(slug)
            wiki_cands.append({
                "name": name,
                "slug": slug,
                "wiki_title": title,
                "source": source,
                "source_url": source_url,
                "priority": prio,
            })
            added += 1
        print(f"  leftover from {cat}: {added} (wiki leftover total {len(wiki_cands)})", flush=True)
        if ready0 + len(crn_cands) + len(wiki_cands) >= TARGET_READY + 2000:
            break

    print(f"wiki remaining candidates {len(wiki_cands)}", flush=True)

    # Resolve CRN via search + P856, with enwiki sitelink fallback
    searches: dict[str, list] = {}
    if crn_cands:
        with ThreadPoolExecutor(max_workers=wd.WORKERS) as ex:
            futs = {ex.submit(wd.search_entities, c["name"]): c["name"] for c in crn_cands}
            done = 0
            for fut in as_completed(futs):
                n = futs[fut]
                try:
                    searches[n] = fut.result()
                except Exception as e:
                    print(f"SEARCH FAIL {n}: {e}", flush=True)
                    searches[n] = []
                done += 1
                print(f"  crn search {done}/{len(crn_cands)} {n}", flush=True)

    wiki_titles = [c["wiki_title"] for c in wiki_cands]
    for c in crn_cands:
        if not (searches.get(c["name"]) or []):
            wiki_titles.append(c["name"])
            wiki_titles.append(f"{c['name']} (company)")
    wiki_titles = list(dict.fromkeys(wiki_titles))
    print(f"resolving {len(wiki_titles)} wiki titles to qids", flush=True)
    title_qids = wiki_titles_to_qids(wiki_titles)

    all_qids, seenq = [], set()
    for hits in searches.values():
        for h in hits:
            qid = h.get("id")
            if qid and qid not in seenq:
                seenq.add(qid)
                all_qids.append(qid)
    for qid in title_qids.values():
        if qid not in seenq:
            seenq.add(qid)
            all_qids.append(qid)

    print(f"fetching {len(all_qids)} entities", flush=True)
    entities = wd.get_entities(all_qids) if all_qids else {}
    p31_ids, p31_seen = [], set()
    for ent in entities.values():
        for qid in wd.claim_values_item(ent, "P31"):
            if qid not in p31_seen:
                p31_seen.add(qid)
                p31_ids.append(qid)
    print(f"fetching {len(p31_ids)} P31 types", flush=True)
    p31_entities = wd.get_entities(p31_ids) if p31_ids else {}
    p31_labels = {qid: wd.lang_text(ent.get("labels")) or "" for qid, ent in p31_entities.items()}

    resolved, unresolved, dropped = [], [], []
    used_domains = set(have_domains)
    used_slugs = set(have_slugs)

    def accept(cand, domain, qid, reason):
        if domain.startswith("www."):
            domain = domain[4:]
        if not host_ok(domain):
            dropped.append({**cand, "domain": domain, "reason": "blocked-host", "qid": qid})
            return False
        if not domain_plausible(cand["name"], domain):
            dropped.append({**cand, "domain": domain, "reason": "implausible-p856", "qid": qid})
            print(f"  DROP {cand['name']} -> {domain} implausible {qid}", flush=True)
            return False
        if domain in used_domains:
            dropped.append({**cand, "domain": domain, "reason": "dup-domain", "qid": qid})
            return False
        if cand["slug"] in used_slugs:
            dropped.append({**cand, "domain": domain, "reason": "dup-slug", "qid": qid})
            return False
        alias_dest = REGISTER_ALIASES.get(cand["slug"])
        if alias_dest and alias_dest in used_slugs:
            dropped.append({**cand, "domain": domain, "reason": f"alias-to-{alias_dest}", "qid": qid})
            print(f"  SKIP alias {cand['slug']} -> {alias_dest}", flush=True)
            return False
        if skip_processor(cand["slug"], cand.get("name") or ""):
            dropped.append({**cand, "domain": domain, "reason": "garbage-slug", "qid": qid})
            return False
        rec = {**cand, "domain": domain, "qid": qid, "reason": reason}
        resolved.append(rec)
        used_domains.add(domain)
        used_slugs.add(cand["slug"])
        print(f"  P856 {cand['name']} -> {domain} {qid} ({reason})", flush=True)
        return True

    for cand in crn_cands:
        dec = wd.decide(cand["name"], searches.get(cand["name"], []), entities, p31_labels)
        print(
            f"  DECIDE {cand['name']}: status={dec.get('status')} domain={dec.get('domain')} "
            f"qid={dec.get('qid')} reason={dec.get('reason')}",
            flush=True,
        )
        if dec["status"] == "resolved" and dec.get("domain"):
            if accept(cand, dec["domain"], dec.get("qid"), dec.get("reason")):
                continue
        qid = title_qids.get(cand["name"]) or title_qids.get(f"{cand['name']} (company)")
        if qid and qid in entities:
            ent = entities[qid]
            org, org_why = wd.looks_like_org(ent, p31_labels)
            desc = wd.lang_text(ent.get("descriptions"))
            domain = wd.pick_domain(ent, desc)
            print(f"  WIKI {cand['name']} qid={qid} org={org}/{org_why} domain={domain}", flush=True)
            if org and domain:
                if accept(cand, domain, qid, "enwiki-title P856"):
                    continue
            unresolved.append({**cand, "reason": f"wiki-sitelink no-p856 org={org} {org_why}", "qid": qid})
            continue
        unresolved.append({**cand, "reason": dec.get("reason"), "status": dec.get("status")})

    for cand in wiki_cands:
        qid = title_qids.get(cand["wiki_title"])
        if not qid or qid not in entities:
            unresolved.append({**cand, "reason": "no-wikidata-item"})
            continue
        ent = entities[qid]
        org, org_why = wd.looks_like_org(ent, p31_labels)
        desc = wd.lang_text(ent.get("descriptions"))
        domain = wd.pick_domain(ent, desc)
        if domain and domain.startswith("www."):
            domain = domain[4:]
        if not org:
            unresolved.append({**cand, "reason": f"not-org {org_why}", "qid": qid})
            continue
        if not domain:
            unresolved.append({**cand, "reason": "no-p856", "qid": qid})
            continue
        if not accept(cand, domain, qid, "enwiki-title P856"):
            continue

    print(
        f"resolved {len(resolved)} unresolved {len(unresolved)} dropped {len(dropped)}",
        flush=True,
    )
    Path("/tmp/topup_hour_report.json").write_text(json.dumps({
        "resolved": [{"name": r["name"], "slug": r["slug"], "domain": r["domain"],
                      "source": r["source"], "source_url": r["source_url"], "qid": r.get("qid")}
                     for r in resolved],
        "unresolved_n": len(unresolved),
        "dropped_n": len(dropped),
        "unresolved": [{"name": r["name"], "slug": r["slug"], "reason": r.get("reason")} for r in unresolved],
        "dropped": [{"name": r["name"], "slug": r["slug"], "domain": r.get("domain"), "reason": r.get("reason")} for r in dropped],
    }, indent=2) + "\n")

    need = max(0, TARGET_READY - ready0)
    appended = resolved[:MAX_APPEND]
    print(f"WILL APPEND {len(appended)} (need {need} to reach {TARGET_READY})", flush=True)
    if not appended:
        print("no verified rows; not writing queue")
        return 1

    stamp = now()
    for row in appended:
        queue["companies"].append({
            "name": row["name"],
            "slug": row["slug"],
            "domain": row["domain"],
            "source": row["source"],
            "source_url": row["source_url"],
            "priority": row["priority"],
        })
    queue["queued"] = len(queue["companies"])
    queue["generated_at"] = stamp
    QUEUE_PATH.write_text(json.dumps(queue, indent=2) + "\n")

    by_url = defaultdict(int)
    by_source = defaultdict(int)
    for row in appended:
        by_url[row["source_url"]] += 1
        by_source[row["source"]] += 1
    log = {
        "generated_at": stamp,
        "method": "wikidata enwiki sitelink -> P856 only; no invented domains",
        "user_agent": UA,
        "note": (
            f"hourly top-up appended {len(appended)} verified P856 from "
            "CRN Security 100 2023 leftover + Wikipedia tech-established 1915-1929 + EU/Asia software leftover + unused geo/sector categories "
            "(and further unused software categories if needed); "
            "CMC software page 6+ was empty; did not repeat exhausted lists or S&P 500"
        ),
        "counts": {
            "appended": len(appended),
            "resolved": len(resolved),
            "unresolved": len(unresolved),
            "dropped_wrong_or_dup": len(dropped),
            "by_source": dict(by_source),
            "by_source_url": dict(by_url),
        },
        "appended": [
            {
                "name": r["name"],
                "slug": r["slug"],
                "domain": r["domain"],
                "source": r["source"],
                "source_url": r["source_url"],
                "priority": r["priority"],
                "qid": r.get("qid"),
                "reason": r.get("reason"),
            }
            for r in appended
        ],
        "dropped_wrong_p856": [
            {"name": r["name"], "slug": r["slug"], "domain": r.get("domain"), "reason": r.get("reason")}
            for r in dropped
            if r.get("reason") in ("implausible-p856", "blocked-host")
        ],
        "unresolved": [
            {"name": r["name"], "slug": r["slug"], "reason": r.get("reason"), "status": r.get("status")}
            for r in unresolved
        ],
    }
    LOG_PATH.write_text(json.dumps(log, indent=2) + "\n")

    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text())
        state["note"] = (
            "hourly batches; do not invent domains; "
            f"top-up appended {len(appended)} verified P856 from "
            "CRN leftover + Wikipedia 1915-1929 + unused geo/sector; "
            "CMC software page 6+ empty; not repeating S&P 500 after Zoetis"
        )
        STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")

    remaining = count_ready(queue, enr)
    print("APPENDED", len(appended), "REMAINING_DOMAIN_READY", remaining, flush=True)
    for r in appended:
        print(f"  {r['slug']:40} {r['domain']:30} {r['source']} {r.get('reason')}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
