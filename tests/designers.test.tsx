import { expect, test } from 'claude-code/testing'

// The Quest designer, the Conflicts panel and the Logs panel, drawn against a fake PC with two mods.
const NOW = Date.UTC(2026, 10, 9, 12, 0, 0)
const MODS = 'C:/mods'
const MOD = `${MODS}/MyMod`
const OTHER = `${MODS}/OtherMod`

const pane = (requestId: string, title: string) => ({
  plugin: 'zonecraft',
  component: 'Pane',
  requestId,
  props: { title, isFocused: false, bodyColumns: 100, placement: 'dock', scroll: { offset: 0, bodyRows: 200 }, view: {} },
}) as const

const norm = (p: string) => p.split('\\').join('/')
const missing = () => Object.assign(new Error('ENOENT'), { code: 'ENOENT' })

type Seen = { prompts: string[]; toasts: string[]; store: Record<string, unknown>; written: Record<string, string>; runs: string[][] }

function fakePc(on: Parameters<Parameters<typeof test>[1]>[1], stdout = '{}'): Seen {
  const seen: Seen = { prompts: [], toasts: [], store: {}, written: {}, runs: [] }
  const files: Record<string, string> = {
    [`${MOD}/mod.json`]: '{"name": "MyMod", "short": "MM"}',
    [`${OTHER}/mod.json`]: '{"name": "OtherMod", "short": "OM"}',
    'C:/Local/zonecraft/settings.json': JSON.stringify({ mods_dir: MODS }),
  }
  const dirs: Record<string, { name: string; kind: 'file' | 'dir'; mtimeMs: number }[]> = {
    [MODS]: [{ name: 'MyMod', kind: 'dir', mtimeMs: NOW }, { name: 'OtherMod', kind: 'dir', mtimeMs: NOW }],
  }
  on('session.cwd', () => ({ value: `${MOD}/zonekit` }))
  on('clock.now', () => ({ value: NOW }))
  on('env.get', (_, e) => ({ value: e.name === 'LOCALAPPDATA' ? 'C:/Local' : undefined }))
  on('fs.exists', (_, e) => ({ value: norm(e.path) in files || norm(e.path) in dirs }))
  on('fs.read', (_, e) => {
    const p = norm(e.path)
    if (p in seen.written) return { value: seen.written[p] }
    if (!(p in files)) throw missing()
    return { value: files[p] }
  })
  on('fs.write', (_, e) => {
    const p = norm(e.path)
    seen.written[p] = e.text
    const dir = p.slice(0, p.lastIndexOf('/'))
    dirs[dir] = [...(dirs[dir] ?? []).filter(x => x.name !== p.slice(dir.length + 1)), { name: p.slice(dir.length + 1), kind: 'file', mtimeMs: NOW }]
    return { value: undefined }
  })
  on('fs.list', (_, e) => {
    const list = dirs[norm(e.path)]
    if (!list) throw missing()
    return { value: list.map(x => ({ ...x, size: 1, isLink: false })) }
  })
  on('fs.stat', () => ({ value: { kind: 'file', size: 1, mtimeMs: NOW, isLink: false } }))
  on('store.get', (_, e) => ({ value: seen.store[e.key] }))
  on('store.set', (_, e) => {
    seen.store[e.key] = e.value
    return { value: undefined }
  })
  on('prompt.submit', (_, e) => {
    seen.prompts.push(e.text)
    return { text: e.text }
  })
  on('ui.toast', (_, e) => {
    seen.toasts.push(e.text)
    return { value: undefined }
  })
  on('process.run', (_, e) => {
    seen.runs.push([...e.argv])
    return { value: { exitCode: 0, stdout, stderr: '' } }
  })
  return seen
}

test('the Quest designer belongs to a mod, builds stages and characters, saves and sends', async ($, on) => {
  const seen = fakePc(on)
  const ui = await $.ui.mount({ ...pane('zonecraft-quest', 'Quest designer'), surface: 'desktop' })

  await ui.press({ key: 'send' })
  expect(seen.prompts).toEqual([])
  expect(seen.toasts.at(-1)).toContain('a title')

  await ui.input({ key: 'f:title', text: 'The Lost Courier' })
  await ui.input({ key: 'f:summary', text: 'Find the courier who never came back.' })
  await ui.select({ key: 'p:region', value: 'Garbage' })
  await ui.select({ key: 'pc:faction', value: 'Duty' })
  await ui.input({ key: 'pc:name:0', text: 'Courier Petro' })
  await ui.select({ key: 'ps:kind', value: 'Find (search area)' })
  await ui.input({ key: 'ps:text:0', text: 'Search the tunnels' })
  await ui.select({ key: 'ps:kind', value: 'Talk to' })
  await ui.input({ key: 'ps:text:1', text: 'Bring the news back' })
  await ui.press({ key: 's:1:up' })
  await ui.press({ key: 'rewards:offer:0' })

  await ui.press({ key: 'send' })
  expect(seen.prompts).toHaveLength(1)
  const sent = seen.prompts[0]
  expect(sent).toContain(`my mod MyMod (${MOD})`)
  expect(sent).toContain('Quest SID: MM_TheLostCourier')
  expect(sent).toContain('Where: Garbage')
  expect(sent).toContain('Courier Petro (Quest giver, Duty')
  expect(sent).toContain('1. [Talk to] Bring the news back')
  expect(sent).toContain('2. [Find (search area)] Search the tunnels')
  expect(sent).toContain('- Money (coupons)')
  expect(sent).toContain('knowledge/quests.md')
  expect(Object.keys(seen.written)).toContain(`${MOD}/zonekit/quests/MM_TheLostCourier.json`)
  expect(seen.store[`quest-draft:${MOD.toLowerCase()}`]).toBeDefined()

  // another mod has its own (empty) draft; coming back finds this one
  await ui.select({ key: 'mod', value: OTHER })
  expect((await ui.find({ type: 'Text', text: /^Still needed/ }))?.text).toContain('a title')
  await ui.select({ key: 'mod', value: MOD })
  expect(await ui.find({ key: 'load:MM_TheLostCourier' })).toBeDefined()
  await ui.unmount()
})

test('the Conflicts panel scans your mods and shows each winner', async ($, on) => {
  const report = {
    atMs: NOW, sources: ['yours: MyMod', 'installed'],
    mods: [{ name: 'MyMod', files: 3, order: 103, isYours: true, source: 'yours: MyMod' },
      { name: 'BigHud', files: 9, order: 203, isYours: false, source: 'installed' }],
    conflicts: [
      { kind: 'asset', what: 'stalker2/content/ui/w_gamehud', mods: [{ name: 'BigHud', file: 'BigHud_1_P.pak', order: 203 },
        { name: 'MyMod', file: 'zzzz_MyMod_P.pak', order: 103 }], verdict: 'risky', note: 'BigHud wins.', isYours: true },
      { kind: 'asset', what: 'stalker2/content/ui/w_map', mods: [{ name: 'BigHud', file: 'a', order: 1 },
        { name: 'MyMod', file: 'b', order: 1 }], verdict: 'same', note: 'Identical.', isYours: true },
    ],
    errors: [],
  }
  const seen = fakePc(on, JSON.stringify(report))
  const ui = await $.ui.mount({ ...pane('zonecraft-conflicts', 'Mod conflicts'), surface: 'desktop' })
  expect((await ui.find({ type: 'Text', text: /^No scan yet/ }))).toBeDefined()
  await ui.input({ key: 'collection', text: 'D:/Collections/Hardcore' })
  await ui.press({ key: 'scan' })
  const argv = seen.runs.at(-1)!
  expect(argv).toContain('--collection')
  expect(argv).toContain('D:/Collections/Hardcore')
  expect(argv.filter(a => a === '--yours')).toHaveLength(2)
  expect((await ui.find({ type: 'Text', text: /^wins:/ }))?.text).toBe('wins: BigHud')
  expect((await ui.find({ type: 'Text', text: /identically/ }))?.text).toContain('1 more')
  await ui.press({ key: 'ask:0' })
  expect(seen.prompts.at(-1)).toContain('winner BigHud')
  expect(seen.store['conflicts-report']).toBeDefined()
  await ui.unmount()
})

test('the Logs panel draws before the watcher has run', async ($, on) => {
  fakePc(on)
  const ui = await $.ui.mount({ ...pane('zonecraft-logs', 'zonecraft logs'), surface: 'desktop' })
  expect((await ui.find({ type: 'Text', text: /^Not started yet/ }))).toBeDefined()
  expect((await ui.find({ type: 'Text', text: /^None seen yet/ }))).toBeDefined()
  await ui.unmount()
})
