import { expect, test } from 'claude-code/testing'

// The zonecraft panel, drawn against a fake PC: two mods in the mods folder, machine settings, a cook, a test copy,
// a paste.
const NOW = Date.UTC(2026, 10, 8, 12, 0, 0)
const MIN = 60_000
const MODS = 'C:/mods'
const MOD = `${MODS}/MyMod`
const OTHER = `${MODS}/OtherMod`
const KIT = 'D:/Kit'
const GAME = 'E:/Steam/S2'
const UTOC = `${KIT}/Stalker2/SavedMods/Staged/MyMod/Windows/NewContent/Windows/Stalker2/Mods/MyMod/Content/Paks/Windows/MyModStalker2-Windows-NewContent.utoc`
const PASTE = 'Begin Object Class=/Script/BlueprintGraph.K2Node_Event Name="A"\nEnd Object\n' +
  'Begin Object Class=/Script/BlueprintGraph.K2Node_IfThenElse Name="B"\nEnd Object\n' +
  'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="C"\nEnd Object\n'

const FILES: Record<string, string> = {
  [`${MOD}/mod.json`]: '{"name": "MyMod", "short": "MM"}',
  [`${MOD}/CLAUDE.md`]: '# MyMod\n\n## Current state\n- 2026-11-01: repo created.\n- 2026-11-07: build 3 sits by the fire.\n\n## Key facts\n',
  [`${OTHER}/mod.json`]: '{"name": "OtherMod", "short": "OM"}',
  [`${OTHER}/CLAUDE.md`]: '# OtherMod\n\n## Current state\n- 2026-11-05: the radio plays.\n',
  [`${MOD}/zonekit/paste/seat_tick.txt`]: PASTE,
  [`${MOD}/zonekit/paste/seat_tick.lint.json`]: '{"ok": true, "summary": "2 nodes, no problems"}',
}
const DIRS: Record<string, { name: string; kind: 'file' | 'dir'; mtimeMs: number }[]> = {
  [`${MOD}/zonekit/paste`]: [
    { name: 'seat_tick.txt', kind: 'file', mtimeMs: NOW - 2 * MIN },
    { name: 'seat_tick.lint.json', kind: 'file', mtimeMs: NOW - 2 * MIN },
  ],
  [MODS]: [
    { name: 'MyMod', kind: 'dir', mtimeMs: NOW },
    { name: 'OtherMod', kind: 'dir', mtimeMs: NOW },
    { name: 'notes', kind: 'dir', mtimeMs: NOW },
  ],
  [`${MOD}/zonekit/builds`]: [{ name: 'build3', kind: 'dir', mtimeMs: NOW - 60 * MIN }],
  [`${GAME}/Stalker2/Content/Paks/~mods/zzz_MyMod_PakTest`]: [
    { name: 'zzz_MyMod_30_P.utoc', kind: 'file', mtimeMs: NOW - 10 * MIN },
  ],
}
const STATS: Record<string, number> = { [UTOC]: NOW - 12 * MIN }

const PANE = {
  plugin: 'zonecraft',
  component: 'Pane',
  requestId: 'zonecraft',
  props: {
    title: 'zonecraft',
    isFocused: false,
    bodyColumns: 80,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 40 },
    view: {},
  },
} as const

const norm = (p: string) => p.split('\\').join('/')
const missing = () => Object.assign(new Error('ENOENT'), { code: 'ENOENT' })

type Pc = { cwd: string; copiedTexts?: string[]; modsDir?: boolean; store?: Record<string, unknown> }

function fakePc(on: Parameters<Parameters<typeof test>[1]>[1], pc: Pc) {
  const { cwd, copiedTexts = [], modsDir = true, store = {} } = pc
  const files: Record<string, string> = {
    ...FILES,
    ['C:/Local/zonecraft/settings.json']: JSON.stringify({ kit: KIT, game: GAME, ...(modsDir ? { mods_dir: MODS } : {}) }),
  }
  on('session.cwd', () => ({ value: cwd }))
  on('clock.now', () => ({ value: NOW }))
  on('env.get', (_, e) => ({ value: e.name === 'LOCALAPPDATA' ? 'C:/Local' : undefined }))
  on('fs.exists', (_, e) => ({ value: norm(e.path) in files || norm(e.path) in DIRS }))
  on('fs.read', (_, e) => {
    const p = norm(e.path)
    if (!(p in files)) throw missing()
    return { value: files[p] }
  })
  on('fs.list', (_, e) => {
    const list = DIRS[norm(e.path)]
    if (!list) throw missing()
    return { value: list.map(x => ({ ...x, size: 1, isLink: false })) }
  })
  on('fs.stat', (_, e) => {
    const t = STATS[norm(e.path)]
    if (t === undefined) throw missing()
    return { value: { kind: 'file', size: 1, mtimeMs: t, isLink: false } }
  })
  on('store.get', (_, e) => ({ value: store[e.key] }))
  on('store.set', (_, e) => {
    store[e.key] = e.value
    return { value: undefined }
  })
  on('ui.copy', (_, e) => {
    copiedTexts.push(e.text)
    return { value: { isCopied: true } }
  })
}

test('the panel shows the mod, its cook and test copy, and a paste to copy', async ($, on) => {
  const copiedTexts: string[] = []
  fakePc(on, { cwd: `${MOD}/zonekit/tools`, copiedTexts })

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect((await ui.find({ type: 'Text', text: /^MyMod/ }))?.text).toContain('MyMod')
    expect((await ui.find({ type: 'Text', text: /build 3 sits/ }))?.text).toContain('2026-11-07')
    expect((await ui.find({ type: 'Text', text: /12 min ago/ }))?.text).toBe('12 min ago')
    expect((await ui.find({ type: 'Text', text: /installed/ }))?.text).toBe('installed 10 min ago')
    expect((await ui.find({ type: 'Text', text: /build3/ }))?.text).toBe('1 (last: build3)')
    expect((await ui.find({ type: 'Text', text: /nodes/ }))?.text).toBe('2 nodes · 2 min ago')
    expect((await ui.find({ type: 'Text', text: /check:/ }))?.text).toBe('check: 2 nodes, no problems')
    const scene = await ui.find({ type: surface === 'terminal' ? 'Raster' : 'Svg' })
    expect(scene).toBeDefined()
    if (surface === 'desktop') expect(String((scene?.props as { source?: string }).source).length).toBeLessThan(131072)
    await ui.unmount()
  }

  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  await ui.press({ key: 'copy:seat_tick' })
  expect(copiedTexts).toEqual([PASTE])
  await ui.unmount()
})

test('the picker switches the panel to another mod and remembers the pick', async ($, on) => {
  const store: Record<string, unknown> = {}
  fakePc(on, { cwd: MOD, store })
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    const select = await ui.find({ type: 'Select', key: 'mod' })
    expect(JSON.stringify(select?.props)).toContain('OtherMod')
    expect(JSON.stringify(select?.props)).not.toContain('notes')
    await ui.select({ key: 'mod', value: OTHER })
    expect((await ui.find({ type: 'Text', text: /^OtherMod/ }))?.text).toContain('OtherMod')
    expect((await ui.find({ type: 'Text', text: /radio plays/ }))?.text).toContain('2026-11-05')
    expect(store['mod-picked']).toBe(OTHER)
    await ui.select({ key: 'mod', value: MOD })
    await ui.unmount()
  }
})

test('outside a mod the panel shows the mod picked last time', async ($, on) => {
  fakePc(on, { cwd: 'C:/somewhere/else', store: { 'mod-picked': OTHER } })
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect((await ui.find({ type: 'Text', text: /^OtherMod/ }))?.text).toContain('OtherMod')
  await ui.unmount()
})

test('with no mod anywhere the panel says how to get one', async ($, on) => {
  fakePc(on, { cwd: 'C:/somewhere/else', modsDir: false })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /No mod in this folder/ }))?.text).toContain('mod.json')
  expect((await ui.find({ type: 'Text', text: /None yet/ }))?.text).toContain('zonekit/paste')
  await ui.unmount()
})
