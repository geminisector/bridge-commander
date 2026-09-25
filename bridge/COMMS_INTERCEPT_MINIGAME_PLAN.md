# Comms Intercept Minigame — partial decode and the hail response

## Why Comms needs its own judgment mechanic

`COMMS_WEAPONS_PLAN.md` gives Comms transmission modes, IFF challenges, and
event effects (relay, challenge, civilian, false surrender), but most of
that is reactive — respond to an event with a fixed menu. This plan gives
Comms something to actively *work on* between events: intercepted traffic
that arrives incomplete, and hails that must be answered without full
information.

## Loop test

1. **Resource:** intercept attempts (`comms:intercept`, cooldown-limited per
   `HAZARDS_AND_REALTIME_PLAN`'s station-action cooldowns) and transmission
   exposure budget.
2. **Deadline:** intercepted traffic is time-boxed — a fleet order or a
   contact's own transmission is only interceptable in its window before it
   ends or moves out of range.
3. **Owner:** Comms. Affects Sensors (a decoded contact ID or intent feeds
   the catalogue board), Command (RoE and mission decisions), Weapons (a
   decoded "weapons free" order should matter).
4. **Decision:** which fragments to prioritize decoding, and how to answer a
   hail without knowing the other side's true intent.
5. **Graded failure:** a botched decode yields a plausible-but-wrong
   fragment, not silence — it can mislead rather than merely fail.
6. **Feedback:** decoded content changes the tactical picture and can
   trigger or defuse a decision event.

**The "why":** the player should be able to say "I prioritized decoding the
IFF blocks over the message body because knowing who they are mattered more
than what they're saying" — a triage call under a shared time budget.

## Mechanic: fragment triage, not a cipher puzzle

Avoid literal cryptography (slow, un-fun, and not deterministic-friendly at
speed). Instead, model an intercept as several **fragments** that arrive with
independent, partial completeness:

- **Header fragment** — sender identity / IFF block.
- **Intent fragment** — order type (patrol, weapons-free, rendezvous,
  distress, stand-down).
- **Detail fragment** — specifics (coordinates, target, deadline).

Each fragment has a completeness value that rises with successive intercept
passes, similar in shape to the Sensors frequency plot. The player chooses
which fragment to focus the next pass on — full header first to confirm
who's talking, or gamble on the detail fragment to get the coordinates
before the window closes. Low-completeness fragments render as a **degraded
but real reading** (e.g., a coordinate with a wide error band, an order
type flagged `LIKELY: WEAPONS FREE (unconfirmed)`), never as blank noise —
the tension is trusting a shaky read under a closing window, not staring at
static.

## Mechanic: the hail response

When a contact hails the ship, Comms answers under the same evidence
Sensors has produced (or hasn't). The response is a small structured choice,
not free text:

- **Stance:** cooperative / neutral / evasive / hostile.
- **Disclosure:** what to reveal (identity, cargo, heading, nothing).
- **Channel:** which transmission mode to answer on (tight-beam limits who
  else hears; open is faster but exposes position, per
  `COMMS_WEAPONS_PLAN.md`'s exposure costs).

The other side's true intent is never shown. The response choice should
visibly interact with the current Sensors tag and IFF confidence — e.g.,
answering cooperatively to a contact Sensors has tagged as probable hostile
is a real gamble the player is choosing to take, and the log should record
it as a decision, not a mistake the game made for them.

## Ambiguity tools

- **Confidence-weighted fragments**, not correct/incorrect — mirrors the
  Sensors design principle. A fragment read at 40% completeness should look
  and feel meaningfully shakier than one at 90%, via qualitative labels
  (`FRAGMENTARY`, `PARTIAL`, `CLEAR`) rather than a bare percentage.
- **False fragments:** hazard/EW conditions (per
  `HAZARDS_AND_REALTIME_PLAN`'s comms dead-zone and
  `SUBMARINE_INSPIRATION_PLAN`'s comms-window idea) can degrade a fragment
  into a *plausible wrong reading* rather than a gap, so trusting a shaky
  intercept is a real risk, not just a missing-data inconvenience.
- **Cross-check:** Sensors' IFF challenge and Comms' intercepted header
  should be able to agree or conflict; a conflict is the single most
  interesting state the board can show, and should be surfaced clearly.

## Station interaction

- Sensors can request Comms prioritize a header fragment to firm up a
  contested catalogue tag.
- Weapons cares about a decoded "weapons free" or "stand down" order —
  route it as a visible flag on the weapons panel, not just Comms' own
  screen.
- Command owns the actual hail-response decision when stakes are high
  (first contact, distress, surrender) and can override Comms' proposed
  stance under the false-surrender event already specified in
  `COMMS_WEAPONS_PLAN.md`.

## Data, protocol, UI

- `Intercept {id, sourceContactId, fragments: {header, intent, detail}: 
  {completeness, degradedReading}, windowEndsAt}`.
- C2S: `comms:interceptFocus {interceptId, fragment}`,
  `comms:hailRespond {contactId, stance, disclosure, channel}`.
- UI: an intercept board listing active intercepts with per-fragment
  completeness bars and a focus selector; a hail-response panel that
  surfaces the current Sensors tag/IFF confidence alongside the response
  choice so the gamble is visible at the moment it's made.

## Tests

- Fragment completeness accrues deterministically under 1x/4x/manual
  advance and freezes on pause.
- A low-completeness fragment never renders as blank; it renders as a
  labelled degraded reading.
- Hazard/EW conditions can degrade a fragment into a wrong-but-plausible
  reading at the documented rate.
- Hail response records the Sensors tag/IFF state at the moment of the
  decision, for later log/handoff review.
- Conflicting Sensors IFF and Comms header intercepts both persist and are
  shown, rather than one silently overwriting the other.
- Intercept windows close on schedule and are visible on the watch bar as
  an upcoming deadline.

## Roadmap placement

Extends `COMMS_WEAPONS_PLAN.md`'s "next slice" (transmission/IFF UI work);
build after IFF confidence and spoof detection land, since hail response
and fragment cross-checks depend on that state existing.
