"""CAPTAIN shared type definitions.

Direct port of ``packages/shared/src/types.ts``.  All mutable game state lives in
Pydantic models so ``model_dump_json()`` replaces ``JSON.stringify()`` and
``Model.model_validate_json()`` replaces ``JSON.parse()``.

Field names deliberately keep the TypeScript camelCase spelling: the wire
protocol and the persisted SQLite rows are shared with the (unchanged) React
frontend, so the JSON keys must not change.  The single Python keyword clash is
``ShipState.class`` which is exposed as ``className`` and aliased back to
``class`` for serialization/deserialization.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Scalars / literals
# ---------------------------------------------------------------------------

Faction = Literal["friendly", "neutral", "enemy"]
ContactType = Literal[
    "unknown",
    "prospector",
    "freighter",
    "liner",
    "escort",
    "capship",
    "fighter",
    "carrier",
    # Environmental / non-manoeuvring returns.  These are terrain, not traffic:
    # they have no crew, no transponder and no evasion, but they wreck passive
    # classification and saturate the gravidar.
    "asteroid",
    "nebula",
    "debris",
    # Sensor obstacles: dust scatters, ice reflects/refracts and throws ghosts.
    "dust",
    "ice",
]
ContactState = Literal["unknown", "tracking", "probable", "classified", "confirmed"]

SeatId = Literal["command", "ops", "sensor", "comms"]
HatId = Literal["nav", "ops", "sensors", "ew", "comms", "weapons", "dc"]

Condition = Literal["green", "yellow", "red"]
RuleOfEngagement = Literal["safe", "hold", "free"]
WeaponsState = Literal["safe", "standby", "armed", "locked"]
# A quick shot leans on whatever solution exists; a refined shot waits for the
# full requirement.  Guns, missiles and torpedoes each want a different one.
ShotType = Literal["quick", "refined"]
WeaponKind = Literal["gun", "missile", "torpedo", "turret"]
CheckOutcome = Literal["critical-success", "success", "failure", "critical-failure"]
# Condition Three (peacetime), Two (Yellow: shields up), One (Red: weapons too).
AlertLevel = Literal["three", "two", "one"]
# Charted feature kinds on the ops plot.
NavKind = Literal["nav", "jump", "body", "hazard"]
# Transit doctrine: sprint loud and fast, drift slow and silent, or plain transit.
Posture = Literal["transit", "sprint", "drift"]
# Thermal management: normal circulation, fast-and-loud venting, quiet bottling.
HeatMode = Literal["normal", "vent", "bottle"]
# Watch bill: standard 6-on/12-off, everyone closed up, or standing the crew down.
WatchBill = Literal["standard", "battle", "rest"]
OperatingMode = Literal["cruise", "quiet", "max"]

LogEntryType = Literal[
    "info", "ok", "warn", "danger", "intel", "comms", "weapons", "rp"
]

GameStatus = Literal["lobby", "running", "handoff", "ended"]
TimeMode = Literal["paused", "slow", "fast", "warp"]


class WireModel(BaseModel):
    """Base model that always serializes using field aliases.

    Only ``className`` currently has an alias (``class``), but forcing the
    behaviour on every model keeps the JSON wire shape identical to what the
    TypeScript server produced without sprinkling ``by_alias=True`` across the
    server code.
    """

    model_config = ConfigDict(populate_by_name=True)

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        kwargs.setdefault("by_alias", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs: Any) -> str:  # type: ignore[override]
        kwargs.setdefault("by_alias", True)
        return super().model_dump_json(**kwargs)


# ---------------------------------------------------------------------------
# Primitive value objects
# ---------------------------------------------------------------------------


class Vec(WireModel):
    x: float
    y: float
    z: float


class EmconnState(WireModel):
    radar: bool
    radios: bool
    optics: bool


class EmconPatch(WireModel):
    """``Partial<EmconnState>`` — ``None`` means "leave unchanged"."""

    radar: bool | None = None
    radios: bool | None = None
    optics: bool | None = None


class ShieldArc(WireModel):
    """One defence arc's shield hit points (fore/aft/port/starboard)."""

    shp: float = 0.0
    max: float = 0.0


class SystemHealth(WireModel):
    """One ship system's condition.

    ``health`` is damage (100 is untouched, 0 is destroyed); ``wear`` is the
    deferred maintenance burden that accrues with hard running and harsh
    environments and never heals itself.  ``juryRigged`` marks a field patch
    that will fail again the moment the system takes a fresh hit.
    """

    health: float = 100.0
    malfunctioning: bool = False
    wear: float = 0.0
    juryRigged: bool = False
    # What is festering in it; a contaminated fault recurs until cleaned.
    contaminated: str = ""


class BearingSample(WireModel):
    t: float
    bearing: float
    elev: float | None = None
    range: float | None = None
    source: Literal["passive", "active", "ew", "visual", "intel"]
    # Which sensor origin cut this bearing: "" is the ship's own array, anything
    # else is a deployed buoy id.  Two origins with a baseline between them let
    # the crew cross-fix a passive-only contact.
    originId: str = ""


class Waveform(WireModel):
    progress: float
    resolved: bool


class CatalogueMatch(WireModel):
    """A ranked but never verified catalogue comparison.

    The catalogue candidate is a specific **hull** (``shipClass``), not a broad
    contact type: the passive barcode is a hull's own frequency profile, so a
    listen pass ranks actual ship types.  ``contactType`` rides along because
    that is what a tag ultimately commits to.
    """

    shipClass: str = ""
    name: str = ""
    contactType: ContactType
    score: float


class CheckResult(WireModel):
    """One d20 Check, resolved.

    ``roll`` is a d20 (1-20); the Check succeeds when ``roll + modifier >= dc``.
    A natural 20 is a critical success and a natural 1 a critical failure
    regardless of the total.  ``score`` is the station's raw 0-99 skill rating
    and ``modifier`` the derived d20 bonus, so the GM can see both.  ``degree``
    is the margin by which the total beat (or missed) the DC.
    """

    skill: str = ""
    score: int = 0
    modifier: int = 0
    dc: int = 0
    roll: int = 0
    total: int = 0
    success: bool = False
    degree: int = 0
    outcome: CheckOutcome = "failure"


class SpectralLine(WireModel):
    """One named absorption/emission feature on the spectral analyzer."""

    band: str
    pos: float
    strength: float


class Spectrum(WireModel):
    """A contact's spectral fingerprint.

    ``emission`` is the self-radiated spectrum (drive plumes, fusion cores,
    excited nebular gas); ``reflection`` is the blackbody/solar light bouncing
    off a cold body (asteroids, debris, hulls).  Both are fixed-length
    normalized bins (see ``SPECTRUM_BINS``) so the frontend can plot them
    directly without re-deriving a scale.
    """

    emission: list[float] = Field(default_factory=list)
    reflection: list[float] = Field(default_factory=list)
    lines: list[SpectralLine] = Field(default_factory=list)
    summary: str = ""


class ShipClass(WireModel):
    """A hull the GM can assign to a scenario.

    ``stealth`` masks emissions (hurts enemy *passive* detection of this ship),
    ``profile`` is the radar cross-section multiplier (hurts *active* return),
    and ``massKt``/``emission`` drive the gravidar arc and the passive grill.
    """

    id: str
    name: str
    role: str
    contactType: ContactType
    massKt: float
    profile: float
    stealth: float
    emission: float
    sensorQuality: float
    cruiseSpeed: float
    maxSpeed: float
    crew: int
    blurb: str
    # Sensor frequency profile — the hull's "barcode", one 0..1 amplitude per
    # band.  Passive listening paints it in; no two hulls share a pattern.
    bands: list[float] = Field(default_factory=list)
    # Art resolved from the ships DB / img tree (``/img/action`` and ``/img/vdu``).
    image: str = ""
    vdu: str = ""
    # Hull defences from the ships DB (WCRPG Ch 7.2.2): per-arc shield and
    # armour pools, the shield recharge rate, and structural body points.
    shieldFore: float = 0.0
    shieldAft: float = 0.0
    shieldRefresh: float = 0.0
    armorFore: float = 0.0
    armorAft: float = 0.0
    armorPort: float = 0.0
    armorStarboard: float = 0.0
    body: float = 0.0
    # Fuel points carried (the ships DB ``fuel`` column).
    fuelCapacity: float = 0.0


class WeaponSpec(WireModel):
    """A crew weapon mount and the firing solution it demands.

    A firing solution is graded 0..1 from the contact's classification
    confidence (a resolved spectrum helps).  Guns want little; a torpedo wants a
    confirmed track and a lot of patience.  ``rangeKlik`` is the effective
    envelope: beyond it the mount simply cannot hold a solution.
    """

    id: str
    name: str
    kind: WeaponKind
    # Minimum solution quality (0..1) needed to hold ARMED or LOCKED.
    solutionRequired: float
    # Some mounts (torpedoes, imaging missiles) will not lock an unconfirmed track.
    requiresConfirmed: bool = False
    # Maximum effective range in klik.
    rangeKlik: float
    # Extra exposure charged when the mount goes to ARMED / LOCKED.
    lockExposure: float
    blurb: str


class AdminShipBrief(WireModel):
    """Compact ship record shipped to the GM console."""
    id: str
    name: str
    role: str
    contactType: ContactType
    massKt: float
    profile: float
    stealth: float
    emission: float
    sensorQuality: float


class GravArc(WireModel):
    """A gravidar return: bearing is known, range is not.

    The target's mass is painted as an arc centred on the bearing; ``halfWidth``
    is the angular uncertainty in degrees.  Heavy, close contacts tighten the
    arc; noise, clutter and reflection smear it open.
    """

    bearing: float
    halfWidth: float
    massKt: float


class SensorReadout(WireModel):
    """What the sensor fit has resolved about a contact.

    The sensors run **at the same time**, not as exclusive modes:

    - passive (always on): bearing/angular precision, emission, type, barcode;
    - gravidar (on unless the ship is stopped): a mass heat map with good
      bearing precision and an OK, approximate distance;
    - active radar (toggled): precise range/bearing/elevation;
    - EM/motion (always on, easily scrambled): target course and speed.
    """

    passiveEmission: float = 0.0
    passiveType: ContactType = "unknown"
    activeRange: float | None = None
    activeBearing: float | None = None
    activeElev: float | None = None
    gravArc: GravArc | None = None
    # Gravidar's "OK distance": approximate range plus its error in klik.
    gravRange: float | None = None
    gravRangeError: float = 0.0
    # EM/motion sensors: target course and speed, with a 0..1 confidence that
    # sun glare and asteroid/debris/dust fields chew through.
    emCourse: float | None = None
    emSpeed: float | None = None
    emQuality: float = 0.0
    # 0..1 aggregate line-of-sight attenuation from intervening obstacles.
    obstructed: float = 0.0
    # Intercept clock: closest approach and when it happens, plus time to reach
    # the crew's ETA range ring if the tracks hold their courses.
    cpaKlik: float | None = None
    cpaMinutes: float | None = None
    etaMinutes: float | None = None
    # TMA: a range solved by manoeuvring the ship, and how good it is.
    tmaRangeKlik: float | None = None
    tmaQuality: float = 0.0
    # Frequency bands resolved so far (0..1 per band); fills in while listening.
    bands: list[float] = Field(default_factory=list)
    catalogueMatches: list[CatalogueMatch] = Field(default_factory=list)


class SensorEffect(WireModel):
    """How an obstacle interacts with the sensor triad.

    ``block`` attenuates line of sight, ``scatter`` injects bearing/range noise,
    and ``reflect`` produces false or multipath returns (ice is the extreme).
    """

    block: float = 0.0
    scatter: float = 0.0
    reflect: float = 0.0


class Buoy(WireModel):
    """A deployed passive sensor buoy.

    Immobile by design: it is a listening post, not a drone.  The ops seat drops
    it and can recover it back to the rack, and while it is out its bearings are
    a second sensor origin the crew can cross-fix against.
    """

    id: str
    name: str
    pos: Vec
    deployedAt: float
    active: bool = True


class SeatPlayer(WireModel):
    # ``sessionId`` identifies the *connection* that holds the seat; ``userId``
    # is the Discord/browser identity (display + grouping).  Two connections from
    # the same user are two sessions and must not share a seat.
    userId: str
    name: str
    sessionId: str = ""


class LogEntry(WireModel):
    id: int
    time: float
    type: LogEntryType
    source: str
    text: str


class Contact(WireModel):
    id: str
    # ``name`` is the *display* label.  Until the track is CONFIRMED it is an
    # anonymous designation (``TRACK-01``); ``trueName`` holds the real vessel,
    # military or place name and is only revealed on confirmation, so the plot
    # cannot spoil its own contacts.
    name: str
    trueName: str = ""
    trueType: ContactType
    faction: Faction
    hostile: bool
    pos: Vec
    heading: float
    speed: float
    state: ContactState
    confidence: float
    guess: ContactType
    firstSeen: float
    lastSeen: float
    seenCount: int
    bearingHistory: list[BearingSample] = Field(default_factory=list)
    estimated: Vec | None = None
    emitting: bool = False
    detected: bool = False
    everDetected: bool = False
    signal: float = 0.0
    signature: str = ""
    waveform: Waveform = Field(default_factory=lambda: Waveform(progress=0.0, resolved=False))
    tail: float | None = None
    # Gravidar acquisition energy: a mass return needs a couple of looks before
    # the operator will call it a contact, so the plot does not fill in one tick.
    gravTail: float | None = None
    massKt: float = 0.0
    gravRead: float | None = None
    # Gravidar returns from a field contact (asteroid/debris/nebula) are a
    # saturated smear rather than a tonnage curve; the board flags it so the
    # sensor desk knows to trust the waveform instead.
    gravSaturated: bool = False
    spectrum: Spectrum | None = None
    # --- detection race ------------------------------------------------------
    # The enemy's track quality on *us* (0..1).  Reaching 1.0 is a firing lock
    # and loses the patrol; a noisemaker floods it back down.
    lock: float = 0.0
    hostileLock: bool = False
    # True once a hostile has closed inside ``DISENGAGE_RANGE_KLIK``.  A patrol
    # is won when every hostile has left that envelope and at least one was ever
    # inside it — the crew "made it through" rather than never being threatened.
    everNear: bool = False
    # True once a hostile's track on *us* reaches ``DETECTED_LOCK``.  The
    # endurance win ("six hours undetected") is void the moment this is set.
    everTrackedUs: bool = False
    # True once a second sensor origin has cross-fixed this contact's range.
    triangulated: bool = False
    # --- IFF interrogation ----------------------------------------------------
    # How far the transponder is trusted (0..1), how many times it has been
    # challenged this run, and whether the gear has caught it lying.  A hostile
    # that squawks a false type can eventually be unmasked by repeat challenges
    # or by matching the response against a resolved spectrum.
    iffConfidence: float = 0.0
    iffChallenges: int = 0
    spoofDetected: bool = False
    # True once the ops watch has filed a fleet intel report on this track.
    reported: bool = False
    # --- ship-class driven sensor properties ---------------------------------
    shipClass: str = ""
    # Radar cross-section multiplier (active return); 0 = invisible, 1 = huge.
    profile: float = 0.5
    # Emission masking; 1 = silent runner, 0 = broadcasting.
    stealth: float = 0.0
    # Baseline emitted power; the passive grill loves a loud hull.
    emission: float = 0.5
    # The hull's own sensor suite, used when *it* is hunting the crew ship.
    sensorQuality: float = 0.5
    # Obstacle radius in klik (terrain only; ships are point sources).
    radiusKlik: float = 6.0
    # The hull's true sensor frequency profile (see ShipClass.bands). Terrain
    # carries a short, lumpy profile of its own.
    frequencyProfile: list[float] = Field(default_factory=list)
    # Art URLs for this contact's hull/terrain (``/img/...``), from the DB.
    image: str = ""
    vdu: str = ""
    sensor: SensorReadout = Field(default_factory=SensorReadout)


class SeatSkills(WireModel):
    """A station's crew skills, in the WCRPG sense.

    ``scores`` maps a skill name (see ``shared/checks.ALL_SKILLS``) to a 0-99
    score; a skill with no entry falls back to the crew average, so a station
    need only record what it is actually good or bad at.  ``specializations``
    add to a named skill when the GM says the specialization applies.
    """

    scores: dict[str, int] = Field(default_factory=dict)
    specializations: dict[str, int] = Field(default_factory=dict)


class Seat(WireModel):
    id: SeatId
    title: str
    hats: list[HatId]
    player: SeatPlayer | None = None
    primary: bool = False
    # The crew behind the station: player skills when a player holds it, or the
    # NPC crew the GM authored.  Missing skills use the crew-average default.
    skills: SeatSkills = Field(default_factory=SeatSkills)


class ShipState(WireModel):
    name: str
    className: str = Field(alias="class")
    registry: str
    pos: Vec
    heading: float
    speed: float
    cruiseSpeed: float
    quietSpeed: float
    maxSpeed: float
    waypoints: list[Vec] = Field(default_factory=list)
    emcon: EmconnState
    mode: OperatingMode
    condition: Condition
    roe: RuleOfEngagement
    weaponsState: WeaponsState = "safe"
    # The prepped mount, the graded quality of its firing solution (0..1), and
    # whether it was built quick-and-dirty or refined.  These feed the handoff
    # pack so the tabletop knows exactly what was dressed.
    weapon: str = ""
    solutionQuality: float = 0.0
    shotType: ShotType = "quick"
    # The contact the current solution is held on ("" when none).  The activity
    # UI reveals that hull's picture once the solution is LOCKED — a clear
    # solution means the crew can see what they are pointing at.
    weaponTarget: str = ""
    # The live shooting problem for the prepped mount (None until one is prepped).
    weaponEhd: Ehd | None = None
    # The subsystem the crew is trying to hit on that target.
    weaponTargetSystem: str = ""
    # Spoofing pods: countermeasures that make a shot that beat the EHD miss.
    spoofPods: int = 0
    # --- endurance (heat, fatigue, morale) ----------------------------------
    # Heat is capability, not exposure: run hot and the ship fights worse.
    heat: float = 0.0
    heatMode: HeatMode = "normal"
    # Crew fatigue from the watch, and whether the crew is shaken.
    fatigue: float = 0.0
    watchBill: WatchBill = "standard"
    shaken: bool = False
    # Crew strength as a percentage; below 90% the ship is undermanned.
    crewStrength: float = 100.0
    # Small-craft ops: whether a craft is away and until when the door is open.
    smallCraftAway: bool = False
    hangarOpenUntil: float = 0.0
    # Consumables: field spares, provisions in hours, and rounds by weapon.
    spares: int = 0
    provisions: float = 0.0
    ordnanceLoadout: dict[str, int] = Field(default_factory=dict)
    # --- shipyard: hardpoints and modules (P9.2/P9.3) ------------------------
    hardpoints: list[Hardpoint] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)
    # Budgets the modules are fitted against.
    powerBudget: float = 0.0
    massBudgetKt: float = 0.0
    cargoCapacity: float = 0.0
    # Heraldry: the ship's name and registry already ride ShipState; the livery
    # is how she is painted.
    livery: str = ""
    spoofActiveUntil: float = 0.0
    spoofBonus: int = 0
    exposure: float
    readiness: float
    hull: float
    battery: float
    sensorQuality: float
    selfNoise: float
    altTarget: float
    # Active radar is the only sensor that switches; passive, gravidar and EM
    # run alongside it (gravidar only while the ship is making way).
    activeSensor: bool = False
    # Consumables.  ``speed`` is the *actual* speed ordered on the 0-100 dial;
    # ``mode`` is the named bucket it falls in.
    buoyCount: int = 2
    noisemakers: int = 2
    # --- ship-class driven properties (set by the GM at scenario build) ------
    shipClass: str = "friendly-corvette"
    profile: float = 0.45
    stealth: float = 0.5
    emission: float = 0.35
    massKt: float = 4.2
    # Directional stern drive-plume heat (0..1).  High when making way, zero
    # when stopped; it dazzles the ship's own aft sensors.
    rearHeat: float = 0.0
    # --- alert, defences and systems (WCRPG Ch 7/9) -------------------------
    # Condition Three (peacetime) -> Two (Yellow: shields up, weapons cold)
    # -> One (Red: shields up, weapons armed).  Attack actions need One.
    alert: AlertLevel = "three"
    # Defence arcs, each with its own shield hit points; armour sits behind.
    shields: dict[str, ShieldArc] = Field(default_factory=dict)
    armor: dict[str, float] = Field(default_factory=dict)
    # Core damage as a percentage; 100 destroys the ship.
    core: float = 0.0
    # Per-system condition and deferred wear.
    systems: dict[str, SystemHealth] = Field(default_factory=dict)
    # Simulated-minute timestamp of the next shield regeneration tick.
    shieldRegenAt: float = 0.0
    # Consecutive hits on already-dead systems, for the escalating core damage
    # of WCRPG's "stop poking the hole" rule.
    excessHits: int = 0
    # Fuel points; the transit loop spends these.
    fuel: float = 0.0
    fuelCapacity: float = 0.0
    # Derived transit picture, refreshed every step so the UI never has to do
    # the arithmetic: current burn, how far the remaining fuel reaches at the
    # ordered speed, and the fuel needed to get home with a reserve.
    fuelBurnPerHour: float = 0.0
    fuelRangeKlik: float = 0.0
    bingoFuel: float = 0.0
    #: True while the remaining fuel is at or below the bingo figure.
    bingo: bool = False
    # True once the tanks are dry: the ship cannot reposition or evade.
    deadDrift: bool = False
    # Dead-reckoning uncertainty (klik).  Grows with time under way; a fix
    # (star sighting, landmark, radar ping) resets it.  It stretches plotted
    # ETAs and degrades jump alignment until it is worked off.
    navErrorKlik: float = 0.0
    # FTL drive type (see resources/bridge_drives.json).
    drive: str = "standard"
    # Current defensive manoeuvre and its modifiers, held until the next helm
    # order.  ``evasive`` makes us harder to hit; ``gunnery`` spoils our shot.
    maneuver: str = ""
    maneuverEvasive: int = 0
    maneuverGunnery: int = 0
    maneuverUntil: float = 0.0


class WarState(WireModel):
    tension: float
    phase: str
    frontLine: float


# ---------------------------------------------------------------------------
# Contact templates / patches (campaign seeds and GM admin)
# ---------------------------------------------------------------------------


class ContactTemplate(WireModel):
    x: float
    y: float
    z: float | None = None
    heading: float
    speed: float
    type: ContactType
    faction: Faction
    hostile: bool
    emitting: bool
    name: str | None = None
    # Optional hull from the ship catalog; fills profile/stealth/mass/emission.
    shipClass: str | None = None
    radiusKlik: float | None = None


class ContactPatch(WireModel):
    """``Partial<ContactPatch>`` — ``None`` means "field not supplied"."""

    name: str | None = None
    pos: Vec | None = None
    alt: float | None = None
    heading: float | None = None
    speed: float | None = None
    trueType: ContactType | None = None
    faction: Faction | None = None
    hostile: bool | None = None
    emitting: bool | None = None
    state: ContactState | None = None
    guess: ContactType | None = None
    shipClass: str | None = None


# ---------------------------------------------------------------------------
# Decision events
# ---------------------------------------------------------------------------


class EventEffect(WireModel):
    exposure: float | None = None
    tension: float | None = None
    launchContacts: list[ContactTemplate] | None = None
    loseTrack: bool | None = None
    # Resolve this decision by generating the combat handoff pack (pauses the
    # patrol).  ``targetId`` names the contact the pack is built for.
    handoff: bool | None = None
    # Which contact a ``loseTrack`` / targeted effect applies to; when absent
    # the engine picks the weakest track.
    targetId: str | None = None
    # --- Comms / weapons event outcomes --------------------------------------
    # Bounce the traffic through a relay: the relay carries the signal, so the
    # ship's own signature is spared.
    relay: bool | None = None
    # Put a challenge-response to the contact (the engine runs an IFF call, with
    # any resolved spectrum helping to unmask a spoof).
    challenge: bool | None = None
    # Civilian traffic crosses the box: a neutral hull joins the plot.
    civilian: bool | None = None
    # The contact sings out a surrender that may not be genuine; the engine
    # decides whether it is a prize or a trap.
    falseSurrender: bool | None = None
    log: str | None = None


class DecisionOption(WireModel):
    id: str
    label: str
    hint: str | None = None
    effect: EventEffect = Field(default_factory=EventEffect)


class DecisionEvent(WireModel):
    id: str
    title: str
    kind: str
    deadline: float
    text: str
    source: str
    options: list[DecisionOption] = Field(default_factory=list)


class EventSchedule(WireModel):
    atMinute: float
    template: str


# ---------------------------------------------------------------------------
# Campaign seed
# ---------------------------------------------------------------------------


class Patrol(WireModel):
    center: Vec
    radiusKlik: float


class ZBand(WireModel):
    min: float
    max: float


class Hazard(WireModel):
    id: str
    type: str
    title: str
    startMinute: float = 0
    endMinute: float | None = None
    intensity: float = 1.0
    # Qualitative, tunable modifiers. Positive noise/exposure are harmful;
    # concealment reduces the ship's apparent signature.
    noise: float = 0.0
    exposure: float = 0.0
    concealment: float = 0.0


class NavPoint(WireModel):
    """A charted feature the ops station can plot a leg to.

    ``chartAgeHours`` is the confidence flag: fresh data plots cleanly, stale
    data raises the Astrogation DC and the arrival error if the crew commits
    without re-surveying.
    """

    id: str
    name: str
    kind: NavKind = "nav"
    pos: Vec
    radiusKlik: float = 6.0
    chartAgeHours: float = 0.0
    note: str = ""
    # --- jump points (kind == "jump") ---------------------------------------
    # A stable point is forgiving; a pirate point is tighter and riskier.
    jumpType: Literal["stable", "pirate"] = "stable"
    # Sim-minute window the point is usable (None close = always open).
    windowOpen: float = 0.0
    windowClose: float | None = None
    # Alignment quality the drive needs.  Interference at the point adds to it.
    alignmentRequired: float = 0.6
    interference: float = 0.0
    # Arrival coordinates; with none, a successful jump is an extraction.
    dest: Vec | None = None


class PlotLeg(WireModel):
    """A candidate leg, with the three numbers the crew must trade off."""

    navId: str
    name: str
    kind: NavKind = "nav"
    distanceKlik: float = 0.0
    timeMinutes: float = 0.0
    fuelCost: float = 0.0
    exposure: float = 0.0
    chartAgeHours: float = 0.0
    #: Time the navigation uncertainty adds to the leg.
    uncertaintyMinutes: float = 0.0
    #: "clear" | "stale charts" | "hazard" | "contact"
    risk: str = "clear"


class NavCommit(WireModel):
    """A committed leg, carrying the Astrogation result and its arrival error."""

    navId: str
    name: str
    outcome: CheckOutcome = "failure"
    #: How far off-axis the ship will arrive (klik).
    offsetKlik: float = 0.0
    committedAt: float = 0.0
    #: True when the navigation data was stale at commit time.
    staleCharts: bool = False


class SensorLayer(WireModel):
    """An EM/thermal gradient band.

    A sensor looking across a band boundary is attenuated: the layer hides a
    contact on the far side from the near one.  The right layer depends on who
    is hunting whom.
    """

    id: str
    name: str
    zMin: float = 0.0
    zMax: float = 10.0
    note: str = ""


class TmaState(WireModel):
    """A deliberate manoeuvre leg flown to solve a bearing-only track."""

    contactId: str = ""
    startedAt: float = 0.0
    startHeading: float = 0.0
    startBearing: float = 0.0
    solved: bool = False
    quality: float = 0.0
    #: Bearing change the leg has generated so far (degrees).
    bearingRate: float = 0.0


class Datum(WireModel):
    """A hunter's positional memory of where the crew ship last was.

    Placed when a hostile builds a track (or the crew pings), it decays while
    the ship stays quiet and ages out entirely if worked off — the hunt breaks
    and the window opens.  A fresh detection re-centers it.
    """

    id: str = ""
    pos: Vec
    radiusKlik: float = 5.0
    strength: float = 1.0
    ageMinutes: float = 0.0
    source: str = ""
    active: bool = True


class JumpState(WireModel):
    """The jump drive's spool-up: a graded alignment like a firing solution.

    ``alignment`` accrues while spooling from how clean the ship's position,
    heading and closing velocity are against the point.  Committing below
    ``required`` is a **misjump**; below the floor the drive will not engage.
    """

    navId: str = ""
    name: str = ""
    spooling: bool = False
    alignment: float = 0.0
    required: float = 0.6
    startedAt: float = 0.0
    ready: bool = False
    windowOpen: bool = True
    #: "", "spooling", "aborted", "jumped", "misjump", "refused"
    outcome: str = ""


class CampaignSeed(WireModel):
    id: str
    title: str
    theater: str
    brief: str
    target: str
    startHour: float
    patrol: Patrol
    clutter: float
    noiseRate: float | None = None
    noiseFilter: bool | None = None
    zBand: ZBand | None = None
    escalation: float
    contacts: list[ContactTemplate] = Field(default_factory=list)
    events: list[EventSchedule] = Field(default_factory=list)
    hazards: list[Hazard] = Field(default_factory=list)
    # Optional crew hull chosen by the GM for this scenario.
    shipClass: str | None = None
    # A local star: EM/motion sensing is scrambled by sun glare along the line
    # of sight, so a scenario can place the sun to blind a whole bearing arc.
    sun: Vec | None = None
    sunRadiusKlik: float = 0.0
    # Charted nav points / jump points the ops station can plot to.
    navPoints: list[NavPoint] = Field(default_factory=list)
    # EM/thermal layer bands for this scenario.
    layers: list[SensorLayer] = Field(default_factory=list)
    # The environment the scenario starts in (hazards override while open).
    environment: str = "clear-space"
    # Picket lines strung across the map.
    barriers: list[Barrier] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Handoff / digest
# ---------------------------------------------------------------------------


class HandoffContact(WireModel):
    id: str
    name: str
    type: ContactType
    range: float
    bearing: float
    elev: float
    course: float
    speed: float
    confidence: float


class HandoffOwn(WireModel):
    readiness: float
    batteries: float
    condition: Condition
    roe: RuleOfEngagement
    exposure: float
    # Identity: which hull, how she is painted, and how she is fitted.
    hullId: str = ""
    livery: str = ""
    modules: list[str] = Field(default_factory=list)
    loadout: dict[str, str] = Field(default_factory=dict)
    # Current defensive manoeuvre, if any.
    maneuver: str = ""
    evasive: int = 0
    # Alert condition and the defence picture, so the tabletop knows what state
    # the ship was in when the handoff was generated.
    alert: AlertLevel = "three"
    core: float = 0.0
    shields: dict[str, float] = Field(default_factory=dict)
    systems: dict[str, float] = Field(default_factory=dict)


class Barrier(WireModel):
    """A picket line: sensors strung between two points.

    Crossing one is not an instant loss — it is a *detection event* with a
    position, so it feeds the datum hunt like any other contact.
    """

    id: str
    name: str
    a: Vec
    b: Vec
    sensitivity: float = 0.6
    faction: str = "enemy"
    note: str = ""


class Hardpoint(WireModel):
    """A mount on a hull: which bearing it can bear on, and what fits it."""

    id: str
    arc: Literal["fore", "aft", "port", "starboard", "all"] = "all"
    kind: Literal["gun", "missile", "torpedo"] = "gun"
    fitted: str = ""


class ModuleSpec(WireModel):
    """A fitted accessory: budget cost, the system it rides, and its effect."""

    id: str
    name: str = ""
    power: int = 0
    massKt: float = 0.0
    cargo: float = 0.0
    system: str = ""
    shieldMultiplier: float = 1.0
    armorMultiplier: float = 1.0
    sensorBonus: float = 0.0
    fuelBonus: float = 0.0
    sparesBonus: int = 0
    note: str = ""


class EnvironmentSpec(WireModel):
    """One environment type: how it bends every system at once."""

    id: str
    name: str = "Clear space"
    sensor: float = 1.0
    emission: float = 1.0
    fuel: float = 1.0
    comms: float = 1.0
    wearPerHour: float = 1.0
    repairDcPenalty: int = 0
    contamination: str = ""
    evaRisk: str = ""
    salvage: bool = False
    crewStress: bool = False
    note: str = ""


class Ordnance(WireModel):
    """A weapon in flight — a Size-Class-1 track that can be shot down.

    Torpedoes and missiles leave as objects rather than as a resolved shot, so
    the crew can track them, decoy them, shoot them down, or let terrain break
    the lock.  They are tracked on the plot like any other contact once seen.
    """

    id: str
    kind: Literal["missile", "torpedo"] = "torpedo"
    name: str = ""
    pos: Vec
    heading: float = 0.0
    speed: float = 0.0
    fuelKlik: float = 0.0
    warhead: float = 0.0
    hostile: bool = True
    detected: bool = False
    alive: bool = True
    note: str = ""


class Ehd(WireModel):
    """Effective Hull Defence: the number a shot must beat.

    ``targetHd + evasive - tactical - rangePenalty + solutionBonus``.  Every
    term is surfaced so the tabletop (and the crew) can see exactly why a shot
    is hard.  ``hitsPerFiveOver`` is the extra hit per five points of degree on
    a full success.
    """

    targetHd: int = 0
    evasive: int = 0
    tactical: int = 0
    rangePenalty: int = 0
    solutionBonus: int = 0
    ehd: int = 0
    hitsPerFiveOver: int = 1


class HandoffWeapons(WireModel):
    prepped: bool
    targetId: str | None = None
    state: WeaponsState = "safe"
    solutionQuality: float = 0
    # The shooting problem, spelled out: see ``Ehd``.
    ehd: Ehd | None = None
    # Subsystem strike: the system aimed at, and the Targeting Check to hit it.
    targetSystem: str = ""
    subsystemCheck: CheckResult | None = None
    # Which mount was dressed and how the solution was built, for the tabletop.
    weapon: str = ""
    shotType: str = "quick"


class HandoffPack(WireModel):
    generatedAt: float
    contact: HandoffContact
    own: HandoffOwn
    weapons: HandoffWeapons
    orders: str
    summary: str
    # The setting the tabletop is playing, so the off-app resolution knows which
    # flavor's hull names and units the pack is written in.
    flavorId: str = "core"
    flavorTitle: str = ""


class LogbookDigest(WireModel):
    title: str
    theater: str
    durationMinutes: float
    contactsSeen: int
    classifiedCount: int
    hostileConfirmed: int
    handoffs: int
    rpNotes: int
    generatedAt: float
    # "won" when the crew identified the enemy first, "lost" when they were
    # painted first; None for a run that ended without resolving the race.
    outcome: str | None = None
    # Career: experience, standing, and the medals earned along the way.
    xp: int = 0
    reputation: float = 0.0
    medals: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


class AdminChannel(WireModel):
    channelId: str
    title: str
    status: GameStatus
    players: int
    hostId: str | None = None
    # The setting this room is playing, so the GM console can show and change it.
    flavorId: str = "core"


class AdminFlavorBrief(WireModel):
    """An installed flavor, for the GM console and the ``--list-flavors`` CLI."""

    id: str
    title: str
    extends: str | None = None
    hulls: int = 0
    missions: int = 0
    valid: bool = True
    error: str = ""
    # Activation state: a mod is inert until an operator switches it on.
    enabled: bool = False
    default: bool = False
    core: bool = False


class AdminPlayer(WireModel):
    sessionId: str
    userId: str
    name: str
    channelId: str
    seat: SeatId | None = None


class CampaignBrief(WireModel):
    id: str
    title: str
    theater: str


# ---------------------------------------------------------------------------
# Top-level game state
# ---------------------------------------------------------------------------


class RoomRef(WireModel):
    channelId: str
    instanceId: str


class GameState(WireModel):
    # Wire key is ``schema`` (the persisted state schema version); the attribute
    # is named ``schemaVersion`` to avoid shadowing Pydantic's BaseModel.schema.
    schemaVersion: int = Field(alias="schema")
    room: RoomRef
    # The setting (flavor) this room plays.  Recorded so a reconnecting client
    # renders the same units and art as everyone else, and so the handoff pack
    # can name the setting the tabletop is playing.  "core" is the shipped
    # default; the loader falls back to it when a flavor disappears from disk.
    flavorId: str = "core"
    campaign: CampaignSeed
    ship: ShipState
    seats: dict[SeatId, Seat]
    contacts: list[Contact] = Field(default_factory=list)
    events: list[DecisionEvent] = Field(default_factory=list)
    war: WarState
    log: list[LogEntry] = Field(default_factory=list)
    clock: float
    status: GameStatus
    hostId: str | None = None
    # The *session* that currently holds the conn — host authority is per
    # connection, not per user, so duplicate user ids cannot fight over it.
    hostSession: str | None = None
    handoffPack: HandoffPack | None = None
    digest: LogbookDigest | None = None
    autoTick: bool
    # Server-owned watch speed. ``autoTick`` remains for backwards-compatible
    # clients; new clients should use timeMode.
    timeMode: TimeMode = "paused"
    timeScale: float = 1.0
    # Action name -> simulated minute when that action becomes available.
    cooldowns: dict[str, float] = Field(default_factory=dict)
    noise: float
    noiseFilterAt: float | None = None
    seq: int
    # GM holds the clock while re-arranging pieces; ``advance`` is blocked.
    timeFrozen: bool = False
    # Deployed passive sensor buoys and the turns left on the crybaby flood.
    buoys: list[Buoy] = Field(default_factory=list)
    noisemakerTurns: int = 0
    # The detection race.  ``outcome`` is terminal: the patrol is decided the
    # moment one side fixes the other.
    outcome: Literal["won", "lost", "jumped"] | None = None
    outcomeAt: float | None = None
    endReason: str | None = None
    # Highest escalation tier already triggered, so hunters spawn once per tier.
    escalationLevel: int = 0
    # The most recent station Check, for the watch readout.  The full trail is
    # in the log; this is just the last roll.
    lastCheck: CheckResult | None = None
    # Astrometrics: candidate legs (refreshed every step), the plotted target,
    # and the committed leg with its Astrogation result.
    plotLegs: list[PlotLeg] = Field(default_factory=list)
    navTarget: str = ""
    navPlan: PlotLeg | None = None
    navCommit: NavCommit | None = None
    # Jump drive spool-up (None until ops starts one).
    jumpState: JumpState | None = None
    # Long-range comms window: orders and intel only arrive when it is open.
    commsOpen: bool = True
    commsNote: str = ""
    # --- the hunt (SUBMARINE plan §1, §3, §5) -------------------------------
    # Hunters' datums on the crew ship, the transit doctrine, and the timestamp
    # until which the aft baffles have been cleared.
    datums: list[Datum] = Field(default_factory=list)
    posture: Posture = "transit"
    bafflesClearedUntil: float = 0.0
    # The layer the ship is currently riding, and any TMA leg in progress.
    layer: str = ""
    layerCrossUntil: float = 0.0
    tma: TmaState | None = None
    # Weapons in flight (ours and theirs).
    ordnance: list[Ordnance] = Field(default_factory=list)
    # The environment the ship is in right now, and why.
    environment: str = "clear-space"
    environmentNote: str = ""
    # The module ids the yard can fit (data-driven, for the UI).
    moduleCatalog: list[str] = Field(default_factory=list)
    # Career: experience, standing with the fleet, and medals earned.
    xp: int = 0
    reputation: float = 0.0
    medals: list[str] = Field(default_factory=list)
    # Picket lines the ship has crossed, and whether one is alerted.
    barriersCrossed: list[str] = Field(default_factory=list)
    barrierAlert: bool = False
    barrierAlertUntil: float = 0.0
    # The last subsystem-targeting Check, for the handoff.
    subsystemCheck: CheckResult | None = None
