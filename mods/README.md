# Flavors — adding a setting (a mod)

A **flavor** is a setting: a folder of data that re-skins, re-scales and
re-narrates the bridge without shipping a line of Python. Player mods live in
this `mods/` folder at the project root; the shipped default is `core/`.

## Shipped examples

Three worked examples live in this tree. They are demonstration re-skins, not
published content (the wheel ships only `core/`, copied out of this folder by
`setup.py`):

| Flavor | Setting | Shows off |
|---|---|---|
| `wc/` | space combat (the acceptance test) | namespaced hulls, its own `defaults`, surname callsigns, an Mm distance ladder |
| `stk/` | Star Trek | an AU/Mm auto-scaling ladder, a standalone LCARS theme, registry callsigns (`USS Enterprise`) |
| `sw/` | Star Wars | a km/Mm ladder with `MGLT` speed, a crawl-yellow theme, registry callsigns (`ISD Devastator`) |

Copy whichever is closest to what you want and edit it.

## Let an agent interview you

The `bridge-commander-mods` skill (`.agents/skills/bridge-commander-mods/`)
turns a setting idea into a validated mod by asking the right questions first:
what the universe is, how ranges and speeds should read, what each ship is
called and who flies it, where the images come from, the colour theme, callsigns
and missions. It then generates, validates and activates the package. Deep
details live in its `references/` (`flavor-format.md`, `art.md`). Ask an agent
to "create a mod" or "make a new setting", or invoke the skill by name.

## The 30-second version

```sh
cp -r mods/core mods/mine
python -m bridge --list-flavors             # loads and validates every flavor
```

That is a working flavor: **the folder name is the id**, so there is no id to
rename and nothing else to edit first. It is a private copy of the shipped
setting's hulls, missions and theme; change only what your setting needs.

`flavor.json` is optional. A folder with a manifest, or any of the conventional
files (`units.json`, `theme.css`, `ships.json`, `callsigns.json`, `missions/`),
is discovered as a flavor. The manifest only carries what you want to say:

```json
{ "title": "My Setting", "extends": null, "defaultMission": "mine.first" }
```

The conventional filenames are found automatically, so no path needs listing;
give a key an explicit path for a file in a non-standard place, or `null` to
stop a copied file from overriding the parent. If you do write an `"id"`, it is
an assertion that must match the folder, which catches a stale id left on a copy.

## Layout

```
mods/<id>/
  flavor.json      # optional manifest: title, extends, defaultMission, custom paths
  units.json       # optional: distance ladder + speed dial labels
  theme.css        # optional: a :root override, served after activity.css
  ships.json       # optional: hulls, art and the contact-type defaults
  callsigns.json   # optional: generated-name pools
  missions/*.json  # optional: CampaignSeed-shaped scenarios
  assets/          # optional: action/ and vdu/ images
    action/*.png
    vdu/*.gif
```

Inheritance is **opt-in**. A manifest with no `extends` is standalone and must
carry its own hulls and missions; name a parent (`"extends": "core"`) to build on
one instead. `"extends": null` states the standalone choice explicitly. Chains
are walked until `core`, and a cycle is a load error.

Standalone is the default because mods are alternative universes played one at a
time: a mod that silently inherited `core` would mix another setting's hulls,
missions and scenarios into its own.

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
| `theme.css` | the `:root` custom properties | Served after `activity.css`, so all existing markup resolves. Set `--font-display` and `--font-mono` for type, the palette (`--bg`, `--accent`, …) for colour, and the surface tokens (`--tint-rgb`, `--panel-bg`, `--wash`) for panel borders, glows and the background wash. `core/theme.css` lists the full set. |
| `ships.json` | hulls, art, `defaults`, terrain images | Merge is per hull id and per field: an override may change just a name, a stat or an art file. Art resolves through the flavor chain, so a hull with no `assets/` falls back to core art. Add a `defaults` entry for every contact type you rename the catalog for. |
| `callsigns.json` | name adjectives, nouns, naming style, hostile pools | Lists replace; hostile pools merge per role. `vesselName` is one of `corporate` (`MV GREY FALCON`), `surname` (`Grey Falcon`), `callsign` (`Vanguard 612`) or `registry` (`USS Enterprise`). |
| `missions/*.json` | scenarios | Mirrors `CampaignSeed` field-for-field. Explicit positions keep placement deterministic. |

JSON Schemas for every file live in [`schema/`](schema/) for editor completion
and CI. Point your editor at the schema with a `$schema` key:

```json
{ "$schema": "../schema/ships.schema.json", "hulls": {} }
```

## Selecting a flavor

* **Exactly one mod is loaded at a time.** Activating a mod unloads every other
  one, `core` included, and every live room is rebuilt onto it.
* The loaded mod is what new rooms start on, so there is no separate "default".
* `DEFAULT_FLAVOR=wc` (or `python -m bridge --flavor wc`) loads that setting at
  boot. `--flavor` also persists the choice, so it beats whatever the console
  last loaded.
* A room records its `flavorId` in game state, so reconnecting clients render
  the same units and art, the page theme follows the setting, and the handoff
  names it.

If a room's flavor disappears from disk, the room stays playable on the loaded
setting and the server logs the fallback.

## Loading a mod

Installing a flavor on disk makes it a **candidate**, not a loaded setting. It
does nothing until an operator loads it in the GM console's **Mods / settings**
panel:

| Action | Effect |
|---|---|
| **ACTIVATE** | Loads this setting and unloads every other mod, `core` included. Live rooms are rebuilt onto it, keeping their claimed seats. A package that fails validation cannot be activated. |
| **UNLOAD** | Unloads the loaded mod and falls back to `core`. `core` is never unloaded directly — load another mod instead. |
| **DEFAULT_FLAVOR / `--flavor`** | Loads that setting at boot; `--flavor` persists it. |

The loaded mod persists in the rooms database, so it survives a restart. A room
whose mod was unloaded, or whose package was removed from disk, is rebuilt onto
the loaded setting on load and stays playable; the server logs the reason.
`python -m bridge --list-flavors` shows what is installed; `--check-flavor <id>`
validates one package.

## Licensing

A flavor that names a third-party universe carries the same exposure as any
other fan work. **A contributed flavor is the contributor's responsibility.**
Do not add a third-party setting to this repository unless you are comfortable
with that; `wc/`, `stk/` and `sw/` are included as local examples of the
mechanism and are deliberately not shipped in the built package (see
`pyproject.toml` `package-data`).
