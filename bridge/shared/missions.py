"""CombatBot mission integration (Phase 10.5).

The mission generator already produces named nav points and ``dest`` jumps.  The
bridge shares that vocabulary so a mission can open as a bridge watch: this
module maps a CombatBot mission document onto bridge nav points.

Mission nav points carry no coordinates (the generator lays them out at run
time), so the bridge lays them out deterministically on a ring — the same
mission always produces the same chart.
"""

from __future__ import annotations

import math
from typing import Any

from .math_utils import clamp
from .types import NavPoint, Vec

#: Radius the generated nav points are laid out on.
MISSION_RING_KLIK = 60.0


def mission_nav_points(mission: dict[str, Any]) -> list[NavPoint]:
    """Map a CombatBot mission's nav points onto bridge nav points."""
    raw = mission.get("nav_points") or {}
    if not isinstance(raw, dict) or not raw:
        return []
    names = list(raw.keys())
    count = max(1, len(names))
    points: list[NavPoint] = []
    for index, name in enumerate(names):
        angle = 2 * math.pi * index / count
        entry = raw.get(name) or {}
        note = str(entry.get("descr", "")) if isinstance(entry, dict) else ""
        points.append(
            NavPoint(
                id=f"mission-{index}",
                name=str(name),
                kind="nav",
                pos=Vec(
                    x=round(math.sin(angle) * MISSION_RING_KLIK, 1),
                    y=round(math.cos(angle) * MISSION_RING_KLIK, 1),
                    z=0,
                ),
                radiusKlik=8.0,
                chartAgeHours=0.0,
                note=note[:200],
            )
        )
    return points


def mission_brief(mission: dict[str, Any]) -> str:
    """The mission's own opening description, if it has one."""
    raw = mission.get("nav_points") or {}
    if isinstance(raw, dict):
        for entry in raw.values():
            if isinstance(entry, dict) and entry.get("descr"):
                return str(entry["descr"])
    return str(mission.get("description") or "")


def mission_title(mission: dict[str, Any]) -> str:
    return str(mission.get("name") or "Mission")


def apply_mission(seed: Any, mission: dict[str, Any]) -> Any:
    """Graft a mission's title, brief and nav points onto a campaign seed."""
    points = mission_nav_points(mission)
    if points:
        seed.navPoints = points
    title = mission_title(mission)
    if title:
        seed.title = title
    brief = mission_brief(mission)
    if brief:
        seed.brief = brief
    return seed


def clamp_ring(radius: float) -> float:
    return clamp(radius, 5.0, 400.0)


__all__ = [
    "MISSION_RING_KLIK",
    "apply_mission",
    "clamp_ring",
    "mission_brief",
    "mission_nav_points",
    "mission_title",
]
