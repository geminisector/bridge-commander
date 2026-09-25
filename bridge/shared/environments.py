"""Environment catalog (ENVIRONMENTS_AND_MAINTENANCE_PLAN).

Nine environment types, each a single model: how it affects sensors, own
emission, fuel burn, comms, wear, repair difficulty, contamination and EVA
risk.  A hazard is simply an environment with a time window, so there is one
model rather than two.
"""

from __future__ import annotations

import json
from typing import Any

from ..paths import resource_path
from .types import EnvironmentSpec

_FILE = "bridge_environments.json"
_FALLBACK = EnvironmentSpec(id="clear-space", name="Clear space")

#: Hazard type substrings mapped onto environment ids.
_HAZARD_MAP: tuple[tuple[str, str], ...] = (
    ("asteroid", "asteroid-belt"),
    ("nebula", "nebula"),
    ("ice", "ice-field"),
    ("dust", "dust-field"),
    ("debris", "debris-field"),
    ("radiation", "radiation-storm"),
    ("solar", "radiation-storm"),
    ("ion", "ion-storm"),
    ("gravity", "gravity-well"),
    ("well", "gravity-well"),
)


def _load() -> dict[str, Any]:
    path = resource_path(_FILE)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


_DATA = _load()

#: environment id -> spec
ENVIRONMENTS: dict[str, EnvironmentSpec] = {
    str(k): EnvironmentSpec.model_validate({"id": k, **v})
    for k, v in (_DATA.get("environments") or {}).items()
}
DEFAULT_ENVIRONMENT: str = str(_DATA.get("default") or "clear-space")


def environment_spec(env_id: str | None) -> EnvironmentSpec:
    """The spec for an environment id, falling back to clear space."""
    if env_id and env_id in ENVIRONMENTS:
        return ENVIRONMENTS[env_id]
    if DEFAULT_ENVIRONMENT in ENVIRONMENTS:
        return ENVIRONMENTS[DEFAULT_ENVIRONMENT]
    return _FALLBACK.model_copy()


def environment_for_hazard(hazard_type: str) -> str:
    """Map a hazard type string onto an environment id."""
    low = (hazard_type or "").lower()
    for needle, env_id in _HAZARD_MAP:
        if needle in low:
            return env_id
    return DEFAULT_ENVIRONMENT


__all__ = [
    "DEFAULT_ENVIRONMENT",
    "ENVIRONMENTS",
    "environment_for_hazard",
    "environment_spec",
]
