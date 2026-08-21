#!/usr/bin/env python3
"""Merge curated first-party AI-page URLs into data.json and filled dossiers."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PAGES = SITE / "data" / "aiti-pages.json"
DATA = SITE / "data.json"

ROW_RE = re.compile(
    r'(<p class="sec-kicker">Instruments</p>[\s\S]*?)(</tbody>\s*</table>)',
    re.I,
)


def official_a(url: str, host: str) -> str:
    return (
        f'<a class="official" href="{url}" rel="noopener noreferrer">{host}</a>'
    )


def main() -> int:
    doc = json.loads(PAGES.read_text())
    pages = doc.get("pages") or {}
    seen = doc.get("seen") or "2026-08-20"
    data = json.loads(DATA.read_text())
    by_slug = {c["slug"]: c for c in data["companies"]}

    for slug, rec in pages.items():
        row = by_slug.get(slug)
        if not row:
            raise SystemExit(f"unknown slug {slug}")
        url = rec["url"]
        host = rec.get("host") or ""
        filed = {"url": url, "host": host, "seen": rec.get("seen") or seen}
        row["ai_page"] = dict(filed)
        inst = row.setdefault("instruments", {})
        inst["ai"] = dict(filed)

        html_path = SITE / "c" / f"{slug}.html"
        html = html_path.read_text(encoding="utf-8")
        if url in html and ">AI page<" in html:
            continue
        row_html = (
            f"<tr><td>AI page</td><td>{official_a(url, host)}</td>"
            f"<td>21 Aug 2026</td></tr>"
        )
        patched, n = ROW_RE.subn(r"\1" + row_html + r"\2", html, count=1)
        if n != 1:
            raise SystemExit(f"could not patch dossier {slug}")
        html_path.write_text(patched, encoding="utf-8")

    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("filed", len(pages), "open", len(doc.get("open") or []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
