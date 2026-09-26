"""CAPTAIN ship catalog, resolved through the flavor system.

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

The catalog itself is **data**: ``flavors/<id>/ships.json``.  This module is the
flavor-aware view over it.  The module-level ``SHIP_CLASSES`` / ``SHIP_ART`` /
``HULL_STATS`` / ``SHIP_NAMES`` / ``DEFAULT_BY_TYPE`` are the ``core`` flavor's
tables, kept for compatibility; anything that knows which room it is serving
passes a ``flavor_id`` and gets that setting's catalog instead.
"""

from __future__ import annotations

from .flavors import Flavor, get as _get_flavor
from .flavors import ship_bands  # noqa: F401  (re-exported for callers/tests)
from .types import AdminShipBrief, ContactType, ShipClass

# Terrain contacts: the DB has asteroid/debris rows; the rest reuse the closest.
# A flavor may override named entries through ``ships.json``'s ``terrain`` map.
TERRAIN_IMAGES: dict[str, str] = {
    "asteroid": "/img/action/asteroid.png",
    "debris": "/img/action/debris.png",
    "nebula": "/img/action/cloud.png",
    "dust": "/img/action/cloud.png",
    "ice": "/img/action/asteroid.png",
}


def flavor(flavor_id: str | None = None) -> Flavor:
    """The resolved flavor (cached); unknown ids fall back to ``core``."""
    return _get_flavor(flavor_id)


def ship_classes(flavor_id: str | None = None) -> dict[str, ShipClass]:
    return flavor(flavor_id).ship_classes


def default_ship_class(flavor_id: str | None = None) -> str:
    resolved = flavor(flavor_id)
    fallback = resolved.defaults.get("unknown") or ""
    if fallback and fallback in resolved.ship_classes:
        return fallback
    return next(iter(resolved.ship_classes), "")


def ship_art(ship_id: str | None, flavor_id: str | None = None) -> tuple[str, str]:
    """``(action_url, vdu_url)`` for a hull id."""
    return flavor(flavor_id).ship_art.get(ship_id or "", ("", ""))


def resolve_ship_art(flavor_id: str | None = None) -> dict[str, tuple[str, str]]:
    """``hull id -> (image_url, vdu_url)`` for a flavor."""
    return dict(flavor(flavor_id).ship_art)


def resolve_hull_stats(flavor_id: str | None = None) -> dict[str, dict[str, float]]:
    return {
        hull_id: dict(stats)
        for hull_id, stats in flavor(flavor_id).hull_stats.items()
    }


def terrain_image(contact_type: str, flavor_id: str | None = None) -> str:
    override = flavor(flavor_id).terrain_images.get(contact_type)
    if override:
        return override
    return TERRAIN_IMAGES.get(contact_type, "")


def audit_ship_art(flavor_id: str | None = None) -> list[str]:
    """Findings about a flavor's resolved art map.

    ``ERROR:`` lines are failures (a hull with no art, or art pointing at a file
    that is not on disk).  ``INFO:`` lines are decisions to keep on purpose, such
    as two hulls sharing a parent class's art.  Run this in tests and at startup.
    """
    resolved = flavor(flavor_id)
    findings: list[str] = []
    by_action: dict[str, list[str]] = {}
    for hull in resolved.ship_classes.values():
        action, vdu = resolved.ship_art.get(hull.id, ("", ""))
        if not action:
            findings.append(f"ERROR: {hull.id}: no art resolved")
            continue
        if not resolved.url_exists(action):
            findings.append(f"ERROR: {hull.id}: action art missing on disk: {action}")
        if vdu and not resolved.url_exists(vdu):
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


def _home_hull(resolved: Flavor) -> ShipClass | None:
    """The flavor's default crew hull, or ``None`` if its catalog is empty."""
    home = default_ship_class(resolved.id)
    return resolved.ship_classes.get(home)


def ship_name(ship_id: str | None, flavor_id: str | None = None) -> str:
    """The proper name of the hull when the crew is flying it."""
    resolved = flavor(flavor_id)
    fallback = default_ship_class(flavor_id)
    return resolved.ship_names.get(ship_id or "", resolved.ship_names.get(fallback, ""))


def ship_class(ship_id: str | None, flavor_id: str | None = None) -> ShipClass:
    """Look up a hull, falling back to the flavor's default crew hull.

    Validation guarantees a non-empty catalog, but a defensive fallback to core
    keeps a live room alive if a flavor disappears between load and use.
    """
    resolved = flavor(flavor_id)
    if ship_id and ship_id in resolved.ship_classes:
        return resolved.ship_classes[ship_id]
    home = _home_hull(resolved)
    if home is not None:
        return home
    core = _get_flavor("core")
    return core.ship_classes[default_ship_class("core")]


def ship_for_type(
    contact_type: ContactType,
    ship_id: str | None = None,
    flavor_id: str | None = None,
) -> ShipClass:
    """Resolve a hull for a contact, preferring the explicit id.

    A dangling explicit id is a data error that validation catches at load; at
    runtime it degrades to the type default rather than crashing a live room.
    """
    resolved = flavor(flavor_id)
    if ship_id and ship_id in resolved.ship_classes:
        return resolved.ship_classes[ship_id]
    fallback = resolved.defaults.get(contact_type) or ""
    if fallback in resolved.ship_classes:
        return resolved.ship_classes[fallback]
    home = _home_hull(resolved)
    if home is not None:
        return home
    core = _get_flavor("core")
    return core.ship_classes[default_ship_class("core")]


def ship_briefs(flavor_id: str | None = None) -> list[AdminShipBrief]:
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
        for s in flavor(flavor_id).ship_classes.values()
    ]


# ---------------------------------------------------------------------------
# Core-flavor compatibility views
#
# These are the historical module-level tables.  They are pinned to ``core``
# explicitly (not to ``DEFAULT_FLAVOR``) so callers and tests that predate
# per-flavor catalogs always see the shipped default, whatever the server's boot
# setting is.
# ---------------------------------------------------------------------------

_DEFAULT_FLAVOR = _get_flavor("core")
SHIP_CLASSES: dict[str, ShipClass] = _DEFAULT_FLAVOR.ship_classes
SHIP_ART: dict[str, tuple[str, str]] = _DEFAULT_FLAVOR.ship_art
HULL_STATS: dict[str, dict[str, float]] = _DEFAULT_FLAVOR.hull_stats
SHIP_NAMES: dict[str, str] = _DEFAULT_FLAVOR.ship_names
DEFAULT_BY_TYPE: dict[ContactType, str] = dict(_DEFAULT_FLAVOR.defaults)  # type: ignore[assignment]
DEFAULT_SHIP_CLASS: str = default_ship_class("core")


__all__ = [
    "DEFAULT_BY_TYPE",
    "DEFAULT_SHIP_CLASS",
    "HULL_STATS",
    "SHIP_ART",
    "SHIP_CLASSES",
    "SHIP_NAMES",
    "TERRAIN_IMAGES",
    "audit_ship_art",
    "default_ship_class",
    "flavor",
    "resolve_hull_stats",
    "resolve_ship_art",
    "ship_art",
    "ship_bands",
    "ship_briefs",
    "ship_class",
    "ship_classes",
    "ship_for_type",
    "ship_name",
    "terrain_image",
]
