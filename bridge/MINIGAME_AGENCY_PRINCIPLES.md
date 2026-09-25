# Minigame-Shaped Agency — Design Principles

## Why this document

Several station plans (Sensors, Comms/Weapons, Ops) need more moment-to-moment
"something to actually do" without breaking the constraints the rest of the
game already depends on: server-authoritative pause, deterministic replay
across 1x/4x/manual advance, blind identification, and cooperative legibility
across four seats. This document is the filter for judging any proposed
minigame before it gets its own plan file.

## The two kinds of minigame

**Execution minigames** — timing bars, drag-precision under a clock, reflex
challenges, hand-eye QTEs. Agency comes from *dexterity*: the player did a
physical thing well.

**Judgment minigames** — structured choices made under incomplete information,
where the fun is assembling evidence, weighing a tradeoff, and committing to a
bet whose quality you can defend but not guarantee. Agency comes from
*reasoning*: the player made a good call with what they had.

Bridge Commander must stay almost entirely in the second category. A
judgment minigame is not a lesser reflex minigame — it is a different genre of
fun, and it is the one this game is built to support.

## Why execution minigames don't fit here

- **Determinism.** `HAZARDS_AND_REALTIME_PLAN` requires 1x, 4x, and manual
  advance to produce identical simulated state, and pause must freeze
  everything. A reflex/timing mechanic lives in wall-clock milliseconds, not
  simulated minutes — it cannot be paused, replayed, or made fair across a
  slow and fast watch without special-casing it outside the sim clock.
- **Seat parity.** A cooperative bridge game needs every seat to feel
  valuable regardless of which player is sitting in it tonight. If a
  station's output quality depends on a player's twitch skill at a specific
  minigame, that seat's value swings with who shows up, not with the
  tactical situation — which breaks Command's ability to reason about crew
  reports as *information* rather than *performance*.
- **Blind evidence, not blind execution.** The design principle already
  stated in `SENSORS_EW_MINIGAME_PLAN` — "never tells you if you were
  right, only how convincing the evidence looked" — only works if the input
  to that judgment is itself a judgment (which band to trust, which contact
  to focus) and not a dexterity score.
- **Handoff legibility.** Everything must reduce to a clean state snapshot
  for the external tabletop handoff pack. A judgment call produces a
  `confidence`/`solutionQuality`-shaped number that serializes cleanly. A
  reflex score does not represent anything the tabletop needs.

## What a judgment minigame must have

Reuse the six-point loop test from `TRANSIT_AND_ENDURANCE_PLAN.md`, plus one
addition specific to minigames:

1. A visible, finite resource.
2. A deadline or window.
3. A station that owns it, with at least one other station affected.
4. A real decision with no dominant option.
5. A graded failure, not a game-over.
6. Feedback into a neighbouring system.
7. **A legible "why."** After the fact, the player (and Command, reading the
   log) can point to the specific piece of evidence or tradeoff that drove
   the call. If the only explanation is "I was fast/accurate," it is an
   execution minigame wearing a judgment costume.

## Where juice is still allowed

Cosmetic feedback — an animated frequency plot resolving band by band, a
visual "thunk" on a layer crossing, a satisfying meter fill — is free and
encouraged. The test: if you strip the animation and replace it with a plain
number update, does the underlying decision change? If no, it is juice. If
yes, it is secretly an execution minigame and should be redesigned as a
judgment one.

## How to use this filter

Before writing a new `*_MINIGAME_PLAN.md`:

1. State the resource, deadline, owner, decision, failure, and feedback (the
   loop test).
2. State the one-sentence "why" a player would give for their call.
3. Confirm the mechanic still functions correctly under pause, at 4x, and on
   reconnect with no wall-clock dependency.
4. Confirm the output is a small serializable state (a tag, a confidence
   value, a chosen leg, an allocation) suitable for the handoff pack.

If a proposal fails any of these, cut it back to its judgment core before
building it.

## Companion plans

- `CATALOGUE_MATCHING_MINIGAME_PLAN.md` — Sensors/Catalogue pattern-matching
  identification board.
- `COMMS_INTERCEPT_MINIGAME_PLAN.md` — Comms partial-decode and hail
  response under ambiguity.
- `OPS_SOLUTION_PLOTTING_MINIGAME_PLAN.md` — Ops discrete-leg TMA/intercept
  solving.
- `WEAPONS_SALVO_ALLOCATION_MINIGAME_PLAN.md` — Weapons fire-budget
  allocation across multiple contacts.
