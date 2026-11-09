# Mods and zonecraft: new mods, updates, sharing what you learn

zonecraft (the Claude Code plugin) holds the tools, the knowledge and the templates. A mod folder holds only the mod.
Nothing of zonecraft is copied into a mod, so there is nothing to sync: updating the plugin updates every mod at once.

## Ownership
| Path | Owner | Changes by |
|---|---|---|
| zonecraft (`tools/`, `knowledge/`, `templates/`, `skills/`) | the zonecraft repo | commits there; reaches every PC as a plugin update |
| machine settings `%LOCALAPPDATA%\zonecraft\settings.json` | this PC | `setup.ps1` / `new_mod.ps1`; shared by every mod, never committed |
| `<mod>/zonecraft.local.json` | one mod on this PC | rare per-mod override (gitignored) |
| `CLAUDE.md`, `mod.json`, `PLAN.md`, `BUILD.md`, `README.md`, `zonekit/**`, `.gitignore` | the mod | normal commits |

The mod's `CLAUDE.md` tells Claude to load the `zonecraft` skill first, so every session in every mod gets the shared
rules.

## New mod
When the user wants a new mod but has not described it (or only loosely), open the New mod form (the
`new_mod_form` tool; the user can also type `/zonecraft-newmod`). They write down the name, the main idea, the
features and the details to check, and "Send to Claude" brings that brief as their next message. Settle the names
with them, run `new_mod.ps1` below, then write the brief into the new mod's `PLAN.md`: the idea under `## Idea`,
each feature as a `- [ ]` line under `## Features`, each detail as a `- [ ]` line under `## Details to check`. Ask
about anything unclear before the first feature.

The zonecraft panel shows those two lists as the mod's progress, so keep them true: tick a feature `- [x]` only
once the tester confirms it works in game, tick a detail once it is settled, and add a line when the tester asks for
something new. A mod without the sections (made before them) gets them when the tester first talks about scope.

```
powershell -File <zonecraft>\tools\setup\new_mod.ps1 -Name ImmersiveFoo -Short ImmFoo -RepoName stalker2-immersive-foo -Description "..."
```
Creates `<mods folder>\stalker2-immersive-foo` (the mods folder: `-Into`, else `mods_dir` in the machine settings,
else next to the current mod, else the current folder; it is saved as `mods_dir`), writes the templates, `mod.json`
and empty classifier lists, runs `GSCCreatePlainMod` and fixes the `.uplugin`, mirrors the plugin into the folder,
makes the git repo and commits, and creates + pushes the public GitHub repo (`-Private`, `-NoGitHub`, `-NoKit` to
change that). Then the tester restarts the editor and picks the mod in the toolbar selector once (creates the
GameFeatureData); mirror again and commit. Move the session into the new folder.

## Mod-specific generators
Blueprint generators live in the mod's `zonekit/tools/gen_*.py`. They start with `import zonecraft_path` (the
template's `zonekit/tools/zonecraft_path.py`), which finds zonecraft (`$ZONECRAFT_ROOT`, else the newest installed
plugin) and puts its Blueprint tools on `sys.path`; then `from bp_nodes import Nodes`.

## Update zonecraft
"Update zonecraft" from the user means: `claude plugin marketplace update elusyon-zonecraft`, then
`claude plugin update zonecraft`, then `/reload-plugins` (or a new session).

## Share a learning
A fact that holds for any mod (the game, the kit, the pipeline, how to work with the tester, a tool) goes into
zonecraft, not the mod: edit a checkout of `https://github.com/Elusyon117/zonecraft` (`knowledge/*.md` or `tools/`),
commit and push in the same session, then update the plugin. Mod-only history stays in the mod's `zonekit/README.md`.
Without push rights to zonecraft, open a pull request instead.

## Adopting a mod made with the original harness
Such a mod carries its own `harness/` copy, `.harness-sync`, an `AGENTS.md` and `CLAUDE.md` / `GEMINI.md` shims. To
move it to zonecraft: delete `harness/` and `.harness-sync`, merge `AGENTS.md` into a `CLAUDE.md` that starts like
`templates/CLAUDE.md` (load the `zonecraft` skill first), delete `AGENTS.md` and `GEMINI.md`, add
`zonekit/tools/zonecraft_path.py` from `templates/`, change generators' `sys.path` lines to `import zonecraft_path`,
rename a `harness/local.json` to `zonecraft.local.json`, and remove the `harness` git remote. Until then the mod keeps
working with its own copy.
