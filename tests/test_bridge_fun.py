"""Coverage for the detection race, contact anonymity, buoys and crybabies.

These exercise the layer added on top of the ported engine: names stay hidden
until a track is CONFIRMED, an enemy track on the crew ship can end the patrol,
deployed buoys give a second passive origin, noisemakers flood the EM band, and
decision events finally have teeth.
"""

from __future__ import annotations

import pytest

from bridge.shared import *
from bridge.shared.protocol import parse_c2s
from bridge.server.engine import *


def _state(
    contacts: list[ContactTemplate],
    *,
    escalation: float = 30,
    clutter: float = 0.0,
    ship_id: str | None = None,
) -> GameState:
    campaign = CampaignSeed(
        id="fun",
        title="Fun Box",
        theater="Test Reach",
        brief="brief",
        target="target",
        startHour=0,
        patrol=Patrol(center=Vec(x=0, y=0, z=0), radiusKlik=120),
        clutter=clutter,
        escalation=escalation,
        contacts=contacts,
        events=[],
        shipClass=ship_id,
    )
    s = create_state("chan-fun", "inst-fun", campaign, ship_id=ship_id)
    s.status = "running"
    return s


def _hostile(x: float = 20, y: float = 0, *, speed: float = 0) -> ContactTemplate:
    return ContactTemplate(
        x=x,
        y=y,
        heading=0,
        speed=speed,
        type="escort",
        faction="enemy",
        hostile=True,
        emitting=True,
        shipClass="kamekh-escort",
    )


def _freighter(x: float = 20, y: float = 0) -> ContactTemplate:
    return ContactTemplate(
        x=x,
        y=y,
        heading=0,
        speed=0,
        type="freighter",
        faction="neutral",
        hostile=False,
        emitting=False,
        shipClass="longhaul-freighter",
    )


class TestContactAnonymity:
    def test_contacts_are_anonymous_until_confirmed(self):
        s = _state([_hostile()])
        c = s.contacts[0]
        assert c.trueName  # the real name is tracked internally...
        assert c.name == "TRACK-01"  # ...but the plot does not show it
        assert c.name != c.trueName

    def test_confirmation_releases_the_true_name(self):
        s = _state([_hostile()])
        c = s.contacts[0]
        c.everDetected = True
        bump_confidence(s, c, 1.0)
        assert c.state == "confirmed"
        assert c.name == c.trueName


class TestDetectionRace:
    def test_going_loud_brings_the_enemy_lock_faster(self):
        loud = _state([_hostile(x=15)])
        set_mode(loud, "max")
        quiet = _state([_hostile(x=15)])
        set_mode(quiet, "quiet")

        advance(loud, 45)
        advance(quiet, 45)

        assert loud.contacts[0].lock > quiet.contacts[0].lock > 0

    def test_being_painted_first_ends_the_patrol_as_a_loss(self):
        s = _state([_hostile(x=5)])
        set_speed(s, 0)  # loitering in the open, radiating
        c = s.contacts[0]
        assert c.name.startswith("TRACK-")

        advance(s, 240)

        assert c.hostileLock is True
        # Close enough to read, the hunter is finally named on the plot.
        assert c.name == c.trueName
        assert s.outcome == "lost"
        assert s.status == "ended"
        assert s.ship.hull < 100

    def test_identifying_the_enemy_first_wins_the_patrol(self):
        s = _state([_hostile(x=200, y=200)])
        c = s.contacts[0]
        c.everDetected = True
        bump_confidence(s, c, 1.0)

        advance(s, 45)

        assert s.outcome == "won"
        assert s.status == "ended"
        assert s.digest is not None and s.digest.outcome == "won"

    def test_weapons_hot_is_a_choice_to_fight_not_a_race_win(self):
        s = _state([_hostile(x=20)])
        c = s.contacts[0]
        c.everDetected = True
        bump_confidence(s, c, 1.0)
        s.ship.roe = "hold"

        advance(s, 45)

        assert s.outcome is None
        assert any(e.kind == "engagement" for e in s.events)


class TestPatrolVictory:
    """Win by tracking every hunter, or by outlasting the lane."""

    def test_tracking_every_hostile_wins_the_patrol(self):
        s = _state([_hostile(x=180, y=0), _hostile(x=190, y=20)])
        for c in s.contacts:
            c.everDetected = True
            bump_confidence(s, c, 0.3)  # at least "tracking"

        advance(s, 15)

        assert s.outcome == "won"
        assert any("detected and tracked" in e.text for e in s.log)

    def test_one_untracked_hostile_keeps_the_patrol_live(self):
        s = _state([_hostile(x=180, y=0), _hostile(x=190, y=20)])
        s.contacts[0].everDetected = True
        bump_confidence(s, s.contacts[0], 0.3)

        advance(s, 15)

        assert s.outcome is None

    def test_tracking_every_hostile_still_needs_weapons_safe(self):
        s = _state([_hostile(x=20), _hostile(x=30, y=10)])
        for c in s.contacts:
            c.everDetected = True
            bump_confidence(s, c, 0.3)
        s.ship.roe = "hold"

        advance(s, 15)

        assert s.outcome is None

    def test_a_hostile_that_closes_then_leaves_wins_by_disengagement(self):
        s = _state([_hostile(x=20)])
        c = s.contacts[0]
        c.everDetected = True

        advance(s, 15)  # the hunter closes inside the envelope...
        assert c.everNear is True

        c.pos = Vec(x=DISENGAGE_RANGE_KLIK + 60, y=0, z=0)  # ...then breaks off
        advance(s, 15)

        assert s.outcome == "won"
        assert any("lane is clear" in e.text for e in s.log)

    def test_a_hostile_that_was_never_close_is_not_disengagement(self):
        # Starting far away is not "making it through" something — nothing ever
        # threatened the patrol, so the watch stays live.
        s = _state([_hostile(x=DISENGAGE_RANGE_KLIK + 80, y=0)])
        assert s.contacts[0].everNear is False

        advance(s, 15)

        assert s.outcome is None

    def test_disengagement_wins_even_with_weapons_held(self):
        s = _state([_hostile(x=20)])
        c = s.contacts[0]
        c.everDetected = True
        c.everNear = True
        c.pos = Vec(x=DISENGAGE_RANGE_KLIK + 60, y=0, z=0)
        s.ship.roe = "hold"

        advance(s, 15)

        assert s.outcome == "won"

    def test_six_hours_dark_wins_by_endurance(self):
        s = _state([_hostile(x=200, y=200)])

        advance(s, ENDURE_MINUTES)

        assert s.outcome == "won"
        assert any("hours dark" in e.text for e in s.log)

    def test_a_working_enemy_track_voids_the_endurance_win(self):
        s = _state([_hostile(x=200, y=200)])
        s.contacts[0].everTrackedUs = True

        advance(s, ENDURE_MINUTES)

        assert s.outcome is None

    def test_endurance_also_needs_weapons_safe(self):
        s = _state([_hostile(x=200, y=200)])
        s.ship.roe = "hold"

        advance(s, ENDURE_MINUTES)

        assert s.outcome is None


def _campaign_state(campaign_id: str) -> GameState:
    s = create_state("chan-fun", "inst-fun", campaign_for(campaign_id))
    s.status = "running"
    set_speed(s, 0)
    set_mode(s, "quiet")
    set_emcon(s, EmconPatch(radar=False, radios=False, optics=False))
    return s


class TestScenarioCampaigns:
    """The three victory-condition scenarios must actually be winnable."""

    def test_new_campaigns_carry_events_and_hazards(self):
        for cid in ("silent-vigil", "empty-lane", "full-sweep"):
            camp = campaign_for(cid)
            assert camp.contacts, cid
            assert camp.events, cid
            assert camp.hazards, cid

    def test_silent_vigil_is_won_by_endurance(self):
        s = _campaign_state("silent-vigil")

        advance(s, ENDURE_MINUTES + 1)

        assert s.outcome == "won"
        assert any("hours dark" in e.text for e in s.log)

    def test_empty_lane_is_won_by_disengagement(self):
        s = _campaign_state("empty-lane")

        for _ in range(12):
            if s.outcome is not None:
                break
            advance(s, 15)

        assert s.outcome == "won"
        assert any("lane is clear" in e.text for e in s.log)

    def test_full_sweep_is_won_by_tracking_every_hostile(self):
        s = _campaign_state("full-sweep")
        hostiles = [c for c in s.contacts if c.hostile]
        t = 0
        while s.outcome is None and t < 300:
            advance(s, 10)
            t += 10
            for c in hostiles:
                if c.everDetected and not c.waveform.resolved:
                    for _ in range(8):
                        listen_waveform(s, c.id)
                        if c.waveform.resolved:
                            break
                if s.outcome is not None:
                    break

        assert s.outcome == "won"
        assert any("detected and tracked" in e.text for e in s.log)


class TestIdentificationPath:
    """Identification is evidence-based and blind: the crew calls the track, the
    sensor watch never says whether the call was right."""

    def test_resolved_spectrum_plus_a_call_is_strong_but_blind(self):
        s = _state([_hostile(x=200, y=200)])
        c = s.contacts[0]
        c.everDetected = True

        for _ in range(7):
            listen_waveform(s, c.id)
        assert c.waveform.resolved is True
        assert c.state != "confirmed"

        claim_contact(s, c.id, c.trueType)

        # A resolved barcode plus a call is strong evidence, but the identity
        # stays unreleased until that evidence accumulates.
        assert c.guess == c.trueType
        assert c.state != "confirmed"
        assert c.name != c.trueName

    def test_sustained_evidence_confirms_and_releases_the_name(self):
        s = _state([_hostile(x=200, y=200)])
        c = s.contacts[0]
        c.everDetected = True
        c.waveform.resolved = True

        for _ in range(6):
            claim_contact(s, c.id, c.trueType)

        assert c.state == "confirmed"
        assert c.name == c.trueName

    def test_a_bare_correct_call_does_not_confirm(self):
        s = _state([_hostile(x=200, y=200)])
        c = s.contacts[0]
        c.everDetected = True

        claim_contact(s, c.id, c.trueType)

        assert c.state != "confirmed"


class TestShipCatalogue:
    """A listen pass ranks ship *types* (hulls), not broad contact categories."""

    def test_catalogue_lists_hulls_with_the_true_hull_on_top(self):
        s = _state([_hostile(x=200, y=200)])
        c = s.contacts[0]
        c.everDetected = True
        # Paint the barcode the way a passive watch does.
        c.sensor.bands = list(c.frequencyProfile)

        listen_waveform(s, c.id)

        matches = c.sensor.catalogueMatches
        assert matches
        # Candidates are hull ids from the ship catalogue, each with a name...
        assert {m.shipClass for m in matches} <= set(SHIP_CLASSES)
        assert all(m.name for m in matches)
        # ...and each still carries the contact type a tag commits to.
        assert all(m.contactType for m in matches)
        # Every hull is ranked, best first; the true hull is the top call.
        assert len(matches) == len(SHIP_CLASSES)
        assert matches[0].shipClass == c.shipClass
        assert matches[0].score >= matches[-1].score

    def test_terrain_has_no_ship_candidates(self):
        s = _state(
            [
                ContactTemplate(
                    x=20, y=0, heading=0, speed=0, type="asteroid",
                    faction="neutral", hostile=False, emitting=False,
                )
            ]
        )
        c = s.contacts[0]
        c.everDetected = True
        c.sensor.bands = list(c.frequencyProfile)

        listen_waveform(s, c.id)

        assert c.sensor.catalogueMatches == []


class TestSensorBuoy:
    def test_deploy_and_recover_round_trip(self):
        s = _state([_hostile(x=200, y=200)])
        assert s.ship.buoyCount == SENSOR_BUOY_LOADOUT

        b = deploy_buoy(s)
        assert b is not None
        assert s.ship.buoyCount == SENSOR_BUOY_LOADOUT - 1
        assert len(s.buoys) == 1
        assert (b.pos.x, b.pos.y) == (s.ship.pos.x, s.ship.pos.y)

        assert recover_buoy(s, b.id) is True
        assert s.buoys == []
        assert s.ship.buoyCount == SENSOR_BUOY_LOADOUT

    def test_the_buoy_cannot_move(self):
        s = _state([_hostile(x=200, y=200)])
        b = deploy_buoy(s)
        assert b is not None
        start = (b.pos.x, b.pos.y)
        advance(s, 90)
        assert (b.pos.x, b.pos.y) == start

    def test_a_buoy_cross_fixes_a_passive_only_contact(self):
        s = _state([_freighter(x=20, y=0)])
        set_speed(s, 0)  # hold station so the ship keeps the return in reach
        b = deploy_buoy(s)
        assert b is not None
        b.pos = Vec(x=0, y=30, z=0)
        s.noise = 1.0

        # Passive acquisition is slow by design: give the array several looks
        # before the ship and the buoy can cross-fix the return.
        advance(s, 225)

        c = s.contacts[0]
        assert c.triangulated is True
        assert c.estimated is not None
        assert any(sample.range is not None for sample in c.bearingHistory)
        assert any("Cross-fix" in e.text for e in s.log)

    def test_an_empty_rack_refuses_to_deploy(self):
        s = _state([_hostile(x=200, y=200)])
        s.ship.buoyCount = 0
        assert deploy_buoy(s) is None
        assert s.buoys == []


class TestNoisemaker:
    def test_launching_a_crybaby_breaks_a_building_lock(self):
        s = _state([_hostile(x=10)])
        c = s.contacts[0]
        c.lock = 0.9

        assert deploy_noisemaker(s) is True
        assert s.noisemakerTurns == NOISEMAKER_TURNS
        assert c.lock == 0.0
        assert s.ship.noisemakers == NOISEMAKER_LOADOUT - 1

    def test_the_flood_holds_the_lock_down_for_two_turns(self):
        s = _state([_hostile(x=5)])
        set_mode(s, "max")
        deploy_noisemaker(s)

        advance(s, 45)
        c = s.contacts[0]
        assert s.noisemakerTurns == 1
        assert c.hostileLock is False
        assert c.lock < 0.2  # heavily suppressed by the hash

        advance(s, 45)
        assert s.noisemakerTurns == 0

    def test_no_crybabies_left_is_a_no_op(self):
        s = _state([_hostile(x=200, y=200)])
        s.ship.noisemakers = 0
        assert deploy_noisemaker(s) is False
        assert s.noisemakerTurns == 0


class TestEventConsequences:
    def test_unanswered_events_expire_with_a_tension_penalty(self):
        s = _state([_hostile(x=200, y=200)])
        before = s.war.tension
        s.events.append(
            DecisionEvent(
                id="e1",
                title="Test window",
                kind="intel",
                deadline=s.clock + 45,
                text="decide",
                source="test",
                options=[],
            )
        )

        advance(s, 45)

        assert all(e.id != "e1" for e in s.events)
        assert s.war.tension > before
        assert any("window closes" in e.text for e in s.log)

    def test_lose_track_effect_removes_the_track(self):
        s = _state([_hostile(x=20)])
        c = s.contacts[0]
        c.everDetected = True
        c.confidence = 0.5
        c.state = "probable"
        s.events.append(
            DecisionEvent(
                id="e1",
                title="Lose it",
                kind="intel",
                deadline=s.clock + 90,
                text="t",
                source="test",
                options=[
                    DecisionOption(
                        id="a", label="Break the track", effect=EventEffect(loseTrack=True)
                    )
                ],
            )
        )

        resolve_event(s, "e1", "a")

        assert c.everDetected is False
        assert c.state == "unknown"
        assert c.bearingHistory == []


class TestSystemsEconomy:
    def test_active_radar_drains_the_battery(self):
        s = _state([_hostile(x=200, y=200)])
        set_speed(s, 0)
        set_active_sensor(s, True)
        before = s.ship.battery

        advance(s, 180)

        assert s.ship.battery < before

    def test_low_battery_refuses_the_radar(self):
        s = _state([_hostile(x=200, y=200)])
        s.ship.battery = 1.0
        set_active_sensor(s, True)
        assert s.ship.activeSensor is False
        assert any("not enough charge" in e.text for e in s.log)

    def test_noise_filter_spends_battery(self):
        s = _state([_hostile(x=200, y=200)])
        before = s.ship.battery
        filter_noise(s)
        assert s.ship.battery < before


class TestEscalation:
    def test_rising_tension_summons_hunters(self):
        s = _state([_hostile(x=200, y=200)])
        before = len(s.contacts)

        s.war.tension = 75
        advance(s, 45)

        assert len(s.contacts) > before
        assert any("hunting" in e.text for e in s.log)


class TestSpeedDial:
    def test_the_ordered_speed_is_what_moves_the_ship(self):
        s = _state([_hostile(x=200, y=200)])
        set_speed(s, 30)
        assert s.ship.speed == 30
        start = s.ship.pos.x

        advance(s, 45)

        # 30 kps on the shared dial is 30 * 0.75h * 0.25 klik/kps-hour.
        assert s.ship.pos.x == pytest.approx(start + 5.625, abs=0.5)
        assert s.ship.mode == "cruise"

    def test_zero_speed_actually_holds_station(self):
        s = _state([_hostile(x=200, y=200)])
        set_speed(s, 0)
        before = (s.ship.pos.x, s.ship.pos.y)

        advance(s, 45)

        assert (s.ship.pos.x, s.ship.pos.y) == before
        assert s.ship.rearHeat == 0


class TestEngagementResolve:
    """The prompt's primary option must actually build the handoff pack."""

    def test_resolve_option_generates_the_handoff(self):
        s = _state([_hostile(x=10)])
        c = s.contacts[0]
        c.everDetected = True
        bump_confidence(s, c, 1.0)
        s.ship.roe = "hold"

        advance(s, 45)
        ev = next(e for e in s.events if e.kind == "engagement")

        resolve_event(s, ev.id, "resolve")

        assert s.status == "handoff"
        assert s.handoffPack is not None
        assert s.handoffPack.contact.id == c.id
        assert s.handoffPack.contact.name == c.name


class TestIntelReport:
    """Ops reporting is the payoff for doing the classification work."""

    def test_reporting_a_confirmed_contact_pushes_the_front_line(self):
        s = _state([_hostile(x=20)])
        c = s.contacts[0]
        c.everDetected = True
        c.guess = c.trueType
        bump_confidence(s, c, 1.0)
        before = s.war.frontLine

        report_contact(s, c.id)

        assert c.reported is True
        assert s.war.frontLine > before
        assert any("Fleet intel report" in e.text for e in s.log)

    def test_a_wrong_call_costs_the_front_line(self):
        s = _state([_hostile(x=20)])
        c = s.contacts[0]
        c.everDetected = True
        c.guess = "freighter"
        c.state = "classified"
        c.confidence = 0.75
        before = s.war.frontLine

        report_contact(s, c.id)

        assert s.war.frontLine < before
        assert any("flags your report" in e.text for e in s.log)

    def test_a_contact_is_only_reported_once(self):
        s = _state([_hostile(x=20)])
        c = s.contacts[0]
        c.everDetected = True
        c.guess = c.trueType
        bump_confidence(s, c, 1.0)

        report_contact(s, c.id)
        once = s.war.frontLine
        report_contact(s, c.id)

        assert s.war.frontLine == once
        assert any("already on the net's file" in e.text for e in s.log)


class TestNewProtocolMessages:
    def test_intel_report_parses(self):
        msg = parse_c2s({"type": "intel:report", "contactId": "c1"})
        assert msg.type == "intel:report"
        assert msg.contactId == "c1"

    def test_weapons_prep_carries_a_mount_and_shot_type(self):
        msg = parse_c2s(
            {
                "type": "weapons:prep",
                "contactId": "c1",
                "state": "locked",
                "weapon": "torpedo",
                "shot": "refined",
            }
        )
        assert msg.weapon == "torpedo"
        assert msg.shot == "refined"
        # The fields are optional; an old client still parses.
        old = parse_c2s({"type": "weapons:prep", "contactId": "c1"})
        assert old.weapon is None
        assert old.shot == "quick"


class TestIffInterrogation:
    def test_a_legitimate_hull_earns_transponder_confidence(self):
        s = _state([_freighter()])
        c = s.contacts[0]
        c.everDetected = True

        call_iff(s, c.id)

        assert c.iffConfidence == IFF_CONFIDENCE_LEGIT
        assert c.spoofDetected is False
        assert c.guess == c.trueType

    def test_repeat_challenges_catch_a_spoofed_transponder(self):
        s = _state([_hostile(x=200, y=200)])
        c = s.contacts[0]
        c.everDetected = True

        # The detection odds climb with every challenge, so a worked track is
        # unmasked within a handful of attempts even holding the clock still.
        for _ in range(5):
            call_iff(s, c.id)
            if c.spoofDetected:
                break

        assert c.spoofDetected is True
        assert c.iffConfidence == 0.0
        assert any("SPOOF DETECTED" in e.text for e in s.log)

    def test_a_resolved_spectrum_sharpens_the_spoof_ear(self):
        # At clock 19 the spoof roll is 0.5: below the spectrum-assisted 0.55,
        # above the bare 0.35.  The resolved barcode is what catches it.
        naive = _state([_hostile(x=200, y=200)])
        naive.clock = 19
        naive.contacts[0].everDetected = True
        savvy = _state([_hostile(x=200, y=200)])
        savvy.clock = 19
        c = savvy.contacts[0]
        c.everDetected = True
        c.waveform.resolved = True
        c.waveform.progress = 1.0

        call_iff(naive, naive.contacts[0].id)
        call_iff(savvy, c.id)

        assert naive.contacts[0].spoofDetected is False
        assert c.spoofDetected is True


class TestFiringSolutions:
    def _ready(self, *, confidence: float = 0.9, state: str = "classified"):
        s = _state([_hostile(x=10)])
        c = s.contacts[0]
        c.everDetected = True
        c.confidence = confidence
        c.state = state
        return s, c

    def test_a_quick_shot_waives_part_of_the_requirement(self):
        # A 31% track is short of the particle cannon's 45% bar, but the quick
        # shot's relief lets it hold anyway.
        s, c = self._ready(confidence=0.31, state="tracking")
        prep_weapons(s, c.id, "armed", "particle-cannon", "quick")
        assert s.ship.weaponsState == "armed"
        assert s.ship.weapon == "particle-cannon"
        assert s.ship.shotType == "quick"

    def test_a_refined_shot_on_the_same_track_is_refused(self):
        s, c = self._ready(confidence=0.31, state="tracking")
        prep_weapons(s, c.id, "armed", "particle-cannon", "refined")
        assert s.ship.weaponsState == "standby"
        assert any("short of the" in e.text for e in s.log)

    def test_a_quick_shot_costs_more_exposure_than_a_refined_one(self):
        quick, qc = self._ready(confidence=0.6, state="probable")
        prep_weapons(quick, qc.id, "armed", "heat-seeker", "quick")
        refined, rc = self._ready(confidence=0.6, state="probable")
        prep_weapons(refined, rc.id, "armed", "heat-seeker", "refined")

        assert quick.ship.exposure > refined.ship.exposure

    def test_a_torpedo_will_not_lock_an_unconfirmed_track(self):
        s, c = self._ready(confidence=0.8, state="classified")
        prep_weapons(s, c.id, "armed", "torpedo", "refined")
        assert s.ship.weaponsState == "standby"

        c.state = "confirmed"
        prep_weapons(s, c.id, "armed", "torpedo", "refined")
        assert s.ship.weaponsState == "armed"

    def test_a_mount_refuses_a_track_outside_its_envelope(self):
        s, c = self._ready(confidence=0.9)
        c.pos = Vec(x=20, y=0, z=0)  # past the particle cannon's 18 klik
        prep_weapons(s, c.id, "armed", "particle-cannon", "quick")
        assert s.ship.weaponsState == "standby"
        assert any("envelope" in e.text for e in s.log)

    def test_the_handoff_pack_reports_the_mount_and_shot(self):
        s, c = self._ready(confidence=0.9)
        prep_weapons(s, c.id, "locked", "heat-seeker", "refined")

        force_handoff(s, "Captain", c.id)

        w = s.handoffPack.weapons
        assert w.prepped is True
        assert w.weapon == "heat-seeker"
        assert w.shotType == "refined"
        assert w.solutionQuality > 0

    def test_standdown_clears_the_solution(self):
        s, c = self._ready(confidence=0.9)
        prep_weapons(s, c.id, "locked", "heat-seeker", "refined")
        standdown_weapons(s)

        assert s.ship.weaponsState == "safe"
        assert s.ship.weapon == ""
        assert s.ship.solutionQuality == 0.0
        assert s.ship.shotType == "quick"
        assert s.ship.weaponTarget == ""

    def test_a_solution_records_its_target_for_the_ui(self):
        s, c = self._ready(confidence=0.9)
        prep_weapons(s, c.id, "locked", "heat-seeker", "refined")

        # The locked solution names the contact so the activity UI can reveal
        # that hull's picture.
        assert s.ship.weaponTarget == c.id
        assert s.ship.weaponsState == "locked"

    def test_a_refused_solution_still_names_the_target(self):
        s, c = self._ready(confidence=0.8, state="classified")
        prep_weapons(s, c.id, "armed", "torpedo", "refined")

        assert s.ship.weaponsState == "standby"
        assert s.ship.weaponTarget == c.id


class TestCommsWeaponsEffects:
    def _resolve(self, s, effect):
        s.events.append(
            DecisionEvent(
                id="e1",
                title="Test",
                kind="comms",
                deadline=s.clock + 90,
                text="t",
                source="test",
                options=[DecisionOption(id="a", label="A", effect=effect)],
            )
        )
        resolve_event(s, "e1", "a")

    def test_a_relay_spares_the_ship_signature(self):
        s = _state([_hostile(x=200, y=200)])
        before = s.ship.exposure
        self._resolve(s, EventEffect(relay=True))
        assert s.ship.exposure < before
        assert any("relayed" in e.text for e in s.log)

    def test_a_challenge_response_works_the_transponder(self):
        s = _state([_freighter(x=20)])
        c = s.contacts[0]
        c.everDetected = True
        self._resolve(s, EventEffect(challenge=True, targetId=c.id))
        assert c.iffConfidence > 0
        assert c.iffChallenges == 1

    def test_civilian_traffic_joins_the_plot_as_neutral(self):
        s = _state([_hostile(x=200, y=200)])
        before = len(s.contacts)
        self._resolve(s, EventEffect(civilian=True))
        assert len(s.contacts) == before + 1
        fresh = s.contacts[-1]
        assert fresh.faction == "neutral"
        assert fresh.hostile is False

    def test_a_false_surrender_can_be_a_genuine_prize(self):
        s = _state([_hostile(x=10)])
        c = s.contacts[0]
        c.everDetected = True
        s.clock = 1  # hash_random(1, 41) < 0.5 -> genuine
        self._resolve(s, EventEffect(falseSurrender=True))

        assert c.hostile is False
        assert c.faction == "neutral"
        assert s.ship.weaponsState == "safe"

    def test_a_false_surrender_can_be_a_trap(self):
        s = _state([_hostile(x=10)])
        c = s.contacts[0]
        c.everDetected = True
        before = len(s.contacts)
        s.clock = 0  # hash_random(0, 41) >= 0.5 -> trap
        self._resolve(s, EventEffect(falseSurrender=True))

        assert len(s.contacts) == before + 1
        assert any("Trap" in e.text for e in s.log)


class TestCommsWeaponsEventTemplates:
    @pytest.mark.parametrize(
        "template",
        ["relay", "challenge", "civilian", "false-surrender", "weapons-warning"],
    )
    def test_templates_build_with_options(self, template):
        s = _state([_hostile(x=20)])
        ev = make_event(s, template)
        assert ev.id == f"{template}-{int(s.clock)}"
        assert len(ev.options) >= 2


class TestNavigationAndEwProtocolMessages:
    def test_buoy_messages_parse(self):
        deploy = parse_c2s({"type": "nav:deployBuoy"})
        assert deploy.type == "nav:deployBuoy"
        recover = parse_c2s({"type": "nav:recoverBuoy", "buoyId": "buoy-1"})
        assert recover.type == "nav:recoverBuoy"
        assert recover.buoyId == "buoy-1"

    def test_noisemaker_message_parses(self):
        msg = parse_c2s({"type": "ew:noisemaker"})
        assert msg.type == "ew:noisemaker"
