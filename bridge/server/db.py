"""CAPTAIN persistence layer.

Direct port of ``apps/server/src/db.ts``: ``node:sqlite`` (synchronous) becomes
stdlib :mod:`sqlite3` (also synchronous).  A single module-level connection is
reused for the lifetime of the process.
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

from ..shared.constants import STATE_SCHEMA_VERSION
from ..shared.types import GameState
from .config import DATA_DIR

_conn: sqlite3.Connection | None = None


def init_db(data_dir: str | None = None) -> sqlite3.Connection:
    """Create (once) and return the rooms database connection."""
    global _conn
    if _conn is not None:
        return _conn
    directory = data_dir if data_dir is not None else DATA_DIR
    Path(directory).mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: the connection is created on the import/main
    # thread but may be used from the uvicorn event loop; access stays
    # single-threaded in practice, this only silences sqlite's guard.
    _conn = sqlite3.connect(
        os.path.join(directory, "bridge.sqlite"), check_same_thread=False
    )
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
          channel TEXT PRIMARY KEY,
          state TEXT NOT NULL,
          updated INTEGER NOT NULL
        );
        """
    )
    # Mod (flavor) activation: installed flavors are inert until an operator
    # activates them.  ``is_default`` marks the setting new rooms start on.
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mods (
          flavor_id TEXT PRIMARY KEY,
          enabled INTEGER NOT NULL DEFAULT 0,
          is_default INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    _conn.commit()
    return _conn


def save_room(channel: str, state: GameState) -> None:
    conn = _conn if _conn is not None else init_db()
    conn.execute(
        """INSERT INTO rooms (channel, state, updated) VALUES (?, ?, ?)
           ON CONFLICT(channel) DO UPDATE SET state = excluded.state, updated = excluded.updated""",
        (channel, state.model_dump_json(), _now_ms()),
    )
    conn.commit()


def load_room(channel: str) -> GameState | None:
    conn = _conn if _conn is not None else init_db()
    row = conn.execute(
        "SELECT state FROM rooms WHERE channel = ?", (channel,)
    ).fetchone()
    if not row:
        return None
    try:
        parsed = GameState.model_validate_json(row[0])
        # v2 moved the sim to 3D (z, elevation) and reworked the passive noise
        # model. Older runs are incompatible — discard them and start fresh.
        if parsed.schemaVersion != STATE_SCHEMA_VERSION:
            return None
        return parsed
    except Exception:
        return None


def _now_ms() -> int:
    """``Date.now()`` — milliseconds since the Unix epoch."""
    return int(time.time() * 1000)


# ---------------------------------------------------------------------------
# Mod (flavor) activation
#
# Installed flavors are inert until activated.  ``core`` is implicit and never
# stored.  ``is_default`` marks the setting new rooms start on.  These helpers
# degrade to empty/false rather than raising: a mod store that cannot be read
# must not take the server down (activation is a convenience, not sim state).
# ---------------------------------------------------------------------------


def _mods_conn() -> sqlite3.Connection:
    return _conn if _conn is not None else init_db()


def load_enabled_mods() -> set[str]:
    try:
        rows = _mods_conn().execute(
            "SELECT flavor_id FROM mods WHERE enabled = 1"
        ).fetchall()
    except sqlite3.Error:
        return set()
    return {str(row[0]) for row in rows}


def set_mod_enabled(flavor_id: str, enabled: bool) -> None:
    conn = _mods_conn()
    if enabled:
        conn.execute(
            """INSERT INTO mods (flavor_id, enabled, is_default) VALUES (?, 1, 0)
               ON CONFLICT(flavor_id) DO UPDATE SET enabled = 1""",
            (flavor_id,),
        )
    else:
        # Deactivating the default clears the default too, so a disabled mod
        # cannot be selected for new rooms.
        conn.execute(
            """INSERT INTO mods (flavor_id, enabled, is_default) VALUES (?, 0, 0)
               ON CONFLICT(flavor_id) DO UPDATE SET enabled = 0, is_default = 0""",
            (flavor_id,),
        )
    conn.commit()


def load_default_mod() -> str | None:
    try:
        row = _mods_conn().execute(
            "SELECT flavor_id FROM mods WHERE is_default = 1 LIMIT 1"
        ).fetchone()
    except sqlite3.Error:
        return None
    return str(row[0]) if row else None


def set_default_mod(flavor_id: str | None) -> None:
    conn = _mods_conn()
    conn.execute("UPDATE mods SET is_default = 0")
    if flavor_id:
        conn.execute(
            """INSERT INTO mods (flavor_id, enabled, is_default) VALUES (?, 1, 1)
               ON CONFLICT(flavor_id) DO UPDATE SET is_default = 1, enabled = 1""",
            (flavor_id,),
        )
    conn.commit()


# TypeScript exports ``initDb``; keep the camelCase alias for an easy diff.
initDb = init_db
saveRoom = save_room
loadRoom = load_room


__all__ = [
    "init_db",
    "save_room",
    "load_room",
    "initDb",
    "saveRoom",
    "loadRoom",
    "load_enabled_mods",
    "set_mod_enabled",
    "load_default_mod",
    "set_default_mod",
]
