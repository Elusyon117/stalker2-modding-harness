// The Build & test band and the Logs panel. Every few seconds tools/watch/zcwatch.py reports what changed: a packaging
// in progress (the editor's Package Mod, cook_and_install.ps1, a Workshop upload), the release candidate copy, new
// lines of the game's and the kit's logs worth seeing, and new crash reports. The band above the prompt shows a
// packaging while it runs and for a while after, with what to test in game; /zonecraft-logs shows the rest.
import { atom, read, update } from 'claude-code'
import type { EngineInterface as Engine, On } from 'claude-code'

import type { CrashInfo, LogEvent, PackageInfo, RcInfo, WatchState } from '../types'
import { activeModRoot, age, clock, dashboard, readSettings, runJson } from './data'
import { action, ORANGE, RUST, scene, section, top } from './theme'

export const LOGS_PANE = 'zonecraft-logs'
const TOOL = 'mcp__zonecraft__open_logs'
const POLL_MS = 4000
const SHOW_FOR_MS = 20 * 60_000
const EVENTS_MAX = 200

export const WATCH_EMPTY: WatchState = {
  package: {}, isGameRunning: false, isEditorRunning: false, events: [], crashes: [], lastPollMs: 0, dismissedMs: 0,
  isTestOpen: false,
}
export const watch = atom({ plugin: 'zonecraft', key: 'watch' } as const, WATCH_EMPTY, { shape: 'watch-1' })

type Poll = {
  atMs: number
  package: PackageInfo
  rc: RcInfo | null
  game: { running: boolean }
  editor: { running: boolean }
  events: Omit<LogEvent, 'atMs'>[]
  crash: CrashInfo | null
}

/** Folds one poll into the state; returns what deserves a toast. */
export function fold(cur: WatchState, p: Poll): { next: WatchState; toasts: string[] } {
  const toasts: string[] = []
  const was = cur.package
  const pkg = p.package ?? {}
  if (was.active && !pkg.active && pkg.endedMs) {
    toasts.push(pkg.result === 'ok'
      ? `Packaging done${pkg.mod ? ` (${pkg.mod})` : ''}${pkg.startedMs ? ` in ${clock(pkg.endedMs - pkg.startedMs)}` : ''}.`
      : `Packaging failed${pkg.errors?.length ? `: ${pkg.errors[pkg.errors.length - 1]}` : ''}`)
  }
  if (p.rc?.isNew) toasts.push(`Release candidate updated: ${(p.rc.files ?? []).join(', ')}`)
  if (p.crash) toasts.push(`The game crashed: ${p.crash.family}. Open /zonecraft-logs for what to do.`)
  const events = [...cur.events, ...p.events.map(e => ({ ...e, atMs: p.atMs }))].slice(-EVENTS_MAX)
  return {
    next: {
      ...cur,
      package: pkg,
      rc: p.rc ?? cur.rc,
      isGameRunning: p.game?.running ?? false,
      isEditorRunning: p.editor?.running ?? false,
      events,
      crashes: p.crash ? [p.crash, ...cur.crashes].slice(0, 10) : cur.crashes,
      lastPollMs: p.atMs,
      error: undefined,
    },
    toasts,
  }
}

/** Whether the band has something to show at `now`. */
export function bandVisible(w: WatchState, now: number): boolean {
  if (w.package.active) return true
  const recent = (t?: number) => t !== undefined && t > w.dismissedMs && now - t < SHOW_FOR_MS
  return recent(w.package.endedMs) || recent(w.crashes[0]?.atMs)
}

let busy = false

async function pollOnce($: Engine) {
  if (busy) return
  busy = true
  try {
    const settings = await readSettings($)
    if (!settings.kit && !settings.game) return // not set up: nothing to watch
    const root = await activeModRoot($)
    const r = await runJson<Poll>($, settings, 'tools/watch/zcwatch.py', ['poll', ...(root ? ['--mod-root', root] : [])])
    if (!r.value) {
      await update($, watch, cur => ({ ...cur, error: r.error, lastPollMs: Date.now() }))
      return
    }
    let toasts: string[] = []
    const poll = r.value
    await update($, watch, cur => {
      const f = fold(cur, poll)
      toasts = f.toasts
      return f.next
    })
    for (const t of toasts) await $.ui.toast(t)
  } finally {
    busy = false
  }
}

const crashPrompt = (c: CrashInfo) => [
  `The game crashed (${new Date(c.atMs).toLocaleString()}). zonecraft's crash watcher found:`,
  `- report: ${c.path}`,
  `- message: ${c.message || '(none)'}`,
  ...(c.stack.length ? [`- stack: ${c.stack.slice(0, 6).join(' | ')}`] : []),
  `- family: ${c.family}`,
  '',
  'Read the report and the game log (knowledge/diagnostics.md), tell me in game terms what happened and what we do next.',
].join('\n')

export async function watchSessionStart($: Engine) {
  await $.command.register({
    name: 'zonecraft-logs',
    description: 'Show the zonecraft Logs panel: packaging, crashes with what they mean, cfg patch and game data warnings',
  })
  await $.tool.register({
    name: 'open_logs',
    description:
      'Opens the zonecraft Logs panel beside the chat: the last packaging and its errors, crash reports with their ' +
      'known family and advice, and new warnings from the game and Zone Kit logs (cfg patches, broken game data, ' +
      'texts, mounts). Call it after a test run so the tester sees what the logs said.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  })
  $.clock.every(POLL_MS, () => void pollOnce($).catch(() => undefined))
}

export function registerWatch(on: On) {
  on('command.run', { command: 'zonecraft-logs' }, async $ => {
    void pollOnce($).catch(() => undefined)
    const { isPlaced } = await $.ui.open({ id: LOGS_PANE, title: 'zonecraft logs' })
    return { text: isPlaced ? 'Logs panel opened.' : 'Logs panel opened (shown where your app has room for panes).' }
  })

  on('tool.call', { tool: TOOL }, async $ => {
    void pollOnce($).catch(() => undefined)
    const { isPlaced } = await $.ui.open({ id: LOGS_PANE, title: 'zonecraft logs' })
    return { result: isPlaced ? 'The Logs panel is open beside the chat.' : 'This app shows no panes right now.' }
  }).catch(() => ({ result: 'The Logs panel could not be opened; ask the tester to type /zonecraft-logs.' }))

  // The band above the prompt: packaging progress, then what to do with the build; a crash if one just happened.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const w = await read($, watch)
    const now = await $.clock.now()
    if (e.props.hasSurvey || !bandVisible(w, now)) return next(e)
    const { Box, Text, Button } = $.ui.resolve(e)
    const els = { Box, Text, Button }
    const p = w.package
    const hide = () => void update($, watch, cur => ({ ...cur, dismissedMs: Date.now(), isTestOpen: false }))
    const crash = w.crashes[0] && w.crashes[0].atMs > w.dismissedMs && now - w.crashes[0].atMs < SHOW_FOR_MS
      ? w.crashes[0] : undefined

    const rows: JSX.Element[] = []
    if (crash) {
      rows.push(
        <Box flexDirection="row" gap={1} key="crash">
          <Text color="error">✗</Text>
          <Text bold>Game crashed</Text>
          <Text dimColor>{`${age(crash.atMs, now)} · ${crash.family}`}</Text>
          {action(els, 'crash-ask', 'Ask Claude', () => void $.prompt.submit({ text: crashPrompt(crash), asUser: true }))}
          <Button key="crash-logs" dimColor onPress={() => void $.ui.open({ id: LOGS_PANE, title: 'zonecraft logs' })}>Logs</Button>
        </Box>)
    }
    if (p.active) {
      const pct = p.progress && p.progress[1] ? ` · ${Math.round((100 * p.progress[0]) / p.progress[1])}%` : ''
      rows.push(
        <Box flexDirection="column" key="pkg">
          <Box flexDirection="row" gap={1}>
            <Text color={ORANGE}>●</Text>
            <Text bold>{`Packaging${p.mod ? ` ${p.mod}` : ''}`}</Text>
            <Text>{p.phase ?? 'running'}</Text>
            <Text dimColor>{`${clock(now - (p.startedMs ?? now))}${pct}${w.isGameRunning ? ' · close the game before installing' : ''}`}</Text>
          </Box>
          {p.last ? <Text dimColor wrap="truncate">{p.last}</Text> : null}
        </Box>)
    } else if (p.endedMs && p.endedMs > w.dismissedMs && now - p.endedMs < SHOW_FOR_MS) {
      const ok = p.result === 'ok'
      const took = p.startedMs ? ` in ${clock(p.endedMs - p.startedMs)}` : ''
      rows.push(
        <Box flexDirection="row" gap={1} key="done">
          <Text color={ok ? 'success' : 'error'}>{ok ? '✓' : '✗'}</Text>
          <Text bold>{ok ? `Packaged${p.mod ? ` ${p.mod}` : ''}${took}` : 'Packaging failed'}</Text>
          <Text dimColor>{ok ? age(p.endedMs, now) : (p.errors?.[p.errors.length - 1] ?? 'see the Logs panel')}</Text>
        </Box>)
      if (ok) {
        const rc = w.rc
        rows.push(
          <Box flexDirection="row" gap={1} flexWrap="wrap" key="next">
            {rc?.files?.length && !rc.pending
              ? <Text dimColor>{`Release candidate: ${rc.files.length} files ${rc.copied ? age(rc.copied * 1000, now) : ''}`}</Text>
              : action(els, 'rc', 'Copy to release candidate', () => void copyRc($))}
            <Button key="install" onPress={() => void $.prompt.submit({
              text: 'Install the build I just packaged as a test copy (install_paktest.ps1), then tell me what to test.',
              asUser: true,
            })}>Install test copy</Button>
            <Button key="test" onPress={() => void update($, watch, cur => ({ ...cur, isTestOpen: !cur.isTestOpen }))}>
              {w.isTestOpen ? 'Hide tests' : 'What to test'}
            </Button>
            <Button key="hide" dimColor onPress={hide}>Hide</Button>
          </Box>)
        if (w.isTestOpen) rows.push(await testCard($, els))
      } else {
        rows.push(
          <Box flexDirection="row" gap={1} key="failed">
            {action(els, 'fail-ask', 'Ask Claude', () => void $.prompt.submit({
              text: `My last packaging failed. The log is ${p.log ?? '(unknown)'}; the last errors were:\n` +
                (p.errors ?? []).map(x => `- ${x}`).join('\n') + '\nFind out why and fix it.',
              asUser: true,
            }))}
            <Button key="hide" dimColor onPress={hide}>Hide</Button>
          </Box>)
      }
    } else if (crash) {
      rows.push(<Box flexDirection="row" key="hide-row"><Button key="hide" dimColor onPress={hide}>Hide</Button></Box>)
    }
    return <Box flexDirection="column">{rows}</Box>
  })

  on('ui.render', { component: 'Pane', requestId: LOGS_PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const els = { Box, Text, Button }
    const w = await read($, watch)
    const now = await $.clock.now()
    const p = w.package
    const problems = w.events.filter(x => x.level !== 'info')
    const color = (l: LogEvent['level']) => (l === 'bad' ? 'error' : l === 'warn' ? RUST : undefined)

    const status = section(els, 'watching', 'Watching', undefined,
      <Text dimColor>{w.lastPollMs ? `Last look ${age(w.lastPollMs, now)}` : 'Not started yet (needs the kit or the game set up).'}</Text>,
      <Text dimColor>{`Game ${w.isGameRunning ? 'running' : 'not running'} · Zone Kit ${w.isEditorRunning ? 'open' : 'closed'}`}</Text>,
      w.error ? <Text color={RUST} wrap="wrap">{`The watcher failed: ${w.error}`}</Text> : null)

    const pkg = section(els, 'package', 'Last packaging', undefined,
      p.startedMs
        ? <Text>{p.active
          ? `${p.mod ?? ''} ${p.phase ?? 'running'} for ${clock(now - p.startedMs)}`
          : `${p.mod ?? ''} ${p.result === 'ok' ? 'packaged' : 'failed'} ${age(p.endedMs, now)}${p.endedMs ? ` (${clock(p.endedMs - p.startedMs)})` : ''}`}</Text>
        : <Text dimColor>None seen yet. Press Package Mod in the Zone Kit and it shows up here and above the prompt.</Text>,
      ...(p.errors ?? []).map((x, i) => <Text key={`err:${i}`} color="error" wrap="wrap">{x}</Text>),
      p.note ? <Text dimColor>{p.note}</Text> : null,
      w.rc?.folder ? <Text dimColor wrap="wrap">{`Release candidate: ${w.rc.folder}${w.rc.files?.length ? ` (${w.rc.files.join(', ')})` : ''}`}</Text> : null)

    const crashes = section(els, 'crashes', 'Crashes', undefined,
      w.crashes.length === 0 ? <Text dimColor>None since the watcher started.</Text> : null,
      ...w.crashes.slice(0, 3).map((c, i) => (
        <Box flexDirection="column" key={`crash:${i}`}>
          <Box flexDirection="row" gap={1}>
            <Text color="error">✗</Text>
            <Text bold>{c.family}</Text>
            <Text dimColor>{age(c.atMs, now)}</Text>
            {action(els, `ask:${i}`, 'Ask Claude', () => void $.prompt.submit({ text: crashPrompt(c), asUser: true }))}
          </Box>
          <Text wrap="wrap">{c.advice}</Text>
          {c.message ? <Text dimColor wrap="wrap">{c.message}</Text> : null}
          {c.stack.slice(0, 3).map((s, k) => <Text key={`st:${i}:${k}`} dimColor wrap="truncate">{`  ${s}`}</Text>)}
        </Box>
      )))

    const shown = [...problems].reverse().slice(0, 40)
    const log = section(els, 'events', 'From the logs', 'Cfg patch warnings, broken game data, texts, mod mounts and errors, newest first.',
      shown.length === 0 ? <Text dimColor>Nothing worth seeing yet.</Text> : null,
      ...shown.map((x, i) => (
        <Box flexDirection="row" gap={1} key={`ev:${i}`}>
          <Text color={color(x.level)}>{x.level === 'bad' ? '✗' : '!'}</Text>
          <Text dimColor>{`${x.source} ${x.kind}`}</Text>
          <Text wrap="truncate">{x.text}</Text>
        </Box>
      )),
      <Box flexDirection="row" gap={1} key="ev-actions">
        {shown.length ? action(els, 'ask-events', 'Ask Claude about these', () => void $.prompt.submit({
          text: 'zonecraft\'s log watcher shows these lines from my last session; what do they mean for the mod?\n' +
            shown.slice(0, 15).map(x => `- [${x.source} ${x.kind}] ${x.text}`).join('\n'),
          asUser: true,
        })) : null}
        <Button key="clear" dimColor onPress={() => void update($, watch, cur => ({ ...cur, events: [], crashes: [] }))}>Clear</Button>
        <Button key="refresh" dimColor onPress={() => void pollOnce($).catch(() => undefined)}>Refresh</Button>
      </Box>)

    const art = w.crashes.length
      ? scene($, e, 'repair', 'Clawd fixing his rifle with a wrench, sparks flying: the game crashed')
      : scene($, e, 'detector', 'Clawd sweeping his detector: watching the logs')
    return <Box flexDirection="column" gap={1}>{top(els, e.surface === 'terminal', art, status)}{pkg}{crashes}{log}</Box>
  })
}

async function copyRc($: Engine) {
  const settings = await readSettings($)
  const root = await activeModRoot($)
  if (!root) {
    await $.ui.toast('No mod to copy: open Claude in a mod folder, or pick one in /zonecraft-panel.')
    return
  }
  const r = await runJson<{ folder: string; files: string[] }>($, settings, 'tools/build/release_candidate.py',
    ['--mod-root', root, '--json'])
  if (r.value) {
    await update($, watch, cur => ({ ...cur, rc: { folder: r.value!.folder, files: r.value!.files, copied: Date.now() / 1000, pending: false } }))
    await $.ui.toast(`Release candidate in ${r.value.folder}: ${r.value.files.join(', ')}`)
  } else {
    await $.ui.toast(`Could not copy the release candidate: ${r.error}`)
  }
}

/** The features of the mod's PLAN.md still to confirm, each with Worked / Didn't buttons that tell Claude. */
async function testCard($: Engine, els: { Box: any; Text: any; Button: any }) {
  const { Box, Text, Button } = els
  const root = await activeModRoot($)
  const d = await dashboard($, root)
  const open = d.features.filter(f => !f.isDone)
  if (!root || d.features.length === 0) {
    return <Text key="tests" dimColor>No feature list in PLAN.md yet: test what you changed, then tell Claude how it went.</Text>
  }
  if (open.length === 0) return <Text key="tests" color="success">Every feature in PLAN.md is confirmed. Test what changed in this build.</Text>
  return (
    <Box flexDirection="column" key="tests" paddingLeft={2}>
      <Text dimColor>Try each in game, then press what happened:</Text>
      {open.slice(0, 8).map((f, i) => (
        <Box flexDirection="row" gap={1} key={`t:${i}`}>
          <Text color={ORANGE}>○</Text>
          <Text>{f.text}</Text>
          <Button key={`ok:${i}`} onPress={() => void $.prompt.submit({
            text: `In-game test of the latest build: "${f.text}" worked.`, asUser: true })}>Worked</Button>
          <Button key={`no:${i}`} dimColor onPress={() => void $.prompt.fill({
            text: `In-game test of the latest build: "${f.text}" did not work: `, mode: 'replace' })}>Didn't</Button>
        </Box>
      ))}
    </Box>
  )
}
