"""CAPTAIN WebSocket protocol messages.

Direct port of ``packages/shared/src/protocol.ts``.  The TypeScript union types
become Pydantic discriminated unions keyed on the ``type`` field; use the
``parse_*`` helpers to validate an incoming JSON payload.
"""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal, Union

from pydantic import Field, TypeAdapter

from .types import (
    AdminChannel,
    AdminFlavorBrief,
    AdminPlayer,
    AdminShipBrief,
    AlertLevel,
    CampaignBrief,
    Condition,
    ContactPatch,
    ContactType,
    ContactTemplate,
    EmconPatch,
    GameState,
    ShipClass,
    TimeMode,
    OperatingMode,
    HeatMode,
    Posture,
    WatchBill,
    RuleOfEngagement,
    ShotType,
    WeaponsState,
    SeatId,
    Vec,
    WireModel,
)

# ---------------------------------------------------------------------------
# Client → server
# ---------------------------------------------------------------------------


class ClientHello(WireModel):
    channelId: str
    instanceId: str
    userId: str
    name: str
    # Per-connection session id.  The client keeps it in sessionStorage so a
    # reconnect in the same tab resumes its seat, while other tabs/users are
    # separate sessions even when they share a userId.
    sessionId: str | None = None


class MsgHello(WireModel):
    type: Literal["hello"]
    hello: ClientHello


class MsgSetSeat(WireModel):
    type: Literal["setSeat"]
    seat: SeatId | None


class MsgStart(WireModel):
    type: Literal["start"]
    # Optional per-room setup: when the host starts a lobby with any of these,
    # the server rebuilds the room's state with that setting, mission and hull.
    flavorId: str | None = None
    campaignId: str | None = None
    shipId: str | None = None


class MsgAdvance(WireModel):
    type: Literal["advance"]
    minutes: float


class MsgSetAutoTick(WireModel):
    type: Literal["setAutoTick"]
    on: bool


class MsgSetTimeMode(WireModel):
    type: Literal["setTimeMode"]
    mode: TimeMode


class MsgCondition(WireModel):
    type: Literal["condition"]
    value: Condition


class MsgRoe(WireModel):
    type: Literal["roe"]
    value: RuleOfEngagement


class MsgSetAlert(WireModel):
    """Command sets the ship's alert condition (three / two / one)."""

    type: Literal["setAlert"]
    level: AlertLevel


class MsgResolveEvent(WireModel):
    type: Literal["resolveEvent"]
    eventId: str
    optionId: str


class MsgHandoffForce(WireModel):
    type: Literal["handoff:force"]


class MsgResume(WireModel):
    type: Literal["resume"]


class MsgEnd(WireModel):
    type: Literal["end"]


class MsgNavWaypoints(WireModel):
    type: Literal["nav:waypoints"]
    waypoints: list[Vec]


class MsgNavPlot(WireModel):
    """Ops selects a charted point to plot a leg to."""

    type: Literal["nav:plot"]
    navId: str


class MsgNavCommit(WireModel):
    """Commit the plotted leg; an Astrogation Check sets arrival precision."""

    type: Literal["nav:commit"]
    navId: str = ""


class MsgNavSurvey(WireModel):
    """Sensors re-survey a chart, refreshing its age."""

    type: Literal["nav:survey"]
    navId: str


class MsgNavFix(WireModel):
    """Work off dead-reckoning error: star sighting, landmark or radar ping."""

    type: Literal["nav:fix"]
    method: str = "star"


class MsgPosture(WireModel):
    """Transit doctrine: sprint loud and fast, drift slow and silent."""

    type: Literal["ops:posture"]
    posture: Posture


class MsgClearBaffles(WireModel):
    """A deliberate turn aft to clear the passive array's blind arc."""

    type: Literal["sensor:clearBaffles"]


class MsgTma(WireModel):
    """Begin a manoeuvre leg to solve a bearing-only track."""

    type: Literal["ops:tma"]
    contactId: str


class MsgManeuver(WireModel):
    """Fly a defensive manoeuvre; modifiers hold until the next helm order."""

    type: Literal["ops:maneuver"]
    maneuver: str


class MsgTargetSystem(WireModel):
    """Aim the prepped shot at a named system ("" clears to a hull shot)."""

    type: Literal["weapons:targetSystem"]
    system: str = ""


class MsgShootOrdnance(WireModel):
    """A gun solution on an inbound weapon."""

    type: Literal["sensor:shootOrdnance"]
    ordnanceId: str


class MsgSpoof(WireModel):
    """Fire a spoofing pod."""

    type: Literal["sensor:spoof"]


class MsgHeatMode(WireModel):
    """Thermal management: normal, vent (fast and loud) or bottle (quiet and hot)."""

    type: Literal["ops:heat"]
    mode: HeatMode


class MsgWatchBill(WireModel):
    """Crew rotation: standard, battle stations, or stood down to rest."""

    type: Literal["ops:watch"]
    bill: WatchBill


class MsgRally(WireModel):
    """Command rallies a shaken crew."""

    type: Literal["ops:rally"]


class MsgHangar(WireModel):
    """Launch or recover the small craft."""

    type: Literal["ops:hangar"]
    launch: bool = True


class MsgBoard(WireModel):
    """Put a boarding party aboard a derelict or prize."""

    type: Literal["comms:board"]
    contactId: str


class MsgFitModule(WireModel):
    """Fit an accessory to the hull, if the budgets allow."""

    type: Literal["dc:fitModule"]
    moduleId: str


class MsgUnfitModule(WireModel):
    """Strip an accessory back out."""

    type: Literal["dc:unfitModule"]
    moduleId: str


class MsgSalvage(WireModel):
    """Go outside in a debris field and cut spares free."""

    type: Literal["dc:salvage"]


class MsgReplenish(WireModel):
    """Take on fuel, spares and provisions at a depot."""

    type: Literal["nav:replenish"]

class MsgJumpSpool(WireModel):
    """Start charging the jump drive at a charted jump point."""

    type: Literal["jump:spool"]
    navId: str


class MsgJumpCommit(WireModel):
    type: Literal["jump:commit"]


class MsgJumpAbort(WireModel):
    type: Literal["jump:abort"]

class MsgNavSpeed(WireModel):
    type: Literal["nav:speed"]
    kps: float


class MsgNavMode(WireModel):
    type: Literal["nav:mode"]
    mode: OperatingMode


class MsgNavAltitude(WireModel):
    type: Literal["nav:altitude"]
    z: float


class MsgNavDeployBuoy(WireModel):
    """Ops drops a passive sensor buoy at the ship's current position."""

    type: Literal["nav:deployBuoy"]


class MsgNavRecoverBuoy(WireModel):
    """Ops clicks a deployed buoy on the plot to recover it to the rack."""

    type: Literal["nav:recoverBuoy"]
    buoyId: str


class MsgEwNoisemaker(WireModel):
    """Launch a crybaby: flood the EM band for a couple of turns."""

    type: Literal["ew:noisemaker"]


class MsgIntelReport(WireModel):
    """Ops files a fleet intel report on a tracked contact."""

    type: Literal["intel:report"]
    contactId: str


class MsgSensorActiveSweep(WireModel):
    type: Literal["sensor:activeSweep"]


class MsgSensorActive(WireModel):
    """Key or stow the active radar (passive/gravidar/EM are unaffected)."""

    type: Literal["sensor:active"]
    on: bool


class MsgSensorListen(WireModel):
    type: Literal["sensor:listen"]
    contactId: str


class MsgSensorGravScan(WireModel):
    type: Literal["sensor:gravScan"]


class MsgSensorNoiseFilter(WireModel):
    type: Literal["sensor:noiseFilter"]


class MsgSensorClaim(WireModel):
    type: Literal["sensor:claim"]
    contactId: str
    guess: ContactType


class MsgSensorIgnore(WireModel):
    type: Literal["sensor:ignore"]
    contactId: str


class MsgEwEmcon(WireModel):
    type: Literal["ew:emcon"]
    emcon: EmconPatch


class MsgEwSniff(WireModel):
    type: Literal["ew:sniff"]


class MsgCommsIff(WireModel):
    type: Literal["comms:iff"]
    contactId: str


class MsgCommsIntercept(WireModel):
    type: Literal["comms:intercept"]


class MsgCommsTransmit(WireModel):
    type: Literal["comms:transmit"]
    mode: Literal["tight-beam", "burst", "open", "spoof"]


class MsgWeaponsPrep(WireModel):
    type: Literal["weapons:prep"]
    contactId: str
    state: WeaponsState = "armed"
    # The mount to dress (defaults to the ship's gun) and how the solution is
    # built: a quick shot leans on the track, a refined shot adds margin.
    weapon: str | None = None
    shot: ShotType = "quick"


class MsgWeaponsStanddown(WireModel):
    type: Literal["weapons:standdown"]


class MsgDcInspect(WireModel):
    type: Literal["dc:inspect"]


class MsgDcRepair(WireModel):
    """Damage control works on one system; ``juryRig`` is a fast field patch."""

    type: Literal["dc:repair"]
    system: str
    juryRig: bool = False


class MsgDcMaintain(WireModel):
    """Scheduled upkeep on one system: strip wear before it fails."""

    type: Literal["dc:maintain"]
    system: str


class MsgRpNote(WireModel):
    type: Literal["rp:note"]
    text: str


C2S = Annotated[
    Union[
        MsgHello,
        MsgSetSeat,
        MsgStart,
        MsgAdvance,
        MsgSetAutoTick,
        MsgSetTimeMode,
        MsgCondition,
        MsgRoe,
        MsgSetAlert,
        MsgResolveEvent,
        MsgHandoffForce,
        MsgResume,
        MsgEnd,
        MsgNavWaypoints,
        MsgNavPlot,
        MsgNavCommit,
        MsgNavSurvey,
        MsgNavFix,
        MsgPosture,
        MsgClearBaffles,
        MsgTma,
        MsgManeuver,
        MsgTargetSystem,
        MsgShootOrdnance,
        MsgSpoof,
        MsgHeatMode,
        MsgWatchBill,
        MsgRally,
        MsgHangar,
        MsgBoard,
        MsgFitModule,
        MsgUnfitModule,
        MsgSalvage,
        MsgReplenish,
        MsgJumpSpool,
        MsgJumpCommit,
        MsgJumpAbort,
        MsgNavSpeed,
        MsgNavMode,
        MsgNavAltitude,
        MsgNavDeployBuoy,
        MsgNavRecoverBuoy,
        MsgSensorActiveSweep,
        MsgSensorActive,
        MsgSensorListen,
        MsgSensorGravScan,
        MsgSensorNoiseFilter,
        MsgSensorClaim,
        MsgSensorIgnore,
        MsgEwEmcon,
        MsgEwSniff,
        MsgEwNoisemaker,
        MsgIntelReport,
        MsgCommsIff,
        MsgCommsIntercept,
        MsgCommsTransmit,
        MsgWeaponsPrep,
        MsgWeaponsStanddown,
        MsgDcInspect,
        MsgDcRepair,
        MsgDcMaintain,
        MsgRpNote,
    ],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Server → client
# ---------------------------------------------------------------------------


class MsgHelloS2C(WireModel):
    type: Literal["hello"] = "hello"
    clientId: str
    state: GameState
    # Reference library for the F5-style acoustic signature comparison / F7
    # ship database. This is catalogue data, never contact truth.
    catalogue: list[ShipClass] = Field(default_factory=list)


class MsgState(WireModel):
    type: Literal["state"] = "state"
    state: GameState


class MsgPong(WireModel):
    type: Literal["pong"] = "pong"
    tick: int


class MsgError(WireModel):
    type: Literal["error"] = "error"
    message: str


S2C = Annotated[
    Union[MsgHelloS2C, MsgState, MsgPong, MsgError], Field(discriminator="type")
]

# ---------------------------------------------------------------------------
# Game-master / opposition builder area (separate admin port)
# ---------------------------------------------------------------------------


class MsgAdminHello(WireModel):
    type: Literal["admin.hello"]
    token: str | None = None


class MsgAdminList(WireModel):
    type: Literal["admin.list"]
    channelId: str | None = None


class MsgAdminSubscribe(WireModel):
    type: Literal["admin.subscribe"]
    channelId: str


class MsgAdminSpawn(WireModel):
    type: Literal["admin.spawn"]
    channelId: str
    contact: ContactTemplate


class MsgAdminUpdate(WireModel):
    type: Literal["admin.update"]
    channelId: str
    contactId: str
    patch: ContactPatch


class MsgAdminRemove(WireModel):
    type: Literal["admin.remove"]
    channelId: str
    contactId: str


class MsgAdminTension(WireModel):
    type: Literal["admin.tension"]
    channelId: str
    value: float


class MsgAdminEvent(WireModel):
    type: Literal["admin.event"]
    channelId: str
    # Deliberately permissive: the payload is untrusted GM input and is
    # sanitised by admin_events.clean_event afterwards (as in the TS server).
    event: dict[str, Any]


class MsgAdminLayout(WireModel):
    type: Literal["admin.layout"]
    channelId: str
    center: Vec
    radiusKlik: float


class MsgAdminReset(WireModel):
    type: Literal["admin.reset"]
    channelId: str
    campaignId: str | None = None
    # Optional crew hull for the new scenario; falls back to the campaign default.
    shipId: str | None = None
    # Optional setting for the room; falls back to the room's current flavor.
    flavorId: str | None = None


class MsgAdminSetShip(WireModel):
    type: Literal["admin.setShip"]
    channelId: str
    shipId: str


class MsgAdminFreeze(WireModel):
    type: Literal["admin.freeze"]
    channelId: str
    frozen: bool


class MsgAdminKick(WireModel):
    type: Literal["admin.kick"]
    channelId: str
    sessionId: str


class MsgAdminTorpedo(WireModel):
    """GM puts a weapon in the water, aimed at the crew ship."""

    type: Literal["admin.torpedo"]
    channelId: str
    kind: str = "torpedo"


class MsgAdminSetDrive(WireModel):
    """GM fits a different FTL drive to the crew hull."""

    type: Literal["admin.setDrive"]
    channelId: str
    drive: str


class MsgAdminSkills(WireModel):
    """GM authors a station's crew skills (0-99 WCRPG scores)."""

    type: Literal["admin.skills"]
    channelId: str
    seat: SeatId
    scores: dict[str, int] = Field(default_factory=dict)
    specializations: dict[str, int] = Field(default_factory=dict)


class MsgAdminActivateMod(WireModel):
    """Activate an installed setting server-wide so rooms may use it."""

    type: Literal["admin.activateMod"]
    flavorId: str


class MsgAdminDeactivateMod(WireModel):
    """Deactivate a setting; rooms on it fall back to the current default."""

    type: Literal["admin.deactivateMod"]
    flavorId: str


class MsgAdminActivateModForRoom(WireModel):
    """Switch a room onto an activated setting (rebuilds it, keeping seats)."""

    type: Literal["admin.activateModForRoom"]
    channelId: str
    flavorId: str


class MsgAdminSetDefaultMod(WireModel):
    """Set (or clear, with null) the setting new rooms start on."""

    type: Literal["admin.setDefaultMod"]
    flavorId: str | None = None


AdminC2S = Annotated[
    Union[
        MsgAdminHello,
        MsgAdminList,
        MsgAdminSubscribe,
        MsgAdminSpawn,
        MsgAdminUpdate,
        MsgAdminRemove,
        MsgAdminTension,
        MsgAdminEvent,
        MsgAdminLayout,
        MsgAdminReset,
        MsgAdminSetShip,
        MsgAdminFreeze,
        MsgAdminKick,
        MsgAdminTorpedo,
        MsgAdminSetDrive,
        MsgAdminSkills,
        MsgAdminActivateMod,
        MsgAdminDeactivateMod,
        MsgAdminActivateModForRoom,
        MsgAdminSetDefaultMod,
    ],
    Field(discriminator="type"),
]


class MsgAdminOk(WireModel):
    type: Literal["admin.ok"] = "admin.ok"
    token: bool
    channels: list[AdminChannel]
    campaigns: list[CampaignBrief]
    ships: list[AdminShipBrief] = Field(default_factory=list)
    players: list[AdminPlayer] = Field(default_factory=list)
    # Installed settings, so the GM console can offer them per room.
    flavors: list[AdminFlavorBrief] = Field(default_factory=list)
    # The station skill catalogue, so the GM console can offer valid skill names.
    skills: list[str] = Field(default_factory=list)


class MsgAdminState(WireModel):
    type: Literal["admin.state"] = "admin.state"
    channelId: str
    state: GameState


class MsgAdminError(WireModel):
    type: Literal["admin.error"] = "admin.error"
    message: str


AdminS2C = Annotated[
    Union[MsgAdminOk, MsgAdminState, MsgAdminError], Field(discriminator="type")
]


# ---------------------------------------------------------------------------
# Parse helpers
# ---------------------------------------------------------------------------

_C2S_ADAPTER: TypeAdapter[C2S] = TypeAdapter(C2S)
_ADMIN_C2S_ADAPTER: TypeAdapter[AdminC2S] = TypeAdapter(AdminC2S)


def parse_c2s(raw: str | bytes | dict) -> object:
    """Validate a client message (JSON text or already-decoded dict)."""
    data = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
    return _C2S_ADAPTER.validate_python(data)


def parse_admin_c2s(raw: str | bytes | dict) -> object:
    """Validate an admin client message."""
    data = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
    return _ADMIN_C2S_ADAPTER.validate_python(data)
