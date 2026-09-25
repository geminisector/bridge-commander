"""Room registry and per-channel game state fan-out.

Direct port of ``apps/server/src/rooms.ts``.  The TypeScript ``setTimeout``
debounced save becomes an asyncio timer (with a threading.Timer fallback for
callers with no running loop); ``broadcast``/``reset`` are now ``async`` because
sending over a FastAPI/Starlette websocket is asynchronous.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import threading
from dataclasses import dataclass
from typing import Any, Callable

from ..shared.campaigns import campaign_for
from ..shared.types import GameState, SeatId
from .db import load_room, save_room
from .engine import create_state

SAVE_DEBOUNCE_SECONDS = 0.15


@dataclass
class Client:
    # ``sessionId`` keys the connection; ``userId`` is the Discord/browser id.
    userId: str
    name: str
    ws: Any
    sessionId: str = ""


StateListener = Callable[[GameState], Any]
Unsubscribe = Callable[[], None]


def public_state(state: GameState) -> dict[str, Any]:
    data = state.model_dump(mode="json")
    data["campaign"]["contacts"] = []
    own_pos = data["ship"]["pos"]
    for index, contact in enumerate(data["contacts"], start=1):
        visible = bool(contact["detected"])
        confirmed = visible and contact["state"] == "confirmed"
        solution_locked = (
            visible
            and state.ship.weaponsState == "locked"
            and state.ship.weaponTarget == contact["id"]
        )
        hull_revealed = confirmed or solution_locked
        contact["name"] = contact["name"] if confirmed else f"TRACK-{index:02d}"
        contact["trueName"] = contact["name"] if confirmed else ""
        contact["trueType"] = contact["guess"] if confirmed and contact["guess"] != "unknown" else "unknown"
        contact["faction"] = contact["faction"] if confirmed else "neutral"
        contact["hostile"] = bool(contact["hostile"]) if confirmed else False
        contact["shipClass"] = contact["shipClass"] if hull_revealed else ""
        contact["profile"] = contact["profile"] if hull_revealed else 0.0
        contact["stealth"] = contact["stealth"] if hull_revealed else 0.0
        contact["emission"] = contact["emission"] if hull_revealed else 0.0
        contact["sensorQuality"] = contact["sensorQuality"] if hull_revealed else 0.0
        contact["frequencyProfile"] = contact["frequencyProfile"] if hull_revealed else []
        contact["image"] = contact["image"] if hull_revealed else ""
        contact["vdu"] = contact["vdu"] if hull_revealed else ""
        contact["lock"] = contact["lock"] if state.status == "ended" else 0.0
        contact["hostileLock"] = bool(contact["hostileLock"]) if state.status == "ended" else False
        contact["everNear"] = bool(contact["everNear"]) if state.status == "ended" else False
        contact["everTrackedUs"] = bool(contact["everTrackedUs"]) if state.status == "ended" else False
        if not visible:
            contact.update(
                {
                    "pos": dict(own_pos),
                    "heading": 0.0,
                    "speed": 0.0,
                    "estimated": None,
                    "emitting": False,
                    "detected": False,
                    "state": "unknown",
                    "firstSeen": 0.0,
                    "lastSeen": 0.0,
                    "seenCount": 0,
                    "bearingHistory": [],
                    "signal": 0.0,
                    "signature": "",
                    "waveform": {"progress": 0.0, "resolved": False},
                    "spectrum": None,
                    "massKt": 0.0,
                    "gravRead": None,
                    "gravTail": None,
                    "sensor": {},
                }
            )
    return data


def _ws_open(ws: Any) -> bool:
    """Best-effort equivalent of ``ws.readyState === ws.OPEN``."""
    try:
        from starlette.websockets import WebSocketState

        state = getattr(ws, "client_state", None)
        if state is not None:
            return state == WebSocketState.CONNECTED
    except Exception:
        pass
    return getattr(ws, "readyState", 1) == 1


class Room:
    def __init__(self, channel_id: str, instance_id: str, state: GameState) -> None:
        self.channel_id = channel_id
        self.instance_id = instance_id
        self.state = state
        self.clients: dict[str, Client] = {}
        self._listeners: set[StateListener] = set()
        self._save_timer: Any = None

    # -- listeners ---------------------------------------------------------

    def on_state(self, fn: StateListener) -> Unsubscribe:
        self._listeners.add(fn)

        def _unsubscribe() -> None:
            self._listeners.discard(fn)

        return _unsubscribe

    # -- construction ------------------------------------------------------

    @classmethod
    def load_or_create(cls, channel_id: str, instance_id: str) -> "Room":
        saved = load_room(channel_id)
        if saved is not None:
            room = cls(channel_id, instance_id, saved)
            room.state.room.instanceId = instance_id
            # Seats belong to live connections.  After a restart none of the old
            # sessions exist, so clear them rather than leaving ghost occupants.
            for seat in room.state.seats.values():
                seat.player = None
            room.state.hostId = None
            room.state.hostSession = None
            return room
        return cls(
            channel_id,
            instance_id,
            create_state(channel_id, instance_id, campaign_for(None)),
        )

    # -- membership --------------------------------------------------------

    def join(self, cl: Client) -> None:
        # One session per connection.  Keying by userId collapsed two tabs that
        # shared a dev identity onto one client, so the second tab's seat claim
        # released the first tab's seat.
        self.clients[cl.sessionId] = cl
        self.sync_host()

    def leave(self, session_id: str) -> None:
        cl = self.clients.get(session_id)
        if cl is None:
            return
        self.release_seat(session_id)
        self.clients.pop(session_id, None)
        self.sync_host()

    def disconnect(self, session_id: str) -> None:
        if self.clients.pop(session_id, None) is None:
            return
        self.sync_host()

    @staticmethod
    def _owns(player: Any, session_id: str) -> bool:
        if player.sessionId:
            return player.sessionId == session_id
        # Rows persisted before sessions existed fall back to the user id.
        return player.userId == session_id

    def release_seat(self, session_id: str) -> None:
        for seat in self.state.seats.values():
            if seat.player is not None and self._owns(seat.player, session_id):
                seat.player = None
        self.state.seq += 1
        if self.state.hostSession == session_id:
            self.sync_host(True)

    def sync_host(self, force: bool = False) -> None:
        seated = [s.player for s in self.state.seats.values() if s.player is not None]
        host = self.state.hostSession or ""
        still_around = any(p.sessionId == host for p in seated) and host in self.clients
        if not still_around or force:
            nxt = next((p for p in seated if p.sessionId in self.clients), None)
            self.state.hostSession = nxt.sessionId if nxt is not None else None
            self.state.hostId = nxt.userId if nxt is not None else None
            self.state.seq += 1

    def seat_of(self, session_id: str) -> SeatId | None:
        for k, s in self.state.seats.items():
            if s.player is not None and self._owns(s.player, session_id):
                return k
        return None

    # -- fan-out -----------------------------------------------------------

    async def broadcast(self) -> None:
        self.state.seq += 1
        payload = json.dumps(
            {"type": "state", "state": public_state(self.state)},
            separators=(",", ":"),
        )
        for cl in list(self.clients.values()):
            if _ws_open(cl.ws):
                try:
                    await cl.ws.send_text(payload)
                except Exception:
                    pass
        for fn in list(self._listeners):
            res = fn(self.state)
            if inspect.isawaitable(res):
                await res
        self.schedule_save()

    async def reset(self, campaign: GameState) -> None:
        payload = json.dumps(
            {"type": "state", "state": public_state(campaign)},
            separators=(",", ":"),
        )
        for cl in list(self.clients.values()):
            if _ws_open(cl.ws):
                try:
                    await cl.ws.send_text(payload)
                except Exception:
                    pass
        self.state = campaign
        for fn in list(self._listeners):
            res = fn(self.state)
            if inspect.isawaitable(res):
                await res
        self.schedule_save()

    # -- persistence -------------------------------------------------------

    def schedule_save(self) -> None:
        self._cancel_save_timer()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            self._save_timer = loop.call_later(
                SAVE_DEBOUNCE_SECONDS, self._save_now
            )
        else:
            timer = threading.Timer(SAVE_DEBOUNCE_SECONDS, self._save_now)
            timer.daemon = True
            timer.start()
            self._save_timer = timer

    def _cancel_save_timer(self) -> None:
        if self._save_timer is not None:
            try:
                self._save_timer.cancel()
            except Exception:
                pass
            self._save_timer = None

    def _save_now(self) -> None:
        self._save_timer = None
        save_room(self.channel_id, self.state)


class RoomManager:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}

    def get(self, channel_id: str, instance_id: str) -> Room:
        room = self.rooms.get(channel_id)
        if room is None:
            room = Room.load_or_create(channel_id, instance_id)
            self.rooms[channel_id] = room
        return room

    def has(self, channel_id: str) -> bool:
        return channel_id in self.rooms


# Global registry shared by ws.py / admin.py / main.py.
rooms = RoomManager()


__all__ = [
    "Client",
    "Room",
    "RoomManager",
    "rooms",
    "SAVE_DEBOUNCE_SECONDS",
]
