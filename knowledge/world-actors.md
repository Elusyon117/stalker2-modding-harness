# Actors in the world: add, patch, delete (and placeholders)

Sources: GSC's Zone Kit guides "Intro to actor & placeholder mods", "How to add new actors", "How to patch vanilla
actors", "How to delete vanilla actors", "How to mod placeholders", "Mod game features" (`zonekit-guides.md`).
Level editing itself (sculpting, re-saving vanilla levels) is still not supported; these systems are how a mod
changes the world without touching vanilla map files.

## The two kinds of world entity
- **Actor**: anything placed in a level (meshes, lights, Blueprints). Vanilla actors cannot be checked out like
  assets; changes to them are recorded by the patch and deletion systems below.
- **Placeholder**: an editor-only actor that stands for a **SpawnActorPrototype** (a `.cfg` entry that defines a
  spawned NPC, item, container, trigger, anomaly...). Placeholders are destroyed at PIE start and never baked into
  the map: in game only the `.cfg` exists, so placeholder mods follow the cfg patch rules
  (`config-files.md`).

## Before any world edit
Select the mod in the toolbar (all three systems are active only while a mod is selected), open `WorldMap_WP`
(Content Browser → All, filter by Level), Window → World Partition → World Partition Editor, select a small area →
right-click → **Load Region From Selection**. Actors inside a Level Instance need that instance opened for editing
first. Never check out levels, external actors or external objects as assets: World Partition does not support
redirection and it can crash.

## Adding actors (new content)
Place actors normally (Quick Add → Place Actors, or drag your own Blueprint class from the mod's folder) and save
the level. They are written to the mod as external actors:
`Mods\<Mod>\Content\ExternalActors\ContentBundle\<guid>_Stalker_2\maps_Stalker2_WorldMap\WorldMap_WP\...\<id>.uasset`,
classified as New content and mounted at `Stalker2/Mods/<Mod>/Content` in game. New actors can be deleted and
edited freely; the patch and deletion systems ignore them. Test in PIE with Play → Spawn Player At → Current Camera
Location.

## Patching vanilla actors
Edit a vanilla actor in the Details panel (transform, properties, components added or removed) and save the level.
The kit compares each changed actor with its file on disk, property by property and component by component, and
writes the differences into a **Mod Actor Patches** data asset in the mod (created automatically; save it too). No
vanilla file changes. The game applies the patches at runtime. In the kit, patches are applied when the mod is
selected or a region loads, and undone when the mod is deselected.

## Deleting vanilla actors
Select the actor and press Delete. The kit hides it and records a deletion info in a **Mod Actor Deletions** data
asset (save it). Editing a deleted actor's properties un-deletes it. An actor is either patched or deleted, never
both: a new patch removes its deletion info and vice versa.

## Placeholders in a mod
In game, placeholder changes are pure cfg: patching or deleting a placeholder in the kit also writes a
SpawnActorPrototype cfg into the mod (the data asset entries only matter in the editor, to resume work).
- Vanilla placeholder changed or deleted: `Mods\<Mod>\Content\GameLite\GameData\SpawnActorPrototypes\<Level>\<SID>.cfg`
  (packaged as `Stalker2\Content\GameLite\GameData\SpawnActorPrototypes\...`). A patch is the full struct with
  `{bpatch}` and a `NodePrototypeAppliedMods : struct.begin {bpatch}` block naming the mod (shared between mods,
  stored in the save). A deletion is a single `<SID> : removenode` line.
- New placeholder: `Mods\<Mod>\Content\GameLite\ModGameData\SpawnActorPrototypes\<Level>\<SID>.cfg`.
- Fields worth knowing: `SID`, `SpawnOnStart` (true for world loot, NPCs, mutants; false for quest entities spawned
  by a Spawn node), `SpawnType` (`ESpawnType::Item`, `Trigger`, ...), `Position*`, `Rotator*`, `Scale*`,
  `LevelName`, `PlaceholderMapPath`, `DLC`, type-specific fields (`ItemSID`, `MeshPath`, `TriggerShape`...). You can
  edit these files by hand or write one from scratch.
- At runtime the game deletes an already spawned entity whose prototype changed and spawns it again from the
  modded prototype (SpawnOnStart ones immediately, others when their quest spawns them). Existing saves therefore
  pick up the change, except **PackOfItems** placeholders, which need a new game.

## Mods as game features (why this works)
Since Zone Kit phase 2 every mod is a UE **game feature**: its own mount point (`Stalker2/Mods/<Mod>/`), asset
registry and shader library, so new assets of different mods cannot collide. The kit converts older plain-plugin
mods automatically when you select them (`LogModKitGameFeaturesManager` shows it). Do not edit the generated Game
Feature Data asset (`/<Mod>/<Mod>`) or its actions. The `.uplugin` needs `"Mod": true` (plus the game-feature fields
`pipeline.md` § 1 lists) or it is not treated as a mod.
