# Working on zonecraft itself

This repository is the zonecraft Claude Code plugin (the repo root is the plugin root). It is not a mod: there is no
`mod.json` here, and tools that need a mod take `-Mod` or run from inside a mod folder.

- `skills/zonecraft/SKILL.md` is what Claude loads in a mod session: the rules and the map of `knowledge/`. Read it
  first; its rules apply here too.
- Layout: `knowledge/` (what is known), `tools/` (`setup/`, `build/`, `editor/`, `blueprints/`, `pak/`, shared
  `common.ps1` / `hconf.py` / `config.json`), `templates/` (a new mod's files), `probe/`, `tests/`, `assets/` (logo,
  icon generator), `.claude-plugin/` (manifest, marketplace, icon).
- Tools find the mod by walking up from the current folder to `mod.json`; never assume a tool runs from this repo.
- Keep everything generic: no mod-specific history (that goes in a mod's `zonekit/README.md`) and no user- or
  machine-specific values (paths and accounts belong in `%LOCALAPPDATA%\zonecraft\settings.json`).
- The repo is public: nothing private (credentials, emails, personal files) in knowledge, tools or commit messages.
- Before pushing: `py -I tests/test_bp_nodes.py`, `py -I tests/test_gamedata.py`, `py -I tests/test_conflicts.py`, `claude plugin test .`, `claude plugin validate .`, and bump `version` in
  `.claude-plugin/plugin.json` for a release (installed copies update only on a new version).
- The logo and the icon come from `assets/make_logo.py` (`<out>.gif` for the logo, `<out>.png` for the icon).
  Clawd's scenes come from `assets/clawd_scenes.py`: `hooks/clawd.ts` for the panels, `assets/clawd` for the README
  GIFs, `<out>.png sheet` to check every scene on light and dark. Regenerate all three after changing a drawing.
  The README's panel pictures come from `assets/make_screens.py assets/screens` (example content; redraw them when a
  panel's layout changes, or replace them with real screenshots).
