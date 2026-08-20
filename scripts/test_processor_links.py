#!/usr/bin/env python3
"""Named processors link to a dossier or the map node. No invented pages."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from build_pages import (  # noqa: E402
    looks_like_date_name,
    looks_like_processor_name,
    link_mark_words,
    map_cert,
    processor_cell,
    processor_href,
    register_slug_for,
)


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"fail: {msg}")


def main() -> int:
    check(
        processor_href({"name": "OpenAI", "slug": "openai", "id": "openai"})
        == "./openai.html",
        "register slug goes to dossier",
    )
    check(
        processor_href({"name": "Amazon Web Services", "slug": "amazon-web-services", "id": "aws"})
        == "./amazon-web-services.html",
        "aws node with amazon-web-services slug goes to that dossier",
    )
    check(
        processor_href({"name": "WorkOS", "slug": None, "id": "workos"})
        == "../graph.html#p=workos",
        "map-only node goes to #p=",
    )
    check(processor_href({"name": "Ghost"}) is None, "no file and no node stays unlinked")

    cell = processor_cell({"name": "OpenAI", "slug": "openai", "id": "openai"})
    check(cell == '<a href="./openai.html">OpenAI</a>', f"cell {cell}")

    by_slug = {"openai": {"slug": "openai"}, "amazon-web-services": {"slug": "amazon-web-services"}}
    by_domain = {"aws.amazon.com": "amazon-web-services"}
    by_name = {"amazon web services": "amazon-web-services"}
    check(
        register_slug_for(
            {"id": "aws", "name": "Amazon Web Services", "domain": "aws.amazon.com"},
            by_slug,
            by_domain,
            by_name,
        )
        == "amazon-web-services",
        "aws node resolves to amazon-web-services",
    )
    check(
        register_slug_for({"id": "google-gemini", "name": "Google Gemini"}, by_slug, by_domain, by_name)
        is None,
        "do not invent a google-gemini dossier",
    )
    check(map_cert("DORA")["id"] == "dora", "dora has a framework entry")
    check(map_cert("EU-US DPF")["id"] == "eu-us-dpf", "eu-us dpf has a framework entry")
    check(map_cert("NIST 800-171")["id"] == "nist-800-171", "nist 800-171 has a framework entry")
    check(map_cert("SOC 2")["id"] == "soc-2-type-ii", "soc 2 alias stays on the existing file")
    check(map_cert("SLSA")["id"] is None, "do not invent a slsa page")
    clerk = link_mark_words(
        "On file: SOC 2 Type II, AIUC-1.",
        [
            {"name": "SOC 2 Type II", "id": "soc-2-type-ii"},
            {"name": "AIUC-1", "id": "aiuc-1"},
        ],
    )
    check(
        'href="../attestations.html#soc-2-type-ii">SOC 2 Type II</a>' in clerk
        and 'href="../attestations.html#aiuc-1">AIUC-1</a>' in clerk,
        f"clerk links {clerk}",
    )
    check(looks_like_date_name("29 April 2026"), "publisher rejects 29 April 2026")
    check(looks_like_date_name("2026-04-29"), "publisher rejects ISO date")
    check(looks_like_date_name("2025"), "publisher rejects a bare year")
    check(not looks_like_processor_name("01 April 2025"), "date is not a processor name")
    check(looks_like_processor_name("Amazon Web Services"), "AWS still looks like a processor")
    check(not looks_like_date_name("OpenAI"), "OpenAI is not a date")
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
