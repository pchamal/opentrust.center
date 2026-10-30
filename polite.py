"""Polite HTTP for the register crawler.

Caps in-flight fetches, waits between requests to one host, reads robots.txt,
honors Retry-After, and stops guessed paths after a homepage 403 or 429.
Nothing here is deployed. Tests replace ``urlopen`` and ``sleep``.
"""
from __future__ import annotations

import ssl
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen as _real_urlopen
from urllib.robotparser import RobotFileParser

# Public address on https://opentrust.center/contact
CONTACT_EMAIL = "hello@opentrust.center"
UA = f"opentrust.center/1.0 (+https://opentrust.center; {CONTACT_EMAIL})"

MAX_IN_FLIGHT = 4
MIN_HOST_INTERVAL = 2.0
# Pause before the next real request after a homepage 403 or 429
# when the response has no Retry-After.
HOMEPAGE_BLOCK_PAUSE = 30.0
# Guessed paths stay unsent for this long after that homepage answer.
GUESS_BACKOFF_SECONDS = 24 * 60 * 60
# Do not sleep inside the process longer than this for one Retry-After.
MAX_RETRY_SLEEP = 120.0

# Query keys dropped before a request. SafeBase itemUid links and utm tags
# otherwise fan out into many fetches of one page.
_TRACKING_EXACT = frozenset({
    "itemuid",
    "itemname",
    "source",
    "_gl",
    "__hssc",
})
_TRACKING_PREFIXES = ("utm_", "vero_")

# Path guesses used by crawl.py and enrich.py. A homepage 403 or 429
# suppresses these on that host. A recorded page that is not in this set
# is still fetched, after the host pause.
GUESSED_PATHS = frozenset({
    "/.well-known/security.txt",
    "/security.txt",
    "/privacy",
    "/privacy-policy",
    "/legal/privacy",
    "/subprocessors",
    "/sub-processors",
    "/legal/subprocessors",
    "/legal/sub-processors",
    "/legal/service-providers",
    "/privacy/subprocessors",
    "/company/subprocessors",
    "/trust/subprocessors",
    "/legal/sub-processors-page",
    "/dpa",
    "/legal/dpa",
    "/legal/data-processing-addendum",
    "/legal/data-processing-agreement",
    "/data-processing-addendum",
    "/data-processing-agreement",
    "/policies/data-processing-addendum",
    "/policies/data-processing-agreement",
    "/policies/dpa",
    "/terms/dpa",
    "/company/dpa",
    "/gdpr/dpa",
    "/legal/gdpr/dpa",
    "/privacy/dpa",
    "/legal/processor-terms",
    "/legal/data-processing",
    "/data-processing",
    "/status",
    "/bug-bounty",
    "/responsible-disclosure",
    "/security/responsible-disclosure",
    "/vulnerability-disclosure",
    "/security",
    "/trust",
    "/trust-center",
    "/docs/security",
})

SSL_CTX = ssl.create_default_context()

# Tests replace these.
urlopen = _real_urlopen
sleep = time.sleep


class _State:
    def __init__(self) -> None:
        self.sem = threading.BoundedSemaphore(MAX_IN_FLIGHT)
        self.guard = threading.Lock()
        self.host_locks: dict[str, threading.Lock] = {}
        self.next_allowed: dict[str, float] = {}
        self.guess_blocked_until: dict[str, float] = {}
        self.homepage_checked: set[str] = set()
        # exact hostname -> (mode, parser or None, crawl delay or None, retry_at monotonic)
        self.robots: dict[str, tuple] = {}


_state = _State()


def reset() -> None:
    """Clear per-run host memory. Tests call this. A new process starts clean."""
    global _state
    _state = _State()


def normalize_fetch_url(url: str) -> str:
    """Drop the fragment and tracking query params. This is the URL on the wire."""
    raw = (url or "").strip()
    parts = urlsplit(raw)
    if not parts.scheme or not parts.netloc:
        return raw
    host = (parts.hostname or "").lower()
    if not host:
        return raw
    netloc = host
    if parts.port:
        netloc = f"{host}:{parts.port}"
    if parts.username:
        auth = parts.username
        if parts.password:
            auth = f"{auth}:{parts.password}"
        netloc = f"{auth}@{netloc}"
    kept = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        low = key.lower()
        if low in _TRACKING_EXACT or low.startswith(_TRACKING_PREFIXES):
            continue
        kept.append((key, value))
    query = urlencode(kept)
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", query, ""))


def rate_host(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    if host.startswith("www."):
        return host[4:]
    return host


def exact_host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def is_homepage(url: str) -> bool:
    path = urlsplit(url).path or "/"
    return path in {"", "/"}


def is_guessed_path(url: str) -> bool:
    path = (urlsplit(url).path or "/").rstrip("/") or "/"
    return path.lower() in GUESSED_PATHS


def guesses_blocked(url: str, now: float | None = None) -> bool:
    host = rate_host(url)
    until = _state.guess_blocked_until.get(host)
    if until is None:
        return False
    clock = time.time() if now is None else now
    return clock < until


def _host_lock(host: str) -> threading.Lock:
    with _state.guard:
        lock = _state.host_locks.get(host)
        if lock is None:
            lock = threading.Lock()
            _state.host_locks[host] = lock
        return lock


def _skipped(url: str, reason: str, status: int = 0) -> dict:
    return {
        "ok": False,
        "status": status,
        "final_url": url,
        "headers": {},
        "body": "",
        "skipped": reason,
    }


def _header_map(headers) -> dict:
    if not headers:
        return {}
    try:
        return {str(k).lower(): v for k, v in headers.items()}
    except Exception:
        return {}


def _parse_retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        seconds = float(text)
    except ValueError:
        seconds = None
    if seconds is not None:
        return max(0.0, seconds)
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def _safe_read(obj, limit: int) -> bytes:
    try:
        data = obj.read(limit) if limit else obj.read()
    except Exception:
        return b""
    return data or b""


def _http(url: str, max_body: int, timeout: int, accept: str) -> tuple[int, dict, bytes, str]:
    req = Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": accept,
            "Accept-Language": "en",
        },
        method="GET",
    )
    try:
        resp = urlopen(req, timeout=timeout, context=SSL_CTX)
    except HTTPError as exc:
        body = _safe_read(exc, max_body)
        return exc.code or 0, _header_map(exc.headers), body, url
    except (URLError, TimeoutError, ssl.SSLError, OSError):
        return 0, {}, b"", url
    try:
        status = getattr(resp, "status", 200) or 200
        final = resp.geturl() if hasattr(resp, "geturl") else url
        headers = _header_map(getattr(resp, "headers", None))
        body = _safe_read(resp, max_body)
        return status, headers, body, final or url
    finally:
        close = getattr(resp, "close", None)
        if close:
            try:
                close()
            except Exception:
                pass


def _wait_turn(host: str) -> bool:
    """Sleep out a short host gap. A long backoff returns False and does not fetch."""
    delay = _state.next_allowed.get(host, 0.0) - time.monotonic()
    if delay <= 0:
        return True
    if delay > MAX_RETRY_SLEEP:
        return False
    sleep(delay)
    return True


def _schedule_next(host: str, interval: float | None = None) -> None:
    gap = MIN_HOST_INTERVAL if interval is None else max(MIN_HOST_INTERVAL, interval)
    target = time.monotonic() + gap
    current = _state.next_allowed.get(host, 0.0)
    if target > current:
        _state.next_allowed[host] = target


def _extend_pause(host: str, seconds: float) -> None:
    target = time.monotonic() + max(0.0, seconds)
    current = _state.next_allowed.get(host, 0.0)
    if target > current:
        _state.next_allowed[host] = target


def _host_interval(host: str, exact: str) -> float:
    rec = _state.robots.get(exact)
    delay = None
    if rec and rec[2] is not None:
        delay = rec[2]
    if delay is None:
        return MIN_HOST_INTERVAL
    try:
        return max(MIN_HOST_INTERVAL, float(delay))
    except (TypeError, ValueError):
        return MIN_HOST_INTERVAL


def _looks_like_html(body: bytes, content_type: str) -> bool:
    ctype = (content_type or "").lower()
    if "html" in ctype:
        return True
    sample = body.lstrip()[:400].lower()
    if sample.startswith(b"<!doctype html") or sample.startswith(b"<html") or sample.startswith(b"<head"):
        return True
    return b"<html" in sample or b"<!doctype html" in sample


def _robots_parser(text: str) -> tuple[RobotFileParser, float | None]:
    parser = RobotFileParser()
    parser.parse(text.splitlines())
    delay = parser.crawl_delay(UA)
    try:
        delay_f = float(delay) if delay is not None else None
    except (TypeError, ValueError):
        delay_f = None
    return parser, delay_f


def _load_robots(url: str, max_body: int, timeout: int) -> tuple[str, str]:
    """Return (decision, detail). decision is allow, deny, or retry.

    An HTML body is treated as no robots file, even if the markup contains
    the word Disallow. Trust apps sometimes serve their page at /robots.txt.
    """
    exact = exact_host(url)
    host = rate_host(url)
    cached = _state.robots.get(exact)
    if cached:
        mode = cached[0]
        if mode == "retry" and time.monotonic() < cached[3]:
            return "retry", "robots-retry"
        if mode != "retry":
            return mode, "cached"
    parts = urlsplit(url)
    robots = urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
    if exact_host(robots) == exact and (urlsplit(url).path or "/").rstrip("/") == "/robots.txt":
        return "allow", "is-robots"
    got = _exchange(robots, max_body=min(max_body, 65536), timeout=timeout, accept="text/plain,*/*;q=0.1")
    if got is None:
        return "retry", "robots-wait"
    status, headers, body, _final = got
    if status == 429:
        delay = _parse_retry_after(headers.get("retry-after")) or HOMEPAGE_BLOCK_PAUSE
        delay = min(delay, MAX_RETRY_SLEEP)
        _extend_pause(host, delay)
        _state.robots[exact] = ("retry", None, None, time.monotonic() + delay)
        return "retry", "robots-429"
    ctype = headers.get("content-type", "")
    if status != 200 or _looks_like_html(body, ctype):
        _state.robots[exact] = ("allow", None, None, 0.0)
        return "allow", "absent"
    text = body.decode("utf-8", "replace")
    parser, delay = _robots_parser(text)
    _state.robots[exact] = ("rules", parser, delay, 0.0)
    if delay is not None and delay > MIN_HOST_INTERVAL:
        _extend_pause(host, delay)
    return "rules", "parsed"


def _robots_allows(url: str) -> bool:
    exact = exact_host(url)
    rec = _state.robots.get(exact)
    if not rec or rec[0] != "rules":
        return True
    parser: RobotFileParser = rec[1]
    try:
        return bool(parser.can_fetch(UA, url))
    except Exception:
        return True


def _exchange(url: str, max_body: int, timeout: int, accept: str):
    """Return (status, headers, body, final) or None when the host is still backing off."""
    host = rate_host(url)
    exact = exact_host(url)
    lock = _host_lock(host)
    with lock:
        if not _wait_turn(host):
            return None
        with _state.sem:
            status, headers, body, final = _http(url, max_body, timeout, accept)
        _schedule_next(host, _host_interval(host, exact))
        return status, headers, body, final


def _block_guesses(host: str, headers: dict) -> None:
    retry = _parse_retry_after(headers.get("retry-after"))
    pause = retry if retry is not None else HOMEPAGE_BLOCK_PAUSE
    pause = max(MIN_HOST_INTERVAL, pause)
    # Guesses stop for 24 hours. The pause is the gap before any other request.
    _state.guess_blocked_until[host] = time.time() + GUESS_BACKOFF_SECONDS
    if pause > MAX_RETRY_SLEEP:
        # A huge Retry-After is honored by not sending another request this run.
        _extend_pause(host, MAX_RETRY_SLEEP + 1)
    else:
        _extend_pause(host, pause)


def _homepage_url(url: str) -> str:
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return ""
    return urlunsplit((parts.scheme, parts.netloc, "/", "", ""))


def _decode(status: int, headers: dict, body: bytes, final: str) -> dict:
    ok = bool(status) and status < 400
    return {
        "ok": ok,
        "status": status,
        "final_url": final,
        "headers": headers,
        "body": body.decode("utf-8", "replace") if body else "",
    }


def fetch(url: str, max_body: int = 32768, *, guessed: bool = False, timeout: int = 8) -> dict:
    """GET one URL under the politeness rules. ``guessed`` marks a path probe."""
    norm = normalize_fetch_url(url)
    if not norm.lower().startswith("http"):
        return _skipped(url, "bad-url")
    host = rate_host(norm)
    if not host:
        return _skipped(url, "bad-url")
    path = (urlsplit(norm).path or "/").rstrip("/") or "/"
    if path == "/robots.txt":
        return _skipped(norm, "robots-direct")

    guess = guessed or is_guessed_path(norm)
    if guess and not is_homepage(norm) and guesses_blocked(norm):
        return _skipped(norm, "host-backoff")

    if guess and not is_homepage(norm) and host not in _state.homepage_checked:
        _state.homepage_checked.add(host)
        home = _homepage_url(norm)
        if home and home != norm:
            # Status only. The body is not kept. A 403 or 429 arms the block
            # inside this call, before the guessed path is requested.
            fetch(home, max_body=1024, guessed=False, timeout=timeout)
            if guesses_blocked(norm):
                return _skipped(norm, "host-backoff")

    decision, _detail = _load_robots(norm, max_body=max_body, timeout=timeout)
    if decision == "retry":
        return _skipped(norm, "robots-retry", status=429)
    if decision == "rules" and not _robots_allows(norm):
        return _skipped(norm, "robots")

    accept = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    got = _exchange(norm, max_body, timeout, accept)
    if got is None:
        reason = "host-backoff" if guesses_blocked(norm) else "retry-after"
        return _skipped(norm, reason, status=429 if reason == "retry-after" else 0)
    status, headers, body, final = got
    if is_homepage(norm):
        _state.homepage_checked.add(host)
        if status in {403, 429}:
            _block_guesses(host, headers)
            return _decode(status, headers, body, final)

    if status in {429, 503} and not is_homepage(norm):
        retry = _parse_retry_after(headers.get("retry-after"))
        delay = max(MIN_HOST_INTERVAL, retry if retry is not None else MIN_HOST_INTERVAL)
        if delay > MAX_RETRY_SLEEP:
            _extend_pause(host, MAX_RETRY_SLEEP + 1)
            _state.guess_blocked_until[host] = time.time() + GUESS_BACKOFF_SECONDS
            return _decode(status, headers, body, final)
        sleep(min(delay, MAX_RETRY_SLEEP))
        _state.next_allowed[host] = time.monotonic()
        got = _exchange(norm, max_body, timeout, accept)
        if got is None:
            return _decode(status, headers, body, final)
        status, headers, body, final = got
        if status in {403, 429} and is_homepage(final):
            _block_guesses(rate_host(final or norm), headers)
    return _decode(status, headers, body, final)
