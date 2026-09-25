# Bridge Commander — watch manual

A short field guide to a six-hour watch. You are the bridge crew of a ship
hunting (and being hunted) through a star system. Nothing is scripted; the
enemy is the same simulation you are.

---

## 1. The job

You win one of three ways, and lose one way.

| Outcome | How |
|---|---|
| **Endurance win** | Stay dark for **6 hours** (360 sim minutes) with **no hostile ever building a working track** on you — *and no live datum on you*. |
| **All tracked** | Detect every hostile and get each to *tracking*, with weapons still SAFE. |
| **Disengaged** | Let every hostile fall outside 120 klik after at least one came inside it. |
| **Loss** | A hostile reaches a firing lock on you (its track hits 100%). |

The endurance win is the real one. It is not a stealth stat — it is a hunt you
have to **break**.

---

## 2. Start a watch

```bash
python -m bridge                         # PORT=8787 by default
```

Open `http://localhost:8787`, pick a station (**CLAIM**), then whoever holds
Command presses **START ENGAGEMENT**. One crew member can fly all four seats by
**LEAVE SEAT** and claiming another; the AI does not fly your ship.

The GM console is a separate app on `ADMIN_PORT` — it can spawn contacts, drop
a torpedo in the water, set your hull, skills and drive, and freeze the clock.

---

## 3. Read the watch bar first

Everything that matters is on one line:

`PAUSE · 1X · 4X TRANSIT · 60X WARP` — time. **Pause is sacred**: the tabletop
handoff only ever sees a paused, coherent picture.

Then, left to right: your **posture**, the **environment** (and the next hazard
forecast), **exposure/noise**, **fuel** and **range**, **heat**, **fatigue**,
any **SPOOLING** or **PICKET LINE** alarm, the last **Check** roll, and cooldowns.

If a number is red, it is costing you something *right now*.

---

## 4. Who owns what

| Station | You own |
|---|---|
| **Command** | Alert condition, RoE, decision events, the watch bill, rallying a shaken crew, damage-control work, shipyard fit, salvage/replenish |
| **Ops** | Helm (speed, mode, waypoints), transit doctrine, nav plots and jumps, TMA legs, evasive manoeuvres |
| **Sensors & EW** | Passive listen, active radar, gravidar, catalogue calls, chart surveys, baffles, spoofs, shooting down inbound weapons |
| **Comms & Weapons** | Transmission modes, IFF challenges, intercepts, weapon prep/lock, subsystem aiming |

---

## 5. The loops

### 5.1 Find and name contacts (Sensors)

1. **LISTEN** on a contact. A listen pass fills in its spectral barcode; more
   passes resolve it fully.
2. **TAG** it from the catalogue. Tagging is **blind** — you commit to a call
   and you are *never told if you were right* until the engagement resolves.
   A resolved spectrum plus a call is strong evidence; a bare guess is weak.
3. Options: **KEY RADAR** (precise range, broadcasts your position),
   **HIGH-POWER PING** (sharp fixes, shouts — and puts a datum on *you*),
   **DEEP GRAV SWEEP** (finds quiet hulls, needs headway).

The **CATALOGUE** tab is where hull art and the contact board live.

### 5.2 The hunt (the heart of the game)

When a hunter builds a track on you, it drops a **DATUM** — a search box
centred on where you were. It widens and fades with time; a fresh detection
**re-centres** it. While it lives, you cannot win on endurance.

Break it with any combination of:

- **DRIFT** (Ops → posture). Slow and silent: detection decays ~2.5× faster and
  the datum fades fast. Sprinting is the opposite — fast, loud, and it feeds
  the hunter.
- **Change layer** (Ops → altitude). Bands hide you from a sensor on the other
  side of the boundary; crossing costs noise and briefly blinds *you*.
- **Fix your navigation** (Ops → STAR / LANDMARK / PING FIX). Dead-reckoning
  error grows while you run; it stretches your ETAs and spoils jump alignment.
- **Clear the baffles** (Sensors). Your towed array is blind dead astern; a
  clearing turn fixes that and is *heard*.
- **Solve the track by manoeuvring** (Ops → TMA). Fly a deliberate course
  change, hold it, and a bearing-only contact yields a **range** — but a
  careless leg inside a datum re-centres it.

Watch the Sensors board for the enemy's search tracks converging.

### 5.3 Move, and jump (Ops)

- **Fuel is real.** Burn rises with speed, action stations, the active radar and
  bad terrain. **BINGO** means get home; **DEAD DRIFT** means you cannot move.
- **Plot a leg** (OPS → Astrometrics): each candidate shows **time, fuel and
  exposure**, plus a risk flag. **COMMIT** rolls an **Astrogation Check**:
  success is an on-axis arrival, failure is an offset arrival, a critical
  failure is a gravity-well incident.
- **Jump** at a charted point: **SPOOL** (costs fuel, huge emission spike, and
  the ship goes blind, slow and loud), watch **alignment** climb against the
  required figure inside the point's **window**, then **COMMIT**. Under the
  requirement is a **misjump** — wrong place, late, and hurt. **ABORT** burns
  the charge.
- **Picket lines** are drawn on the ops plot. Crossing one is a detection event
  that drops a datum on you — unless you slip it quietly.

### 5.4 Fight and survive (Weapons / Command)

- **Prep a mount**: ARM → LOCK. Attacks need **Condition One** (Command sets
  THREE → TWO → ONE; raising costs a fuel point).
- **EHD** is the number your shot must beat: `target HD + its evasive + range
  penalty − your Tactical − your solution bonus`. It is shown live.
- **Manoeuvres** (jink, slip 90/180, snap turn, break) make you harder to hit
  and **spoil your own aim** — they hold until your next helm order.
- **Subsystem aiming** picks a system; a Targeting Check decides whether the
  strike lands there, and shields divide system damage by 100.
- **Inbound ordnance** is a track you can **shoot down**, **decoy** with a
  noisemaker, **spoof** with a pod, **lose in terrain**, or **outlast** on fuel.

### 5.5 Endure (Command)

- **Heat** is capability, not exposure. **VENT** dumps it fast and visibly;
  **BOTTLE** is quiet but it climbs; at the cap the plant vents itself. Heat
  past 70 degrades *every* station's Checks.
- **Watch bill** — standard / battle / rest. Fatigue past 40 costs Checks; a
  hard hit leaves the crew **SHAKEN** until Command **RALLIES** them.
- **Environment** bends everything: sensors, fuel, wear, comms, repairs. The
  nine types range from clear space to an ion storm that kills long-range
  traffic. A dust field fouls your repairs; a debris field offers **salvage**.
- **Damage control**: REPAIR consumes a spare, JURY-RIG is quicker but fails
  again under fire, SERVICE strips wear and cleans contamination. Strip a
  fitted module back out if you need the mass.

---

## 6. Control cheat sheet

Global: `PAUSE` `1X` `4X TRANSIT` `60X WARP` · tabs **COMMAND OPS SENSORS COMMS
CATALOGUE LOG** · `LEAVE SEAT`.

| Where | Controls |
|---|---|
| Command | `THREE/TWO/ONE` alert · `REPAIR` `JURY-RIG` `SERVICE` · `NORMAL/VENT/BOTTLE` · `STANDARD/BATTLE/REST` · `RALLY` · `SALVAGE` `REPLENISH` · `FIT`/`STRIP` modules |
| Ops | `TRANSIT/SPRINT/DRIFT` · `SPEED` presets · `CRUISE/QUIET` · waypoints on the plot · `TMA <contact>` · `STAR/LANDMARK/PING FIX` · `PLOT` `COMMIT` `SURVEY` a leg · `SPOOL` `COMMIT` `ABORT` a jump · `JINK/SLIP 90/SLIP 180/SNAP TURN/BREAK` |
| Sensors | `LISTEN` · `KEY/STOW RADAR` · `HIGH-POWER PING` · `DEEP GRAV SWEEP` · `TAG <hull>` · `CLEAR BAFFLES` · `SPOOF` · `SHOOT IT DOWN` |
| Comms | `TIGHT-BEAM/BURST/OPEN/SPOOF` · `INTERCEPT THE NETS` · `CHALLENGE IFF` · `ARM` `LOCK` `STAND DOWN` · subsystem `TARGET` buttons |

---

## 7. Five things to do in your first watch

1. **Claim Ops and plot a leg** to a nav point before you need to. Learn what
   time, fuel and exposure look like on this hull.
2. **Ping once, on purpose.** Watch the datum appear on the ops plot — then spend
   the next hour breaking it with DRIFT and a layer change. That is the whole game.
3. **Listen a contact to full resolution**, then tag it. Feel how much more the
   call is worth than a guess.
4. **Fit a module** and watch a stat change; then strip it and watch it change back.
5. **Pause and hand off once.** Read the pack. That is what the tabletop gets.

---

*See `ROADMAP.md` for the design record, and `CREDITS.md` for attribution.*
