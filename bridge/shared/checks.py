"""d20 Check layer.

The bridge resolves most things by deterministic accumulation; this module adds
a *Check* for the moments that should be able to go spectacularly right or
wrong.  It is resolved on a **d20** to match the rest of CombatBot, not the
WCRPG book's d%:

- roll d20 and add the skill modifier; the Check succeeds on ``total >= dc``;
- a natural 20 is a critical success and a natural 1 a critical failure,
  whatever the total;
- degree of success is ``total - dc``, failure is ``dc - total``.

Skill ratings stay on the WCRPG 0-99 scale (the catalogue in
``resources/bridge_skills.json``), converted to a d20 modifier by
``skill_modifier``: 50 is the +0 baseline, 60 is +2, 95 is +9, 40 is -2.

Everything is deterministic in the simulated clock: two identical states at the
same simulated time roll the same die, at 1x, 4x or manual advance.  Rolls are
salted per action (and per contact where it matters) by the caller, so the same
minute can resolve several different Checks.
"""

from __future__ import annotations

import json
from typing import Any, cast

from ..paths import resource_path
from .math_utils import clamp, hash_random
from .types import CheckResult, SeatId

_SKILLS_FILE = "bridge_skills.json"

#: Skill rating that maps to a +0 d20 modifier.
MODIFIER_BASELINE = 50
#: Rating points per +1 (WCRPG scores are coarse; five points is one step).
MODIFIER_DIVISOR = 5
#: Keep even extreme ratings inside a sane d20 range.
MODIFIER_MIN = -5
MODIFIER_MAX = 10


def _load_skills() -> dict[str, Any]:
    path = resource_path(_SKILLS_FILE)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


_DATA = _load_skills()

#: WCRPG skill category -> its skills, verbatim from the book.
SKILL_CATEGORIES: dict[str, list[str]] = {
    str(k): [str(s) for s in v] for k, v in (_DATA.get("categories") or {}).items()
}
#: Which skills each bridge seat rolls.
STATION_SKILLS: dict[SeatId, list[str]] = {
    cast(SeatId, str(k)): [str(s) for s in v]
    for k, v in (_DATA.get("stations") or {}).items()
}
#: Named DC ladder ("routine" -> 16).  Deliberately hard.
DIFFICULTIES: dict[str, int] = {
    str(k): int(v) for k, v in (_DATA.get("difficulties") or {}).items()
}
#: Ready-made crew ratings ("crew" -> 60 -> +2).
DEFAULT_SCORES: dict[str, int] = {
    str(k): int(v) for k, v in (_DATA.get("defaults") or {}).items()
}
#: Every skill name, whatever its category.
ALL_SKILLS: tuple[str, ...] = tuple(
    skill for skills in SKILL_CATEGORIES.values() for skill in skills
)


def difficulty(name: str) -> int:
    """The DC for a named difficulty, defaulting to Routine."""
    return DIFFICULTIES.get(name.lower(), DIFFICULTIES.get("routine", 16))


def default_score(name: str = "crew") -> int:
    """A ready-made crew rating, defaulting to the crew average."""
    return DEFAULT_SCORES.get(name.lower(), DEFAULT_SCORES.get("crew", 60))


def skill_modifier(score: int) -> int:
    """Convert a 0-99 skill rating into a d20 modifier."""
    return int(
        clamp(
            (int(score) - MODIFIER_BASELINE) // MODIFIER_DIVISOR,
            MODIFIER_MIN,
            MODIFIER_MAX,
        )
    )


def roll_d20(state: Any, salt: int) -> int:
    """A d20 roll (1-20), deterministic in the simulated clock and ``salt``.

    Callers must choose a distinct salt per action, and per contact when more
    than one could resolve in the same minute.
    """
    return min(20, int(hash_random(state.clock, salt) * 20) + 1)


def resolve_check(
    modifier: int,
    dc: int,
    roll: int,
    *,
    skill: str = "",
    score: int = 0,
) -> CheckResult:
    """Resolve a d20 roll against a DC."""
    modifier = int(modifier)
    dc = int(dc)
    roll = 1 if int(roll) < 1 else 20 if int(roll) > 20 else int(roll)
    total = roll + modifier
    if roll == 20:
        outcome = "critical-success"
    elif roll == 1:
        outcome = "critical-failure"
    elif total >= dc:
        outcome = "success"
    else:
        outcome = "failure"
    success = outcome in ("critical-success", "success")
    degree = (total - dc) if success else (dc - total)
    if success and degree < 0:
        # A natural 20 can beat a DC the total could not; a success is a success.
        degree = 0
    return CheckResult(
        skill=skill,
        score=int(score),
        modifier=modifier,
        dc=dc,
        roll=roll,
        total=total,
        success=success,
        degree=degree,
        outcome=outcome,  # type: ignore[arg-type]
    )


def check(
    state: Any,
    skill: str,
    dc: int,
    salt: int,
    modifier: int | None = None,
    score: int | None = None,
) -> CheckResult:
    """Roll and resolve one Check for a station skill.

    ``modifier`` wins if supplied; otherwise it is derived from ``score``, which
    itself defaults to the crew average rating.
    """
    if score is None:
        score = default_score("crew")
    if modifier is None:
        modifier = skill_modifier(score)
    return resolve_check(
        modifier, dc, roll_d20(state, salt), skill=skill, score=int(score)
    )


__all__ = [
    "ALL_SKILLS",
    "DEFAULT_SCORES",
    "DIFFICULTIES",
    "MODIFIER_BASELINE",
    "MODIFIER_DIVISOR",
    "SKILL_CATEGORIES",
    "STATION_SKILLS",
    "check",
    "default_score",
    "difficulty",
    "resolve_check",
    "roll_d20",
    "skill_modifier",
]
