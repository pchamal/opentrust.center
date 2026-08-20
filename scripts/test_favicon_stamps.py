#!/usr/bin/env python3
"""Stamp filter: missing = name only. No box, globe, or letter tile."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.fetch_favicons import stamp_reason  # noqa: E402

SITE = ROOT / "site"
FAV = SITE / "favicons"


def expect(name: str, cond: bool) -> None:
    if not cond:
        print("fail", name)
        raise SystemExit(1)
    print("ok", name)


def solid_square() -> Image.Image:
    im = Image.new("RGBA", (32, 32), (11, 20, 17, 255))
    return im


def filled_disc() -> Image.Image:
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((1, 1, 30, 30), fill=(20, 80, 200, 255))
    return im


def letter_a() -> Image.Image:
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((6, 4, 26, 28), fill=(200, 30, 20, 255))
    d.rectangle((10, 8, 22, 24), fill=(0, 0, 0, 0))
    return im


def chevron() -> Image.Image:
    im = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(10, 6), (34, 24), (10, 42), (16, 42), (40, 24), (16, 6)], fill=(110, 20, 180, 255))
    return im


expect("solid square is a stamp", bool(stamp_reason(solid_square())))
expect("filled disc is a stamp", bool(stamp_reason(filled_disc())))
expect("letter tile is a stamp", bool(stamp_reason(letter_a())))
expect("chevron is a mark", stamp_reason(chevron()) == "")

named_drop = [
    "1password.com.png",
    "1spatial.com.png",
    "abnormal.ai.png",
    "abridge.com.png",
    "acronis.com.png",
    "aciworldwide.com.png",
    "admicom.fi.png",
]
named_keep = [
    "accenture.com.png",
    "3dsystems.com.png",
    "a10networks.com.png",
]
mark_stamps = [
    "enx.com.png",
    "kisa.or.kr.png",
    "imda.gov.sg.png",
    "cyberab.org.png",
]
for name in named_drop:
    path = FAV / name
    if path.exists():
        im = Image.open(path)
        expect(f"{name} is rejected", bool(stamp_reason(im)))
    else:
        expect(f"{name} already name-only", True)
for name in named_keep:
    path = FAV / name
    expect(f"{name} still on disk", path.exists())
    expect(f"{name} is a mark", stamp_reason(Image.open(path)) == "")
for name in mark_stamps:
    path = FAV / name
    if path.exists():
        expect(f"{name} mark is rejected", bool(stamp_reason(Image.open(path))))
    else:
        expect(f"{name} mark is name-only", True)

print("ok stamp filter")
