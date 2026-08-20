#!/usr/bin/env python3
"""Classify first-party status pages. Marketing, tweets, and portal walls stay off file."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from enrich import (
    apply_status_to_row,
    classify_as_status,
    clear_status_from_row,
    extract_status_candidates,
    is_filed_status_valid,
    is_first_party_url,
    is_followable_status_href,
    is_statuspage_marketing_url,
    status_host_matches_company,
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
GITHUB = {"slug": "github", "name": "GitHub", "domain": "github.com", "aliases": []}
BRIGHTWHEEL = {"slug": "brightwheel", "name": "Brightwheel", "domain": "brightwheel.com", "aliases": []}
ACME = {"slug": "acme", "name": "Acme", "domain": "acme.com", "aliases": []}
CLOUDFLARE = {"slug": "cloudflare", "name": "Cloudflare", "domain": "cloudflare.com", "aliases": []}
ATTENTIVE = {"slug": "attentive", "name": "Attentive", "domain": "attentive.com", "aliases": []}


class StatusClassifyTest(unittest.TestCase):
    def test_first_party_status_subdomain(self):
        url = "https://status.stripe.com"
        self.assertTrue(classify_as_status(url, rec(
            url,
            title="Stripe Status",
            text="All systems operational. Subscribe to updates. Past incidents.",
        ), STRIPE))
        self.assertTrue(status_host_matches_company(url, STRIPE))

    def test_first_party_status_path(self):
        url = "https://github.com/status"
        self.assertTrue(classify_as_status(url, rec(
            url,
            title="GitHub Status",
            text="All systems operational. Current status of GitHub services.",
        ), GITHUB))

    def test_branded_statuspage_subdomain(self):
        url = "https://brightwheel.statuspage.io/"
        self.assertTrue(classify_as_status(url, rec(
            url,
            title="Brightwheel Status",
            text="All systems operational. Past incidents.",
        ), BRIGHTWHEEL))
        self.assertTrue(is_followable_status_href(url, BRIGHTWHEEL))

    def test_branded_companystatus_host(self):
        url = "https://www.cloudflarestatus.com"
        self.assertTrue(classify_as_status(url, rec(
            url,
            title="Cloudflare Status",
            text="All systems operational. Subscribe to updates.",
        ), CLOUDFLARE))

    def test_statuspage_marketing_is_not_a_status_page(self):
        url = "https://www.statuspage.io/"
        self.assertTrue(is_statuspage_marketing_url(url))
        self.assertFalse(classify_as_status(url, rec(
            url,
            title="Statuspage · Atlassian",
            text="Create a status page. Statuspage pricing. Get started with Statuspage.",
        ), ACME))
        url2 = "https://www.atlassian.com/software/statuspage"
        self.assertTrue(is_statuspage_marketing_url(url2))
        self.assertFalse(classify_as_status(url2, rec(
            url2,
            title="Atlassian Statuspage",
            text="The best status page software for communicating incidents.",
        ), ACME))

    def test_tweet_is_not_a_status_page(self):
        url = "https://twitter.com/acme/status/12345"
        self.assertFalse(classify_as_status(url, rec(
            url,
            title="Acme on X",
            text="We are investigating an incident. Status update.",
        ), ACME))
        self.assertFalse(is_followable_status_href(url, ACME))

    def test_news_article_is_not_a_status_page(self):
        url = "https://techcrunch.com/2026/01/01/acme-outage/"
        self.assertFalse(classify_as_status(url, rec(
            url,
            title="Acme outage hits status page",
            text="Acme published incidents on its status page after an outage.",
        ), ACME))

    def test_login_wall_is_not_filed(self):
        url = "https://status.acme.com"
        self.assertFalse(classify_as_status(url, rec(
            url,
            title="Sign in to continue",
            text="Please log in to view this document.",
        ), ACME))

    def test_itemuid_portal_doc_is_not_a_status_page(self):
        url = "https://trust.acme.com/?itemUid=a26c76c4-6568-4a97-a75b-5cc628e0a407"
        self.assertFalse(classify_as_status(url, rec(
            url,
            title="Status Monitoring",
            text="Request access. Status page document.",
        ), ACME))
        self.assertFalse(is_filed_status_valid(url, ACME))

    def test_security_portal_is_not_a_status_page(self):
        url = "https://security.attentive.com"
        self.assertFalse(classify_as_status(url, rec(
            url,
            title="Attentive Trust Center",
            text="SOC 2 Type II. Request access to our trust center.",
        ), ATTENTIVE))
        self.assertFalse(is_filed_status_valid(url, ATTENTIVE))

    def test_other_company_statuspage_is_not_filed(self):
        url = "https://aws.statuspage.io/"
        self.assertFalse(classify_as_status(url, rec(
            url,
            title="Amazon Web Services Status",
            text="All systems operational. Past incidents.",
        ), ACME))

    def test_homepage_bounce_from_status_subdomain(self):
        url = "https://status.attentive.com"
        self.assertFalse(classify_as_status(url, rec(
            url,
            title="Attentive Trust Center",
            text="SOC 2. Request documents.",
            final="https://security.attentive.com",
        ), ATTENTIVE))

    def test_link_text_extracts_status(self):
        html = (
            '<a href="/privacy">Privacy</a>'
            '<a href="https://status.acme.com">Status page</a>'
            '<a href="https://twitter.com/acme/status/1">Status</a>'
            '<a href="https://www.statuspage.io/">Statuspage</a>'
        )
        got = extract_status_candidates(html, "https://trust.acme.com", ACME)
        self.assertIn("https://status.acme.com", got)
        self.assertNotIn("https://twitter.com/acme/status/1", got)
        self.assertNotIn("https://www.statuspage.io/", got)

    def test_apply_status_adds_six_and_leaves_other_factors(self):
        row = {
            "found": True,
            "links": {"privacy": "https://example.com/privacy"},
            "disclosure": {
                "score": 52,
                "tier": "on-file",
                "factors": {"page": 20, "marks": 10, "privacy": 6, "years": 16},
            },
        }
        self.assertTrue(apply_status_to_row(row, "https://status.example.com"))
        self.assertEqual(row["links"]["status"], "https://status.example.com")
        self.assertEqual(row["disclosure"]["factors"]["status"], 6)
        self.assertEqual(row["disclosure"]["factors"]["page"], 20)
        self.assertEqual(row["disclosure"]["score"], 58)
        self.assertEqual(row["disclosure"]["tier"], "on-file")
        self.assertFalse(apply_status_to_row(row, "https://status.example.com"))

    def test_clear_invalid_status_drops_six(self):
        row = {
            "found": True,
            "links": {"status": "https://trust.acme.com/?itemUid=abc", "privacy": "https://acme.com/privacy"},
            "disclosure": {
                "score": 46,
                "tier": "on-file",
                "factors": {"page": 20, "privacy": 6, "status": 6, "years": 14},
            },
        }
        self.assertTrue(clear_status_from_row(row))
        self.assertNotIn("status", row["links"])
        self.assertNotIn("status", row["disclosure"]["factors"])
        self.assertEqual(row["disclosure"]["score"], 40)

    def test_inactive_statuspage_is_not_filed(self):
        url = "https://apple.statuspage.io/inactive"
        self.assertFalse(classify_as_status(url, rec(
            url,
            title="Statuspage",
            text="This page is currently inactive. Create a status page.",
        ), {"slug": "apple", "name": "Apple", "domain": "apple.com", "aliases": []}))
        self.assertFalse(is_filed_status_valid(url, {"slug": "apple", "name": "Apple", "domain": "apple.com", "aliases": []}))

    def test_deleted_statuspage_is_not_filed(self):
        url = "https://beyondtrust.statuspage.io/page-deleted"
        self.assertFalse(is_filed_status_valid(url, {"slug": "beyondtrust", "name": "BeyondTrust", "domain": "beyondtrust.com", "aliases": []}))

    def test_status_login_wall_path_is_not_filed(self):
        url = "https://status.abridge.com/access/login"
        self.assertFalse(classify_as_status(url, rec(
            url,
            title="Abridge Status",
            text="Please log in to view this status page.",
        ), {"slug": "abridge", "name": "Abridge", "domain": "abridge.com", "aliases": []}))
        self.assertFalse(is_filed_status_valid(url, {"slug": "abridge", "name": "Abridge", "domain": "abridge.com", "aliases": []}))

    def test_nested_non_status_path_is_not_filed(self):
        url = "https://www.alliantenergy.com/ways-to-save/interruptible-program/status"
        self.assertFalse(classify_as_status(url, rec(
            url,
            title="Interruptible program status",
            text="Check the interruptible program status for your account.",
        ), {"slug": "alliant-energy", "name": "Alliant Energy", "domain": "alliantenergy.com", "aliases": []}))

    def test_generic_corporate_statuspage_is_not_filed(self):
        url = "https://corporate.statuspage.io"
        self.assertTrue(is_statuspage_marketing_url(url))
        self.assertFalse(classify_as_status(url, rec(
            url,
            title="Corporate Status",
            text="All systems operational. Subscribe to updates.",
        ), {"slug": "visa", "name": "Visa", "domain": "visa.com", "aliases": []}))

    def test_vanta_owns_vanta_dot_com(self):
        vanta = {"slug": "vanta", "name": "Vanta", "domain": "vanta.com", "aliases": []}
        self.assertTrue(is_first_party_url("https://status.vanta.com", vanta))
        self.assertTrue(classify_as_status(
            "https://status.vanta.com",
            rec("https://status.vanta.com", title="Vanta Status", text="All systems operational."),
            vanta,
        ))


if __name__ == "__main__":
    unittest.main()
