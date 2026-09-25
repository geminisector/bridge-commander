# Ship Customization Plan

## Why

"Which ship are we flying, and how is it fitted?" is the first question any
bridge crew asks, and the current answer is thin: the bridge exposes **11 hulls**
from `shared/ships.py` with mass, profile, stealth, emission, sensor quality,
speed, crew and art — and no way to change anything.

The original ship catalogue already carried almost
everything a customization system needs:

| Table | Rows | What it gives us |
|---|---|---|
| `ship_types` | 182 | hull + `CraftType` (Strike Carrier, Destroyer, Corvette, Cruiser, Fighter…), `BaseAgility`, **per-arc armour** (`BaseFArmor/AArmor/LArmor/RArmor`), `BaseBody`, **shields** (`BaseFShields/AShields` + refresh), **component hit-location map** (`BaseComponents`), `Turrets`, `MaxGunners`, `Weapons`, `CargoHold`, `fuel`, `Faction`, `ProfileBonus`, art |
| `ship_weapons_link` | 583 | which weapon tags a hull can carry |
| `weapons` | 131 | tag, type, `ShieldByPass`, `LockTime`, `Spoofability`, `TurretArcSq`, and `hull_/shield_/armor_/system_damage` |

All the hulls named as examples are present: **Venture**, **Bristol**,
**Bengal**, **Fralthi** (plus Ralatha, Kamekh, Drayman, Tarsus, Longhaul, and
variants like `Fralthi-CL`, `Sabre-T`, `RapierII-WW`, `Kamekh-S`).

So this plan is not "invent a ship system"; it is **surface the chassis and
loadout data we already own, and give it a refit loop**.

## Design intent

- A ship is a **chassis + a loadout + a crew + an identity**, chosen under
  budgets.
- Choices must **change the watch**: a corvette is a stealth/screening problem,
  a strike carrier is a fighter-ops problem, a cruiser is a gun-and-shield
  problem.
- Customization must feed the mechanics other plans define: armour arcs and
  component damage (`WCRPG_INTEGRATION_PLAN`), fuel and engine class
  (`TRANSIT_AND_ENDURANCE_PLAN`), maintenance and spares
  (`ENVIRONMENTS_AND_MAINTENANCE_PLAN`), signature and layers
  (`SUBMARINE_INSPIRATION_PLAN`).

## The four layers

### 1. Chassis (hull)
Pulled from `ship_types`, curated into `resources/bridge_hulls.json` (a curated
subset first, then the full 182 with `Variant`/`BaseShip` grouping).

Carries: craft type and **size class**, agility, per-arc armour, body/SI,
shields and refresh, **component map**, hardpoints/turrets, max gunners, cargo,
fuel, faction, profile modifier, art, and a "role" for the UI.

### 2. Loadout (hardpoints and arcs)
From `ship_weapons_link` + `weapons`. Each hull's `Weapons`/`Turrets` entries are
hardpoints with an arc code (`HL1-LB`, `HL2-FB`, `V-LT`, `V-RT`, `TP-B/3`…).
A loadout assigns a weapon tag to each hardpoint, within what the hull can
carry, honouring:

- **arc coverage** (hard-point 45°, sponson 90°, barbette 180°, limited turret,
  full turret 315–360°),
- **magazine/ammo** and re-fire rate,
- **gunners** (`MaxGunners`) — you cannot man more hardpoints than you have
  gunners without penalty,
- weapon character: `ShieldByPass` (antimatter guns/torpedoes), `LockTime`,
  `Spoofability`, and the hull/shield/armour/system damage split.

### 3. Modules, power and sensors
WCRPG §7.2.2 accessories over the DB component map: ECM module, SWACS, repair
bay, auxiliary reactor, backup shield/sensor/comms, FTL drive (D/Morvan/
Akwende), fuel tank, cloaking device, countermeasure pods, ITTS, tracking
computer, gun cooler, shield regenerator, plus the fuel/maintenance hooks.

Each module occupies **power, mass/space, and a component slot**, and some add a
component hit location (so damaging them matters). Power budget is the reactor
output split between drives, shields, weapons, sensors/EW and jump charge
(`WCRPG_INTEGRATION_PLAN` alert ladder + `TRANSIT_AND_ENDURANCE_PLAN` heat).

### 4. Crew, identity and cosmetics
- **Crew complement** vs `MaxGunners`/crew need: under 90% triggers the
  Undermanned penalty; station skills come from `WCRPG_INTEGRATION_PLAN`.
- **Identity**: name, registry, faction livery, heraldry/nose art, bridge
  nameplate. Cosmetic only, but the name and silhouette should reach the plot
  and the handoff pack.

## The budgets (what makes it a decision)

A fit is only interesting if something has to give. Constraints:

| Budget | Limits | Fails when exceeded |
|---|---|---|
| Hardpoints/arcs | hull's `Weapons`/`Turrets` list | weapon cannot be mounted |
| Gunners | `MaxGunners` | hardpoints unmanned or penalty |
| Power | reactor output | brownouts: shields/weapons/sensors degrade |
| Mass/space | hull size class, cargo | agility/speed loss, no room for modules |
| Fuel | `fuel` + tanks | shorter range ring |
| Crew | complement | undermanned double-Checks |
| Spares/consumables | magazine + stores | can't reload / can't repair |

## Worked examples

| Hull | Class / role | Sketch (DB) | Playstyle |
|---|---|---|---|
| **Venture** | Corvette | agility 3, body 175, shields 25/25, 2 turrets (`V-LT`/`V-RT`), `FF/10` + `TP/10`, fuel 5, cargo 300 | light, fast, thin shields; scouting, screening, running |
| **Bristol** | Destroyer | body 220, shields 200/200, `HL2-FB`/`HL2-CB` + `HL-3` + `TP/20`, 2 gunners, fuel 5, cargo 900 | gun platform; poor agility, strong arcs |
| **Bengal** | Strike Carrier | body 400, shields 500/500, 5 turrets/hardpoints, `FDeck`, cargo 2200, 5 gunners, fuel 6 | fighter ops, hangar launch/recover window |
| **Fralthi** | Kilrathi Cruiser | body 330, shields 300/200, `HL1-FB`/`HL1-SB` + `AMG-2` (shield-bypass) + `TP-B/2`, sensors 60, fuel 6 | balanced raider; AMG threatens through shields |

These four alone give four genuinely different watches, which is the point:
hull choice is scenario design.

## The loops

### Refit loop (between missions)
Shipyard/drydock: choose hull, fit hardpoints/modules, assign crew, name the
ship. Costs **time, credits and resources**; the fit is saved as a **blueprint**
so a crew can standardise or experiment. Output is the next mission's ship.
Deadline: the mission window and the treasury.

### Field-modification loop (during a watch)
You cannot always wait for a yard. **Hot-swap** a mount, **jury-rig** a
hardpoint, or **cannibalise salvage** (debris fields, prizes) for a module or
spare — each a DC Check, consuming time and spares, at risk of making it worse
(`ENVIRONMENTS_AND_MAINTENANCE_PLAN` repair-in-hazard). This is how a fit
changes mid-campaign.

### Component damage / repair loop
`BaseComponents` already defines hit locations with HP (Bridge, Engines, Nose,
FDeck, hardpoints, Life_support, Computer, Accel_Absorbers, Fuel_Tank,
Communications, Sensors, Weapons, Cargo). Damage lands on a location; the
weapons/DC stations feel it immediately. Ties the customization layer to the
system-damage and maintenance phases — a fit decides *what you have to lose*.

### Doctrine / identity loop
The hull defines the patrol's shape: a corvette wants to see and not be seen; a
destroyer wants a gun fight; a carrier wants to survive long enough to launch.
Campaigns should state a recommended hull, and victory conditions should read
differently for each.

## Data model, protocol, UI

- `shared/types.py`: `HullSpec` (extends today's `ShipClass` with craft type,
  size class, armour arcs, body, shields, component map, hardpoints, gunners,
  cargo, fuel, role), `Hardpoint {id, arc, weaponTag, ammo}`, `ShipLoadout
  {hullId, hardpoints[], modules[], crew, cosmetics}`, `ShipInstance` (persisted
  per guild).
- `resources/bridge_hulls.json` (curated catalog derived from the DB) and
  `resources/bridge_modules.json`; a loader in `shared/ships.py` next to the
  existing `SHIP_ART` resolver.
- Protocol: extend `admin.reset {shipId}` / `admin.setShip` with a loadout
  payload; add `ship:refit {loadout}`, `ship:fieldMod {hardpoint, module}`,
  `ship:rename`; the crew's own seats see their hardpoints.
- UI: **GM shipyard** (hull browser with stats/art, hardpoint diagram over the
  arcs, module slots, budget meters, blueprint save/load) and a **crew loadout
  card** on the Weapons/Command stations; the handoff pack carries hull, name,
  registry, arcs, shields, component damage and loadout.
- Validation: reject a fit that exceeds hardpoints, gunners, power, mass or
  cargo, with a clear reason (same pattern as the weapon-solution refusals).

## Integration

- **WCRPG** — components are the system-damage table; armour arcs, shields,
  modules and the alert ladder are already specified there.
- **Sensors/EW** — array quality and modules set the sensor station's numbers;
  stealth profile feeds the detection race and the submarine datum loop.
- **Transit/Endurance** — hull `fuel` and engine class set the range ring;
  cargo and mass trade against range.
- **Maintenance** — each module has wear and spares; a heavily fitted ship has
  more to maintain.
- **Ship art** — `ship_types.action_url`/`vdu_url` already drive
  `SHIP_ART_MAPPING_PLAN`; variants should map to their base art explicitly.
- **Victory/handoff** — hull identity and component state travel with the pack.

## Tests

- Catalog loads; every curated hull maps to real art and a component map.
- Hardpoint/gunner/power/mass/cargo budgets reject invalid fits with a reason.
- Arc coverage computes correctly and a target aspect (fore/aft/beam) changes
  which hardpoints bear.
- Component HP round-trips persistence and appears in the handoff.
- A loadout change alters the handoff and the station UI.
- Blueprints save/load; a refit costs the documented time/credits.
- Field modification applies its DC and can fail destructively.
- Variant hulls resolve to their base art, not a neighbour's.

## Roadmap placement

Depends on the component/shield model (Phase 3), fuel/engine data (Phase 4) and
modules/maintenance (Phase 8). Insert as its own phase before content/release:

- **P9 — Shipyard & loadout**: P9.1 hull catalog, P9.2 hardpoints/arcs loadout,
  P9.3 modules/power budgets, P9.4 refit/blueprints/field-mod, P9.5 identity and
  handoff.
- **P10 — Content & release** (formerly P9): barriers, small craft, prize/
  boarding, trade, mission integration, polish.

Hull *selection* already exists (`admin.setShip`/`reset {shipId}`) and should
keep working from day one; this phase makes it a real fit, not a label.
