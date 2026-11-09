# {{MOD}} — mod context for Claude

This is a S.T.A.L.K.E.R. 2 mod made with [zonecraft](https://github.com/Elusyon117/zonecraft). **Load the
`zonecraft` skill first**: it holds the shared rules, the tester workflow and where the tools and knowledge are. This
file holds only what is specific to this mod.

Purpose: {{DESCRIPTION}}

Repo `{{OWNER}}/{{REPO}}`, Zone Kit plugin `{{MOD}}` (`/{{MOD}}/`), asset prefix `{{SHORT}}`. Created with zonecraft
on {{DATE}}.

## Current state (one line per checkpoint / release: date, what changed, what the tester confirmed in game)
- {{DATE}}: repo created. Next: the tester picks `{{MOD}}` in the editor's toolbar mod selector once
  (GameFeatureData), then kit research for PLAN.md.

## Key facts (verified; cite file:line in the kit)
- _(fill in as research lands)_

## Assets this mod may override
- _(none yet; see zonecraft's knowledge/compatibility.md before adding any)_

## Files
- `PLAN.md` idea, feature checklist (the zonecraft panel shows it; tick a feature once the tester confirms it in
  game), details to check, plan and test matrix · `BUILD.md` every edit asset by asset · `zonekit/README.md` engineering log
  (what each test showed, dead ends) · `zonekit/{{MOD}}/` plugin mirror · `zonekit/tools/` mod-specific generators
  (`gen_*.py`, which import zonecraft through `zonecraft_path.py`) and classifier lists · `zonekit/builds/` checkpoint
  and release paks · `mod.json` names and pak suffixes.

## Release (only when the tester says "cut a release")
Follow zonecraft's `knowledge/pipeline.md` § Release. Nexus page: _(record the mod id here once it exists)_.
