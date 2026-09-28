"""Tests for the admin mod manager (`bridge/server/mods.py`).

Installed flavors are inert until loaded, and **exactly one mod is active at a
time**: activating one unloads every other, ``core`` included.  The active mod
persists in the rooms database.  These tests pin that contract, the fail-closed
guards around unloaded mods, and the admin websocket surface.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from bridge.shared import flavors
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


def _flavors_of(ok) -> dict:
    return {f["id"]: f for f in ok["flavors"]}


# ---------------------------------------------------------------------------
# Activation store
# ---------------------------------------------------------------------------


def test_installed_mods_start_unloaded_and_core_falls_back():
    assert mods.active_mod() == "core"
    assert mods.is_enabled("core") is True
    assert mods.is_enabled("wc") is False
    assert mods.enabled_ids() == ["core"]


def test_activating_a_mod_unloads_every_other_mod():
    ok, reason = mods.activate("wc")
    assert ok, reason
    assert mods.active_mod() == "wc"
    assert mods.is_enabled("wc") is True
    # Core is an ordinary mod here: loading wc unloads it.
    assert mods.is_enabled("core") is False
    assert mods.enabled_ids() == ["wc"]

    # Loading a third mod unloads the second.
    assert mods.activate("stk")[0] is True
    assert mods.active_mod() == "stk"
    assert mods.is_enabled("wc") is False

    # Core can be loaded back like any other mod.
    assert mods.activate("core")[0] is True
    assert mods.active_mod() == "core"
    assert mods.enabled_ids() == ["core"]


def test_activation_persists_across_a_reconnect(tmp_path):
    db_path = str(tmp_path)
    assert mods.activate("wc")[0] is True
    assert db.load_active_mod() == "wc"
    # Simulate a restart against the same database file.
    assert db._conn is not None
    db._conn.close()
    db._conn = None
    db.init_db(db_path)
    assert db.load_active_mod() == "wc"
    assert mods.active_mod() == "wc"


def test_deactivating_the_active_mod_falls_back_to_core():
    assert mods.activate("wc")[0] is True
    ok, reason = mods.deactivate("wc")
    assert ok, reason
    assert mods.active_mod() == "core"
    assert mods.is_enabled("wc") is False


def test_deactivating_an_inactive_mod_is_refused():
    ok, reason = mods.deactivate("wc")
    assert ok is False
    assert "not the active" in reason


def test_core_is_refused_as_a_deactivation_target():
    # With core active there is nothing to fall back to...
    ok, reason = mods.deactivate("core")
    assert ok is False
    assert "fallback" in reason
    # ...and with another mod loaded, core is simply not the active one.
    assert mods.activate("wc")[0] is True
    ok, reason = mods.deactivate("core")
    assert ok is False
    assert "not the active" in reason


def test_unknown_mod_is_rejected():
    ok, reason = mods.activate("does-not-exist")
    assert ok is False
    assert "no such mod" in reason


def test_a_legacy_multi_mod_database_is_normalised_on_open(tmp_path):
    """An old DB could hold several enabled rows; exactly one must survive."""
    path = str(tmp_path / "legacy.sqlite")
    db._conn = None
    db.init_db(path)
    db._conn.execute(
        "INSERT INTO mods (flavor_id, enabled, is_default) VALUES ('wc', 1, 1)"
    )
    db._conn.execute(
        "INSERT INTO mods (flavor_id, enabled, is_default) VALUES ('stk', 1, 0)"
    )
    db._conn.commit()
    db._conn.close()
    db._conn = None

    db.init_db(path)
    enabled = db._conn.execute(
        "SELECT flavor_id FROM mods WHERE enabled = 1"
    ).fetchall()
    assert len(enabled) == 1
    assert enabled[0][0] == "wc"  # the first-loaded mod is kept


def test_guard_room_always_resolves_to_the_active_mod():
    assert mods.guard_room("wc") == "core"
    assert mods.activate("wc")[0] is True
    assert mods.guard_room("wc") == "wc"
    # A stale or unknown room flavor is pulled onto the loaded mod.
    assert mods.guard_room("core") == "wc"
    assert mods.guard_room("does-not-exist") == "wc"


def test_env_default_selects_the_active_mod(monkeypatch):
    monkeypatch.setenv("DEFAULT_FLAVOR", "wc")
    assert mods.active_mod() == "wc"
    assert mods.is_enabled("wc") is True
    assert mods.is_enabled("core") is False
    # A persisted console choice still wins over the environment.
    assert mods.activate("stk")[0] is True
    assert mods.active_mod() == "stk"


def test_list_mods_reports_exactly_one_active():
    rows = {row["id"]: row for row in mods.list_mods()}
    assert rows["core"]["enabled"] is True
    assert rows["core"]["core"] is True
    assert rows["wc"]["enabled"] is False

    assert mods.activate("wc")[0] is True
    rows = {row["id"]: row for row in mods.list_mods()}
    assert rows["wc"]["enabled"] is True
    assert rows["core"]["enabled"] is False
    assert sum(1 for row in rows.values() if row["enabled"]) == 1


def test_a_mod_that_fails_to_load_cannot_be_activated(monkeypatch):
    """Fail closed: an invalid setting must never become the active one."""
    summaries = [
        {"id": "broken", "title": "Broken", "valid": False, "error": "boom"},
    ]
    monkeypatch.setattr(flavors, "summaries", lambda: summaries)
    monkeypatch.setattr(flavors, "available", lambda: ["core", "broken"])
    ok, reason = mods.activate("broken")
    assert ok is False
    assert "invalid" in reason
    assert mods.active_mod() == "core"


# ---------------------------------------------------------------------------
# Room integration
# ---------------------------------------------------------------------------


def test_new_rooms_use_the_active_mod():
    assert mods.activate("wc")[0] is True
    room = rooms.get("chan-default-mod", "inst")
    assert room.state.flavorId == "wc"
    assert room.state.campaign.id.startswith("wc.")


def test_room_reconfigure_follows_the_active_mod():
    room = rooms.get("chan-guard", "inst")
    assert room.state.flavorId == "core"
    import asyncio

    # wc is not loaded, so the room stays on the active setting.
    asyncio.run(room.reconfigure(flavor_id="wc"))
    assert room.state.flavorId == "core"

    assert mods.activate("wc")[0] is True
    asyncio.run(room.reconfigure())
    assert room.state.flavorId == "wc"
    assert room.state.campaign.id.startswith("wc.")


# ---------------------------------------------------------------------------
# Admin websocket surface
# ---------------------------------------------------------------------------


def test_admin_activation_is_exclusive():
    app = create_admin_app("secret")
    with TestClient(app) as client:
        with _admin_ws(client) as ws:
            ok = _hello(ws)
            flavors_by_id = _flavors_of(ok)
            assert flavors_by_id["core"]["enabled"] is True
            assert flavors_by_id["wc"]["enabled"] is False

            ws.send_text(json.dumps({"type": "admin.activateMod", "flavorId": "wc"}))
            ok = ws.receive_json()
            assert ok["type"] == "admin.ok"
            flavors_by_id = _flavors_of(ok)
            assert flavors_by_id["wc"]["enabled"] is True
            assert flavors_by_id["core"]["enabled"] is False
            assert flavors_by_id["stk"]["enabled"] is False

            ws.send_text(json.dumps({"type": "admin.activateMod", "flavorId": "stk"}))
            ok = ws.receive_json()
            flavors_by_id = _flavors_of(ok)
            assert flavors_by_id["stk"]["enabled"] is True
            assert flavors_by_id["wc"]["enabled"] is False

            ws.send_text(json.dumps({"type": "admin.deactivateMod", "flavorId": "stk"}))
            ok = ws.receive_json()
            assert ok["type"] == "admin.ok"
            flavors_by_id = _flavors_of(ok)
            assert flavors_by_id["core"]["enabled"] is True
            assert flavors_by_id["stk"]["enabled"] is False


def test_admin_activate_sweeps_live_rooms_onto_the_mod():
    """No room may be left playing an unloaded universe."""
    room = rooms.get("chan-sweep", "inst")
    assert room.state.flavorId == "core"

    app = create_admin_app("secret")
    with TestClient(app) as client:
        with _admin_ws(client) as ws:
            _hello(ws)
            ws.send_text(json.dumps({"type": "admin.activateMod", "flavorId": "wc"}))
            assert ws.receive_json()["type"] == "admin.ok"

    assert room.state.flavorId == "wc"
    assert room.state.campaign.id.startswith("wc.")
    # The mod's own default mission, not the core scenario it was running.
    assert room.state.campaign.id == "wc.vega-patrol"


def test_admin_rejects_deactivating_core_when_it_is_all_that_is_loaded():
    app = create_admin_app("secret")
    with TestClient(app) as client:
        with _admin_ws(client) as ws:
            _hello(ws)
            ws.send_text(json.dumps({"type": "admin.deactivateMod", "flavorId": "core"}))
            err = ws.receive_json()
            assert err["type"] == "admin.error"
            assert "core" in err["message"]


def test_admin_snapshot_follows_the_active_mod():
    assert mods.activate("wc")[0] is True
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
            # The active mod drives the mission and hull pickers.
            assert any(c["id"].startswith("wc.") for c in ok["campaigns"])
            crew = flavors.get("wc").defaults["unknown"]
            assert any(s["id"] == crew for s in ok["ships"])
            # Core's scenarios are not on offer: it is unloaded.
            assert not any(c["id"] == "iron-collar" for c in ok["campaigns"])


def test_admin_lists_only_the_loaded_mod_as_active():
    app = create_admin_app("secret")
    with TestClient(app) as client:
        with _admin_ws(client) as ws:
            _hello(ws)
            ws.send_text(json.dumps({"type": "admin.activateMod", "flavorId": "sw"}))
            ok = ws.receive_json()
            assert sum(1 for f in ok["flavors"] if f["enabled"]) == 1
            assert _flavors_of(ok)["sw"]["enabled"] is True
