---
name: bridge-commander-mods
description: "A guided, interview-driven workflow for creating a new bridge-commander mod (flavor) from scratch. Asks the author what universe/setting it is, how distances and speeds read, what each ship is called and who flies it, where the images come from, the colour theme, callsigns and missions, then generates, validates and activates the data package. Triggers on: create a mod, make a mod, new mod, add a mod, create a flavor, new setting, new universe, reskin, ship roster, what ships, ship art, where do I get images, design a campaign setting."
whenToUse: "Use when the user wants to invent or scaffold a new setting/mod for bridge-commander and needs to be walked through the decisions. For editing an existing flavor, the format reference still applies but the interview can be skipped."
---

# Creating a new mod for bridge-commander

You are the author's collaborator. Turn a setting idea into a validated, playable
flavor by **interviewing first, generating second**. Never dump a wall of
questions and never write files before you understand the setting.

A flavor is a folder of data (`bridge/flavors/<id>/`) that re-skins ships,
units, theme, callsigns and missions. It ships no code. The loader is
`bridge/shared/flavors.py`; `bridge/flavors/README.md` is the human guide.

## How to run this skill

- **Ask in batches.** Two to four related questions at a time, not fifteen.
- **Use the question tool for choices** (universe type, inheritance, units, art
  source, theme, roster shape). Use plain chat for free text — names, blurbs,
  lore. If no question tool is available, ask in chat.
- **Always offer a default** and accept "you decide" / "surprise me" / "same as
  core". A stalled interview is worse than a sensible guess.
- **Keep a design sheet.** After each phase, append answers to a short markdown
  summary and read it back before generating. The sheet is the source of truth
  for Phase 7.
- **Reuse mechanics, invent flavour.** Copy core hull stats and hardpoints by
  role; change names, blurbs, art, units, colours and scenarios. A mod never
  changes simulation rules.
- **Validate cheaply as you go** (`--check-flavor`) rather than only at the end.

Phases: **0** ground it → **1** units → **2** theme → **3** ship roster →
**4** art → **5** callsigns → **6** missions → **7** build → **8** validate,
activate, document.

---

## Phase 0 — Ground the idea

Ask:

1. *"What's the setting called, and what's the one-line hook?"*
2. *"Is this your own universe, or a third party's (a film/show/game/book)?"*
   This decides packaging and licensing (Phase 8): own universes can ship;
   third-party settings stay local examples.
3. *"How big is this first pass — a full re-skin of the 15 core hulls, a light
   reskin of a few, or a standalone setting that replaces core entirely?"*

Derive the **flavor id**: lowercase, kebab-case, from the title (`"Star Trek"`
→ `stk`; `"Dune"` → `dune`). It must match the directory name.

Restate back: *"So: a `<scope>` setting called `<title>`, `<original /
third-party>`, id `<id>`. Right?"* Then continue.

## Phase 1 — Units (how numbers read)

Ask:

- *"How should distances read on the plot — stay in klik, or scale to something
  bigger? e.g. AU and Mm for a Trek feel, km and Mm for a Wars feel."*
- *"How should speed read? Keep kps, or a named unit like MGLT / impulse?"*
- *"What should the speed settings be called?"* (core: Silent Running / Cruise /
  Flank).

Rules to state while asking: the simulation and the wire stay in **klik** and
**kps**; this file only changes display. `min` is a threshold in **canonical
klik** (1 Mm = 1000 klik, so an Mm rung's `min` is `1000`, not `1`). The last
rung must be `min: 0`.

Default if unsure: keep core's klik ladder and just rename the dial.

## Phase 2 — Theme (how it looks)

Ask:

- *"Describe the look — three or four colours, or 'match <reference>'."* Capture
  background, panel, accent, text, and a danger/good pair.
- *"Fonts? Display face and readout face. Default is Zen Dots over Share Tech
  Mono."*

If the author has no preference, propose a palette derived from the setting's
description and say why. `theme.css` is written in Phase 7 from these answers.

## Phase 3 — The ship roster (the heart of the mod)

This is ship-by-ship. First ask the shape, then walk the roles.

**Ask:** *"Who's in this setting — a friendly navy, a hostile one, civilians?
Tell me the ships you already know and I'll map them onto the roles the game
needs."*

Then explain the roles and fill the gaps together. The core catalog is a
ready-made checklist; a full re-skin answers all fifteen, a light reskin answers
only the ones it uses:

| Core slot | What it serves | Typical example |
|---|---|---|
| `home` | **the ship the players fly** (crew hull) | the hero cruiser |
| `friendly-corvette` | friendly escort | a patrol corvette |
| `friendly-transport` | neutral/civilian freighter (`freighter`, `liner`) | a cargo hauler |
| `friendly-prospector` | `prospector` | a survey/mining hull |
| `friendly-freighter` | `freighter` | an independent trader |
| `friendly-carrier` | friendly carrier | a fleet carrier |
| `friendly-light-cruiser` | friendly light cruiser | a frigate |
| `enemy-escort` | hostile `escort` | a raider |
| `enemy-fighter` | hostile `fighter` | a light fighter |
| `enemy-medium-fighter` | hostile `fighter` | a line fighter |
| `enemy-heavy-fighter` | hostile `fighter` | a heavy fighter |
| `enemy-bomber` | hostile `fighter` | a strike bomber |
| `enemy-destroyer` | hostile `capship` | a destroyer |
| `enemy-cruiser` | hostile `carrier` | an enemy carrier |
| `enemy-heavy-transport` | hostile `freighter` | a resupply hull |

For **each** ship the author names, capture:

1. **Class name** — what it is (`Miranda-class cruiser`).
2. **Role** — a short human label (`Light cruiser`).
3. **Who flies it** — friendly / neutral / hostile, which sets `contactType`
   (`escort`, `fighter`, `capship`, `carrier`, `freighter`, `prospector`).
4. **One-line blurb** — the sensor-catalogue flavour text. Offer to write it if
   the author is tired of typing.
5. **Registry name(s)** — the proper name when the crew flies it (`CS Audacity`,
   `USS Enterprise`). One is enough; a list gives variety.
6. **Stats** — *"reuse the core stats for that role, or tweak?"* Default: reuse.
7. **Art** — deferred to Phase 4.

Ask the "who flies what" question explicitly: *"Which of these does the crew
fly, which are hostile, and which are civilian traffic?"* The answers drive
`defaults` (Phase 7): `unknown` must point at the crew hull, and every contact
type you use must point at a hull, or unnamed contacts fly the wrong ship.

Tips: if the author gives a flat list of names, propose the role mapping
yourself and ask them to correct it. If they only have three ships, build a
three-hull catalog and point several `defaults` entries at the same hull — that
is valid.

## Phase 4 — Art (the "where do the images come from?" question)

Ask directly: *"Do you have ship art, or should we reuse the core placeholder
images for now?"* Then lay out the three options:

1. **Reuse core art** (default, zero work). In `ships.json`, name an existing
   core file: `"art": {"action": "friendly-cruiser.png", "vdu":
   "friendly-cruiser-vdu.gif"}`. Art resolves flavour-first, then down the
   `extends` chain, then the core `img/` tree, so no `assets/` directory is
   needed at all.
2. **Supply your own.** Drop files in
   `bridge/flavors/<id>/assets/action/<stem>.png` and
   `bridge/flavors/<id>/assets/vdu/<stem>-vdu.gif`, then name `<stem>.png` in
   the hull's `art`. The resolver also accepts `.gif/.jpg/.jpeg/.webp` and tries
   a same-basename extension swap, so a `.png` action with a `.gif` VDU works.
3. **Generate placeholders.** `tools/generate_placeholder_art.py` paints 128×128
   labelled placeholders (needs `pip install pillow`; currently paints the core
   catalog, so copy or adapt it for a new setting). Any external art tool is
   fine too.

Specs: **128×128**, transparent or dark background reads best; action art is the
ship portrait, VDU art is the scan/oscilloscope look. A flavor's own art is
served at `/img/f/<id>/action/<file>`; core art keeps `/img/...`.

Licensing: use your own, public-domain/CC0, or commissioned art. Third-party art
carries the same exposure as a third-party setting — the contributor's
responsibility (Phase 8).

See `references/art.md` for naming details and a per-hull checklist.

## Phase 5 — Callsigns (what contacts are called)

Ask:

- *"What naming convention do contacts use?"* Offer the four styles:
  `corporate` (`MV GREY FALCON`), `surname` (`Grey Falcon`), `callsign`
  (`Vanguard 612`), `registry` (`USS Enterprise`).
- *"Give me a dozen name words for civilian traffic"* (adjectives + nouns).
- *"What are the hostile ships called?"* — pools for `escort`, `capship` and
  `fighter` roles, so two hostiles never read alike.

Default if unsure: the setting's registry prefixes plus a list of evocative
nouns. Pool entries carry their own capitalisation.

## Phase 6 — Missions (what the table actually plays)

Ask per mission (start with one; offer two):

- *"Name and location?"* (title + theater)
- *"What's the situation, and what does winning look like?"* (brief + target)
- *"Who's out there?"* — the contact mix: types, hulls, hostile/neutral, whether
  they are emitting, and roughly where.
- *"Any terrain or weather?"* — asteroid field, dust, ice, ion storm, radiation,
  debris; these become `hazards`, which also drive the environment.
- *"Any places to plot to?"* — nav points and jump points.
- *"Any scripted beats?"* — decision events, from the fixed core template list.

Constraints to state: positions are explicit numbers (no randomness in a
flavor); every `shipClass` must be a hull in the catalog; explicit contact names
must be unique; events may only use core templates: `fleetnet` (`sosus` alias),
`unmarked`, `distress`, `orders`, `probe`, `weapons-warning`, `relay`,
`challenge`, `civilian`, `false-surrender`, `contactclose`.

## Phase 7 — Build it

Now write files from the design sheet. Exact shapes and field lists are in
`references/flavor-format.md`; do not guess.

```sh
# Extending core (normal case): copy the closest example.
cp -r bridge/flavors/core bridge/flavors/<id>
# Standalone (replaces core): start minimal instead and set "extends": null.
mkdir -p bridge/flavors/<id>/missions
```

Then:

1. **`flavor.json`** — `id` matching the directory, `title`, `extends` (`core`,
   another id, or `null`), file references, `defaultMission`.
2. **`ships.json`** — one entry per hull, ids namespaced `<id>.<name>`, required
   fields filled, stats/hardpoints copied from the matching core role,
   `defaults` covering every contact type you use.
3. **`units.json`** — the ladder and dial from Phase 1.
4. **`theme.css`** — the palette from Phase 2 (copy `core/theme.css` and change
   the `:root` values).
5. **`callsigns.json`** — from Phase 5.
6. **`missions/*.json`** — one file per mission, named `<id>.<mission>.json`.

Delete any copied file you are not overriding. Keep a `defaults` entry for every
contact type the missions use.

## Phase 8 — Validate, activate, test, document

```sh
.venv/bin/python -m bridge --check-flavor <id>   # exits 1 on any error
.venv/bin/python -m bridge --list-flavors        # all flavors + hull/mission counts
```

Read the validator's reason and fix the data; never patch code to accept a
broken flavor. Then:

- **Activate it.** Installed is not active. In the GM console's **Mods /
  settings**: ACTIVATE, then USE IN ROOM or SET DEFAULT. Or boot with
  `DEFAULT_FLAVOR=<id>` / `python -m bridge --flavor <id>`. In tests:
  `from bridge.server import mods; mods.activate("<id>")`.
- **Play a room on it** and confirm units, theme, ship name and contact names
  read correctly.
- **Add tests** for a shipped example (`tests/test_flavors.py`) and run the
  gates: `.venv/bin/python -m pytest -q`, `.venv/bin/ruff check bridge tests`,
  `.venv/bin/mypy bridge`.
- **Document licensing.** If it names a third party's universe, keep it a local
  example: do **not** add it to `pyproject.toml` package-data, and note the
  contributor owns the exposure. If it uses vocabulary that the retired-names
  gate bans (see `tests/test_no_wing_commander_names.py`), add the flavor to
  that test's allowlist or the build gate fails.

## Interview cheat sheet

Longer prompts you can lift verbatim:

- *"Let's build a setting. Start me with the universe and the vibe in a
  sentence."*
- *"How do you want ranges and speeds to read on the plot?"*
- *"List the ships you already know about — I'll fit them to the roles the game
  needs and fill the gaps."*
- *"For each ship: what's it called, what does it do, and who flies it?"*
- *"Do you have art, or should I reuse the core placeholder images for now?"*
- *"What do contact callsigns look like in this universe?"*
- *"Design me one mission: name, place, who's out there, and what winning looks
  like."*

Handling common answers:

- **"I don't know."** → propose two concrete options, pick one, and say it is
  easy to change later.
- **"Just make it cool."** → choose a coherent palette, roster and one mission,
  generate it, then show the result and invite edits.
- **"Reuse everything."** → a minimal flavor is just `flavor.json` plus a theme
  or units override; that is a complete, valid mod.
- **A wall of lore.** → extract only what maps to fields (names, blurbs,
  factions, places) and summarise back.

## References

- `references/flavor-format.md` — every file's exact shape, enums, required
  fields and validator rules. Read before Phase 7.
- `references/art.md` — image options, specs, naming, resolution order and
  licensing. Read before Phase 4.
