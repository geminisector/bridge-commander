---
name: bridge-commander-mods
description: "Use this skill when adding, editing, validating, or activating a bridge-commander flavor (a mod) under bridge/flavors/. Covers the full data-only package: flavor.json manifest, units.json distance/speed ladders, ships.json hulls plus contact-type defaults, callsigns.json name pools, theme.css :root overrides, missions/*.json CampaignSeed scenarios, the validator's fail-closed rules, and activation through the GM mod manager or DEFAULT_FLAVOR. Triggers on: add flavor, new flavor, add mod, new mod, create setting, flavor.json, ships.json, units.json, callsigns.json, theme.css, flavor mission, hull catalog, distance ladder, contact defaults, mod manager, activate mod, DEFAULT_FLAVOR, FLAVORS_DIR, --check-flavor, --list-flavors."
whenToUse: "Adding or editing a setting/mod in bridge/flavors, debugging a flavor that fails to load, or wiring a new mod into the GM console. Not for changing simulation mechanics — flavors are presentation and content only."
---

# Adding a flavor (mod) to bridge-commander

A **flavor** is a setting: a directory of data that re-skins, re-scales and
re-narrates the bridge without shipping Python. The loader is
`bridge/shared/flavors.py`; the design spec is `bridge/FLAVOR_PLUGIN_PLAN.md`;
the authoring guide is `bridge/flavors/README.md`. Read those for depth — this
skill is the working procedure.

```
bridge/flavors/<id>/
  flavor.json      # manifest: every field optional except "id"
  units.json       # optional: distance ladder + speed dial labels
  theme.css        # optional: :root override, served after activity.css
  ships.json       # optional: hulls, art and contact-type defaults
  callsigns.json   # optional: generated-name pools
  missions/*.json  # optional: CampaignSeed-shaped scenarios
  assets/          # optional: action/ and vdu/ images
    action/*.png
    vdu/*.gif
```

Shipped flavors to copy from: `core` (the default), `wc`, `stk`, `sw`
(worked examples). `FLAVORS_DIR` overrides the root at runtime.

## Golden rules

1. **Data only.** JSON, CSS and images. No Python, no templates with code.
2. **Canonical units on the wire.** Distances stay klik and speeds stay kps in
   the sim and on the wire; `units.json` converts for display only.
3. **Fail closed.** A flavor that fails validation does not half-load: the
   server logs the reason and plays the room on the default setting. Fix the
   data; never special-case it in code.
4. **No implicit id inheritance.** Every hull id named in `defaults` or in a
   mission's `shipClass` must exist in the merged catalog. Dangling ids are load
   errors by design.
5. **Namespace new ids.** Use `<id>.<name>` (`stk.miranda`) so flat id
   namespaces never collide. Core keeps its historical bare ids.

## Recipe

```sh
# 1. Copy the closest example (extends core by default).
cp -r bridge/flavors/core bridge/flavors/mine
# 2. Set id + title in the manifest (id MUST match the directory name).
$EDITOR bridge/flavors/mine/flavor.json
# 3. Edit the data files you care about; delete the ones you do not override.
# 4. Validate. This exits non-zero on any validator error.
.venv/bin/python -m bridge --check-flavor mine
.venv/bin/python -m bridge --list-flavors
```

To replace core wholesale instead of extending it, set `"extends": null` — you
must then supply your own hull catalog **and** at least one mission.

## flavor.json

```json
{
  "id": "mine",
  "title": "My Setting",
  "extends": "core",
  "units": "units.json",
  "theme": "theme.css",
  "ships": "ships.json",
  "callsigns": "callsigns.json",
  "missions": "missions/",
  "defaultMission": "mine.first"
}
```

`extends` chains (child overrides parent); omit it to inherit `core`; set it to
`null` to stand alone. A cycle or a missing parent is a load error. A missing
file reference is simply not overridden. JSON Schema:
`bridge/flavors/schema/flavor.schema.json`.

## units.json — display only

`min` is in **canonical klik**, not display units: the formatter picks the
largest rung whose `min` the value reaches. `factor` is canonical units per
display unit, so the formatter divides. The last rung's `min` must be 0.

```json
{
  "distance": {
    "base": "klik",
    "ladder": [
      { "min": 100000000, "unit": "AU", "factor": 149597870.7, "precision": 4 },
      { "min": 1000, "unit": "Mm", "factor": 1000.0, "precision": 1 },
      { "min": 0, "unit": "klik", "factor": 1.0, "precision": 1 }
    ]
  },
  "speed": {
    "base": "kps",
    "factor": 1.0,
    "dial": { "15": "Maneuvering", "60": "Cruise", "100": "Full impulse" }
  }
}
```

Common mistake: giving an Mm rung `"min": 1.0`. 1 Mm is 1000 klik, so a 40-klik
knife fight would render as `0.0 Mm`. Use `1000`.

## ships.json — hulls, art and defaults

Merge is per hull id **and per field**, so an override may change only a name, a
stat or an art file. Use `hulls` as a map (preferred) or a list with `id` keys.

```json
{
  "hulls": {
    "mine.miranda": {
      "name": "Miranda-class cruiser",
      "role": "Light cruiser",
      "contactType": "carrier",
      "massKt": 28.8, "profile": 0.45, "stealth": 0.55,
      "emission": 0.3, "sensorQuality": 0.92, "crew": 280,
      "blurb": "A workhorse hull refit a dozen ways.",
      "art": { "action": "friendly-cruiser.png", "vdu": "friendly-cruiser-vdu.gif" },
      "stats": {
        "shieldFore": 300, "shieldAft": 200, "shieldRefresh": 150,
        "armorFore": 35, "armorAft": 25, "armorPort": 5, "armorStarboard": 5,
        "body": 330, "fuelCapacity": 6
      },
      "hardpoints": [{ "id": "fore-gun", "arc": "fore", "kind": "gun" }],
      "names": ["CS Audacity"]
    }
  },
  "defaults": {
    "unknown": "mine.miranda", "escort": "mine.miranda",
    "capship": "mine.miranda", "fighter": "mine.miranda",
    "carrier": "mine.miranda", "freighter": "mine.miranda",
    "prospector": "mine.miranda",
    "asteroid": "", "nebula": "", "debris": "", "dust": "", "ice": ""
  },
  "terrain": { "asteroid": "asteroid.png" }
}
```

- Required per hull: `name`, `role`, `contactType`, `stats`, `hardpoints`,
  `art`. Numeric fields (`massKt`, `profile`, `stealth`, `emission`,
  `sensorQuality`, `crew`) and every stat value must be numbers.
- `contactType` is one of: `unknown`, `prospector`, `freighter`, `liner`,
  `escort`, `capship`, `fighter`, `carrier`, `asteroid`, `nebula`, `debris`,
  `dust`, `ice`.
- `hardpoints` is a list of `{id, arc, kind}`; `arc` is `fore|aft|port|starboard|all`,
  `kind` is `gun|missile|torpedo`.
- `defaults` maps a contact type to a hull id; **every** contact type you rename
  the catalog for needs an entry, or a scenario that names no hull flies the
  wrong ship. Terrain keys map to `""`. Unknown keys and unknown hull values are
  load errors.
- `art` is optional in effect: filenames resolve flavor-first, then up the
  `extends` chain, then the core image tree (`bridge/img`, or `ASSET_DIR`), so a
  hull can reuse core art by filename. A flavor's own file is served at
  `/img/f/<id>/action/<file>`. A filename that resolves nowhere is a load error.
- `terrain` overrides the terrain contact images through the same resolver.

The physics shapes match the core catalog, so copy a core hull's stats and
hardpoints and change the names/flavor text rather than inventing numbers.

## callsigns.json

```json
{
  "vesselName": "registry",
  "adjectives": ["USS", "NCC", "SS"],
  "nouns": ["Enterprise", "Voyager", "Defiant"],
  "hostile": {
    "escort": ["IKS Rotarran-01", "IKS Rotarran-02"],
    "capship": ["IRW D'deridex-01", "IKS Negh'Var-01"],
    "fighter": ["Jem'Hadar-01", "Jem'Hadar-02"]
  }
}
```

`vesselName` selects the generator: `corporate` (`MV GREY FALCON`), `surname`
(`Grey Falcon`), `callsign` (`Vanguard 612`), `registry` (`USS Enterprise`).
Lists replace the inherited list; `hostile` pools merge per role. Hostile pools
are used for `escort`, `capship` and `fighter` contacts and are de-duplicated
within a scenario.

## theme.css

A straight `:root` override served after `activity.css`, so all existing markup
resolves. Set `--font-display` and `--font-mono` to change type; the core values
are Zen Dots and Share Tech Mono. `@import` a font at the top if you use a new
one. Copy `bridge/flavors/core/theme.css` and change the palette.

## missions/*.json

Mirrors `CampaignSeed` field-for-field; the loader is
`CampaignSeed.model_validate(doc)`. Positions are explicit, so placement is
deterministic — a flavor must never introduce its own randomness.

```json
{
  "id": "mine.first",
  "title": "First Patrol",
  "theater": "My Sector",
  "brief": "Opening situation.",
  "target": "What winning looks like.",
  "startHour": 0,
  "patrol": { "center": { "x": 0, "y": 0, "z": 0 }, "radiusKlik": 70 },
  "clutter": 0.3,
  "escalation": 20,
  "shipClass": "mine.miranda",
  "zBand": { "min": 3, "max": 12 },
  "environment": "clear-space",
  "contacts": [
    { "x": 8, "y": -30, "z": 4, "heading": 20, "speed": 62, "type": "escort",
      "faction": "enemy", "hostile": true, "emitting": true,
      "name": "IKS Rotarran", "shipClass": "mine.miranda", "radiusKlik": null }
  ],
  "events": [{ "atMinute": 60, "template": "fleetnet" }],
  "hazards": [
    { "id": "mine.ion", "type": "ion-storm", "title": "Ion storm",
      "startMinute": 0, "endMinute": 240, "intensity": 1.4,
      "noise": 0.05, "exposure": 0.5, "concealment": 0.4 }
  ],
  "navPoints": [
    { "id": "mine.relay", "name": "Relay", "kind": "nav",
      "pos": { "x": 40, "y": 12, "z": 0 }, "radiusKlik": 8, "chartAgeHours": 96 }
  ],
  "layers": [
    { "id": "surface", "name": "Surface duct", "zMin": 0, "zMax": 10, "note": "Loud." }
  ],
  "barriers": []
}
```

- Required contact fields: `x`, `y`, `heading`, `speed`, `type`, `faction`,
  `hostile`, `emitting`. Optional: `z`, `name`, `shipClass`, `radiusKlik`.
- `shipClass` must be a hull id in the merged catalog; the same holds for the
  mission's own `shipClass` (the crew hull).
- Explicit `contacts[].name` values must be unique within the mission.
- `events[].template` must be a core decision-event template: `fleetnet`
  (`sosus` alias), `unmarked`, `distress`, `orders`, `probe`,
  `weapons-warning`, `relay`, `challenge`, `civilian`, `false-surrender`,
  `contactclose`. Flavors cannot add templates.
- Hazard `type` is matched by substring to an environment: asteroid, nebula,
  ice, dust, debris, radiation/solar, ion, gravity/well.

## Validate and fix

```sh
.venv/bin/python -m bridge --check-flavor mine   # load one flavor; exit 1 on error
.venv/bin/python -m bridge --list-flavors        # all installed flavors + counts
```

The validator rejects, among others: a missing hull catalog or no missions;
missing required hull fields; non-numeric stats or hull fields; a bad
`contactType`, hardpoint `arc`/`kind`; art that resolves nowhere; unknown
`defaults` keys or dangling hull ids; a mission that fails `CampaignSeed`; a
mission `shipClass` not in the catalog; duplicate contact names; an unsorted
unit ladder, a non-positive factor, a last rung whose `min` is not 0, or a dial
key outside 0-100. `--list-flavors` marks invalid flavors `INVALID` with the
reason; `get()` falls back to core and logs why.

## Activate the mod

Installed is not the same as active. Mods start **disabled**; `core` is always
active.

- GM console → **Mods / settings**: ACTIVATE/DEACTIVATE server-wide, USE IN ROOM
  (rebuilds that room on the setting's `defaultMission`, keeping seats), SET
  DEFAULT / CLEAR DEFAULT for new rooms. Persisted in the `mods` table in
  `DATA_DIR/bridge.sqlite`.
- `DEFAULT_FLAVOR=<id>` or `python -m bridge --flavor <id>` counts as an
  explicit activation at boot.
- Programmatically (tests): `from bridge.server import mods; mods.activate("mine")`
  then `mods.set_default("mine")` if it should be the default.

A room records its `flavorId` in state; if the mod is deactivated or removed
from disk the room falls back to the default on load and stays playable.

## Test it

Add coverage to `tests/test_flavors.py` (or a sibling). The established pattern:
build a throwaway flavor tree with the `flavor_home` fixture, or assert on a
shipped example. Run the repo gates:

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check bridge tests
.venv/bin/mypy bridge
node --check bridge/server/admin-ui/admin.js
```

A shipped example should be covered by the parameterised
`test_example_mods_are_namespaced_and_playable` table (namespaced hulls,
`defaults` resolve, a room builds and advances). Also add a `--check-flavor`
assertion if you add a new shipped example.

## Packaging and licensing

Only `flavors/core/**`, `flavors/schema/**` and `flavors/README.md` ship in the
built wheel (`pyproject.toml` `[tool.setuptools.package-data]`). Third-party
settings (`wc`, `stk`, `sw`) are deliberately local examples: do **not** add a
new third-party flavor to package-data, and note that a contributed flavor that
names someone else's universe is the contributor's responsibility. A flavor
containing retired Wing Commander vocabulary must be added to the allowlist in
`tests/test_no_wing_commander_names.py` (the gate otherwise fails the build),
and only if that is the deliberate intent.

## Checklist

- [ ] Directory name matches `flavor.json` `id`; ids namespaced `<id>.<name>`.
- [ ] `ships.json` defines every hull it references, with all required fields.
- [ ] `defaults` covers every contact type the flavor renames; values resolve.
- [ ] `units.json` ladder is descending by canonical klik and ends at `min: 0`.
- [ ] Art filenames resolve (flavor `assets/`, then chain, then core `img/`).
- [ ] Missions validate, reference known hulls, and have unique explicit names.
- [ ] `--check-flavor <id>` and `--list-flavors` are clean.
- [ ] `.venv/bin/python -m pytest -q`, ruff and mypy pass.
- [ ] Tests added for any shipped example.
- [ ] Not added to package-data; licensing noted if third-party.
