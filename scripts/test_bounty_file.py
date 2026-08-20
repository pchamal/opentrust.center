#!/usr/bin/env python3
"""Classify first-party VDP / branded platform program pages. News and login walls stay off file."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from enrich import (
    apply_bounty_to_row,
    bounty_platform_handle,
    classify_as_bounty,
    extract_bounty_candidates,
    is_bounty_platform_host,
)


def rec(url, *, title="", text="", status=200, ok=True, ctype="text/html", final=None):
    return {
        "ok": ok,
        "status": status,
        "title": title,
        "text": text,
        "ctype": ctype,
        "final_url": final or url,
    }


STRIPE = {"slug": "stripe", "name": "Stripe", "domain": "stripe.com", "aliases": []}
BOX = {"slug": "box", "name": "Box", "domain": "box.com", "aliases": []}
DATABRICKS = {
    "slug": "databricks",
    "name": "Databricks",
    "domain": "databricks.com",
    "aliases": [],
}


class BountyClassifyTest(unittest.TestCase):
    def test_first_party_security_vulnerability(self):
        url = "https://example.com/security/vulnerability"
        self.assertTrue(classify_as_bounty(url, rec(
            url,
            title="Vulnerability disclosure",
            text="Report a vulnerability to our security team. Out of scope items are listed below.",
        )))

    def test_first_party_responsible_disclosure(self):
        url = "https://vercel.com/security/responsible-disclosure"
        self.assertTrue(classify_as_bounty(url, rec(
            url,
            title="Responsible disclosure",
            text="We invite security researchers to report a vulnerability through this page.",
        )))

    def test_hackerone_branded_program(self):
        url = "https://hackerone.com/stripe"
        self.assertEqual(bounty_platform_handle(url), "stripe")
        self.assertTrue(classify_as_bounty(url, rec(
            url,
            title="Stripe | HackerOne",
            text="Stripe bug bounty program. Submit a report. Out of scope: social engineering.",
        ), STRIPE))

    def test_hackerone_marketing_is_not_a_program(self):
        url = "https://hackerone.com"
        self.assertIsNone(bounty_platform_handle(url))
        self.assertFalse(classify_as_bounty(url, rec(
            url,
            title="HackerOne | Bug Bounty Platform",
            text="Hacker-powered security. Find your next bounty.",
        ), STRIPE))

    def test_hackerone_directory_is_not_a_program(self):
        url = "https://hackerone.com/directory"
        self.assertIsNone(bounty_platform_handle(url))
        self.assertFalse(classify_as_bounty(url, rec(
            url,
            title="Directory | HackerOne",
            text="Browse bug bounty programs.",
        ), STRIPE))

    def test_hackerone_wrong_company_is_not_filed(self):
        url = "https://hackerone.com/shopify"
        self.assertTrue(is_bounty_platform_host("hackerone.com"))
        self.assertFalse(classify_as_bounty(url, rec(
            url,
            title="Shopify | HackerOne",
            text="Shopify bug bounty program. Submit a report.",
        ), STRIPE))

    def test_login_wall_is_not_filed(self):
        url = "https://example.com/security/responsible-disclosure"
        self.assertFalse(classify_as_bounty(url, rec(
            url,
            title="Sign in to continue",
            text="Please log in to view this document.",
        )))

    def test_private_hackerone_is_not_filed(self):
        url = "https://hackerone.com/databricks"
        self.assertFalse(classify_as_bounty(url, rec(
            url,
            title="Databricks | HackerOne",
            text="This program is private. Sign in to view this program.",
        ), DATABRICKS))

    def test_news_article_is_not_a_program(self):
        url = "https://www.grammarly.com/blog/company/hackerone-bug-bounty-security/"
        self.assertFalse(classify_as_bounty(url, rec(
            url,
            title="Grammarly launches a bug bounty",
            text="Today we announce our HackerOne bug bounty program for security researchers.",
        )))

    def test_generic_security_page_is_not_a_program(self):
        url = "https://navan.com/security"
        self.assertFalse(classify_as_bounty(url, rec(
            url,
            title="Security",
            text="Navan takes security seriously. We encrypt data and run audits.",
        )))

    def test_itemuid_portal_is_not_a_program(self):
        url = "https://trust.example.com/?itemUid=64c9680b-ef79-4c92-baa0-13b541954bef"
        self.assertFalse(classify_as_bounty(url, rec(
            url,
            title="Trust Center",
            text="Request access to documents.",
        )))

    def test_short_name_needs_title_or_handle(self):
        url = "https://hackerone.com/box"
        self.assertTrue(classify_as_bounty(url, rec(
            url,
            title="Box | HackerOne",
            text="Box bug bounty program. Submit a report.",
        ), BOX))
        self.assertFalse(classify_as_bounty("https://hackerone.com/acme", rec(
            "https://hackerone.com/acme",
            title="Acme Storage | HackerOne",
            text="A program that mentions Box as a customer. Submit a report.",
        ), BOX))

    def test_link_text_extracts_program(self):
        html = (
            '<a href="/legal/terms">Master terms</a>'
            '<a href="/security/responsible-disclosure">Responsible disclosure</a>'
            '<a href="https://hackerone.com/directory">HackerOne</a>'
            '<a href="https://hackerone.com/stripe">Report a vulnerability</a>'
        )
        got = extract_bounty_candidates(html, "https://stripe.com/trust")
        self.assertIn("https://stripe.com/security/responsible-disclosure", got)
        self.assertIn("https://hackerone.com/stripe", got)
        self.assertNotIn("https://hackerone.com/directory", got)
        self.assertNotIn("https://stripe.com/legal/terms", got)

    def test_apply_bounty_adds_six_without_security_txt(self):
        row = {
            "found": True,
            "links": {"privacy": "https://example.com/privacy"},
            "disclosure": {
                "score": 52,
                "tier": "on-file",
                "factors": {"page": 20, "marks": 10, "privacy": 6, "years": 16},
            },
        }
        self.assertTrue(apply_bounty_to_row(row, "https://example.com/responsible-disclosure"))
        self.assertEqual(row["links"]["bug_bounty"], "https://example.com/responsible-disclosure")
        self.assertEqual(row["disclosure"]["factors"]["disclosure"], 6)
        self.assertEqual(row["disclosure"]["factors"]["page"], 20)
        self.assertEqual(row["disclosure"]["score"], 58)
        self.assertEqual(row["disclosure"]["tier"], "on-file")
        self.assertFalse(apply_bounty_to_row(row, "https://example.com/other"))

    def test_apply_bounty_does_not_double_count_security_txt(self):
        row = {
            "found": True,
            "links": {"security_txt": "https://example.com/.well-known/security.txt"},
            "disclosure": {
                "score": 62,
                "tier": "on-file",
                "factors": {"page": 20, "disclosure": 6, "privacy": 6},
            },
        }
        self.assertTrue(apply_bounty_to_row(row, "https://hackerone.com/example"))
        self.assertEqual(row["links"]["bug_bounty"], "https://hackerone.com/example")
        self.assertEqual(row["disclosure"]["score"], 62)
        self.assertEqual(row["disclosure"]["factors"]["disclosure"], 6)


if __name__ == "__main__":
    unittest.main()
