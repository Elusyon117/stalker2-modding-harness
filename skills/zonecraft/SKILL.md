---
name: zonecraft
description: Make S.T.A.L.K.E.R. 2 (Heart of Chornobyl) mods with GSC's Zone Kit editor. Use when the user wants to set up Stalker 2 modding, create or continue a Stalker 2 mod, work on Zone Kit Blueprints, animation or input, write Blueprint paste text, cook / install / test a mod pak, read the game's logs or crashes, or cut a release for Nexus Mods. Also for "where were we?" in a Stalker 2 mod folder.
---

# zonecraft: making S.T.A.L.K.E.R. 2 mods

The game is **S.T.A.L.K.E.R. 2: Heart of Chornobyl** (Unreal Engine 5.5, game patch 2.0.x). Mods are built in the
official **Zone Kit** (GSC's UE 5.5 mod editor) and ship as **paks only**. UE4SS is a dev-box diagnostic tool and
never ships.

## Where zonecraft is
This skill's base directory (shown above as "Base directory for this skill") is `<zonecraft>/skills/zonecraft`, so
**`<zonecraft>` is two folders up from it**. Use that absolute path for everything below:
- `<zonecraft>/knowledge/`: what is known about the game, the kit and the pipeline (table below).
- `<zonecraft>/tools/`: the tools (`knowledge/tools.md` lists them). They act on the **mod folder**: the nearest
  folder with `mod.json` above the current folder. Run them from inside the mod.
- `<zonecraft>/templates/`: what `new_mod.ps1` writes into a new mod.

A **mod folder** has `mod.json` and a `CLAUDE.md` at its root, and holds only the mod: no copy of zonecraft.

## Session start
- **New user or new PC** (no `%LOCALAPPDATA%\zonecraft\settings.json` or `%LOCALAPPDATA%\stalker2-modding-harness\settings.json`,
  or `check_setup.ps1` reports problems, or the user asks to be set up): follow `knowledge/setup.md`. Do every step
  yourself; the user only answers questions and clicks where a program insists on a human.
- **In a mod folder**: read its `CLAUDE.md` "Current state" so "where were we?" has an answer.
- **The user wants a new mod**: `knowledge/mod-workflow.md` § New mod (choose the names with them).
- **A mod made with the original harness** (it has `harness/` and `.harness-sync`): it still works with its own copy;
  offer to adopt it (`knowledge/mod-workflow.md` § Adopting).
- **No Zone Kit on this PC** (`check_setup.ps1` says so): you can still write paste text, edit knowledge and tools,
  and run `tests/test_bp_nodes.py`; say what needs the PC with the kit.

## Roles (read `knowledge/collaboration.md` before the first reply of a session)
- **The tester** (the user) plays the game, does the clicks and pastes in the Zone Kit editor, and decides scope,
  releases and when to stop. Assume they do not read code or run commands.
- **You** own everything else: research in the kit, scripts, Blueprint paste text, cooks, installs, log and crash
  reading, mirroring assets into the mod folder, docs, commits they ask for, releases.
- Never hand the tester build or install commands, or ask them to paste files or logs you can read yourself.
- Talk in game terms: which place, which keys, what success looks like, what a run must contain.

## Hard rules
1. **Kit first.** Grep the kit's dumps and cfgs (`knowledge/zonekit.md`) and ask the tester to open assets in the
   editor before any blind build/test cycle. Most `/Script/Stalker2` classes are native with no graph; look for the
   assets that USE them.
2. **One change per cook** (5-6 min), tested by the tester before the next. At the first regression, roll back to
   the last checkpoint. Don't bundle a cleanup with a behaviour change.
3. **No versions, candidate commits, tags or releases unless the tester says so.** Test builds stay uncommitted;
   doc commits are fine. Releases only on "cut a release" (`knowledge/pipeline.md` § Release).
4. **Prove a diagnostic captures before asking for a run**, and say exactly what the run must contain
   (`knowledge/diagnostics.md`). The tester's patience is the scarce resource.
5. **Don't park or defer work on your own.** If stuck, say what blocks and ask; iterate until they say stop.
6. **Trust what the tester sees.** When data contradicts them, suspect the mod's own stalls or the probe first.
7. **Override as little as possible** (`knowledge/compatibility.md`): per asset the last-mounted pak wins outright,
   so every overridden asset is a conflict with every other mod touching it. Prefer NewContent hosts
   (`knowledge/runtime-host.md`) and cfg *patches*; never ship a whole-file `.cfg` override. Never override
   `BP_Stalker2Character`, `AnimBP_Player`, `AnimBP_player_bh` or `IMC_Exploration` without the tester's explicit
   decision after hearing the conflict cost.
8. **Canary.** Every test build of an input change keeps one extra, harmless key on a known action so
   "override not loaded" and "action vetoed natively" are distinguishable. Remove it for release.
9. **Checkpoints**: once the tester confirms a working state and agrees, commit it tagged with the cooked paks in
   `zonekit/builds/<checkpoint>/`. Mirror `.uasset`s from the kit into the mod folder after every editor save they
   report.
10. **After a release, remove the dev test pak** (`revert_paktest.ps1`) so they play on the Nexus/Vortex copy.

## Knowledge
| Need | Read (in `<zonecraft>/knowledge/`) |
|---|---|
| How to work with the tester, instruction style, test runs | `collaboration.md` |
| Kit layout, dumps, cfgs, what to grep, what to ask them to open | `zonekit.md` |
| Plugin creation, classifier lists, cook rules, mount order, install, release | `pipeline.md` |
| Blueprint paste text, reading graphs back, editor Python, editor traps | `blueprints.md` |
| Input mapping contexts, rebinds, key sync | `input.md` |
| Running Blueprint logic without overriding anything (ModWorldSubsystem + actor) | `runtime-host.md` |
| Player animation, montages, anim layers, known crash families | `animation.md` |
| Game `.cfg` data, patch files | `config-files.md` |
| UE4SS probes, logs, crash dumps | `diagnostics.md` |
| Other popular mods, shared assets, inspecting other paks, MCM | `compatibility.md` |
| Verified game behaviour (native vetoes, flags, functions) | `game-facts.md` |
| Setting up a new PC | `setup.md` |
| New mods, updating zonecraft, sharing what you learn, adopting old mods | `mod-workflow.md` |
| Every tool, with arguments | `tools.md` |

## Blueprint paste text in one breath
In the mod's `zonekit/tools/gen_*.py`: `import zonecraft_path`, then build the graph with `bp_nodes.Nodes(graph,
self_class=...)` (events, input actions, calls, variables, Branch, Sequence, Delay, loops, casts, delegates), call
`graph.layout_tree()` and write the text. Run `tools/blueprints/verify_paste.py lint <file>`, put the text on the
clipboard for the tester to paste with Ctrl+V, and after they compile and save run `verify_paste.py compare <file>
--asset /<Mod>/...` to check every node arrived with its links. Details and traps: `knowledge/blueprints.md`.

## Keeping knowledge where it belongs
- A fact about the game, the kit, the pipeline, another mod, or how to work with the tester → zonecraft's
  `knowledge/` (`mod-workflow.md` § Share a learning), in the same session.
- A fact about this mod (what was tried, what each build showed) → the mod's `zonekit/README.md` log; the
  reproducible edit → the mod's `BUILD.md`; status → the mod's `CLAUDE.md` "Current state" (one line per checkpoint).
- Never put user- or machine-specific values (paths, accounts) in zonecraft or a mod: they go in the machine settings.
