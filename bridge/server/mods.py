"""Mod (flavor) activation registry.

A **flavor** is a setting deployed on disk; a **mod** is that flavor switched on.
Installed flavors are inert until an operator activates them from the GM console
(or via ``DEFAULT_FLAVOR``/``--flavor``, which counts as an explicit operator
activation).  This module is the single place that answers "may this room play
this setting?" so the fail-closed rule stays honest:

* ``core`` is always active — it is the fallback every other path degrades to.
* Only installed, valid, *activated* mods may be selected for a room.
* The server-wide default mod is persisted and must itself be activated.

The enabled set and the default live in the rooms database
(``bridge/server/db.py``), so they survive a restart.
"""

from __future__ import annotations

import logging
import os

from ..shared import flavors
from . import db
from .config import DEFAULT_FLAVOR

log = logging.getLogger("bridge.mods")

CORE = "core"


def _clean(flavor_id: str | None) -> str:
    return (flavor_id or "").strip()


def _installed() -> set[str]:
    return set(flavors.available())


def _env_default() -> str:
    """``DEFAULT_FLAVOR`` when it names an installed flavor, else ``""``.

    Read from the environment at call time (not the import-time config value) so
    the ``--flavor`` CLI flag, which sets the variable at startup, is honoured.
    """
    configured = os.getenv("DEFAULT_FLAVOR", DEFAULT_FLAVOR).strip()
    if configured and configured in _installed():
        return configured
    return ""


def is_enabled(flavor_id: str | None) -> bool:
    """Whether a mod may be used for a room.

    ``core`` is always on.  An installed mod is on when an operator activated it
    in the console or when ``DEFAULT_FLAVOR`` names it (an explicit boot-time
    activation).
    """
    fid = _clean(flavor_id)
    if not fid:
        return False
    if fid == CORE:
        return True
    if fid not in _installed():
        return False
    if fid == _env_default():
        return True
    return fid in db.load_enabled_mods()


def enabled_ids() -> list[str]:
    return [fid for fid in flavors.available() if is_enabled(fid)]


def activate(flavor_id: str | None) -> tuple[bool, str]:
    """Switch a mod on.  Returns ``(ok, reason)``."""
    fid = _clean(flavor_id)
    if fid == CORE:
        return True, "core is always active"
    if fid not in _installed():
        return False, f"no such mod: {fid!r}"
    summary = next(
        (row for row in flavors.summaries() if row["id"] == fid),
        None,
    )
    if summary is None:
        return False, f"no such mod: {fid!r}"
    if not summary.get("valid", False):
        return False, f"mod {fid!r} is invalid: {summary.get('error', 'failed to load')}"
    db.set_mod_enabled(fid, True)
    log.info("mod %s activated", fid)
    return True, ""


def deactivate(flavor_id: str | None) -> tuple[bool, str]:
    """Switch a mod off.  Returns ``(ok, reason)``."""
    fid = _clean(flavor_id)
    if fid == CORE:
        return False, "core cannot be deactivated"
    if fid not in _installed():
        return False, f"no such mod: {fid!r}"
    if fid == _env_default():
        return (
            False,
            f"{fid!r} is selected by DEFAULT_FLAVOR; unset it before deactivating",
        )
    db.set_mod_enabled(fid, False)
    log.info("mod %s deactivated", fid)
    return True, ""


def default_flavor() -> str:
    """The setting new rooms start on: persisted default, else env, else core."""
    persisted = _clean(db.load_default_mod())
    if persisted and is_enabled(persisted):
        return persisted
    configured = _env_default()
    if configured and is_enabled(configured):
        return configured
    return CORE


def set_default(flavor_id: str | None) -> tuple[bool, str]:
    """Persist the server-wide default.  ``None``/"" clears it.  Returns ``(ok, reason)``."""
    fid = _clean(flavor_id)
    if not fid:
        db.set_default_mod(None)
        return True, ""
    if not is_enabled(fid):
        return False, f"mod {fid!r} must be activated before it can be the default"
    db.set_default_mod(fid)
    log.info("default mod set to %s", fid)
    return True, ""


def guard_room(flavor_id: str | None) -> str:
    """The flavor a room may actually use, falling back to the default/core."""
    fid = _clean(flavor_id)
    if fid and is_enabled(fid):
        return fid
    fallback = default_flavor()
    if fid and fallback != fid:
        log.warning("mod %r is not activated; falling back to %r", fid, fallback)
    return fallback


def list_mods() -> list[dict]:
    """Every installed flavor with its activation state, for the GM console."""
    current_default = default_flavor()
    rows: list[dict] = []
    for summary in flavors.summaries():
        fid = summary["id"]
        rows.append(
            {
                "id": fid,
                "title": summary["title"],
                "extends": summary.get("extends"),
                "hulls": summary.get("hulls", 0),
                "missions": summary.get("missions", 0),
                "valid": bool(summary.get("valid", True)),
                "error": summary.get("error", ""),
                "enabled": is_enabled(fid),
                "default": fid == current_default,
                "core": fid == CORE,
            }
        )
    return rows


__all__ = [
    "CORE",
    "activate",
    "deactivate",
    "default_flavor",
    "enabled_ids",
    "guard_room",
    "is_enabled",
    "list_mods",
    "set_default",
]
