# BRIDGE COMMANDER (Python)

Standalone Python implementation of the fleet bridge simulator. The browser
activity and GM console are bundled with the server and use the camelCase
WebSocket protocol defined in `bridge/shared/protocol.py`.

## Layout

```
bridge/
  activity/dist/  player UI
  img/            128x128 placeholder hull, terrain, and contact art
  resources/      events, hazards, environments, hulls, and modules
  server/         FastAPI, WebSocket, persistence, engine, and GM console
  shared/         types, constants, math, flavors, campaigns, events, and protocol
mods/             settings (mods) as data at the project root: core plus examples
tests/            shared, engine, flavor, protocol, and server integration tests
pyproject.toml    install, test, lint, type-check, and package metadata
```

The project requires Python 3.12 or newer and has no external service
dependency.

## Plans and status

`ROADMAP.md` is the sequencing index; each plan below is the detailed spec for
its area. Status is the roadmap's current-state view.

| Plan | Covers | Status |
|---|---|---|
| `ROADMAP.md` | phase order, dependencies, exit criteria, milestones | living index |
| `COMMS_WEAPONS_PLAN.md` | transmission modes, IFF, weapon states, solutions | done |
| `HAZARDS_AND_REALTIME_PLAN.md` | time modes, hazards, cooldowns, watch bar | done |
| `SENSORS_EW_MINIGAME_PLAN.md` | barcode, passive minigame, blind tagging, catalogue | done |
| `SHIP_ART_MAPPING_PLAN.md` | canonical art data file, resolver, audit, contact sheet | done (P0) |
| `WCRPG_INTEGRATION_PLAN.md` | d20 Checks, skills, shields/arcs, system damage, manoeuvres, EHD | P1–P3 done; P7 done (EHD, manoeuvres, subsystem strikes, ordnance, spoofing) |
| `TRANSIT_AND_ENDURANCE_PLAN.md` | fuel, range ring, ETA/CPA, astrometrics, jumps, heat, crew | P4–P5 done; P8 partly (heat, watch bill); consumables/environments planned |
| `SUBMARINE_INSPIRATION_PLAN.md` | datum/hunt, signature layers, sprint/drift, TMA, baffles | P6 done (datum, sprint/drift, baffles, layers, TMA, hunters) |
| `ENVIRONMENTS_AND_MAINTENANCE_PLAN.md` | 9 environment types, wear vs damage, repair-in-hazard | P3b + P8b done (wear/repair, catalog, spares/salvage/contamination) |
| `SHIP_CUSTOMIZATION_PLAN.md` | hull catalog, hardpoint loadout, modules, refit, identity | P9 done (15 hulls, arc-coded hardpoints, modules, handoff identity) |
| `CREDITS.md` | attribution and licensing (WCRPG CC BY-NC-SA, non-commercial) | reference |
| `MANUAL.md` | **player-facing** watch manual: controls, the loops, cheat sheet | read this to play |

Hull art is chosen by `resources/bridge_ship_art.json` and checked by
`shared/ships.audit_ship_art()`. The bundled images are generated 128x128
placeholders, one per hull plus terrain and unknown-contact fallbacks.

## Install

```bash
python -m pip install -e ".[dev]"
```

For a runtime-only installation, use `python -m pip install .`.

## Verify

```bash
python -m pytest
ruff check bridge tests
mypy bridge
```

## Running

```bash
python -m bridge                               # PORT=8787 by default
# After installation, the equivalent console command is:
bridge
```

Environment (see `server/config.py`): `HOST`, `PORT`, `CORS_ORIGINS`, `DATA_DIR`,
`ADMIN_HOST`, `ADMIN_PORT`, `ADMIN_TOKEN`, `ADMIN_ORIGINS`, `ACTIVITY_DIST`,
`ASSET_DIR`, `FLAVORS_DIR`, and `DEFAULT_FLAVOR`. The server binds to
`127.0.0.1` by default; set `HOST=0.0.0.0` only
behind an appropriate access-control layer.
When the built activity dist is present it is served from `/`; the client
WebSocket is `/ws`. The GM builder is a second FastAPI app on `ADMIN_PORT`
(websocket at `/`).

The activity bundle is auto-discovered from `ACTIVITY_DIST` (a directory
containing `index.html`) or the packaged `bridge/activity/dist`. Contact art
referenced at `/img/...` is served from `ASSET_DIR`, defaulting to packaged
`bridge/img`.

### Voice

Each game room has a **VOICE** tab that embeds an audio-only [Jitsi
Meet](https://jitsi.github.io/handbook/docs/dev-guide/dev-guide-iframe/) call, so
the crew can talk while they work different stations. The call keeps running when
a player switches tabs; it ends only when they leave it.

The room id is a **UUIDv5 derived from the watch and its mission**
(`server/voice.py`) rather than a random one, which is what makes it work with no
coordination at all:

- everyone playing that mission computes the identical UUID, so they all land in
  the same call — nobody has to share a link;
- it is stable across reloads, reconnects and restarts, because nothing is
  stored;
- it is mission-scoped, so switching missions moves the crew to a fresh room
  instead of dropping a new game into the last one's channel. Every client sees
  the same state, so they regroup together rather than splitting.

It is a *name*, not a credential: anyone who knows the channel, instance and
mission ids can derive it, so it hides a room from casual guessing but does not
make a public Jitsi instance private. For a private table, point `JITSI_DOMAIN`
at your own deployment.

| Variable | Default | Purpose |
|---|---|---|
| `JITSI_DOMAIN` | `meet.jit.si` | Jitsi Meet host to embed. An **empty** value hides the tab. |

Two limits are worth knowing before a session:

- **The microphone needs a secure context.** `getUserMedia` only works over
  `https://` or on `localhost`. The default `http://127.0.0.1:8787` is fine for
  the machine running the server, but a player opening `http://192.168.x.x:8787`
  gets no microphone at all. Put the app behind TLS (a reverse proxy, or
  `mkcert` with the CA trusted on each device) for LAN play.
- **The public `meet.jit.si` is no longer anonymous** — since 8x8 ended anonymous
  meetings there, someone has to sign in as moderator to start a room, and a
  publicly-guessable room name can be joined by anyone who guesses it. For a
  private table, point `JITSI_DOMAIN` at your own Jitsi deployment.

### Settings (flavors)

A **flavor** is a setting — a mod — as data: a directory under the
project-root `mods/` folder (the wheel falls back to the packaged
`bridge/flavors` tree, which ships `core`). The **directory name is the id**, and
the conventional files (`units.json`, `theme.css`, `ships.json`,
`callsigns.json`, `missions/`) are discovered automatically, so `cp -r` of an
existing flavor is all it takes to start a new one. `flavor.json` is an optional
manifest for a `title`, an `extends` parent, a `defaultMission` or a
non-standard path. `core` is the shipped default; `wc`, `stk` (Star Trek) and
`sw` (Star Wars) are worked examples of the seam.
A flavor is **standalone by default** and carries its own hull catalog, missions
and theme; naming a parent with `extends` opts into inheriting one instead. It
ships no code (see `FLAVOR_PLUGIN_PLAN.md` for the design and `mods/README.md`
for the authoring guide).

```bash
python -m bridge --list-flavors         # installed settings, hull/mission counts
python -m bridge --check-flavor wc      # load + validate one flavor, exit 1 on error
python -m bridge --flavor wc            # load wc at boot
```

Installed settings are **inert until loaded**, and **one mod is loaded at a
time**: the GM console's *Mods / settings* panel loads a mod and unloads every
other — `core` included — rebuilding live rooms onto it; the choice persists in
the rooms database. `DEFAULT_FLAVOR` / `--flavor` loads a setting at boot, and
`--flavor` persists it. A room whose mod was unloaded, or whose package was
removed from disk, is rebuilt onto the loaded setting and stays playable.

Units, theme, hulls, art, callsigns and missions are independently flavorable.
Distances and speeds stay canonical (`klik`, `kps`) everywhere on the wire and in
the simulation; `units.json` only changes how a value is *displayed*. A flavor
that fails validation does not half-load: the server logs the reason and plays
that room on `core`. Rooms record their `flavorId` in state, so a reconnecting
client renders the same units and art.

### Activity UI styling

The player-facing bundle in `bridge/activity/dist` is hand-maintained (no build
step): `index.html` is the shell, `activity.js` renders the stations, and
`activity.css` carries the whole look. It follows the deep-space "sector hub"
design language credited in `CREDITS.md`:

- the shared `starfield.svg` tiled and fixed behind the whole app, with a
  translucent nebula/vignette wash layered over it;
- the `#0b0d17` / `#151928` palette, `#00f0ff` accent and glow shadows;
- Zen Dots headings over Share Tech Mono readouts (loaded from Google Fonts,
  with system fallbacks when offline);
- glowing, hover-lifting cards around the sensor, command, ops, comms,
  catalogue and log panels.

Because it is a static bundle, editing those files is served immediately — no
rebuild or restart. `ActivityPanel` changes that touch the wire protocol still
need the matching `shared/` change; see the port notes below.

### Launching the admin panel

The admin panel is disabled unless `ADMIN_PORT` is set. A non-empty
`ADMIN_TOKEN` is then required; the app fails closed if either setting is
missing. From the repository root, configure an admin port and token, then
start the server:

```bash
export ADMIN_PORT=8788
export ADMIN_TOKEN=replace-with-a-long-random-token
python -m bridge
```

Scheduled campaign events are configured in `resources/bridge_events.json`.
Each campaign maps to an ordered list of `{ "atMinute": ..., "template": ... }`
entries. The minute is the base trigger time; the existing seeded 0–40 minute
variation is still applied per engagement. `template` names refer to the event
builders in `bridge/shared/events.py`.

Open <http://localhost:8788/> in a browser and enter the value of
`ADMIN_TOKEN`. The panel connects to the admin WebSocket on the same port.

These settings can also be placed in a `.env` file next to the server:

```dotenv
ADMIN_PORT=8788
ADMIN_TOKEN=change-me
ADMIN_ORIGINS=http://localhost:8788
```

Use a long, private token outside local development. Set `ADMIN_ORIGINS` to
the origin hosting the admin page when accessing it from another host.

## Sessions (one per connection)

Seats and host authority belong to a **connection**, not to a user.  Each client
sends a per-tab `sessionId` in `hello` (kept in `sessionStorage`, so a reconnect
in that tab resumes its seat while a second tab is a separate session); the
server echoes it as `hello.clientId` and mints one when absent. `Room.clients`
is keyed by that session id, `SeatPlayer.sessionId` records the holder, and
`GameState.hostSession` names the host connection. A disconnected session keeps
its seat reserved for reconnect; another live session can claim that seat when
needed, and a server restart clears stale occupants.

This matters on the web/dev path: every tab on one machine shares a
`localStorage` user id, so keying by `userId` made the second tab overwrite the
first's client record — and a `setSeat` then released the *other* tab's seat.
On Discord each participant has a distinct user id, so 3+ real users were
already fine; the session keying also makes multiple tabs per user safe.

## Port notes

- State lives in Pydantic models in `shared/types.py`. JSON keys stay camelCase
  because the frontend and persisted rows are shared with the TS server.
  `ShipState.className` is aliased to the wire key `class`, and
  `GameState.schemaVersion` to `schema`.
- `shared/math_utils.hash_random` faithfully emulates the JS float64 + `ToInt32`
  arithmetic (a plain 32-bit mask, as sketched in MIGRATION.md, produces
  different numbers). Values are locked by `tests/test_shared.py`.
- `Room.broadcast`/`reset` are `async`; the server-to-client message models give
  `type` a default so they can be constructed server-side.
- `admin.event` payloads are parsed permissively and sanitised by
  `admin_events.clean_event`, matching the TS server.

Set `ADMIN_PORT` and `ADMIN_TOKEN` to enable the Python GM console. It is
served at `http://localhost:<ADMIN_PORT>/`; the browser connects to the admin
WebSocket on that same origin. See `.env.example` for the available settings.

## Ships, sensors and obstacles

`shared/ships.py` is the hull catalog the GM builds a scenario from. Every hull
has a **mass** (feeds the gravidar), a radar **profile** (feeds active radar), a
**stealth** rating and an **emission** level (both feed passive listening), plus
speed/sensor-quality stats. The admin console can set the crew hull for a new
engagement (`admin.reset { shipId }`), change it live (`admin.setShip`), and
assign a hull to any contact (`admin.spawn`/`admin.update { shipClass }`).

The sensors run **together**, not as exclusive modes:

| Sensor | State | Resolves |
|---|---|---|
| Passive | always on | angular precision; emission, type and the frequency barcode |
| Gravidar (towed) | on while making way | mass heat map: good bearing, **OK (approximate) distance** |
| Active radar | toggled (`sensor:active`) | good precision: range, bearing, elevation |
| EM / motion | always on | target course and speed — scrambled by sun glare and fields |

Terrain (`asteroid`, `nebula`, `debris`, `dust`, `ice`) also acts as a sensor
obstacle. `OBSTACLE_EFFECTS` defines how much each **blocks** line of sight,
**scatters** bearing/range, and **reflects** (ice is the extreme: it refracts a
mirror-image ghost return). Occlusion is geometric — an obstacle attenuates any
line of sight passing within `radiusKlik * OBSTACLE_LOS_INFLUENCE` of it.

Hull art is resolved from `resources/bridge_ship_art.json`, verified against the
packaged `img/` tree, and exposed on each contact as `image` with a VDU fallback.
Terrain art comes from `TERRAIN_IMAGES`. All bundled art is 128x128 placeholder
imagery and is served at `/img` by the bridge.

## Detection race, anonymity, buoys and crybabies

The patrol is now a race, and the plot no longer spoils it:

- **Anonymity.** Every internal contact carries a `trueName` (the
  vessel/military/place name) and a displayed `name`. Player broadcasts redact
  truth, position, faction, hull data, and art for undetected tracks; only the
  anonymous designation (`TRACK-01`) is sent. Confirmation releases the real
  name. The authenticated GM channel still receives the complete internal
  state. Terrain and GM-named opposition obey the same rule.
- **Win / lose.** The patrol is won three ways, and lost one
  (`_check_patrol_win`, `_painted`):
  - **Endurance** — `ENDURE_MINUTES` (360, six hours) have passed since the
    patrol began and no hostile ever built a working track on the crew ship
    (`Contact.everTrackedUs`, set once a hunter's `lock` reaches
    `DETECTED_LOCK`). Weapons must be safe. Fly dark and let the watch pass.
  - **All tracked** — every hostile is detected and at least `tracking`, with
    weapons still safe (`roe == "safe"`). Resolving a spectral barcode
    (`sensor:listen` until `waveform.resolved`) and calling the track correctly
    (`sensor:claim`) is the reliable path; a bare guess is worth far less.
  - **Disengaged** — every hostile has cleared `DISENGAGE_RANGE_KLIK` (120,
    outside every sensor envelope) and at least one had closed inside it first,
    so a campaign cannot start already won. This one does not require weapons
    safe: surviving to watch the lane empty is the win whatever the posture.
  - You **lose** when a hostile's `lock` reaches 1.0: it has a firing solution
    on you. Any result is terminal (`status == "ended"`, `outcome` set, digest
    sealed). Going weapons-hot before the picture is complete is a choice to
    fight, so it takes the engagement/handoff path instead of the all-tracked
    win.
  - Three campaigns are built around these conditions (`shared/campaigns.py`):
    **Silent Vigil** (endurance — six hours dark while a hunter-killer screen
    sweeps past), **The Empty Lane** (disengagement — hold the box while a
    raider squadron transits out), and **Full Sweep** (all-tracked — find and
    hold a track on every hull of a wolfpack lying dark).
- **Enemy lock.** `_enemy_detect` accumulates each hostile's track on the crew
  ship from your own emission (masked by hull stealth), radar cross-section,
  whether the hunter is radiating, range and terrain occlusion. Quiet running
  and a smaller hull delay it; flank speed and active radar feed it.
- **Ship catalogue.** Every `sensor:listen` pass refreshes
  `SensorReadout.catalogueMatches`. Candidates are the actual hulls in
  `SHIP_CLASSES` — all of them, best match first — not broad contact
  categories: the passive barcode picks the exact hull, and a contact only the
  gravidar has found falls back to its emission spectrum ranked against each
  hull's type. Terrain returns no ship candidates. A tag still commits to the
  winning hull's `contactType`.
- **Sensor buoys.** The ops seat drops an immobile passive buoy
  (`nav:deployBuoy`, 2 aboard). It listens as an independent sensor origin, and
  once the ship and a buoy both hold a bearing the engine cross-fixes the range
  (`_triangulate`) and grades the confidence up. Recover it by clicking it on
  the ops plot (`nav:recoverBuoy { buoyId }`), which returns it to the rack.
- **Noisemakers (crybabies).** Two per ship (`ew:noisemaker`). A launch floods
  the EM band for `NOISEMAKER_TURNS` turns: enemy lock accumulation drops to a
  fraction and any building track is broken, at the cost of your own passive
  and EM hearing while it sings.
- **Consequences.** Unanswered decision events expire for a tension penalty;
  `EventEffect.loseTrack` (with an optional `targetId`) now actually drops a
  track; `EventEffect.handoff` makes an engagement option build the real
  handoff pack and pause the patrol. Active radar, manual sweeps and the noise
  filter draw on the battery, and the radar/filter refuse to run below
  `BATTERY_MIN_ACTIVE`. Readiness wears with hard running and recovers at rest,
  and each tension tier sends searching hunters into the patrol box.
- **Slower sensors.** `PASSIVE_ACQUIRE_THRESHOLD` (20) and
  `PASSIVE_SAMPLE_SCALE` (32) mean a contact needs several watch steps of
  accumulated listening before it appears on the passive grill. The gravidar
  now acquires like a real sensor too: `GRAVIDAR_RANGE_KLIK` (50) with
  `GRAVIDAR_ACQUIRE_THRESHOLD` (3.0) means a heavy, fast-crossing hull firms up
  in a look or two while a distant fighter takes most of a watch — the plot no
  longer fills in on the first tick. `WAVEFORM_LISTEN_PROGRESS` (0.15) means a
  spectrum takes ~7 listen passes to read. Confidence gains across passive,
  gravidar, active, optics and buoys were all cut. `ENEMY_LOCK_MINUTES` (135)
  keeps the race winnable at that slower pace.
- **Ops payoffs.** The ops seat drops and recovers passive sensor buoys
  (`nav:deployBuoy` / `nav:recoverBuoy`), plots helm and search patterns, and
  files fleet intel reports (`intel:report`). A confirmed, correctly classified
  report pushes `war.frontLine` out and settles tension; a bearing-only report
  is worth less; a wrong call hands ground back. `frontLine` is no longer
  write-only.

`nav:speed` now orders a real speed on the 0-100 dial (`ship.speed`), with
`nav:mode` naming the bucket; 0 genuinely holds station, and the hull's own
`quietSpeed`/`cruiseSpeed`/`maxSpeed` are what the modes resolve to.

## Comms, IFF and firing solutions

The comms watch has its own little war of nerves, and the weapons bay dresses
the tubes with a mount-specific solution.

- **Transmission modes.** `comms:transmit { mode }` sends `tight-beam` (+2
  exposure), `burst` (+5), `open` (+10) or `spoof` (+7 and +6 tension). The mode
  is the trade: a tight beam is cheap but slow to pass, an open call is loud.
- **IFF.** `comms:iff` interrogates a track's transponder. A legitimate hull
  answers cleanly and `Contact.iffConfidence` climbs to 0.85; a hostile may
  squawk a false type (low trust), answer truly and go comms-dark (0.35), or be
  caught. The spoof-detection roll starts at `IFF_SPOOF_DETECT_BASE` (0.35) and
  climbs `IFF_SPOOF_DETECT_PER_CHALLENGE` (0.25) per repeat challenge, with a
  resolved spectrum worth a further `IFF_SPOOF_DETECT_SPECTRUM` (0.2). A catch
  sets `Contact.spoofDetected` and collapses `iffConfidence` to zero — work the
  track and you will unmask it.
- **Weapons states** stay `safe` / `standby` / `armed` / `locked`; only a
  hostile armed/locked solution moves RoE to HOLD, so the rules of engagement
  behave exactly as before.
- **Mount-specific solutions.** `shared/weapons.py` is the crew catalog: laser
  cannon and mass driver (short envelope, little asked), particle cannon, heat
  seeker, imaging missile and torpedo (long envelope, a *confirmed* track and a
  high required grade). `weapons:prep { contactId, state, weapon, shot }` builds
  a solution graded 0..1 from the contact's confidence (a resolved spectrum adds
  `SOLUTION_SPECTRUM_BONUS`):
  - a **quick shot** waives `QUICK_SHOT_RELIEF` (0.15) of the mount's
    requirement but is charged `QUICK_SHOT_EXPOSURE` — fast and loud;
  - a **refined shot** keeps the full requirement and adds
    `REFINED_SHOT_BONUS` (0.12) of margin — patient and quieter.
  Out-of-envelope, unconfirmed-track and too-rough-solution attempts are
  refused into `standby` with a reason in the log rather than silently locking.
  `ShipState.weapon`, `solutionQuality` and `shotType` are carried into the
  handoff pack (`HandoffWeapons`), and the pack summary names the mount and shot.
  `ShipState.weaponTarget` names the contact the solution is held on; the
  activity UI swaps that contact's generic silhouette for its hull picture once
  the solution is `locked` — on the ops plot, the sensor card and the contact
  board — and offers per-contact PREP/LOCK controls with a mount/shot picker.
- **Decision events with teeth.** `EventEffect` grew `relay` (bounce the traffic
  and spare the signature), `challenge` (run a challenge-response, no extra
  exposure), `civilian` (a neutral hull crosses the box) and `falseSurrender`
  (resolve a surrender call — a genuine prize or a trap that spawns a close
  escort). Templates `relay`, `challenge`, `civilian` and `false-surrender` live
  in `shared/events.py`; the GM can set the same effects through `admin.event`,
  sanitised by `admin_events.clean_event`.
