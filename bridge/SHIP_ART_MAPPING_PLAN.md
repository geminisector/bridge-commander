# Ship Art Mapping and Validation Plan

## Problem

Some bridge contacts display the wrong ship art—for example, an `enemy-cruiser`
contact currently resolving to an `enemy-destroyer` image. This makes the visual
identification game unreliable and can spoil or contradict the sensor
information.

## Goals

- Every ship class resolves to its own canonical action and VDU art.
- Unknown or missing art uses an explicit unknown silhouette, never another
  ship's image.
- The same mapping is used by contacts, player ship displays, handoff packs, and
  the admin console.
- Mapping errors fail validation before deployment.

## Inventory and canonical naming

Create an inventory of the available assets under `img/action` and
`img/vdu`, recording:

- Canonical ship class ID.
- Display name.
- Action image path.
- VDU image path.
- Faction and role.
- Source asset and any aliases.

Normalize naming differences such as `enemy-cruiser`, `ENEMY-CRUISER`,
`enemy-cruiser.png`, and legacy hull names into one canonical ID. Do not infer a
missing mapping by falling back to a neighboring ship class.

The crew's `home` hull and the hostile `enemy-cruiser` are the same class flown
by both sides, so they share one silhouette. They still own distinct art files
(`friendly-cruiser.png` and `enemy-cruiser.png`) so the one-file-per-class rule
holds; the duplication is **intentional** and recorded here rather than fixed by
splitting the drawing.

## Data-driven mapping

Add an editable resource such as:

`resources/bridge_ship_art.json`

Example shape:

```json
{
  "enemy-cruiser": {
    "action": "/img/action/enemy-cruiser.png",
    "vdu": "/img/vdu/enemy-cruiser-vdu.gif"
  },
  "enemy-destroyer": {
    "action": "/img/action/enemy-destroyer.png",
    "vdu": "/img/vdu/enemy-destroyer-vdu.gif"
  }
}
```

The mapping should support aliases explicitly, but aliases must point to the
canonical class rather than silently selecting another image.

## Resolver behavior

Centralize art lookup in one resolver used by all bridge code:

1. Normalize the requested ship class.
2. Resolve an explicit canonical mapping.
3. Verify the referenced file exists.
4. Return the mapped action/VDU paths.
5. Return the unknown silhouette when no valid mapping exists.
6. Log a warning and expose a diagnostic reason for missing or invalid art.

Remove independent image-selection logic from contact construction, ship
loading, and admin presentation.

## Asset audit

Build a one-shot audit command that reports:

- Classes with no mapping.
- Mappings pointing to missing files.
- Multiple classes sharing an image unexpectedly.
- Assets with no class mapping.
- Aliases that resolve inconsistently.
- Case-sensitive path failures on Linux.

The audit should specifically assert that `enemy-cruiser` and `enemy-destroyer`
resolve to different assets and that each points to the intended hull.

## Visual verification

Generate a contact-art contact sheet labelled with canonical class IDs. Include
both action and VDU variants so humans can quickly spot swapped, duplicated, or
mislabelled files.

For ambiguous legacy assets, record the decision in the inventory rather than
guessing based on filename. If an asset cannot be confidently identified, map
it to an unknown or provisional class until verified.

## Integration changes

- Populate `Contact.image` and `Contact.vdu` only through the central resolver.
- Populate player ship art through the same resolver.
- Include the canonical art ID in serialized state for debugging.
- Keep art paths separate from sensor class tags so visual art does not reveal a
  blind sensor identification.
- Ensure the admin console uses the canonical class/art mapping when spawning or
  editing contacts.

## Tests

- Every canonical class has a valid mapping.
- Every mapped file exists.
- `enemy-cruiser` and `enemy-destroyer` resolve to distinct expected paths.
- Case and legacy aliases resolve to the same canonical class.
- Unknown classes use the unknown silhouette.
- Missing assets never fall back to a different known ship.
- Contact and player ship construction use the resolver.
- Serialized contacts preserve the resolved art paths.
- Sensor tags do not change or reveal the art resolver’s true class.

## Implementation order

1. Inventory the current image tree and current resolver behavior.
2. Define canonical ship IDs and aliases.
3. Add `bridge_ship_art.json` with verified mappings.
4. Implement and adopt the central resolver.
5. Correct `enemy-cruiser`/`enemy-destroyer` and all other discovered mismatches.
6. Add the audit command and contact-sheet generator.
7. Add unit/integration tests and make the audit part of CI or startup checks.
8. Remove legacy fallback mappings once all assets are verified.
