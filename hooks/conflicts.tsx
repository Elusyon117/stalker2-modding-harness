// /zonecraft-conflicts: which mods fight over the same files. tools/pak/conflicts.py lists every container of the
// installed mods (~mods), of your own mods (their release candidates, else the kit's last packaging) and of any
// collection folder, then reports shared assets (last mounted wins), whole cfg files and cfg patches touching the
// same fields. The panel shows the last report, kept across sessions, with the winner of each conflict.
import { atom, read, update } from 'claude-code'
import type { EngineInterface as Engine, On } from 'claude-code'

import type { Conflict, ConflictReport } from '../types'
import { age, knownMods, readSettings, runJson } from './data'
import { action, ORANGE, RUST, section } from './theme'

export const CONFLICTS_PANE = 'zonecraft-conflicts'
const TOOL = 'mcp__zonecraft__check_conflicts'
const STORE = 'conflicts-report'
const SHOW_MAX = 40

const conflictState = atom({ plugin: 'zonecraft', key: 'conflicts' } as const,
  { report: undefined as ConflictReport | undefined, isScanning: false, collection: '', onlyYours: false },
  { shape: 'conflicts-1' })

const strings = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [])

const MARK: Record<Conflict['verdict'], { mark: string; color?: string; label: string }> = {
  risky: { mark: '✗', color: 'error', label: 'risky' },
  tie: { mark: '!', color: RUST, label: 'check' },
  wins: { mark: '!', color: ORANGE, label: 'one wins' },
  same: { mark: '·', label: 'same file' },
}

/** One conflict as a line for Claude. */
export function conflictLine(c: Conflict): string {
  return `[${c.kind}] ${c.what}: ${c.mods.map((m, i) => `${i === 0 ? 'winner ' : ''}${m.name} (${m.file}, order ${m.order})`).join(' vs ')}. ${c.note}`
}

async function scan($: Engine) {
  const cur = await read($, conflictState)
  if (cur.isScanning) return
  await update($, conflictState, s => ({ ...s, isScanning: true }))
  try {
    const settings = await readSettings($)
    const mods = await knownMods($, await $.session.cwd(), settings, strings(await $.store.get('mods-seen')))
    const args = ['scan', '--json', ...mods.flatMap(m => ['--yours', m.root])]
    if (cur.collection.trim()) args.push('--collection', cur.collection.trim())
    if (cur.onlyYours) args.push('--only-yours')
    // listing every pak with UnrealPak is slow the first time; each listing is cached as it is made, so a scan that
    // runs out of time picks up where it stopped
    const r = await runJson<ConflictReport>($, settings, 'tools/pak/conflicts.py', args, 600_000)
    if (r.value) {
      const report = r.value
      await update($, conflictState, s => ({ ...s, report, isScanning: false }))
      await $.store.set(STORE, report)
      const mine = report.conflicts.filter(c => c.isYours && c.verdict !== 'same').length
      await $.ui.toast(`Conflict check: ${report.mods.length} mods, ${report.conflicts.filter(c => c.verdict !== 'same').length} conflicts (${mine} with your mods).`)
    } else {
      await update($, conflictState, s => ({ ...s, isScanning: false }))
      await $.ui.toast(`The conflict check failed: ${r.error}`)
    }
  } catch (err) {
    await update($, conflictState, s => ({ ...s, isScanning: false }))
    await $.ui.toast(`The conflict check failed: ${err instanceof Error ? err.message : String(err)}`)
  }
}

async function open($: Engine) {
  return $.ui.open({ id: CONFLICTS_PANE, title: 'Mod conflicts' })
}

export async function conflictsSessionStart($: Engine) {
  const cur = await read($, conflictState)
  if (!cur.report) {
    const kept = await $.store.get(STORE).catch(() => undefined)
    if (kept && typeof kept === 'object') await update($, conflictState, s => ({ ...s, report: kept as ConflictReport }))
  }
  await $.command.register({
    name: 'zonecraft-conflicts',
    description: 'Check your mods, the installed mods and a mod collection for conflicts (shared assets, cfg fields)',
  })
  await $.tool.register({
    name: 'check_conflicts',
    description:
      'Opens the zonecraft Conflicts panel and starts a scan: every installed mod in ~mods, the user\'s own mods ' +
      '(release candidates or last packaging) and optionally a collection folder, listed with UnrealPak, then ' +
      'shared assets (last mounted wins), whole cfg replacements and cfg patches touching the same fields, each ' +
      'with its winner. Call it when the user asks whether mods conflict or builds a mod collection.',
    inputSchema: {
      type: 'object',
      properties: { collection: { type: 'string', description: 'A folder of paks to check together (optional)' } },
      additionalProperties: false,
    },
  })
}

export function registerConflicts(on: On) {
  on('command.run', { command: 'zonecraft-conflicts' }, async $ => {
    const { isPlaced } = await open($)
    return { text: isPlaced ? 'Conflicts panel opened. Press Scan to check.' : 'Conflicts panel opened (shown where your app has room for panes).' }
  })

  on('tool.call', { tool: TOOL }, async ($, e) => {
    const input = (e.input ?? {}) as { collection?: unknown }
    if (typeof input.collection === 'string') {
      const collection = input.collection
      await update($, conflictState, s => ({ ...s, collection }))
    }
    await open($)
    void scan($)
    return {
      result: 'The Conflicts panel is open and a scan started (the first one lists every pak and can take minutes). ' +
        'The tester sees the result there; it is also kept for the next session.',
    }
  }).catch(() => ({ result: 'The Conflicts panel could not be opened; ask the tester to type /zonecraft-conflicts.' }))

  on('ui.render', { component: 'Pane', requestId: CONFLICTS_PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const els = { Box, Text, Button }
    const s = await read($, conflictState)
    const now = await $.clock.now()
    const rep = s.report
    const set = (patch: Partial<typeof s>) => update($, conflictState, cur => ({ ...cur, ...patch }))
    const hasFields = e.surface === 'terminal' || e.surface === 'desktop' || e.surface === 'vscode'

    const controls = () => {
      if (!hasFields) return <Text dimColor>Scan from your PC (type /zonecraft-conflicts there).</Text>
      const { Input, Select } = $.ui.resolve({ ...e, surface: e.surface as 'terminal' | 'desktop' | 'vscode' })
      return (
        <Box flexDirection="column" key="controls">
          <Input key="collection" label="Collection folder" placeholder="Optional: a folder of paks to check with the rest"
            value={s.collection} onInput={v => set({ collection: v })} onSubmit={v => set({ collection: v })} />
          <Select key="only" label="Show" value={s.onlyYours ? 'yours' : 'all'}
            options={[{ value: 'all', label: 'Every conflict' }, { value: 'yours', label: 'Only those with my mods' }]}
            onSelect={v => set({ onlyYours: v === 'yours' })} />
          <Box flexDirection="row" gap={1}>
            {s.isScanning
              ? <Text color={ORANGE}>Scanning… (the first scan lists every pak and can take minutes)</Text>
              : action(els, 'scan', rep ? 'Scan again' : 'Scan', () => scan($))}
          </Box>
        </Box>
      )
    }

    const intro = section(els, 'intro', 'Mod conflicts',
      'Per asset the last-mounted pak wins and nothing merges; cfg patches clash only on the same field.', controls())
    if (!rep) {
      return <Box flexDirection="column" gap={1}>{intro}<Text dimColor>No scan yet.</Text></Box>
    }

    const real = rep.conflicts.filter(c => c.verdict !== 'same')
    const shown = real.filter(c => !s.onlyYours || c.isYours)
    const mods = section(els, 'mods', `Mods scanned (${rep.mods.length})`, `${age(rep.atMs, now)} · ${rep.sources.join(', ')}`,
      <Box flexDirection="row" flexWrap="wrap" gap={1} key="mod-list">
        {rep.mods.map((m, i) => (
          <Text key={`m:${i}`} color={m.isYours ? ORANGE : undefined} dimColor={!m.isYours}>
            {`${m.name}${m.isYours ? ' (yours)' : ''} · ${m.order}`}
          </Text>
        ))}
      </Box>,
      ...rep.errors.slice(0, 5).map((x, i) => <Text key={`err:${i}`} color={RUST} wrap="wrap">{x}</Text>))

    const counts = (['risky', 'tie', 'wins'] as const).map(v => `${shown.filter(c => c.verdict === v).length} ${MARK[v].label}`).join(' · ')
    const list = section(els, 'conflicts', `Conflicts (${shown.length})`, shown.length ? counts : undefined,
      shown.length === 0
        ? <Text color="success">{s.onlyYours ? 'None with your mods.' : 'No conflicts.'}</Text>
        : null,
      ...shown.slice(0, SHOW_MAX).map((c, i) => {
        const m = MARK[c.verdict]
        return (
          <Box flexDirection="column" key={`c:${i}`}>
            <Box flexDirection="row" gap={1}>
              <Text color={m.color}>{m.mark}</Text>
              <Text dimColor>{c.kind}</Text>
              <Text bold wrap="truncate">{c.what}</Text>
            </Box>
            <Box flexDirection="row" gap={1} paddingLeft={2} flexWrap="wrap">
              <Text color="success">{`wins: ${c.mods[0]?.name ?? '?'}`}</Text>
              <Text dimColor>{`over ${c.mods.slice(1).map(x => x.name).join(', ')}`}</Text>
              {c.isYours ? <Text color={ORANGE}>yours</Text> : null}
              <Button key={`ask:${i}`} dimColor onPress={() => void $.prompt.submit({
                text: `zonecraft's conflict check found this conflict:\n${conflictLine(c)}\nWhat does it break in game, and how do we resolve it (load order, a patch file instead, merging, or making one mod optional)?`,
                asUser: true,
              })}>Ask Claude</Button>
            </Box>
            <Text dimColor wrap="wrap">{`  ${c.note}`}</Text>
          </Box>
        )
      }),
      shown.length > SHOW_MAX ? <Text dimColor>{`and ${shown.length - SHOW_MAX} more`}</Text> : null,
      shown.length
        ? (
          <Box flexDirection="row" gap={1} key="all">
            {action(els, 'ask-all', 'Ask Claude about all of them', () => void $.prompt.submit({
              text: 'zonecraft\'s conflict check of my mods' + (s.collection ? ` and the collection in ${s.collection}` : '') +
                ' found these conflicts:\n' + shown.slice(0, 25).map(c => `- ${conflictLine(c)}`).join('\n') +
                '\nWhich ones matter in game, and what load order or fixes make the set work together?',
              asUser: true,
            }))}
          </Box>
        )
        : null)

    const same = rep.conflicts.length - real.length
    return (
      <Box flexDirection="column" gap={1}>
        {intro}
        {mods}
        {list}
        {same ? <Text dimColor>{`${same} more files are shipped identically by several mods (harmless).`}</Text> : null}
      </Box>
    )
  })
}
