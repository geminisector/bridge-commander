"""CAPTAIN crew weapon catalog.

The bridge does not resolve fire — the engagement leaves the app as a handoff
pack.  What matters here is the **firing solution**: each mount demands a
different grade of track and a different envelope, so "prep the tubes" is a
real choice rather than a single button.

A solution is graded 0..1 from the contact's classification confidence (a
resolved spectrum adds a little).  Guns ask for very little and only reach a
few klik; missiles reach further and want a solid track; a torpedo wants a
*confirmed* hull and a long envelope.  ``solutionRequired`` is the grade, and
``rangeKlik`` is the effective envelope — beyond it the mount cannot hold.
"""

from __future__ import annotations

from .constants import REFINED_SHOT_BONUS, SOLUTION_SPECTRUM_BONUS
from .math_utils import clamp
from .types import ShotType, WeaponSpec

DEFAULT_WEAPON = "laser-cannon"

WEAPON_SPECS: dict[str, WeaponSpec] = {
    "laser-cannon": WeaponSpec(
        id="laser-cannon",
        name="Laser cannon",
        kind="gun",
        solutionRequired=0.2,
        rangeKlik=12,
        lockExposure=2,
        blurb="The dogfight gun. Unforgiving of range, forgiving of everything else.",
    ),
    "mass-driver": WeaponSpec(
        id="mass-driver",
        name="Mass driver",
        kind="gun",
        solutionRequired=0.3,
        rangeKlik=15,
        lockExposure=3,
        blurb="Kinetic, close and loud. A rough track is enough to point it.",
    ),
    "particle-cannon": WeaponSpec(
        id="particle-cannon",
        name="Particle cannon",
        kind="gun",
        solutionRequired=0.45,
        rangeKlik=18,
        lockExposure=4,
        blurb="Hard-hitting and hungry. Wants a settled track, not a smear.",
    ),
    "heat-seeker": WeaponSpec(
        id="heat-seeker",
        name="Heat-seeking missile",
        kind="missile",
        solutionRequired=0.55,
        rangeKlik=35,
        lockExposure=5,
        blurb="Tracks a drive plume out to medium range. Patient, but not picky.",
    ),
    "image-recognition-missile": WeaponSpec(
        id="image-recognition-missile",
        name="Imaging missile",
        kind="missile",
        solutionRequired=0.7,
        requiresConfirmed=True,
        rangeKlik=45,
        lockExposure=7,
        blurb="Needs a confirmed silhouette; will not fly on a guess.",
    ),
    "torpedo": WeaponSpec(
        id="torpedo",
        name="Anti-ship torpedo",
        kind="torpedo",
        solutionRequired=0.85,
        requiresConfirmed=True,
        rangeKlik=60,
        lockExposure=9,
        blurb="The capital-ship answer. A confirmed track, a long envelope, and time.",
    ),
}

# Torpedoes and imaging missiles only lock a CONFIRMED track; guns and heat
# seekers fly on a good enough solution alone.


def weapon_spec(weapon_id: str | None) -> WeaponSpec:
    """Look up a mount, falling back to the default gun."""
    if weapon_id and weapon_id in WEAPON_SPECS:
        return WEAPON_SPECS[weapon_id]
    return WEAPON_SPECS[DEFAULT_WEAPON]


def weapon_briefs() -> list[WeaponSpec]:
    return [spec.model_copy() for spec in WEAPON_SPECS.values()]


def solution_grade(confidence: float, spectrum_resolved: bool, shot: ShotType) -> float:
    """Grade a firing solution from the track, the spectrum and the shot type."""
    grade = confidence
    if spectrum_resolved:
        grade += SOLUTION_SPECTRUM_BONUS
    if shot == "refined":
        grade += REFINED_SHOT_BONUS
    return clamp(grade, 0.0, 1.0)


__all__ = [
    "DEFAULT_WEAPON",
    "WEAPON_SPECS",
    "weapon_spec",
    "weapon_briefs",
    "solution_grade",
]
