# Comms / Weapons fun plan

## Implemented

- Add transmission modes: tight-beam, burst, open, and spoof.
- Give each transmission a different exposure and tension cost.
- Add Weapons states: safe, standby, armed, and locked.
- Make armed and locked solutions increase exposure, with locked solutions costing more.
- Preserve the existing rules-of-engagement behavior: only hostile armed/locked contacts move the ship to HOLD.
- Include Weapons state and solution quality in the external handoff pack.
- Add a schedulable `weapons-warning` decision event with quick-lock, standby, and stand-down choices.
- Add IFF confidence and an explicit spoof-detected result: `Contact.iffConfidence`,
  `iffChallenges` and `spoofDetected`, with repeat challenges and a resolved spectrum
  both raising the odds of unmasking a false transponder.
- Add weapon-specific solution requirements and a quick-shot/refined-shot choice:
  the `shared/weapons.py` mount catalog (guns, missiles, torpedo) sets each mount's
  required grade, envelope and lock exposure; `weapons:prep` now takes `weapon` and
  `shot`, and the handoff pack carries the mount and shot type.
- Add Comms/Weapons event effects for relays, challenge-response, civilian traffic,
  and false surrender calls: `EventEffect.relay` / `challenge` / `civilian` /
  `falseSurrender`, with `relay`, `challenge`, `civilian` and `false-surrender`
  templates in `shared/events.py`.

## Next slice

- Surface transmission and Weapons controls in the activity UI (React repo,
  `captain/apps/activity`): transmission-mode buttons, a mount picker with quick/refined
  shot, and `iffConfidence` / `spoofDetected` readouts.
- Expose the IFF confidence and spoof result on the sensor/comms contact card.
- Let a spoof-detected track feed the classification ladder directly (an automatic
  bump rather than the current manual call).
