import type { EngineInterface as Engine } from 'claude-code'

import type { Dashboard, ModChoice, Paste, PlanItem, Status } from '../types'

export const slash = (p: string) => p.replace(/\\/g, '/').replace(/\/+$/, '')
export const join = (...parts: string[]) => parts.map(slash).join('/')
const parent = (p: string) => {
  const s = slash(p)
  const cut = s.lastIndexOf('/')
  return cut <= 0 ? s : s.slice(0, cut)
}

async function readJson($: Engine, path: string): Promise<Record<string, unknown> | undefined> {
  try {
    const text = await $.fs.read(path)
    return JSON.parse(text.replace(/^﻿/, '')) as Record<string, unknown>
  } catch {
    return undefined
  }
}

async function mtime($: Engine, path: string): Promise<number | undefined> {
  try {
    return (await $.fs.stat(path)).mtimeMs
  } catch {
    return undefined
  }
}

/** The nearest folder holding mod.json, walking up from `cwd`. */
export async function findModRoot($: Engine, cwd: string): Promise<string | undefined> {
  let dir = slash(cwd)
  for (let i = 0; i < 40; i++) {
    if (await $.fs.exists(join(dir, 'mod.json'))) return dir
    const up = parent(dir)
    if (up === dir) return undefined
    dir = up
  }
  return undefined
}

/** Machine settings: the original harness's file first, zonecraft's own on top. */
export async function readSettings($: Engine): Promise<Record<string, unknown>> {
  const local = await $.env.get('LOCALAPPDATA')
  if (!local) return {}
  const legacy = (await readJson($, join(local, 'stalker2-modding-harness', 'settings.json'))) ?? {}
  const own = (await readJson($, join(local, 'zonecraft', 'settings.json'))) ?? {}
  return { ...legacy, ...own }
}

/** The last "- " line under "## Current state" in the mod's CLAUDE.md (or a legacy AGENTS.md). */
export function currentState(text: string): string | undefined {
  const at = text.search(/^## Current state/m)
  if (at < 0) return undefined
  const rest = text.slice(at).split('\n').slice(1)
  const end = rest.findIndex(l => l.startsWith('## '))
  const lines = (end < 0 ? rest : rest.slice(0, end)).filter(l => l.startsWith('- '))
  const last = lines[lines.length - 1]
  return last?.slice(2).trim()
}

/** The lines under the "## <heading>..." section of a Markdown text, up to the next "## " heading. */
function section(text: string, heading: string): string[] {
  const lines = text.split('\n')
  const at = lines.findIndex(l => l.toLowerCase().startsWith(`## ${heading.toLowerCase()}`))
  if (at < 0) return []
  const rest = lines.slice(at + 1)
  const end = rest.findIndex(l => l.startsWith('## '))
  return end < 0 ? rest : rest.slice(0, end)
}

/** A mod's PLAN.md as the panel shows it: the idea's first line and the two checklists. */
export function readPlan(text: string): { idea?: string; features: PlanItem[]; details: PlanItem[] } {
  const checklist = (heading: string) => section(text, heading)
    .map(l => /^\s*[-*] \[( |x|X)\]\s+(.+?)\s*$/.exec(l))
    .filter((m): m is RegExpExecArray => m !== null)
    .map(m => ({ text: m[2], isDone: m[1] !== ' ' }))
  const idea = section(text, 'Idea').map(l => l.trim()).find(l => l && !l.startsWith('_'))
  return { idea, features: checklist('Features'), details: checklist('Details to check') }
}

/** Counts top-level node blocks of paste text (comment boxes excluded). */
export function countNodes(text: string): number {
  let n = 0
  for (const line of text.split('\n')) {
    if (/^Begin Object Class=\S+/.test(line) && !line.includes('EdGraphNode_Comment')) n++
  }
  return n
}

/** Reads a report verify_paste wrote next to a paste: `{ ok, summary }`. */
async function report($: Engine, path: string): Promise<{ status: Status; text: string }> {
  const r = await readJson($, path)
  if (!r) return { status: 'none', text: '' }
  const ok = r.ok === true
  const summary = typeof r.summary === 'string' ? r.summary : ''
  return { status: ok ? 'ok' : 'bad', text: summary }
}

export async function listPastes($: Engine, modRoot: string, limit = 6): Promise<Paste[]> {
  const dir = join(modRoot, 'zonekit', 'paste')
  let entries: Awaited<ReturnType<Engine['fs']['list']>> = []
  try {
    entries = await $.fs.list(dir)
  } catch {
    return []
  }
  const files = entries
    .filter(e => e.kind === 'file' && e.name.endsWith('.txt'))
    .sort((a, b) => b.mtimeMs - a.mtimeMs)
    .slice(0, limit)
  const out: Paste[] = []
  for (const f of files) {
    const path = join(dir, f.name)
    const base = path.slice(0, -4)
    let nodes = 0
    try {
      nodes = countNodes(await $.fs.read(path))
    } catch {
      nodes = 0
    }
    const lint = await report($, `${base}.lint.json`)
    const cmp = await report($, `${base}.compare.json`)
    out.push({
      path, name: f.name.slice(0, -4), mtimeMs: f.mtimeMs, nodes,
      lint: lint.status, lintText: lint.text, compare: cmp.status, compareText: cmp.text,
    })
  }
  return out
}

const setting = (s: Record<string, unknown>, key: string) =>
  typeof s[key] === 'string' && s[key] ? slash(s[key] as string) : undefined

async function modName($: Engine, root: string): Promise<string> {
  const mod = await readJson($, join(root, 'mod.json'))
  return typeof mod?.name === 'string' && mod.name ? mod.name : root.slice(root.lastIndexOf('/') + 1)
}

/** Every mod the panel can track: the one this session is in, each mod folder under the machine's `mods_dir` (where
 * new_mod.ps1 makes them), and the mods earlier sessions were opened in (`remembered`); gone folders are dropped.
 * The session's own mod comes first, the rest by name. */
export async function knownMods($: Engine, cwd: string, settings: Record<string, unknown>,
  remembered: readonly string[]): Promise<ModChoice[]> {
  const here = await findModRoot($, cwd)
  const roots: string[] = []
  const add = (r: string) => {
    if (!roots.some(x => x.toLowerCase() === r.toLowerCase())) roots.push(r)
  }
  if (here) add(here)
  const modsDir = setting(settings, 'mods_dir')
  if (modsDir) {
    try {
      for (const e of await $.fs.list(modsDir)) {
        if (e.kind === 'dir' && await $.fs.exists(join(modsDir, e.name, 'mod.json'))) add(join(modsDir, e.name))
      }
    } catch {
      // no such folder
    }
  }
  for (const r of remembered) {
    if (await $.fs.exists(join(r, 'mod.json'))) add(slash(r))
  }
  const out: ModChoice[] = []
  for (const root of roots) out.push({ root, name: await modName($, root), isHere: root === here })
  return out.sort((a, b) => Number(b.isHere) - Number(a.isHere) || a.name.localeCompare(b.name))
}

/** Which mod to show: the one picked this session, else the session's own, else the one picked last time, else the
 * first known. A pick whose folder is gone is passed over. */
export function chooseMod(mods: readonly ModChoice[], picked: string, lastPicked: string): ModChoice | undefined {
  const find = (root: string) => (root ? mods.find(m => m.root.toLowerCase() === root.toLowerCase()) : undefined)
  return find(picked) ?? mods.find(m => m.isHere) ?? find(lastPicked) ?? mods[0]
}

export async function dashboard($: Engine, root: string | undefined, settings?: Record<string, unknown>):
  Promise<Dashboard> {
  settings ??= await readSettings($)
  const kit = setting(settings, 'kit')
  const game = setting(settings, 'game')
  const d: Dashboard = { isLegacy: false, kit, game, testPakFiles: 0, checkpoints: 0, pastes: [], features: [], details: [] }
  if (!root) return d
  try {
    const plan = readPlan((await $.fs.read(join(root, 'PLAN.md'))).replace(/\r\n/g, '\n'))
    d.idea = plan.idea
    d.features = plan.features
    d.details = plan.details
  } catch {
    // no plan yet
  }
  d.modRoot = root
  const mod = (await readJson($, join(root, 'mod.json'))) ?? {}
  d.modName = typeof mod.name === 'string' ? mod.name : undefined
  d.short = typeof mod.short === 'string' ? mod.short : undefined
  d.isLegacy = await $.fs.exists(join(root, '.harness-sync'))
  for (const doc of ['CLAUDE.md', 'AGENTS.md']) {
    try {
      const state = currentState((await $.fs.read(join(root, doc))).replace(/\r\n/g, '\n'))
      if (state) {
        d.state = state
        break
      }
    } catch {
      // no such file
    }
  }
  const name = d.modName
  if (name && kit) {
    const staged = join(kit, 'Stalker2', 'SavedMods', 'Staged', name, 'Windows')
    const times: number[] = []
    for (const kind of ['OverrideContent', 'NewContent']) {
      const t = await mtime($, join(staged, kind, 'Windows', 'Stalker2', 'Mods', name, 'Content', 'Paks', 'Windows',
        `${name}Stalker2-Windows-${kind}.utoc`))
      if (t !== undefined) times.push(t)
    }
    if (times.length) d.cookMs = Math.max(...times)
  }
  if (name && game) {
    try {
      const files = (await $.fs.list(join(game, 'Stalker2', 'Content', 'Paks', '~mods', `zzz_${name}_PakTest`)))
        .filter(e => e.kind === 'file')
      d.testPakFiles = files.length
      if (files.length) d.testPakMs = Math.max(...files.map(f => f.mtimeMs))
    } catch {
      // not installed
    }
  }
  try {
    const builds = (await $.fs.list(join(root, 'zonekit', 'builds'))).filter(e => e.kind === 'dir')
    d.checkpoints = builds.length
    const newest = [...builds].sort((a, b) => b.mtimeMs - a.mtimeMs)[0]
    d.lastCheckpoint = newest?.name
  } catch {
    // none yet
  }
  d.pastes = await listPastes($, root)
  return d
}

/** How to start a zonecraft Python tool: the machine settings' "python" if set, else the Windows launcher `py`.
 * `-I` keeps the tool from importing files of the folder it runs in. */
export function pythonArgv(settings: Record<string, unknown>, script: string, args: string[] = []): string[] {
  const py = typeof settings.python === 'string' && settings.python ? settings.python : 'py'
  return [py, '-I', script, ...args]
}

/** Runs a zonecraft Python tool that prints one JSON object; undefined (and the reason) when it fails. */
export async function runJson<T>($: Engine, settings: Record<string, unknown>, script: string, args: string[],
  timeoutMs = 30_000): Promise<{ value?: T; error?: string }> {
  try {
    const r = await $.process.run(pythonArgv(settings, join($.plugin.root, script), args), { timeoutMs })
    if (r.exitCode !== 0) return { error: (r.stderr || r.stdout).trim().split('\n').slice(-3).join(' ') || `exit ${r.exitCode}` }
    return { value: JSON.parse(r.stdout) as T }
  } catch (err) {
    return { error: err instanceof Error ? err.message : String(err) }
  }
}

/** The mod a background job works on: the one picked in the panel (kept in $.store), else the session's own. */
export async function activeModRoot($: Engine): Promise<string | undefined> {
  const picked = await $.store.get('mod-picked').catch(() => undefined)
  const here = await findModRoot($, await $.session.cwd()).catch(() => undefined)
  if (here) return here
  if (typeof picked === 'string' && picked && await $.fs.exists(join(picked, 'mod.json'))) return slash(picked)
  return undefined
}

export async function modJson($: Engine, root: string): Promise<Record<string, unknown>> {
  return (await readJson($, join(root, 'mod.json'))) ?? {}
}

export function clock(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

export function age(ms: number | undefined, nowMs: number): string {
  if (ms === undefined) return ''
  const s = Math.max(0, Math.round((nowMs - ms) / 1000))
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.round(s / 60)} min ago`
  if (s < 86400) return `${Math.round(s / 3600)} h ago`
  return `${Math.round(s / 86400)} d ago`
}
