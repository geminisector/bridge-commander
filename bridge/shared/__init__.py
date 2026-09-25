"""BRIDGE COMMANDER shared package.

Re-exports the whole shared surface (mirrors ``packages/shared/src/index.ts``)
plus the small helpers that ``index.ts`` adds on top.
"""

from __future__ import annotations

from .campaigns import *  # noqa: F401,F403
from .checks import *  # noqa: F401,F403
from .constants import *  # noqa: F401,F403
from .drives import *  # noqa: F401,F403
from .ehd import *  # noqa: F401,F403
from .environments import *  # noqa: F401,F403
from .shipyard import *  # noqa: F401,F403
from .missions import *  # noqa: F401,F403
from .events import *  # noqa: F401,F403
from .math_utils import *  # noqa: F401,F403
from .protocol import *  # noqa: F401,F403
from .ships import *  # noqa: F401,F403
from .types import *  # noqa: F401,F403
from .weapons import *  # noqa: F401,F403

from .constants import CONFIDENCE_BY_STATE, STATE_ORDER, TYPE_NAMES
from .math_utils import format_clock
from .types import ContactState, ContactType, LogbookDigest, RuleOfEngagement


def is_confirmed(s: ContactState) -> bool:
    return s == "confirmed"


def state_of_confidence(c: float) -> ContactState:
    for s in reversed(STATE_ORDER):
        if c >= CONFIDENCE_BY_STATE[s]:
            return s
    return "unknown"


def describe_type(t: ContactType) -> str:
    return TYPE_NAMES.get(t, TYPE_NAMES["unknown"])


_ROE_LABELS: dict[RuleOfEngagement, str] = {
    "safe": "WEAPONS SAFE",
    "hold": "HOLD",
    "free": "WEAPONS FREE",
}


def roe_label(r: RuleOfEngagement) -> str:
    return _ROE_LABELS[r]


def digest_text(d: LogbookDigest) -> str:
    h = int(d.durationMinutes // 60)
    m = int(d.durationMinutes % 60)
    lines = [
        f"**BRIDGE COMMANDER — after-action log · {d.title}**",
        f"Theater: {d.theater} · Duration: {h}h {m}m",
        "",
        f"Contacts seen: {d.contactsSeen} · Classified: {d.classifiedCount} · Confirmed hostiles: {d.hostileConfirmed}",
        f"Combat handoffs: {d.handoffs} · Crew roleplay notes: {d.rpNotes}",
    ]
    if d.outcome == "won":
        lines.append("**RESULT: PATROL WON — the enemy was identified first.**")
    elif d.outcome == "lost":
        lines.append("**RESULT: PATROL LOST — the crew ship was painted first.**")
    lines += [
        "",
        f"_Ship's log sealed at {format_clock(d.generatedAt)}._",
    ]
    return "\n".join(lines)
