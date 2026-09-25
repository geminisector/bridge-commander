"""Sanitise a game-master supplied decision event.

Direct port of ``apps/server/src/admin-events.ts`` (``cleanEvent``).  Every
string is length-clamped and every numeric field is coerced, so a sloppy GM
payload can never corrupt the running game state.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from ..shared.types import (
    ContactTemplate,
    DecisionEvent,
    DecisionOption,
    EventEffect,
    GameState,
)

def _num(v: Any) -> float:
    """``const num = (v) => typeof v === 'number' && Number.isFinite(v) ? v : 0``."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return 0.0
    if v != v or v in (float("inf"), float("-inf")):  # NaN / Infinity
        return 0.0
    return float(v)


def _field(obj: Any, name: str, default: Any = None) -> Any:
    """Read ``name`` from a Pydantic model or a plain dict."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _text(v: Any, default: str) -> str:
    """``String(v ?? default)``."""
    return default if v is None else str(v)


def _bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _safe_id(value: Any, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]+", "-", str(value or "")).strip("-_.")
    return (cleaned or fallback)[:40]


def clean_event(state: GameState, ev: Any) -> DecisionEvent:
    raw_id = _field(ev, "id")
    ev_id = _safe_id(
        raw_id,
        f"gm-ev-{uuid.uuid4().hex[:12]}",
    )

    raw_options = _field(ev, "options")
    options_list = raw_options if isinstance(raw_options, (list, tuple)) else []

    options: list[DecisionOption] = []
    for i, o in enumerate(list(options_list)[:4]):
        o_id = _safe_id(_field(o, "id"), f"{ev_id}-o{i}")

        label = _text(_field(o, "label"), "Option")[:80]

        raw_hint = _field(o, "hint")
        hint = str(raw_hint)[:120] if raw_hint else None

        effect = _field(o, "effect")
        raw_log = _field(effect, "log")
        log = str(raw_log)[:300] if raw_log else None

        launches = _field(effect, "launchContacts")
        launch_contacts: list[ContactTemplate] | None = None
        if isinstance(launches, (list, tuple)):
            launch_contacts = []
            for value in launches:
                try:
                    launch_contacts.append(
                        value
                        if isinstance(value, ContactTemplate)
                        else ContactTemplate.model_validate(value)
                    )
                except (TypeError, ValueError):
                    continue

        raw_target = _field(effect, "targetId")
        target_id = _safe_id(raw_target, "target") if raw_target else None
        raw_lose = _field(effect, "loseTrack")
        lose_track = _bool(raw_lose) if raw_lose is not None else None
        raw_handoff = _field(effect, "handoff")
        handoff = _bool(raw_handoff) if raw_handoff is not None else None
        # Comms / weapons outcomes.  Like ``handoff``/``loseTrack`` these are
        # tri-state: absent means "not part of this option".
        raw_relay = _field(effect, "relay")
        relay = _bool(raw_relay) if raw_relay is not None else None
        raw_challenge = _field(effect, "challenge")
        challenge = _bool(raw_challenge) if raw_challenge is not None else None
        raw_civilian = _field(effect, "civilian")
        civilian = _bool(raw_civilian) if raw_civilian is not None else None
        raw_surrender = _field(effect, "falseSurrender")
        false_surrender = _bool(raw_surrender) if raw_surrender is not None else None

        options.append(
            DecisionOption(
                id=o_id,
                label=label,
                hint=hint,
                effect=EventEffect(
                    exposure=_num(_field(effect, "exposure")),
                    tension=_num(_field(effect, "tension")),
                    log=log,
                    launchContacts=launch_contacts,
                    loseTrack=lose_track,
                    handoff=handoff,
                    targetId=target_id,
                    relay=relay,
                    challenge=challenge,
                    civilian=civilian,
                    falseSurrender=false_surrender,
                ),
            )
        )

    deadline = _num(_field(ev, "deadline")) or (state.clock + 60)

    return DecisionEvent(
        id=ev_id,
        title=_text(_field(ev, "title"), "GM event")[:80],
        kind=_text(_field(ev, "kind"), "intel")[:24],
        deadline=deadline,
        text=_text(_field(ev, "text"), "")[:600],
        source=_text(_field(ev, "source"), "GM")[:24],
        options=options,
    )


# TypeScript spelling kept for callers doing a mechanical diff.
cleanEvent = clean_event

__all__ = ["clean_event", "cleanEvent"]
