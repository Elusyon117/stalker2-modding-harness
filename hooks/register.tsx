import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { Dashboard, Paste, Status } from '../types'
import { sceneCells, sceneSvg } from './art'
import { H as SCENE_H, W as SCENE_W } from './clawd'
import { age, chooseMod, dashboard, findModRoot, knownMods, readSettings } from './data'

const PANE = 'zonecraft'
const TITLE = 'zonecraft'
const TOOL = 'mcp__zonecraft__open_panel'

const tick = atom({ plugin: 'zonecraft', key: 'tick' } as const, 0, { shape: 'tick-1' })
const copied = atom({ plugin: 'zonecraft', key: 'copied' } as const, { path: '', atMs: 0 }, { shape: 'copied-1' })
const tracked = atom({ plugin: 'zonecraft', key: 'tracked' } as const, '', { shape: 'tracked-1' })

// Kept across sessions in $.store: the mod folders sessions were opened in, and the mod last picked in the panel.
const SEEN = 'mods-seen'
const LAST = 'mod-picked'
const SEEN_MAX = 30

const strings = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [])

const SCENE_SVG = sceneSvg()
const SCENE_ALT = 'The zonecraft crab in its gas mask, sitting by a campfire and roasting a sausage on a stick'

// Tools whose run can change what the panel shows (files written, a cook, an install).
const CHANGERS = new Set(['Bash', 'PowerShell', 'Write', 'Edit', 'NotebookEdit'])

const MARK: Record<Status, string> = { ok: '✓', warn: '!', bad: '✗', none: '·' }
const COLOR: Record<Status, string | undefined> = { ok: 'success', warn: 'warning', bad: 'error', none: undefined }

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    // Bash children (a mod's gen_*.py through zonekit/tools/zonecraft_path.py) find zonecraft through this.
    await $.env.set('ZONECRAFT_ROOT', $.plugin.root)
    // Remember the mod this session is in, so the panel can offer it from other sessions too.
    const here = await findModRoot($, await $.session.cwd()).catch(() => undefined)
    if (here) {
      const seen = strings(await $.store.get(SEEN)).filter(r => r.toLowerCase() !== here.toLowerCase())
      await $.store.set(SEEN, [here, ...seen].slice(0, SEEN_MAX))
    }
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
    const d: Dashboard = await dashboard($, current?.root, settings)

    const pick = async (root: string) => {
      await update($, tracked, () => root)
      await $.store.set(LAST, root)
    }

    // The mod picker, where the surface draws one and there is more than one mod to pick from.
    const picker = () => {
      if (mods.length < 2 || !current) return null
      const options = mods.map(m => ({ value: m.root, label: m.isHere ? `${m.name} (this folder)` : m.name }))
      if (e.surface === 'terminal' || e.surface === 'desktop' || e.surface === 'vscode') {
        const { Select } = $.ui.resolve({ ...e, surface: e.surface })
        return <Select key="mod" label="Tracking" options={options} value={current.root} onSelect={pick} />
      }
      return <Text dimColor>{`Tracking ${current.name} (${mods.length} mods; pick another on your PC)`}</Text>
    }

    // The crab by its campfire, top right: animated where the surface draws SVG, block cells in a terminal.
    const scene = () => {
      if (e.surface === 'desktop' || e.surface === 'mobile' || e.surface === 'vscode') {
        const { Svg } = $.ui.resolve({ ...e, surface: e.surface })
        return <Svg source={SCENE_SVG} alt={SCENE_ALT} width={SCENE_W * 2} height={SCENE_H * 2} />
      }
      if (e.surface === 'terminal') {
        const { Raster } = $.ui.resolve({ ...e, surface: e.surface })
        return <Raster key="campfire" {...sceneCells()} />
      }
      return null
    }

    const row = (label: string, value: string, status: Status = 'none') => (
      <Box flexDirection="row" gap={1}>
        <Text color={COLOR[status]}>{MARK[status]}</Text>
        <Text dimColor>{label}</Text>
        <Text>{value}</Text>
      </Box>
    )

    const modSection = () => {
      if (!d.modRoot) {
        return (
          <Box flexDirection="column">
            <Text dimColor>No mod in this folder. Open Claude Code in a mod folder (one with mod.json), or ask</Text>
            <Text dimColor>"make a new Stalker 2 mod".</Text>
          </Box>
        )
      }
      const cookOk = d.cookMs !== undefined
      const pakFresh = d.testPakMs !== undefined && (d.cookMs === undefined || d.testPakMs >= d.cookMs)
      return (
        <Box flexDirection="column">
          <Text bold>{d.modName ?? '(mod.json has no name)'}{d.short ? <Text dimColor> · {d.short}</Text> : ''}</Text>
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
            <Button key={`copy:${p.name}`} variant="primary" onPress={copy}>{isCopied ? 'Copied' : 'Copy'}</Button>
            <Text bold>{p.name}</Text>
            <Text dimColor>{p.nodes} nodes · {age(p.mtimeMs, now)}</Text>
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
        </Box>
      )
    }

    return (
      <Box flexDirection="column" gap={1}>
        {e.surface === 'terminal'
          ? (
            // a terminal's cells are wide: the scene takes its own row, at the right
            <>
              <Box flexDirection="row" justifyContent="flex-end">{scene()}</Box>
              <Box flexDirection="column" gap={1}>
                <Text bold color="claude">Mod</Text>
                {picker()}
                {modSection()}
              </Box>
            </>
          )
          : (
            <Box flexDirection="row" justifyContent="space-between" alignItems="flex-start" gap={2}>
              <Box flexDirection="column" flexShrink={1} gap={1}>
                <Text bold color="claude">Mod</Text>
                {picker()}
                {modSection()}
              </Box>
              <Box flexShrink={0}>{scene()}</Box>
            </Box>
          )}
        <Box flexDirection="column">
          <Text bold color="claude">Blueprint pastes</Text>
          {d.pastes.length === 0
            ? <Text dimColor>None yet. Paste text Claude writes to zonekit/paste/ shows up here with a Copy button.</Text>
            : null}
          {d.pastes.map(pasteRow)}
          {d.pastes.length > 0
            ? <Text dimColor>Copy, click into the Blueprint graph in the Zone Kit, press Ctrl+V, then Compile and Save.</Text>
            : null}
        </Box>
        <Box flexDirection="row">
          <Button key="refresh" dimColor onPress={() => void update($, tick, n => n + 1)}>Refresh</Button>
        </Box>
      </Box>
    )
  })
}
