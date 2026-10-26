#!/usr/bin/env python3
"""Resolve official website domains from Wikidata P856 only. Never guess."""

from __future__ import annotations

import json
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path("/workspace/trust-index")
QUEUE_PATH = ROOT / "data" / "crawl-queue.json"
LOG_PATH = ROOT / "data" / "crawl-domains-log.json"
STATE_PATH = ROOT / "data" / "crawl-state.json"
CACHE_DIR = ROOT / "data" / "cache" / "wikidata"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

UA = "opentrust.center/1.0 (+https://opentrust.center)"
API = "https://www.wikidata.org/w/api.php"
WORKERS = 5
TIMEOUT = 25
MAX_RETRIES = 6

BLOCKED_HOST_PARTS = (
    "wikipedia",
    "wikidata",
    "facebook",
    "twitter",
    "linkedin",
    "crunchbase",
    "youtube",
)

P31_ORG_WORDS = ("company", "business", "enterprise")
DESC_ORG_WORDS = ("company", "startup", "software")
THEME_WORDS = ("software", "ai", "security", "cloud")

LEGAL_SUFFIXES = {
    "inc", "incorporated", "ltd", "limited", "llc", "corp", "corporation",
    "plc", "gmbh", "company", "holdings", "holding", "group", "se",
    "nv", "bv", "the", "lp", "ag", "ab",
}
# leftover tokens allowed when the Wikidata label extends the query name
CORPORATE_EXTRAS = LEGAL_SUFFIXES | {
    "systems", "networks", "software", "technologies", "technology",
    "labs", "lab", "ai", "security", "solutions", "global", "worldwide", "digital", "analytics", "services",
    "com", "io", "app", "hq", "enterprises", "enterprise", "commerce",
    "it", "exports",  # not "international": too many unrelated firms
}
# only used when a SINGLE org candidate remains
GEO_EXTRAS = {
    "india", "poland", "japan", "china", "israel", "germany", "france",
    "australia", "canada", "sweden", "finland", "norway", "denmark",
    "ireland", "switzerland", "brazil", "mexico", "korea", "singapore",
    "netherlands", "uk", "us", "usa", "united", "states", "america",
    "american", "british", "european",
}

GENERIC_TLDS = {
    "com", "net", "org", "io", "ai", "co", "app", "dev", "cloud", "security",
    "so", "gg", "info", "biz", "xyz", "tech", "software", "inc", "company",
    "global", "group", "ltd", "edu", "gov", "mil", "int", "name", "pro",
    "online", "site", "shop", "store", "tv", "cc", "me", "us",
}

US_HINTS = ("american", "united states", "u.s.", "us-based", "u.s. ")

NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

lock = threading.Lock()
_last_request = 0.0


def polite_wait(min_gap: float = 0.15):
    global _last_request
    with lock:
        now = time.monotonic()
        gap = min_gap - (now - _last_request)
        if gap > 0:
            time.sleep(gap)
        _last_request = time.monotonic()


def http_get_json(url: str) -> dict:
    last_err = None
    for attempt in range(MAX_RETRIES):
        polite_wait(0.20)
        req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2.0 * (attempt + 1))
                continue
            raise
        except (URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed after retries: {url} ({last_err})")


def cache_path(kind: str, key: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", key)[:180]
    return CACHE_DIR / f"{kind}-{safe}.json"


def cached_json(kind: str, key: str, fetcher):
    path = cache_path(kind, key)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    data = fetcher()
    path.write_text(json.dumps(data))
    return data


def search_entities(name: str) -> list[dict]:
    def fetch():
        url = (
            f"{API}?action=wbsearchentities&search={quote(name)}"
            f"&language=en&uselang=en&format=json&limit=5&type=item"
        )
        return http_get_json(url)

    data = cached_json("search", name, fetch)
    return data.get("search") or []


def get_entities(ids: list[str]) -> dict:
    out = {}
    missing = []
    for qid in ids:
        path = cache_path("entity", qid)
        if path.exists():
            try:
                out[qid] = json.loads(path.read_text())
                continue
            except json.JSONDecodeError:
                pass
        missing.append(qid)

    for i in range(0, len(missing), 40):
        chunk = missing[i : i + 40]
        url = (
            f"{API}?action=wbgetentities&ids={'|'.join(chunk)}"
            f"&props=claims|labels|descriptions|aliases"
            f"&languages=en|mul&format=json"
        )
        data = http_get_json(url)
        entities = data.get("entities") or {}
        for qid, ent in entities.items():
            cache_path("entity", qid).write_text(json.dumps(ent))
            out[qid] = ent
    return out


def lang_text(obj: dict | None, langs=("en", "mul")) -> str:
    if not obj:
        return ""
    for lang in langs:
        node = obj.get(lang)
        if not node:
            continue
        if isinstance(node, list):
            vals = [x.get("value", "") for x in node if isinstance(x, dict) and x.get("value")]
            if vals:
                return vals[0] if lang != "en" or len(vals) == 1 else " ".join(vals)
        val = node.get("value") if isinstance(node, dict) else ""
        if val:
            return val
    return ""


def all_lang_texts(obj: dict | None, langs=("en", "mul")) -> list[str]:
    if not obj:
        return []
    out = []
    for lang in langs:
        node = obj.get(lang)
        if not node:
            continue
        if isinstance(node, list):
            out.extend(x.get("value", "") for x in node if isinstance(x, dict) and x.get("value"))
        elif isinstance(node, dict) and node.get("value"):
            out.append(node["value"])
    return out


PARENTHETICAL_RE = re.compile(r"\s*\([^)]*\)\s*")


def official_labels(ent: dict, hit: dict | None = None) -> list[str]:
    labels = all_lang_texts(ent.get("labels"))
    if hit and hit.get("label"):
        labels.append(hit["label"])
    expanded = []
    for lab in labels:
        expanded.append(lab)
        stripped = PARENTHETICAL_RE.sub(" ", lab).strip()
        if stripped and stripped != lab:
            expanded.append(stripped)
    seen = set()
    out = []
    for lab in expanded:
        k = norm(lab)
        if k and k not in seen:
            seen.add(k)
            out.append(lab)
    return out


def en_aliases(ent: dict) -> list[str]:
    aliases = (ent.get("aliases") or {})
    out = []
    for lang in ("en", "mul"):
        for a in aliases.get(lang) or []:
            if a.get("value"):
                out.append(a["value"])
    return out


def claim_values_item(ent: dict, pid: str) -> list[str]:
    claims = (ent.get("claims") or {}).get(pid) or []
    ids = []
    for c in claims:
        if (c.get("rank") or "normal") == "deprecated":
            continue
        snak = c.get("mainsnak") or {}
        dv = snak.get("datavalue") or {}
        val = dv.get("value")
        if isinstance(val, dict) and val.get("id"):
            ids.append(val["id"])
    return ids


def claim_urls(ent: dict, pid: str) -> list[str]:
    claims = (ent.get("claims") or {}).get(pid) or []
    preferred, normal = [], []
    for c in claims:
        rank = c.get("rank") or "normal"
        if rank == "deprecated":
            continue
        snak = c.get("mainsnak") or {}
        dv = snak.get("datavalue") or {}
        val = dv.get("value")
        if isinstance(val, str) and val.startswith(("http://", "https://")):
            (preferred if rank == "preferred" else normal).append(val)
    return preferred or normal


def hostname_from_url(url: str) -> str | None:
    try:
        p = urlparse(url.strip())
    except Exception:
        return None
    host = (p.hostname or "").lower()
    if not host:
        return None
    if host.startswith("www."):
        host = host[4:]
    if not host or "." not in host:
        return None
    return host


def is_blocked_host(host: str) -> bool:
    return any(part in host for part in BLOCKED_HOST_PARTS)


def tld_of(host: str) -> str:
    return host.rsplit(".", 1)[-1]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def tokens(s: str) -> list[str]:
    return [t for t in NON_ALNUM_RE.split(norm(s)) if t]


def strip_legal(toks: list[str]) -> list[str]:
    return [t for t in toks if t not in LEGAL_SUFFIXES]


def mentions(text: str, words: tuple[str, ...]) -> bool:
    t = (text or "").lower()
    for w in words:
        if len(w) <= 2:
            if re.search(rf"\b{re.escape(w)}\b", t):
                return True
        else:
            if w in t:
                return True
    return False


def looks_like_org(ent: dict, p31_labels: dict[str, str], hit: dict | None = None) -> tuple[bool, str]:
    desc = lang_text(ent.get("descriptions")) or ((hit or {}).get("description") or "")
    p31_ids = claim_values_item(ent, "P31")
    p31_text = " ".join(p31_labels.get(i, "") for i in p31_ids)
    if mentions(p31_text, P31_ORG_WORDS):
        return True, f"P31:{p31_text}"
    if mentions(desc, DESC_ORG_WORDS):
        return True, f"desc:{desc}"
    return False, f"no-org p31={p31_ids} desc={desc}"


def nationality_contradicts(desc: str, host: str) -> bool:
    """Drop American-company + foreign country-TLD pairs (e.g. pinterest.de)."""
    d = (desc or "").lower()
    if not any(h in d for h in US_HINTS):
        return False
    tld = tld_of(host)
    if tld in GENERIC_TLDS:
        return False
    return True


def pick_domain(ent: dict, desc: str) -> str | None:
    hosts = []
    for url in claim_urls(ent, "P856"):
        host = hostname_from_url(url)
        if not host or is_blocked_host(host):
            continue
        if nationality_contradicts(desc, host):
            continue
        hosts.append(host)
    if not hosts:
        return None
    # stable: already preferred-rank first from claim_urls
    return hosts[0]


def theme_score(desc: str, label: str) -> bool:
    return mentions(desc, THEME_WORDS) or mentions(label, THEME_WORDS)


def compact(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def exact_official(name: str, labels: list[str]) -> bool:
    n = norm(name)
    cn = compact(name)
    for lab in labels:
        if norm(lab) == n:
            return True
        # spacing / punctuation only (MercadoLibre vs Mercado Libre)
        if cn and len(cn) >= 6 and compact(lab) == cn:
            return True
    return False


def close_official(name: str, labels: list[str]) -> bool:
    nt = strip_legal(tokens(name))
    if not nt:
        return False
    for lab in labels:
        lt = strip_legal(tokens(lab))
        if lt and lt == nt:
            return True
    return False


def prefix_official(name: str, labels: list[str]) -> bool:
    """Name is a leading token sequence of the label (or vice versa), extras are corporate."""
    nt = strip_legal(tokens(name))
    if not nt:
        return False
    for lab in labels:
        lt = strip_legal(tokens(lab))
        if not lt:
            continue
        if lt == nt:
            return True
        if len(lt) > len(nt) and lt[: len(nt)] == nt:
            extra = lt[len(nt) :]
            if extra and all(t in CORPORATE_EXTRAS for t in extra):
                return True
        if len(nt) > len(lt) and nt[: len(lt)] == lt:
            extra = nt[len(lt) :]
            if extra and all(t in CORPORATE_EXTRAS for t in extra):
                return True
    return False


def hit_looks_org(hit: dict) -> bool:
    desc = hit.get("description") or ""
    return mentions(desc, P31_ORG_WORDS + DESC_ORG_WORDS + ("public company", "corporation"))


def decide(name: str, search_hits: list[dict], entities: dict, p31_labels: dict) -> dict:
    inspected = []
    candidates = []
    p856_by_exact_label = {}  # norm(label) -> set of hosts for ANY hit with P856

    for hit in search_hits:
        qid = hit.get("id")
        if not qid:
            continue
        ent = entities.get(qid)
        if not ent or ent.get("missing") is not None:
            inspected.append({"qid": qid, "reason": "missing"})
            continue
        labels = official_labels(ent, hit)
        label = labels[0] if labels else (hit.get("label") or "")
        desc = lang_text(ent.get("descriptions")) or (hit.get("description") or "")
        org, org_why = looks_like_org(ent, p31_labels, hit)
        domain = pick_domain(ent, desc)
        raw_hosts = []
        for url in claim_urls(ent, "P856"):
            h = hostname_from_url(url)
            if h and not is_blocked_host(h):
                raw_hosts.append(h)
        if exact_official(name, labels) and raw_hosts:
            p856_by_exact_label.setdefault(norm(name), set()).update(raw_hosts)
        rec = {
            "qid": qid,
            "label": label,
            "labels": labels,
            "description": desc,
            "org": org,
            "org_why": org_why,
            "has_p856": bool(raw_hosts),
            "domain": domain,
            "raw_hosts": raw_hosts,
            "exact": exact_official(name, labels),
            "close": close_official(name, labels),
            "prefix": prefix_official(name, labels),
            "theme": theme_score(desc, label),
        }
        inspected.append(rec)
        if org and domain:
            candidates.append(rec)

    result = {
        "name": name,
        "domain": None,
        "qid": None,
        "status": "unresolved",
        "reason": "",
        "inspected": inspected,
    }

    if not search_hits:
        result["reason"] = "no-wikidata-hits"
        return result
    if not candidates:
        result["reason"] = "no-org-with-official-website"
        return result

    # Competing organisation in the search set (even without P856)
    competing_org_hits = []
    for hit in search_hits:
        qid = hit.get("id")
        ent = entities.get(qid) if qid else None
        if not ent:
            continue
        labels = official_labels(ent, hit)
        if exact_official(name, labels) or close_official(name, labels) or prefix_official(name, labels):
            org, _ = looks_like_org(ent, p31_labels, hit)
            if org or hit_looks_org(hit):
                competing_org_hits.append(qid)

    def finish(chosen, reason, status="resolved"):
        result.update(
            domain=chosen["domain"] if status == "resolved" else None,
            qid=chosen.get("qid") if status == "resolved" else None,
            status=status,
            reason=reason,
        )
        return result

    def pick_from(pool: list[dict], kind: str):
        if not pool:
            return None
        if len(pool) == 1:
            return finish(pool[0], kind)
        themed = [c for c in pool if c["theme"]]
        if len(themed) == 1:
            return finish(themed[0], kind + "+theme")
        domains = {c["domain"] for c in (themed or pool)}
        # same registrable outcome
        if len({c["domain"] for c in pool}) == 1:
            chosen = themed[0] if themed else pool[0]
            return finish(chosen, f"{kind}; same-domain-among-{len(pool)}")
        return finish(
            pool[0],
            f"several {kind} matches: "
            + "; ".join(f"{c['qid']} {c['label']} -> {c['domain']}" for c in pool),
            status="skipped-ambiguous",
        )

    exact = [c for c in candidates if c["exact"]]
    if exact:
        # If another exact-label hit (any type) publishes a different host, be careful
        exact_hosts = set()
        for h in p856_by_exact_label.get(norm(name), set()):
            exact_hosts.add(h)
        cand_hosts = {c["domain"] for c in exact}
        if exact_hosts and cand_hosts and not cand_hosts.issubset(exact_hosts) and len(exact_hosts) > 1:
            # conflicting official websites on the exact name
            if len(cand_hosts) > 1 or (exact_hosts - cand_hosts):
                # only skip when hosts truly disagree and we cannot theme-pick
                themed = [c for c in exact if c["theme"]]
                if len(themed) == 1:
                    return finish(themed[0], "exact+theme-vs-conflicting-hosts")
                return finish(
                    exact[0],
                    f"conflicting P856 on exact label: {sorted(exact_hosts)}",
                    status="skipped-ambiguous",
                )
        # competing similarly-named orgs without a unique themed exact
        other_orgs = [q for q in competing_org_hits if q not in {c["qid"] for c in exact}]
        described_exact = [c for c in exact if c.get("description")]
        # skip only when every exact hit is undescribed and another org is in the result set
        if other_orgs and not described_exact and not any(c["theme"] for c in exact):
            return finish(
                exact[0],
                f"exact but competing orgs {other_orgs} and empty description",
                status="skipped-ambiguous",
            )
        # prefer described exact entities when a shell/subsidiary also matches the label
        if described_exact and len(described_exact) < len(exact):
            exact = described_exact
        picked = pick_from(exact, "exact")
        if picked:
            return picked

    strong = [c for c in candidates if c["close"] or c["prefix"]]
    if strong:
        # empty-description exact-ish + another org in the result list → unsure
        other_orgs = [q for q in competing_org_hits if q not in {c["qid"] for c in strong}]
        if other_orgs and any(not c["description"] for c in strong) and not any(c["theme"] for c in strong):
            return finish(
                strong[0],
                f"close/prefix but competing orgs {other_orgs}",
                status="skipped-ambiguous",
            )
        picked = pick_from(strong, "close/prefix")
        if picked:
            return picked

    # last resort: two or more org candidates agree on one official host
    if len(candidates) >= 2 and len({c["domain"] for c in candidates}) == 1:
        return finish(candidates[0], "same-domain-all-org-candidates")

    if len(candidates) == 1:
        only = candidates[0]
        extras = LEGAL_SUFFIXES | GEO_EXTRAS
        nt = strip_legal(tokens(name))
        ok = False
        for lab in only["labels"]:
            lt = strip_legal(tokens(lab))
            if not nt or not lt:
                continue
            if lt == nt:
                ok = True
                break
            if len(lt) > len(nt) and lt[: len(nt)] == nt and all(t in extras for t in lt[len(nt) :]):
                ok = True
                break
            if len(nt) > len(lt) and nt[: len(lt)] == lt and all(t in extras for t in nt[len(lt) :]):
                ok = True
                break
        if ok:
            return finish(only, "unique-org-label-variant")
        result["reason"] = (
            f"no-exact-or-close-label; 1 org candidate "
            f"{candidates[0]['qid']} {candidates[0]['label']}"
        )
        return result
    result["status"] = "skipped-ambiguous"
    result["reason"] = (
        f"no-exact-or-close; {len(candidates)} org candidates: "
        + "; ".join(f"{c['qid']} {c['label']}" for c in candidates)
    )
    return result


def main():
    queue = json.loads(QUEUE_PATH.read_text())
    companies = queue["companies"]
    names = [c["name"] for c in companies]
    print(f"resolving {len(names)} companies via Wikidata", flush=True)

    searches: dict[str, list] = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(search_entities, n): n for n in names}
        done = 0
        for fut in as_completed(futs):
            n = futs[fut]
            try:
                searches[n] = fut.result()
            except Exception as e:
                print(f"SEARCH FAIL {n}: {e}", flush=True)
                searches[n] = []
            done += 1
            if done % 50 == 0 or done == len(names):
                print(f"  search {done}/{len(names)}", flush=True)

    all_qids = []
    seen = set()
    for hits in searches.values():
        for h in hits:
            qid = h.get("id")
            if qid and qid not in seen:
                seen.add(qid)
                all_qids.append(qid)
    print(f"fetching {len(all_qids)} entities", flush=True)
    entities = get_entities(all_qids)

    p31_ids = []
    p31_seen = set()
    for ent in entities.values():
        for qid in claim_values_item(ent, "P31"):
            if qid not in p31_seen:
                p31_seen.add(qid)
                p31_ids.append(qid)
    print(f"fetching {len(p31_ids)} P31 types", flush=True)
    p31_entities = get_entities(p31_ids)
    p31_labels = {
        qid: lang_text(ent.get("labels")) or ""
        for qid, ent in p31_entities.items()
    }

    decisions = []
    for c in companies:
        dec = decide(c["name"], searches.get(c["name"], []), entities, p31_labels)
        decisions.append(dec)
        c["domain"] = dec["domain"] if dec["status"] == "resolved" else None

    resolved = [d for d in decisions if d["status"] == "resolved"]
    unresolved = [d for d in decisions if d["status"] == "unresolved"]
    skipped = [d for d in decisions if d["status"] == "skipped-ambiguous"]

    queue["companies"] = companies
    QUEUE_PATH.write_text(json.dumps(queue, indent=2) + "\n")

    log = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": "wikidata-wbsearchentities + wbgetentities P856",
        "user_agent": UA,
        "rules": {
            "accept": "P856 official website + organization (P31 company/business/enterprise or description company/startup/software)",
            "blocked_hosts": list(BLOCKED_HOST_PARTS),
            "prefer": "exact English/mul official label; else unique close/prefix with corporate suffixes; theme software/AI/security/cloud if several",
            "hostname": "host only, no www/path; no guess if unsure",
        },
        "counts": {
            "total": len(decisions),
            "resolved": len(resolved),
            "unresolved": len(unresolved),
            "skipped-ambiguous": len(skipped),
        },
        "resolved": [
            {
                "name": d["name"],
                "domain": d["domain"],
                "qid": d["qid"],
                "reason": d["reason"],
            }
            for d in decisions
            if d["status"] == "resolved"
        ],
        "unresolved": [
            {"name": d["name"], "reason": d["reason"]}
            for d in decisions
            if d["status"] == "unresolved"
        ],
        "skipped-ambiguous": [
            {
                "name": d["name"],
                "reason": d["reason"],
                "candidates": [
                    {
                        "qid": i.get("qid"),
                        "label": i.get("label"),
                        "domain": i.get("domain"),
                        "description": i.get("description"),
                    }
                    for i in d.get("inspected", [])
                    if i.get("org") and i.get("domain")
                ],
            }
            for d in decisions
            if d["status"] == "skipped-ambiguous"
        ],
    }
    LOG_PATH.write_text(json.dumps(log, indent=2) + "\n")

    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text())
        state["note"] = (
            "hourly batches; do not invent domains; "
            f"wikidata P856 filled {len(resolved)}/{len(decisions)} "
            f"({len(skipped)} ambiguous left null)"
        )
        STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")

    print("COUNTS", json.dumps(log["counts"]))
    print("SKIPPED")
    for s in skipped:
        print(f"  {s['name']}: {s['reason']}")
    print("FIRST20")
    for d in resolved[:20]:
        print(f"  {d['name']} → {d['domain']}")


if __name__ == "__main__":
    main()
