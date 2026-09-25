"""CAPTAIN decision-event templates.

Direct port of ``packages/shared/src/events.ts``.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from .constants import DEFAULT_ADVANCE_MINUTES, ENGAGEMENT_RANGE_KLIK
from .math_utils import hash_random
from .types import DecisionEvent, DecisionOption, EventEffect, GameState


def _round(x: float) -> int:
    return int(math.floor(x + 0.5))


def _js_num(x: float) -> str:
    """Format a number the way a JS template literal would.

    ``state.clock`` is a float in Python but is integral during normal play;
    ``f"{120.0}"`` would give ``"120.0"`` where JS gives ``"120"``.
    """
    return str(int(x)) if float(x).is_integer() else repr(x)


def engagement_prompt(state: GameState, contact_id: str) -> DecisionEvent:
    contact = next((c for c in state.contacts if c.id == contact_id), None)
    name = contact.name if contact else "contact"
    if contact:
        rng = _round(
            math.hypot(
                contact.pos.x - state.ship.pos.x, contact.pos.y - state.ship.pos.y
            )
        )
    else:
        rng = ENGAGEMENT_RANGE_KLIK
    return DecisionEvent(
        id=f"engage-{contact_id}",
        title="CONTACT CLOSING — engagement window",
        kind="engagement",
        deadline=state.clock + 60,
        source="command",
        text=(
            f"{name} is {rng} klik out and closing. This is where the app handsover: "
            "your crew resolves the fight however you like (tabletop, another sim, "
            "improv). Generate the handoff pack, resolve the engagement on your terms, "
            "then resume the patrol."
        ),
        options=[
            DecisionOption(
                id="resolve",
                label="Resolve the engagement (generate handoff)",
                hint="Pauses the patrol and dumps the readiness/contact pack.",
                effect=EventEffect(
                    handoff=True,
                    targetId=contact_id,
                    log="Crew resolved the engagement with $NAME.",
                ),
            ),
            DecisionOption(
                id="evade",
                label="Break contact",
                hint="Run dark. Costs time, risks a detection.",
                effect=EventEffect(
                    exposure=6,
                    tension=4,
                    log="Crew chose to break contact with $NAME.",
                ),
            ),
            DecisionOption(
                id="shadow",
                label="Keep shadowing, no engagement",
                hint="Stay with it but do not fire.",
                effect=EventEffect(tension=8, log="Crew continues shadowing $NAME."),
            ),
        ],
    )


def _fleetnet_event(s: GameState) -> DecisionEvent:
    return DecisionEvent(
        id=f"fleetnet-{_js_num(s.clock)}",
        title="Fleetnet update — long-baseline net",
        kind="intel",
        deadline=s.clock + DEFAULT_ADVANCE_MINUTES * 2,
        source="intel",
        text=(
            "The fleet sensor net passes a contact cut: broadband, slow, bearing on "
            "your 112. Not good enough for a firing solution, but the fix quiets one "
            "corner of the map."
        ),
        options=[
            DecisionOption(
                id="plot",
                label="Plot the cut (gain a bearing fix)",
                effect=EventEffect(
                    log="Fleetnet cut plotted on 112 — free bearing fix. Quietens the 112-292 axis."
                ),
            ),
            DecisionOption(
                id="ignore",
                label="File it",
                effect=EventEffect(log="Fleetnet cut filed without action."),
            ),
        ],
    )


def _unmarked(s: GameState) -> DecisionEvent:
    return DecisionEvent(
        id=f"unmarked-{_js_num(s.clock)}",
        title="Unmarked contact in your patrol box",
        kind="intel",
        deadline=s.clock + DEFAULT_ADVANCE_MINUTES * 4,
        source="naval-intel",
        text=(
            "An unregistered survey buoy lamps up forty minutes north of your hold "
            "point. Reported traffic says nothing in that grid. Someone is running "
            "dark or someone is lying."
        ),
        options=[
            DecisionOption(
                id="sweep",
                label="Run a passive sweep that way",
                effect=EventEffect(
                    log="Crew re-focused the passive sweep. One unknown contact now shows a faint track."
                ),
            ),
            DecisionOption(
                id="hold",
                label="Keep your box clean",
                effect=EventEffect(log="Crew held position, let it pass."),
            ),
        ],
    )


def _distress(s: GameState) -> DecisionEvent:
    return DecisionEvent(
        id=f"distress-{_js_num(s.clock)}",
        title="Distress beacon — freighter hull breach",
        kind="comms",
        deadline=s.clock + DEFAULT_ADVANCE_MINUTES * 5,
        source="comms",
        text=(
            "Broadband comms carry a garbled beacon from a freighter: hull breach "
            "aft, venting, requesting assistance. You are the nearest source of help, "
            "but answering means committing your position to a transmitter and "
            "vectoring into a possibly-cornered area."
        ),
        options=[
            DecisionOption(
                id="answer",
                label="Answer on the transmitter",
                hint="+exposure, +reputation pressure release",
                effect=EventEffect(
                    exposure=8,
                    tension=-4,
                    log="Answered the beacon over Tx — position partially compromised.",
                ),
            ),
            DecisionOption(
                id="watch",
                label="Listen only",
                effect=EventEffect(log="Crew monitored the beacon without transmitting."),
            ),
            DecisionOption(
                id="ignore",
                label="Log it and ignore",
                effect=EventEffect(log="Beacon logged and ignored."),
            ),
        ],
    )


def _orders(s: GameState) -> DecisionEvent:
    north_south = "north" if hash_random(s.clock, 8) > 0.5 else "south"
    east = "-east" if hash_random(s.clock, 9) > 0.5 else ""
    distance = 40 + _round(hash_random(s.clock, 7) * 40)
    return DecisionEvent(
        id=f"orders-{_js_num(s.clock)}",
        title="Orders from fleet command — relocate",
        kind="comms",
        deadline=s.clock + DEFAULT_ADVANCE_MINUTES * 6,
        source="flag-command",
        text=(
            f"Flag command wants a new hold point {distance} klik to your "
            f"{north_south}{east}, and a second pass over your current lane before you "
            "go. This moves you out of position for whatever is coming in on the far "
            "bearing."
        ),
        options=[
            DecisionOption(
                id="comply",
                label="Comply — new hold point",
                effect=EventEffect(log="Crew complies: relocating per flag command."),
            ),
            DecisionOption(
                id="reply",
                label="Reply: request offset",
                hint="stay for the incoming contact",
                effect=EventEffect(
                    tension=4,
                    log="Crew requested a 60-minute offset to hold the current contact.",
                ),
            ),
        ],
    )


def _probe(s: GameState) -> DecisionEvent:
    return DecisionEvent(
        id=f"probe-{_js_num(s.clock)}",
        title="Active probe — something is scanning",
        kind="danger",
        deadline=s.clock + DEFAULT_ADVANCE_MINUTES * 2,
        source="sensors",
        text=(
            "An escort is sweeping with active scan down your bearing. If they are "
            "hunting, someone has already painted you — split cycles and go quiet."
        ),
        options=[
            DecisionOption(
                id="quiet",
                label="Go dead dark, hold station",
                hint="big emission reduction, slow drift",
                effect=EventEffect(log="Crew went dead dark. The probe passed, faint."),
            ),
            DecisionOption(
                id="estimate",
                label="Push a passive fix and shift",
                effect=EventEffect(
                    exposure=5, log="Crew pushed a fix and eased away quietly."
                ),
            ),
        ],
    )


def _weapons_warning(s: GameState) -> DecisionEvent:
    return DecisionEvent(
        id=f"weapons-warning-{_js_num(s.clock)}", title="Weapons board — uncertain lock", kind="weapons",
        deadline=s.clock + DEFAULT_ADVANCE_MINUTES * 3, source="weapons",
        text="The weapons board has a partial solution, but the contact is inside a clutter shadow. Commit early, wait for a clean track, or stand down.",
        options=[
            DecisionOption(id="lock", label="Take the lock now", hint="Fast, but exposes the ship.", effect=EventEffect(exposure=7, tension=5, log="Weapons took an uncertain lock.")),
            DecisionOption(id="wait", label="Hold at standby", hint="Preserves discipline while the solution improves.", effect=EventEffect(tension=2, log="Weapons held standby and waited for a cleaner solution.")),
            DecisionOption(id="standdown", label="Stand down", effect=EventEffect(log="Weapons stood down rather than fire on a bad picture.")),
        ],
    )


def _relay(s: GameState) -> DecisionEvent:
    return DecisionEvent(
        id=f"relay-{_js_num(s.clock)}",
        title="Comms relay — a clean path home",
        kind="comms",
        deadline=s.clock + DEFAULT_ADVANCE_MINUTES * 2,
        source="comms",
        text=(
            "A friendly comms relay swings through your arc. Routing traffic "
            "through it keeps your own transmitter cold, but it puts your message "
            "on someone else's schedule — and in someone else's log."
        ),
        options=[
            DecisionOption(
                id="relay",
                label="Bounce the traffic through the relay",
                hint="quiet on our own signature",
                effect=EventEffect(
                    relay=True,
                    tension=-1,
                    log="Crew routed the transmission through the relay — our own transmitter stayed cold.",
                ),
            ),
            DecisionOption(
                id="direct",
                label="Transmit direct",
                effect=EventEffect(tension=1, log="Crew transmitted direct rather than trust the relay."),
            ),
        ],
    )


def _challenge(s: GameState) -> DecisionEvent:
    return DecisionEvent(
        id=f"challenge-{_js_num(s.clock)}",
        title="Picket challenge — respond to interrogation",
        kind="comms",
        deadline=s.clock + DEFAULT_ADVANCE_MINUTES * 2,
        source="comms",
        text=(
            "A picket line throws an interrogation at you: squawk authentication "
            "now. Answering proves you are who you say you are; ignoring it makes "
            "you the most interesting thing on that watch officer's screen."
        ),
        options=[
            DecisionOption(
                id="answer",
                label="Answer the challenge",
                hint="run a challenge-response",
                effect=EventEffect(
                    challenge=True,
                    exposure=2,
                    log="Crew answered the picket's challenge.",
                ),
            ),
            DecisionOption(
                id="spoof",
                label="Spoof the authentication",
                hint="buys time, risks exposure",
                effect=EventEffect(
                    exposure=7,
                    tension=4,
                    log="Crew spoofed the picket's authentication.",
                ),
            ),
            DecisionOption(
                id="dark",
                label="Go comms-dark",
                effect=EventEffect(
                    exposure=3,
                    tension=2,
                    log="Crew let the challenge go unanswered and went dark.",
                ),
            ),
        ],
    )


def _civilian(s: GameState) -> DecisionEvent:
    return DecisionEvent(
        id=f"civilian-{_js_num(s.clock)}",
        title="Civilian traffic crossing the box",
        kind="comms",
        deadline=s.clock + DEFAULT_ADVANCE_MINUTES * 3,
        source="comms",
        text=(
            "A civilian hull wanders into the patrol box on someone else's "
            "schedule: no escort, no manifest worth the name, and a transponder "
            "that could be genuine or could be a coat. Hailing it may firm up the "
            "picture — or make you the loudest thing in the sector."
        ),
        options=[
            DecisionOption(
                id="hail",
                label="Hail the traffic",
                effect=EventEffect(
                    civilian=True, log="Crew hailed the civilian traffic."
                ),
            ),
            DecisionOption(
                id="shadow",
                label="Shadow it silently",
                effect=EventEffect(log="Crew shadowed the traffic without transmitting."),
            ),
        ],
    )


def _false_surrender(s: GameState) -> DecisionEvent:
    return DecisionEvent(
        id=f"false-surrender-{_js_num(s.clock)}",
        title="Surrender call — the target strikes its colours",
        kind="weapons",
        deadline=s.clock + DEFAULT_ADVANCE_MINUTES * 2,
        source="weapons",
        text=(
            "The contact breaks off and sings out a surrender: powering down, "
            "offering to heave to. It is either a broken enemy or a knife in a "
            "smiling hand — and you have one watch step to decide which."
        ),
        options=[
            DecisionOption(
                id="accept",
                label="Accept the surrender",
                hint="close to boarding range",
                effect=EventEffect(
                    falseSurrender=True,
                    tension=-2,
                    log="Crew accepted the surrender call and closed.",
                ),
            ),
            DecisionOption(
                id="verify",
                label="Hold off and demand authentication",
                effect=EventEffect(
                    challenge=True,
                    exposure=2,
                    log="Crew held off, demanding authentication before closing.",
                ),
            ),
            DecisionOption(
                id="doubt",
                label="Treat it as a trick",
                effect=EventEffect(
                    exposure=3,
                    tension=3,
                    log="Crew treated the surrender as a trick and stayed at action stations.",
                ),
            ),
        ],
    )


def _contactclose(s: GameState) -> DecisionEvent:
    enemy = next(
        (c for c in s.contacts if c.state == "confirmed" and c.hostile), None
    )
    if enemy:
        return engagement_prompt(s, enemy.id)
    likely = next(
        (c for c in s.contacts if c.state == "classified" and c.hostile), None
    )
    if likely:
        return engagement_prompt(s, likely.id)
    ordered = sorted(
        s.contacts,
        key=lambda c: math.hypot(c.pos.x - s.ship.pos.x, c.pos.y - s.ship.pos.y),
    )
    if ordered:
        return engagement_prompt(s, ordered[0].id)
    return make_event(s, "probe")


_T: dict[str, Callable[[GameState], DecisionEvent]] = {
    "sosus": _fleetnet_event,  # legacy alias for saved runs
    "fleetnet": _fleetnet_event,
    "unmarked": _unmarked,
    "distress": _distress,
    "orders": _orders,
    "probe": _probe,
    "weapons-warning": _weapons_warning,
    "relay": _relay,
    "challenge": _challenge,
    "civilian": _civilian,
    "false-surrender": _false_surrender,
    "contactclose": _contactclose,
}


def make_event(state: GameState, template: str) -> DecisionEvent:
    fn = _T.get(template)
    if fn is None:
        return _T["orders"](state)
    return fn(state)
