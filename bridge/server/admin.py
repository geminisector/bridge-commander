"""BRIDGE COMMANDER game-master / opposition-builder admin app.

Direct port of ``apps/server/src/admin.ts``: a second FastAPI app (served on
``ADMIN_PORT``) with a token-gated websocket the admin UI connects to at the
server root, plus static serving of ``admin-ui/index.html`` when present.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from ..shared import campaign_for, clamp, ship_briefs
from ..shared.campaigns import campaign_briefs
from ..shared.protocol import MsgAdminError, MsgAdminOk, MsgAdminState, parse_admin_c2s
from ..shared.types import (
    AdminChannel,
    AdminFlavorBrief,
    AdminPlayer,
    CampaignBrief,
    GameState,
    Patrol,
    Vec,
)
from .admin_events import clean_event
from .config import ADMIN_ORIGINS
from .engine import (
    create_state,
    gm_event,
    log,
    patch_opposition,
    remove_opposition,
    launch_ordnance,
    set_drive,
    set_seat_skills,
    set_ship_class,
    set_time_frozen,
    spawn_opposition,
)
from ..shared.checks import ALL_SKILLS
from . import mods
from .rooms import rooms

_ADMIN_UI_DIR = Path(__file__).resolve().parent / "admin-ui"

_PLACEHOLDER_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>BRIDGE COMMANDER admin</title></head>
<body style="font-family:system-ui;background:#0b0f14;color:#c8d6e5;padding:2rem">
<h1>BRIDGE COMMANDER — game master console</h1>
<p>The admin UI bundle (<code>admin-ui/index.html</code>) was not found next to
the Python server. The admin websocket is live on this origin at
<code>/</code>.</p>
</body></html>"""


@dataclass
class Sub:
    ws: WebSocket
    authed: bool = False
    subscribed: str | None = None
    unsub: Callable[[], None] | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def create_admin_app(token: str) -> FastAPI:
    if not token.strip():
        raise ValueError("ADMIN_TOKEN must not be empty")
    app = FastAPI(title="BRIDGE COMMANDER admin")

    allowed = ADMIN_ORIGINS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if "*" in allowed else list(allowed),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    subs: dict[Any, Sub] = {}

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "roles": "admin", "time": _now_iso()}

    @app.websocket("/")
    async def admin_ws(websocket: WebSocket) -> None:
        await websocket.accept()
        sub = Sub(ws=websocket)
        subs[websocket] = sub
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = parse_admin_c2s(raw)
                except Exception:
                    continue
                await _handle(websocket, msg, token, subs)
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            s = subs.pop(websocket, None)
            if s is not None and s.unsub is not None:
                s.unsub()

    if _ADMIN_UI_DIR.is_dir() and (_ADMIN_UI_DIR / "index.html").is_file():
        app.mount("/", StaticFiles(directory=str(_ADMIN_UI_DIR), html=True), name="admin-ui")
    else:

        @app.get("/")
        async def placeholder() -> HTMLResponse:
            return HTMLResponse(_PLACEHOLDER_HTML)

    return app


async def _handle(
    websocket: WebSocket, msg: Any, token: str, subs: dict[Any, Sub]
) -> None:
    s = subs.get(websocket)
    if s is None:
        return

    if msg.type == "admin.hello":
        if msg.token != token:
            await _send(websocket, MsgAdminError(message="bad or missing admin token"))
            await websocket.close()
            return
        s.authed = True
        await _send(websocket, _admin_snapshot())
        return

    if not s.authed:
        await _send(websocket, MsgAdminError(message="admin.hello first"))
        return

    if msg.type == "admin.list":
        base = _admin_snapshot(msg.channelId)
        if msg.channelId:
            base.channels = [
                c for c in base.channels if c.channelId == msg.channelId
            ]
        await _send(websocket, base)
        return

    if msg.type == "admin.subscribe":
        room = rooms.rooms.get(msg.channelId)
        if room is None:
            await _send(
                websocket,
                MsgAdminError(message="no such room on this server"),
            )
            return
        if s.unsub is not None:
            s.unsub()

        async def _listener(state: GameState, _room=room, _ws=websocket) -> None:
            await _send(
                _ws,
                MsgAdminState(channelId=_room.channel_id, state=state),
            )

        s.unsub = room.on_state(_listener)
        s.subscribed = msg.channelId
        await _send(
            websocket,
            MsgAdminState(channelId=msg.channelId, state=room.state),
        )
        return

    if msg.type == "admin.spawn":
        room = _room_for(msg.channelId)
        c = spawn_opposition(room.state, msg.contact)
        if c is None:
            await _send(websocket, MsgAdminError(message="spawn failed"))
            return
        await room.broadcast()
        await _send(websocket, MsgAdminState(channelId=room.channel_id, state=room.state))
        return

    if msg.type == "admin.update":
        room = _room_for(msg.channelId)
        if not patch_opposition(room.state, msg.contactId, msg.patch):
            await _send(websocket, MsgAdminError(message="unknown contact"))
            return
        await room.broadcast()
        await _send(websocket, MsgAdminState(channelId=room.channel_id, state=room.state))
        return

    if msg.type == "admin.remove":
        room = _room_for(msg.channelId)
        if not remove_opposition(room.state, msg.contactId):
            await _send(websocket, MsgAdminError(message="unknown contact"))
            return
        await room.broadcast()
        await _send(websocket, MsgAdminState(channelId=room.channel_id, state=room.state))
        return

    if msg.type == "admin.tension":
        room = _room_for(msg.channelId)
        room.state.war.tension = clamp(msg.value, 0, 100)
        await room.broadcast()
        await _send(websocket, MsgAdminState(channelId=room.channel_id, state=room.state))
        return

    if msg.type == "admin.event":
        room = _room_for(msg.channelId)
        ev = clean_event(room.state, msg.event)
        gm_event(room.state, ev)
        log(room.state, "COMMAND", f"GM injects: {ev.title}.", "danger")
        await room.broadcast()
        await _send(websocket, MsgAdminState(channelId=room.channel_id, state=room.state))
        return

    if msg.type == "admin.layout":
        room = _room_for(msg.channelId)
        z = msg.center.z if msg.center.z is not None else 0
        room.state.campaign.patrol = Patrol(
            center=Vec(
                x=clamp(msg.center.x, -400, 400),
                y=clamp(msg.center.y, -400, 400),
                z=clamp(z, -400, 400),
            ),
            radiusKlik=clamp(msg.radiusKlik, 20, 200),
        )
        await room.broadcast()
        await _send(websocket, MsgAdminState(channelId=room.channel_id, state=room.state))
        return

    if msg.type == "admin.setShip":
        room = _room_for(msg.channelId)
        set_ship_class(room.state, msg.shipId)
        await room.broadcast()
        await _send(websocket, MsgAdminState(channelId=room.channel_id, state=room.state))
        return

    if msg.type == "admin.freeze":
        room = _room_for(msg.channelId)
        set_time_frozen(room.state, msg.frozen)
        await room.broadcast()
        await _send(websocket, MsgAdminState(channelId=room.channel_id, state=room.state))
        return

    if msg.type == "admin.torpedo":
        room = _room_for(msg.channelId)
        launch_ordnance(room.state, kind=msg.kind)
        await room.broadcast()
        await _send(websocket, MsgAdminState(channelId=room.channel_id, state=room.state))
        return

    if msg.type == "admin.setDrive":
        room = _room_for(msg.channelId)
        set_drive(room.state, msg.drive)
        await room.broadcast()
        await _send(websocket, MsgAdminState(channelId=room.channel_id, state=room.state))
        return

    if msg.type == "admin.skills":
        room = _room_for(msg.channelId)
        if not set_seat_skills(
            room.state, msg.seat, msg.scores, msg.specializations
        ):
            await _send(websocket, MsgAdminError(message="unknown seat"))
            return
        await room.broadcast()
        await _send(websocket, MsgAdminState(channelId=room.channel_id, state=room.state))
        return

    if msg.type == "admin.activateMod":
        ok, reason = mods.activate(msg.flavorId)
        if not ok:
            await _send(websocket, MsgAdminError(message=reason))
            return
        await _send(websocket, _admin_snapshot())
        return

    if msg.type == "admin.deactivateMod":
        ok, reason = mods.deactivate(msg.flavorId)
        if not ok:
            await _send(websocket, MsgAdminError(message=reason))
            return
        await _send(websocket, _admin_snapshot())
        return

    if msg.type == "admin.setDefaultMod":
        ok, reason = mods.set_default(msg.flavorId)
        if not ok:
            await _send(websocket, MsgAdminError(message=reason))
            return
        await _send(websocket, _admin_snapshot())
        return

    if msg.type == "admin.activateModForRoom":
        room = _room_for(msg.channelId)
        if not mods.is_enabled(msg.flavorId):
            await _send(
                websocket,
                MsgAdminError(message=f"mod {msg.flavorId!r} is not activated"),
            )
            return
        await room.reconfigure(flavor_id=msg.flavorId)
        await _send(websocket, MsgAdminState(channelId=room.channel_id, state=room.state))
        await _send(websocket, _admin_snapshot(room.channel_id))
        return

    if msg.type == "admin.kick":
        room = rooms.rooms.get(msg.channelId)
        if room is None or msg.sessionId not in room.clients:
            await _send(websocket, MsgAdminError(message="unknown player"))
            return
        client = room.clients[msg.sessionId]
        await client.ws.close(code=4001, reason="Removed by game master")
        room.leave(msg.sessionId)
        await room.broadcast()
        await _send(websocket, _admin_snapshot())
        return

    if msg.type == "admin.reset":
        room = _room_for(msg.channelId)
        instance_id = room.state.room.instanceId or "gm-prep"
        if msg.flavorId and not mods.is_enabled(msg.flavorId):
            await _send(
                websocket,
                MsgAdminError(message=f"mod {msg.flavorId!r} is not activated"),
            )
            return
        flavor_id = msg.flavorId or mods.guard_room(room.state.flavorId)
        fresh = create_state(
            room.channel_id,
            instance_id,
            campaign_for(msg.campaignId, flavor_id),
            ship_id=msg.shipId,
            flavor_id=flavor_id,
        )
        fresh.room.instanceId = instance_id
        await room.reset(fresh)
        await _send(websocket, MsgAdminState(channelId=room.channel_id, state=room.state))
        return


def _admin_snapshot(channel_id: str | None = None) -> MsgAdminOk:
    room = rooms.rooms.get(channel_id) if channel_id else None
    flavor_id = room.state.flavorId if room is not None else mods.default_flavor()
    players = [
        AdminPlayer(
            sessionId=client.sessionId,
            userId=client.userId,
            name=client.name,
            channelId=channel_id,
            seat=room.seat_of(client.sessionId),
        )
        for channel_id, room in rooms.rooms.items()
        for client in room.clients.values()
    ]
    return MsgAdminOk(
        token=False,
        channels=[
            AdminChannel(
                channelId=channel_id,
                title=room.state.campaign.title,
                status=room.state.status,
                players=len(room.clients),
                hostId=room.state.hostId,
                flavorId=room.state.flavorId,
            )
            for channel_id, room in rooms.rooms.items()
        ],
        campaigns=[
            CampaignBrief(id=mission_id, title=title, theater=theater)
            for mission_id, title, theater in campaign_briefs(flavor_id)
        ],
        ships=ship_briefs(flavor_id),
        flavors=[
            AdminFlavorBrief(
                id=row["id"],
                title=row["title"],
                extends=row.get("extends"),
                hulls=row.get("hulls", 0),
                missions=row.get("missions", 0),
                valid=bool(row.get("valid", True)),
                error=row.get("error", ""),
                enabled=bool(row.get("enabled", False)),
                default=bool(row.get("default", False)),
                core=bool(row.get("core", False)),
            )
            for row in mods.list_mods()
        ],
        players=players,
        skills=list(ALL_SKILLS),
    )


def admin_snapshot() -> MsgAdminOk:
    return _admin_snapshot()


def _room_for(channel_id: str):
    return rooms.get(channel_id, "gm-prep")


def room_for(channel_id: str):
    return _room_for(channel_id)


async def _send(websocket: WebSocket, msg: Any) -> None:
    from .rooms import _ws_open

    if _ws_open(websocket):
        try:
            await websocket.send_text(msg.model_dump_json())
        except Exception:
            pass


__all__ = ["create_admin_app", "admin_snapshot", "room_for", "Sub"]
