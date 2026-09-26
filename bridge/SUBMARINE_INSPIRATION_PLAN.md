# Submarine-Warfare Inspiration for Bridge Commander

## Why submarines are the right reference

Bridge Commander is already a submarine watch in space clothing: silent running,
EMCON, hydrophone-as-passive-array, active ping as a career-ending risk,
bearing history as TMA, noisemakers as decoys, thermal layers as hazards. The
submarine genre has spent forty years solving exactly the problems this bridge
has — stealth vs speed, contact classification, counter-detection, limited
consumables and command pressure — and it has proven **loops**, not just stats.

This plan follows the loop test in `TRANSIT_AND_ENDURANCE_PLAN.md`: every
mechanic needs a visible finite resource, a deadline, an owning station, a
non-dominant decision, a graded failure, and feedback into a neighbour system.

Inspiration (genre, not text — take mechanics, not prose):
- *Red Storm Rising* (GDW) — datum/hold-contact, sensor conditions.
  [manual](https://archive.org/stream/redstormrisingmanual/RedStormRising-Manual_djvu.txt)
- *Cold Waters* / *Dangerous Waters* / *688 Attack Sub* — thermal layers,
  TMA, wire-guided torpedoes, evasion. [layer discussion](https://steamcommunity.com/app/541210/discussions/0/1353742967799693461)
- *The Hunters* / *Silent Victory* / *Steel Wolves* (GMT) — patrol loop, fuel,
  torpedoes, crew. [The Hunters](https://www.gmtgames.com/p-967.aspx)
- *Harpoon* / Admiralty Trilogy (*Command at Sea*) — sensor/detection modelling.
- Top Secret/S.I. *The Doomsday Drop* — the tabletop-RPG take on a nuclear boat.
  [module](https://the-eye.eu/public/Books/rpg.rem.uz/Top%20Secret/S.I/Top%20Secret%20S.I.%20-%20TS2%20The%20Doomsday%20Drop.pdf)
- *Red November*-style status/consumable tracking. [status markers](https://www.historicalboardgaming.com/assets/images/HBG/HBGMarkers/00Marker%20Rules/Submarine%20Status%20Marker%20Rules-HBG.pdf)

## Already borrowed (keep, don't duplicate)

Silent running / EMCON; passive vs active sensing and the cost of radiating;
bearing history and `_refresh_estimate` (a TMA seed); noisemakers; contact
classification with blind tagging; RoE and decision events; readiness/battery;
the detection race and enemy lock.

## The gaps the genre fills

### 1. A datum *and the hunt* (highest value)

Today detection ends in a scalar: `lock` rises to 1.0 and the patrol is lost.
Submarine games model something positional and recoverable: when you are
detected, a **datum** is placed at your last-known position, the hunter searches
*around* it, and the datum **decays** if you stay quiet.

**Loop:** be detected (a Check, an active ping, a noise spike) → a datum appears
on the plot, with an age and a growing uncertainty radius → enemy search tracks
converge on it → you must **clear the datum**: run ultra-quiet, change layer,
change course behind a layer, launch a decoy, or use terrain → if the datum ages
out, the hunt breaks and you get a window; if it does not, a new detection
re-centers it.

**Stations:** Sensors sees the search tracks; Ops owns the evasion leg; EW owns
the decoy; Command decides whether to keep the mission or run.
**Failure (graded):** datums stack and the ring tightens — you are hunted, not
instantly dead. **Integrates** with enemy lock, the endurance victory (staying
undetected), and the disengage victory.

### 2. Signature layers (activate altitude)

The bridge has `z`/altitude and does almost nothing with it. Cold-water boats
live or die by the **thermal layer** and shadow zones.

**Loop:** the water column (or, here, the EM/thermal gradient) has one or more
layers at set altitude bands. Below a layer you are hidden from a sensor above
it and vice versa; crossing a layer costs time, noise and manoeuvre, and
**breaks your own contacts** briefly. Sonar conditions vary by band, so the
correct layer depends on who is hunting whom.

**Stations:** Ops flies the layer; Sensors reports which layer holds the
contact; Command decides whether to hide or to see. **Failure:** getting caught
mid-crossing is loud; being in the wrong layer blinds you.
**Integrates** with hazards, passive/active ranges, and datum clearing.

### 3. Sprint-and-drift, with an acoustic budget

Transit is not a speed setting; it is a doctrine of alternating sprint and
silence. This is the natural home for the heat/fuel costs already proposed.

**Loop:** choose a sprint leg (fast, loud, burns fuel/heat) and a drift leg
(silent, slow, vulnerable) → the enemy's detection accumulates against the
sprint and decays in the drift → the crew must judge how long they can afford to
drift given the mission clock.
**Integrates** with fuel, heat, datum decay, and ETA/CPA.

### 4. TMA: manoeuvre to solve

The bridge accumulates bearings and estimates range from bearing rate, but does
not reward *deliberately manoeuvring* to generate that rate — the single most
submarine act there is.

**Loop:** to fix a passive-only contact you must **change course** through a
known angle and hold it long enough to measure bearing rate; the leg costs time
and exposes your turn, and a careless turn inside a datum re-centers it. Reward
the solve with a range/quality jump (extend `_refresh_estimate`).
**Stations:** Ops flies the leg; Sensors calls the leg and reads the rate.

### 5. Baffles and "clearing the baffles"

Aft of the towed array is a blind arc; the classic response is a deliberate
turn to look behind you. The bridge's stern dazzle is half of this already.

**Loop:** a track can hide in your baffles (you cannot see it; it can see you),
so you periodically spend time and noise clearing them. **Integrates** with
passive detection geometry and the datum loop.

### 6. Comms windows at "periscope depth"

Radio silence is the default; transmitting means coming shallow and raising a
mast. The bridge has transmission modes and altitude but no physical window.

**Loop:** to send/receive (orders, distress, intel) the ship must come to a
shallow depth band and go active on comms for a bounded window — visible,
slower, and unable to manoeuvre freely. The message you need may arrive only in
that window. **Integrates** with EMCON, layers, and decision events.

### 7. Barriers and pickets (SOSUS analog)

Fixed sensor lines across a map: crossing loudly lights you up for a wide area;
crossing quietly (drift, layer, terrain) is the whole game.

**Loop:** Ops plots a crossing; Sensors estimates coverage gaps; EW may need to
jam or decoy a node. **Integrates** with astrometrics routing and the datum loop.

### 8. Position uncertainty (dead reckoning)

Your own plot is exact today. Submarine navigation is a loop: DR error grows,
and a fix requires a star sighting, a landmark, or a risky surfacing.

**Loop:** nav error accrues with time and manoeuvre; a fix costs time/exposure;
an unfixed error makes your plotted ETA and your jump alignment wrong.
**Integrates** directly with the astrometrics and jump-alignment loops.

### 9. Watch bill, fatigue and consumables

Submarines run watches, and crews break down on long patrols. This is the
endurance loop from the other plan, but the genre supplies the shape:
6-on/12-off rotations, a commander who must decide who is sharp, and a
**consumables clock** (torpedoes, spares, scrubbers) that never stops.

**Loop:** a long watch degrades Checks; rotate stations or accept mistakes;
low consumables or morale force mission decisions. **Integrates** with crew
fatigue/morale, WCRPG's Shaken/Undermanned, and the endurance victory.

### 10. Torpedo in the water

Weapons currently resolve only in the handoff. Submarine games make the inbound
weapon its own loop: counter-detect the launch, evade (turn inside it, decoy,
terrain, outrun), and survive to counter-attack.

**Loop:** an inbound ordnance track appears (use the WCRPG "ordnance as a
Size-Class-1 object" model) with a time-to-impact; Sensors tracks it, EW decoys
it, Ops flies the evasion, DC prepares for the hit. **Integrates** with datum,
layers, and the handoff pack.

## Priority

1. **Datum and the hunt** — the biggest missing loop; converts the detection
   race from a scalar into a search you can break.
2. **Signature layers** — activates altitude, cheap, huge tactical depth.
3. **Sprint-and-drift + acoustic budget** — the doctrine that makes fuel/heat
   decisions legible.
4. **TMA manoeuvre-to-solve** — deepens the passive game that already exists.
5. **Position uncertainty + comms windows** — gives astrometrics and comms a
   physical cost.
6. **Baffles**, **barriers**, **torpedo-in-the-water**, **watch bill** — later or
   scenario-specific.

## Do not add

Under-ice navigation, wire-guided torpedo steering, and full sonar-propagation
models (convergence zones, bottom bounce, ray tracing) — they are magnificent in
a sim and unreadable in a browser watch. Also do not import real-world
classification levels or weapons details; this is a fan game, not
a training aid.

## Data, protocol, UI

- `GameState`: `datums[] {pos, radius, age, strength, sourceId}`, `layers[]`
  (altitude bands with sensor modifiers), `navError`, `consumables`.
- `ShipState`: `depthBand` (derived from `z`), `sprint`/`drift` posture,
  `baffleClear`, `commsWindow`.
- C2S: `nav:depth`, `nav:posture {sprint|drift}`, `ew:decoy`, `sonar:tma {leg}`,
  `comms:window {open|close}`.
- UI: Sensors shows the datum ring and search tracks; Ops shows layers and the
  TMA leg; Command gets the "break the datum / keep the mission" call.

## Tests

- Datum placement on detection, radius growth, and decay to "hunt broken".
- A datum re-centers on new noise and clears under quiet + layer change.
- Layer crossing hides from one side, blinds the crosser, and costs time/noise.
- Sprint/drift detection accumulation and decay are deterministic.
- TMA leg produces a range/quality gain proportional to bearing rate.
- Baffle blind arc hides a track until a clearing turn.
- Comms window opens at the right depth band and exposes the ship.
- Nav error accrues, a fix resets it, and it perturbs the plotted jump alignment.

## Relation to the other plans

This is the doctrine layer over `TRANSIT_AND_ENDURANCE_PLAN.md` (fuel, heat,
astrometrics, crew), `SENSORS_EW_MINIGAME_PLAN.md` (TMA and catalogue),
`HAZARDS_AND_REALTIME_PLAN.md` (layers as environment) and
`WCRPG_INTEGRATION_PLAN.md` (Checks, system damage, ordnance-as-objects).
Build the datum loop first: it makes every other stealth mechanic mean
something.
