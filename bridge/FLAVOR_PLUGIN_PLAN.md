# Flavor Plugin Plan

## Problem

The content model is welded to one fictional universe in six places at once:

1. **Units.** `klik` is a hardcoded constant *and* a naming convention baked
   into ~40 identifiers (`rangeKlik`, `cpaKlik`, `offsetKlik`, `radiusKlik`,
   `NAV_FIX_BASE_KLIK`, `JUMP_RANGE_KLIK`, `KLIK_PER_KPS_HOUR`) and every
   display string in `engine.py`, `events.py` and `ehd.py`. A Star Trek
   campaign wants AU; BSG wants MGLT/hr.
2. **Theme.** 17 CSS custom properties are defined once in `activity.css:9-27`,
   with fonts hardwired to Zen Dots + Share Tech Mono at lines 5 and 34.
3. **Hulls.** One `bridge_hulls.json`, one flat id namespace, and a hardcoded
   `DEFAULT_BY_TYPE` (`ships.py:452-466`) pointing at core ids.
4. **Art.** One `bridge_ship_art.json` behind a process-global `ASSET_DIR`
   override (`paths.py:17-23`).
5. **Missions.** `CAMPAIGNS` (`campaigns.py:494`) is a dict of Python factory
   functions. A flavor cannot ship Python safely.
6. **Callsigns.** Three faction-flavoured variant pools hardcoded at
   `campaigns.py:28-34`.

Adding a setting today is a fork. This plan makes a setting a data package.

## Goals

- Any setting — a re-skinned core, Star Trek, Star Wars, BSG, Farscape — loads as
  a **data-only** package.
- `core` is the default flavor and stays exactly as playable as today.
- A flavor is standalone by default, or names a parent to extend (override two
  hulls of a base setting) — inheritance is opt-in, so no mod silently mixes
  another universe's hulls and missions into its own.
- Units, theme, hulls, art, callsigns and missions are independently
  flavorable; a flavor provides only what it overrides.
- No flavor executes code.
- ROADMAP invariants 1 (determinism) and 6 (data-driven content) still hold.

## Non-goals

- **No mid-scenario switching.** The flavor is chosen when the scenario starts
  and is recorded in state. Switching mid-run would invalidate sensor contacts,
  fuel range rings and the handoff pack.
- **No browser-side flavor install.** Flavors are a server-side directory,
  deployed with the app.
- **No new mechanics.** Flavors re-skin, re-scale and re-narrate. A flavor that
  needs a new rule gets it in core, not in the flavor.

## Prerequisites

`NEUTRAL_FLEET_RENAMING_PLAN.md` lands first. It makes `core` WC-free, which
means the new system has a genuinely generic default to extend, and it stabilizes
the 28 art filenames and 15 hull ids that a flavor's `defaults` block must
reference. Doing the plugin work first means building it against a catalog that
is about to be renamed.

## Design invariants

These extend the ROADMAP list; a flavor that breaks one is a bad flavor.

9. **Data only.** A flavor is JSON, CSS and images. No Python, no imports, no
   templates with code.
10. **Canonical units on the wire.** Every distance crossing the wire is in
    `*Klik`. Flavors convert on display. Sensor physics, determinism and
    persistence never see flavor units.
11. **Fail closed.** A flavor that fails validation does not load, and the
    server falls back to `core` with a logged reason. It never half-loads.
12. **No implicit inheritance of ids.** A flavor that renames a core hull id must
    declare a replacement. Dangling `defaults` are a validation error — this is
    exactly the `lance-corvette` bug (`types.py:582`) that survived because
    `shipClass` is a free-form `str`.

## Layout

```
mods/                          # player-facing, at the project root
  core/                        # today's catalog, unchanged, becomes the default
    flavor.json theme.css units.json ships.json callsigns.json missions/
  wc/ stk/ sw/ bsg/ farscape/
    flavor.json
    theme.css
    ships.json
    callsigns.json
    missions/*.json
    assets/action/*.png
    assets/vdu/*.gif
```

A flavor is standalone by default and carries its own catalog; naming `extends`
opts into another setting's data. Art is optional either way: a flavor with no
`assets/` falls back to the packaged `img/` tree.

*Landed later:* the directory moved out of the package to the project-root
`mods/` folder so a player can copy it; a wheel install falls back to the
packaged `bridge/flavors` tree, which `setup.py` populates with `core` and the
schemas. See the implementation notes at the end.

## Manifest

```json
{
  "title": "Star Trek",
  "extends": "core",
  "defaultMission": "stk.babel"
}
```

The manifest is **optional** and every field in it is optional. The **directory
name is the flavor id**, so there is no id to declare (an `id` key, if written,
is an assertion that must match the folder). The conventional filenames —
`units.json`, `theme.css`, `ships.json`, `callsigns.json`, `missions/` — are
discovered automatically; a key only appears to point at a file in a
non-standard place or to disable a copied file with `null`. `extends` is opt-in:
omit it (or write `null`) for a standalone setting, or name a parent to chain
onto. Ids are namespaced `<flavor>.<name>` (`stk.miranda`) to keep the flat id
namespaces in `ships.py` and the state blob from colliding. Core ids keep their
current names so existing scenarios keep resolving.

## Units

Distance and speed are **separate** blocks, because the iconic scales differ in
kind: BSG's MGLT is a time, so it only works as a speed.

```json
{
  "distance": {
    "base": "klik",
    "ladder": [
      { "min": 1.496e8, "unit": "AU",   "factor": 1.495978707e8, "precision": 4 },
      { "min": 1.0,    "unit": "Mm",   "factor": 1.0e3,          "precision": 1 },
      { "min": 0,      "unit": "klik", "factor": 1.0,           "precision": 1 }
    ]
  },
  "speed": {
    "base": "kps",
    "factor": 1.0,
    "dial": { "15": "Silent Running", "60": "Cruise", "100": "Full Ahead" }
  }
}
```

`factor` is always **canonical units per display unit**, so the ladder divides.
The auto-scaling ladder picks the largest rung where the value is ≥ `min`, so one
ladder serves a 4-klik knife fight and a 40-AU intercept without the flavor
author hand-tuning a range. `dial` relabels the 0-100 speed dial
(`SILENT_KPS`/`CRUISE_KPS`/`FLANK_KPS`, `constants.py:56-60`), which is how a
flavor ships "Silent Running / Cruise / Full Ahead" or "Idle / Flank / Battle
Station" without touching physics.

The loader exposes `format_distance(klik)`, `format_speed(kps)`,
`unit_label(kind)` and `speed_dial_name(kps)`. Every `"...klik"` display string
routes through these. **Identifier and constant names do not change** — that is
a large refactor with no gameplay benefit, and invariant 10 keeps them stable by
construction.

`MGLT` is a useful cautionary case: its real-world value is an author estimate,
not a measured constant. That is precisely why it belongs in flavor data rather
than `constants.py`, and why the schema takes an arbitrary `factor` rather than
enumerating known units.

## Theme

A straight override of the existing `:root` block, so all current markup
resolves without edits:

```css
:root{
  --bg:#0a0a0c; --bg-deep:#000; --panel:#141414; --panel-2:#1e1e1e;
  --line:#3a3a3a; --text:#e8e8e8; --text-dim:#909090;
  --accent:#ff9c1a; --accent-hover:#ffb84d;
  --glow:0 0 8px rgba(255,156,26,.35);
  --glow-hover:0 0 15px rgba(255,184,77,.75);
  --cyan:var(--accent); --dim:#7a88aa;
  --amber:#f9d71c; --red:#ff6b73; --green:#21d054; --active:#3d2a08;
  --font-display:'Orbitron',sans-serif;
  --font-mono:'Share Tech Mono',monospace;
}
```

`--font-display` / `--font-mono` are the one **addition** to the block; today
fonts are hardcoded at `activity.css:5` and `34`. The theme is served *after*
`activity.css`; `core`'s theme is the existing values verbatim, so a run with no
flavor looks identical to today.

## Ships

`ships.json` carries hulls, art and the default map in one file. The shapes
deliberately match the existing `_HULL_STATS` / `bridge_hulls.json` /
`bridge_ship_art.json` structures so the sensor physics and `shipyard.py`
hardpoint fitting work unmodified.

```json
{
  "hulls": {
    "stk.miranda": {
      "name": "Miranda-class cruiser", "role": "Light cruiser",
      "contactType": "capship", "massKt": 690, "crew": 150,
      "profile": 0.7, "stealth": 0.25, "emission": 0.5, "sensorQuality": 0.85,
      "blurb": "General-purpose workhorse, refit a dozen different ways.",
      "art": { "action": "miranda.png", "vdu": "miranda-vdu.gif" },
      "stats": { "shieldFore": 300, "shieldAft": 280, "armorFore": 20,
                 "armorAft": 18, "armorPort": 5, "armorStarboard": 5,
                 "body": 260, "fuelCapacity": 5 },
      "hardpoints": [
        { "id": "phaser-fore", "arc": "fore", "kind": "gun" },
        { "id": "phaser-port", "arc": "port", "kind": "gun" }
      ],
      "names": ["USS Cerritos", "USS Resolute", "USS Alacrity"]
    }
  },
  "defaults": {
    "unknown": "stk.miranda", "escort": "stk.ariel",
    "capship": "stk.miranda", "fighter": "stk.flynn",
    "carrier": "stk.enterprise", "freighter": "stk.cargo"
  }
}
```

`defaults` replaces the hardcoded `DEFAULT_BY_TYPE` (`ships.py:452-466`). A
flavor that renames the catalog **must** supply it, or a GM template that names
no hull silently flies the wrong ship. Every id in `defaults` is validated
against the merged hull list at load — invariant 12.

The dynamic `SHIP_CLASSES` population loop (`ships.py:391-411`) already handles
hulls it has never seen: it takes the id and derives a name from
`name or _hull_id.replace("-", " ").title()`. A flavor's hulls flow through it
unchanged. Namespaced ids make that fallback read `Stk.Miranda`, so `name` is
effectively required in practice — validation should say so rather than
discovering it at runtime.

## Missions and callsigns

`CampaignSeed` (`types.py:882-911`) is already pure data; only its *source* is
Python. Flavor missions are JSON expanded by one generic loader, so no flavor
ships code:

```json
{
  "id": "stk.babel",
  "theater": "Babel Sector",
  "brief": "Six civilian ships have gone dark inside the corridor.",
  "target": "Trace the relay source and recover the manifest.",
  "startHour": 0, "clutter": 0.4, "escalation": 0.15,
  "patrol": { "center": { "x": 0, "y": 0, "z": 0 }, "radiusKlik": 60 },
  "environment": "ion-storm",
  "shipClass": "stk.enterprise",
  "zBand": { "min": 3, "max": 12 },
  "contacts": [
    { "name": "Klingon Bird-of-Prey", "type": "fighter", "hostile": true,
      "emitting": true, "kps": 40, "shipClass": "stk.birdofprey", "s": 4, "idx": 2 }
  ],
  "navPoints": [
    { "id": "stk.babel.wp1", "name": "Babel Relay", "kind": "nav",
      "pos": { "x": 40, "y": 12, "z": 0 }, "radiusKlik": 8, "chartAgeHours": 96 }
  ],
  "hazards": [
    { "id": "stk.babel.ion", "type": "ion-storm", "title": "Ion Storm",
      "startMinute": 0, "endMinute": 240, "intensity": 1.4,
      "noise": 1.2, "concealment": 0.4 }
  ],
  "events": [ { "atMinute": 45, "template": "stk.comm.scoop" } ]
}
```

All distances stay canonical `*Klik` on the wire — invariant 10. The JSON
mirrors `CampaignSeed` field-for-field, so the loader is
`CampaignSeed.model_validate(merged_json)` plus deterministic contact placement
from the existing `_circ` / `hash_random` helpers, which is what invariant 1
requires. No flavor may introduce its own randomness.

`callsigns.json` replaces the pools at `campaigns.py:28-34`:

```json
{
  "adjectives": ["USS", "CV", "RCS", "CSV", "Klingon"],
  "nouns": ["CERBERUS", "GRIFFIN", "VALKYRIE", "ORION", "PHOENIX"],
  "vesselName": "corporate"
}
```

`vesselName` selects the generator: `corporate` gives `USS Cerritos` (Trek),
`surname` gives `Grey Falcon`-style merchant names, `callsign` gives
`Vanguard 612`-style designations. The pools are the per-flavor replacement for
`NEUTRAL_FLEET_RENAMING_PLAN.md`'s numbered variants, which is a deliberate
sequence: generic first, then flavorful through the mechanism.

## Selection and loader

**One mod at a time, per server.** A room records its `flavorId` in
`GameState`, but that id is always the single mod the operator has loaded, and
loading a mod rebuilds every live room onto it. Mods are alternative universes,
not per-table skins, so a room is never left playing a setting that has been
unloaded — `core` included.

*Amended after the first pass:* this started as a per-room selection with a boot
default. The per-flavor isolation it bought is still exactly what makes the
one-at-a-time model work (`asset_root(flavor_id)`, per-flavor hull/art caches,
a flavor id on the state blob, per-flavor themes served at
`/flavor/<id>/theme.css`), and rebuilding a room onto the loaded mod reuses the
same path as a restart.

The cost is that `ASSET_DIR` and the unit formatter stop being process-global.
`asset_root()` becomes `asset_root(flavor_id)`, threaded through the art
resolver, and the module-level caches at `ships.py:417` (`SHIP_ART`) and
`ships.py:424` (`HULL_STATS`) become a per-flavor cache keyed by flavor id —
built once on first use, not per call. `resource_path()` in `paths.py:13` needs
a parallel flavor lookup.

Flavor id and the resolved unit formatter go on the state blob so a reconnecting
client renders the same units as everyone else, and so the handoff pack names
the setting the tabletop is playing.

### Seam changes

| Area | Today | Change |
|---|---|---|
| `paths.py:13,17-23` | `resource_path`, global `ASSET_DIR` | `resource_path(name, flavor)`, `asset_root(flavor)` — flavor `assets/` first, core second |
| `ships.py:64-80` | `_FALLBACK_ACTION` | per-flavor, merged over core |
| `ships.py:136-157` | one art map | per-flavor art map takes precedence; ext-swap fallback retained |
| `ships.py:391-411` | reads global `HULLS` | merged namespaced `HULLS` |
| `ships.py:417,424` | module-level caches | per-flavor cache keyed by id |
| `ships.py:452-466` | hardcoded `DEFAULT_BY_TYPE` | flavor `defaults`, validated |
| `campaigns.py:494` | Python factories | generic JSON → `CampaignSeed` loader |
| `campaigns.py:28-34` | hardcoded pools | `callsigns.json` |
| `types.py:582` | free-form `shipClass` str | default validated against merged hull list |
| `types.py:223-262` `ShipClass` | — | no change; flavor fields fit the existing model |
| ~40 display sites | `"klik"` literals | `format_distance()`; identifiers untouched |
| `activity.css:5,9-27,34` | hardwired fonts, `:root` | `--font-display` / `--font-mono`; theme served after |
| `GameState` | — | `flavorId` field |

`ShipClass` and `CampaignSeed` need no new fields. The flavor's per-hull
`stats` merge into the existing `HULL_STATS` shape and the per-arc shield
setattr loop at `ships.py:425-427` already applies them.

## Validation

One validator run at load, per flavor, over the *merged* result:

- Manifest parses; `extends` chain resolves; no cycle.
- Every `defaults` value is a hull id in the merged list.
- Every mission `shipClass` / contact `shipClass` is a hull id in the merged list.
- Every hull has `name`, `role`, `contactType`, `stats`, `hardpoints`, `art`.
- Every art target exists on disk, in the flavor's tree or core's.
- Every `ContactType` and `NavKind` value is in the `types.py` literal set.
- Unit ladders are ordered by descending `min`, factors are positive and finite,
  and the last rung's `min` is 0.
- `speed.dial` keys are numbers reachable by the 0-100 dial.

Failure logs the flavor id and reason and falls back to `core` (invariant 11). A
`--flavor` CLI flag and a startup summary listing loaded flavors and mission
counts make the whole thing inspectable in one command. Ship a JSON Schema for
the manifest, `units`, `ships` and mission shapes so flavor authors get editor
completion and CI can check a pull request that adds one.

## Tests

- Validator rejects: a dangling `defaults` id, a mission naming a missing hull,
  a missing art file, an unsorted unit ladder, a cycle in `extends`, a
  non-positive factor.
- **Regression guard for invariant 12:** a flavor that removes a hull named in
  core `defaults` fails to load — the `lance-corvette` case.
- Units: a `stk` scenario at 40 AU renders `26.8 AU`, not `6.0e9 klik`; a `core`
  scenario at 40 km still renders `40.0 klik`. Both directions.
- Identical simulated time under `stk` produces byte-identical state to `core`
  (invariant 1) — flavor must not enter the sim.
- A flavor theme applies, `core` theme is unchanged, and a missing theme file
  falls back without breaking layout.
- A flavor hull with art resolves to the flavor image; a flavor hull **without**
  art falls back to core, not to a blank.
- Per-flavor cache: two rooms on different flavors in one process each resolve
  their own art, units and defaults, concurrently.
- Room reload after a flavor is removed from disk falls back to `core` with the
  room still playable.
- Every `contacts[].name` in a flavor mission is unique within the scenario.

## Implementation order

1. Add `units.json` to `core`, written in the current units, so formatting is a
   no-op before anything else moves. Route the display sites through it.
2. Thread `asset_root(flavor)` and `resource_path(name, flavor)` through
   `paths.py`; convert the two `ships.py` caches to per-flavor.
3. Split `DEFAULT_BY_TYPE` out of `ships.py` into `core`'s `ships.json`, and add
   the `defaults` validation. This is the invariant 12 fix and the smallest
   change that proves the merge layer.
4. `theme.css` for `core` with the current values; add the two font vars; serve
   the theme after `activity.css`.
5. JSON → `CampaignSeed` loader; move the existing factories to `core/missions/`.
6. `callsigns.json`; move the pools out of `campaigns.py`.
7. `flavorId` on `GameState`; `DEFAULT_FLAVOR`; per-room selection.
8. JSON Schema, validator CLI, startup summary.
9. Ship `wc` as the first real flavor. It is the acceptance test: if the WC
   content loads as a flavor against a WC-free `core`, the seam is proven.
   Reuse the names `NEUTRAL_FLEET_RENAMING_PLAN.md` retired.
10. Then `stk`, `sw`, `bsg`, `farscape` as reference flavors, ideally community
    contributions.

Steps 1-3 are independently shippable and improve the current build. Step 9 is
where the plan either works or does not.

## Open questions

1. **Per-room or per-server flavors?** *Resolved: per-server, one mod at a
   time.* Per-room was the recommendation here, but mods turned out to be whole
   universes rather than per-table skins, so the operator loads one and every
   room plays it. The per-flavor cache and the flavor id on the state blob were
   kept anyway — they are what let a room be rebuilt onto a different setting.
2. **Do flavor units change the numbers, or only the labels?** Recommend labels
   only (invariant 10). Letting a flavor rescale the 42-klik passive range is
   tempting for AU-scale play, but it breaks determinism comparisons across
   rooms and puts flavor data on the physics path. A separate
   `ranges: { passive: 0.02 }` multiplier, if ever wanted, should be an explicit
   opt-in that the engine records in the state blob.
3. **Do flavors ship previews to the GM console?** The admin console
   (`server/admin.py`) would be the natural place to pick a flavor per room. Nice
   to have; not in this plan's scope.
4. **Who owns flavor licensing?** A flavor naming a third-party universe has the
   same exposure `NEUTRAL_FLEET_RENAMING_PLAN.md` is about. Worth a
   `mods/README.md` stating that a contributed flavor is the contributor's
   responsibility, with `wc` shipped as a local-only example not published with
   the app.

## Implementation notes

Landed with these decisions, which supersede the text above where they differ.

- **Core is fully data.** `mods/core/` carries `flavor.json`,
  `units.json`, `theme.css`, `ships.json` (all 15 hulls with stats, hardpoints,
  art and registry names), `callsigns.json` and `missions/*.json` (all 9
  campaigns, each with its hazards, nav points, layers, barriers and events).
  The in-code `_HULL_STATS`, `_FALLBACK_ACTION`, `DEFAULT_BY_TYPE`, `SHIP_NAMES`
  and the campaign factories are gone; `shared/ships.py` and
  `shared/campaigns.py` are compatibility/behavior layers over the loader.
  `tools/export_core_flavor.py` records how the data was migrated.
- **`min` is in canonical klik.** The plan's sample ladder gives the Mm rung
  `"min": 1.0`; that would render a 40-klik knife fight as `0.0 Mm`. It is a
  typo for `1.0e3` (1 Mm). The schema and `mods/README.md` state the
  canonical-units rule, and the validator only enforces ordering, positivity and
  a zero last rung.
- **The legacy fallback maps are obsolete.** `art` is explicit per hull in
  `ships.json`, so `_FALLBACK_ACTION` is not re-created; the per-flavor art
  resolver keeps the extension-swap behavior and searches the flavor chain, so a
  hull that overrides a core hull without art inherits the core art.
- **Server-side display strings route through `Units`; the bundled client does
  not.** `engine.py` and `events.py` format every human-readable distance and
  speed through the room's flavor, but the prebuilt `activity/dist` bundle still
  carries a handful of hardcoded `KLIK` labels. Those are a UI follow-up, not a
  simulation concern; the canonical wire values are unchanged.
- **`flavorId` has a default**, so older saved rooms stay valid and
  `STATE_SCHEMA_VERSION` did not need a bump. A room whose flavor is no longer
  installed falls back to `core` on load with a logged reason.
- **Selection surfaces:** `DEFAULT_FLAVOR` / `--flavor`, `MsgStart.flavorId`,
  and the GM console's *Mods / settings* panel (load/unload). There is no
  per-room picker: the loaded mod is the setting, and loading one rebuilds the
  rooms onto it. Open question 3's previews remain out of scope.
- **A mod manager gates what rooms play.** Landed after the first pass:
  installed flavors are *inert* until loaded (`bridge/server/mods.py`; the loaded
  mod persists in the rooms DB). The GM console's *Mods / settings* panel loads
  one mod and shows what is loaded; because mods are exclusive, loading one
  unloads every other — `core` is an ordinary mod and can be unloaded like any
  other. Loading a mod rebuilds every live room onto it, keeping claimed seats,
  so nothing is left playing an unloaded universe. A flavor that fails
  validation cannot be loaded, unloaded mods are guarded at room load, and
  `DEFAULT_FLAVOR`/`--flavor` loads a setting at boot (`--flavor` persists it).
- **Inheritance is opt-in.** A manifest that omits `extends` is standalone;
  naming a parent is what pulls in another setting's hulls, missions, units and
  callsigns. This is what keeps a mod's catalog to its own universe — the
  shipped `wc`/`stk`/`sw` examples are standalone and share no hull ids with
  `core`.
- **Validator hardened after audit.** The loader now type-checks numeric hull
  fields, stats, hardpoint shape/arc/kind and terrain overrides; requires a
  non-empty hull catalog and at least one mission; and wraps validate+compile so
  no `ValueError`/`TypeError` can escape `get()`/`summaries()`/`--check-flavor`
  (one malformed flavor can no longer block startup). `defaults` keys are
  checked against `ContactType`, and `terrain` filenames resolve through the
  flavor art chain instead of being passed through raw.
- **Step 9 shipped as `wc/`**, the acceptance test: it loads against a WC-free
  core, namespaces its hulls (`wc.*`), supplies its own `defaults`, and
  demonstrates every seam (units, theme, ships, art fallback, callsigns,
  missions). It is allowlisted in `tests/test_no_wing_commander_names.py` and
  excluded from the built package (see `mods/README.md`).
- **Step 10 partly shipped as examples.** `stk/` (Star Trek) and `sw/` (Star
  Wars) are full reference flavors alongside `wc/`: each re-skins all 15 core
  roles with namespaced hulls and its own `defaults`, theme, units and two
  missions. `stk` exercises the AU/Mm auto-scaling ladder and `sw` a km/Mm
  ladder with `MGLT`; both use the `registry` callsign style (`USS Enterprise`,
  `ISD Devastator`). Like `wc` they are local examples, excluded from the built
  package. `bsg`/`farscape` are left to contributors.
- **Callsign styles are now four**: `corporate`, `surname`, `callsign` and
  `registry` (prefix + proper name), so a setting with a registry convention
  does not need to fake it with the merchant generators.
- **The folder is the id.** Landing the authoring ergonomics: `flavor.json` is
  optional and `id` is gone from every shipped manifest; the loader derives the
  id from the directory name. The conventional files (`units.json`, `theme.css`,
  `ships.json`, `callsigns.json`, `missions/`) are auto-discovered, so a manifest
  only carries `title`/`extends`/`defaultMission` or a non-standard path, and an
  explicit `null` disables a conventional file. Discovery treats a directory as a
  flavor when it has a manifest or any conventional file, which keeps the shipped
  `schema/` tree out of `available()`. Copying a folder with `cp -r` is now the
  whole "new flavor" workflow; a stale explicit `id` is a load error rather than
  a silent mismatch, and `id` absent is the normal case.
- **Mods moved to the project root.** The flavor tree now lives in `mods/` at
  the project root, not inside the package, so a player can find and copy it.
  `bridge/paths.flavor_roots()` discovers the project-root `mods/` first, then
  falls back to the packaged `bridge/flavors/` tree — an installed wheel has no
  project root, so `setup.py`'s `build_py` hook copies the shipped `core` and the
  authoring schemas into `bridge/flavors/` in the wheel (the example settings are
  pruned from the sdist and never published). `FLAVORS_DIR` still replaces
  discovery wholesale, and `flavor_dir(id)` searches every root so an id resolves
  wherever it is installed.

