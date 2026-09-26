"""CAPTAIN campaign factories.

Direct port of ``packages/shared/src/campaigns.ts``.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable

from ..paths import resource_path
from .math_utils import hash_random
from .types import (
    CampaignSeed,
    ContactTemplate,
    ContactType,
    EventSchedule,
    Faction,
    Hazard,
    Barrier,
    NavPoint,
    Patrol,
    SensorLayer,
    Vec,
)

_ADJ = ["GRAY", "BLUE", "LONG", "RED", "RUST", "STILL", "SLOW", "BROKEN", "COLD", "HARD", "SOFT", "FAT"]
_NOUN = ["VEGA", "TRITON", "APOLLO", "MERIDIAN", "PERSEUS", "SOLACE", "JANUS", "CYGNUS", "AURORA", "HARVEST", "TITAN", "VULCAN", "LYRA"]

# Hostile callsign pools.  Each pool holds numbered variants of one role, so two
# hostile contacts of the same role do not read identically on the plot.
ESCORT_CLASSES = ["Enemy_Escort-01", "Enemy_Escort-02", "Enemy_Escort-03", "Enemy_Escort-04"]
CAPSHIP_CLASSES = ["Enemy_Cruiser-01", "Enemy_Destroyer-01", "Enemy_HeavyTransport-01", "Enemy_Cruiser-02"]
FIGHTER_CLASSES = [
    "Enemy_Fighter-01",
    "Enemy_Fighter-02",
    "Enemy_Fighter-03",
    "Enemy_Fighter-04",
    "Enemy_Fighter-05",
    "Enemy_Fighter-06",
    "Enemy_Fighter-07",
]


def _round(x: float) -> int:
    """JS ``Math.round`` (half away from zero / toward +inf for positives)."""
    return int(math.floor(x + 0.5))


def vessel_name(seed: int) -> str:
    adj = _ADJ[int(math.floor(hash_random(seed, 11) * len(_ADJ)))]
    noun = _NOUN[int(math.floor(hash_random(seed, 12) * len(_NOUN)))]
    return f"MV {adj} {noun}"


def military_name(pool: list[str], i: int, used: set[str] | None = None) -> str:
    """Pick a callsign variant from a numbered pool.

    ``i`` is the caller's running index.  When ``used`` names the contacts
    already in the scenario, the next free variant is taken so two contacts of
    the same role never share a callsign.
    """
    if not pool:
        return ""
    start = (max(i, 1) - 1) % len(pool)
    for offset in range(len(pool)):
        candidate = pool[(start + offset) % len(pool)]
        if used is None or candidate not in used:
            return candidate
    return pool[start]


def _circ(a: int, camp_seed: int) -> Vec:
    ang = hash_random(camp_seed, a) * math.pi * 2
    rad = 30 + hash_random(camp_seed, a + 100) * 60
    return Vec(x=math.cos(ang) * rad, y=math.sin(ang) * rad, z=0.0)


def _mk(
    s: int,
    idx: int,
    ctype: ContactType,
    faction: Faction,
    hostile: bool,
    emitting: bool,
    kps: float,
    ship_class: str | None = None,
) -> ContactTemplate:
    p = _circ(idx, s)
    # The catalog runs on a 0-100 kps dial; the campaign tables below are
    # written on the old 3-16 scale, so lift them into the new range.
    speed = _round(min(100.0, kps * 7.5 + hash_random(s, idx * 13) * 30))
    return ContactTemplate(
        x=_round(p.x),
        y=_round(p.y),
        heading=_round(hash_random(s, idx * 7) * 360),
        speed=speed,
        type=ctype,
        faction=faction,
        hostile=hostile,
        emitting=emitting,
        shipClass=ship_class,
    )


def _ev(s: int, at_minute: float, template: str) -> EventSchedule:
    return EventSchedule(
        atMinute=at_minute + _round(hash_random(s, at_minute) * 40), template=template
    )


def _external_events(s: int, campaign_id: str) -> list[EventSchedule]:
    path = resource_path("bridge_events.json")
    try:
        entries = json.loads(path.read_text(encoding="utf-8")).get(campaign_id, [])
    except (OSError, json.JSONDecodeError):
        entries = []
    return [_ev(s, float(item["atMinute"]), str(item["template"])) for item in entries]


def _external_hazards(campaign_id: str) -> list[Hazard]:
    path = resource_path("bridge_hazards.json")
    try:
        entries = json.loads(path.read_text(encoding="utf-8")).get(campaign_id, [])
    except (OSError, json.JSONDecodeError):
        entries = []
    return [Hazard.model_validate(item) for item in entries]


def _external_layers() -> list[SensorLayer]:
    path = resource_path("bridge_layers.json")
    try:
        entries = json.loads(path.read_text(encoding="utf-8")).get("layers", [])
    except (OSError, json.JSONDecodeError):
        entries = []
    return [
        SensorLayer(
            id=str(item["id"]),
            name=str(item["name"]),
            zMin=float(item.get("zMin", 0)),
            zMax=float(item.get("zMax", 10)),
            note=str(item.get("note", "")),
        )
        for item in entries
    ]


def _external_barriers(campaign_id: str) -> list[Barrier]:
    path = resource_path("bridge_barriers.json")
    try:
        entries = json.loads(path.read_text(encoding="utf-8")).get(campaign_id, [])
    except (OSError, json.JSONDecodeError):
        entries = []
    return [
        Barrier(
            id=str(item["id"]),
            name=str(item["name"]),
            a=Vec(x=float(item.get("ax", 0)), y=float(item.get("ay", 0)), z=0),
            b=Vec(x=float(item.get("bx", 0)), y=float(item.get("by", 0)), z=0),
            sensitivity=float(item.get("sensitivity", 0.6)),
            faction=str(item.get("faction", "enemy")),
            note=str(item.get("note", "")),
        )
        for item in entries
    ]


def _external_nav_points(campaign_id: str) -> list[NavPoint]:
    path = resource_path("bridge_nav_points.json")
    try:
        entries = json.loads(path.read_text(encoding="utf-8")).get(campaign_id, [])
    except (OSError, json.JSONDecodeError):
        entries = []
    return [
        NavPoint(
            id=str(item["id"]),
            name=str(item["name"]),
            kind=item.get("kind", "nav"),
            pos=Vec(
                x=float(item.get("x", 0)),
                y=float(item.get("y", 0)),
                z=float(item.get("z", 0)),
            ),
            radiusKlik=float(item.get("radiusKlik", 6.0)),
            chartAgeHours=float(item.get("chartAgeHours", 0.0)),
            note=str(item.get("note", "")),
            jumpType=item.get("jumpType", "stable"),
            windowOpen=float(item.get("windowOpen", 0.0)),
            windowClose=(
                float(item["windowClose"])
                if item.get("windowClose") is not None
                else None
            ),
            alignmentRequired=float(item.get("alignmentRequired", 0.6)),
            interference=float(item.get("interference", 0.0)),
            dest=(
                Vec(
                    x=float(item["dest"].get("x", 0)),
                    y=float(item["dest"].get("y", 0)),
                    z=float(item["dest"].get("z", 0)),
                )
                if item.get("dest")
                else None
            ),
        )
        for item in entries
    ]


def _iron_collar(s: int) -> CampaignSeed:
    contacts = [
        _mk(s, 1, "prospector", "neutral", False, False, 3),
        _mk(s, 2, "prospector", "neutral", False, False, 4),
        _mk(s, 3, "freighter", "neutral", False, False, 9),
        _mk(s, 4, "freighter", "neutral", False, False, 11),
        _mk(s, 5, "liner", "neutral", False, False, 16),
        _mk(s, 6, "escort", "enemy", True, True, 12),
        _mk(s, 7, "escort", "enemy", True, True, 15),
        _mk(s, 8, "capship", "enemy", True, False, 5),
    ]
    return CampaignSeed(
        id="iron-collar",
        title="Iron Collar Patrol",
        theater="North Foster Strait",
        brief=(
            "A supply war has closed the strait. Your ship is the tripwire: keep the "
            "pattern on the traffic, build a picture of who is coming through, and do "
            "not get pinned."
        ),
        target="Classify every persistent contact. Report the enemy patrol pattern. Avoid being targeted.",
        startHour=2,
        patrol=Patrol(center=Vec(x=0, y=0, z=0), radiusKlik=90),
        clutter=0.1,
        escalation=32,
        contacts=contacts,
        events=_external_events(s, "iron-collar"),
    )


def _whale_road(s: int) -> CampaignSeed:
    contacts = [
        _mk(s, 1, "freighter", "neutral", False, False, 8),
        _mk(s, 2, "freighter", "neutral", False, False, 9),
        _mk(s, 3, "freighter", "neutral", False, False, 10),
        _mk(s, 4, "liner", "neutral", False, False, 6),
        _mk(s, 5, "escort", "enemy", True, True, 12),
        _mk(s, 6, "escort", "enemy", True, True, 14),
        _mk(s, 7, "capship", "enemy", True, False, 6),
    ]
    return CampaignSeed(
        id="whale-road",
        title="Whale Road Run",
        theater="Hastings Reach",
        brief=(
            "A freighter convoy is transiting under escort. Your orders: shadow it, "
            "break down its screen, call the report line, and stay off their scopes."
        ),
        target="Track the convoy. ID its escort. Send a traffic report. Do not be detected.",
        startHour=6,
        patrol=Patrol(center=Vec(x=0, y=0, z=0), radiusKlik=75),
        clutter=0.05,
        escalation=46,
        contacts=contacts,
        events=_external_events(s, "whale-road"),
    )


def _capship_sniff(s: int) -> CampaignSeed:
    contacts = [
        _mk(s, 1, "prospector", "neutral", False, False, 4),
        _mk(s, 2, "freighter", "neutral", False, False, 9),
        _mk(s, 3, "freighter", "neutral", False, False, 8),
        _mk(s, 4, "capship", "enemy", True, False, 3),
        _mk(s, 5, "capship", "enemy", True, False, 4),
    ]
    return CampaignSeed(
        id="capship-sniff",
        title="Capship Sniff",
        theater="Deep Quartet Basin",
        brief=(
            "A hostile fleet carrier is believed to be slipping dark through this "
            "basin. Do not sprint, do not scan. Find the big quiet one by patience and "
            "geometry alone."
        ),
        target="Locate and fix the capital ship. Build a confirmed firing solution. (Firing happens off-app.)",
        startHour=0,
        patrol=Patrol(center=Vec(x=0, y=0, z=0), radiusKlik=110),
        clutter=0.3,
        escalation=24,
        sun=Vec(x=-180, y=90, z=0),
        sunRadiusKlik=55.0,
        contacts=contacts,
        events=_external_events(s, "capship-sniff"),
    )


def _lima_drift(s: int) -> CampaignSeed:
    contacts = [
        _mk(s, 1, "prospector", "neutral", False, False, 5),
        _mk(s, 2, "liner", "neutral", False, False, 7),
        _mk(s, 3, "escort", "enemy", True, True, 11),
        _mk(s, 4, "escort", "enemy", True, True, 13),
        _mk(s, 5, "freighter", "neutral", False, False, 10),
    ]
    return CampaignSeed(
        id="lima-drift",
        title="Lima Drift",
        theater="Hostile Approaches",
        brief=(
            "Tight patrol lanes, a lot of traffic masking people who do not want to be "
            "seen. Get into your loiter box, monitor the resupply axis, then ease out."
        ),
        target="Loiter undetected. Fix the axis of traffic. Carry a clean egress.",
        startHour=1,
        patrol=Patrol(center=Vec(x=0, y=0, z=0), radiusKlik=70),
        clutter=0.2,
        escalation=42,
        contacts=contacts,
        events=_external_events(s, "lima-drift"),
    )


def _rubble_run(s: int) -> CampaignSeed:
    contacts = [
        _mk(s, 1, "prospector", "neutral", False, False, 4),
        _mk(s, 2, "prospector", "neutral", False, False, 5),
        _mk(s, 3, "freighter", "neutral", False, False, 9),
        _mk(s, 4, "freighter", "neutral", False, False, 11),
        _mk(s, 5, "liner", "neutral", False, False, 7),
        _mk(s, 6, "escort", "enemy", True, True, 12),
        _mk(s, 7, "capship", "enemy", True, False, 5),
    ]
    return CampaignSeed(
        id="rubble-run",
        title="Rubble Run",
        theater="Vega Belt",
        brief=(
            "An asteroid belt lanes a thousand traders and hides everyone else. Hold "
            "the belt mouth, sort the freighters from the wolves, and mind the rocks — "
            "among the rubble every gravidar read lies."
        ),
        target="Hold the belt mouth. Classify the traffic. Trust the waveform board, not the masses.",
        startHour=3,
        patrol=Patrol(center=Vec(x=0, y=0, z=0), radiusKlik=80),
        clutter=0.8,
        escalation=38,
        contacts=contacts,
        events=_external_events(s, "rubble-run"),
    )


def _sector_9_anomaly(s: int) -> CampaignSeed:
    contacts = [
        _mk(s, 1, "fighter", "enemy", True, True, 12, ship_class="enemy-heavy-fighter"),
        _mk(s, 2, "fighter", "enemy", True, True, 13, ship_class="enemy-heavy-fighter"),
        _mk(s, 3, "fighter", "enemy", True, True, 11, ship_class="enemy-heavy-fighter"),
        _mk(s, 4, "capship", "enemy", True, False, 6, ship_class="enemy-destroyer"),
        _mk(s, 5, "capship", "enemy", True, False, 5, ship_class="enemy-destroyer"),
        # Sensor terrain: scatter with the dust and debris, refract with the ice.
        ContactTemplate(x=-34, y=18, heading=0, speed=0, type="debris", faction="neutral", hostile=False, emitting=False),
        ContactTemplate(x=26, y=42, heading=0, speed=0, type="dust", faction="neutral", hostile=False, emitting=False),
        ContactTemplate(x=8, y=-30, heading=0, speed=0, type="ice", faction="neutral", hostile=False, emitting=False),
        ContactTemplate(x=-52, y=-24, heading=0, speed=0, type="asteroid", faction="neutral", hostile=False, emitting=False),
    ]
    return CampaignSeed(
        id="sector-9-anomaly",
        title="Sector 9 Anomaly",
        theater="Hostile Outer Reach",
        brief=(
            "You have CS Audacity. A hostile hunter-killer group is sweeping the "
            "drift — three heavy fighters flying the screen and two destroyers "
            "holding the lane. You cannot fight them. Use the debris, dust and ice "
            "to break their sensor picture and slip past unseen."
        ),
        target=(
            "Avoid detection. Cross the drift without being fixed by the heavy-fighter "
            "screen or the destroyer picket. Run dark and let the terrain lie for you."
        ),
        startHour=22,
        patrol=Patrol(center=Vec(x=0, y=0, z=0), radiusKlik=110),
        clutter=0.6,
        escalation=70,
        shipClass="home",
        sun=Vec(x=210, y=-140, z=0),
        sunRadiusKlik=40.0,
        contacts=contacts,
        events=_external_events(s, "sector-9-anomaly"),
    )


def _silent_vigil(s: int) -> CampaignSeed:
    """Endurance scenario: six hours dark, nothing may build a track on you."""
    contacts = [
        # The screen sweeps in long, straight runs.  Every track is drawn to
        # pass outside its own lock reach *provided the crew stays dark* — the
        # whole fight is emissions discipline, not gunnery.
        ContactTemplate(
            x=-150, y=90, heading=90, speed=70, type="escort",
            faction="enemy", hostile=True, emitting=True, shipClass="enemy-escort",
        ),
        ContactTemplate(
            x=-120, y=-100, heading=0, speed=55, type="escort",
            faction="enemy", hostile=True, emitting=False, shipClass="enemy-escort",
        ),
        ContactTemplate(
            x=-70, y=80, heading=90, speed=90, type="fighter",
            faction="enemy", hostile=True, emitting=True, shipClass="enemy-heavy-fighter",
        ),
        ContactTemplate(
            x=40, y=-60, heading=180, speed=40, type="prospector",
            faction="neutral", hostile=False, emitting=False, shipClass="friendly-prospector",
        ),
    ]
    return CampaignSeed(
        id="silent-vigil",
        title="Silent Vigil",
        theater="Ransom Rift",
        brief=(
            "A hostile hunter-killer screen is sweeping the rift for six hours "
            "while a convoy slips through behind you. Your job is to be invisible: "
            "no radar, no transmissions, no track. Sit dark and let the watch pass."
        ),
        target="Survive six hours undetected. No hostile may build a track on you.",
        startHour=0,
        patrol=Patrol(center=Vec(x=0, y=0, z=0), radiusKlik=130),
        clutter=0.25,
        escalation=6,
        shipClass="home",
        contacts=contacts,
        events=_external_events(s, "silent-vigil"),
    )


def _empty_lane(s: int) -> CampaignSeed:
    """Disengagement scenario: hold the box and wait every hostile out."""
    contacts = [
        # All three transit outward from inside the disengage envelope, so the
        # crew genuinely waits them out rather than never being threatened.
        ContactTemplate(
            x=-50, y=0, heading=270, speed=100, type="escort",
            faction="enemy", hostile=True, emitting=True, shipClass="enemy-escort",
        ),
        ContactTemplate(
            x=30, y=60, heading=0, speed=100, type="escort",
            faction="enemy", hostile=True, emitting=True, shipClass="enemy-escort",
        ),
        ContactTemplate(
            x=0, y=-95, heading=180, speed=100, type="fighter",
            faction="enemy", hostile=True, emitting=True, shipClass="enemy-fighter",
        ),
    ]
    return CampaignSeed(
        id="empty-lane",
        title="The Empty Lane",
        theater="Tyr Holding",
        brief=(
            "A raider squadron is transiting your holding box. Flag command wants "
            "the lane proven empty, not a fight: hold your ground, let them run "
            "their course, and confirm when the last hull has cleared the box."
        ),
        target="Wait out every hostile until they clear the box. Do not be fixed.",
        startHour=0,
        patrol=Patrol(center=Vec(x=0, y=0, z=0), radiusKlik=120),
        clutter=0.1,
        escalation=8,
        shipClass="home",
        contacts=contacts,
        events=_external_events(s, "empty-lane"),
    )


def _full_sweep(s: int) -> CampaignSeed:
    """All-tracked scenario: find and hold a track on every hostile."""
    contacts = [
        # Lying dark and close enough for the passive grill to work.  No hull
        # here is manoeuvring, so the job is sensor work, not evasion.
        ContactTemplate(
            x=32, y=0, heading=0, speed=0, type="escort",
            faction="enemy", hostile=True, emitting=False, shipClass="enemy-escort",
        ),
        ContactTemplate(
            x=-18, y=28, heading=0, speed=0, type="escort",
            faction="enemy", hostile=True, emitting=False, shipClass="enemy-escort",
        ),
        ContactTemplate(
            x=6, y=-34, heading=0, speed=0, type="fighter",
            faction="enemy", hostile=True, emitting=False, shipClass="enemy-heavy-fighter",
        ),
        ContactTemplate(
            x=-40, y=-20, heading=0, speed=0, type="freighter",
            faction="neutral", hostile=False, emitting=False, shipClass="friendly-freighter",
        ),
    ]
    return CampaignSeed(
        id="full-sweep",
        title="Full Sweep",
        theater="Bex Reach",
        brief=(
            "A raider wolfpack is lying dark in the reach, and command will not "
            "commit the convoy until every hull is on the board. Find them all, "
            "hold a track on each, and do it without lighting up."
        ),
        target="Detect and track every hostile contact. Weapons stay safe.",
        startHour=0,
        patrol=Patrol(center=Vec(x=0, y=0, z=0), radiusKlik=90),
        clutter=0.2,
        escalation=6,
        shipClass="home",
        contacts=contacts,
        events=_external_events(s, "full-sweep"),
    )


CAMPAIGNS: dict[str, Callable[[int], CampaignSeed]] = {
    "iron-collar": _iron_collar,
    "whale-road": _whale_road,
    "capship-sniff": _capship_sniff,
    "lima-drift": _lima_drift,
    "rubble-run": _rubble_run,
    "sector-9-anomaly": _sector_9_anomaly,
    "silent-vigil": _silent_vigil,
    "empty-lane": _empty_lane,
    "full-sweep": _full_sweep,
}


def campaign_for(campaign_id: str | None) -> CampaignSeed:
    key = campaign_id if campaign_id and campaign_id in CAMPAIGNS else "iron-collar"
    fn = CAMPAIGNS.get(key) or CAMPAIGNS["iron-collar"]
    seed = ord(campaign_id[0]) if campaign_id else 7
    result = fn(seed)
    result.hazards = _external_hazards(key)
    result.navPoints = _external_nav_points(key)
    result.layers = _external_layers()
    result.barriers = _external_barriers(key)
    return result


CAMPAIGN_TITLES: dict[str, str] = {k: v(0).title for k, v in CAMPAIGNS.items()}
