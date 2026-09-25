"""CAPTAIN client websocket endpoint.

Direct port of ``apps/server/src/ws.ts``.  The ``ws`` npm server becomes a
FastAPI/Starlette websocket route registered by :func:`attach_ws`; the
per-connection ``pending`` WeakMap becomes a module-level dict keyed by the
websocket object.
"""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from ..shared.constants import DEFAULT_ADVANCE_MINUTES
from ..shared.protocol import MsgError, MsgHelloS2C, parse_c2s
from ..shared.ships import SHIP_CLASSES
from ..shared.types import SeatId
from .engine import (
    active_sweep,
    add_note,
    advance,
    call_iff,
    claim_contact,
    deploy_buoy,
    deploy_noisemaker,
    end_campaign,
    filter_noise,
    force_handoff,
    grav_scan,
    ignore_contact,
    inspect_dc,
    maintain_system,
    repair_system,
    intercept_comms,
    transmit_comms,
    listen_waveform,
    prep_weapons,
    recover_buoy,
    report_contact,
    resolve_event,
    resume_after_handoff,
    set_active_sensor,
    set_alert,
    set_altitude,
    set_condition,
    set_emcon,
    set_mode,
    set_speed,
    abort_jump,
    clear_baffles,
    commit_course,
    fix_nav,
    deploy_spoof,
    board_prize,
    fit_module,
    launch_small_craft,
    recover_small_craft,
    rally_crew,
    unfit_module,
    replenish,
    salvage_spares,
    set_heat_mode,
    set_watch_bill,
    set_maneuver,
    set_posture,
    set_target_system,
    shoot_down_ordnance,
    start_tma,
    commit_jump,
    plot_course,
    spool_jump,
    set_waypoints,
    survey_nav,
    sniff,
    standdown_weapons,
)
from .rooms import Client, Room, public_state, rooms

# Per-connection pending identity until 'hello' arrives.
@dataclass
class Pending:
    client: Client
    channelId: str | None = None
    instanceId: str | None = None
    userId: str | None = None
    name: str | None = None
    sessionId: str | None = None


pending: dict[Any, Pending] = {}


def attach_ws(app: FastAPI):
    """Register the ``/ws`` route on ``app``.

    Returns the app so ``attach_ws(app)`` can be used as a statement.
    """

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        p = Pending(client=Client(userId="pending", name="…", ws=websocket))
        pending[websocket] = p

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                except Exception:
                    await _send_text(websocket, MsgError(message="bad json"))
                    continue
                try:
                    msg = parse_c2s(data)
                except Exception:
                    # Well-formed JSON with an unknown `type` falls through the
                    # TS switch silently; only malformed JSON errors.
                    continue
                await handle(websocket, msg)
        except WebSocketDisconnect:
            pass
        except Exception:
            # Mirror the bare ``ws.on('error', () => {})`` — never let a
            # single bad connection take the server down.
            pass
        finally:
            await _cleanup(websocket, p)

    return app


async def _cleanup(websocket: WebSocket, p: Pending) -> None:
    pending.pop(websocket, None)
    if p.sessionId:
        channel = p.channelId
        if channel and rooms.has(channel):
            room = rooms.get(channel, p.instanceId or "")
            room.disconnect(p.sessionId)
            if len(room.clients) == 0:
                room.schedule_save()
            else:
                await room.broadcast()


async def _send_text(ws: Any, msg: Any) -> None:
    try:
        await ws.send_text(msg.model_dump_json())
    except Exception:
        pass


async def handle(websocket: WebSocket, msg: Any) -> None:
    msg_type = getattr(msg, "type", None)

    if msg_type == "hello":
        p = pending.get(websocket)
        if p is None:
            return
        hello = msg.hello
        # One session per connection.  Reuse the client's per-tab session id when
        # it supplies one (so a reconnect keeps its seat); otherwise mint one.
        session_id = (hello.sessionId or "").strip() or f"s-{uuid.uuid4().hex[:12]}"
        p.channelId = hello.channelId
        p.instanceId = hello.instanceId
        p.userId = hello.userId
        p.name = hello.name
        p.sessionId = session_id
        p.client.userId = hello.userId
        p.client.name = hello.name
        p.client.sessionId = session_id
        room = rooms.get(hello.channelId, hello.instanceId)
        room.join(p.client)
        hello = MsgHelloS2C(
            clientId=session_id,
            state=room.state,
            catalogue=list(SHIP_CLASSES.values()),
        ).model_dump(mode="json")
        hello["state"] = public_state(room.state)
        await websocket.send_text(json.dumps(hello, separators=(",", ":")))
        await room.broadcast()
        return

    if msg_type == "setSeat":

        async def _set_seat(room: Room, user_id: str) -> None:
            room.release_seat(user_id)
            if msg.seat:
                seat = room.state.seats.get(msg.seat)
                if seat is not None and seat.player is not None:
                    owner = seat.player.sessionId or seat.player.userId
                    if owner not in room.clients:
                        seat.player = None
                        room.state.seq += 1
                if seat is not None and seat.player is None:
                    seat.player = _seat_player(room, user_id)
                    room.state.seq += 1
                elif seat is not None and user_id == room.state.hostSession:
                    seat.player = _seat_player(room, user_id)
                    room.state.seq += 1
            room.sync_host()
            await room.broadcast()

        await with_room(websocket, _set_seat)
        return

    if msg_type == "start":

        async def _start(room: Room, user_id: str) -> None:
            if host_or_command(room, user_id):
                if room.state.status == "lobby":
                    room.state.status = "running"
                    await room.broadcast()

        await with_cmd(websocket, _start)
        return

    if msg_type == "advance":

        async def _advance(room: Room, user_id: str) -> None:
            if not host_or_command(room, user_id):
                return
            minutes = min(480, max(15, _js_round(msg.minutes)))
            if room.state.status == "running":
                advance(room.state, minutes)
                await room.broadcast()

        await with_cmd(websocket, _advance)
        return

    if msg_type == "setAutoTick":

        async def _set_auto_tick(room: Room, user_id: str) -> None:
            if not host_or_command(room, user_id):
                return
            room.state.autoTick = msg.on
            room.state.timeMode = "slow" if msg.on else "paused"
            room.state.timeScale = 1.0
            await room.broadcast()

        await with_cmd(websocket, _set_auto_tick)
        return

    if msg_type == "setTimeMode":

        async def _set_time_mode(room: Room, user_id: str) -> None:
            if not host_or_command(room, user_id):
                return
            room.state.timeMode = msg.mode
            room.state.timeScale = {"paused": 0.0, "slow": 1.0, "fast": 4.0, "warp": 60.0}[msg.mode]
            room.state.autoTick = msg.mode != "paused"
            await room.broadcast()

        await with_cmd(websocket, _set_time_mode)
        return

    if msg_type == "condition":

        async def _condition(room: Room, user_id: str) -> None:
            if not host_or_command(room, user_id):
                return
            set_condition(room.state, msg.value)
            await room.broadcast()

        await with_cmd(websocket, _condition)
        return

    if msg_type == "roe":

        async def _roe(room: Room, user_id: str) -> None:
            room.state.ship.roe = msg.value
            room.state.seq += 1
            await room.broadcast()

        await with_seat(websocket, ["command"], _roe)
        return

    if msg_type == "setAlert":

        async def _alert(room: Room, user_id: str) -> None:
            set_alert(room.state, msg.level)
            await room.broadcast()

        await with_seat(websocket, ["command"], _alert)
        return

    if msg_type == "resolveEvent":

        async def _resolve_event(room: Room, user_id: str) -> None:
            if not host_or_command(room, user_id):
                return
            resolve_event(room.state, msg.eventId, msg.optionId)
            await room.broadcast()

        await with_cmd(websocket, _resolve_event)
        return

    if msg_type == "handoff:force":

        async def _force_handoff(room: Room, user_id: str) -> None:
            if not host_or_command(room, user_id):
                return
            force_handoff(room.state, name_of(room, user_id))
            await room.broadcast()

        await with_cmd(websocket, _force_handoff)
        return

    if msg_type == "resume":

        async def _resume(room: Room, user_id: str) -> None:
            if not host_or_command(room, user_id):
                return
            resume_after_handoff(room.state)
            await room.broadcast()

        await with_cmd(websocket, _resume)
        return

    if msg_type == "end":

        async def _end(room: Room, user_id: str) -> None:
            if not host_or_command(room, user_id):
                return
            end_campaign(room.state)
            await room.broadcast()

        await with_cmd(websocket, _end)
        return

    if msg_type == "nav:waypoints":

        async def _waypoints(room: Room, user_id: str) -> None:
            set_waypoints(room.state, list(msg.waypoints)[:6])
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _waypoints)
        return

    if msg_type == "nav:plot":

        async def _plot(room: Room, user_id: str) -> None:
            plot_course(room.state, msg.navId)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _plot)
        return

    if msg_type == "nav:commit":

        async def _commit(room: Room, user_id: str) -> None:
            commit_course(room.state, msg.navId)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _commit)
        return

    if msg_type == "nav:survey":

        async def _survey(room: Room, user_id: str) -> None:
            survey_nav(room.state, msg.navId)
            await room.broadcast()

        await with_seat(websocket, ["sensor", "command"], _survey)
        return

    if msg_type == "nav:fix":

        async def _fix(room: Room, user_id: str) -> None:
            fix_nav(room.state, msg.method)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _fix)
        return

    if msg_type == "ops:posture":

        async def _posture(room: Room, user_id: str) -> None:
            set_posture(room.state, msg.posture)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _posture)
        return

    if msg_type == "sensor:clearBaffles":

        async def _clear_baffles(room: Room, user_id: str) -> None:
            clear_baffles(room.state)
            await room.broadcast()

        await with_seat(websocket, ["sensor", "command"], _clear_baffles)
        return

    if msg_type == "ops:tma":

        async def _tma(room: Room, user_id: str) -> None:
            start_tma(room.state, msg.contactId)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _tma)
        return

    if msg_type == "ops:maneuver":

        async def _maneuver(room: Room, user_id: str) -> None:
            set_maneuver(room.state, msg.maneuver)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _maneuver)
        return

    if msg_type == "weapons:targetSystem":

        async def _target_system(room: Room, user_id: str) -> None:
            set_target_system(room.state, msg.system)
            await room.broadcast()

        await with_seat(websocket, ["comms", "command"], _target_system)
        return

    if msg_type == "sensor:shootOrdnance":

        async def _shoot_ordnance(room: Room, user_id: str) -> None:
            shoot_down_ordnance(room.state, msg.ordnanceId)
            await room.broadcast()

        await with_seat(websocket, ["sensor", "comms", "command"], _shoot_ordnance)
        return

    if msg_type == "sensor:spoof":

        async def _spoof(room: Room, user_id: str) -> None:
            deploy_spoof(room.state)
            await room.broadcast()

        await with_seat(websocket, ["sensor", "command"], _spoof)
        return

    if msg_type == "ops:heat":

        async def _heat(room: Room, user_id: str) -> None:
            set_heat_mode(room.state, msg.mode)
            await room.broadcast()

        await with_seat(websocket, ["command", "ops", "sensor", "comms"], _heat)
        return

    if msg_type == "ops:watch":

        async def _watch(room: Room, user_id: str) -> None:
            set_watch_bill(room.state, msg.bill)
            await room.broadcast()

        await with_seat(websocket, ["command", "ops"], _watch)
        return

    if msg_type == "ops:rally":

        async def _rally(room: Room, user_id: str) -> None:
            rally_crew(room.state)
            await room.broadcast()

        await with_seat(websocket, ["command"], _rally)
        return

    if msg_type == "ops:hangar":

        async def _hangar(room: Room, user_id: str) -> None:
            if msg.launch:
                launch_small_craft(room.state)
            else:
                recover_small_craft(room.state)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _hangar)
        return

    if msg_type == "comms:board":

        async def _board(room: Room, user_id: str) -> None:
            board_prize(room.state, msg.contactId)
            await room.broadcast()

        await with_seat(websocket, ["comms", "command"], _board)
        return

    if msg_type == "dc:fitModule":

        async def _fit_module(room: Room, user_id: str) -> None:
            fit_module(room.state, msg.moduleId)
            await room.broadcast()

        await with_seat(websocket, [], _fit_module)
        return

    if msg_type == "dc:unfitModule":

        async def _unfit_module(room: Room, user_id: str) -> None:
            unfit_module(room.state, msg.moduleId)
            await room.broadcast()

        await with_seat(websocket, [], _unfit_module)
        return

    if msg_type == "dc:salvage":

        async def _salvage(room: Room, user_id: str) -> None:
            salvage_spares(room.state)
            await room.broadcast()

        await with_seat(websocket, [], _salvage)
        return

    if msg_type == "nav:replenish":

        async def _replenish(room: Room, user_id: str) -> None:
            replenish(room.state)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _replenish)
        return

    if msg_type == "jump:spool":

        async def _spool(room: Room, user_id: str) -> None:
            spool_jump(room.state, msg.navId)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _spool)
        return

    if msg_type == "jump:commit":

        async def _jump_commit(room: Room, user_id: str) -> None:
            commit_jump(room.state)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _jump_commit)
        return

    if msg_type == "jump:abort":

        async def _jump_abort(room: Room, user_id: str) -> None:
            abort_jump(room.state)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _jump_abort)
        return

    if msg_type == "nav:speed":

        async def _speed(room: Room, user_id: str) -> None:
            set_speed(room.state, msg.kps)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _speed)
        return

    if msg_type == "nav:mode":

        async def _mode(room: Room, user_id: str) -> None:
            set_mode(room.state, msg.mode)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _mode)
        return

    if msg_type == "nav:altitude":

        async def _altitude(room: Room, user_id: str) -> None:
            set_altitude(room.state, msg.z)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _altitude)
        return

    if msg_type == "nav:deployBuoy":

        async def _deploy_buoy(room: Room, user_id: str) -> None:
            deploy_buoy(room.state)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _deploy_buoy)
        return

    if msg_type == "nav:recoverBuoy":

        async def _recover_buoy(room: Room, user_id: str) -> None:
            recover_buoy(room.state, msg.buoyId)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _recover_buoy)
        return

    if msg_type == "intel:report":

        async def _report(room: Room, user_id: str) -> None:
            report_contact(room.state, msg.contactId)
            await room.broadcast()

        await with_seat(websocket, ["ops", "command"], _report)
        return

    if msg_type == "ew:noisemaker":

        async def _noisemaker(room: Room, user_id: str) -> None:
            deploy_noisemaker(room.state)
            await room.broadcast()

        await with_seat(websocket, ["sensor", "command"], _noisemaker)
        return

    if msg_type == "sensor:activeSweep":

        async def _active_sweep(room: Room, user_id: str) -> None:
            active_sweep(room.state)
            await room.broadcast()

        await with_seat(websocket, ["sensor", "command"], _active_sweep)
        return

    if msg_type == "sensor:active":

        async def _sensor_active(room: Room, user_id: str) -> None:
            set_active_sensor(room.state, msg.on)
            await room.broadcast()

        await with_seat(websocket, ["sensor", "command"], _sensor_active)
        return

    if msg_type == "sensor:noiseFilter":

        async def _noise_filter(room: Room, user_id: str) -> None:
            filter_noise(room.state)
            await room.broadcast()

        await with_seat(websocket, ["sensor", "command"], _noise_filter)
        return

    if msg_type == "sensor:claim":

        async def _claim(room: Room, user_id: str) -> None:
            claim_contact(room.state, msg.contactId, msg.guess)
            await room.broadcast()

        await with_seat(websocket, ["sensor", "command"], _claim)
        return

    if msg_type == "sensor:ignore":

        async def _ignore(room: Room, user_id: str) -> None:
            ignore_contact(room.state, msg.contactId)
            await room.broadcast()

        await with_seat(websocket, ["sensor", "command"], _ignore)
        return

    if msg_type == "sensor:listen":

        async def _listen(room: Room, user_id: str) -> None:
            listen_waveform(room.state, msg.contactId)
            await room.broadcast()

        await with_seat(websocket, ["sensor", "command"], _listen)
        return

    if msg_type == "sensor:gravScan":

        async def _grav_scan(room: Room, user_id: str) -> None:
            grav_scan(room.state)
            await room.broadcast()

        await with_seat(websocket, ["sensor", "command"], _grav_scan)
        return

    if msg_type == "ew:emcon":

        async def _emcon(room: Room, user_id: str) -> None:
            set_emcon(room.state, msg.emcon)
            await room.broadcast()

        await with_seat(websocket, ["sensor", "command"], _emcon)
        return

    if msg_type == "ew:sniff":

        async def _sniff(room: Room, user_id: str) -> None:
            sniff(room.state)
            await room.broadcast()

        await with_seat(websocket, ["sensor", "command"], _sniff)
        return

    if msg_type == "comms:iff":

        async def _iff(room: Room, user_id: str) -> None:
            call_iff(room.state, msg.contactId)
            await room.broadcast()

        await with_seat(websocket, ["comms", "command"], _iff)
        return

    if msg_type == "comms:intercept":

        async def _intercept(room: Room, user_id: str) -> None:
            intercept_comms(room.state)
            await room.broadcast()

        await with_seat(websocket, ["comms", "command"], _intercept)
        return

    if msg_type == "comms:transmit":

        async def _transmit(room: Room, user_id: str) -> None:
            transmit_comms(room.state, msg.mode)
            await room.broadcast()

        await with_seat(websocket, ["comms", "command"], _transmit)
        return

    if msg_type == "weapons:prep":

        async def _prep(room: Room, user_id: str) -> None:
            prep_weapons(room.state, msg.contactId, msg.state, msg.weapon, msg.shot)
            await room.broadcast()

        await with_seat(websocket, ["comms", "command"], _prep)
        return

    if msg_type == "weapons:standdown":

        async def _standdown(room: Room, user_id: str) -> None:
            standdown_weapons(room.state)
            await room.broadcast()

        await with_seat(websocket, ["comms", "command"], _standdown)
        return

    if msg_type == "dc:inspect":

        async def _inspect(room: Room, user_id: str) -> None:
            inspect_dc(room.state)
            await room.broadcast()

        await with_seat(websocket, [], _inspect)
        return

    if msg_type == "dc:repair":

        async def _repair(room: Room, user_id: str) -> None:
            repair_system(room.state, msg.system, jury_rig=msg.juryRig)
            await room.broadcast()

        await with_seat(websocket, [], _repair)
        return

    if msg_type == "dc:maintain":

        async def _maintain(room: Room, user_id: str) -> None:
            maintain_system(room.state, msg.system)
            await room.broadcast()

        await with_seat(websocket, [], _maintain)
        return

    if msg_type == "rp:note":

        async def _note(room: Room, user_id: str) -> None:
            add_note(room.state, name_of(room, user_id), msg.text[:300])
            await room.broadcast()

        await with_seat(websocket, [], _note)
        return

    # Unknown message types are ignored, matching the TS switch fall-through.


async def with_room(
    websocket: WebSocket, fn: Callable[[Room, str], Awaitable[None]]
) -> None:
    p = pending.get(websocket)
    if p is None or not p.channelId or not p.sessionId:
        await _send_text(websocket, MsgError(message="hello first"))
        return
    room = rooms.get(p.channelId, p.instanceId or "")
    # The callback receives the *session* id — seats and host authority are per
    # connection.
    await fn(room, p.sessionId)


async def with_cmd(
    websocket: WebSocket, fn: Callable[[Room, str], Awaitable[None]]
) -> None:
    await with_room(websocket, fn)


async def with_seat(
    websocket: WebSocket,
    allowed: list[SeatId],
    fn: Callable[[Room, str], Awaitable[None]],
) -> None:
    async def _wrapped(room: Room, user_id: str) -> None:
        seat = room.seat_of(user_id)
        if not seat:
            await _send_text(websocket, MsgError(message="you are not seated"))
            return
        if allowed and seat not in allowed:
            await _send_text(
                websocket,
                MsgError(message="that panel belongs to another seat"),
            )
            return
        await fn(room, user_id)

    await with_room(websocket, _wrapped)


def host_or_command(room: Room, session_id: str) -> bool:
    if room.state.hostSession == session_id:
        return True
    command = room.state.seats.get("command")
    return command is not None and command.player is not None and command.player.sessionId == session_id


def name_of(room: Room, session_id: str) -> str:
    cl = room.clients.get(session_id)
    if cl is not None:
        return cl.name
    for s in room.state.seats.values():
        if s.player is not None and s.player.sessionId == session_id:
            return s.player.name
    return "Crew"


def _seat_player(room: Room, session_id: str):
    from ..shared.types import SeatPlayer

    cl = room.clients.get(session_id)
    user_id = cl.userId if cl is not None else session_id
    return SeatPlayer(userId=user_id, name=name_of(room, session_id), sessionId=session_id)


def _js_round(value: float) -> int:
    """``Math.round`` rounds halves toward +inf, unlike Python's ``round``."""
    return math.floor(value + 0.5)


__all__ = ["attach_ws", "rooms", "pending", "handle", "DEFAULT_ADVANCE_MINUTES"]
