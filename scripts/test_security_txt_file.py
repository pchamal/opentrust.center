#!/usr/bin/env python3
"""RFC 9116 security.txt: file the URL after a live-shaped parse. Do not invent."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from enrich import (
    accept_security_txt,
    apply_optional_txt_links,
    apply_security_txt_to_row,
    is_first_party_or_branded_bounty,
    is_security_txt_path,
    is_valid_security_txt,
    optional_links_from_security_txt,
    security_txt_probe_urls,
)


def rec(url, *, text="", status=200, ok=True, ctype="text/plain", final=None, title=""):
    return {
        "ok": ok,
        "status": status,
        "title": title,
        "text": text,
        "raw_head": text,
        "ctype": ctype,
        "final_url": final or url,
    }


MSFT = {"slug": "microsoft", "name": "Microsoft", "domain": "microsoft.com", "aliases": []}
STRIPE = {"slug": "stripe", "name": "Stripe", "domain": "stripe.com", "aliases": []}


RFC = """# security.txt
Contact: mailto:security@example.com
Expires: 2027-12-31T23:59:59.000Z
Canonical: https://example.com/.well-known/security.txt
Policy: https://example.com/security
"""


class SecurityTxtParseTest(unittest.TestCase):
    def test_contact_is_enough(self):
        self.assertTrue(is_valid_security_txt("Contact: mailto:sec@ex.com\n", "text/plain"))

    def test_policy_is_enough(self):
        self.assertTrue(is_valid_security_txt("Policy: https://ex.com/security\n", "text/plain"))

    def test_expires_is_enough(self):
        self.assertTrue(is_valid_security_txt("Expires: 2027-01-01T00:00:00.000Z\n", "text/plain"))

    def test_canonical_is_enough(self):
        self.assertTrue(is_valid_security_txt(
            "Canonical: https://ex.com/.well-known/security.txt\n", "text/plain"
        ))

    def test_html_security_page_is_not_security_txt(self):
        html = "<!doctype html><html><body><h1>Security</h1><p>Contact us.</p></body></html>"
        self.assertFalse(is_valid_security_txt(html, "text/html"))
        url = "https://example.com/security"
        self.assertIsNone(accept_security_txt(url, rec(url, text=html, ctype="text/html")))
        self.assertFalse(is_security_txt_path(url))

    def test_empty_rejected(self):
        self.assertFalse(is_valid_security_txt("", "text/plain"))
        self.assertFalse(is_valid_security_txt("   ", "text/plain"))

    def test_accepts_well_known_200(self):
        url = "https://example.com/.well-known/security.txt"
        self.assertEqual(accept_security_txt(url, rec(url, text=RFC)), url)

    def test_404_rejected(self):
        url = "https://example.com/.well-known/security.txt"
        self.assertIsNone(accept_security_txt(url, rec(url, text=RFC, status=404, ok=False)))

    def test_home_bounce_rejected(self):
        url = "https://example.com/.well-known/security.txt"
        self.assertIsNone(accept_security_txt(url, rec(
            url, text=RFC, final="https://example.com/"
        )))

    def test_well_known_redirect_to_security_txt_kept(self):
        url = "https://example.com/.well-known/security.txt"
        final = "https://www.example.com/security.txt"
        self.assertEqual(accept_security_txt(url, rec(url, text=RFC, final=final)), final)


class SecurityTxtScoreTest(unittest.TestCase):
    def test_files_url_and_adds_six_when_unpaid(self):
        row = {
            "found": True,
            "links": {"privacy": "https://ex.com/privacy"},
            "disclosure": {"score": 32, "tier": "thin", "factors": {"portal": 20, "privacy": 6}},
        }
        self.assertTrue(apply_security_txt_to_row(row, "https://ex.com/.well-known/security.txt"))
        self.assertEqual(row["links"]["security_txt"], "https://ex.com/.well-known/security.txt")
        self.assertEqual(row["disclosure"]["factors"]["disclosure"], 6)
        self.assertEqual(row["disclosure"]["score"], 38)
        self.assertEqual(row["disclosure"]["tier"], "thin")

    def test_does_not_double_count_existing_bounty(self):
        row = {
            "found": True,
            "links": {"bug_bounty": "https://ex.com/security"},
            "disclosure": {"score": 26, "tier": "thin", "factors": {"portal": 20, "disclosure": 6}},
        }
        self.assertTrue(apply_security_txt_to_row(row, "https://ex.com/.well-known/security.txt"))
        self.assertEqual(row["disclosure"]["score"], 26)
        self.assertEqual(row["disclosure"]["factors"]["disclosure"], 6)

    def test_does_not_invent_expires_as_score(self):
        row = {
            "found": True,
            "links": {},
            "disclosure": {"score": 20, "tier": "thin", "factors": {"portal": 20}},
        }
        apply_security_txt_to_row(row, "https://ex.com/.well-known/security.txt")
        self.assertNotIn("expires", row["disclosure"]["factors"])
        self.assertEqual(row["disclosure"]["factors"]["disclosure"], 6)
        self.assertEqual(row["disclosure"]["score"], 26)

    def test_silent_stays_silent(self):
        row = {
            "found": False,
            "links": {},
            "disclosure": {"score": 0, "tier": "silent", "factors": {}},
        }
        apply_security_txt_to_row(row, "https://ex.com/.well-known/security.txt")
        self.assertEqual(row["disclosure"]["tier"], "silent")
        self.assertEqual(row["disclosure"]["score"], 6)

    def test_does_not_overwrite_existing(self):
        row = {
            "links": {"security_txt": "https://ex.com/.well-known/security.txt"},
            "disclosure": {"score": 26, "tier": "thin", "factors": {"disclosure": 6}},
        }
        self.assertFalse(apply_security_txt_to_row(row, "https://other.example/.well-known/security.txt"))


class OptionalLinksTest(unittest.TestCase):
    def test_mailto_contact_is_not_filed(self):
        extras = optional_links_from_security_txt(
            "Contact: mailto:security@microsoft.com\nPolicy: https://www.microsoft.com/msrc\n",
            MSFT,
            {},
        )
        self.assertNotIn("security", extras)

    def test_first_party_contact_url(self):
        extras = optional_links_from_security_txt(
            "Contact: https://www.microsoft.com/msrc\nExpires: 2027-01-01T00:00:00Z\n",
            MSFT,
            {},
        )
        self.assertEqual(extras.get("security"), "https://www.microsoft.com/msrc")

    def test_branded_hackerone_policy(self):
        text = "Policy: https://hackerone.com/stripe\nContact: mailto:security@stripe.com\n"
        extras = optional_links_from_security_txt(text, STRIPE, {})
        self.assertEqual(extras.get("bug_bounty"), "https://hackerone.com/stripe")
        self.assertTrue(is_first_party_or_branded_bounty("https://hackerone.com/stripe", STRIPE))

    def test_platform_homepage_is_not_branded(self):
        self.assertFalse(is_first_party_or_branded_bounty("https://hackerone.com", STRIPE))

    def test_optional_apply_does_not_add_score(self):
        row = {
            "links": {"security_txt": "https://stripe.com/.well-known/security.txt"},
            "disclosure": {"score": 26, "tier": "thin", "factors": {"disclosure": 6}},
        }
        apply_optional_txt_links(row, {"bug_bounty": "https://hackerone.com/stripe"})
        self.assertEqual(row["links"]["bug_bounty"], "https://hackerone.com/stripe")
        self.assertEqual(row["disclosure"]["score"], 26)


class ProbeUrlTest(unittest.TestCase):
    def test_well_known_first(self):
        urls = security_txt_probe_urls(MSFT, well_known_only=True)
        self.assertIn("https://microsoft.com/.well-known/security.txt", urls)
        self.assertIn("https://www.microsoft.com/.well-known/security.txt", urls)
        self.assertTrue(all("security.txt" in u for u in urls))
        self.assertFalse(any(u.rstrip("/").endswith("/security") for u in urls))


if __name__ == "__main__":
    unittest.main()
