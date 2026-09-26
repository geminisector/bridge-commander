# Ship art for a flavor

Everything the art question needs: where images come from, what to name them,
what size, and how they resolve.

## Three options

### 1. Reuse core art (default, zero work)

Point the hull's `art` at an existing core filename and ship no `assets/`
directory at all:

```json
"art": { "action": "friendly-cruiser.png", "vdu": "friendly-cruiser-vdu.gif" }
```

The resolver searches the flavor's own `assets/` first, then up the `extends`
chain, then the core image tree (`bridge/img`, or `ASSET_DIR`). A flavor that
re-skins in words only does not need a single image.

Core files to borrow from, by role:

| Role | Action | VDU |
|---|---|---|
| crew / home carrier | `friendly-cruiser.png` | `friendly-cruiser-vdu.gif` |
| corvette / escort | `friendly-corvette.png` | `friendly-corvette-vdu.gif` |
| transport | `friendly-transport.png` | `friendly-transport-vdu.gif` |
| prospector | `friendly-prospector.png` | `friendly-prospector-vdu.gif` |
| freighter | `friendly-freighter.png` | `friendly-freighter-vdu.gif` |
| carrier | `friendly-carrier.png` | `friendly-carrier-vdu.gif` |
| light cruiser | `friendly-light-cruiser.png` | `friendly-light-cruiser-vdu.gif` |
| hostile escort | `enemy-escort.png` | `enemy-escort-vdu.gif` |
| hostile fighter | `enemy-fighter.png` | `enemy-fighter-vdu.gif` |
| hostile medium fighter | `enemy-medium-fighter.png` | `enemy-medium-fighter-vdu.gif` |
| hostile heavy fighter | `enemy-heavy-fighter.png` | `enemy-heavy-fighter-vdu.gif` |
| hostile bomber | `enemy-bomber.png` | `enemy-bomber-vdu.gif` |
| hostile destroyer | `enemy-destroyer.png` | `enemy-destroyer-vdu.gif` |
| hostile cruiser / carrier | `enemy-cruiser.png` | `enemy-cruiser-vdu.gif` |
| hostile transport | `enemy-heavy-transport.png` | `enemy-heavy-transport-vdu.gif` |

### 2. Supply your own

```
bridge/flavors/<id>/assets/
  action/<stem>.png
  vdu/<stem>-vdu.gif
```

Then name `<stem>.png` in the hull's `art.action` and `<stem>-vdu.gif` in
`art.vdu`. `<stem>` is any filename you like; the examples use the hull's short
name (`miranda.png`, `miranda-vdu.gif`).

- **Size:** 128×128 is the bundle convention. Larger works but is downscaled by
  the UI; keep the ship centred with transparent or dark background.
- **Formats:** the resolver also accepts `.gif`, `.jpg`, `.jpeg`, `.webp`, and
  if the exact name is missing it tries the same basename with each other
  extension. So a `.png` action and a `.gif` VDU coexist fine.
- **Serving:** a flavor's own file is served at `/img/f/<id>/action/<file>`;
  core files keep the historical `/img/action/<file>`.

### 3. Generate placeholders

`tools/generate_placeholder_art.py` paints deterministic 128×128 labelled
placeholders (banner, silhouette, starfield, VDU scan). Notes:

- It needs Pillow: `pip install pillow` (not a runtime dependency).
- It currently paints the **core** catalog into `bridge/img/`. For a new setting,
  copy it and swap the hull table, or use it as a reference and generate art with
  any external tool.
- Deterministic output means the same hull id always paints the same image; keep
  that property if you adapt it.

Any external art pipeline (Aseprite, Blender renders, an image model, hand
drawing) is fine as long as the files land in the right directories with the
right names.

## If a hull has no art of its own

- Deleting `art.action`/`art.vdu` from an override inherits the parent's art —
  when you `extends` core and re-declare a core hull id, omitting `art` keeps the
  core image.
- A brand-new hull with `art` naming a file that resolves nowhere is a **load
  error** (fail closed), so name a core file or ship the image.
- If the action image is missing but the VDU resolves, the VDU is used as the
  action portrait so the UI has something to render.

## Licensing

Use art you have the right to ship: your own work, public-domain/CC0 assets, or
commissioned pieces. Fan art or screenshots from a third-party universe carry
the same exposure as naming that universe — a contributed flavor is the
contributor's responsibility. Third-party settings stay local examples and are
not added to `pyproject.toml` package-data (see the main skill, Phase 8).

## Per-hull art checklist

For every hull in `ships.json`:

- [ ] `art.action` names a file that resolves (flavor `assets/`, chain, or core).
- [ ] `art.vdu` names a file that resolves, or is `""`.
- [ ] If shipping files: they are under `assets/action/` and `assets/vdu/`,
      named consistently (`<stem>.png`, `<stem>-vdu.gif`).
- [ ] `.venv/bin/python -m bridge --check-flavor <id>` reports no art errors.
- [ ] `.venv/bin/python -c "from bridge.shared.ships import audit_ship_art; \
      print(audit_ship_art('<id>'))"` shows no `ERROR:` lines.
