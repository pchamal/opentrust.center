#!/usr/bin/env python3
"""File the verified 200-company AITI universe. Do not invent names, pages, or marks."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
LISTS = SITE / "data" / "aiti-lists.json"
EXTRA = ROOT / "extra-companies.json"
ENRICHED_PATHS = (SITE / "data" / "enriched.json", ROOT / "data" / "enriched.json")

SLUG_ALIASES = {
    "humans&": "humans-and",
    "humansand": "humans-and",
    "cursor": "anysphere",
    "fal": "fal-ai",
    "perplexity": "perplexity-ai",
    "minimax": "minimax-group",
    "thinking-machines-lab": "thinking-machine-labs",
    "liquid-ai": "liquid",
}

DOMAIN_TO_SLUG = {
    "cursor.com": "anysphere",
    "fal.ai": "fal-ai",
    "perplexity.ai": "perplexity-ai",
    "fireworks.ai": "fireworks-ai",
    "mistral.ai": "mistral-ai",
    "together.ai": "together-ai",
    "thinkingmachines.ai": "thinking-machine-labs",
    "huggingface.co": "hugging-face",
    "stability.ai": "stability-ai",
    "minimax.io": "minimax-group",
    "humansand.ai": "humans-and",
    "notion.com": "notion",
    "runway.com": "runway",
    "alibabacloud.com": "alibaba",
    "moonshot.cn": "moonshot-ai",
    "liquid.ai": "liquid",
    "skild.ai": "skild-ai",
    "worldlabs.ai": "world-labs",
}

SOURCE_URLS = {
    "forbes-ai-50-2026": "https://www.forbes.com/lists/ai50/",
    "forbes-ai-50-brink-2026": "https://www.forbes.com/sites/sofiachierchio/2026/04/16/the-ai-50-brink-list/",
    "cb-insights-ai-100-2026": "https://www.cbinsights.com/research/report/artificial-intelligence-top-startups-2026/",
    "arena-org": "https://arena.ai/leaderboard",
    "openrouter-provider": "https://openrouter.ai/api/v1/providers",
    "hugging-face-org": "https://huggingface.co/",
}


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def name_to_slug(name: str) -> str:
    key = (name or "").strip().lower()
    if key in SLUG_ALIASES:
        return SLUG_ALIASES[key]
    slug = re.sub(r"[^a-z0-9]+", "-", key).strip("-")
    return SLUG_ALIASES.get(slug, slug)


def norm_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def domain_of(value: str) -> str:
    d = (value or "").strip().lower().replace("https://", "").replace("http://", "")
    d = d.split("/")[0].removeprefix("www.")
    return d


def index_register(companies: list[dict]) -> tuple[dict, dict, dict]:
    by_slug, by_domain, by_name = {}, {}, {}
    for row in companies:
        slug = row.get("slug")
        if slug:
            by_slug[slug] = row
        domain = domain_of(row.get("domain") or "")
        if domain:
            by_domain.setdefault(domain, row)
        name = norm_name(row.get("name") or "")
        if name:
            by_name.setdefault(name, row)
    return by_slug, by_domain, by_name


def match_row(rec: dict, by_slug: dict, by_domain: dict, by_name: dict):
    domain = domain_of(rec.get("domain") or "")
    mapped = DOMAIN_TO_SLUG.get(domain)
    if mapped and mapped in by_slug:
        return by_slug[mapped]
    slug = rec.get("slug") or name_to_slug(rec.get("name") or "")
    if slug and slug in by_slug:
        return by_slug[slug]
    if domain and domain in by_domain:
        return by_domain[domain]
    name = norm_name(rec.get("name") or "")
    if name and name in by_name:
        return by_name[name]
    return None


def silent_row(rec: dict, list_id: str, source_url: str) -> dict:
    domain = domain_of(rec["domain"])
    slug = rec.get("slug") or name_to_slug(rec["name"])
    official = (rec.get("official_url") or "").strip()
    if not domain or not slug or not official:
        raise SystemExit(f"missing domain, slug, or official_url for {rec}")
    return {
        "rank": None,
        "name": rec["name"],
        "slug": slug,
        "domain": domain,
        "found": False,
        "trust_url": None,
        "final_url": None,
        "vendor": "unknown",
        "title": "",
        "probed": 0,
        "source": source_url,
        "source_url": source_url,
        "official_url": official,
        "summary": "",
        "list": list_id,
        "certs": [],
        "links": {},
        "subprocessors": [],
        "disclosure": {"score": 0, "tier": "silent", "factors": {}},
        "aiti_lists": [list_id],
    }


def extra_row(rec: dict, list_id: str, source_url: str) -> dict:
    return {
        "name": rec["name"],
        "slug": rec.get("slug") or name_to_slug(rec["name"]),
        "domain": domain_of(rec["domain"]),
        "aliases": [],
        "source": list_id,
        "source_url": source_url,
        "official_url": rec.get("official_url") or "",
    }


def stamp_membership(companies: list[dict], membership: dict[str, list[str]], official_by_slug: dict[str, str]) -> None:
    for row in companies:
        slug = row.get("slug")
        lists_for = membership.get(slug) or []
        if lists_for:
            row["aiti_lists"] = lists_for
            official = official_by_slug.get(slug)
            if official:
                row["official_url"] = official
        else:
            row.pop("aiti_lists", None)
            row.pop("official_url", None)


def universe_records(lists: dict) -> list[dict]:
    recs = list(lists.get("companies") or [])
    if not recs:
        raise SystemExit("aiti-lists.json has no companies")
    if len(recs) != 200:
        raise SystemExit(f"verified universe must be 200 companies, got {len(recs)}")
    seen_names, seen_domains = set(), set()
    for rec in recs:
        if not rec.get("name") or not rec.get("domain") or not rec.get("source") or not rec.get("official_url"):
            raise SystemExit(f"incomplete universe row: {rec}")
        if rec["name"] in seen_names or rec["domain"] in seen_domains:
            raise SystemExit(f"duplicate universe row: {rec}")
        seen_names.add(rec["name"])
        seen_domains.add(rec["domain"])
        if rec["source"] not in SOURCE_URLS:
            raise SystemExit(f"unknown source {rec['source']} for {rec['name']}")
        if not str(rec["official_url"]).startswith(("http://", "https://")):
            raise SystemExit(f"official_url must be a fetched homepage for {rec['name']}")
    return recs


def main() -> int:
    lists = load_json(LISTS, {})
    extra = load_json(EXTRA, [])
    enriched_docs = [load_json(path, {"companies": []}) for path in ENRICHED_PATHS]
    companies = list(enriched_docs[0].get("companies") or [])
    by_slug, by_domain, by_name = index_register(companies)
    extra_slugs = {r.get("slug") for r in extra if r.get("slug")}

    added = []
    membership: dict[str, list[str]] = {}
    official_by_slug: dict[str, str] = {}

    for rec in universe_records(lists):
        list_id = rec["source"]
        source_url = SOURCE_URLS[list_id]
        official = rec["official_url"].strip()
        hit = match_row(rec, by_slug, by_domain, by_name)
        if hit:
            slug = hit["slug"]
            membership.setdefault(slug, [])
            if list_id not in membership[slug]:
                membership[slug].append(list_id)
            official_by_slug[slug] = official
            continue
        row = silent_row(rec, list_id, source_url)
        if row["slug"] in by_slug:
            slug = row["slug"]
            membership.setdefault(slug, [])
            if list_id not in membership[slug]:
                membership[slug].append(list_id)
            official_by_slug[slug] = official
            continue
        companies.append(row)
        by_slug[row["slug"]] = row
        by_domain[row["domain"]] = row
        by_name[norm_name(row["name"])] = row
        membership[row["slug"]] = [list_id]
        official_by_slug[row["slug"]] = official
        added.append(row)
        if row["slug"] not in extra_slugs:
            extra.append(extra_row(rec, list_id, source_url))
            extra_slugs.add(row["slug"])

    if len(membership) != 200:
        raise SystemExit(f"membership must be 200 slugs, got {len(membership)}")

    stamp_membership(companies, membership, official_by_slug)

    for doc, path in zip(enriched_docs, ENRICHED_PATHS):
        if path == ENRICHED_PATHS[0]:
            doc["companies"] = companies
        else:
            have = {c["slug"] for c in (doc.get("companies") or [])}
            for row in added:
                if row["slug"] not in have:
                    doc.setdefault("companies", []).append(row)
            stamp_membership(doc.get("companies") or [], membership, official_by_slug)
        write_json(path, doc)

    write_json(EXTRA, extra)
    write_json(SITE / "data" / "aiti-membership.json", {
        "generated_at": lists.get("generated_at"),
        "rule": lists.get("rule"),
        "count": len(membership),
        "slugs": membership,
        "added": [
            {
                "name": r["name"],
                "slug": r["slug"],
                "domain": r["domain"],
                "source_url": r.get("source_url"),
                "official_url": r.get("official_url"),
            }
            for r in added
        ],
    })
    print("added", len(added), "membership", len(membership))
    for row in added:
        print(f"  {row['slug']} {row['domain']} {row['list']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
