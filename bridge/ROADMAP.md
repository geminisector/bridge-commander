# Bridge Commander — Consolidated Roadmap

## Purpose

The seven plans in this folder are detailed specs. This document is the single
**sequencing** layer: what order to build them in, what each phase delivers,
what it depends on, and how we know it is done.

Source specs (unchanged; read the one you are implementing):

| Plan | Covers |
|---|---|
| `COMMS_WEAPONS_PLAN.md` | transmission modes, IFF, weapon states, solutions, `weapons-warning` |
| `HAZARDS_AND_REALTIME_PLAN.md` | time modes, hazard model, cooldowns, interrupts, watch bar |
| `SENSORS_EW_MINIGAME_PLAN.md` | barcode, passive minigame, blind tagging, catalogue |
| `SHIP_ART_MAPPING_PLAN.md` | canonical hull art resolver, audit, contact sheet |
| `WCRPG_INTEGRATION_PLAN.md` | d20 Checks, skills, shields/arcs, system damage, manoeuvres, EHD |
| `TRANSIT_AND_ENDURANCE_PLAN.md` | fuel, range ring, ETA/CPA, astrometrics, jump alignment, heat, crew |
| `SUBMARINE_INSPIRATION_PLAN.md` | datum/hunt, signature layers, sprint/drift, TMA, baffles, comms windows |
| `ENVIRONMENTS_AND_MAINTENANCE_PLAN.md` | 9 environment types, wear vs damage, repair-in-hazard, spares/salvage |
| `SHIP_CUSTOMIZATION_PLAN.md` | hull catalog, hardpoint loadout, modules/power, refit & field-mod, identity |

## Product goal

A GM-light, browser-based **tactical watch** for 4 stations (Command, Ops,
Sensors/EW, Comms/Weapons) in which the crew's real job is *to see and not be
seen* — and which can pause at any moment and hand the fight off to a tabletop.

## Design invariants

Every phase must preserve all of these. A phase that breaks one is wrong even
if it "works".

1. **Determinism.** All randomness comes from `hash_random(simClock, salt)`.
   1x, 4x and manual advance must produce identical state for identical
   simulated time.
2. **Pause and hand off.** The handoff pack must remain complete and truthful at
   any point. Never trap the table in a live loop.
3. **Station ownership.** Every mechanic has one owning station and affects at
   least two others. If nobody owns it, it is scenery.
4. **The loop test.** A mechanic needs a visible finite resource, a deadline, an
   owner, a decision with no dominant option, a *graded* failure, and feedback
   into a neighbour system. Otherwise it is a stat.
5. **Agent/UI parity.** Anything the GM or a player can set has a wire field
   with a safe default; the hand-maintained bundle must keep rendering.
6. **Data-driven content.** New tables/values go in `resources/bridge_*.json`,
   not constants, unless they are physics.
7. **Tests ship with the phase.** Including a determinism test and a
   round-trip/persistence test for any new state.
8. **Licensing.** Port mechanics, re-author tables, credit WCRPG / TEOC and the
   submarine-genre references, stay non-commercial. Never copy rules text.

## Phase gate

Every phase must pass this checklist before it counts as done (P0.4). Record
deviations in the phase section rather than waiving them silently.

- [ ] `python -m pytest` is green; no test was deleted or skipped to get there.
- [ ] A **determinism** test: identical simulated minutes produce identical
      state at 1x, 4x and manual advance.
- [ ] A **persistence round-trip** test for any new state, with a schema bump.
- [ ] New wire fields default safely; `node --check` passes on the activity
      bundle and the affected tab still renders.
- [ ] The **GM console** can author/set the new values, or the plan says
      explicitly why not.
- [ ] The owning station's panel shows the new loop; the watch bar shows its
      urgent state.
- [ ] The **loop test** holds: visible resource, deadline, owner, no dominant
      option, graded failure, neighbour feedback.
- [ ] README/plan updated and this file's **Current state** row ticked.

## Current state

| Area | Status | Evidence / gap |
|---|---|---|
| Sensors barcode, catalogue, blind tagging | **Done** | `catalogueMatches`, `waveform`, `resources/bridge_signatures.json` |
| Comms modes, IFF, relay/challenge/civilian/false-surrender | **Done** | engine + `resources/bridge_events.json` |
| Weapon states, mount catalog, quick/refined solutions, handoff | **Done** | `prep_weapons`, `solutionQuality`, `weaponTarget` |
| Comms/Weapons UI (modes, prep/lock, hull reveal, IFF, intercept) | **Done** | activity bundle comms + sensor panels |
| Time modes, hazards, cooldowns, watch bar | **Done** | `timeMode`/`timeScale`/`cooldowns`, `bridge_hazards.json` |
| Victory conditions (endurance / all-tracked / disengage), campaigns | **Done** | `_check_patrol_win`, three scenario campaigns |
| Seats, leave/claim, GM admin | **Done** | `setSeat`, admin reset/setShip |
| Ship art catalog, resolver, audit, contact sheet | **Done** | `resources/bridge_ship_art.json`, `audit_ship_art()`, `tools/bridge_contact_sheet.py` |
| Test suite | **Green** | bridge suite passes; stale tests re-encoded to blind tagging + grav-scan cooldown |
| d20 Check layer, seat skills, Checks on actions | **Done** | `shared/checks.py`, `Seat.skills`, wired into claim/sweep/grav/IFF/DC, GM skill editor |
| Shields/arcs, alert ladder, handoff defences | **Done (P3a)** | DB-fitted shields, Three/Two/One alert, regen, Refocus; handoff carries alert/core/shields/systems |
| System damage, damage control, wear | **Done (P3b)** | `apply_damage` (arcs→system table→excess core), malfunction gates, `dc:repair`/jury-rig, `dc:maintain`, wear accrual; DC panel |
| EHD in the handoff, defensive manoeuvres | **Done (P7a)** | `shared/ehd.py`, live `weaponEhd`, `ops:maneuver` (jink/slips/snap/break) |
| Fuel economy, range ring, bingo, dead-drift | **Done (P4a)** | DB fuel capacity, speed/alert/sensor/hazard burn, ops range ring, bingo + dead-drift |
| ETA/CPA intercept clock | **Done (P4a)** | `sensor.cpaKlik`/`cpaMinutes`/`etaMinutes` per track; sensors panel |
| Astrometrics: nav plots, legs, Astrogation, arrival | **Done (P4a)** | `resources/bridge_nav_points.json`, `plotLegs`, `nav:plot`/`nav:commit`/`nav:survey`, offset arrival |
| Jump points, spool/alignment, commit/abort, misjump | **Done (P5a)** | `jump:spool`/`jump:commit`/`jump:abort`, `JumpState`, windows, pirate points, misjump |
| Drive table, nav uncertainty + fixes, comms windows | **Done (P5b)** | `resources/bridge_drives.json`, `navErrorKlik` + `nav:fix`, periodic relay window |
| Heat budget (vent/bottle) | **Done (P8a)** | `ship.heat` + `heat_load_per_hour`, `ops:heat`, penalty folded into every Check |
| Datum / hunt, sprint-drift, baffles | **Done (P6a)** | `GameState.datums`, `place_datum` decay/re-center, `ops:posture`, aft baffle arc + `sensor:clearBaffles`, endurance gate |
| Signature layers, TMA manoeuvre-to-solve, hunter behaviour | **Done (P6b)** | `resources/bridge_layers.json` + cross-band attenuation, `ops:tma` solve, hunters search datums / prosecute locks |
| Subsystem targeting, ordnance in flight, spoofing | **Done (P7b)** | `weaponTargetSystem` + defence-scaled system damage, `GameState.ordnance` loop, spoofing pods |
| Watch bill, fatigue, morale, consumables | **Done (P8a)** | `ops:watch`/`ops:heat`/`ops:rally`, `state_check_penalty` folded into every Check, spares/provisions |
| Nine-environment catalog, spares, salvage, contamination | **Done (P8b)** | `resources/bridge_environments.json` + modifiers wired into sensors/fuel/wear/comms/repair; `dc:salvage`, `nav:replenish` |
| Hull catalog, hardpoint loadout, modules, refit | **Done (P9)** | `resources/bridge_hulls.json` (15 hulls, arc-coded hardpoints), `bridge_modules.json`, `dc:fitModule`/`dc:unfitModule`, handoff identity |
| Picket barriers, hangar ops, boarding, career, mission chart | **Done (P10)** | `bridge_barriers.json` + crossing events, `ops:hangar`, `comms:board`, XP/medals in the digest, `shared/missions.py` |

## Roadmap at a glance

| Phase | Name | Goal | Depends on | Exit criteria |
|---|---|---|---|---|
| **P0** | Stabilise | Green suite, close out in-flight specs, single docs index | — | `python -m pytest` green; art audit passing; no plan left half-shipped |
| **P1** | Rules foundation | Deterministic d20 Check layer + skill data, no behaviour change | P0 | `checks.py` + tests; same game state for the same rolls |
| **P2** | Crew & command | Seat skills; first Checks on committing actions; GM authoring | P1 | Roll visible in UI; a Check can crit; GM can edit skills |
| **P3** | Survivability | Shields/arcs, alert ladder, system health, damage control, wear & repair-in-hazard | P2 | A ship can be hurt system-by-system, repaired, and arrive worn |
| **P4** | Transit operations | Fuel + range ring, ETA/CPA clock, astrometrics plotting | P2 | A leg has a visible time/fuel/risk cost and a deadline |
| **P5** | FTL & navigation | Jump alignment, drives, nav uncertainty, comms windows | P4 | A jump can be won, aborted, or misjumped |
| **P6** | The hunt | Datum, signature layers, sprint/drift, TMA, baffles | P4, P5 | Detection creates a decaying search you can break |
| **P7** | Threat & weapons | Manoeuvres/EHD, ordnance objects, inbound torpedo, spoofing | P3, P6 | A shot has a legible EHD; an inbound weapon is a loop |
| **P8** | Endurance | Heat, watch bill/fatigue/morale, consumables, 9 environment types, maintenance windows | P4, P6 | The six-hour endurance win is an endurance *loop*; environments wear the ship down |
| **P9** | Shipyard & loadout | Hull catalog, hardpoints/arcs, modules/power, refit & field-mod, identity | P3, P8 | Two crews fit different hulls and get measurably different watches |
| **P10** | Content & release | Barriers, small craft, prize/boarding, trade, reputation, polish | P9 | Two full missions playable end-to-end without GM hand-holding |

## Dependency graph

```
P0 Stabilise
  └─ P1 Rules foundation
       └─ P2 Crew & command
            ├─ P3 Survivability ──┐
            └─ P4 Transit ────────┤
                 ├─ P5 FTL ───────┼─ P6 The hunt ──┐
                 │                │                 ├─ P8 Endurance ─┐
                 └────────────────┴─ P7 Threat ─────┘                │
                                                                     ├─ P9 Shipyard ── P10 Content
                                                                     └──────────────────┘
```

P3 and P4 parallelise after P2. P5 can start as soon as P4 lands. P6 needs
P4+P5. P7 needs P3 and benefits from P6. P8 can overlap P7. P9 needs the
component/fuel/module model (P3, P4, P8) before a shipyard can mean anything.

---

## Phase 0 — Stabilise

**Objective:** a trustworthy baseline before any new mechanic.

**Status: done.** Seven stale tests re-encoded to the blind-tagging / evidence /
grav-scan-cooldown behaviour; ship-art data file, resolver, `audit_ship_art()`
and contact sheet; comms IFF + intercept added to the bundle; plans index in the
README; phase gate recorded below. (`python -m pytest` green.)

- **P0.1** Fix the ~7 red tests in `tests/test_engine.py` / `tests/test_bridge_fun.py`
  left by the concurrent classification/gravidar refactor (claim/confirm,
  `build_spectrum`, `listen_waveform`, `_gravidar_pass`). Decide and encode the
  intended behaviour; do not paper over it.
- **P0.2** Close out in-flight specs: audit each of the four implemented plans
  against code and finish the trailing items — notably `SHIP_ART_MAPPING_PLAN`
  (`resources/bridge_ship_art.json`, central resolver, audit command, contact
  sheet) and any COMMS/SENSORS UI gaps.
- **P0.3** Add a **docs index** in `bridge/README.md` linking every
  plan and marking status; add this roadmap as the sequencing source.
- **P0.4** Establish the phase gate: a checklist (tests green, determinism test,
  persistence round-trip, admin parity, README updated) that every later phase
  must pass.

**Exit:** `python -m pytest` green; art audit passes; plans indexed and labelled.

## Phase 1 — Rules foundation (`WCRPG_INTEGRATION_PLAN` §1)

**Objective:** the deterministic Check layer, with no gameplay change.

**Status: done.** `shared/checks.py` (`roll_d20`, `resolve_check`, `check`,
natural-20/1 crits, hard DC ladder), `resources/bridge_skills.json` (13
categories, seat maps, difficulties), `CheckResult` wire model, tests including
manual-vs-step advance equivalence. Checks resolve on a **d20** (roll + skill
modifier vs a hard DC), not the book's d%. Not yet wired to actions — that is P2.

- **P1.1** `bridge/shared/checks.py`: `roll_d20(state, salt)`,
  `resolve_check(modifier, dc, roll)` with natural-20 / natural-1 crits and
  `skill_modifier(score)` mapping the 0-99 rating to a d20 bonus.
- **P1.2** `CheckResult` wire model; `resources/bridge_skills.json` (skills,
  categories, hard DC ladder, crew ratings).
- **P1.3** Tests: success boundary, degree maths, natural-20/1 crits, hard-DC
  guard, modifier mapping, same-minute determinism, 1x/4x/manual equivalence,
  and that no existing behaviour changes.

**Exit:** suite green, no state diff for identical simulated time.

## Phase 2 — Crew & command (`WCRPG_INTEGRATION_PLAN` §2–3)

**Objective:** stations have skills; committing actions roll against them.

**Status: done.** `SeatSkills` on every seat (missing skills fall back to the
crew average), Checks wired into `sensor:claim`, `sensor:activeSweep`,
`nav:gravScan`, `comms:iff` and `dc:inspect`, the roll shown in the watch bar,
and GM authoring via `admin.skills` (merging, clamped) with a console editor.
`dc:inspect` stays a whole-ship readiness repair until the system model lands in
P3, when it becomes `dc:repair {system}`.

- **P2.1** `SeatSkills` (Technology/Communications/Astrogation/Targeting/
  DamageControl/Defenses/Strategy/Leadership + specializations); default
  "crew average" for solo play.
- **P2.2** Wire Checks into `sensor:claim`, `sensor:activeSweep`/`nav:gravScan`,
  `comms:iff`; `dc:inspect` → `dc:repair {system}`.
- **P2.3** UI: show `ROLL 43 ≤ DC 55 — SUCCESS (deg 12)` and crits; keep the
  "evidence, not truth" rule for tags.
- **P2.4** Admin: edit crew skills per seat.

**Exit:** a player can crit a tag; the log explains every roll; GM can tune.

## Phase 3 — Survivability (`WCRPG_INTEGRATION_PLAN` §4–5;
`ENVIRONMENTS_AND_MAINTENANCE_PLAN` — wear & repair)

**Objective:** the ship becomes a set of systems that can be hurt *and wear out*.

**Status: done except P3.8 (deferred to P8).** P3a: per-arc shields fitted from
the ships DB, the Three/Two/One **alert ladder** (raise = shields to full + 1
fuel point; One arms the mounts; `prep_weapons` brings the ship to One), **shield
regen** every ten minutes (+ Defenses modifier, step-size independent), **Refocus
Shields**, and the handoff pack carrying alert/core/shields/systems. P3b:
`apply_damage` (shields → armour → core, then a d10 system-table strike with
escalating core damage on dead systems), **malfunction gates** (engines hold
station, radar refuses the active fit, comms silence, guns refuse solutions,
shields refuse raising), `dc:repair` + **jury-rig** (fails again under fire),
`dc:maintain` (strips wear), and per-system **wear** accrual with malfunction
risk. P3.8 repair-in-hazard waits for the environment model in P8.

- **P3.1** Shields per defence arc (`fore/aft/port/starboard`), SHP/AHP, regen
  (10% + Defenses / 10 rounds), **Refocus Shields** (two consecutive Checks;
  a critical failure damages the shield system).
- **P3.2** **Alert ladder** Three/Two/One: shields up/weapons armed costs a fuel
  point and instantly charges weapons; attacks require Condition One.
- **P3.3** `ShipState.systems` health + malfunction; the d10 system table
  (radar −25 HD / no lock ordnance, comms disables hails and flips FOF
  missiles, engines stop movement, life-support defers to hazards).
- **P3.4** Damage control: mitigate `degree ÷ 10` %, malfunction DC
  `100 + DamageControl − damage`, **jury-rig** auto-fails on new hits; armour
  and core unrecoverable in a watch; **excessive damage** +10/+10.
- **P3.5** Handoff pack carries arcs, shield state, system health, alert.
- **P3.6** UI: DC panel (system list, repair/jury-rig, cooldowns); arcs on the
  ship widget.
- **P3.7** **Wear vs damage**: per-system `wear 0–100` that never auto-heals,
  accruing from environment severity, speed, heat and combat stress; wear
  thresholds give Check penalties and raise malfunction chance. `dc:maintain`
  (scheduled upkeep, consumes spares and a window) vs `dc:repair` (fixes
  damage).
- **P3.8** **Repair in a hazardous environment**: environment `repairDcPenalty`,
  EVA risk (collision/exposure/cold), **contaminated faults** that recur until
  cleaned, and **field patches** that auto-fail on new damage. Ops can hold a
  **lee** position to reduce work DCs at a fuel/time cost.

**Exit:** a watch can take system damage, repair some of it, and arrive worn
from an environment it was not meant to linger in; the handoff tells the table
exactly what is broken and what is worn.

## Phase 4 — Transit operations (`TRANSIT_AND_ENDURANCE_PLAN` §1, §3, §5)

**Objective:** moving anywhere costs something and has a deadline.

**Status: done (P4.1–P4.5).** Fuel capacity now comes from the
ships DB (`fuel`), and burn reflects speed, alert condition, the active radar and
terrain; the derived picture (`fuelBurnPerHour`, `fuelRangeKlik`, `bingoFuel`,
`bingo`, `deadDrift`) refreshes every step. Ops draws a **fuel range ring**; the
watch bar shows fuel/range/bingo; empty tanks mean **dead-drift** (no movement)
and bingo logs once on transition. **ETA/CPA**: every track carries
`sensor.cpaKlik`, `cpaMinutes` and `etaMinutes` (time to the 40-klik ring),
surfaced in a new **Intercept Clock** panel. **Astrometrics**:
`resources/bridge_nav_points.json` charts nav/jump/body points per campaign, each
leg is scored for **time, fuel and exposure** with a risk flag (clear / stale
charts / hazard / contact), and Ops can `nav:plot`, `nav:commit` (an **Astrogation
Check** sets on-axis vs offset arrival; a critical failure is a **gravity-well
incident**) and Sensors can `nav:survey` to refresh a stale chart. Heat and the
watch bill remain with P8.

- **P4.1** Fuel pool + capacity (hull/module), burn from speed/mode, alert
  state, sensors/ECM, hazards (terrain ladder), and jump charge.
- **P4.2** Ops **fuel range ring**; bingo-fuel warning; **dead-drift** as a
  graded failure (no evasion, cannot reposition; outs are tanker, ramscoop,
  abandon leg).
- **P4.3** **ETA/CPA intercept clock**: time-to-range per track, crossing times;
  surfaced in the watch bar.
- **P4.4** Astrometrics: `jumpPoints[]`/`navPoints[]` map data; candidate legs
  show **time / fuel / exposure**; chart-age flags; Astrogation Check at commit
  sets arrival precision (offset arrival, not a crash).
- **P4.5** Data: `CampaignSeed.navPoints`, `resources/bridge_nav_*.json`;
  protocol `nav:plot`.

**Exit:** a leg is a decision with a visible cost; waiting is never free.

## Phase 5 — FTL & navigation (`TRANSIT_AND_ENDURANCE_PLAN` §2;
`SUBMARINE_INSPIRATION_PLAN` §6, §8)

**Objective:** jumps are a contested, failure-graded loop.

**Status: P5.1–P5.3, P5.7 done; P5.4–P5.6 pending.** Jump points carry a type
(stable/pirate), an open/close window, a required alignment and interference
(from the point and active hazards). `jump:spool` charges the drive for a fuel
point and a large emission spike, then **alignment** accrues every step from
position, heading and closing-velocity quality times the ops Astrogation skill,
capped at 1 — while the ship is **blind** (radar off-line), **slow** (speed
clamped) and **loud** (`selfNoise` up). `jump:commit` is a clean jump at or above
the requirement (transit to `dest`, or extraction ends the watch), a **misjump**
between the floor and the requirement (off-axis arrival, +45 min, core damage),
or a **refusal** below the floor; `jump:abort` loses the charge. **P5b** adds
the **drive table** (`resources/bridge_drives.json`: Standard / Morvan / Akwende
vary spool rate, fuel cost and misjump floor; GM via `admin.setDrive`), **nav
uncertainty** (dead-reckoning error accrues under way, stretches plotted ETAs and
degrades jump alignment; `nav:fix` star/landmark/ping works it off, the ping
costing exposure), and the **comms window** (a periodic relay window; long-range
`open` traffic is refused outside it while short-range directional modes still
work). The plan's *depth band* half of P5.6 has no analogue in a space setting
and defers to the P6 submarine work.

- **P5.1** Jump points: position, radius, alignment tolerances, open/close
  window; pirate points tighter/riskier.
- **P5.2** `alignmentQuality` accrual on the weapons-solution pattern; spool
  cost (fuel, power, heat, emission spike); **spooling is blind, slow and
  loud**.
- **P5.3** Commit/abort; **misjump** below threshold (wrong arrival, time/fuel
  loss, damage); interference raises the required quality.
- **P5.4** Drives (D/Morvan/Akwende) and engine-class efficiency table.
- **P5.5** **Nav uncertainty**: DR error accrues; a fix (star sighting,
  landmark, risky surfacing) resets it; unfixed error perturbs plotted ETA and
  jump alignment.
- **P5.6** **Comms windows**: transmitting requires a shallow depth band and an
  exposed window; orders/intel may only arrive there.
- **P5.7** Protocol `jump:spool|commit|abort`, `nav:depth`; UI alignment widget.

**Exit:** a jump can be won, aborted, or botched; the campaign has a travel loop.

## Phase 6 — The hunt (`SUBMARINE_INSPIRATION_PLAN` §1–5; flagship)

**Objective:** detection becomes a search you can break, not a scalar.

**Status: P6.1, P6.3, P6.5, P6.7 (partly) done; P6.2, P6.4, P6.6 pending.** A
hostile crossing a `DATUM_LOCK_THRESHOLD` track (or the crew's own high-power
ping) places a **datum** at the ship's last known position; the datum's box
widens and its strength fades with age, a fresh detection **re-centers** it, and
when it ages out the hunt **breaks** and the log says so. Hunters searching
inside a datum get a lock bonus. **Sprint/drift** (`ops:posture`) sets speed and
mode and scales both the hunter's signal and the lock's decay; drift also
accelerates datum decay. **Baffles**: the aft arc crushes passive returns until
`sensor:clearBaffles` buys a window at the cost of noise. The **endurance win now
requires no active datum**, so staying dark is not enough — you must break the
hunt. **P6b** adds **signature layers** (`resources/bridge_layers.json`: four
altitude bands; detection across a boundary is cut to 25%, crossing costs noise
and briefly blinds your own array), **TMA manoeuvre-to-solve** (`ops:tma`: fly a
deliberate course change, log bearings, and a leg that generates enough turn and
bearing rate solves a passive range — a careless leg inside a datum re-centers
it), and **hunter behaviour** (hostiles prosecute a lock and otherwise search the
nearest active datum, turning at a limited rate).

- **P6.1** **Datum**: placement on detection, radius/strength/age, search tracks
  converging, **decay under quiet**, re-centering on new noise; `GameState.datums[]`.
- **P6.2** **Signature layers**: altitude bands with sensor modifiers; crossing
  hides from one side, blinds the crosser, costs time/noise; correct layer
  depends on who is hunting whom.
- **P6.3** **Sprint-and-drift** posture with an acoustic budget; detection
  accumulates on the sprint, decays in the drift.
- **P6.4** **TMA manoeuvre-to-solve**: a deliberate course-change leg generates
  bearing rate and a range/quality jump; a careless leg inside a datum
  re-centers it (extends `_refresh_estimate`).
- **P6.5** **Baffles**: aft blind arc; a clearing turn costs time/noise.
- **P6.6** Enemy behaviour: hunters search datums, clear baffles, and prosecute;
  integrate with the existing lock/loss race and the endurance victory.
- **P6.7** UI: datum ring + search tracks on the sensors plot; layer bands and
  TMA leg on ops; the "break the datum / keep the mission" Command call.

**Exit:** a detected ship can escape by skill, not by dice; the endurance
victory depends on it.

## Phase 7 — Threat & weapons (`WCRPG_INTEGRATION_PLAN` §6–7;
`SUBMARINE_INSPIRATION_PLAN` §10)

**Objective:** the shooting problem becomes legible and two-sided.

**Status: done (P7.1–P7.5).** `shared/ehd.py` derives a hull's
HD from its own profile/stealth and assembles **EHD = HD + evasive + range
penalty − Tactical − solution bonus** (five-klik increments, per-kind falloff:
gun 2, missile 3, torpedo 5), exposed part-by-part in the handoff and live on
`ship.weaponEhd` as soon as a solution is prepped. **Manoeuvres** (`ops:maneuver`)
— jink, slip 90/180, snap turn, break — buy evasive bonus at a gunnery penalty
that feeds straight back into our own EHD, with a Starship Piloting Check for
the turns (a botched slip halves the bonus and doesn't turn; a critical failure
gets nothing), and the posture drops on the next helm order. Remaining:
**P7b** adds **subsystem targeting** (`weapons:targetSystem`: a Targeting Check
vs the target's HD decides whether the strike lands on the named system; damage
that reaches a system is scaled by the target's defence state — shields ÷100,
armour ÷10, bare hull full), **ordnance in flight** (`GameState.ordnance`:
torpedoes and missiles fly, are detected, can be shot down, decoyed by a
noisemaker, lost in terrain, or run out of fuel before they detonate on the
hull), and **countermeasure spoofing** (`sensor:spoof`: a Ballistics Check
spends a pod for a decoy that can make a weapon that beat the EHD miss).

- **P7.1** **EHD** in the handoff: `target HD − (our Tactical − their Evasive) −
  range`, per-scale range penalties; full success adds hits per 5 points of
  degree.
- **P7.2** **Manoeuvre orders**: jink (−10 HD / −10 gunnery, first action), snap
  turn, slips/90s/180s with Checks, canonical compositions; stacking CM/EM until
  next turn.
- **P7.3** **Subsystem targeting**: Targeting Check vs HD; damage converted by
  defence state (shields ÷100, armour ÷10, none full).
- **P7.4** **Ordnance as objects**: torpedoes as Size-Class-1 tracks that can be
  shot down; **torpedo-in-the-water** loop (track, decoy, evade, terrain).
- **P7.5** **Countermeasure spoofing**: failed-Ballistics-that-beat-EHD,
  +5/+10 per pod, resolved on a d20 Check.
- **P7.6** UI: arc/shield selection and EHD readout in the weapons/handoff view.

**Exit:** a manoeuvre changes the shot; an inbound weapon is a playable loop.

## Phase 8 — Endurance (`TRANSIT_AND_ENDURANCE_PLAN` §4, §6;
`SUBMARINE_INSPIRATION_PLAN` §9; `HAZARDS_AND_REALTIME_PLAN`;
`ENVIRONMENTS_AND_MAINTENANCE_PLAN`)

**Objective:** the long watch is the game, and the environment is the clock.

**Status: done (P8.1–P8.6).** **Heat** is now capability, not
exposure: the reactor, the active radar, action stations, armed mounts and a
jump spool all add load, and the captain chooses **normal / vent / bottle** —
venting dumps heat fast and visibly, bottling is quiet but lets heat climb, and
at the cap the plant vents itself. Heat past 70 costs up to −4 on every station
Check, and bottling also cuts self-noise. **The watch bill** (standard / battle /
rest) drives **fatigue**, which past 40 costs Checks; a hard hit leaves the crew
**shaken** (−2 until Command rallies them with an Inspire Check), and a crew
under 90% is **undermanned** (−1). All of it is folded into `station_check`, so
running hot, tired and shaken degrades everything. **P8b** adds the **nine-environment catalog**
(`resources/bridge_environments.json` — clear space, asteroid belt, nebula, ice
field, dust field, debris field, radiation storm, ion storm, gravity well), each
bending sensors, own emission, fuel burn, comms, wear, repair difficulty,
contamination and EVA risk at once, with **hazards resolved into environments by
window** (one model, not two). **Consumables** (spares, provisions, ordnance
loadout) run down and can be **replenished at a depot** (`nav:replenish`);
repairs consume spares and get harder without them; a contaminating environment
fouls the repair until `dc:maintain` cleans it; and a debris field allows
**salvage** (`dc:salvage`) at EVA risk — which is also where P3.8's
repair-in-hazard lands.

- **P8.1** **Heat**: budget from active sensors/shields/weapons/ECM/jump;
  **vent** (fast, loud) vs **bottle** (quiet, degraded); the missing EW
  scarcity.
- **P8.2** **Watch bill**: 6-on/12-off rotation, fatigue degrades Checks,
  casualties, and morale (Shaken); Rally/Inspire and the Undermanned penalty.
- **P8.3** **Consumables**: torpedoes, spares, provisions; replenishment
  rendezvous.
- **P8.4** **Environment catalog** (`resources/bridge_environments.json`): nine
  types — clear space, asteroid belt, nebula, ice field, dust field, debris
  field, radiation storm, ion storm, gravity well — each with sensor, emission,
  nav/fuel, comms, systems-stress and maintenance values. Hazards become
  environments with a time window (one model, not two).
- **P8.5** UI: environment/heat panel; crew/rotation panel; endurance progress
  in the Command objective readout; environment forecast and severity in the
  watch bar.
- **P8.6** **Maintenance windows, spares and salvage**: schedule upkeep during
  quiet stretches; spares consumed by repair and replenished from salvage in
  debris fields (EVA risk); contaminated faults (dust filters, ice seals,
  ionized boards) recur until cleaned.

**Exit:** the six-hour-dark victory is a managed endurance feat, and a patrol
can be lost to wear and contamination rather than to enemy fire.

## Phase 9 — Shipyard & loadout (`SHIP_CUSTOMIZATION_PLAN`)

**Objective:** the crew flies a ship they chose and fitted.

**Status: done (P9.1–P9.6).** `resources/bridge_hulls.json` curates **15 hulls**
(the 11 the bridge flew plus Bengal, Bristol, Raptor and Broadsword), each
carrying **arc-coded hardpoints** derived from the DB turret list and a weapon
kind per mount; `resources/bridge_modules.json` adds five accessories fitted
against **power, mass and cargo budgets**. `prep_weapons` now refuses a shot when
**no mount of the right kind bears on the target** — a fore gun cannot shoot
astern — and the handoff carries hull id, livery, modules and the fitted loadout
so component damage and identity travel with it. The GM's live hull change
re-equips the mounts. UI: a Command **SHIPYARD** card listing hardpoints, arcs
and fitted weapons with FIT/STRIP controls.

- **P9.1** **Hull catalog** (`resources/bridge_hulls.json`) curated from
  `ship_types` — Bengal, Bristol, Venture, Fralthi, Ralatha, Kamekh, variants
  and the rest — carrying craft type, size class, agility, per-arc armour, body,
  shields/refresh, component map, hardpoints, gunners, cargo, fuel, role, art.
- **P9.2** **Hardpoint loadout**: assign weapon tags from `ship_weapons_link` /
  `weapons` to the hull's arc-coded hardpoints; honour arc coverage, magazine,
  `MaxGunners`, `ShieldByPass`, `LockTime`, `Spoofability`.
- **P9.3** **Modules, power and sensors**: WCRPG accessories over the component
  map; power/mass/cargo budgets; a module that is fitted can be hit.
- **P9.4** **Refit loop**: shipyard between missions (time/credits/resources),
  blueprints, and the **field-modification loop** (hot-swap, jury-rig,
  cannibalise salvage) during a watch.
- **P9.5** **Identity & handoff**: name, registry, livery/heraldry reach the
  plot, the station UI and the handoff pack; component damage travels with it.
- **P9.6** UI: GM shipyard (hull browser, hardpoint/arc diagram, budget meters,
  blueprints) and a crew loadout card on Weapons/Command.

**Exit:** two crews can pick and fit different hulls and get measurably different
watches and handoffs.

## Phase 10 — Content & release

**Objective:** a self-contained playable product.

**Status: done (P10.1–P10.6), with the manual QA exit noted below.** **Picket
barriers** (`resources/bridge_barriers.json`) are segment features: crossing one
is a *detection event* that places a datum and alerts the watch, and a hull
running quiet can slip a thin line. **Hangar ops** launch and recover a small
craft, opening a vulnerable window on the parent. **Prize/boarding** puts a party
aboard a derelict for spares — or takes casualties. **Career** adds XP, standing
and medals, awarded on outcomes and jumps and carried in the logbook digest
(shown on the watch-ended screen). **Mission integration**
(`shared/missions.py`) maps a CombatBot mission's nav points onto the bridge
chart deterministically, so a mission can open as a bridge watch. Release docs:
`CREDITS.md` records the WCRPG CC BY-NC-SA attribution and the d20 deviation.

**Not certified here:** the phase's manual exit — "two full missions play
start-to-finish with no GM hand-holding and a correct handoff at any pause" — is
a human play-through. The unit and live checks cover each loop in isolation; a
full two-mission QA pass remains to be played.

- **P10.1** **Barriers/pickets** (SOSUS analog) as map features.
- **P10.2** **Hangar/small-craft ops** (launch/recover window; parent vulnerable).
- **P10.3** **Prize/boarding/rescue** loop.
- **P10.4** **Trade/economy** between missions; **reputation/medals/XP** into the
  digest.
- **P10.5** **Mission-generator integration** so a CombatBot mission can open as
  a bridge watch and hand back.
- **P10.6** Release polish: balance pass, GM console parity, performance,
  keyboard/accessibility, docs, credits/licensing page.

**Exit:** two full missions play start-to-finish with no GM hand-holding and a
correct handoff at any pause.

---

## Cross-cutting workstreams

- **Determinism & persistence.** Every phase adds a schema-version bump and a
  round-trip test; keep 1x/4x/manual equivalence tested.
- **Protocol & frontend compatibility.** New fields default safely; the
  hand-maintained bundle is updated in the same phase as the wire change, and
  the `focusInContent`/carousel render guards stay intact.
- **UI pattern.** Each loop gets one owning panel plus one alert in the watch
  bar. Prefer visible rings/bars/countdowns over hidden modifiers.
- **GM console.** Each phase exposes its new knobs (skills, modules, DCs,
  hazards, nav data, crew).
- **Testing.** Unit + determinism + integration; no phase ships with red tests.
- **Docs & licensing.** Update README and the phase plan; keep the WCRPG/TEOC
  and submarine-reference credits current.

## Milestones

- **M1 — Rules & Crew** (P0–P2): green suite, Checks, skills, first rolls.
- **M2 — A Ship That Can Be Hurt** (P3): shields, systems, damage control.
- **M3 — A Place to Go** (P4–P5): fuel, ETA, astrometrics, jumps.
- **M4 — The Hunt** (P6): datum, layers, TMA — the identity release.
- **M5 — The Long Watch** (P7–P8): EHD, ordnance, heat, crew, environments.
- **M6 — This Is Our Ship** (P9): hull catalog, loadout, refit, identity.
- **M7 — Content Complete** (P10): barriers, small craft, boarding, economy.

## Risks

| Risk | Mitigation |
|---|---|
| Scope: this is a wargame's worth of mechanics | Strict phase gates; phases 0–6 are the product; 7–10 are enrichment |
| Balance collapse as loops stack | One scarcity per phase; a "no dominant option" review at each gate |
| Determinism broken by new rolls | Hash-only rolls, per-action salts, determinism tests in CI |
| Frontend churn / concurrent writers | Small phases, wire fields additive, screenshot check per UI change |
| Player overwhelm (four stations × many loops) | One owning panel per loop; alerts only when urgent |
| Solo play stalls | Default crew averages; all Checks succeed-or-degrade, never hard-block |
| Licensing | Mechanics only, re-authored tables, credits, non-commercial |

## Out of scope

Character-scale melee and Ch 12.3 character hazards; full vector movement;
real sonar propagation; a deep trading economy inside the bridge; anything that
breaks pause-and-handoff.

## Working agreement

Treat this as the index; the nine plans stay the source of truth for detail.
When a phase lands, update its row in **Current state**, tick its exit criteria,
and fold any deviation into the relevant plan rather than here.
