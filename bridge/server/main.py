"""BRIDGE COMMANDER server entry point.

Direct port of ``apps/server/src/index.ts``.  Run with::

    python -m bridge

which starts the FastAPI app (client websocket + health + optional static
activity bundle) on ``PORT`` and, when ``ADMIN_PORT`` is set, the admin app on
its own port in a background thread.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, Response

from ..paths import asset_root, asset_roots, package_path
from ..shared.flavors import format_summary, get as get_flavor
from .admin import create_admin_app
from .config import (
    ACTIVITY_DIST,
    ADMIN_HOST,
    ADMIN_PORT,
    ADMIN_TOKEN,
    ASSET_DIR,
    CORS_ORIGINS,
    DATA_DIR,
    DEFAULT_FLAVOR,
    HOST,
    JITSI_DOMAIN,
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
    _report_flavors()
    tick_task = asyncio.create_task(_auto_tick())
    _start_admin_thread()
    try:
        yield
    finally:
        tick_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await tick_task


def _report_flavors() -> None:
    """Validate and advertise the installed settings at startup.

    A flavor that fails validation is already failing closed (``get`` falls back
    to core); this makes the whole catalog inspectable in one log line.
    """
    from . import mods

    print(format_summary())
    if DEFAULT_FLAVOR:
        print(f"[bridge] DEFAULT_FLAVOR={DEFAULT_FLAVOR}")
    active = mods.active_mod()
    print(f"[bridge] active mod: {active}")
    # Force-load the active mod so a broken setting is reported now, not at the
    # first websocket hello.
    resolved = get_flavor(active)
    print(f"[bridge] serving rooms on flavor: {resolved.id} ({resolved.title})")
    from ..shared.ships import audit_ship_art

    for finding in audit_ship_art(resolved.id):
        if finding.startswith("ERROR:"):
            print(f"[bridge] {resolved.id}: {finding}")


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


# ---------------------------------------------------------------------------
# Flavor serving
#
# A flavor's art and theme are served per flavor id, so two rooms on different
# settings in one process never see each other's files.  Core art keeps its
# historical /img/... URLs; flavor art lives under /img/f/<flavor>/....
# ---------------------------------------------------------------------------


def _room_flavor(request: Request) -> str:
    """The flavor the page's room is playing, or the activated default."""
    from . import mods

    channel_id = request.query_params.get("channelId") or ""
    room = rooms.rooms.get(channel_id) if channel_id else None
    if room is not None:
        return room.state.flavorId
    return mods.active_mod()


def _voice_bootstrap() -> str:
    """The Jitsi settings the activity client reads (see ``activity.js``).

    Returns ``""`` when voice is switched off, which also hides the tab.
    """
    domain = JITSI_DOMAIN.strip()
    if not domain:
        return ""
    payload = json.dumps({"domain": domain})
    # No ``<`` may survive into the tag, whatever the environment says.
    return f"<script>window.__BRIDGE_VOICE__={payload.replace('<', chr(92) + 'u003c')};</script>"


def _render_index(dist: Path, flavor_id: str) -> str:
    """Inject the flavor theme after activity.css, so it overrides cleanly.

    The link carries an id so the activity client can swap it in place when the
    room's mod changes without a page reload.  The voice bootstrap rides along
    here so the client knows which Jitsi domain to embed.
    """
    html = (dist / "index.html").read_text(encoding="utf-8")
    link = (
        f'<link rel="stylesheet" id="flavor-theme" '
        f'href="/flavor/{flavor_id}/theme.css">'
    )
    if link not in html:
        marker = '<link rel="stylesheet" href="/activity.css">'
        if marker in html:
            html = html.replace(marker, marker + "\n  " + link, 1)
        else:
            html = html.replace("</head>", "  " + link + "\n</head>", 1)
    voice = _voice_bootstrap()
    if voice and voice not in html:
        html = html.replace("</head>", "  " + voice + "\n</head>", 1)
    return html


@app.get("/", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
async def flavored_index(request: Request) -> Response:
    dist = _activity_dist()
    if dist is None:
        return HTMLResponse(
            "<h1>BRIDGE COMMANDER</h1><p>Activity bundle not found; "
            "set ACTIVITY_DIST to serve the UI.</p>",
            status_code=200,
        )
    return HTMLResponse(_render_index(dist, _room_flavor(request)))


@app.get("/flavor/{flavor_id}/theme.css", include_in_schema=False)
async def flavor_theme(flavor_id: str) -> Response:
    css = get_flavor(flavor_id).theme_css or get_flavor("core").theme_css
    return Response(content=css, media_type="text/css")


@app.get("/img/f/{flavor_id}/{kind}/{filename}", include_in_schema=False)
async def flavor_asset(flavor_id: str, kind: str, filename: str) -> Response:
    from ..shared.flavors import available

    if flavor_id not in set(available()):
        return Response(status_code=404)
    for root in asset_roots(flavor_id):
        candidate = root / kind / filename
        if candidate.is_file():
            return FileResponse(candidate)
    return Response(status_code=404)


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
    """Run the server, or inspect the installed flavors from the CLI.

    ``--flavor`` picks the setting new rooms start on (equivalent to the
    ``DEFAULT_FLAVOR`` environment variable); ``--list-flavors`` prints the
    catalog and exits, which is what flavor authors and CI use to check a new
    package without booting the game.
    """
    parser = argparse.ArgumentParser(
        prog="bridge", description="BRIDGE COMMANDER server"
    )
    parser.add_argument(
        "--flavor",
        default="",
        help="default setting for new rooms (overrides DEFAULT_FLAVOR)",
    )
    parser.add_argument(
        "--list-flavors",
        action="store_true",
        help="list installed flavors and exit",
    )
    parser.add_argument(
        "--check-flavor",
        action="append",
        default=[],
        metavar="ID",
        help="load and validate one flavor, then exit (repeatable)",
    )
    args, _unknown = parser.parse_known_args()
    if args.list_flavors:
        print(format_summary())
        return
    if args.check_flavor:
        from ..shared import flavors as _flavors

        status = 0
        for flavor_id in args.check_flavor:
            try:
                checked = _flavors.load_flavor(flavor_id)
            except _flavors.FlavorError as exc:
                print(f"FAIL {flavor_id}: {exc}")
                status = 1
                continue
            print(
                f"OK   {checked.id}: {checked.title} — "
                f"{len(checked.hull_defs)} hulls, {len(checked.missions)} missions"
            )
            for finding in checked.findings:
                print(f"     {finding}")
        raise SystemExit(status)
    if args.flavor:
        os.environ["DEFAULT_FLAVOR"] = args.flavor
        from ..shared import flavors as _flavors

        _flavors.reset_cache()
    init_db(DATA_DIR)
    if args.flavor:
        # ``--flavor`` is an operator activation, so it persists: the CLI choice
        # wins over whatever the console last selected.
        from . import mods

        ok, reason = mods.activate(args.flavor)
        if not ok:
            print(f"[bridge] --flavor {args.flavor}: {reason}")
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
