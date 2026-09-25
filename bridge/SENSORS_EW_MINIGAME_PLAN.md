# Sensors / EW Signature Analysis Plan

## Goal

Make passive sensors a Red Storm Rising-style identification minigame: a
frequency plot slowly emerges from noise, the crew compares it with a ship
catalogue, and then commits to a blind identification. The system never tells
the player whether the tag is correct.

## Core loop

1. Detect a contact and begin accumulating its frequency plot.
2. Watch frequency bands resolve gradually through passive listening.
3. Compare the partial plot against the ship catalogue.
4. Choose a likely ship class and tag the contact.
5. Use that tag for Comms, Weapons, and the engagement handoff.
6. Discover the truth only through later engagement or campaign resolution.

The displayed confidence measures evidence quality, not correctness.

## Data

Add `resources/bridge_signatures.json` containing editable reference profiles:

- Ship class and family.
- Reference frequency bands.
- Natural variation.
- Emission level.
- Recognition difficulty.
- Confusable ship classes.
- Decoy/spoof traits.

Optionally add `resources/bridge_sensor_profiles.json` for per-class behavior,
including damaged, quiet, masked, and deceptive signatures.

The current contact model already accumulates frequency bands through
`frequencyProfile` and sensor readouts; preserve that behavior and expose it
cleanly to the client.

## Sensor and EW actions

- Passive listen: slow plot improvement with minimal exposure.
- Focus a band: faster analysis in one frequency range at the cost of broad
  awareness.
- Compare against catalogue: show ranked candidates without confirmation.
- Active ping: rapidly improve the plot while increasing exposure.
- EW sniff: identify emitters and radar behavior, with a chance of misleading
  or incomplete returns.
- IFF challenge: provide additional evidence but remain vulnerable to spoofing.

## Blind tagging

Add a `TAG CONTACT` action that stores the player’s selected class separately
from the contact’s true class.

After tagging, show:

```text
TAGGED: KAMEKH
CONFIDENCE: 61%
VERIFICATION: UNAVAILABLE
```

Allow revisions, but make them cost time, confidence, or command trust. Never
show a correct/incorrect result at tagging time.

## Consequences of bad identification

Use the player’s tag when appropriate for:

- Weapon preparation and solution recommendations.
- Comms challenge-response procedures.
- The engagement handoff pack.
- Tactical warnings and command summaries.

Examples of dangerous mistakes:

- Tagging a Fralthi as a Kamekh produces an inadequate engagement plan.
- Tagging an escort as a freighter lets it close or launch fighters.
- Tagging a neutral ship as hostile creates political or mission consequences.
- Tagging a hostile ship as neutral delays weapons preparation.

Do not apply an arbitrary “wrong guess” penalty; let the bad information cause
the tactical problem.

## Deception and ambiguity

Support contacts that are difficult to classify:

- Quiet capital ships resembling escorts.
- Damaged ships with missing identifying bands.
- Altered engine emissions.
- Civilian or military decoys.
- Formation signatures that merge several contacts.
- Enemy spoofing and false transponder data.

Catalogue entries should have similarity groups so profiles are not perfectly
separable.

## Station interaction

- Sensors can request Comms authentication.
- EW can isolate an emitter or identify radar behavior.
- Ops can maneuver to reduce obstruction or improve aspect.
- Weapons can require a minimum confidence threshold before arming.
- Command can override an uncertain tag under time pressure.

The desired result is useful disagreement between stations rather than a single
correct button sequence.

## Engagement reveal

Reveal truth progressively during handoff or external combat:

- Strong passive analysis improves the starting solution.
- A correct tag provides accurate class and weapon recommendations.
- A wrong tag creates a misleading handoff.
- Active pings improve information but raise exposure.
- EW intercepts can reveal contradictions before engagement.
- Unknown contacts can still be handed off as unknown hostiles.

## Implementation order

1. Expose accumulated frequency bands and sensor metadata in the state protocol.
2. Add and load `bridge_signatures.json`.
3. Implement catalogue matching and ranked candidates.
4. Add blind contact tagging while preserving true type separately.
5. Make Comms, Weapons, and handoff consume the player tag where appropriate.
6. Add quiet, damaged, obstructed, and deceptive profiles.
7. Build the sensor catalogue and frequency-plot UI.
8. Add cross-station actions and time-pressure overrides.

## Tests

Cover:

- Gradual frequency-band accumulation.
- Catalogue ranking from partial plots.
- Blind correct and incorrect tags.
- True type remaining hidden after tagging.
- Wrong tags affecting handoff data and recommendations.
- Quiet, damaged, obstructed, and deceptive contacts.
- Active scanning improving information while increasing exposure.
- Tag revisions applying their intended cost.

## Design principle

> Sensors never tells you whether the identification is correct. It only tells
> you how convincing the evidence looked when you made the call.
