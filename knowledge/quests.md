# Quests, dialogs and texts (Quest Tool, Dialog Tool, Mod TextTool)

Sources: GSC's Zone Kit guides "Quest Tool Complete Guide" (PDF), "Quest Toolset: your first quest", "How to launch
a new quest without console", "Launching a new quest using ModWorldSubsystem", "Mod TextTool"
(`zonekit-guides.md` has the links). Written for modders; the PDF was written for GSC's own staff, so its
`Z:\git\s2gamebuild\...` paths mean `<kit>\Stalker2\...` here, and anything about Jira, commits or "ask a level
designer" does not apply.

## Model in one paragraph
A **Quest Blueprint** (QBP) is a node graph. A node runs when a signal reaches an input pin, does its job, finishes,
and sends the signal on through its output pins. Every QBP has **Start** and **End**. A signal into a node's red
**exclude** pin stops it (and for long-running nodes undoes the effect, see each node). End has
**Exclude All Nodes in Container** (set it, so lingering nodes such as Protect Placeholder or Restrict Save stop
with the quest) and can have several input pins (all connected inputs must fire for End to fire). Saving a QBP also
writes it as text into `GameLite/GameData/QuestNodePrototypes/<QBP>.cfg`.

Node kinds:
- **Action**: does something when signalled (most nodes).
- **Event** (`On ... Event`): fires by itself when the game event happens; needs no input to arm beyond being
  reachable. Many have **Track Before Active**: count the event as done if it happened before this QBP started
  (almost mandatory for rank, money, faction checks).
- **Condition**: wired in parallel; lets a signal through only while its check holds; keeps running.
  **If**: wired in series; routes to True or False once and ends. Both take a list of checks with And/Or and a
  **NOT Condition** flag.
- **Container**: runs another QBP inside this one. A second signal while it runs restarts it. A QBP cannot contain
  itself. **Scheduled Container** runs only inside a time window (Morning 06-12, Day 12-18, Evening 18-24,
  Night 00-06, or Custom hours 0-23).

## Making a quest (mod workflow)
1. Pick the mod in the toolbar, open `WorldMap_WP`, open Window → World Partition → World Partition Editor, drag a
   **small** box and *Load Region From Selection* (loading the whole map makes the editor unstable).
2. Content Drawer → `/All/Mods/<Mod>` → right-click → Quest Tool Asset → **Quest Blueprint**.
3. Place the entities the quest uses (placeholders, `world-actors.md`): `BP_TriggerPlaceholder`,
   `BP_NPCPlaceholder` (set **Prototype SID**, e.g. `GeneralNPC_Neutral_Recon`), `BP_SquadPlaceholder`
   (Spawned Members Count, Prototype SID, Spawn in Radius), `BP_ItemContainerPlaceholder`, `BP_ItemPlaceholder`,
   `BP_DeadBodyPlaceholder`, `BP_AnomalySpawnerPlaceholder`, `BP_ArtifactSpawnerPlaceholder`,
   `BP_LairPlaceholder`, `BP_DestructibleObjectPlaceholder`, `BP_TeleportPlaceholder` (all under the
   GameDataEditor plugin content). Lift anything that spawned inside geometry.
4. In the QBP, add nodes, pick targets by name or with the pipette (Pick Actor from scene), wire them, save.
5. Test in PIE: quests do not start by themselves. Console (`~`): `xStartQuestBySID <QBPName>`. While it runs, the
   open QBP shows each node's state (active, done, excluded...).
6. Package Mod.

**Starting the quest in the real game** (in game there is no console by default). Options, best first:
- **ModWorldSubsystem (GSC's newer guide; recommended)**: a `ModWorldSubsystem` (`runtime-host.md`) with
  `Event OnWorldBeginPlay` → `Get Object Name(World)` → `Equal, Case Insensitive (String)` with `WorldMap_WP` →
  Branch → True → `Execute Console Command "xStartQuestBySID <QBPName>"`. Fires on every load into the world map
  but does not restart a quest that is already running. Overrides nothing, so it cannot conflict. It starts the
  quest in existing saves too; if it should start only after some story point, make the first nodes of your QBP an
  event or condition gate (e.g. On Journal Quest Event with Track Before Active), not the subsystem.
- **Container in a vanilla quest (GSC's older guide)**: put a Container node for your QBP into a vanilla QBP such as
  `E01_MQ01`, wired from its Start. Ties the start to that quest's progress without extra logic, but it overrides
  the vanilla QBP: it conflicts with every mod that touches the same quest, only starts when that quest runs (a new
  game for `E01_MQ01`) and goes stale on game patches. Use only if the tester accepts that.
- **Console** (`xStartQuestBySID`): PIE and testing only.

**Readable graphs** (GSC's own rule): ordered nodes, no crossing wires, comment blocks (C) and a name on every node.
Keep each concern (e.g. a quest's audio, `audio.md`) in its own QBP run from a Container.

## Signals across graphs
- **Bridge Event**: fires when a chosen node (in any QBP) has finished. Hides long wires. The bridged node gets a
  chain icon and becomes locked (its outputs cannot be renamed or deleted). Cannot watch a dialog node that signals
  without finishing (wire that node to a Technical node and bridge the Technical node). In a QBP that restarts, run
  **Bridge CleanUp** on the bridged nodes (not the bridge) before the container ends, or the bridge will not fire
  again.
- **Technical**: a junction / delay node (merge several wires, wait N seconds). Exclude during the delay cancels it.
- **Random**: picks one output pin by weight (weights indexed like the pins; 0 disables a pin).
- **On Tick Event**: fires once on the QBP's first tick, for nodes that do not depend on quest flow.

## Node catalog
"Ends at once" = finishes right after acting, and exclusion does not undo it. "Until excluded" = stays active and
its effect lasts until you exclude it: always plan that exclusion.

**Spawning and world**
- *Spawn Object NPC Monster* (Spawn): spawns a placeholder's entity. Options: Ignore Damage Type (None /
  Invulnerable / Unkillable but woundable), Spawn Hidden, Exclude Type (Seamless despawn unseen / Force despawn /
  Kill). Ends when the NPC or squad dies, the item is picked up or the container is emptied.
- *Despawn*: Seamless, Force, Kill, or Specific Item Despawn (removes a spawned item wherever it is). Waits for the
  target to spawn first. Ends at once.
- *Toggle NPC Hidden*: Hide (when unseen) / Force Hide / Unhide.
- *Toggle Lair Activity*: Activate or Force Despawn a lair.
- *Enable Data Layer* (old) and *Activate Data Layer Combination* (new; Group + Combination): swap level geometry
  states. Only existing layers/combinations can be used.
- *Activate Anomaly*: triggers an anomaly's active phase; Continue keeps it active until excluded. Many anomalies
  are always on and ignore it (Razor, Flycatcher, Pillow, Psy); Lightning Ball does not work.
- *Activate Restrictor*, *Set Faction Restriction*, *Set Personal Restriction*: switch a ScriptedNavModifierVolume
  (Space Restrictor) on for everyone / one faction / one NPC or squad; In = may not enter, Out = may not leave;
  until excluded.
- *Deactivate Zone*: pauses a SafeZone, Shelter, Hub or SpaceRestrictor zone; exclude to restore (so put it in a
  region-level QBP, not one that ends).
- *A-Life Director Zone Switch*: enable/disable an AlifeZoneTrigger, optionally override its Scenario Group SID.
- *Send Signal* / *On Signal Received*: talk to an interactive object's Signal Receiver / Signal Sender component.
- *Force Interact*: acts as if the player pressed F on an object or placeholder (bIgnoreEnabledCheck forces it).
- *Give Cache*: puts a stash marker on the map, optional extra Item Generator.
- *Load Asset*: preloads heavy assets (e.g. a cutscene sequence) a few seconds ahead; exclude when done.
- *Play Effect* (a `BP_QuestVFX` actor with its Niagara component; Use Setup Particles must be on), *Play Post
  Process* (param usually 10-100), *Play Sound* (AkEvent; Master AkEvent for save loads), *Play Video* (.mp4 via
  a File Media Source), *Sequence Start* (Level Sequence; Loop needs an exclusion).

**Characters and AI**
- *Set AI Behavior*: one node, many goals: Berserker, Escort, Follow, Guard, Kill, Move To, Patrol, Stay, Target
  Shoot, Use Ability, Looting (WIP). Common settings: Priority (Higher than A-Life / Anomaly Fields / Radiation /
  Emission / Combat, or Ignore Threat), Can be interrupted (by dialog), Weapon State (No Weapon / Relaxed / Combat /
  Keep Current), Ignore and FailureBy lists, React on Approach with Weapon, React on Nonenemy sound. Pins: Success,
  Failure, Dead. Follow never ends by itself. Move To targets: Path Legacy (any object), Path (Move To
  Placeholder), Dynamic Object. Stay types: Idle, Contextual Action, Animation (avoid). Kill works offline too
  (outcome computed out of sight).
- *Reset AI*: hands quest NPCs back to A-Life. Required after an encounter unless you despawn them.
- *Protect Placeholder*: immunity to A-Life damage and controller zombification; until excluded.
- *Change Faction*, *Change Relationships* (Absolute / Increase / Decrease / Preset: Enemy -800, Disaffection -400,
  Neutral 0, Friend 800; always both ways; Use Faction Relationship as Personal), *Reputation Locker* (until
  excluded; dangerous on Varta, Spark, Neutrals, Bandits).
- *Add Or Remove From Squad* (needs both squad and NPC placeholders), *Set Wounded* (HP 10, regen 0; heal by Hold
  F, Dialog with Give Medkit, or another Set Wounded), *Teleport Character* (None for NPCs/items; Classic, Immersive,
  Quest for the player; use `BP_TeleportPlaceholder`).
- *Set Character Param*: HP, HP %, Stamina, Bleeding, Hunger, Radiation, Money, Rank, Weight (set / add / subtract
  / multiply / divide), Ignore Damage Type. *Set Character Effect*: apply an effect SID (bleeding, drunkenness,
  radiation, sleepiness, hunger, concussion...; not all work on NPCs).
- *Set Name* (a character SID from TextTool), *Set Mesh Generator* (pair with Set Item Generator so armour stats
  match the look), *Set Emotional State* (face mask; one per NPC), *Set NPC Sequential Ability* (add/remove a
  combat ability with weight; not on squads; an unsuitable ability crashes on save), *Add Technician Skill Or
  Upgrade*, *Set Hub Owner*, *Set Quest Giver* (marker shows within 5000 units).
- *NPC Bark* / *Disable NPC Bark*: play or block a bark event (barks wait for the current one to end).
- *Disable NPC Interactions*: block talk, defeat-state interaction, carrying, looting or despawn of an NPC or
  corpse.
- *Look At*: force the player's camera or an NPC's gaze (Static location, Follow Object, Follow Character Bone e.g.
  `jnt_head`, Exit Look At). Use sparingly.
- *Flashlight On\Off* (Disable Flashlight Control makes it last until excluded), *Equip Item* (forces a slot;
  excluded automatically if the player lacks the item).

**Items**
- *Item Add* / *Item Remove* (Item SID, Items Count, target player / NPC / corpse / container).
- *Set Item Generator* (Replace Inventory, Equip Items flags; on a squad it gives every member the items),
  *Move Inventory* (With Equipped, Move Quest Items), *Switch Quest Item State* (IsQuestItem on/off),
  *Set Durability Param* (Primary / Secondary / Pistol, 0-100).

**Player, journal and world state**
- *Set Journal*: start / finish / fail / cancel / change description of a quest or quest stage, with markers.
  Marker = fixed point; Quest Marker = follows a quest actor (Remove on Death; on a squad each member). Zone markers
  have a radius in cm; Add on Condition / Remove on Condition. Finishing a quest cancels its open stages; failing
  it fails them. Saving warns if a Start has no Finish.
- *Show Marker*: Default → Discovered (question mark) → Explored; never goes back.
- *Set Location Name*, *Add Note* (a note SID; notes and audio logs), *Show Fade Screen* (text or image for Fade
  Time seconds; good placeholder for unfinished art), *Cancel All Side Quests*.
- *Set Global Variable* (Int: set / add / subtract / multiply / divide; or Bool), defined in
  `GlobalVariablePrototypes.cfg`.
- *Set Time* (0-23 h, 0-59 min; avoid Use Transition Time), *Time Lock* (until excluded), *Set Timer* (game hours;
  GSC advises against timers), *Set Weather* (Clearly, Cloudy, Foggy, Stormy, Light Rainy, Rainy, Thundary,
  Emission, Calm Before Emission; blocks the weather controller until excluded).
- *Emission Start* (Default Prototype, Start Quest for the find-shelter quest, Force Emission skips the weather
  blend), *Emission Schedule Control* (Pause / Resume: always resume, or emissions stop for the whole save).
- *Restrict Save* (Manual / Auto / Quick / Quest; until excluded), *Save Game*.

**Events** (all `On ... Event`): Ability Start/End, Dialog Start, Emission Finish, Emission Stage Activated/Finish
(Before the Storm, Activate Quest, Shock Wave, Active, After The Storm), Faction Become Enemy/Friend, Hit (producer
→ receiver), Infotopic Finish, Interact (Start/Finish; quest objects, not Interactable Objects), Journal Quest
(Quest or Stage: Start/Finish/Fail/Cancel/Change Description), Killer Check, Money Amount Reached, NPC Become
Enemy/Friend, NPC Create, NPC Death, NPC Defeat, Player Get Item / Lost Item (only items shown in the inventory UI),
Player Noticed, Player Rank Reached (Newbie, Experienced, Veteran, Master), Signal Received, Tick, Trigger Enter /
Exit, Upgrade Install. The *Trigger* action node also covers enter/exit, with Target Player, Triggers by Anybody,
squad mode (first member / all) and React Type (dead bodies).

**Condition checks**: HP, HPPercent, Stamina, Radiation, Bleeding, Psy, Hunger, Money, Inventory Weight, Is Alive,
Is Online (visualised within 15000 units, unloaded beyond 18000), Is Created, Faction / Personal Relationship, Rank,
Effects, Awareness (Calm 0, TurnHead 100, SearchEnemy 300, MoveToLocation / CallAllies 800, Battle 1000), Note, Item
In Inventory, Item In Container, Has Item Type, Equipment in Hands, Is Aiming, Corpse Carry, AI Target, Global
Variable, Trigger, Distance to NPC, Distance to Point, Look At Angle, Bridge (a node finished), Node State (Not
started / Active / Finished / Excluded), IO State (interactive object states such as IsLocked), Journal State,
Emission, Weather, Player Overload, Is Wounded, Contextual Action, Sleepiness, Is Dialog Member Valid (dialogs only).

**Triggers**: a trigger only counts a character it covers over the full capsule height. GSC's encounter rule: 1-2 m
thick, inside one room or doorway so it cannot fire through walls.

## Dialogs (Dialog Tool)
A **Dialog Blueprint** is built per dialog topic (one per topic) and played by the quest node **Set Dialog**.
Nodes: Start, Label (lines + voice; at most one Dialog Action), Reference Label (a label from another topic),
Wait For Reply (player choice, up to 4), Timed WFR (timeout pin; never 0, no conditions on the timeout), Condition /
If, Random, End. No exclude pins in dialogs.
- End types: Do nothing (only creates an output pin on Set Dialog), Close UI, Return to topic selection; **Finish
  Linked Quest Node** decides whether Set Dialog ends. After changing a dialog's End nodes press **Update Node** on
  every Set Dialog using it and resave those QBPs.
- Blueprint flags: Dialog on the Go (no UI, max 2 replies), Continue after interrupt, Interrupt by combat /
  emission, Main Reply in Topic Selection, DLCName.
- WFR pin options: Main Reply, Answer To, Is Available, Include By, Exclude By, Is Visible on Failed Condition,
  Important Choice Branch.
- Dialog Actions: Open Trade / Upgrade Menu, Heal Player, Give / Get / Show Money, Give Medkit, Show / Give / Get
  Item (up to 3), Eat, Drink, Travel (UI, To Point, Point Selection for guides), Attack, Hit, Threat, Reward, Get
  Side Quest, Faction Relationship Check, Rank, Laugh, Dialog Exit Reply.
- Set Dialog options: Start Forced Dialog, Ignore Global WFR, Is Comment (no UI, no movement lock), Talk Through
  Radio, Voice Modulator, NPC To Start Dialog (or Any member), Can Exit Anytime, Can be interrupted, Override
  Hello / Bye / Info / Defeat / Busy topic (one override per node; lasts until excluded; last one wins).
- Text limits: line 140 chars (max 200), reply 6-70 (max 140), speaker name 18 (max 36), quest description
  300-400, stage 50, item description 500, note 1200, audio log 750.

## Texts and localisation (Mod TextTool)
Editor-only assets (Create Advanced Asset → Mod TextTool), never packaged themselves:
`CharacterModTextToolAsset` (NPC names), `JournalModTextToolAsset` (journal quests and stages),
`LocalizationModTextToolAsset` (any string; **AddExistingLocalizedText** finds a vanilla SID to override),
`DialogModTextToolAsset` (dialog topics for Dialog Blueprints; **AddCharacterToDialog**). Vanilla texts come from
`<kit>\Stalker2\Content\TextToolBackup\TextDatabase.json` (grep it for SIDs). After saving a TextTool asset accept
the refresh prompt or use **Tools → Refresh Mod TextTool**; unrefreshed texts are missing in PIE and in Quest Tool
pickers. Package Mod generates a Mod Localization Database asset from them. Missing languages fall back to
English. Log category `LogModTextToolManager`.

## Quest data configs (all under `GameLite/GameData`; in a mod put new prototypes in the mod's ModGameData folder,
`config-files.md`)
- `ItemPrototypes/QuestItemPrototypes.cfg`: quest items. Minimum `X : struct.begin {refkey=[0]}` + `SID`, `Icon`,
  `IconBig`, `MeshPrototypeSID` (from `MeshPrototypes.cfg`); inherit real weapons/consumables with
  `{refurl=ConsumablePrototypes.cfg;refkey=Bread}`. `IsQuestItem` blocks drop/sell; leave `IsQuestItemPrototype`
  alone (it only picks the TextTool category).
- `NPCPrototypes.cfg` (`SID`, `NameTextKey = sid_character_<SID>`) plus an `ObjPrototypes` entry inheriting
  `QuestNPCBase` with `Faction` and `NPCPrototypeSID`: that SID is what the NPC placeholder selects.
- `NotePrototypes.cfg` (SID only), `GlobalVariablePrototypes.cfg` (`Type = EGlobalVariableType::Int|Bool`,
  `DefaultValue`), `DialogPoolPrototypes.cfg` (runtime barks and busy comments by `EDialogEventType::Busy_*`),
  `EmissionPrototypes.cfg`.
- Generated by the editors on save: QuestNodePrototypes (QBPs), DialogPrototypes / DialogChainPrototypes, JournalPrototypes,
  SpawnActorPrototypes (placeholders).
- Per-quest split configs: rewards in `ItemGeneratorPrototypes/QuestRewardsPrototypes/<Quest>_Reward.cfg`, stash and
  corpse loot from `QuestStashBodyItemGeneratorPrototypes/Template_QuestStashBodyItemGenerator.cfg`, quest NPC kit
  from `QuestNPCGeneratorPrototypes/Template_QuestNPCGenerator.cfg` (copy the template, rename the struct and SID;
  later structs inherit from the first). Prefer named structs over numbered `[34]` ones (no ID clashes).
- Configs are whitespace-sensitive: run PIE after editing; the engine reports bad formatting.

## Debugging quests
- **Quest Tool Validator** runs on QBP save and lists broken nodes with links.
- **Broken Game Data Validator** checks on PIE start, shows results in the Message Log after PIE, and on a crash
  writes logs to `<kit>\Stalker2\Saved\QuestBrokenGameData` (QBP errors) and `...\Saved\BrokenGameData`
  (placeholders and configs), as `EQxx_NodeName` lines. Usual causes: an unset or deleted target, item, faction,
  journal or sound. Fix: reselect it, **Reassign Pointers**, resave. A deleted node that lingers in the QBP config:
  nudge any node one pixel and resave; if that fails, delete its `Name : struct.begin` … `struct.end` block from
  the QBP's QuestNodePrototypes cfg with the editor closed.
- **Runtime quest reload**: add, change or delete nodes during PIE and reload the QBP. Changed Spawn nodes respawn
  their entity; deleted active nodes count as excluded.
- **Quest blueprint search** (Window → Search): find nodes by name, type, SID or QBP across all quests.
- GSC encounter templates to study on `WorldMap_WP`: `GDEQ_Template_SpawnNpcMutants_BP`,
  `GDEQ_Template_ActivateLair_BP`, `GDEQ_Template_AnomalyAct_BP`, `GDEQ_Template_ActivateIntObj_BP`,
  `GDEQ_Template_SpawnObject_BP`.

## Traps
- Spawned quest NPCs ignore contextual actions until given a Set AI Behavior Stay → Contextual Action, or Reset AI.
- A quest NPC that stays quest-bound and goes offline teleports to the edge of the visualiser and follows the
  player; A-Life NPCs despawn instead. Pick on purpose, per encounter.
- Long-running nodes (Protect Placeholder, Reputation Locker, Restrict Save, Time Lock, Set Weather, Emission
  Schedule Pause, restrictors) persist until excluded: always wire their exclusion and set Exclude All Nodes in
  Container on End.
- Two mods editing the same vanilla QBP conflict like any override: start your quest from your own subsystem.
