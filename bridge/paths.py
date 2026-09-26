"""Filesystem layout for the app, the image tree and the flavor packages.

A *flavor* is a setting (a mod): a directory under ``bridge/flavors/<id>/``
holding a ``flavor.json`` manifest plus the JSON, CSS and images it overrides.
The layout helpers here are deliberately free of flavor semantics — they only
answer "where would this flavor's files live, and what does it extend?" — so the
loader in :mod:`bridge.shared.flavors` can be the single place that decides what
a flavor *means*.

``core`` is the shipped default setting: its art lives in the historical
``bridge/img`` tree (still overridable with ``ASSET_DIR``), while every other
flavor keeps its art under its own ``assets/`` directory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent

#: Directory holding the shipped and user-installed flavors.
FLAVORS_DIRNAME = "flavors"

#: The flavor every other flavor extends unless it says otherwise.
CORE_FLAVOR_ID = "core"


def package_path(*parts: str) -> Path:
    return PACKAGE_ROOT.joinpath(*parts)


def flavors_root() -> Path:
    """The directory flavors are discovered under (``FLAVORS_DIR`` overrides)."""
    configured = os.getenv("FLAVORS_DIR", "").strip()
    if configured:
        override = Path(configured).expanduser()
        if override.is_dir():
            return override
    return package_path(FLAVORS_DIRNAME)


def flavor_dir(flavor_id: str) -> Path:
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

    ``core`` never extends.  Any other manifest that omits ``extends`` inherits
    ``core``; an explicit ``"extends": null`` opts out and replaces core
    wholesale.
    """
    if flavor_id == CORE_FLAVOR_ID:
        return None
    doc = _manifest(flavor_id)
    if "extends" in doc:
        value = doc.get("extends")
        return str(value) if value else None
    return CORE_FLAVOR_ID


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
    "PACKAGE_ROOT",
    "asset_root",
    "asset_roots",
    "core_asset_dir",
    "flavor_chain",
    "flavor_dir",
    "flavor_extends",
    "flavors_root",
    "package_path",
    "resource_path",
    "resource_roots",
]
