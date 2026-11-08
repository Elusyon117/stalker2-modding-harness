import type { EngineInterface as Engine } from 'claude-code'

import type { Dashboard, Paste, Status } from '../types'

const slash = (p: string) => p.replace(/\\/g, '/').replace(/\/+$/, '')
const join = (...parts: string[]) => parts.map(slash).join('/')
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

export async function dashboard($: Engine, cwd: string): Promise<Dashboard> {
  const settings = await readSettings($)
  const kit = typeof settings.kit === 'string' && settings.kit ? slash(settings.kit) : undefined
  const game = typeof settings.game === 'string' && settings.game ? slash(settings.game) : undefined
  const d: Dashboard = { isLegacy: false, kit, game, testPakFiles: 0, checkpoints: 0, pastes: [] }
  const root = await findModRoot($, cwd)
  if (!root) return d
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

export function age(ms: number | undefined, nowMs: number): string {
  if (ms === undefined) return ''
  const s = Math.max(0, Math.round((nowMs - ms) / 1000))
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.round(s / 60)} min ago`
  if (s < 86400) return `${Math.round(s / 3600)} h ago`
  return `${Math.round(s / 86400)} d ago`
}
