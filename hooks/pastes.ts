// The Blueprint pastes' buttons beyond Copy and Show nodes: Open graph (the Blueprint and graph a paste goes in,
// in the open editor), Pasted it: check (verify_paste.py compare against the asset), and Fix it (the problem, sent
// to Claude). The target comes from <paste>.meta.json, which Graph.write puts beside the paste.
import { atom, update } from 'claude-code'
import type { EngineInterface as Engine } from 'claude-code'

import type { Paste, PasteBusy } from '../types'
import { join, pythonArgv, readSettings } from './data'

export const BUSY_NONE: PasteBusy = { path: '', what: '' }
const busy = atom({ plugin: 'zonecraft', key: 'pasteBusy' } as const, BUSY_NONE, { shape: 'pasteBusy-1' })

const lastLine = (s: string) => s.trim().split('\n').filter(Boolean).pop() ?? ''

/** Runs a zonecraft Python tool for the mod `modRoot`; its exit code and output, or the error it failed with. */
async function run($: Engine, modRoot: string, script: string, args: string[], timeoutMs: number) {
  const argv = pythonArgv(await readSettings($), join($.plugin.root, script), args)
  try {
    const r = await $.process.run(argv, { env: { ZONECRAFT_MOD_DIR: modRoot }, timeoutMs })
    return { code: r.exitCode, out: `${r.stdout}\n${r.stderr}` }
  } catch (err) {
    return { code: -1, out: err instanceof Error ? err.message : String(err) }
  }
}

async function working($: Engine, p: Paste, what: PasteBusy['what'], job: () => Promise<void>) {
  await update($, busy, () => ({ path: p.path, what }))
  try {
    await job()
  } finally {
    await update($, busy, () => BUSY_NONE)
  }
}

/** Opens the paste's Blueprint in the editor and brings its graph forward (tools/editor/open_graph.py). */
export async function openGraph($: Engine, modRoot: string, p: Paste): Promise<void> {
  const t = p.target
  if (!t) return
  await working($, p, 'open', async () => {
    const r = await run($, modRoot, 'tools/editor/ue_exec.py',
      [join($.plugin.root, 'tools/editor/open_graph.py'), '--arg', `ASSET=${t.asset}`, '--arg', `GRAPH=${t.graph}`], 60_000)
    const name = t.asset.slice(t.asset.lastIndexOf('/') + 1)
    if (r.out.includes('NO_EDITOR_NODE')) {
      await $.ui.toast('Open the Zone Kit editor first (with Remote Execution on in Project Settings › Python).')
    } else if (r.code !== 0) {
      await $.ui.toast(`Could not open ${name}: ${lastLine(r.out)}`)
    } else {
      await $.ui.toast(r.out.includes(`GRAPH ${t.graph}`)
        ? `${name} is open at ${t.graph}: click into the graph and press Ctrl+V.`
        : `${name} is open: click its ${t.graph} tab, then into the graph, and press Ctrl+V.`)
    }
  })
}

/** Checks in the open editor that every pasted node arrived with its links (verify_paste.py compare --asset); the
 * report lands in <paste>.compare.json, which the panel shows. */
export async function checkPaste($: Engine, modRoot: string, p: Paste, redraw: () => Promise<void>): Promise<void> {
  const t = p.target
  if (!t) return
  await working($, p, 'check', async () => {
    const r = await run($, modRoot, 'tools/blueprints/verify_paste.py',
      ['compare', p.path, '--asset', t.asset, '--graph', t.graph], 180_000)
    if (r.code !== 0 && r.code !== 1) {
      await $.ui.toast(r.out.includes('editor open?') || r.out.includes('NO_EDITOR_NODE')
        ? 'Open the Zone Kit editor first (with Remote Execution on), then press Pasted it: check again.'
        : `Could not check ${p.name}: ${lastLine(r.out)}`)
    }
  })
  await redraw()
}

/** What Fix it sends Claude: the paste, where it goes and what its checks found. */
export async function fixPrompt($: Engine, p: Paste): Promise<string> {
  const details = async (kind: string) => {
    try {
      const r = JSON.parse(await $.fs.read(`${p.path.slice(0, -4)}.${kind}.json`)) as { details?: unknown }
      return Array.isArray(r.details) ? r.details.filter((x): x is string => typeof x === 'string') : []
    } catch {
      return []
    }
  }
  const lines = [`The Blueprint paste ${p.name} (${p.path}) has a problem.`]
  if (p.target) lines.push(`It goes in ${p.target.asset} › ${p.target.graph}.`)
  if (p.lint === 'bad') lines.push(`Paste check: ${p.lintText}`, ...(await details('lint')).map(x => `- ${x}`))
  if (p.compare === 'bad' && p.compareFresh) {
    lines.push(`After pasting, in the editor: ${p.compareText}`, ...(await details('compare')).map(x => `- ${x}`))
  }
  lines.push('Find the cause, fix the generator, write the paste again and run its check; tell me what to do in the editor.')
  return lines.join('\n')
}
