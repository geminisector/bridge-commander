"""Integration tests for the CAPTAIN server layer.

These cover the gaps the port left unverified: SQLite round-trip against a real
``GameState``, schema-version rejection, a live websocket handshake with the
camelCase/alias wire shape, seat permissions, and ``clean_event`` clamping.
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bridge.server import db
from bridge.server.admin_events import clean_event
from bridge.server.engine import create_state
from bridge.server.rooms import rooms as room_manager
from bridge.server.ws import attach_ws
from bridge.shared import campaign_for
from bridge.shared.constants import STATE_SCHEMA_VERSION
from bridge.shared.types import DecisionEvent


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    """Point the module-level connection at a throwaway DB and clear rooms."""
    db._conn = None
    db.init_db(str(tmp_path))
    room_manager.rooms.clear()
    yield
    if db._conn is not None:
        db._conn.close()
    db._conn = None
    room_manager.rooms.clear()


def _hello(ws, channel="chan-1", instance="inst-1", user="u1", name="Alice", session=None):
    hello = {
        "channelId": channel,
        "instanceId": instance,
        "userId": user,
        "name": name,
    }
    if session is not None:
        hello["sessionId"] = session
    ws.send_text(json.dumps({"type": "hello", "hello": hello}))


def _read_state(ws, pred, limit=12):
    """Read until a state broadcast satisfies ``pred`` (ignore older ones)."""
    last = None
    for _ in range(limit):
        msg = ws.receive_json()
        if msg.get("type") == "state":
            last = msg["state"]
            if pred(last):
                return last
    raise AssertionError(f"state condition never met; last={last}")


@contextmanager
def _client():
    """A TestClient entered as a context manager.

    ``websocket_connect`` blocks forever in this Starlette/httpx version unless
    the client's portal has been started by ``with TestClient(...)``.
    """
    app = FastAPI()
    attach_ws(app)
    with TestClient(app) as client:
        yield client


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_db_round_trip_preserves_state():
    state = create_state("chan-1", "inst-1", campaign_for(None))
    db.save_room("chan-1", state)

    loaded = db.load_room("chan-1")
    assert loaded is not None
    assert loaded.model_dump() == state.model_dump()
    assert loaded.schemaVersion == STATE_SCHEMA_VERSION


def test_db_rejects_stale_schema():
    state = create_state("chan-1", "inst-1", campaign_for(None))
    db.save_room("chan-1", state)
    assert STATE_SCHEMA_VERSION == 4

    conn = db._conn
    assert conn is not None
    raw = json.loads(conn.execute("SELECT state FROM rooms WHERE channel='chan-1'").fetchone()[0])
    raw["schema"] = 3
    conn.execute(
        "UPDATE rooms SET state = ? WHERE channel = 'chan-1'", (json.dumps(raw),)
    )
    conn.commit()

    assert db.load_room("chan-1") is None
    # The caller then mints a fresh room at the current schema.
    fresh = create_state("chan-1", "inst-1", campaign_for(None))
    assert fresh.schemaVersion == STATE_SCHEMA_VERSION


def test_db_load_missing_channel_is_none():
    assert db.load_room("nope") is None


# ---------------------------------------------------------------------------
# WebSocket protocol
# ---------------------------------------------------------------------------


def test_ws_hello_returns_state_with_wire_aliases():
    with _client() as client, client.websocket_connect("/ws") as ws:
        _hello(ws)
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert hello["clientId"].startswith("s-")  # per-connection session id
        # Wire keys stay camelCase and the aliased keys are the JSON names.
        assert hello["state"]["schema"] == STATE_SCHEMA_VERSION
        assert "schemaVersion" not in hello["state"]
        assert hello["state"]["ship"]["class"]
        assert "className" not in hello["state"]["ship"]
        assert hello["state"]["campaign"]["contacts"] == []
        own_pos = hello["state"]["ship"]["pos"]
        for contact in hello["state"]["contacts"]:
            assert contact["everDetected"] is False
            assert contact["trueName"] == ""
            assert contact["trueType"] == "unknown"
            assert contact["shipClass"] == ""
            assert contact["pos"] == own_pos

        broadcast = ws.receive_json()
        assert broadcast["type"] == "state"


def test_ws_command_before_seating_is_rejected():
    with _client() as client, client.websocket_connect("/ws") as ws:
        _hello(ws)
        ws.receive_json()  # hello
        ws.receive_json()  # broadcast
        ws.send_text(json.dumps({"type": "nav:speed", "kps": 8}))
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "not seated" in err["message"]


def test_ws_seat_then_command_applies_state():
    with _client() as client, client.websocket_connect("/ws") as ws:
        _hello(ws)
        ws.receive_json()
        ws.receive_json()

        ws.send_text(json.dumps({"type": "setSeat", "seat": "command"}))
        seated = ws.receive_json()
        assert seated["type"] == "state"
        assert seated["state"]["seats"]["command"]["player"]["userId"] == "u1"
        assert seated["state"]["hostId"] == "u1"

        ws.send_text(json.dumps({"type": "nav:speed", "kps": 8}))
        moved = ws.receive_json()
        assert moved["type"] == "state"
        assert moved["state"]["ship"]["speed"] == 8


def test_ws_sensor_claim_is_routed_to_engine():
    with _client() as client, client.websocket_connect("/ws") as ws:
        _hello(ws)
        ws.receive_json()
        ws.receive_json()

        ws.send_text(json.dumps({"type": "setSeat", "seat": "sensor"}))
        seated = ws.receive_json()
        contact_id = seated["state"]["contacts"][0]["id"]

        ws.send_text(
            json.dumps(
                {"type": "sensor:claim", "contactId": contact_id, "guess": "freighter"}
            )
        )
        msg = ws.receive_json()
        assert msg["type"] == "state"


def test_ws_unknown_type_does_not_kill_connection():
    with _client() as client, client.websocket_connect("/ws") as ws:
        _hello(ws)
        ws.receive_json()
        ws.receive_json()
        ws.send_text(json.dumps({"type": "totally:unknown"}))
        # The connection stays usable afterwards.
        ws.send_text(json.dumps({"type": "setSeat", "seat": None}))
        msg = ws.receive_json()
        assert msg["type"] == "state"


def test_public_state_reveals_only_confirmed_identity():
    from bridge.server.rooms import public_state
    from bridge.shared import campaign_for

    state = create_state("public-state", "inst", campaign_for(None))
    contact = state.contacts[0]
    contact.everDetected = True
    contact.detected = True
    contact.guess = "escort"
    contact.state = "classified"

    hidden = public_state(state)["contacts"][0]
    assert hidden["trueName"] == ""
    assert hidden["trueType"] == "unknown"
    assert hidden["shipClass"] == ""

    contact.state = "confirmed"
    revealed = public_state(state)["contacts"][0]
    assert revealed["trueName"] == contact.name
    assert revealed["trueType"] == "escort"
    assert revealed["shipClass"] == contact.shipClass

    contact.detected = False
    lost = public_state(state)["contacts"][0]
    assert lost["trueName"] == ""
    assert lost["trueType"] == "unknown"
    assert lost["name"].startswith("TRACK-")
    assert lost["name"] != contact.trueName
    assert lost["pos"] == state.ship.pos.model_dump()


# ---------------------------------------------------------------------------
# GM event sanitising
# ---------------------------------------------------------------------------


def test_admin_event_parses_permissively_then_cleans():
    from bridge.shared.protocol import parse_admin_c2s

    msg = parse_admin_c2s(
        {"type": "admin.event", "channelId": "c1", "event": {"title": 123, "deadline": "soon"}}
    )
    assert msg.event["title"] == 123

    state = create_state("chan-1", "inst-1", campaign_for(None))
    ev = clean_event(state, msg.event)
    assert ev.title == "123"
    assert ev.deadline == state.clock + 60


def test_clean_event_clamps_and_coerces():
    state = create_state("chan-1", "inst-1", campaign_for(None))
    raw = {
        "title": "T" * 500,
        "kind": "K" * 500,
        "deadline": None,
        "text": "X" * 5000,
        "source": "S" * 500,
        "options": [
            {"label": "L" * 500, "effect": {"exposure": "not-a-number", "log": "G" * 900}},
            {"label": "ok"},
            {"label": "ok2"},
            {"label": "ok3"},
            {"label": "dropped"},
        ],
    }
    ev = clean_event(state, raw)
    assert isinstance(ev, DecisionEvent)
    assert ev.title == "T" * 80
    assert ev.kind == "K" * 24
    assert ev.text == "X" * 600
    assert ev.source == "S" * 24
    assert ev.deadline == state.clock + 60
    assert len(ev.options) == 4  # slice(0, 4)
    assert ev.options[0].label == "L" * 80
    assert ev.options[0].effect.exposure == 0
    assert ev.options[0].effect.log == "G" * 300


def test_clean_event_sanitizes_inline_identifiers():
    state = create_state("chan-1", "inst-1", campaign_for(None))
    ev = clean_event(
        state,
        {
            "id": "x');alert(1)//",
            "options": [
                {
                    "id": "y');alert(2)//",
                    "label": "Unsafe",
                    "effect": {"targetId": "z');alert(3)//"},
                }
            ],
        },
    )

    assert ev.id == "x-alert-1"
    assert ev.options[0].id == "y-alert-2"
    assert ev.options[0].effect.targetId == "z-alert-3"

    generated_a = clean_event(state, {"title": "A"})
    generated_b = clean_event(state, {"title": "B"})
    assert generated_a.id != generated_b.id


def test_clean_event_parses_boolean_strings_and_skips_bad_contacts():
    state = create_state("chan-1", "inst-1", campaign_for(None))
    ev = clean_event(
        state,
        {
            "options": [
                {
                    "label": "Mixed",
                    "effect": {
                        "relay": "false",
                        "challenge": "true",
                        "launchContacts": [
                            {"invalid": True},
                            {
                                "type": "fighter",
                                "x": 10,
                                "y": 0,
                                "heading": 0,
                                "speed": 20,
                                "faction": "enemy",
                                "hostile": True,
                                "emitting": True,
                            },
                        ],
                    },
                }
            ]
        },
    )

    effect = ev.options[0].effect
    assert effect.relay is False
    assert effect.challenge is True
    assert effect.launchContacts is not None
    assert len(effect.launchContacts) == 1


def test_clean_event_keeps_comms_weapons_effects():
    state = create_state("chan-1", "inst-1", campaign_for(None))
    raw = {
        "title": "Board decision",
        "options": [
            {
                "label": "Relay it",
                "effect": {"relay": True, "challenge": False, "civilian": 1},
            },
            {
                "label": "Surrender call",
                "effect": {"falseSurrender": True, "targetId": "c1"},
            },
        ],
    }
    ev = clean_event(state, raw)
    relayed = ev.options[0].effect
    assert relayed.relay is True
    assert relayed.challenge is False
    assert relayed.civilian is True
    surrender = ev.options[1].effect
    assert surrender.falseSurrender is True
    assert surrender.targetId == "c1"
    # An option that names none of them stays "not part of this option".
    bare = clean_event(state, {"options": [{"label": "Nothing"}]}).options[0].effect
    assert bare.relay is None and bare.civilian is None and bare.falseSurrender is None


# ---------------------------------------------------------------------------
# Admin app
# ---------------------------------------------------------------------------


def test_admin_app_refuses_an_empty_token():
    from bridge.server.admin import create_admin_app

    with pytest.raises(ValueError, match="ADMIN_TOKEN"):
        create_admin_app("")


def test_admin_ws_requires_hello_then_accepts_token():
    from bridge.server.admin import create_admin_app

    app = create_admin_app("secret")
    with TestClient(app) as client:
        with client.websocket_connect("/") as ws:
            ws.send_text(json.dumps({"type": "admin.list"}))
            err = ws.receive_json()
            assert err["type"] == "admin.error"
            assert "admin.hello first" in err["message"]

            ws.send_text(json.dumps({"type": "admin.hello", "token": "secret"}))
            ok = ws.receive_json()
            assert ok["type"] == "admin.ok"
            assert len(ok["campaigns"]) == 9


def test_main_exposes_health_and_ws_before_the_static_mount():
    from starlette.routing import Mount

    from bridge.server import main

    client = TestClient(main.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    paths = [getattr(r, "path", None) for r in main.app.routes]
    ws_index = paths.index("/ws")
    mount_indices = [i for i, r in enumerate(main.app.routes) if isinstance(r, Mount)]
    # The /ws route must be matched before any catch-all static mount.
    assert all(ws_index < i for i in mount_indices)



# ---------------------------------------------------------------------------
# Activity bundle / asset discovery (regression: a missing bundle 404s "/")
# ---------------------------------------------------------------------------


def _fake_bundle(tmp_path):
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "index.html").write_text("<!doctype html>")
    (bundle / "assets").mkdir()
    return bundle


def test_packaged_activity_and_art_are_served():
    from bridge.server import main

    client = TestClient(main.app)
    for path, media_type in (
        ("/", "text/html"),
        ("/activity.js", "text/javascript"),
        ("/favicon.png", "image/png"),
        ("/img/action/friendly-cruiser.png", "image/png"),
        ("/img/vdu/friendly-cruiser-vdu.gif", "image/gif"),
        ("/img/brief/unknown.png", "image/png"),
    ):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.headers["content-type"].startswith(media_type), path


def test_activity_uses_the_current_wire_and_speed_scale():
    from bridge.paths import package_path

    script = package_path("activity", "dist", "activity.js").read_text(encoding="utf-8")
    assert "state.ship.className" not in script
    assert "state.ship.layer" not in script
    assert "window.speed(15)" in script
    assert "window.speed(60)" in script
    assert "window.speed(100)" in script
    assert "canFire()" in script
    assert "const n=32||bands.length" not in script


def test_activity_dist_override_wins_when_it_holds_index_html(tmp_path, monkeypatch):
    from bridge.server import main

    bundle = _fake_bundle(tmp_path)
    monkeypatch.setattr(main, "ACTIVITY_DIST", str(bundle))
    assert main._activity_dist() == bundle


def test_activity_dist_ignores_an_override_without_index_html(tmp_path, monkeypatch):
    from bridge.server import main

    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(main, "ACTIVITY_DIST", str(empty))
    found = main._activity_dist()
    # Auto-discovery may still find a real checkout, but never the empty dir.
    assert found != empty
    if found is not None:
        assert (found / "index.html").is_file()


def test_activity_dist_finds_the_packaged_bundle():
    from bridge.paths import package_path
    from bridge.server import main

    found = main._activity_dist()
    assert found is not None
    assert found == package_path("activity", "dist")
    assert (found / "index.html").is_file()


def test_asset_dir_override_used_when_the_directory_exists(tmp_path, monkeypatch):
    from bridge.server import main

    assets = tmp_path / "img"
    assets.mkdir()
    monkeypatch.setattr(main, "ASSET_DIR", str(assets))
    assert main._asset_dir() == assets


def test_static_mounts_serve_the_bundle_and_contact_art(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from starlette.testclient import TestClient

    bundle = _fake_bundle(tmp_path)
    (bundle / "assets" / "app.js").write_text("console.log('ok')")
    assets = tmp_path / "img"
    (assets / "brief").mkdir(parents=True)
    (assets / "brief" / "unknown.png").write_bytes(b"\x89PNG\r\n")

    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"ok": True}

    app.mount("/img", StaticFiles(directory=str(assets)), name="img")
    app.mount("/", StaticFiles(directory=str(bundle), html=True), name="activity")

    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/img/brief/unknown.png").status_code == 200
    assert client.get("/health").status_code == 200


# ---------------------------------------------------------------------------
# GM scenario building: dictate the crew hull and contact hulls
# ---------------------------------------------------------------------------


def test_admin_snapshot_lists_ships_and_can_dictate_the_crew_hull():
    from bridge.server.admin import create_admin_app
    from bridge.server.rooms import rooms

    room = rooms.get("chan-admin-ship", "inst")
    app = create_admin_app("secret")
    with TestClient(app) as client:
        with client.websocket_connect("/") as ws:
            ws.send_text(json.dumps({"type": "admin.hello", "token": "secret"}))
            ok = ws.receive_json()
            assert ok["type"] == "admin.ok"
            assert len(ok["ships"]) >= 8
            assert {"id", "massKt", "profile", "stealth", "emission"} <= set(ok["ships"][0])

            ws.send_text(
                json.dumps(
                    {
                        "type": "admin.setShip",
                        "channelId": "chan-admin-ship",
                        "shipId": "enemy-cruiser",
                    }
                )
            )
            st = ws.receive_json()
            assert st["type"] == "admin.state"
            assert st["state"]["ship"]["shipClass"] == "enemy-cruiser"
            assert st["state"]["ship"]["massKt"] == 320
    assert room.state.ship.shipClass == "enemy-cruiser"


def test_admin_can_spawn_a_contact_with_a_chosen_hull():
    from bridge.server.admin import create_admin_app
    from bridge.server.rooms import rooms

    room = rooms.get("chan-admin-spawn", "inst")
    before = len(room.state.contacts)
    app = create_admin_app("secret")
    with TestClient(app) as client:
        with client.websocket_connect("/") as ws:
            ws.send_text(json.dumps({"type": "admin.hello", "token": "secret"}))
            ws.receive_json()
            ws.send_text(
                json.dumps(
                    {
                        "type": "admin.spawn",
                        "channelId": "chan-admin-spawn",
                        "contact": {
                            "type": "capship",
                            "shipClass": "enemy-cruiser",
                            "x": 15,
                            "y": 0,
                            "heading": 0,
                            "speed": 5,
                            "faction": "enemy",
                            "hostile": True,
                            "emitting": True,
                        },
                    }
                )
            )
            st = ws.receive_json()
            assert st["type"] == "admin.state"
    assert len(room.state.contacts) == before + 1
    spawned = room.state.contacts[-1]
    assert spawned.shipClass == "enemy-cruiser"
    assert spawned.massKt == 320
    assert spawned.profile == 0.95


def test_admin_reset_takes_a_crew_hull():
    from bridge.server.admin import create_admin_app
    from bridge.server.rooms import rooms

    rooms.get("chan-admin-reset", "inst")
    app = create_admin_app("secret")
    with TestClient(app) as client:
        with client.websocket_connect("/") as ws:
            ws.send_text(json.dumps({"type": "admin.hello", "token": "secret"}))
            ws.receive_json()
            ws.send_text(
                json.dumps(
                    {
                        "type": "admin.reset",
                        "channelId": "chan-admin-reset",
                        "campaignId": "iron-collar",
                        "shipId": "enemy-escort",
                    }
                )
            )
            st = ws.receive_json()
            assert st["type"] == "admin.state"
            assert st["state"]["ship"]["shipClass"] == "enemy-escort"
            assert st["state"]["ship"]["name"] == "Enemy_Escort-01"


def test_admin_can_freeze_and_release_the_clock():
    from bridge.server.admin import create_admin_app
    from bridge.server.engine import advance
    from bridge.server.rooms import rooms

    room = rooms.get("chan-freeze", "inst")
    room.state.status = "running"
    app = create_admin_app("secret")
    with TestClient(app) as client:
        with client.websocket_connect("/") as ws:
            ws.send_text(json.dumps({"type": "admin.hello", "token": "secret"}))
            ws.receive_json()
            ws.send_text(
                json.dumps(
                    {
                        "type": "admin.freeze",
                        "channelId": "chan-freeze",
                        "frozen": True,
                    }
                )
            )
            st = ws.receive_json()
            assert st["type"] == "admin.state"
            assert st["state"]["timeFrozen"] is True

    before = room.state.clock
    advance(room.state, 90)
    assert room.state.clock == before


def test_admin_can_set_crew_skills_and_they_reach_the_check_layer():
    from bridge.server.admin import create_admin_app
    from bridge.server.engine import skill_score
    from bridge.server.rooms import rooms

    room = rooms.get("chan-skills", "inst")
    app = create_admin_app("secret")
    with TestClient(app) as client:
        with client.websocket_connect("/") as ws:
            ws.send_text(json.dumps({"type": "admin.hello", "token": "secret"}))
            ok = ws.receive_json()
            assert ok["type"] == "admin.ok"
            # The console is offered the skill catalogue to populate its picker.
            assert "Technology" in ok["skills"]
            ws.send_text(
                json.dumps(
                    {
                        "type": "admin.skills",
                        "channelId": "chan-skills",
                        "seat": "sensor",
                        "scores": {"Technology": 82},
                    }
                )
            )
            st = ws.receive_json()
            assert st["type"] == "admin.state"

    assert room.state.seats["sensor"].skills.scores["Technology"] == 82
    assert skill_score(room.state, "sensor", "Technology") == 82


def test_admin_skills_merge_instead_of_wiping_a_station():
    from bridge.server.engine import set_seat_skills
    from bridge.server.rooms import rooms

    room = rooms.get("chan-skills-merge", "inst")
    set_seat_skills(room.state, "comms", {"Translate": 70})
    set_seat_skills(room.state, "comms", {"Distress": 40})
    scores = room.state.seats["comms"].skills.scores
    assert scores == {"Translate": 70, "Distress": 40}


# ---------------------------------------------------------------------------
# Sessions: one per connection (the 3+ player seat-loss bug)
# ---------------------------------------------------------------------------


def test_ws_hello_mints_a_session_id_when_absent():
    with _client() as client, client.websocket_connect("/ws") as ws:
        _hello(ws)
        reply = ws.receive_json()
        assert reply["type"] == "hello"
        assert reply["clientId"].startswith("s-")


def test_duplicate_user_ids_are_independent_sessions():
    """Two connections sharing a userId must not steal each other's seat.

    This is the dev/browser case: every tab on one machine shares a
    localStorage id, and the old code keyed clients by userId, so the second
    tab's seat claim released the first tab's seat.
    """
    with _client() as client:
        with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
            _hello(ws_a, channel="chan-sess", instance="i", user="same-user", name="A", session="sess-a")
            ws_a.receive_json()  # hello
            ws_a.receive_json()  # broadcast
            _hello(ws_b, channel="chan-sess", instance="i", user="same-user", name="B", session="sess-b")
            ws_b.receive_json()  # hello
            ws_b.receive_json()  # broadcast

            ws_a.send_text(json.dumps({"type": "setSeat", "seat": "command"}))
            _read_state(ws_a, lambda s: s["seats"]["command"]["player"] is not None)

            ws_b.send_text(json.dumps({"type": "setSeat", "seat": "ops"}))
            state = _read_state(ws_b, lambda s: s["seats"]["ops"]["player"] is not None)
            seats = state["seats"]
            # Same user, two sessions: both seats hold.
            assert seats["command"]["player"]["sessionId"] == "sess-a"
            assert seats["ops"]["player"]["sessionId"] == "sess-b"
            assert seats["command"]["player"]["userId"] == "same-user"
            assert seats["ops"]["player"]["userId"] == "same-user"
            assert state["hostSession"] == "sess-a"

            room = room_manager.get("chan-sess", "i")
            assert len(room.clients) == 2

            # Drop A only; B is still connected, so assert before leaving the
            # block (exiting would close B as well).
            ws_a.close()
            time.sleep(0.1)
            # A's seat stays reserved for a quick reconnect; B keeps ops and
            # becomes the active host connection.
            assert room.state.seats["command"].player.sessionId == "sess-a"
            assert room.state.seats["ops"].player is not None
            assert room.state.seats["ops"].player.sessionId == "sess-b"
            assert room.state.hostSession == "sess-b"
            assert room.state.hostId == "same-user"
            assert len(room.clients) == 1

            ws_b.send_text(json.dumps({"type": "setSeat", "seat": "command"}))
            _read_state(
                ws_b,
                lambda state: state["seats"]["command"]["player"]["sessionId"] == "sess-b",
            )
            assert room.state.seats["ops"].player is None


def test_reconnect_in_the_same_tab_reuses_its_session_id_and_seat():
    with _client() as client:
        with client.websocket_connect("/ws") as ws:
            _hello(ws, channel="chan-reconnect", instance="i", user="u9", session="sess-9")
            reply = ws.receive_json()
            assert reply["clientId"] == "sess-9"
            ws.receive_json()
            ws.send_text(json.dumps({"type": "setSeat", "seat": "ops"}))
            _read_state(ws, lambda state: state["seats"]["ops"]["player"] is not None)

        with client.websocket_connect("/ws") as ws:
            _hello(ws, channel="chan-reconnect", instance="i", user="u9", session="sess-9")
            reply = ws.receive_json()
            assert reply["clientId"] == "sess-9"
            assert reply["state"]["seats"]["ops"]["player"]["sessionId"] == "sess-9"
