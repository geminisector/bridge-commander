"""FTL drive table (WCRPG Ch 8).

Data lives in ``resources/bridge_drives.json``.  A drive changes three things:
how fast alignment accrues, what a jump costs in fuel, and how good the
alignment must be before the drive will engage at all.
"""

from __future__ import annotations

import json
from typing import Any

from ..paths import resource_path

_FILE = "bridge_drives.json"
_FALLBACK: dict[str, Any] = {
    "name": "Standard Drive",
    "spoolRate": 1.0,
    "fuelMultiplier": 1.0,
    "misjumpFloor": 0.35,
    "note": "",
}


def _load() -> dict[str, Any]:
    path = resource_path(_FILE)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


_DATA = _load()

#: drive id -> spec
DRIVES: dict[str, dict[str, Any]] = {
    str(k): dict(v) for k, v in (_DATA.get("drives") or {}).items()
}
#: The drive fitted when nothing else is chosen.
DEFAULT_DRIVE: str = str(_DATA.get("default") or "standard")


def drive_spec(name: str | None) -> dict[str, Any]:
    """The spec for a drive id, falling back to the default (then a stub)."""
    if name and name in DRIVES:
        return DRIVES[name]
    if DEFAULT_DRIVE in DRIVES:
        return DRIVES[DEFAULT_DRIVE]
    return dict(_FALLBACK)


def drive_name(name: str | None) -> str:
    return str(drive_spec(name).get("name", "Standard Drive"))


__all__ = ["DEFAULT_DRIVE", "DRIVES", "drive_name", "drive_spec"]
