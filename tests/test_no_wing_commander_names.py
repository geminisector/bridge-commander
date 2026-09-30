"""Regression gate: no retired *Wing Commander* name may creep back in.

`NEUTRAL_FLEET_RENAMING_PLAN.md` retires the setting vocabulary that used to be
borrowed from the *Wing Commander* series.  WCRPG attribution is deliberately
kept, so the gate allowlists the attribution files and the migration record
itself; every other tracked text file must be clean.

The names below are distinctive enough to match with word boundaries.  Generic
English words that happen to appear in the retired registry (`Sting`, `Fury`)
are left out on purpose: the `KIS`/`TCS` prefixes that made them proper nouns
are banned instead.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Distinctive retired proper nouns and universe terms.
BANNED = (
    # Hull / class names.
    "fralthi",
    "ralatha",
    "dorkathi",
    "kamekh",
    "salthi",
    "grikath",
    "raptor",
    "broadsword",
    "bengal",
    "bristol",
    "drayman",
    "tarsus",
    "longhaul",
    "venture",
    "targu",
    "gothri",
    "ralari",
    "jalthi",
    "gratha",
    "dralthi",
    "hhriss",
    "krant",
    "drakhri",
    "gorathi",
    "sabre-t",
    "fralthi-cl",
    "rapierii",
    "kamekh-s",
    # Factions, places and universe terms.
    "kilrathi",
    "kilrah",
    "k'har",
    "sumn",
    "tpka",
    "rakshasa",
    "bloodfang",
    "gemini",
    "wing commander",
    "confederation",
    "confed",
    "morvan",
    "akwende",
    # Registry prefixes.
    "tcs",
    "kis",
)

#: Files that legitimately name the retired material.
ALLOWLIST = {
    "bridge/CREDITS.md",
    "bridge/WCRPG_INTEGRATION_PLAN.md",
    "bridge/NEUTRAL_FLEET_RENAMING_PLAN.md",
    "tests/test_no_wing_commander_names.py",
}

#: Directories that legitimately name the retired material.  ``mods/wc`` is
#: the plugin plan's acceptance-test setting: it exists *because* the vocabulary
#: is now data, so it is the one place the retired names are supposed to appear.
#: It is a local/community example and is not shipped in the wheel (see
#: ``pyproject.toml`` package-data).  ``mods/wc2`` is a second local WC
#: example (a copy of ``wc``) and carries the same vocabulary by construction.
ALLOWLIST_PREFIXES = (
    "mods/wc/",
    "mods/wc2/",
)

SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pip-cache",
    ".pydeps",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "site-packages",
}


_PATTERN = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in BANNED) + r")\b", re.I)

#: Build output at the repository root.  Note that ``bridge/activity/dist`` is
#: committed source and must stay in scope.
SKIP_TOP_LEVEL = {"build", "dist"}


def _text_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        parts = path.relative_to(REPO_ROOT).parts
        if parts[0] in SKIP_TOP_LEVEL or any(part in SKIP_DIRS for part in parts):
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in ALLOWLIST or rel.startswith(ALLOWLIST_PREFIXES):
            continue
        files.append(path)
    return files


def test_the_gate_scans_the_committed_activity_bundle():
    # ``dist`` is build output at the repo root but committed source under
    # ``bridge/activity``; the whole bundle must stay in scope.
    rels = {path.relative_to(REPO_ROOT).as_posix() for path in _text_files()}
    assert "bridge/activity/dist/index.html" in rels
    assert "bridge/activity/dist/activity.js" in rels
    assert "bridge/activity/dist/activity.css" in rels
    assert "bridge/resources/bridge_hulls.json" in rels


def test_no_retired_wing_commander_names_remain():
    offenders: list[str] = []
    for path in _text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = _PATTERN.search(line)
            if match:
                rel = path.relative_to(REPO_ROOT).as_posix()
                offenders.append(f"{rel}:{lineno}: {match.group(0)}")
    assert offenders == [], "retired Wing Commander names found:\n" + "\n".join(offenders)
