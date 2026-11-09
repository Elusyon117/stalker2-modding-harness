// The Quest designer's model: the choices its pickers offer (named after the Quest Tool's own nodes and settings,
// knowledge/quests.md), reading a stored draft back, and the brief Claude gets. The form itself is questform.tsx.
import type { QuestCharacter, QuestDraft, QuestStage } from '../types'

export type Option = { value: string; label: string }
const opts = (...labels: string[]): Option[] => labels.map(l => ({ value: l, label: l }))

export const KINDS = opts('Side quest', 'Main story branch', 'Faction quest', 'Repeatable job', 'Hunt', 'Fetch / delivery',
  'Escort', 'Investigation', 'Stash hunt', 'Encounter (no journal)')
export const STARTS = opts('Talk to a quest giver', 'Enter an area (trigger)', 'Pick up an item', 'Read a note or PDA message',
  'After a vanilla quest or stage', 'After another quest of this mod', 'Game start / first load (On Tick Event)',
  'Emission ends', 'Player rank reached', 'Money amount reached', 'An NPC dies')
export const REGIONS = opts('Lesser Zone', 'Zalissya', 'Garbage', 'Cordon', 'Rostok', 'Wild Island', 'Yaniv', 'Swamps',
  'Red Forest', 'Duga', 'Pripyat', 'Chornobyl NPP', 'Several regions', 'New area (Data Layer)')
export const ROLES = opts('Quest giver', 'Target', 'Ally', 'Enemy', 'Companion', 'Trader', 'Witness', 'Victim (wounded)',
  'Squad', 'Mutant', 'Lair')
export const FACTIONS = opts('Loners', 'Duty', 'Freedom', 'Ward', 'Spark', 'Monolith', 'Bandits', 'Mercenaries', 'Noon',
  'Scientists', 'Varta', 'Corps', 'Military', 'Neutrals', 'Mutants', 'None')
export const BEHAVIORS = opts('Stay (idle)', 'Stay (contextual action)', 'Patrol', 'Guard', 'Follow the player', 'Escort',
  'Move to', 'Kill a target', 'Berserker', 'Wounded (Set Wounded)', 'Hidden until needed', 'A-Life (no override)')
export const STAGE_KINDS = opts('Go to', 'Talk to', 'Kill', 'Collect', 'Deliver', 'Defend', 'Escort', 'Find (search area)',
  'Interact with', 'Wait / survive', 'Choose', 'Hide from emission', 'Custom')
export const MARKERS = opts('Marker (fixed point)', 'Quest Marker (follows the target)', 'Zone marker (search radius)',
  'No marker')

/** Offered as one-click additions to each list. */
export const SUGGEST: Record<ListField, string[]> = {
  dialogs: ['Greeting and offer', 'Accept / refuse', 'Haggle for a better reward', 'Report back', 'Lie to the quest giver',
    'Hello / Bye topic override while active'],
  items: ['Quest item (cannot be dropped)', 'Key or keycard', 'Note / audio log (Add Note)', 'PDA data', 'Stash (Give Cache)',
    'Artifact'],
  rewards: ['Money (coupons)', 'An item', 'A unique weapon', 'Reputation with a faction', 'A stash marker',
    'Trader discount or new stock', 'Technician upgrade (Add Technician Skill Or Upgrade)'],
  branches: ['Spare or kill the target', 'Give the item or keep it', 'Side with one faction or the other',
    'Peaceful route through dialog', 'Stealth route'],
  world: ['NPCs spawn / despawn', 'A door or object changes (IO state)', 'Faction relations change (Change Relationships)',
    'Data Layer swap', 'Weather or time set', 'Emission starts', 'Location name or map marker'],
  rules: ['Fails if the quest giver dies', 'Fails if the escort dies', 'Protect quest NPCs (Protect Placeholder)',
    'No saving during the fight (Restrict Save)', 'Timer in game hours', 'Restrict an area (Space Restrictor)',
    'Works in existing saves', 'Must not touch vanilla quests'],
  audio: ['Voiced lines (placeholder text first)', 'NPC barks', 'Music cue', 'Sound effect (AkEvent)', 'Cutscene / sequence'],
}
export type ListField = 'dialogs' | 'items' | 'rewards' | 'branches' | 'world' | 'rules' | 'audio'
export const LIST_FIELDS: { field: ListField; title: string; hint: string; placeholder: string }[] = [
  { field: 'dialogs', title: 'Dialogs', hint: 'Each conversation topic (one Dialog Blueprint per topic).', placeholder: 'Sidorovich asks you to find his courier' },
  { field: 'items', title: 'Items', hint: 'What is found, given, taken or used.', placeholder: "The courier's PDA" },
  { field: 'rewards', title: 'Rewards', hint: 'What the player gets on success.', placeholder: '3000 coupons and a Saiga' },
  { field: 'branches', title: 'Choices and branches', hint: 'Where the player decides, and what each way leads to.', placeholder: 'Return the PDA or sell it to the bandits' },
  { field: 'world', title: 'World changes', hint: 'What changes in the Zone while or after it runs.', placeholder: 'The bandit camp is cleared for good' },
  { field: 'rules', title: 'Rules and failure', hint: 'What must hold, what fails it, what it must not break.', placeholder: 'Fails if the player kills the courier' },
  { field: 'audio', title: 'Audio and presentation', hint: 'Voice, barks, music, cutscenes.', placeholder: 'Radio message when the stage starts' },
]

export const EMPTY_CHARACTER: QuestCharacter = {
  name: '', role: 'Quest giver', faction: 'Loners', sid: '', behavior: 'Stay (idle)', count: '1', notes: '',
}
export const EMPTY_STAGE: QuestStage = { kind: 'Go to', text: '', marker: 'Marker (fixed point)', optional: false }

export function emptyQuest(modRoot: string): QuestDraft {
  return {
    modRoot, sid: '', title: '', kind: 'Side quest', summary: '', journal: '', start: 'Talk to a quest giver',
    startDetail: '', region: 'Lesser Zone', place: '', characters: [], stages: [], dialogs: [], items: [], rewards: [],
    success: '', failure: '', branches: [], world: [], rules: [], audio: [], languages: 'English', notes: '',
    pending: { character: EMPTY_CHARACTER, stage: EMPTY_STAGE }, sentAtMs: 0, savedAtMs: 0,
  }
}

export const clean = (s: string) => s.replace(/\s+/g, ' ').trim()

/** A quest SID from a title: letters and digits, words joined (the mod's short prefix goes in front). */
export function questSid(title: string, prefix: string): string {
  const words = title.split(/[^A-Za-z0-9]+/).filter(Boolean).map(w => w[0].toUpperCase() + w.slice(1)).join('')
  return `${prefix ? `${prefix}_` : ''}${words || 'NewQuest'}`
}

/** A stored or saved draft read back; fields it lacks take the empty quest's. */
export function asQuest(v: unknown, modRoot: string): QuestDraft {
  const base = emptyQuest(modRoot)
  if (!v || typeof v !== 'object') return base
  const o = v as Record<string, unknown>
  const str = (k: keyof QuestDraft) => (typeof o[k] === 'string' ? (o[k] as string) : (base[k] as string))
  const list = (k: string) => (Array.isArray(o[k]) ? (o[k] as unknown[]).filter((s): s is string => typeof s === 'string') : [])
  const rec = <T extends object>(x: unknown, d: T): T => {
    if (!x || typeof x !== 'object') return d
    const out = { ...d } as Record<string, unknown>
    for (const [k, dv] of Object.entries(d)) {
      const xv = (x as Record<string, unknown>)[k]
      if (typeof xv === typeof dv) out[k] = xv
    }
    return out as T
  }
  const pending = (o.pending ?? {}) as Record<string, unknown>
  return {
    ...base,
    sid: str('sid'), title: str('title'), kind: str('kind'), summary: str('summary'), journal: str('journal'),
    start: str('start'), startDetail: str('startDetail'), region: str('region'), place: str('place'),
    success: str('success'), failure: str('failure'), languages: str('languages'), notes: str('notes'),
    characters: Array.isArray(o.characters) ? o.characters.map(c => rec(c, EMPTY_CHARACTER)) : [],
    stages: Array.isArray(o.stages) ? o.stages.map(s => rec(s, EMPTY_STAGE)) : [],
    dialogs: list('dialogs'), items: list('items'), rewards: list('rewards'), branches: list('branches'),
    world: list('world'), rules: list('rules'), audio: list('audio'),
    pending: { character: rec(pending.character, EMPTY_CHARACTER), stage: rec(pending.stage, EMPTY_STAGE) },
    sentAtMs: typeof o.sentAtMs === 'number' ? o.sentAtMs : 0,
    savedAtMs: typeof o.savedAtMs === 'number' ? o.savedAtMs : 0,
  }
}

/** What the quest still needs before Claude can build it; empty when it is ready. */
export function questGaps(q: QuestDraft): string[] {
  const out: string[] = []
  if (!q.modRoot) out.push('a mod')
  if (!clean(q.title)) out.push('a title')
  if (!clean(q.summary)) out.push('a summary')
  if (q.stages.length === 0) out.push('at least one stage')
  return out
}

export function characterLine(c: QuestCharacter): string {
  const n = c.count && c.count !== '1' ? ` ×${c.count}` : ''
  return `${c.name}${n} (${c.role}, ${c.faction}, ${c.behavior}${c.sid ? `, vanilla SID ${c.sid}` : ', new character'})` +
    (c.notes ? `: ${c.notes}` : '')
}

export function stageLine(s: QuestStage, i: number): string {
  return `${i + 1}. [${s.kind}] ${s.text} (${s.marker}${s.optional ? ', optional' : ''})`
}

/** The prompt Claude gets: the quest as designed, and how to build it. */
export function questBrief(q: QuestDraft, modName: string, savedPath?: string): string {
  const list = (items: string[]) => items.map(s => `- ${s}`).join('\n')
  const block = (title: string, items: string[]) => (items.length ? ['', `${title}:`, list(items)] : [])
  const line = (label: string, v: string) => (clean(v) ? [`${label}: ${v.trim()}`] : [])
  return [
    `I designed a quest for my mod ${modName} (${q.modRoot}) in the zonecraft Quest designer. Build it with me.`,
    ...(savedPath ? [`The design is saved as ${savedPath}.`] : []),
    '',
    `Title: ${clean(q.title)}`,
    ...line('Quest SID', q.sid),
    `Kind: ${q.kind}`,
    `Summary: ${q.summary.trim()}`,
    ...line('Journal text', q.journal),
    `Starts: ${q.start}${clean(q.startDetail) ? ` (${q.startDetail.trim()})` : ''}`,
    `Where: ${q.region}${clean(q.place) ? `, ${q.place.trim()}` : ''}`,
    ...block('Characters', q.characters.map(characterLine)),
    '',
    'Stages, in order:',
    ...q.stages.map(stageLine),
    ...block('Dialogs', q.dialogs),
    ...block('Items', q.items),
    ...block('Rewards', q.rewards),
    ...line('Success', q.success),
    ...line('Failure', q.failure),
    ...block('Choices and branches', q.branches),
    ...block('World changes', q.world),
    ...block('Rules and failure conditions', q.rules),
    ...block('Audio and presentation', q.audio),
    ...line('Languages', q.languages),
    ...line('Notes', q.notes),
    '',
    'Follow knowledge/quests.md: plan the QBP (Quest Blueprint) node by node first, with each stage\'s Set Journal, ' +
      'the placeholders and spawns, dialogs per topic, texts in the Mod TextTool, and the exclusion of every ' +
      'long-running node. Show me the plan, ask about anything unclear, add the quest as a feature in PLAN.md, then ' +
      'tell me step by step what to build in the Quest Tool and the Dialog Tool.',
  ].join('\n')
}
