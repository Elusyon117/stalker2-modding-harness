// /zonecraft-newmod: a form beside the chat for a new mod's brief (its name, the main idea, the features wanted and the
// details to check). "Send to Claude" hands the brief over as a prompt; Claude creates the mod and writes the brief
// into its PLAN.md as checklists, which the zonecraft panel then shows as the mod's progress.
import { atom, read, update } from 'claude-code'
import type { EngineInterface as Engine, On } from 'claude-code'

import type { NewModDraft } from '../types'
import { age } from './data'
import { action, ORANGE, scene, section, top } from './theme'


export const NEWMOD_PANE = 'zonecraft-newmod'
const TOOL = 'mcp__zonecraft__new_mod_form'
const STORE = 'newmod-draft'

const EMPTY: NewModDraft = { name: '', idea: '', features: [], details: [], sentAtMs: 0 }
const draft = atom({ plugin: 'zonecraft', key: 'draft' } as const, EMPTY, { shape: 'draft-1' })

/** Questions most mods have to settle; each one not yet in the list is offered as a button. */
export const SUGGESTED = [
  'Keyboard and gamepad',
  'Rebound keys',
  'Works alongside other popular mods',
  'Settings in the mod menu (MCM)',
  'Survives save, load and death',
  'Where in the game it happens',
]

const clean = (s: string) => s.replace(/\s+/g, ' ').trim()

function asDraft(v: unknown): NewModDraft | undefined {
  if (!v || typeof v !== 'object') return undefined
  const o = v as Record<string, unknown>
  const list = (x: unknown) => (Array.isArray(x) ? x.filter((s): s is string => typeof s === 'string') : [])
  return {
    name: typeof o.name === 'string' ? o.name : '',
    idea: typeof o.idea === 'string' ? o.idea : '',
    features: list(o.features),
    details: list(o.details),
    sentAtMs: typeof o.sentAtMs === 'number' ? o.sentAtMs : 0,
  }
}

/** What is still missing before the brief can go to Claude; empty when it is ready. */
export function missing(d: NewModDraft): string[] {
  const out: string[] = []
  if (!clean(d.name)) out.push('a name')
  if (!clean(d.idea)) out.push('the main idea')
  if (d.features.length === 0) out.push('at least one feature')
  return out
}

/** The prompt Claude gets: the brief as given, and what to do with it. */
export function brief(d: NewModDraft): string {
  const list = (items: string[]) => items.map(s => `- ${s}`).join('\n')
  return [
    'I want to make a new Stalker 2 mod. Here is my brief from the zonecraft New mod form.',
    '',
    `Name: ${clean(d.name)}`,
    `Main idea: ${d.idea.trim()}`,
    '',
    'Features:',
    list(d.features),
    ...(d.details.length ? ['', 'Details to check:', list(d.details)] : []),
    '',
    'Set it up with zonecraft (knowledge/mod-workflow.md, New mod): agree the plugin name, short prefix and repo ' +
      'name with me first, then create the mod and write this brief into its PLAN.md (the idea under "## Idea", ' +
      'each feature and each detail as a "- [ ]" line under "## Features" and "## Details to check"). Ask me about ' +
      'anything unclear before starting on the first feature.',
  ].join('\n')
}

async function open($: Engine) {
  return $.ui.open({ id: NEWMOD_PANE, title: 'New mod' })
}

/** The form's part of the plugin's session start: bring back a draft left in another session, and register the
 * command and the tool. */
export async function newModSessionStart($: Engine) {
  const now = await read($, draft)
  if (!now.name && !now.idea && now.features.length === 0) {
    const kept = asDraft(await $.store.get(STORE).catch(() => undefined))
    if (kept) await update($, draft, () => kept)
  }
  await $.command.register({
      name: 'zonecraft-newmod',
    description: 'Plan a new Stalker 2 mod in a form: its name, main idea, the features you want and what to check',
  })
  await $.tool.register({
    name: 'new_mod_form',
    description:
      'Opens the zonecraft New mod form beside the chat, where the user writes down a new mod\'s name, main idea, ' +
      'the features they want and the details to check, then sends it to you as a brief. Call it when the user ' +
      'wants a new Stalker 2 mod but has not described it yet, or describes it loosely.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  })
}

export function registerNewMod(on: On) {
  on('command.run', { command: 'zonecraft-newmod' }, async $ => {
    const { isPlaced } = await open($)
    return { text: isPlaced ? 'New mod form opened.' : 'New mod form opened (shown where your app has room for panes).' }
  })

  on('tool.call', { tool: TOOL }, async $ => {
    const { isPlaced } = await open($)
    return {
      result: isPlaced
        ? 'The New mod form is open beside the chat. Tell the user to fill it in and press "Send to Claude"; the ' +
          'brief arrives as their next message.'
        : 'This app shows no panes right now; ask the user for the mod\'s name, main idea, features and details instead.',
    }
  }).catch(() => ({ result: 'The New mod form could not be opened; ask the user to type /zonecraft-newmod.' }))

  on('ui.render', { component: 'Pane', requestId: NEWMOD_PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const d = await read($, draft)
    const now = await $.clock.now()

    const change = async (fn: (d: NewModDraft) => NewModDraft) => {
      let saved = EMPTY
      await update($, draft, cur => (saved = fn(cur)))
      await $.store.set(STORE, saved)
    }
    const addTo = (field: 'features' | 'details') => (text: string) => {
      const item = clean(text)
      if (item) void change(cur => (cur[field].includes(item) ? cur : { ...cur, [field]: [...cur[field], item] }))
    }
    const removeFrom = (field: 'features' | 'details', i: number) => () =>
      void change(cur => ({ ...cur, [field]: cur[field].filter((_, k) => k !== i) }))

    const send = async () => {
      const gaps = missing(d)
      if (gaps.length) {
        await $.ui.toast(`Add ${gaps.join(', ')} first.`)
        return
      }
      await change(cur => ({ ...cur, sentAtMs: now }))
      // the brief is the person's own, so it goes in as their words
      void $.prompt.submit({ text: brief(d), asUser: true })
    }

    const list = (field: 'features' | 'details') => d[field].map((item, i) => (
      <Box flexDirection="row" gap={1} key={`${field}:${i}`}>
        <Text dimColor>{field === 'features' ? `${i + 1}.` : '-'}</Text>
        <Text>{item}</Text>
        {e.surface === 'mobile' ? null : <Button key={`remove-${field}:${i}`} dimColor onPress={removeFrom(field, i)}>Remove</Button>}
      </Box>
    ))

    const els = { Box, Text, Button }
    const isTerminal = e.surface === 'terminal'

    const intro = (
      <Box flexDirection="column" key="intro">
        <Text bold color={ORANGE}>NEW MOD BRIEF</Text>
        <Text dimColor wrap="wrap">Write down what you know. Claude asks about the rest, creates the mod and keeps</Text>
        <Text dimColor wrap="wrap">this plan in its PLAN.md, where the zonecraft panel ticks off finished features.</Text>
      </Box>
    )
    // Clawd plots the route on his PDA while the brief is written, and heads out once it is sent.
    const art = d.sentAtMs
      ? scene($, e, 'exploring', 'Clawd heading out into the Zone with his pack: the brief is with Claude')
      : scene($, e, 'planning', 'Clawd sitting with his PDA out plotting a route, his backpack beside him')

    // The phone app draws no text fields yet: show the draft, fill it in on the PC.
    if (e.surface !== 'terminal' && e.surface !== 'desktop' && e.surface !== 'vscode') {
      return (
        <Box flexDirection="column" gap={1}>
          {top(els, false, art, intro)}
          {section(els, 'draft', d.name || 'Nothing written yet', d.idea || undefined, ...list('features'))}
          <Text dimColor>Fill in the form on your PC (type /zonecraft-newmod there).</Text>
        </Box>
      )
    }
    const { Input } = $.ui.resolve({ ...e, surface: e.surface })
    const gaps = missing(d)
    const suggestions = SUGGESTED.filter(s => !d.details.includes(s))

    // One blank line between sections, none inside one.
    return (
      <Box flexDirection="column" gap={1}>
        {top(els, isTerminal, art, intro)}
        {section(els, 'name', 'Name', 'What players will see on Nexus.',
          <Input key="name" placeholder="Immersive Campfires" value={d.name} autoFocus
            onInput={v => void change(cur => ({ ...cur, name: v }))}
            onSubmit={v => void change(cur => ({ ...cur, name: v }))} />)}
        {section(els, 'idea', 'Main idea', 'One or two sentences: what changes for the player.',
          <Input key="idea" rows={3} value={d.idea}
            placeholder="Sit down at any campfire: the camera lowers, time passes faster and you heal slowly."
            onInput={v => void change(cur => ({ ...cur, idea: v }))}
            onSubmit={v => void change(cur => ({ ...cur, idea: v }))} />)}
        {section(els, 'features', 'Features', 'Each thing it should do, one at a time. They become the checklist in the panel.',
          ...list('features'),
          <Input key={`feature:${d.features.length}`} placeholder="Add a feature and press Enter" submitLabel="add"
            onSubmit={addTo('features')} />)}
        {section(els, 'details', 'Details to check', 'Questions to settle and cases to test. Pick the usual ones or add your own.',
          ...list('details'),
          <Input key={`detail:${d.details.length}`} placeholder="Add a detail and press Enter" submitLabel="add"
            onSubmit={addTo('details')} />,
          suggestions.length
            ? (
              <Box flexDirection="row" flexWrap="wrap" gap={1} key="suggestions">
                {suggestions.map(s => (
                  <Button key={`suggest:${SUGGESTED.indexOf(s)}`} dimColor onPress={() => addTo('details')(s)}>
                    <Text color={ORANGE}>+</Text> {s}
                  </Button>
                ))}
              </Box>
            )
            : null)}
        <Box flexDirection="column">
          {d.sentAtMs
            ? <Text color="success">{`Sent to Claude ${age(d.sentAtMs, now)}. Answer its questions in the chat; the plan then shows in /zonecraft-panel.`}</Text>
            : gaps.length
              ? <Text dimColor>{`Still needed: ${gaps.join(', ')}.`}</Text>
              : <Text dimColor>Ready to send.</Text>}
          <Box flexDirection="row" gap={1}>
            {action(els, 'send', d.sentAtMs ? 'Send again' : 'Send to Claude', () => void send())}
            <Button key="clear" dimColor onPress={() => void change(() => EMPTY)}>Start over</Button>
          </Box>
        </Box>
      </Box>
    )
  })
}
