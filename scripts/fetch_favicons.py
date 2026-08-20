#!/usr/bin/env python3
"""Vendor first-party favicons. Skip failures. Do not hotlink Google s2."""
from __future__ import annotations

import io
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
OUT = SITE / "favicons"
UA = "opentrust.center-favicon/1.0 (+https://opentrust.center/)"
TIMEOUT = 12
WORKERS = 16

# First-party issuer marks only. Skip seals, ribbons, badges, and
# wordmarks-in-a-circle — the word stays the authority.
MARK_DOMAINS = {
    "cmmc-l1": "cyberab.org",
    "cmmc-l2": "cyberab.org",
    "k-isms": "kisa.or.kr",
    "mtcs": "imda.gov.sg",
    "tisax": "enx.com",
}

ICON_REL = re.compile(r"(?:^|\s)(?:shortcut\s+)?icon(?:\s|$)|apple-touch-icon", re.I)
DATA_URI = re.compile(r"^data:", re.I)


class IconParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.candidates: list[tuple[int, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return
        ad = {k.lower(): (v or "") for k, v in attrs}
        rel = ad.get("rel", "")
        href = ad.get("href", "").strip()
        if not href or DATA_URI.match(href) or not ICON_REL.search(rel):
            return
        typ = ad.get("type", "").lower()
        sizes = ad.get("sizes", "").lower()
        score = 10
        if "svg" in typ or href.lower().endswith(".svg"):
            score = 1
        elif "png" in typ or href.lower().endswith(".png"):
            score = 40
        elif href.lower().endswith(".ico") or "icon" in typ:
            score = 25
        if "apple-touch" in rel.lower():
            score -= 5
        if sizes and sizes != "any":
            try:
                n = max(int(p) for p in re.findall(r"\d+", sizes))
                if 16 <= n <= 64:
                    score += 8
                elif n > 64:
                    score += 3
            except ValueError:
                pass
        self.candidates.append((score, href))


def host_of(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
        return host
    except Exception:
        return ""


def safe_url(url: str) -> str:
    raw = str(url or "").strip()
    if not raw or any(ord(ch) < 32 for ch in raw):
        return ""
    try:
        parsed = urlparse(raw)
    except Exception:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    path = quote(parsed.path or "/", safe="/%._-~")
    query = quote(parsed.query, safe="=&%._-~")
    return parsed._replace(path=path, query=query, fragment="").geturl()


def fetch(url: str, timeout: int = TIMEOUT) -> tuple[bytes, str, str] | None:
    url = safe_url(url)
    if not url:
        return None
    req = Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            final = resp.geturl()
            data = resp.read(2_000_000)
            return data, ctype, final
    except Exception:
        return None


def looks_like_html(data: bytes, ctype: str) -> bool:
    if "html" in ctype:
        return True
    head = data[:200].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<html" in head[:80]


def parse_icons(html: bytes, base: str) -> list[str]:
    try:
        text = html.decode("utf-8", errors="ignore")
    except Exception:
        return []
    parser = IconParser()
    try:
        parser.feed(text)
    except Exception:
        return []
    ranked = sorted(parser.candidates, key=lambda x: -x[0])
    out = []
    for _score, href in ranked:
        absu = urljoin(base, href)
        if absu not in out:
            out.append(absu)
    return out


def image_from_bytes(data: bytes) -> Image.Image | None:
    if not data or len(data) < 32:
        return None
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    if getattr(im, "n_frames", 1) > 1:
        best = None
        best_area = -1
        for i in range(im.n_frames):
            try:
                im.seek(i)
                frame = im.copy()
            except Exception:
                continue
            area = frame.size[0] * frame.size[1]
            if 16 * 16 <= area <= 128 * 128 and area > best_area:
                best = frame
                best_area = area
            elif best is None or (area > best_area and area <= 256 * 256):
                best = frame
                best_area = area
        im = best or im
    try:
        im = im.convert("RGBA")
    except Exception:
        return None
    w, h = im.size
    if w < 8 or h < 8:
        return None
    if w > 64 or h > 64:
        im.thumbnail((64, 64), Image.Resampling.LANCZOS)
    return im


def save_png(im: Image.Image, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp.png")
    try:
        im.save(tmp, format="PNG", optimize=True)
        tmp.replace(dest)
        return dest.stat().st_size > 20
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return False


def collect_from_url(url: str) -> Image.Image | None:
    got = fetch(url)
    if not got:
        return None
    data, ctype, _final = got
    if looks_like_html(data, ctype):
        return None
    return image_from_bytes(data)


def collect_domain(domain: str) -> Image.Image | None:
    domain = (domain or "").strip().lower().removeprefix("www.")
    if not domain or "." not in domain:
        return None
    roots = [f"https://{domain}/", f"https://www.{domain}/"]
    seen: set[str] = set()
    for root in roots:
        got = fetch(root)
        if not got:
            continue
        data, ctype, final = got
        if looks_like_html(data, ctype) or "html" in ctype or data[:20].lstrip().startswith(b"<"):
            for href in parse_icons(data, final or root):
                if href in seen:
                    continue
                seen.add(href)
                im = collect_from_url(href)
                if im:
                    return im
        else:
            im = image_from_bytes(data)
            if im:
                return im
        ico = urljoin(final or root, "/favicon.ico")
        if ico not in seen:
            seen.add(ico)
            im = collect_from_url(ico)
            if im:
                return im
    for ico in (f"https://{domain}/favicon.ico", f"https://www.{domain}/favicon.ico"):
        if ico in seen:
            continue
        im = collect_from_url(ico)
        if im:
            return im
    return None


def filename_for(domain: str) -> str:
    safe = re.sub(r"[^a-z0-9._-]+", "-", domain.lower())
    return f"{safe}.png"


def load_company_domains() -> list[str]:
    data = json.loads((SITE / "data.json").read_text())
    seen: set[str] = set()
    out: list[str] = []
    for row in data.get("companies") or []:
        domain = (row.get("domain") or "").strip().lower().removeprefix("www.")
        if domain and domain not in seen:
            seen.add(domain)
            out.append(domain)
    wires = SITE / "data" / "subprocessors.json"
    if wires.exists():
        doc = json.loads(wires.read_text())
        for node in doc.get("nodes") or []:
            domain = (node.get("domain") or "").strip().lower().removeprefix("www.")
            if domain and domain not in seen:
                seen.add(domain)
                out.append(domain)
    return out


def write_index(company_ok: dict[str, str], mark_ok: dict[str, str]) -> None:
    payload = {
        "companies": dict(sorted(company_ok.items())),
        "marks": dict(sorted(mark_ok.items())),
    }
    (OUT / "index.json").write_text(json.dumps(payload, indent=2) + "\n")


def job(kind: str, key: str, domain: str) -> tuple[str, str, str, bool]:
    dest = OUT / filename_for(domain)
    if dest.exists() and dest.stat().st_size > 20:
        return kind, key, domain, True
    try:
        im = collect_domain(domain)
        if not im:
            return kind, key, domain, False
        return kind, key, domain, save_png(im, dest)
    except Exception:
        return kind, key, domain, False


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    companies = load_company_domains()
    mark_domains = {mid: host for mid, host in MARK_DOMAINS.items() if host}
    unique_mark_hosts = sorted(set(mark_domains.values()))
    tasks: list[tuple[str, str, str]] = [("company", d, d) for d in companies]
    tasks += [("mark-host", host, host) for host in unique_mark_hosts]
    print(f"fetching {len(companies)} company domains + {len(unique_mark_hosts)} issuer domains", flush=True)
    company_ok: dict[str, str] = {}
    host_ok: set[str] = set()
    done = 0
    ok_n = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(job, kind, key, domain): (kind, key, domain) for kind, key, domain in tasks}
        for fut in as_completed(futs):
            kind, key, domain = futs[fut]
            try:
                kind, key, domain, ok = fut.result()
            except Exception:
                ok = False
            done += 1
            if ok:
                ok_n += 1
                name = filename_for(domain)
                if kind == "company":
                    company_ok[domain] = name
                else:
                    host_ok.add(domain)
            if done % 40 == 0 or done == len(tasks):
                print(f"  {done}/{len(tasks)} tried · {ok_n} on file", flush=True)
    mark_ok = {}
    for mid, host in mark_domains.items():
        name = filename_for(host)
        if host in host_ok or (OUT / name).exists():
            mark_ok[mid] = name
            host_ok.add(host)
    write_index(company_ok, mark_ok)
    print(
        f"wrote {len(company_ok)} company icons, {len(mark_ok)} mark mappings "
        f"in {time.time() - t0:.1f}s → {OUT}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
