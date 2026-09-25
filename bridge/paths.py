from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent


def package_path(*parts: str) -> Path:
    return PACKAGE_ROOT.joinpath(*parts)


def resource_path(filename: str) -> Path:
    return package_path("resources", filename)


def asset_root() -> Path:
    configured = os.getenv("ASSET_DIR", "").strip()
    if configured:
        override = Path(configured).expanduser()
        if override.is_dir():
            return override
    return package_path("img")


__all__ = ["PACKAGE_ROOT", "asset_root", "package_path", "resource_path"]
