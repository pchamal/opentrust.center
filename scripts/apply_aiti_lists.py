#!/usr/bin/env python3
"""File sourced AITI list companies onto the register. Do not invent domains or pages."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
LISTS = SITE / "data" / "aiti-lists.json"
EXTRA = ROOT / "extra-companies.json"
ENRICHED_PATHS = (SITE / "data" / "enriched.json", ROOT / "data" / "enriched.json")


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


SLUG_ALIASES = {
    "humans&": "humans-and",
    "humansand": "humans-and",
}


def name_to_slug(name: str) -> str:
    key = (name or "").strip().lower()
    if key in SLUG_ALIASES:
        return SLUG_ALIASES[key]
    return re.sub(r"[^a-z0-9]+", "-", key).strip("-")


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
    slug = rec.get("slug")
    if slug and slug in by_slug:
        return by_slug[slug]
    domain = domain_of(rec.get("domain") or "")
    if domain and domain in by_domain:
        return by_domain[domain]
    name = norm_name(rec.get("name") or "")
    if name and name in by_name:
        return by_name[name]
    return None


def silent_row(rec: dict, list_id: str, source_url: str) -> dict:
    domain = domain_of(rec["domain"])
    slug = rec.get("slug") or name_to_slug(rec["name"])
    if not domain or not slug:
        raise SystemExit(f"missing domain or slug for {rec}")
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
    }


def main() -> int:
    lists = load_json(LISTS, {})
    extra = load_json(EXTRA, [])
    enriched_docs = [load_json(path, {"companies": []}) for path in ENRICHED_PATHS]
    companies = list(enriched_docs[0].get("companies") or [])
    by_slug, by_domain, by_name = index_register(companies)
    extra_slugs = {r.get("slug") for r in extra if r.get("slug")}

    added = []
    membership: dict[str, list[str]] = {}

    for lst in lists.get("lists") or []:
        list_id = lst["id"]
        source_url = lst["source_url"]
        recs = list(lst.get("companies") or [])
        for name in lst.get("match_names") or []:
            hit = by_name.get(norm_name(name))
            if hit:
                membership.setdefault(hit["slug"], [])
                if list_id not in membership[hit["slug"]]:
                    membership[hit["slug"]].append(list_id)
        for rec in recs:
            if not rec.get("domain"):
                raise SystemExit(f"{list_id}: {rec.get('name')} missing domain")
            hit = match_row(rec, by_slug, by_domain, by_name)
            if hit:
                membership.setdefault(hit["slug"], [])
                if list_id not in membership[hit["slug"]]:
                    membership[hit["slug"]].append(list_id)
                continue
            row = silent_row(rec, list_id, source_url)
            if row["slug"] in by_slug:
                membership.setdefault(row["slug"], [])
                if list_id not in membership[row["slug"]]:
                    membership[row["slug"]].append(list_id)
                continue
            companies.append(row)
            by_slug[row["slug"]] = row
            by_domain[row["domain"]] = row
            by_name[norm_name(row["name"])] = row
            membership.setdefault(row["slug"], [list_id])
            added.append(row)
            if row["slug"] not in extra_slugs:
                extra.append(extra_row(rec, list_id, source_url))
                extra_slugs.add(row["slug"])

    for row in companies:
        lists_for = membership.get(row["slug"]) or []
        if lists_for:
            row["aiti_lists"] = lists_for
            if not row.get("source_url"):
                # keep an existing source; new rows already carry the list URL
                continue

    for doc, path in zip(enriched_docs, ENRICHED_PATHS):
        # Keep the first document's merged company list; second copy tracks the same rows.
        if path == ENRICHED_PATHS[0]:
            doc["companies"] = companies
        else:
            have = {c["slug"] for c in (doc.get("companies") or [])}
            for row in added:
                if row["slug"] not in have:
                    doc.setdefault("companies", []).append(row)
            for row in doc.get("companies") or []:
                if row.get("slug") in membership:
                    row["aiti_lists"] = membership[row["slug"]]
        write_json(path, doc)

    write_json(EXTRA, extra)
    write_json(SITE / "data" / "aiti-membership.json", {
        "generated_at": lists.get("generated_at"),
        "rule": lists.get("rule"),
        "slugs": membership,
        "added": [{"name": r["name"], "slug": r["slug"], "domain": r["domain"], "source_url": r.get("source_url")} for r in added],
    })
    print("added", len(added), "membership", len(membership))
    for row in added:
        print(f"  {row['slug']} {row['domain']} {row['list']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
