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
from file_company_years import jsonld_later_than_known  # noqa: E402


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
    check(
        parse_official_founded_year(
            'Urban Airship was founded in 2009. {"@type":"Organization","foundingDate":"2019-06-01"}',
            "Airship",
        ) == 2009,
        "earlier founded sentence beats a later JSON-LD foundingDate",
    )
    check(
        parse_official_founded_year(
            'The company rebranded in 2019. {"@type":"Organization","foundingDate":"2019-06-01"}',
            "Airship",
        ) is None,
        "JSON-LD foundingDate next to a rebrand is not founding",
    )
    check(
        jsonld_later_than_known({"slug": "airship", "name": "Airship"}, 2019)
        == "jsonld-later-than-known-founding",
        "Airship 2019 is later than the 2009 Urban Airship founding",
    )
    check(
        jsonld_later_than_known({"slug": "huntress", "name": "Huntress"}, 2015) is None,
        "Huntress 2015 is not a known-later JSON-LD",
    )
    check(
        parse_official_founded_year(
            "Temasek operates in markets around the world. Established in 1974, "
            "the company is driven by its core values of integrity, excellence, "
            "and respect, investing with a focus on sustainability.",
            "Orca Security",
        ) is None,
        "Temasek 1974 on an Orca page is not Orca’s year",
    )
    check(
        parse_official_founded_year(
            "Our Story 2005 Fenrir Established 2008 Collaborative Development "
            "2014 First International Expansion",
            "Fenrir Inc",
        ) is None,
        "Fenrir timeline 2008 is the next beat, not founding",
    )
    check(
        parse_official_founded_year(
            "Learn more Thriv Founded in 2018, Thriv is a Helsinki-based tech "
            "talent agency. We connect ambitious freelance software developers.",
            "Futurice",
        ) is None,
        "Thriv 2018 on a Futurice family page is not Futurice’s year",
    )
    check(
        parse_official_founded_year(
            "01.AI was founded in Beijing in May 2023 under the leadership of "
            "Dr. Kai-Fu Lee and became a unicorn within six months.",
            "01.AI",
        ) == 2023,
        "founded in city in month YYYY is founding",
    )
    check(
        parse_official_founded_year(
            "Since 1998, we've been building software and systems for safety.",
            "Critical Software",
        ) is None,
        "since YYYY building copy is not a founded sentence",
    )
    check(
        parse_official_founded_year(
            "A defining moment for Cencora Cencora was established in 2023, "
            "as a new name for the AmerisourceBergen Corporation.",
            "Cencora",
        ) is None,
        "Cencora 2023 rename is not founding",
    )
    check(
        parse_official_founded_year(
            "2001 Keyhole founded 2004 Acquired by Google 2005 Google Maps is "
            "born 2011 Niantic Labs incubated at Google 2025 Niantic Spatial "
            "formed",
            "Niantic Spatial",
        ) is None,
        "Niantic Spatial timeline 2004 is Keyhole’s Google acquisition, not founding",
    )
    check(
        parse_official_founded_year(
            "Factsheet Developer: Isotope 244 Based in Tampa, FL "
            "Founding date: July 1st, 1999 Website: isotope244.com/",
            "Isotope 244",
        ) == 1999,
        "founding date colon month day YYYY is founding",
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


def test_report_years_landed() -> None:
    """This increment filed four first-party years. Held false hits stay open."""
    import json
    public = json.loads((ROOT / "site" / "data.json").read_text())
    enr = json.loads((ROOT / "site" / "data" / "enriched.json").read_text())
    report = json.loads((ROOT / "data" / "render" / "company-years.json").read_text())
    by_pub = {c["slug"]: c for c in public["companies"]}
    by_enr = {c["slug"]: c for c in enr["companies"]}
    filed = report.get("years_filed") or []
    batch = report.get("batch") or []
    stayed = report.get("stayed_open") or []
    filed_by = {r["slug"]: r for r in filed}
    check(len(filed) == 4, f"this increment filed 4, got {len(filed)}")
    check(len(stayed) == 36, f"36 stayed open, got {len(stayed)}")
    check(len(batch) == 40, f"batch is 40, got {len(batch)}")
    expect = {
        "filament-games": (2005, "https://www.filamentgames.com/"),
        "hitcents": (1999, "https://hitcents.com/"),
        "isotope-244": (1999, "https://isotope244.com/press"),
        "mastiff": (2002, "https://mastiff-games.com/about"),
    }
    check(set(filed_by) == set(expect), f"filed slugs, got {sorted(filed_by)}")
    for slug, (year, source) in expect.items():
        rec, pub, row = filed_by[slug], by_pub[slug], by_enr[slug]
        check(rec.get("year") == year, f"{slug} report year")
        check(rec.get("url") == source, f"{slug} report source")
        check(pub.get("founded_year") == year, f"{slug} public year")
        check(pub.get("founded_source") == source, f"{slug} public source")
        check(row.get("founded_year") == year, f"{slug} enriched year")
        check((pub.get("file") or {}).get("years") in (True, 20), f"{slug} file.years")
        html = (ROOT / "site" / "c" / f"{slug}.html").read_text(encoding="utf-8")
        check(f"founded · {year}" in html, f"{slug} dossier year")
        check(source in html, f"{slug} dossier source")
        check(
            'target="_blank" rel="noopener noreferrer"' in html,
            f"{slug} outbound source keeps noopener",
        )
    check("faculty" not in batch, "Faculty is not re-walked")
    check("airship" not in batch, "Airship is not re-walked")
    check("appian" not in batch, "PR 107 fills are not re-walked")
    check("orca-security" not in batch, "PR 111 Orca is not re-walked")
    check("craigslist" not in batch, "PR 115 leftovers are not re-walked")
    check("innofactor" not in batch, "PR 117 fills are not re-walked")
    check("01-ai" not in batch, "PR 124 fills are not re-walked")
    check("crowdin" not in batch, "PR 124 fills are not re-walked")
    check("grafana-labs" not in batch, "earlier trust-URL years files are not re-walked")
    check("checkr" not in batch, "earlier trust-URL years files are not re-walked")
    check("american-water-works" not in batch, "PR 129 fills are not re-walked")
    check("blackrock" not in batch, "PR 129 fills are not re-walked")
    check("cencora" not in batch, "PR 135 leftovers are not re-walked")
    check("danaher-corporation" not in batch, "PR 135 fills are not re-walked")
    check("first-solar" not in batch, "PR 140 fills are not re-walked")
    check("klarna" not in batch, "PR 140 fills are not re-walked")
    check("mitek-systems" not in batch, "PR 143 leftovers are not re-walked")
    check("sandisk" not in batch, "PR 143 leftovers are not re-walked")
    check("sanmina" not in batch, "PR 146 leftovers are not re-walked")
    check("unitedhealth-group" not in batch, "PR 146 leftovers are not re-walked")
    check("agility-robotics" not in batch, "PR 152 leftovers are not re-walked")
    check("lloyd-s-list-intelligence" not in batch, "PR 152 leftovers are not re-walked")
    check("alphasights" not in batch, "PR 152 fills are not re-walked")
    check(
        "gamecaster" in batch and "night-light-interactive" in batch,
        "latest expand silent/unread rows are walked",
    )
    from file_company_years import PRIOR_ATTEMPTED, select_batch
    for slug in batch:
        check(slug in PRIOR_ATTEMPTED, f"{slug} is on the next-increment skip list")
    leftover = select_batch(list(public["companies"]), by_enr)
    leftover_slugs = {r["slug"] for r in leftover}
    check(not leftover_slugs & set(batch), f"this batch is not retried, got {leftover_slugs & set(batch)}")
    orca = by_pub["orca-security"]
    check(not orca.get("founded_year"), "Orca year stays open")
    check(not orca.get("founded_source"), "Orca source stays off file")
    check((orca.get("file") or {}).get("years") in (0, None, False), "Orca years rule open")
    orca_html = (ROOT / "site" / "c" / "orca-security.html").read_text(encoding="utf-8")
    check("founded · <span class=\"absent\">not on file</span>" in orca_html, "Orca dossier years open")
    check("founded · 1974" not in orca_html, "Orca 1974 is not printed")
    airship = by_pub["airship"]
    check(not airship.get("founded_year"), "Airship year stays open")
    check(not airship.get("founded_source"), "Airship source stays off file")
    check((airship.get("file") or {}).get("years") in (0, None, False), "Airship years rule open")
    air_html = (ROOT / "site" / "c" / "airship.html").read_text(encoding="utf-8")
    check("founded · <span class=\"absent\">not on file</span>" in air_html, "Airship dossier years open")
    check("founded · 2019" not in air_html, "Airship 2019 is not printed")
    faculty = by_pub["faculty"]
    check(faculty.get("founded_year") == 2014, "Faculty year 2014 stays")
    check(faculty.get("founded_source") == "https://faculty.ai/en-gb", "Faculty source stays")
    prior = {
        "appian": 1999,
        "esentire": 2001,
        "xylem-inc": 2011,
        "huntress": 2015,
        "salt-security": 2016,
        "bluevoyant": 2017,
        "crusoe": 2018,
        "dubber": 2011,
        "innofactor": 2000,
        "preferred-networks": 2014,
        "works-applications": 1996,
        "01-ai": 2023,
        "crowdin": 2008,
        "cyberlink": 1996,
        "graphisoft": 1982,
        "scoro": 2013,
        "tmaxsoft": 1997,
        "american-water-works": 1886,
        "blackrock": 1988,
        "brown-forman": 1870,
        "consolidated-edison": 1823,
        "danaher-corporation": 1984,
        "echostar": 1980,
        "first-solar": 1999,
        "freee-k-k": 2012,
        "genius-sports": 2001,
        "klarna": 2005,
        "sea-limited": 2009,
        "stitch-fix": 2011,
        "synaptics": 1986,
        "tencent": 1998,
        "alphasights": 2008,
        "black-cube": 2011,
        "lighton": 2016,
        "owkin": 2016,
        "raic-labs": 2019,
        "filament-games": 2005,
        "hitcents": 1999,
        "isotope-244": 1999,
        "mastiff": 2002,
    }
    for slug, year in prior.items():
        pub, row = by_pub[slug], by_enr[slug]
        check(pub.get("founded_year") == year, f"{slug} public year stays")
        check(row.get("founded_year") == year, f"{slug} enriched year stays")
        check((pub.get("file") or {}).get("years") in (True, 20), f"{slug} file.years stays")
        html = (ROOT / "site" / "c" / f"{slug}.html").read_text(encoding="utf-8")
        check(f"founded · {year}" in html, f"{slug} dossier year stays")
    watch = by_pub["watchguard"]
    check(not watch.get("founded_year"), "WatchGuard year stays open")
    check((watch.get("file") or {}).get("marks") == 20, "WatchGuard marks stay")
    check((watch.get("file") or {}).get("years") in (0, None, False), "WatchGuard years rule open")
    held = {
        "fenrir-inc": "2008",
        "futurice": "2018",
        "critical-software": "1998",
        "zeroturnaround": "2007",
        "orthograph": "2004",
        "a-o-smith": "1904",
        "cencora": "2023",
        "niantic-spatial": "2004",
    }
    aosmith_html = (ROOT / "site" / "c" / "a-o-smith.html").read_text(encoding="utf-8")
    check("founded · 1874" not in aosmith_html, "A. O. Smith 1874 is not printed")
    for slug, year in held.items():
        pub = by_pub[slug]
        check(not pub.get("founded_year"), f"{slug} year stays open")
        check((pub.get("file") or {}).get("years") in (0, None, False), f"{slug} years rule open")
        html = (ROOT / "site" / "c" / f"{slug}.html").read_text(encoding="utf-8")
        check(
            "founded · <span class=\"absent\">not on file</span>" in html,
            f"{slug} dossier years open",
        )
        check(f"founded · {year}" not in html, f"{slug} {year} is not printed")
    for row in stayed:
        slug = row["slug"]
        if slug in expect:
            raise SystemExit(f"fail: {slug} is filed and stayed open")
        pub = by_pub[slug]
        check(not pub.get("founded_year"), f"{slug} year stays open")
        check((pub.get("file") or {}).get("years") in (0, None, False), f"{slug} years rule open")


def test_teleport_year_landed() -> None:
    """Prior increment filed Teleport 2015 from first-party foundingDate."""
    import json
    public = json.loads((ROOT / "site" / "data.json").read_text())
    enr = json.loads((ROOT / "site" / "data" / "enriched.json").read_text())
    by_pub = {c["slug"]: c for c in public["companies"]}
    by_enr = {c["slug"]: c for c in enr["companies"]}
    pub, row = by_pub["teleport"], by_enr["teleport"]
    check(pub.get("founded_year") == 2015, "Teleport public year 2015")
    check(row.get("founded_year") == 2015, "Teleport enriched year 2015")
    check(pub.get("founded_source") == "https://goteleport.com/about", "Teleport year source is /about")
    check((pub.get("file") or {}).get("years") in (True, 20), "Teleport years rule prints")
    html = (ROOT / "site" / "c" / "teleport.html").read_text(encoding="utf-8")
    check("founded · 2015" in html, "Teleport dossier prints 2015")
    check("https://goteleport.com/about" in html, "Teleport dossier cites about source")
    check("ISO 27701" not in html, "Teleport SafeBase JSON-LD ISO 27701 stays open")
    check("PCI DSS" not in html, "Teleport SafeBase JSON-LD PCI DSS stays open")


def test_ketch_inkeep_years_landed() -> None:
    """This increment filed Ketch 2020 and Inkeep 2023 from first-party foundingDate."""
    import json
    public = json.loads((ROOT / "site" / "data.json").read_text())
    enr = json.loads((ROOT / "site" / "data" / "enriched.json").read_text())
    by_pub = {c["slug"]: c for c in public["companies"]}
    by_enr = {c["slug"]: c for c in enr["companies"]}
    ketch_pub, ketch_row = by_pub["ketch"], by_enr["ketch"]
    check(ketch_pub.get("founded_year") == 2020, "Ketch public year 2020")
    check(ketch_row.get("founded_year") == 2020, "Ketch enriched year 2020")
    check(ketch_pub.get("founded_source") == "https://www.ketch.com/about", "Ketch year source is /about")
    check((ketch_pub.get("file") or {}).get("years") in (True, 20), "Ketch years rule prints")
    check(ketch_pub.get("found") is False, "Ketch Official page stays open")
    ketch_html = (ROOT / "site" / "c" / "ketch.html").read_text(encoding="utf-8")
    check("founded · 2020" in ketch_html, "Ketch dossier prints 2020")
    check("https://www.ketch.com/about" in ketch_html, "Ketch dossier cites about source")
    inkeep_pub, inkeep_row = by_pub["inkeep"], by_enr["inkeep"]
    check(inkeep_pub.get("founded_year") == 2023, "Inkeep public year 2023")
    check(inkeep_row.get("founded_year") == 2023, "Inkeep enriched year 2023")
    check(inkeep_pub.get("founded_source") == "https://inkeep.com/about", "Inkeep year source is /about")
    check((inkeep_pub.get("file") or {}).get("years") in (True, 20), "Inkeep years rule prints")
    inkeep_html = (ROOT / "site" / "c" / "inkeep.html").read_text(encoding="utf-8")
    check("founded · 2023" in inkeep_html, "Inkeep dossier prints 2023")
    check("https://inkeep.com/about" in inkeep_html, "Inkeep dossier cites about source")
    check("policies/dpa.pdf" not in inkeep_html, "Inkeep DPA PDF stays unread")


def main() -> int:
    test_prefix_is_not_a_match()
    test_official_site_only()
    test_parse_founded_sentence()
    test_apply_rejects_wiki_and_keeps_existing()
    test_teleport_year_landed()
    test_ketch_inkeep_years_landed()
    test_report_years_landed()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
