# Hazards and Real-Time Gameplay Plan

## Design goal

Make the bridge feel like a live tactical watch rather than a sequence of
isolated turns. The ship should continuously move through an environment that
changes detection quality, emissions, weapons readiness, and decision pressure.

The game should remain pausable and deterministic enough for tests, roleplay,
and external combat handoffs.

## Recommended time model

Use a hybrid simulation clock:

- Paused: no simulation progress.
- Slow watch: 1x, where 30 in-game minutes takes 30 real minutes.
- Fast watch: 4x, where 2 in-game hours takes 30 real minutes.
- Manual advance: retain the current `advance` control for GM/testing and for
  safely jumping through uneventful time.

The existing advance engine remains the single source of truth. Real-time mode
should repeatedly call the same advance function using elapsed wall-clock time,
rather than introducing a second simulation path.

Suggested controls:

- Pause / Resume.
- 1x watch.
- 4x transit.
- Manual advance presets: 15m, 30m, 2h.
- Automatic slow-down when a decision event, detection, missile warning, or
  hazard threshold occurs.

The simulation must never skip past a decision deadline or important alert.
Advance in bounded slices, inspect the resulting state, and reduce speed or
pause when an interrupt condition appears.

## Real-time architecture

Add explicit clock state rather than inferring it from `autoTick`:

- `timeMode`: `paused`, `slow`, or `fast`.
- `timeScale`: numeric simulation multiplier for future extensibility.
- `lastSimulatedAt`: server-side monotonic timestamp, not persisted as game
  time.
- `nextInterruptAt`: nearest scheduled event or hazard boundary.

The server owns the clock. Clients send mode changes; clients do not send time
increments. Broadcast state updates at a modest UI cadence, such as 2–5 times
per real second, while keeping event and state transitions authoritative.

When a room has no connected players, pause simulation or use a configurable
background policy. Do not let an unattended room burn through an entire patrol
silently.

## Hazard model

Add hazards as campaign/environment state, not as special-case event text.
Each hazard should have:

- Type and display name.
- Position or affected region.
- Start and end time, or movement behavior.
- Intensity.
- Effects on emissions, sensors, navigation, comms, and weapons.
- Warning signs and escalation thresholds.
- Possible mitigation actions.

Initial hazard types:

### Ionized nebula

- Raises passive noise and distorts bearing samples.
- Makes active radar more valuable but more detectable.
- Increases self-noise from high-speed travel.
- Causes comms transmission errors or delayed acknowledgements.
- Can make a quiet ship appear intermittently louder.

### Debris or asteroid field

- Creates line-of-sight shadows and false returns.
- Causes frequency plots to arrive in broken fragments.
- Makes high-speed navigation dangerous.
- Offers concealment from enemy sensors.
- Can damage or degrade a ship that rushes through it.

### Solar or radiation storm

- Floods sensors and reduces catalogue confidence.
- Forces the crew to choose between waiting and operating blind.
- Increases battery drain and weapons lock instability.
- Produces intermittent false contacts.

### Thermal layer or dust front

- Masks low-emission contacts while exaggerating hot engines.
- Changes which contact classes are easiest to identify.
- Makes speed and engine state materially affect the signature plot.

### Communications dead zone

- Delays fleet responses.
- Makes open transmission ineffective or risky.
- Encourages relay buoys, tight-beam messages, or local autonomy.

## Hazard effects on emissions

Separate emissions into at least three values:

- Own signature: how detectable the ship is.
- Sensor noise floor: how difficult it is to interpret returns.
- Contact distortion: how much a target’s apparent signature differs from its
  true signature.

Hazards should modify these values continuously and directionally. For example,
an ion storm can hide everyone equally while a dust front hides cold contacts
better than hot ones.

Show the crew the environmental cause, but not always its exact numerical
effect. The bridge should say “passive plot unstable” rather than always saying
“noise +4.2.”

## Hazard gameplay loop

1. Sensors notices a changing background condition.
2. The crew chooses whether to slow down, push through, alter course, or exploit
   the hazard.
3. The hazard changes the frequency plot and emissions.
4. Other stations respond with different costs.
5. The crew receives better or worse information depending on the choice.

Hazards should create opportunities as well as penalties. A nebula can hide a
retreat. An asteroid field can break a missile lock. A radiation storm can mask
an open transmission but also ruin an IFF exchange.

## Event and alert interrupts

## Station action cooldowns

Actions should have visible cooldowns so the crew must choose when to spend its
limited opportunities. Cooldowns are simulated-time timers owned by the server,
not client-side button locks.

Initial cooldown candidates:

- Active sensor sweep: long cooldown; stronger in clear space and riskier in
  unstable environments.
- Active radar ping: warm-up and recovery period; repeated use increases
  exposure and may temporarily worsen passive listening.
- Gravidar scan and noise filter: medium cooldowns affected by hazards.
- EW sniff: medium cooldown; repeated scans risk counter-detection.
- IFF challenge: per-contact cooldown so the crew cannot repeatedly interrogate
  a target until it produces a desired answer.
- Comms transmission: channel cooldown based on transmission mode.
- Weapons lock: warm-up and recovery cooldown; breaking a lock loses some
  solution quality.
- Weapons stand-down: immediate safety action, but re-arming takes time.
- Decoys/noisemakers: inventory-limited with launch and reload timing.

Every action should expose its ready/cooling-down state, remaining simulated
time, and current effect on emissions or sensor quality. Cooldowns should create
coordination problems: Sensors may want an active sweep while EW wants to sniff
and Weapons wants to hold a lock.

Cooldown rules:

- Use simulated time, so 1x, 4x, and manual advance behave identically.
- Pausing freezes cooldowns.
- Fast mode must broadcast cooldown completion and never silently skip a ready
  action.
- Dangerous actions may automatically slow the watch when they become ready.
- Some actions may share a system budget, such as active radar and weapons lock.
- Hazards can lengthen, shorten, or disable cooldowns.
- Display cooldowns as tactical information, not hidden penalties.

## Event and alert interrupts

The real-time model should automatically interrupt or slow when:

- A decision event is created.
- A new contact is detected within a warning range.
- A contact becomes probable, classified, or confirmed.
- Weapons reaches standby, armed, or locked state.
- A missile or hostile active scan is detected.
- A hazard crosses an escalation threshold.
- A campaign event deadline is approaching.

Use a short grace period for low-priority alerts so the game does not constantly
freeze during ordinary sensor updates.

## Preventing real-time frustration

- Every important alert must remain visible until acknowledged.
- Pause should be available to every relevant station or at least Command.
- A reconnect should resume from authoritative server state.
- The UI should show both real time and simulated time.
- Fast mode should automatically fall back to slow mode near danger.
- Manual advance should remain available for solo play and testing.
- Never make players lose a major decision because a browser tab throttled.

## Persistence and determinism

- Persist simulated game time, mode, and active hazards.
- Do not persist wall-clock timestamps as gameplay time.
- Use bounded simulation slices and the existing seeded random functions.
- Ensure the same sequence of simulated minutes produces the same state whether
  it was reached by manual advance, 1x, or 4x mode.
- Record mode changes and hazard transitions in the logbook.

## UI plan

Add a persistent watch bar showing:

- Pause / 1x / 4x.
- Current simulated time.
- Current hazard and severity.
- Next scheduled event.
- Interrupt reason when speed has been reduced.

Add an environment panel showing:

- Sensor clarity.
- Own emission condition.
- Comms reliability.
- Navigation risk.
- Weapons/sensor side effects.

Use qualitative labels such as `CLEAR`, `UNSTABLE`, and `SEVERE` alongside
optional detail on hover.

## Implementation order

1. Introduce explicit `timeMode` and server-owned real-time ticking.
2. Preserve manual advance and add pause/slow/fast protocol messages.
3. Add bounded slices and interrupt detection.
4. Add a generic hazard model and environment state.
5. Implement ionized nebula and debris/asteroid field first.
6. Feed hazard modifiers into emissions, noise, bearing, comms, and weapons
   solution quality.
7. Add hazard warnings, mitigation choices, and opportunity effects.
8. Add server-owned station cooldowns and shared system budgets.
9. Build the watch bar and environment panel, including cooldown indicators.
10. Add solar storm and communications dead-zone variants.

## Tests

- 1x and 4x produce equivalent simulated state to manual advance.
- Paused rooms do not advance.
- Empty rooms follow the configured unattended-room policy.
- Decision events interrupt fast mode before their deadline.
- Hazard transitions are deterministic at the same simulated time.
- Nebula changes noise and emissions without permanently corrupting contacts.
- Debris changes line of sight and can provide concealment.
- Hazard mitigation has both costs and benefits.
- Active sensor scans and station actions respect simulated-time cooldowns.
- Cooldowns behave identically under 1x, 4x, manual advance, pause, and reconnect.
- Shared system budgets prevent incompatible actions from running freely at the
  same time.
- Reconnects preserve simulated time, hazards, and mode.
- Browser/server timing cannot skip a major decision.

## Recommendation

Build this as a hybrid model, not pure real time. The 1x/4x idea is good for
immersion, but pause, manual advance, and automatic danger slow-down are needed
for a cooperative bridge game. Hazards then give the live clock something
interesting to make players react to instead of merely waiting for the next
scheduled event.
