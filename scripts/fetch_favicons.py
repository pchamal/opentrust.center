#!/usr/bin/env python3
"""Vendor first-party favicons. Skip failures. Do not hotlink Google s2."""
from __future__ import annotations

import io
import json
import re
import sys
import time
from collections import deque
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

# Issuer homepage favicons are stamps after the ink pass (CMMC, K-ISMS,
# MTCS, TISAX). The word stays the authority. Do not map marks here.
MARK_DOMAINS: dict[str, str] = {}

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
    if stamp_reason(im):
        return None
    return im


def _alpha_mask(im: Image.Image, threshold: int = 32) -> tuple[list[list[bool]], int, int]:
    rgba = im.convert("RGBA")
    w, h = rgba.size
    pix = rgba.load()
    mask = [[pix[x, y][3] >= threshold for x in range(w)] for y in range(h)]
    return mask, w, h


def _components(mask: list[list[bool]], w: int, h: int) -> list[list[tuple[int, int]]]:
    seen = [[False] * w for _ in range(h)]
    comps: list[list[tuple[int, int]]] = []
    min_size = max(4, int(w * h * 0.008))
    for y in range(h):
        for x in range(w):
            if not mask[y][x] or seen[y][x]:
                continue
            q = deque([(x, y)])
            seen[y][x] = True
            cells: list[tuple[int, int]] = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        q.append((nx, ny))
            if len(cells) >= min_size:
                comps.append(cells)
    comps.sort(key=len, reverse=True)
    return comps


def _hole_count(mask: list[list[bool]], w: int, h: int) -> int:
    seen = [[False] * w for _ in range(h)]
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            if not mask[y][x] and not seen[y][x]:
                seen[y][x] = True
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if not mask[y][x] and not seen[y][x]:
                seen[y][x] = True
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not mask[ny][nx] and not seen[ny][nx]:
                seen[ny][nx] = True
                q.append((nx, ny))
    holes = 0
    for y in range(h):
        for x in range(w):
            if mask[y][x] or seen[y][x]:
                continue
            holes += 1
            qq = deque([(x, y)])
            seen[y][x] = True
            while qq:
                cx, cy = qq.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and not mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        qq.append((nx, ny))
    return holes


def _convexity(cells: list[tuple[int, int]]) -> float:
    if len(cells) < 8:
        return 1.0
    pts = sorted(set(cells))

    def cross(o: tuple[int, int], a: tuple[int, int], b: tuple[int, int]) -> int:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[int, int]] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[tuple[int, int]] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        return 1.0
    area = 0
    for i, (x1, y1) in enumerate(hull):
        x2, y2 = hull[(i + 1) % len(hull)]
        area += x1 * y2 - x2 * y1
    area = abs(area) / 2
    return len(cells) / area if area else 1.0


def _circle_jaccard(mask: list[list[bool]], w: int, h: int) -> float:
    ink = [(x, y) for y in range(h) for x in range(w) if mask[y][x]]
    if not ink:
        return 0.0
    xs = [p[0] for p in ink]
    ys = [p[1] for p in ink]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    r = max(max(xs) - min(xs), max(ys) - min(ys)) / 2
    if r < 1:
        return 0.0
    inter = 0
    circ = 0
    r2 = r * r
    for y in range(h):
        for x in range(w):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                circ += 1
                if mask[y][x]:
                    inter += 1
    union = circ + len(ink) - inter
    return inter / union if union else 0.0


def _letterish(aspect: float, fill_bbox: float) -> bool:
    return 0.55 <= aspect <= 1.40 and 0.20 <= fill_bbox <= 0.70


def _component_box(cells: list[tuple[int, int]]) -> tuple[float, float, float]:
    xs = [p[0] for p in cells]
    ys = [p[1] for p in cells]
    bw = max(xs) - min(xs) + 1
    bh = max(ys) - min(ys) + 1
    aspect = bw / max(bh, 1)
    fill_bbox = len(cells) / max(bw * bh, 1)
    return aspect, fill_bbox, _convexity(cells)


def _dominant_disc(comps: list[list[tuple[int, int]]], ink_n: int) -> bool:
    if not comps or ink_n <= 0:
        return False
    main = comps[0]
    if len(main) < 0.5 * ink_n:
        return False
    aspect, fill_bbox, conv = _component_box(main)
    return 0.75 <= aspect <= 1.35 and fill_bbox >= 0.72 and conv >= 0.95


def _similar_square_peers(comps: list[list[tuple[int, int]]]) -> bool:
    """Three similar near-square tiles — punctuation, not a mark."""
    if len(comps) != 3:
        return False
    sizes = [len(c) for c in comps]
    if min(sizes) < 0.75 * max(sizes):
        return False
    for cells in comps:
        aspect, _fill, _conv = _component_box(cells)
        if not (0.75 <= aspect <= 1.35):
            return False
    return True


def _union_box(comps: list[list[tuple[int, int]]]) -> tuple[float, float]:
    cells = [p for c in comps for p in c]
    if not cells:
        return 1.0, 0.0
    xs = [p[0] for p in cells]
    ys = [p[1] for p in cells]
    bw = max(xs) - min(xs) + 1
    bh = max(ys) - min(ys) + 1
    return bw / max(bh, 1), len(cells) / max(bw * bh, 1)


def _wordmark_bar(comps: list[list[tuple[int, int]]]) -> bool:
    """Wide/tall wordmark bar or stacked-bar equals-sign. Not a two-part logo."""
    if not comps:
        return False
    aspect, fill = _union_box(comps)
    if (aspect >= 2.2 or aspect <= 0.45) and fill >= 0.60:
        return True
    if len(comps) == 2:
        a0, f0, _c0 = _component_box(comps[0])
        a1, f1, _c1 = _component_box(comps[1])
        n0, n1 = len(comps[0]), len(comps[1])
        similar = min(n0, n1) >= 0.70 * max(n0, n1)
        bars = a0 >= 2.0 and a1 >= 2.0 and f0 >= 0.55 and f1 >= 0.55
        if similar and bars:
            return True
    return False


def stamp_reason(im: Image.Image) -> str:
    """Why this bitmap must not emit after the 12px Ledger Black ink pass.

    The CSS crush makes every opaque pixel the same ink. Only the alpha
    silhouette remains. A filled square, disc, globe, letter tile, or
    unreadable blob is a placeholder — missing = name only. When unsure,
    reject. Empty string means the silhouette is distinctive enough.
    """
    try:
        mask, w, h = _alpha_mask(im)
    except Exception:
        return "unreadable"
    canvas = w * h
    if w < 8 or h < 8 or canvas <= 0:
        return "tiny"
    ink_n = sum(sum(row) for row in mask)
    ink_pct = ink_n / canvas
    if ink_pct >= 0.72:
        return "solid-fill"
    jac = _circle_jaccard(mask, w, h)
    if jac >= 0.82:
        return "disc"
    if min(w, h) <= 16 and ink_pct >= 0.50:
        return "16px-blob"
    comps = _components(mask, w, h)
    if not comps:
        return "empty"
    if _dominant_disc(comps, ink_n):
        return "disc"
    if _similar_square_peers(comps):
        return "punctuation"
    if _wordmark_bar(comps):
        return "punctuation"
    if min(w, h) <= 32 and len(comps) >= 4:
        return "letter-tile"
    if len(comps) == 1:
        cells = comps[0]
        xs = [p[0] for p in cells]
        ys = [p[1] for p in cells]
        bw = max(xs) - min(xs) + 1
        bh = max(ys) - min(ys) + 1
        aspect = bw / max(bh, 1)
        fill_bbox = len(cells) / max(bw * bh, 1)
        if fill_bbox >= 0.88:
            return "solid-shape"
        letter = _letterish(aspect, fill_bbox)
        if letter and _hole_count(mask, w, h) >= 1:
            return "letter-tile"
        if letter and _convexity(cells) >= 0.85:
            return "letter-tile"
        if jac >= 0.75:
            return "disc"
    if len(comps) == 2:
        main, dot = comps[0], comps[1]
        if len(dot) < 0.12 * len(main):
            xs = [p[0] for p in main]
            ys = [p[1] for p in main]
            bw = max(xs) - min(xs) + 1
            bh = max(ys) - min(ys) + 1
            aspect = bw / max(bh, 1)
            fill_bbox = len(main) / max(bw * bh, 1)
            if _letterish(aspect, fill_bbox):
                return "letter-tile"
    return ""


def keep_mark(im: Image.Image) -> bool:
    return not stamp_reason(im)


def save_png(im: Image.Image, dest: Path) -> bool:
    if stamp_reason(im):
        return False
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


def existing_mark(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size <= 20:
        return False
    try:
        im = Image.open(path)
        im.load()
    except Exception:
        return False
    if stamp_reason(im):
        path.unlink(missing_ok=True)
        return False
    return True


def job(kind: str, key: str, domain: str) -> tuple[str, str, str, bool]:
    dest = OUT / filename_for(domain)
    if existing_mark(dest):
        return kind, key, domain, True
    try:
        im = collect_domain(domain)
        if not im:
            return kind, key, domain, False
        return kind, key, domain, save_png(im, dest)
    except Exception:
        return kind, key, domain, False


def rescan_vendored() -> tuple[int, int]:
    """Drop stamps, discs, globes, letter tiles. Missing = name only."""
    company_ok: dict[str, str] = {}
    for domain in load_company_domains():
        name = filename_for(domain)
        if existing_mark(OUT / name):
            company_ok[domain] = name
    host_ok: set[str] = set()
    for host in set(MARK_DOMAINS.values()):
        name = filename_for(host)
        if existing_mark(OUT / name):
            host_ok.add(host)
    mark_ok = {}
    for mid, host in MARK_DOMAINS.items():
        name = filename_for(host)
        if host in host_ok and existing_mark(OUT / name):
            mark_ok[mid] = name
    indexed = set(company_ok.values()) | set(mark_ok.values())
    dropped = 0
    for path in OUT.glob("*.png"):
        if path.name in indexed and existing_mark(path):
            continue
        path.unlink(missing_ok=True)
        dropped += 1
    write_index(company_ok, mark_ok)
    return len(company_ok), dropped


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if "--rescan" in sys.argv:
        kept, dropped = rescan_vendored()
        print(f"rescan · {kept} company marks kept · stamps removed", flush=True)
        return 0
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
        if existing_mark(OUT / name):
            mark_ok[mid] = name
    write_index(company_ok, mark_ok)
    print(
        f"wrote {len(company_ok)} company icons, {len(mark_ok)} mark mappings "
        f"in {time.time() - t0:.1f}s → {OUT}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
