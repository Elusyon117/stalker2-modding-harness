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

const pic = (w: number, h: number) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="-100 -50 ${w} ${h}" role="img"><rect/></svg>`
const VIEW = {
  version: 1,
  views: [
    { title: 'Tick: heal while seated', nodes: 12, hand: [], minx: -100, miny: -50, w: 3000, h: 600, svg: pic(3000, 600) },
    { title: 'Input: stand up', nodes: 2, hand: [], minx: -100, miny: -50, w: 800, h: 500, svg: pic(800, 500) },
  ],
  hand: ['Branch (only while seated) › false → Stop Healing'],
}

const FILES: Record<string, string> = {
  [`${MOD}/mod.json`]: '{"name": "MyMod", "short": "MM"}',
  [`${MOD}/CLAUDE.md`]: '# MyMod\n\n## Current state\n- 2026-11-01: repo created.\n- 2026-11-07: build 3 sits by the fire.\n\n## Key facts\n',
  [`${OTHER}/mod.json`]: '{"name": "OtherMod", "short": "OM"}',
  [`${OTHER}/CLAUDE.md`]: '# OtherMod\n\n## Current state\n- 2026-11-05: the radio plays.\n',
  [`${MOD}/PLAN.md`]: [
    '# MyMod — plan', '', '## Idea', 'Sit by any fire.', '',
    '## Features', '_(tick when confirmed)_', '- [x] Sit with a key', '- [x] Camera lowers', '- [ ] Heal while sitting', '',
    '## Details to check', '- [x] Keyboard and gamepad', '- [ ] Works with Campfire Saves', '',
    '## Approach', '- [ ] not a feature', '',
  ].join('\n'),
  [`${MOD}/zonekit/paste/seat_tick.txt`]: PASTE,
  [`${MOD}/zonekit/paste/seat_tick.lint.json`]: '{"ok": true, "summary": "2 nodes, no problems"}',
  [`${MOD}/zonekit/paste/seat_tick.view.json`]: JSON.stringify(VIEW),
}
const DIRS: Record<string, { name: string; kind: 'file' | 'dir'; mtimeMs: number }[]> = {
  [`${MOD}/zonekit/paste`]: [
    { name: 'seat_tick.txt', kind: 'file', mtimeMs: NOW - 2 * MIN },
    { name: 'seat_tick.lint.json', kind: 'file', mtimeMs: NOW - 2 * MIN },
    { name: 'seat_tick.view.json', kind: 'file', mtimeMs: NOW - 2 * MIN },
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
    expect((await ui.find({ type: 'Text', text: /^Sit by any fire/ }))?.text).toBe('Sit by any fire.')
    expect((await ui.find({ type: 'Text', text: /of 3 done/ }))?.text).toBe('2 of 3 done')
    expect((await ui.find({ type: 'Text', text: /^Heal while/ }))?.text).toBe('Heal while sitting')
    expect((await ui.find({ type: 'Text', text: /open$/ }))?.text).toBe('1 open')
    expect(await ui.find({ type: 'Text', text: /not a feature/ })).toBeUndefined()
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

test('All mods lists every mod with its status; picking one opens it and is remembered', async ($, on) => {
  const store: Record<string, unknown> = {}
  fakePc(on, { cwd: MOD, store })
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    // in a mod folder the dashboard opens on that mod, with a way back to the list
    expect((await ui.find({ type: 'Text', text: /^MyMod/ }))?.text).toContain('MyMod')
    await ui.press({ key: 'all-mods' })
    expect((await ui.find({ type: 'Text', text: /^YOUR MODS/ }))?.text).toBe('YOUR MODS (2)')
    expect(await ui.find({ key: 'open:0' })).toBeDefined()
    expect(await ui.find({ key: 'open:1' })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /notes/ })).toBeUndefined()
    expect((await ui.find({ type: 'Text', text: /^built 12 min ago/ }))?.text).toBe('built 12 min ago')
    expect((await ui.find({ type: 'Text', text: /test copy ✓/ }))?.text).toBe(' · test copy ✓')
    expect((await ui.find({ type: 'Text', text: /features/ }))?.text).toBe(' · 2/3 features')
    expect((await ui.find({ type: 'Text', text: /radio plays/ }))?.text).toContain('2026-11-05')

    await ui.press({ key: 'open:1' })
    expect((await ui.find({ type: 'Text', text: /^OtherMod/ }))?.text).toContain('OtherMod')
    expect((await ui.find({ type: 'Text', text: /No feature list yet/ }))?.text).toContain('PLAN.md')
    expect(store['mod-picked']).toBe(OTHER)
    await ui.press({ key: 'all-mods' })
    await ui.press({ key: 'open:0' })
    await ui.unmount()
  }
})

test('outside a mod the dashboard opens on the list of mods', async ($, on) => {
  fakePc(on, { cwd: 'C:/somewhere/else', store: { 'mod-picked': OTHER } })
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect((await ui.find({ type: 'Text', text: /^YOUR MODS/ }))?.text).toBe('YOUR MODS (2)')
  expect((await ui.find({ type: 'Text', text: /last opened/ }))?.text).toBe('last opened')
  expect((await ui.find({ type: 'Text', text: /^not built yet|^build unknown|^built/ }))).toBeDefined()
  await ui.unmount()
})

test('with no mod anywhere the panel says how to get one', async ($, on) => {
  fakePc(on, { cwd: 'C:/somewhere/else', modsDir: false })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /No mod in this folder/ }))?.text).toContain('mod.json')
  expect((await ui.find({ type: 'Text', text: /None yet/ }))?.text).toContain('zonekit/paste')
  expect(await ui.find({ key: 'scene:exploring' })).toBeDefined()
  await ui.unmount()
})

test('Show nodes draws the paste one comment box at a time, with zoom, moves and the wires to draw by hand', async ($, on) => {
  fakePc(on, { cwd: MOD })
  const viewBox = async (ui: Awaited<ReturnType<typeof $.ui.mount>>) => {
    const sources = (await ui.findAll({ type: 'Svg' })).map(x => String((x.props as { source?: string }).source))
    const m = /viewBox="([^"]*)"/.exec(sources.find(src => src.endsWith('<rect/></svg>')) ?? '')
    return m?.[1]
  }
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await viewBox(ui)).toBeUndefined()
  await ui.press({ key: 'nodes:seat_tick' })
  expect(await viewBox(ui)).toBe('-100 -50 700 600')          // the closest zoom, at the left end
  expect((await ui.find({ type: 'Text', text: /Stop Healing/ }))?.text).toContain('Branch (only while seated)')
  await ui.press({ key: 'dash:right' })
  expect(await viewBox(ui)).toBe('320 -50 700 600')
  await ui.press({ key: 'dash:out' })
  expect(await viewBox(ui)).toBe('-100 -50 3000 600')         // the whole box
  await ui.press({ key: 'dash:tab:1' })
  expect(await viewBox(ui)).toBe('-100 -50 800 500')          // a short box is drawn whole
  await ui.press({ key: 'hide:seat_tick' })
  expect(await viewBox(ui)).toBeUndefined()
  await ui.unmount()

  // a terminal lists the wires to draw by hand and says where the picture shows
  const term = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await term.press({ key: 'nodes:seat_tick' })
  expect((await term.find({ type: 'Text', text: /Stop Healing/ }))?.text).toContain('false')
  expect((await term.find({ type: 'Text', text: /desktop app/ }))?.text).toContain('picture')
  await term.unmount()
})

test('a picture older than the paste or its names is drawn again: errors show, Redraw runs paste_view.py', async ($, on) => {
  fakePc(on, { cwd: MOD })
  const dir = DIRS[`${MOD}/zonekit/paste`]
  dir.push({ name: 'seat_tick.meta.json', kind: 'file', mtimeMs: NOW - MIN })   // names added after the picture
  const runs: string[][] = []
  let result = { exitCode: 1, stdout: '', stderr: 'Traceback\nValueError: boom' }
  on('process.run', (_, e) => {
    runs.push([...e.argv])
    return { value: result }
  })
  try {
    const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
    await ui.press({ key: 'nodes:seat_tick' })
    expect(runs).toHaveLength(1)
    expect(runs[0].some(a => a.endsWith('tools/blueprints/paste_view.py'))).toBe(true)
    expect(runs[0].at(-1)).toBe(`${MOD}/zonekit/paste/seat_tick.txt`)
    expect((await ui.find({ type: 'Text', text: /Could not draw/ }))?.text).toContain('boom')

    result = { exitCode: 0, stdout: '{"views": 2, "nodes": 14, "hand": 1}', stderr: '' }
    await ui.press({ key: 'redraw:seat_tick' })
    expect(runs).toHaveLength(2)
    expect(await ui.find({ type: 'Text', text: /Could not draw/ })).toBeUndefined()
    expect((await ui.find({ type: 'Text', text: /Stop Healing/ }))?.text).toContain('Branch')
    await ui.unmount()
  } finally {
    dir.pop()
  }
})

test('a paste with a target opens its graph, checks itself in the editor and asks Claude to fix what is missing', async ($, on) => {
  const dir = DIRS[`${MOD}/zonekit/paste`]
  const meta = `${MOD}/zonekit/paste/seat_tick.meta.json`
  const cmp = `${MOD}/zonekit/paste/seat_tick.compare.json`
  FILES[meta] = '{"asset": "/MyMod/Runtime/BP_Seat", "graph": "EventGraph"}'
  FILES[cmp] = '{"ok": false, "summary": "1 node(s) missing, 0 with fewer links", "details": ["MISSING x1: Branch (every 2 s)"]}'
  dir.push({ name: 'seat_tick.meta.json', kind: 'file', mtimeMs: NOW - 3 * MIN })
  fakePc(on, { cwd: MOD })
  const runs: { argv: string[]; env?: Record<string, string> }[] = []
  const toasts: string[] = []
  const prompts: string[] = []
  on('process.run', (_, e) => {
    runs.push({ argv: [...e.argv], env: e.init?.env })
    if (e.argv.includes('compare')) dir.push({ name: 'seat_tick.compare.json', kind: 'file', mtimeMs: NOW })
    return { value: { exitCode: e.argv.includes('compare') ? 1 : 0, stdout: 'OPENED /MyMod/Runtime/BP_Seat\nGRAPH_TAB EventGraph', stderr: '' } }
  })
  on('ui.toast', (_, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  on('prompt.submit', (_, e) => {
    prompts.push(e.text)
    return { text: e.text }
  })
  try {
    const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
    expect((await ui.find({ type: 'Text', text: /BP_Seat › EventGraph/ }))?.text).toBe('BP_Seat › EventGraph')
    expect(await ui.find({ key: 'fix:seat_tick' })).toBeUndefined()       // an old editor check is not shown

    await ui.press({ key: 'open:seat_tick' })
    expect(runs[0].argv.some(a => a.endsWith('tools/editor/ue_exec.py'))).toBe(true)
    expect(runs[0].argv).toContain('ASSET=/MyMod/Runtime/BP_Seat')
    expect(runs[0].env?.ZONECRAFT_MOD_DIR).toBe(MOD)
    expect(toasts[0]).toContain('click its EventGraph tab')

    await ui.press({ key: 'check:seat_tick' })
    expect(runs[1].argv.slice(-6)).toEqual(['compare', `${MOD}/zonekit/paste/seat_tick.txt`, '--asset', '/MyMod/Runtime/BP_Seat', '--graph', 'EventGraph'])
    expect((await ui.find({ type: 'Text', text: /in the editor/ }))?.text).toContain('1 node(s) missing')
    await ui.press({ key: 'fix:seat_tick' })
    expect(prompts[0]).toContain('MISSING x1: Branch (every 2 s)')
    expect(prompts[0]).toContain('/MyMod/Runtime/BP_Seat › EventGraph')
    await ui.unmount()
  } finally {
    while (dir.length > 3) dir.pop()
    delete FILES[meta]
    delete FILES[cmp]
  }
})

test('a paste checked in the editor with every node there folds into Done', async ($, on) => {
  const dir = DIRS[`${MOD}/zonekit/paste`]
  const cmp = `${MOD}/zonekit/paste/seat_tick.compare.json`
  FILES[cmp] = '{"ok": true, "summary": "every node arrived with its links"}'
  dir.push({ name: 'seat_tick.compare.json', kind: 'file', mtimeMs: NOW })
  fakePc(on, { cwd: MOD })
  try {
    const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
    expect((await ui.find({ type: 'Text', text: /^Done/ }))?.text).toBe('Done (1)')
    expect((await ui.find({ type: 'Text', text: /all arrived/ }))?.text).toBe('2 nodes · all arrived · 2 min ago')
    expect(await ui.find({ key: 'copy:seat_tick' })).toBeUndefined()
    expect(await ui.find({ key: 'copy-done:seat_tick' })).toBeDefined()
    await ui.unmount()
  } finally {
    dir.pop()
    delete FILES[cmp]
  }
})
