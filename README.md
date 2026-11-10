<p align="center">
  <img src="assets/logo.gif" alt="zonecraft: a pixel crab in a gas mask sits by a campfire roasting a sausage in front of a nuclear plant while an anomaly pulses" width="600">
</p>

<h1 align="center">zonecraft</h1>

<p align="center">
  <b>Make your own S.T.A.L.K.E.R. 2 mods by talking to Claude.</b><br>
  No modding, terminal or coding experience needed.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FElusyon117%2Fzonecraft%2Fmain%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=e8772e" alt="version">
  <img src="https://img.shields.io/badge/Claude_Code-plugin-e8772e" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/S.T.A.L.K.E.R._2-Zone_Kit-4a4944" alt="S.T.A.L.K.E.R. 2 Zone Kit">
  <img src="https://img.shields.io/badge/platform-Windows-4a4944" alt="Windows">
  <img src="https://img.shields.io/badge/license-MIT-4a4944" alt="MIT license">
</p>

<p align="center">
  <a href="#install">Install</a> ·
  <a href="#get-started">Get started</a> ·
  <a href="#make-a-mod">Make a mod</a> ·
  <a href="#the-panels">The panels</a> ·
  <a href="#handy-things-to-say">Things to say</a> ·
  <a href="#whats-inside">What's inside</a>
</p>

---

zonecraft is a Claude Code plugin for **S.T.A.L.K.E.R. 2: Heart of Chornobyl** and GSC's official mod editor, the
**Zone Kit**. You say what the mod should do; Claude plans it, writes it, builds it, installs it into your game for
testing and packages it for Nexus Mods. It gives Claude:

- **Rules** for working with you: what to check before building anything, what never to do.
- **Hard-won knowledge** from shipping real mods: how the game and the Zone Kit behave, which approaches crash the
  game, how to stay compatible with other popular mods.
- **GSC's official Zone Kit guides, digested**: all 26 support-site guides and the Quest Tool manual folded in, in
  its own words (quests and dialogs, world actors, audio, weapons, cfg patches, packaging, publishing), each with a
  link to the original.
- **Tools** that set up your PC, write Blueprint logic you paste into the editor (and check it arrived intact), build
  your mod, install it for testing and package it for release.
- **Panels** beside the chat that show where every mod stands, with Clawd keeping you company.

## Install

In a Claude Code terminal session, type:

```
/plugin install zonecraft --marketplace Elusyon117/zonecraft
```

Answer `y` to add the marketplace, then pick the user scope so it loads in every session. From a shell instead:

```bash
claude plugin install zonecraft --marketplace Elusyon117/zonecraft
```

**Desktop app:** click **+** next to the prompt box → **Plugins** → **Add marketplace** → `Elusyon117/zonecraft` →
**Add plugin**.

Update later with `claude plugin marketplace update elusyon-zonecraft`, then `claude plugin update zonecraft`.

Claude uses the `zonecraft` skill by itself whenever you talk about Stalker 2 modding, or you can type `/zonecraft`.

## Get started

You need a **Windows PC with the game installed**, about **600 GB of free disk space** for the Zone Kit, and
**Claude Code** with zonecraft installed.

1. **Install the Zone Kit** (the one thing Claude can't do for you): open the **Epic Games Store**, search for
   **S.T.A.L.K.E.R. 2 Zone Kit**, install it, start it once and let it finish its first start (it takes a long time).
   You can do step 2 while it downloads.
2. **Open Claude Code** and send it this:

   > Set me up to make S.T.A.L.K.E.R. 2 mods with zonecraft.

That's it. Claude picks a folder for your mods with you, installs what's missing, finds your game and the Zone Kit,
and asks you a few questions (your name, your GitHub account; it helps you make one if you have none). Twice it will
ask you to do something yourself: approve a GitHub login in your browser, and close and reopen the Zone Kit editor.

## How it works

| You | Claude |
|---|---|
| Say what the mod should do | Researches how the game does it and writes a plan |
| Play the game and say what you see ("it worked", "nothing happened", "it crashed when I sat down") | Reads the game's logs and crash reports itself |
| Click or paste in the Zone Kit editor when asked (it tells you exactly where; pasting is Ctrl+V) | Writes the logic, builds the mod, installs it into your game |
| Say when to publish | Packages the release and writes the notes |

After setup you never type commands. You talk in plain language.

## Make a mod

Tell Claude what you want, in your own words:

> I want a mod that makes the flashlight brighter and wider.

It suggests a name, creates the mod (its own folder and GitHub page), researches the game and writes a plan in
`PLAN.md`. Read the plan, say what you think, then say *"go ahead"*. From then on, each round goes like this:

1. Sometimes Claude asks you to do something in the Zone Kit editor: open something and take a screenshot, or paste
   text it prepared (click into the window it names, press **Ctrl+V**, then **Compile** and **Save**). Tell it when
   you're done.
2. It builds the mod (about 5-6 minutes) and installs a test copy into your game. Keep the game closed until it says
   it's installed.
3. It tells you what to do in the game and what should happen.
4. You play and tell it what you saw.

One change per round, so when something breaks you always know what caused it. When something works the way you
want, say *"that works, save a checkpoint"*. Next time, open Claude Code in the mod's folder and ask
*"where were we?"*.

Not sure yet what the mod should do? Type **`/zonecraft-newmod`** and fill in the form below.

## The panels

zonecraft's panels open beside the chat. Type the command on each card, or let Claude open them when they help.

<p align="center"><img src="assets/screens/dashboard.svg" alt="The zonecraft dashboard: a mod's page with its build, test copy, plan and Blueprint pastes, and Clawd at his campfire" width="880"></p>

With more than one mod, the dashboard opens on **All mods**: a status line per mod (packaging now, last build, test
copy, features done, conflicts). Pick one to open its page.

<p align="center"><img src="assets/screens/nodes.svg" alt="Show nodes: a Blueprint paste's comment box drawn as the Zone Kit graph editor will show it, with the wires to draw by hand" width="880"></p>

<p align="center"><img src="assets/screens/build.svg" alt="The Build and test band above the prompt: a packaging in progress with its stage and time, then the finished build with Install test copy and the features to try" width="880"></p>

<p align="center"><img src="assets/screens/newmod.svg" alt="The New mod form: release candidate naming, the mod's name, main idea, features and details to check, and Send to Claude" width="880"></p>

<p align="center"><img src="assets/screens/quest.svg" alt="The Quest designer: the quest's basics, start and place, characters, ordered stages with markers, rewards, branches and rules, and Send to Claude" width="880"></p>

<p align="center"><img src="assets/screens/data.svg" alt="The Game data browser: the AK74 entry with its values, one being changed, and the patch to add to the mod" width="880"></p>

<p align="center"><img src="assets/screens/conflicts.svg" alt="The Conflicts panel: the mods scanned with their mount order, and each conflict with its winner and an Ask Claude button" width="880"></p>

<p align="center"><img src="assets/screens/logs.svg" alt="The Logs panel: the last packaging, a crash with its known family and advice, and warnings from the game and kit logs" width="880"></p>

<p align="center"><sub>Example content: your own mods show up instead.</sub></p>

| Command | Opens |
|---|---|
| `/zonecraft-panel` | The dashboard: All mods, each mod's page, Blueprint pastes with **Copy**, **Show nodes**, **Open graph**, **Pasted it: check** and **Fix it** |
| `/zonecraft-newmod` | The New mod form |
| `/zonecraft-quest` | The Quest designer |
| `/zonecraft-data` | The Game data browser |
| `/zonecraft-conflicts` | The conflict check |
| `/zonecraft-logs` | Packaging, crashes and log warnings |
| *(automatic)* | The Build & test band above the prompt, while you press **Package Mod** |

## Handy things to say

| Say | What happens |
|---|---|
| *"Where were we?"* | It reads the mod's notes and tells you the current state and next step |
| *"Save a checkpoint"* | It saves the current working state so it can always return to it |
| *"Roll back to the last checkpoint"* | Undo everything since the last good state |
| *"Remove the test copy"* | Takes your test build out of the game so you can play normally |
| *"Check my setup"* | Runs the setup check and fixes what it can |
| *"Cut a release, version 1.0.0"* | Final build, notes, a zip in your Downloads folder ready for Nexus Mods, test copy removed |
| *"Share what we learned"* | Adds the lesson to zonecraft so every mod gets it |
| *"Update zonecraft"* | Installs the latest zonecraft |

## Publishing on Nexus Mods

After *"cut a release"*: on [nexusmods.com](https://www.nexusmods.com) (free account), open the S.T.A.L.K.E.R. 2
section, choose to upload a mod, fill in the page (name, description, screenshots) and upload the zip from your
Downloads folder. Paste the release notes Claude wrote into the changelog. Tell Claude the mod's Nexus ID so it can
record it.

## If something goes wrong

Describe it to Claude the way you'd describe it to a friend: what you did, what you expected, what happened. It
reads the game's logs and crash reports itself. A few things worth knowing:

- New mods only appear in the Zone Kit's mod list after you restart the editor.
- After a game update, update the Zone Kit in the Epic launcher too, then ask Claude to rebuild your mods.
- If the Zone Kit editor crashes every time it starts, tell Claude; there is a known fix.

<details>
<summary><b>Words you will see</b></summary>
<br>

| Word | Meaning |
|---|---|
| **Zone Kit** | GSC's official mod editor for S.T.A.L.K.E.R. 2 (a version of Unreal Engine 5.5). |
| **Blueprint** | Unreal's visual scripting: boxes connected by wires. Claude writes them as text you paste. |
| **Asset** | A game file inside the editor: a Blueprint, an animation, an input setting. |
| **Override** | Replacing one of the game's own assets with an edited copy. Two mods can't both override the same asset, so Claude avoids it. |
| **Cook / build** | Turning the editor's files into the compact files the game loads (5-6 minutes). |
| **Pak** | The finished mod files (`.pak`, `.ucas`, `.utoc`) that go into the game's `~mods` folder. |
| **cfg patch** | A small text file that changes single game values (damage, speeds) without replacing whole files. |
| **Checkpoint** | A saved, known-good state of your mod. |
| **Repository / GitHub** | Where each mod's files and history are stored online. |
| **MCM** | Mod Configuration Menu, a popular mod that adds an in-game settings screen for other mods. |

</details>

## What's inside

| Folder | What |
|---|---|
| [`skills/zonecraft/`](skills/zonecraft/SKILL.md) | The skill Claude loads: rules, session start, where everything is |
| [`knowledge/`](knowledge/) | What is known about the game, the Zone Kit and the pipeline ([setup](knowledge/setup.md), [blueprints](knowledge/blueprints.md), [animation](knowledge/animation.md), [quests](knowledge/quests.md), [world actors](knowledge/world-actors.md), [audio](knowledge/audio.md), [weapons](knowledge/weapons.md), [official guides](knowledge/zonekit-guides.md), [tools](knowledge/tools.md), ...) |
| [`tools/`](tools/) | `setup/`, `build/`, `editor/`, `blueprints/` (node library, paste checker, paste pictures), `pak/`, `data/`. PowerShell plus the Python that ships inside the Zone Kit; nothing else to install |
| [`hooks/`](hooks/) | The panels beside the chat and the Build & test band |
| [`templates/`](templates/) | The files a new mod starts with |
| [`probe/`](probe/) | UE4SS debug probes (your PC only, never shipped) |
| [`assets/`](assets/) | The logo, the icon, Clawd's scenes and the README pictures, all drawn by Python scripts |
| [`tests/`](tests/) | Offline tests for the Blueprint tools, the game data index and the panels |
| [`.claude-plugin/`](.claude-plugin/) | Plugin manifest, marketplace, icon |

Each mod lives in its own folder and repository and holds only the mod; the tools and knowledge stay here, so
updating zonecraft updates every mod.

Mods made with the original harness: [Immersive Dialogue](https://github.com/noahsemus/stalker2-immersive-dialogue),
[Immersive Campfires](https://github.com/noahsemus/stalker2-immersive-campfires),
[Immersive Reloading](https://github.com/noahsemus/stalker2-immersive-reloading).
Contributions are welcome as pull requests.

## Meet Clawd

zonecraft's crab, in his gas mask, doing what stalkers do in the Zone. He sits in the corner of every panel and
changes scene with what you are doing; the scenes are drawn by [`assets/clawd_scenes.py`](assets/clawd_scenes.py).

<p align="center"><img src="assets/screens/clawd.svg" alt="Clawd, zonecraft's crab in a gas mask, in twelve scenes: by the campfire, playing the guitar, plotting a route, exploring the Zone, throwing bolts, hunting artifacts, hunting mutants, looting a stash, trading, stories at the fire, fixing his gear, sleeping it off" width="880"></p>

## Credits and license

zonecraft is built on Noah Semus's [stalker2-modding-harness](https://github.com/noahsemus/stalker2-modding-harness)
(MIT): its knowledge and tools are the core of this plugin.

MIT (see [LICENSE](LICENSE)). S.T.A.L.K.E.R. 2 and its assets belong to GSC Game World; this repository contains no
game files. Mods you make are yours; check GSC's modding terms and Nexus Mods' rules before publishing.

<sub>Unofficial fan project, not affiliated with GSC Game World or Anthropic. The crab in the logo is drawn in the style
of Clawd, Anthropic's Claude Code mascot; the plant in the background is original pixel art.</sub>
