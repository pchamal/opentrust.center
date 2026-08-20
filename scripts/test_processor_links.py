#!/usr/bin/env python3
"""Named processors link to a dossier or the map node. No invented pages."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from build_pages import processor_cell, processor_href, register_slug_for  # noqa: E402


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
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
