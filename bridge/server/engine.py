"""CAPTAIN game engine.

Direct port of ``apps/server/src/engine.ts``. Every function operates on a
room's :class:`~bridge.shared.types.GameState` without sharing sequence counters
between rooms.
"""

from __future__ import annotations

import math
import uuid
from typing import Any

from pydantic import BaseModel

from ..shared import describe_type, state_of_confidence
from ..shared.drives import drive_name, drive_spec
from ..shared.ehd import compute_ehd, hull_hd
from ..shared.environments import environment_for_hazard, environment_spec
from ..shared.shipyard import (
    MODULES,
    default_loadout,
    fits_arc,
    hull_entry,
    module_multiplier,
    module_spec,
    module_sum,
    module_totals,
    within_budgets,
)
from ..shared.checks import (
    STATION_SKILLS,
    check as run_check,
    default_score,
    difficulty,
    roll_d20,
    skill_modifier,
)
from ..shared.campaigns import (
    CAPSHIP_CLASSES,
    ESCORT_CLASSES,
    FIGHTER_CLASSES,
    military_name,
    vessel_name,
)
from ..shared.constants import (
    ACTIVE_SWEEP_RANGE_KLIK,
    ALTITUDE_RATE_KLIK_PER_HOUR,
    AUTO_TICK_MINUTE,
    ALERT_FUEL_CAPACITY,
    ALERT_FUEL_COST,
    BINGO_RESERVE_FRACTION,
    ETA_RANGE_KLIK,
    ASTRO_DC_NAME,
    ASTRO_DC_PER_CHART_HOUR,
    EXPOSURE_PER_KLIK,
    JUMP_ALIGN_RATE_PER_MIN,
    JUMP_COMMIT_FUEL_COST,
    JUMP_MISJUMP_DAMAGE,
    JUMP_MISJUMP_DELAY_MIN,
    JUMP_MISJUMP_FLOOR,
    JUMP_RANGE_KLIK,
    JUMP_SPOOL_EXPOSURE,
    JUMP_SPOOL_FUEL_COST,
    JUMP_SPOOL_MAX_SPEED,
    JUMP_SPOOL_NOISE,
    NAV_ARRIVAL_RADIUS_PAD,
    NAV_INCIDENT_DAMAGE,
    NAV_INCIDENT_OFFSET,
    NAV_OFFSET_PER_CHART_HOUR,
    NAV_OFFSET_PER_DEGREE,
    NAV_STALE_CHART_HOURS,
    NAV_SURVEY_DC_NAME,
    NAV_ALIGN_ERROR_PENALTY,
    NAV_ERROR_MAX_KLIK,
    NAV_ERROR_RATE_PER_HOUR,
    NAV_FIX_BASE_KLIK,
    NAV_FIX_LANDMARK_DC_NAME,
    NAV_FIX_LANDMARK_RANGE_KLIK,
    NAV_FIX_PING_EXPOSURE,
    NAV_FIX_STAR_DC_NAME,
    BAFFLE_ARC_DEG,
    BAFFLE_ATTENUATION,
    BAFFLE_CLEAR_MINUTES,
    BAFFLE_CLEAR_NOISE,
    DATUM_DECAY_PER_MIN,
    DATUM_DRIFT_DECAY_MULTIPLIER,
    DATUM_INITIAL_RADIUS_KLIK,
    DATUM_LOCK_THRESHOLD,
    DATUM_MAX_ACTIVE,
    DATUM_MAX_AGE_MIN,
    DATUM_RADIUS_GROWTH,
    DATUM_SEARCH_BONUS,
    DATUM_SEARCH_RANGE_KLIK,
    HUNTER_TURN_RATE_DEG_PER_MIN,
    LAYER_ATTENUATION,
    MANEUVERS,
    MANEUVER_HOLD_MIN,
    FATIGUE_PENALTY_AT,
    FATIGUE_PENALTY_DIVISOR,
    FATIGUE_PER_HOUR,
    HEAT_ALERT,
    HEAT_BASE_PER_HOUR,
    HEAT_BOTTLE_DISSIPATION,
    HEAT_BOTTLE_NOISE_RELIEF,
    HEAT_CRITICAL,
    HEAT_DISSIPATION_PER_HOUR,
    HEAT_PENALTY_AT,
    HEAT_PENALTY_MAX,
    HEAT_SENSOR_ACTIVE,
    HEAT_SPOOL,
    HEAT_VENT_EXPOSURE,
    HEAT_VENT_PER_HOUR,
    HEAT_WEAPONS,
    RALLY_DC_NAME,
    SHAKEN_PENALTY,
    SHOCK_CORE_DAMAGE,
    UNDERMANNED_CREW,
    UNDERMANNED_PENALTY,
    BARRIER_ALERT_MIN,
    HANGAR_OPEN_EXPOSURE,
    HANGAR_OPEN_MIN,
    SALVAGE_SPARES_MAX,
    ORDNANCE_DETECT_KLIK,
    ORDNANCE_FUEL_KLIK,
    ORDNANCE_HIT_KLIK,
    ORDNANCE_SHOOT_DC_NAME,
    ORDNANCE_TURN_RATE_DEG_PER_MIN,
    ORDNANCE_WARHEAD,
    SPOOF_BONUS_PER_POD,
    SPOOF_DC_NAME,
    SPOOF_DECOY_CHANCE,
    SPOOF_DURATION_MIN,
    CONTAMINATION_CHANCE_PER_HOUR,
    NO_SPARES_DC_PENALTY,
    EVA_COLD_INJURY,
    PROVISIONS_HOURS,
    SPARES_LOADOUT,
    SPOOF_POD_LOADOUT,
    SUBSYSTEM_ARMOR_FACTOR,
    SUBSYSTEM_SHIELD_FACTOR,
    SUBSYSTEM_TARGET_DC_NAME,
    MANEUVER_NOISE,
    LAYER_CROSS_BREAK_MIN,
    LAYER_CROSS_NOISE,
    TMA_BASE_QUALITY,
    TMA_DATUM_RECENTER,
    TMA_MAX_MIN,
    TMA_MIN_BEARING_DEG,
    TMA_MIN_TURN_DEG,
    POSTURE_DECAY_MULTIPLIER,
    POSTURE_LOCK_MULTIPLIER,
    COMMS_WINDOW_DURATION_MIN,
    COMMS_WINDOW_PERIOD_MIN,
    FUEL_BURN_ACTIVE_SENSOR,
    FUEL_BURN_ALERT,
    FUEL_BURN_CRUISE_PER_HOUR,
    FUEL_BURN_IDLE_PER_HOUR,
    FUEL_BURN_MAX_PER_HOUR,
    FUEL_HAZARD_CLUTTER_FACTOR,
    CORE_DAMAGE_EXCESS_STEP,
    CORE_DAMAGE_PER_POINT,
    JURY_RIG_RELIEF,
    MIN_SIZE_CLASS,
    REPAIR_DC_NAME,
    REPAIR_DC_PER_DAMAGE,
    REPAIR_MIN_PER_CHECK,
    SYSTEM_HIT_TABLE,
    SYSTEM_WEAR_BASE_PER_HOUR,
    WEAR_FAIL_AT,
    WEAR_MALFUNCTION_CHANCE,
    WEAR_RISK_AT,
    WEAR_SPEED_FACTOR,
    SHIELD_REFOCUS_FRACTION,
    SHIELD_REGEN_INTERVAL_MIN,
    SHIELD_REGEN_PERCENT,
    SHIP_SYSTEMS,
    BATTERY_ACTIVE_SWEEP_COST,
    BATTERY_FLANK_PER_HOUR,
    BATTERY_MIN_ACTIVE,
    BATTERY_NOISE_FILTER_COST,
    BATTERY_QUIET_RECHARGE_PER_HOUR,
    BATTERY_RADAR_PER_HOUR,
    BATTERY_RECHARGE_PER_HOUR,
    BEARING_DRIFT_MINUTES,
    BUOY_PASSIVE_RANGE_KLIK,
    BUOY_TRIANGULATION_BASELINE_KLIK,
    BUOY_TRIANGULATION_CONFIDENCE,
    CONFIDENCE_BY_STATE,
    CONTACT_DECAY_MINUTES,
    CRUISE_KPS,
    DEFAULT_ADVANCE_MINUTES,
    DEFAULT_EMCON,
    DETECTED_LOCK,
    DISENGAGE_RANGE_KLIK,
    EMISSION_LINES,
    EMISSION_MODE_FACTOR,
    EM_BASE_QUALITY,
    EM_LOST_QUALITY,
    EM_SUN_GLARE_DEG,
    EM_SUN_SCRAMBLE,
    EM_TERRAIN_SCRAMBLE,
    ENGAGEMENT_RANGE_KLIK,
    ENEMY_LOCK_DECAY,
    ENEMY_LOCK_MINUTES,
    ENEMY_PURSUE_LOCK,
    ENEMY_PASSIVE_BASE_KLIK,
    ENEMY_PROFILE_WEIGHT,
    ENVIRONMENTAL_TYPES,
    ENDURE_MINUTES,
    ESCALATION_TIERS,
    EVENT_EXPIRY_TENSION,
    EXPOSE_CLOSE_IFF,
    EXPOSE_DRIFT_PER_HOUR,
    EXPOSE_GRAVIDAR,
    EXPOSE_OPTICS,
    EXPOSE_RADAR,
    EXPOSE_SPEED_MAX,
    FLANK_KPS,
    FREQ_BANDS,
    FRONT_LINE_GAIN_CONFIRMED,
    FRONT_LINE_GAIN_TENTATIVE,
    FRONT_LINE_LOSS_BAD_CALL,
    GRAVIDAR_ACQUIRE_THRESHOLD,
    GRAVIDAR_RANGE_ERROR,
    GRAVIDAR_RANGE_KLIK,
    HYDROGEN_BAND,
    IFF_CONFIDENCE_DARK,
    IFF_CONFIDENCE_DECOY,
    IFF_CONFIDENCE_LEGIT,
    IFF_SPOOF_DETECT_BASE,
    IFF_SPOOF_DETECT_PER_CHALLENGE,
    IFF_SPOOF_DETECT_SPECTRUM,
    KLIK_PER_KPS_HOUR,
    MASS_KT,
    NEUTRAL_SIGNATURE_SET,
    NOISEMAKER_ENEMY_SIGNAL,
    NOISEMAKER_LOADOUT,
    NOISEMAKER_SELF_EM,
    NOISEMAKER_SELF_PASSIVE,
    NOISEMAKER_TURNS,
    NOISE_CAP,
    NOISE_DEFAULT_RATE,
    NOISE_FILTER_COOLDOWN,
    NOISE_INIT,
    NOISE_MIN,
    OBSTACLE_EFFECTS,
    OBSTACLE_LOS_INFLUENCE,
    OBSTACLE_RADIUS,
    PAINTED_EXPOSURE,
    PAINTED_HULL_DAMAGE,
    PAINTED_READINESS_DAMAGE,
    PASSIVE_ACQUIRE_THRESHOLD,
    PASSIVE_BASE_RANGE_KLIK,
    PASSIVE_SAMPLE_SCALE,
    QUICK_SHOT_EXPOSURE,
    QUICK_SHOT_RELIEF,
    READINESS_RECOVER_QUIET,
    READINESS_RECOVER_STOPPED,
    READINESS_WEAR_CRUISE,
    READINESS_WEAR_MAX,
    REFINED_SHOT_EXPOSURE,
    REFLECTION_LINES,
    REPORT_TENSION_RELIEF,
    SELF_NOISE_BURDEN,
    SELF_NOISE_SHADOW,
    SENSOR_BUOY_LOADOUT,
    SHIP_ALT_MAX_KLIK,
    SILENT_KPS,
    SPECTRUM_BINS,
    STATE_SCHEMA_VERSION,
    STERN_DAZZLE_ARC_DEG,
    STERN_DAZZLE_STRENGTH,
    STERN_HEAT_BY_MODE,
    TENSION_PER_EXPOSURE,
    TENSION_RELAX_PER_HOUR,
    TYPICAL_SIGHTING_RANGE_KLIK,
    WAVEFORM_LISTEN_PROGRESS,
)
from ..shared.events import engagement_prompt, make_event
from ..shared.math_utils import (
    bearing,
    bearing_diff,
    clamp,
    dist,
    elevation,
    flat_dist,
    format_clock,
    hash_random,
    moved,
    noise,
    segments_intersect,
    wrap_bearing,
)
from ..shared.ships import (
    SHIP_CLASSES,
    TERRAIN_IMAGES,
    ship_briefs,
    ship_class,
    ship_for_type,
    ship_name,
)
from ..shared.weapons import solution_grade, weapon_spec
from ..shared.types import (
    BearingSample,
    Buoy,
    CampaignSeed,
    CheckResult,
    Condition,
    Contact,
    CatalogueMatch,
    ContactPatch,
    ContactTemplate,
    ContactType,
    DecisionEvent,
    EmconPatch,
    EmconnState,
    EventEffect,
    GameState,
    GravArc,
    HandoffContact,
    HandoffOwn,
    HandoffPack,
    HandoffWeapons,
    LogEntry,
    LogEntryType,
    LogbookDigest,
    OperatingMode,
    RoomRef,
    Seat,
    SeatId,
    Datum,
    JumpState,
    Ordnance,
    SensorLayer,
    TmaState,
    NavCommit,
    PlotLeg,
    SeatSkills,
    SensorReadout,
    ShieldArc,
    ShipClass,
    AlertLevel,
    ShipState,
    ShotType,
    Spectrum,
    SystemHealth,
    Vec,
    WarState,
    WeaponsState,
    Waveform,
    ZBand,
)


def _next_buoy_number(state: GameState) -> int:
    used = {
        int(buoy.id.rsplit("-", 1)[1])
        for buoy in state.buoys
        if buoy.id.startswith("buoy-") and buoy.id.rsplit("-", 1)[1].isdigit()
    }
    number = 1
    while number in used:
        number += 1
    return number


def _round(x: float) -> int:
    """JavaScript ``Math.round`` (half toward +infinity)."""
    return int(math.floor(x + 0.5))


def _round_to(x: float, places: int = 1) -> float:
    """Round to ``places`` decimals (half toward +infinity)."""
    factor = 10 ** places
    return math.floor(x * factor + 0.5) / factor


def _as(model: type[BaseModel], value: Any) -> Any:
    """Accept an already-built model or the raw dict the wire layer may pass."""
    if isinstance(value, model):
        return value
    return model.model_validate(value)


def _b36(n: int) -> str:
    """JavaScript ``Number.prototype.toString(36)`` for integers."""
    if n == 0:
        return "0"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    neg = n < 0
    n = abs(n)
    out = ""
    while n:
        out = digits[n % 36] + out
        n //= 36
    return ("-" + out) if neg else out


# ---------------------------------------------------------------------------
# State creation
# ---------------------------------------------------------------------------


def _patrol_route(center: Vec, radius_klik: float) -> list[Vec]:
    """A box patrol loop for the crew to fly when the GM gives no orders."""
    r = max(15.0, radius_klik * 0.6)
    return [
        Vec(x=center.x + r, y=center.y, z=0),
        Vec(x=center.x, y=center.y + r, z=0),
        Vec(x=center.x - r, y=center.y, z=0),
        Vec(x=center.x, y=center.y - r, z=0),
    ]


def _init_defences(ship: ShipState, klass: ShipClass) -> None:
    """Fit a fresh ship's shields, armour, systems and fuel."""
    mid = (klass.shieldFore + klass.shieldAft) / 2
    ship.shields = {
        "fore": ShieldArc(shp=klass.shieldFore, max=klass.shieldFore),
        "aft": ShieldArc(shp=klass.shieldAft, max=klass.shieldAft),
        "port": ShieldArc(shp=mid, max=mid),
        "starboard": ShieldArc(shp=mid, max=mid),
    }
    ship.armor = {
        "fore": klass.armorFore,
        "aft": klass.armorAft,
        "port": klass.armorPort,
        "starboard": klass.armorStarboard,
    }
    ship.systems = {name: SystemHealth() for name in SHIP_SYSTEMS}
    ship.core = 0.0
    # The ship starts at Condition Three with shields down and cold mounts.
    ship.alert = "three"
    for arc in ship.shields.values():
        arc.shp = 0.0
    ship.spoofPods = SPOOF_POD_LOADOUT
    ship.spares = SPARES_LOADOUT
    ship.provisions = PROVISIONS_HOURS
    ship.ordnanceLoadout = {"torpedo": 2, "heat-seeker": 4}
    _init_loadout(ship, klass)
    ship.fuelCapacity = klass.fuelCapacity or ALERT_FUEL_CAPACITY
    ship.fuel = ship.fuelCapacity
    ship.shieldRegenAt = 0.0


def _raise_shields(ship: ShipState) -> None:
    """Charge every arc to full — raising shields from cold is instant."""
    for arc in ship.shields.values():
        arc.shp = arc.max


def set_alert(state: GameState, level: AlertLevel) -> None:
    """Move the ship between Conditions Three, Two and One.

    Two raises shields; One also arms the mounts.  Going **up** costs a fuel
    point and instantly charges the mounts; standing down is free.  Attack
    actions require Condition One.
    """
    ship = state.ship
    if level == ship.alert:
        return
    order = {"three": 0, "two": 1, "one": 2}
    raising = order[level] > order[ship.alert]
    if raising and order[ship.alert] == 0 and _system_down(state, "shields"):
        log(state, "COMMAND", "Shield generators are down — cannot raise them.", "warn")
        return
    if raising:
        if ship.fuel < ALERT_FUEL_COST:
            log(
                state,
                "COMMAND",
                "Not enough fuel to bring the ship to action stations.",
                "warn",
            )
            return
        ship.fuel = clamp(ship.fuel - ALERT_FUEL_COST, 0, ship.fuelCapacity)
        if order[ship.alert] == 0:
            _raise_shields(ship)
            ship.shieldRegenAt = state.clock + SHIELD_REGEN_INTERVAL_MIN
    ship.alert = level
    if level == "three":
        for arc in ship.shields.values():
            arc.shp = 0.0
        ship.weaponsState = "safe"
        ship.roe = "safe"
    elif level == "two":
        if ship.weaponsState in ("armed", "locked"):
            ship.weaponsState = "safe"
            ship.roe = "safe"
    else:  # one
        ship.weaponsState = "armed"
    label = {"three": "THREE", "two": "TWO", "one": "ONE"}[level]
    log(
        state,
        "COMMAND",
        f"Alert Condition {label} — "
        + (
            "shields down, mounts cold."
            if level == "three"
            else "shields up, mounts armed."
            if level == "one"
            else "shields up, mounts cold."
        ),
        "ok" if level == "one" else "info",
    )
    state.seq += 1


def _regen_shields(state: GameState, dt: float) -> None:
    """Shield generators recharge every ten simulated minutes, if raised.

    The number of ten-minute ticks is derived from the simulated clock, so a
    single 30-minute step regenerates exactly as much as three 10-minute steps.
    """
    ship = state.ship
    if ship.alert == "three" or not ship.shields or _system_down(state, "shields"):
        return
    if state.clock < ship.shieldRegenAt:
        return
    ticks = 0
    while state.clock >= ship.shieldRegenAt:
        ticks += 1
        ship.shieldRegenAt += SHIELD_REGEN_INTERVAL_MIN
    bonus = max(0, skill_modifier(skill_score(state, "command", "Defenses")))
    gained = 0.0
    for arc in ship.shields.values():
        if arc.max <= 0:
            continue
        before = arc.shp
        arc.shp = clamp(
            arc.shp + (arc.max * SHIELD_REGEN_PERCENT + bonus) * ticks, 0, arc.max
        )
        gained += arc.shp - before
    if gained > 0:
        log(
            state,
            "DC",
            f"Shield generators recharge {_round(gained)} SHP across the arcs.",
            "info",
        )


def refocus_shields(state: GameState, from_arc: str, to_arc: str) -> None:
    """Move shield power between arcs: two consecutive Defenses Checks."""
    ship = state.ship
    src = ship.shields.get(from_arc)
    dst = ship.shields.get(to_arc)
    if src is None or dst is None or from_arc == to_arc:
        return
    first = station_check(
        state, "Defenses", difficulty("hard"), action="refocus_a", contact_id=to_arc
    )
    second = station_check(
        state, "Defenses", difficulty("hard"), action="refocus_b", contact_id=to_arc
    )
    if first.success and second.success:
        amount = min(src.shp, src.max * SHIELD_REFOCUS_FRACTION)
        src.shp = clamp(src.shp - amount, 0, src.max)
        dst.shp = clamp(dst.shp + amount, 0, dst.max)
        log(
            state,
            "DC",
            f"Refocus complete — {_round(amount)} SHP moved from {from_arc} to {to_arc}.",
            "ok",
        )
    elif first.outcome == "critical-failure" or second.outcome == "critical-failure":
        src.shp = clamp(src.shp * 0.9, 0, src.max)
        system = ship.systems.get("shields")
        if system is not None:
            system.health = clamp(system.health - 5, 0, 100)
        log(
            state,
            "DC",
            f"Refocus botched — the {from_arc} emitter arcs and the generator takes damage.",
            "danger",
        )
    else:
        log(
            state,
            "DC",
            "Refocus failed — the generators will not hold the transfer.",
            "warn",
        )
    state.seq += 1


def _size_class(ship: ShipState) -> int:
    klass = ship_class(ship.shipClass)
    return max(MIN_SIZE_CLASS, _round(klass.body / 25.0)) if klass.body else 6


def apply_damage(
    state: GameState,
    amount: float,
    arc: str = "fore",
    *,
    system: str | None = None,
) -> str | None:
    """Resolve a hit: shields, then armour, then core, plus a system strike.

    Returns the system that was struck (or ``None``).  A hit that lands on an
    already-dead system does no further damage to it but instead escalates core
    damage — the "stop poking the hole" rule.
    """
    ship = state.ship
    if amount <= 0:
        return None
    if arc not in ship.shields:
        arc = "fore"
    remaining = float(amount)

    shield = ship.shields.get(arc)
    if shield is not None and shield.shp > 0:
        absorbed = min(shield.shp, remaining)
        shield.shp -= absorbed
        remaining -= absorbed

    armour = ship.armor.get(arc, 0.0)
    if remaining > 0 and armour > 0:
        absorbed = min(armour, remaining)
        ship.armor[arc] = armour - absorbed
        remaining -= absorbed

    if remaining > 0:
        ship.core = clamp(
            ship.core + remaining * CORE_DAMAGE_PER_POINT / _size_class(ship), 0, 100
        )
        if ship.core >= SHOCK_CORE_DAMAGE:
            shock_crew(state, "the hull is badly hit")

    # A hit the shields or armour stopped never reaches a system.
    hit: str | None = None
    if remaining > 0:
        face = (roll_d20(state, check_salt("damage", f"{arc}{state.seq}")) - 1) % len(
            SYSTEM_HIT_TABLE
        )
        hit = system or SYSTEM_HIT_TABLE[face]
        struck = ship.systems.get(hit)
        if struck is not None:
            if struck.health <= 0:
                ship.excessHits += 1
                ship.core = clamp(
                    ship.core + CORE_DAMAGE_EXCESS_STEP * ship.excessHits, 0, 100
                )
                log(
                    state,
                    "TAC",
                    f"Hit on the already-dead {hit} — "
                    f"{_round(CORE_DAMAGE_EXCESS_STEP * ship.excessHits)}% more core damage.",
                    "danger",
                )
            else:
                ship.excessHits = 0
                struck.health = clamp(struck.health - remaining, 0, 100)
                if struck.health <= 0 or struck.juryRigged:
                    struck.malfunctioning = True
                    struck.juryRigged = False
                    log(state, "TAC", f"{hit} is DOWN.", "danger")
    log(
        state,
        "TAC",
        f"Hit on the {arc} arc for {_round(amount)} — core {_round(ship.core)}%"
        + (f", {hit} struck." if hit else ", absorbed."),
        "danger",
    )
    state.seq += 1
    return hit


def repair_system(state: GameState, system: str, *, jury_rig: bool = False) -> None:
    """Damage-control work on one system.

    A Damage Control Check restores ``REPAIR_MIN_PER_CHECK`` plus the degree.
    A jury-rig is easier but marks the system to fail again on the next hit;
    armour and core damage cannot be repaired in a watch.
    """
    ship = state.ship
    target = ship.systems.get(system)
    if target is None:
        return
    damage = max(0.0, 100.0 - target.health)
    spec = environment_spec(state.environment)
    dc = difficulty(REPAIR_DC_NAME) + int(damage // REPAIR_DC_PER_DAMAGE)
    dc += spec.repairDcPenalty
    if state.ship.spares <= 0:
        dc += NO_SPARES_DC_PENALTY
    if jury_rig:
        dc -= JURY_RIG_RELIEF
    result = station_check(
        state,
        "Damage Control",
        max(difficulty("easy"), dc),
        action="repair",
        contact_id=system,
    )
    if result.success:
        restored = REPAIR_MIN_PER_CHECK + result.degree
        target.health = clamp(target.health + restored, 0, 100)
        if state.ship.spares > 0:
            state.ship.spares -= 1
        if spec.contamination and not jury_rig:
            target.contaminated = spec.contamination
        # A successful Damage Control Check brings the system back on line, even
        # if it is not yet at full health.
        target.malfunctioning = False
        if target.health >= 100:
            target.juryRigged = False
            target.wear = clamp(target.wear - 10, 0, 100)
            log(state, "DC", f"{system} restored to full.", "ok")
        elif jury_rig:
            target.juryRigged = True
            log(
                state,
                "DC",
                f"{system} jury-rigged (+{restored}) — it will fail again under fire.",
                "warn",
            )
        else:
            target.juryRigged = False
            log(state, "DC", f"{system} partly repaired (+{restored}).", "ok")
    else:
        log(state, "DC", f"Repair failed on {system} — the chief needs another go.", "warn")
    state.seq += 1


def maintain_system(state: GameState, system: str) -> None:
    """Scheduled upkeep: strip wear before it turns into a malfunction."""
    ship = state.ship
    target = ship.systems.get(system)
    if target is None:
        return
    result = station_check(
        state,
        "Damage Control",
        difficulty("routine"),
        action="maintain",
        contact_id=system,
    )
    if result.success:
        target.wear = clamp(target.wear - (25 + result.degree), 0, 100)
        if target.contaminated:
            cleaned = target.contaminated
            target.contaminated = ""
            log(state, "DC", f"{system} cleaned of {cleaned}.", "ok")
        log(
            state,
            "DC",
            f"{system} serviced — wear down to {_round(target.wear)}%.",
            "ok",
        )
    else:
        target.wear = clamp(target.wear + 5, 0, 100)
        log(state, "DC", f"Service on {system} did not take — wear {_round(target.wear)}%.", "warn")
    state.seq += 1


def _accrue_wear(state: GameState, dt: float) -> None:
    """Wear accretes with time and hard running; it never heals itself."""
    ship = state.ship
    hours = dt / 60.0
    speed_factor = 1.0 + (ship.speed / 100.0) * WEAR_SPEED_FACTOR
    for name, system in ship.systems.items():
        system.wear = clamp(
            system.wear
            + SYSTEM_WEAR_BASE_PER_HOUR
            * speed_factor
            * hours
            * env_factor(state, "wearPerHour"),
            0,
            100,
        )
        if system.malfunctioning:
            continue
        if system.wear >= WEAR_FAIL_AT:
            system.malfunctioning = True
            log(state, "DC", f"{name} has worn out — it fails.", "danger")
        elif system.wear >= WEAR_RISK_AT and (
            hash_random(state.clock, _id_salt(name) + 700) < WEAR_MALFUNCTION_CHANCE
        ):
            system.malfunctioning = True
            log(state, "DC", f"{name} stutters and drops out — wear {_round(system.wear)}%.", "warn")


def fuel_burn_per_hour(state: GameState) -> float:
    """Current fuel burn: speed, alert state, the radar and the terrain."""
    ship = state.ship
    if ship.speed <= 0:
        base = FUEL_BURN_IDLE_PER_HOUR
    elif ship.cruiseSpeed > 0 and ship.speed <= ship.cruiseSpeed:
        frac = ship.speed / ship.cruiseSpeed
        base = FUEL_BURN_IDLE_PER_HOUR + (
            FUEL_BURN_CRUISE_PER_HOUR - FUEL_BURN_IDLE_PER_HOUR
        ) * frac
    else:
        span = max(1.0, ship.maxSpeed - ship.cruiseSpeed)
        frac = clamp((ship.speed - ship.cruiseSpeed) / span, 0, 1)
        base = FUEL_BURN_CRUISE_PER_HOUR + (
            FUEL_BURN_MAX_PER_HOUR - FUEL_BURN_CRUISE_PER_HOUR
        ) * frac
    base += FUEL_BURN_ALERT.get(ship.alert, 0.0)
    if ship.activeSensor:
        base += FUEL_BURN_ACTIVE_SENSOR
    hazard = FUEL_HAZARD_CLUTTER_FACTOR * (state.campaign.clutter or 0.0)
    hazard += env_factor(state, "fuel") - 1.0
    hazard += sum(
        h.exposure * h.intensity
        for h in state.campaign.hazards
        if h.startMinute <= state.clock
        and (h.endMinute is None or state.clock <= h.endMinute)
    )
    return base * (1.0 + hazard)


def _update_transit(state: GameState) -> None:
    """Refresh the derived transit picture and flag bingo / dead-drift."""
    ship = state.ship
    burn = fuel_burn_per_hour(state)
    ship.fuelBurnPerHour = _round_to(burn, 2)
    klik_per_hour = ship.speed * _KLIK_PER_KPS_HOUR
    hours_left = ship.fuel / burn if burn > 0 else 0.0
    ship.fuelRangeKlik = _round_to(hours_left * klik_per_hour, 1)
    # Bingo: fuel to reach the patrol centre at the current burn, plus reserve.
    centre = state.campaign.patrol.center
    home = math.hypot(ship.pos.x - centre.x, ship.pos.y - centre.y)
    if klik_per_hour > 0.01:
        to_home = (home / klik_per_hour) * burn * (1 + BINGO_RESERVE_FRACTION)
    else:
        to_home = ship.fuelCapacity
    # Even alongside the depot, keep a reserve in hand.
    ship.bingoFuel = _round_to(
        max(to_home, ship.fuelCapacity * BINGO_RESERVE_FRACTION), 2
    )
    was_drift = ship.deadDrift
    ship.deadDrift = ship.fuel <= 0.0
    was_bingo = ship.bingo
    ship.bingo = (not ship.deadDrift) and ship.fuel <= ship.bingoFuel
    if ship.deadDrift and not was_drift:
        log(
            state,
            "OPS",
            "FUEL EXHAUSTED — the ship is dead in space. No evasion, no repositioning; "
            "call a tanker, rig a ramscoop, or abandon the leg.",
            "danger",
        )
    elif ship.bingo and not was_bingo:
        log(
            state,
            "OPS",
            f"BINGO FUEL — {_round(ship.fuel)} points left, {_round(ship.bingoFuel)} "
            "needed to get home with reserve.",
            "warn",
        )


def _burn_fuel(state: GameState, dt: float) -> None:
    ship = state.ship
    if ship.fuel <= 0:
        return
    ship.fuel = clamp(ship.fuel - fuel_burn_per_hour(state) * (dt / 60.0), 0, ship.fuelCapacity)


def _update_cpa(state: GameState) -> None:
    """Intercept clock: closest approach and time-to-range for every track."""
    ship = state.ship
    sv = _contact_vel(ship.pos.z, ship.heading, ship.speed)
    for c in state.contacts:
        if c.trueType in ENVIRONMENTAL_TYPES or not c.everDetected:
            c.sensor.cpaKlik = None
            c.sensor.cpaMinutes = None
            c.sensor.etaMinutes = None
            continue
        cv = _contact_vel(c.pos.z, c.heading, c.speed)
        rx, ry = c.pos.x - ship.pos.x, c.pos.y - ship.pos.y
        # ``_contact_vel`` is in kps; positions are klik, so scale to klik/hour.
        vx = (cv.x - sv.x) * _KLIK_PER_KPS_HOUR
        vy = (cv.y - sv.y) * _KLIK_PER_KPS_HOUR
        v2 = vx * vx + vy * vy
        if v2 < 1e-9:
            t = 0.0
        else:
            t = max(0.0, -(rx * vx + ry * vy) / v2)
        cx, cy = rx + vx * t, ry + vy * t
        c.sensor.cpaKlik = _round_to(math.hypot(cx, cy), 1)
        c.sensor.cpaMinutes = _round_to(t * 60, 1)
        # Time until the range closes to the ETA ring (smallest root >= 0).
        cc = rx * rx + ry * ry - ETA_RANGE_KLIK * ETA_RANGE_KLIK
        if cc <= 0:
            c.sensor.etaMinutes = 0.0
        elif v2 < 1e-9:
            c.sensor.etaMinutes = None
        else:
            b = 2 * (rx * vx + ry * vy)
            disc = b * b - 4 * v2 * cc
            if disc < 0:
                c.sensor.etaMinutes = None
            else:
                root = (-b - math.sqrt(disc)) / (2 * v2)
                c.sensor.etaMinutes = _round_to(max(0.0, root) * 60, 1)


def _active_hazard_load(state: GameState) -> float:
    return sum(
        h.exposure * h.intensity
        for h in state.campaign.hazards
        if h.startMinute <= state.clock
        and (h.endMinute is None or state.clock <= h.endMinute)
    )


def nav_leg(state: GameState, nav: Any) -> PlotLeg:
    """Score one candidate leg: time, fuel and exposure, plus a risk flag."""
    ship = state.ship
    distance = dist(ship.pos, nav.pos)
    speed = ship.speed if ship.speed > 0.01 else ship.cruiseSpeed
    klik_per_hour = max(0.01, speed * _KLIK_PER_KPS_HOUR)
    error_hours = ship.navErrorKlik / klik_per_hour
    hours = distance / klik_per_hour
    burn = fuel_burn_per_hour(state)
    exposure = distance * EXPOSURE_PER_KLIK + _active_hazard_load(state) * hours
    risk = "clear"
    if nav.chartAgeHours >= NAV_STALE_CHART_HOURS:
        risk = "stale charts"
    if _active_hazard_load(state) > 0.0:
        risk = "hazard"
    mid = Vec(x=(ship.pos.x + nav.pos.x) / 2, y=(ship.pos.y + nav.pos.y) / 2, z=0)
    for c in state.contacts:
        if c.everDetected and c.hostile and dist(c.pos, mid) < 20:
            risk = "contact"
            break
    return PlotLeg(
        navId=nav.id,
        name=nav.name,
        kind=nav.kind,
        distanceKlik=_round_to(distance, 1),
        timeMinutes=_round_to((hours + error_hours) * 60, 1),
        uncertaintyMinutes=_round_to(error_hours * 60, 1),
        fuelCost=_round_to(burn * hours, 2),
        exposure=_round_to(exposure, 1),
        chartAgeHours=nav.chartAgeHours,
        risk=risk,
    )


def refresh_plot(state: GameState) -> None:
    """Recompute every candidate leg — plans decay as the situation changes."""
    state.plotLegs = [nav_leg(state, n) for n in state.campaign.navPoints]
    if state.navTarget:
        state.navPlan = next(
            (leg for leg in state.plotLegs if leg.navId == state.navTarget), None
        )


def plot_course(state: GameState, nav_id: str) -> None:
    """Ops selects a destination; the legs are scored so the crew can compare."""
    if not any(n.id == nav_id for n in state.campaign.navPoints):
        return
    state.navTarget = nav_id
    refresh_plot(state)
    leg = state.navPlan
    if leg is None:
        return
    log(
        state,
        "OPS",
        f"Plotted {leg.name}: {_round(leg.timeMinutes)} min, {leg.fuelCost} fuel, "
        f"exposure {leg.exposure} — {leg.risk}.",
        "info",
    )
    state.seq += 1


def commit_course(state: GameState, nav_id: str = "") -> None:
    """Commit the plotted leg: an Astrogation Check sets arrival precision."""
    if nav_id:
        state.navTarget = nav_id
    nav = next((n for n in state.campaign.navPoints if n.id == state.navTarget), None)
    if nav is None:
        return
    refresh_plot(state)
    dc = difficulty(ASTRO_DC_NAME) + int(nav.chartAgeHours * ASTRO_DC_PER_CHART_HOUR)
    result = station_check(
        state, "Astrogation", dc, action="astrogation", contact_id=nav.id
    )
    stale = nav.chartAgeHours >= NAV_STALE_CHART_HOURS
    if result.success:
        offset = 0.0
    else:
        offset = (
            result.degree * NAV_OFFSET_PER_DEGREE
            + nav.chartAgeHours * NAV_OFFSET_PER_CHART_HOUR
        )
        if result.outcome == "critical-failure":
            offset += NAV_INCIDENT_OFFSET
    state.navCommit = NavCommit(
        navId=nav.id,
        name=nav.name,
        outcome=result.outcome,
        offsetKlik=_round_to(offset, 1),
        committedAt=state.clock,
        staleCharts=stale,
    )
    state.ship.waypoints = [nav.pos]
    if result.outcome == "critical-failure":
        # A gravity-well incident is structural, not a weapon hit: it bites the
        # core directly, bypassing shields and armour.
        state.ship.core = clamp(
            state.ship.core + NAV_INCIDENT_DAMAGE / _size_class(state.ship), 0, 100
        )
        log(
            state,
            "OPS",
            f"GRAVITY-WELL INCIDENT plotting {nav.name} — the ship is off-axis and "
            "the hull has taken structural damage.",
            "danger",
        )
    log(
        state,
        "OPS",
        f"Leg committed to {nav.name}: Astrogation {result.outcome.replace('-', ' ')}"
        + (
            f", arrival {_round_to(offset, 1)} klik off-axis."
            if offset
            else ", on-axis arrival."
        ),
        "ok" if result.success else "warn",
    )
    state.seq += 1


def survey_nav(state: GameState, nav_id: str) -> None:
    """Sensors re-survey a chart, refreshing its age (and lowering the DC)."""
    nav = next((n for n in state.campaign.navPoints if n.id == nav_id), None)
    if nav is None:
        return
    result = station_check(
        state,
        "Technology",
        difficulty(NAV_SURVEY_DC_NAME),
        action="survey",
        contact_id=nav_id,
    )
    if result.success:
        nav.chartAgeHours = 0.0
        log(state, "SENSORS", f"{nav.name} re-surveyed — charts current.", "ok")
    else:
        nav.chartAgeHours = _round_to(nav.chartAgeHours * 0.5, 1)
        log(
            state,
            "SENSORS",
            f"{nav.name} survey incomplete — chart age {nav.chartAgeHours}h.",
            "warn",
        )
    refresh_plot(state)
    state.seq += 1


def _check_nav_arrival(state: GameState) -> None:
    """Apply the committed leg's arrival error when the ship reaches the point."""
    commit = state.navCommit
    if commit is None:
        return
    nav = next((n for n in state.campaign.navPoints if n.id == commit.navId), None)
    if nav is None:
        state.navCommit = None
        return
    if dist(state.ship.pos, nav.pos) > nav.radiusKlik + NAV_ARRIVAL_RADIUS_PAD:
        return
    if commit.offsetKlik > 0:
        angle = (check_salt("arrive", nav.id) % 360) * math.pi / 180
        state.ship.pos = Vec(
            x=state.ship.pos.x + math.cos(angle) * commit.offsetKlik,
            y=state.ship.pos.y + math.sin(angle) * commit.offsetKlik,
            z=state.ship.pos.z,
        )
        log(
            state,
            "OPS",
            f"Arrival at {commit.name}: {commit.offsetKlik} klik off-axis "
            "(navigation error).",
            "warn",
        )
    else:
        log(state, "OPS", f"Arrival at {commit.name}: on-axis.", "ok")
    state.ship.waypoints = []
    state.navCommit = None
    state.navTarget = ""
    state.navPlan = None
    state.seq += 1


def _accrue_nav_error(state: GameState, dt: float) -> None:
    """Dead reckoning drifts: the longer and faster you run, the less sure."""
    ship = state.ship
    if ship.speed <= 0.01:
        return
    ship.navErrorKlik = clamp(
        ship.navErrorKlik
        + NAV_ERROR_RATE_PER_HOUR * (dt / 60.0) * (1 + ship.speed / 100.0),
        0,
        NAV_ERROR_MAX_KLIK,
    )


def fix_nav(state: GameState, method: str = "star") -> None:
    """Work off dead-reckoning error: star sighting, landmark, or a radar ping."""
    ship = state.ship
    method = (method or "star").lower()
    if method == "landmark":
        near = min(
            (
                n
                for n in state.campaign.navPoints
                if dist(ship.pos, n.pos) <= NAV_FIX_LANDMARK_RANGE_KLIK
            ),
            key=lambda n: dist(ship.pos, n.pos),
            default=None,
        )
        if near is None:
            log(state, "OPS", "No charted landmark in range for a fix.", "warn")
            state.seq += 1
            return
        dc = difficulty(NAV_FIX_LANDMARK_DC_NAME)
        label = f"landmark fix on {near.name}"
    elif method == "ping":
        dc = difficulty(NAV_FIX_STAR_DC_NAME)
        label = "radar fix"
        add_exposure(state, NAV_FIX_PING_EXPOSURE, "navigation fix ping")
    else:
        method = "star"
        dc = difficulty(NAV_FIX_STAR_DC_NAME) + int(_active_hazard_load(state) * 10)
        label = "star sighting"
    result = station_check(state, "Astrogation", dc, action="navfix", contact_id=method)
    if result.success:
        ship.navErrorKlik = NAV_FIX_BASE_KLIK
        log(
            state,
            "OPS",
            f"{label.capitalize()} — position error down to {NAV_FIX_BASE_KLIK:.0f} klik.",
            "ok",
        )
    else:
        ship.navErrorKlik = _round_to(ship.navErrorKlik * 0.6, 1)
        log(
            state,
            "OPS",
            f"{label.capitalize()} failed — the error only trims to {ship.navErrorKlik} klik.",
            "warn",
        )
    refresh_plot(state)
    state.seq += 1


def comms_window_open(state: GameState) -> bool:
    """The relay window cycles; long-range traffic needs it."""
    return (state.clock % COMMS_WINDOW_PERIOD_MIN) < COMMS_WINDOW_DURATION_MIN


def _update_comms_window(state: GameState) -> None:
    was = state.commsOpen
    state.commsOpen = comms_window_open(state)
    next_in = COMMS_WINDOW_PERIOD_MIN - (state.clock % COMMS_WINDOW_PERIOD_MIN)
    state.commsNote = (
        "relay window open"
        if state.commsOpen
        else f"window closed — next in {_round(next_in)} min"
    )
    if state.commsOpen and not was:
        log(state, "COMMS", "Relay window open — long-range traffic is clean.", "info")
    elif was and not state.commsOpen:
        log(
            state,
            "COMMS",
            "Relay window closed — long-range transmissions will be heard by the wrong people.",
            "warn",
        )


def set_drive(state: GameState, drive: str) -> None:
    """The GM or a refit fits a different FTL drive."""
    state.ship.drive = drive
    log(state, "GM", f"FTL drive set to {drive_name(drive)}.", "rp")
    state.seq += 1


def jump_window_open(state: GameState, nav: Any) -> bool:
    """A jump point is only usable inside its gravity/EM window."""
    if nav.windowClose is None:
        return state.clock >= nav.windowOpen
    return nav.windowOpen <= state.clock <= nav.windowClose


def _jump_required(state: GameState, nav: Any) -> float:
    return clamp(
        nav.alignmentRequired + nav.interference + _active_hazard_load(state) * 0.5,
        0.1,
        0.98,
    )


def _jump_interference(state: GameState, nav: Any) -> float:
    return clamp(nav.interference + _active_hazard_load(state) * 0.5, 0.0, 0.9)


def _jump_skill_factor(state: GameState) -> float:
    return 0.5 + skill_score(state, "ops", "Astrogation") / 99.0


def alignment_quality(state: GameState, nav: Any) -> float:
    """How clean the ship's position/heading/velocity are against the point."""
    ship = state.ship
    distance = dist(ship.pos, nav.pos)
    dist_err = clamp(distance / JUMP_RANGE_KLIK, 0, 1)
    head_err = clamp(
        abs(bearing_diff(ship.heading, bearing(ship.pos, nav.pos))) / 180.0, 0, 1
    )
    if ship.speed <= 0.01:
        vel_err = 1.0
    else:
        sv = _contact_vel(ship.pos.z, ship.heading, ship.speed)
        rx, ry = nav.pos.x - ship.pos.x, nav.pos.y - ship.pos.y
        span = math.hypot(rx, ry) or 1.0
        closing = (sv.x * rx + sv.y * ry) / span
        vel_err = clamp(1.0 - max(0.0, closing) / ship.speed, 0, 1)
    quality = 1.0 - (0.5 * dist_err + 0.3 * head_err + 0.2 * vel_err)
    # You cannot align onto a point you are not sure where you are.
    quality *= 1.0 - NAV_ALIGN_ERROR_PENALTY * clamp(
        ship.navErrorKlik / JUMP_RANGE_KLIK, 0, 1
    )
    return clamp(quality, 0, 1)


def spool_jump(state: GameState, nav_id: str) -> None:
    """Start charging the jump drive: blind, slow, loud and vulnerable."""
    nav = next(
        (n for n in state.campaign.navPoints if n.id == nav_id and n.kind == "jump"),
        None,
    )
    if nav is None:
        return
    ship = state.ship
    if dist(ship.pos, nav.pos) > JUMP_RANGE_KLIK:
        log(
            state,
            "OPS",
            f"Too far to spool — close to within {int(JUMP_RANGE_KLIK)} klik of {nav.name}.",
            "warn",
        )
        state.seq += 1
        return
    if not jump_window_open(state, nav):
        log(state, "OPS", f"{nav.name} is closed — the window is not open.", "warn")
        state.seq += 1
        return
    spec = drive_spec(ship.drive)
    spool_cost = JUMP_SPOOL_FUEL_COST * float(spec.get("fuelMultiplier", 1.0))
    if ship.fuel < spool_cost:
        log(state, "OPS", "Not enough fuel to charge the jump drive.", "warn")
        state.seq += 1
        return
    ship.fuel = clamp(ship.fuel - spool_cost, 0, ship.fuelCapacity)
    add_exposure(state, JUMP_SPOOL_EXPOSURE, "jump drive spool — emission spike")
    state.jumpState = JumpState(
        navId=nav.id,
        name=nav.name,
        spooling=True,
        alignment=0.0,
        required=_jump_required(state, nav),
        startedAt=state.clock,
        windowOpen=True,
        outcome="spooling",
    )
    ship.activeSensor = False
    ship.emcon.radar = False
    ship.speed = min(ship.speed, JUMP_SPOOL_MAX_SPEED)
    ship.mode = "quiet"
    _apply_emission(ship)
    log(
        state,
        "OPS",
        f"Jump drive spooling for {nav.name}. The ship is blind, slow and loud; "
        "alignment builds as the vector cleans up.",
        "warn",
    )
    state.seq += 1


def _accrue_alignment(state: GameState, dt: float) -> None:
    """Alignment accrues like a firing solution while the drive spools."""
    js = state.jumpState
    if js is None or not js.spooling:
        return
    nav = next((n for n in state.campaign.navPoints if n.id == js.navId), None)
    if nav is None:
        state.jumpState = None
        return
    js.required = _jump_required(state, nav)
    js.windowOpen = jump_window_open(state, nav)
    spec = drive_spec(state.ship.drive)
    rate = (
        JUMP_ALIGN_RATE_PER_MIN
        * alignment_quality(state, nav)
        * _jump_skill_factor(state)
        * (1.0 - _jump_interference(state, nav))
        * float(spec.get("spoolRate", 1.0))
    )
    js.alignment = clamp(js.alignment + max(0.0, rate) * dt, 0, 1)
    js.ready = js.alignment >= js.required
    # The drive is a beacon: recompute self-noise with the spool term so it
    # does not compound across steps.
    base = clamp(state.ship.emission if state.ship.emission > 0 else 0.4, 0, 1)
    base *= EMISSION_MODE_FACTOR.get(state.ship.mode, 1.0)
    state.ship.selfNoise = clamp(base + JUMP_SPOOL_NOISE, 0, 1)


def commit_jump(state: GameState) -> None:
    """Engage the drive: a clean jump, a misjump, or a refusal."""
    js = state.jumpState
    if js is None or not js.spooling:
        return
    nav = next((n for n in state.campaign.navPoints if n.id == js.navId), None)
    if nav is None:
        state.jumpState = None
        return
    if not jump_window_open(state, nav):
        js.outcome = "refused"
        log(state, "OPS", f"Commit refused — {nav.name} is closed.", "warn")
        state.seq += 1
        return
    spec = drive_spec(state.ship.drive)
    floor = float(spec.get("misjumpFloor", JUMP_MISJUMP_FLOOR))
    required = _jump_required(state, nav)
    if js.alignment < floor:
        js.outcome = "refused"
        log(
            state,
            "OPS",
            f"Commit refused — alignment {_round(js.alignment * 100)}% is below the "
            f"{_round(floor * 100)}% floor of the {spec.get('name', 'drive')}; it will not engage.",
            "warn",
        )
        state.seq += 1
        return
    ship = state.ship
    commit_cost = JUMP_COMMIT_FUEL_COST * float(spec.get("fuelMultiplier", 1.0))
    if ship.fuel < commit_cost:
        js.outcome = "refused"
        log(state, "OPS", "Commit refused — not enough fuel remains for the jump.", "warn")
        state.seq += 1
        return
    ship.fuel = clamp(ship.fuel - commit_cost, 0, ship.fuelCapacity)
    ship.waypoints = []
    if js.alignment < required:
        offset = (required - js.alignment) * 40.0
        ship.core = clamp(ship.core + JUMP_MISJUMP_DAMAGE / _size_class(ship), 0, 100)
        state.clock += JUMP_MISJUMP_DELAY_MIN
        if nav.dest is not None:
            ship.pos = Vec(x=nav.dest.x + offset, y=nav.dest.y + offset, z=nav.dest.z)
        else:
            ship.pos = Vec(x=ship.pos.x + offset, y=ship.pos.y - offset, z=ship.pos.z)
        js.spooling = False
        js.outcome = "misjump"
        log(
            state,
            "OPS",
            f"MISJUMP — the drive fires off-axis at {_round(js.alignment * 100)}% of the "
            f"{_round(required * 100)}% needed. The ship arrives wrong, late and hurt.",
            "danger",
        )
    else:
        js.spooling = False
        js.outcome = "jumped"
        if nav.dest is not None:
            ship.pos = Vec(x=nav.dest.x, y=nav.dest.y, z=nav.dest.z)
            award_career(state, 30, 2.0, "clean jump")
            log(state, "OPS", f"Jump complete — clean transit to {nav.name}.", "ok")
        else:
            log(state, "OPS", f"Jump complete — extraction from {nav.name}.", "ok")
            state.status = "ended"
            state.outcome = "jumped"
            state.outcomeAt = state.clock
    state.seq += 1


def abort_jump(state: GameState) -> None:
    """Stand the drive down: the charge and the fuel are gone."""
    js = state.jumpState
    if js is None or not js.spooling:
        return
    js.spooling = False
    js.outcome = "aborted"
    log(state, "OPS", "Jump spool aborted — charge lost, the fuel is spent.", "warn")
    state.seq += 1


def create_state(
    channel_id: str,
    instance_id: str,
    campaign: CampaignSeed,
    ship_id: str | None = None,
) -> GameState:
    center = campaign.patrol.center
    klass = ship_class(ship_id or campaign.shipClass)
    ship = ShipState(
        name=ship_name(klass.id),
        registry="CC-112",
        pos=Vec(x=center.x, y=center.y, z=0),
        heading=45,
        # The ship is under way on her cruise setting from the start; the speed
        # dial orders an actual speed and the mode names the bucket it falls in.
        speed=klass.cruiseSpeed,
        cruiseSpeed=klass.cruiseSpeed,
        quietSpeed=SILENT_KPS,
        maxSpeed=klass.maxSpeed,
        waypoints=_patrol_route(center, campaign.patrol.radiusKlik),
        emcon=DEFAULT_EMCON.model_copy(),
        mode="cruise",
        condition="yellow",
        roe="safe",
        exposure=8,
        readiness=92,
        hull=100,
        battery=100,
        sensorQuality=klass.sensorQuality,
        selfNoise=klass.emission,
        altTarget=0,
        shipClass=klass.id,
        profile=klass.profile,
        stealth=klass.stealth,
        emission=klass.emission,
        massKt=klass.massKt,
        buoyCount=SENSOR_BUOY_LOADOUT,
        noisemakers=NOISEMAKER_LOADOUT,
        className=klass.name,
    )
    _apply_emission(ship)
    _init_defences(ship, klass)

    seats = _seat_defaults()

    contacts: list[Contact] = []
    used_names: set[str] = set()
    for i, t in enumerate(campaign.contacts):
        contact = instantiate_contact(t, i, campaign, used_names=used_names)
        if contact.trueName:
            used_names.add(contact.trueName)
        contacts.append(contact)

    state = GameState(
        schemaVersion=STATE_SCHEMA_VERSION,
        room=RoomRef(channelId=channel_id, instanceId=instance_id),
        campaign=campaign,
        ship=ship,
        seats=seats,
        contacts=contacts,
        events=[],
        war=WarState(
            tension=campaign.escalation,
            phase=phase_name(campaign.escalation),
            frontLine=50,
        ),
        log=[],
        clock=campaign.startHour * 60,
        status="lobby",
        hostId=None,
        handoffPack=None,
        digest=None,
        autoTick=False,
        noise=NOISE_INIT,
        seq=0,
        buoys=[],
        noisemakerTurns=0,
        outcome=None,
        outcomeAt=None,
        escalationLevel=_phase_level(campaign.escalation),
    )
    state.ship.shieldRegenAt = state.clock + SHIELD_REGEN_INTERVAL_MIN
    _update_transit(state)
    _update_environment(state)
    state.moduleCatalog = list(MODULES)
    refresh_plot(state)
    state.commsOpen = comms_window_open(state)
    state.commsNote = "relay window open" if state.commsOpen else "window closed"
    return state


def _seat_defaults() -> dict[SeatId, Seat]:
    return {
        "command": Seat(
            id="command", title="Command", hats=["ops", "dc"], player=None, primary=True
        ),
        "ops": Seat(id="ops", title="Ops", hats=["nav", "ops", "dc"], player=None, primary=False),
        "sensor": Seat(
            id="sensor",
            title="Sensors & EW",
            hats=["sensors", "ew", "dc"],
            player=None,
            primary=False,
        ),
        "comms": Seat(
            id="comms",
            title="Comms & Weapons",
            hats=["comms", "weapons", "dc"],
            player=None,
            primary=False,
        ),
    }


def _military_pool(type: ContactType) -> list[str]:
    if type == "capship":
        return CAPSHIP_CLASSES
    if type == "fighter":
        return FIGHTER_CLASSES
    return ESCORT_CLASSES


# Terrain names — fields and clouds are charted places, not vessels, so they
# borrow from the local survey instead of the ship-name pools.
ASTEROID_FIELD_NAMES = (
    "Kepler Shelf",
    "Tannhauser Rocks",
    "Vega Scarp",
    "Bellamy Shoal",
    "Dresden Rubble",
)
NEBULA_NAMES = (
    "Nyx Veil",
    "Cygnus Drift",
    "Amber Halo",
    "Vela Curtain",
    "Kali's Breath",
)
DEBRIS_NAMES = (
    "Harrow Wreckline",
    "Boneyard Alpha",
    "Shatter Belt",
    "Graveyard Orbit",
    "Cold Hulk Field",
)
DUST_NAMES = (
    "Chaff Drift",
    "Ochre Haze",
    "Meridian Dust",
    "Slow Silt",
    "Grey Curtain",
)
ICE_NAMES = (
    "Vega Ice Shelf",
    "Glass Shoal",
    "Halo Rime",
    "Frozen Lattice",
    "White Mirror",
)


def environmental_name(t: ContactType, i: int) -> str:
    pool = {
        "asteroid": ASTEROID_FIELD_NAMES,
        "nebula": NEBULA_NAMES,
        "debris": DEBRIS_NAMES,
        "dust": DUST_NAMES,
        "ice": ICE_NAMES,
    }[t if t in ENVIRONMENTAL_TYPES else "debris"]
    return pool[i % len(pool)]


def _terrain_bands(contact_type: ContactType) -> list[float]:
    """Terrain has a broad, lumpy frequency profile of its own."""
    seed = sum(ord(ch) for ch in contact_type) or 11
    return [round(hash_random(seed, i + 1) * 0.6, 3) for i in range(FREQ_BANDS)]


def instantiate_contact(
    t: ContactTemplate,
    i: int,
    campaign: CampaignSeed,
    track_number: int | None = None,
    used_names: set[str] | None = None,
) -> Contact:
    hostile = t.hostile
    terrain = t.type in ENVIRONMENTAL_TYPES
    if terrain:
        true_name = environmental_name(t.type, i)
    elif t.type in ("escort", "capship", "fighter"):
        true_name = military_name(_military_pool(t.type), i + 1, used_names)
    else:
        true_name = vessel_name(i + 3)
    # The plot shows an anonymous designation until the track is CONFIRMED;
    # ``trueName`` is released by ``_reveal_contact`` at that point.
    name = f"TRACK-{(track_number if track_number is not None else i + 1):02d}"
    z_band = campaign.zBand if campaign.zBand is not None else ZBand(min=0, max=8)
    z = (
        t.z
        if t.z is not None
        else clamp(
            z_band.min + hash_random(i, 3) * (z_band.max - z_band.min),
            z_band.min,
            z_band.max,
        )
    )
    if terrain:
        ship_id = ""
        profile = 0.0
        stealth = 0.0
        emission = 0.15 if t.type == "nebula" else 0.05
        mass = MASS_KT[t.type]
        radius = (
            t.radiusKlik
            if t.radiusKlik is not None
            else OBSTACLE_RADIUS.get(t.type, 8.0)
        )
        frequency = _terrain_bands(t.type)
        image = TERRAIN_IMAGES.get(t.type, "")
        vdu = ""
        sensor_quality = 0.0
    else:
        klass = ship_for_type(t.type, t.shipClass)
        ship_id = klass.id
        profile = klass.profile
        stealth = klass.stealth
        emission = klass.emission
        mass = klass.massKt
        radius = 0.0
        frequency = list(klass.bands)
        image = klass.image
        vdu = klass.vdu
        sensor_quality = klass.sensorQuality
    return Contact(
        id=f"c{campaign.id}-{i}",
        name=name,
        trueName=true_name,
        trueType=t.type,
        faction=t.faction,
        hostile=hostile,
        pos=Vec(x=t.x, y=t.y, z=z),
        heading=t.heading,
        speed=t.speed,
        state="unknown",
        confidence=0,
        guess="unknown",
        firstSeen=0,
        lastSeen=0,
        seenCount=0,
        bearingHistory=[],
        estimated=None,
        emitting=t.emitting,
        detected=False,
        everDetected=False,
        signal=0,
        signature=NEUTRAL_SIGNATURE_SET[
            math.floor(hash_random(i, 5) * len(NEUTRAL_SIGNATURE_SET))
        ],
        waveform=Waveform(progress=0, resolved=False),
        massKt=mass,
        gravRead=None,
        shipClass=ship_id,
        profile=profile,
        stealth=stealth,
        emission=emission,
        sensorQuality=sensor_quality,
        radiusKlik=radius,
        frequencyProfile=frequency,
        image=image,
        vdu=vdu,
        sensor=SensorReadout(),
    )


def log(state: GameState, source: str, text: str, type: LogEntryType = "info") -> None:
    log_id = max((entry.id for entry in state.log), default=0) + 1
    state.log.append(LogEntry(id=log_id, time=state.clock, type=type, source=source, text=text))
    state.seq += 1
    if len(state.log) > 400:
        del state.log[: len(state.log) - 400]


def _cooldown(state: GameState, action: str, duration: float) -> bool:
    ready = state.cooldowns.get(action, 0.0)
    if state.clock < ready:
        log(state, "COMMAND", f"{action} cooling down — ready in {_round(ready - state.clock)} min.", "warn")
        return False
    state.cooldowns[action] = state.clock + duration
    return True


# ---------------------------------------------------------------------------
# Time advance
# ---------------------------------------------------------------------------


def advance(state: GameState, minutes: float) -> None:
    if state.status != "running":
        return
    if state.timeFrozen:
        log(state, "COMMAND", "Time is frozen by the GM — advance held.", "warn")
        return
    minutes = max(0.0, minutes)
    steps = max(1, _round(minutes / BEARING_DRIFT_MINUTES))
    step_minutes = minutes / steps if minutes else 0.0
    for _ in range(steps):
        _step_sim(state, step_minutes)
        if state.outcome is not None:
            break
    _finalize_step(state, minutes)
    _tick_noisemaker(state)


def set_time_frozen(state: GameState, frozen: bool) -> None:
    """GM holds the clock (e.g. while dragging pieces on the tactical map)."""
    if state.timeFrozen == frozen:
        return
    state.timeFrozen = frozen
    state.seq += 1
    log(
        state,
        "COMMAND",
        "GM FREEZES time — no advance until released."
        if frozen
        else "GM releases the clock — time runs again.",
        "warn" if frozen else "ok",
    )


def _step_sim(state: GameState, dt: float) -> None:
    state.clock += dt
    h = dt / 60
    _step_noise(state, dt)
    before = state.ship.pos
    _move_ship(state, h)
    _update_barriers(state, before)
    # Gravidar needs the array to be making way *during* this step, even if the
    # ship arrives at its final waypoint and stops before the step ends.
    made_way = flat_dist(before, state.ship.pos) > 0.01
    for c in state.contacts:
        _move_contact(state, c, h)
        # Remember whether this hostile ever came inside the disengage envelope:
        # the "made it through" win needs a threat that actually approached.
        if c.hostile and dist(state.ship.pos, c.pos) <= DISENGAGE_RANGE_KLIK:
            c.everNear = True
        _passive_detect(state, c, dt)
        _visual_detect(state, c, dt)
        # The other half of the race: they are listening for us too.
        _enemy_detect(state, c, dt)
    # Deployed buoys are a second passive origin, independent of the ship.
    _buoy_detect(state, dt)
    # The fit runs together: passive and EM are always on, gravidar runs while
    # making way, active radar only when the crew keys it.
    _gravidar_detect(state, made_way)
    _active_detect(state)
    _em_detect(state)
    _decay_contacts(state, dt)
    _drift(state, h)
    _spend_systems(state, h)
    _burn_fuel(state, dt)
    _update_transit(state)
    _regen_shields(state, dt)
    _accrue_wear(state, dt)
    _update_cpa(state)
    _check_nav_arrival(state)
    refresh_plot(state)
    _accrue_alignment(state, dt)
    _accrue_nav_error(state, dt)
    _update_comms_window(state)
    _update_datums(state, dt)
    _update_layer(state)
    _update_tma(state, dt)
    _hunters_move(state, dt)
    _update_ordnance(state, dt)
    _update_heat(state, dt)
    _update_watch(state, dt)
    _update_environment(state)
    _spend_provisions(state, dt)
    _contamination_watch(state, dt)
    _fire_scheduled(state)


# The background noise floor accumulates faster than linearly while you stay on
# watch (PLAN.md: X^2). Own emissions feed it; the floor buries weak signals.
def _step_noise(state: GameState, dt: float) -> None:
    rate = state.campaign.noiseRate if state.campaign.noiseRate is not None else NOISE_DEFAULT_RATE
    hazard_noise = sum(
        h.noise * h.intensity
        for h in state.campaign.hazards
        if h.startMinute <= state.clock
        and (h.endMinute is None or state.clock <= h.endMinute)
    )
    total = (rate + hazard_noise) * dt * dt + state.ship.selfNoise * SELF_NOISE_BURDEN * dt
    state.noise = clamp(state.noise + total, NOISE_MIN, NOISE_CAP)


def _finalize_step(state: GameState, minutes: float) -> None:
    _expire_events(state)
    if state.outcome is None:
        _check_patrol_win(state)
    if state.outcome is None:
        incoming = _engagement_candidates(state)
        if incoming is not None:
            state.events.append(incoming)
            state.seq += 1
    state.seq += 1
    state.war.phase = phase_name(state.war.tension)
    if state.outcome is None:
        _escalate(state)


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------


# A waypoint this close (klik) counts as reached on arrival.
WAYPOINT_ARRIVE_KLIK = 1.1
# Kept as a local alias so the movement math reads in one place.
_KLIK_PER_KPS_HOUR = KLIK_PER_KPS_HOUR


def _advance(p: Vec, heading: float, distance: float) -> Vec:
    """Step ``distance`` klik along a compass course, horizontally."""
    rad = math.radians(heading)
    return Vec(x=p.x + math.sin(rad) * distance, y=p.y + math.cos(rad) * distance, z=p.z)


def env_factor(state: GameState, attr: str, default: float = 1.0) -> float:
    """A named multiplier from the environment the ship is in."""
    return float(getattr(environment_spec(state.environment), attr, default))


def _update_environment(state: GameState) -> None:
    """The environment is the active hazard's kind, else the scenario's."""
    active = [
        h
        for h in state.campaign.hazards
        if h.startMinute <= state.clock
        and (h.endMinute is None or state.clock <= h.endMinute)
    ]
    if active:
        strongest = max(active, key=lambda h: h.intensity)
        env_id = environment_for_hazard(strongest.type)
        note = strongest.title
    else:
        env_id = state.campaign.environment or "clear-space"
        note = environment_spec(env_id).name
    if env_id != state.environment:
        state.environment = env_id
        spec = environment_spec(env_id)
        log(
            state,
            "OPS",
            f"Entering {spec.name} — {spec.note}",
            "warn" if env_id != "clear-space" else "info",
        )
    state.environmentNote = note


def _spend_provisions(state: GameState, dt: float) -> None:
    ship = state.ship
    if ship.provisions > 0:
        ship.provisions = max(0.0, ship.provisions - dt / 60.0)
        return
    # No provisions: the watch tires faster and morale frays.
    ship.fatigue = clamp(ship.fatigue + 1.0 * (dt / 60.0), 0, 100)
    if int(state.clock) % 180 == 0:
        log(state, "COMMAND", "Provisions are exhausted — the crew is running on fumes.", "warn")


def _contamination_watch(state: GameState, dt: float) -> None:
    """A contaminated fault recurs until it is cleaned."""
    for name, system in state.ship.systems.items():
        if not system.contaminated or system.malfunctioning:
            continue
        chance = CONTAMINATION_CHANCE_PER_HOUR * (dt / 60.0)
        if hash_random(state.clock, _id_salt(name) + 950) < chance:
            system.malfunctioning = True
            log(
                state,
                "DC",
                f"{name} fails again — {system.contaminated} still in it.",
                "warn",
            )


def salvage_spares(state: GameState) -> None:
    """Go outside in a debris field and cut spares free."""
    spec = environment_spec(state.environment)
    if not spec.salvage:
        log(state, "DC", "Nothing to salvage here — this is not a debris field.", "warn")
        state.seq += 1
        return
    result = station_check(
        state, "Damage Control", difficulty("routine"), action="salvage"
    )
    add_exposure(state, 8, "EVA salvage")
    if spec.evaRisk:
        state.ship.crewStrength = clamp(state.ship.crewStrength - EVA_COLD_INJURY, 0, 100)
    if result.success:
        gained = 1 + max(0, result.degree // 5)
        state.ship.spares = min(SALVAGE_SPARES_MAX, state.ship.spares + gained)
        log(state, "DC", f"Salvage recovered — {gained} spare(s) aboard.", "ok")
    else:
        log(state, "DC", "The salvage drifted away from the manipulator.", "warn")
    state.seq += 1


def replenish(state: GameState) -> None:
    """Take on fuel, spares and provisions at a depot."""
    near = next(
        (
            n
            for n in state.campaign.navPoints
            if n.kind == "body" and dist(state.ship.pos, n.pos) <= n.radiusKlik + 8
        ),
        None,
    )
    if near is None:
        log(state, "OPS", "No depot in range to replenish from.", "warn")
        state.seq += 1
        return
    ship = state.ship
    ship.fuel = ship.fuelCapacity
    ship.spares = max(ship.spares, SPARES_LOADOUT)
    ship.provisions = PROVISIONS_HOURS
    log(state, "OPS", f"Replenished alongside {near.name} — fuel, spares and provisions.", "ok")
    state.seq += 1


def _init_loadout(ship: ShipState, klass: ShipClass) -> None:
    """Fit the hull's mounts and set the module budgets it can spend."""
    entry = hull_entry(klass.id)
    ship.hardpoints = default_loadout(klass.id)
    ship.powerBudget = 6.0 + klass.body / 40.0
    ship.massBudgetKt = max(4.0, klass.massKt * 0.5)
    ship.cargoCapacity = float(entry.get("cargoHold") or 0.0)
    ship.modules = []
    ship.livery = ship.livery or ""


def _apply_module_fit(state: GameState) -> None:
    """Recompute hull stats from the fitted modules."""
    ship = state.ship
    klass = ship_class(ship.shipClass)
    shield_mult = module_multiplier(ship.modules, "shieldMultiplier")
    mid = (klass.shieldFore + klass.shieldAft) / 2
    base_shields = {
        "fore": klass.shieldFore,
        "aft": klass.shieldAft,
        "port": mid,
        "starboard": mid,
    }
    for arc_id, arc in ship.shields.items():
        arc.max = base_shields.get(arc_id, mid) * shield_mult
        arc.shp = min(arc.shp, arc.max)
    armor_mult = module_multiplier(ship.modules, "armorMultiplier")
    ship.armor = {
        "fore": klass.armorFore * armor_mult,
        "aft": klass.armorAft * armor_mult,
        "port": klass.armorPort * armor_mult,
        "starboard": klass.armorStarboard * armor_mult,
    }
    ship.fuelCapacity = (
        klass.fuelCapacity or ALERT_FUEL_CAPACITY
    ) + module_sum(ship.modules, "fuelBonus")
    ship.fuel = min(ship.fuel, ship.fuelCapacity)
    ship.spares = SPARES_LOADOUT + int(module_sum(ship.modules, "sparesBonus"))
    ship.sensorQuality = clamp(
        klass.sensorQuality + module_sum(ship.modules, "sensorBonus"), 0, 1
    )


def fit_module(state: GameState, module_id: str) -> None:
    """Fit an accessory if the hull's power, mass and cargo budgets allow."""
    spec = module_spec(module_id)
    if spec is None:
        return
    ship = state.ship
    if module_id in ship.modules:
        return
    proposed = ship.modules + [module_id]
    if not within_budgets(
        proposed, ship.powerBudget, ship.massBudgetKt, ship.cargoCapacity
    ):
        totals = module_totals(proposed)
        log(
            state,
            "DC",
            f"Cannot fit {spec.name} — that would need {int(totals['power'])} power, "
            f"{int(totals['massKt'])} kt and {int(totals['cargo'])} cargo; the hull "
            f"budgets {int(ship.powerBudget)}, {int(ship.massBudgetKt)} and "
            f"{int(ship.cargoCapacity)}.",
            "warn",
        )
        state.seq += 1
        return
    ship.modules = proposed
    _apply_module_fit(state)
    log(state, "DC", f"Fitted {spec.name}. {spec.note}", "ok")
    state.seq += 1


def unfit_module(state: GameState, module_id: str) -> None:
    """Strip an accessory back out; the budgets come back with it."""
    ship = state.ship
    if module_id not in ship.modules:
        return
    ship.modules = [m for m in ship.modules if m != module_id]
    _apply_module_fit(state)
    log(state, "DC", f"Stripped {module_id} back out.", "info")
    state.seq += 1


def launch_small_craft(state: GameState) -> None:
    """Open the hangar and put a craft out: useful, and a window of vulnerability."""
    ship = state.ship
    if ship.smallCraftAway:
        log(state, "OPS", "The small craft is already away.", "warn")
        state.seq += 1
        return
    result = station_check(
        state, "Starship Piloting", difficulty("routine"), action="hangar"
    )
    ship.hangarOpenUntil = state.clock + HANGAR_OPEN_MIN
    add_exposure(state, HANGAR_OPEN_EXPOSURE, "hangar door open")
    if result.success:
        ship.smallCraftAway = True
        log(
            state,
            "OPS",
            "Small craft away. The door is open and the parent is vulnerable until "
            "it is recovered.",
            "ok",
        )
    else:
        log(state, "OPS", "Launch aborted on the deck — the door was open for nothing.", "warn")
    state.seq += 1


def recover_small_craft(state: GameState) -> None:
    """Bring the craft back aboard; the window closes."""
    ship = state.ship
    if not ship.smallCraftAway:
        log(state, "OPS", "Nothing to recover.", "warn")
        state.seq += 1
        return
    result = station_check(
        state, "Starship Piloting", difficulty("routine"), action="hangar"
    )
    if result.success:
        ship.smallCraftAway = False
        ship.hangarOpenUntil = 0.0
        log(state, "OPS", "Small craft recovered and the door sealed.", "ok")
    else:
        log(state, "OPS", "Recovery wave-off — the craft is still out there.", "warn")
    state.seq += 1


def board_prize(state: GameState, contact_id: str) -> None:
    """Put a party aboard a derelict or prize: spares, or casualties."""
    c = next((x for x in state.contacts if x.id == contact_id), None)
    if c is None or not c.everDetected:
        return
    if c.hostile and c.confidence > 0.5:
        log(state, "COMMS", f"{c.name} is still fighting — no boarding action.", "warn")
        state.seq += 1
        return
    result = station_check(
        state, "Security", difficulty("hard"), action="board", contact_id=c.id
    )
    if result.success:
        gained = 1 + max(0, result.degree // 5)
        state.ship.spares = min(SALVAGE_SPARES_MAX, state.ship.spares + gained)
        award_career(state, 15, 1.0, "prize taken")
        log(state, "COMMS", f"Boarding party away aboard {c.name} — {gained} spare(s) recovered.", "ok")
    else:
        state.ship.crewStrength = clamp(state.ship.crewStrength - 6.0, 0, 100)
        log(state, "COMMS", f"The boarding action on {c.name} went badly — casualties.", "danger")
    state.seq += 1


def _update_barriers(state: GameState, before: Vec) -> None:
    """A picket line is a detection event, not an instant loss."""
    ship = state.ship
    for line in state.campaign.barriers:
        if line.id in state.barriersCrossed:
            continue
        if not segments_intersect(before, ship.pos, line.a, line.b):
            continue
        # A hull running quiet (or drifting) can slip a *thin* line; a loud
        # ship, or a thick line, always hears it.
        quiet = ship.mode == "quiet" or state.posture == "drift"
        if quiet and line.sensitivity < 0.5:
            log(
                state,
                "SENSORS",
                f"Slipped the {line.name} quietly — the line never heard us.",
                "ok",
            )
            state.barriersCrossed.append(line.id)
            continue
        state.barriersCrossed.append(line.id)
        state.barrierAlert = True
        state.barrierAlertUntil = state.clock + BARRIER_ALERT_MIN
        place_datum(state, f"crossed the {line.name}")
        log(
            state,
            "EW",
            f"PICKET LINE — we have crossed the {line.name}. The line has us and "
            "the datum is live.",
            "danger",
        )
    if state.barrierAlert and state.clock >= state.barrierAlertUntil:
        state.barrierAlert = False
        log(state, "EW", "The picket line has lost us again.", "info")


def heat_load_per_hour(state: GameState) -> float:
    """Heat the ship is making right now, from every system drawing power."""
    ship = state.ship
    load = HEAT_BASE_PER_HOUR
    if ship.activeSensor:
        load += HEAT_SENSOR_ACTIVE
    load += HEAT_ALERT.get(ship.alert, 0.0)
    if ship.weaponsState in ("armed", "locked"):
        load += HEAT_WEAPONS
    if state.jumpState is not None and state.jumpState.spooling:
        load += HEAT_SPOOL
    return load


def set_heat_mode(state: GameState, mode: str) -> None:
    """Normal circulation, a fast-and-loud vent, or quiet bottling."""
    if mode not in ("normal", "vent", "bottle"):
        return
    state.ship.heatMode = mode  # type: ignore[assignment]
    label = {"normal": "Normal circulation", "vent": "VENTING — fast and loud", "bottle": "BOTTLED — quiet and hot"}[mode]
    log(
        state,
        "DC",
        f"{label}."
        + (" Everyone watching can see the plume." if mode == "vent" else "")
        + (" Heat will climb, and so will the strain." if mode == "bottle" else ""),
        "warn" if mode != "normal" else "info",
    )
    state.seq += 1


def _update_heat(state: GameState, dt: float) -> None:
    """Heat is capability: run hot and the ship fights worse."""
    ship = state.ship
    hours = dt / 60.0
    ship.heat = clamp(ship.heat + heat_load_per_hour(state) * hours, 0, HEAT_CRITICAL)
    if ship.heat >= HEAT_CRITICAL and ship.heatMode != "vent":
        # The plant dumps heat whether you like it or not.
        ship.heat = HEAT_PENALTY_AT
        add_exposure(state, HEAT_VENT_EXPOSURE, "automatic heat vent")
        log(
            state,
            "DC",
            "HEAT CRITICAL — the plant vents automatically. Everyone saw that.",
            "danger",
        )
    if ship.heatMode == "vent":
        ship.heat = clamp(ship.heat - HEAT_VENT_PER_HOUR * hours, 0, HEAT_CRITICAL)
        add_exposure(state, HEAT_VENT_EXPOSURE * hours, "heat vent — visible plume")
    else:
        rate = (
            HEAT_BOTTLE_DISSIPATION
            if ship.heatMode == "bottle"
            else HEAT_DISSIPATION_PER_HOUR
        )
        ship.heat = clamp(ship.heat - rate * hours, 0, HEAT_CRITICAL)
        if ship.heatMode == "bottle":
            ship.selfNoise = clamp(ship.selfNoise - HEAT_BOTTLE_NOISE_RELIEF, 0, 1)



def heat_penalty(state: GameState) -> int:
    """d20 penalty the crew is carrying from heat."""
    heat = state.ship.heat
    if heat < HEAT_PENALTY_AT:
        return 0
    span = HEAT_CRITICAL - HEAT_PENALTY_AT
    return int(
        clamp(round((heat - HEAT_PENALTY_AT) / span * HEAT_PENALTY_MAX), 0, HEAT_PENALTY_MAX)
    )


def set_watch_bill(state: GameState, bill: str) -> None:
    """Standard rotation, everyone closed up, or the crew stood down."""
    if bill not in ("standard", "battle", "rest"):
        return
    state.ship.watchBill = bill  # type: ignore[assignment]
    log(
        state,
        "COMMAND",
        {
            "standard": "Watch bill: standard rotation (six on, twelve off).",
            "battle": "Watch bill: battle stations — everyone closed up, and everyone tires.",
            "rest": "Watch bill: crew stood down to rest; the watch is thin.",
        }[bill],
        "info",
    )
    state.seq += 1


def _update_watch(state: GameState, dt: float) -> None:
    """Fatigue builds on watch and recovers when the crew is stood down."""
    ship = state.ship
    rate = FATIGUE_PER_HOUR.get(ship.watchBill, 2.0)
    ship.fatigue = clamp(ship.fatigue + rate * (dt / 60.0), 0, 100)


def fatigue_penalty(state: GameState) -> int:
    fatigue = state.ship.fatigue
    if fatigue < FATIGUE_PENALTY_AT:
        return 0
    return int((fatigue - FATIGUE_PENALTY_AT) // FATIGUE_PENALTY_DIVISOR)


def state_check_penalty(state: GameState) -> tuple[int, str]:
    """Total d20 penalty the crew carries, and why."""
    penalty = heat_penalty(state) + fatigue_penalty(state)
    reasons: list[str] = []
    if heat_penalty(state):
        reasons.append("heat")
    if fatigue_penalty(state):
        reasons.append("fatigue")
    if state.ship.shaken:
        penalty += SHAKEN_PENALTY
        reasons.append("shaken")
    if state.ship.crewStrength < UNDERMANNED_CREW:
        penalty += UNDERMANNED_PENALTY
        reasons.append("undermanned")
    return penalty, ", ".join(reasons)


def shock_crew(state: GameState, why: str) -> None:
    """A hard hit shakes the crew until someone rallies them."""
    if state.ship.shaken:
        return
    state.ship.shaken = True
    log(
        state,
        "COMMAND",
        f"The crew is SHAKEN ({why}) — every station works at a penalty until "
        "someone rallies them.",
        "danger",
    )


def rally_crew(state: GameState) -> None:
    """Command's Inspire Check to settle a shaken crew."""
    result = station_check(
        state, "Inspire", difficulty(RALLY_DC_NAME), action="rally"
    )
    if result.success:
        state.ship.shaken = False
        state.ship.fatigue = clamp(state.ship.fatigue - 10, 0, 100)
        log(state, "COMMAND", "The crew settles — shaken cleared.", "ok")
    else:
        log(state, "COMMAND", "The words did not land — the crew is still shaken.", "warn")
    state.seq += 1


def subsystem_damage_factor(state: GameState, arc: str = "fore") -> float:
    """How much damage actually reaches a system, by defence state.

    Shields up ÷100, armour intact ÷10, bare hull takes it full — the WCRPG
    subsystem rule, and the reason shields matter even to a system strike.
    """
    shield = state.ship.shields.get(arc)
    if shield is not None and shield.shp > 0:
        return SUBSYSTEM_SHIELD_FACTOR
    if state.ship.armor.get(arc, 0.0) > 0:
        return SUBSYSTEM_ARMOR_FACTOR
    return 1.0


def apply_subsystem_damage(
    state: GameState, amount: float, system: str, arc: str = "fore"
) -> None:
    """Damage one named system, scaled by the target's defence state."""
    target = state.ship.systems.get(system)
    if target is None:
        return
    dealt = float(amount) * subsystem_damage_factor(state, arc)
    if dealt <= 0:
        return
    target.health = clamp(target.health - dealt, 0, 100)
    if target.health <= 0:
        target.malfunctioning = True
        target.juryRigged = False
        log(state, "TAC", f"{system} is DOWN — subsystem hit.", "danger")
    state.seq += 1


def set_target_system(state: GameState, system: str) -> None:
    """Aim the prepped shot at a named system: a Targeting Check on the way in."""
    if system and system not in SHIP_SYSTEMS:
        return
    ship = state.ship
    ship.weaponTargetSystem = system
    if not system:
        log(state, "WEAPONS", "Subsystem targeting cleared — hull shot.", "info")
        state.seq += 1
        return
    c = next((x for x in state.contacts if x.id == ship.weaponTarget), None)
    target_hd = hull_hd(c.profile, c.stealth) if c is not None else 15
    result = station_check(
        state,
        "Targeting",
        difficulty(SUBSYSTEM_TARGET_DC_NAME) + max(0, target_hd - 15) // 2,
        action="targetSystem",
        contact_id=system,
    )
    ship.weaponTargetSystem = system if result.success else ""
    state.subsystemCheck = result
    log(
        state,
        "WEAPONS",
        f"Subsystem strike on {system}: Targeting {'succeeds' if result.success else 'fails'} "
        f"— the shot will hit the {'system' if result.success else 'hull'}.",
        "ok" if result.success else "warn",
    )
    state.seq += 1


def launch_ordnance(
    state: GameState,
    *,
    kind: str = "torpedo",
    pos: Vec | None = None,
    heading: float | None = None,
    speed: float = 40.0,
    warhead: float = ORDNANCE_WARHEAD,
    hostile: bool = True,
    name: str = "",
) -> Ordnance:
    """Put a weapon in the water; it flies, it can be killed, it can be spoofed."""
    ship = state.ship
    if pos is not None:
        origin = pos
    else:
        angle = hash_random(state.clock, len(state.ordnance) + 41) * 360.0
        origin = Vec(
            x=ship.pos.x + math.sin(math.radians(angle)) * ORDNANCE_DETECT_KLIK,
            y=ship.pos.y + math.cos(math.radians(angle)) * ORDNANCE_DETECT_KLIK,
            z=ship.pos.z,
        )
    flight = heading if heading is not None else bearing(origin, ship.pos)
    o = Ordnance(
        id=f"ord-{uuid.uuid4().hex[:12]}",
        kind="missile" if kind == "missile" else "torpedo",
        name=name or ("Inbound torpedo" if kind != "missile" else "Inbound missile"),
        pos=origin.model_copy(),
        heading=flight,
        speed=speed,
        fuelKlik=ORDNANCE_FUEL_KLIK,
        warhead=warhead,
        hostile=hostile,
    )
    state.ordnance.append(o)
    log(
        state,
        "TAC",
        f"ORDNANCE IN THE WATER — {o.name} launched at us. Track it, shoot it "
        "down, decoy it, or put terrain between us.",
        "danger",
    )
    state.seq += 1
    return o


def shoot_down_ordnance(state: GameState, ordnance_id: str) -> None:
    """A gun solution on an inbound weapon."""
    o = next((x for x in state.ordnance if x.id == ordnance_id and x.alive), None)
    if o is None:
        return
    result = station_check(
        state,
        "Targeting",
        difficulty(ORDNANCE_SHOOT_DC_NAME),
        action="ordnance",
        contact_id=o.id,
    )
    if result.success:
        o.alive = False
        state.ordnance = [x for x in state.ordnance if x.alive]
        log(state, "WEAPONS", f"{o.name} destroyed in flight.", "ok")
    else:
        log(state, "WEAPONS", f"Miss — {o.name} is still inbound.", "warn")
    state.seq += 1


def deploy_spoof(state: GameState) -> None:
    """Fire a spoofing pod: a good shot that beat the EHD may still miss."""
    ship = state.ship
    if ship.spoofPods <= 0:
        log(state, "EW", "No spoofing pods left.", "warn")
        state.seq += 1
        return
    result = station_check(
        state, "Ballistics", difficulty(SPOOF_DC_NAME), action="spoof"
    )
    ship.spoofPods -= 1
    if result.success:
        ship.spoofBonus = SPOOF_BONUS_PER_POD * max(1, result.degree // 5 + 1)
        ship.spoofActiveUntil = state.clock + SPOOF_DURATION_MIN
        log(
            state,
            "EW",
            f"Spoofing pod away — decoy up for {int(SPOOF_DURATION_MIN)} min "
            f"(+{ship.spoofBonus} against inbound weapons).",
            "ok",
        )
    else:
        log(state, "EW", "Spoofing pod failed to decoy — the pod is spent.", "warn")
    state.seq += 1


def _update_ordnance(state: GameState, dt: float) -> None:
    """Fly every weapon in the water and resolve what it does."""
    if not state.ordnance:
        return
    ship = state.ship
    survivors: list[Ordnance] = []
    for o in state.ordnance:
        if not o.alive:
            continue
        # Terrain: a weapon whose line of sight is blocked loses the lock.
        block, _scatter, _reflect = _obstacle_shadow(state, o)  # type: ignore[arg-type]
        if block > 0.6:
            log(state, "SENSORS", f"{o.name} lost the lock in terrain — it flies on.", "ok")
            continue
        target = ship.pos
        # A decoy pulls the weapon off us.
        if state.noisemakerTurns > 0 and o.hostile:
            target = Vec(x=ship.pos.x + 30, y=ship.pos.y + 30, z=ship.pos.z)
        want = bearing(o.pos, target)
        limit = ORDNANCE_TURN_RATE_DEG_PER_MIN * dt
        o.heading = wrap_bearing(o.heading + clamp(bearing_diff(want, o.heading), -limit, limit))
        step = o.speed * _KLIK_PER_KPS_HOUR * (dt / 60.0)
        o.fuelKlik = max(0.0, o.fuelKlik - step)
        o.pos = _advance(o.pos, o.heading, step)
        o.detected = dist(ship.pos, o.pos) <= ORDNANCE_DETECT_KLIK
        if o.fuelKlik <= 0:
            log(state, "SENSORS", f"{o.name} ran out of fuel and self-destructed.", "ok")
            continue
        if dist(o.pos, ship.pos) <= ORDNANCE_HIT_KLIK:
            # A live spoof can still make it miss.
            if ship.spoofBonus > 0 and state.clock < ship.spoofActiveUntil:
                if hash_random(state.clock, _id_salt(o.id) + 900) < SPOOF_DECOY_CHANCE:
                    log(
                        state,
                        "EW",
                        f"The spoof decoys {o.name} — it detonates on the decoy.",
                        "ok",
                    )
                    continue
            log(state, "TAC", f"{o.name} DETONATES on the hull.", "danger")
            apply_damage(state, o.warhead, "fore")
            continue
        survivors.append(o)
    state.ordnance = survivors


def _system_down(state: GameState, name: str) -> bool:
    system = state.ship.systems.get(name)
    return bool(system is not None and system.malfunctioning)


def _move_ship(state: GameState, h: float) -> None:
    ship = state.ship
    if _system_down(state, "engines") or ship.deadDrift:
        return
    # ``speed`` is the ordered speed on the 0-100 dial (set by nav:speed/nav:mode);
    # the named mode is only the bucket it falls in.
    kps = clamp(ship.speed, 0, ship.maxSpeed)
    remaining = kps * h * _KLIK_PER_KPS_HOUR
    # Consume waypoints *along* the step.  A 45-minute tick can cover more ground
    # than the gap between waypoints, so arrive exactly at each one and carry the
    # remainder into the next leg; otherwise the ship overshoots, turns around and
    # orbits a waypoint it can never sit still long enough to "reach".  Reaching
    # the final waypoint is arrival: hold station there rather than overflying it.
    while ship.waypoints and remaining > 1e-9:
        target = ship.waypoints[0]
        gap = flat_dist(ship.pos, target)
        if gap <= WAYPOINT_ARRIVE_KLIK:
            ship.waypoints.pop(0)
            continue
        ship.heading = bearing(ship.pos, target)
        leg = min(gap, remaining)
        ship.pos = _advance(ship.pos, ship.heading, leg)
        remaining -= leg
        if leg < gap:
            break
        ship.waypoints.pop(0)
    if ship.waypoints:
        ship.speed = kps
    else:
        # Arrived at the last waypoint (or holding with no orders set): stop.
        ship.speed = 0.0
    # Hold altitude toward the set target (climb/descend in the vertical).
    d_alt = ship.altTarget - ship.pos.z
    if abs(d_alt) > 1e-3:
        ship.pos.z += clamp(
            d_alt,
            -ALTITUDE_RATE_KLIK_PER_HOUR * h,
            ALTITUDE_RATE_KLIK_PER_HOUR * h,
        )
    ship.selfNoise = 0.0  # replaced immediately below by _apply_emission
    _apply_emission(ship)


def _apply_emission(ship: ShipState) -> None:
    """Own emission profile: overall self-noise plus the directional stern plume.

    A stopped ship still radiates (plant, life support).  Silent running is
    *quieter overall* than sitting still — the hull masks its plant — but the
    drive plume out the back is hotter than an idling ship's, and that plume
    dazzles your own aft sensors (see ``_passive_snr``).
    """
    base = clamp(ship.emission if ship.emission > 0 else 0.4, 0, 1)
    if ship.speed <= 0.01:
        ship.selfNoise = base
        ship.rearHeat = 0.0
        return
    ship.selfNoise = clamp(base * EMISSION_MODE_FACTOR.get(ship.mode, 1.0), 0, 1)
    ship.rearHeat = STERN_HEAT_BY_MODE.get(ship.mode, 0.5)


def _stern_dazzle(state: GameState, target: Contact) -> float:
    """How much of a target's signal your own stern plume washes out (0..1)."""
    rear = state.ship.rearHeat
    if rear <= 0:
        return 0.0
    true_b = bearing(state.ship.pos, target.pos)
    astern = abs(bearing_diff(true_b, wrap_bearing(state.ship.heading + 180)))
    if astern >= STERN_DAZZLE_ARC_DEG:
        return 0.0
    proximity = 1 - astern / STERN_DAZZLE_ARC_DEG
    return proximity * rear * STERN_DAZZLE_STRENGTH


def _mode_speed(mode: OperatingMode) -> float:
    return {"cruise": CRUISE_KPS, "quiet": SILENT_KPS, "max": FLANK_KPS}[mode]


def _mode_speed_for(ship: ShipState, mode: OperatingMode) -> float:
    """The hull's own anchor for a named mode.

    Catalog hulls currently share the 0-100 dial anchors, but routing this
    through the ship means a hull that is faster or quieter than the standard
    (set by the GM) actually flies that way.
    """
    return {
        "quiet": ship.quietSpeed,
        "cruise": ship.cruiseSpeed,
        "max": ship.maxSpeed,
    }[mode]


def _move_contact(state: GameState, c: Contact, h: float) -> None:
    # Hunters chase once they have a sniff of a track on us (a partial lock), not
    # merely because *we* have seen them.  Losing the scent — quiet running, a
    # crybaby — drops the lock and they resume their sweep.
    if (
        c.hostile
        and (c.hostileLock or c.lock > ENEMY_PURSUE_LOCK)
        and c.trueType in ("escort", "capship", "fighter")
        and state.war.tension > 30
    ):
        _hostile_pursuit(state, c)
    else:
        c.heading = wrap_bearing(c.heading + 0.15 * noise(len(c.id) + c.heading, 1.0))
    c.pos = moved(c.pos, c.heading, c.speed, h)


def _hostile_pursuit(state: GameState, c: Contact) -> None:
    b = bearing(c.pos, state.ship.pos)
    c.heading = wrap_bearing(c.heading + clamp(bearing_diff(b, c.heading), -2.2, 2.2))
    c.speed = clamp(c.speed, 30, max(c.speed, 80))


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def _reach(range: float, state: GameState) -> float:
    return (
        range
        * (1 - (state.ship.selfNoise * SELF_NOISE_SHADOW))
        * (0.75 + state.ship.sensorQuality * 0.35)
    )


TYPE_EASE: dict[ContactType, float] = {
    "unknown": 0.6,
    "prospector": 0.95,
    "freighter": 0.9,
    "liner": 0.85,
    "escort": 0.8,
    "capship": 0.5,
    "fighter": 0.72,
    "carrier": 0.5,
    # Terrain: cold rock is a poor passive return, a nebula screams on the
    # emission lines, and a debris field is faint and intermittent.  Dust and
    # ice are noisy scatterers rather than emitters.
    "asteroid": 0.35,
    "nebula": 0.7,
    "debris": 0.45,
    "dust": 0.4,
    "ice": 0.3,
}

# Passive detection. Every contact radiates a signature driven by its own
# ``emission`` masked by ``stealth``; emitters ride far above it. The probability
# of a bearing is driven by a signal-to-noise ratio that falls off with range AND
# as the X^2 background noise floor accumulates while you stay on watch.
EMISSION_BASE = 1.2


def _segment_distance(p: Vec, a: Vec, b: Vec) -> float:
    """Horizontal distance from point ``p`` to segment ``a-b`` (klik)."""
    dx, dy = b.x - a.x, b.y - a.y
    if dx == 0 and dy == 0:
        return math.hypot(p.x - a.x, p.y - a.y)
    t = clamp(((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy), 0, 1)
    return math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy))


def _obstacle_between(
    state: GameState, a: Vec, b: Vec, *, exclude: Contact | None = None
) -> tuple[float, float, float]:
    """Aggregate (block, scatter, reflect) for any line of sight ``a``→``b``.

    Generalises :func:`_obstacle_shadow` so an enemy's look at the ship, or a
    buoy's bearing on a contact, is occluded by the same terrain physics.
    """
    block = scatter = reflect = 0.0
    for o in state.contacts:
        if o is exclude:
            continue
        eff = OBSTACLE_EFFECTS.get(o.trueType)
        if eff is None:
            continue
        r = o.radiusKlik or OBSTACLE_RADIUS.get(o.trueType, 6.0)
        d = _segment_distance(o.pos, a, b)
        if d > r * OBSTACLE_LOS_INFLUENCE:
            continue
        w = clamp(1 - d / (r * OBSTACLE_LOS_INFLUENCE), 0, 1)
        block += eff.block * w
        scatter += eff.scatter * w
        reflect += eff.reflect * w
    return (clamp(block, 0, 1), clamp(scatter, 0, 1), clamp(reflect, 0, 1))


def _obstacle_shadow(state: GameState, target: Contact) -> tuple[float, float, float]:
    """Aggregate (block, scatter, reflect) from obstacles on the ship→target LOS.

    Obstacles near the ship-to-target bearing attenuate and distort the return;
    the influence falls off to zero at ``radius * OBSTACLE_LOS_INFLUENCE``.
    """
    return _obstacle_between(state, state.ship.pos, target.pos, exclude=target)


def _contact_loudness(c: Contact) -> float:
    """How brightly a contact burns on the passive grill (0..1)."""
    if c.trueType in ENVIRONMENTAL_TYPES:
        return clamp(c.emission, 0, 1)
    return clamp(c.emission * (1 - c.stealth), 0, 1)


def _passive_snr(state: GameState, c: Contact) -> float:
    ship = state.ship
    reach_klik = _reach(PASSIVE_BASE_RANGE_KLIK, state)
    d = dist(ship.pos, c.pos)
    if d > reach_klik:
        return 0
    block, _scatter, _reflect = _obstacle_shadow(state, c)
    c.sensor.obstructed = block
    ease = TYPE_EASE[c.trueType]
    loud = _contact_loudness(c)
    emitting_boost = 1.4 if c.emitting else 1.0
    closeness = clamp(1 - d / (reach_klik * 1.5), 0, 1)
    peak = (
        EMISSION_BASE
        * (0.3 + 1.7 * loud)
        * ease
        * emitting_boost
        * closeness
        * (1 - block)
        * env_factor(state, "sensor")
    )
    # Your own stern plume washes out anything sitting in the aft arc.
    peak *= 1 - _stern_dazzle(state, c)
    # The aft blind arc: nothing passive gets through until it is cleared.
    if state.clock > state.bafflesClearedUntil:
        astern = abs(
            bearing_diff(bearing(ship.pos, c.pos), wrap_bearing(ship.heading + 180))
        )
        if astern <= BAFFLE_ARC_DEG:
            peak *= BAFFLE_ATTENUATION
    # A crybaby floods your own receiver while it covers your escape.
    if state.noisemakerTurns > 0:
        peak *= NOISEMAKER_SELF_PASSIVE
    # Signature layers: a contact in another band is hidden by the boundary.
    peak *= _layer_penalty(state, c)
    return clamp((peak * PASSIVE_SAMPLE_SCALE) / max(state.noise, NOISE_MIN), 0, 22)


def _passive_detect(state: GameState, c: Contact, dt: float) -> None:
    if c.state == "confirmed":
        return
    snr = _passive_snr(state, c)
    c.signal = snr
    if snr <= 0:
        return
    if not c.everDetected:
        # A new contact only firms up after enough accumulated listening energy;
        # the X^2 noise floor stretches that out as the watch drags on.
        c.tail = (c.tail if c.tail is not None else 0) + snr * (dt / BEARING_DRIFT_MINUTES)
        if c.tail < PASSIVE_ACQUIRE_THRESHOLD:
            return

    d = dist(state.ship.pos, c.pos)
    _block, scatter, _reflect = _obstacle_shadow(state, c)
    sigma = (
        clamp(d / 55, 0.8, 14) * (1.6 if c.trueType == "capship" else 1)
        + (3 if state.ship.selfNoise > 0.6 else 0)
        + scatter * 16
    )
    true_b = bearing(state.ship.pos, c.pos)
    elev = elevation(state.ship.pos, c.pos)
    sample = BearingSample(
        t=state.clock,
        bearing=wrap_bearing(true_b + noise(int(state.clock), sigma) + 0.5),
        elev=elev,
        source="passive",
    )
    c.bearingHistory.append(sample)
    c.detected = True
    c.everDetected = True
    c.lastSeen = state.clock
    c.seenCount += 1

    # Passive resolves emission and, on a loud hull, its type — never range.
    loud = _contact_loudness(c)
    observed = clamp(loud * (0.85 + 0.3 * hash_random(c.seenCount, 41)), 0, 1)
    c.sensor.passiveEmission = clamp(
        c.sensor.passiveEmission + (observed - c.sensor.passiveEmission) * 0.4, 0, 1
    )
    identify = clamp(loud * 1.25 - state.noise / (PASSIVE_SAMPLE_SCALE * 4), 0, 1)
    if hash_random(int(state.clock), len(c.id)) < identify:
        c.sensor.passiveType = c.trueType

    # Paint the frequency barcode in band by band: a strong, close signal
    # resolves its profile fast, a faint one stays fuzzy and noise-dominated.
    if c.frequencyProfile:
        if len(c.sensor.bands) != len(c.frequencyProfile):
            c.sensor.bands = [0.0] * len(c.frequencyProfile)
        reveal = clamp(0.08 + snr / 45.0, 0.04, 0.85)
        for bi, true_v in enumerate(c.frequencyProfile):
            target_v = clamp(
                true_v * (0.6 + 0.4 * loud)
                + abs(noise(c.seenCount * 7 + bi, 0.18)),
                0,
                1,
            )
            cur = c.sensor.bands[bi]
            c.sensor.bands[bi] = clamp(cur + (target_v - cur) * reveal, 0, 1)

    ease = TYPE_EASE[c.trueType]
    bump_confidence(
        state,
        c,
        (0.018 + 0.035 * clamp(1 - d / PASSIVE_BASE_RANGE_KLIK, 0, 1) * ease)
        * (0.5 + loud),
    )
    if c.seenCount == 1:
        c.firstSeen = state.clock
        el = sample.elev if sample.elev is not None else 0
        log(
            state,
            "SENSORS",
            f"New faint bearing {_round(sample.bearing):03d} at "
            f"{'+' if el >= 0 else ''}{_round(el)}° — {c.signature} on the passive grill.",
            "info",
        )
    elif c.seenCount % 4 == 0:
        log(
            state,
            "SENSORS",
            f"Bearing {_round(sample.bearing):03d} repeats — tracking {c.name}.",
            "info",
        )
    # No range from passive: the plot keeps bearing alone until radar or optics.


def _visual_detect(state: GameState, c: Contact, dt: float) -> None:
    if not state.ship.emcon.optics:
        return
    d = dist(state.ship.pos, c.pos)
    if d > TYPICAL_SIGHTING_RANGE_KLIK:
        return
    if hash_random(int(state.clock), ord(c.id[0])) < 0.25:
        return
    true_b = bearing(state.ship.pos, c.pos)
    elev = elevation(state.ship.pos, c.pos)
    c.bearingHistory.append(
        BearingSample(
            t=state.clock,
            bearing=wrap_bearing(true_b + noise(state.clock, 2)),
            range=_round(d),
            elev=elev,
            source="visual",
        )
    )
    c.detected = True
    c.everDetected = True
    c.lastSeen = state.clock
    c.seenCount += 1
    bump_confidence(state, c, 0.09)
    add_exposure(state, EXPOSE_OPTICS, "optical scan")
    _refresh_estimate(state, c)
    if c.trueType != "unknown":
        c.guess = c.trueType
    log(
        state,
        "VISUAL",
        f"Optics: {c.name} in the lens at {_round(d)} klik, bearing "
        f"{_round(true_b):03d}, {'+' if elev >= 0 else ''}{_round(elev)}° elevation.",
        "intel",
    )


# ---------------------------------------------------------------------------
# Detection race: they are hunting us too
# ---------------------------------------------------------------------------


def _enemy_lock_signal(state: GameState, c: Contact) -> tuple[float, float]:
    """How well ``c`` can hear/fix the crew ship right now: ``(signal, reach)``.

    ``signal`` is a 0..2 rate multiplier; the lock accumulates as
    ``signal * dt / ENEMY_LOCK_MINUTES``.  A close, loud, radiating ship shows
    up fast; a quiet hull behind an asteroid can stay invisible.
    """
    ship = state.ship
    d = dist(c.pos, ship.pos)
    sq = c.sensorQuality if c.sensorQuality > 0 else 0.5
    reach = ENEMY_PASSIVE_BASE_KLIK * (0.7 + 0.6 * sq) * (1.35 if c.emitting else 1.0)
    if d > reach:
        return 0.0, reach
    # Your own noise, masked by hull stealth, plus the radar cross-section they
    # can paint if they are radiating.
    loud = clamp(ship.selfNoise * (1 - ship.stealth) + ship.profile * ENEMY_PROFILE_WEIGHT, 0, 1)
    block, _scatter, _reflect = _obstacle_between(state, c.pos, ship.pos, exclude=c)
    signal = (
        clamp(1 - d / reach, 0, 1)
        * (0.25 + 1.6 * loud)
        * (1 - block)
        * (1.2 if c.emitting else 1.0)
    )
    if state.noisemakerTurns > 0:
        signal *= NOISEMAKER_ENEMY_SIGNAL
    return clamp(signal, 0, 2.0), reach


def layer_of(state: GameState, z: float) -> SensorLayer | None:
    """The EM/thermal band an altitude sits in."""
    for layer in state.campaign.layers:
        if layer.zMin <= z < layer.zMax:
            return layer
    return state.campaign.layers[-1] if state.campaign.layers else None


def _layer_penalty(state: GameState, c: Contact) -> float:
    """Detection across a layer boundary is cut; crossing blinds you briefly."""
    if not state.campaign.layers:
        return 1.0
    ours = layer_of(state, state.ship.pos.z)
    theirs = layer_of(state, c.pos.z)
    separated = ours is not None and theirs is not None and ours.id != theirs.id
    if state.clock < state.layerCrossUntil:
        # Mid-crossing: your own array is in turmoil.
        return LAYER_ATTENUATION
    if separated:
        return LAYER_ATTENUATION
    return 1.0


def _update_layer(state: GameState) -> None:
    """Track which band the ship is riding; announce and pay for crossings."""
    if not state.campaign.layers:
        return
    here = layer_of(state, state.ship.pos.z)
    name = here.name if here is not None else ""
    if name and name != state.layer:
        previous = state.layer
        state.layer = name
        if previous:
            state.noise = clamp(state.noise + LAYER_CROSS_NOISE, NOISE_MIN, NOISE_CAP)
            state.layerCrossUntil = state.clock + LAYER_CROSS_BREAK_MIN
            log(
                state,
                "OPS",
                f"Crossing into the {name} — the boundary hides us from one side "
                "and blinds us to it; the array will settle in a few minutes.",
                "warn",
            )


def start_tma(state: GameState, contact_id: str) -> None:
    """Begin a manoeuvre leg to solve a bearing-only track."""
    c = next((x for x in state.contacts if x.id == contact_id), None)
    if c is None or not c.everDetected:
        return
    if state.tma is not None and not state.tma.solved:
        return
    _log_tma_bearing(state, c)
    state.tma = TmaState(
        contactId=c.id,
        startedAt=state.clock,
        startHeading=state.ship.heading,
        startBearing=bearing(state.ship.pos, c.pos),
    )
    log(
        state,
        "OPS",
        f"TMA leg started on {c.name} — hold the course change and let the "
        "bearing rate build.",
        "info",
    )
    if TMA_DATUM_RECENTER and active_datum_near(state, state.ship.pos) is not None:
        # A careless leg inside a datum tells the hunter exactly where we are.
        place_datum(state, "our own TMA turn")
    state.seq += 1


def _log_tma_bearing(state: GameState, c: Contact) -> None:
    """The operator logs one bearing for the leg — a TMA plot, not a snapshot."""
    if c.bearingHistory and c.bearingHistory[-1].t == state.clock:
        return
    d = dist(state.ship.pos, c.pos)
    sigma = clamp(d / 55, 0.8, 14) * 0.5
    c.bearingHistory.append(
        BearingSample(
            t=state.clock,
            bearing=wrap_bearing(
                bearing(state.ship.pos, c.pos) + noise(int(state.clock), sigma)
            ),
            elev=elevation(state.ship.pos, c.pos),
            source="passive",
        )
    )
    if len(c.bearingHistory) > 40:
        c.bearingHistory = c.bearingHistory[-40:]


def _tma_range(state: GameState, c: Contact) -> float | None:
    """Range from bearing rate — the whole point of a passive TMA solve."""
    recent = c.bearingHistory[-6:]
    if len(recent) < 2:
        return None
    first, last = recent[0], recent[-1]
    span = max(1.0, last.t - first.t)
    rate = abs(bearing_diff(last.bearing, first.bearing)) / span
    return clamp(520 / (rate + 0.15), 4, PASSIVE_BASE_RANGE_KLIK * 1.4)


def _update_tma(state: GameState, dt: float) -> None:
    """Solve the leg once enough bearing rate has been generated."""
    tma = state.tma
    if tma is None:
        return
    c = next((x for x in state.contacts if x.id == tma.contactId), None)
    if c is None or not c.everDetected:
        state.tma = None
        return
    _log_tma_bearing(state, c)
    turn = abs(bearing_diff(state.ship.heading, tma.startHeading))
    drift = abs(bearing_diff(bearing(state.ship.pos, c.pos), tma.startBearing))
    tma.bearingRate = _round_to(drift, 1)
    if turn >= TMA_MIN_TURN_DEG and drift >= TMA_MIN_BEARING_DEG:
        tma.solved = True
        tma.quality = clamp(
            TMA_BASE_QUALITY + drift / 40.0 + turn / 90.0, 0, 1
        )
        _refresh_estimate(state, c)
        rng = _tma_range(state, c)
        c.sensor.tmaRangeKlik = _round_to(rng, 1) if rng is not None else None
        c.sensor.tmaQuality = _round_to(tma.quality, 2)
        bump_confidence(state, c, 0.08)
        log(
            state,
            "SENSORS",
            f"TMA SOLUTION on {c.name} — {_round_to(rng, 1) if rng else '—'} klik "
            f"(quality {_round(tma.quality * 100)}%) from the manoeuvre.",
            "ok",
        )
        state.tma = None
        state.seq += 1
        return
    if state.clock - tma.startedAt >= TMA_MAX_MIN:
        log(
            state,
            "OPS",
            f"TMA leg on {c.name} timed out — no bearing rate worth solving.",
            "warn",
        )
        state.tma = None
        state.seq += 1


def _hunters_move(state: GameState, dt: float) -> None:
    """Hunters prosecute a lock, or search the nearest active datum."""
    if not state.contacts:
        return
    datum = next((d for d in state.datums if d.active), None)
    for c in state.contacts:
        if c.trueType in ENVIRONMENTAL_TYPES or not c.hostile:
            continue
        target: Vec | None = None
        if c.lock >= DATUM_LOCK_THRESHOLD:
            target = state.ship.pos
        elif datum is not None and dist(c.pos, datum.pos) <= DATUM_SEARCH_RANGE_KLIK:
            target = datum.pos
        if target is None:
            continue
        want = bearing(c.pos, target)
        delta = bearing_diff(want, c.heading)
        limit = HUNTER_TURN_RATE_DEG_PER_MIN * dt
        c.heading = wrap_bearing(
            c.heading + clamp(delta, -limit, limit)
        )


def place_datum(state: GameState, source: str) -> Datum:
    """Place — or re-center — a hunter's datum on the ship's position."""
    d = next((x for x in state.datums if x.active), None)
    if d is not None:
        d.pos = state.ship.pos.model_copy()
        d.radiusKlik = DATUM_INITIAL_RADIUS_KLIK
        d.strength = 1.0
        d.ageMinutes = 0.0
        d.source = source
        log(
            state,
            "EW",
            f"THE DATUM RE-CENTERS — a hunter has us again ({source}).",
            "danger",
        )
        return d
    d = Datum(
        id=f"datum-{len(state.datums) + 1}",
        pos=state.ship.pos.model_copy(),
        radiusKlik=DATUM_INITIAL_RADIUS_KLIK,
        strength=1.0,
        source=source,
    )
    state.datums.append(d)
    state.datums = state.datums[-DATUM_MAX_ACTIVE:]
    log(
        state,
        "EW",
        f"DATUM — a hunter has placed a search datum on our last known position "
        f"({source}). Run quiet to break it.",
        "danger",
    )
    return d


def active_datum_near(state: GameState, pos: Vec) -> Datum | None:
    """A datum whose search box currently covers ``pos``."""
    for d in state.datums:
        if d.active and dist(pos, d.pos) <= d.radiusKlik + 12:
            return d
    return None


def _update_datums(state: GameState, dt: float) -> None:
    """Age every datum: its box widens, its strength fades, and it can die."""
    if not state.datums:
        return
    decay = DATUM_DECAY_PER_MIN * (
        DATUM_DRIFT_DECAY_MULTIPLIER if state.posture == "drift" else 1.0
    )
    remaining: list[Datum] = []
    for d in state.datums:
        if not d.active:
            continue
        d.ageMinutes += dt
        d.radiusKlik += DATUM_RADIUS_GROWTH * dt
        d.strength = clamp(d.strength - decay * dt, 0, 1)
        if d.strength <= 0 or d.ageMinutes >= DATUM_MAX_AGE_MIN:
            log(
                state,
                "EW",
                "The datum has aged out — the hunt is breaking. Window open.",
                "ok",
            )
            continue
        remaining.append(d)
    state.datums = remaining


def set_posture(state: GameState, posture: str) -> None:
    """Transit doctrine: sprint loud and fast, or drift slow and silent."""
    if posture not in ("transit", "sprint", "drift"):
        return
    state.posture = posture  # type: ignore[assignment]
    ship = state.ship
    if posture == "sprint":
        ship.mode = "max"
        ship.speed = ship.maxSpeed
        log(state, "OPS", "SPRINT — fast and loud; the hunters will hear us.", "warn")
    elif posture == "drift":
        ship.mode = "quiet"
        ship.speed = ship.quietSpeed
        log(
            state,
            "OPS",
            "DRIFT — slow and silent; detection decays while we creep.",
            "ok",
        )
    else:
        ship.mode = "cruise"
        ship.speed = ship.cruiseSpeed
        log(state, "OPS", "Transit posture.", "info")
    _apply_emission(ship)
    state.seq += 1


def _clear_maneuver(state: GameState, why: str) -> None:
    ship = state.ship
    if not ship.maneuver:
        return
    ship.maneuver = ""
    ship.maneuverEvasive = 0
    ship.maneuverGunnery = 0
    ship.maneuverUntil = 0.0
    log(state, "OPS", f"Evasive posture dropped — {why}.", "info")


def set_maneuver(state: GameState, name: str) -> None:
    """Fly a defensive manoeuvre; the modifiers hold until the next helm order."""
    spec = MANEUVERS.get(name)
    if spec is None:
        return
    ship = state.ship
    evasive = int(spec["evasive"])  # type: ignore[arg-type]
    gunnery = int(spec["gunnery"])  # type: ignore[arg-type]
    turn = float(spec["turn"])  # type: ignore[arg-type]
    dc_name = spec["dc"]
    ok = True
    if dc_name:
        result = station_check(
            state,
            "Starship Piloting",
            difficulty(str(dc_name)),
            action="maneuver",
            contact_id=name,
        )
        ok = result.success
        if result.outcome == "critical-failure":
            evasive = 0
            gunnery = 0
            turn = 0.0
    if not ok:
        evasive = evasive // 2
        turn = 0.0
    if turn:
        ship.heading = wrap_bearing(ship.heading + turn)
    ship.maneuver = name if ok else f"{name} (botched)"
    ship.maneuverEvasive = evasive
    ship.maneuverGunnery = gunnery
    ship.maneuverUntil = state.clock + MANEUVER_HOLD_MIN
    state.noise = clamp(state.noise + MANEUVER_NOISE, NOISE_MIN, NOISE_CAP)
    log(
        state,
        "OPS",
        f"{spec['label']}"
        + (f" — heading {_round(ship.heading):03d}," if turn else " —")
        + f" evasive +{evasive}, our gunnery -{gunnery}."
        + ("" if ok else " The turn did not take."),
        "ok" if ok else "warn",
    )
    state.seq += 1


def clear_baffles(state: GameState) -> None:
    """A deliberate turn aft: the blind arc is cleared, and everyone heard it."""
    state.bafflesClearedUntil = state.clock + BAFFLE_CLEAR_MINUTES
    state.noise = clamp(state.noise + BAFFLE_CLEAR_NOISE, NOISE_MIN, NOISE_CAP)
    log(
        state,
        "SENSORS",
        "Clearing the baffles — a hard turn aft. The array is blind back there "
        "no longer, but they heard the turn.",
        "warn",
    )
    state.seq += 1


def _enemy_detect(state: GameState, c: Contact, dt: float) -> None:
    """Advance one hostile's track on the crew ship.

    This is the loss side of the race.  It is deliberately independent of
    whether *we* have seen the contact: a hunter can be tracking us while we
    have no idea it is there.
    """
    if state.outcome is not None:
        return
    if c.trueType in ENVIRONMENTAL_TYPES or not c.hostile:
        return
    if c.hostileLock:
        return
    signal, _reach = _enemy_lock_signal(state, c)
    signal *= env_factor(state, "emission")
    if active_datum_near(state, c.pos) is not None:
        # A hunter searching inside the datum knows roughly where to listen.
        signal *= 1 + DATUM_SEARCH_BONUS
    signal *= POSTURE_LOCK_MULTIPLIER.get(state.posture, 1.0)
    if signal <= 0:
        decay = ENEMY_LOCK_DECAY * POSTURE_DECAY_MULTIPLIER.get(state.posture, 1.0)
        c.lock = clamp(c.lock - decay * (dt / BEARING_DRIFT_MINUTES), 0, 1)
        return
    before = c.lock
    c.lock = clamp(c.lock + signal * dt / ENEMY_LOCK_MINUTES, 0, 1)
    if before < DATUM_LOCK_THRESHOLD <= c.lock:
        place_datum(state, f"{c.name} held a track")
    if c.lock >= DETECTED_LOCK:
        # A working track, not a transient ping: this voids the endurance win.
        c.everTrackedUs = True
    if before < DETECTED_LOCK <= c.lock:
        log(
            state,
            "EW",
            "A transmitter is ranging us — someone has a partial track. "
            "The crybaby or a hard turn buys time.",
            "warn",
        )
    if c.lock >= 1.0:
        c.hostileLock = True
        _painted(state, c)


def _painted(state: GameState, c: Contact) -> None:
    """A hunter has a firing solution on the crew ship: the patrol is lost."""
    # At knife range you finally see who found you.
    _reveal_contact(c, force=True)
    ship = state.ship
    ship.exposure = clamp(ship.exposure + PAINTED_EXPOSURE, 0, 100)
    ship.hull = clamp(ship.hull - PAINTED_HULL_DAMAGE, 0, 100)
    ship.readiness = clamp(ship.readiness - PAINTED_READINESS_DAMAGE, 0, 100)
    log(
        state,
        "TAC",
        f"FIRING SOLUTION on us from {c.name}. We were spotted first — taking "
        f"{PAINTED_HULL_DAMAGE}% hull getting clear.",
        "danger",
    )
    _declare_outcome(
        state,
        "lost",
        f"PATROL LOST — {c.name} fixed us first. The enemy saw us before we saw them.",
    )


# ---------------------------------------------------------------------------
# Sensor buoys: a second passive origin
# ---------------------------------------------------------------------------


def _buoy_passive_snr(state: GameState, b: Buoy, c: Contact) -> float:
    """Passive signal-to-noise for a buoy listening to ``c``."""
    reach = BUOY_PASSIVE_RANGE_KLIK
    d = dist(b.pos, c.pos)
    if d > reach:
        return 0.0
    block, _scatter, _reflect = _obstacle_between(state, b.pos, c.pos, exclude=c)
    ease = TYPE_EASE[c.trueType]
    loud = _contact_loudness(c)
    emitting_boost = 1.4 if c.emitting else 1.0
    closeness = clamp(1 - d / (reach * 1.5), 0, 1)
    peak = (
        EMISSION_BASE
        * (0.3 + 1.7 * loud)
        * ease
        * emitting_boost
        * closeness
        * (1 - block)
        * env_factor(state, "sensor")
    )
    return clamp((peak * PASSIVE_SAMPLE_SCALE) / max(state.noise, NOISE_MIN), 0, 22)


def _triangulate(state: GameState, c: Contact) -> bool:
    """Cross-fix a passive-only contact from two sensor origins.

    A bearing from the ship and a bearing from a deployed buoy share a known
    baseline, so their intersection is a range.  This is the payoff for putting
    a buoy out: it converts bearing-only tracks into actual fixes.
    """
    if c.triangulated:
        return False
    own = [s for s in c.bearingHistory if not s.originId and s.range is None]
    remote = [s for s in c.bearingHistory if s.originId]
    if not own or not remote:
        return False
    b = next((x for x in state.buoys if x.id == remote[-1].originId and x.active), None)
    if b is None:
        return False
    a = state.ship.pos
    if flat_dist(a, b.pos) < BUOY_TRIANGULATION_BASELINE_KLIK:
        return False
    ra = math.radians(own[-1].bearing)
    rb = math.radians(remote[-1].bearing)
    ua = (math.sin(ra), math.cos(ra))
    ub = (math.sin(rb), math.cos(rb))
    wx, wy = b.pos.x - a.x, b.pos.y - a.y
    denom = ua[0] * ub[1] - ua[1] * ub[0]
    if abs(denom) < 1e-6:  # parallel bearings: no intersection
        return False
    t = (wx * ub[1] - wy * ub[0]) / denom
    s = (wx * ua[1] - wy * ua[0]) / denom
    if t <= 0 or s <= 0:
        return False
    rng = clamp(t, 1.0, PASSIVE_BASE_RANGE_KLIK * 1.8)
    elev = own[-1].elev if own[-1].elev is not None else 0.0
    c.estimated = Vec(
        x=a.x + ua[0] * rng,
        y=a.y + ua[1] * rng,
        z=clamp(a.z + math.sin(math.radians(elev)) * rng, -200, 200),
    )
    c.bearingHistory.append(
        BearingSample(
            t=state.clock,
            bearing=own[-1].bearing,
            range=_round(rng),
            source="passive",
            originId="",
        )
    )
    c.triangulated = True
    bump_confidence(state, c, BUOY_TRIANGULATION_CONFIDENCE)
    log(
        state,
        "SENSORS",
        f"Cross-fix: {b.name} and our own array intersect one return at "
        f"{_round(rng)} klik, bearing {_round(own[-1].bearing):03d}. Track ranged.",
        "intel",
    )
    return True


def _buoy_detect(state: GameState, dt: float) -> None:
    """Every deployed buoy listens on its own, feeding the crew's plot."""
    if not state.buoys:
        return
    for b in state.buoys:
        if not b.active:
            continue
        for c in state.contacts:
            if c.state == "confirmed":
                continue
            snr = _buoy_passive_snr(state, b, c)
            if snr <= 0:
                continue
            if not c.everDetected:
                c.tail = (c.tail if c.tail is not None else 0) + snr * (
                    dt / BEARING_DRIFT_MINUTES
                )
                if c.tail < PASSIVE_ACQUIRE_THRESHOLD:
                    continue
            sigma = clamp(dist(b.pos, c.pos) / 55, 0.8, 14)
            sample = BearingSample(
                t=state.clock,
                bearing=wrap_bearing(
                    bearing(b.pos, c.pos) + noise(int(state.clock), sigma)
                ),
                elev=elevation(b.pos, c.pos),
                source="passive",
                originId=b.id,
            )
            c.bearingHistory.append(sample)
            if not c.everDetected:
                c.firstSeen = state.clock
                log(
                    state,
                    "SENSORS",
                    f"{b.name} cuts a passive bearing {_round(sample.bearing):03d} on "
                    f"an unidentified return.",
                    "intel",
                )
            c.detected = True
            c.everDetected = True
            c.lastSeen = state.clock
            c.seenCount += 1
            bump_confidence(state, c, 0.015)
            _triangulate(state, c)
            if len(c.bearingHistory) > 40:
                c.bearingHistory = c.bearingHistory[-40:]


def deploy_buoy(state: GameState) -> Buoy | None:
    """Drop a passive sensor buoy at the ship's current position.

    The buoy is immobile; it exists to put a second listening point a baseline
    away from the ship so passive bearings can be cross-fixed.
    """
    ship = state.ship
    if ship.buoyCount <= 0:
        log(state, "OPS", "The buoy rack is empty — nothing left to drop.", "warn")
        state.seq += 1
        return None
    number = _next_buoy_number(state)
    ship.buoyCount -= 1
    buoy = Buoy(
        id=f"buoy-{number}",
        name=f"BUOY-{number}",
        pos=Vec(x=ship.pos.x, y=ship.pos.y, z=ship.pos.z),
        deployedAt=state.clock,
    )
    state.buoys.append(buoy)
    log(
        state,
        "OPS",
        f"{buoy.name} away and listening. Immobile from here — it gives us a "
        f"second bearing to cross-fix against. ({ship.buoyCount} left in the rack.)",
        "ok",
    )
    state.seq += 1
    return buoy


def recover_buoy(state: GameState, buoy_id: str) -> bool:
    """Recover a deployed buoy back to the rack (ops clicks it on the plot)."""
    i = next((idx for idx, b in enumerate(state.buoys) if b.id == buoy_id), -1)
    if i < 0:
        return False
    buoy = state.buoys.pop(i)
    state.ship.buoyCount = min(SENSOR_BUOY_LOADOUT, state.ship.buoyCount + 1)
    log(
        state,
        "OPS",
        f"{buoy.name} recovered to the rack. ({state.ship.buoyCount} aboard.)",
        "ok",
    )
    state.seq += 1
    return True


# ---------------------------------------------------------------------------
# Noisemakers (crybabies)
# ---------------------------------------------------------------------------


def deploy_noisemaker(state: GameState) -> bool:
    """Flood the EM band for a couple of turns and break any track on us."""
    ship = state.ship
    if ship.noisemakers <= 0:
        log(state, "EW", "No crybabies left in the tube.", "warn")
        state.seq += 1
        return False
    ship.noisemakers -= 1
    state.noisemakerTurns = NOISEMAKER_TURNS
    broken = 0
    for c in state.contacts:
        if c.hostile and (c.lock > 0 or c.hostileLock):
            broken += 1
        if c.hostile:
            c.lock = 0.0
    log(
        state,
        "EW",
        f"Crybaby away — the band floods with EM hash for {NOISEMAKER_TURNS} turns. "
        + (f"{broken} track(s) shaken off. " if broken else "Nothing was tracking us. ")
        + "Our own passive and EM ears are deaf while it sings.",
        "warn",
    )
    state.seq += 1
    return True


def _tick_noisemaker(state: GameState) -> None:
    if state.noisemakerTurns <= 0:
        return
    state.noisemakerTurns -= 1
    if state.noisemakerTurns == 0:
        log(state, "EW", "The crybaby sputters out — the band goes quiet again.", "info")
    state.seq += 1


# ---------------------------------------------------------------------------
# Confidence / classification ladder
# ---------------------------------------------------------------------------


def _reveal_contact(c: Contact, *, force: bool = False) -> None:
    """Release a contact's true name once it is CONFIRMED.

    Until then the plot only carries its anonymous track designation; seeing
    ``MV GRAY TRITON`` before you have done the work would hand the crew the
    answer.  ``force`` is for the moment the enemy is close enough to read
    anyway.
    """
    if c.trueName and (force or c.state == "confirmed"):
        c.name = c.trueName


def bump_confidence(state: GameState, c: Contact, amount: float) -> None:
    before = state_of_confidence(c.confidence)
    c.confidence = clamp(c.confidence + amount, 0, 1)
    after = state_of_confidence(c.confidence)
    c.state = after
    if after != before:
        log(state, "CLASS", f"{c.name} upgraded to {after.upper()}.", "intel")
        if after == "confirmed":
            _reveal_contact(c)
            log(
                state,
                "CLASS",
                f"{c.name} is CONFIRMED {c.trueType.upper()}{' — HOSTILE' if c.hostile else ''}.",
                "danger",
            )


def _decay_contacts(state: GameState, dt: float) -> None:
    decays_in = CONTACT_DECAY_MINUTES
    for c in state.contacts:
        if c.lastSeen > 0 and state.clock - c.lastSeen > decays_in:
            c.confidence = clamp(c.confidence - 0.018 * (dt / decays_in), 0, 1)
        st = state_of_confidence(c.confidence)
        if st != c.state:
            c.state = st
        if (
            c.state == "unknown"
            and c.everDetected
            and c.lastSeen > 0
            and state.clock - c.lastSeen > decays_in * 2
        ):
            log(state, "CLASS", f"No new data on {c.name} — faded back to unknown.", "warn")
        if c.confidence <= CONFIDENCE_BY_STATE["probable"] and len(c.bearingHistory) > 30:
            c.bearingHistory = c.bearingHistory[-30:]


# ---------------------------------------------------------------------------
# TMA estimate
# ---------------------------------------------------------------------------


def _refresh_estimate(state: GameState, c: Contact) -> None:
    # Only ranged fixes (active radar, optics, intel) can place a contact on the
    # chart.  Passive gives bearing alone; callers that need a TMA solution add
    # the range themselves.
    recent = [s for s in c.bearingHistory[-6:] if s.range is not None]
    if len(recent) < 2:
        return
    first = recent[0]
    last = recent[len(recent) - 1]
    dt = max(1, last.t - first.t)
    drift = bearing_diff(last.bearing, first.bearing)
    rate = drift / dt  # deg per minute of bearing drift
    # Fast drift = close & crossing; slow drift = far away. Forgiving, not orbital-grade.
    est_dist_klik = clamp(520 / (abs(rate) + 0.15), 4, PASSIVE_BASE_RANGE_KLIK * 1.4)
    direction = (last.bearing * math.pi) / 180
    elev = last.elev if last.elev is not None else 0
    esin = math.sin((elev * math.pi) / 180)
    c.estimated = Vec(
        x=state.ship.pos.x + math.sin(direction) * est_dist_klik,
        y=state.ship.pos.y + math.cos(direction) * est_dist_klik,
        z=clamp(state.ship.pos.z + esin * est_dist_klik, -200, 200),
    )


# ---------------------------------------------------------------------------
# Exposure / tension
# ---------------------------------------------------------------------------


def add_exposure(state: GameState, amount: float, why: str) -> None:
    if amount <= 0:
        return
    state.ship.exposure = clamp(state.ship.exposure + amount, 0, 100)
    state.war.tension = clamp(
        state.war.tension + amount * TENSION_PER_EXPOSURE, 0, 100
    )
    if amount >= 8:
        log(
            state,
            "EXPOSE",
            f"{why} — reported exposure now {_round(state.ship.exposure)}%.",
            "warn",
        )


def _drift(state: GameState, h: float) -> None:
    s = state.ship
    e: float = float(EXPOSE_DRIFT_PER_HOUR)
    if s.emcon.radar:
        e += EXPOSE_RADAR
    if s.speed > 0.01:
        # The towed array bleeds a little whenever it is streamed.
        e += EXPOSE_GRAVIDAR
    if s.mode == "max":
        e += EXPOSE_SPEED_MAX
    if s.mode == "quiet":
        e -= 2.5
    add_exposure(state, e * h, "steady state")
    state.war.tension = clamp(
        state.war.tension - TENSION_RELAX_PER_HOUR * h * (1.6 if state.ship.mode == "quiet" else 1),
        0,
        100,
    )
    state.ship.exposure = clamp(
        state.ship.exposure - 0.8 * h * (1.4 if state.ship.mode == "quiet" else 1),
        0,
        100,
    )


def _spend_systems(state: GameState, h: float) -> None:
    """Run the ship's consumables: battery charge and crew readiness.

    Active radar and flank speed are what cost power; quiet running and holding
    station put some back.  Hard running wears the crew, rest recovers them.
    Without this the battery and readiness readouts were inert decoration.
    """
    s = state.ship
    consume = 0.0
    if s.activeSensor:
        consume += BATTERY_RADAR_PER_HOUR
    if s.mode == "max":
        consume += BATTERY_FLANK_PER_HOUR
    if s.mode == "quiet":
        recharge = BATTERY_QUIET_RECHARGE_PER_HOUR
    else:
        recharge = BATTERY_RECHARGE_PER_HOUR
    if s.speed <= 0.01:
        recharge += BATTERY_RECHARGE_PER_HOUR * 0.5
    s.battery = clamp(s.battery + (recharge - consume) * h, 0, 100)

    if s.speed <= 0.01:
        wear = -READINESS_RECOVER_STOPPED
    elif s.mode == "max":
        wear = READINESS_WEAR_MAX
    elif s.mode == "quiet":
        wear = -READINESS_RECOVER_QUIET
    else:
        wear = READINESS_WEAR_CRUISE
    s.readiness = clamp(s.readiness - wear * h, 0, 100)


# ---------------------------------------------------------------------------
# Scheduled events & engagement detection
# ---------------------------------------------------------------------------


def _fire_scheduled(state: GameState) -> None:
    fired: list[int] = []
    for idx, sch in enumerate(state.campaign.events):
        if sch.atMinute <= state.clock:
            state.events.append(make_event(state, sch.template))
            fired.append(idx)
    for idx in reversed(fired):
        state.campaign.events.pop(idx)
    if fired:
        state.seq += 1


def _engagement_candidates(state: GameState) -> DecisionEvent | None:
    hostile = next(
        (
            c
            for c in state.contacts
            if c.hostile and state_of_confidence(c.confidence) == "confirmed"
        ),
        None,
    )
    if hostile is None:
        return None
    d = dist(state.ship.pos, hostile.pos)
    if d <= ENGAGEMENT_RANGE_KLIK and state.ship.roe != "safe":
        if not any(e.kind == "engagement" for e in state.events):
            log(
                state,
                "TAC",
                f"{hostile.name} CONFIRMED and inside the engagement window "
                f"({_round(d)} klik). Handoff readiness advised.",
                "danger",
            )
            return engagement_prompt(state, hostile.id)
    return None


# ---------------------------------------------------------------------------
# The race: identifying first wins, being painted first loses
# ---------------------------------------------------------------------------


def _check_patrol_win(state: GameState) -> None:
    """Win the patrol by staying dark, by mapping every hunter, or by outlasting.

    Three ways out:

    - **Endurance** — ``ENDURE_MINUTES`` have passed since the patrol began with
      no hostile ever building a working track on us (``everTrackedUs``); the
      crew ran dark for six hours.
    - **All tracked** — every hostile is detected and at least "tracking", with
      weapons still safe: the crew has the whole picture before anyone fixes
      them.
    - **Disengaged** — every hostile has cleared ``DISENGAGE_RANGE_KLIK`` and at
      least one had closed inside it: the lane emptied and the crew made it
      through.  This one does not require weapons safe — surviving to watch them
      go is the win whatever the firing posture.
    """
    hostiles = [
        c for c in state.contacts if c.hostile and c.trueType not in ENVIRONMENTAL_TYPES
    ]
    if not hostiles:
        return
    if (
        state.ship.roe == "safe"
        and state.clock - state.campaign.startHour * 60 >= ENDURE_MINUTES
        and not any(c.everTrackedUs for c in hostiles)
        and not any(d.active for d in state.datums)
    ):
        _declare_outcome(
            state,
            "won",
            f"PATROL WON — {int(ENDURE_MINUTES // 60)} hours dark and undetected. "
            f"No hunter ever built a track on us; the lane is ours.",
        )
        return
    if all(
        dist(state.ship.pos, c.pos) > DISENGAGE_RANGE_KLIK for c in hostiles
    ) and any(c.everNear for c in hostiles):
        _declare_outcome(
            state,
            "won",
            f"PATROL WON — the lane is clear. Every hostile has broken off beyond "
            f"{DISENGAGE_RANGE_KLIK} klik and we made it through.",
        )
        return
    if state.ship.roe != "safe":
        return
    if all(
        c.everDetected and state_of_confidence(c.confidence) != "unknown"
        for c in hostiles
    ):
        _declare_outcome(
            state,
            "won",
            f"PATROL WON — all {len(hostiles)} hostile contact(s) detected and "
            f"tracked. We saw the whole picture before anyone fixed us.",
        )


def award_career(state: GameState, xp: int, reputation: float, why: str) -> None:
    """Experience and standing from a mission event."""
    state.xp += int(xp)
    state.reputation = clamp(state.reputation + reputation, -100, 100)
    log(
        state,
        "COMMAND",
        f"Career: +{int(xp)} XP, {reputation:+.1f} standing ({why}).",
        "ok",
    )


def award_medal(state: GameState, medal: str) -> None:
    """A medal is earned once."""
    if medal in state.medals:
        return
    state.medals.append(medal)
    log(state, "COMMAND", f"MEDAL AWARDED — {medal}.", "ok")


def _declare_outcome(state: GameState, outcome: str, headline: str) -> None:
    """Seal the patrol with a result.  The race is terminal."""
    if state.outcome is not None:
        return
    state.outcome = outcome  # type: ignore[assignment]
    state.outcomeAt = state.clock
    state.endReason = headline
    if outcome == "won":
        award_career(state, 50, 5.0, "patrol completed")
        award_medal(state, "Lane Runner")
    elif outcome == "lost":
        award_career(state, 10, -2.0, "patrol lost")
    state.status = "ended"
    state.digest = build_digest(state)
    log(state, "COMMAND", headline, "ok" if outcome == "won" else "danger")
    state.seq += 1


def _expire_events(state: GameState) -> None:
    """Unanswered decision events close themselves, at a cost."""
    if not state.events:
        return
    expired = [e for e in state.events if state.clock >= e.deadline]
    if not expired:
        return
    state.events = [e for e in state.events if state.clock < e.deadline]
    for ev in expired:
        state.war.tension = clamp(state.war.tension + EVENT_EXPIRY_TENSION, 0, 100)
        log(
            state,
            "EVENT",
            f"No decision on {ev.title} — the window closes. The lane tenses.",
            "warn",
        )
    state.seq += 1


def _drop_track(state: GameState, contact_id: str | None = None) -> None:
    """A decision (or a lost sensor picture) takes a track off the board."""
    c = next((x for x in state.contacts if x.id == contact_id), None) if contact_id else None
    if c is None:
        candidates = [x for x in state.contacts if x.everDetected]
        if not candidates:
            return
        # Default to the weakest hostile track, else the weakest track overall.
        hostiles = [x for x in candidates if x.hostile] or candidates
        c = min(hostiles, key=lambda x: x.confidence)
    lost_name = c.name
    c.confidence = 0.0
    c.state = "unknown"
    c.detected = False
    c.everDetected = False
    c.bearingHistory = []
    c.estimated = None
    c.triangulated = False
    c.tail = None
    c.gravTail = None
    c.lock = 0.0
    log(state, "SENSORS", f"Track on {lost_name} lost — it is off the board.", "warn")


# ---------------------------------------------------------------------------
# Escalation: the lane answers the noise we make
# ---------------------------------------------------------------------------


def _phase_level(tension: float) -> int:
    return sum(1 for t in ESCALATION_TIERS if tension >= t)


def _escalate(state: GameState) -> None:
    """Each tension tier sends hunters.  Going loud summons the reaction."""
    level = _phase_level(state.war.tension)
    if level <= state.escalationLevel:
        return
    state.escalationLevel = level
    if level >= 3:
        _spawn_reaction(state, "escort", 1)
        _spawn_reaction(state, "fighter", 1)
        log(state, "TAC", "The lane is hunting: escorts and fighters launching toward our box.", "danger")
    elif level == 2:
        _spawn_reaction(state, "escort", 1)
        log(state, "TAC", "A hunter-killer escort is now sweeping our box.", "danger")
    else:
        log(state, "TAC", "The lane is tense — patrols are probing.", "warn")


def _spawn_reaction(state: GameState, ctype: ContactType, count: int) -> None:
    """Put a searching hostile on the patrol boundary, heading inward."""
    center = state.campaign.patrol.center
    radius = max(30.0, state.campaign.patrol.radiusKlik)
    for i in range(count):
        a = hash_random(state.clock, _phase_level(state.war.tension) + i) * 360
        rad = math.radians(a)
        template = ContactTemplate(
            x=_round(center.x + math.sin(rad) * radius),
            y=_round(center.y + math.cos(rad) * radius),
            heading=wrap_bearing(a + 180),
            speed=int(CRUISE_KPS * 0.8),
            type=ctype,
            faction="enemy",
            hostile=True,
            emitting=True,  # searching on active — findable if you are looking
            name=military_name(
                _military_pool(ctype),
                len(state.contacts) + i + 1,
                {c.trueName for c in state.contacts},
            ),
        )
        spawn_opposition(state, template)


# ---------------------------------------------------------------------------
# Handoff pack
# ---------------------------------------------------------------------------


def build_handoff_pack(state: GameState, contact: Contact) -> HandoffPack:
    d = dist(state.ship.pos, contact.pos)
    b = bearing(state.ship.pos, contact.pos)
    el = elevation(state.ship.pos, contact.pos)
    pic = HandoffContact(
        id=contact.id,
        name=contact.name,
        # The handoff carries the crew's committed tag, not the server's answer
        # key. A bad call should create a bad engagement plan.
        type=contact.guess if contact.guess != "unknown" else "unknown",
        range=_round(d),
        bearing=_round(b),
        elev=_round(el),
        course=_round(contact.heading),
        speed=_round(contact.speed),
        confidence=_round(contact.confidence * 100),
    )
    solution_matches = (
        state.ship.weaponsState != "safe"
        and state.ship.weaponTarget == contact.id
    )
    solution = state.ship.solutionQuality if solution_matches else 0.0
    weapon_id = state.ship.weapon if solution_matches else ""
    shot_type = state.ship.shotType if solution_matches else "quick"
    spec = weapon_spec(weapon_id)
    return HandoffPack(
        generatedAt=state.clock,
        contact=pic.model_copy(),
        own=HandoffOwn(
            hullId=state.ship.shipClass,
            livery=state.ship.livery,
            modules=list(state.ship.modules),
            loadout={hp.id: hp.fitted for hp in state.ship.hardpoints if hp.fitted},
            readiness=_round(state.ship.readiness),
            batteries=_round(state.ship.battery),
            condition=state.ship.condition,
            roe=state.ship.roe,
            exposure=_round(state.ship.exposure),
            maneuver=state.ship.maneuver,
            evasive=state.ship.maneuverEvasive,
            alert=state.ship.alert,
            core=_round(state.ship.core),
            shields={a: _round(s.shp) for a, s in state.ship.shields.items()},
            systems={n: _round(h.health) for n, h in state.ship.systems.items()},
        ),
        weapons=HandoffWeapons(
            prepped=solution_matches,
            targetId=pic.id,
            state=state.ship.weaponsState if solution_matches else "safe",
            solutionQuality=round(solution * 100, 1),
            weapon=weapon_id,
            shotType=shot_type,
            targetSystem=state.ship.weaponTargetSystem if solution_matches else "",
            subsystemCheck=state.subsystemCheck if solution_matches else None,
            ehd=(
                compute_ehd(
                    target_hd=hull_hd(contact.profile, contact.stealth),
                    target_evasive=0,
                    tactical=skill_modifier(skill_score(state, "comms", "Targeting"))
                    - state.ship.maneuverGunnery,
                    kind=spec.kind,
                    distance_klik=d,
                    solution_quality=solution,
                )
                if solution_matches
                else None
            ),
        ),
        orders=_handoff_orders(state),
        summary=(
            f"{pic.name} ({pic.type}), {int(pic.range)} klik, bearing "
            f"{int(pic.bearing):03d}, course {int(pic.course)} at {int(pic.speed)} kps. "
            f"Crew readiness {_round(state.ship.readiness)}%. "
            + (
                f"{spec.name} {shot_type} shot at "
                f"{round(solution * 100)}% solution. "
                if solution_matches
                else ""
            )
            + (
                "WEAPONS FREE."
                if state.ship.roe == "free"
                else "Weapons discipline active."
            )
        ),
    )


def _handoff_orders(state: GameState) -> str:
    if state.ship.roe == "free":
        return "Engage at your discretion consistent with your orders. Remain on the declared line."
    if state.ship.roe == "hold":
        return "Hold fire. Weapons prepared but not released. Recommend authorization for an engagement run."
    return "Weapons safe. Evade or neutralize via non-kinetic means if practical."


def phase_name(t: float) -> str:
    if t < 20:
        return "QUIET — patrol lanes thin"
    if t < 45:
        return "TENSING — transiting traffic disturbed"
    if t < 70:
        return "ACTIVE — patrols probing"
    return "HOT — the lane is hunting"


# ---------------------------------------------------------------------------
# Player actions
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Station Checks (the WCRPG d% layer, wired into committing actions)
# ---------------------------------------------------------------------------

# Salt convention: a base per action, plus a stable digest of the contact id so
# two contacts can resolve in the same simulated minute without colliding.
_CHECK_SALTS: dict[str, int] = {
    "claim": 101,
    "active_sweep": 211,
    "grav_scan": 223,
    "iff": 307,
    "dc": 401,
    "refocus_a": 503,
    "refocus_b": 509,
    "damage": 601,
    "repair": 607,
    "maintain": 613,
    "astrogation": 701,
    "survey": 709,
    "arrive": 719,
    "navfix": 809,
    "maneuver": 907,
    "ordnance": 911,
    "targetSystem": 919,
    "spoof": 929,
    "rally": 937,
}

# Check outcome -> how it colours the action.  Kept here so every station reads
# the same way and a later phase can tune one table.
_CHECK_BONUS = {
    "critical-success": 1.0,
    "success": 0.5,
    "failure": 0.0,
    "critical-failure": -1.0,
}
_CRIT_CONFIDENCE_BONUS = {"critical-success": 0.10, "success": 0.02}


def _id_salt(contact_id: str) -> int:
    return sum(ord(ch) for ch in contact_id) % 100


def check_salt(action: str, contact_id: str = "") -> int:
    """The deterministic salt a station Check uses (exported for tests)."""
    return _CHECK_SALTS.get(action, 999) * 100 + _id_salt(contact_id)


def seat_for_skill(skill: str) -> SeatId:
    for seat, skills in STATION_SKILLS.items():
        if skill in skills:
            return seat
    return "command"


def skill_score(state: GameState, seat: SeatId, skill: str) -> int:
    """A station's score in a skill, falling back to the crew average."""
    block = state.seats.get(seat)
    if block is not None and block.skills is not None:
        raw = block.skills.scores.get(skill)
        if raw is not None:
            return int(clamp(raw, 0, 99))
    return default_score("crew")


def check_text(result: CheckResult) -> str:
    label = {
        "critical-success": "CRITICAL SUCCESS",
        "success": "SUCCESS",
        "failure": "FAILURE",
        "critical-failure": "CRITICAL FAILURE",
    }[result.outcome]
    sign = f"{result.modifier:+d}" if result.modifier else "+0"
    return (
        f"{result.skill}: d20 {result.roll} {sign} = {result.total} vs DC {result.dc} "
        f"— {label} (degree {result.degree})"
    )


def check_log_type(result: CheckResult) -> LogEntryType:
    if result.outcome in ("critical-success", "success"):
        return "ok"
    if result.outcome == "critical-failure":
        return "danger"
    return "warn"


def station_check(
    state: GameState,
    skill: str,
    dc: int | None = None,
    *,
    action: str,
    contact_id: str = "",
    bonus: int = 0,
    specialization: str | None = None,
) -> CheckResult:
    """Roll a station Check, record it on the state, and log the result.

    The DC defaults to the Routine step of the hard ladder.  ``bonus`` is a
    circumstance modifier (evidence, tools, help); a named ``specialization``
    adds its rating to the station's skill first.
    """
    seat = seat_for_skill(skill)
    score = skill_score(state, seat, skill)
    block = state.seats.get(seat)
    if (
        specialization
        and block is not None
        and block.skills is not None
    ):
        score = int(
            clamp(score + block.skills.specializations.get(specialization, 0), 0, 99)
        )
    penalty, why = state_check_penalty(state)
    modifier = skill_modifier(score) + int(bonus) - penalty
    if dc is None:
        dc = difficulty("routine")
    if penalty:
        log(state, "CHECK", f"{skill}: the crew is carrying {why} (-{penalty}).", "warn")
    result = run_check(
        state, skill, dc, check_salt(action, contact_id), modifier, score
    )
    state.lastCheck = result
    log(state, "CHECK", check_text(result), check_log_type(result))
    return result


def claim_contact(state: GameState, contact_id: str, guess: ContactType) -> None:
    c = next((x for x in state.contacts if x.id == contact_id), None)
    if c is None or not c.everDetected:
        return
    c.guess = guess
    # Tagging is deliberately blind: the crew commits to a catalogue call but
    # does not receive an answer key.  The call itself is a Check against the
    # sensor watch, and a resolved spectrum sharpens the target.
    evidence = c.waveform is not None and c.waveform.resolved
    result = station_check(
        state,
        "Technology",
        difficulty("hard"),
        action="claim",
        contact_id=c.id,
        bonus=2 if evidence else 0,
    )
    base = 0.16 if evidence else 0.05
    gain = base + _CRIT_CONFIDENCE_BONUS.get(result.outcome, 0.0)
    bump_confidence(state, c, gain)
    log(
        state,
        "SENSORS",
        f"{c.name}: tagged {guess.upper()} from the catalogue. Verification unavailable.",
        "intel",
    )
    if result.outcome == "critical-failure":
        # A botched read costs array time, not confidence: the plot is lying.
        add_exposure(state, 1, "bad sensor read")
        log(
            state,
            "SENSORS",
            f"{c.name}: the plot will not settle — that tag rests on a bad read.",
            "warn",
        )
    c.state = state_of_confidence(c.confidence)


def _spectrum_bins(
    lines: list[tuple[str, float, float]], seed: int, progress: float
) -> list[float]:
    """Rasterize spectral features into normalized analyzer bins.

    Called with ``progress`` in 0..1 so a listen pass literally fills the
    spectrum in: weak lines emerge first, the strong reference lines last.
    """
    bins = [0.0] * SPECTRUM_BINS
    for idx in range(SPECTRUM_BINS):
        bins[idx] = 0.03 + 0.05 * abs(noise(seed * 31 + idx, 1.0))
    # The 21-cm hydrogen reference is always present as the zero-mark wash.
    bins[_nearest_bin(HYDROGEN_BAND)] += 0.18 * progress
    for _band, pos, strength in lines:
        center = pos * (SPECTRUM_BINS - 1)
        width = 1.7
        for idx in range(SPECTRUM_BINS):
            d = idx - center
            bins[idx] += strength * math.exp(-(d * d) / (2 * width * width)) * progress
    return [round(clamp(v, 0.0, 1.0), 3) for v in bins]


def _nearest_bin(pos: float) -> int:
    return int(round(clamp(pos, 0.0, 1.0) * (SPECTRUM_BINS - 1)))


def build_spectrum(c: Contact) -> Spectrum:
    """Build (or refresh) a contact's emission/reflection fingerprint.

    Deterministic in the contact id, so the same target always reads the same
    spectrum; ``waveform.progress`` drives how much of it has emerged.
    """
    progress = c.waveform.progress if c.waveform is not None else 0.0
    seed = sum(ord(ch) for ch in c.id) or 7
    emission_lines = EMISSION_LINES[c.trueType]
    reflection_lines = REFLECTION_LINES[c.trueType]
    spectrum = Spectrum(
        emission=_spectrum_bins(emission_lines, seed, progress),
        reflection=_spectrum_bins(reflection_lines, seed + 7, progress),
        lines=[],
        summary="Partial spectrum — compare the plot against the ship catalogue.",
    )
    c.spectrum = spectrum
    return spectrum


def _update_catalogue_matches(c: Contact) -> None:
    """Rank the ship catalogue by what the listen pass has pulled in.

    Candidates are actual **ship types** (``SHIP_CLASSES`` hulls), not broad
    contact categories.  The barcode painted by the passive watch is a hull's
    own frequency profile, so when it is available the ranking names the exact
    hull; a contact only the gravidar has found has no barcode yet, so the
    ranking falls back to the resolved emission spectrum against each hull's
    contact type.  Either way the whole ship-type table loads, best match first,
    and the answer key is never exposed.
    """
    if c.trueType in ENVIRONMENTAL_TYPES:
        c.sensor.catalogueMatches = []
        return
    observed = c.sensor.bands
    emission = c.spectrum.emission if c.spectrum else []
    matches: list[CatalogueMatch] = []
    for hull in SHIP_CLASSES.values():
        score: float | None = None
        if observed and len(observed) == len(hull.bands):
            error = sum((a - b) ** 2 for a, b in zip(observed, hull.bands)) / len(observed)
            score = clamp(1 - error * 1.6, 0, 1)
        elif emission:
            lines = EMISSION_LINES.get(hull.contactType, [])
            if lines:
                reference = _spectrum_bins(lines, 7, 1.0)
                error = sum((a - b) ** 2 for a, b in zip(emission, reference)) / len(reference)
                score = clamp(1 - error * 2, 0, 1)
        if score is None:
            continue
        matches.append(
            CatalogueMatch(
                shipClass=hull.id,
                name=hull.name,
                contactType=hull.contactType,
                score=round(score, 3),
            )
        )
    matches.sort(key=lambda m: m.score, reverse=True)
    c.sensor.catalogueMatches = matches


def listen_waveform(state: GameState, contact_id: str) -> None:
    c = next((x for x in state.contacts if x.id == contact_id), None)
    if c is None or not c.everDetected:
        return
    if c.waveform is None:
        c.waveform = Waveform(progress=0, resolved=False)
    if c.waveform.resolved:
        return
    add_exposure(state, 1, "waveform listen")
    listens = math.floor(c.waveform.progress / WAVEFORM_LISTEN_PROGRESS) + 1
    c.waveform.progress = clamp(c.waveform.progress + WAVEFORM_LISTEN_PROGRESS, 0, 1)
    build_spectrum(c)
    _update_catalogue_matches(c)
    if c.waveform.progress >= 1:
        c.waveform.resolved = True
        bump_confidence(state, c, 0.16)
        log(
            state,
            "SENSORS",
            f"Waveform resolved: {c.name}'s spectrum is complete. Catalogue comparison available; identity unverified.",
            "intel",
        )
    else:
        bump_confidence(state, c, 0.02 + 0.015 * c.waveform.progress)
        log(
            state,
            "SENSORS",
            f"Listen pass {listens} on {c.name}: another line in the spectrum.",
            "info",
        )
    state.seq += 1


def _gravidar_pass(
    state: GameState, *, sharp: bool = False, made_way: bool = True
) -> tuple[int, int]:
    """One gravidar look: a mass heat map with good bearing precision and an
    OK, approximate distance.  Returns ``(reads, ghosts)``."""
    if not made_way:
        return 0, 0
    clutter = state.campaign.clutter if state.campaign.clutter is not None else 0
    ship_v = _contact_vel(state.ship.pos.z, state.ship.heading, state.ship.speed)
    reads = 0
    ghosts = 0
    for c in state.contacts:
        d = dist(state.ship.pos, c.pos)
        if d > GRAVIDAR_RANGE_KLIK:
            continue
        _block, scatter, reflect = _obstacle_shadow(state, c)
        # Gravidar sensitivity scales with relative velocity: a still target pools
        # in the same gravity well and is hard to read.
        c_v = _contact_vel(c.pos.z, c.heading, c.speed)
        rel = math.hypot(c_v.x - ship_v.x, c_v.y - ship_v.y)
        factor = clamp(0.5 + rel * 0.05, 0.5, 1.5)
        if c.trueType in ENVIRONMENTAL_TYPES:
            # A whole field returns a saturated smear, not a tonnage curve.
            c.gravSaturated = True
            error = 0.85 + clutter * 2.6
        else:
            c.gravSaturated = False
            error = (0.35 + clutter * 2.6) / factor
        jitter = 1 + noise(len(c.id) * 3 + _round(state.clock), error)
        c.gravRead = _round((c.massKt * jitter) * 10) / 10
        true_b = bearing(state.ship.pos, c.pos)
        # Bearing is the precise axis; heavy hulls tighten the arc.
        tight = clamp(math.log10(max(c.massKt, 1.0)) / 2.5, 0, 1)
        half = clamp(
            (6 if sharp else 9)
            - (4 if sharp else 3) * tight
            + scatter * 16
            + reflect * 12
            + abs(noise(_round(state.clock) + len(c.id), 5)) * 6
            + clutter * 10,
            1.0,
            72,
        )
        if c.gravSaturated:
            half = clamp(half + 22, 1.5, 80)
        # Range is only "OK": a broad band, not a point.
        range_err = d * (GRAVIDAR_RANGE_ERROR + clutter * 0.5 + scatter * 0.4 + reflect * 0.2)
        if sharp:
            range_err *= 0.6
        measured_r = max(0.5, d + noise(_round(state.clock) + len(c.id), max(0.4, range_err)))
        c.sensor.gravArc = GravArc(
            bearing=wrap_bearing(true_b + noise(int(state.clock), scatter * 10)),
            halfWidth=half,
            massKt=c.gravRead,
        )
        c.sensor.gravRange = _round(measured_r * 10) / 10
        c.sensor.gravRangeError = _round(range_err * 10) / 10
        # Gravidar is a sensor in its own right: it can find a quiet hull that
        # passive never hears — but a mass return has to be worked for.  Heavy,
        # fast-crossing hulls firm up in a look or two; a distant fighter takes
        # most of a watch.  Until it is called, the arc is only a smear.
        if not c.everDetected:
            strength = clamp(tight * factor * (1 - _block), 0, 1.5)
            c.gravTail = (c.gravTail if c.gravTail is not None else 0.0) + (
                0.2 + strength
            )
            if c.gravTail >= GRAVIDAR_ACQUIRE_THRESHOLD:
                c.detected = True
                c.everDetected = True
                c.firstSeen = state.clock
                c.seenCount += 1
                bump_confidence(state, c, 0.03)
        c.lastSeen = state.clock
        if reflect > 0.45 and hash_random(_round(state.clock), 17) < reflect:
            ghosts += 1
        reads += 1
    return reads, ghosts


def _gravidar_detect(state: GameState, made_way: bool) -> None:
    """Continuous gravidar watch — on unless the ship is stopped."""
    _gravidar_pass(state, sharp=False, made_way=made_way)


def grav_scan(state: GameState) -> None:
    """Manual deep gravidar sweep: tighter arc, better range, more exposure."""
    if not _cooldown(state, "gravidar", 15):
        return
    add_exposure(state, EXPOSE_GRAVIDAR, "gravidar sweep")
    reads, ghosts = _gravidar_pass(
        state, sharp=True, made_way=state.ship.speed > 0.01
    )
    result = station_check(state, "Technology", action="grav_scan")
    if result.outcome == "critical-success":
        for x in state.contacts:
            if x.everDetected:
                bump_confidence(state, x, 0.02)
        log(
            state,
            "SENSORS",
            "Mass arcs are clean — a firm gravidar look, cross-checked.",
            "ok",
        )
    elif result.outcome == "critical-failure":
        ghosts += 1
        log(
            state,
            "SENSORS",
            "The array returned a false mass — treat this sweep as noise.",
            "warn",
        )
    saturated = sum(1 for c in state.contacts if c.gravSaturated)
    log(
        state,
        "SENSORS",
        f"Gravar sweep: {reads} mass arc{'' if reads == 1 else 's'} across the bearings"
        + (f", {ghosts} false arc(s) from reflective terrain" if ghosts else "")
        + (
            f" — {saturated} saturated by field terrain. Trust the waveform board, not the masses."
            if saturated
            else " — but the debris field is lying to us. Treat the reads as noise."
            if state.campaign.clutter > 0.6
            else " resolved. Range is approximate."
        ),
        "warn" if (saturated or (state.campaign.clutter or 0) > 0.6 or ghosts) else "ok",
    )
    state.seq += 1


RADS_PER_DEG = math.pi / 180


def _contact_vel(z: float, heading: float, speed: float) -> Vec:
    r = heading * RADS_PER_DEG
    return Vec(x=math.sin(r) * speed, y=math.cos(r) * speed, z=0)


def _active_pass(state: GameState, *, strong: bool) -> tuple[int, int]:
    """One active-radar look.  ``strong`` is the manual high-power ping."""
    hit = 0
    ghosts = 0
    for c in state.contacts:
        block, scatter, reflect = _obstacle_shadow(state, c)
        d = dist(state.ship.pos, c.pos)
        c.sensor.obstructed = block
        # Radar sees cross-section, not emissions: a low-profile hull hides even
        # from an active sweep, while a big field gives a fat return.
        if c.trueType in ENVIRONMENTAL_TYPES:
            profile = clamp((c.radiusKlik or 8.0) / 20.0, 0.2, 1.0)
        else:
            profile = c.profile
        reach = ACTIVE_SWEEP_RANGE_KLIK * (0.4 + 0.6 * profile) * (1 - 0.7 * block)
        reach *= _layer_penalty(state, c) * env_factor(state, "sensor")
        if strong:
            reach *= 1.15
        if d > reach:
            continue
        hit += 1
        c.detected = True
        c.everDetected = True
        c.lastSeen = state.clock
        c.seenCount += 1
        true_b = bearing(state.ship.pos, c.pos)
        elev = elevation(state.ship.pos, c.pos)
        # Active gives *good* precision: tight range and bearing.
        measured = max(
            0.5,
            d
            + noise(
                _round(state.clock) + len(c.id),
                (0.5 if strong else 0.9)
                * (1 + scatter * 0.22)
                * (1 + abs(noise(int(state.clock), 3))),
            ),
        )
        meas_b = wrap_bearing(true_b + noise(int(state.clock), (0.6 if strong else 1.2) + scatter * 15))
        c.sensor.activeRange = _round(measured * 10) / 10
        c.sensor.activeBearing = meas_b
        c.sensor.activeElev = elev
        c.bearingHistory.append(
            BearingSample(
                t=state.clock,
                bearing=meas_b,
                range=_round(measured),
                elev=elev,
                source="active",
            )
        )
        bump_confidence(state, c, 0.12 if strong else 0.03)
        c.estimated = Vec(
            x=state.ship.pos.x + math.sin((meas_b * math.pi) / 180) * measured,
            y=state.ship.pos.y + math.cos((meas_b * math.pi) / 180) * measured,
            z=state.ship.pos.z + math.sin((elev * math.pi) / 180) * measured,
        )
        if strong:
            log(
                state,
                "SENSORS",
                f"Radar return: {c.name} at {_round(measured)} klik"
                + (f" (scattered ±{_round(scatter * 20)}%)" if scatter > 0.3 else "")
                + f", bearing {_round(meas_b):03d}, {'+' if elev >= 0 else ''}{_round(elev)}°.",
                "info",
            )
        # A hard reflection throws a ghost bearing off the mirror — ice does this.
        ghost_chance = reflect * (1.0 if strong else 0.5)
        if reflect > 0.4 and hash_random(int(state.clock), 23) < ghost_chance:
            ghosts += 1
            ghost_b = wrap_bearing(true_b + 180 + noise(int(state.clock), 8))
            c.bearingHistory.append(
                BearingSample(t=state.clock, bearing=ghost_b, source="active")
            )
            if strong:
                log(
                    state,
                    "SENSORS",
                    f"Ghost return on {c.name}: a mirror-image bearing {_round(ghost_b):03d} — "
                    "ice is refracting the sweep.",
                    "warn",
                )
    return hit, ghosts


def _active_detect(state: GameState) -> None:
    """Continuous active watch — only while the crew has keyed the radar."""
    if not state.ship.activeSensor or _system_down(state, "radar"):
        return
    if state.ship.battery < BATTERY_MIN_ACTIVE:
        state.ship.activeSensor = False
        state.ship.emcon.radar = False
        log(state, "SENSORS", "Radar stowed — battery reserve is below the active threshold.", "warn")
        return
    _active_pass(state, strong=False)


def active_sweep(state: GameState) -> None:
    """Manual high-power radar ping: sharper fixes, but it shouts your position."""
    if _system_down(state, "radar"):
        log(state, "SENSORS", "High-power ping refused — the radar is down.", "warn")
        state.seq += 1
        return
    if state.ship.battery < BATTERY_MIN_ACTIVE:
        log(state, "SENSORS", "High-power ping refused — battery reserve is too low.", "warn")
        state.seq += 1
        return
    if not _cooldown(state, "activeSweep", 20):
        return
    hazard_exposure = sum(
        h.exposure * h.intensity
        for h in state.campaign.hazards
        if h.startMinute <= state.clock
        and (h.endMinute is None or state.clock <= h.endMinute)
    )
    add_exposure(state, EXPOSE_RADAR + hazard_exposure, "radar sweep — active emitter")
    place_datum(state, "our own high-power ping")
    state.ship.battery = clamp(
        state.ship.battery - BATTERY_ACTIVE_SWEEP_COST, 0, 100
    )
    hit, ghosts = _active_pass(state, strong=True)
    result = station_check(state, "Technology", action="active_sweep")
    if result.outcome == "critical-success":
        near = min(
            (x for x in state.contacts if x.everDetected),
            key=lambda x: dist(x.pos, state.ship.pos),
            default=None,
        )
        if near is not None:
            bump_confidence(state, near, 0.05)
        log(
            state,
            "SENSORS",
            "Sweep resolution is clean — the operator pulled a firm fix out of the return.",
            "ok",
        )
    elif result.outcome == "critical-failure":
        ghosts += 1
        add_exposure(state, 2, "misread sweep")
        log(
            state,
            "SENSORS",
            "The operator called a return that was not there — the board is lying.",
            "warn",
        )
    log(
        state,
        "SENSORS",
        f"Sweep complete — {hit} ranged fix{'' if hit == 1 else 'es'}"
        + (f" and {ghosts} false return(s)" if ghosts else "")
        + ". Anyone listening now knows roughly where you are.",
        "warn" if hit > 0 else "ok",
    )
    if hit > 0:
        state.events.append(make_event(state, "probe"))
    state.seq += 1


def _em_quality(state: GameState, c: Contact) -> float:
    """EM/motion sensing confidence (0..1).

    Always on, but sun glare along the line of sight and any asteroid/debris/
    dust field it has to look through scramble the drive-plume return.
    """
    q = EM_BASE_QUALITY
    sun = state.campaign.sun
    if sun is not None:
        glare = abs(
            bearing_diff(
                bearing(state.ship.pos, c.pos),
                bearing(state.ship.pos, sun),
            )
        )
        if glare < EM_SUN_GLARE_DEG:
            q *= 1 - EM_SUN_SCRAMBLE * (1 - glare / EM_SUN_GLARE_DEG)
    block, scatter, _reflect = _obstacle_shadow(state, c)
    q *= 1 - min(0.95, scatter * EM_TERRAIN_SCRAMBLE + block * 0.4)
    # Our own crybaby is the loudest emitter in the neighbourhood.
    if state.noisemakerTurns > 0:
        q *= NOISEMAKER_SELF_EM
    return clamp(q, 0, 1)


def _em_detect(state: GameState) -> None:
    """EM/motion watch: read each detected contact's course and speed."""
    for c in state.contacts:
        if c.trueType in ENVIRONMENTAL_TYPES or not c.everDetected:
            continue
        q = _em_quality(state, c)
        c.sensor.emQuality = _round(q * 100) / 100
        if q < EM_LOST_QUALITY:
            c.sensor.emCourse = None
            c.sensor.emSpeed = None
            continue
        err = 1 - q
        c.sensor.emCourse = wrap_bearing(
            c.heading + noise(_round(state.clock) + len(c.id), 45 * err)
        )
        c.sensor.emSpeed = max(
            0.0,
            _round(
                (c.speed + noise(_round(state.clock) * 2 + len(c.id), 30 * err)) * 10
            )
            / 10,
        )


def sniff(state: GameState) -> None:
    found = 0
    for c in state.contacts:
        if not c.emitting:
            continue
        d = dist(state.ship.pos, c.pos)
        if d > PASSIVE_BASE_RANGE_KLIK * 1.4:
            continue
        is_search = c.trueType in ("escort", "capship", "fighter")
        c.detected = True
        c.everDetected = True
        found += 1
        label = "search radar" if is_search else "navigational radar"
        b = bearing(state.ship.pos, c.pos)
        el = elevation(state.ship.pos, c.pos)
        log(
            state,
            "EW",
            f"Emitter intercepted at bearing {_round(b):03d}"
            f"{'+' if el >= 0 else ''}{_round(el)}°: {c.name} on {label}.",
            "intel",
        )
        if is_search and c.trueType in ("escort", "capship"):
            c.guess = c.trueType
            bump_confidence(state, c, 0.2)
    log(
        state,
        "EW",
        "Sweep clean — no emitters up in range."
        if found == 0
        else f"Sweep complete — {found} emitter(s) tagged.",
        "intel" if found else "ok",
    )


def call_iff(state: GameState, contact_id: str, *, free: bool = False) -> None:
    """Interrogate a track's transponder.

    A legitimate hull answers cleanly and earns trust; a hostile may squawk a
    false type, answer truly and then go dark, or be caught lying.  Repeat
    challenges and a resolved spectrum both raise the odds of unmasking a spoof,
    so an interrogator who works a track is rewarded.  ``free`` is set when the
    challenge rides on an event outcome and should not charge its own exposure.
    """
    c = next((x for x in state.contacts if x.id == contact_id), None)
    if c is None or not c.everDetected:
        return
    if _system_down(state, "comms"):
        log(state, "COMMS", "Transmitter is down — no challenge can be sent.", "warn")
        state.seq += 1
        return
    if not free:
        add_exposure(state, EXPOSE_CLOSE_IFF, "IFF challenge sent")
    c.iffChallenges += 1
    # The signal work is itself a Check; a sharp operator (or a botched read)
    # tilts the spoof contest.
    comms = station_check(state, "Translate", action="iff", contact_id=c.id)
    comms_bias = {"critical-success": 0.35, "critical-failure": -0.35}.get(
        comms.outcome, 0.0
    )
    if not c.hostile:
        c.guess = c.trueType
        c.spoofDetected = False
        c.iffConfidence = clamp(c.iffConfidence + IFF_CONFIDENCE_LEGIT, 0, 1)
        bump_confidence(state, c, 0.3)
        log(
            state,
            "COMMS",
            f"{c.name} answers the challenge as {c.trueType.upper()} — legitimate. "
            f"Transponder confidence {_round(c.iffConfidence * 100)}%.",
            "ok",
        )
        return
    # A hostile: pick what the transponder does, then whether the gear sees
    # through it.  Each prior challenge and a resolved spectrum sharpen the ear.
    squawks_decoy = hash_random(state.clock, 7) < 0.55
    detect_chance = (
        IFF_SPOOF_DETECT_BASE
        + IFF_SPOOF_DETECT_PER_CHALLENGE * (c.iffChallenges - 1)
        + (
            IFF_SPOOF_DETECT_SPECTRUM
            if c.waveform is not None and c.waveform.resolved
            else 0.0
        )
    )
    detect_chance = clamp(detect_chance + comms_bias, 0.0, 1.0)
    if hash_random(state.clock, 17) < detect_chance:
        c.spoofDetected = True
        c.iffConfidence = 0.0
        c.guess = c.trueType
        bump_confidence(state, c, 0.2)
        log(
            state,
            "COMMS",
            f"SPOOF DETECTED — {c.name}'s transponder does not match its spectral "
            f"signature. It is a {c.trueType.upper()} flying a false flag.",
            "danger",
        )
    elif squawks_decoy:
        decoy: ContactType = "freighter" if c.trueType == "escort" else "prospector"
        c.guess = decoy
        c.iffConfidence = clamp(c.iffConfidence + IFF_CONFIDENCE_DECOY, 0, 1)
        bump_confidence(state, c, 0.06)
        log(
            state,
            "COMMS",
            f"{c.name} answers as {decoy.upper()} — the transponder squawks "
            "cattle-class. Could be honest traffic; could be a coat.",
            "comms",
        )
    else:
        c.guess = c.trueType
        c.iffConfidence = clamp(c.iffConfidence + IFF_CONFIDENCE_DARK, 0, 1)
        bump_confidence(state, c, 0.24)
        log(
            state,
            "COMMS",
            f"{c.name} answers as {c.trueType.upper()} — then goes comms-DARK. Suspicious.",
            "danger",
        )


def intercept_comms(state: GameState) -> None:
    add_exposure(state, 2, "communications intercept")
    target = next((c for c in state.contacts if c.hostile and c.emitting), None)
    if target is not None:
        log(
            state,
            "COMMS",
            f"Intercept on {target.name}: procedural traffic, convoy frequency. Direction "
            f"confirms bearing "
            f"{_round(bearing(state.ship.pos, target.pos)):03d}.",
            "intel",
        )
        if target.trueType == "fighter":
            target.guess = "fighter"
        else:
            target.guess = "escort"
        bump_confidence(state, target, 0.12)
    else:
        log(state, "COMMS", "Net quiet. Routine nav traffic only.", "ok")


def transmit_comms(state: GameState, mode: str) -> None:
    if _system_down(state, "comms"):
        log(state, "COMMS", "Transmitter is down — nothing can be sent.", "warn")
        state.seq += 1
        return
    if mode == "open" and env_factor(state, "comms") < 0.5:
        log(
            state,
            "COMMS",
            f"The {environment_spec(state.environment).name} drowns the relay — "
            "long-range traffic is impossible here.",
            "warn",
        )
        state.seq += 1
        return
    if mode == "open" and not comms_window_open(state):
        # Short-range directional modes still work; a long-range broadcast
        # without the relay window is heard by everyone.
        log(
            state,
            "COMMS",
            "No relay window — a long-range broadcast now would be heard by the "
            "wrong people. Go quiet or wait for the window.",
            "warn",
        )
        state.seq += 1
        return
    costs: dict[str, tuple[int, LogEntryType]] = {
        "tight-beam": (2, "intel"),
        "burst": (5, "comms"),
        "open": (10, "danger"),
        "spoof": (7, "danger"),
    }
    exposure, level = costs.get(mode, costs["tight-beam"])
    add_exposure(state, exposure, f"{mode} transmission")
    if mode == "spoof":
        state.war.tension = clamp(state.war.tension + 6, 0, 100)
        log(state, "COMMS", "Spoofed orders transmitted. Someone out there is listening.", level)
    else:
        log(state, "COMMS", f"{mode.replace('-', ' ').title()} transmission sent; signature exposure +{exposure}.", level)


def _refuse_solution(state: GameState, c: Contact, spec: Any, reason: str) -> None:
    """The selected mount cannot hold a solution on this track: hold at STANDBY."""
    state.ship.weaponsState = "standby"
    state.ship.roe = "safe"
    state.ship.weapon = spec.id
    state.ship.solutionQuality = 0.0
    state.ship.weaponTarget = c.id
    add_exposure(state, 1, "weapons standby")
    log(
        state,
        "WEAPONS",
        f"{spec.name}: no solution on {c.name} — {reason}. Holding at STANDBY.",
        "warn",
    )


def prep_weapons(
    state: GameState,
    contact_id: str,
    weapons_state: WeaponsState = "armed",
    weapon: str | None = None,
    shot: ShotType = "quick",
) -> None:
    """Dress a mount and build a firing solution on a tracked contact.

    ``weapon`` picks the mount (defaults to the laser cannon); ``shot`` chooses
    between a quick shot — which waives part of the mount's requirement but is
    charged extra exposure — and a refined shot, which adds margin to the
    solution.  Each mount has its own envelope and required grade, so a torpedo
    on an unconfirmed distant track is refused where a gun would happily lock.
    """
    c = next((x for x in state.contacts if x.id == contact_id), None)
    if c is None or not c.everDetected:
        return
    if shot not in ("quick", "refined"):
        shot = "quick"
    spec = weapon_spec(weapon)
    rng = dist(state.ship.pos, c.pos)
    spectrum = c.waveform is not None and c.waveform.resolved
    grade = solution_grade(c.confidence, spectrum, shot)
    required = spec.solutionRequired - (QUICK_SHOT_RELIEF if shot == "quick" else 0.0)

    if _system_down(state, "guns") or _system_down(state, "ordnance"):
        log(state, "WEAPONS", "The mounts are down — no solution can be built.", "warn")
        state.seq += 1
        return
    # A mount has to bear on the target: arcs are not a formality.  We gate on
    # the mount *kind* rather than the exact weapon, so a hull with no mount of
    # that kind falls back to the legacy catalogue behaviour.
    hp_kinds = {hp.kind for hp in state.ship.hardpoints}
    if state.ship.hardpoints and spec.kind in hp_kinds:
        offset = bearing_diff(bearing(state.ship.pos, c.pos), state.ship.heading)
        bears = [
            hp
            for hp in state.ship.hardpoints
            if hp.kind == spec.kind and fits_arc(hp.arc, offset)
        ]
        if not bears:
            log(
                state,
                "WEAPONS",
                f"No {spec.name} mount bears on {c.name} from this bearing — the "
                "shot is masked by the hull.",
                "warn",
            )
            state.seq += 1
            return
    if weapons_state in ("armed", "locked") and state.ship.alert != "one":
        # Bringing mounts up is bringing the ship to action stations.
        set_alert(state, "one")
        if state.ship.alert != "one":
            log(
                state,
                "WEAPONS",
                "Cannot prepare a solution — the ship cannot reach Condition One.",
                "warn",
            )
            return
    if weapons_state in ("armed", "locked"):
        if spec.requiresConfirmed and c.state != "confirmed":
            _refuse_solution(state, c, spec, "the track is not CONFIRMED")
            return
        if rng > spec.rangeKlik:
            _refuse_solution(
                state,
                c,
                spec,
                f"range {_round(rng)} klik is outside its "
                f"{_round(spec.rangeKlik)}-klik envelope",
            )
            return
        if grade < required:
            _refuse_solution(
                state,
                c,
                spec,
                f"the {_round(grade * 100)}% solution is short of the "
                f"{_round(required * 100)}% it needs",
            )
            return

    state.ship.weaponsState = weapons_state
    state.ship.weapon = spec.id
    state.ship.solutionQuality = grade
    state.ship.shotType = shot
    state.ship.weaponTarget = c.id
    # The live shooting problem, so the weapons panel can show the EHD before
    # anything leaves the app.
    state.ship.weaponEhd = compute_ehd(
        target_hd=hull_hd(c.profile, c.stealth),
        tactical=skill_modifier(skill_score(state, "comms", "Targeting"))
        - state.ship.maneuverGunnery,
        kind=spec.kind,
        distance_klik=rng,
        solution_quality=grade,
    )
    state.ship.roe = "hold" if c.hostile and weapons_state in ("armed", "locked") else "safe"
    shot_exposure = QUICK_SHOT_EXPOSURE if shot == "quick" else REFINED_SHOT_EXPOSURE
    if weapons_state == "locked":
        add_exposure(state, spec.lockExposure + shot_exposure, "weapons lock")
    elif weapons_state == "armed":
        add_exposure(state, spec.lockExposure * 0.4 + shot_exposure, "weapons armed")
    log(
        state,
        "WEAPONS",
        f"Solution {weapons_state.upper()} — {spec.name}, {shot} shot, "
        f"{_round(grade * 100)}% on {c.name} at {_round(rng)} klik. "
        + (
            "Contact flagged HOSTILE — RoE to HOLD."
            if c.hostile
            else "Contact is not flagged hostile; RoE stays SAFE."
        ),
        "weapons",
    )


def standdown_weapons(state: GameState) -> None:
    state.ship.roe = "safe"
    state.ship.weaponsState = "safe"
    state.ship.weapon = ""
    state.ship.solutionQuality = 0.0
    state.ship.shotType = "quick"
    state.ship.weaponTarget = ""
    state.ship.weaponTargetSystem = ""
    state.ship.weaponEhd = None
    state.subsystemCheck = None
    log(state, "WEAPONS", "Firing solution stood down. RoE to SAFE.", "ok")
    state.seq += 1


def inspect_dc(state: GameState) -> None:
    """A preventive Damage Control round, resolved on the chief's skill.

    A Check decides how much readiness the watch finds (or loses): a critical
    success finds margin, a critical failure disturbs something.  Per-system
    repair arrives with the system-damage model in Phase 3.
    """
    result = station_check(state, "Damage Control", action="dc")
    delta = {
        "critical-success": 4,
        "success": 2,
        "failure": 0,
        "critical-failure": -3,
    }[result.outcome]
    state.ship.readiness = clamp(state.ship.readiness + delta, 0, 100)
    note = {
        "critical-success": "The chief found margin nobody expected.",
        "success": "Systems steady.",
        "failure": "Nothing to fix, and the watch spent the time looking.",
        "critical-failure": "A sullen coolant loop was disturbed — margin lost.",
    }[result.outcome]
    log(
        state,
        "DC",
        f"Preventive check complete. Readiness {_round(state.ship.readiness)}%. {note}",
        check_log_type(result),
    )
    state.seq += 1


def add_note(state: GameState, who: str, text: str) -> None:
    log(state, who, text, "rp")


def set_seat_skills(
    state: GameState,
    seat: SeatId,
    scores: dict[str, int] | None = None,
    specializations: dict[str, int] | None = None,
) -> bool:
    """The GM authors a station's crew skills, in WCRPG 0-99 scores.

    Returns ``False`` for an unknown seat; scores are clamped and unknown skill
    names are kept (the catalogue may grow) but ignored by lookups until known.
    """
    block = state.seats.get(seat)
    if block is None:
        return False
    cleaned = {
        str(k): int(clamp(int(v), 0, 99)) for k, v in (scores or {}).items()
    }
    spec = {
        str(k): int(clamp(int(v), 0, 99)) for k, v in (specializations or {}).items()
    }
    # Merge: a GM editing one skill must not wipe the rest of the station.
    merged_scores = dict(block.skills.scores) if block.skills else {}
    merged_scores.update(cleaned)
    merged_spec = dict(block.skills.specializations) if block.skills else {}
    merged_spec.update(spec)
    block.skills = SeatSkills(scores=merged_scores, specializations=merged_spec)
    state.seq += 1
    log(
        state,
        "GM",
        f"{block.title} crew skills set ({len(cleaned)} score(s)).",
        "rp",
    )
    return True


def resolve_event(state: GameState, event_id: str, option_id: str) -> None:
    ev = next((e for e in state.events if e.id == event_id), None)
    if ev is None:
        return
    opt = next((o for o in ev.options if o.id == option_id), None)
    if opt is None:
        return
    _apply_effect(state, opt.effect, ev)
    state.events = [e for e in state.events if e.id != event_id]
    state.seq += 1


def _relay_traffic(state: GameState) -> None:
    """Bounce a transmission through a relay: the relay carries the signature."""
    state.ship.exposure = clamp(state.ship.exposure - 6, 0, 100)
    log(
        state,
        "COMMS",
        "Traffic relayed through the net — our own transmitter stayed cold. "
        "Signature exposure −6.",
        "intel",
    )


def _spawn_civilian(state: GameState) -> Contact | None:
    """A neutral civilian hull wanders into the patrol box."""
    center = state.campaign.patrol.center
    radius = max(20.0, state.campaign.patrol.radiusKlik * 0.4)
    a = hash_random(state.clock, 23) * 360
    rad = math.radians(a)
    ctype: ContactType = (
        "freighter" if hash_random(state.clock, 29) < 0.5 else "prospector"
    )
    template = ContactTemplate(
        x=_round(center.x + math.sin(rad) * radius),
        y=_round(center.y + math.cos(rad) * radius),
        heading=wrap_bearing(a + 180),
        speed=int(CRUISE_KPS * 0.6),
        type=ctype,
        faction="neutral",
        hostile=False,
        emitting=True,
        shipClass="friendly-transport" if ctype == "freighter" else "friendly-prospector",
    )
    c = spawn_opposition(state, template)
    log(
        state,
        "COMMS",
        f"Civilian traffic: a {describe_type(ctype)} is crossing the box on its "
        "own schedule. It has no business here and no escort.",
        "comms",
    )
    return c


def _false_surrender(state: GameState, contact_id: str | None = None) -> None:
    """Resolve a surrender call: genuine prize or a knife in a smiling hand."""
    c = next((x for x in state.contacts if x.id == contact_id), None)
    if c is None:
        candidates = [x for x in state.contacts if x.everDetected and x.hostile]
        if not candidates:
            log(
                state,
                "WEAPONS",
                "The surrender call came from a track we cannot place. Treat it as noise.",
                "warn",
            )
            return
        c = min(candidates, key=lambda x: x.confidence)
    if hash_random(state.clock, 41) < 0.5:
        # Genuine: the hull is out of the fight.
        bump_confidence(state, c, 0.25)
        c.hostile = False
        c.faction = "neutral"
        state.ship.roe = "safe"
        state.ship.weaponsState = "safe"
        state.ship.solutionQuality = 0.0
        state.ship.weaponTarget = ""
        log(
            state,
            "WEAPONS",
            f"{c.name} heaves to — the surrender is genuine. Weapons back to SAFE.",
            "ok",
        )
        return
    # A trap: a close escort breaks cover while the crew closed to board.
    p = state.ship.pos
    trap = ContactTemplate(
        x=_round(p.x + 6),
        y=_round(p.y + 6),
        heading=wrap_bearing(c.heading + 180),
        speed=FLANK_KPS,
        type="fighter",
        faction="enemy",
        hostile=True,
        emitting=True,
        shipClass="enemy-fighter",
    )
    contact = spawn_opposition(state, trap)
    state.war.tension = clamp(state.war.tension + 6, 0, 100)
    log(
        state,
        "WEAPONS",
        f"Trap — {c.name}'s surrender was a coat for a close escort breaking cover."
        + (f" {contact.name} is on you." if contact is not None else ""),
        "danger",
    )


def _apply_effect(state: GameState, effect: EventEffect, ev: DecisionEvent) -> None:
    if effect.exposure:
        add_exposure(state, effect.exposure, "event decision")
    if effect.tension:
        state.war.tension = clamp(state.war.tension + effect.tension, 0, 100)
    if effect.log:
        log(state, "EVENT", effect.log.replace("$NAME", ev.title), "rp")
    if effect.launchContacts:
        for t in effect.launchContacts:
            state.contacts.append(
                instantiate_contact(
                    t,
                    len(state.contacts),
                    state.campaign,
                    track_number=len(state.contacts) + 1,
                    used_names={c.trueName for c in state.contacts},
                )
            )
    if effect.loseTrack:
        _drop_track(state, effect.targetId)
    if effect.relay:
        _relay_traffic(state)
    if effect.challenge:
        target = effect.targetId
        if not target:
            seen = [x for x in state.contacts if x.everDetected]
            target = (
                min(seen, key=lambda x: dist(x.pos, state.ship.pos)).id
                if seen
                else None
            )
        if target:
            # The challenge rides on the event: no extra exposure of its own.
            call_iff(state, target, free=True)
    if effect.civilian:
        _spawn_civilian(state)
    if effect.falseSurrender:
        _false_surrender(state, effect.targetId)
    if effect.handoff:
        # The engagement prompt promises a handoff; actually build it, pause the
        # patrol, and let the fight resolve off-app.
        force_handoff(state, "COMMAND", effect.targetId)


def force_handoff(state: GameState, actor: str, contact_id: str | None = None) -> None:
    c = sorted(
        (x for x in state.contacts if x.everDetected),
        key=lambda x: dist(x.pos, state.ship.pos),
    )
    if not c:
        log(state, actor, "No tracked contact to hand over. Stand by or advance time.", "warn")
        return
    target = next((x for x in c if x.id == contact_id), None) or c[0]
    state.handoffPack = build_handoff_pack(state, target)
    standdown_weapons(state)
    state.status = "handoff"
    state.seq += 1
    log(
        state,
        "COMMAND",
        f"Patrol PAUSED — combat handoff generated for {target.name}. Resolve your fight "
        f"off-app, then resume.",
        "danger",
    )


def resume_after_handoff(state: GameState) -> None:
    if state.status != "handoff":
        return
    state.status = "running"
    state.clock += 240
    state.ship.readiness = clamp(state.ship.readiness - 6, 0, 100)
    state.handoffPack = None
    for c in state.contacts:
        c.confidence = clamp(c.confidence - 0.25, 0, 1)
        c.state = state_of_confidence(c.confidence)
    log(
        state,
        "COMMAND",
        f"Patrol resumed. {format_clock(state.clock)}. Damage control repairs underway; "
        f"readiness {_round(state.ship.readiness)}%.",
        "ok",
    )
    state.seq += 1


def end_campaign(state: GameState) -> None:
    state.status = "ended"
    state.endReason = "Campaign ended by Command."
    state.digest = build_digest(state)
    state.seq += 1
    log(
        state,
        "COMMAND",
        f"Campaign ended. {len(state.log)} log entries filed. The war keeps rolling without you.",
        "rp",
    )


def build_digest(state: GameState) -> LogbookDigest:
    seen = [c for c in state.contacts if c.everDetected]
    classified = [
        c for c in seen if c.state != "unknown" and (c.guess != "unknown" or c.state == "confirmed")
    ]
    hostile = [c for c in seen if c.hostile and c.state == "confirmed"]
    handoffs = len([e for e in state.log if "handoff generated" in e.text])
    rp_notes = len(
        [
            e
            for e in state.log
            if e.type == "rp" and e.source not in ("EVENT", "COMMAND", "WEAPONS")
        ]
    )
    return LogbookDigest(
        title=state.campaign.title,
        theater=state.campaign.theater,
        durationMinutes=state.clock - state.campaign.startHour * 60,
        contactsSeen=len(seen),
        classifiedCount=len(classified),
        hostileConfirmed=len(hostile),
        handoffs=handoffs,
        rpNotes=rp_notes,
        generatedAt=state.clock,
        outcome=state.outcome,
        xp=state.xp,
        reputation=_round_to(state.reputation, 1),
        medals=list(state.medals),
    )


def set_emcon(state: GameState, patch: EmconPatch) -> None:
    patch = _as(EmconPatch, patch)
    old = state.ship.emcon
    state.ship.emcon = EmconnState(
        radar=patch.radar if patch.radar is not None else old.radar,
        radios=patch.radios if patch.radios is not None else old.radios,
        optics=patch.optics if patch.optics is not None else old.optics,
    )
    state.seq += 1


def set_active_sensor(state: GameState, active: bool) -> None:
    """Key or stow the active radar.

    Passive, gravidar and EM keep running either way — active is the only part
    of the fit that switches.  Keying it also raises the radar emitter, so the
    steady-state exposure drift charges for it.
    """
    if state.ship.activeSensor == active:
        return
    if (
        active
        and state.jumpState is not None
        and state.jumpState.spooling
    ):
        log(
            state,
            "SENSORS",
            "Radar is off-line — power is diverted to the jump drive.",
            "warn",
        )
        state.seq += 1
        return
    if active and _system_down(state, "radar"):
        log(state, "SENSORS", "Radar is down — the set will not key.", "warn")
        state.seq += 1
        return
    if active and state.ship.battery < BATTERY_MIN_ACTIVE:
        log(
            state,
            "SENSORS",
            f"Battery at {_round(state.ship.battery)}% — not enough charge to key the "
            f"radar. Run quiet or hold station to recover.",
            "warn",
        )
        state.seq += 1
        return
    state.ship.activeSensor = active
    state.ship.emcon = EmconnState(
        radar=active,
        radios=state.ship.emcon.radios,
        optics=state.ship.emcon.optics,
    )
    log(
        state,
        "SENSORS",
        "Active radar keyed — precise fixes, and every receiver sees you."
        if active
        else "Active radar stowed — passive, gravidar and EM still running.",
        "warn" if active else "ok",
    )
    state.seq += 1


def set_waypoints(state: GameState, waypoints: list[Vec]) -> None:
    _clear_maneuver(state, "new helm order")
    state.ship.waypoints = [
        Vec(
            x=w.x,
            y=w.y,
            z=clamp(w.z if w.z is not None else 0, 0, SHIP_ALT_MAX_KLIK),
        )
        for w in waypoints[:6]
    ]
    # Ordering a course implies making way: a ship holding station on 0 kps
    # needs her mode speed restored or she would sit at the first waypoint.
    if state.ship.waypoints and state.ship.speed <= 0.01:
        state.ship.speed = _mode_speed_for(state.ship, state.ship.mode)
        _apply_emission(state.ship)
    state.seq += 1


def set_altitude(state: GameState, z: float) -> None:
    state.ship.altTarget = clamp(z, 0, SHIP_ALT_MAX_KLIK)
    state.seq += 1


def filter_noise(state: GameState) -> None:
    cooldown = state.noiseFilterAt if state.noiseFilterAt is not None else 0
    if state.clock < cooldown:
        wait = math.ceil(cooldown - state.clock)
        log(
            state,
            "SENSORS",
            f"Noise filter is recooling — stands to in {wait} more game-minutes.",
            "info",
        )
        return
    if state.ship.battery < BATTERY_MIN_ACTIVE:
        log(
            state,
            "SENSORS",
            f"Battery at {_round(state.ship.battery)}% — the filter draws more than the "
            f"plant can spare. Recharge first.",
            "warn",
        )
        state.seq += 1
        return
    state.noise = clamp(state.noise * 0.45, NOISE_MIN, NOISE_CAP)
    state.ship.battery = clamp(
        state.ship.battery - BATTERY_NOISE_FILTER_COST, 0, 100
    )
    state.noiseFilterAt = state.clock + NOISE_FILTER_COOLDOWN
    state.seq += 1
    log(
        state,
        "SENSORS",
        f"Noise filter run: the X² background drops to {state.noise:.2f}. The passive grill "
        f"has breathing room — for a while.",
        "ok",
    )


def set_speed(state: GameState, kps: float) -> None:
    _clear_maneuver(state, "new speed order")
    ceiling = state.ship.maxSpeed
    if state.jumpState is not None and state.jumpState.spooling:
        # Hard manoeuvring is impossible with the drive charged.
        ceiling = min(ceiling, JUMP_SPOOL_MAX_SPEED)
        if kps > ceiling:
            log(
                state,
                "OPS",
                f"Speed held at {int(ceiling)} kps — the drive is spooling and the "
                "ship cannot manoeuvre hard.",
                "warn",
            )
    state.ship.speed = clamp(kps, 0, ceiling)
    state.ship.mode = (
        "max"
        if kps >= FLANK_KPS - 5
        else "quiet"
        if kps <= SILENT_KPS + 5
        else "cruise"
    )
    _apply_emission(state.ship)
    state.seq += 1


def set_mode(state: GameState, mode: OperatingMode) -> None:
    state.ship.mode = mode
    state.ship.speed = _mode_speed_for(state.ship, mode)
    _apply_emission(state.ship)
    state.seq += 1


def set_condition(state: GameState, value: Condition) -> None:
    state.ship.condition = value
    state.seq += 1
    log(state, "COMMAND", f"Condition {value.upper()}.", "warn" if value == "red" else "info")


def set_ship_class(state: GameState, ship_id: str | None) -> bool:
    """The GM dictates which hull the crew flies for this scenario."""
    klass = ship_class(ship_id)
    s = state.ship
    s.shipClass = klass.id
    s.name = ship_name(klass.id)
    s.className = klass.name
    s.cruiseSpeed = klass.cruiseSpeed
    s.maxSpeed = klass.maxSpeed
    s.quietSpeed = SILENT_KPS
    s.sensorQuality = klass.sensorQuality
    s.profile = klass.profile
    s.stealth = klass.stealth
    s.emission = klass.emission
    s.massKt = klass.massKt
    s.speed = clamp(s.speed, 0, s.maxSpeed)
    _init_loadout(s, klass)
    _apply_module_fit(state)
    _apply_emission(s)
    state.seq += 1
    log(
        state,
        "COMMAND",
        f"GM sets the crew ship to {klass.name} — profile {klass.profile:.2f}, "
        f"stealth {klass.stealth:.2f}, mass {klass.massKt:g} kt.",
        "intel",
    )
    return True


# Public alias so tests and other modules can reason about line-of-sight cover.
obstacle_shadow = _obstacle_shadow
# Public aliases for the emission model (used by tests and the GM console).
apply_emission = _apply_emission
stern_dazzle = _stern_dazzle


def ignore_contact(state: GameState, contact_id: str) -> None:
    c = next((x for x in state.contacts if x.id == contact_id), None)
    if c is None:
        return
    c.confidence = 0.01
    c.detected = False
    c.state = "unknown"
    log(
        state,
        "SENSORS",
        f"Dropped the track on {c.name}. If it circles back, you may re-acquire.",
        "info",
    )
    state.seq += 1


def report_contact(state: GameState, contact_id: str) -> None:
    """File a fleet intel report on a tracked contact (the ops seat's payoff).

    A confirmed, correctly identified contact pushes the front line out and
    bleeds tension.  A tentative or bearing-only report is worth less.  A wrong
    call actively helps the enemy, so classification has skin in the game.
    """
    c = next((x for x in state.contacts if x.id == contact_id), None)
    if c is None or not c.everDetected:
        log(state, "OPS", "Nothing on that track to report to the net.", "warn")
        state.seq += 1
        return
    if c.reported:
        log(state, "OPS", f"{c.name} is already on the net's file for this watch.", "info")
        state.seq += 1
        return

    c.reported = True
    firm = c.state == "confirmed" and c.guess == c.trueType
    if c.guess == "unknown":
        gain = FRONT_LINE_GAIN_TENTATIVE
        state.war.frontLine = clamp(state.war.frontLine + gain, 0, 100)
        log(
            state,
            "OPS",
            f"Bearing report filed on {c.name} — the net has the axis, not the "
            f"identity. Front line +{gain:g}.",
            "info",
        )
    elif firm:
        gain = FRONT_LINE_GAIN_CONFIRMED
        state.war.frontLine = clamp(state.war.frontLine + gain, 0, 100)
        state.war.tension = clamp(state.war.tension - REPORT_TENSION_RELIEF, 0, 100)
        log(
            state,
            "OPS",
            f"Fleet intel report: {c.name} confirmed {describe_type(c.trueType).upper()}. "
            f"The line moves out; the lane settles. Front line +{gain:g}.",
            "intel",
        )
    elif c.guess != c.trueType:
        loss = FRONT_LINE_LOSS_BAD_CALL
        state.war.frontLine = clamp(state.war.frontLine - loss, 0, 100)
        state.war.tension = clamp(state.war.tension + 2, 0, 100)
        log(
            state,
            "OPS",
            f"The net flags your report on {c.name}: the plot does not match the "
            f"traffic picture. Front line -{loss:g}.",
            "warn",
        )
    else:
        gain = FRONT_LINE_GAIN_TENTATIVE
        state.war.frontLine = clamp(state.war.frontLine + gain, 0, 100)
        log(
            state,
            "OPS",
            f"Probable identification of {c.name} filed — the net wants it "
            f"confirmed. Front line +{gain:g}.",
            "info",
        )
    state.seq += 1


# ---------------------------------------------------------------------------
# GM opposition builder (admin port)
# ---------------------------------------------------------------------------


def spawn_opposition(state: GameState, t: ContactTemplate) -> Contact | None:
    t = _as(ContactTemplate, t)
    c = instantiate_contact(
        t,
        len(state.contacts) + 1000,
        state.campaign,
        track_number=len(state.contacts) + 1,
        used_names={x.trueName for x in state.contacts},
    )
    c.id = f"gm-{uuid.uuid4().hex[:12]}"
    if t.name:
        # The GM's name is the contact's real name; the plot still shows the
        # anonymous track until the crew confirms it.
        c.trueName = t.name[:32]
    state.contacts.append(c)
    state.seq += 1
    return c


def patch_opposition(state: GameState, contact_id: str, patch: ContactPatch) -> bool:
    patch = _as(ContactPatch, patch)
    c = next((x for x in state.contacts if x.id == contact_id), None)
    if c is None:
        return False
    if patch.name:
        c.trueName = patch.name[:32]
        _reveal_contact(c, force=c.state == "confirmed")
    if patch.pos:
        c.pos = Vec(
            x=clamp(patch.pos.x, -400, 400),
            y=clamp(patch.pos.y, -400, 400),
            z=clamp(patch.pos.z if patch.pos.z is not None else c.pos.z, -400, 400),
        )
    if patch.alt is not None:
        c.pos.z = clamp(patch.alt, -400, 400)
    if patch.heading is not None:
        c.heading = wrap_bearing(patch.heading)
    if patch.speed is not None:
        c.speed = clamp(patch.speed, 0, FLANK_KPS)
    if patch.trueType:
        c.trueType = patch.trueType
        c.guess = patch.trueType
    if patch.faction:
        c.faction = patch.faction
    if patch.hostile is not None:
        c.hostile = patch.hostile
    if patch.emitting is not None:
        c.emitting = patch.emitting
    if patch.state:
        c.state = patch.state
    if patch.guess:
        c.guess = patch.guess
    if patch.shipClass:
        klass = ship_for_type(c.trueType, patch.shipClass)
        c.shipClass = klass.id
        c.profile = klass.profile
        c.stealth = klass.stealth
        c.emission = klass.emission
        c.sensorQuality = klass.sensorQuality
        c.massKt = klass.massKt
        c.frequencyProfile = list(klass.bands)
        c.image = klass.image
        c.vdu = klass.vdu
    state.seq += 1
    return True


def remove_opposition(state: GameState, contact_id: str) -> bool:
    i = next((idx for idx, c in enumerate(state.contacts) if c.id == contact_id), -1)
    if i < 0:
        return False
    del state.contacts[i]
    state.seq += 1
    return True


def gm_event(state: GameState, ev: DecisionEvent) -> None:
    ev = _as(DecisionEvent, ev)
    state.events = [*state.events, ev]
    state.seq += 1


__all__ = [
    "MASS_KT",
    "create_state",
    "instantiate_contact",
    "build_spectrum",
    "environmental_name",
    "ASTEROID_FIELD_NAMES",
    "NEBULA_NAMES",
    "DEBRIS_NAMES",
    "DUST_NAMES",
    "ICE_NAMES",
    "obstacle_shadow",
    "apply_emission",
    "stern_dazzle",
    "set_ship_class",
    "set_time_frozen",
    "ship_briefs",
    "WAYPOINT_ARRIVE_KLIK",
    "log",
    "advance",
    "bump_confidence",
    "add_exposure",
    "build_handoff_pack",
    "claim_contact",
    "listen_waveform",
    "grav_scan",
    "active_sweep",
    "sniff",
    "call_iff",
    "intercept_comms",
    "prep_weapons",
    "inspect_dc",
    "add_note",
    "resolve_event",
    "force_handoff",
    "resume_after_handoff",
    "end_campaign",
    "build_digest",
    "set_emcon",
    "set_active_sensor",
    "set_alert",
    "set_waypoints",
    "set_altitude",
    "filter_noise",
    "spool_jump",
    "commit_jump",
    "abort_jump",
    "launch_ordnance",
    "replenish",
    "set_speed",
    "set_mode",
    "ignore_contact",
    "spawn_opposition",
    "patch_opposition",
    "remove_opposition",
    "gm_event",
    "standdown_weapons",
    "set_condition",
    "phase_name",
    "deploy_buoy",
    "recover_buoy",
    "deploy_noisemaker",
    "report_contact",
    "TYPE_EASE",
    "EMISSION_BASE",
    "RADS_PER_DEG",
    "DEFAULT_ADVANCE_MINUTES",
    "AUTO_TICK_MINUTE",
    "check_salt",
    "check_text",
    "seat_for_skill",
    "set_seat_skills",
    "skill_score",
    "station_check",
]
