"""Filesystem layout for the app, the image tree and the flavor packages.

A *flavor* is a setting (a mod): a directory whose **directory name is the id**,
holding an optional ``flavor.json`` manifest plus the JSON, CSS and images it
overrides.  Player-facing mods live in ``mods/`` at the project root, beside the
app, so a player can copy a folder and get a new setting.  A wheel install has
no project root, so discovery falls back to the ``bridge/flavors`` tree packaged
inside the distribution, which ships ``core``.  The layout helpers here are
deliberately free of flavor semantics — they only answer "where would this
flavor's files live, and what does it extend?" — so the loader in
:mod:`bridge.shared.flavors` can be the single place that decides what a flavor
*means*.

``core`` is the shipped default setting: its art lives in the historical
``bridge/img`` tree (still overridable with ``ASSET_DIR``), while every other
flavor keeps its art under its own ``assets/`` directory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent

#: Project root — the directory holding ``bridge/`` and the player ``mods/``.
PROJECT_ROOT = PACKAGE_ROOT.parent

#: Player-facing mods directory, at the project root.
MODS_DIRNAME = "mods"

#: Fallback directory inside the package, shipped in the wheel for installs
#: that have no project-root ``mods/``.
FLAVORS_DIRNAME = "flavors"

#: The flavor every other flavor extends unless it says otherwise.
CORE_FLAVOR_ID = "core"


def package_path(*parts: str) -> Path:
    return PACKAGE_ROOT.joinpath(*parts)


def flavor_roots() -> list[Path]:
    """Every directory flavors are discovered under, highest priority first.

    ``FLAVORS_DIR`` replaces discovery entirely (alternate installs and tests).
    Otherwise the project-root ``mods/`` comes first, with the packaged
    ``bridge/flavors`` tree as the wheel fallback — so deleting a mod never
    removes the shipped ``core``.
    """
    configured = os.getenv("FLAVORS_DIR", "").strip()
    if configured:
        override = Path(configured).expanduser()
        if override.is_dir():
            return [override]
    roots: list[Path] = []
    mods = PROJECT_ROOT / MODS_DIRNAME
    if mods.is_dir():
        roots.append(mods)
    packaged = package_path(FLAVORS_DIRNAME)
    if packaged.is_dir():
        roots.append(packaged)
    return roots


def flavors_root() -> Path:
    """The primary flavor directory (discovery order, for display)."""
    roots = flavor_roots()
    return roots[0] if roots else package_path(FLAVORS_DIRNAME)


def flavor_dir(flavor_id: str) -> Path:
    """The directory a flavor id lives in, searching every root.

    An id missing from every root resolves under the primary root, so the
    caller's "no such flavor" handling still names a sensible path.
    """
    for root in flavor_roots():
        candidate = root / flavor_id
        if candidate.is_dir():
            return candidate
    return flavors_root() / flavor_id


def core_asset_dir() -> Path:
    """The image tree served at ``/img``: ``ASSET_DIR`` or the packaged ``img/``."""
    configured = os.getenv("ASSET_DIR", "").strip()
    if configured:
        override = Path(configured).expanduser()
        if override.is_dir():
            return override
    return package_path("img")


def _manifest(flavor_id: str) -> dict:
    path = flavor_dir(flavor_id) / "flavor.json"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def flavor_extends(flavor_id: str) -> str | None:
    """The id this flavor extends, or ``None`` for a standalone flavor.

    Inheritance is **opt-in**.  A manifest that omits ``extends`` (or sets it to
    ``null``) is standalone and carries its own complete catalog.  Mods are
    alternative settings played one at a time, so a mod that silently inherited
    the shipped ``core`` catalog would mix another universe's hulls and missions
    into its own; a flavor must name a parent to get one.

    ``core`` never extends.
    """
    if flavor_id == CORE_FLAVOR_ID:
        return None
    doc = _manifest(flavor_id)
    value = doc.get("extends")
    return str(value) if value else None


def flavor_chain(flavor_id: str) -> list[str]:
    """``[flavor, parent, ..., core]``, stopping on a missing manifest or cycle."""
    chain: list[str] = []
    seen: set[str] = set()
    current: str | None = flavor_id
    while current and current not in seen:
        seen.add(current)
        chain.append(current)
        current = flavor_extends(current)
    return chain


def resource_roots(flavor_id: str | None = None) -> list[Path]:
    """Data directories searched for a resource, flavor first, core last."""
    roots: list[Path] = []
    if flavor_id:
        roots.extend(flavor_dir(fid) / "resources" for fid in flavor_chain(flavor_id))
    roots.append(package_path("resources"))
    return [root for root in roots if root.is_dir()]


def asset_roots(flavor_id: str | None = None) -> list[Path]:
    """Image directories searched for hull art, flavor first, core last."""
    roots: list[Path] = []
    if flavor_id:
        roots.extend(flavor_dir(fid) / "assets" for fid in flavor_chain(flavor_id))
    roots = [root for root in roots if root.is_dir()]
    roots.append(core_asset_dir())
    return roots


def resource_path(filename: str, flavor: str | None = None) -> Path:
    """Resolve a ``resources/`` file through the flavor chain.

    Returns the flavor's own copy when it ships one, otherwise the packaged
    ``bridge/resources/`` path (which may or may not exist — callers keep their
    existing missing-file handling).
    """
    for root in resource_roots(flavor):
        candidate = root / filename
        if candidate.is_file():
            return candidate
    return package_path("resources", filename)


def asset_root(flavor: str | None = None) -> Path:
    """The first image directory in the flavor's search chain."""
    roots = asset_roots(flavor)
    return roots[0] if roots else core_asset_dir()


__all__ = [
    "CORE_FLAVOR_ID",
    "FLAVORS_DIRNAME",
    "MODS_DIRNAME",
    "PACKAGE_ROOT",
    "PROJECT_ROOT",
    "asset_root",
    "asset_roots",
    "core_asset_dir",
    "flavor_chain",
    "flavor_dir",
    "flavor_extends",
    "flavor_roots",
    "flavors_root",
    "package_path",
    "resource_path",
    "resource_roots",
]
