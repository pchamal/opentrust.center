#!/usr/bin/env python3
"""Classify first-party DPA pages. Privacy, cookies, and portal hosts stay off file."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from enrich import (
    apply_dpa_to_row,
    apply_subprocessors_to_row,
    classify_as_dpa,
    extract_dpa_candidates,
    extract_subprocessor_candidates,
    is_first_party_url,
    is_portal_vendor_host,
    path_is_privacy_or_cookie_only,
    path_is_product_page,
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


class DpaClassifyTest(unittest.TestCase):
    def test_strong_path_with_body(self):
        url = "https://example.com/legal/data-processing-addendum"
        self.assertTrue(classify_as_dpa(url, rec(
            url,
            title="Legal",
            text="This Data Processing Addendum (DPA) is entered into under Article 28.",
        )))

    def test_short_dpa_path_needs_body(self):
        url = "https://example.com/legal/dpa"
        self.assertTrue(classify_as_dpa(url, rec(
            url,
            title="DPA",
            text="This DPA sets processor terms and names sub-processors.",
        )))
        self.assertFalse(classify_as_dpa(url, rec(
            url,
            title="dpa",
            text="A GitHub user profile with a long bio about hiking and photos. " * 20,
        )))

    def test_pdf_on_dpa_path(self):
        url = "https://example.com/legal/dpa-2024.pdf"
        self.assertTrue(classify_as_dpa(url, rec(url, title="", text="%PDF-1.4", ctype="application/pdf")))

    def test_privacy_policy_is_not_a_dpa(self):
        url = "https://example.com/privacy"
        self.assertTrue(path_is_privacy_or_cookie_only("/privacy"))
        self.assertFalse(classify_as_dpa(url, rec(
            url,
            title="Privacy Policy",
            text="We process personal data. Contact us about data processing and sub-processors.",
        )))

    def test_cookie_banner_is_not_a_dpa(self):
        url = "https://example.com/cookies"
        self.assertFalse(classify_as_dpa(url, rec(
            url,
            title="Cookie Policy",
            text="This cookie policy explains data processing on our site.",
        )))

    def test_product_page_is_not_a_dpa(self):
        url = "https://www.nvidia.com/en-us/solutions/data-processing/"
        self.assertTrue(path_is_product_page("/en-us/solutions/data-processing/"))
        self.assertFalse(classify_as_dpa(url, rec(
            url,
            title="Data Processing Solutions",
            text="NVIDIA data processing units accelerate the data center.",
        )))

    def test_login_wall_is_not_filed(self):
        url = "https://example.com/legal/dpa"
        self.assertFalse(classify_as_dpa(url, rec(
            url,
            title="Sign in to continue",
            text="Please log in to view this document.",
        )))

    def test_vendor_facing_dpa_is_not_customer_processor_terms(self):
        url = "https://www.flocksafety.com/legal/vendor-dpa"
        self.assertFalse(classify_as_dpa(url, rec(
            url,
            title="Vendor Data Processing Addendum",
            text="This Vendor Data Processing Addendum applies to Flock vendors.",
        )))
        url2 = "https://www.bmc.com/legal/data-processing-addendum.html"
        self.assertFalse(classify_as_dpa(url2, rec(
            url2,
            title="Previous DPA for BMC Vendors - BMC Software",
            text="This previous DPA for BMC Vendors is provided for reference.",
        )))

    def test_itemuid_without_dpa_name_is_not_filed(self):
        url = "https://trust.example.com/?itemUid=c4223a81-5840-4e11-ac9f-2b812794a67e"
        self.assertFalse(classify_as_dpa(url, rec(
            url,
            title="Trust Center",
            text="Request access to documents.",
        )))

    def test_portal_vendor_host_rejected_for_other_companies(self):
        plaid = {"slug": "plaid", "domain": "plaid.com", "aliases": []}
        self.assertTrue(is_portal_vendor_host("https://plaid.securitypal.com/legal", plaid))
        self.assertFalse(is_first_party_url("https://plaid.securitypal.com/legal", plaid))
        vanta = {"slug": "vanta", "domain": "vanta.com", "aliases": []}
        self.assertFalse(is_portal_vendor_host("https://www.vanta.com/legal/dpa", vanta))
        self.assertTrue(is_first_party_url("https://www.vanta.com/legal/dpa", vanta))

    def test_link_text_extracts_dpa(self):
        html = (
            '<a href="/legal/terms">Master terms</a>'
            '<a href="/legal/customer-dpa">Data Processing Addendum</a>'
        )
        got = extract_dpa_candidates(html, "https://example.com/trust")
        self.assertIn("https://example.com/legal/customer-dpa", got)
        self.assertNotIn("https://example.com/legal/terms", got)

    def test_apply_dpa_adds_eight_and_leaves_other_factors(self):
        row = {
            "found": True,
            "links": {"privacy": "https://example.com/privacy"},
            "disclosure": {
                "score": 52,
                "tier": "on-file",
                "factors": {"page": 20, "marks": 10, "privacy": 6, "years": 16},
            },
        }
        self.assertTrue(apply_dpa_to_row(row, "https://example.com/legal/dpa"))
        self.assertEqual(row["links"]["dpa"], "https://example.com/legal/dpa")
        self.assertEqual(row["disclosure"]["factors"]["dpa"], 8)
        self.assertEqual(row["disclosure"]["factors"]["page"], 20)
        self.assertEqual(row["disclosure"]["score"], 60)
        self.assertEqual(row["disclosure"]["tier"], "on-file")
        self.assertFalse(apply_dpa_to_row(row, "https://example.com/other"))

    def test_link_text_extracts_subprocessors_and_drops_itemuid(self):
        html = (
            '<a href="/legal/terms">Master terms</a>'
            '<a href="/legal/subprocessors">Sub-processors</a>'
            '<a href="https://trust.example.com/?itemUid=abc">Subprocessors</a>'
        )
        got = extract_subprocessor_candidates(html, "https://example.com/trust")
        self.assertIn("https://example.com/legal/subprocessors", got)
        self.assertNotIn("https://example.com/legal/terms", got)
        self.assertFalse(any("itemUid" in u for u in got))

    def test_apply_subprocessors_adds_eight_and_leaves_other_factors(self):
        row = {
            "found": True,
            "links": {"privacy": "https://example.com/privacy"},
            "disclosure": {
                "score": 52,
                "tier": "on-file",
                "factors": {"page": 20, "marks": 10, "privacy": 6, "years": 16},
            },
        }
        self.assertTrue(apply_subprocessors_to_row(row, "https://example.com/legal/subprocessors"))
        self.assertEqual(row["links"]["subprocessors"], "https://example.com/legal/subprocessors")
        self.assertEqual(row["disclosure"]["factors"]["subprocessors"], 8)
        self.assertEqual(row["disclosure"]["factors"]["page"], 20)
        self.assertEqual(row["disclosure"]["score"], 60)
        self.assertEqual(row["disclosure"]["tier"], "on-file")
        self.assertFalse(apply_subprocessors_to_row(row, "https://example.com/other"))


if __name__ == "__main__":
    unittest.main()
