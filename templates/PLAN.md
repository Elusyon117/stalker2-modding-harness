# {{MOD}} — plan

## Idea
{{DESCRIPTION}}

## Features
_(one `- [ ]` line per feature the tester wants; tick it `- [x]` once the tester confirms it works in game. The
zonecraft panel shows this list as the mod's progress.)_

## Details to check
_(one `- [ ]` line per question to settle or case to test; tick it once settled.)_

## How the game does it today (evidence: kit file:line, probe runs, tester reports)
_(research first: zonecraft's knowledge/zonekit.md)_

## Approach, cheapest and least conflicting first
Prefer, in order: a cfg patch file → a NewContent runtime host (ModWorldSubsystem + actor) → an asset override
(only with the tester's explicit decision; list who else overrides it).

| Layer | Change | Ships as | Conflicts |
|---|---|---|---|
| 1 | | | |

## Open questions and how each gets answered
| Question | Answered by (kit grep / tester opens asset / probe / test run) |
|---|---|

## Test matrix (all must pass before a release)
| # | Setup | Steps | Expected |
|---|---|---|---|
| 1 | vanilla keys, keyboard | | |
| 2 | rebound keys | | |
| 3 | gamepad | | |
| 4 | with our other mods installed | | |
| 5 | save / load mid-action, death, cutscene | | |
