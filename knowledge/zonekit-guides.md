# GSC's official Zone Kit guides

GSC publishes modding guides at <https://zonekit-support.stalker2.com/en-US/kb/category/14> (26 articles, read
2026-11-08; the Quest Tool guide is a PDF at <https://cdn.stalker2.com/guides/Quest_Tool_complete_guide.pdf>).
zonecraft does not copy them. It folds what they teach into its own knowledge files, in its own words, next to what
zonecraft found by testing. Read the right file below first; open the original article when you need its
screenshots, or when a kit update may have changed it.

Where zonecraft knows a better way than a guide, the file lists **both as options**: "GSC's way" and "Better way",
with what each costs. Offer both to the tester, recommend the better one, and let them choose. Where they differ:
| Topic | GSC's way | Better way | File |
|---|---|---|---|
| cfg mods | copy the whole `.cfg` | patch file with only the changed fields | `config-files.md` § Rules |
| New weapon data | copy whole prototype files | own `.cfg` in the prototype folder, inheriting | `weapons.md` |
| Recoil | override the shared camera curve | `{bpatch}` the gun's own recoil fields | `weapons.md` |
| Getting the weapon | starting kit (new games only) | trader / stash patch or quest Item Add (existing saves) | `weapons.md` |
| Added animations | replace vanilla anim assets | new-content montage from a runtime host | `weapons.md`, `animation.md` |
| Starting a quest | Container in a vanilla quest | ModWorldSubsystem (also GSC's newer guide) | `quests.md` |
| Testing builds | private upload + subscribe | local test pak (`cook_and_install.ps1`) | `pipeline.md` § 5 |
| Checking a pak | `UnrealPak -list` | extract + `zen_names.py --imports` | `pipeline.md` § 4 |

| Article | Covered in |
|---|---|
| [Getting started with Zone Kit (full guide)](https://zonekit-support.stalker2.com/en-US/kb/article/149/getting-started-with-zone-kit-or-zone-kit-full-guide) | `pipeline.md` § 1, 2, 4, 7 (Steam, mod.io) |
| [Creating mods with Mini SDK](https://zonekit-support.stalker2.com/en-US/kb/article/148/creating-mods-with-mini-sdk) | `pipeline.md` § 4 |
| [Mod game features](https://zonekit-support.stalker2.com/en-US/kb/article/162/mod-game-features) | `pipeline.md` § 1-2, `world-actors.md` § Mods as game features |
| [How to exclude assets from mod packaging](https://zonekit-support.stalker2.com/en-US/kb/article/146/how-to-exclude-assets-from-mod-packaging) | `pipeline.md` § 4 |
| [Config patches](https://zonekit-support.stalker2.com/en-US/kb/article/145/config-patches) | `config-files.md` § Patch files |
| [How to apply modifications to vanilla .cfg files](https://zonekit-support.stalker2.com/en-US/kb/article/173/how-to-apply-modifications-to-vanilla-cfg-files) | `config-files.md` § Patch files |
| [How to patch contents of a .cfg file](https://zonekit-support.stalker2.com/en-US/kb/article/172/how-to-patch-contents-of-a-cfg-file) | `config-files.md` § Patch files |
| [Command line arguments reference](https://zonekit-support.stalker2.com/en-US/kb/article/161/command-line-arguments-reference) | `diagnostics.md` § Zone Kit logs |
| [Debugging utilities](https://zonekit-support.stalker2.com/en-US/kb/article/168/debugging-utilities) | `diagnostics.md` § Zone Kit logs |
| [How to report a bug](https://zonekit-support.stalker2.com/en-US/kb/article/151/how-to-report-a-bug) | `diagnostics.md` § Zone Kit logs |
| [How to work with ModWorldSubsystem](https://zonekit-support.stalker2.com/en-US/kb/article/147/how-to-work-with-modworldsubsystem) | `runtime-host.md` |
| [Save/Load system for mods](https://zonekit-support.stalker2.com/en-US/kb/article/159/saveload-system-for-mods) | `runtime-host.md` § Saving mod data |
| [Intro to actor & placeholder mods](https://zonekit-support.stalker2.com/en-US/kb/article/170/intro-to-actor--placeholder-mods) | `world-actors.md` |
| [How to add new actors](https://zonekit-support.stalker2.com/en-US/kb/article/171/how-to-add-new-actors) | `world-actors.md` § Adding |
| [How to patch vanilla actors](https://zonekit-support.stalker2.com/en-US/kb/article/167/how-to-patch-vanilla-actors) | `world-actors.md` § Patching |
| [How to delete vanilla actors](https://zonekit-support.stalker2.com/en-US/kb/article/169/how-to-delete-vanilla-actors) | `world-actors.md` § Deleting |
| [How to mod placeholders](https://zonekit-support.stalker2.com/en-US/kb/article/166/how-to-mod-placeholders) | `world-actors.md` § Placeholders |
| [Quest Tool Complete Guide (PDF)](https://zonekit-support.stalker2.com/en-US/kb/article/174/discover-stalker-2-modding-quest-tool-complete-guide) | `quests.md` (nodes, dialogs, configs, validators), `audio.md` § Sounds from quests |
| [Quest Toolset: your first quest](https://zonekit-support.stalker2.com/en-US/kb/article/165/zone-kit-quest-toolset-creating-your-first-quest-modification-from-a-clean-slate) | `quests.md` § Making a quest |
| [Launching a new quest using ModWorldSubsystem](https://zonekit-support.stalker2.com/en-US/kb/article/164/launching-new-quest-in-game-build-using-modworldsubsystem) | `quests.md` § Making a quest, `runtime-host.md` |
| [How to launch a new quest without console](https://zonekit-support.stalker2.com/en-US/kb/article/163/how-to-launch-newly-created-quest-in-build-without-console) | `quests.md` § Making a quest (the conflict-prone way) |
| [Mod TextTool](https://zonekit-support.stalker2.com/en-US/kb/article/160/mod-texttool) | `quests.md` § Texts and localisation |
| [Audio modding quick start](https://zonekit-support.stalker2.com/en-US/kb/article/155/zone-kit-–-audio-modding-quick-start-guide) | `audio.md` |
| [Adding a new weapon](https://zonekit-support.stalker2.com/en-US/kb/article/152/zone-kit-guide-adding-new-weapon) | `weapons.md` § New weapon |
| [Weapon animation modding](https://zonekit-support.stalker2.com/en-US/kb/article/153/zone-kit-—-weapon-animation-modding) | `weapons.md` § Replacing a weapon animation |
| [Cook mod request for Xbox](https://zonekit-support.stalker2.com/en-US/kb/article/150/how-to-create-a-cook-mod-request-for-xbox) | `pipeline.md` § Xbox |

## Not possible yet (per the guides)
- Editing levels themselves (terrain, re-saving vanilla level files). Add, patch and delete actors instead
  (`world-actors.md`).
- Checking out levels, external actors or external objects (World Partition).
