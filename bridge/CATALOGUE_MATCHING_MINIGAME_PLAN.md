# Catalogue Matching Minigame — the ID board

## Loop test

1. **Resource:** listen passes already spent on a contact (from
   `SENSORS_EW_MINIGAME_PLAN`'s frequency-plot accumulation).
2. **Deadline:** the tactical window before the contact closes to weapons
   range, or before Command needs a tag for the handoff.
3. **Owner:** Sensors. Affects Comms (IFF/challenge routing), Weapons
   (solution requirements), Command (RoE and handoff).
4. **Decision:** which catalogue entry the partial evidence best fits, when
   more than one entry is a plausible read.
5. **Graded failure:** a wrong tag does not "fail" the minigame — it produces
   a bad handoff and a bad tactical plan later, per the design principle
   already in `SENSORS_EW_MINIGAME_PLAN`.
6. **Feedback:** the chosen tag flows into weapon prep, comms procedure, and
   the engagement handoff.

**The "why":** the player should be able to say "I tagged it `Enemy_Escort`
because the low-band signature matched and the mid-band was still too thin to
rule out `Enemy_Cruiser`" — a defensible read of ambiguous evidence, not a fast
click.

## The board

A visual corkboard, not a dropdown:

- Left side: the contact's **accumulating evidence** — resolved frequency
  bands as they fill in (reuses the existing `frequencyProfile` accrual),
  any EW intercept notes, any IFF challenge results.
- Right side: a **rack of catalogue silhouettes**, grouped into the
  `SENSORS_EW_MINIGAME_PLAN` similarity clusters (e.g., `Enemy_Cruiser` /
  `Enemy_Destroyer` sit adjacent, `Enemy_Escort` / `Friendly_Transport` sit
  adjacent) so the visual grouping itself
  teaches which ships are genuinely hard to tell apart.
- The player **drags a band segment onto a candidate silhouette** to compare
  it against that ship's reference profile; the board shows an overlay
  (not a score) so the player judges the match by eye.
- Committing a tag is a distinct, deliberate action (`TAG <hull>`) separate
  from browsing comparisons, so idle comparison carries no cost and no
  information leak, but committing is a real decision point.

## Ambiguity tools

- **Overlay ghosting:** hovering a candidate shows its reference bands
  faintly overlaid on the accumulated plot — close enough to compare, not
  clean enough to be an answer key. Add a small amount of profile jitter
  drawn once per contact (server-side, seeded) so two contacts of the same
  true class never look pixel-identical.
- **Confusable flag:** if two or more candidates are within the
  similarity-group tolerance, the board shows "AMBIGUOUS: 2 candidates
  plausible" rather than silently picking a leader — this is the prompt to
  gather more evidence (another listen pass, an EW sniff, an IFF challenge)
  instead of guessing.
- **Revision cost:** changing a tag after commitment is allowed but costs
  time and a small command-trust penalty, per the existing design in
  `SENSORS_EW_MINIGAME_PLAN`; the board should show this cost before the
  player confirms a revision.

## Multi-contact triage

When several contacts are being tracked at once, the board becomes a triage
puzzle: listen passes are a shared, finite resource this watch (per
`SENSORS_EW_MINIGAME_PLAN`'s cooldown model), so the player must choose
*which* contact to spend the next pass on. Surface this explicitly: a queue
of pending contacts with their current evidence completeness, so "which one
do I resolve next" is itself part of the decision, not just "resolve the one
I'm looking at."

## Station interaction

- Sensors can request an **IFF challenge** from Comms to add evidence to a
  specific candidate rather than resolve it alone.
- Weapons can flag a **minimum confidence threshold** it requires before
  arming against a given tag, visible on the board as a target readiness
  gate.
- Command can see the board's current ambiguity state (not the true class)
  and can override under time pressure, accepting the risk explicitly.

## Data, protocol, UI

- Reuses `Contact.frequencyProfile`, `bridge_signatures.json`, and
  `Contact.playerTag` / true-class separation already specified in
  `SENSORS_EW_MINIGAME_PLAN`. No new server-side identification model is
  required — this plan is the client-side board and the `AMBIGUOUS` signal.
- Add `Contact.candidateCount` (server-computed: how many catalogue entries
  are within tolerance of current evidence) so the client can show the
  ambiguity flag without exposing the true class.
- C2S: existing `sensors:tag` action; add `sensors:compare {contactId,
  candidateId}` as a read-only, cost-free action for overlay browsing.

## Tests

- Overlay comparison never reveals the true class or a correctness signal.
- `candidateCount` reflects the same similarity-group tolerance used by the
  server's own matching, and changes only as evidence accrues.
- Revision cost applies consistently and is shown before confirmation.
- Multi-contact triage queue reflects true evidence completeness per
  contact, deterministically, under 1x/4x/manual advance.
- A tag committed via the board round-trips into weapons/comms/handoff
  exactly as a tag committed via the existing `sensors:tag` command.

## Roadmap placement

Client-side addition to the Sensors/Catalogue UI once
`SENSORS_EW_MINIGAME_PLAN`'s blind-tagging and similarity groups exist
(depends on that plan's steps 1–4). No new Phase; ships alongside the
catalogue UI milestone.
