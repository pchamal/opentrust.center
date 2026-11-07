#!/usr/bin/env python3
"""Anchor links and opt-in first-party hosts. No live vendor traffic."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from enrich import (  # noqa: E402
    OPT_IN_FIRST_PARTY_HOSTS,
    cited_list_skip_reason,
    extract_subprocessor_candidates,
    hosts_for,
    is_first_party_list_url,
    is_first_party_url,
    is_portal_vendor_host,
)


SECURITYPAL = {"slug": "securitypal", "domain": "securitypalhq.com", "aliases": []}
PLAID = {"slug": "plaid", "domain": "plaid.com", "aliases": []}
ACME = {"slug": "acme", "domain": "acme.com", "aliases": []}
VANTA = {"slug": "vanta", "domain": "vanta.com", "aliases": []}


def rec(url, *, title="", text="", html="", status=200):
    return {
        "ok": True,
        "status": status,
        "title": title,
        "text": text,
        "html": html,
        "ctype": "text/html",
        "final_url": url,
    }


class AnchorFinderTest(unittest.TestCase):
    def test_keeps_in_page_subprocessor_anchor(self):
        html = '<a href="#subprocessors">Subprocessors</a>'
        got = extract_subprocessor_candidates(html, "https://trust.securitypal.com/")
        self.assertIn("https://trust.securitypal.com/#subprocessors", got)

    def test_keeps_absolute_url_with_fragment(self):
        html = '<a href="https://trust.securitypal.com/#subprocessors">List</a>'
        got = extract_subprocessor_candidates(html, "https://trust.securitypal.com/")
        self.assertIn("https://trust.securitypal.com/#subprocessors", got)

    def test_keeps_fragment_on_a_list_path(self):
        html = '<a href="/legal/subprocessors#vendors">vendors</a>'
        got = extract_subprocessor_candidates(html, "https://example.com/trust")
        self.assertIn("https://example.com/legal/subprocessors#vendors", got)

    def test_still_drops_itemuid_and_unrelated_anchors(self):
        html = (
            '<a href="/legal/terms">Master terms</a>'
            '<a href="/legal/subprocessors">Sub-processors</a>'
            '<a href="https://trust.example.com/?itemUid=abc">Subprocessors</a>'
            '<a href="#pricing">Pricing</a>'
        )
        got = extract_subprocessor_candidates(html, "https://example.com/trust")
        self.assertIn("https://example.com/legal/subprocessors", got)
        self.assertNotIn("https://example.com/legal/terms", got)
        self.assertFalse(any("itemUid" in u for u in got))
        self.assertFalse(any(u.endswith("#pricing") for u in got))


class DomainAliasTest(unittest.TestCase):
    def test_securitypal_owns_the_listed_hosts_only(self):
        self.assertEqual(
            set(OPT_IN_FIRST_PARTY_HOSTS["securitypal"]),
            {"securitypalhq.com", "securitypal.com", "trust.securitypal.com"},
        )
        # The general hosts list must not treat securitypal.com as a
        # registrable domain, or every customer portal would match.
        self.assertIn("securitypalhq.com", hosts_for(SECURITYPAL))
        self.assertNotIn("securitypal.com", hosts_for(SECURITYPAL))

        anchor = "https://trust.securitypal.com/#subprocessors"
        self.assertTrue(is_first_party_url(anchor, SECURITYPAL))
        self.assertTrue(is_first_party_list_url(anchor, anchor, SECURITYPAL))
        self.assertTrue(is_first_party_url("https://securitypal.com/legal", SECURITYPAL))
        self.assertTrue(is_first_party_url("https://www.securitypal.com/legal", SECURITYPAL))
        self.assertTrue(is_first_party_url("https://www.securitypalhq.com/dpa", SECURITYPAL))
        self.assertFalse(is_portal_vendor_host("https://trust.securitypal.com/", SECURITYPAL))
        self.assertFalse(is_portal_vendor_host("https://securitypal.com/", SECURITYPAL))

    def test_customer_portals_stay_third_party(self):
        portal = "https://plaid.securitypal.com/legal"
        self.assertTrue(is_portal_vendor_host(portal, PLAID))
        self.assertFalse(is_first_party_url(portal, PLAID))
        self.assertTrue(is_portal_vendor_host(portal, SECURITYPAL))
        self.assertFalse(is_first_party_url(portal, SECURITYPAL))
        self.assertFalse(is_first_party_list_url(portal, portal, SECURITYPAL))

        safebase = "https://acme.safebase.io/"
        self.assertTrue(is_portal_vendor_host(safebase, ACME))
        self.assertFalse(is_first_party_url(safebase, ACME))
        self.assertFalse(is_portal_vendor_host("https://www.vanta.com/legal/dpa", VANTA))
        self.assertTrue(is_first_party_url("https://www.vanta.com/legal/dpa", VANTA))

    def test_own_trust_host_is_not_skipped_as_a_portal(self):
        url = "https://trust.securitypal.com/#subprocessors"
        reason = cited_list_skip_reason(
            url,
            rec(url, title="SecurityPal", text="Subprocessors", html="<h2>Subprocessors</h2>"),
            SECURITYPAL,
        )
        self.assertNotEqual(reason, "not-first-party")
        self.assertNotEqual(reason, "js-portal")

        other = "https://plaid.securitypal.com/"
        self.assertEqual(
            cited_list_skip_reason(
                other,
                rec(other, title="SecurityPal", text="Subprocessors", html="<h2>Subprocessors</h2>"),
                PLAID,
            ),
            "not-first-party",
        )


if __name__ == "__main__":
    unittest.main()
