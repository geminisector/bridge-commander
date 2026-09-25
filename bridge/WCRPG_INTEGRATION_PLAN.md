# WCRPG Integration Plan

## What this is

A plan for importing mechanics from **The Wing Commander Role-Playing Game**
(WCRPG, the 2013 d% rulebook by Stephen A. Rogers) into the Bridge Commander
tactical watch in `bridge/`.

Source examined: `the_wing_commander_role_playing_game.pdf`, 1118 pages. Its
text layer has a broken ToUnicode map, so the rules were read by rendering and
OCR-ing pages. **Printed page = PDF page − 10**; all refs below are PDF pages.
An OCR digest and transcripts live in `tmp/wcrpg/` (`WCRPG_DIGEST.md`,
`ch9.txt`, `ch9gen.txt`, `ch7sys.txt`, `ch8.txt`, `ch12env.txt`, `ch3a-c.txt`).

WCRPG is a full tabletop RPG with character-scale melee, worlds, a bestiary and
a trading economy. This plan lifts only what deepens the bridge's existing
fantasy — a watch fighting to see and not be seen — and drops the rest.

## Licensing and attribution (read first)

- The rulebook is **CC BY-NC-SA 3.0** and derives in part from *The Edge of
  Chaos, A Wing Commander RPG* by Mark Shotwell.
- CombatBot is unofficial and non-commercial, so the licence fits — but it is
  **ShareAlike**: copied *text or tables* must credit WCRPG + TEOC and be
  relicensed under the same terms.
- Therefore **port mechanics, not prose or table layouts** (mechanics are not
  copyrightable; expression is). Re-author every table in our own words and
  credit WCRPG/TEOC. Nothing here may be sold or paywalled.

## What the bridge already has

`shared/`: types, constants, `math_utils.hash_random`, ships, weapons,
campaigns, events, protocol. `server/`: `engine.py` (sensors/EW/comms/weapons/
navigation/hazards/events), `ws.py`, `rooms.py`, admin.
Player checks today are **deterministic accumulation**, not dice: passive
barcodes paint in, lock accumulates on a rate, cooldowns are simulated-time
timers. There is **no skill or check system anywhere** in `bridge/`
(verified). Already planned (don't duplicate): `HAZARDS_AND_REALTIME_PLAN.md`,
`SENSORS_EW_MINIGAME_PLAN.md`, `COMMS_WEAPONS_PLAN.md`,
`SHIP_ART_MAPPING_PLAN.md`.

## The one big idea: a d% Check layer, used only at decisive moments

> **Implementation note (decided).** The bridge resolves Checks on a **d20**, to
> match the rest of CombatBot, not the book's d%: roll + skill modifier (derived
> from the 0-99 WCRPG rating) against a **hard** DC, a natural 20 a critical
> success and a natural 1 a critical failure. The skill catalogue,
> specializations and the *idea* that difficulty should bite all survive; the die
> and the crit rule do not. The d% references below describe the source rules,
> not what we build.

WCRPG's core mechanic (PDF 13): roll d%, succeed if **≤ DC** (the relevant
attribute/skill score); degree of success = `DC − roll`, failure = `roll − DC`.
Crucially, the **crit bands scale with the DC**: crit-success threshold is
`DC ÷ 10`, crit-failure threshold is `90 + (DC ÷ 10)`; 00 and 99 always crit.
A high-DC action is both harder to crit-succeed and *easier to crit-fail* —
exactly the tension we want on a hard sensor read or a jury-rig.

Keep the gradual accumulation. Layer Checks on the **committing** actions: tag a
track, a high-power sweep, an IFF challenge, a repair, a manoeuvre, a gunnery
solution. That adds a climax without turning the watch into a dice fest.

## The ten highest-value mechanics to port

Ranked by fit with the bridge; all page-cited.

1. **DC-scaled crit bands** (PDF 13). As above. Plug into firing-solution
   quality, repairs, and identification: the harder the task, the wider the
   failure band.
2. **One EHD formula drives every shot** (PDF 587–589, 606–607):
   `EHD = target HD (BHD/FHD as applicable) − (attacker Combat Maneuvers −
   target Evasive Maneuvers) − range penalty`. Range penalty is 2/increment for
   vehicles (1 with Tachyon Radar), 1/increment for capital ships, and 5 for
   ordnance beyond optimal range. A Marksmanship Check per gun, a Ballistics
   Check per ordnance piece; full success adds **one extra hit per 5 points of
   degree**. This is the natural home for the bridge's sensor picture and EMCON
   state: they should set the range penalty and lock.
3. **Radar damage has a hard, legible effect** (PDF 592, 609). A damaged/destroyed
   radar gives **−25 HD to anyone the ship fires upon** (i.e. attackers get
   better) and forbids lock-requiring ordnance. Maps straight onto the
   gravidar/EM model as a sensor-system malfunction.
4. **Jamming flips Friend-or-Foe missiles into automatic critical misses that
   damage the firer** (PDF 583, 602). A ready-made IFF/comms-warfare consequence
   that pairs with the existing IFF layer.
5. **Countermeasure spoofing is a real opposed sub-game** (PDF 589–590): needs
   a failed Ballistics that still beat EHD, requires ≥1 pod, and each pod adds
   **+5 (+10 enhanced)** to the spoof DC, capped by range; resolved on d%. The
   bridge's noisemakers map 1:1.
6. **Targeting a specific system converts damage by defence state** (PDF 601):
   shields up → **damage ÷ 100**; armour only → **÷ 10**; no defences → full.
   Each point = 1% system damage plus a malfunction check, capped at 100%.
   Subsystem strikes only pay off once shields are stripped — a strong tactical
   sequencing rule.
7. **Alert status costs something** (PDF 599–600): Condition Three → Two
   (Yellow: shields up, weapons still disarmed) → One (Red: shields + weapons).
   **Arming weapons or raising shields costs one fuel point and instantly
   charges all weapons**; lowering is free. A natural Three/Two/One state
   machine for the readiness/battery dial.
8. **Capital-ship defence arcs + refocus** (PDF 590, 603): four independent
   SHP/AHP pools. **Refocus Shields** needs **two consecutive Defenses Checks**
   to redistribute SHP, and a critical failure does **1d% shield damage** — a
   facing mechanic with a risk-bearing crew action instead of free reallocation.
9. **Excessive-damage escalation** (PDF 593, 610): hitting an already-destroyed
   or absent system deals **+10% Core Damage, then +10% per subsequent hit**
   (10/20/30/40). A clean "stop poking the hole" rule.
10. **Space terrain doubles as a hazard/fuel index** (PDF 457): interstellar =
    Extremely Easy … asteroid field = Difficult, packed field = Very Difficult,
    **neutron-star vicinity = Extremely Difficult, black-hole event horizon =
    Impossible**. Plus **nebula = −500 SHP** (PDF 390) and asteroid collision =
    `10 × (5 + 1d5) × current speed × 1d10` (PDF 587).

Also cheap and strong: **Undermanned Penalty** — below 90% crew, every Check
must succeed **twice in a row** (PDF 596, 611); and **Shaken** (−30 to all
Checks, refuses orders) with **Rally/Inspire** as the commander's counters
(PDF 578, 598, 140).

## Mapping: WCRPG → bridge (corrected refs)

| WCRPG | Bridge today | Proposed use |
|---|---|---|
| d% Check, DC-scaled crits (PDF 13) | none | `shared/checks.py`: `roll_percent(state, salt)`, `resolve_check(score, dc, roll)`. |
| Skills, 13 categories (PDF 135–149) | seats/hats | Seat skill blocks; Tech→Sensors, Translate/Distress→Comms, Astrogation/Piloting/Stealth→Ops, Targeting/Marksmanship/Ballistics/CM/EM→Weapons, Damage Control/Defenses/Internal Systems→DC, Strategy/Leadership→Command. |
| EHD (PDF 587–589, 606–607) | solution quality | Solution becomes an EHD calculation carried in the handoff. |
| Four defence arcs, SHP/AHP, refocus (PDF 590–594, 601–603) | no shields | Per-arc shields/armour, regen, Refocus, arc targeting. |
| Core Damage %, SI Check, systems table (PDF 590–594) | `ship.hull` 0–100 | Hull → armour + core %; per-system health; SI check. |
| System malfunction, Damage Control, jury-rig (PDF 593–596) | `dc:inspect` | `dc:repair {system}`, jury-rig, malfunction DC `100 + Damage Control − damage`. |
| Alert ladder Three/Two/One (PDF 599–600) | condition + RoE + battery | Explicit alert state machine with fuel cost. |
| Engine Class table (PDF 390) | cruise/max speed | Engine class → initiative, max speed, fuel efficiency, −1 HD/class. |
| Modules: ECM, SWACS, cloak, countermeasure pods, phase shields, ITTS, tracking computer (PDF 395–396) | noisemakers/buoys/mounts | Ship module loadout reusing existing systems. |
| Fuel + terrain ladder + FTL (PDF 390, 456–459) | no fuel | Ops fuel dial, drive types (D/Morvan/Akwende), jump costs. |
| Nebula/asteroid/minefield, life-support (PDF 390, 587, 593, 605, 609) | `Hazard` model | Ship-scale hazards (Ch 12.3 is character-scale only — see below). |
| Traits / Complications (Ch 4) | none | Crew traits + modifiers + RP hooks. |
| Trading (Ch 5), reputation (PDF 830/960/970) | weapon catalog, digest | Refit market; reputation as a Trait feeding the digest. |

## Proposed additions in detail

### 1. Deterministic d% Check layer (foundation)
`bridge/shared/checks.py`:
- `roll_percent(state, salt)` (0–99) on `hash_random(simClock, salt)`, so 1x/4x/
  manual produce identical results (the hazards plan's determinism rule).
- `resolve_check(score, dc, roll)` → `(success, degree, critical)` with the
  DC-scaled bands and 00/99 overrides.
- `CheckResult` wire model so the UI can show `ROLL 43 ≤ DC 55 — SUCCESS (deg 12)`
  and crits, keeping the "evidence, not truth" honesty.
- `resources/bridge_skills.json`: skill catalogue + default DCs, GM-editable.

### 2. Crew skills on stations
- `SeatSkills` per seat (`technology`, `communications`, `astrogation`,
  `targeting`, `damageControl`, `defenses`, `strategy`, `leadership`, …) plus
  one or two **specializations** (WCRPG specializations add directly to a Check;
  the book's worked example adds +23).
- Default "crew average" so solo play never stalls; GM console can set scores.
- WCRPG's command skills become real: **Strategy** (+1 CM/EM per 5 points of
  success), **Guidance** (one-tenth of result to a subordinate's next DC),
  **Security** (+1 attack per 5 points), **Leadership** (Rally/Inspire).

### 3. Checks on committing actions (first integration)
- `sensor:claim` — tag becomes a Check vs a DC set by evidence quality; crit
  success promotes a rung, crit failure reports a confident wrong class (still
  never reveals truth).
- `sensor:activeSweep` / `nav:gravScan` — Check for an extra barcode step or a
  false return; scanning-gear damage subtracts from the DC.
- `comms:iff` — Communications Check vs target ECM; crit failure believes a
  spoof.
- `dc:inspect` → `dc:repair {system}` with an Engineering Check.

### 4. Shields, arcs, alert state
- `ShipState.shields: {fore, aft, port, starboard}` each `{shp, max}` +
  `shieldClass`; armour per arc; SI check = `DC 100 − coreDamage` (failure
  destroys the craft).
- Regen: `10% total SHP + engineering Defenses` every ten rounds when not under
  fire; **Recharge** action restores one gun hardpoint plus
  `10% max + Defenses` to all arcs (PDF 603).
- **Refocus Shields**: two consecutive Defenses Checks; crit failure = 1d%
  shield damage.
- **Alert ladder**: Three → Two (shields up, weapons disarmed) → One (shields +
  weapons); going up costs a fuel point and charges all weapons; attacks require
  Condition One.

### 5. System health and damage control
- `ShipState.systems: {shields, guns, ordnance, radar, comms, engines, flightDeck,
  lifeSupport}` with `health 0–100` and `malfunctioning`.
- One systems-damage instance per 5% core damage, each 25% to a d10-rolled
  system; the effects table is already bridge-shaped (radar −25 HD/no lock
  ordnance; comms no hail and FOF missiles auto-miss into the firer; engines =
  no movement; life-support defers to environmental rules).
- **Damage Control Check** mitigates `degree ÷ 10` %; malfunction DC =
  `100 + Damage Control − accumulated damage`; **jury-rig** restores function at
  a DC penalty equal to damage received but auto-malfunctions on any new hit.
  Armour and core are **not** repairable in combat.
- **Excessive damage**: strikes on a dead/absent system add +10% core, then +10%
  more each subsequent hit.

### 6. Manoeuvres and EHD solutions
- `maneuver:order {type}`: **Jink** (−10 to incoming HD bonus, −10 to own
  gunnery, must be first), snap turn (free movement), forward slip / 90° / 180°
  with escalating piloting Checks, and the canonical compositions (Immelmann,
  Shelton Slide, etc.). Advanced manoeuvres accumulate CM/EM bonuses until the
  next turn, paid for with a gunnery penalty.
- Solution quality in the handoff becomes `EHD` via the formula, so a manoeuvre
  changes the shot, not just the exposure meter.
- Targeting a subsystem uses Targeting Check vs HD (`−1`/increment capital,
  `−2` vehicle) and the defence-state damage conversion.

### 7. Ordnance as objects
- Heavy ordnance (torpedoes/capship missiles) is **not** resolved instantly: it
  is a Size-Class-1 vehicle with HD 15/29/21, EM 5, Init +11, 300 SHP / 100 AHP,
  active for its optimal range, and can be **shot down** (PDF 611–614). This
  gives the bridge a live inbound-track phase to hang decision events on.
- Light ordnance can be **spoofed** (the countermeasure sub-game above).

### 8. Fuel, drives, navigation
- `ShipState.fuel` + `fuelCapacity`; consumption indexes the **terrain
  difficulty ladder** against engine efficiency (PDF 457).
- Engine class table (PDF 390): efficiency 5→50%, initiative = class, max speed
  2→1024 kps, −1 HD/class.
- Drives: D-Drive (low FTL, ≤5 AU), Morvan (hops), Akwende (instantaneous
  between systems); fuel per transit by size class; a ramscoop refuels in flight
  (PDF 396, 458–459). Astrogation + FTL Mechanics gate course-plotting.
- Ops gets a fuel dial; running dry is a decision event, not silent failure.

### 9. Ship-scale hazards (corrected)
**Ch 12.3 (PDF 980–998) is entirely character-scale** — heat/cold, fire, acid,
smoke/thin air, gravity/falling, disease/poison — and contains **no ship hazard
table**. Life-support failure explicitly defers to it, i.e. the GM hand-applies
Suffocation/Heat-Cold to compartments. So build ship hazards from the scattered
canon instead: **nebula (−500 SHP, PDF 390)**, **asteroid/minefield collision
(PDF 587, 605)**, and the **terrain-difficulty ladder (PDF 457)** — plus
life-support failure (PDF 593, 609) mapped to the existing `Hazard` fields
(`noise`/`exposure`/`concealment`).

### 10. Morale, traits, equipment, progression
- **Shaken** (−30, refuses orders) and **Rally/Inspire**; **Undermanned Penalty**
  (double-success Checks below 90% crew); overcrowding (−5 DC per whole multiple
  over 120%).
- **Traits / Talents / Complications** (Ch 4): one or two per station.
- **Refit/trading** (Ch 5) between missions, off `shared/weapons.py`.
- **Reputation** is only a Trait in WCRPG (PDF 830/960/970) — keep it that way;
  feed awards into `LogbookDigest`.

## Explicit non-goals

Character-scale/melee combat and the whole of Ch 12.3's character hazards;
worlds/communities/creatures and the bestiary; the full navigation atlas and the
100 adventure seeds. The CombatBot mission generator already owns scenario
authoring. Do not port the full WCRPG wargame — the bridge is a watch, not a
squadron simulator.

## Data model, protocol, UI

- `shared/types.py`: `CheckResult`, `SeatSkills`, `ShipModule`; `ShipState` gains
  `shields`, `armor` (per arc), `core`, `systems`, `alert`, `fuel`,
  `fuelCapacity`, `modules`, `maneuver`, `crewStrength`; `HandoffWeapons` gains
  `targetHd`, `ehd`, `arc`, `shieldShp`.
- `shared/protocol.py` (C2S): `dc:repair`, `power:distribute`, `maneuver:order`,
  `nav:alert`, and fuel folded into nav; ordnance tracks as contacts.
- UI: **Command** crew skills + system health + alert; **Sensors** the Check
  result; **DC** system repair/jury-rig; **Ops** fuel + manoeuvre + arcs;
  **Weapons/Comms** arc and shield state in the solution/handoff.
- Admin console: edit skills, modules, shields, DCs.

## Determinism and testing

- All rolls from `hash_random(simClock, salt)`; no wall-clock, no global RNG;
  1x/4x/manual identical (existing rule).
- Tests: crit bands incl. 00/99; same-minute determinism; EHD against the book's
  worked example re-authored; spoof DC with pods; defence-state damage
  conversion; Refocus two-Check rule and crit damage; malfunction DC and
  jury-rig re-failure; excessive-damage escalation; radar −25 HD; alert fuel
  cost and instant charge; undermanned double-success; nebula −500 SHP;
  asteroid collision formula; and that a bad tag still never reveals truth.

## Phased implementation

1. **Rules foundation** — `checks.py`, `bridge_skills.json`, `CheckResult`,
   tests. No gameplay change.
2. **Crew skills + first Checks** — seat skills; Checks on `claim`,
   `activeSweep`, `iff`, `dc:repair`; UI shows the roll.
3. **Shields + arcs + alert ladder** — SHP/AHP per arc, regen, Refocus, Three/
   Two/One; handoff gets arc/shield/alert data.
4. **System health + damage control** — per-system damage, d10 table effects,
   malfunction, jury-rig, excessive damage.
5. **Manoeuvres + EHD solutions** — manoeuvre orders; handoff solution becomes
   EHD; subsystem targeting.
6. **Fuel + drives + terrain ladder** — fuel dial, engine class, drives, jumps.
7. **Ordnance as objects** — inbound torpedo tracks, shoot-down, spoofing.
8. **Ship hazards + morale/traits** — nebula/asteroid/life-support, Shaken,
   Rally/Inspire, Undermanned.
9. **Refit, traits authoring, progression** — between-mission market, GM skill/
   module editing, digest awards.

Each phase ships with tests and keeps the game playable; nothing should break
the "pause and hand off to tabletop" escape hatch.

## Risks / open questions

- **Scope**: WCRPG combat is a full wargame. Checks + shields + system damage are
  the high-value core; movement points, every module and mixed-scale conversion
  are optional. Recommend phases 1–5 first.
- **Solo play**: default crew scores are required.
- **Determinism vs surprise**: hash rolls are reproducible; salt per
  action+contact and never expose it.
- **Licensing**: mechanics only, re-authored tables, credit WCRPG/TEOC,
  non-commercial, ShareAlike any copied expression.
- **Canon**: WCRPG uses the Arena timeline; keep rules timeline-agnostic.

## Recommendation

Do phases 1–5. They convert the bridge's deterministic sensors-and-solutions
loop into a skill-driven watch with shields, real system damage, alert states
and manoeuvres — the WCRPG material native to a bridge simulation — while
respecting the repo's determinism, test and handoff conventions. Fuel, ordnance
objects, hazards and refit are strong later flavour.
