import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { ConflictReport, Dashboard, ModChoice, Paste, Status, WatchState } from '../types'
import type { SceneName } from './art'
import { age, chooseMod, dashboard, findModRoot, knownMods, readSettings } from './data'
import { conflictsSessionStart, registerConflicts } from './conflicts'
import { dataSessionStart, registerData } from './databrowser'
import { newModSessionStart, registerNewMod } from './newmod'
import { hideNodes, NODES_NONE, nodesBody, registerNodes, showNodes } from './pasteview'
import { questSessionStart, registerQuest } from './questform'
import { action, ORANGE, RUST, scene, section, top } from './theme'
import { registerWatch, WATCH_EMPTY, watchSessionStart } from './watch'

const PANE = 'zonecraft'
const TITLE = 'zonecraft'
const TOOL = 'mcp__zonecraft__open_panel'

const tick = atom({ plugin: 'zonecraft', key: 'tick' } as const, 0, { shape: 'tick-1' })
const copied = atom({ plugin: 'zonecraft', key: 'copied' } as const, { path: '', atMs: 0 }, { shape: 'copied-1' })
const tracked = atom({ plugin: 'zonecraft', key: 'tracked' } as const, '', { shape: 'tracked-1' })
// Read here too, for the All mods page: what the watcher saw (watch.tsx) and the last conflict check (conflicts.tsx).
const watch = atom({ plugin: 'zonecraft', key: 'watch' } as const, WATCH_EMPTY, { shape: 'watch-1' })
const conflictState = atom({ plugin: 'zonecraft', key: 'conflicts' } as const,
  { report: undefined as ConflictReport | undefined, isScanning: false, collection: '', onlyYours: false },
  { shape: 'conflicts-1' })
// The paste shown as nodes (pasteview.tsx keeps it).
const nodesShown = atom({ plugin: 'zonecraft', key: 'nodes' } as const, NODES_NONE, { shape: 'nodes-1' })
const view = atom({ plugin: 'zonecraft', key: 'view' } as const, 'auto' as 'auto' | 'mods' | 'mod', { shape: 'view-1' })

// Kept across sessions in $.store: the mod folders sessions were opened in, and the mod last picked in the panel.
const SEEN = 'mods-seen'
const LAST = 'mod-picked'
const SEEN_MAX = 30

const strings = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [])

// Clawd at the top right does what the mod is doing: out exploring with no mod open, at the campfire while work goes
// on, playing the guitar once every feature in the plan is done.
const MOOD: Record<'none' | 'working' | 'done', { scene: SceneName; alt: string }> = {
  none: { scene: 'exploring', alt: 'Clawd walking through the Zone with his pack, looking for a mod to work on' },
  working: { scene: 'campfire', alt: 'Clawd sitting by a campfire, roasting a sausage on a stick' },
  done: { scene: 'guitar', alt: 'Clawd playing the guitar: every feature in the plan is done' },
}

// Tools whose run can change what the panel shows (files written, a cook, an install).
const CHANGERS = new Set(['Bash', 'PowerShell', 'Write', 'Edit', 'NotebookEdit'])

const MARK: Record<Status, string> = { ok: '✓', warn: '!', bad: '✗', none: '·' }
const COLOR: Record<Status, string | undefined> = { ok: 'success', warn: RUST, bad: 'error', none: undefined }

/** The dashboard's page when nobody picked one: the mod this session is in, or the only mod; else every mod. */
export function autoView(mods: readonly ModChoice[]): 'mods' | 'mod' {
  return mods.length <= 1 || mods.some(m => m.isHere) ? 'mod' : 'mods'
}

type Part = { text: string; status: Status | 'busy' }

/** One mod's status line on the All mods page: the build (or the packaging running now), the test copy, the plan,
 * and conflicts with it from the last conflict check. */
export function statusParts(d: Dashboard, w: WatchState | undefined, report: ConflictReport | undefined,
  now: number): Part[] {
  const out: Part[] = []
  const name = (d.modName ?? '').toLowerCase()
  const pkg = w?.package
  const mine = !!name && (pkg?.mod ?? '').toLowerCase() === name
  if (mine && pkg?.active) {
    const pct = pkg.progress && pkg.progress[1] ? ` ${Math.round((100 * pkg.progress[0]) / pkg.progress[1])}%` : ''
    out.push({ text: `packaging ${pkg.phase ?? ''}${pct}`.trim(), status: 'busy' })
  } else if (mine && pkg?.result === 'failed' && (pkg.endedMs ?? 0) > (d.cookMs ?? 0)) {
    out.push({ text: 'packaging failed', status: 'bad' })
  } else {
    out.push(d.cookMs !== undefined ? { text: `built ${age(d.cookMs, now)}`, status: 'none' }
      : { text: d.kit ? 'not built yet' : 'build unknown', status: 'none' })
  }
  if (d.testPakMs === undefined) out.push({ text: 'no test copy', status: 'none' })
  else if (d.cookMs !== undefined && d.testPakMs < d.cookMs) out.push({ text: 'old test copy', status: 'warn' })
  else out.push({ text: 'test copy ✓', status: 'ok' })
  if (d.features.length) {
    const done = d.features.filter(f => f.isDone).length
    out.push({ text: `${done}/${d.features.length} features`, status: done === d.features.length ? 'ok' : 'none' })
  }
  const clashes = (report?.conflicts ?? []).filter(c => c.verdict !== 'same' && c.mods.some(m => m.name.toLowerCase() === name))
  if (name && clashes.length) out.push({ text: `${clashes.length} conflict${clashes.length === 1 ? '' : 's'}`, status: 'warn' })
  return out
}

export const register: Register = on => {
  registerNewMod(on)
  registerWatch(on)
  registerQuest(on)
  registerConflicts(on)
  registerData(on)
  registerNodes(on)

  on('session.start', async ($, e, next) => {
    // Bash children (a mod's gen_*.py through zonekit/tools/zonecraft_path.py) find zonecraft through this.
    await $.env.set('ZONECRAFT_ROOT', $.plugin.root)
    // Remember the mod this session is in, so the panel can offer it from other sessions too.
    const here = await findModRoot($, await $.session.cwd()).catch(() => undefined)
    if (here) {
      const seen = strings(await $.store.get(SEEN)).filter(r => r.toLowerCase() !== here.toLowerCase())
      await $.store.set(SEEN, [here, ...seen].slice(0, SEEN_MAX))
    }
    await newModSessionStart($)
    await watchSessionStart($)
    await questSessionStart($)
    await conflictsSessionStart($)
    await dataSessionStart($)
    await $.command.register({
      name: 'zonecraft-panel',
      description: 'Show the zonecraft panel: the current mod, its last cook and test copy, and Blueprint pastes to copy',
    })
    await $.tool.register({
      name: 'open_panel',
      description:
        'Opens the zonecraft panel beside the chat: the current Stalker 2 mod (last cook, test copy installed, ' +
        'checkpoints) and the Blueprint paste files in <mod>/zonekit/paste with a Copy button each and their ' +
        'verify_paste results. Call it after writing a paste file so the tester can copy it with one click.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    })
    return next(e)
  })

  on('command.run', { command: 'zonecraft-panel' }, async $ => {
    await update($, tick, n => n + 1)
    const { isPlaced } = await $.ui.open({ id: PANE, title: TITLE })
    return { text: isPlaced ? 'zonecraft panel opened.' : 'zonecraft panel opened (shown where your app has room for panes).' }
  })

  on('tool.call', { tool: TOOL }, async $ => {
    await update($, tick, n => n + 1)
    const { isPlaced } = await $.ui.open({ id: PANE, title: TITLE })
    return {
      result: isPlaced
        ? 'The zonecraft panel is open beside the chat. Tell the tester to press Copy on the paste they need.'
        : 'The panel was opened but this app shows no panes right now; give the tester the paste another way.',
    }
  }).catch(() => ({ result: 'The zonecraft panel could not be opened; ask the tester to type /zonecraft-panel.' }))

  // Redraw after a tool that may have changed what the panel shows. Never in the tool's way: the redraw runs on
  // its own and any failure of it is dropped.
  on('tool.call', async ($, e, next) => {
    const ran = await next(e)
    if (CHANGERS.has(e.tool)) void update($, tick, n => n + 1).catch(() => undefined)
    return ran
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    await read($, tick) // redraws after file-changing tool calls and on Refresh
    const last = await read($, copied)
    const now = await $.clock.now()
    const settings = await readSettings($)
    const mods = await knownMods($, await $.session.cwd(), settings, strings(await $.store.get(SEEN)))
    const picked = await read($, tracked)
    const lastPicked = await $.store.get(LAST)
    const current = chooseMod(mods, picked, typeof lastPicked === 'string' ? lastPicked : '')
    const els = { Box, Text, Button }
    const page = await read($, view)
    const shown = page === 'auto' ? autoView(mods) : page

    // Picking a mod on the All mods page opens its own page, and is remembered for the next session.
    const pick = async (root: string) => {
      await update($, tracked, () => root)
      await $.store.set(LAST, root)
      await update($, view, () => 'mod')
    }

    if (shown === 'mods' && mods.length > 1) {
      const w = await read($, watch)
      const report = (await read($, conflictState)).report
      const boards = await Promise.all(mods.map(m => dashboard($, m.root, settings)))
      const crash = w.crashes[0] && now - w.crashes[0].atMs < 30 * 60_000 ? w.crashes[0] : undefined
      const partColor = (s: Part['status']) => (s === 'busy' ? ORANGE : COLOR[s])
      const modRow = (m: ModChoice, b: Dashboard, i: number) => {
        const parts = statusParts(b, w, report, now)
        const lead = parts.some(p => p.status === 'bad') ? 'bad' : parts.some(p => p.status === 'busy') ? 'busy'
          : parts.some(p => p.status === 'warn') ? 'warn' : 'ok'
        return (
          <Box flexDirection="column" key={`mod:${i}`}>
            <Box flexDirection="row" gap={1}>
              <Text color={partColor(lead === 'ok' ? 'ok' : lead)}>{lead === 'busy' ? '●' : MARK[lead]}</Text>
              <Button key={`open:${i}`} onPress={() => pick(m.root)}><Text bold>{m.name}</Text></Button>
              {m.isHere ? <Text dimColor>this folder</Text> : null}
              {m.root.toLowerCase() === current?.root.toLowerCase() && !m.isHere ? <Text dimColor>last opened</Text> : null}
            </Box>
            <Box flexDirection="row" flexWrap="wrap" paddingLeft={2}>
              {parts.map((p, k) => (
                <Text key={`part:${i}:${k}`} color={partColor(p.status)} dimColor={p.status === 'none'}>
                  {`${k ? ' · ' : ''}${p.text}`}
                </Text>
              ))}
            </Box>
            {b.state ? <Box paddingLeft={2}><Text dimColor wrap="truncate">{b.state}</Text></Box> : null}
          </Box>
        )
      }
      return (
        <Box flexDirection="column" gap={1}>
          {top(els, e.surface === 'terminal', scene($, e, MOOD.none.scene, MOOD.none.alt),
            section(els, 'mods', `Your mods (${mods.length})`, 'Pick one to open its page.',
              crash
                ? <Text color="error" wrap="wrap">{`✗ The game crashed ${age(crash.atMs, now)}: ${crash.family}. See /zonecraft-logs.`}</Text>
                : null))}
          {mods.map((m, i) => modRow(m, boards[i], i))}
          <Box flexDirection="row" gap={1}>
            <Button key="newmod" onPress={() => $.ui.open({ id: 'zonecraft-newmod', title: 'New mod' })}>New mod</Button>
            <Button key="refresh" dimColor onPress={() => void update($, tick, n => n + 1)}>Refresh</Button>
          </Box>
        </Box>
      )
    }

    const d: Dashboard = await dashboard($, current?.root, settings)

    // Back to the All mods page, where there is more than one mod.
    const picker = () => {
      if (mods.length < 2 || !current) return null
      return (
        <Box flexDirection="row" key="back">
          <Button key="all-mods" dimColor onPress={() => update($, view, () => 'mods')}>{`‹ All mods (${mods.length})`}</Button>
        </Box>
      )
    }
    const mood = MOOD[!d.modRoot ? 'none' : d.features.length && d.features.every(f => f.isDone) ? 'done' : 'working']

    const row = (label: string, value: string, status: Status = 'none') => (
      <Box flexDirection="row" gap={1}>
        <Text color={COLOR[status]}>{MARK[status]}</Text>
        <Text dimColor>{label}</Text>
        <Text>{value}</Text>
      </Box>
    )

    const modBody = () => {
      if (!d.modRoot) {
        return (
          <Box flexDirection="column">
            <Text dimColor>No mod in this folder. Open Claude Code in a mod folder (one with mod.json), or plan</Text>
            <Text dimColor>a new one with /zonecraft-newmod.</Text>
          </Box>
        )
      }
      const cookOk = d.cookMs !== undefined
      const pakFresh = d.testPakMs !== undefined && (d.cookMs === undefined || d.testPakMs >= d.cookMs)
      return (
        <Box flexDirection="column">
          <Text bold>{d.modName ?? '(mod.json has no name)'}{d.short ? <Text dimColor> · {d.short}</Text> : ''}</Text>
          {d.idea ? <Text wrap="wrap">{d.idea}</Text> : null}
          {d.state ? <Text dimColor wrap="wrap">{d.state}</Text> : null}
          {d.isLegacy ? row('Layout', 'made with the original harness; ask Claude to adopt it', 'warn') : null}
          {row('Zone Kit', d.kit ? 'set up' : 'not set up on this PC', d.kit ? 'ok' : 'warn')}
          {row('Last cook', cookOk ? age(d.cookMs, now) : d.kit ? 'none yet' : 'unknown', cookOk ? 'ok' : 'none')}
          {row('Test copy', d.testPakMs === undefined
            ? (d.game ? 'not installed' : 'unknown (game not set up)')
            : `installed ${age(d.testPakMs, now)}${pakFresh ? '' : ' (older than the last cook)'}`,
          d.testPakMs === undefined ? 'none' : pakFresh ? 'ok' : 'warn')}
          {row('Checkpoints', d.checkpoints ? `${d.checkpoints} (last: ${d.lastCheckpoint})` : 'none yet')}
        </Box>
      )
    }

    // PLAN.md's checklists: every feature with its tick, and the details still open.
    const planSection = () => {
      if (!d.modRoot) return null
      if (d.features.length === 0) {
        return section(els, 'plan', 'Plan', undefined,
          <Text dimColor>No feature list yet. Ask Claude to add one to PLAN.md ("## Features" with "- [ ]" lines).</Text>)
      }
      const done = d.features.filter(f => f.isDone).length
      const open = d.details.filter(x => !x.isDone)
      return section(els, 'plan', 'Plan', undefined,
        row('Features', `${done} of ${d.features.length} done`, done === d.features.length ? 'ok' : 'none'),
        ...d.features.map((f, i) => (
          <Box flexDirection="row" gap={1} paddingLeft={2} key={`feature:${i}`}>
            <Text color={f.isDone ? 'success' : ORANGE}>{f.isDone ? '✓' : '○'}</Text>
            <Text dimColor={f.isDone}>{f.text}</Text>
          </Box>
        )),
        d.details.length
          ? row('To check', open.length ? `${open.length} open` : 'all settled', open.length ? 'none' : 'ok')
          : null,
        ...open.slice(0, 5).map((x, i) => (
          <Box flexDirection="row" gap={1} paddingLeft={2} key={`detail:${i}`}>
            <Text dimColor>-</Text>
            <Text dimColor>{x.text}</Text>
          </Box>
        )),
        open.length > 5 ? <Text dimColor>{`  and ${open.length - 5} more in PLAN.md`}</Text> : null)
    }

    // The paste shown as nodes, drawn ahead (the rows below are built synchronously).
    const shownNodes = await read($, nodesShown)
    const nodesPaste = d.pastes.find(p => p.path === shownNodes.path)
    const nodesView = nodesPaste ? await nodesBody($, e, els, shownNodes, false) : null

    const pasteRow = (p: Paste) => {
      const isCopied = last.path === p.path && now - last.atMs < 60_000
      const copy = async (press: { surface?: string }) => {
        const text = await $.fs.read(p.path)
        const done = await $.ui.copy({ text, surface: press.surface as never })
        if (done.isCopied) await update($, copied, () => ({ path: p.path, atMs: Date.now() }))
        else await $.ui.toast(`Could not copy ${p.name}: ${done.reason ?? 'no clipboard'}`)
      }
      return (
        <Box flexDirection="column" key={`paste:${p.name}`}>
          <Box flexDirection="row" gap={1}>
            {action(els, `copy:${p.name}`, isCopied ? 'Copied' : 'Copy', copy)}
            <Text bold>{p.name}</Text>
            <Text dimColor>{p.nodes} nodes · {age(p.mtimeMs, now)}</Text>
            {p === nodesPaste
              ? <Button key={`hide:${p.name}`} dimColor onPress={() => void hideNodes($)}>Hide nodes</Button>
              : <Button key={`nodes:${p.name}`} dimColor onPress={() => void showNodes($, p.path, p.view === 'fresh')}>Show nodes</Button>}
          </Box>
          <Box flexDirection="row" gap={1} paddingLeft={2}>
            <Text color={COLOR[p.lint]}>{MARK[p.lint]}</Text>
            <Text dimColor>{p.lint === 'none' ? 'not checked' : `check: ${p.lintText}`}</Text>
          </Box>
          {p.compare !== 'none'
            ? (
              <Box flexDirection="row" gap={1} paddingLeft={2}>
                <Text color={COLOR[p.compare]}>{MARK[p.compare]}</Text>
                <Text dimColor>{`in the editor: ${p.compareText}`}</Text>
              </Box>
            )
            : null}
          {p === nodesPaste && p.view !== 'fresh'
            ? (
              <Box flexDirection="row" gap={1} paddingLeft={2}>
                <Text color={RUST}>!</Text>
                <Text dimColor>the paste changed since this picture</Text>
                <Button key={`redraw:${p.name}`} dimColor onPress={() => void showNodes($, p.path, false)}>Redraw</Button>
              </Box>
            )
            : null}
          {p === nodesPaste ? <Box paddingLeft={2} paddingTop={1}>{nodesView}</Box> : null}
        </Box>
      )
    }

    const pastes = section(els, 'pastes', 'Blueprint pastes', undefined,
      d.pastes.length === 0
        ? <Text dimColor>None yet. Paste text Claude writes to zonekit/paste/ shows up here with a Copy button.</Text>
        : null,
      ...d.pastes.map(pasteRow),
      d.pastes.length > 0
        ? <Text dimColor>Copy, click into the Blueprint graph in the Zone Kit, press Ctrl+V, then Compile and Save.</Text>
        : null)

    // One blank line between sections, none inside one.
    return (
      <Box flexDirection="column" gap={1}>
        {top(els, e.surface === 'terminal', scene($, e, mood.scene, mood.alt),
          section(els, 'mod', 'Mod', undefined, picker(), modBody()))}
        {planSection()}
        {pastes}
        <Box flexDirection="row">
          <Button key="refresh" dimColor onPress={() => void update($, tick, n => n + 1)}>Refresh</Button>
        </Box>
      </Box>
    )
  })
}
