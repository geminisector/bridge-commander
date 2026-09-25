"""CAPTAIN ship catalog.

Every hull the GM can assign to a scenario.  The three sensor modes read
different properties off a hull, which is the whole point of letting the admin
dictate the ship:

- **passive** listens to ``emission`` (masked by ``stealth``);
- **active** radar sees ``profile`` (radar cross-section);
- **towed gravidar** feels ``massKt``.

Every hull also carries a **sensor frequency profile** (``bands``) — a barcode of
per-band amplitudes that passive listening paints in.  No two hulls share one.

All hulls run on the shared 0-100 kps dial: 15 silent running, 60 cruise,
100 flank (see ``SILENT_KPS``/``CRUISE_KPS``/``FLANK_KPS``).
"""

from __future__ import annotations

import json

from ..paths import asset_root, resource_path
from .shipyard import HULLS

from .constants import CRUISE_KPS, FLANK_KPS, FREQ_BANDS
from .math_utils import hash_random
from .types import AdminShipBrief, ContactType, ShipClass


def ship_bands(ship_id: str) -> list[float]:
    """Deterministic barcode-like frequency profile for a hull id."""
    seed = sum(ord(ch) for ch in ship_id) or 7
    bands: list[float] = []
    for i in range(FREQ_BANDS):
        v = hash_random(seed, i + 1)
        # Spiky: quiet gaps, loud ticks, a couple of strong carriers.
        bands.append(round(v if v > 0.3 else v * 0.25, 3))
    return bands


# ---------------------------------------------------------------------------
# Ship art — resolved from resources/bridge_ship_art.json and the img tree
# ---------------------------------------------------------------------------

_HULL_STATS: dict[str, dict[str, float]] = {
    "home": {"shieldFore": 300, "shieldAft": 200, "shieldRefresh": 150, "armorFore": 35, "armorAft": 25, "armorPort": 5, "armorStarboard": 5, "body": 330, "fuelCapacity": 6},
    "venture-corvette": {"shieldFore": 25, "shieldAft": 25, "shieldRefresh": 15, "armorFore": 15, "armorAft": 15, "armorPort": 5, "armorStarboard": 5, "body": 175, "fuelCapacity": 5},
    "drayman-transport": {"shieldFore": 17, "shieldAft": 15, "shieldRefresh": 9.6, "armorFore": 10, "armorAft": 10, "armorPort": 5, "armorStarboard": 5, "body": 110, "fuelCapacity": 6},
    "tarsus-prospector": {"shieldFore": 6, "shieldAft": 6, "shieldRefresh": 3.6, "armorFore": 8, "armorAft": 8, "armorPort": 6.5, "armorStarboard": 6.5, "body": 30, "fuelCapacity": 3},
    "longhaul-freighter": {"shieldFore": 5, "shieldAft": 5, "shieldRefresh": 4.8, "armorFore": 6, "armorAft": 8, "armorPort": 8, "armorStarboard": 8, "body": 22, "fuelCapacity": 1},
    "kamekh-escort": {"shieldFore": 30, "shieldAft": 30, "shieldRefresh": 18, "armorFore": 20, "armorAft": 20, "armorPort": 5, "armorStarboard": 5, "body": 175, "fuelCapacity": 6},
    "salthi-fighter": {"shieldFore": 3.5, "shieldAft": 3.5, "shieldRefresh": 2.1, "armorFore": 3, "armorAft": 2, "armorPort": 1.5, "armorStarboard": 1.5, "body": 15, "fuelCapacity": 2},
    "grikath-fighter": {"shieldFore": 11, "shieldAft": 11, "shieldRefresh": 6.6, "armorFore": 16, "armorAft": 16, "armorPort": 15, "armorStarboard": 15, "body": 40, "fuelCapacity": 1},
    "ralatha-destroyer": {"shieldFore": 400, "shieldAft": 400, "shieldRefresh": 240, "armorFore": 50, "armorAft": 50, "armorPort": 5, "armorStarboard": 5, "body": 240, "fuelCapacity": 6},
    "fralthi-carrier": {"shieldFore": 300, "shieldAft": 200, "shieldRefresh": 150, "armorFore": 35, "armorAft": 25, "armorPort": 5, "armorStarboard": 5, "body": 330, "fuelCapacity": 6},
    "dorkathi-transport": {"shieldFore": 19, "shieldAft": 19, "shieldRefresh": 11.4, "armorFore": 17, "armorAft": 17, "armorPort": 5, "armorStarboard": 5, "body": 130, "fuelCapacity": 5},
    "bengal-carrier": {"shieldFore": 500, "shieldAft": 500, "shieldRefresh": 300, "armorFore": 60, "armorAft": 60, "armorPort": 5, "armorStarboard": 5, "body": 400, "fuelCapacity": 6},
    "bristol-cruiser": {"shieldFore": 200, "shieldAft": 200, "shieldRefresh": 135, "armorFore": 18, "armorAft": 18, "armorPort": 5, "armorStarboard": 5, "body": 220, "fuelCapacity": 5},
    "raptor-medium": {"shieldFore": 9, "shieldAft": 9, "shieldRefresh": 5.4, "armorFore": 10, "armorAft": 10, "armorPort": 8, "armorStarboard": 8, "body": 40, "fuelCapacity": 1},
    "broadsword-bomber": {"shieldFore": 30, "shieldAft": 30, "shieldRefresh": 18, "armorFore": 25, "armorAft": 25, "armorPort": 23, "armorStarboard": 23, "body": 50, "fuelCapacity": 1},
}

# Used only when the DB is unavailable.  These are the DB's own filenames.
_FALLBACK_ACTION: dict[str, str] = {
    "home": "fralthi.png",
    "venture-corvette": "venture.png",
    "drayman-transport": "drayman.png",
    "tarsus-prospector": "tarsus.png",
    "longhaul-freighter": "longhaul.png",
    "kamekh-escort": "kamekh.png",
    "salthi-fighter": "salthi.png",
    "grikath-fighter": "grikath.png",
    "ralatha-destroyer": "ralatha.png",
    "fralthi-carrier": "fralthi.png",
    "dorkathi-transport": "dorkathi.png",
    "bengal-carrier": "bengal.png",
    "bristol-cruiser": "bristol.png",
    "raptor-medium": "raptor.png",
    "broadsword-bomber": "broadsword.png",
}

# Terrain contacts: the DB has asteroid/debris rows; the rest reuse the closest.
TERRAIN_IMAGES: dict[ContactType, str] = {
    "asteroid": "/img/action/asteroid.png",
    "debris": "/img/action/debris.png",
    "nebula": "/img/action/cloud.png",
    "dust": "/img/action/cloud.png",
    "ice": "/img/action/asteroid.png",
}


def _as_url(raw: str | None) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    return raw if raw.startswith("/") else "/" + raw


def _url_exists(url: str) -> bool:
    if not url.startswith("/img/"):
        return False
    return (asset_root() / url.removeprefix("/img/")).is_file()


def _candidate_urls(url: str) -> list[str]:
    """The URL plus same-basename siblings with a swapped extension.

    The DB is not always in step with the files on disk (e.g. it lists
    ``longhaul-vdu.gif`` while the tree holds ``longhaul-vdu.png``).
    """
    url = _as_url(url)
    if not url:
        return []
    base, _, ext = url.rpartition(".")
    if not base:
        return [url]
    candidates = [url]
    for other in ("png", "gif", "jpg", "jpeg", "webp"):
        alt = f"{base}.{other}"
        if alt != url:
            candidates.append(alt)
    return candidates


def _first_existing(url: str) -> str:
    for candidate in _candidate_urls(url):
        if _url_exists(candidate):
            return candidate
    return ""


def resolve_hull_stats() -> dict[str, dict[str, float]]:
    return {hull_id: dict(stats) for hull_id, stats in _HULL_STATS.items()}


def _load_ship_art_overrides() -> dict[str, tuple[str, str]]:
    """Canonical ``hull id -> (action, vdu)`` from ``bridge_ship_art.json``.

    The data file is authoritative for hulls it names; anything it does not
    cover falls through to the per-hull filename.  A malformed or missing file
    is not fatal.
    """
    path = resource_path("bridge_ship_art.json")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    overrides: dict[str, tuple[str, str]] = {}
    for hull_id, entry in raw.items():
        if hull_id.startswith("_") or not isinstance(entry, dict):
            continue
        overrides[str(hull_id)] = (
            str(entry.get("action") or ""),
            str(entry.get("vdu") or ""),
        )
    return overrides


def resolve_ship_art() -> dict[str, tuple[str, str]]:
    """``hull id -> (image_url, vdu_url)``, verified against the local img tree.

    Precedence: the canonical ``bridge_ship_art.json`` override, then the
    per-hull fallback filename.  The action art is preferred; when it is not on
    disk the **VDU image is used in its place**, so ``image`` is always
    something the UI can render.  An empty string means nothing was found and
    the caller should show a generic silhouette.
    """
    overrides = _load_ship_art_overrides()
    art: dict[str, tuple[str, str]] = {}
    for hull in SHIP_CLASSES.values():
        action = vdu = ""
        override = overrides.get(hull.id)
        if override is not None:
            action = _first_existing(override[0])
            vdu = _first_existing(override[1])
        if not action:
            fallback = _FALLBACK_ACTION.get(hull.id, "")
            if fallback:
                action = _first_existing(f"/img/action/{fallback}")
        # Fall back to the VDU when the main (action) art is unavailable.
        if not action and vdu:
            action = vdu
        art[hull.id] = (action, vdu)
    return art


def audit_ship_art() -> list[str]:
    """Findings about the resolved art map.

    ``ERROR:`` lines are failures (a hull with no art, or art pointing at a file
    that is not on disk).  ``INFO:`` lines are decisions to keep on purpose, such
    as two hulls sharing a parent class's art.  Run this in tests and at startup.
    """
    findings: list[str] = []
    by_action: dict[str, list[str]] = {}
    for hull in SHIP_CLASSES.values():
        action, vdu = SHIP_ART.get(hull.id, ("", ""))
        if not action:
            findings.append(f"ERROR: {hull.id}: no art resolved")
            continue
        if not _url_exists(action):
            findings.append(f"ERROR: {hull.id}: action art missing on disk: {action}")
        if vdu and not _url_exists(vdu):
            findings.append(f"ERROR: {hull.id}: vdu art missing on disk: {vdu}")
        if vdu and action == vdu:
            findings.append(
                f"INFO: {hull.id}: no action art; using the VDU image ({vdu})"
            )
        by_action.setdefault(action, []).append(hull.id)
    for url, ids in by_action.items():
        if len(ids) > 1:
            findings.append(f"INFO: shared action art {url}: {', '.join(sorted(ids))}")
    return findings



def ship_art(ship_id: str | None) -> tuple[str, str]:
    """``(action_url, vdu_url)`` for a hull id."""
    return SHIP_ART.get(ship_id or "", ("", ""))


SHIP_CLASSES: dict[str, ShipClass] = {
    "home": ShipClass(
        id="home",
        name="Fralthi-Class Cruiser",
        role="Home Carrier",
        contactType="carrier",
        massKt=28.8,
        profile=0.45,
        stealth=0.55,
        emission=0.3,
        sensorQuality=0.92,
        cruiseSpeed=CRUISE_KPS,
        maxSpeed=FLANK_KPS,
        crew=280,
        blurb="Fast, quiet and sensor-rich. The tripwire hull: see first, be seen last.",
    ),
    "venture-corvette": ShipClass(
        id="venture-corvette",
        name="Venture-class corvette",
        role="Corvette",
        contactType="escort",
        massKt=6.5,
        profile=0.6,
        stealth=0.3,
        emission=0.5,
        sensorQuality=0.8,
        cruiseSpeed=CRUISE_KPS,
        maxSpeed=FLANK_KPS,
        crew=60,
        blurb="General-purpose escort. Loud enough to be found, tough enough to leave.",
    ),
    "drayman-transport": ShipClass(
        id="drayman-transport",
        name="Drayman-class transport",
        role="Transport",
        contactType="freighter",
        massKt=18,
        profile=0.8,
        stealth=0.1,
        emission=0.55,
        sensorQuality=0.5,
        cruiseSpeed=CRUISE_KPS,
        maxSpeed=FLANK_KPS,
        crew=24,
        blurb="Slow, broad and radiating. Passive will find it before it finds you.",
    ),
    "tarsus-prospector": ShipClass(
        id="tarsus-prospector",
        name="Tarsus-class prospector",
        role="Prospector",
        contactType="prospector",
        massKt=2.5,
        profile=0.5,
        stealth=0.2,
        emission=0.6,
        sensorQuality=0.6,
        cruiseSpeed=CRUISE_KPS,
        maxSpeed=FLANK_KPS,
        crew=4,
        blurb="Mining rig with a hot plant. Small, but it chatters on the grill.",
    ),
    "longhaul-freighter": ShipClass(
        id="longhaul-freighter",
        name="Longhaul-class freighter",
        role="Freighter",
        contactType="freighter",
        massKt=2,
        profile=0.85,
        stealth=0.05,
        emission=0.7,
        sensorQuality=0.45,
        cruiseSpeed=CRUISE_KPS,
        maxSpeed=FLANK_KPS,
        crew=18,
        blurb="A city block of cargo with engines. Visible on every sensor ever built.",
    ),
    "kamekh-escort": ShipClass(
        id="kamekh-escort",
        name="KAMEKH-class corvette",
        role="Kilrathi corvette",
        contactType="escort",
        massKt=12,
        profile=0.5,
        stealth=0.35,
        emission=0.45,
        sensorQuality=0.8,
        cruiseSpeed=CRUISE_KPS,
        maxSpeed=FLANK_KPS,
        crew=120,
        blurb="Kilrathi escort. Runs dark when hunting; hot when it wants to be found.",
    ),
    "salthi-fighter": ShipClass(
        id="salthi-fighter",
        name="Salthi-class light fighter",
        role="Fighter",
        contactType="fighter",
        massKt=0.9,
        profile=0.22,
        stealth=0.65,
        emission=0.75,
        sensorQuality=0.7,
        cruiseSpeed=CRUISE_KPS,
        maxSpeed=FLANK_KPS,
        crew=1,
        blurb="Tiny radar cross-section, huge afterburner. Active barely sees it; passive hears it scream.",
    ),
    "grikath-fighter": ShipClass(
        id="grikath-fighter",
        name="GRIKATH-class heavy fighter",
        role="Kilrathi heavy fighter",
        contactType="fighter",
        massKt=2.4,
        profile=0.38,
        stealth=0.45,
        emission=0.65,
        sensorQuality=0.75,
        cruiseSpeed=CRUISE_KPS,
        maxSpeed=FLANK_KPS,
        crew=2,
        blurb="Kilrathi heavy fighter. Patient hunter: runs quiet, then pounces.",
    ),
    "ralatha-destroyer": ShipClass(
        id="ralatha-destroyer",
        name="RALATHA-class destroyer",
        role="Destroyer",
        contactType="capship",
        massKt=200,
        profile=0.7,
        stealth=0.3,
        emission=0.55,
        sensorQuality=0.85,
        cruiseSpeed=CRUISE_KPS,
        maxSpeed=FLANK_KPS,
        crew=600,
        blurb="A wall of armour and emitters. Gravidar reads it clear across the basin.",
    ),
    "fralthi-carrier": ShipClass(
        id="fralthi-carrier",
        name="FRALTHI-class fleet carrier",
        role="Fleet carrier",
        contactType="carrier",
        massKt=320,
        profile=0.95,
        stealth=0.25,
        emission=0.4,
        sensorQuality=0.9,
        cruiseSpeed=CRUISE_KPS,
        maxSpeed=FLANK_KPS,
        crew=1400,
        blurb="The big quiet one: enormous mass, disciplined emissions. Find it by patience.",
    ),
    "dorkathi-transport": ShipClass(
        id="dorkathi-transport",
        name="DORKATHI-class transport",
        role="Kilrathi transport",
        contactType="freighter",
        massKt=120,
        profile=0.8,
        stealth=0.2,
        emission=0.5,
        sensorQuality=0.55,
        cruiseSpeed=CRUISE_KPS,
        maxSpeed=FLANK_KPS,
        crew=300,
        blurb="Fleet resupply hull. Big gravidar arc, ordinary emissions.",
    ),
}

# Hulls from the curated catalog that the bridge does not already define.
for _hull_id, _entry in HULLS.items():
    if _hull_id in SHIP_CLASSES or not _entry.get("shipType"):
        continue
    _art = ("", "")  # filled by the art pass below, once SHIP_ART resolves
    SHIP_CLASSES[_hull_id] = ShipClass(
        id=_hull_id,
        name=str(_entry.get("name") or _hull_id.replace("-", " ").title()),
        role=str(_entry.get("role") or "Warship"),
        contactType=_entry.get("contactType", "capship"),
        massKt=float(_entry.get("massKt") or 100.0),
        profile=float(_entry.get("profile") or 0.5),
        stealth=float(_entry.get("stealth") or 0.4),
        emission=float(_entry.get("emission") or 0.5),
        sensorQuality=float(_entry.get("sensorQuality") or 0.6),
        cruiseSpeed=CRUISE_KPS,
        maxSpeed=FLANK_KPS,
        crew=int(_entry.get("crew") or 40),
        blurb=str(_entry.get("blurb") or ""),
        image=_art[0],
        vdu=_art[1],
    )

for _hull in SHIP_CLASSES.values():
    _hull.bands = ship_bands(_hull.id)

# Resolve the art once, from the ships DB when it is present.
SHIP_ART: dict[str, tuple[str, str]] = resolve_ship_art()
for _hull in SHIP_CLASSES.values():
    _action, _vdu = SHIP_ART.get(_hull.id, ("", ""))
    _hull.image = _action
    _hull.vdu = _vdu

# Resolve the hull defences (per-arc shields/armour, refresh, body).
HULL_STATS: dict[str, dict[str, float]] = resolve_hull_stats()
for _hull in SHIP_CLASSES.values():
    for _field, _value in HULL_STATS.get(_hull.id, {}).items():
        setattr(_hull, _field, float(_value))

DEFAULT_SHIP_CLASS = "home"

# Registry/proper names used when a hull is flown by the crew.
SHIP_NAMES: dict[str, str] = {
    "home": "TCS Rakshasha",
    "venture-corvette": "TCS Venture",
    "drayman-transport": "MV Grey Drayman",
    "tarsus-prospector": "MV Lucky Tarsus",
    "longhaul-freighter": "MV Long Haul",
    "kamekh-escort": "KIS Bloodfang",
    "salthi-fighter": "KIS Sting",
    "grikath-fighter": "KIS Grikath",
    "ralatha-destroyer": "KIS Ralatha",
    "fralthi-carrier": "KIS Fury",
    "dorkathi-transport": "KIS Pack Mule",
    "bengal-carrier": "CSV Bengal",
    "bristol-cruiser": "TCS Bristol",
    "raptor-medium": "KIS Raptor",
    "broadsword-bomber": "KIS Broadsword",
}

# When a campaign or GM template names no hull, derive one from its contact type
# so the sensor physics still has real numbers to work with.
DEFAULT_BY_TYPE: dict[ContactType, str] = {
    "unknown": DEFAULT_SHIP_CLASS,
    "prospector": "tarsus-prospector",
    "freighter": "drayman-transport",
    "liner": "drayman-transport",
    "escort": "venture-corvette",
    "capship": "ralatha-destroyer",
    "fighter": "salthi-fighter",
    "carrier": "fralthi-carrier",
    "asteroid": "",
    "nebula": "",
    "debris": "",
    "dust": "",
    "ice": "",
}


def ship_name(ship_id: str | None) -> str:
    """The proper name of the hull when the crew is flying it."""
    return SHIP_NAMES.get(ship_id or "", SHIP_NAMES[DEFAULT_SHIP_CLASS])


def ship_class(ship_id: str | None) -> ShipClass:
    """Look up a hull, falling back to the crew's home hull."""
    if ship_id and ship_id in SHIP_CLASSES:
        return SHIP_CLASSES[ship_id]
    return SHIP_CLASSES[DEFAULT_SHIP_CLASS]


def ship_for_type(contact_type: ContactType, ship_id: str | None = None) -> ShipClass:
    """Resolve a hull for a contact, preferring the explicit id."""
    if ship_id and ship_id in SHIP_CLASSES:
        return SHIP_CLASSES[ship_id]
    fallback = DEFAULT_BY_TYPE.get(contact_type, DEFAULT_SHIP_CLASS)
    return SHIP_CLASSES.get(fallback, SHIP_CLASSES[DEFAULT_SHIP_CLASS])


def ship_briefs() -> list[AdminShipBrief]:
    return [
        AdminShipBrief(
            id=s.id,
            name=s.name,
            role=s.role,
            contactType=s.contactType,
            massKt=s.massKt,
            profile=s.profile,
            stealth=s.stealth,
            emission=s.emission,
            sensorQuality=s.sensorQuality,
        )
        for s in SHIP_CLASSES.values()
    ]


__all__ = [
    "SHIP_CLASSES",
    "SHIP_ART",
    "TERRAIN_IMAGES",
    "DEFAULT_SHIP_CLASS",
    "DEFAULT_BY_TYPE",
    "SHIP_NAMES",
    "ship_art",
    "ship_bands",
    "ship_class",
    "ship_name",
    "ship_for_type",
    "ship_briefs",
    "resolve_ship_art",
    "audit_ship_art",
]
