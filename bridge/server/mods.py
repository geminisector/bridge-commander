"""Mod (flavor) activation registry.

A **flavor** is a setting deployed on disk; a **mod** is that flavor switched on.
Mods are alternative universes, so **exactly one is active at a time**:
activating a mod unloads every other one, ``core`` included.  That single active
mod is what every room plays and what new rooms start on, so this module is the
single place that answers "which setting is the table playing?":

* Exactly one mod is active; ``core`` is the fallback when none was ever chosen.
* Only installed, valid mods may be activated.
* The active mod is persisted, so it survives a restart.

``core`` is an ordinary mod here, not a privileged one: it can be unloaded like
any other, and it is only special in that it is the setting the registry falls
back to when the persisted choice names something no longer installed.
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


def active_mod() -> str:
    """The single active mod: the persisted choice, else ``DEFAULT_FLAVOR``.

    Falls back to ``core`` when nothing was chosen, or when the persisted mod is
    no longer installed (a flavor deleted from disk must not brick the server).
    """
    persisted = _clean(db.load_active_mod())
    if persisted and persisted in _installed():
        return persisted
    configured = _env_default()
    if configured:
        return configured
    return CORE


def is_enabled(flavor_id: str | None) -> bool:
    """Whether this mod is *the* active one.

    There is no "enabled set" any more: a mod is either the setting in play or
    it is unloaded.
    """
    fid = _clean(flavor_id)
    if not fid or fid != active_mod():
        return False
    return fid == CORE or fid in _installed()


def enabled_ids() -> list[str]:
    """The active mods.  Always exactly one entry, or none with no flavors."""
    active = active_mod()
    return [active] if is_enabled(active) else []


def activate(flavor_id: str | None) -> tuple[bool, str]:
    """Make one mod the active setting, unloading every other.  ``(ok, reason)``."""
    fid = _clean(flavor_id)
    if not fid:
        return False, "no mod given"
    if fid not in _installed():
        return False, f"no such mod: {fid!r}"
    summary = next((row for row in flavors.summaries() if row["id"] == fid), None)
    if summary is None:
        return False, f"no such mod: {fid!r}"
    if not summary.get("valid", False):
        return False, f"mod {fid!r} is invalid: {summary.get('error', 'failed to load')}"
    previous = active_mod()
    db.set_active_mod(fid)
    if previous != fid:
        log.info("mod %s activated; %s unloaded", fid, previous)
    else:
        log.info("mod %s activated", fid)
    return True, ""


def deactivate(flavor_id: str | None) -> tuple[bool, str]:
    """Unload a mod.  Returns ``(ok, reason)``.

    Because one mod is always active, unloading the active mod loads ``core``
    in its place: the table always has *some* setting.  ``core`` itself is
    therefore never "deactivated" directly — pick another mod instead.
    """
    fid = _clean(flavor_id)
    if fid not in _installed():
        return False, f"no such mod: {fid!r}"
    if fid != active_mod():
        return False, f"mod {fid!r} is not the active setting"
    if fid == CORE:
        return False, "core is the fallback setting; activate another mod instead"
    db.set_active_mod(CORE)
    log.info("mod %s unloaded; core is active", fid)
    return True, ""


def guard_room(flavor_id: str | None) -> str:
    """The flavor a room may actually use — always the one active mod."""
    fid = _clean(flavor_id)
    active = active_mod()
    if fid and fid != active:
        log.warning("mod %r is not active; room plays %r instead", fid, active)
    return active


def list_mods() -> list[dict]:
    """Every installed flavor with its activation state, for the GM console."""
    active = active_mod()
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
                "enabled": fid == active,
                "core": fid == CORE,
            }
        )
    return rows


__all__ = [
    "CORE",
    "activate",
    "active_mod",
    "deactivate",
    "enabled_ids",
    "guard_room",
    "is_enabled",
    "list_mods",
]
