"""CAPTAIN campaigns, loaded from flavor mission data.

A mission is **data**: ``flavors/<id>/missions/*.json``, a document that mirrors
:class:`~bridge.shared.types.CampaignSeed` field-for-field.  The generic loader
is ``CampaignSeed.model_validate(merged_json)``; a flavor never ships code and
never introduces its own randomness (FLAVOR_PLUGIN_PLAN.md invariant 1).

``core`` keeps its historical campaign ids (``iron-collar`` and friends) so
existing saved rooms and the GM console keep resolving.  A flavor's missions are
namespaced by convention — ``stk.babel`` — and reference its own hull ids.
"""

from __future__ import annotations

from collections.abc import Callable

from .flavors import Flavor, FlavorError, get as _get_flavor
from .types import CampaignSeed

__all__ = [
    "CAMPAIGNS",
    "CAMPAIGN_TITLES",
    "CAPSHIP_CLASSES",
    "ESCORT_CLASSES",
    "FIGHTER_CLASSES",
    "campaign_briefs",
    "campaign_for",
    "campaign_ids",
    "military_name",
    "military_pool",
    "vessel_name",
]


def military_name(
    pool: list[str], i: int, used: set[str] | None = None
) -> str:
    """Pick a callsign variant from a numbered pool.

    ``i`` is the caller's running index.  When ``used`` names the contacts
    already in the scenario, the next free variant is taken so two contacts of
    the same role never share a callsign.
    """
    if not pool:
        return ""
    start = (max(i, 1) - 1) % len(pool)
    for offset in range(len(pool)):
        candidate = pool[(start + offset) % len(pool)]
        if used is None or candidate not in used:
            return candidate
    return pool[start]


def vessel_name(seed: int, flavor_id: str | None = None) -> str:
    """A neutral/civilian name from the flavor's pools and naming style."""
    return _get_flavor(flavor_id).callsigns.vessel(seed)


def military_pool(contact_type: str, flavor_id: str | None = None) -> list[str]:
    """The hostile callsign pool for a contact type under a flavor."""
    return _get_flavor(flavor_id).callsigns.pool_for(contact_type)


def _flavor(flavor_id: str | None) -> Flavor:
    return _get_flavor(flavor_id)


def campaign_ids(flavor_id: str | None = None) -> list[str]:
    return _flavor(flavor_id).mission_ids


def campaign_for(
    campaign_id: str | None = None, flavor_id: str | None = None
) -> CampaignSeed:
    """The seed for ``campaign_id`` under a flavor.

    An unknown or missing id falls back to the flavor's ``defaultMission`` (for
    ``core`` that is ``iron-collar``), so a stale GM template still starts a
    playable patrol.
    """
    resolved = _flavor(flavor_id)
    key = campaign_id if campaign_id and campaign_id in resolved.missions else ""
    if not key:
        key = resolved.first_mission_or("")
    if not key:
        raise FlavorError("no missions installed for this flavor")
    return resolved.mission_seed(key)


def campaign_briefs(flavor_id: str | None = None) -> list[tuple[str, str, str]]:
    """``(id, title, theater)`` for every mission in a flavor."""
    resolved = _flavor(flavor_id)
    briefs: list[tuple[str, str, str]] = []
    for mission_id in resolved.mission_ids:
        seed = resolved.mission_seed(mission_id)
        briefs.append((mission_id, seed.title, seed.theater))
    return briefs


# The core flavor's pools, kept as module-level names for callers and tests that
# predate per-flavor catalogs.  Pinned to ``core`` explicitly, not to
# ``DEFAULT_FLAVOR``.
_core = _flavor("core")
ESCORT_CLASSES: list[str] = _core.callsigns.pool_for("escort")
CAPSHIP_CLASSES: list[str] = _core.callsigns.pool_for("capship")
FIGHTER_CLASSES: list[str] = _core.callsigns.pool_for("fighter")


def _core_loader(mission_id: str) -> Callable[[int], CampaignSeed]:
    def _load(_seed: int = 0) -> CampaignSeed:
        return campaign_for(mission_id, "core")

    return _load


#: The shipped (core) campaigns, id -> factory.  Kept for the legacy surface;
#: flavor-aware callers use ``campaign_for(id, flavor_id)``.
CAMPAIGNS: dict[str, Callable[[int], CampaignSeed]] = {
    mission_id: _core_loader(mission_id) for mission_id in campaign_ids("core")
}

CAMPAIGN_TITLES: dict[str, str] = {
    mission_id: CAMPAIGNS[mission_id](0).title for mission_id in CAMPAIGNS
}
