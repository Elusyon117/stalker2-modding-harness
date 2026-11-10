# Game data (.cfg) files

All gameplay data (items, weapons, NPCs, effects, abilities, input contexts, core variables) lives in text `.cfg`
files under `<kit>\Stalker2\Content\GameLite\GameData\` in GSC's struct DSL (`Name : struct.begin {refkey=...}`
... `struct.end`, inheritance through `refurl` / `refkey`). Look up any gameplay number in the game data index first
(below), and grep only for what it does not cover.

## Game data index (`tools/data/gamedata.py`)
Run it with any Python 3 (`py -I <zonecraft>\tools\data\gamedata.py ...`) from inside the mod folder.
- `build`: indexes every struct in `GameLite/GameData` and `GameLite/DLCGameData` of the kit, plus the kit's text
  database, into `%LOCALAPPDATA%\zonecraft\gamedata\index.sqlite` (per machine, never in a repo). Run it after
  setup and after every Zone Kit update; any query prints a NOTE when the kit is newer than the index. `status`
  shows counts and whether the text database was understood (its layout is guessed; if `status` says "format not
  recognised", read the JSON's shape and adjust `load_texts`).
- `find <SID or name>`: definition file:line, the `refkey` chain, the **resolved fields** (inherited values filled
  in, then the current mod's own patches applied; `--raw` for the struct's own lines, `--field RE` to filter,
  `--depth N`), copies in DLC data (patch those too), other definitions and patches, the in-game name, how many
  prototypes inherit from it, and **where this mod's patch for it goes** (by GSC's two rules below).
- `search <text>`: SIDs, struct names and in-game texts containing the text (`--in RE` limits to files).
- `kids <SID>`: everything inheriting from it. A patch on the parent does not reach fields a child overrides.
- `patch <SID> --set Path.To[0].Field=Value [--remove Path.[2]]`: prints a `{bpatch}` patch and its file; a path that
  is not in the resolved struct is flagged as a probable typo. `--write` adds it to the mod's patch file (kit plugin
  folder, else the mirror), merged with a patch of the same struct already there; refused while a path is flagged.
- `--mod-root <mod folder>` works on another mod than the one you are in; `--json` prints one JSON object (status,
  search with `--kind weapons|items|npcs|quests|effects`, find with each field's origin, patch).
- **`/zonecraft-data`** is the same index as a panel for the tester: search, open an entry, press a value to change
  it, **Add to my mod** (`patch --write`) or **Send to Claude**. When the tester adds a change there, package the mod
  and test it like any other cfg patch.
The current mod's cfgs (kit plugin folder, else the `zonekit/<Mod>/` mirror) are read live, never cached. Use the
index for every SID you put in a cfg, quest node or Blueprint: a wrong SID costs a cook and a test run, and it is what
the Broken Game Data validator keeps catching (`quests.md`). The resolved fields follow inheritance the way the files
read; the game's own merge can differ in corners, so confirm surprising values in game.

## Rules
- **Never ship a whole-file override** of a game `.cfg`. It silently replaces every other mod's edits to the same
  file (ImmersiveDialogue 2.0.0 was re-cut once because a full `CoreVariables.cfg` had slipped into the pak).
- Two ways to make a cfg mod; offer both, recommend the second:
  - **GSC's way** (Zone Kit guide "Creating a configuration mod"): copy the whole vanilla `.cfg` into the mod at the
    same path (`Mods\<Mod>\Content\GameLite\GameData\Credits.cfg`) and edit it. Acceptable for a quick private
    test, never for a release (rule above): it replaces the game's file and every other mod's patches to it, and
    goes stale after game patches.
  - **Better way**: a patch file with only the changed fields (below). Coexists with other mods; survives patches.
- Change data with **patch files** that touch only the fields you need (the mechanism grEdit, Better Vaulting and
  ImmersiveDialogue's talk-distance plan use). Syntax and placement: see "Patch files" below.
- Offer different values as optional pak variants (e.g. `Optional-Fast/`), or at runtime through Blueprint if a
  setter exists (then an MCM slider becomes possible).
- A mod's own cfg folder comes from its GameFeatureData action AddConfigsPath:
  `Content/GameLite/ModGameData/<Mod>/`.
- Data reached through `refkey` inheritance: check that a patch on the base prototype actually reaches the
  children that override the same field (they keep their own value).

## Patch files (verified 2026-09-30 in installed mods; official docs: Zone Kit guides "Config patches", "How to
apply modifications to vanilla .cfg files", "How to patch contents of a .cfg file", `zonekit-guides.md`)
The loader scans `Content\GameLite\GameData` (the **ConfigFileCache**); for each `X.cfg` it also loads patch files.
Which kind depends on the file (GSC's rule):
- **Ordinary cfg** (e.g. `CoreVariables.cfg`, `AIGlobals.cfg`, `Credits.cfg`): a sibling `X.cfg_patch_<Mod>` in the
  same folder.
- **Prototype cfg** (the `*Prototypes.cfg` files, which the game also loads binarised as `.cfg.bin`): any `.cfg`
  with a unique name inside a folder named after it, e.g.
  `WeaponData/CharacterWeaponSettingsPrototypes/<Mod>.cfg`, `AnomalyPrototypes/<Mod>.cfg`. Every `.cfg` in that folder
  is applied as a patch; `.cfg_patch_*` files are **not** looked for there.
- Several mods patching one file each ship their own differently named patch; the names never collide.

Without `{bpatch}`, a struct in a patch **replaces the whole node** of that name (nothing of the vanilla node is
kept); a struct whose name is new is **added**.

**Syntax.** Put `{bpatch}` on **every** struct level down to the field; fields listed replace or add, everything
else is kept. Top-level prototypes are addressed by name, array elements by index. `removenode` deletes a node and
only works inside a `{bpatch}`. Example, one field of one array element of one weapon:
```
GunAK74_ST : struct.begin {bpatch}
   WeaponReloadTimePerAttachment : struct.begin {bpatch}
      [0] : struct.begin {bpatch}
         TacticalReloadTimeMultiplier = 0.75
      struct.end
   struct.end
struct.end
```
Remove an element: `PreinstalledUpgrades : struct.begin {bpatch}` / `[0] : removenode` / `struct.end`.

**Placement** (both seen working; path relative to the pak root `Stalker2/Content/GameLite/GameData/`):
- sibling file: `CoreVariables.cfg_patch_<Mod>` next to `CoreVariables.cfg`;
- folder named after the cfg: `ObjPrototypes/ObjPrototypes.cfg_patch_<Mod>.cfg`, or
  `WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_<Mod>.cfg` (the folder need not exist in
  vanilla; the file alone is enough).
- DLC data is separate: patch `GameLite/DLCGameData/{DLC1,Deluxe,PreOrder,Ultimate}/...` too for DLC items/weapons.
- Zone Kit mods ship patch files in the OverrideContent pak (as loose files under the GameData path).

**New prototypes** (new effects, items, quest nodes): plain `.cfg` files in the mod's
`Content/GameLite/ModGameData/<Mod>/<Type>/` (loaded through the GameFeatureData's AddConfigsPath; PIR, ZST, Sleeping
Bag do this), inheriting with `{refurl=../EffectPrototypes.cfg; refkey=[0]}` or `{refkey=[0]}`.

**Per-field last-wins.** Two mods bpatching the same field of the same prototype: the later-loaded wins that field
only; different fields in the same file coexist (e.g. grEdit recoil + OXA reload arrays).

**References.** A patch may reference nodes of the cfg it patches without `refurl`. A `refurl` to a `.cfg` that does
not exist inside a prototype folder is redirected to the `.cfg.bin` and the node is looked up there.

**Conflicts the kit reports** (category `LogParserNodePatching`, warnings and errors): patch A re-adds a node patch
B removed; patch A removes, or replaces, a node (or a child of it) that patch B modified.

**Debugging patches** (`diagnostics.md` § Zone Kit logs): set `LogParserNodePatching` to Verbose to get one line per
patched node; launch with `-ProtoLoadingMode=2` (load all prototypes synchronously: slower, but patches apply in
order and the log reads straight); `-DumpConfigFileCache` writes `ConfigFileCacheDump_ModEditor.txt` to the logs
folder on each cache update (startup, mod (de)selected, content pack toggled), and `LogConfigFileCache` prints what
the cache found. In the kit, cfgs of the selected mod apply in PIE.

## Useful data (see `game-facts.md` for more)
- Player prototype: `ObjPrototypes.cfg` `Player` (~line 653): `StaminaPerAction`, `StaminaDisableThresholds`,
  `MovementParams` (`RunSpeed 370`, `JoggingSpeed 625`, `SprintSpeed 820`), `VitalParams`, `ApplicableMechanicsEffects`.
- Effects: `EffectPrototypes.cfg` (types `EEffectType::*`, `bIsPermanent`, `Duration`, `ValueMin/Max` in `%`).
- Weapons: `WeaponData/WeaponGeneralSetupPrototypes.cfg` (every weapon redeclares its own arrays, so a template patch
  does not reach them); NPC/player split is in `CharacterWeaponSettingsPrototypes/`.
- Input contexts: `InputMappingContextPrototypes.cfg`; PC settings defaults: `SettingsVariablesPC.cfg`.
