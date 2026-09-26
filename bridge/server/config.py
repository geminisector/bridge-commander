"""CAPTAIN server configuration.

Direct port of ``apps/server/src/config.ts`` using python-dotenv.

The TypeScript version exports a single ``config`` object; the Python port keeps
the individual module-level names (``PORT``, ``CORS_ORIGINS``, ...) that
MIGRATION.md §2.1 specifies, and additionally exposes a small ``Config``
namespace-like object for callers that prefer the original shape.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from ..paths import package_path

load_dotenv()
load_dotenv(package_path(".env"))

HOST: str = os.getenv("HOST", "127.0.0.1")
PORT: int = int(os.getenv("PORT", "8787"))
CORS_ORIGINS: list[str] = [
    s.strip() for s in os.getenv("CORS_ORIGINS", "*").split(",") if s.strip()
]
DATA_DIR: str = os.getenv("DATA_DIR", "./data")
# Optional explicit path to the built activity bundle (the directory holding
# ``index.html``).  When unset the server auto-discovers the bundle relative to
# the repo checkout; see ``main._activity_dist``.
ACTIVITY_DIST: str = os.getenv("ACTIVITY_DIST", "")
# Optional explicit path to the static image tree served at ``/img`` (the
# contact art referenced by the activity UI, e.g. ``/img/action/enemy-fighter.png``).
# When unset the server uses the packaged ``bridge/img`` tree.
ASSET_DIR: str = os.getenv("ASSET_DIR", "")
# Optional directory holding the flavor packages.  When unset the server uses
# the packaged ``bridge/flavors`` tree.
FLAVORS_DIR: str = os.getenv("FLAVORS_DIR", "")
# The setting new rooms start on.  Unset / unknown ids fall back to ``core``.
DEFAULT_FLAVOR: str = os.getenv("DEFAULT_FLAVOR", "")
# ``Number(process.env.ADMIN_PORT) || 0`` — an unset/blank/invalid value is 0.
try:
    ADMIN_PORT: int = int(os.getenv("ADMIN_PORT") or "0")
except ValueError:
    ADMIN_PORT = 0
ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "")
ADMIN_HOST: str = os.getenv("ADMIN_HOST", "127.0.0.1")
ADMIN_ORIGINS: list[str] = [
    s.strip() for s in os.getenv("ADMIN_ORIGINS", "*").split(",") if s.strip()
]


@dataclass(frozen=True)
class Config:
    host: str = HOST
    port: int = PORT
    corsOrigins: list[str] | None = None
    dataDir: str = DATA_DIR
    activityDist: str = ACTIVITY_DIST
    assetDir: str = ASSET_DIR
    flavorsDir: str = FLAVORS_DIR
    defaultFlavor: str = DEFAULT_FLAVOR
    adminPort: int = ADMIN_PORT
    adminToken: str = ADMIN_TOKEN
    adminHost: str = ADMIN_HOST
    adminOrigins: list[str] | None = None


config = Config(
    host=HOST,
    port=PORT,
    corsOrigins=CORS_ORIGINS,
    dataDir=DATA_DIR,
    activityDist=ACTIVITY_DIST,
    assetDir=ASSET_DIR,
    flavorsDir=FLAVORS_DIR,
    defaultFlavor=DEFAULT_FLAVOR,
    adminPort=ADMIN_PORT,
    adminToken=ADMIN_TOKEN,
    adminHost=ADMIN_HOST,
    adminOrigins=ADMIN_ORIGINS,
)

if os.getenv("NODE_ENV") == "development":
    print(f"[config] port={PORT} dataDir={DATA_DIR}")


__all__ = [
    "HOST",
    "PORT",
    "CORS_ORIGINS",
    "DATA_DIR",
    "ACTIVITY_DIST",
    "ASSET_DIR",
    "FLAVORS_DIR",
    "DEFAULT_FLAVOR",
    "ADMIN_PORT",
    "ADMIN_TOKEN",
    "ADMIN_HOST",
    "ADMIN_ORIGINS",
    "Config",
    "config",
]
