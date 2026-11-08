---
name: zonecraft
description: Make S.T.A.L.K.E.R. 2 (Heart of Chornobyl) mods with GSC's Zone Kit editor. Use when the user wants to set up Stalker 2 modding, create or continue a Stalker 2 mod, work on Zone Kit Blueprints, animation or input, write Blueprint paste text, cook / install / test a mod pak, read the game's logs or crashes, or cut a release for Nexus Mods. Also for "where were we?" in a Stalker 2 mod folder.
---

# zonecraft

zonecraft is a harness for making S.T.A.L.K.E.R. 2 mods: agent instructions, hard-won knowledge about the game and
the Zone Kit, and PowerShell / Python tools (setup, Blueprint paste text, cook, install, release).

## Where the harness is

This skill's base directory (shown above as "Base directory for this skill") is `<plugin>/skills/zonecraft`. The
plugin root is two folders up from it, and the harness is `<plugin root>/harness/`:
- `harness/AGENTS.md`: the standing rules for every Stalker 2 mod. **Read it before anything else** and follow it.
- `harness/docs/`: the knowledge base (`setup.md`, `zonekit.md`, `blueprints.md`, `pipeline.md`, `animation.md`, ...).
- `harness/tools/`: the tools (`harness/README.md` lists them).

The plugin's copy is for reading. Tools run from a **workspace** on the user's PC, never from the plugin folder
(plugin updates replace it):
- The **zonecraft workspace** is a git clone of `https://github.com/Elusyon117/zonecraft.git`. Every mod repo is a
  sibling folder next to it and carries its own synced copy of `harness/` (`harness/docs/harness-workflow.md`).
- A **mod repo** has `mod.json` and `.harness-sync` at its root.

## What to do

1. Find where you are: a mod repo (`mod.json` in the working folder), the zonecraft workspace (`harness/` and
   `.claude-plugin/` at the root, no `mod.json`), or neither.
2. **Neither** (a new user, or a new PC): follow `<plugin root>/harness/docs/setup.md`. It clones the workspace,
   installs what is missing, finds the game and the Zone Kit, and asks the user a few questions. Then move the session
   into the workspace folder.
3. **In the workspace or a mod repo**: read `harness/AGENTS.md` there (the local copy wins over the plugin's) and do
   what its "Session start" section says.
4. Talk to the user in game terms. They play, click and paste in the Zone Kit; you do everything else.

The Zone Kit runs only on a Windows PC with the game installed. If this PC has no Zone Kit (`check_setup.ps1`
reports it missing), you can still write paste text, edit docs and tools, and run the offline tests
(`harness/tools/t3d/test_bp_nodes.py`); say what needs the PC with the kit.

## Blueprint paste text in one breath

Build graphs with `harness/tools/t3d/bp_nodes.py` (`Nodes(graph, self_class=...)`: events, input actions, calls,
variables, Branch, Sequence, Delay, loops, casts, delegates) on `bp_graph.py`, call `graph.layout_tree()`, write the
text, run `verify_paste.py lint <file>`, put it on the clipboard for the user to paste with Ctrl+V, and after they
compile and save run `verify_paste.py compare <file> --asset /<Mod>/...` to check every node arrived with its links.
Details and traps: `harness/docs/blueprints.md`.
