# Bridge Commander — credits and licensing

Bridge Commander is an **unofficial, non-commercial project**. It is a free,
tabletop-assisted bridge simulator; it is not affiliated with, endorsed by, or
licensed by any rights holder.

## Setting and hull catalogue

The setting, ship classes, faction callsigns, place names and terminology are
**original to this project**. Hulls use role-bearing, faction-neutral names
(`Friendly_Cruiser`, `Enemy_Destroyer`, …) so the same mechanics can be
re-flavoured; see `FLAVOR_PLUGIN_PLAN.md`. The project depicts no third-party
universe and ships no third-party artwork.

## WCRPG mechanics

Many of the mechanics implemented across Phases 1–9 are **ported from the
WCRPG (Wing Commander Role Playing Game) rules**, by Stephen A. Rogers and
contributors, published under a **Creative Commons
Attribution-NonCommercial-ShareAlike** licence.

We port **mechanics, not text**: dice conventions, the skill catalogue, the
crit and damage bands, shields and defence arcs, manoeuvre effects and EHD are
re-implemented in our own code and our own words. Where a rule was adapted, the
adapted form and its reason are recorded in the plan documents under
`bridge/` (notably `WCRPG_INTEGRATION_PLAN.md`, which carries an
implementation note explaining that we resolve Checks on a **d20** for
consistency with the rest of CombatBot, rather than the book's d%). Hull and
drive names in the shipped catalogue are our own neutral vocabulary, not the
rulebook's setting terms.

WCRPG is itself a game set in the *Wing Commander* universe, which is the
property of its respective rights holders (Electronic Arts and/or Origin
Systems). Bridge Commander claims no rights to that material and ships no
*Wing Commander* game artwork.

Attribution: *WCRPG — The Wing Commander Role Playing Game*, used under
CC BY-NC-SA. This project is non-commercial and any reuse of the ported
mechanics must carry the same attribution and licence.

The WCRPG rulebook PDF is **not** committed to this repository; it is
git-ignored and used for design reference only.

## Design language

The player UI's palette, typography and card language follow the **Gemini
Sector Hub** design language (`geminisector.github.io`). This is a visual-style
credit only; no setting content is taken from it.

## Other material

- Hull statistics are project data derived from the bridge ship catalogue.
- Environment, drive, module, event, hazard, hull and nav-point catalogues under
  `resources/` are original project data authored for Bridge Commander.
- The 128x128 images under `img/` are generated placeholders. Regenerate them
  with `tools/generate_placeholder_art.py`.

## Plans

The phase plans in `bridge/` are the working design record. The
roadmap that sequences them is `bridge/ROADMAP.md`; the README's
"Plans and status" table is the index.
