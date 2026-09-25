# Weapons Readiness & Point-Defense Minigame — utilitarian only

## Supersedes

This replaces `WEAPONS_SALVO_ALLOCATION_MINIGAME_PLAN.md`. That plan modeled
offensive multi-contact engagement (EHD-based salvo allocation), which
belongs to the external combat game this bridge hands off to, not to the
bridge itself. Weapons on the bridge has three legitimate jobs: manage
readiness posture as an exposure/deterrence decision, defend against inbound
ordnance, and prep a solution's *inputs* for the handoff — never resolve a
hit here.

## What moves out entirely

- EHD calculation, hit/miss resolution, subsystem damage, and any
  multi-target offensive allocation. These resolve in the external combat
  handoff, using the solution quality and tag data the bridge already
  produces.
- `COMMS_WEAPONS_PLAN.md`'s quick-shot/refined-shot distinction and
  `MANUAL.md`'s "Fight and survive" EHD description should be read as
  **handoff-pack inputs**, not as bridge-resolved combat. The bridge
  computes and displays a solution quality number; it never decides whether
  a shot lands.

## What stays, reframed as utilitarian

### 1. Readiness posture (deterrence and exposure)

**Loop test**
1. Resource: exposure budget and fuel (raising Condition costs a fuel
   point, per `MANUAL.md`).
2. Deadline: RoE and the closing contact's ETA.
3. Owner: Weapons, gated by Command's Condition ladder.
4. Decision: how much readiness to show, trading deterrence value against
   exposure and the risk of provoking a hostile response.
5. Graded failure: over-showing readiness can trigger the "only hostile
   armed/locked contacts move to HOLD" rule against you — you provoke the
   exact reaction you were trying to prevent.
6. Feedback: readiness state feeds the handoff pack and the contact's own
   behavior model.

**The "why":** "I brought us to STANDBY rather than ARMED because I wanted
the contact to hold at range without escalating it to a lock-for-lock
standoff" — a posture decision, not a targeting decision.

Mechanically: arm/lock/stand-down remain simple state changes (as today),
but the UI should foreground the *behavioral consequence* — a live read of
how the targeted contact's posture is likely to shift in response — rather
than a firing-solution readout.

### 2. Point-defense (the actual minigame)

**Loop test**
1. Resource: point-defense mounts and decoy/noisemaker inventory (finite,
   per `SUBMARINE_INSPIRATION_PLAN`'s consumables).
2. Deadline: inbound ordnance's time-to-impact, per
   `SUBMARINE_INSPIRATION_PLAN`'s "torpedo in the water" loop.
3. Owner: Weapons, coordinating with Sensors (tracking) and Ops (evasion).
4. Decision: shoot it down, decoy it, or rely on Ops's evasive leg — each
   has a different cost and a different failure mode.
5. Graded failure: a missed intercept doesn't necessarily mean a hit; it
   can mean "still inbound, try the next layer of defense" (decoy, then
   evasion), giving the crew a second and third chance rather than an
   instant loss.
6. Feedback: point-defense outcomes feed the handoff pack (what defenses
   were already expended before the engagement resolves elsewhere).

**The mechanic:** present the inbound track with a small decision, not a
targeting reticle — a discrete choice of response (`INTERCEPT`, `DECOY`,
`REQUEST EVASION`) made once per inbound track, with the *quality* of that
choice depending on how much warning Sensors gave and how the ship is
currently postured (per `SUBMARINE_INSPIRATION_PLAN`'s layers/datum state).
Resolution of whether the intercept/decoy actually works is a graded roll
against that quality — visible as a percentage, not a hit confirmation —
and if it doesn't fully resolve the threat, it degrades the threat (buys
time, forces a second decision) rather than skipping straight to damage.

**The "why":** "I decoyed instead of intercepting because our point-defense
mount was still on cooldown from the last pass" — a resourcing call under a
visible constraint.

### 3. Solution prep as a handoff input, not a shot

Keep `weapons:prep`, mount states, and quick/refined choice exactly as
specified in `COMMS_WEAPONS_PLAN.md` — but their sole output is a
**solution quality value** attached to the handoff pack. The bridge never
converts that value into a hit or a damage result. This preserves all the
existing tension (mount requirements, envelope, lock exposure) as a
*preparation* loop feeding the other game, without the bridge adjudicating
combat itself.

## Station interaction

- Sensors' tag confidence still gates whether a solution can be marked
  ready, since a bad tag makes for a useless handoff, not a wasted shot.
- Ops's evasive maneuvers are a first-class point-defense option, not a
  Weapons-only tool — the decision to fly a break vs. rely on interception
  should be visibly shared between the two stations.
- Command owns the readiness posture call under RoE and decides whether a
  contested contact gets handed off to the other game at all (engage,
  disengage, or continue observing).

## Data, protocol, UI

- `WeaponsState`: posture (`SAFE/STANDBY/ARMED/LOCKED`), point-defense mount
  cooldowns, decoy/noisemaker inventory, and per-contact `solutionQuality`
  — no hit/damage fields at all on the bridge side.
- `InboundTrack {id, sourceContactId, timeToImpact, threatLevel}` with a
  single `weapons:respond {trackId, action: intercept|decoy|requestEvasion}`
  action.
- Handoff pack carries posture, mount states, solution quality, and
  point-defense inventory expended — exactly what the external combat game
  needs as its starting conditions, and nothing about outcomes.

## Tests

- No bridge-side code path computes a hit, miss, or damage value.
- Readiness posture changes correctly affect contact behavior per the
  existing HOLD rule, without resolving an engagement.
- Point-defense response quality is computed from warning time and posture,
  deterministically, under 1x/4x/manual advance.
- A partially-resolved inbound track degrades rather than binarily
  resolving, and correctly re-offers a response option.
- Handoff pack contains posture, solution quality, and consumable state but
  never a resolved outcome.
- Fuel cost for raising Condition matches `MANUAL.md`'s documented figure.

## Roadmap placement

Replaces the salvo-allocation slice of `COMMS_WEAPONS_PLAN.md`'s "next
slice." Point-defense depends on `SUBMARINE_INSPIRATION_PLAN`'s
"torpedo in the water" loop (priority item 10) existing first; readiness
posture and solution-prep-as-handoff-input can ship immediately since they
only reframe existing state, not add new mechanics.
