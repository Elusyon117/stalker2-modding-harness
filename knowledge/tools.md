# zonecraft tools

All paths are relative to the zonecraft folder (the plugin root, `<zonecraft>` below). Tools act on the **mod folder**:
the nearest folder holding `mod.json`, walking up from the current folder (or `$env:ZONECRAFT_MOD_DIR`). Run them
from inside the mod. PowerShell: `powershell -ExecutionPolicy Bypass -File <zonecraft>\tools\...`.
Python = the kit's embedded interpreter `<kit>\Engine\Binaries\ThirdParty\Python3\Win64\python.exe`.

PowerShell tools default `-Mod` to `mod.json` "name". Per-user values (kit and game folders, GitHub account, mods
folder) live outside every repo: `tools/config.json` has only generic defaults, overridden by the machine settings
`%LOCALAPPDATA%\zonecraft\settings.json` (written by `setup.ps1`; a PC set up with the original harness also has its
`%LOCALAPPDATA%\stalker2-modding-harness\settings.json` read first) < a gitignored `zonecraft.local.json` in one mod.

| Tool | Runs | Does |
|---|---|---|
| `tools/setup/check_setup.ps1` | shell | read-only check of paths, Git, GitHub login, editor remote Python; prints fixes |
| `tools/setup/setup.ps1 [-Install] [-EnableRemotePython]` | shell | automatable setup: finds the kit and game, writes the machine settings, installs Git / GitHub CLI, turns on editor remote Python |
| `tools/setup/new_mod.ps1 -Name -Short -RepoName -Description [-Into]` | shell | new mod folder from `templates/`, Zone Kit plugin, git repo, GitHub repo (`mod-workflow.md`) |
| `tools/build/cook_and_install.ps1 [-Mod] [-Suffix N] [-NoInstall]` | shell | `GSCCookMod` (5-6 min), classifier-list sanity check + mirror, waits for the game to close, installs |
| `tools/build/install_paktest.ps1 [-Mod] [-Suffix N]` | shell, game closed | staged OverrideContent → `~mods\zzz_<Mod>_PakTest\zzz_<Mod>_<N>_P.*` (default 30), NewContent under its kit name |
| `tools/build/revert_paktest.ps1 [-Mod] [-Park]` | shell, game closed | removes (or parks outside `Content\Paks`) the dev test pak |
| `tools/build/mirror_from_kit.ps1 [-Mod]` | shell | kit plugin (`.uplugin`, `Content`, `Resources`) + classifier lists → mod folder |
| `tools/build/deploy_to_kit.ps1 [-Mod] [-Force]` | shell | mod folder → kit; refuses to clobber newer kit files |
| `tools/build/make_release.py X.Y.Z [--downloads]` | shell | release zip from the last cook |
| `tools/build/release_candidate.py [--mod-root] [--names] [--json]` | shell | last packaging → `<mod>/<release.folder>/`, renamed per mod.json `"release"` (e.g. `zzzz_<Mod>_P.*` so it mounts after `zzz_` mods); writes `rc.json`. The Build & test band runs it after each packaging when `release.auto` is on |
| `tools/watch/zcwatch.py poll [--mod-root]` | shell (the band polls it) | what changed since the last call: packaging phase and errors (UAT logs, `%TEMP%\<Mod>_cook.log`), game / editor running, new game and kit log lines worth seeing, new crash reports with their family from `tools/watch/crash_rules.json` (add a rule when a crash is understood) |
| `tools/editor/ue_exec.py <file\|code> [--arg K=V]` | shell → open editor | Python in the tester's editor via remote execution; prepends the prelude (`MOD`, `MOD_ROOT`, `UPLUGIN`, `SCRATCH`, `ARGS`) |
| `tools/editor/run_headless.ps1 -Script f.py [-Arg K=V,..]` | shell → commandlet | same prelude, headless editor (~4.5 min); editor closed for asset moves |
| `tools/editor/duplicate_asset.py` | headless | `SRC` → `DST` duplicate (Blueprint graphs survive) |
| `tools/editor/move_asset.py` | headless, editor closed | rename with referencer fix-up, deletes the redirector |
| `tools/editor/set_bp_default.py` | either | one class-default value (`BP`, `PROP`, `VALUE`) |
| `tools/editor/dump_imc.py` | either | mapping-context rows, mappable names, modifiers, triggers → JSON |
| `tools/editor/export_t3d.py` | open editor | full T3D export of any asset (read Blueprints back) |
| `tools/editor/create_marker.py` | headless | permanent compatibility marker asset |
| `tools/blueprints/bp_t3d.py`, `bp_graph.py` | library | write Blueprint paste text (nodes, pins, both-ended links, comment boxes, layout) |
| `tools/blueprints/bp_nodes.py` | library | ready-made nodes on `bp_graph`: events, input actions, calls, variables, Branch, Sequence, Delay, loops, casts, delegates |
| `tools/blueprints/verify_paste.py lint <f>` / `compare <f> [<export> \| --asset P]` | shell (compare `--asset`: open editor) | checks paste text before pasting; after pasting, compares it with the asset's export (missing nodes, lost links) |
| `tools/blueprints/t3d_lift.py` | library | lift nodes from an exported T3D into paste text |
| `tools/pak/zen_names.py <dir> [--imports] [--filter RE]` | shell | names / imports of cooked (Zen) packages |
| `tools/pak/dump_names.py <uasset>` | shell | FName table of an uncooked package (keys, actions, modifiers) |
| `tools/pak/extract_from_pak.py` | shell | single uncooked assets out of the kit's editor pak by index offset |
| `tools/pak/scan_mods.py <Name>...` | shell | which installed mod containers mention an asset, with mount order |
| `tools/pak/conflicts.py scan [--yours DIR] [--collection DIR] [--only-yours] [--json]` | shell, kit set up (UnrealPak) | every container of ~mods, your mods and a collection folder: shared assets with the winner (mount order, then file name), whole cfg replacements, cfg patches touching the same field (`compatibility.md`); listings cached in `%LOCALAPPDATA%\zonecraft\conflicts\` |
| `tools/data/gamedata.py build\|status\|find\|search\|kids\|patch` | shell (any Python 3) | game data index: SID lookup with file:line, inheritance, resolved fields, the mod's patches, in-game name, patch path; ready `{bpatch}` text; `patch --write` merges it into the mod's patch file; `--mod-root` picks the mod, `--json` feeds the `/zonecraft-data` panel (`config-files.md` § Game data index) |
| `tools/data/cfg_parse.py` | library | parser for the cfg DSL: parse, light top-level scan, patch and inheritance merge, dump, build patch text |
| `tests/test_bp_nodes.py`, `tests/test_gamedata.py`, `tests/test_conflicts.py` | shell | offline tests for the Blueprint tools, the game data index and the conflict check (no kit needed) |
| `probe/` | modder's PC only | UE4SS C++/Lua probe examples and build notes |
| `templates/` | `new_mod.ps1` | the files a new mod starts with, including `zonekit/tools/zonecraft_path.py` (lets a mod's `gen_*.py` import the Blueprint tools) |
