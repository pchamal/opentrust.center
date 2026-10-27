#!/usr/bin/env python3
"""Resolve official domains for named-processor gap rows. Never invent."""
from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path("/workspace/trust-index")
sys.path.insert(0, "/workspace")
sys.path.insert(0, "/tmp")
sys.path.insert(0, str(ROOT / "scripts"))
import resolve_wikidata_domains as wd  # noqa: E402
from _named_processor_gap import gap_rows  # noqa: E402
from processor_aliases import REGISTER_ALIASES  # noqa: E402

QUEUE_PATH = ROOT / "data" / "crawl-queue.json"
ENRICHED_PATH = ROOT / "data" / "enriched.json"
OUT = ROOT / "data" / "render" / "named-processor-gap-resolve-hour.json"
UA = "opentrust.center/1.0 (+https://opentrust.center)"
EXTRA_BLOCKED = (
    "archive.org", "web.archive", "wikipedia.", "wikimedia.", "wikidata.",
    "fandom.com", "blogspot.", "wordpress.com", "twitter.com", "x.com",
    "facebook.com", "linkedin.com", "youtube.com", "crunchbase.com",
    "instagram.com", "github.com",
)

def nkey(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def host_of(url: str) -> str:
    try:
        h = (urlparse(url).hostname or "").lower()
    except Exception:
        return ""
    if h.startswith("www."):
        h = h[4:]
    return h


def host_ok(host: str | None) -> bool:
    if not host or "." not in host:
        return False
    h = host.lower()
    if h.startswith("www."):
        h = h[4:]
    for part in EXTRA_BLOCKED:
        if part.endswith("."):
            if part in h:
                return False
        elif h == part or h.endswith("." + part):
            return False
    if wd.is_blocked_host(h):
        return False
    return True


def domain_plausible(name: str, host: str) -> bool:
    if not host_ok(host):
        return False
    parts = host.split(".")
    sld = {"co", "com", "ne", "or", "ac", "gov", "org", "net"}
    if len(parts) >= 3 and parts[-2] in sld:
        label = parts[-3]
    else:
        label = parts[-2] if len(parts) >= 2 else parts[0]
    nt = set(wd.strip_legal(wd.tokens(name)))
    ht = set(wd.tokens(label.replace("-", " ")))
    weak = {
        "zero", "one", "net", "network", "networks", "security", "cloud", "data",
        "systems", "system", "group", "global", "digital", "tech", "the", "inc",
        "labs", "lab", "ai", "io", "app", "hq", "solutions", "solution", "cyber",
        "computer", "software", "computing", "providers", "services", "service",
        "info", "consulting",
    }
    distinctive = (nt & ht) - weak
    if distinctive:
        return True
    cn, ch = wd.compact(name), wd.compact(label)
    if cn and ch:
        if cn == ch:
            return True
        if len(cn) >= 5 and (cn in ch or ch in cn):
            return True
        initials = "".join(t[0] for t in wd.strip_legal(wd.tokens(name)) if t)
        if initials and initials == ch and len(initials) >= 3:
            return True
    return False


def fetch(url: str) -> str:
    last = None
    for attempt in range(4):
        wd.polite_wait(0.2)
        req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
        try:
            with urlopen(req, timeout=25) as resp:
                raw = resp.read(400000)
                return raw.decode("utf-8", "ignore")
        except HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(1.5 * (attempt + 1))
                continue
            return ""
        except (URLError, TimeoutError) as e:
            last = e
            time.sleep(1.2 * (attempt + 1))
    return ""


HREF_RE = re.compile(r'href=["\'](https?://[^"\']+)["\']', re.I)


def naming_list_homepage(name: str, html: str, namer_host: str) -> tuple[str | None, int]:
    """Pick a first-party homepage linked near the published processor name."""
    if not html or not name:
        return None, 0
    text = unescape(html)
    low = text.lower()
    needle = name.lower()
    idx = low.find(needle)
    if idx < 0:
        # try without legal tail
        short = re.sub(r"\s+(inc\.?|llc|ltd\.?|limited|corp\.?|gmbh|pte\.?|pvt\.?|eood|sas|slu)\b.*", "", needle, flags=re.I)
        if short and short != needle:
            idx = low.find(short)
        if idx < 0:
            return None, 0
    window = text[max(0, idx - 1800) : idx + 1800]
    scores = []
    for m in HREF_RE.finditer(window):
        url = m.group(1)
        host = host_of(url)
        if not host or host == namer_host or host.endswith("." + namer_host):
            continue
        if not domain_plausible(name, host):
            continue
        score = 10
        if wd.compact(name) and wd.compact(name) in wd.compact(host):
            score += 4
        scores.append((score, host, url))
    if not scores:
        return None, 0
    scores.sort(key=lambda t: (-t[0], t[1]))
    best = scores[0]
    # unique host among plausible
    hosts = {s[1] for s in scores}
    if len(hosts) > 1 and best[0] < 14:
        return None, best[0]
    return best[1], best[0]


def main() -> int:
    enr = json.loads(ENRICHED_PATH.read_text())
    register = {c["slug"]: c for c in enr.get("companies") or [] if c.get("slug")}
    print("register", len(register), flush=True)
    rows = gap_rows(register=register, min_named=1)
    print("gap", len(rows), flush=True)

    # destinations already on file for this hour's aliases
    print("alias dests on register:")
    for src, dest in [
        ("250ok", "validity"),
        ("processout", "checkout"),
        ("email-data-source", "messagebird"),
        ("neustar-info-services", "transunion-formerly-neustar-information-services"),
        ("telus-international", "telus"),
        ("propay", "global-payments"),
        ("sirius-federal", "cdw"),
        ("kiss-metrics-usage-analytics", "kiss-metrics"),
        ("kount", "equifax"),
        ("popout", "linear"),
        ("popout", "shippo"),
    ]:
        print(f"  {src} -> {dest}  dest_on_file={dest in register}", flush=True)

    searches: dict[str, list] = {}
    names = [r["name"] for r in rows]
    with ThreadPoolExecutor(max_workers=wd.WORKERS) as ex:
        futs = {ex.submit(wd.search_entities, n): n for n in names}
        done = 0
        for fut in as_completed(futs):
            n = futs[fut]
            try:
                searches[n] = fut.result()
            except Exception as e:
                print(f"SEARCH FAIL {n}: {e}", flush=True)
                searches[n] = []
            done += 1
            if done % 10 == 0 or done == len(names):
                print(f"  search {done}/{len(names)}", flush=True)

    all_qids, seenq = [], set()
    for hits in searches.values():
        for h in hits:
            qid = h.get("id")
            if qid and qid not in seenq:
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

    resolved, unresolved = [], []
    for r in rows:
        if r["slug"] in REGISTER_ALIASES and REGISTER_ALIASES[r["slug"]] in register:
            unresolved.append({**r, "reason": "already-aliased-on-register", "status": "alias"})
            continue
        if r.get("domain") and host_ok(r["domain"]):
            resolved.append({**r, "reason": "node-domain", "status": "resolved"})
            continue
        dec = wd.decide(r["name"], searches.get(r["name"], []), entities, p31_labels)
        print(
            f"  WD {r['slug']}: status={dec.get('status')} domain={dec.get('domain')} "
            f"qid={dec.get('qid')} reason={dec.get('reason')}",
            flush=True,
        )
        if dec["status"] == "resolved" and dec.get("domain") and host_ok(dec["domain"]) and domain_plausible(r["name"], dec["domain"]):
            rec = {**r, "domain": dec["domain"], "qid": dec.get("qid"), "reason": dec.get("reason"), "status": "resolved"}
            resolved.append(rec)
        else:
            unresolved.append({**r, "reason": dec.get("reason"), "status": dec.get("status"), "qid": dec.get("qid")})

    # first-party homepage on naming list for still-unresolved (not aliases)
    still = [u for u in unresolved if u.get("status") not in {"alias"}]
    pages: dict[str, str] = {}
    urls = sorted({u.get("source_url") for u in still if u.get("source_url")})
    print(f"fetching {len(urls)} naming lists", flush=True)
    for url in urls:
        pages[url] = fetch(url)
        print(f"  list {url} bytes={len(pages[url])}", flush=True)

    homepage_hits = []
    leftover = []
    for u in still:
        html = pages.get(u.get("source_url") or "") or ""
        namer = host_of(u.get("source_url") or "")
        host, score = naming_list_homepage(u["name"], html, namer)
        if host and score >= 10:
            rec = {**u, "domain": host, "reason": f"naming-list-homepage score={score}", "status": "resolved"}
            homepage_hits.append(rec)
            resolved.append(rec)
            print(f"  HOME {u['slug']} -> {host} score={score}", flush=True)
        else:
            leftover.append(u)

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gap": len(rows),
        "wikidata_resolved": [r for r in resolved if str(r.get("reason", "")).startswith("exact") or r.get("qid")],
        "enqueued_candidates": [
            {
                "name": r["name"],
                "slug": r["slug"],
                "domain": r["domain"],
                "source": "named-processor-gap",
                "source_url": r.get("source_url"),
                "named_by": r.get("named_by"),
                "reason": r.get("reason"),
            }
            for r in resolved
        ],
        "homepage_hits": [{"slug": r["slug"], "domain": r["domain"], "reason": r["reason"]} for r in homepage_hits],
        "unresolved_n": len(leftover),
        "unresolved": [{"slug": r["slug"], "name": r["name"], "reason": r.get("reason"), "status": r.get("status")} for r in leftover],
        "already_aliased": [r["slug"] for r in unresolved if r.get("status") == "alias"],
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("RESOLVED", len(resolved), "LEFTOVER", len(leftover), "ALIASED_ALREADY", report["already_aliased"], flush=True)
    for r in resolved:
        print(f"  {r['slug']:40} {r.get('domain'):30} {r.get('reason')}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
