"""CAPTAIN shared constants.

Direct port of ``packages/shared/src/constants.ts``.
"""

from __future__ import annotations

from typing import Final, TypedDict

from .types import ContactState, ContactType, EmconnState, SeatId, SensorEffect

# Persisted state schema version. Old runs (pre-3D) are wiped on load.
# v3 removed the exclusive sensor mode in favour of an active-radar toggle.
STATE_SCHEMA_VERSION: Final = 3

CLIENT_VERSION: Final = 1

# ---- detection / sensors (klik, minutes) ----
PASSIVE_BASE_RANGE_KLIK: Final = 42
ACTIVE_SWEEP_RANGE_KLIK: Final = 34
TYPICAL_SIGHTING_RANGE_KLIK: Final = 14
ENGAGEMENT_RANGE_KLIK: Final = 28
GRAVIDAR_RANGE_KLIK: Final = 50
# Gravidar acquisition: integrated mass-return energy before a contact is
# called.  Heavy hulls and fast crossers firm up quickly; a distant fighter has
# to be worked for.
GRAVIDAR_ACQUIRE_THRESHOLD: Final = 3.0

# Higher own self-noise (emissions) shrinks your passive listening reach; lower (0) = full reach.
SELF_NOISE_SHADOW: Final = 0.35

DETECT_MINUTES: Final = 30
BEARING_DRIFT_MINUTES: Final = 45
CONTACT_DECAY_MINUTES: Final = 90

# ---- passive noise floor (see PLAN.md: X^2 background accumulation) ----
NOISE_INIT: Final = 1.5
NOISE_CAP: Final = 240
NOISE_MIN: Final = 0.8
NOISE_DEFAULT_RATE: Final = 0.0012  # per minute^2 while on watch
SELF_NOISE_BURDEN: Final = 0.03  # per minute from own emissions
# Bearing samples per minute of data-rate.  Lowered so a watch step paints less
# of the picture: a contact needs several looks before it is really there.
PASSIVE_SAMPLE_SCALE: Final = 32
# Integrated passive energy required for a first fix.  This is the main dial for
# how fast the passive picture fills in — raise it to make the watch slower.
PASSIVE_ACQUIRE_THRESHOLD: Final = 20
NOISE_FILTER_COOLDOWN: Final = 120  # game-minutes between noise-filter runs

# ---- speed scale (kps) ----
# Every ship runs on a 0-100 dial with three named settings.  The klik
# conversion is a game unit, not nautical miles, chosen so a 45-minute cruise
# tick covers about the same ground the old 8-kps scale did.
SILENT_KPS: Final = 15
CRUISE_KPS: Final = 60
FLANK_KPS: Final = 100
KLIK_PER_KPS_HOUR: Final = 0.25

# ---- sensor frequency profile ----
# Number of bands in a hull's "barcode" emission signature.
FREQ_BANDS: Final = 16

# ---- own emission model ----
# A stopped ship still radiates (plant, life support).  Silent running is
# quieter *overall* than sitting still, but it cannot hide the drive plume: the
# stern heat is higher, and that plume dazzles your own aft sensors.
#
# ``selfNoise`` (overall) is the hull baseline scaled by the mode factor;
# ``rearHeat`` is the directional stern plume, 0 when stopped.
EMISSION_MODE_FACTOR: Final[dict[str, float]] = {
    "quiet": 0.6,
    "cruise": 1.8,
    "max": 2.8,
}
STERN_HEAT_BY_MODE: Final[dict[str, float]] = {
    "quiet": 0.45,
    "cruise": 0.7,
    "max": 1.0,
}
# Contacts within this many degrees of dead astern are washed out by your own
# plume, by up to STERN_DAZZLE_STRENGTH of their signal-to-noise.
STERN_DAZZLE_ARC_DEG: Final = 40.0
STERN_DAZZLE_STRENGTH: Final = 0.65

# ---- EM / motion sensors ----
# EM sensing reads a contact's drive plume for course and speed.  It is always
# on, but sun glare and asteroid/debris/dust fields scramble it easily.
EM_BASE_QUALITY: Final = 0.85
EM_SUN_GLARE_DEG: Final = 28.0
EM_SUN_SCRAMBLE: Final = 0.9
EM_TERRAIN_SCRAMBLE: Final = 0.85
EM_LOST_QUALITY: Final = 0.12

# ---- gravidar range ----
# The gravidar resolves bearing well and distance only "OK": this is the base
# fractional range error before clutter and scatter make it worse.
GRAVIDAR_RANGE_ERROR: Final = 0.22

# ---- 3D altitude movement ----
ALTITUDE_RATE_KLIK_PER_HOUR: Final = 12
SHIP_ALT_MAX_KLIK: Final = 50

# ---- detection race: who sees whom first ----
# An enemy's track quality on *you* accumulates every watch step.  Fixing a
# firing solution (``lock`` reaching 1.0) loses the patrol.  The patrol is won
# two ways, both available while the picture is being built: every hostile is
# detected and tracked, or every hostile has cleared ``DISENGAGE_RANGE_KLIK``
# (made it through until the lane emptied).
#
# The rate is driven by your own emission (``selfNoise`` masked by hull
# stealth), your radar cross-section, whether the hunter is radiating, range
# and terrain occlusion.  Tune ``ENEMY_LOCK_MINUTES`` to make the race longer
# or shorter; it is the number of minutes a perfectly loud, close contact
# takes to be fixed.
ENEMY_LOCK_MINUTES: Final = 135
# Enemy passive reach scales with its hull's sensorQuality around this base.
ENEMY_PASSIVE_BASE_KLIK: Final = 44
# Their receivers can pick up your stern plume and radar cross-section too.
ENEMY_PROFILE_WEIGHT: Final = 0.35
# A locked track decays this much per watch step when it loses the scent.
ENEMY_LOCK_DECAY: Final = 0.08
# A hunter with at least this much of a track turns and runs us down; below it
# they keep sweeping.  Raise it to give a quiet crew more room to work.
ENEMY_PURSUE_LOCK: Final = 0.25
# A hostile this far out is off the plot: outside every sensor envelope
# (passive 42, gravidar 50, active 34 klik) and no longer a threat.  Once every
# hostile has cleared it the patrol is won — provided at least one had closed
# inside it first, so a campaign cannot start already "won".
DISENGAGE_RANGE_KLIK: Final = 120
# A hostile lock at or above this is a working track on us, not a transient
# ranging ping.  It is the "detected" line the endurance win is measured
# against, and matches the partial-track warning in ``_enemy_detect``.
DETECTED_LOCK: Final = 0.5
# Endurance win: stay dark this long without any hostile building a track
# (``everTrackedUs``) and the patrol is won — six hours undetected.
ENDURE_MINUTES: Final = 360
# Being painted: exposure spike and the hit you take getting clear.
PAINTED_EXPOSURE: Final = 22
PAINTED_HULL_DAMAGE: Final = 5
PAINTED_READINESS_DAMAGE: Final = 4

# ---- sensor buoys ----
# Dedicated passive listening posts.  Dropped from the ship's rack, immobile,
# and recoverable by the ops seat.  A second bearing from a different origin
# lets the crew cross-fix a contact it could otherwise only hear.
SENSOR_BUOY_LOADOUT: Final = 2
BUOY_PASSIVE_RANGE_KLIK: Final = 40
# A contact must be heard by two origins at least this far apart to be fixed.
BUOY_TRIANGULATION_BASELINE_KLIK: Final = 2.0
# A cross-fix is worth more confidence than another single-origin bearing.
BUOY_TRIANGULATION_CONFIDENCE: Final = 0.14

# ---- noisemakers (crybabies) ----
# Launch a decoy that floods the EM band.  Two turns of cover to run, at the
# cost of your own passive and EM hearing while it sings.
NOISEMAKER_LOADOUT: Final = 2
NOISEMAKER_TURNS: Final = 2
# Enemy lock accumulation is multiplied by this while the band is flooded.
NOISEMAKER_ENEMY_SIGNAL: Final = 0.12
# ...and your own passive / EM sensing by these.
NOISEMAKER_SELF_PASSIVE: Final = 0.4
NOISEMAKER_SELF_EM: Final = 0.5

# ---- ship's battery / readiness economies ----
BATTERY_RADAR_PER_HOUR: Final = 6.0
BATTERY_FLANK_PER_HOUR: Final = 5.0
BATTERY_RECHARGE_PER_HOUR: Final = 2.0
BATTERY_QUIET_RECHARGE_PER_HOUR: Final = 3.0
BATTERY_ACTIVE_SWEEP_COST: Final = 1.5
BATTERY_NOISE_FILTER_COST: Final = 5.0
# Below this the active radar and the noise filter cannot be run at all.
BATTERY_MIN_ACTIVE: Final = 5.0
READINESS_WEAR_MAX: Final = 0.7
READINESS_WEAR_CRUISE: Final = 0.25
READINESS_RECOVER_QUIET: Final = 0.6
READINESS_RECOVER_STOPPED: Final = 0.8

# ---- escalation ----
# Tension thresholds (matching phase_name) at which the lane sends hunters.
ESCALATION_TIERS: Final[list[float]] = [20, 45, 70]
# Inaction on an unanswered decision event costs this much tension.
EVENT_EXPIRY_TENSION: Final = 3

# ---- fleet intel reports (the ops seat's payoff) ----
# Filing a report on a properly identified contact pushes the front line our
# way and bleeds a little tension; a wrong call actively helps the enemy.
FRONT_LINE_GAIN_CONFIRMED: Final = 5.0
FRONT_LINE_GAIN_TENTATIVE: Final = 1.0
FRONT_LINE_LOSS_BAD_CALL: Final = 4.0
REPORT_TENSION_RELIEF: Final = 2.5

# ---- exposure ----
EXPOSE_RADAR: Final = 26
EXPOSE_CLOSE_IFF: Final = 6
EXPOSE_OPTICS: Final = 10
EXPOSE_GRAVIDAR: Final = 3
EXPOSE_SPEED_MAX: Final = 8
EXPOSE_DRIFT_PER_HOUR: Final = 2

# ---- IFF / transponder interrogation ----
# A legitimate hull answers cleanly and is trusted; a hostile may squawk a
# false type ("cattle-class"), answer truly and then go dark, or be caught by
# the gear.  Each repeat challenge (and any resolved spectrum) raises the odds
# of unmasking a spoof, so an interrogator who works at it is rewarded.
IFF_CONFIDENCE_LEGIT: Final = 0.85
IFF_CONFIDENCE_DARK: Final = 0.35
IFF_CONFIDENCE_DECOY: Final = 0.1
IFF_SPOOF_DETECT_BASE: Final = 0.35
IFF_SPOOF_DETECT_PER_CHALLENGE: Final = 0.25
IFF_SPOOF_DETECT_SPECTRUM: Final = 0.2

# ---- firing solutions ----
# A quick shot waives part of the mount's requirement but is charged extra
# exposure; a refined shot adds margin to the solution instead.
QUICK_SHOT_RELIEF: Final = 0.15
REFINED_SHOT_BONUS: Final = 0.12
QUICK_SHOT_EXPOSURE: Final = 2.0
REFINED_SHOT_EXPOSURE: Final = -0.5
# A resolved spectrum sharpens any mount's solution by this much.
SOLUTION_SPECTRUM_BONUS: Final = 0.05

TENSION_PER_EXPOSURE: Final = 0.9
TENSION_RELAX_PER_HOUR: Final = 4

# ---- waveform recognition ----
# Fraction of the barcode resolved per listen pass.  Lowered from 0.25 so a
# spectrum takes several passes to read — the classification game has a clock.
WAVEFORM_LISTEN_PROGRESS: Final = 0.15

# ---- tick / time ----
DEFAULT_ADVANCE_MINUTES: Final = 30
AUTO_TICK_MINUTE: Final = 60  # real seconds per auto game-minute when autoTick on

# ---- thresholds on the confidence ladder ----
CONFIDENCE_BY_STATE: Final[dict[ContactState, float]] = {
    "unknown": 0.0,
    "tracking": 0.2,
    "probable": 0.45,
    "classified": 0.7,
    "confirmed": 0.9,
}

STATE_ORDER: Final[list[ContactState]] = [
    "unknown",
    "tracking",
    "probable",
    "classified",
    "confirmed",
]

# ---- seats / hats ----
SEATS: Final[dict[SeatId, dict[str, object]]] = {
    "command": {"title": "Command", "hats": ["ops", "dc"], "primaryLabel": "Captain"},
    "ops": {"title": "Ops", "hats": ["nav", "ops", "dc"], "primaryLabel": "Navigation"},
    "sensor": {
        "title": "Sensors & EW",
        "hats": ["sensors", "ew", "dc"],
        "primaryLabel": "Sensors",
    },
    "comms": {
        "title": "Comms & Weapons",
        "hats": ["comms", "weapons", "dc"],
        "primaryLabel": "Comms",
    },
}

HAT_TITLES: Final[dict[str, str]] = {
    "nav": "Navigation",
    "ops": "Operations",
    "sensors": "Sensors",
    "ew": "Electronic Warfare",
    "comms": "Communications",
    "weapons": "Weapons (prep)",
    "dc": "Damage Control",
}

TYPE_NAMES: Final[dict[ContactType, str]] = {
    "unknown": "UNKNOWN",
    "prospector": "Prospector",
    "freighter": "Freighter",
    "liner": "Passenger liner",
    "escort": "Escort corvette",
    "capship": "Capital ship",
    "fighter": "Fighter",
    "carrier": "Carrier",
    "asteroid": "Asteroid field",
    "nebula": "Nebula",
    "debris": "Debris field",
    "dust": "Dust cloud",
    "ice": "Ice field",
}

# ---- environmental contacts / sensor obstacles ----
# These are terrain: no crew, no transponder, no manoeuvre.  They saturate the
# gravidar and return spectra that look like just about anything warm, so the
# only honest way to clear them is the waveform board.  Every obstacle also
# blocks, scatters or reflects the sensor picture (see OBSTACLE_EFFECTS).
ENVIRONMENTAL_TYPES: Final[frozenset[ContactType]] = frozenset(
    {"asteroid", "nebula", "debris", "dust", "ice"}
)

# Block attenuates line of sight; scatter injects bearing/range noise; reflect
# throws false or multipath returns.  Ice is the refracting, ghost-making one.
OBSTACLE_EFFECTS: Final[dict[ContactType, SensorEffect]] = {
    "asteroid": SensorEffect(block=0.9, scatter=0.3, reflect=0.2),
    "debris": SensorEffect(block=0.4, scatter=0.7, reflect=0.5),
    "nebula": SensorEffect(block=0.6, scatter=0.35, reflect=0.05),
    "dust": SensorEffect(block=0.45, scatter=0.8, reflect=0.1),
    "ice": SensorEffect(block=0.2, scatter=0.4, reflect=0.95),
}

# Nominal obstacle radius in klik (ships are point sources and ignore this).
OBSTACLE_RADIUS: Final[dict[ContactType, float]] = {
    "asteroid": 11.0,
    "nebula": 18.0,
    "debris": 8.0,
    "dust": 14.0,
    "ice": 10.0,
}

# A line of sight that passes within (obstacle radius * this) of a hull contact
# is considered occluded; grazing passes attenuate proportionally.
OBSTACLE_LOS_INFLUENCE: Final = 1.6

# ---- spectral analysis ----
# Number of normalized bins in a :class:`Spectrum`.  The analyzer lays the
# spectrum across this many channels; HYDROGEN_BAND is the 21-cm HI reference
# zero-mark used to read Doppler range-rate.
SPECTRUM_BINS: Final = 32
HYDROGEN_BAND: Final = 0.78

# A spectral feature is ``(band_name, position_0_to_1, strength_0_to_1)``.
SpectralFeature = tuple[str, float, float]

# Self-radiated lines (drive plants, fusion cores, excited gas).
EMISSION_LINES: Final[dict[ContactType, list[SpectralFeature]]] = {
    "unknown": [],
    "prospector": [("fusion hum", 0.22, 0.55), ("drive harmonics", 0.5, 0.3)],
    "freighter": [("plasma vent", 0.18, 0.42), ("cargo-deck hum", 0.44, 0.5)],
    "liner": [("reactor hum", 0.3, 0.5), ("hotel load", 0.62, 0.36)],
    "escort": [("military fusion", 0.26, 0.68), ("radar sidelobe", 0.7, 0.4)],
    "capship": [("fusion spine", 0.24, 0.9), ("main reactor", 0.52, 0.78)],
    "fighter": [("afterburner", 0.34, 0.72), ("cannon capacitor", 0.6, 0.45)],
    "carrier": [("flight-deck plant", 0.2, 0.7), ("launch catapults", 0.46, 0.55), ("hangar traffic", 0.68, 0.4)],
    "asteroid": [],
    "nebula": [("H-alpha", 0.62, 0.85), ("O III", 0.48, 0.62), ("S II", 0.72, 0.4)],
    "debris": [("residual heat", 0.4, 0.22)],
    "dust": [("warm grains", 0.34, 0.3), ("IR excess", 0.6, 0.22)],
    "ice": [("excited volatiles", 0.5, 0.18)],
}

# Reflected starlight lines (cold rock, ice, metal hulls).  A nebula reflects
# almost nothing; an asteroid field is pure reflection.
REFLECTION_LINES: Final[dict[ContactType, list[SpectralFeature]]] = {
    "unknown": [],
    "prospector": [("hull albedo", 0.4, 0.3)],
    "freighter": [("hull albedo", 0.38, 0.32), ("cargo containers", 0.58, 0.24)],
    "liner": [("white hull", 0.42, 0.4)],
    "escort": [("matte hull", 0.36, 0.26)],
    "capship": [("armour plate", 0.4, 0.3)],
    "fighter": [("small albedo", 0.44, 0.2)],
    "carrier": [("flight deck", 0.4, 0.35), ("island tower", 0.6, 0.3)],
    "asteroid": [("silicate", 0.3, 0.72), ("water ice", 0.66, 0.5)],
    "nebula": [("dust scatter", 0.5, 0.14)],
    "debris": [("bare metal", 0.34, 0.62), ("tumbling facet", 0.62, 0.44)],
    "dust": [("forward scatter", 0.44, 0.35)],
    "ice": [("specular glint", 0.3, 0.95), ("refraction halo", 0.58, 0.7)],
}

SPECTRAL_SUMMARY: Final[dict[ContactType, str]] = {
    "unknown": "no reference lines",
    "prospector": "small hot plant, narrow drive lines",
    "freighter": "broad plasma vent over a steady reactor",
    "liner": "clean reactor hum, big white albedo",
    "escort": "military fusion core with radar sidelobes",
    "capship": "twin fusion spines — unmistakable tonnage",
    "fighter": "afterburner spike, tiny cross-section",
    "carrier": "flight-deck plant and catapult transients",
    "asteroid": "silicate/ice reflection, no emission",
    "nebula": "strong H-alpha emission, almost no albedo",
    "debris": "cold metal reflection, sporadic residual heat",
    "dust": "warm-grain IR excess, heavy forward scatter",
    "ice": "specular glint and a refraction halo — a sensor liar",
}

# Mass curves used by the gravidar (kilotonnes).  Field contacts read as huge
# smears rather than a number.
MASS_KT: Final[dict[ContactType, float]] = {
    "unknown": 0.0,
    "prospector": 2.5,
    "freighter": 22.0,
    "liner": 14.0,
    "escort": 60.0,
    "capship": 320.0,
    "fighter": 0.9,
    "carrier": 360.0,
    "asteroid": 900.0,
    "nebula": 240.0,
    "debris": 45.0,
    "dust": 160.0,
    "ice": 300.0,
}

NEUTRAL_SIGNATURE_SET: Final[list[str]] = [
    "steady fusion hum",
    "plasma-vent whine",
    "gravitic lay",
    "cargo-deck clang",
    "distant ion drive",
    "torpedo-bay tick",
    "transponder squawk",
    "gutting thruster gait",
]

DEFAULT_EMCON: Final[EmconnState] = EmconnState(radar=False, radios=False, optics=False)

# ---- alert condition and shields (WCRPG Ch 7.2.2 / 9.3) ----
# Condition Three (peacetime) -> Two (Yellow: shields up, weapons cold) -> One
# (Red: shields up, weapons armed).  Going up costs a fuel point and charges
# the mounts; attack actions require Condition One.
SHIELD_ARCS: Final[tuple[str, ...]] = ("fore", "aft", "port", "starboard")
# Per ten-minute tick: 10% of the arc's pool plus the engineer's Defenses
# modifier.  Damage stops regeneration for that tick.
SHIELD_REGEN_PERCENT: Final = 0.10
SHIELD_REGEN_INTERVAL_MIN: Final = 10
# Fraction of the donor arc's pool moved by a successful Refocus Shields.
SHIELD_REFOCUS_FRACTION: Final = 0.25
# Fuel points: capacity is a placeholder until the transit loop lands (P4).
ALERT_FUEL_CAPACITY: Final = 12.0
ALERT_FUEL_COST: Final = 1.0

# ---- transit: fuel burn, range and intercept (WCRPG Ch 8) ----
# Points per hour.  Idle is a trickle; cruise and flank burn hard, and a ship
# at action stations with the radar up pays for both.
FUEL_BURN_IDLE_PER_HOUR: Final = 0.05
FUEL_BURN_CRUISE_PER_HOUR: Final = 0.40
FUEL_BURN_MAX_PER_HOUR: Final = 1.60
FUEL_BURN_ACTIVE_SENSOR: Final = 0.10
#: Extra burn per hour by alert condition (shields up / mounts armed).
FUEL_BURN_ALERT: Final[dict[str, float]] = {"three": 0.0, "two": 0.08, "one": 0.20}
#: Terrain/obstacle penalty: clutter and active hazards make every klik dearer.
FUEL_HAZARD_CLUTTER_FACTOR: Final = 0.5
#: Fraction of a leg's fuel a skipper keeps as reserve when computing bingo.
BINGO_RESERVE_FRACTION: Final = 0.25
#: Range at which a track counts as "in the envelope" for the ETA readout.
ETA_RANGE_KLIK: Final = 40.0

# ---- astrometrics: plotting a leg (TRANSIT plan §3) ----
#: Steady-state exposure cost per klik travelled.
EXPOSURE_PER_KLIK: Final = 0.05
#: Astrogation commitment uses the hard ladder, worsened by stale charts.
ASTRO_DC_NAME: Final = "hard"
ASTRO_DC_PER_CHART_HOUR: Final = 0.4
#: Chart age at which data counts as stale (risk flag + larger errors).
NAV_STALE_CHART_HOURS: Final = 16.0
#: Arrival error: klik per point of failure degree, plus per hour of chart age.
NAV_OFFSET_PER_DEGREE: Final = 1.5
NAV_OFFSET_PER_CHART_HOUR: Final = 0.6
#: Extra offset and damage a critical-failure gravity-well incident inflicts.
NAV_INCIDENT_OFFSET: Final = 10.0
NAV_INCIDENT_DAMAGE: Final = 15.0
#: How close counts as arrived (on top of the point's own radius).
NAV_ARRIVAL_RADIUS_PAD: Final = 2.0
#: Sensors re-survey of a chart.
NAV_SURVEY_DC_NAME: Final = "routine"

# ---- jump drive: spool, alignment and misjump (TRANSIT plan §2) ----
#: How close the ship must be to the point to start a spool.
JUMP_RANGE_KLIK: Final = 30.0
#: Base alignment quality gained per minute at a perfect position.
JUMP_ALIGN_RATE_PER_MIN: Final = 0.035
#: Below this alignment the drive simply will not engage (a refusal).
JUMP_MISJUMP_FLOOR: Final = 0.35
#: A pirate point is tighter by default.
JUMP_PIRATE_REQUIRED: Final = 0.8
#: Spooling costs fuel and a large emission spike, and deafens the ship.
JUMP_SPOOL_FUEL_COST: Final = 1.0
JUMP_COMMIT_FUEL_COST: Final = 0.5
JUMP_SPOOL_EXPOSURE: Final = 25.0
#: Self-noise added while spooling (the drive is a beacon).
JUMP_SPOOL_NOISE: Final = 0.55
#: Hard manoeuvring is impossible with the drive charged; speed clamps here.
JUMP_SPOOL_MAX_SPEED: Final = 15.0
#: Structural damage a misjump inflicts, and the time it costs.
JUMP_MISJUMP_DAMAGE: Final = 20.0
JUMP_MISJUMP_DELAY_MIN: Final = 45.0
#: Astrogation Check DC to re-acquire a clean alignment after a misjump.
JUMP_REALIGN_DC_NAME: Final = "hard"

# ---- nav uncertainty and fixes (TRANSIT plan §2.5 / §3) ----
#: Dead-reckoning error accrued per hour under way (klik), speed-scaled.
NAV_ERROR_RATE_PER_HOUR: Final = 1.2
#: Error left after a good fix.
NAV_FIX_BASE_KLIK: Final = 2.0
#: A landmark fix needs a charted point this close.
NAV_FIX_LANDMARK_RANGE_KLIK: Final = 30.0
#: A radar fix is exact but shouts.
NAV_FIX_PING_EXPOSURE: Final = 12.0
#: Fraction of jump-alignment quality lost when the error is at max.
NAV_ALIGN_ERROR_PENALTY: Final = 0.5
#: Cap on accrued dead-reckoning error.
NAV_ERROR_MAX_KLIK: Final = 45.0
#: Fix Check difficulties.
NAV_FIX_STAR_DC_NAME: Final = "routine"
NAV_FIX_LANDMARK_DC_NAME: Final = "easy"

# ---- long-range comms window (TRANSIT plan §2.6) ----
#: A relay window opens for the first stretch of every period.
COMMS_WINDOW_PERIOD_MIN: Final = 240.0
COMMS_WINDOW_DURATION_MIN: Final = 150.0
#: Extra exposure a long-range transmission pays outside the window.
COMMS_OUT_OF_WINDOW_PENALTY: Final = 2.0

# ---- the hunt: datum, posture and baffles (SUBMARINE plan §1, §3, §5) ----
#: A hunter's lock at which a datum is placed (and re-centered) on the ship.
DATUM_LOCK_THRESHOLD: Final = 0.5
#: Starting radius of a fresh datum and how fast it grows (klik / minute).
DATUM_INITIAL_RADIUS_KLIK: Final = 5.0
DATUM_RADIUS_GROWTH: Final = 0.35
#: Strength lost per minute at transit posture (drift decays faster).
DATUM_DECAY_PER_MIN: Final = 0.012
DATUM_DRIFT_DECAY_MULTIPLIER: Final = 2.5
#: Age at which a datum is useless even if its strength held.
DATUM_MAX_AGE_MIN: Final = 90.0
#: Datums are capped so a long hunt does not fill the plot.
DATUM_MAX_ACTIVE: Final = 3
#: A hunter searching inside a datum's radius gets a lock bonus on us.
DATUM_SEARCH_BONUS: Final = 0.3
#: Posture effects on the hunter's signal and its decay.
POSTURE_LOCK_MULTIPLIER: Final[dict[str, float]] = {
    "transit": 1.0,
    "sprint": 1.6,
    "drift": 0.4,
}
POSTURE_DECAY_MULTIPLIER: Final[dict[str, float]] = {
    "transit": 1.0,
    "sprint": 0.5,
    "drift": 2.5,
}

#: Aft blind arc: passive returns from inside it are crushed.
BAFFLE_ARC_DEG: Final = 35.0
BAFFLE_ATTENUATION: Final = 0.15
#: How long a clearing turn keeps the baffles clear, and what it costs.
BAFFLE_CLEAR_MINUTES: Final = 12.0
BAFFLE_CLEAR_NOISE: Final = 0.25

# ---- signature layers and TMA (SUBMARINE plan §2, §4) ----
#: Detection across a layer boundary is cut to this fraction.
LAYER_ATTENUATION: Final = 0.25
#: Crossing a layer costs noise and blinds your own array briefly.
LAYER_CROSS_NOISE: Final = 0.15
LAYER_CROSS_BREAK_MIN: Final = 5.0
#: TMA: a leg must change course and generate bearing rate to solve.
TMA_MIN_TURN_DEG: Final = 20.0
TMA_MIN_BEARING_DEG: Final = 4.0
TMA_MAX_MIN: Final = 45.0
TMA_BASE_QUALITY: Final = 0.5
#: A TMA leg that is careless inside a datum tells the hunter where you are.
TMA_DATUM_RECENTER: Final = True
#: How far a hunter will range to search an active datum.
DATUM_SEARCH_RANGE_KLIK: Final = 120.0
#: How fast a hunter can turn onto a new course.
HUNTER_TURN_RATE_DEG_PER_MIN: Final = 4.0

# ---- defensive manoeuvres (WCRPG Ch 7.5) ----
#: name -> (evasive bonus, gunnery penalty, heading change, Check difficulty or None)
# ---- heat: capability, not exposure (TRANSIT plan §4) ----
#: Heat gained per hour by each draw.  The reactor always runs warm.
HEAT_BASE_PER_HOUR: Final = 0.6
HEAT_SENSOR_ACTIVE: Final = 0.8
HEAT_ALERT: Final[dict[str, float]] = {"three": 0.0, "two": 0.4, "one": 0.8}
HEAT_WEAPONS: Final = 0.5
HEAT_SPOOL: Final = 2.0
#: Passive circulation, a fast-and-loud vent, and quiet bottling.
HEAT_DISSIPATION_PER_HOUR: Final = 1.2
HEAT_VENT_PER_HOUR: Final = 6.0
HEAT_BOTTLE_DISSIPATION: Final = 0.4
HEAT_VENT_EXPOSURE: Final = 20.0
#: Above this the ship fights worse; at the cap it vents whether you like it or not.
HEAT_PENALTY_AT: Final = 70.0
HEAT_CRITICAL: Final = 100.0
HEAT_PENALTY_MAX: Final = 4
#: Bottling is quiet: it cuts self-noise while it lasts.
HEAT_BOTTLE_NOISE_RELIEF: Final = 0.15

# ---- watch bill, fatigue and morale (TRANSIT plan §6) ----
#: Fatigue gained per hour on watch, and recovered per hour standing down.
FATIGUE_PER_HOUR: Final[dict[str, float]] = {"standard": 2.0, "battle": 4.0, "rest": -6.0}
#: Fatigue above which Checks start to suffer.
FATIGUE_PENALTY_AT: Final = 40.0
FATIGUE_PENALTY_DIVISOR: Final = 20
#: A shaken crew takes this d20 penalty until rallied.
SHAKEN_PENALTY: Final = 2
#: Crew strength below this counts as undermanned (a further small penalty).
UNDERMANNED_CREW: Final = 90.0
UNDERMANNED_PENALTY: Final = 1
#: Damage that shakes the crew, and the Check that rallies them.
SHOCK_CORE_DAMAGE: Final = 40.0
RALLY_DC_NAME: Final = "routine"
#: Hangar ops: how long the door is open and what that costs.
HANGAR_OPEN_MIN: Final = 20.0
HANGAR_OPEN_EXPOSURE: Final = 10.0

#: How long a crossed picket line keeps us alerted.
BARRIER_ALERT_MIN: Final = 25.0

#: Consumables carried at the start of a watch.
SPARES_LOADOUT: Final = 3
PROVISIONS_HOURS: Final = 48.0
SALVAGE_SPARES_MAX: Final = 6
#: A field repair without spares is harder; EVA salvage risks the crew.
NO_SPARES_DC_PENALTY: Final = 2
EVA_COLD_INJURY: Final = 4.0
#: Contamination re-fires at about this chance per hour.
CONTAMINATION_CHANCE_PER_HOUR: Final = 0.15

# ---- subsystem targeting, ordnance and spoofing (WCRPG Ch 9.3, Ch 7) ----
#: Damage that reaches a system is scaled by the target's defence state.
SUBSYSTEM_SHIELD_FACTOR: Final = 0.01
SUBSYSTEM_ARMOR_FACTOR: Final = 0.10
#: Targeting Check base difficulty for a subsystem strike.
SUBSYSTEM_TARGET_DC_NAME: Final = "hard"
#: Ordnance: how close counts as a hit, how far it can be seen, how far it flies.
ORDNANCE_HIT_KLIK: Final = 1.5
ORDNANCE_DETECT_KLIK: Final = 45.0
ORDNANCE_FUEL_KLIK: Final = 90.0
ORDNANCE_TURN_RATE_DEG_PER_MIN: Final = 120.0
ORDNANCE_WARHEAD: Final = 40.0
#: Shooting down an inbound weapon: a Targeting Check at this difficulty.
ORDNANCE_SHOOT_DC_NAME: Final = "routine"
#: Spoofing pods: a Ballistics Check buys a bonus that makes a good shot miss.
SPOOF_DC_NAME: Final = "hard"
SPOOF_BONUS_PER_POD: Final = 5
SPOOF_DURATION_MIN: Final = 12.0
#: Spoofing pods carried per watch.
SPOOF_POD_LOADOUT: Final = 2
#: A spoof makes an inbound weapon re-attack the decoy on this roll.
SPOOF_DECOY_CHANCE: Final = 0.7

#: How long a manoeuvre's modifiers hold without a new helm order.
MANEUVER_HOLD_MIN: Final = 30.0
MANEUVER_NOISE: Final = 0.12


class ManeuverSpec(TypedDict):
    label: str
    evasive: int
    gunnery: int
    turn: float
    dc: str | None


MANEUVERS: Final[dict[str, ManeuverSpec]] = {
    "jink": {"label": "Jink", "evasive": 10, "gunnery": 10, "turn": 0.0, "dc": None},
    "slip-90": {"label": "Slip 90", "evasive": 8, "gunnery": 4, "turn": 90.0, "dc": "routine"},
    "slip-180": {"label": "Slip 180", "evasive": 12, "gunnery": 10, "turn": 180.0, "dc": "hard"},
    "snap-turn": {"label": "Snap turn", "evasive": 6, "gunnery": 6, "turn": 90.0, "dc": "hard"},
    "break": {"label": "Break", "evasive": 14, "gunnery": 14, "turn": 180.0, "dc": "formidable"},
}
# Core damage a destroyed (or already dead) system passes on, escalated by
# each further hit on the same dead system.
CORE_DAMAGE_EXCESS_STEP: Final = 10.0

#: Systems that can be damaged, malfunction and be repaired.
SHIP_SYSTEMS: Final[tuple[str, ...]] = (
    "shields",
    "guns",
    "ordnance",
    "radar",
    "comms",
    "engines",
    "flightDeck",
    "lifeSupport",
)

# ---- system damage and damage control (WCRPG Ch 9.3) ----
# A hit rolls a d10 against this table (re-authored from the book's, which also
# has separate crew/officer entries we fold into life support).
SYSTEM_HIT_TABLE: Final[tuple[str, ...]] = (
    "shields",
    "guns",
    "ordnance",
    "radar",
    "comms",
    "engines",
    "flightDeck",
    "lifeSupport",
    "radar",
    "engines",
)
#: Core damage per point of overflow, divided by the hull's size class.
CORE_DAMAGE_PER_POINT: Final = 1.0
#: Minimum size class, so a fighter's single overflow point still hurts.
MIN_SIZE_CLASS: Final = 1
#: Named difficulty a repair Check starts from, +1 DC per this many damage.
REPAIR_DC_NAME: Final = "hard"
REPAIR_DC_PER_DAMAGE: Final = 10
#: DC relief a field patch buys, at the cost of re-failing on the next hit.
JURY_RIG_RELIEF: Final = 4
#: Repair restores at least this much per successful Check, plus the degree.
REPAIR_MIN_PER_CHECK: Final = 5

#: Wear accrues every watch hour from hard running; environments add more.
SYSTEM_WEAR_BASE_PER_HOUR: Final = 1.2
WEAR_SPEED_FACTOR: Final = 1.0
#: Wear at which malfunction risk begins, and the cap that guarantees it.
WEAR_RISK_AT: Final = 70.0
WEAR_FAIL_AT: Final = 100.0
#: Chance per watch step of a worn system failing once past WEAR_RISK_AT.
WEAR_MALFUNCTION_CHANCE: Final = 0.05
