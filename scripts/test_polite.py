#!/usr/bin/env python3
"""Politeness rules for the register crawler. No live vendor traffic."""
from __future__ import annotations

import sys
import threading
import time
import unittest
from email.message import Message
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import crawl  # noqa: E402
import enrich  # noqa: E402
import polite  # noqa: E402


class Resp:
    def __init__(self, status, headers, body, final):
        self.status = status
        self.headers = headers
        self._body = body if isinstance(body, bytes) else body.encode()
        self._final = final

    def geturl(self):
        return self._final

    def read(self, n=-1):
        if n is None or n < 0:
            return self._body
        return self._body[:n]

    def close(self):
        return None


def http_error(url, code, headers=None, body=b""):
    msg = Message()
    for key, value in (headers or {}).items():
        msg[key] = value
    payload = body if isinstance(body, bytes) else body.encode()
    return HTTPError(url, code, "error", msg, BytesIO(payload))


class Router:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []
        self.inflight = 0
        self.max_inflight = 0
        self.lock = threading.Lock()
        self.delay = 0.0

    def __call__(self, req, timeout=None, context=None):
        url = req.full_url
        with self.lock:
            self.calls.append(url)
            self.inflight += 1
            self.max_inflight = max(self.max_inflight, self.inflight)
        if self.delay:
            time.sleep(self.delay)
        try:
            route = self.routes.get(url)
            if route is None:
                return Resp(404, {"content-type": "text/plain"}, b"", url)
            if isinstance(route, list):
                item = route.pop(0) if len(route) > 1 else route[0]
            else:
                item = route
            status, headers, body = item
            if status >= 400:
                raise http_error(url, status, headers, body)
            return Resp(status, headers, body, url)
        finally:
            with self.lock:
                self.inflight -= 1


class PoliteTest(unittest.TestCase):
    def setUp(self):
        polite.reset()
        enrich.clear_processor_page_cache()
        self.sleeps = []
        polite.sleep = self.sleeps.append

    def tearDown(self):
        polite.urlopen = polite._real_urlopen
        polite.sleep = time.sleep
        polite.reset()

    def test_user_agent_names_the_published_contact(self):
        self.assertEqual(polite.CONTACT_EMAIL, "hello@opentrust.center")
        self.assertIn("hello@opentrust.center", polite.UA)
        self.assertIn("opentrust.center/1.0", polite.UA)
        self.assertEqual(crawl.UA, polite.UA)
        self.assertEqual(enrich.UA, polite.UA)
        self.assertEqual(crawl.WORKERS, 4)
        self.assertEqual(enrich.WORKERS, 4)
        self.assertEqual(enrich.WIKI_WORKERS, 4)
        self.assertEqual(polite.MAX_IN_FLIGHT, 4)

    def test_tracking_params_are_stripped_before_the_request(self):
        raw = (
            "https://trust.example/subprocessors"
            "?itemUid=abc&itemName=List&source=footer&_gl=1&__hssc=2"
            "&utm_source=x&vero_id=9&lang=en#section"
        )
        self.assertEqual(
            polite.normalize_fetch_url(raw),
            "https://trust.example/subprocessors?lang=en",
        )
        router = Router({
            "https://trust.example/robots.txt": (404, {}, b""),
            "https://trust.example/": (200, {"content-type": "text/html"}, b"<html></html>"),
            "https://trust.example/subprocessors?lang=en": (
                200, {"content-type": "text/html"}, b"<html>list</html>",
            ),
        })
        polite.urlopen = router
        # Homepage is allowed, so the guessed path is still fetched once, without tracking tags.
        polite.fetch("https://trust.example/", guessed=False)
        polite.fetch(raw, guessed=True)
        joined = " ".join(router.calls)
        self.assertNotIn("itemUid", joined)
        self.assertNotIn("utm_source", joined)
        self.assertNotIn("vero_id", joined)
        self.assertNotIn("#section", joined)
        self.assertIn("https://trust.example/subprocessors?lang=en", router.calls)

    def test_robots_disallow_skips_the_page(self):
        body = "User-agent: *\nDisallow: /private\n"
        router = Router({
            "https://example.com/robots.txt": (200, {"content-type": "text/plain"}, body.encode()),
        })
        polite.urlopen = router
        rec = polite.fetch("https://example.com/private")
        self.assertEqual(rec.get("skipped"), "robots")
        self.assertEqual(router.calls, ["https://example.com/robots.txt"])

    def test_html_robots_txt_is_treated_as_absent(self):
        html = b"<html><body><p>Disallow: /</p></body></html>"
        router = Router({
            "https://trust.form.example/robots.txt": (200, {"content-type": "text/html"}, html),
            "https://trust.form.example/security": (200, {"content-type": "text/html"}, b"<html>ok</html>"),
        })
        polite.urlopen = router
        rec = polite.fetch("https://trust.form.example/security")
        self.assertTrue(rec["ok"])
        self.assertEqual(rec["status"], 200)
        self.assertIn("https://trust.form.example/security", router.calls)

    def test_same_host_waits_at_least_two_seconds(self):
        router = Router({
            "https://example.com/robots.txt": (404, {}, b""),
            "https://example.com/about": (200, {"content-type": "text/html"}, b"<html>a</html>"),
            "https://example.com/pricing": (200, {"content-type": "text/html"}, b"<html>b</html>"),
        })
        polite.urlopen = router
        polite.fetch("https://example.com/about")
        polite.fetch("https://example.com/pricing")
        gaps = [s for s in self.sleeps if s >= polite.MIN_HOST_INTERVAL - 0.05]
        self.assertGreaterEqual(len(gaps), 1)

    def test_retry_after_is_honored_before_a_second_try(self):
        router = Router({
            "https://example.com/robots.txt": (404, {}, b""),
            "https://example.com/about": [
                (429, {"retry-after": "9"}, b"slow"),
                (200, {"content-type": "text/html"}, b"<html>ok</html>"),
            ],
        })
        polite.urlopen = router
        rec = polite.fetch("https://example.com/about")
        self.assertEqual(rec["status"], 200)
        self.assertTrue(rec["ok"])
        self.assertIn(9, self.sleeps)
        about_calls = [u for u in router.calls if u.endswith("/about")]
        self.assertEqual(len(about_calls), 2)

    def test_homepage_403_stops_guessed_paths_and_backs_off(self):
        router = Router({
            "https://vendor.example/robots.txt": (404, {}, b""),
            "https://vendor.example/": (403, {}, b"no"),
            "https://vendor.example/subprocessors": (200, {"content-type": "text/html"}, b"<html>list</html>"),
            "https://vendor.example/legal/subprocessors": (
                200, {"content-type": "text/html"}, b"<html>list</html>",
            ),
        })
        polite.urlopen = router
        home = polite.fetch("https://vendor.example/")
        self.assertEqual(home["status"], 403)
        self.assertTrue(polite.guesses_blocked("https://vendor.example/subprocessors"))
        skipped = polite.fetch("https://vendor.example/subprocessors", guessed=True)
        self.assertEqual(skipped.get("skipped"), "host-backoff")
        also = crawl.fetch("https://vendor.example/legal/subprocessors", guessed=True)
        self.assertEqual(also.get("skipped"), "host-backoff")
        self.assertNotIn("https://vendor.example/subprocessors", router.calls)
        self.assertNotIn("https://vendor.example/legal/subprocessors", router.calls)
        until = polite._state.guess_blocked_until[polite.rate_host("https://vendor.example/")]
        self.assertGreater(until - time.time(), 23 * 60 * 60)

    def test_homepage_429_prefetched_before_a_guess(self):
        router = Router({
            "https://slow.example/robots.txt": (404, {}, b""),
            "https://slow.example/": (429, {"retry-after": "10"}, b"later"),
            "https://slow.example/trust": (200, {"content-type": "text/html"}, b"<html>trust</html>"),
        })
        polite.urlopen = router
        rec = polite.fetch("https://slow.example/trust", guessed=True)
        self.assertEqual(rec.get("skipped"), "host-backoff")
        self.assertIn("https://slow.example/", router.calls)
        self.assertNotIn("https://slow.example/trust", router.calls)
        self.assertTrue(polite.guesses_blocked("https://slow.example/trust"))

    def test_subprocessor_page_is_cached_within_the_run(self):
        router = Router({
            "https://example.com/robots.txt": (404, {}, b""),
            "https://example.com/legal/subprocessors": (
                200, {"content-type": "text/html"}, b"<html><title>List</title>names</html>",
            ),
        })
        polite.urlopen = router
        first = enrich.fetch_processor_page(
            "https://example.com/legal/subprocessors?utm_source=a&itemUid=1"
        )
        second = enrich.fetch_processor_page(
            "https://example.com/legal/subprocessors?utm_medium=b&itemUid=2"
        )
        self.assertIs(first, second)
        self.assertEqual(first["status"], 200)
        page_calls = [u for u in router.calls if "subprocessors" in u]
        self.assertEqual(page_calls, ["https://example.com/legal/subprocessors"])
        third = enrich.fetch_cited_processor_page("https://example.com/legal/subprocessors")
        self.assertIs(third, first)
        self.assertEqual([u for u in router.calls if "subprocessors" in u], page_calls)

    def test_at_most_four_fetches_in_flight(self):
        hosts = [f"h{i}.example" for i in range(8)]
        routes = {}
        for host in hosts:
            routes[f"https://{host}/robots.txt"] = (404, {}, b"")
            routes[f"https://{host}/about"] = (200, {"content-type": "text/html"}, b"<html>ok</html>")
        router = Router(routes)
        router.delay = 0.05
        polite.urlopen = router
        polite.sleep = lambda _s: None
        threads = [
            threading.Thread(target=polite.fetch, args=(f"https://{host}/about",))
            for host in hosts
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertLessEqual(router.max_inflight, 4)
        self.assertGreaterEqual(router.max_inflight, 2)


if __name__ == "__main__":
    unittest.main()
