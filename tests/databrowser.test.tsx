import { expect, test } from 'claude-code/testing'

// The Game data browser against a fake index: search, filters, an entry's values, an edit, the patch, Add to my mod.
const NOW = Date.UTC(2026, 10, 9, 12, 0, 0)
const MOD = 'C:/mods/MyMod'
const PANE = {
  plugin: 'zonecraft',
  component: 'Pane',
  requestId: 'zonecraft-data',
  props: { title: 'Game data', isFocused: false, bodyColumns: 100, placement: 'dock', scroll: { offset: 0, bodyRows: 200 }, view: {} },
} as const

const HITS = {
  results: [
    { key: 'GunAK74_ST', name: 'GunAK74_ST', file: 'GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes.cfg', line: 10, src: 'game', kind: 'weapons', game: 'AK74 Kalashnikov', isMine: true },
    { key: 'Ammo_545', name: 'Ammo_545', file: 'GameLite/GameData/ItemPrototypes/AmmoPrototypes.cfg', line: 4, src: 'game', kind: 'weapons', game: null, isMine: false },
  ],
  more: false,
}
const field = (path: string, value: string | null, origin: string, isStruct = false, count?: number) => ({
  path, key: path.split('.').pop(), depth: path.split('.').length - 1, isStruct, count, value, origin,
})
const ENTRY = {
  key: 'GunAK74_ST', name: 'GunAK74_ST', sid: 'GunAK74_ST', file: 'GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes.cfg',
  line: 10, src: 'game', path: 'K:/x.cfg', kind: 'weapons', game: 'AK74 Kalashnikov', chain: [{ name: 'GunBase', file: 'f' }],
  kids: 4, hasDlc: true, mine: ['GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/MyMod.cfg'], mod: 'MyMod',
  patchFile: 'GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/MyMod.cfg', isRemoved: false, isCut: false,
  fields: [
    field('BaseDamage', '10', 'own'),
    field('Weight', '3.6', 'inherited'),
    field('Recoil', null, 'own', true, 2),
    field('Recoil.Up', '1.2', 'mine'),
    field('Recoil.Side', '0.4', 'inherited'),
  ],
}

type Seen = { runs: string[][]; prompts: string[]; toasts: string[]; store: Record<string, unknown> }

function fakePc(on: Parameters<Parameters<typeof test>[1]>[1]): Seen {
  const seen: Seen = { runs: [], prompts: [], toasts: [], store: {} }
  const files: Record<string, string> = {
    [`${MOD}/mod.json`]: '{"name": "MyMod", "short": "MM"}',
    'C:/Local/zonecraft/settings.json': '{}',
  }
  on('session.cwd', () => ({ value: MOD }))
  on('clock.now', () => ({ value: NOW }))
  on('env.get', (_, e) => ({ value: e.name === 'LOCALAPPDATA' ? 'C:/Local' : undefined }))
  on('fs.exists', (_, e) => ({ value: e.path.split('\\').join('/') in files }))
  on('fs.read', (_, e) => {
    const p = e.path.split('\\').join('/')
    if (!(p in files)) throw Object.assign(new Error('ENOENT'), { code: 'ENOENT' })
    return { value: files[p] }
  })
  on('fs.list', () => { throw Object.assign(new Error('ENOENT'), { code: 'ENOENT' }) })
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
    const argv = [...e.argv]
    seen.runs.push(argv)
    const cmd = argv[argv.indexOf('--json') + 1]
    const sets = argv.flatMap((a, i) => (a === '--set' ? [argv[i + 1]] : []))
    const out = cmd === 'search' ? (argv.includes('npcs') ? { results: [], more: false } : HITS)
      : cmd === 'find' ? ENTRY
        : cmd === 'patch' ? {
          key: 'GunAK74_ST', file: ENTRY.patchFile, target: `K:/Kit/${ENTRY.patchFile}`, exists: true,
          text: `GunAK74_ST : struct.begin {bpatch}\n   ${sets.join('\n   ').replace('=', ' = ')}\nstruct.end`,
          warnings: [], written: argv.includes('--write'),
        }
          : { exists: true, builtMs: NOW - 3 * 86_400_000, entries: 48210, stale: false, mod: 'MyMod', modContent: 'K:/c' }
    return { value: { exitCode: 0, stdout: JSON.stringify(out), stderr: '', isStdoutTruncated: false } }
  })
  return seen
}

test('search, open an entry, edit a value and add the patch to the mod', async ($, on) => {
  const seen = fakePc(on)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })

  await ui.input({ key: 'q', text: 'ak74' })
  expect(seen.runs.at(-1)).toEqual(expect.arrayContaining(['--json', 'search', 'ak74']))
  expect((await ui.find({ type: 'Text', text: /^2 RESULTS/ }))?.text).toBe('2 RESULTS')
  expect((await ui.find({ type: 'Text', text: /patched by your mod/ }))).toBeDefined()

  await ui.press({ key: 'kind:npcs' })
  expect(seen.runs.at(-1)).toEqual(expect.arrayContaining(['--kind', 'npcs']))
  expect((await ui.find({ type: 'Text', text: /^NO RESULTS/ }))?.text).toBe('NO RESULTS')
  await ui.press({ key: 'kind:all' })

  await ui.press({ key: 'open:0' })
  expect((await ui.find({ type: 'Text', text: /^AK74 Kalashnikov/ }))?.text).toBe('AK74 Kalashnikov')
  expect((await ui.find({ type: 'Text', text: /entries inherit/ }))?.text).toContain('DLC copies')
  expect(await ui.find({ key: 'edit:Recoil.Up' })).toBeUndefined() // inside a closed group
  await ui.press({ key: 'toggle:Recoil' })
  expect(await ui.find({ key: 'edit:Recoil.Up' })).toBeDefined()

  await ui.press({ key: 'edit:BaseDamage' })
  await ui.input({ key: 'value:BaseDamage', text: '14' })
  expect(seen.runs.at(-1)).toEqual(expect.arrayContaining(['patch', 'GunAK74_ST', '--set', 'BaseDamage=14']))
  expect((await ui.find({ type: 'Text', text: /^10 → 14/ }))?.text).toBe('10 → 14')
  expect((await ui.find({ type: 'Text', text: /Checked: every field/ }))).toBeDefined()

  await ui.press({ key: 'write' })
  expect(seen.runs.some(r => r.includes('--write') && r.includes('BaseDamage=14'))).toBe(true)
  expect(seen.toasts.at(-1)).toContain('Added to')
  expect(await ui.find({ key: 'write' })).toBeUndefined() // the change is in the mod now
  expect(seen.store['data-recent']).toEqual(['GunAK74_ST'])

  await ui.press({ key: 'fav' })
  expect(seen.store['data-favs']).toEqual(['GunAK74_ST'])
  await ui.press({ key: 'ask-about' })
  expect(seen.prompts.at(-1)).toContain('GunAK74_ST')
  await ui.press({ key: 'back' })
  expect(await ui.find({ key: 'favs:0' })).toBeDefined()
  await ui.unmount()
})
