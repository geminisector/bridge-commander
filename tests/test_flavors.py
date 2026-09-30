"""Tests for the flavor plugin system (``bridge/FLAVOR_PLUGIN_PLAN.md``).

These cover the four design invariants and every validator case the plan names:

* data only — the loader never executes flavor content;
* canonical units on the wire — conversion happens on display only;
* fail closed — a bad flavor does not half-load;
* no implicit inheritance of ids — dangling ``defaults`` and mission hull
  references are load errors (the ``lance-corvette`` regression).
"""

from __future__ import annotations

import asyncio
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from bridge.paths import PROJECT_ROOT, package_path
from bridge.server import db, engine, mods, rooms as rooms_mod
from bridge.shared import flavors
from bridge.shared.campaigns import campaign_for
from bridge.shared.ships import ship_art, ship_class, ship_classes

CORE_DIR = PROJECT_ROOT / "mods" / "core"


@pytest.fixture(autouse=True)
def _isolated_mod_db(tmp_path):
    """Give every test a private mod-activation store (never the repo's data/)."""
    db._conn = None
    db.init_db(str(tmp_path))
    yield
    if db._conn is not None:
        db._conn.close()
    db._conn = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, doc: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def _flavor(root: Path, fid: str, manifest: dict | None = None, **files: object) -> Path:
    """Create a flavor directory with a manifest and inline JSON files.

    Inheritance is opt-in, and these fixtures are mostly *overrides* of the
    shipped setting, so they extend ``core`` unless the manifest says otherwise
    (``{"extends": None}`` for a standalone one).
    """
    directory = root / fid
    directory.mkdir(parents=True, exist_ok=True)
    doc = {"id": fid, "title": fid.upper(), "extends": "core"}
    for name in files:
        doc.setdefault(name, f"{name}.json")
    doc.update(manifest or {})
    _write(directory / "flavor.json", doc)
    for name, payload in files.items():
        _write(directory / f"{name}.json", payload)
    return directory


def _hull(name: str, **overrides: object) -> dict:
    hull = {
        "name": name,
        "role": "Test hull",
        "contactType": "escort",
        "massKt": 5.0,
        "profile": 0.5,
        "stealth": 0.4,
        "emission": 0.5,
        "sensorQuality": 0.6,
        "crew": 10,
        "blurb": "",
        "art": {"action": "friendly-corvette.png", "vdu": "friendly-corvette-vdu.gif"},
        "stats": {"shieldFore": 10, "shieldAft": 10, "body": 50},
        "hardpoints": [{"id": "fore-gun", "arc": "fore", "kind": "gun"}],
    }
    hull.update(overrides)
    return hull


def _mission(mission_id: str, hull_id: str) -> dict:
    return {
        "id": mission_id,
        "title": mission_id,
        "theater": "Nowhere",
        "brief": "",
        "target": "",
        "startHour": 0,
        "patrol": {"center": {"x": 0, "y": 0, "z": 0}, "radiusKlik": 50},
        "clutter": 0,
        "escalation": 10,
        "shipClass": hull_id,
        "contacts": [
            {
                "x": 0,
                "y": 0,
                "heading": 0,
                "speed": 0,
                "type": "fighter",
                "faction": "enemy",
                "hostile": True,
                "emitting": False,
                "shipClass": hull_id,
            }
        ],
    }


@pytest.fixture
def flavor_home(tmp_path, monkeypatch):
    """A throwaway flavor tree seeded with the real core package."""
    root = tmp_path / "flavors"
    shutil.copytree(CORE_DIR, root / "core")
    monkeypatch.setenv("FLAVORS_DIR", str(root))
    flavors.reset_cache()
    yield root
    flavors.reset_cache()


# ---------------------------------------------------------------------------
# Core is the shipped default and stays intact
# ---------------------------------------------------------------------------


def test_core_flavor_loads_with_the_historical_catalog():
    core = flavors.get("core")
    assert core.id == "core"
    assert len(core.hull_defs) == 15
    assert len(core.missions) == 9
    assert core.defaults["unknown"] == "home"
    # The merge layer's hull tables agree with the compatibility view.
    assert set(core.ship_classes) == set(ship_classes("core"))
    assert "iron-collar" in core.missions


def test_core_mission_matches_the_legacy_factory_coordinates():
    seed = flavors.get("core").mission_seed("iron-collar")
    assert seed.contacts[0].x == -15
    assert seed.contacts[0].y == -58
    assert seed.contacts[0].heading == 282
    assert seed.contacts[0].speed == 30


def test_available_lists_core_first_with_the_example_flavors():
    ids = flavors.available()
    assert ids[0] == "core"
    # The shipped examples: core plus one re-skin per documented setting.
    assert {"wc", "stk", "sw"} <= set(ids)


# ---------------------------------------------------------------------------
# Units: conversion on display only
# ---------------------------------------------------------------------------

AU = 1.495978707e8
MM = 1.0e3


def _star_trek_units() -> dict:
    # ``min`` is in canonical klik: the AU rung opens at ~0.67 AU, the Mm rung
    # at 1 Mm (1000 klik), so a knife fight stays in klik and an intercept in AU.
    return {
        "distance": {
            "base": "klik",
            "ladder": [
                {"min": 1.0e8, "unit": "AU", "factor": AU, "precision": 4},
                {"min": 1.0e3, "unit": "Mm", "factor": MM, "precision": 1},
                {"min": 0, "unit": "klik", "factor": 1.0, "precision": 1},
            ],
        },
        "speed": {
            "base": "kps",
            "factor": 1.0,
            "dial": {"15": "Silent Running", "60": "Cruise", "100": "Full Ahead"},
        },
    }


def test_units_scale_both_directions(flavor_home):
    _flavor(flavor_home, "stk", {"title": "Star Trek"}, units=_star_trek_units())
    stk = flavors.get("stk")
    core = flavors.get("core")
    # 40 AU of canonical distance renders as AU under stk...
    assert stk.units.format_distance(40 * AU) == "40.0000 AU"
    # ...and the same value is plain klik under core, which is the point.
    assert core.units.format_distance(40 * AU) == "5983914828.0 klik"
    # A 40-klik knife fight is still klik under both.
    assert core.units.format_distance(40) == "40.0 klik"
    assert stk.units.format_distance(40) == "40.0 klik"
    assert stk.units.format_distance(2000) == "2.0 Mm"
    assert stk.units.speed_dial_name(60) == "Cruise"
    assert stk.units.unit_label("distance") == "klik"


def test_display_sites_use_the_room_flavor(flavor_home):
    _flavor(flavor_home, "stk", {"title": "Star Trek"}, units=_star_trek_units())
    state = engine.create_state(
        "units", "inst", campaign_for("iron-collar", "stk"), flavor_id="stk"
    )
    assert state.flavorId == "stk"
    assert engine._fd(state, 40 * AU) == "40.0000 AU"
    core_state = engine.create_state(
        "units-core", "inst", campaign_for("iron-collar", "core"), flavor_id="core"
    )
    assert engine._fd(core_state, 40) == "40.0 klik"


def test_flavor_never_enters_the_simulation(flavor_home):
    """Invariant 1: identical simulated time is byte-identical across flavors."""
    _flavor(flavor_home, "stk", {"title": "Star Trek"}, units=_star_trek_units())
    core_state = engine.create_state(
        "same-room", "inst", campaign_for("iron-collar", "core"), flavor_id="core"
    )
    stk_state = engine.create_state(
        "same-room", "inst", campaign_for("iron-collar", "stk"), flavor_id="stk"
    )
    engine.advance(core_state, 120)
    engine.advance(stk_state, 120)
    core_dump = json.loads(core_state.model_dump_json())
    stk_dump = json.loads(stk_state.model_dump_json())
    core_dump.pop("flavorId")
    stk_dump.pop("flavorId")
    assert core_dump == stk_dump


def test_callsign_styles_cover_the_documented_generators():
    from bridge.shared.flavors import Callsigns

    corporate = Callsigns(adjectives=["GRAY"], nouns=["VEGA"], vessel_name="corporate")
    assert corporate.vessel(3) == "MV GRAY VEGA"
    surname = Callsigns(adjectives=["Grey"], nouns=["Falcon"], vessel_name="surname")
    assert surname.vessel(3) == "Grey Falcon"
    callsign = Callsigns(adjectives=["A"], nouns=["Vanguard"], vessel_name="callsign")
    assert callsign.vessel(3).startswith("Vanguard ")
    registry = Callsigns(adjectives=["USS"], nouns=["Enterprise"], vessel_name="registry")
    assert registry.vessel(3) == "USS Enterprise"


def test_registry_flavors_generate_registry_names():
    # stk and sw name their contacts with a registry prefix plus a proper name.
    for flavor_id, prefixes in (("stk", ("USS ", "NCC ", "SS ", "IKS ", "IRW ")), ("sw", ("CR90 ", "GR-75 ", "MC80 ", "ISD ", "SSD "))):
        callsigns = flavors.get(flavor_id).callsigns
        assert callsigns.vessel_name == "registry"
        assert callsigns.vessel(5).startswith(prefixes)


# ---------------------------------------------------------------------------
# Validator: fail closed
# ---------------------------------------------------------------------------

def test_validator_rejects_a_dangling_default(flavor_home):
    _flavor(
        flavor_home,
        "bad",
        {"extends": None},
        ships={"hulls": {"bad.one": _hull("One")}, "defaults": {"escort": "bad.missing"}},
    )
    with pytest.raises(flavors.FlavorError, match="defaults"):
        flavors.load_flavor("bad")


def test_core_defaults_regression_is_caught(flavor_home):
    """The lance-corvette case: a catalog missing a hull core defaults to."""
    core_defaults = json.loads((CORE_DIR / "ships.json").read_text())["defaults"]
    _flavor(
        flavor_home,
        "broken",
        {"extends": None},
        ships={"hulls": {"broken.one": _hull("One")}, "defaults": core_defaults},
    )
    with pytest.raises(flavors.FlavorError):
        flavors.load_flavor("broken")


def test_validator_rejects_a_mission_naming_a_missing_hull(flavor_home):
    mission = {
        "id": "bad.mission",
        "title": "Bad",
        "theater": "Nowhere",
        "brief": "",
        "target": "",
        "startHour": 0,
        "patrol": {"center": {"x": 0, "y": 0, "z": 0}, "radiusKlik": 50},
        "clutter": 0,
        "escalation": 10,
        "contacts": [
            {
                "x": 0,
                "y": 0,
                "heading": 0,
                "speed": 0,
                "type": "fighter",
                "faction": "enemy",
                "hostile": True,
                "emitting": False,
                "shipClass": "bad.ghost",
            }
        ],
    }
    directory = _flavor(
        flavor_home,
        "bad",
        {"extends": None},
        ships={"hulls": {"bad.one": _hull("One")}, "defaults": {"unknown": "bad.one"}},
    )
    _write(directory / "missions" / "bad.mission.json", mission)
    _write(directory / "flavor.json", {"id": "bad", "extends": None, "ships": "ships.json", "missions": "missions/"})
    with pytest.raises(flavors.FlavorError, match="unknown hull"):
        flavors.load_flavor("bad")


def test_validator_rejects_missing_art(flavor_home):
    _flavor(
        flavor_home,
        "bad",
        {"extends": None},
        ships={
            "hulls": {
                "bad.one": _hull("One", art={"action": "not-there.png", "vdu": ""})
            },
            "defaults": {"unknown": "bad.one"},
        },
    )
    with pytest.raises(flavors.FlavorError, match="art not on disk"):
        flavors.load_flavor("bad")


def test_validator_rejects_an_unsorted_ladder():
    with pytest.raises(flavors.FlavorError, match="descending"):
        flavors.parse_units(
            {
                "distance": {
                    "ladder": [
                        {"min": 0, "unit": "klik", "factor": 1.0},
                        {"min": 100, "unit": "Mm", "factor": 1000.0},
                    ]
                }
            }
        )


def test_validator_requires_the_last_rung_to_be_zero():
    with pytest.raises(flavors.FlavorError, match="min 0"):
        flavors.parse_units(
            {"distance": {"ladder": [{"min": 5, "unit": "klik", "factor": 1.0}]}}
        )


def test_validator_rejects_a_non_positive_factor():
    with pytest.raises(flavors.FlavorError, match="positive"):
        flavors.parse_units(
            {"distance": {"ladder": [{"min": 0, "unit": "klik", "factor": 0}]}}
        )


def test_validator_rejects_a_bad_dial_key():
    with pytest.raises(flavors.FlavorError, match="0-100"):
        flavors.parse_units({"speed": {"dial": {"150": "Too fast"}}})


def test_validator_rejects_an_extends_cycle(flavor_home):
    _flavor(flavor_home, "a", {"extends": "b"})
    _flavor(flavor_home, "b", {"extends": "a"})
    with pytest.raises(flavors.FlavorError, match="cycle"):
        flavors.load_flavor("a")


def test_get_fails_closed_to_core_with_a_logged_reason(flavor_home, caplog):
    _flavor(
        flavor_home,
        "bad",
        {"extends": None},
        ships={"hulls": {}, "defaults": {"escort": "bad.missing"}},
    )
    with caplog.at_level("WARNING"):
        resolved = flavors.get("bad")
    assert resolved.id == "core"
    assert "failed to load" in caplog.text


def test_validator_rejects_duplicate_contact_names(flavor_home):
    mission = {
        "id": "bad.dup",
        "title": "Dup",
        "theater": "Nowhere",
        "brief": "",
        "target": "",
        "startHour": 0,
        "patrol": {"center": {"x": 0, "y": 0, "z": 0}, "radiusKlik": 50},
        "clutter": 0,
        "escalation": 10,
        "contacts": [
            {"x": 0, "y": 0, "heading": 0, "speed": 0, "type": "fighter", "faction": "enemy", "hostile": True, "emitting": False, "name": "Same"},
            {"x": 1, "y": 1, "heading": 0, "speed": 0, "type": "fighter", "faction": "enemy", "hostile": True, "emitting": False, "name": "Same"},
        ],
    }
    directory = _flavor(
        flavor_home,
        "bad",
        {"extends": None},
        ships={"hulls": {"bad.one": _hull("One")}, "defaults": {"unknown": "bad.one"}},
    )
    _write(directory / "missions" / "bad.dup.json", mission)
    _write(directory / "flavor.json", {"id": "bad", "extends": None, "ships": "ships.json", "missions": "missions/"})
    with pytest.raises(flavors.FlavorError, match="repeats a contact name"):
        flavors.load_flavor("bad")


def test_non_numeric_hull_fields_fail_closed(flavor_home):
    _flavor(
        flavor_home,
        "bad",
        {"extends": None},
        ships={
            "hulls": {"bad.one": _hull("One", massKt="abc")},
            "defaults": {"unknown": "bad.one"},
        },
    )
    with pytest.raises(flavors.FlavorError, match="massKt"):
        flavors.load_flavor("bad")
    # The fail-closed boundary itself: a ValueError must not escape get()/summaries().
    assert flavors.get("bad").id == "core"
    assert any(row["id"] == "core" for row in flavors.summaries())


def test_a_stat_that_is_not_a_number_fails_closed(flavor_home):
    _flavor(
        flavor_home,
        "bad",
        {"extends": None},
        ships={
            "hulls": {"bad.one": _hull("One", stats={"shieldFore": "abc"})},
            "defaults": {"unknown": "bad.one"},
        },
    )
    with pytest.raises(flavors.FlavorError, match="shieldFore"):
        flavors.load_flavor("bad")


def test_validator_requires_a_hull_catalog(flavor_home):
    _flavor(flavor_home, "empty", {"extends": None}, ships={"hulls": {}, "defaults": {}})
    with pytest.raises(flavors.FlavorError, match="no hulls"):
        flavors.load_flavor("empty")


def test_validator_requires_a_mission(flavor_home):
    _flavor(
        flavor_home,
        "nomissions",
        {"extends": None},
        ships={
            "hulls": {"nomissions.one": _hull("One")},
            "defaults": {"unknown": "nomissions.one"},
        },
    )
    with pytest.raises(flavors.FlavorError, match="no missions"):
        flavors.load_flavor("nomissions")


def test_validator_rejects_an_unknown_defaults_key(flavor_home):
    _flavor(
        flavor_home,
        "typo",
        {"extends": None},
        ships={
            "hulls": {"typo.one": _hull("One")},
            "defaults": {"unknown": "typo.one", "figher": "typo.one"},
        },
    )
    with pytest.raises(flavors.FlavorError, match="unknown contact type"):
        flavors.load_flavor("typo")


def test_validator_rejects_bad_hardpoints(flavor_home):
    _flavor(
        flavor_home,
        "bad",
        {},
        ships={"hulls": {"bad.one": _hull("One", hardpoints="fore-gun")}},
    )
    with pytest.raises(flavors.FlavorError, match="hardpoints must be a list"):
        flavors.load_flavor("bad")


def test_terrain_overrides_resolve_through_the_chain(flavor_home):
    _flavor(flavor_home, "rock", {}, ships={"terrain": {"asteroid": "asteroid.png"}})
    flavors.reset_cache()
    assert flavors.get("rock").terrain_images["asteroid"] == "/img/action/asteroid.png"
    from bridge.shared.ships import terrain_image

    assert terrain_image("asteroid", "rock") == "/img/action/asteroid.png"


def test_missing_terrain_art_fails(flavor_home):
    _flavor(flavor_home, "bad", {}, ships={"terrain": {"asteroid": "nope.png"}})
    with pytest.raises(flavors.FlavorError, match="terrain"):
        flavors.load_flavor("bad")


def test_wc_mm_rung_is_canonical():
    wc_units = flavors.get("wc").units
    # 1 Mm = 1000 klik, so a 200 Mm distance renders in Mm, not klik.
    assert wc_units.format_distance(200_000) == "200.0 Mm"
    assert wc_units.format_speed(60) == "60 kps"


# ---------------------------------------------------------------------------
# Ships, art and the merge layer
# ---------------------------------------------------------------------------


def test_flavor_hull_with_art_resolves_to_the_flavor_image(flavor_home):
    directory = _flavor(
        flavor_home,
        "art",
        {},
        ships={
            "hulls": {
                "art.one": _hull("Art One", art={"action": "art-one.png", "vdu": ""})
            }
        },
    )
    (directory / "assets" / "action").mkdir(parents=True)
    shutil.copy(package_path("img", "action", "enemy-fighter.png"), directory / "assets" / "action" / "art-one.png")
    flavors.reset_cache()
    resolved = flavors.get("art")
    action, _vdu = resolved.ship_art["art.one"]
    assert action == "/img/f/art/action/art-one.png"
    assert resolved.url_exists(action)


def test_flavor_hull_without_art_falls_back_to_core(flavor_home):
    _flavor(flavor_home, "reskin", {}, ships={"hulls": {"home": {"name": "Reskinned"}}})
    flavors.reset_cache()
    resolved = flavors.get("reskin")
    assert resolved.ship_classes["home"].name == "Reskinned"
    # The inherited field is the core art, not a blank.
    assert resolved.ship_art["home"][0] == "/img/action/friendly-cruiser.png"
    assert resolved.url_exists(resolved.ship_art["home"][0])


def test_defaults_are_validated_against_the_merged_catalog(flavor_home):
    _flavor(
        flavor_home,
        "ext",
        {},
        ships={"hulls": {"ext.one": _hull("One")}, "defaults": {"fighter": "ext.one"}},
    )
    flavors.reset_cache()
    resolved = flavors.get("ext")
    # Inherited core hulls remain, and the new default resolves.
    assert "home" in resolved.ship_classes
    assert ship_class("ext.one", "ext").name == "One"
    assert resolved.defaults["fighter"] == "ext.one"


def test_a_flavor_can_replace_core_wholesale(flavor_home):
    """``extends: null`` is a standalone setting: no core hulls or missions leak in."""
    mission = {
        "id": "solo.run",
        "title": "Solo Run",
        "theater": "Nowhere",
        "brief": "",
        "target": "",
        "startHour": 0,
        "patrol": {"center": {"x": 0, "y": 0, "z": 0}, "radiusKlik": 40},
        "clutter": 0.1,
        "escalation": 5,
        "shipClass": "solo.one",
        "contacts": [
            {
                "x": 10,
                "y": 5,
                "heading": 0,
                "speed": 40,
                "type": "fighter",
                "faction": "enemy",
                "hostile": True,
                "emitting": True,
                "shipClass": "solo.one",
            }
        ],
    }
    directory = _flavor(
        flavor_home,
        "solo",
        {"extends": None},
        ships={"hulls": {"solo.one": _hull("Solo One")}, "defaults": {"unknown": "solo.one"}},
    )
    _write(directory / "missions" / "solo.run.json", mission)
    _write(
        directory / "flavor.json",
        {"id": "solo", "extends": None, "ships": "ships.json", "missions": "missions/"},
    )
    flavors.reset_cache()
    solo = flavors.get("solo")
    assert solo.extends is None
    # The core catalog is genuinely absent, not merged in.
    assert set(solo.ship_classes) == {"solo.one"}
    assert "iron-collar" not in solo.missions
    state = engine.create_state(
        "solo-room", "inst", campaign_for("solo.run", "solo"), flavor_id="solo"
    )
    assert state.flavorId == "solo"
    assert state.ship.shipClass == "solo.one"
    assert state.contacts[0].shipClass == "solo.one"


def test_inheritance_is_opt_in(flavor_home):
    """A manifest only inherits when it *names* a parent."""
    from bridge.paths import flavor_extends

    _flavor(flavor_home, "named", {"extends": "core"})
    directory = flavor_home / "unnamed"
    directory.mkdir(parents=True, exist_ok=True)
    _write(directory / "flavor.json", {"id": "unnamed"})

    assert flavor_extends("named") == "core"
    assert flavor_extends("unnamed") is None


# ---------------------------------------------------------------------------
# Folder-is-the-id: no hardcoded ids, copy/paste a folder into a new flavor
# ---------------------------------------------------------------------------


def test_the_directory_name_is_the_flavor_id(flavor_home):
    """A manifest may omit ``id``; the folder supplies it."""
    directory = flavor_home / "plain"
    directory.mkdir()
    _write(directory / "flavor.json", {"extends": "core", "title": "Plain Setting"})
    _write(directory / "ships.json", {"hulls": {"home": {"name": "Plain"}}})
    flavors.reset_cache()
    plain = flavors.load_flavor("plain")
    assert plain.id == "plain"
    assert plain.title == "Plain Setting"


def test_manifest_title_defaults_to_the_folder_name(flavor_home):
    directory = flavor_home / "untitled"
    directory.mkdir()
    _write(directory / "flavor.json", {"extends": "core"})
    _write(directory / "ships.json", {"hulls": {"home": {"name": "Reskinned"}}})
    flavors.reset_cache()
    assert flavors.load_flavor("untitled").title == "Untitled"


def test_a_stale_id_on_a_copied_folder_fails_loudly(flavor_home):
    """An explicit id is an assertion, so a copy that keeps the old one is caught."""
    _flavor(flavor_home, "mine", {"id": "stale"})
    with pytest.raises(flavors.FlavorError, match="does not match directory"):
        flavors.load_flavor("mine")


def test_conventional_files_are_discovered(flavor_home):
    """A manifest may name no files: the conventional names win by default."""
    directory = flavor_home / "conv"
    directory.mkdir()
    _write(directory / "flavor.json", {"extends": "core", "defaultMission": "conv.run"})
    _write(directory / "units.json", _star_trek_units())
    (directory / "theme.css").write_text(":root{--bg:#123}", encoding="utf-8")
    _write(directory / "ships.json", {"hulls": {"home": {"name": "Conventional"}}})
    _write(
        directory / "callsigns.json",
        {"adjectives": ["Zeta"], "nouns": ["Nine"], "vesselName": "surname"},
    )
    _write(directory / "missions" / "conv.run.json", _mission("conv.run", "home"))
    flavors.reset_cache()
    conv = flavors.load_flavor("conv")
    assert conv.id == "conv"
    assert conv.ship_classes["home"].name == "Conventional"
    assert "conv.run" in conv.missions
    assert conv.units.format_distance(40 * AU) == "40.0000 AU"
    assert conv.theme_css == ":root{--bg:#123}"
    assert conv.callsigns.vessel(1) == "Zeta Nine"


def test_an_explicit_null_disables_a_conventional_file(flavor_home):
    """Dropping a copied file need not override it: ``null`` says inherit."""
    directory = flavor_home / "nounits"
    directory.mkdir()
    _write(directory / "flavor.json", {"extends": "core", "units": None})
    _write(directory / "units.json", _star_trek_units())
    flavors.reset_cache()
    assert flavors.load_flavor("nounits").units.format_distance(40) == "40.0 klik"


def test_a_folder_of_files_needs_no_manifest(flavor_home):
    """Drop a complete folder in; the folder name is the id and title."""
    shutil.copytree(flavor_home / "core", flavor_home / "loose")
    (flavor_home / "loose" / "flavor.json").unlink()
    flavors.reset_cache()
    assert "loose" in flavors.available()
    loose = flavors.get("loose")
    assert loose.id == "loose"
    assert loose.title == "Loose"
    assert len(loose.hull_defs) == 15
    assert len(loose.missions) == 9


def test_copying_a_flavor_folder_makes_a_new_flavor(flavor_home):
    """The headline workflow: ``cp -r``, no edits, and it is a new setting."""
    shutil.copytree(flavor_home / "core", flavor_home / "mine")
    flavors.reset_cache()
    assert "mine" in flavors.available()
    mine = flavors.get("mine")
    assert mine.id == "mine"
    assert len(mine.hull_defs) == 15
    state = engine.create_state(
        "mine-room", "inst", campaign_for(mine.first_mission_or(), "mine"), flavor_id="mine"
    )
    assert state.flavorId == "mine"
    engine.advance(state, 30)


def test_discovery_ignores_directories_that_are_not_flavors():
    available = flavors.available()
    assert "schema" not in available
    assert "core" in available


def test_discovery_uses_project_mods_then_the_packaged_fallback(tmp_path, monkeypatch):
    """The checkout's project-root mods/ wins; a wheel's packaged tree falls back."""
    project = tmp_path / "project"
    (project / "mods" / "core").mkdir(parents=True)
    (project / "mods" / "core" / "ships.json").write_text("{}", encoding="utf-8")
    packaged = tmp_path / "packaged"
    (packaged / "flavors" / "core").mkdir(parents=True)
    (packaged / "flavors" / "core" / "ships.json").write_text("{}", encoding="utf-8")

    from bridge import paths

    monkeypatch.delenv("FLAVORS_DIR", raising=False)
    monkeypatch.setattr(paths, "PROJECT_ROOT", project)
    monkeypatch.setattr(paths, "package_path", lambda *parts: packaged.joinpath(*parts))

    assert paths.flavor_roots() == [project / "mods", packaged / "flavors"]
    # The project-root copy is the one an id resolves to.
    assert paths.flavor_dir("core") == project / "mods" / "core"


def test_available_merges_roots_without_duplicating_ids(tmp_path, monkeypatch):
    first, second = tmp_path / "first", tmp_path / "second"
    for root, name in (
        (first, "dup"),
        (first, "shared"),
        (second, "dup"),
        (second, "only"),
    ):
        (root / name).mkdir(parents=True)
        (root / name / "ships.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(flavors, "flavor_roots", lambda: [first, second])
    assert sorted(flavors.available()) == ["dup", "only", "shared"]


def test_the_example_universe_mods_are_standalone():
    """Mods are alternative universes: no core hull or mission may leak in."""
    core = flavors.get("core")
    core_hulls = set(core.hull_defs)
    core_missions = set(core.missions)
    for fid in ("wc", "stk", "sw"):
        mod = flavors.get(fid)
        assert mod.extends is None
        assert not (set(mod.hull_defs) & core_hulls), fid
        assert not (set(mod.missions) & core_missions), fid
        # Everything is namespaced under the mod's own id.
        assert all(h.startswith(f"{fid}.") for h in mod.hull_defs), fid
        assert all(m.startswith(f"{fid}.") for m in mod.missions), fid


def test_art_urls_are_per_flavor_for_a_flavor_hull():
    wc = flavors.get("wc")
    # The crew hull id is read from the flavor, not hardcoded, because the
    # retired-vocabulary gate scans this file.
    crew = wc.defaults["unknown"]
    action, vdu = ship_art(crew, "wc")
    # wc ships no assets of its own, so its hulls resolve through core art.
    assert action == "/img/action/friendly-carrier.png"
    assert wc.url_exists(action)
    # The registry name comes from the flavor's own ships.json.
    expected_name = json.loads(
        (PROJECT_ROOT / "mods" / "wc" / "ships.json").read_text(encoding="utf-8")
    )["hulls"][crew]["names"][0]
    assert wc.ship_names[crew] == expected_name


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------


def test_core_theme_is_unchanged():
    css = flavors.get("core").theme_css
    assert "--bg:#0b0d17" in css
    assert "--font-mono:'Share Tech Mono',monospace" in css


def test_flavor_theme_overrides_core(flavor_home):
    directory = _flavor(flavor_home, "dark", {})
    (directory / "theme.css").write_text(":root{--bg:#000}", encoding="utf-8")
    _write(directory / "flavor.json", {"id": "dark", "extends": "core", "theme": "theme.css"})
    flavors.reset_cache()
    assert flavors.get("dark").theme_css == ":root{--bg:#000}"


def test_missing_theme_falls_back_to_core(flavor_home):
    _flavor(flavor_home, "notheme", {"theme": "missing.css"})
    flavors.reset_cache()
    resolved = flavors.get("notheme")
    assert resolved.theme_css == flavors.get("core").theme_css


def test_index_injection_places_the_theme_after_activity_css():
    from bridge.server.main import _render_index

    html = _render_index(package_path("activity", "dist"), "wc")
    css_at = html.index('href="/activity.css"')
    theme_at = html.index('href="/flavor/wc/theme.css"')
    assert css_at < theme_at
    # The link is addressable so the client can swap it without a reload.
    assert 'id="flavor-theme"' in html


def _theme_var(css: str, name: str) -> str:
    import re

    match = re.search(rf"{re.escape(name)}\s*:\s*([^;]+);", css)
    assert match, f"{name} missing from theme"
    return match.group(1).strip()


def test_every_mod_ships_its_own_distinct_theme():
    """Each universe brings its own palette, type pairing and surface tokens."""
    themes = {fid: flavors.get(fid).theme_css for fid in ("core", "wc", "stk", "sw")}
    for fid, css in themes.items():
        assert css.strip(), fid
        for token in ("--bg:", "--accent:", "--font-display:", "--font-mono:"):
            assert token in css, f"{fid} is missing {token}"
        # Surface tokens are what stop a mod from fighting hardcoded core cyan.
        _theme_var(css, "--tint-rgb")
        _theme_var(css, "--panel-bg")

    def values(name):
        return {fid: _theme_var(css, name) for fid, css in themes.items()}

    # Every mod brings its own palette, type and panel surface.
    for token in ("--font-display", "--font-mono", "--accent", "--tint-rgb", "--panel-bg"):
        assert len(set(values(token).values())) == 4, f"mods share {token}"


@pytest.mark.parametrize(
    ("fid", "family"),
    [("wc", "Chakra Petch"), ("stk", "Orbitron"), ("sw", "Oxanium")],
)
def test_each_mod_uses_and_fetches_its_display_face(fid, family):
    """Naming a family without importing it silently falls back to system-ui."""
    css = flavors.get(fid).theme_css
    assert _theme_var(css, "--font-display").startswith(f"'{family}'")
    assert f"family={family.replace(' ', '+')}" in css


def test_a_mods_theme_is_served_at_its_own_route():
    from bridge.server.main import flavor_theme

    core = asyncio.run(flavor_theme("core"))
    wc = asyncio.run(flavor_theme("wc"))
    assert core.status_code == 200 and wc.status_code == 200
    assert core.body != wc.body
    assert b"Chakra Petch" in wc.body  # wc ships and loads its own display face


def test_theme_route_serves_css():
    from bridge.server.main import flavor_theme

    response = asyncio.run(flavor_theme("core"))
    assert response.status_code == 200
    assert b"--bg:#0b0d17" in response.body


# ---------------------------------------------------------------------------
# Per-flavor cache and rooms
# ---------------------------------------------------------------------------


def test_two_flavors_keep_their_own_catalogs_in_one_process():
    core = flavors.get("core")
    wc = flavors.get("wc")
    assert core is not wc
    assert core.ship_classes["home"] is not wc.ship_classes.get("home")
    assert core.defaults["unknown"] == "home"
    assert wc.defaults["unknown"].startswith("wc.")
    assert wc.defaults["unknown"] in wc.ship_classes
    assert wc.defaults["unknown"] != core.defaults["unknown"]
    assert core.units.format_distance(40) == "40.0 klik"
    assert wc.units is not core.units


def test_per_flavor_caches_are_safe_under_concurrent_first_use():
    flavors.reset_cache()

    def resolve(flavor_id: str) -> str:
        return flavors.get(flavor_id).id

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(resolve, ["core", "wc"] * 4))
    assert results == ["core", "wc"] * 4
    assert flavors.get("core").ship_art["home"][0].startswith("/img/action/")
    wc = flavors.get("wc")
    assert wc.ship_art[wc.defaults["unknown"]][0].startswith("/img/action/")


def test_a_room_remembers_its_flavor():
    state = engine.create_state(
        "wc-room", "inst", campaign_for("wc.vega-patrol", "wc"), flavor_id="wc"
    )
    assert state.flavorId == "wc"
    assert state.ship.shipClass == flavors.get("wc").defaults["unknown"]
    assert state.contacts[0].shipClass.startswith("wc.")


def test_handoff_pack_names_the_setting():
    state = engine.create_state(
        "handoff-wc", "inst", campaign_for("wc.vega-patrol", "wc"), flavor_id="wc"
    )
    state.contacts[0].everDetected = True
    engine.force_handoff(state, "Captain")
    assert state.handoffPack is not None
    assert state.handoffPack.flavorId == "wc"
    assert state.handoffPack.flavorTitle == flavors.get("wc").title


def test_removed_flavor_falls_back_to_core_on_reload(monkeypatch):
    state = engine.create_state(
        "ghost-room", "inst", campaign_for("iron-collar", "core"), flavor_id="core"
    )
    state.flavorId = "ghost"
    monkeypatch.setattr(rooms_mod, "load_room", lambda channel: state)
    room = rooms_mod.Room.load_or_create("ghost-room", "inst")
    assert room.state.flavorId == "core"
    # Still playable: the sim advances without a missing-flavor crash.
    engine.advance(room.state, 30)


def test_room_reconfigure_preserves_seats():
    flavor_home_state = engine.create_state(
        "reconf", "inst", campaign_for("iron-collar", "core"), flavor_id="core"
    )
    room = rooms_mod.Room("reconf", "inst", flavor_home_state)
    mods.activate("wc")
    asyncio.run(room.reconfigure(flavor_id="wc", campaign_id="wc.vega-patrol"))
    assert room.state.flavorId == "wc"
    assert room.state.campaign.id == "wc.vega-patrol"


def test_default_flavor_env_picks_the_room_setting(monkeypatch):
    monkeypatch.setenv("DEFAULT_FLAVOR", "wc")
    assert flavors.default_flavor_id() == "wc"
    monkeypatch.setenv("DEFAULT_FLAVOR", "not-installed")
    assert flavors.default_flavor_id() == "core"


# ---------------------------------------------------------------------------
# CLI / schemas
# ---------------------------------------------------------------------------


def test_list_flavors_cli(capsys):
    from bridge.server.main import main

    import sys

    argv = sys.argv
    sys.argv = ["bridge", "--list-flavors"]
    try:
        main()
    finally:
        sys.argv = argv
    out = capsys.readouterr().out
    assert "core" in out
    assert "wc" in out
    assert "INVALID" not in out


def test_check_flavor_cli_reports_failure(flavor_home, capsys):
    from bridge.server.main import main

    import sys

    _flavor(
        flavor_home,
        "bad",
        {"extends": None},
        ships={"hulls": {}, "defaults": {"escort": "bad.missing"}},
    )
    argv = sys.argv
    sys.argv = ["bridge", "--check-flavor", "bad"]
    try:
        with pytest.raises(SystemExit) as excinfo:
            main()
    finally:
        sys.argv = argv
    assert excinfo.value.code == 1
    assert "FAIL bad" in capsys.readouterr().out


def test_shipped_schemas_are_valid_json():
    schema_dir = PROJECT_ROOT / "mods" / "schema"
    names = sorted(path.name for path in schema_dir.glob("*.json"))
    assert names == [
        "callsigns.schema.json",
        "flavor.schema.json",
        "mission.schema.json",
        "ships.schema.json",
        "units.schema.json",
    ]
    for path in schema_dir.glob("*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc["$schema"].startswith("https://json-schema.org/")


def test_every_shipped_flavor_loads():
    rows = {row["id"]: row for row in flavors.summaries()}
    assert rows["core"]["valid"]
    for flavor_id in ("wc", "stk", "sw"):
        assert rows[flavor_id]["valid"], rows[flavor_id].get("error")
        # Each example re-skins core's roles and adds its own scenarios.
        assert rows[flavor_id]["hulls"] >= 15
        assert rows[flavor_id]["missions"] >= 2


@pytest.mark.parametrize(
    "flavor_id,mission_id",
    [
        ("wc", "wc.vega-patrol"),
        ("stk", "stk.babel"),
        ("sw", "sw.kessel-run"),
    ],
)
def test_example_mods_are_namespaced_and_playable(flavor_id, mission_id):
    flavor = flavors.get(flavor_id)
    # Every hull the example defines is namespaced under the flavor id.
    added = {h for h in flavor.ship_classes if h.startswith(f"{flavor_id}.")}
    assert added, flavor_id
    assert all(h.startswith(f"{flavor_id}.") for h in added)
    # Its own missions and defaults resolve inside the merged catalog.  The
    # crew hull id is read from the flavor, not hardcoded, because the
    # retired-vocabulary gate scans this file.
    assert mission_id in flavor.missions
    default_hull = flavor.defaults["unknown"]
    assert default_hull.startswith(f"{flavor_id}.")
    assert default_hull in flavor.ship_classes
    # A room can actually be built and advanced on the setting.
    state = engine.create_state(
        f"{flavor_id}-room", "inst", campaign_for(mission_id, flavor_id), flavor_id=flavor_id
    )
    assert state.flavorId == flavor_id
    assert state.ship.shipClass.startswith(f"{flavor_id}.")
    engine.advance(state, 30)
