# Flavor file formats

Exact shapes for everything under `bridge/flavors/<id>/`. JSON Schemas live in
`bridge/flavors/schema/` for editor completion. The loader is
`bridge/shared/flavors.py`; the human guide is `bridge/flavors/README.md`.

## flavor.json — the manifest

```json
{
  "id": "mine",
  "title": "My Setting",
  "units": "units.json",
  "theme": "theme.css",
  "ships": "ships.json",
  "callsigns": "callsigns.json",
  "missions": "missions/",
  "defaultMission": "mine.first"
}
```

- `id` is required and **must match the directory name**.
- `extends` is **opt-in**: omit it (or write `null`) and the mod is standalone,
  carrying its own complete hull catalog and at least one mission. Name a parent
  (`"extends": "core"`, or another flavor id) to chain onto it, in which case you
  may ship only the files you override — but the parent's other hulls and
  scenarios stay in play.
- A missing file reference is simply not overridden; a missing parent or a cycle
  is a load error.

## units.json — display only

The sim and the wire stay in canonical klik/kps. `min` is a threshold in
**canonical klik**; `factor` is canonical units per display unit (so the
formatter divides). Ladder must be ordered by descending `min` and end at
`min: 0`. `factor` must be positive and finite; `dial` keys must be in 0–100.

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
    "dial": { "0": "Station", "15": "Slow", "60": "Cruise", "100": "Attack speed" }
  }
}
```

## ships.json — hulls, art, defaults

Merge is per hull id **and per field**: an override may change just a name, a
stat or an art file. `hulls` is a map (preferred) or a list whose entries carry
`id`.

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

**Required per hull:** `name`, `role`, `contactType`, `stats`, `hardpoints`,
`art`.

**Optional per hull:** `massKt`, `profile`, `stealth`, `emission`,
`sensorQuality`, `crew`, `blurb`, `names` (list; the first is used), plus
`shipType`, `gunners`, `cargoHold` carried into the shipyard entry.

**Enums:**

- `contactType`: `unknown`, `prospector`, `freighter`, `liner`, `escort`,
  `capship`, `fighter`, `carrier`, `asteroid`, `nebula`, `debris`, `dust`,
  `ice`.
- hardpoint `arc`: `fore`, `aft`, `port`, `starboard`, `all`.
- hardpoint `kind`: `gun`, `missile`, `torpedo`.

**Numbers:** `massKt`, `profile`, `stealth`, `emission`, `sensorQuality`, `crew`
and every `stats` value must be numbers (not strings). Stats keys are the
`ShipClass` defence fields; an unknown key warns and is ignored.

**`defaults`** maps a contact type to a hull id. Every contact type a mission
uses should have an entry, or a hull-less contact flies the wrong ship. Terrain
types map to `""`. Unknown keys, and non-empty values that are not hull ids, are
load errors.

**`terrain`** overrides terrain contact images; values resolve through the same
art chain as hull art (see `art.md`).

Use `bridge/flavors/core/ships.json` as the authoritative source for stats and
hardpoints — copy a role's numbers rather than inventing them.

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

`vesselName` is one of `corporate` (`MV GREY FALCON`), `surname`
(`Grey Falcon`), `callsign` (`Vanguard 612`), `registry` (`USS Enterprise` —
pool entries carry their own capitalisation). Lists replace the inherited list;
`hostile` pools merge per role and are used for `escort`, `capship` and
`fighter` contacts, de-duplicated within a scenario.

## theme.css

A `:root` override, served after `activity.css`. Copy `core/theme.css` and change
the custom properties. The only required additions for a new look are
`--font-display` and `--font-mono`; `@import` a font at the top of the file if
you use a family the bundle does not load.

## missions/*.json — CampaignSeed

The loader is `CampaignSeed.model_validate(doc)`. Positions are explicit, so
placement is deterministic; a flavor must never introduce randomness.

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

- **Required:** `id`, `title`, `theater`, `brief`, `target`, `startHour`,
  `patrol` (`center`, `radiusKlik`), `clutter`, `escalation`.
- **Required per contact:** `x`, `y`, `heading`, `speed`, `type`, `faction`,
  `hostile`, `emitting`. Optional: `z`, `name`, `shipClass`, `radiusKlik`.
- `shipClass` (contact or mission) must be a hull id in the merged catalog.
- Explicit `contacts[].name` values must be unique within the mission.
- `events[].template` must be a core template: `fleetnet` (`sosus` alias),
  `unmarked`, `distress`, `orders`, `probe`, `weapons-warning`, `relay`,
  `challenge`, `civilian`, `false-surrender`, `contactclose`. Flavors cannot add
  templates.
- `navPoints[].kind` is one of `nav`, `jump`, `body`, `hazard`.
- Hazard `type` is matched by substring to an environment: asteroid, nebula,
  ice, dust, debris, radiation/solar, ion, gravity/well.

## What the validator rejects

A missing hull catalog or no missions; missing required hull fields;
non-numeric stats or hull fields; an unknown `contactType`, hardpoint
`arc`/`kind`; art that resolves nowhere; unknown `defaults` keys or dangling
hull ids; a mission that fails `CampaignSeed`; a mission `shipClass` not in the
catalog; duplicate contact names; an unsorted unit ladder; a non-positive
factor; a last rung whose `min` is not 0; a dial key outside 0–100; a
`defaultMission` that does not exist.

Failure is fail-closed: the flavor does not load, `get()` returns core with a
logged reason, and rooms fall back. `--list-flavors` marks it `INVALID` with the
reason.

## Lineage

- Loader: `bridge/shared/flavors.py`
- Compatibility views: `bridge/shared/ships.py`, `bridge/shared/campaigns.py`
- Activation: `bridge/server/mods.py` (mods table in `DATA_DIR/bridge.sqlite`)
- Schemas: `bridge/flavors/schema/*.json`
- Examples: `bridge/flavors/{core,wc,stk,sw}/`
