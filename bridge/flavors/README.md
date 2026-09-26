# Flavors — adding a setting (a mod)

A **flavor** is a setting: a folder of data that re-skins, re-scales and
re-narrates the bridge without shipping a line of Python. The shipped default is
`core/`.

## Shipped examples

Three worked examples live in this tree. They are demonstration re-skins, not
published content (`core/` is the only flavor bundled into the built package):

| Flavor | Setting | Shows off |
|---|---|---|
| `wc/` | space combat (the acceptance test) | namespaced hulls, overridden `defaults`, surname callsigns, an Mm distance ladder |
| `stk/` | Star Trek | an AU/Mm auto-scaling ladder, a standalone LCARS theme, registry callsigns (`USS Enterprise`) |
| `sw/` | Star Wars | a km/Mm ladder with `MGLT` speed, a crawl-yellow theme, registry callsigns (`ISD Devastator`) |

Copy whichever is closest to what you want and edit it.

## The 30-second version

```sh
cp -r bridge/flavors/core bridge/flavors/mine
$EDITOR bridge/flavors/mine/flavor.json     # { "id": "mine", "title": "My Setting" }
python -m bridge --list-flavors             # loads and validates every flavor
```

That is a working flavor: it inherits everything from `core` and overrides
nothing. Change only what your setting needs.

## Layout

```
bridge/flavors/<id>/
  flavor.json      # manifest: every field optional except "id"
  units.json       # optional: distance ladder + speed dial labels
  theme.css        # optional: a :root override, served after activity.css
  ships.json       # optional: hulls, art and the contact-type defaults
  callsigns.json   # optional: generated-name pools
  missions/*.json  # optional: CampaignSeed-shaped scenarios
  assets/          # optional: action/ and vdu/ images
    action/*.png
    vdu/*.gif
```

Inheritance is `core` unless the manifest says `"extends": null`, which makes the
flavor standalone. A manifest may also extend another flavor; chains are walked
until `core`, and a cycle is a load error.

## Rules a flavor must keep

1. **Data only.** JSON, CSS and images. No Python, no templates with code.
2. **Canonical units on the wire.** Distances stay `*Klik`, speeds stay `kps`.
   `units.json` converts for display only, so sensor physics, determinism and
   saved rooms never see flavor units.
3. **Fail closed.** A flavor that fails validation does not load; the server
   logs the reason and plays the room on `core`. It never half-loads.
4. **No implicit id inheritance.** Every hull id named in `defaults` or in a
   mission's `shipClass` must exist in the *merged* catalog. A dangling id is a
   validation error, not a silent substitution.

Run `python -m bridge --list-flavors` after every edit: invalid flavors are
listed with the reason, and valid ones report hull and mission counts.

## What each file can override

| File | Overrides | Notes |
|---|---|---|
| `units.json` | distance ladder, speed factor, dial labels | `factor` is canonical units per display unit, so the formatter divides. The ladder auto-scales: pick the largest rung whose `min` the value reaches. |
| `theme.css` | the `:root` custom properties | Served after `activity.css`, so all existing markup resolves. Set `--font-display` and `--font-mono` to change type. |
| `ships.json` | hulls, art, `defaults`, terrain images | Merge is per hull id and per field: an override may change just a name, a stat or an art file. Art resolves through the flavor chain, so a hull with no `assets/` falls back to core art. Add a `defaults` entry for every contact type you rename the catalog for. |
| `callsigns.json` | name adjectives, nouns, naming style, hostile pools | Lists replace; hostile pools merge per role. `vesselName` is one of `corporate` (`MV GREY FALCON`), `surname` (`Grey Falcon`), `callsign` (`Vanguard 612`) or `registry` (`USS Enterprise`). |
| `missions/*.json` | scenarios | Mirrors `CampaignSeed` field-for-field. Explicit positions keep placement deterministic. |

JSON Schemas for every file live in [`schema/`](schema/) for editor completion
and CI. Point your editor at the schema with a `$schema` key:

```json
{ "$schema": "../schema/ships.schema.json", "hulls": {} }
```

## Selecting a flavor

* `DEFAULT_FLAVOR=wc` (or `python -m bridge --flavor wc`) sets the setting new
  rooms start on.
* A room records its `flavorId` in game state, so reconnecting clients render
  the same units and art, and the handoff names the setting.
* The GM console can set a room's flavor when starting a new engagement, and a
  host may pass `flavorId` on `start`.

If a room's flavor disappears from disk, the room stays playable on `core` and
the server logs the fallback.

## Activating a mod

Installing a flavor on disk makes it a **candidate**, not an active setting. It
does nothing until an operator activates it in the GM console's **Mods /
settings** panel:

| Action | Effect |
|---|---|
| **ACTIVATE / DEACTIVATE** | Server-wide: whether any room may play this setting. `core` is always on and cannot be deactivated. |
| **USE IN ROOM** | Switches the selected room onto this setting (rebuilds it on that setting's default mission, keeping claimed seats). Only available for activated mods. |
| **SET DEFAULT** | New rooms start on this setting. Only available for activated mods; **CLEAR DEFAULT** returns to `core`. |
| **DEFAULT_FLAVOR / `--flavor`** | Counts as an explicit operator activation for that flavor at boot. Deactivating an env-selected mod is refused until the variable is unset. |

The enabled set and the default persist in the rooms database, so they survive a
restart. A room whose mod is deactivated or removed from disk falls back to the
default setting (normally `core`) on load and stays playable; the server logs
the reason. `python -m bridge --list-flavors` shows what is installed;
`--check-flavor <id>` validates one package.

## Licensing

A flavor that names a third-party universe carries the same exposure as any
other fan work. **A contributed flavor is the contributor's responsibility.**
Do not add a third-party setting to this repository unless you are comfortable
with that; `wc/`, `stk/` and `sw/` are included as local examples of the
mechanism and are deliberately not shipped in the built package (see
`pyproject.toml` `package-data`).
