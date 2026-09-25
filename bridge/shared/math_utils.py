"""CAPTAIN shared math helpers.

Direct port of ``packages/shared/src/math.ts``.  Angles are degrees; positions
are kliks on the local 3D plane.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .types import Vec

TAU = math.pi * 2


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def deg_to_rad(d: float) -> float:
    return (d * math.pi) / 180


def rad_to_deg(r: float) -> float:
    return (r * 180) / math.pi


def bearing(a: Vec, b: Vec) -> float:
    """Compass bearing (000-360, 000 = North, clockwise) on the ecliptic plane."""
    dx = b.x - a.x
    dy = b.y - a.y
    brg = rad_to_deg(math.atan2(dx, dy))
    return (brg + 360) % 360


def elevation(a: Vec, b: Vec) -> float:
    """Elevation angle (-90..+90) of b above a's plane along the ecliptic."""
    flat = flat_dist(a, b)
    return rad_to_deg(math.atan2(b.z - a.z, flat or 1))


def dist(a: Vec, b: Vec) -> float:
    """True 3D range between two points."""
    dx = b.x - a.x
    dy = b.y - a.y
    dz = b.z - a.z
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def flat_dist(a: Vec, b: Vec) -> float:
    dx = b.x - a.x
    dy = b.y - a.y
    return math.sqrt(dx * dx + dy * dy)


def range_rate(a: Vec, va: Vec, b: Vec, vb: Vec) -> float:
    """Doppler range-rate: positive = closing, negative = opening."""
    d = dist(a, b)
    if d < 1e-6:
        return 0.0
    los = {"x": (b.x - a.x) / d, "y": (b.y - a.y) / d, "z": (b.z - a.z) / d}
    rel = {"x": vb.x - va.x, "y": vb.y - va.y, "z": vb.z - va.z}
    return -(rel["x"] * los["x"] + rel["y"] * los["y"] + rel["z"] * los["z"])


def moved(p: Vec, heading: float, speed: float, hours: float) -> Vec:
    """Step along a course (compass degrees) at speed in kps over a watch hour.

    The kps->klik conversion is a game unit shared with the crew's own movement
    (``KLIK_PER_KPS_HOUR``), so traffic and the player ship cover ground at the
    same rate on the 0-100 dial.
    """
    from .constants import KLIK_PER_KPS_HOUR

    d = speed * hours * KLIK_PER_KPS_HOUR
    rad = deg_to_rad(heading)
    return Vec(x=p.x + math.sin(rad) * d, y=p.y + math.cos(rad) * d, z=p.z)


def _to_uint32(x: float) -> int:
    """JavaScript ``ToUint32`` (used by ``>>> 0``)."""
    if not math.isfinite(x):
        return 0
    return int(x) & 0xFFFFFFFF


def _to_int32(x: float) -> int:
    """JavaScript ``ToInt32``: truncate toward zero, wrap to signed 32-bit."""
    if not math.isfinite(x):
        return 0
    m = int(x) & 0xFFFFFFFF
    return m - 0x100000000 if m >= 0x80000000 else m


def _js_xor_ushr(h: int, shift: int) -> int:
    """JavaScript ``h ^ (h >>> shift)`` on a signed 32-bit ``h``."""
    return h ^ ((h & 0xFFFFFFFF) >> shift)


def hash_random(seed_a: float, seed_b: float, salt: float = 0) -> float:
    """Deterministic pseudo random in [0,1) from a seed pair.

    Faithful to the JavaScript ``hashRandom`` including its float64 arithmetic:
    the multiplications are performed as IEEE-754 doubles (so they round at
    2**53 before ``ToInt32`` truncates), which the plain "mask to 32 bits"
    recipe in MIGRATION.md does *not* reproduce.  Seeds may be floats because
    the engine passes ``state.clock``.
    """
    h = (
        _to_int32(seed_a * 73856093)
        ^ _to_int32(seed_b * 19349663)
        ^ _to_int32(salt * 83492791)
    )
    h = _to_int32(float(_js_xor_ushr(h, 15)) * 2246822519)
    h = _to_int32(float(_js_xor_ushr(h, 13)) * 3266489917)
    h = _js_xor_ushr(h, 16)
    return (_to_uint32(float(h)) % 100000) / 100000


def noise(seed: float, magnitude: float) -> float:
    """Gaussian-ish noise composed of two dice for better distribution."""
    u = (hash_random(seed, 1) + hash_random(seed, 2)) / 2
    return (u - 0.5) * 2 * magnitude


def wrap_bearing(b: float) -> float:
    return ((b % 360) + 360) % 360


def bearing_diff(a: float, b: float) -> float:
    d = wrap_bearing(a) - wrap_bearing(b)
    if d > 180:
        d -= 360
    if d < -180:
        d += 360
    return d


def format_clock(minute: float) -> str:
    m = int(math.floor(minute)) % (24 * 60)
    day = int(math.floor(minute / (24 * 60))) + 1
    hh = f"{int(math.floor(m / 60)):02d}"
    mm = f"{m % 60:02d}"
    return f"Day {day} {hh}:{mm}"


@dataclass
class Circle:
    center: Vec
    radius: float


def segments_intersect(a: Vec, b: Vec, c: Vec, d: Vec) -> bool:
    """Whether 2D segments ``a-b`` and ``c-d`` cross (shared endpoints count)."""
    def orient(p: Vec, q: Vec, r: Vec) -> float:
        return (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x)

    def on_segment(p: Vec, q: Vec, r: Vec) -> bool:
        return (
            min(p.x, r.x) <= q.x <= max(p.x, r.x)
            and min(p.y, r.y) <= q.y <= max(p.y, r.y)
        )

    o1, o2 = orient(a, b, c), orient(a, b, d)
    o3, o4 = orient(c, d, a), orient(c, d, b)
    if ((o1 > 0) != (o2 > 0)) and ((o3 > 0) != (o4 > 0)):
        return True
    if abs(o1) < 1e-9 and on_segment(a, c, b):
        return True
    if abs(o2) < 1e-9 and on_segment(a, d, b):
        return True
    if abs(o3) < 1e-9 and on_segment(c, a, d):
        return True
    if abs(o4) < 1e-9 and on_segment(c, b, d):
        return True
    return False


def in_circle(p: Vec, c: Circle) -> bool:
    return dist(p, c.center) <= c.radius
