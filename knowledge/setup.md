# Setting up a new user (agent runbook)

The user may never have used a terminal, Git or a mod editor. Do every step yourself; the user only answers
questions and does the few things a program insists a human does (install from the Epic launcher, approve a GitHub
login in the browser). Explain each human step in one or two plain sentences, one at a time. Commands below are
PowerShell; run `.ps1` tools as `powershell -ExecutionPolicy Bypass -File <path>`.

## 0. Where are we?
- zonecraft is the Claude Code plugin you are running (`<zonecraft>` = two folders up from the skill's base
  directory). Nothing needs cloning.
- Pick a **mods folder** with the user: where their mod projects will live (default `%USERPROFILE%\Documents\Stalker2Mods`).
  Create it and move the session there. `new_mod.ps1` creates each mod as a folder inside it.
- Run `<zonecraft>\tools\setup\setup.ps1` (no switches). It finds the Zone Kit (Epic launcher manifests) and the game
  (Steam libraries), writes the machine settings `%LOCALAPPDATA%\zonecraft\settings.json` (paths and GitHub account;
  never inside a repo), and ends with `check_setup.ps1`. Work through what it reports, in this order:

## 1. Things only the user can do (ask for them early; downloads are long)
- **The game** must be installed and updated. If `setup.ps1` can't find it (not Steam, unusual drive), ask where it
  is and write `"game"` (the folder that contains `Stalker2`, forward slashes) into the machine settings file.
- **The Zone Kit**: "Open the Epic Games launcher, search the store for *S.T.A.L.K.E.R. 2 Zone Kit*, install it (it
  needs about 600 GB), then start it once from the launcher and leave it until the editor window is fully open; the
  first start compiles shaders and takes a long time." Re-run `setup.ps1` afterwards; it finds the install.
- **A GitHub account** if they have none (github.com/signup). Their mods are published there.

## 2. Programs
If Git or the GitHub CLI is missing, tell the user you will install them, then run `setup.ps1 -Install` (winget).
If `winget` itself is missing, ask them to install "App Installer" from the Microsoft Store. New programs are only on
PATH in new shells; `setup.ps1` refreshes PATH for its own run, but restart your shell/tool if later commands can't
find them.

## 3. Identity and GitHub login
- Ask for the name and email to put on their commits (the email can be GitHub's private noreply address), then
  `git config --global user.name "<name>"` and `git config --global user.email "<email>"`.
- `gh auth login --hostname github.com --git-protocol https --web`. It prints a one-time code and opens the browser:
  give the user the code and tell them to approve. If your shell cannot show interactive prompts, ask the user to run
  that exact command in their own terminal and tell you when it says "Logged in".

## 4. Editor remote Python
Lets the tools run Python inside the open editor. Ask the user to close the Zone Kit editor, run
`setup.ps1 -EnableRemotePython` (sets `bRemoteExecution=True` under `[/Script/PythonScriptPlugin.PythonScriptPluginSettings]`
in `<kit>\Stalker2\Config\DefaultEngine.ini`, backup next to it), then ask them to reopen the editor.
Manual equivalent: Edit → Project Settings → Plugins → Python → Enable Remote Execution.

## 5. Verify and hand over
Build the game data index once: `py -I <zonecraft>\tools\data\gamedata.py build` (a few minutes; again after every
Zone Kit update, `config-files.md` § Game data index).
Run `check_setup.ps1` with the editor open; everything must be OK. Then tell the user, in two or three sentences, how
the work goes from here (they describe what they want, you research and build, they test in game and paste into the
editor when asked) and ask what their first mod should do. Create it with `new_mod.ps1`
(`mod-workflow.md` § New mod), choosing the three names with them, then tell them to restart the editor and pick
the new mod once in the toolbar mod selector.


