#!/usr/bin/env python3
"""Classify first-party privacy policies. DPA, cookies, CMP, and news stay off file."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from enrich import (
    apply_privacy_to_row,
    classify_as_privacy,
    extract_privacy_candidates,
    is_cmp_vendor_host,
    is_first_party_url,
    is_portal_vendor_host,
    path_is_cookie_only,
    path_is_dpa,
    path_is_news,
    path_is_privacy_center_marketing,
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


POLICY = (
    "This Privacy Policy describes how we collect personal information "
    "and how we use your data. Contact the data protection officer."
)


class PrivacyClassifyTest(unittest.TestCase):
    def test_strong_path_with_body(self):
        url = "https://example.com/legal/privacy-policy"
        self.assertTrue(classify_as_privacy(url, rec(
            url,
            title="Legal",
            text=POLICY,
        )))

    def test_exact_privacy_needs_title_or_body(self):
        url = "https://example.com/privacy"
        self.assertTrue(classify_as_privacy(url, rec(
            url,
            title="Privacy Policy",
            text=POLICY,
        )))
        self.assertFalse(classify_as_privacy(url, rec(
            url,
            title="Home",
            text="A GitHub user profile with a long bio about hiking and photos. " * 20,
        )))

    def test_pdf_on_privacy_path(self):
        url = "https://example.com/legal/privacy-notice.pdf"
        self.assertTrue(classify_as_privacy(url, rec(
            url, title="", text="%PDF-1.4", ctype="application/pdf",
        )))

    def test_dpa_is_not_a_privacy_policy(self):
        url = "https://example.com/legal/data-processing-addendum"
        self.assertTrue(path_is_dpa("/legal/data-processing-addendum"))
        self.assertFalse(classify_as_privacy(url, rec(
            url,
            title="Data Processing Addendum",
            text="This DPA sets processor terms and names sub-processors. " + POLICY,
        )))

    def test_cookie_banner_is_not_a_privacy_policy(self):
        url = "https://example.com/cookies"
        self.assertTrue(path_is_cookie_only("/cookies"))
        self.assertFalse(classify_as_privacy(url, rec(
            url,
            title="Cookie Policy",
            text="This cookie policy explains personal information on our site.",
        )))

    def test_privacy_choices_is_not_the_policy(self):
        url = "https://example.com/your-privacy-choices"
        self.assertTrue(path_is_cookie_only("/your-privacy-choices"))
        self.assertFalse(classify_as_privacy(url, rec(
            url,
            title="Your Privacy Choices",
            text="Do not sell my personal information. Manage cookies.",
        )))

    def test_privacy_center_marketing_is_not_the_policy(self):
        url = "https://example.com/privacy-center"
        self.assertTrue(path_is_privacy_center_marketing("/privacy-center"))
        self.assertFalse(classify_as_privacy(url, rec(
            url,
            title="Privacy Center",
            text="Explore our privacy program and request access to reports.",
        )))

    def test_privacy_center_legal_can_be_the_policy(self):
        url = "https://example.com/privacy-center/legal"
        self.assertFalse(path_is_privacy_center_marketing("/privacy-center/legal"))
        self.assertTrue(classify_as_privacy(url, rec(
            url,
            title="Privacy Policy",
            text=POLICY,
        )))

    def test_news_article_is_not_the_policy(self):
        url = "https://example.com/blog/new-privacy-policy"
        self.assertTrue(path_is_news("/blog/new-privacy-policy"))
        self.assertFalse(classify_as_privacy(url, rec(
            url,
            title="We updated our Privacy Policy",
            text=POLICY,
        )))

    def test_subprocessors_under_privacy_is_not_the_policy(self):
        url = "https://example.com/privacy/subprocessors"
        self.assertFalse(classify_as_privacy(url, rec(
            url,
            title="Subprocessors",
            text="These sub-processors handle personal information. " + POLICY,
        )))

    def test_cmp_vendor_host_rejected(self):
        self.assertTrue(is_cmp_vendor_host("https://app.onetrust.com/privacy"))
        url = "https://app.onetrust.com/privacy"
        self.assertFalse(classify_as_privacy(url, rec(
            url,
            title="Privacy Policy",
            text=POLICY,
        )))

    def test_login_wall_is_not_filed(self):
        url = "https://example.com/privacy"
        self.assertFalse(classify_as_privacy(url, rec(
            url,
            title="Sign in to continue",
            text="Please log in to view this document.",
        )))

    def test_homepage_bounce_is_not_filed(self):
        url = "https://example.com/privacy"
        self.assertFalse(classify_as_privacy(url, rec(
            url,
            title="Example",
            text=POLICY,
            final="https://example.com/",
        )))

    def test_portal_vendor_host_rejected_for_other_companies(self):
        plaid = {"slug": "plaid", "domain": "plaid.com", "aliases": []}
        self.assertTrue(is_portal_vendor_host("https://plaid.securitypal.com/legal", plaid))
        self.assertFalse(is_first_party_url("https://plaid.securitypal.com/legal", plaid))
        notion = {"slug": "notion", "domain": "notion.so", "aliases": ["notion.com"]}
        self.assertTrue(is_first_party_url("https://www.notion.so/privacy", notion))
        self.assertFalse(is_first_party_url("https://cookiebot.com/privacy", notion))

    def test_link_text_extracts_privacy_policy(self):
        html = (
            '<a href="/legal/terms">Master terms</a>'
            '<a href="/legal/privacy-notice">Privacy Policy</a>'
            '<a href="/cookies">Cookie Policy</a>'
            '<a href="/blog/privacy-policy">We updated our Privacy Policy</a>'
        )
        got = extract_privacy_candidates(html, "https://example.com/trust")
        self.assertIn("https://example.com/legal/privacy-notice", got)
        self.assertNotIn("https://example.com/legal/terms", got)
        self.assertNotIn("https://example.com/cookies", got)
        self.assertNotIn("https://example.com/blog/privacy-policy", got)

    def test_apply_privacy_adds_six_and_leaves_other_factors(self):
        row = {
            "found": True,
            "links": {"dpa": "https://example.com/legal/dpa"},
            "disclosure": {
                "score": 54,
                "tier": "on-file",
                "factors": {"page": 20, "marks": 10, "dpa": 8, "years": 16},
            },
        }
        self.assertTrue(apply_privacy_to_row(row, "https://example.com/legal/privacy"))
        self.assertEqual(row["links"]["privacy"], "https://example.com/legal/privacy")
        self.assertEqual(row["links"]["dpa"], "https://example.com/legal/dpa")
        self.assertEqual(row["disclosure"]["factors"]["privacy"], 6)
        self.assertEqual(row["disclosure"]["factors"]["dpa"], 8)
        self.assertEqual(row["disclosure"]["factors"]["page"], 20)
        self.assertEqual(row["disclosure"]["score"], 60)
        self.assertEqual(row["disclosure"]["tier"], "on-file")
        self.assertFalse(apply_privacy_to_row(row, "https://example.com/other"))


if __name__ == "__main__":
    unittest.main()
