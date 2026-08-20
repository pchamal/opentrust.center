#!/usr/bin/env python3
"""Official-site years only. Title-only prefix matches and news articles stay off file."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from enrich import (  # noqa: E402
    apply_year_to_row,
    is_news_article_url,
    is_official_year_source,
    parse_official_founded_year,
    title_close,
    website_matches,
)


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"fail: {msg}")


def test_prefix_is_not_a_match() -> None:
    """The Manhattan / Sage Publishing class of false hits from PR 22."""
    check(
        not title_close("Manhattan", "Manhattan Associates"),
        "borough title is not Manhattan Associates",
    )
    check(
        not title_close("Sage Publishing", "Sage"),
        "Sage Publishing is not Sage Group",
    )
    check(
        not title_close("Sage", "Sage Group"),
        "Sage prefix is not Sage Group",
    )
    check(title_close("Adobe Inc.", "Adobe"), "corporate suffix is the same firm")
    check(title_close("Stripe, Inc.", "Stripe"), "Inc. suffix is the same firm")
    check(
        not website_matches(["https://en.wikipedia.org/wiki/Manhattan"], ["manh.com"]),
        "borough page is not Manhattan Associates",
    )
    check(
        not website_matches(["https://sagepub.com"], ["sage.com"]),
        "Sage Publishing is not Sage Group",
    )
    check(website_matches(["https://www.fico.com"], ["fico.com"]), "FICO official site matches")


def test_official_site_only() -> None:
    company = {"name": "Fivetran", "slug": "fivetran", "domain": "fivetran.com"}
    check(
        is_official_year_source("https://www.fivetran.com/about", company),
        "about page on the register domain is a source",
    )
    check(
        not is_official_year_source("https://en.wikipedia.org/wiki/Fivetran", company),
        "Wikipedia is not a source unless the official site confirms",
    )
    check(
        not is_official_year_source("https://www.crunchbase.com/organization/fivetran", company),
        "Crunchbase is not a source",
    )
    check(
        not is_official_year_source(
            "https://techcrunch.com/2013/01/01/fivetran-launches/", company
        ),
        "a news article is not a source",
    )
    check(is_news_article_url("https://www.fivetran.com/press/2023/series-d"), "dated press path is an article")
    check(not is_news_article_url("https://www.fivetran.com/press"), "press landing is not an article")
    check(
        not is_official_year_source("https://checkr.com/company/careers", company),
        "careers is not about/company/press",
    )


def test_parse_founded_sentence() -> None:
    check(parse_official_founded_year("Fivetran was founded in 2012 in Oakland.", "Fivetran") == 2012, "founded in YYYY")
    check(parse_official_founded_year("We were established in January 1998.") == 1998, "established month YYYY")
    check(parse_official_founded_year("Acme Founded: 2014", "Acme") == 2014, "founded colon year")
    check(parse_official_founded_year('{"@type":"Organization","foundingDate":"2015-03-01"}') == 2015, "JSON-LD foundingDate")
    check(parse_official_founded_year("In 2016 the company was founded in New York.") == 2016, "reverse founded")
    check(
        parse_official_founded_year("2012 Fivetran is founded out of Y Combinator", "Fivetran") == 2012,
        "timeline year-then-founded",
    )
    check(parse_official_founded_year("© 2024 Example Inc. All rights reserved.") is None, "copyright is not founding")
    check(parse_official_founded_year("Since 2020 we have offered SOC 2.") is None, "since YYYY alone is not founding")
    check(parse_official_founded_year("ISO/IEC 27001:2022 and SOC 2 Type II.") is None, "cert year is not founding")
    check(parse_official_founded_year("We launched the product in 2021.") is None, "launched is not founded")
    check(
        parse_official_founded_year("Founded in 2012. Established in 2018.") is None,
        "conflicting founding years stay off file",
    )
    check(
        parse_official_founded_year(
            "In 2023, Align established programs with non-profit organizations.",
            "Align Technology",
        ) is None,
        "established a program is not founding",
    )
    check(
        parse_official_founded_year(
            "Wipro’s US-based Black Alliance was established in 2020.",
            "Wipro",
        ) is None,
        "an employee alliance is not founding",
    )
    check(
        parse_official_founded_year(
            "Established in 2015, zBeat is Zalando’s online survey.",
            "Zalando",
        ) is None,
        "a survey is not founding",
    )
    check(
        parse_official_founded_year(
            "After selling the company in 2006, Huffman co-founded the travel company Hipmunk.",
            "Reddit",
        ) is None,
        "co-founded another company is not Reddit’s year",
    )
    check(
        parse_official_founded_year(
            "New York, Newfoundland, and London Telegraph Co., founded in 1854 by Cyrus West Field.",
            "Citigroup",
        ) is None,
        "another firm on a heritage page is not this company",
    )
    check(
        parse_official_founded_year(
            "1997 CBS Corporation is established, uniting CBS and Westinghouse.",
            "Paramount Skydance Corporation",
        ) is None,
        "CBS on a history timeline is not Paramount",
    )
    check(
        parse_official_founded_year(
            "the new Mahindra University, a multi-disciplinary campus established in 2020.",
            "Tech Mahindra",
        ) is None,
        "a university campus is not the company",
    )
    check(
        parse_official_founded_year(
            "Yonsei Cancer Center (South Korea) Established in 1969, Yonsei Cancer Center takes a leading role.",
            "RaySearch Laboratories",
        ) is None,
        "a clinical partner is not this company",
    )
    check(
        parse_official_founded_year(
            "We are part of the Mahindra Group, founded in 1945, one of the largest groups.",
            "Tech Mahindra",
        ) is None,
        "the parent group’s year is not this company’s year",
    )
    check(
        parse_official_founded_year(
            "Tech Mahindra is part of the Mahindra Group, founded in 1945, one of the largest groups.",
            "Tech Mahindra",
        ) is None,
        "is part of the parent group is not this company’s year",
    )


def test_apply_rejects_wiki_and_keeps_existing() -> None:
    row = {
        "name": "Example",
        "slug": "example",
        "domain": "example.com",
        "found": True,
        "disclosure": {"score": 40, "tier": "on-file", "factors": {"portal": 20}},
    }
    check(
        not apply_year_to_row(row, 2014, "https://en.wikipedia.org/wiki/Example"),
        "Wikipedia source is not filed",
    )
    check(not row.get("founded_year"), "year stays off file without an official source")
    check(apply_year_to_row(row, 2014, "https://example.com/about"), "official about is filed")
    check(row["founded_year"] == 2014, "year landed")
    check(row["founded_source"] == "https://example.com/about", "source is the official page")
    check(row["disclosure"]["factors"].get("longevity") == 6, f"longevity factor: {row['disclosure']}")
    held = dict(row)
    check(not apply_year_to_row(row, 2010, "https://example.com/company"), "existing year is not overwritten")
    check(row["founded_year"] == held["founded_year"], "first official year stays")


def main() -> int:
    test_prefix_is_not_a_match()
    test_official_site_only()
    test_parse_founded_sentence()
    test_apply_rejects_wiki_and_keeps_existing()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
