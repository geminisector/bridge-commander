"""Regression tests for the shared CAPTAIN layer.

The important one is :func:`hash_random`: the JS implementation multiplies as
IEEE-754 doubles and then ``ToInt32`` truncates, which is subtly different from
naively masking every step to 32 bits (the recipe MIGRATION.md suggests).  These
expected values were produced by running the original ``math.ts``/``campaigns.ts``
under Node 22.
"""

from __future__ import annotations

import math
import struct

import pytest

from bridge.shared import (
    CAMPAIGN_TITLES,
    CAMPAIGNS,
    DEFAULT_EMCON,
    EMISSION_LINES,
    ENVIRONMENTAL_TYPES,
    HYDROGEN_BAND,
    MASS_KT,
    REFLECTION_LINES,
    SHIP_ART,
    SHIP_CLASSES,
    SPECTRAL_SUMMARY,
    SPECTRUM_BINS,
    TYPE_NAMES,
    Vec,
    audit_ship_art,
    campaign_for,
    describe_type,
    digest_text,
    format_clock,
    hash_random,
    noise,
    roe_label,
    state_of_confidence,
)
from bridge.shared.types import LogbookDigest


@pytest.mark.parametrize(
    "seed_a,seed_b,salt,expected",
    [
        (7, 11, 0, 0.0758),
        (7, 12, 0, 0.68646),
        (7, 1, 0, 0.46901),
        (7, 2, 0, 0.413),
        (12345, 678, 9, 0.30978),
        (0, 0, 0, 0.0),
        (40, 200, 0, 0.54875),
        (2, 45, 0, 0.36757),
        # Float seeds (engine passes state.clock) must also match Node.
        (30.0, 5, 0, 0.09319),
        (17.5, 1, 0, 0.90926),
    ],
)
def test_hash_random_matches_js(seed_a, seed_b, salt, expected):
    assert hash_random(seed_a, seed_b, salt) == pytest.approx(expected, abs=1e-9)


def test_noise_matches_js():
    assert noise(7, 3) == pytest.approx(-0.3539700000000001, abs=1e-12)
    assert noise(12345, 5) == pytest.approx(-1.12805, abs=1e-12)


def test_campaign_seed_circle_matches_js():
    # cos(hashRandom(7,1)*2pi) * (30 + hashRandom(7,101)*60)
    x = math.cos(hash_random(7, 1) * math.pi * 2) * (30 + hash_random(7, 101) * 60)
    assert x == pytest.approx(-36.838443300168386, abs=1e-9)


def test_campaign_for_defaults_and_titles():
    assert campaign_for(None).id == "iron-collar"
    assert campaign_for("does-not-exist").id == "iron-collar"
    assert campaign_for("whale-road").title == "Whale Road Run"
    assert set(CAMPAIGN_TITLES) == set(CAMPAIGNS)
    assert len(CAMPAIGN_TITLES) == 9
    # The three scenarios built around the patrol victory conditions.
    assert campaign_for("silent-vigil").title == "Silent Vigil"
    assert campaign_for("empty-lane").title == "The Empty Lane"
    assert campaign_for("full-sweep").title == "Full Sweep"


def test_campaign_contacts_are_visible_but_unknown_state_on_creation():
    c = campaign_for("iron-collar")
    assert len(c.contacts) == 8
    # Seed is ord('i') == 105, verified against the original campaigns.ts under Node.
    assert c.contacts[0].x == -15
    assert c.contacts[0].y == -58
    assert c.contacts[0].heading == 282
    # Speeds are lifted onto the shared 0-100 kps dial.
    assert c.contacts[0].speed == 30


def test_shared_helpers():
    assert describe_type("escort") == "Escort corvette"
    assert roe_label("free") == "WEAPONS FREE"
    assert state_of_confidence(0.5) == "probable"
    assert state_of_confidence(0.05) == "unknown"
    assert format_clock(0) == "Day 1 00:00"
    assert format_clock(1499) == "Day 2 00:59"
    assert DEFAULT_EMCON.radar is False
    assert TYPE_NAMES["unknown"] == "UNKNOWN"


def test_event_ids_use_js_number_formatting():
    """JS template literals render 120.0 as "120"; ids must match the TS."""
    from bridge.shared.events import make_event

    class _S:
        clock = 120.0

    for template in (
        "fleetnet",
        "unmarked",
        "distress",
        "orders",
        "probe",
        "relay",
        "challenge",
        "civilian",
        "false-surrender",
        "weapons-warning",
    ):
        assert make_event(_S(), template).id == f"{template}-120"


def test_digest_text():
    d = LogbookDigest(
        title="Test Box",
        theater="Test Reach",
        durationMinutes=125,
        contactsSeen=4,
        classifiedCount=2,
        hostileConfirmed=1,
        handoffs=1,
        rpNotes=3,
        generatedAt=0,
    )
    text = digest_text(d)
    assert "after-action log" in text
    assert "Duration: 2h 5m" in text


def test_vec_serialization_is_camel_case_and_aliases_class():
    from bridge.shared.types import GameState, ShipState

    ship = ShipState(
        name="Test",
        className="Kamekh",
        registry="TEST-1",
        pos=Vec(x=1, y=2, z=3),
        heading=0,
        speed=8,
        cruiseSpeed=8,
        quietSpeed=4,
        maxSpeed=12,
        emcon=DEFAULT_EMCON,
        mode="cruise",
        condition="green",
        roe="safe",
        exposure=0,
        readiness=1,
        hull=1,
        battery=1,
        sensorQuality=1,
        selfNoise=0,
        altTarget=0,
    )
    dumped = ship.model_dump()
    assert dumped["class"] == "Kamekh"
    assert "className" not in dumped
    assert dumped["pos"] == {"x": 1.0, "y": 2.0, "z": 3.0}
    # GameState.schemaVersion is aliased back to the wire key "schema".
    assert GameState.model_fields["schemaVersion"].alias == "schema"
    # The active-radar toggle is part of the wire contract the UI reads; the
    # rest of the sensor fit runs without a mode.
    assert dumped["activeSensor"] is False
    assert "sensorMode" not in dumped


def test_type_names_cover_the_environmental_returns():
    assert describe_type("asteroid") == "Asteroid field"
    assert describe_type("nebula") == "Nebula"
    assert describe_type("debris") == "Debris field"


def test_environmental_types_have_gravidar_mass_and_spectra():
    for t in ENVIRONMENTAL_TYPES:
        assert t in MASS_KT
        assert len(EMISSION_LINES[t]) + len(REFLECTION_LINES[t]) > 0
        assert t in SPECTRAL_SUMMARY
    # A nebula is the emission-line case; an asteroid is the reflection case.
    assert sum(s for _, _, s in EMISSION_LINES["nebula"]) > sum(
        s for _, _, s in REFLECTION_LINES["nebula"]
    )
    assert sum(s for _, _, s in REFLECTION_LINES["asteroid"]) > sum(
        s for _, _, s in EMISSION_LINES["asteroid"]
    )
    for name, pos, strength in REFLECTION_LINES["asteroid"]:
        assert name
        assert 0 <= pos <= 1
        assert 0 <= strength <= 1


def test_spectrum_bins_and_hydrogen_band_are_sane():
    assert SPECTRUM_BINS >= 16
    assert 0 < HYDROGEN_BAND < 1



def test_packaged_catalogs_are_complete():
    from bridge.shared.checks import ALL_SKILLS
    from bridge.shared.drives import DRIVES
    from bridge.shared.environments import ENVIRONMENTS
    from bridge.shared.shipyard import HULLS, MODULES

    assert len(ALL_SKILLS) >= 40
    assert set(DRIVES) == {"standard", "morvan", "akwende"}
    assert len(ENVIRONMENTS) == 9
    assert len(HULLS) == 15
    assert set(MODULES) == {
        "shield-booster",
        "long-range-array",
        "auxiliary-tankage",
        "machine-shop",
        "ablative-plating",
    }
    for campaign_id in CAMPAIGNS:
        campaign = campaign_for(campaign_id)
        assert campaign.events, campaign_id
        assert campaign.navPoints, campaign_id
    assert campaign_for("rubble-run").hazards
    assert campaign_for("full-sweep").barriers
    assert len(campaign_for(None).layers) == 4


def test_every_hull_has_runtime_defense_and_fuel_stats():
    for hull in SHIP_CLASSES.values():
        assert hull.shieldFore > 0, hull.id
        assert hull.shieldAft > 0, hull.id
        assert hull.shieldRefresh > 0, hull.id
        assert hull.armorFore > 0, hull.id
        assert hull.body > 0, hull.id
        assert hull.fuelCapacity > 0, hull.id


def test_ship_catalog_is_complete_and_briefs_match():
    from bridge.shared import ship_briefs

    briefs = ship_briefs()
    assert len(briefs) == len(SHIP_CLASSES)
    ids = {b.id for b in briefs}
    assert ids == set(SHIP_CLASSES)
    for b in briefs:
        hull = SHIP_CLASSES[b.id]
        assert b.massKt == hull.massKt
        assert b.profile == hull.profile
        assert b.stealth == hull.stealth


def test_ship_lookup_falls_back_by_contact_type_and_to_default():
    from bridge.shared import DEFAULT_SHIP_CLASS, ship_class, ship_for_type, ship_name

    assert ship_class("salthi-fighter").id == "salthi-fighter"
    assert ship_class("nope").id == DEFAULT_SHIP_CLASS
    assert ship_for_type("capship").id == "ralatha-destroyer"
    assert ship_for_type("capship", "fralthi-carrier").id == "fralthi-carrier"
    assert ship_name("fralthi-carrier") == "KIS Fury"
    assert ship_name("bengal-carrier") == "CSV Bengal"
    assert ship_name("broadsword-bomber") == "KIS Broadsword"


def test_obstacle_effects_cover_every_environmental_type():
    from bridge.shared import (
        ENVIRONMENTAL_TYPES,
        OBSTACLE_EFFECTS,
        OBSTACLE_RADIUS,
    )

    for t in ENVIRONMENTAL_TYPES:
        eff = OBSTACLE_EFFECTS[t]
        assert OBSTACLE_RADIUS[t] > 0
        assert 0 <= eff.block <= 1
        assert 0 <= eff.scatter <= 1
        assert 0 <= eff.reflect <= 1
        # Every obstacle must do *something*.
        assert eff.block + eff.scatter + eff.reflect > 0
    # Ice is the refractor; dust is the scatterer; asteroid is the wall.
    assert OBSTACLE_EFFECTS["ice"].reflect > OBSTACLE_EFFECTS["dust"].reflect
    assert OBSTACLE_EFFECTS["dust"].scatter > OBSTACLE_EFFECTS["asteroid"].scatter
    assert OBSTACLE_EFFECTS["asteroid"].block > OBSTACLE_EFFECTS["ice"].block


def test_ship_catalog_speeds_and_barcodes():
    from bridge.shared import (
        CRUISE_KPS,
        FLANK_KPS,
        FREQ_BANDS,
    )

    assert {"home", "grikath-fighter"} <= set(SHIP_CLASSES)
    for h in SHIP_CLASSES.values():
        assert h.cruiseSpeed == CRUISE_KPS
        assert h.maxSpeed == FLANK_KPS
        assert len(h.bands) == FREQ_BANDS


def test_sumn_tpka_campaign_exists():
    from bridge.shared import CAMPAIGNS, campaign_for

    assert "sumn-tpka" in CAMPAIGNS
    c = campaign_for("sumn-tpka")
    assert c.title == "Sumn Tp'ka"
    assert c.shipClass == "home"


def test_ship_art_resolves_from_the_package_and_exists_on_disk():
    from bridge.paths import asset_root
    from bridge.shared import SHIP_ART, ship_art

    root = asset_root()
    for hull in SHIP_CLASSES.values():
        image, vdu = ship_art(hull.id)
        assert image, f"{hull.id} has no renderable image"
        assert image.startswith("/img/"), image
        assert (root / image.removeprefix("/img/")).is_file(), f"missing file for {image}"
        if vdu:
            assert (root / vdu.removeprefix("/img/")).is_file(), f"missing file for {vdu}"
    assert SHIP_ART["drayman-transport"][0].endswith("drayman.png")
    assert SHIP_ART["drayman-transport"][1].endswith("drayman-vdu.gif")
    assert SHIP_ART["longhaul-freighter"][1].endswith("longhaul-vdu.png")


def test_placeholder_art_is_128_by_128():
    from bridge.paths import asset_root

    images = [
        path
        for path in asset_root().rglob("*")
        if path.suffix.lower() in {".gif", ".png"}
    ]
    assert images
    for path in images:
        header = path.read_bytes()[:10]
        if path.suffix.lower() == ".png":
            assert header[:8] == b"\x89PNG\r\n\x1a\n"
            full_header = path.read_bytes()[:24]
            size = struct.unpack(">II", full_header[16:24])
        else:
            assert header[:6] in {b"GIF87a", b"GIF89a"}
            size = struct.unpack("<HH", header[6:10])
        assert size == (128, 128), path


def test_ship_art_audit_reports_no_errors():
    errors = [f for f in audit_ship_art() if f.startswith("ERROR:")]
    assert errors == [], errors


def test_fralthi_and_ralatha_keep_their_own_art():
    # The canonical data file must not let a cruiser borrow its neighbour's hull.
    assert SHIP_ART["fralthi-carrier"][0] != SHIP_ART["ralatha-destroyer"][0]
    assert SHIP_ART["ralatha-destroyer"][0].endswith("ralatha.png")
    assert SHIP_ART["home"][0].endswith("fralthi.png")


def test_unknown_hull_returns_no_art():
    from bridge.shared import ship_art

    assert ship_art("does-not-exist") == ("", "")
