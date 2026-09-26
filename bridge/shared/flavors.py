"""Flavor plugin system: a setting is a data package, not a fork.

See ``bridge/FLAVOR_PLUGIN_PLAN.md``.  A **flavor** is a directory under
``bridge/flavors/<id>/`` containing a ``flavor.json`` manifest and the JSON,
CSS and images it wants to change.  A flavor inherits from ``core`` by default,
so the minimal one is a manifest plus the files it overrides::

    bridge/flavors/stk/
      flavor.json      # { "id": "stk", "title": "Star Trek" }
      units.json       # optional: distance/speed presentation
      theme.css        # optional: a :root override
      ships.json       # optional: hulls, art and the default map
      callsigns.json   # optional: name pools
      missions/*.json  # optional: CampaignSeed-shaped scenarios
      assets/          # optional: action/ and vdu/ images

Design invariants (FLAVOR_PLUGIN_PLAN.md §"Design invariants"):

* **Data only** — JSON, CSS and images.  No Python.
* **Canonical units on the wire** — every distance stays in klik; a flavor
  converts on display only, via :class:`Units`.
* **Fail closed** — a flavor that fails validation does not load; the caller
  falls back to ``core`` with a logged reason, never a half-loaded flavor.
* **No implicit inheritance of ids** — ``defaults`` and mission ``shipClass``
  references are validated against the *merged* hull list, so the
  ``lance-corvette`` class of bug cannot survive.

The loader caches each flavor once, keyed by id, so two rooms on different
flavors in one process never share art, units or hull tables.
"""

from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, get_args

from ..paths import (
    CORE_FLAVOR_ID,
    core_asset_dir,
    flavor_chain,
    flavor_dir,
    flavor_extends,
    flavors_root,
)
from .constants import CRUISE_KPS, FLANK_KPS, FREQ_BANDS
from .math_utils import hash_random
from .types import CampaignSeed, ContactType, NavKind, ShipClass

log = logging.getLogger("bridge.flavors")

#: Contact categories a ``defaults`` map can name a hull for.  Environmental
#: types map to an empty string (terrain is never a hull).
CONTACT_TYPES: tuple[str, ...] = get_args(ContactType)
NAV_KINDS: tuple[str, ...] = get_args(NavKind)

#: fields every merged hull definition must carry.
REQUIRED_HULL_FIELDS = (
    "name",
    "role",
    "contactType",
    "stats",
    "hardpoints",
    "art",
)

#: Hull fields the compiler turns into numbers, so a non-number must fail
#: validation with a reason rather than raise out of ``_compile``.
NUMERIC_HULL_FIELDS = ("massKt", "profile", "stealth", "emission", "sensorQuality", "crew")

HARDPOINT_ARCS = ("fore", "aft", "port", "starboard", "all")
HARDPOINT_KINDS = ("gun", "missile", "torpedo")
TERRAIN_TYPES = ("asteroid", "nebula", "debris", "dust", "ice")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class FlavorError(Exception):
    """A flavor failed to parse, merge or validate."""


# ---------------------------------------------------------------------------
# Units — display formatting only; the wire stays canonical
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DistanceRung:
    """One rung of the auto-scaling distance ladder.

    ``factor`` is *canonical units per display unit* (klik per AU), so a value
    converts by dividing.  The formatter picks the largest rung whose ``min``
    the value reaches, which is what lets one ladder serve a 4-klik knife fight
    and a 40-AU intercept.
    """

    min: float
    unit: str
    factor: float
    precision: int


@dataclass(frozen=True)
class Units:
    """How a flavor presents distance and speed.  Never touches the sim."""

    distance_base: str = "klik"
    ladder: tuple[DistanceRung, ...] = (
        DistanceRung(min=0.0, unit="klik", factor=1.0, precision=1),
    )
    speed_base: str = "kps"
    speed_factor: float = 1.0
    dial: tuple[tuple[float, str], ...] = ()

    # -- distance ----------------------------------------------------------

    def rung_for(self, klik: float) -> DistanceRung:
        magnitude = abs(float(klik))
        for rung in self.ladder:
            if magnitude >= rung.min:
                return rung
        return self.ladder[-1]

    def format_distance(self, klik: float, places: int | None = None) -> str:
        rung = self.rung_for(klik)
        precision = rung.precision if places is None else places
        value = float(klik) / rung.factor
        return f"{value:.{precision}f} {rung.unit}"

    # -- speed -------------------------------------------------------------

    def format_speed(self, kps: float, places: int | None = None) -> str:
        precision = 0 if places is None else places
        value = float(kps) / self.speed_factor
        return f"{value:.{precision}f} {self.speed_base}"

    def unit_label(self, kind: str = "distance") -> str:
        if kind == "speed":
            return self.speed_base
        if kind == "distance":
            return self.distance_base
        return ""

    def speed_dial_name(self, kps: float) -> str:
        """The label for the largest dial key at or below ``kps`` ("" if none)."""
        best: str = ""
        best_key = float("-inf")
        for key, label in self.dial:
            if key <= float(kps) + 1e-9 and key >= best_key:
                best_key = key
                best = label
        return best


DEFAULT_UNITS = Units()


def _positive_finite(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number > 0


def parse_units(raw: dict[str, Any] | None, *, source: str = "units.json") -> Units:
    """Validate and build :class:`Units` from a flavor's ``units.json``."""
    if raw is None:
        return DEFAULT_UNITS
    if not isinstance(raw, dict):
        raise FlavorError(f"{source}: expected an object")

    distance = raw.get("distance") or {}
    speed = raw.get("speed") or {}
    if not isinstance(distance, dict) or not isinstance(speed, dict):
        raise FlavorError(f"{source}: 'distance' and 'speed' must be objects")

    base = str(distance.get("base") or "klik")
    ladder_raw = distance.get("ladder")
    if ladder_raw is None:
        ladder_raw = [{"min": 0, "unit": base, "factor": 1.0, "precision": 1}]
    if not isinstance(ladder_raw, list) or not ladder_raw:
        raise FlavorError(f"{source}: distance.ladder must be a non-empty list")

    ladder: list[DistanceRung] = []
    for index, rung in enumerate(ladder_raw):
        if not isinstance(rung, dict):
            raise FlavorError(f"{source}: distance.ladder[{index}] must be an object")
        factor = rung.get("factor")
        if factor is None or not _positive_finite(factor):
            raise FlavorError(
                f"{source}: distance.ladder[{index}].factor must be positive and finite"
            )
        raw_min = rung.get("min")
        if raw_min is None:
            raise FlavorError(f"{source}: distance.ladder[{index}].min is required")
        try:
            minimum = float(raw_min)
        except (TypeError, ValueError) as exc:
            raise FlavorError(
                f"{source}: distance.ladder[{index}].min must be a number"
            ) from exc
        if not math.isfinite(minimum) or minimum < 0:
            raise FlavorError(f"{source}: distance.ladder[{index}].min must be >= 0")
        try:
            precision = int(rung.get("precision", 1))
        except (TypeError, ValueError) as exc:
            raise FlavorError(
                f"{source}: distance.ladder[{index}].precision must be an int"
            ) from exc
        ladder.append(
            DistanceRung(
                min=minimum,
                unit=str(rung.get("unit") or base),
                factor=float(factor),
                precision=precision,
            )
        )

    for previous, current in zip(ladder, ladder[1:]):
        if current.min > previous.min:
            raise FlavorError(
                f"{source}: distance.ladder must be ordered by descending min "
                f"({previous.min:g} then {current.min:g})"
            )
    if ladder[-1].min != 0:
        raise FlavorError(f"{source}: the last distance rung must have min 0")

    speed_factor = speed.get("factor", 1.0)
    if not _positive_finite(speed_factor):
        raise FlavorError(f"{source}: speed.factor must be positive and finite")

    dial_raw = speed.get("dial") or {}
    if not isinstance(dial_raw, dict):
        raise FlavorError(f"{source}: speed.dial must be an object")
    dial: list[tuple[float, str]] = []
    for key, label in dial_raw.items():
        try:
            number = float(key)
        except (TypeError, ValueError) as exc:
            raise FlavorError(
                f"{source}: speed.dial key {key!r} is not a number"
            ) from exc
        if not math.isfinite(number) or not (0.0 <= number <= 100.0):
            raise FlavorError(
                f"{source}: speed.dial key {key!r} must be within the 0-100 dial"
            )
        dial.append((number, str(label)))
    dial.sort(key=lambda item: item[0])

    return Units(
        distance_base=base,
        ladder=tuple(ladder),
        speed_base=str(speed.get("base") or "kps"),
        speed_factor=float(speed_factor),
        dial=tuple(dial),
    )


# ---------------------------------------------------------------------------
# Callsigns
# ---------------------------------------------------------------------------


@dataclass
class Callsigns:
    """Per-flavor name pools.

    ``vesselName`` selects the generator: ``corporate`` gives ``MV GREY FALCON``
    (the shipped style), ``surname`` gives ``Grey Falcon``-style merchant names
    and ``callsign`` gives ``Vanguard 612``-style designations.
    """

    adjectives: list[str] = field(default_factory=list)
    nouns: list[str] = field(default_factory=list)
    vessel_name: str = "corporate"
    hostile: dict[str, list[str]] = field(default_factory=dict)

    def copy(self) -> "Callsigns":
        return Callsigns(
            adjectives=list(self.adjectives),
            nouns=list(self.nouns),
            vessel_name=self.vessel_name,
            hostile={k: list(v) for k, v in self.hostile.items()},
        )

    def vessel(self, seed: int) -> str:
        if not self.adjectives or not self.nouns:
            return f"Contact {seed}"
        adjective = self.adjectives[
            int(math.floor(hash_random(seed, 11) * len(self.adjectives)))
        ]
        noun = self.nouns[int(math.floor(hash_random(seed, 12) * len(self.nouns)))]
        if self.vessel_name == "surname":
            return f"{adjective.title()} {noun.title()}"
        if self.vessel_name == "callsign":
            number = 100 + int(math.floor(hash_random(seed, 13) * 900))
            return f"{noun.title()} {number}"
        return f"MV {adjective} {noun}"

    def pool_for(self, contact_type: str) -> list[str]:
        if contact_type == "capship":
            pool = self.hostile.get("capship")
        elif contact_type == "fighter":
            pool = self.hostile.get("fighter")
        else:
            pool = self.hostile.get("escort")
        return list(pool or [])


# ---------------------------------------------------------------------------
# Ship compilation
# ---------------------------------------------------------------------------


def ship_bands(ship_id: str) -> list[float]:
    """Deterministic barcode-like frequency profile for a hull id."""
    seed = sum(ord(ch) for ch in ship_id) or 7
    bands: list[float] = []
    for i in range(FREQ_BANDS):
        v = hash_random(seed, i + 1)
        # Spiky: quiet gaps, loud ticks, a couple of strong carriers.
        bands.append(round(v if v > 0.3 else v * 0.25, 3))
    return bands


# ---------------------------------------------------------------------------
# Flavor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssetLayer:
    """An image directory and the flavor that owns it (``None`` = core)."""

    flavor: str | None
    root: Path


@dataclass
class Flavor:
    id: str
    title: str
    extends: str | None
    root: Path
    units: Units = DEFAULT_UNITS
    units_raw: dict[str, Any] = field(default_factory=dict)
    theme_css: str = ""
    theme_path: Path | None = None
    default_mission: str = ""
    callsigns: Callsigns = field(default_factory=Callsigns)
    hull_defs: dict[str, dict[str, Any]] = field(default_factory=dict)
    defaults: dict[str, str] = field(default_factory=dict)
    terrain_images: dict[str, str] = field(default_factory=dict)
    missions: dict[str, dict[str, Any]] = field(default_factory=dict)
    asset_layers: tuple[AssetLayer, ...] = ()
    findings: tuple[str, ...] = ()

    # Compiled views, built once by validation.
    ship_classes: dict[str, ShipClass] = field(default_factory=dict)
    ship_art: dict[str, tuple[str, str]] = field(default_factory=dict)
    hull_stats: dict[str, dict[str, float]] = field(default_factory=dict)
    ship_names: dict[str, str] = field(default_factory=dict)
    hull_entries: dict[str, dict[str, Any]] = field(default_factory=dict)

    # -- convenience -------------------------------------------------------

    @property
    def mission_ids(self) -> list[str]:
        return sorted(self.missions)

    def mission_seed(self, mission_id: str) -> CampaignSeed:
        doc = self.missions.get(mission_id)
        if doc is None:
            raise FlavorError(f"{self.id}: unknown mission {mission_id!r}")
        return CampaignSeed.model_validate(doc)

    def first_mission_or(self, fallback: str = "") -> str:
        if self.default_mission and self.default_mission in self.missions:
            return self.default_mission
        ordered = self.mission_ids
        if ordered:
            return ordered[0]
        return fallback

    def hull_entry(self, hull_id: str) -> dict[str, Any]:
        return dict(self.hull_entries.get(hull_id, {}))

    # -- art ---------------------------------------------------------------

    def art_url(self, filename: str, kind: str) -> str:
        """Resolve an art filename to a URL, flavor art first then core.

        A file found in a flavor's own ``assets/`` is served under
        ``/img/f/<id>/...`` so the process never confuses two flavors' art;
        everything in the core image tree keeps its historical ``/img/...`` URL.
        """
        raw = (filename or "").strip()
        if not raw:
            return ""
        if raw.startswith("/"):
            return raw
        base, _, _ext = raw.rpartition(".")
        candidates = [raw]
        if base:
            candidates += [
                f"{base}.{other}"
                for other in ("png", "gif", "jpg", "jpeg", "webp")
            ]
        seen: set[str] = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            for layer in self.asset_layers:
                if (layer.root / kind / candidate).is_file():
                    if layer.flavor is None:
                        return f"/img/{kind}/{candidate}"
                    return f"/img/f/{layer.flavor}/{kind}/{candidate}"
        return ""

    def url_exists(self, url: str) -> bool:
        if not url:
            return False
        if url.startswith("/img/f/"):
            fid, _, rel = url.removeprefix("/img/f/").partition("/")
            if not rel:
                return False
            return any((layer.root / rel).is_file() for layer in layers_for(fid))
        if url.startswith("/img/"):
            rel = url.removeprefix("/img/")
            return any((layer.root / rel).is_file() for layer in self.asset_layers)
        return False


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------


def _deep_merge(base: Any, override: Any) -> Any:
    """Recursive dict merge; every non-dict (including lists) replaces."""
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = _deep_merge(base.get(key), value)
        return merged
    return override


def _read_json(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FlavorError(f"{path.name}: {exc}") from exc
    if not isinstance(doc, dict):
        raise FlavorError(f"{path.name}: expected a JSON object")
    return doc


def _ref_path(flavor_id: str, manifest: dict[str, Any], key: str) -> Path | None:
    value = manifest.get(key)
    if not isinstance(value, str) or not value:
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = flavor_dir(flavor_id) / value
    return candidate


def _optional_json(flavor_id: str, manifest: dict[str, Any], key: str) -> dict[str, Any]:
    """Read an optional top-level manifest reference (a file, else {})."""
    path = _ref_path(flavor_id, manifest, key)
    if path is None or not path.is_file():
        return {}
    return _read_json(path)


def _read_missions(flavor_id: str, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    value = manifest.get("missions")
    missions: dict[str, dict[str, Any]] = {}
    if not isinstance(value, str) or not value:
        return missions
    root = Path(value)
    if not root.is_absolute():
        root = flavor_dir(flavor_id) / value
    if root.is_dir():
        paths = sorted(root.glob("*.json"))
    elif root.is_file():
        paths = [root]
    else:
        return missions
    for path in paths:
        doc = _read_json(path)
        mission_id = str(doc.get("id") or path.stem)
        if not mission_id:
            raise FlavorError(f"{path.name}: mission needs an id")
        missions[mission_id] = doc
    return missions


def layers_for(flavor_id: str) -> tuple[AssetLayer, ...]:
    """A flavor's own asset layer plus every ancestor's, then core's."""
    layers: list[AssetLayer] = []
    for fid in flavor_chain(flavor_id):
        root = flavor_dir(fid) / "assets"
        if root.is_dir():
            layers.append(AssetLayer(flavor=fid, root=root))
    layers.append(AssetLayer(flavor=None, root=core_asset_dir()))
    return tuple(layers)


# ---------------------------------------------------------------------------
# Loading, merging, validation, compilation
# ---------------------------------------------------------------------------


def load_flavor(flavor_id: str) -> Flavor:
    """Load, merge, validate and compile one flavor.

    Raises :class:`FlavorError` on any problem so the caller can fail closed.
    """
    return _load_flavor(flavor_id, ())


def _load_flavor(flavor_id: str, seen: tuple[str, ...]) -> Flavor:
    if flavor_id in seen:
        chain = " -> ".join((*seen, flavor_id))
        raise FlavorError(f"extends cycle: {chain}")
    root = flavor_dir(flavor_id)
    if not root.is_dir() or not (root / "flavor.json").is_file():
        raise FlavorError(f"no such flavor: {flavor_id}")
    manifest = _read_json(root / "flavor.json")
    declared = manifest.get("id")
    if declared is not None and str(declared) != flavor_id:
        raise FlavorError(
            f"flavor.json id {declared!r} does not match directory {flavor_id!r}"
        )

    extends = flavor_extends(flavor_id)
    parent: Flavor | None = None
    if extends:
        try:
            parent = _load_flavor(extends, (*seen, flavor_id))
        except FlavorError as exc:
            raise FlavorError(f"extends {extends!r}: {exc}") from exc

    flavor = Flavor(
        id=flavor_id,
        title=str(manifest.get("title") or flavor_id.title()),
        extends=extends,
        root=root,
        callsigns=_merge_callsigns(flavor_id, manifest, parent),
        defaults=_merge_defaults(flavor_id, manifest, parent),
        terrain_images=_merge_terrain(flavor_id, manifest, parent),
        hull_defs=_merge_hulls(flavor_id, manifest, parent),
        missions=_merge_missions(flavor_id, manifest, parent),
        default_mission=str(
            manifest.get("defaultMission")
            or (parent.default_mission if parent else "")
        ),
        theme_css="",
        theme_path=None,
        asset_layers=layers_for(flavor_id),
    )
    flavor.units_raw = _merge_units_raw(flavor_id, manifest, parent)
    flavor.units = parse_units(flavor.units_raw, source=f"{flavor_id}/units.json")
    flavor.theme_path = _theme_path(flavor_id, manifest, parent)
    flavor.theme_css = _theme_text(flavor.theme_path, parent)
    try:
        _validate(flavor)
        _compile(flavor)
    except FlavorError:
        raise
    except Exception as exc:  # never let a malformed flavor escape fail-closed
        raise FlavorError(f"{flavor_id}: {type(exc).__name__}: {exc}") from exc
    return flavor


def _merge_units_raw(
    flavor_id: str, manifest: dict[str, Any], parent: Flavor | None
) -> dict[str, Any]:
    raw = _optional_json(flavor_id, manifest, "units")
    if parent is None or not parent.units_raw:
        return raw
    return _deep_merge(parent.units_raw, raw)


def _merge_callsigns(
    flavor_id: str, manifest: dict[str, Any], parent: Flavor | None
) -> Callsigns:
    base = parent.callsigns if parent else Callsigns()
    raw = _optional_json(flavor_id, manifest, "callsigns")
    if not raw:
        return base.copy()
    hostile = {k: list(v) for k, v in base.hostile.items()}
    raw_hostile = raw.get("hostile")
    if isinstance(raw_hostile, dict):
        for role, pool in raw_hostile.items():
            if isinstance(pool, list):
                hostile[str(role)] = [str(item) for item in pool]
    return Callsigns(
        adjectives=[str(x) for x in (raw.get("adjectives") or base.adjectives)],
        nouns=[str(x) for x in (raw.get("nouns") or base.nouns)],
        vessel_name=str(raw.get("vesselName") or base.vessel_name),
        hostile=hostile,
    )


def _merge_defaults(
    flavor_id: str, manifest: dict[str, Any], parent: Flavor | None
) -> dict[str, str]:
    defaults: dict[str, str] = dict(parent.defaults) if parent else {}
    ships = _optional_json(flavor_id, manifest, "ships")
    raw = ships.get("defaults") if isinstance(ships, dict) else None
    if isinstance(raw, dict):
        for key, value in raw.items():
            defaults[str(key)] = str(value) if value else ""
    return defaults


def _merge_terrain(
    flavor_id: str, manifest: dict[str, Any], parent: Flavor | None
) -> dict[str, str]:
    terrain: dict[str, str] = dict(parent.terrain_images) if parent else {}
    ships = _optional_json(flavor_id, manifest, "ships")
    raw = ships.get("terrain") if isinstance(ships, dict) else None
    if isinstance(raw, dict):
        for key, value in raw.items():
            terrain[str(key)] = str(value)
    return terrain


def _merge_hulls(
    flavor_id: str, manifest: dict[str, Any], parent: Flavor | None
) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = (
        {hull_id: dict(defn) for hull_id, defn in parent.hull_defs.items()}
        if parent
        else {}
    )
    ships = _optional_json(flavor_id, manifest, "ships")
    raw_hulls = ships.get("hulls") if isinstance(ships, dict) else None
    if raw_hulls is None:
        return merged
    if isinstance(raw_hulls, dict):
        for hull_id, defn in raw_hulls.items():
            if not isinstance(defn, dict):
                raise FlavorError(f"ships.hulls[{hull_id!r}] must be an object")
            merged[str(hull_id)] = _deep_merge(merged.get(str(hull_id), {}), defn)
        return merged
    if isinstance(raw_hulls, list):
        for defn in raw_hulls:
            if not isinstance(defn, dict) or not defn.get("id"):
                raise FlavorError("ships.hulls entries need an id")
            hull_id = str(defn["id"])
            merged[hull_id] = _deep_merge(merged.get(hull_id, {}), defn)
        return merged
    raise FlavorError("ships.hulls must be an object or a list")


def _merge_missions(
    flavor_id: str, manifest: dict[str, Any], parent: Flavor | None
) -> dict[str, dict[str, Any]]:
    missions: dict[str, dict[str, Any]] = dict(parent.missions) if parent else {}
    missions.update(_read_missions(flavor_id, manifest))
    return missions


def _theme_path(
    flavor_id: str, manifest: dict[str, Any], parent: Flavor | None
) -> Path | None:
    path = _ref_path(flavor_id, manifest, "theme")
    if path is not None and path.is_file():
        return path
    return parent.theme_path if parent else None


def _theme_text(path: Path | None, parent: Flavor | None) -> str:
    if path is None:
        return parent.theme_css if parent else ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return parent.theme_css if parent else ""


def _validate(flavor: Flavor) -> None:
    findings: list[str] = []

    # A flavor that cannot start a room is not a valid flavor, even if every
    # individual file parses (invariant 11: fail closed, never half-load).
    if not flavor.hull_defs:
        findings.append("ERROR: no hulls defined — a flavor must declare a catalog")
    if not flavor.missions:
        findings.append("ERROR: no missions defined — a flavor must declare a scenario")

    for contact_type, hull_id in flavor.defaults.items():
        if contact_type not in CONTACT_TYPES:
            findings.append(
                f"ERROR: defaults has unknown contact type {contact_type!r}"
            )
        if not hull_id:
            continue
        if hull_id not in flavor.hull_defs:
            findings.append(
                f"ERROR: defaults[{contact_type!r}] names unknown hull {hull_id!r}"
            )

    for hull_id, defn in flavor.hull_defs.items():
        missing = [key for key in REQUIRED_HULL_FIELDS if key not in defn]
        if missing:
            findings.append(f"ERROR: hull {hull_id!r} is missing {', '.join(missing)}")
            continue
        contact_type = str(defn.get("contactType"))
        if contact_type not in CONTACT_TYPES:
            findings.append(
                f"ERROR: hull {hull_id!r} has unknown contactType {contact_type!r}"
            )
        for numeric_field in NUMERIC_HULL_FIELDS:
            value = defn.get(numeric_field, 0)
            if not _is_number(value):
                findings.append(
                    f"ERROR: hull {hull_id!r} {numeric_field} must be a number, "
                    f"got {value!r}"
                )
        art = defn.get("art")
        if not isinstance(art, dict):
            findings.append(f"ERROR: hull {hull_id!r} art must be an object")
        else:
            for kind, filename in art.items():
                if not filename:
                    continue
                if not flavor.art_url(str(filename), str(kind)):
                    findings.append(
                        f"ERROR: hull {hull_id!r} {kind} art not on disk: {filename}"
                    )
        hardpoints = defn.get("hardpoints")
        if not isinstance(hardpoints, list):
            findings.append(f"ERROR: hull {hull_id!r} hardpoints must be a list")
        else:
            for index, point in enumerate(hardpoints):
                if not isinstance(point, dict):
                    findings.append(
                        f"ERROR: hull {hull_id!r} hardpoints[{index}] must be an object"
                    )
                    continue
                if point.get("arc", "all") not in HARDPOINT_ARCS:
                    findings.append(
                        f"ERROR: hull {hull_id!r} hardpoints[{index}] has unknown "
                        f"arc {point.get('arc')!r}"
                    )
                if point.get("kind", "gun") not in HARDPOINT_KINDS:
                    findings.append(
                        f"ERROR: hull {hull_id!r} hardpoints[{index}] has unknown "
                        f"kind {point.get('kind')!r}"
                    )
        stats = defn.get("stats")
        if not isinstance(stats, dict) or not stats:
            findings.append(f"ERROR: hull {hull_id!r} stats must be a non-empty object")
        else:
            for key, value in stats.items():
                if not _is_number(value):
                    findings.append(
                        f"ERROR: hull {hull_id!r} stat {key!r} must be a number, "
                        f"got {value!r}"
                    )
                # A misspelled stat would otherwise be merged and then silently
                # dropped, which is exactly the typo fail-closed wants loud.
                if key not in ShipClass.model_fields:
                    findings.append(
                        f"WARN: hull {hull_id!r} has unknown stat {key!r} (ignored)"
                    )

    for contact_type, url in flavor.terrain_images.items():
        if contact_type not in TERRAIN_TYPES:
            findings.append(
                f"ERROR: terrain has unknown contact type {contact_type!r}"
            )
        elif not flavor.art_url(str(url), "action"):
            findings.append(f"ERROR: terrain {contact_type!r} art not on disk: {url}")

    for mission_id, doc in flavor.missions.items():
        try:
            seed = CampaignSeed.model_validate(doc)
        except Exception as exc:  # pydantic ValidationError
            findings.append(f"ERROR: mission {mission_id!r} does not validate: {exc}")
            continue
        names = [c.name for c in seed.contacts if c.name]
        if len(names) != len(set(names)):
            findings.append(f"ERROR: mission {mission_id!r} repeats a contact name")
        referenced = [seed.shipClass] if seed.shipClass else []
        referenced += [c.shipClass for c in seed.contacts if c.shipClass]
        for hull_id in referenced:
            if hull_id not in flavor.hull_defs:
                findings.append(
                    f"ERROR: mission {mission_id!r} names unknown hull {hull_id!r}"
                )

    if flavor.default_mission and flavor.default_mission not in flavor.missions:
        findings.append(
            f"ERROR: defaultMission {flavor.default_mission!r} is not a known mission"
        )

    flavor.findings = tuple(findings)
    errors = [f for f in findings if f.startswith("ERROR:")]
    if errors:
        raise FlavorError(f"{flavor.id}: " + "; ".join(errors[:8]))


def _compile(flavor: Flavor) -> None:
    classes: dict[str, ShipClass] = {}
    art_map: dict[str, tuple[str, str]] = {}
    stats_map: dict[str, dict[str, float]] = {}
    names: dict[str, str] = {}
    entries: dict[str, dict[str, Any]] = {}

    for hull_id, defn in flavor.hull_defs.items():
        klass = ShipClass(
            id=hull_id,
            name=str(defn.get("name") or hull_id.replace("-", " ").title()),
            role=str(defn.get("role") or "Warship"),
            contactType=defn.get("contactType", "capship"),
            massKt=float(defn.get("massKt") or 0.0),
            profile=float(defn.get("profile") or 0.0),
            stealth=float(defn.get("stealth") or 0.0),
            emission=float(defn.get("emission") or 0.0),
            sensorQuality=float(defn.get("sensorQuality") or 0.0),
            cruiseSpeed=float(defn.get("cruiseSpeed") or CRUISE_KPS),
            maxSpeed=float(defn.get("maxSpeed") or FLANK_KPS),
            crew=int(defn.get("crew") or 0),
            blurb=str(defn.get("blurb") or ""),
        )
        art = defn.get("art") or {}
        action = flavor.art_url(str(art.get("action") or ""), "action")
        vdu = flavor.art_url(str(art.get("vdu") or ""), "vdu")
        if not action and vdu:
            action = vdu
        klass.image = action
        klass.vdu = vdu
        klass.bands = ship_bands(hull_id)
        stats = {str(k): float(v) for k, v in (defn.get("stats") or {}).items()}
        for key, value in stats.items():
            if key in ShipClass.model_fields:
                setattr(klass, key, value)
        classes[hull_id] = klass
        art_map[hull_id] = (action, vdu)
        stats_map[hull_id] = stats
        declared_names = defn.get("names") or []
        if isinstance(declared_names, str):
            declared_names = [declared_names]
        names[hull_id] = str((declared_names[0] if declared_names else "") or klass.name)
        entry: dict[str, Any] = {
            "name": klass.name,
            "role": klass.role,
            "contactType": klass.contactType,
            "massKt": klass.massKt,
            "profile": klass.profile,
            "stealth": klass.stealth,
            "emission": klass.emission,
            "sensorQuality": klass.sensorQuality,
            "hardpoints": list(defn.get("hardpoints") or []),
        }
        for optional in ("shipType", "gunners", "cargoHold", "crew", "blurb"):
            if optional in defn:
                entry[optional] = defn[optional]
        entries[hull_id] = entry

    flavor.ship_classes = classes
    flavor.ship_art = art_map
    flavor.hull_stats = stats_map
    flavor.ship_names = names
    flavor.hull_entries = entries
    # Terrain overrides go through the same flavor-chain resolver as hull art,
    # so a filename becomes a servable URL and a missing file was caught above.
    flavor.terrain_images = {
        key: flavor.art_url(str(value), "action")
        for key, value in flavor.terrain_images.items()
    }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_CACHE: dict[str, Flavor] = {}
_SUMMARY_CACHE: list[dict[str, Any]] | None = None


def reset_cache() -> None:
    """Drop the per-flavor caches (tests and hot reloads)."""
    global _SUMMARY_CACHE
    _CACHE.clear()
    _SUMMARY_CACHE = None


def available() -> list[str]:
    """Every flavor directory with a manifest, core first."""
    root = flavors_root()
    ids: list[str] = []
    if root.is_dir():
        for child in sorted(root.iterdir()):
            if child.is_dir() and (child / "flavor.json").is_file():
                ids.append(child.name)
    if CORE_FLAVOR_ID in ids:
        ids.remove(CORE_FLAVOR_ID)
        ids.insert(0, CORE_FLAVOR_ID)
    return ids


def default_flavor_id() -> str:
    """``DEFAULT_FLAVOR`` when it names a real flavor, else ``core``."""
    configured = os.getenv("DEFAULT_FLAVOR", "").strip()
    if configured and (flavor_dir(configured) / "flavor.json").is_file():
        return configured
    if configured:
        log.warning(
            "DEFAULT_FLAVOR=%r is not installed; falling back to core", configured
        )
    return CORE_FLAVOR_ID


def get(flavor_id: str | None = None) -> Flavor:
    """The cached flavor, falling back to ``core`` (fail closed) on any error."""
    requested = (flavor_id or "").strip() or default_flavor_id()
    if requested in _CACHE:
        return _CACHE[requested]
    try:
        flavor = load_flavor(requested)
    except FlavorError as exc:
        log.warning(
            "flavor %r failed to load (%s); falling back to core", requested, exc
        )
        if requested == CORE_FLAVOR_ID:
            raise
        fallback = get(CORE_FLAVOR_ID)
        _CACHE[requested] = fallback
        return fallback
    _CACHE[requested] = flavor
    return flavor


def core() -> Flavor:
    return get(CORE_FLAVOR_ID)


def summaries() -> list[dict[str, Any]]:
    """One row per installed flavor, for the startup report and the CLI.

    Cached alongside the flavors themselves so a GM console refresh does not
    re-read every manifest and mission on disk.
    """
    global _SUMMARY_CACHE
    if _SUMMARY_CACHE is not None:
        return [dict(row) for row in _SUMMARY_CACHE]
    rows = _build_summaries()
    _SUMMARY_CACHE = [dict(row) for row in rows]
    return rows


def _build_summaries() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for flavor_id in available():
        try:
            flavor = load_flavor(flavor_id)
        except FlavorError as exc:
            rows.append(
                {
                    "id": flavor_id,
                    "valid": False,
                    "error": str(exc),
                    "title": flavor_id,
                    "extends": None,
                    "hulls": 0,
                    "missions": 0,
                    "units": "",
                    "findings": 0,
                }
            )
            continue
        rows.append(
            {
                "id": flavor.id,
                "valid": True,
                "error": "",
                "title": flavor.title,
                "extends": flavor.extends,
                "hulls": len(flavor.hull_defs),
                "missions": len(flavor.missions),
                "units": flavor.units.unit_label("distance"),
                "findings": len(flavor.findings),
            }
        )
    return rows


def format_summary() -> str:
    """A one-block startup summary of installed flavors."""
    rows = summaries()
    lines = [f"[bridge] flavors: {len(rows)} installed under {flavors_root()}"]
    for row in rows:
        if row["valid"]:
            extends = f" extends {row['extends']}" if row.get("extends") else ""
            lines.append(
                f"  {row['id']:<12} {row['title']}{extends} — "
                f"{row['hulls']} hulls, {row['missions']} missions, units {row['units']}"
            )
        else:
            lines.append(f"  {row['id']:<12} INVALID — {row['error']}")
    return "\n".join(lines)


__all__ = [
    "AssetLayer",
    "Callsigns",
    "CONTACT_TYPES",
    "DEFAULT_UNITS",
    "DistanceRung",
    "Flavor",
    "FlavorError",
    "NAV_KINDS",
    "Units",
    "available",
    "core",
    "default_flavor_id",
    "format_summary",
    "get",
    "layers_for",
    "load_flavor",
    "parse_units",
    "reset_cache",
    "ship_bands",
    "summaries",
]
