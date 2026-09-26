"""Ported from ``apps/server/test/engine.test.ts`` (vitest → pytest).

Assertions and semantics mirror the TypeScript suite one-for-one; nothing is
weakened to accommodate the port.
"""

from __future__ import annotations

import pytest

from bridge.shared import *
from bridge.server.engine import *


def make_state() -> GameState:
    campaign = CampaignSeed(
        id="test",
        title="Test Box",
        theater="Test Reach",
        brief="brief",
        target="target",
        startHour=0,
        patrol=Patrol(center=Vec(x=0, y=0, z=0), radiusKlik=90),
        clutter=0,
        escalation=30,
        contacts=[
            ContactTemplate(
                x=20,
                y=0,
                heading=270,
                speed=4,
                type="freighter",
                faction="neutral",
                hostile=False,
                emitting=False,
            ),
            ContactTemplate(
                x=25,
                y=0,
                heading=0,
                speed=12,
                type="escort",
                faction="enemy",
                hostile=True,
                emitting=True,
            ),
            ContactTemplate(
                x=200,
                y=200,
                heading=270,
                speed=6,
                type="capship",
                faction="enemy",
                hostile=True,
                emitting=False,
            ),
        ],
        events=[],
    )
    return create_state("chan-1", "inst-1", campaign)


def start(s: GameState) -> GameState:
    s.status = "running"
    return s


class TestEngineBasics:
    def test_creates_a_lobby_with_hidden_contacts_and_empty_seats(self):
        s = make_state()
        assert s.status == "lobby"
        assert len(s.contacts) == 3
        assert all(c.state == "unknown" for c in s.contacts)
        assert all(seat.player is None for seat in s.seats.values())

    def test_advances_the_clock_and_passively_detects_a_nearby_freighter(self):
        s = start(make_state())
        # Park the hostile pickets far away: this case is about the passive
        # picture filling in, not the detection race.
        for c in s.contacts:
            if c.hostile:
                c.pos = Vec(x=300, y=300, z=0)
        before = len(s.log)
        advance(s, 480)
        assert s.clock >= 30
        assert len(s.log) > before
        near = next(c for c in s.contacts if c.trueType == "freighter")
        assert near.everDetected is True
        assert len(near.bearingHistory) > 0

    def test_leaves_far_contacts_undetected_but_moving(self):
        s = start(make_state())
        far = next(c for c in s.contacts if c.trueType == "capship")
        before = {"x": far.pos.x, "y": far.pos.y}
        advance(s, 120)
        assert far.everDetected is False
        assert abs(far.pos.x - before["x"]) + abs(far.pos.y - before["y"]) > 0


def test_sequence_ids_are_isolated_per_room():
    a = create_state("room-a", "inst", campaign_for(None))
    b = create_state("room-b", "inst", campaign_for(None))

    log(a, "A", "first")
    log(b, "B", "first")
    buoy_a = deploy_buoy(a)
    buoy_b = deploy_buoy(b)
    log(a, "A", "second")

    assert a.log[0].id == b.log[0].id == 1
    assert a.log[1].id == 2
    assert buoy_a.id == buoy_b.id == "buoy-1"
    assert a.contacts[0].name == b.contacts[0].name == "TRACK-01"


class TestClassification:
    def test_claiming_is_blind_and_scored_on_evidence_not_correctness(self):
        s = make_state()
        contact = s.contacts[0]
        contact.everDetected = True
        contact.confidence = 0.0
        contact.waveform = Waveform(progress=0.0, resolved=False)

        # A bare call on an unresolved track stores the tag but barely moves the
        # needle, and never says whether the call was right.
        claim_contact(s, contact.id, "escort")
        bare = contact.confidence
        assert contact.guess == "escort"
        assert 0 < bare <= 0.16
        assert contact.state != "confirmed"

        # A call backed by a resolved spectrum adds the whole evidence step on
        # top of the same Check outcome (the Check salt is unchanged).
        contact.waveform.resolved = True
        before = contact.confidence
        claim_contact(s, contact.id, "freighter")
        resolved_gain = contact.confidence - before
        assert resolved_gain - bare > 0.10
        assert contact.guess == "freighter"
        assert contact.state != "confirmed"

    def test_sustained_evidence_can_confirm_and_release_the_name(self):
        s = make_state()
        c = s.contacts[0]
        c.everDetected = True
        c.waveform = Waveform(progress=1.0, resolved=True)
        for _ in range(6):
            claim_contact(s, c.id, c.trueType)
        assert c.state == "confirmed"
        assert c.name == c.trueName

    def test_confidence_maps_to_the_ladder_states(self):
        s = make_state()
        c = s.contacts[0]
        bump_confidence(s, c, 1.0)
        assert c.state == "confirmed"

    def test_ignore_drops_the_track(self):
        s = make_state()
        c = s.contacts[0]
        c.everDetected = True
        c.confidence = 0.5
        c.state = "probable"
        ignore_contact(s, c.id)
        assert c.state == "unknown"


class TestExposureAndSweep:
    def test_active_sweep_raises_exposure_and_tags_returns(self):
        s = make_state()
        before = s.ship.exposure
        active_sweep(s)
        assert s.ship.exposure > before + 10
        near = next(c for c in s.contacts if c.trueType == "freighter")
        assert any(b.source == "active" for b in near.bearingHistory)


class TestWaveformListenAndGravidar:
    def test_listen_resolves_the_spectrum_but_not_the_identity(self):
        s = make_state()
        c = s.contacts[0]
        c.everDetected = True
        c.waveform = Waveform(progress=0, resolved=False)
        base = c.confidence
        before = s.ship.exposure
        for _ in range(7):
            listen_waveform(s, c.id)
        assert c.waveform.resolved is True
        assert c.waveform.progress == 1
        # The barcode is evidence, not an answer key: the crew still has to call
        # the track, and the sensor watch does not confirm it for them.
        assert c.guess != c.trueType
        assert c.confidence > base
        assert s.ship.exposure > before
        assert c.sensor.catalogueMatches  # candidates offered, truth withheld

    def test_listens_beyond_resolution_are_no_ops_on_progress(self):
        s = make_state()
        c = s.contacts[0]
        c.everDetected = True
        c.waveform = Waveform(progress=0, resolved=False)
        for _ in range(8):
            listen_waveform(s, c.id)
        assert c.waveform.progress == 1
        assert c.guess != c.trueType

    def test_grav_scan_reads_mass_for_detected_contacts_in_range(self):
        s = make_state()
        set_mode(s, "cruise")
        c = s.contacts[0]
        c.everDetected = True
        before = s.ship.exposure
        grav_scan(s)
        assert c.gravRead is not None
        assert s.ship.exposure > before
        assert any("Gravar sweep" in e.text for e in s.log)

    def test_grav_scan_warns_when_the_debris_field_lies(self):
        s = make_state()
        s.campaign.clutter = 0.8
        set_mode(s, "cruise")
        c = s.contacts[0]
        c.everDetected = True
        grav_scan(s)
        assert any("debris field is lying" in e.text for e in s.log)


class Test3DAndNoise:
    def test_moves_contacts_and_ship_in_z_as_well_as_xy(self):
        s = start(make_state())
        c = next(x for x in s.contacts if x.trueType == "freighter")
        active_sweep(s)
        active = next((b for b in c.bearingHistory if b.source == "active"), None)
        assert active is not None
        assert c.estimated is not None
        assert c.estimated.z is not None

    def test_the_noise_floor_grows_and_net_filtering_resets_part_of_it(self):
        s = start(make_state())
        assert s.noise == pytest.approx(1.5, abs=0.05)
        advance(s, 120)
        grown = s.noise
        assert grown > 1.5
        filter_noise(s)
        assert s.noise < grown
        assert s.noise >= 0.8
        assert s.noiseFilterAt is not None and s.noiseFilterAt > s.clock

    def test_noise_filter_is_on_cooldown_right_after_a_run(self):
        s = start(make_state())
        filter_noise(s)
        after = s.noise
        filter_noise(s)
        assert s.noise == after
        assert any("recooling" in e.text for e in s.log)

    def test_set_altitude_clamps_and_the_ship_holds_altitude(self):
        s = start(make_state())
        set_altitude(s, 30)
        assert s.ship.altTarget == 30
        advance(s, 30)
        assert s.ship.pos.z > 0
        set_altitude(s, 999)
        assert s.ship.altTarget == 50

    def test_radar_as_the_active_emitter_paints_contacts_with_elevation(self):
        s = start(make_state())
        freighter = next(c for c in s.contacts if c.trueType == "freighter")
        before = s.ship.exposure
        active_sweep(s)
        assert s.ship.exposure > before + 20
        mark = next((b for b in freighter.bearingHistory if b.source == "active"), None)
        assert mark is not None and mark.elev is not None
        assert any("Radar return" in e.text for e in s.log)

    def test_gravidar_reads_clean_up_as_relative_velocity_grows(self):
        s = start(make_state())
        set_mode(s, "cruise")
        c = s.contacts[0]
        c.everDetected = True
        c.heading = s.ship.heading
        c.speed = s.ship.speed  # parked alongside on the same course
        grav_scan(s)
        parked_err = abs(c.gravRead - c.massKt)
        # A deep sweep is rate-limited; expire the cooldown for a second look.
        s.clock += 16
        c.heading = 270
        c.speed = 40  # crossing fast
        grav_scan(s)
        moving_err = abs(c.gravRead - c.massKt)
        assert moving_err < parked_err

    def test_a_deep_grav_sweep_is_rate_limited(self):
        s = start(make_state())
        set_mode(s, "cruise")
        c = s.contacts[0]
        c.everDetected = True
        grav_scan(s)
        first = c.gravRead
        # A second sweep in the same simulated minute is refused, so the read
        # does not change.
        c.heading = 270
        c.speed = 40
        grav_scan(s)
        assert c.gravRead == first


class TestEngagementAndHandoff:
    def test_confirmed_hostile_inside_range_triggers_engagement_on_advance(self):
        s = start(make_state())
        escort = next(c for c in s.contacts if c.trueType == "escort")
        escort.everDetected = True
        bump_confidence(s, escort, 1.0)
        s.ship.roe = "hold"
        advance(s, 60)
        assert any(e.kind == "engagement" for e in s.events)

    def test_force_handoff_builds_a_pack_and_pauses_the_patrol(self):
        s = make_state()
        escort = next(c for c in s.contacts if c.trueType == "escort")
        escort.everDetected = True
        force_handoff(s, "Captain")
        assert s.status == "handoff"
        assert s.handoffPack is not None
        assert s.handoffPack.contact.name == escort.name
        assert s.handoffPack.own.readiness == s.ship.readiness

    def test_resuming_after_a_handoff_lets_time_move_again(self):
        s = make_state()
        escort = next(c for c in s.contacts if c.trueType == "escort")
        escort.everDetected = True
        force_handoff(s, "Captain")
        paused = s.clock
        advance(s, 30)  # no-op while paused
        assert s.clock == paused


class TestEvents:
    def test_resolving_an_event_removes_it_and_applies_the_effect(self):
        s = make_state()
        s.status = "running"
        before = s.ship.exposure
        s.events.append(
            DecisionEvent(
                id="e1",
                title="Test",
                kind="intel",
                deadline=s.clock + 90,
                text="probe",
                source="test",
                options=[DecisionOption(id="a", label="A", effect=EventEffect(exposure=5))],
            )
        )
        resolve_event(s, "e1", "a")
        assert len(s.events) == 0
        assert s.ship.exposure > before


class TestLogbookDigest:
    def test_end_campaign_seals_a_digest_with_stats_from_the_run(self):
        s = start(make_state())
        advance(s, 480)
        escort = next(c for c in s.contacts if c.trueType == "escort")
        escort.everDetected = True
        bump_confidence(s, escort, 1.0)
        force_handoff(s, "Captain")
        s.status = "running"
        # inject a crew roleplay note
        s.log.append(
            LogEntry(id=999, time=s.clock, type="rp", source="Alice", text="quiet sector, good watch.")
        )

        d = build_digest(s)
        assert d.contactsSeen >= 1
        assert d.hostileConfirmed == 1
        assert d.handoffs == 1
        assert d.rpNotes >= 1
        assert d.durationMinutes > 0
        assert "after-action log" in digest_text(d)


class TestGMOppositionBuilder:
    def test_spawns_patches_and_removes_opposition_contacts(self):
        s = start(make_state())
        before = len(s.contacts)

        spawned = spawn_opposition(
            s,
            ContactTemplate(
                x=12,
                y=-8,
                heading=90,
                speed=10,
                type="escort",
                faction="enemy",
                hostile=True,
                emitting=True,
                name="JACKAL-1",
            ),
        )
        assert spawned is not None
        assert len(s.contacts) == before + 1
        # The GM's name is the contact's true identity; the plot keeps showing
        # the anonymous track until the crew confirms it.
        assert spawned.trueName == "JACKAL-1"
        assert spawned.name.startswith("TRACK-")
        assert spawned.id.startswith("gm-")

        assert patch_opposition(
            s,
            spawned.id,
            ContactPatch(pos=Vec(x=40, y=40, z=spawned.pos.z), speed=16, guess="escort", hostile=False),
        ) is True
        patched = next(c for c in s.contacts if c.id == spawned.id)
        assert patched.pos.x == 40
        assert patched.speed == 16
        assert patched.hostile is False

        assert remove_opposition(s, spawned.id) is True
        assert len(s.contacts) == before
        assert remove_opposition(s, "nope") is False

    def test_injects_a_gm_decision_event_the_command_can_resolve(self):
        s = start(make_state())
        before = len(s.events)
        before_exposure = s.ship.exposure
        gm_event(
            s,
            DecisionEvent(
                id="gm-1",
                title="FleetNet contact",
                kind="intel",
                deadline=s.clock + 90,
                text="Strong slow contact on the outer screen.",
                source="GM",
                options=[
                    DecisionOption(
                        id="a",
                        label="Hold position",
                        effect=EventEffect(exposure=2, log="Stopped cold."),
                    )
                ],
            ),
        )
        assert len(s.events) == before + 1
        resolve_event(s, "gm-1", "a")
        assert len(s.events) == before
        assert s.ship.exposure == pytest.approx(before_exposure + 2)


def make_field_state() -> GameState:
    """A watch with one of each environmental return plus a freighter."""
    campaign = CampaignSeed(
        id="field",
        title="Field Box",
        theater="Test Reach",
        brief="brief",
        target="target",
        startHour=0,
        patrol=Patrol(center=Vec(x=0, y=0, z=0), radiusKlik=90),
        clutter=0.3,
        escalation=30,
        contacts=[
            ContactTemplate(x=10, y=0, heading=0, speed=0, type="asteroid", faction="neutral", hostile=False, emitting=False),
            ContactTemplate(x=-12, y=0, heading=0, speed=0, type="nebula", faction="neutral", hostile=False, emitting=False),
            ContactTemplate(x=0, y=14, heading=0, speed=0, type="debris", faction="neutral", hostile=False, emitting=False),
            ContactTemplate(x=16, y=0, heading=270, speed=4, type="freighter", faction="neutral", hostile=False, emitting=False),
        ],
        events=[],
    )
    s = create_state("chan-field", "inst-field", campaign)
    s.status = "running"
    for c in s.contacts:
        c.everDetected = True
        c.detected = True
    return s


class TestEnvironmentalContacts:
    def test_environmental_contacts_get_terrain_names_and_masses(self):
        s = make_field_state()
        asteroid = next(c for c in s.contacts if c.trueType == "asteroid")
        nebula = next(c for c in s.contacts if c.trueType == "nebula")
        debris = next(c for c in s.contacts if c.trueType == "debris")
        assert asteroid.trueName in ASTEROID_FIELD_NAMES
        assert nebula.trueName in NEBULA_NAMES
        assert debris.trueName in DEBRIS_NAMES
        # Terrain is subject to the same anonymity rule as traffic.
        assert all(c.name.startswith("TRACK-") for c in (asteroid, nebula, debris))
        assert asteroid.massKt == MASS_KT["asteroid"]
        assert asteroid.gravSaturated is False

    def test_grav_scan_saturates_field_contacts_but_not_traffic(self):
        s = make_field_state()
        set_mode(s, "cruise")
        grav_scan(s)
        asteroid = next(c for c in s.contacts if c.trueType == "asteroid")
        freighter = next(c for c in s.contacts if c.trueType == "freighter")
        assert asteroid.gravSaturated is True
        assert asteroid.gravRead is not None
        assert freighter.gravSaturated is False

    def test_build_spectrum_is_deterministic_and_type_distinct(self):
        s = make_field_state()
        asteroid = next(c for c in s.contacts if c.trueType == "asteroid")
        nebula = next(c for c in s.contacts if c.trueType == "nebula")
        asteroid.waveform.progress = 1.0
        nebula.waveform.progress = 1.0
        first = build_spectrum(asteroid)
        again = build_spectrum(asteroid)
        other = build_spectrum(nebula)
        assert first == again
        assert len(first.emission) == SPECTRUM_BINS
        assert len(first.reflection) == SPECTRUM_BINS
        # An asteroid is a reflection body; a nebula is an emission body.
        assert sum(first.reflection) > sum(first.emission)
        assert sum(other.emission) > sum(other.reflection)
        # The summary is deliberately generic: the crew compares the plot with
        # the catalogue, it does not announce the type for them.
        assert first.summary != SPECTRAL_SUMMARY["asteroid"]
        assert "catalogue" in first.summary.lower()

    def test_listen_progressively_paints_the_spectrum(self):
        s = make_field_state()
        debris = next(c for c in s.contacts if c.trueType == "debris")
        assert debris.spectrum is None
        listen_waveform(s, debris.id)
        assert debris.spectrum is not None
        first = list(debris.spectrum.emission)
        listen_waveform(s, debris.id)
        assert list(debris.spectrum.emission) != first
        for _ in range(5):
            listen_waveform(s, debris.id)
        assert debris.waveform.resolved is True
        # Resolving the spectrum is still not an identification.
        assert debris.guess != "debris"


class TestSensorFit:
    """Passive, gravidar and EM run together; only active radar switches."""

    def test_passive_and_em_run_with_active_stowed(self):
        s = make_state()
        assert s.ship.activeSensor is False
        assert s.ship.emcon.radar is False

    def test_keying_active_raises_the_radar(self):
        s = make_state()
        set_active_sensor(s, True)
        assert s.ship.activeSensor is True
        assert s.ship.emcon.radar is True

    def test_stowing_active_darkens_the_radar(self):
        s = make_state()
        set_active_sensor(s, True)
        set_active_sensor(s, False)
        assert s.ship.activeSensor is False
        assert s.ship.emcon.radar is False

    def test_active_message_parses(self):
        from bridge.shared.protocol import MsgSensorActive, parse_c2s

        msg = parse_c2s({"type": "sensor:active", "on": True})
        assert isinstance(msg, MsgSensorActive)
        assert msg.on is True

    def test_gravidar_runs_while_making_way_and_is_silent_when_stopped(self):
        s = start(make_state())
        c = s.contacts[0]
        c.everDetected = True
        set_mode(s, "cruise")
        grav_scan(s)
        assert c.sensor.gravArc is not None
        set_speed(s, 0)
        c.sensor.gravArc = None
        grav_scan(s)
        assert c.sensor.gravArc is None

    def test_towed_array_adds_gravidar_drag_only_while_moving(self):
        import bridge.server.engine as engine

        moving = start(make_state())
        moving.ship.mode = "quiet"
        moving.ship.speed = 15
        engine._drift(moving, 1.0)

        stopped = start(make_state())
        stopped.ship.mode = "quiet"
        stopped.ship.speed = 0
        engine._drift(stopped, 1.0)
        assert moving.ship.exposure > stopped.ship.exposure


class TestEMSensors:
    def test_em_reads_course_and_speed_of_a_detected_contact(self):
        import bridge.server.engine as engine

        s = make_ship_state([_ship_contact("freighter", "friendly-freighter", x=14)])
        s.campaign.sun = None
        engine._em_detect(s)
        c = s.contacts[0]
        assert c.sensor.emQuality > 0.5
        assert c.sensor.emCourse is not None
        assert c.sensor.emSpeed is not None

    def test_sun_glare_scrambles_em_along_the_line_of_sight(self):
        import bridge.server.engine as engine
        from bridge.shared import Vec

        s = make_ship_state([_ship_contact("freighter", "friendly-freighter", x=14, y=0)])
        s.campaign.sun = None
        engine._em_detect(s)
        clear = s.contacts[0].sensor.emQuality
        # Sun directly behind the target bearing: full glare.
        s.campaign.sun = Vec(x=200, y=0, z=0)
        engine._em_detect(s)
        assert s.contacts[0].sensor.emQuality < clear

    def test_dust_field_can_scramble_em_to_nothing(self):
        import bridge.server.engine as engine

        s = make_ship_state(
            [
                _ship_contact("freighter", "friendly-freighter", x=20),
                ContactTemplate(x=10, y=0, heading=0, speed=0, type="dust", faction="neutral", hostile=False, emitting=False),
            ]
        )
        s.campaign.sun = None
        engine._em_detect(s)
        assert s.contacts[0].sensor.emQuality < 0.2

    def test_terrain_gets_no_em_vector(self):
        import bridge.server.engine as engine

        s = make_ship_state(
            [ContactTemplate(x=9, y=0, heading=0, speed=0, type="ice", faction="neutral", hostile=False, emitting=False)]
        )
        engine._em_detect(s)
        assert s.contacts[0].sensor.emCourse is None


def make_ship_state(contacts: list[ContactTemplate], *, ship_id: str | None = None) -> GameState:
    """A running watch with the given contacts and hull, all already detected."""
    campaign = CampaignSeed(
        id="ships",
        title="Ship Box",
        theater="Test Reach",
        brief="brief",
        target="target",
        startHour=0,
        patrol=Patrol(center=Vec(x=0, y=0, z=0), radiusKlik=120),
        clutter=0.0,
        escalation=20,
        contacts=contacts,
        events=[],
    )
    s = create_state("chan-ship", "inst-ship", campaign, ship_id=ship_id)
    s.status = "running"
    for c in s.contacts:
        c.everDetected = True
        c.detected = True
    return s


def _ship_contact(ctype: ContactType, ship_id: str, x: float = 20, y: float = 0, speed: float = 6) -> ContactTemplate:
    return ContactTemplate(
        x=x,
        y=y,
        heading=0,
        speed=speed,
        type=ctype,
        faction="neutral",
        hostile=False,
        emitting=False,
        shipClass=ship_id,
    )


class TestShipCatalog:
    def test_every_hull_exposes_a_full_sensor_profile(self):
        assert SHIP_CLASSES
        for hull in SHIP_CLASSES.values():
            assert 0 <= hull.profile <= 1
            assert 0 <= hull.stealth <= 1
            assert 0 <= hull.emission <= 1
            assert hull.massKt > 0
            assert hull.maxSpeed >= hull.cruiseSpeed > 0
            assert hull.crew >= 1
            assert hull.name and hull.role and hull.blurb

    def test_contacts_inherit_the_hull_properties(self):
        s = make_ship_state([_ship_contact("freighter", "friendly-freighter")])
        c = s.contacts[0]
        hull = SHIP_CLASSES["friendly-freighter"]
        assert c.shipClass == "friendly-freighter"
        assert c.massKt == hull.massKt
        assert c.profile == hull.profile
        assert c.emission == hull.emission
        assert c.stealth == hull.stealth

    def test_terrain_gets_a_radius_and_no_ship_class(self):
        s = make_ship_state([ContactTemplate(x=9, y=0, heading=0, speed=0, type="ice", faction="neutral", hostile=False, emitting=False)])
        c = s.contacts[0]
        assert c.shipClass == ""
        assert c.radiusKlik == OBSTACLE_RADIUS["ice"]
        assert c.profile == 0.0

    def test_set_ship_class_updates_the_crew_hull(self):
        s = make_ship_state([], ship_id="home")
        assert s.ship.shipClass == "home"
        assert s.ship.name == "CS Audacity"
        set_ship_class(s, "enemy-cruiser")
        hull = SHIP_CLASSES["enemy-cruiser"]
        assert s.ship.shipClass == "enemy-cruiser"
        assert s.ship.name == "Enemy_Cruiser-01"
        assert s.ship.massKt == hull.massKt
        assert s.ship.profile == hull.profile
        assert s.ship.maxSpeed == hull.maxSpeed

    def test_unknown_hull_falls_back_to_the_default(self):
        s = make_ship_state([], ship_id="not-a-hull")
        assert s.ship.shipClass == DEFAULT_SHIP_CLASS


class TestModeReturns:
    def test_gravidar_gives_a_mass_arc_and_an_ok_distance(self):
        s = make_ship_state([_ship_contact("freighter", "friendly-freighter", x=20)])
        set_mode(s, "cruise")
        grav_scan(s)
        c = s.contacts[0]
        assert c.sensor.gravArc is not None
        assert c.sensor.gravArc.massKt > 0
        assert 1.5 <= c.sensor.gravArc.halfWidth <= 80
        # Bearing is the precise axis; distance is only "OK".
        assert c.sensor.gravRange is not None
        assert c.sensor.gravRangeError > 0
        # No *active* fix: gravidar is not radar.
        assert c.sensor.activeRange is None
        assert c.gravSaturated is False

    def test_a_heavier_hull_paints_a_tighter_arc(self):
        s = make_ship_state(
            [
                _ship_contact("fighter", "enemy-fighter", x=20),
                _ship_contact("capship", "enemy-cruiser", x=20, y=4),
            ]
        )
        set_mode(s, "cruise")
        grav_scan(s)
        light, heavy = s.contacts[0].sensor.gravArc, s.contacts[1].sensor.gravArc
        assert light is not None and heavy is not None
        assert heavy.halfWidth < light.halfWidth

    def test_active_radar_returns_a_range_for_a_large_hull(self):
        s = make_ship_state([_ship_contact("freighter", "friendly-freighter", x=20)])
        active_sweep(s)
        c = s.contacts[0]
        assert c.sensor.activeRange is not None
        assert 15 <= c.sensor.activeRange <= 25
        assert c.estimated is not None

    def test_a_low_profile_fighter_hides_from_active_radar(self):
        s = make_ship_state([_ship_contact("fighter", "enemy-fighter", x=30)])
        active_sweep(s)
        assert s.contacts[0].sensor.activeRange is None

    def test_passive_resolves_a_loud_hull_over_a_stealthy_one(self):
        s = make_ship_state(
            [
                _ship_contact("freighter", "friendly-freighter", x=9),
                _ship_contact("fighter", "enemy-fighter", x=9, y=3),
            ]
        )
        s.noise = 1.5
        advance(s, 240)
        loud, stealthy = s.contacts[0].sensor.passiveEmission, s.contacts[1].sensor.passiveEmission
        assert loud > stealthy
        assert s.contacts[0].sensor.passiveType == "freighter"

    def test_passive_leaves_no_range_estimate(self):
        s = make_ship_state([_ship_contact("freighter", "friendly-freighter", x=9)])
        s.noise = 1.5
        advance(s, 240)
        passive_samples = [b for b in s.contacts[0].bearingHistory if b.source == "passive"]
        assert passive_samples
        assert all(b.range is None for b in passive_samples)
        assert s.contacts[0].estimated is None


class TestSensorObstacles:
    def _ice_between(self) -> GameState:
        return make_ship_state(
            [
                _ship_contact("freighter", "friendly-freighter", x=20),
                ContactTemplate(x=10, y=0, heading=0, speed=0, type="ice", faction="neutral", hostile=False, emitting=False),
            ]
        )

    def test_ice_on_the_line_of_sight_blocks_scatters_and_reflects(self):
        s = self._ice_between()
        target = s.contacts[0]
        block, scatter, reflect = obstacle_shadow(s, target)
        eff = OBSTACLE_EFFECTS["ice"]
        assert block == pytest.approx(eff.block, abs=1e-6)
        assert scatter == pytest.approx(eff.scatter, abs=1e-6)
        assert reflect == pytest.approx(eff.reflect, abs=1e-6)

    def test_no_shadow_when_terrain_is_off_axis(self):
        s = make_ship_state(
            [
                _ship_contact("freighter", "friendly-freighter", x=20),
                ContactTemplate(x=10, y=60, heading=0, speed=0, type="ice", faction="neutral", hostile=False, emitting=False),
            ]
        )
        assert obstacle_shadow(s, s.contacts[0]) == (0.0, 0.0, 0.0)

    def test_passive_snr_is_attenuated_by_an_intervening_obstacle(self):
        clear = make_ship_state([_ship_contact("freighter", "friendly-freighter", x=20)])
        blocked = self._ice_between()
        clear.noise = blocked.noise = 8.0  # keep both below the SNR cap
        engine = __import__("bridge.server.engine", fromlist=["_passive_snr"])
        assert engine._passive_snr(blocked, blocked.contacts[0]) < engine._passive_snr(clear, clear.contacts[0])
        assert blocked.contacts[0].sensor.obstructed > 0

    def test_ice_throws_a_mirror_ghost_return(self):
        s = self._ice_between()
        # Pick a clock where the mirror roll succeeds (reflect 0.95).
        s.clock = next(t for t in range(0, 80) if hash_random(t, 23) < 0.95)
        active_sweep(s)
        target = s.contacts[0]
        ghost = [b for b in target.bearingHistory if b.source == "active" and b.range is None]
        assert ghost, "ice should refract an un-ranged mirror return"

    def test_debris_scatters_more_than_asteroid_blocks(self):
        assert OBSTACLE_EFFECTS["debris"].scatter > OBSTACLE_EFFECTS["asteroid"].scatter
        assert OBSTACLE_EFFECTS["asteroid"].block > OBSTACLE_EFFECTS["debris"].block


class TestWaypointNavigation:
    """A 45-minute cruise covers ~11 klik, so waypoints must be consumed along
    the fixed simulation slices rather than only at the end of the call."""

    def _nav_state(self, waypoints, heading=90):
        s = start(make_state())
        s.ship.mode = "cruise"
        s.ship.waypoints = waypoints
        s.ship.heading = heading
        return s

    def test_reaching_a_waypoint_selects_the_next_one(self):
        s = self._nav_state([Vec(x=10, y=0, z=0), Vec(x=20, y=0, z=0)])
        advance(s, 45)
        assert s.ship.waypoints == [Vec(x=20.0, y=0.0, z=0.0)]
        assert s.ship.speed > 0
        assert s.ship.pos.x == pytest.approx(11.1, abs=0.3)

    def test_a_waypoint_closer_than_one_tick_is_not_overshot(self):
        s = self._nav_state([Vec(x=5, y=0, z=0)])
        advance(s, 45)
        assert s.ship.waypoints == []
        # Arrival holds station on the waypoint instead of flying past it.
        assert s.ship.pos.x == pytest.approx(5.0, abs=0.2)
        assert s.ship.speed == 0

    def test_a_single_tick_clears_several_close_waypoints(self):
        s = self._nav_state([Vec(x=3, y=0, z=0), Vec(x=6, y=0, z=0), Vec(x=9, y=0, z=0)])
        advance(s, 45)
        assert s.ship.waypoints == []
        assert s.ship.pos.x == pytest.approx(9.0, abs=0.2)

    def test_heading_turns_toward_the_next_waypoint_after_arrival(self):
        s = self._nav_state([Vec(x=8, y=0, z=0), Vec(x=8, y=20, z=0)])
        advance(s, 45)
        assert s.ship.pos.x == pytest.approx(8.0, abs=0.2)
        assert abs(bearing_diff(s.ship.heading, 0)) < 1.0

    def test_holding_with_no_waypoints_keeps_station(self):
        s = self._nav_state([])
        before = (s.ship.pos.x, s.ship.pos.y)
        advance(s, 45)
        assert (s.ship.pos.x, s.ship.pos.y) == before
        assert s.ship.speed == 0
        # Stopped, so no drive plume, but the plant still radiates.
        assert s.ship.rearHeat == 0
        assert s.ship.selfNoise > 0


class TestSpeedScale:
    def test_mode_speeds_are_the_named_anchors(self):
        from bridge.server.engine import _mode_speed

        assert _mode_speed("quiet") == SILENT_KPS == 15
        assert _mode_speed("cruise") == CRUISE_KPS == 60
        assert _mode_speed("max") == FLANK_KPS == 100

    def test_set_speed_clamps_to_the_100_kps_dial(self):
        s = start(make_state())
        set_speed(s, 250)
        assert s.ship.speed == s.ship.maxSpeed == 100
        assert s.ship.mode == "max"
        set_speed(s, 12)
        assert s.ship.mode == "quiet"
        set_speed(s, 60)
        assert s.ship.mode == "cruise"

    def test_catalog_speeds_are_on_the_new_dial(self):
        for hull in SHIP_CLASSES.values():
            assert hull.cruiseSpeed == CRUISE_KPS
            assert hull.maxSpeed == FLANK_KPS

    def test_campaign_contact_speeds_are_in_range(self):
        for cid in ("iron-collar", "whale-road", "sector-9-anomaly"):
            for t in campaign_for(cid).contacts:
                assert 0 <= t.speed <= 100


class TestFrequencyProfile:
    def test_every_hull_has_a_unique_barcode(self):
        seen = set()
        for hull in SHIP_CLASSES.values():
            assert len(hull.bands) == FREQ_BANDS
            assert all(0 <= b <= 1 for b in hull.bands)
            seen.add(tuple(hull.bands))
        assert len(seen) == len(SHIP_CLASSES)

    def test_contacts_carry_their_hull_profile(self):
        s = make_ship_state([_ship_contact("fighter", "enemy-heavy-fighter")])
        assert s.contacts[0].frequencyProfile == SHIP_CLASSES["enemy-heavy-fighter"].bands

    def test_terrain_has_a_profile_too(self):
        s = make_ship_state(
            [ContactTemplate(x=9, y=0, heading=0, speed=0, type="ice", faction="neutral", hostile=False, emitting=False)]
        )
        assert len(s.contacts[0].frequencyProfile) == FREQ_BANDS

    def test_passive_paints_the_barcode_over_time(self):
        s = make_ship_state([_ship_contact("freighter", "friendly-freighter", x=8)])
        s.noise = 1.0
        advance(s, 180)
        bands = s.contacts[0].sensor.bands
        assert len(bands) == FREQ_BANDS
        assert any(b > 0.05 for b in bands)


class TestTimeFreeze:
    def test_frozen_time_blocks_advance(self):
        s = start(make_state())
        set_time_frozen(s, True)
        before = s.clock
        advance(s, 240)
        assert s.clock == before

    def test_releasing_the_clock_resumes_advance(self):
        s = start(make_state())
        set_time_frozen(s, True)
        advance(s, 240)
        frozen_clock = s.clock
        set_time_frozen(s, False)
        advance(s, 45)
        assert s.clock > frozen_clock

    def test_freeze_message_parses(self):
        from bridge.shared.protocol import MsgAdminFreeze, parse_admin_c2s

        msg = parse_admin_c2s({"type": "admin.freeze", "channelId": "c", "frozen": True})
        assert isinstance(msg, MsgAdminFreeze)
        assert msg.frozen is True


class TestSector9AnomalyScenario:
    def test_scenario_is_registered_and_flies_the_home_cruiser(self):
        c = campaign_for("sector-9-anomaly")
        assert c.title == "Sector 9 Anomaly"
        assert c.shipClass == "home"
        s = create_state("c", "i", c)
        assert s.ship.shipClass == "home"
        assert s.ship.name == "CS Audacity"

    def test_hunter_killer_group_and_terrain(self):
        c = campaign_for("sector-9-anomaly")
        classes = [t.shipClass for t in c.contacts]
        assert classes.count("enemy-heavy-fighter") == 3
        assert classes.count("enemy-destroyer") == 2
        types = {t.type for t in c.contacts}
        assert {"debris", "dust", "ice"} <= types

    def test_callsign_variants_stay_distinct_within_a_scenario(self):
        from bridge.shared import FIGHTER_CLASSES

        contacts = [
            ContactTemplate(
                x=i * 5,
                y=0,
                heading=0,
                speed=0,
                type="fighter",
                faction="enemy",
                hostile=True,
                emitting=True,
                shipClass="enemy-fighter",
            )
            for i in range(len(FIGHTER_CLASSES))
        ]
        campaign = CampaignSeed(
            id="pool",
            title="Pool",
            theater="Test Reach",
            brief="brief",
            target="target",
            startHour=0,
            patrol=Patrol(center=Vec(x=0, y=0, z=0), radiusKlik=60),
            clutter=0.0,
            escalation=10,
            contacts=contacts,
            events=[],
        )
        s = create_state("chan-pool", "inst-pool", campaign)
        names = [c.trueName for c in s.contacts]
        assert len(set(names)) == len(names) == len(FIGHTER_CLASSES)
        assert set(names) == set(FIGHTER_CLASSES)


class TestEmissionProfile:
    """Silent running: quieter overall than sitting still, but a hotter stern
    plume — and that plume dazzles your own aft sensors."""

    def test_quiet_is_quieter_overall_than_sitting_still(self):
        s = make_ship_state([])
        set_speed(s, 0)
        idle = s.ship.selfNoise
        assert idle > 0  # a stopped ship still radiates
        set_mode(s, "quiet")
        assert s.ship.selfNoise < idle

    def test_quiet_lights_a_stern_plume(self):
        s = make_ship_state([])
        set_speed(s, 0)
        assert s.ship.rearHeat == 0.0
        set_mode(s, "quiet")
        assert s.ship.rearHeat > 0

    def test_overall_emission_and_stern_heat_rise_with_speed(self):
        s = make_ship_state([])
        set_mode(s, "quiet")
        quiet_o, quiet_r = s.ship.selfNoise, s.ship.rearHeat
        set_mode(s, "cruise")
        cruise_o, cruise_r = s.ship.selfNoise, s.ship.rearHeat
        set_mode(s, "max")
        flank_o, flank_r = s.ship.selfNoise, s.ship.rearHeat
        assert quiet_o < cruise_o < flank_o
        assert quiet_r < cruise_r < flank_r

    def test_stopped_ship_has_no_stern_plume(self):
        s = make_ship_state([])
        set_mode(s, "max")
        set_speed(s, 0)
        assert s.ship.rearHeat == 0.0
        assert s.ship.selfNoise > 0

    def test_own_plume_dazzles_a_contact_dead_astern(self):
        import bridge.server.engine as engine

        s = make_ship_state(
            [
                _ship_contact("freighter", "friendly-freighter", x=20, y=0),
                _ship_contact("freighter", "friendly-freighter", x=-20, y=0),
            ]
        )
        set_mode(s, "cruise")
        s.ship.heading = 90  # east: contact 0 is dead ahead, contact 1 dead astern
        ahead, astern = s.contacts[0], s.contacts[1]
        assert engine.stern_dazzle(s, astern) > 0.4  # cruise plume wash
        assert engine.stern_dazzle(s, ahead) == 0.0
        assert engine._passive_snr(s, astern) < engine._passive_snr(s, ahead)

    def test_stern_dazzle_is_zero_when_stopped(self):
        import bridge.server.engine as engine

        s = make_ship_state([_ship_contact("freighter", "friendly-freighter", x=-20, y=0)])
        s.ship.heading = 90
        set_speed(s, 0)
        assert engine.stern_dazzle(s, s.contacts[0]) == 0.0


class TestReleaseHardening:
    def test_radar_stows_and_sweeps_refuse_below_the_battery_reserve(self):
        s = start(make_state())
        s.ship.battery = 0
        s.ship.activeSensor = True
        s.ship.emcon.radar = True
        advance(s, 15)
        assert s.ship.activeSensor is False
        assert s.ship.emcon.radar is False

        sweep = make_state()
        sweep.ship.battery = 0
        before = sweep.ship.battery
        active_sweep(sweep)
        assert sweep.ship.battery == before
        assert any("battery reserve" in entry.text for entry in sweep.log)

    def test_jump_spooling_stows_radar_and_commit_requires_fuel(self):
        s = create_state("jump", "inst", campaign_for("iron-collar"))
        nav = next(point for point in s.campaign.navPoints if point.kind == "jump")
        s.ship.pos = nav.pos.model_copy()
        s.ship.activeSensor = True
        s.ship.emcon.radar = True
        s.ship.speed = 100

        spool_jump(s, nav.id)

        assert s.ship.activeSensor is False
        assert s.ship.emcon.radar is False
        assert s.ship.speed <= JUMP_SPOOL_MAX_SPEED

        s.jumpState.alignment = 1.0
        s.ship.fuel = 0
        before = s.ship.pos.model_copy()
        commit_jump(s)
        assert s.ship.pos == before
        assert s.jumpState.outcome == "refused"

    def test_default_inbound_ordnance_starts_at_detection_range(self):
        s = make_state()
        shot = launch_ordnance(s)
        assert dist(s.ship.pos, shot.pos) == pytest.approx(ORDNANCE_DETECT_KLIK)
        first_id = shot.id
        s.ordnance.clear()
        second = launch_ordnance(s)
        assert second.id != first_id

    def test_generated_gm_contact_ids_do_not_collide(self):
        s = make_state()
        template = ContactTemplate(
            x=20,
            y=0,
            heading=0,
            speed=20,
            type="fighter",
            faction="enemy",
            hostile=True,
            emitting=True,
        )
        first = spawn_opposition(s, template)
        second = spawn_opposition(s, template)
        assert first is not None and second is not None
        assert first.id != second.id

    def test_handoff_does_not_attach_another_targets_solution(self):
        s = make_state()
        first, second = [contact for contact in s.contacts if contact.hostile]
        first.everDetected = True
        second.everDetected = True
        s.ship.weaponTarget = first.id
        s.ship.weaponsState = "armed"
        s.ship.weapon = "laser-cannon"
        s.ship.solutionQuality = 0.8

        force_handoff(s, "Captain", second.id)

        assert s.handoffPack.contact.id == second.id
        assert s.handoffPack.weapons.prepped is False
        assert s.handoffPack.weapons.weapon == ""
        assert s.handoffPack.weapons.ehd is None
        assert s.ship.weaponsState == "safe"
        assert s.ship.weaponTarget == ""

    def test_replenishment_requires_a_depot(self):
        depot_state = create_state("depot", "inst", campaign_for("whale-road"))
        depot = next(point for point in depot_state.campaign.navPoints if point.kind == "body")
        depot_state.ship.pos = depot.pos.model_copy()
        depot_state.ship.fuel = 0
        replenish(depot_state)
        assert depot_state.ship.fuel == depot_state.ship.fuelCapacity

        nav_state = create_state("nav", "inst", campaign_for("iron-collar"))
        nav = next(point for point in nav_state.campaign.navPoints if point.kind == "nav")
        nav_state.ship.pos = nav.pos.model_copy()
        nav_state.ship.fuel = 0
        replenish(nav_state)
        assert nav_state.ship.fuel == 0

    def test_changing_a_contact_hull_refreshes_its_signature_and_art(self):
        s = make_state()
        contact = s.contacts[0]
        expected = SHIP_CLASSES["enemy-escort"]

        assert patch_opposition(s, contact.id, ContactPatch(shipClass=expected.id))

        assert contact.shipClass == expected.id
        assert contact.frequencyProfile == expected.bands
        assert contact.image == expected.image
        assert contact.vdu == expected.vdu
        assert contact.sensorQuality == expected.sensorQuality

    def test_raising_shields_does_not_catch_up_from_minute_zero(self):
        s = start(make_state())
        s.clock = 120
        set_alert(s, "two")
        s.ship.shields["fore"].shp = 0
        advance(s, 5)
        assert s.ship.shields["fore"].shp == 0


class TestShipArt:
    def test_contacts_carry_their_hull_art(self):
        s = make_ship_state([_ship_contact("capship", "enemy-escort")])
        c = s.contacts[0]
        assert c.image == "/img/action/enemy-escort.png"
        assert c.image == SHIP_CLASSES["enemy-escort"].image
        assert c.vdu.endswith("enemy-escort-vdu.gif")

    def test_the_home_crew_hull_has_art(self):
        s = make_ship_state([], ship_id="home")
        assert s.ship.shipClass == "home"
        assert SHIP_CLASSES["home"].image.endswith("friendly-cruiser.png")

    def test_terrain_contacts_carry_terrain_art(self):
        s = make_ship_state(
            [ContactTemplate(x=9, y=0, heading=0, speed=0, type="asteroid", faction="neutral", hostile=False, emitting=False)]
        )
        assert s.contacts[0].image == "/img/action/asteroid.png"

    def test_a_transport_has_action_and_vdu_art(self):
        s = make_ship_state([_ship_contact("freighter", "friendly-transport")])
        c = s.contacts[0]
        assert c.image.endswith("friendly-transport.png")
        assert c.vdu.endswith("friendly-transport-vdu.gif")
