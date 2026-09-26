# Neutral Fleet Renaming Plan

## Problem

Every ship class, faction callsign prefix, universe proper noun and art filename
in this repo is drawn from the *Wing Commander* series. The names live in the
curated hull catalog, the art tree, the campaign generator, the ship registry,
the credits and five phase plans.

ROADMAP invariant 8 says *"Port mechanics, re-author tables, credit WCRPG /
TEOC."* That covers **mechanics** and **attribution** — the d20 checks, EHD range
bands and per-arc shields come from WCRPG, which is licensed for exactly that use
and is credited in `CREDITS.md`. It does not cover the **setting vocabulary**:
`Fralthi`, `Ralatha`, `KIS`, `TCS`, `Wing Commander` in a README. That is the
remaining exposure, and it is the part a player actually sees.

This plan removes the setting vocabulary only. **No mechanic, balance value,
hardpoint arc, shield/armour number or sensor band changes.** The default
catalog is exactly as playable after this work as before.

## Goals

- No Wing Commander ship, faction, planet or universe name remains in code,
  data, assets, tests or docs.
- Hull ids become role-bearing and generic, so they can be re-flavored per
  `FLAVOR_PLUGIN_PLAN.md` without a second rename.
- Asset filenames match hull ids, so the art audit (`SHIP_ART_MAPPING_PLAN.md`)
  has one source of truth.
- WCRPG / TEOC attribution is preserved and made more precise, not deleted.

## Non-goals

- Renaming WCRPG *mechanic* terms — d20, Checks, DC, EHD, hardpoint, checksum,
  arc. These are the licensed, credited layer and are already generic English.
- Replacing the artwork itself. See **Open question 1**; this is the one place
  the plan may be insufficient on its own.
- Adding the plugin system. That is `FLAVOR_PLUGIN_PLAN.md`.

## Naming scheme

A two-faction, role-bearing scheme. `Enemy_Cruiser` is the target shape: the
name says what it does and who flies it, and says nothing about a copyrighted
universe.

| Hull ID | Old class | Old proper name | Role | Faction | New class |
|---|---|---|---|---|---|
| `home` | Fralthi | TCS Rakshasha | Home Carrier | friendly | `Friendly_Cruiser` |
| `venture-corvette` | Venture | TCS Venture | Corvette | friendly | `Friendly_Corvette` |
| `drayman-transport` | Drayman | MV Grey Drayman | Transport | friendly | `Friendly_Transport` |
| `tarsus-prospector` | Tarsus | MV Lucky Tarsus | Prospector | friendly | `Friendly_Prospector` |
| `longhaul-freighter` | Longhaul | MV Long Haul | Freighter | friendly | `Friendly_Freighter` |
| `bengal-carrier` | Bengal | CSV Bengal | Fleet carrier | friendly | `Friendly_Carrier` |
| `bristol-cruiser` | Bristol | TCS Bristol | Light cruiser | friendly | `Friendly_LightCruiser` |
| `kamekh-escort` | Kamekh | KIS Bloodfang | Escort | enemy | `Enemy_Escort` |
| `salthi-fighter` | Salthi | KIS Sting | Fighter | enemy | `Enemy_Fighter` |
| `raptor-medium` | Raptor | KIS Raptor | Medium fighter | enemy | `Enemy_MediumFighter` |
| `grikath-fighter` | Grikath | KIS Grikath | Heavy fighter | enemy | `Enemy_HeavyFighter` |
| `broadsword-bomber` | Broadsword | KIS Broadsword | Heavy fighter | enemy | `Enemy_Bomber` |
| `ralatha-destroyer` | Ralatha | KIS Ralatha | Destroyer | enemy | `Enemy_Destroyer` |
| `fralthi-carrier` | Fralthi | KIS Fury | Carrier | enemy | `Enemy_Cruiser` |
| `dorkathi-transport` | Dorkathi | KIS Pack Mule | Transport | enemy | `Enemy_HeavyTransport` |

All fifteen class names are unique. The Faction column is derived from the
existing `SHIP_NAMES` registry prefixes: `TCS` / `CSV` / `MV` are friendly,
`KIS` is enemy.

### The Fralthi collision

`Fralthi` is both the crew's home carrier and an enemy hull, and the two carry
**identical** `_HULL_STATS` entries (`ships.py:46` and `ships.py:55`). Under the
new scheme `home` becomes `Friendly_Cruiser` and `fralthi-carrier` becomes
`Enemy_Cruiser` — the same hull flown by both sides, which is what the Fralthi
was. The two ids stay **distinct** and nothing merges; only the class names are
thematically paired.

### `home` keeps its id

`home` is already generic and is referenced from `DEFAULT_SHIP_CLASS`,
`DEFAULT_BY_TYPE`, the tests and the admin console. Renaming it to
`friendly_cruiser` would churn all of them for no naming benefit. Only its
**class name** changes.

## Campaign callsign pools

`campaigns.py:31-34` defines three Kilrathi-clan variant pools used to
generate enemy contact names. These are *variant* pools — several names of the
same role, so two hostile contacts do not read identically.

| Pool | Old names | New names |
|---|---|---|
| `ESCORT_CLASSES` | KAMEKH, TARGU, GOTHRI, RALARI | `Enemy_Escort-01` … `-04` |
| `CAPSHIP_CLASSES` | FRALTHI, RALATHA, DORKATHI, GORATHI | `Enemy_Cruiser-01`, `Enemy_Destroyer-01`, `Enemy_HeavyTransport-01`, `Enemy_Cruiser-02` |
| `FIGHTER_CLASSES` | SALTHI, JALTHI, GRATHA, DRALTHI, HHRISS, KRANT, DRAKHRI | `Enemy_Fighter-01` … `-07` |

**Do not flatten these to `Enemy_Fighter` ×7.** That would collapse the
randomization the pools exist to provide: every hostile fighter would share a
name. Numbered variants keep pool entropy while removing the flavor. The
`vessel_name` / `_class_name` helpers (`campaigns.py:42-50`) need a small change
to accept a numbered variant and de-duplicate against contacts already in the
scenario.

## Proper names

`SHIP_NAMES` (`ships.py:432-448`) supplies registry names for crew-flown hulls.
The `TCS` / `CSV` / `KIS` prefixes are Confederation and Kilrathi constructs and
must go. `MV Long Haul` is the only clean one.

| Old | New |
|---|---|
| TCS Rakshasha | CS Audacity |
| TCS Venture | CS Resolute |
| MV Grey Drayman | MV Grey Falcon |
| MV Lucky Tarsus | MV Lucky Star |
| MV Long Haul | MV Long Haul *(unchanged)* |
| KIS Bloodfang | `Enemy_Escort-01` |
| KIS Sting | `Enemy_Fighter-01` |
| KIS Grikath | `Enemy_HeavyFighter-01` |
| KIS Ralatha | `Enemy_Destroyer-01` |
| KIS Fury | `Enemy_Cruiser-01` |
| KIS Pack Mule | `Enemy_HeavyTransport-01` |
| CSV Bengal | CS Vanguard |
| TCS Bristol | CS Resolute |
| KIS Raptor | `Enemy_MediumFighter-01` |
| KIS Broadsword | `Enemy_Bomber-01` |

Enemy hulls reuse their callsign-pool entry so a hull flown by the crew and the
same hull met as a contact agree on the name. `CS Resolute` appears twice
(`venture-corvette` and `bristol-cruiser`) — change `bristol-cruiser` to
`CS Resolute` → `CSV Lancaster` to keep them distinct.

## Universe terms

| Old | New | Where |
|---|---|---|
| "Wing Commander" | *(dropped)* | `README.md`, `bridge/CREDITS.md`, `bridge/WCRPG_INTEGRATION_PLAN.md`, `bridge/activity/dist/index.html` |
| "Kilrathi" | "Hostile" | `campaigns.py:31` |
| `KIS` | *(drop prefix)* | `ships.py:432-448` |
| `TCS` / `CSV` | `CS` / `CSV` | `ships.py:432-448` |
| "Confed" / "Confederation" | "Concord" | phase plans |
| `Sumn Tp'ka` | `Sector 9 Anomaly` | `campaigns.py:332,346-347,367,500`, `resources/bridge_hazards.json:15`, `resources/bridge_nav_points.json:23`, `resources/bridge_events.json:39`, 2 test files |
| "Frontier" (theater) | "Outer Reach" | `campaigns.py:348` |
| `lance-corvette` (orphaned model default) | `friendly-corvette` | `types.py:582` |
| `Sabre-T`, `Fralthi-CL`, `RapierII-WW`, `Kamekh-S` (plan-doc only) | *(dropped)* | `SHIP_CUSTOMIZATION_PLAN.md:19-21` |

`lance-corvette` at `types.py:582` is dead: it is not in `SHIP_CLASSES`, not in
`bridge_hulls.json` and not in the art map. It survives only as a free-form
`str` default that Pydantic accepts. Fix it as part of this work and note in
`FLAVOR_PLUGIN_PLAN.md` that a flavor's defaults must be validated against the
flavor's hull list, which would have caught it.

## Asset renames

Twenty-eight files. Use `git mv` so history follows.

| Old | New |
|---|---|
| `img/action/{fralthi,venture,drayman,tarsus,longhaul,kamekh,salthi,grikath,ralatha,dorkathi,bengal,bristol,raptor,broadsword}.png` | `img/action/{friendly_cruiser,friendly_corvette,friendly_transport,friendly_prospector,friendly_freighter,friendly_carrier,friendly_light_cruiser,enemy_escort,enemy_fighter,enemy_medium_fighter,enemy_heavy_fighter,enemy_bomber,enemy_destroyer,enemy_cruiser,enemy_heavy_transport}.png` |
| `img/vdu/<same>-vdu.{gif,png}` | `img/vdu/<same>-vdu.{gif,png}` |

`home` and `fralthi-carrier` currently share `fralthi.png` (identical stats, so
identical art is correct). After the rename they share `friendly_cruiser.png` /
`enemy_cruiser.png` — the art audit will flag this as two classes on one image,
which is intended here. Record the decision in the `SHIP_ART_MAPPING_PLAN.md`
inventory rather than splitting the file.

Update in the same commit: `resources/bridge_ship_art.json` (all 15 entries) and
the `_FALLBACK_ACTION` map (`ships.py:64-80`). Note `longhaul-vdu.gif` is listed
in JSON but the tree holds `longhaul-vdu.png`; the extension-swap fallback in
`_candidate_urls` (`ships.py:105-123`) covers this, so it can stay.

There is **no** `ships` table in the database. `db.py` only has `rooms` with a
JSON state blob, and the `_FALLBACK_ACTION` comment about "the DB's own
filenames" refers to a legacy external catalog that is not in this tree. No SQL
migration is required.

## Persistence migration

`db.py:69` discards any room whose `schemaVersion` does not match
`STATE_SCHEMA_VERSION`. Contacts persist their display `name` in the state blob
(`types.py:919`), so a retained blob would show `KIS Fury` indefinitely and a
corrected name would never reach an in-progress room.

**Bump `STATE_SCHEMA_VERSION` 3 → 4** and let in-flight rooms wipe on first
reload. This is the existing precedent — the 2 → 3 bump did the same for the 3D
move. Rooms are ephemeral sessions and a content rename does not justify a
presentation-string migration.

If a deployment has in-progress rooms it cannot lose, the alternative is a
one-off migration that walks `contacts[].name` and rewrites it through the
old→new callsign map. Recommend the wipe; keep the migration in mind only.

## Docs

- `CREDITS.md` — rewrite. Keep WCRPG / TEOC / Origin attribution explicit and
  state plainly that mechanics were ported and tables re-authored, with the
  setting vocabulary original to this project. This is the file that makes the
  rest of the plan defensible, so it is not a cosmetic step.
- `README.md` — drop the "Wing Commander" framing; describe the game on its own
  terms.
- `bridge/activity/dist/index.html:22` — the client title/meta.
- Phase plans naming hulls: `SHIP_CUSTOMIZATION_PLAN.md:19-21,99-102`,
  `SHIP_ART_MAPPING_PLAN.md:5,30,44-46,83,110,124`,
  `SENSORS_EW_MINIGAME_PLAN.md:59,78`,
  `CATALOGUE_MATCHING_MINIGAME_PLAN.md:19,21,31-32`, `ROADMAP.md:463,474`.
- `WCRPG_INTEGRATION_PLAN.md` — keep the "Wing Commander" mentions; they are
  *attribution* for the ruleset, which is correct and required.

## Tests

- No case-insensitive match for any name in the retired list remains outside
  `CREDITS.md` and the attribution lines of `WCRPG_INTEGRATION_PLAN.md`. Encode
  this as a CI grep gate with an explicit allowlist, so the names cannot creep
  back in.
- All 15 hull ids resolve to exactly one `ShipClass`, with unique `name`.
- `home` and `fralthi-carrier` remain distinct classes with equal stats.
- Every `bridge_ship_art.json` target exists; `_FALLBACK_ACTION` agrees with it.
- Each of the 15 classes appears in a `SHIP_NAMES` entry, and no two enemy
  classes share a callsign.
- Campaign contact names drawn from a 7-name pool are distinct within a
  scenario — the regression guard for the pool-flattening trap above.
- `types.py` `shipClass` default is a real hull id in `SHIP_CLASSES`.
- A room persisted at schema 3 is rejected and a fresh room is created at 4.

## Implementation order

1. Decide **Open question 1** (artwork) before touching anything.
2. Rename the 15 classes in `ships.py` `SHIP_CLASSES`, `SHIP_NAMES` and the
   default map; update `bridge_hulls.json` `shipType` and `bridge_ship_art.json`.
3. Rework the three callsign pools in `campaigns.py` to numbered variants; teach
   `_class_name` to de-duplicate within a scenario.
4. `git mv` the 28 art files; update `_FALLBACK_ACTION`.
5. Replace the universe terms: `Sumn Tp'ka`, `Frontier`, "Kilrathi", the
   `lance-corvette` default.
6. Bump `STATE_SCHEMA_VERSION` to 4.
7. Update the tests, then rewrite the docs and `CREDITS.md`.
8. Add the CI grep gate.

## Open questions

1. **Is the artwork itself derived from Wing Commander?** If the images depict
   WC ships, renaming the files is cosmetic — the repo still ships the art.
   This needs answering before step 4, and the honest fix is original art
   against the new class names. `FLAVOR_PLUGIN_PLAN.md` makes replacement
   mechanical once the filenames are stable.
2. **Keep `home` as an id?** Recommended yes. It is already generic; only its
   class name changes.
3. **Does `bristol-cruiser` need a distinct proper name?** `TCS Venture` and
   `TCS Bristol` both want `CS Resolute`; `CSV Lancaster` is proposed.

## Implementation notes

Landed with these decisions, which supersede the tables above where they differ:

- **Hull ids are kebab-case role ids that match the art filenames.** `home` is
  kept; the rest are `friendly-corvette`, `friendly-transport`,
  `friendly-prospector`, `friendly-freighter`, `friendly-carrier`,
  `friendly-light-cruiser`, `enemy-escort`, `enemy-fighter`,
  `enemy-medium-fighter`, `enemy-heavy-fighter`, `enemy-bomber`,
  `enemy-destroyer`, `enemy-cruiser`, `enemy-heavy-transport`. The art stems
  drop the underscores the asset table above proposed.
- **The artwork was regenerated, not just renamed.** The old placeholders had
  the retired class name rendered into the image itself (e.g. `FRALTHI` on
  `fralthi.png`, and in every VDU scan). `tools/generate_placeholder_art.py`
  rebuilds all 30 action/VDU placeholders from the new names, so no retired
  name ships in a binary.
- `home` keeps its id but uses `friendly-cruiser.png` — the one id/filename
  mismatch, recorded in `SHIP_ART_MAPPING_PLAN.md`.
- **Terms outside this plan's list were also retired:** the "Gemini Sector" UI
  label and design-language references, the Morvan/Akwende drive names (now
  Standard/Heavy/Rapid), the "Kilrah Approaches" theater (now "Hostile
  Approaches"), and the Kilrathi-styled `K'har Wreckline` terrain name.
- **Registry prefixes:** `CS` (ex-`TCS`), `CSV` (unchanged) and `MV`;
  `friendly-light-cruiser` is `CSV Lancaster` and `friendly-carrier` is
  `CSV Vanguard`.
- Campaign `sumn-tpka` is now `sector-9-anomaly` ("Sector 9 Anomaly",
  "Hostile Outer Reach").
- `STATE_SCHEMA_VERSION` is 4, and `tests/test_no_wing_commander_names.py` is
  the CI grep gate (allowlisting `CREDITS.md`, `WCRPG_INTEGRATION_PLAN.md` and
  this file).
