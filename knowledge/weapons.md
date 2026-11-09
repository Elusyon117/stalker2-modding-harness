# Weapons: new guns and weapon animations

Sources: GSC's "Zone Kit Guide: Adding new Weapon" and "Zone Kit — Weapon Animation modding"
(`zonekit-guides.md`). Each step gives GSC's way and, where zonecraft knows one, a better way. Offer both to the
tester when it matters, recommend the better one, and say what the GSC way costs (usually: conflicts with other mods).

## The prototype chain of a weapon
| File (under `GameLite/GameData/`) | What it holds | Link to the next |
|---|---|---|
| `ItemPrototypes/WeaponPrototypes.cfg` | the inventory item (e.g. `GunUDP_HG`) | `GeneralWeaponSetup`, `PlayerWeaponAttributes` |
| `WeaponData/WeaponGeneralSetupPrototypes.cfg` | meshes and parts (`WeaponsStaticMeshParts`), sockets, reload arrays, recoil / dispersion | |
| `WeaponData/.../PlayerWeaponAttributesPrototypes.cfg` | player-side attributes | `DefaultWeaponSettingsSID` |
| `WeaponData/CharacterWeaponSettingsPrototypes/PlayerWeaponSettingsPrototypes.cfg` | `BaseDamage`, `ArmorPiercing`, ... | |
| `ItemGeneratorPrototypes.cfg` | who gets it (e.g. `E01_MQ01_PlayerItemGenerator`, the starting kit) | item SIDs |

Grep the kit's copies for the exact paths before writing (`zonekit.md`); NPC and player settings are split.

## New weapon
1. Create the mod. Mirror a vanilla weapon's asset folder layout under the mod (Content Browser → Show in Explorer,
   copy the folder, delete the copied assets) and import or copy your meshes, materials and textures into it.
2. Write the prototypes (copy the closest vanilla struct, the guide uses the UDP pistol, give it a new name and
   `SID` such as `GunNewWeapon_HG`, point its links at your other new SIDs):
   - **GSC's way**: copy the whole vanilla files (`WeaponPrototypes.cfg`, `WeaponGeneralSetupPrototypes.cfg`,
     `ItemGeneratorPrototypes.cfg`, ...) into the mod at the same paths and append your structs. Simple, but each
     copied file replaces the game's file and every other mod's patches to it, and goes stale on the next game patch.
   - **Better way (recommended)**: only your new structs, in a **plain `.cfg` with a unique name inside the folder
     named after each prototype file**, e.g. `Mods\<Mod>\Content\GameLite\GameData\ItemPrototypes\WeaponPrototypes\<Mod>.cfg`,
     `...\WeaponData\WeaponGeneralSetupPrototypes\<Mod>.cfg` (`config-files.md` § Patch files). Inherit
     (`{refkey=GunUDP_HG}`) and list only what differs: shorter, and later game fixes to the base gun reach yours.
3. `WeaponsStaticMeshParts` and other asset fields take references: right-click the asset → **Copy Reference** and
   paste.
4. Set the numbers in your player weapon settings struct (`BaseDamage`, `ArmorPiercing`).
5. Make it obtainable:
   - **GSC's way**: edit the starting kit `E01_MQ01_PlayerItemGenerator` (swap `Gun_SkifGun_HG` for your SID). As a
     `{bpatch}` patch, not a copied file. It only reaches **new games**.
   - **Other options**: a `{bpatch}` on a trader's or a stash's item generator (existing saves see it once the trader
     restocks or the stash is opened); or a quest `Item Add` node started from your ModWorldSubsystem
     (`quests.md`), which hands it out in existing saves too. Magazine meshes are item-generator entries as well.
6. Recoil (optional):
   - **GSC's way**: check out `CameraPatternBlendCurve_Pistols` (or the curve your class uses) and edit it. An
     asset override: it changes every pistol, and conflicts with any mod that touches the same curve.
   - **Better way**: if the change is per gun, `{bpatch}` the recoil / dispersion fields of your weapon's struct in
     `WeaponGeneralSetupPrototypes` (grep the vanilla struct for them; grEdit Ballistics works this way,
     `compatibility.md`). Override the curve only when the curve's shape itself must change.
7. Package and test. See "Testing" in `pipeline.md` § 5: a local test pak is faster than GSC's upload-and-subscribe.

## Changing a weapon animation
1. Prepare the new animation in a DCC tool (GSC recommends Maya) on the game's skeleton.
2. Choose how it gets in:
   - **GSC's way (replace)**: there are two sets, the **player's arms** animation/montage and the **weapon's own**
     animation; replace both. Select each asset in the Content Browser, reimport it from your file (this checks it
     out into the mod), and set the **Animation Montage** length to the new length. Names must stay the vanilla
     ones. Simple, and right for "this reload looks different". The cost: each replaced asset is an override, so
     two mods replacing the same animation conflict (last-mounted wins), and game patches can make it stale.
   - **Better way when you add rather than replace** (a new action, gesture or pose): keep the animation as new
     content under `/<Mod>/` and play it from your own runtime host (ModWorldSubsystem + actor,
     `runtime-host.md`) as a montage, in the mod's own slot group so it does not fight the game's montages
     (`animation.md` § Safe ways). No vanilla asset is touched, so it cannot conflict.
3. If the timing changed, patch the matching cfg timing (e.g. a jam animation going from 3.5 s to 5 s) with a
   `{bpatch}` patch. GSC's guide copies the whole cfg file; a patch does the same without replacing other mods' edits.
4. Package and test. Bigger player animation work (montage layers, AnimBP overrides and their crash families):
   `animation.md`.
