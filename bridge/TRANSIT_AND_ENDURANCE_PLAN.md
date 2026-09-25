# Transit, Endurance and Crew — Missing Game Loops

## Why this document

The bridge has plenty of *state* (exposure, readiness, battery, hull, fuel-none,
hazards, time modes). What it lacks is **loops**: recurring cycles where a
visible resource is spent, a deadline closes, a station owns the decision, and
the outcome feeds back into the sensors/EW/comms/weapons picture.

Fuel management, jump alignment and astrometrics are the biggest gaps, and all
three are really one cluster: **getting somewhere costs something, and the
enemy gets a vote.**

## Loop design rules

Any mechanic worth adding must satisfy all six:

1. **A visible, finite resource** — you can see it running out.
2. **A deadline or window** — waiting is itself a cost, not a safe default.
3. **A station that owns it** — one seat is accountable; at least two others
   are affected by it.
4. **A real decision with no dominant option** — fast/loud/cheap, not
   right/wrong.
5. **A graded failure** — losing the loop hurts and creates a new situation;
   it does not only mean "game over".
6. **Feedback into a neighbour** — the result changes sensors, EW, comms,
   weapons, hazards or the victory conditions.

If a proposed mechanic fails 1, 2 or 5, it is a stat, not a loop. (The existing
hazard system passes; `readiness` alone does not.)

## 1. Fuel management

**Resource:** `fuelCapacity` / `fuel`, in fuel points; capacity from hull +
`Fuel Tank` modules. **Owner:** Ops (Navigation). **Deadline:** every leg has an
ETA and every burn moves it.

**Loop**
1. **Read** — the ops plot draws a **fuel range ring**: "with present loadout you
   can go X klik at cruise, Y at flank, and still make the jump point."
2. **Decide** — set speed/mode and route for the next watch; choose whether to
   sprint to intercept, cruise, or drift dark.
3. **Pay** — burn scales with speed/mode, hard manoeuvres, **alert state**
   (raising shields/arming weapons costs a point), active sensors/ECM draw,
   hazard transit (the terrain-difficulty ladder), and jump charge.
4. **Feedback** — the range ring shrinks; a "bingo fuel" warning fires when the
   remaining fuel no longer covers the plotted leg + reserve.
5. **Deadline** — a scheduled rendezvous, a distress call, or the enemy's
   closing ETA. Waiting is safe for fuel and dangerous for everything else.
6. **Failure (graded)** — below bingo: max speed and manoeuvre options shrink;
   at zero you **dead-drift** (no evasion, no manoeuvre, louder relative
   signature because you cannot reposition) and the only outs are a tanker
   rendezvous, a gas-giant ramscoop (hours, and you are stationary and visible),
   or abandoning the leg. This should create a *situation*, not a game-over.
7. **Stations** — Command decides whether the mission is worth the fuel; Sensors
   wants burn to reposition for geometry; Weapons needs fuel to hold alert;
   Comms may trade a fuel-hungry rendezvous for escort duty.
8. **Integrates** — jump alignment (charge cost), hazards (transit cost), the
   disengage victory (running costs fuel), the endurance victory (drifting is
   quiet), and the handoff pack (fuel state at handoff).

**Why it matters:** it is the missing cost that makes every navigation choice a
tradeoff instead of a free waypoint.

## 2. Jump alignment / FTL transit

**Resource:** charge time + fuel + alignment quality. **Owner:** Ops (fly it) and
Engineering/Command (spool it). **Deadline:** the spool-up vulnerability window.

This deliberately mirrors the **weapons solution** pattern already in the code:
a graded `alignmentQuality` that accrues, a committed state, and a graded
failure. Reuse the `solutionQuality`/`weaponTarget` shape rather than inventing
a new idiom.

**Loop**
1. **Read** — astrometrics posts a **jump point**: position, radius, required
   alignment (distance + heading + closing velocity), and a window that opens
   and closes (a gravity/EM cycle; pirate points are tighter and riskier than
   the standard point).
2. **Decide** — plot to the point, hold the correct vector, and pick the moment
   to spool. Committing early is fast but sloppy; waiting for a clean alignment
   burns time and exposes the ship.
3. **Pay** — fuel for the charge, power diverted from sensors/weapons, heat, and
   a large **emission spike** while spooling.
4. **Feedback** — `alignmentQuality` rises as distance/heading/velocity error
   falls (and is displayed exactly like a firing solution). Spool-up shows a
   countdown.
5. **Deadline** — while spooling the ship **cannot manoeuvre hard, runs degraded
   sensors, and is a fat target**. The jump window, the enemy ETA, and the fuel
   reserve are all racing.
6. **Failure (graded)** — abort before commit: charge lost, fuel burned, time
   gone. Commit below threshold: **misjump** — wrong arrival, extra time, fuel
   loss, system damage, crew injury, and you arrive somewhere you did not
   choose. Interference (deep gravity well, active jamming, hostile fire during
   spool) raises the required quality.
7. **Stations** — Ops flies the alignment; Sensors must keep the plot clean
   while blind; Weapons is offline or degraded during spool; Comms may be the
   one who warns of a blockade; Command owns go/no-go.
8. **Integrates** — the campaign gains a travel loop and a **contested
   objective** (jump-point blockade, minelaying, picket), plus a third win/lose
   axis: arriving vs being caught spooling.

## 3. Astrometrics / navigation plotting

**Resource:** time, fuel, and **nav-data quality**. **Owner:** Ops, with Sensors
as the data supplier. **Deadline:** every plot decays as the situation changes.

**Loop**
1. **Read** — a nav plot richer than waypoints: bodies, jump points, hazards,
   no-go regions, and a **chart-age/confidence flag** per feature.
2. **Decide** — compare candidate legs. The system should show three numbers per
   route: **time, fuel, exposure/risk** (computed from speed, terrain ladder,
   hazard state, and known contacts).
3. **Pay** — a long leg is time the enemy uses; a fast leg is fuel and noise; a
   safe leg may be a detour that misses the event.
4. **Feedback** — new contacts/hazards/distress invalidate the plan and force a
   replot; stale charts produce occasional wrong features (a "no-go" that is
   passable, or a clear lane that is mined).
5. **Deadline** — the plotted ETA vs event deadlines; a replot costs time.
6. **Failure (graded)** — an **Astrogation Check** at commitment sets precision:
   success = on-axis arrival; failure = drift/offset arrival (extra time, wrong
   approach, or a hazard encounter); critical failure = gravity-well incident.
7. **Stations** — Ops plots; Sensors must scan/refresh nav data (a reason to
   choose sensor modes); Command chooses the mission profile; the GM can seed
   false charts.
8. **Integrates** — the CombatBot mission generator already produces nav points
   and `dest` jumps; the bridge should share that vocabulary so a mission can
   start as a bridge watch and hand off, or vice versa.

## 4. Heat / thermal signature (recommended addition)

The missing scarcity for the whole EW layer. Today EMCON costs *exposure*; heat
costs *capability*, which is a different and better decision.

**Loop:** running active sensors, shields, weapons, ECM, the reactor at full
draw, or the jump drive builds heat against a budget. You may **vent** (fast
cooling, huge emission spike — everyone sees you now) or **bottle** (quiet, but
heat degrades weapons recharge, sensor precision and eventually manoeuvre).
Decide when to be cold and blind vs hot and visible. This makes the sensor/EW
station a resource manager rather than a button panel.

## 5. Intercept clock / ETA-CPA (recommended, cheap)

**Loop:** expose **closest point of approach** and **time-to-range** for every
track ("contact reaches weapons range in 22 min"; "you cross the jump point at
T+40"). A shared countdown every station acts against. It converts the open
watch into a race, gives fuel/heat/jump decisions their urgency, and costs
almost nothing to compute from existing positions and velocities.

## 6. Crew fatigue, morale and watch rotation (recommended)

The endurance victory ("six hours dark") is currently a timer. Make it an
endurance loop.

**Loop:** a long watch degrades Checks; the commander **rotates** stations
(someone must be awake and sharp), grants rest, treats casualties, and manages
morale. Morale drops from casualties, low fuel, unanswered distress and long
silence; it recovers via rest, success, and Rally/Inspire. Low morale produces
a graded failure: slower reactions, refused orders, mistakes in identification.
**Integrates** with WCRPG's Shaken/Rally and the Undermanned penalty.

## 7. Optional later loops

- **Hangar / small-craft ops** — launch/recover fighters or a shuttle; the
  parent is vulnerable with the deck open; recovery is its own window.
- **Prize / boarding / rescue** — close, match velocity, board or recover;
  time + exposure + risk; ties to cargo/manifest and to the false-surrender
  event already in the game.
- **Consumables / supply** — buoys and noisemakers already exist; extend to
  torpedoes, spares and provisions, with replenishment rendezvous.

## Do not add

Full vector movement (a different game, and it breaks the watch's readability),
a deep trading economy inside the bridge (that is CombatBot proper), and any
resource with no deadline — it will just become a stat nobody looks at.

## Data, protocol, UI

- `ShipState`: `fuel`, `fuelCapacity`, `heat`, `heatCapacity`, `alert`,
  `crewFatigue`/`morale`, plus `jump: {pointId, alignmentQuality, charge,
  spooling}`.
- `CampaignSeed`/`GameState`: `jumpPoints[]` (position, radius, alignment
  tolerances, window open/close, difficulty), `navPoints[]`, and chart-age flags.
- C2S: `nav:speed`/`nav:mode` already exist; add `nav:plot {route}`,
  `jump:spool`, `jump:commit`, `jump:abort`, `power:distribute`,
  `crew:rotate`.
- UI: Ops gets the **range ring**, route comparison and jump alignment widget;
  Sensors gets chart-age/nav-data refresh; Command gets the go/no-go prompt;
  the watch bar gets ETA/CPA and a bingo-fuel warning.

## Recommended order

1. **Fuel + range ring** — the foundation every other transit decision needs.
2. **ETA/CPA intercept clock** — cheap, and it gives the loops their urgency.
3. **Astrometrics** — the map layer fuel and jumps live on.
4. **Jump alignment** — reuses the weapons-solution pattern; adds a travel loop
   and a contested objective.
5. **Heat** — the missing EW scarcity.
6. **Crew fatigue/morale** — makes the endurance victory real.
7. Optional: hangar, prize/boarding, consumables.

## Tests

- Deterministic burn for a given speed/mode/alert/terrain; range-ring maths.
- Bingo-fuel warning fires at the right threshold and dead-drift is graded.
- Jump alignment accrues and decays; misjump at low quality; abort loses charge.
- Astrogation failure produces offset arrival, not a crash-only outcome.
- Heat vent vs bottle effects on emission and capability.
- ETA/CPA matches a worked geometry example.
- Fatigue degrades a Check by the documented step; rotation restores it.
- Every new field round-trips persistence and appears in the handoff pack.

## Relation to the other plans

This complements `HAZARDS_AND_REALTIME_PLAN.md` (terrain/hazards and cooldowns),
`WCRPG_INTEGRATION_PLAN.md` (Checks, shields, system damage, alert ladder) and
`COMMS_WEAPONS_PLAN.md` (solutions). Fuel, heat and jump alignment are the
scarcities those systems currently lack; the intercept clock is what makes them
urgent.
