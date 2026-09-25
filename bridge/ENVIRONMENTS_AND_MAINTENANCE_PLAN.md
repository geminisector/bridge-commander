# Environments and Maintenance Plan

## Why

The bridge has *terrain* (five environmental contact types) and *hazards* (a
time-windowed noise/exposure/concealment modifier), but no notion of an
**environment** as a place that changes how the ship fights *and wears out*.
This plan does two things the other plans assume but never define:

1. A proper **environment catalog** — at least seven types, each with a distinct
   mechanical signature across sensors, emissions, navigation, comms, systems
   and upkeep.
2. A **maintenance and repair loop**, especially for work done *inside* a
   hazardous environment, where you cannot simply stop and fix things.

It extends `HAZARDS_AND_REALTIME_PLAN.md`, and feeds
`WCRPG_INTEGRATION_PLAN.md` (system damage, Damage Control) and
`ROADMAP.md` phases 3 and 8.

## Design intent

- An environment is a **place with a cost**, not just a sensor filter. Entering
  one should change what you can see, what can see you, how you move, how you
  talk, and what it costs to keep the ship running.
- **Damage and wear are different.** Damage is instant (hits, collisions);
  wear is gradual and deferred. Repair fixes damage; **maintenance prevents
  wear failures**. A crew that never maintains wins the fight and loses the
  patrol.
- Hazardous environments should make **repair itself hazardous**, so "stop and
  fix it" is a real command decision, not a free action.

## Environment model

Data in `resources/bridge_environments.json`; types already in code
(`ENVIRONMENTAL_TYPES`, `OBSTACLE_EFFECTS`, `TERRAIN_IMAGES`) become the visual
and obstacle layer of the same catalog.

```
Environment:
  id, name, class: background | field | cloud | anomaly | artificial
  sensor:      passiveNoise, activeReturn, bearingSigmaDeg, rangeErrorFactor,
               falseReturnChance, gravSaturated
  emission:    ownSignatureMul, concealment, hotContrast   # >1 exaggerates hot vs cold
  nav:         difficultyRank (WCRPG ladder), speedCapKps,
               collisionChancePerHour, collisionDamage
  fuel:        burnMul
  comms:       reliability, delayFactor, blackoutChance
  systems:     shieldDrainPerHour, heatPerHour, electronicsDamagePerHour,
               driveStressPerHour
  maintenance: wearPerHour, repairDcPenalty, evaRisk, sparesDrainPerHour
  detect:      sensorRangeMul            # how far *others* see into it
  mitigation:  [named crew actions]
  warning:     [signs shown before entry]
```

## The environments (nine)

| # | Environment | Class | Signature effect | Chief risk |
|---|---|---|---|---|
| 1 | **Clear space** | background | baseline; long sensor ranges | none — the reference point |
| 2 | **Asteroid belt / dense field** | field | LOS shadows, false returns, gravidar saturation | collision + hull abrasion |
| 3 | **Nebula / ionized gas cloud** | cloud | EM absorption, bearing scatter, own-emission masking | shields drained, electronics |
| 4 | **Ice field / cryo shoal** | field | mirror/refraction ghost returns | false contacts, hull cold-stress |
| 5 | **Dust field / thermal front** | cloud | masks cold hulls, exaggerates hot ones | filters clog → heat rises |
| 6 | **Debris field / wreck line** | field | dense false returns, LOS chop | collision + salvage temptation |
| 7 | **Radiation storm / solar particle event** | anomaly | floods sensors, kills long-range ID | electronics + crew exposure |
| 8 | **Ion storm / EM interference zone** | anomaly | comms dead zone, nav error | blind and mute at once |
| 9 | **Gravity well / neutron-star vicinity** | anomaly | extreme nav difficulty, tidal stress | misjump, fuel, structural |

Two optional artificial ones for later scenarios: **minefield** (deliberate
collision risk + detection tripwires) and **atmospheric skim** (drag, heat,
comms blackout, aerobraking fuel savings).

### 1. Clear space
Baseline. Long passive/active ranges, no wear, no collision, comms nominal.
Everything else is described by how it departs from here.

### 2. Asteroid belt / dense field
- **Sensors:** heavy LOS shadow (block ~0.9), moderate scatter, some reflect;
  gravidar saturates into a smear.
- **Emissions:** excellent concealment if you sit still; running fast lights you.
- **Nav:** WCRPG **Difficult** (packed: **Very Difficult**); speed cap; piloting
  Check with the size class subtracted on each move action.
- **Damage:** collision = `10 × (5 + 1d5) × current speed × 1d10`.
- **Maintenance:** hull abrasion wear; sensor-window pitting; **EVA is
  dangerous** (moving rock, tether risk).
- **Mitigation:** slow down, follow the cleared lane, use a rock as a shield,
  mine a chokepoint.
- **Opportunity:** cover from a datum `(SUBMARINE_INSPIRATION_PLAN)`; salvage.

### 3. Nebula / ionized gas cloud
- **Sensors:** passive noise up, bearing scatter, active radar more valuable but
  more conspicuous; catalogue confidence slow to build.
- **Emissions:** **concealment for the quiet, not the loud** — conceals a dark
  hull best; a burning drive is a beacon.
- **Nav / systems:** drive ionization stress (wear + occasional sputter),
  **shield drain** (canon: nebula costs −500 SHP, WCRPG PDF 390).
- **Maintenance:** electronics carbon-tracking; shield emitters need servicing;
  repair DC penalty from ionization.
- **Comms:** degraded, delayed acknowledgements; relay/beacon discipline matters.
- **Mitigation:** run dark, stow the active fit, accept the shield drain or
  route around.

### 4. Ice field / cryo shoal
- **Sensors:** high **reflect** (0.95) — mirror-image ghost returns and
  multipath; the honest picture is the waveform, not the mass.
- **Emissions:** cold bodies reflect; a warm hull stands out against ice.
- **Nav:** Difficult; refraction makes range/bearing lie.
- **Damage:** ice strike plus **cold-stress** on hull and seals (wear, slow leak
  risk).
- **Maintenance:** seals and thermal systems; **ice is a water/coolant source**
  (opportunity: replenish, patch, cool an overheating plant).
- **Mitigation:** reduce speed, cross on a known bearing, use the reflection to
  bait a hunter.

### 5. Dust field / thermal front
- **Sensors:** high scatter, low reflect; **hotContrast > 1** — masks cold
  contacts while exaggerating hot drives (the classic thermal-layer inversion).
- **Nav:** moderate difficulty; fine particulates.
- **Systems / maintenance:** **filter clogging** — a recurring maintenance tax:
  heat rises, weapons recharge slows, sensors degrade; needs filter service or
  an EVA swap.
- **Comms:** attenuation with distance.
- **Mitigation:** sprint-and-drift (dust hides the drift best), schedule filter
  service, avoid opening the hangar.

### 6. Debris field / wreck line
- **Sensors:** dense false returns and LOS chopping; classification is hard.
- **Damage:** collision on the asteroid formula at reduced severity, but *many*
  small hits → high wear.
- **Maintenance:** **salvage opportunity** — spare parts and modules, at EVA
  risk and time cost; a reason to stop in a dangerous place.
- **Mitigation:** slow, shield forward arc toward the field, do not fight in it.

### 7. Radiation storm / solar particle event
- **Sensors:** floods the passive band; long-range ID collapses; low-band
  barcodes wash out.
- **Systems:** electronics damage accrues (radar, comms), reactor runs hotter,
  shields leak.
- **Crew:** exposure — the watch-bill loop must rotate people out; unshielded
  EVA is prohibited.
- **Maintenance:** repairs need shielding or a storm lull; spares for burned
  boards are precious.
- **Mitigation:** point the armoured aspect at the source, button up, ride it
  out at reduced capability.

### 8. Ion storm / EM interference zone
- **Comms:** the **dead zone** — transmission unreliable, delays, possible full
  blackout; a relay or courier may be the only way to talk.
- **Nav:** astrogation error inflates (feeds `navError`); inertial fixes drift.
- **Sensors:** intermittent ghosts; active radar degrades too.
- **Mitigation:** accept autonomy (Command must decide without flag orders),
  pre-plot the course, use tight-beam line-of-sight only.

### 9. Gravity well / neutron-star vicinity
- **Nav:** WCRPG ladder **Extremely Difficult** (neutron star) to **Impossible**
  (black-hole horizon); tidal stress on the hull; jump alignment distorted.
- **Fuel:** holding station or climbing out burns fuel fast.
- **Systems:** structural wear, shield drain, drive stress.
- **Maintenance:** **repair is nearly impossible while manoeuvring**; only a
  stable orbit lets the crew work.
- **Mitigation:** use the well for a slingshot (free velocity, `navError` cost),
  or a pirate jump point (tight alignment, high reward).

## Maintenance and repair

### Wear vs damage

- **Damage** — discrete, from hits/collisions: reduces a system's `health`,
  can **malfunction** it. Fixed by `dc:repair`.
- **Wear** — continuous, from time in an environment plus how hard the ship is
  run: a per-system `wear 0–100` that never auto-heals. At thresholds it gives
  Check penalties and raises malfunction chance. Addressed by `dc:maintain`
  (scheduled upkeep), not by repair.

Accrual (indicative, tunable):

```
wearPerHour(system) = ENV.wearPerHour(system)
                    × (1 + speed/100)
                    × (1 + heat/100)
                    × (combat ? 1.5 : 1)
```

A ship that sprints through dust and fights in an asteroid belt arrives with
worn sensors and clogged filters **before** it takes a single hit — which is
the point.

### Maintenance loop

1. **Read** — per-system wear bars, upcoming environment forecast, spares count.
2. **Decide** — service now (time, crew, spares, exposure) or defer (risk of a
   fault at the worst moment).
3. **Pay** — maintenance needs a **window**: steady course/depth, hangar or EVA,
   a quiet stretch, and it competes with rest (crew fatigue).
4. **Feedback** — wear resets, performance returns, malfunction odds drop;
   deferred wear shows as slower sensors, weaker shields, sluggish drives.
5. **Deadline** — the next hazard window, the enemy ETA, the jump window, or the
   consumables clock. There is never a "good" time.
6. **Failure (graded)** — wear → fault → malfunction → cascade (heat → reactor →
   battery brownout → sensors blind). A **botched repair in a hazard makes it
   worse**, not merely "fails".

### Repair in a hazardous environment

Standard repair assumes a stopped, safe ship. In an environment it does not:

| Condition | Effect on the work |
|---|---|
| Environment severity | repair/malfunction DC penalty from `repairDcPenalty` |
| Ship manoeuvring | larger penalty; some work impossible under thrust |
| EVA required | `evaRisk`: collision (asteroid/debris), exposure (radiation), cold (ice), tether loss |
| Contamination | dust filters, ice seals, nebula ionization: the same fault recurs until cleaned |
| Time pressure | a temporary **jury-rig** restores function now and re-fails on the next damage |
| Spares | field repairs consume `spares`; salvage/debris fields can replenish |

Rules:

- **Patch vs fix.** A field patch restores function for a bounded time and
  **auto-fails again when new damage lands** (WCRPG jury-rig). A proper fix
  needs a safe window.
- **Clean before you fix.** Contaminated faults (dust filters, ice seals,
  ionized boards) recur unless the system is cleaned — an extra maintenance step.
- **Work in the lee.** Positioning matters: use a rock, an ice body, or the
  shadowed aspect to reduce environment severity while the crew works; Ops must
  hold that position, costing fuel.
- **Rotate the crew.** Radiation/hazard exposure interacts with the watch bill:
  someone must be rested to do the work, and someone must be rested afterwards.
- **Call it.** Command's decision is *stop and fix* (time, exposure, drift) vs
  *push on worn* (risk of cascade at contact) vs *abandon the leg*.

### Station ownership

- **DC/Engineering** owns wear, repair, spares and the work itself.
- **Ops** owns the maintenance window: holding station, plotting the lee, and
  the time it costs; fuel for station-keeping.
- **Sensors** loses picture while the ship is buttoned up or an EVA is outside;
  the environment is also their problem to forecast.
- **Command** owns "stop or push on", and the risk of being caught mid-repair.

## Data, protocol, UI

- `ShipState`: per-system `wear` and `spares`; extend `dc:repair` with
  `dc:maintain {system}` and `dc:patch {system}`; `maintenanceWindow` state.
- `GameState`/`CampaignSeed`: `environments[]` regions (position, radius, type,
  intensity, drift) and an `environmentForecast`; hazard and terrain contacts
  read from the same catalog.
- `resources/bridge_environments.json`: the catalog above; **at least the nine
  types**, with `class`, combat values and maintenance values.
- UI: DC panel gains wear bars, spares, patch/maintain buttons and "work
  conditions" (DC penalty, EVA risk, contamination); Ops gains lee/station-
  keeping; the watch bar shows the environment and its severity.

## Integration

- **Hazards** — hazard instances are just environments with a time window; keep
  one model, not two.
- **WCRPG system damage** — repair/malfunction DCs take the environment penalty;
  spares and modules map to the accessory list.
- **Transit/Endurance** — environments set the fuel burn multiplier and the heat
  load; maintenance competes with crew rest and consumables.
- **Submarine plans** — dust/nebula enable concealment and datum-breaking; ice
  and debris offer salvage and lee positions; radiation forces watch rotation.
- **Roadmap** — Phase 3 gains wear/repair-in-hazard; Phase 8 gains the full
  catalog, maintenance windows and spares/salvage.

## Tests

- Each environment applies its documented sensor/emission/nav/comms multipliers
  deterministically.
- Collision chance and damage match the formula; shield drain matches the
  nebula rule.
- Wear accrues at the documented rate and is not reset by repair.
- Maintenance resets wear and consumes spares; deferring raises malfunction odds.
- Contaminated faults recur until cleaned.
- Field patches re-fail on new damage; a proper fix does not.
- Environment severity raises repair DCs; EVA in asteroid/radiation/ice carries
  its documented risk.
- A **lee** position measurably reduces work DCs and costs fuel/time.
- All new state round-trips persistence and appears in the handoff pack.

## Roadmap placement

- **Phase 3** — wear, `dc:maintain`, `dc:patch`, contaminated faults, repair
  penalties (with the system-damage work).
- **Phase 8** — the nine-environment catalog, `bridge_environments.json`,
  maintenance windows, forecast, spares and salvage.

Environments are the missing *context* for everything else; maintenance is what
makes time in them cost something the crew must plan for.
