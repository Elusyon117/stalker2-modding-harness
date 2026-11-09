// /zonecraft-quest: the Quest designer. A mod is picked at the top, so every quest belongs to one; each mod keeps
// its own draft (in $.store) and its saved designs (<mod>/zonekit/quests/<SID>.json). "Send to Claude" hands the
// quest over as a brief to plan the Quest Blueprint from.
import { atom, read, update } from 'claude-code'
import type { EngineInterface as Engine, On } from 'claude-code'

import type { QuestCharacter, QuestDraft, QuestStage } from '../types'
import { age, chooseMod, join, knownMods, modJson, readSettings } from './data'
import {
  BEHAVIORS, FACTIONS, KINDS, LIST_FIELDS, MARKERS, REGIONS, ROLES, STAGE_KINDS, STARTS,
  SUGGEST, asQuest, characterLine, clean, emptyQuest, questBrief, questGaps, questSid, stageLine,
} from './quest'
import type { ListField } from './quest'
import { action, ORANGE, section } from './theme'

export const QUEST_PANE = 'zonecraft-quest'
const TOOL = 'mcp__zonecraft__quest_designer'
const storeKey = (root: string) => `quest-draft:${root.toLowerCase()}`
const QUESTS_DIR = 'zonekit/quests'

const quest = atom({ plugin: 'zonecraft', key: 'quest' } as const, emptyQuest(''), { shape: 'quest-1' })

const strings = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [])

async function saved($: Engine, root: string): Promise<{ name: string; path: string; mtimeMs: number }[]> {
  if (!root) return []
  const dir = join(root, QUESTS_DIR)
  try {
    const out = []
    for (const f of await $.fs.list(dir)) {
      if (f.kind !== 'file' || !f.name.toLowerCase().endsWith('.json')) continue
      const path = join(dir, f.name)
      out.push({ name: f.name.replace(/\.json$/i, ''), path, mtimeMs: (await $.fs.stat(path)).mtimeMs })
    }
    return out.sort((a, b) => b.mtimeMs - a.mtimeMs)
  } catch {
    return []
  }
}

async function open($: Engine) {
  return $.ui.open({ id: QUEST_PANE, title: 'Quest designer' })
}

export async function questSessionStart($: Engine) {
  await $.command.register({
    name: 'zonecraft-quest',
    description: 'Design a quest for one of your mods: characters, stages, dialogs, rewards, branches and rules',
  })
  await $.tool.register({
    name: 'quest_designer',
    description:
      'Opens the zonecraft Quest designer beside the chat: the user picks one of their Stalker 2 mods and lays out ' +
      'a quest (start, place, characters, stages with markers, dialogs, items, rewards, branches, world changes, ' +
      'rules, audio), then sends it to you as a brief. Call it when the user wants to add a quest but has not ' +
      'described it in detail.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  })
}

export function registerQuest(on: On) {
  on('command.run', { command: 'zonecraft-quest' }, async $ => {
    const { isPlaced } = await open($)
    return { text: isPlaced ? 'Quest designer opened.' : 'Quest designer opened (shown where your app has room for panes).' }
  })

  on('tool.call', { tool: TOOL }, async $ => {
    const { isPlaced } = await open($)
    return {
      result: isPlaced
        ? 'The Quest designer is open beside the chat. Tell the user to pick the mod, fill it in and press "Send to ' +
          'Claude"; the quest arrives as their next message.'
        : 'This app shows no panes right now; ask the user about the quest in the chat instead.',
    }
  }).catch(() => ({ result: 'The Quest designer could not be opened; ask the user to type /zonecraft-quest.' }))

  on('ui.render', { component: 'Pane', requestId: QUEST_PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const els = { Box, Text, Button }
    const now = await $.clock.now()
    const settings = await readSettings($)
    const mods = await knownMods($, await $.session.cwd(), settings, strings(await $.store.get('mods-seen')))
    let q = await read($, quest)
    const lastPicked = await $.store.get('mod-picked')
    const current = chooseMod(mods, q.modRoot, typeof lastPicked === 'string' ? lastPicked : '')

    // First draw, or the draft's mod is gone: show the chosen mod's kept draft (drawing only reads; the first
    // change writes it into the state).
    const same = (a: string, b: string) => a.toLowerCase() === b.toLowerCase()
    if (current && !same(q.modRoot, current.root)) {
      q = asQuest(await $.store.get(storeKey(current.root)).catch(() => undefined), current.root)
    }
    const shown = q
    if (!current) {
      return section(els, 'nomod', 'Quest designer', undefined,
        <Text dimColor wrap="wrap">No mod to add a quest to. Open Claude Code in a mod folder, set mods_dir in the machine settings, or make one with /zonecraft-newmod.</Text>)
    }
    const mod = await modJson($, current.root)
    const prefix = typeof mod.short === 'string' ? mod.short : ''

    const change = async (fn: (d: QuestDraft) => QuestDraft) => {
      let next = shown
      await update($, quest, cur => (next = fn(same(cur.modRoot, shown.modRoot) ? cur : shown)))
      await $.store.set(storeKey(next.modRoot), next)
    }
    const set = (patch: Partial<QuestDraft>) => change(cur => ({ ...cur, ...patch }))
    const pickMod = async (root: string) => {
      await $.store.set(storeKey(shown.modRoot), shown)
      const kept = asQuest(await $.store.get(storeKey(root)).catch(() => undefined), root)
      await update($, quest, () => kept)
      await $.store.set('mod-picked', root)
    }

    if (e.surface !== 'terminal' && e.surface !== 'desktop' && e.surface !== 'vscode') {
      return (
        <Box flexDirection="column" gap={1}>
          {section(els, 'q', q.title || 'Quest designer', `${current.name}${q.summary ? ` · ${q.summary}` : ''}`,
            ...q.stages.map((s, i) => <Text key={`s:${i}`}>{stageLine(s, i)}</Text>))}
          <Text dimColor>Fill in the designer on your PC (type /zonecraft-quest there).</Text>
        </Box>
      )
    }
    const { Input, Select } = $.ui.resolve({ ...e, surface: e.surface })
    const field = (key: keyof QuestDraft, label: string, placeholder: string, rows?: number) => (
      <Input key={`f:${key}`} label={label} placeholder={placeholder} rows={rows} value={q[key] as string}
        onInput={v => set({ [key]: v } as Partial<QuestDraft>)} onSubmit={v => set({ [key]: v } as Partial<QuestDraft>)} />
    )
    const pick = (key: keyof QuestDraft, label: string, options: { value: string; label: string }[]) => (
      <Select key={`p:${key}`} label={label} options={options} value={q[key] as string}
        onSelect={v => set({ [key]: v } as Partial<QuestDraft>)} />
    )
    const move = <T,>(items: T[], i: number, by: number): T[] => {
      const j = i + by
      if (j < 0 || j >= items.length) return items
      const out = [...items]
      ;[out[i], out[j]] = [out[j], out[i]]
      return out
    }
    const rowButtons = (key: string, onUp: () => void, onDown: () => void, onRemove: () => void) => [
      <Button key={`${key}:up`} dimColor onPress={onUp}>↑</Button>,
      <Button key={`${key}:down`} dimColor onPress={onDown}>↓</Button>,
      <Button key={`${key}:x`} dimColor onPress={onRemove}>Remove</Button>,
    ]

    // ── Mod and saved designs
    const designs = await saved($, current.root)
    const save = async () => {
      const sid = clean(q.sid) || questSid(q.title, prefix)
      const path = join(current.root, QUESTS_DIR, `${sid}.json`)
      const next = { ...q, sid, savedAtMs: now }
      await $.fs.write(path, `${JSON.stringify({ ...next, pending: undefined }, null, 2)}\n`)
      await change(() => next)
      await $.ui.toast(`Saved ${current.name}/${QUESTS_DIR}/${sid}.json`)
      return path
    }
    const load = async (path: string) => {
      try {
        const v = JSON.parse(await $.fs.read(path))
        await change(() => asQuest(v, current.root))
      } catch {
        await $.ui.toast(`Could not read ${path}`)
      }
    }
    const modSection = section(els, 'mod', 'Mod', 'The quest belongs to this mod: its files, PLAN.md and texts.',
      mods.length > 1
        ? <Select key="mod" label="Mod" options={mods.map(m => ({ value: m.root, label: m.isHere ? `${m.name} (this folder)` : m.name }))}
          value={current.root} onSelect={v => pickMod(v)} />
        : <Text>{current.name}</Text>,
      designs.length
        ? (
          <Box flexDirection="row" flexWrap="wrap" gap={1} key="designs">
            <Text dimColor>Saved:</Text>
            {designs.slice(0, 8).map(s => (
              <Button key={`load:${s.name}`} dimColor={s.name !== q.sid} onPress={() => load(s.path)}>{s.name}</Button>
            ))}
          </Box>
        )
        : <Text dimColor>{`No saved quests yet (they go to ${QUESTS_DIR}/ in the mod).`}</Text>)

    // ── Basics
    const basics = section(els, 'basics', 'Quest', undefined,
      field('title', 'Title', 'The Lost Courier'),
      <Input key="f:sid" label="SID" placeholder={questSid(q.title, prefix)} value={q.sid}
        onInput={v => set({ sid: v.replace(/[^A-Za-z0-9_]/g, '') })} onSubmit={v => set({ sid: v.replace(/[^A-Za-z0-9_]/g, '') })} />,
      pick('kind', 'Kind', KINDS),
      field('summary', 'Summary', 'A courier carrying a PDA for Sidorovich went missing near the Garbage.', 3),
      field('journal', 'Journal', 'What the PDA journal says when the quest starts.', 2))

    const start = section(els, 'start', 'Start and place', undefined,
      pick('start', 'Starts when', STARTS),
      field('startDetail', 'Detail', 'Which NPC, area, item or quest exactly'),
      pick('region', 'Region', REGIONS),
      field('place', 'Place', 'The tunnels under the old garage'))

    // ── Characters: pickers for the next one, its name's Enter adds it
    const pc = q.pending.character
    const setPc = (patch: Partial<QuestCharacter>) =>
      change(cur => ({ ...cur, pending: { ...cur.pending, character: { ...cur.pending.character, ...patch } } }))
    const addCharacter = (name: string) => {
      if (!clean(name)) return
      return change(cur => ({
        ...cur,
        characters: [...cur.characters, { ...cur.pending.character, name: clean(name) }],
        pending: { ...cur.pending, character: { ...cur.pending.character, name: '', sid: '', notes: '', count: '1' } },
      }))
    }
    const characters = section(els, 'characters', 'Characters', 'Set the pickers, then type the name and press Enter.',
      ...q.characters.map((c, i) => (
        <Box flexDirection="row" gap={1} key={`c:${i}`}>
          <Text color={ORANGE}>•</Text>
          <Text wrap="wrap">{characterLine(c)}</Text>
          {rowButtons(`c:${i}`, () => set({ characters: move(q.characters, i, -1) }),
            () => set({ characters: move(q.characters, i, 1) }),
            () => set({ characters: q.characters.filter((_, k) => k !== i) }))}
        </Box>
      )),
      <Select key="pc:role" label="Role" options={ROLES} value={pc.role} onSelect={v => setPc({ role: v })} />,
      <Select key="pc:faction" label="Faction" options={FACTIONS} value={pc.faction} onSelect={v => setPc({ faction: v })} />,
      <Select key="pc:behavior" label="Behavior" options={BEHAVIORS} value={pc.behavior} onSelect={v => setPc({ behavior: v })} />,
      <Input key="pc:count" label="How many" placeholder="1" value={pc.count}
        onInput={v => setPc({ count: v.replace(/[^0-9]/g, '') })} onSubmit={v => setPc({ count: v.replace(/[^0-9]/g, '') })} />,
      <Input key="pc:sid" label="Vanilla SID" placeholder="Empty for a new character" value={pc.sid}
        onInput={v => setPc({ sid: v.trim() })} onSubmit={v => setPc({ sid: v.trim() })} />,
      <Input key="pc:notes" label="Notes" placeholder="Wounded, hides in the basement" value={pc.notes}
        onInput={v => setPc({ notes: v })} onSubmit={v => setPc({ notes: v })} />,
      <Input key={`pc:name:${q.characters.length}`} label="Name" placeholder="Add a character and press Enter"
        submitLabel="add" onSubmit={addCharacter} />)

    // ── Stages: the same way
    const ps = q.pending.stage
    const setPs = (patch: Partial<QuestStage>) =>
      change(cur => ({ ...cur, pending: { ...cur.pending, stage: { ...cur.pending.stage, ...patch } } }))
    const addStage = (text: string) => {
      if (!clean(text)) return
      return change(cur => ({ ...cur, stages: [...cur.stages, { ...cur.pending.stage, text: clean(text) }] }))
    }
    const stages = section(els, 'stages', 'Stages', 'Each objective in order (a Set Journal stage each). Pick its kind and marker, then type it.',
      ...q.stages.map((s, i) => (
        <Box flexDirection="row" gap={1} key={`s:${i}`}>
          <Text wrap="wrap">{stageLine(s, i)}</Text>
          <Button key={`s:${i}:opt`} dimColor onPress={() => set({ stages: q.stages.map((x, k) => (k === i ? { ...x, optional: !x.optional } : x)) })}>
            {s.optional ? 'Required' : 'Optional'}
          </Button>
          {rowButtons(`s:${i}`, () => set({ stages: move(q.stages, i, -1) }), () => set({ stages: move(q.stages, i, 1) }),
            () => set({ stages: q.stages.filter((_, k) => k !== i) }))}
        </Box>
      )),
      <Select key="ps:kind" label="Kind" options={STAGE_KINDS} value={ps.kind} onSelect={v => setPs({ kind: v })} />,
      <Select key="ps:marker" label="Marker" options={MARKERS} value={ps.marker} onSelect={v => setPs({ marker: v })} />,
      <Select key="ps:optional" label="Stage is" options={[{ value: 'no', label: 'Required' }, { value: 'yes', label: 'Optional' }]}
        value={ps.optional ? 'yes' : 'no'} onSelect={v => setPs({ optional: v === 'yes' })} />,
      <Input key={`ps:text:${q.stages.length}`} label="Objective" placeholder="Find the courier in the tunnels"
        submitLabel="add" onSubmit={addStage} />)

    // ── The string lists, each with its usual entries one press away
    const listSection = (field: ListField, title: string, hint: string, placeholder: string) => {
      const items = q[field]
      const add = (text: string) => {
        const item = clean(text)
        if (item) return change(cur => (cur[field].includes(item) ? cur : { ...cur, [field]: [...cur[field], item] }))
      }
      const offers = SUGGEST[field].filter(s => !items.includes(s))
      return section(els, field, title, hint,
        ...items.map((it, i) => (
          <Box flexDirection="row" gap={1} key={`${field}:${i}`}>
            <Text dimColor>-</Text>
            <Text wrap="wrap">{it}</Text>
            <Button key={`${field}:${i}:x`} dimColor onPress={() => set({ [field]: items.filter((_, k) => k !== i) } as Partial<QuestDraft>)}>Remove</Button>
          </Box>
        )),
        <Input key={`${field}:new:${items.length}`} placeholder={placeholder} submitLabel="add" onSubmit={add} />,
        offers.length
          ? (
            <Box flexDirection="row" flexWrap="wrap" gap={1} key={`${field}:offers`}>
              {offers.map(s => (
                <Button key={`${field}:offer:${SUGGEST[field].indexOf(s)}`} dimColor onPress={() => add(s)}>
                  <Text color={ORANGE}>+</Text> {s}
                </Button>
              ))}
            </Box>
          )
          : null)
    }

    const outcome = section(els, 'outcome', 'Outcome', undefined,
      field('success', 'Success', 'The courier is back, Sidorovich pays and trusts you more', 2),
      field('failure', 'Failure', 'The courier dies: the quest fails, the PDA can still be sold', 2))

    const extra = section(els, 'extra', 'Texts and notes', undefined,
      field('languages', 'Languages', 'English, Ukrainian'),
      field('notes', 'Notes for Claude', 'Anything else: references, a vanilla quest to copy from, open questions', 3))

    const gaps = questGaps(q)
    const send = async () => {
      if (gaps.length) {
        await $.ui.toast(`Add ${gaps.join(', ')} first.`)
        return
      }
      const path = await save()
      await change(cur => ({ ...cur, sentAtMs: now }))
      void $.prompt.submit({ text: questBrief({ ...q, sid: clean(q.sid) || questSid(q.title, prefix) }, current.name, path), asUser: true })
    }

    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="column" key="intro">
          <Text bold color={ORANGE}>QUEST DESIGNER</Text>
          <Text dimColor wrap="wrap">Lay out the quest; Claude turns it into a Quest Blueprint plan and walks you through the Quest Tool.</Text>
        </Box>
        {modSection}
        {basics}
        {start}
        {characters}
        {stages}
        {LIST_FIELDS.map(f => listSection(f.field, f.title, f.hint, f.placeholder))}
        {outcome}
        {extra}
        <Box flexDirection="column" key="send">
          {q.sentAtMs
            ? <Text color="success">{`Sent to Claude ${age(q.sentAtMs, now)}.`}</Text>
            : gaps.length ? <Text dimColor>{`Still needed: ${gaps.join(', ')}.`}</Text> : <Text dimColor>Ready to send.</Text>}
          {q.savedAtMs ? <Text dimColor>{`Saved ${age(q.savedAtMs, now)}.`}</Text> : null}
          <Box flexDirection="row" gap={1}>
            {action(els, 'send', q.sentAtMs ? 'Send again' : 'Send to Claude', () => send())}
            <Button key="save" onPress={() => save()}>Save</Button>
            <Button key="new" dimColor onPress={() => change(() => emptyQuest(current.root))}>New quest</Button>
          </Box>
        </Box>
      </Box>
    )
  })
}

