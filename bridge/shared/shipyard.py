"""Shipyard: the hull catalog, hardpoints, modules and arc coverage (Phase 9).

The hulls the bridge flies are curated from the ships DB into
``resources/bridge_hulls.json`` — each carrying its hardpoints (derived from the
hull's turret list) with the **arc** a mount can bear on and the **kind** of
weapon that fits it.  Modules come from ``resources/bridge_modules.json`` and are
fitted against power, mass and cargo budgets.
"""

from __future__ import annotations

import json
from typing import Any

from ..paths import resource_path
from .math_utils import clamp
from .types import Hardpoint, ModuleSpec

#: How far either side of dead ahead/astern an arc reaches.
ARC_SPAN_DEG = 60.0


def _load(path: str) -> dict[str, Any]:
    try:
        raw = json.loads(resource_path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


_DATA = _load("bridge_hulls.json")
_MODULE_DATA = _load("bridge_modules.json")

#: hull id -> curated catalog entry (hardpoints, gunners, cargo, extra hulls)
HULLS: dict[str, dict[str, Any]] = {
    str(k): dict(v) for k, v in (_DATA.get("hulls") or {}).items()
}
#: module id -> spec
MODULES: dict[str, ModuleSpec] = {
    str(k): ModuleSpec.model_validate({"id": k, **v})
    for k, v in (_MODULE_DATA.get("modules") or {}).items()
}


def hull_entry(hull_id: str) -> dict[str, Any]:
    return HULLS.get(hull_id, {})


def hull_hardpoints(hull_id: str) -> list[Hardpoint]:
    """The mounts a hull carries, unfitted."""
    entry = hull_entry(hull_id)
    points = entry.get("hardpoints") or []
    return [
        Hardpoint(
            id=str(p.get("id", f"hp{index}")),
            arc=p.get("arc", "all"),
            kind=p.get("kind", "gun"),
        )
        for index, p in enumerate(points)
    ]


def module_spec(module_id: str) -> ModuleSpec | None:
    return MODULES.get(module_id)


def fits_arc(arc: str, offset_deg: float) -> bool:
    """Whether a mount with ``arc`` can bear on a target at ``offset_deg``.

    ``offset_deg`` is signed: 0 dead ahead, +90 to starboard, -90 to port,
    +/-180 astern.
    """
    offset = ((offset_deg + 180) % 360) - 180
    if arc == "all":
        return True
    if arc == "fore":
        return abs(offset) <= ARC_SPAN_DEG
    if arc == "aft":
        return abs(offset) >= 180 - ARC_SPAN_DEG
    if arc == "starboard":
        return ARC_SPAN_DEG * 0.5 <= offset <= 180 - ARC_SPAN_DEG
    if arc == "port":
        return -(180 - ARC_SPAN_DEG) <= offset <= -ARC_SPAN_DEG * 0.5
    return True


def module_totals(module_ids: list[str]) -> dict[str, float]:
    """Power, mass and cargo a module list costs."""
    totals = {"power": 0.0, "massKt": 0.0, "cargo": 0.0}
    for module_id in module_ids:
        spec = MODULES.get(module_id)
        if spec is None:
            continue
        totals["power"] += spec.power
        totals["massKt"] += spec.massKt
        totals["cargo"] += spec.cargo
    return totals


def module_multiplier(module_ids: list[str], attr: str) -> float:
    """Product of a multiplier attribute across fitted modules."""
    result = 1.0
    for module_id in module_ids:
        spec = MODULES.get(module_id)
        if spec is None:
            continue
        result *= float(getattr(spec, attr, 1.0) or 1.0)
    return result


def module_sum(module_ids: list[str], attr: str) -> float:
    """Sum of an additive attribute across fitted modules."""
    return sum(
        float(getattr(MODULES[module_id], attr, 0.0) or 0.0)
        for module_id in module_ids
        if module_id in MODULES
    )


def within_budgets(
    module_ids: list[str], power: float, mass_kt: float, cargo: float
) -> bool:
    totals = module_totals(module_ids)
    return (
        totals["power"] <= power + 1e-9
        and totals["massKt"] <= mass_kt + 1e-9
        and totals["cargo"] <= cargo + 1e-9
    )


def default_loadout(hull_id: str) -> list[Hardpoint]:
    """A sensible starting fit: a gun on every gun mount, missiles elsewhere."""
    fitted: list[Hardpoint] = []
    by_kind = {
        "gun": "laser-cannon",
        "missile": "heat-seeker",
        "torpedo": "torpedo",
    }
    for point in hull_hardpoints(hull_id):
        point.fitted = by_kind.get(point.kind, "laser-cannon")
        fitted.append(point)
    return fitted


def clamp_unit(value: float) -> float:
    return clamp(value, 0, 1)


__all__ = [
    "ARC_SPAN_DEG",
    "HULLS",
    "MODULES",
    "default_loadout",
    "fits_arc",
    "hull_entry",
    "hull_hardpoints",
    "module_multiplier",
    "module_spec",
    "module_sum",
    "module_totals",
    "within_budgets",
]
