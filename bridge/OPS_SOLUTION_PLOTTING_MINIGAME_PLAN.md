# Ops Solution Plotting Minigame — solve by manoeuvre, not by joystick

## Why this needs its own plan

`SUBMARINE_INSPIRATION_PLAN.md` calls for TMA ("manoeuvre to solve") and
`TRANSIT_AND_ENDURANCE_PLAN.md` calls for astrogation legs and jump
alignment. All three are naturally suited to become one family of discrete
plotting decisions rather than a real-time steering task — this plan gives
them a shared interaction shape so Ops feels consistent across contexts.

## Loop test

1. **Resource:** time, fuel, and — for TMA specifically — the current
   datum's exposure to being re-centred by a careless leg.
2. **Deadline:** the contact's closing range, the jump window, or the fuel
   range ring.
3. **Owner:** Ops. Affects Sensors (bearing-rate payoff), Command (go/no-go
   on committing), Weapons (a resolved range changes the firing solution).
4. **Decision:** which discrete leg to fly, chosen from a small set of
   real options with visible tradeoffs — not continuous steering.
5. **Graded failure:** a poorly chosen leg yields weak bearing rate (little
   solve progress) or re-centres a datum; it does not crash the ship or end
   the game.
6. **Feedback:** solve quality feeds directly into `_refresh_estimate` (per
   `SUBMARINE_INSPIRATION_PLAN`) and into the weapons EHD calculation.

**The "why":** the player should be able to say "I turned to starboard
because it opened the angle on the bearing without carrying us toward the
datum's centre" — a plotted choice with a legible tradeoff, not a
twitch-steered curve.

## The mechanic: leg cards, not a helm stick

Present Ops with 3–5 **candidate legs** as cards, each computed server-side
from the current geometry:

- Heading change and duration.
- Projected bearing-rate gain (shown as a range, not an exact promised
  number — the true gain depends on the contact's own unknown motion).
- Fuel/heat cost.
- Exposure cost (does this leg carry the ship toward or away from a live
  datum's centre; does it cross a layer boundary; does it enter a hazard).
- A plain-language tag: `AGGRESSIVE`, `CAUTIOUS`, `BLIND SPOT` (if it would
  swing the contact into baffles).

The player picks a card and **commits** to it for its full duration —
mirroring the jump-alignment "commit early is fast but sloppy, waiting for
clean alignment burns time" pattern already specified in
`TRANSIT_AND_ENDURANCE_PLAN.md`. There is no continuous stick input; the
skill is reading the cards against the tactical situation, not executing a
smooth curve.

## Applying the same shape across contexts

- **TMA leg:** cards trade bearing-rate gain against datum exposure and
  baffle risk.
- **Astrogation leg** (`TRANSIT_AND_ENDURANCE_PLAN`): cards trade time,
  fuel, and exposure/risk per the existing three-number leg comparison —
  this plan just specifies that comparison as the same card UI, so Ops
  learns one interaction pattern for both.
- **Jump alignment:** the "hold vector, choose the moment to spool" decision
  becomes a live-updating single card (alignment quality climbing) with an
  explicit `COMMIT NOW` vs `HOLD FOR CLEANER ALIGNMENT` choice at any
  moment, rather than a twitch-timed window.
- **Layer crossing** (`SUBMARINE_INSPIRATION_PLAN`): a crossing is itself a
  leg card with a fixed noise/blind-time cost, so choosing to cross reads
  the same way as choosing any other leg.

## Ambiguity tools

- **Ranged projections, not point estimates.** A card never promises an
  exact bearing-rate gain, because the contact's true motion is unknown —
  show a plausible range so the player is genuinely betting, not
  min-maxing a known number.
- **Datum-exposure warning, not a block.** A leg that would clearly
  re-centre a live datum is flagged, never disabled — Command or Ops may
  have a good reason to take the risk (breaking contact with something
  worse elsewhere), and the game should let them own that call.
- **Stale cards.** If the tactical picture changes mid-consideration (new
  contact, hazard shift), the card set should visibly refresh with a "PLOT
  UPDATED" flag rather than silently invalidating a choice the player was
  about to make.

## Station interaction

- Sensors can request a specific leg ("give me an angle on contact 4") which
  should surface as a suggested/highlighted card on the Ops board rather
  than a separate command, so the ask-and-fly interaction from
  `HAZARDS_AND_REALTIME_PLAN`'s cross-station coordination goals is visible
  in the UI, not just implied by chat.
- Weapons sees the resolved range/quality the moment a TMA leg completes,
  updating any pending solution automatically.
- Command sees exposure and fuel cost on every card and can veto or demand
  a specific leg under RoE.

## Data, protocol, UI

- Server computes leg candidates on request: `ops:legOptions {contactId?
  jumpPointId?}` returns a small array of `LegCard {heading, duration,
  projectedGainRange, fuelCost, exposureDelta, tags[]}`.
- `ops:legCommit {legId}` locks in the choice; server resolves the true
  gain at leg completion using the seeded random already used elsewhere,
  never client-side.
- UI: a card rack replacing/augmenting the raw heading input, with the
  currently-committed leg shown as an in-progress countdown card.

## Tests

- Leg candidates are recomputed deterministically from the same geometry
  under 1x/4x/manual advance.
- Committed legs cannot be altered mid-flight except via the existing
  abort/interrupt rules.
- A leg's true bearing-rate gain is resolved server-side and never
  predictable exactly from the shown range.
- Datum re-centring from a flagged leg matches the documented mechanic in
  `SUBMARINE_INSPIRATION_PLAN`.
- Stale-card refresh fires on any tactical-picture change during
  consideration, before commit.
- The same `LegCard` shape correctly serves TMA, astrogation, and jump
  contexts without duplicated logic.

## Roadmap placement

Sits alongside `SUBMARINE_INSPIRATION_PLAN` priority #4 (TMA) and
`TRANSIT_AND_ENDURANCE_PLAN`'s astrometrics/jump-alignment milestones
(recommended order items 1–4). Build the card UI once astrogation leg
comparison exists, then extend it to TMA and jump alignment rather than
building three separate interfaces.
