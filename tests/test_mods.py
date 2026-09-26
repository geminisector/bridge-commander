"""Tests for the admin mod manager (`bridge/server/mods.py`).

Installed flavors are inert until activated; the enabled set and the server-wide
default persist in the rooms database.  These tests pin that contract, the
fail-closed guards around disabled mods, and the admin websocket surface.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from bridge.server import db, mods
from bridge.server.admin import create_admin_app
from bridge.server.rooms import rooms


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path):
    """A throwaway DB and empty room registry for every test."""
    db._conn = None
    db.init_db(str(tmp_path))
    rooms.rooms.clear()
    yield
    if db._conn is not None:
        db._conn.close()
    db._conn = None
    rooms.rooms.clear()


def _admin_ws(client):
    return client.websocket_connect("/")


def _hello(ws):
    ws.send_text(json.dumps({"type": "admin.hello", "token": "secret"}))
    ok = ws.receive_json()
    assert ok["type"] == "admin.ok"
    return ok


# ---------------------------------------------------------------------------
# Activation store
# ---------------------------------------------------------------------------


def test_installed_mods_start_disabled_and_core_is_always_on():
    assert mods.is_enabled("core") is True
    assert mods.is_enabled("wc") is False
    assert mods.default_flavor() == "core"
    assert mods.enabled_ids() == ["core"]


def test_activate_then_deactivate_persists():
    ok, reason = mods.activate("wc")
    assert ok, reason
    assert mods.is_enabled("wc") is True
    assert "wc" in mods.enabled_ids()

    ok, reason = mods.deactivate("wc")
    assert ok, reason
    assert mods.is_enabled("wc") is False


def test_activation_survives_a_reconnect_to_the_same_db(tmp_path):
    db_path = str(tmp_path)
    mods.activate("wc")
    assert "wc" in db.load_enabled_mods()
    # Simulate a restart against the same database file.
    assert db._conn is not None
    db._conn.close()
    db._conn = None
    db.init_db(db_path)
    assert "wc" in db.load_enabled_mods()


def test_core_cannot_be_deactivated():
    ok, reason = mods.deactivate("core")
    assert ok is False
    assert "core" in reason


def test_unknown_mod_is_rejected():
    ok, reason = mods.activate("does-not-exist")
    assert ok is False
    assert "no such mod" in reason


def test_default_requires_activation():
    ok, reason = mods.set_default("wc")
    assert ok is False
    assert "activated" in reason

    mods.activate("wc")
    ok, reason = mods.set_default("wc")
    assert ok, reason
    assert mods.default_flavor() == "wc"

    # Clearing falls back to core.
    assert mods.set_default(None)[0] is True
    assert mods.default_flavor() == "core"


def test_deactivating_the_default_clears_the_default():
    mods.activate("wc")
    mods.set_default("wc")
    assert mods.default_flavor() == "wc"
    mods.deactivate("wc")
    assert mods.default_flavor() == "core"


def test_guard_room_falls_back_for_a_disabled_mod():
    assert mods.guard_room("wc") == "core"
    mods.activate("wc")
    assert mods.guard_room("wc") == "wc"
    assert mods.guard_room("does-not-exist") == "core"


def test_env_default_counts_as_an_activation(monkeypatch):
    monkeypatch.setenv("DEFAULT_FLAVOR", "wc")
    assert mods.is_enabled("wc") is True
    assert mods.default_flavor() == "wc"
    # Explicitly deactivating an env-selected mod is refused (fail loud).
    ok, reason = mods.deactivate("wc")
    assert ok is False
    assert "DEFAULT_FLAVOR" in reason


def test_list_mods_reports_state():
    rows = {row["id"]: row for row in mods.list_mods()}
    assert rows["core"]["enabled"] is True
    assert rows["core"]["default"] is True
    assert rows["core"]["core"] is True
    assert rows["wc"]["enabled"] is False
    mods.activate("wc")
    mods.set_default("wc")
    rows = {row["id"]: row for row in mods.list_mods()}
    assert rows["wc"]["enabled"] is True
    assert rows["wc"]["default"] is True
    assert rows["core"]["default"] is False


# ---------------------------------------------------------------------------
# Room integration
# ---------------------------------------------------------------------------


def test_new_rooms_use_the_activated_default():
    mods.activate("wc")
    mods.set_default("wc")
    room = rooms.get("chan-default-mod", "inst")
    assert room.state.flavorId == "wc"
    assert room.state.campaign.id.startswith("wc.")


def test_room_reconfigure_refuses_a_disabled_mod():
    room = rooms.get("chan-guard", "inst")
    assert room.state.flavorId == "core"
    import asyncio

    asyncio.run(room.reconfigure(flavor_id="wc"))
    assert room.state.flavorId == "core"  # guard fell back


# ---------------------------------------------------------------------------
# Admin websocket surface
# ---------------------------------------------------------------------------


def test_admin_mod_lifecycle_messages():
    app = create_admin_app("secret")
    with TestClient(app) as client:
        with _admin_ws(client) as ws:
            ok = _hello(ws)
            flavors = {f["id"]: f for f in ok["flavors"]}
            assert flavors["core"]["enabled"] is True
            assert flavors["wc"]["enabled"] is False

            ws.send_text(json.dumps({"type": "admin.activateMod", "flavorId": "wc"}))
            ok = ws.receive_json()
            assert ok["type"] == "admin.ok"
            flavors = {f["id"]: f for f in ok["flavors"]}
            assert flavors["wc"]["enabled"] is True

            ws.send_text(json.dumps({"type": "admin.setDefaultMod", "flavorId": "wc"}))
            ok = ws.receive_json()
            assert ok["type"] == "admin.ok"
            flavors = {f["id"]: f for f in ok["flavors"]}
            assert flavors["wc"]["default"] is True
            assert flavors["core"]["default"] is False

            ws.send_text(json.dumps({"type": "admin.deactivateMod", "flavorId": "wc"}))
            ok = ws.receive_json()
            assert ok["type"] == "admin.ok"
            flavors = {f["id"]: f for f in ok["flavors"]}
            assert flavors["wc"]["enabled"] is False
            assert flavors["wc"]["default"] is False


def test_admin_rejects_deactivating_core():
    app = create_admin_app("secret")
    with TestClient(app) as client:
        with _admin_ws(client) as ws:
            _hello(ws)
            ws.send_text(json.dumps({"type": "admin.deactivateMod", "flavorId": "core"}))
            err = ws.receive_json()
            assert err["type"] == "admin.error"
            assert "core" in err["message"]


def test_admin_activates_a_mod_for_a_room():
    rooms.get("chan-mod-room", "inst")  # creates the room on core
    app = create_admin_app("secret")
    with TestClient(app) as client:
        with _admin_ws(client) as ws:
            _hello(ws)
            # Disabled: refused.
            ws.send_text(
                json.dumps(
                    {
                        "type": "admin.activateModForRoom",
                        "channelId": "chan-mod-room",
                        "flavorId": "wc",
                    }
                )
            )
            err = ws.receive_json()
            assert err["type"] == "admin.error"
            assert "not activated" in err["message"]

            # Activate server-wide, then for the room.
            ws.send_text(json.dumps({"type": "admin.activateMod", "flavorId": "wc"}))
            assert ws.receive_json()["type"] == "admin.ok"
            ws.send_text(
                json.dumps(
                    {
                        "type": "admin.activateModForRoom",
                        "channelId": "chan-mod-room",
                        "flavorId": "wc",
                    }
                )
            )
            state = ws.receive_json()
            assert state["type"] == "admin.state"
            assert state["state"]["flavorId"] == "wc"
            # Activating a mod for a room loads that setting's own default
            # mission, not the inherited core scenario the room was on.
            assert state["state"]["campaign"]["id"] == "wc.vega-run"
    assert rooms.rooms["chan-mod-room"].state.flavorId == "wc"


def test_admin_reset_rejects_an_unactivated_mod():
    rooms.get("chan-mod-reset", "inst")
    app = create_admin_app("secret")
    with TestClient(app) as client:
        with _admin_ws(client) as ws:
            _hello(ws)
            ws.send_text(
                json.dumps(
                    {
                        "type": "admin.reset",
                        "channelId": "chan-mod-reset",
                        "flavorId": "wc",
                    }
                )
            )
            err = ws.receive_json()
            assert err["type"] == "admin.error"
            assert "not activated" in err["message"]


def test_admin_snapshot_follows_the_selected_room_flavor():
    mods.activate("wc")
    mods.set_default("wc")
    room = rooms.get("chan-snapshot", "inst")
    assert room.state.flavorId == "wc"
    app = create_admin_app("secret")
    with TestClient(app) as client:
        with _admin_ws(client) as ws:
            _hello(ws)
            ws.send_text(
                json.dumps({"type": "admin.list", "channelId": "chan-snapshot"})
            )
            ok = ws.receive_json()
            assert ok["type"] == "admin.ok"
            # The room's flavor drives the mission and hull pickers.
            assert any(c["id"].startswith("wc.") for c in ok["campaigns"])
            assert any(s["id"] == "wc.tigers-claw" for s in ok["ships"])
