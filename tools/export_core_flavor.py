"""One-off migration: export the legacy in-code core catalog to ``mods/core``.

The flavor plugin system (``bridge/FLAVOR_PLUGIN_PLAN.md``) makes a setting a
data package.  Before the refactor, ``core`` lived in Python: the hull catalog in
``shared/ships.py``, art in ``resources/bridge_ship_art.json``, callsign pools in
``shared/campaigns.py`` and the missions as factory functions.  This script reads
that legacy surface and writes it out as the ``core`` flavor, so the default
setting keeps behaving exactly as before while the code learns to load flavors.

Run it against the *pre-refactor* tree::

    python tools/export_core_flavor.py

It is kept in the tree as a record of the migration (and to regenerate core from
a checkout that still carries the legacy constants), but normal runs never need
it: the flavor loader reads the JSON directly.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bridge.paths import PROJECT_ROOT, package_path  # noqa: E402
from bridge.shared import campaigns, ships, shipyard  # noqa: E402

OUT = PROJECT_ROOT / "mods" / "core"

STAT_KEYS = (
    "shieldFore",
    "shieldAft",
    "shieldRefresh",
    "armorFore",
    "armorAft",
    "armorPort",
    "armorStarboard",
    "body",
    "fuelCapacity",
)


def _art_basename(url: str) -> str:
    return url.rsplit("/", 1)[-1] if url else ""


def build_ships() -> dict:
    stats = ships.resolve_hull_stats()
    hulls: dict[str, dict] = {}
    for hull_id, klass in ships.SHIP_CLASSES.items():
        entry = shipyard.HULLS.get(hull_id, {})
        action, vdu = ships.SHIP_ART.get(hull_id, ("", ""))
        hull: dict = {
            "name": klass.name,
            "role": klass.role,
            "contactType": klass.contactType,
            "massKt": klass.massKt,
            "profile": klass.profile,
            "stealth": klass.stealth,
            "emission": klass.emission,
            "sensorQuality": klass.sensorQuality,
            "crew": klass.crew,
            "blurb": klass.blurb,
            "art": {"action": _art_basename(action), "vdu": _art_basename(vdu)},
            "stats": {key: stats[hull_id][key] for key in STAT_KEYS if key in stats.get(hull_id, {})},
            "hardpoints": [
                {"id": str(p.get("id", f"hp{i}")), "arc": p.get("arc", "all"), "kind": p.get("kind", "gun")}
                for i, p in enumerate(entry.get("hardpoints") or [])
            ],
        }
        for optional in ("shipType", "gunners", "cargoHold"):
            if optional in entry:
                hull[optional] = entry[optional]
        name = ships.SHIP_NAMES.get(hull_id)
        if name:
            hull["names"] = [name]
        hulls[hull_id] = hull
    return {"hulls": hulls, "defaults": dict(ships.DEFAULT_BY_TYPE)}


def build_callsigns() -> dict:
    return {
        "vesselName": "corporate",
        "adjectives": list(campaigns._ADJ),
        "nouns": list(campaigns._NOUN),
        "hostile": {
            "escort": list(campaigns.ESCORT_CLASSES),
            "capship": list(campaigns.CAPSHIP_CLASSES),
            "fighter": list(campaigns.FIGHTER_CLASSES),
        },
    }


def build_units() -> dict:
    return {
        "distance": {
            "base": "klik",
            "ladder": [{"min": 0, "unit": "klik", "factor": 1.0, "precision": 1}],
        },
        "speed": {
            "base": "kps",
            "factor": 1.0,
            "dial": {"15": "Silent Running", "60": "Cruise", "100": "Flank"},
        },
    }


def build_theme() -> str:
    css = package_path("activity", "dist", "activity.css").read_text(encoding="utf-8")
    match = re.search(r":root\s*\{.*?\}", css, re.S)
    if not match:
        raise SystemExit("could not find the :root block in activity.css")
    block = match.group(0).rstrip()
    # The two font variables are the one addition to the block: today the fonts
    # are hardcoded in activity.css, which makes them unflavorable.
    if "--font-display" not in block:
        body = block[:-1].rstrip()
        body += (
            "\n  --font-display:'Zen Dots',sans-serif;"
            "\n  --font-mono:'Share Tech Mono',monospace;"
        )
        block = body + "\n}"
    return (
        "/* core — the shipped deep-space watch theme (values verbatim from the\n"
        "   original activity.css :root block).  Served after activity.css, so a\n"
        "   flavor theme overrides it wholesale. */\n\n" + block + "\n"
    )


def build_missions() -> dict[str, dict]:
    missions: dict[str, dict] = {}
    for campaign_id in campaigns.CAMPAIGNS:
        seed = campaigns.campaign_for(campaign_id)
        missions[campaign_id] = seed.model_dump(mode="json")
    return missions


def main() -> None:
    # This script reads the *legacy* in-code core catalog, which the flavor
    # refactor removed.  It is kept as a record of how core/ships.json and
    # core/missions/*.json were derived; run it against the commit before the
    # refactor (or a checkout that still carries the constants).
    if not hasattr(campaigns, "_ADJ") or not hasattr(ships, "SHIP_NAMES"):
        raise SystemExit(
            "export_core_flavor.py only runs against the pre-refactor tree: "
            "the legacy constants it reads are now flavor data. "
            "See FLAVOR_PLUGIN_PLAN.md and tools/README if you need to rebuild core."
        )
    (OUT / "missions").mkdir(parents=True, exist_ok=True)
    # No "id" (the directory name is the id) and no file references (the
    # conventional names are discovered automatically).
    flavor = {
        "title": "Core",
        "defaultMission": "iron-collar",
    }
    _write(OUT / "flavor.json", flavor)
    _write(OUT / "units.json", build_units())
    _write(OUT / "ships.json", build_ships())
    _write(OUT / "callsigns.json", build_callsigns())
    (OUT / "theme.css").write_text(build_theme(), encoding="utf-8")
    for mission_id, doc in build_missions().items():
        _write(OUT / "missions" / f"{mission_id}.json", doc)
    print(f"wrote {len(build_ships()['hulls'])} hulls and {len(build_missions())} missions to {OUT}")


def _write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
