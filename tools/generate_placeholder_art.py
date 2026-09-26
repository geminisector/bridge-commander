"""Generate the 128x128 placeholder hull art.

The bundle ships one action image (``img/action/<stem>.png``) and one VDU scan
(``img/vdu/<stem>-vdu.gif``) per hull in ``bridge/resources/bridge_ship_art.json``.
The stem is the hull id for every hull except ``home``, which is named
``friendly-cruiser`` for the art (the one id the renaming kept for
compatibility).  The images are original placeholders, not screenshots or
third-party artwork, and every drawn label is derived from the neutral hull
name, so no external universe name is baked in.

Regenerate from the repository root::

    python tools/generate_placeholder_art.py

The output is deterministic: the same hull id always paints the same
silhouette, starfield and blip pattern.  Terrain art (``asteroid``, ``cloud``,
``debris``) and the unknown-contact silhouette are generic and left alone.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W = H = 128
REPO = Path(__file__).resolve().parents[1]
ACTION_DIR = REPO / "bridge" / "img" / "action"
VDU_DIR = REPO / "bridge" / "img" / "vdu"

FRIENDLY = (0, 240, 255)
ENEMY = (255, 96, 96)
VDU_GREEN = (72, 255, 132)

_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

# hull id, art stem, banner label, accent, beam fraction, length fraction
HULLS: list[tuple[str, str, str, tuple[int, int, int], float, float]] = [
    ("home", "friendly-cruiser", "FRIENDLY CRUISER", FRIENDLY, 0.84, 0.80),
    ("friendly-corvette", "friendly-corvette", "FRIENDLY CORVETTE", FRIENDLY, 0.58, 0.92),
    ("friendly-transport", "friendly-transport", "FRIENDLY TRANSPORT", FRIENDLY, 0.76, 0.74),
    ("friendly-prospector", "friendly-prospector", "FRIENDLY PROSPECTOR", FRIENDLY, 0.64, 0.68),
    ("friendly-freighter", "friendly-freighter", "FRIENDLY FREIGHTER", FRIENDLY, 0.94, 0.56),
    ("friendly-carrier", "friendly-carrier", "FRIENDLY CARRIER", FRIENDLY, 1.00, 0.86),
    ("friendly-light-cruiser", "friendly-light-cruiser", "FRIENDLY LIGHT CRUISER", FRIENDLY, 0.80, 0.84),
    ("enemy-escort", "enemy-escort", "ENEMY ESCORT", ENEMY, 0.62, 0.94),
    ("enemy-fighter", "enemy-fighter", "ENEMY FIGHTER", ENEMY, 0.50, 0.98),
    ("enemy-medium-fighter", "enemy-medium-fighter", "ENEMY MEDIUM FIGHTER", ENEMY, 0.58, 0.96),
    ("enemy-heavy-fighter", "enemy-heavy-fighter", "ENEMY HEAVY FIGHTER", ENEMY, 0.70, 0.90),
    ("enemy-bomber", "enemy-bomber", "ENEMY BOMBER", ENEMY, 0.72, 0.88),
    ("enemy-destroyer", "enemy-destroyer", "ENEMY DESTROYER", ENEMY, 0.76, 0.92),
    ("enemy-cruiser", "enemy-cruiser", "ENEMY CRUISER", ENEMY, 0.84, 0.86),
    ("enemy-heavy-transport", "enemy-heavy-transport", "ENEMY HEAVY TRANSPORT", ENEMY, 0.90, 0.66),
]


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _fit(text: str, path: str, max_width: int, start: int = 14) -> ImageFont.FreeTypeFont:
    """Largest font at or below ``start`` whose text fits ``max_width``."""
    for size in range(start, 5, -1):
        font = _font(path, size)
        if font.getlength(text) <= max_width:
            return font
    return _font(path, 6)


def _seed(hull_id: str) -> int:
    return int.from_bytes(hull_id.encode("utf-8")[:4].ljust(4, b"\0"), "big")


def _background(draw: ImageDraw.ImageDraw) -> None:
    for y in range(H):
        t = y / (H - 1)
        draw.line(
            [(0, y), (W, y)],
            fill=(int(9 + 7 * t), int(11 + 8 * t), int(26 + 16 * t)),
        )
    for x in range(0, W, 16):
        draw.line([(x, 0), (x, H)], fill=(17, 23, 43))
    for y in range(0, H, 16):
        draw.line([(0, y), (W, y)], fill=(17, 23, 43))


def _frame(draw: ImageDraw.ImageDraw, accent: tuple[int, int, int]) -> None:
    draw.rounded_rectangle([(2, 2), (W - 3, H - 3)], radius=9, outline=accent, width=1)
    for x, y, dx, dy in (
        (5, 5, 1, 1),
        (W - 5, 5, -1, 1),
        (5, H - 5, 1, -1),
        (W - 5, H - 5, -1, -1),
    ):
        draw.line([(x, y), (x + dx * 12, y)], fill=accent, width=2)
        draw.line([(x, y), (x, y + dy * 12)], fill=accent, width=2)


def _tag(draw: ImageDraw.ImageDraw, index: int, accent: tuple[int, int, int]) -> None:
    draw.rounded_rectangle([(7, 6), (48, 18)], radius=4, outline=accent, width=1)
    font = _font(_FONT_MONO, 8)
    draw.text((27, 12), f"HULL {index:02d}", font=font, fill=accent, anchor="mm")


def _banner(
    draw: ImageDraw.ImageDraw,
    label: str,
    accent: tuple[int, int, int],
    text_fill: tuple[int, int, int],
    fill: tuple[int, int, int],
) -> None:
    draw.rounded_rectangle([(6, 101), (W - 7, H - 6)], radius=6, fill=fill, outline=accent, width=1)
    font = _fit(label, _FONT_BOLD, W - 26, start=13)
    draw.text(((W - 1) / 2, 112), label, font=font, fill=text_fill, anchor="mm")


def _silhouette(
    draw: ImageDraw.ImageDraw,
    hull_id: str,
    accent: tuple[int, int, int],
    beam: float,
    length: float,
) -> None:
    rng = random.Random(_seed(hull_id))
    cx, cy = W / 2, 55.0
    half_l = 30.0 * length
    half_b = 34.0 * beam
    sweep = 0.10 + 0.22 * rng.random()
    tail = 0.20 + 0.16 * rng.random()
    waist = 0.30 + 0.18 * rng.random()
    points = [
        (cx, cy - half_l),
        (cx + half_b * 0.16, cy - half_l * 0.42),
        (cx + half_b * (0.86 + 0.14 * rng.random()), cy - half_l * sweep),
        (cx + half_b * waist, cy + half_l * 0.30),
        (cx + half_b * 0.30, cy + half_l * (0.62 + tail * 0.3)),
        (cx + half_b * 0.22, cy + half_l),
        (cx - half_b * 0.22, cy + half_l),
        (cx - half_b * 0.30, cy + half_l * (0.62 + tail * 0.3)),
        (cx - half_b * waist, cy + half_l * 0.30),
        (cx - half_b * (0.86 + 0.14 * rng.random()), cy - half_l * sweep),
        (cx - half_b * 0.16, cy - half_l * 0.42),
    ]
    dark = tuple(int(c * 0.18) for c in accent)
    draw.polygon(points, fill=dark, outline=accent)
    draw.line([(cx, cy - half_l + 4), (cx, cy + half_l - 3)], fill=accent)
    draw.ellipse([(cx - 3, cy - 3), (cx + 3, cy + 3)], outline=accent)
    for sign in (-1, 1):
        draw.line(
            [
                (cx + sign * half_b * 0.24, cy + half_l * 0.7),
                (cx + sign * half_b * 0.52, cy + half_l * 1.18),
            ],
            fill=accent,
            width=2,
        )


def _action_image(index: int, hull: tuple[str, str, str, tuple[int, int, int], float, float]) -> Image.Image:
    hull_id, _stem, label, accent, beam, length = hull
    img = Image.new("RGB", (W, H), (9, 11, 26))
    draw = ImageDraw.Draw(img)
    _background(draw)
    rng = random.Random(_seed(hull_id) ^ 0x5A5A)
    for _ in range(48):
        x, y = rng.randrange(4, W - 4), rng.randrange(4, H - 4)
        v = rng.choice((70, 110, 160, 215))
        draw.point((x, y), fill=(v, v, v))
    _frame(draw, accent)
    _tag(draw, index, accent)
    _silhouette(draw, hull_id, accent, beam, length)
    draw.text((10, 92), "HULL SIGNATURE", font=_font(_FONT_MONO, 8), fill=accent)
    _banner(draw, label, accent, (238, 242, 252), (7, 9, 20))
    return img


def _vdu_image(index: int, hull: tuple[str, str, str, tuple[int, int, int], float, float]) -> Image.Image:
    hull_id, _stem, label, _accent, _beam, _length = hull
    img = Image.new("RGB", (W, H), (1, 9, 4))
    draw = ImageDraw.Draw(img)
    for x in range(0, W, 8):
        draw.line([(x, 0), (x, H)], fill=(7, 29, 14))
    for y in range(0, H, 8):
        draw.line([(0, y), (W, y)], fill=(7, 29, 14))
    cx, cy = W / 2, 56
    rng = random.Random(_seed(hull_id) ^ 0x1234)
    angle = rng.random() * math.tau
    sweep = [
        (cx, cy),
        (cx + math.cos(angle) * 62, cy + math.sin(angle) * 62),
        (cx + math.cos(angle + 0.5) * 62, cy + math.sin(angle + 0.5) * 62),
    ]
    draw.polygon(sweep, fill=(10, 58, 26))
    for radius in (16, 30, 44, 56):
        draw.ellipse([(cx - radius, cy - radius), (cx + radius, cy + radius)], outline=(16, 74, 34))
    draw.line([(cx, 6), (cx, 100)], fill=(16, 74, 34))
    draw.line([(6, cy), (W - 6, cy)], fill=(16, 74, 34))
    draw.line([(cx, cy), (cx + math.cos(angle) * 60, cy + math.sin(angle) * 60)], fill=VDU_GREEN)
    for _ in range(6):
        bx, by = rng.randrange(22, W - 22), rng.randrange(14, 96)
        draw.rectangle([(bx, by), (bx + 2, by + 2)], outline=(40, 180, 90))
    draw.polygon([(cx, cy - 6), (cx - 5, cy + 5), (cx + 5, cy + 5)], fill=VDU_GREEN)
    draw.text((8, 8), "SCAN 0108", font=_font(_FONT_MONO, 9), fill=VDU_GREEN)
    _banner(draw, label, VDU_GREEN, (170, 255, 200), (3, 16, 8))
    return img


def main() -> None:
    ACTION_DIR.mkdir(parents=True, exist_ok=True)
    VDU_DIR.mkdir(parents=True, exist_ok=True)
    for index, hull in enumerate(HULLS, start=1):
        stem = hull[1]
        action = _action_image(index, hull)
        action.save(ACTION_DIR / f"{stem}.png")
        vdu = _vdu_image(index, hull).quantize(colors=64)
        vdu.save(VDU_DIR / f"{stem}-vdu.gif")
    print(f"wrote {len(HULLS)} action images and {len(HULLS)} VDU scans")


if __name__ == "__main__":
    main()
