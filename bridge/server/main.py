"""BRIDGE COMMANDER server entry point.

Direct port of ``apps/server/src/index.ts``.  Run with::

    python -m bridge

which starts the FastAPI app (client websocket + health + optional static
activity bundle) on ``PORT`` and, when ``ADMIN_PORT`` is set, the admin app on
its own port in a background thread.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from ..paths import asset_root, package_path
from .admin import create_admin_app
from .config import (
    ACTIVITY_DIST,
    ADMIN_HOST,
    ADMIN_PORT,
    ADMIN_TOKEN,
    ASSET_DIR,
    CORS_ORIGINS,
    DATA_DIR,
    HOST,
    PORT,
)
from .db import init_db
from .engine import advance
from .ws import attach_ws, rooms

# Mirror the express origin allow-list: configured origins plus the Discord
# Activity proxy and localhost during development.
_ORIGIN_RE = (
    r"^https://([a-z0-9-]+\.)*discord\.app$"
    r"|^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
)

# AUTO_TICK: every 60 real seconds advance a running, auto-ticking room by 10
# game minutes (matches the TS ``setInterval(..., 60_000)``).
AUTO_TICK_INTERVAL_SECONDS = 60
AUTO_TICK_MINUTES = 10

_lifespan_admin_started = False
_watch_wall_time: dict[str, float] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    tick_task = asyncio.create_task(_auto_tick())
    _start_admin_thread()
    try:
        yield
    finally:
        tick_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await tick_task


app = FastAPI(title="BRIDGE COMMANDER", lifespan=lifespan)

_allow_origins = ["*"] if "*" in CORS_ORIGINS else list(CORS_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_origin_regex=None if "*" in CORS_ORIGINS else _ORIGIN_RE,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "rooms": len(rooms.rooms), "time": _now_iso()}


@app.get("/favicon.png", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(package_path("favico.png"), media_type="image/png")


def _activity_dist() -> Path | None:
    """Locate the built activity frontend, if it was bundled alongside us.

    Checks the explicit ``ACTIVITY_DIST`` override first, then the packaged
    activity bundle.
    """
    if ACTIVITY_DIST:
        override = Path(ACTIVITY_DIST).expanduser()
        if (override / "index.html").is_file():
            return override
    candidates = [package_path("activity", "dist")]
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return None


def _asset_dir() -> Path | None:
    """Locate the static image tree served at ``/img``.

    The activity UI references contact art by absolute URL (for example
    ``/img/action/enemy-fighter.png`` and ``/img/brief/unknown.png``); those
    files live in the CombatBot repo's ``img/`` tree rather than inside the
    built bundle.
    """
    if ASSET_DIR:
        override = Path(ASSET_DIR).expanduser()
        if override.is_dir():
            return override
    fallback = asset_root()
    return fallback if fallback.is_dir() else None


# Register the websocket route before any catch-all static mount, otherwise a
# mount at "/" would swallow websocket upgrades for "/ws".
attach_ws(app)

# Mount the image tree before "/" so it wins over the activity catch-all.
_assets = _asset_dir()
if _assets is not None:
    app.mount("/img", StaticFiles(directory=str(_assets)), name="img")

_dist = _activity_dist()
if _dist is not None:
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="activity")
else:
    print(
        "[bridge] activity bundle not found — serving API/WS only. "
        "Set ACTIVITY_DIST=/path/to/apps/activity/dist to serve the UI."
    )


async def _auto_tick() -> None:
    while True:
        await asyncio.sleep(1)
        now = time.monotonic()
        for room in list(rooms.rooms.values()):
            state = room.state
            previous = _watch_wall_time.get(room.channel_id, now)
            _watch_wall_time[room.channel_id] = now
            if state.status != "running" or state.timeFrozen:
                continue
            mode = state.timeMode
            # Legacy clients only know autoTick; retain their one-minute pulse.
            if mode == "paused" and state.autoTick:
                mode, scale = "slow", 1.0
            else:
                scale = {"paused": 0.0, "slow": 1.0, "fast": 4.0, "warp": 60.0}[mode]
            if scale <= 0:
                continue
            elapsed = min(5.0, max(0.0, now - previous))
            advance(state, elapsed * scale / 60.0)
            # Decision events and terminal races are natural interrupts: leave
            # fast mode enabled for the client to acknowledge, but stop the
            # server clock so it cannot skip the decision.
            if state.events or state.outcome is not None:
                state.timeMode = "paused"
                state.timeScale = 0.0
                state.autoTick = False
            await room.broadcast()


def _start_admin_thread() -> None:
    global _lifespan_admin_started
    if not ADMIN_PORT or _lifespan_admin_started:
        return
    if not ADMIN_TOKEN.strip():
        raise RuntimeError("ADMIN_TOKEN is required when ADMIN_PORT is set")
    _lifespan_admin_started = True
    admin_app = create_admin_app(ADMIN_TOKEN)
    thread = threading.Thread(
        target=uvicorn.run,
        args=(admin_app,),
        kwargs={
            "host": ADMIN_HOST,
            "port": ADMIN_PORT,
            "log_level": "info",
        },
        name="bridge-admin",
        daemon=True,
    )
    thread.start()


def main() -> None:
    init_db(DATA_DIR)
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
