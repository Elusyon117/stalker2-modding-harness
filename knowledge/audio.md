# Audio mods (Wwise)

Sources: GSC's "Zone Kit – Audio modding quick start guide" and the audio chapter of the Quest Tool Complete Guide
(`zonekit-guides.md`). The game's sound is Audiokinetic Wwise; the kit ships the game's Wwise project and the
original audio so mods can change or add sounds.

## Needs
- The Zone Kit **Originals** pack (source `.wav`s under `<kit>\Originals\SFX\...`, e.g. `S2_Live\01. Menu Theme.wav`).
- **Wwise Authoring 2024.1.10.8979** exactly (the version the project was made with).
- New audio must be `.wav` (PCM).

## Workflow
1. Select the mod in the toolbar. Toolbar → **Audio Modding → Open Wwise Project** opens `S2_WwiseProject` for
   that mod.
2. Find what plays the sound: Project Explorer → **Events** tab (or Search). Example: the main menu is event
   `SFX_UI_MainMenu` (S2 Live → UI → Game Initialization work unit); its actions play the `M_MainMenu` Music Switch
   Container and the `MenuSFX` Blend Container. With Project Explorer set to *Follow Object Selection*, double-click
   an action's target to jump to it in the Actor-Mixer or Interactive Music hierarchy. *Show References* lists who
   uses an object.
3. Listen: select a container and press Space (Transport Control), or use the Soundcaster (Shift+S) to play events
   while changing States, Switches and RTPCs (e.g. `ST_GameState` = `MainMenu`, `RTPC_SFXVolume`,
   `RTPC_MusicVolume`). Names shown in blue are unconverted: Shift+C converts them.
4. Change it, either way:
   - **Into the existing hierarchy** (simplest): drag the `.wav` into the right container (e.g. the `M_MainMenu`
     Music Playlist Container), import, then add the new segment to the playlist order. Properties are inherited
     from the parents.
   - **Own hierarchy**: a new work unit, your containers under it (e.g. a Sequence Container, Play Mode
     Continuous, Loop, Xfade transition), route it to the right **Output Bus** (e.g. `MainMenuMusic`) so the game's
     volume sliders still apply, then drag it into the event's actions; disable the original Play action if yours
     replaces it.
5. Save (Ctrl+S). **Generate SoundBanks** (F7 layout): Auto-Defined banks are fine (pick platform and language,
   Generate); User-Defined banks only for advanced control.
6. In the kit: **Audio Modding → Wwise Browser**, find the event, *Find in Content Browser*, and **Checkout** the
   `AkAudioEvent` (and other changed Wwise assets) into the mod. Space in the Content Browser previews it.
7. New events: create them in Wwise, generate banks, then select them in the Wwise Browser and **Reconcile**: the
   new `AkAudioEvent` assets are created and checked out into the mod automatically.
8. Package Mod.

## Switching mods
Each mod has its own copy of the Wwise project. Close Wwise (save first), select the other mod, Open Wwise Project
again, and **regenerate SoundBanks** whenever you come back to a mod.

## Sounds from quests
The quest node **Play Sound** posts an AkEvent at a Target Location (an AkAmbient actor or any placed actor; unpack
Level Instances in the Outliner to pick one inside), with an optional Master AkEvent for save loads and Repeatable.
GSC keeps a quest's audio in its own QBP named `<Quest>_Audio`, started from the quest by a Container, and triggers
sounds with Bridge Event, On Trigger Enter/Exit, Condition gates, On Signal Received (buttons, switches) or On Player
Noticed (`quests.md`).
- Every looping sound needs a Stop event; set the Stop's Scope to **Global** if the loop is not tied to an object.
- Prefer doing logic inside Wwise events (they can stop sounds too) over extra graph nodes.

## Naming conventions in the game's data (useful for finding things)
- Generic voice lines: AkEvent `VO_General_<CharacterSID>_<Event>_<PhraseID>` in
  `_STALKER2/Audio/WwiseAudio/Events/Voiceover/General/<EventType>/`; voices are switches `Voice-A`, `Voice-B`...
- Quest voice lines: `.../Events/Voiceover/{MainQuests,SideQuests,Encounters,Hubs,ANC,Bossfights}/<Quest>/<Character>/`.
- Bark categories by event-name prefix `General_<CharacterSID>_NPC_{Interact,Emission,Combat,HitReaction,Reaction,
  Contextual,QContextual,Peacefull,Radio,Speakers}_*`; player lines `General_<CharacterSID>_Player_*`.
- Face animation: `AS_FAC_...` under `_STALKER2/Animations/CharacterHead/`.
