"""Effective Hull Defence (WCRPG Ch 7.6).

The bridge never rolls to hit — the shot leaves as a handoff.  What it *can* do
is make the problem legible before the engagement leaves the app:

    EHD = target HD + its evasive + range penalty - our Tactical - solution bonus

so a nimble target at long range is hard, and a good gunner with a settled
solution makes it easier.  **EHD is the number a d20 attack roll must meet or
beat** (higher is harder), which is the convention the handoff states.

A hull's HD is derived from its own stats: a small, stealthy, low-profile hull
is hard to hit and a fat transport is not.  Range penalties count five-klik
increments, scaled by what is being fired: a gun's falloff is gentle, a
torpedo's is savage.

On a full success the tabletop adds one extra hit per five points of degree.
"""

from __future__ import annotations

from .math_utils import clamp
from .types import Ehd

#: HD floor and ceiling, so no hull is unhittable or a formality.
HD_MIN = 5
HD_MAX = 30
#: A hull with no profile data still gets a middling HD.
HD_BASE = 8.0
HD_PROFILE_SCALE = 14.0
HD_STEALTH_SCALE = 4.0

#: Penalty per five-klik increment, by weapon kind.
RANGE_PENALTY_PER_INCREMENT: dict[str, int] = {
    "gun": 2,
    "turret": 2,
    "missile": 3,
    "torpedo": 5,
}
RANGE_INCREMENT_KLIK = 5.0
#: The most a good firing solution is worth against the range penalty.
SOLUTION_BONUS_MAX = 6


def hull_hd(profile: float, stealth: float) -> int:
    """A hull's base Hull Defence from its profile and stealth."""
    raw = HD_BASE + (1.0 - clamp(profile, 0, 1)) * HD_PROFILE_SCALE
    raw += clamp(stealth, 0, 1) * HD_STEALTH_SCALE
    return int(clamp(round(raw), HD_MIN, HD_MAX))


def range_penalty(kind: str, distance_klik: float) -> int:
    """Range falloff in five-klik increments for the weapon's kind."""
    per = RANGE_PENALTY_PER_INCREMENT.get(kind, 2)
    increments = int(max(0.0, distance_klik) // RANGE_INCREMENT_KLIK)
    return per * increments


def compute_ehd(
    *,
    target_hd: int,
    target_evasive: int = 0,
    tactical: int = 0,
    kind: str = "gun",
    distance_klik: float = 0.0,
    solution_quality: float = 0.0,
) -> Ehd:
    """Assemble the shot's difficulty from its parts."""
    penalty = range_penalty(kind, distance_klik)
    bonus = int(round(clamp(solution_quality, 0, 1) * SOLUTION_BONUS_MAX))
    ehd = int(
        clamp(target_hd + int(target_evasive) + penalty - int(tactical) - bonus, 0, 40)
    )
    return Ehd(
        targetHd=int(target_hd),
        evasive=int(target_evasive),
        tactical=int(tactical),
        rangePenalty=penalty,
        solutionBonus=bonus,
        ehd=ehd,
        hitsPerFiveOver=1,
    )


__all__ = [
    "HD_BASE",
    "HD_MAX",
    "HD_MIN",
    "RANGE_INCREMENT_KLIK",
    "RANGE_PENALTY_PER_INCREMENT",
    "SOLUTION_BONUS_MAX",
    "compute_ehd",
    "hull_hd",
    "range_penalty",
]
