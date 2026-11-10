// /zonecraft-data: the Game data browser. Search the game's data (weapons, items, NPCs, quests, effects) through the
// index tools/data/gamedata.py builds, open an entry to see its values (own, inherited, or changed by the mod), edit
// values and add the patch to the mod picked at the top. Every lookup runs gamedata.py --json in a handler; drawing
// only reads the state.
import { atom, read, update } from 'claude-code'
import type { EngineInterface as Engine, On } from 'claude-code'

import type { DataEntry, DataField, DataHit, DataPatch, DataState, DataStatus } from '../types'
import { age, chooseMod, knownMods, readSettings, runJson } from './data'
import { action, ORANGE, RUST, scene, section, top } from './theme'

export const DATA_PANE = 'zonecraft-data'
const TOOL = 'mcp__zonecraft__game_data'
const SCRIPT = 'tools/data/gamedata.py'
const RECENT = 'data-recent'
const FAVS = 'data-favs'
const KEEP = 8
const ROWS_MAX = 150

const EMPTY: DataState = {
  modRoot: '', page: 'search', query: '', kind: '', hasMore: false, open: [], editing: '', edits: {}, busy: '',
  recent: [], favorites: [],
}
const data = atom({ plugin: 'zonecraft', key: 'data' } as const, EMPTY, { shape: 'data-1' })

export const KIND_FILTERS = [
  { value: '', label: 'Everything' }, { value: 'weapons', label: 'Weapons' }, { value: 'items', label: 'Items' },
  { value: 'npcs', label: 'NPCs' }, { value: 'quests', label: 'Quests' }, { value: 'effects', label: 'Effects' },
]

const strings = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [])

/** The paths of the structs a field sits in ("A.B.C" → "A", "A.B"). */
export function ancestors(path: string): string[] {
  const parts = path.split('.')
  return parts.slice(0, -1).map((_, i) => parts.slice(0, i + 1).join('.'))
}

/** The fields shown: those whose every enclosing struct is open. */
export function visibleFields(fields: readonly DataField[], open: readonly string[]): DataField[] {
  const isOpen = new Set(open)
  return fields.filter(f => ancestors(f.path).every(a => isOpen.has(a)))
}

/** gamedata.py's --set arguments for the pending edits. */
export function setArgs(edits: Record<string, string>): string[] {
  return Object.entries(edits).flatMap(([p, v]) => ['--set', `${p}=${v}`])
}

async function run<T>($: Engine, root: string, args: string[], timeoutMs = 60_000) {
  const settings = await readSettings($)
  return runJson<T>($, settings, SCRIPT, [...(root ? ['--mod-root', root] : []), '--json', ...args], timeoutMs)
}

const set = ($: Engine, patch: Partial<DataState>) => update($, data, cur => ({ ...cur, ...patch }))

async function busy<T>($: Engine, what: string, work: () => Promise<T>): Promise<T | undefined> {
  await set($, { busy: what, error: undefined })
  try {
    return await work()
  } finally {
    await update($, data, cur => ({ ...cur, busy: cur.busy === what ? '' : cur.busy }))
  }
}

async function loadStatus($: Engine, root: string) {
  await busy($, 'status', async () => {
    const r = await run<DataStatus>($, root, ['status'])
    await set($, r.value ? { status: r.value } : { error: r.error })
  })
}

async function search($: Engine, root: string, query: string, kind: string) {
  const q = query.trim()
  await set($, { query, kind, page: 'search' })
  if (!q) {
    await set($, { hits: undefined, hasMore: false })
    return
  }
  await busy($, 'search', async () => {
    const r = await run<{ results: DataHit[]; more: boolean }>($, root,
      ['search', q, '--limit', '25', ...(kind ? ['--kind', kind] : [])])
    await set($, r.value ? { hits: r.value.results, hasMore: r.value.more } : { error: r.error })
  })
}

async function openEntry($: Engine, root: string, key: string, keepEdits = false) {
  await busy($, 'find', async () => {
    const r = await run<DataEntry>($, root, ['find', key, '--depth', '4'])
    if (!r.value) {
      await set($, { error: r.error })
      return
    }
    const entry = r.value
    let recent: string[] = []
    await update($, data, cur => {
      recent = [entry.key, ...cur.recent.filter(k => k !== entry.key)].slice(0, KEEP)
      return {
        ...cur, entry, page: 'entry', recent, editing: '',
        open: keepEdits ? cur.open : [],
        edits: keepEdits ? cur.edits : {},
        preview: keepEdits ? cur.preview : undefined,
      }
    })
    await $.store.set(RECENT, recent)
  })
}

async function preview($: Engine, root: string) {
  const s = await read($, data)
  if (!s.entry || Object.keys(s.edits).length === 0) {
    await set($, { preview: undefined })
    return
  }
  await busy($, 'patch', async () => {
    const r = await run<DataPatch>($, root, ['patch', s.entry!.key, ...setArgs(s.edits)])
    await set($, r.value ? { preview: r.value } : { error: r.error })
  })
}

async function write($: Engine, root: string) {
  const s = await read($, data)
  if (!s.entry || !s.preview) return
  if (s.preview.warnings.length) {
    await $.ui.toast('Not added: a field is not on this entry. Fix it, or Send to Claude.')
    return
  }
  if (!s.preview.target) {
    await $.ui.toast('No mod Content folder found (in the kit or the mod folder): Send to Claude instead.')
    return
  }
  const done = await busy($, 'write', async () => {
    const r = await run<DataPatch>($, root, ['patch', s.entry!.key, ...setArgs(s.edits), '--write'])
    if (!r.value?.written) {
      await set($, { error: r.error ?? 'not written' })
      return undefined
    }
    return r.value
  })
  if (done) {
    await set($, { edits: {}, preview: undefined })
    await $.ui.toast(`Added to ${done.file}. Package the mod to try it in game.`)
    await openEntry($, root, s.entry.key)
  }
}

async function open($: Engine) {
  return $.ui.open({ id: DATA_PANE, title: 'Game data' })
}

/** Opening the panel: the mod to work on, and whether the index is there. */
async function prepare($: Engine) {
  const s = await read($, data)
  if (!s.recent.length || !s.favorites.length) {
    await set($, { recent: strings(await $.store.get(RECENT)), favorites: strings(await $.store.get(FAVS)) })
  }
  const settings = await readSettings($)
  const mods = await knownMods($, await $.session.cwd(), settings, strings(await $.store.get('mods-seen')))
  const last = await $.store.get('mod-picked')
  const current = chooseMod(mods, s.modRoot, typeof last === 'string' ? last : '')
  const root = current?.root ?? ''
  if (root !== s.modRoot) await set($, { modRoot: root })
  await loadStatus($, root)
}

export async function dataSessionStart($: Engine) {
  await $.command.register({
    name: 'zonecraft-data',
    description: 'Browse the game data: search weapons, items, NPCs, quests; see their values; change one for your mod',
  })
  await $.tool.register({
    name: 'game_data',
    description:
      'Opens the zonecraft Game data browser beside the chat: the user searches the game\'s data (weapons, items, ' +
      'NPCs, quests, effects) through the game data index, sees an entry\'s values (own, inherited, or changed by ' +
      'their mod), edits values and adds the patch to their mod. Optional "search" starts a search. Call it when the ' +
      'user wants to look up or change a game value themselves.',
    inputSchema: {
      type: 'object',
      properties: { search: { type: 'string', description: 'Text to search for, e.g. "AK74" or "vodka"' } },
      additionalProperties: false,
    },
  })
}

export function registerData(on: On) {
  on('command.run', { command: 'zonecraft-data' }, async $ => {
    const { isPlaced } = await open($)
    await prepare($)
    return { text: isPlaced ? 'Game data browser opened.' : 'Game data browser opened (shown where your app has room for panes).' }
  })

  on('tool.call', { tool: TOOL }, async ($, e) => {
    const input = (e.input ?? {}) as { search?: unknown }
    const { isPlaced } = await open($)
    await prepare($)
    if (typeof input.search === 'string' && input.search.trim()) {
      const s = await read($, data)
      await search($, s.modRoot, input.search, '')
    }
    return {
      result: isPlaced
        ? 'The Game data browser is open beside the chat.'
        : 'This app shows no panes right now; use tools/data/gamedata.py find/search instead.',
    }
  }).catch(() => ({ result: 'The Game data browser could not be opened; ask the user to type /zonecraft-data.' }))

  on('ui.render', { component: 'Pane', requestId: DATA_PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const els = { Box, Text, Button }
    const s = await read($, data)
    const now = await $.clock.now()
    const settings = await readSettings($)
    const mods = await knownMods($, await $.session.cwd(), settings, strings(await $.store.get('mods-seen')))
    const root = s.modRoot
    const hasFields = e.surface === 'terminal' || e.surface === 'desktop' || e.surface === 'vscode'
    const fieldsTable = hasFields ? $.ui.resolve({ ...e, surface: e.surface as 'terminal' | 'desktop' | 'vscode' }) : undefined
    const working = s.busy
      ? <Text color={ORANGE}>{({ status: 'Checking the index…', search: 'Searching…', find: 'Opening…', patch: 'Preparing the patch…', write: 'Adding to your mod…', build: 'Building the index (a few minutes)…' } as Record<string, string>)[s.busy] ?? 'Working…'}</Text>
      : null
    const failed = s.error ? <Text color={RUST} wrap="wrap">{s.error}</Text> : null

    // ── the index
    const st = s.status
    const buildIndex = async () => {
      await busy($, 'build', async () => {
        const r = await runJson<{ entries: number }>($, await readSettings($), SCRIPT, ['--json', 'build'], 600_000)
        if (r.error) await set($, { error: r.error })
        else await $.ui.toast(`Game data index built: ${(r.value?.entries ?? 0).toLocaleString('en-US')} entries.`)
      })
      await loadStatus($, root)
    }
    const indexLine = !st
      ? <Text dimColor>Index not checked yet.</Text>
      : !st.exists
        ? <Text color={RUST} wrap="wrap">No game data index on this PC yet. Build it once (needs the Zone Kit; a few minutes).</Text>
        : (
          <Box flexDirection="row" gap={1}>
            <Text color={st.stale ? RUST : 'success'}>{st.stale ? '!' : '✓'}</Text>
            <Text dimColor>{`Index built ${age(st.builtMs, now)} · ${(st.entries ?? 0).toLocaleString('en-US')} entries${st.stale ? ' · the Zone Kit changed since' : ''}`}</Text>
          </Box>
        )
    const indexRow = (
      <Box flexDirection="column" key="index">
        {indexLine}
        {st && (!st.exists || st.stale)
          ? <Box flexDirection="row">{action(els, 'build', st.exists ? 'Rebuild index' : 'Build index', () => void buildIndex())}</Box>
          : null}
        {st?.exists && !st.modContent && st.mod
          ? <Text dimColor wrap="wrap">{`${st.mod} has no Content folder in the kit yet: you can browse, and Send to Claude instead of adding.`}</Text>
          : null}
      </Box>
    )

    const pickMod = async (r: string) => {
      await set($, { modRoot: r, entry: undefined, edits: {}, preview: undefined, page: 'search' })
      await $.store.set('mod-picked', r)
      await loadStatus($, r)
      const cur = await read($, data)
      if (cur.query.trim()) await search($, r, cur.query, cur.kind)
    }
    const modPicker = mods.length > 1 && fieldsTable
      ? <fieldsTable.Select key="mod" label="Mod" value={root}
        options={mods.map(m => ({ value: m.root, label: m.isHere ? `${m.name} (this folder)` : m.name }))}
        onSelect={v => pickMod(v)} />
      : mods.length === 1 ? <Text dimColor>{`Changes go to ${mods[0].name}.`}</Text> : null

    const favs = new Set(s.favorites)
    const toggleFav = async (key: string) => {
      let next: string[] = []
      await update($, data, cur => {
        next = cur.favorites.includes(key) ? cur.favorites.filter(k => k !== key) : [key, ...cur.favorites].slice(0, 20)
        return { ...cur, favorites: next }
      })
      await $.store.set(FAVS, next)
    }

    // ── search page
    if (s.page === 'search' || !s.entry) {
      const searchBox = fieldsTable
        ? <fieldsTable.Input key="q" label="Search" placeholder="AK74, vodka, bloodsucker, a SID…" value={s.query} autoFocus
          submitLabel="search" onSubmit={v => search($, root, v, s.kind)} />
        : <Text dimColor>Search on your PC (type /zonecraft-data there).</Text>
      const filters = (
        <Box flexDirection="row" flexWrap="wrap" gap={1} key="kinds">
          {KIND_FILTERS.map(k => (
            <Button key={`kind:${k.value || 'all'}`} dimColor={s.kind !== k.value} onPress={() => search($, root, s.query, k.value)}>
              {s.kind === k.value ? <Text bold color={ORANGE}>{k.label}</Text> : k.label}
            </Button>
          ))}
        </Box>
      )
      const hit = (r: DataHit, i: number) => (
        <Box flexDirection="column" key={`hit:${i}`}>
          <Box flexDirection="row" gap={1}>
            <Button key={`open:${i}`} onPress={() => openEntry($, root, r.key)}><Text bold>{r.game ?? r.key}</Text></Button>
            {r.isMine ? <Text color={ORANGE}>patched by your mod</Text> : null}
            {favs.has(r.key) ? <Text color={ORANGE}>★</Text> : null}
          </Box>
          <Box paddingLeft={2}><Text dimColor wrap="truncate">{`${r.key} · ${r.file.split('/').pop()}${r.src === 'mod' ? ' · your mod' : r.src === 'dlc' ? ' · DLC' : ''}`}</Text></Box>
        </Box>
      )
      const hits = s.hits
      const results = hits === undefined
        ? null
        : section(els, 'results', hits.length ? `${hits.length}${s.hasMore ? '+' : ''} results` : 'No results', undefined,
          ...hits.map(hit),
          hits.length === 0 ? <Text dimColor>Try part of the name, or another filter.</Text> : null,
          s.hasMore ? <Text dimColor>More match: type more of the name to narrow it down.</Text> : null)
      const quick = (title: string, keys: string[], k: string) => keys.length
        ? section(els, k, title, undefined,
          <Box flexDirection="row" flexWrap="wrap" gap={1} key={`${k}:list`}>
            {keys.map((key, i) => <Button key={`${k}:${i}`} dimColor onPress={() => openEntry($, root, key)}>{key}</Button>)}
          </Box>)
        : null
      return (
        <Box flexDirection="column" gap={1}>
          {top(els, e.surface === 'terminal', scene($, e, 'stash', 'Clawd opening a stash: a medkit, ammo and an artifact'),
            section(els, 'data', 'Game data', 'Weapons, items, NPCs, quests and effects, as the game defines them.', indexRow, modPicker))}
          <Box flexDirection="column" key="search">{searchBox}{filters}{working}{failed}</Box>
          {results}
          {quick('Favourites', s.favorites, 'favs')}
          {quick('Recent', s.recent, 'recent')}
        </Box>
      )
    }

    // ── entry page
    const d = s.entry
    const visible = visibleFields(d.fields, s.open)
    const shown = visible.slice(0, ROWS_MAX)
    const toggle = (path: string) => update($, data, cur => ({
      ...cur, open: cur.open.includes(path) ? cur.open.filter(p => p !== path && !p.startsWith(`${path}.`)) : [...cur.open, path],
    }))
    const commit = async (path: string, value: string, original: string | null) => {
      await update($, data, cur => {
        const edits = { ...cur.edits }
        if (value.trim() === '' || value.trim() === original) delete edits[path]
        else edits[path] = value.trim()
        return { ...cur, edits, editing: '' }
      })
      await preview($, root)
    }
    const fieldRow = (f: DataField, i: number) => {
      const pad = 2 * f.depth
      if (f.isStruct) {
        const isOpen = s.open.includes(f.path)
        return (
          <Box flexDirection="row" gap={1} paddingLeft={pad} key={`f:${i}`}>
            <Button key={`toggle:${f.path}`} dimColor={f.origin === 'inherited'} onPress={() => toggle(f.path)}>
              {`${isOpen ? '▾' : '›'} ${f.key}`}
            </Button>
            <Text dimColor>{`${f.count ?? 0} ${f.count === 1 ? 'entry' : 'entries'}`}</Text>
            {f.origin === 'mine' ? <Text color={ORANGE}>your mod</Text> : null}
          </Box>
        )
      }
      const edited = s.edits[f.path]
      if (s.editing === f.path && fieldsTable) {
        return (
          <Box flexDirection="column" paddingLeft={pad} key={`f:${i}`}>
            <fieldsTable.Input key={`value:${f.path}`} label={f.key} value={edited ?? f.value ?? ''} autoFocus submitLabel="set"
              onSubmit={v => commit(f.path, v, f.value)} />
            <Box flexDirection="row" gap={1}>
              <Button key={`cancel:${f.path}`} dimColor onPress={() => set($, { editing: '' })}>Cancel</Button>
              {edited !== undefined
                ? <Button key={`undo:${f.path}`} dimColor onPress={() => commit(f.path, f.value ?? '', f.value)}>Undo change</Button>
                : null}
            </Box>
          </Box>
        )
      }
      const color = edited !== undefined || f.origin === 'mine' ? ORANGE : undefined
      return (
        <Box flexDirection="row" gap={1} paddingLeft={pad} key={`f:${i}`}>
          <Text dimColor>{f.key}</Text>
          <Button key={`edit:${f.path}`} dimColor={f.origin === 'inherited' && edited === undefined}
            onPress={() => set($, { editing: f.path })}>
            {edited !== undefined
              ? <Text color={ORANGE}>{`${f.value ?? ''} → ${edited}`}</Text>
              : <Text color={color} dimColor={f.origin === 'inherited'}>{f.value ?? '(removed)'}</Text>}
          </Button>
        </Box>
      )
    }

    const pending = Object.entries(s.edits)
    const p = s.preview
    const copyPatch = async (press: { surface?: string }) => {
      if (!p) return
      const done = await $.ui.copy({ text: p.text, surface: press.surface as never })
      await $.ui.toast(done.isCopied ? 'Patch copied.' : `Could not copy: ${done.reason ?? 'no clipboard'}`)
    }
    const askClaude = () => $.prompt.submit({
      text: [
        `In the zonecraft Game data browser I am changing ${d.key} (${d.file}:${d.line}) for my mod ${d.mod ?? ''}.`,
        ...(pending.length ? ['Changes:', ...pending.map(([k, v]) => `- ${k}: ${d.fields.find(f => f.path === k)?.value ?? '?'} → ${v}`)] : []),
        ...(p ? ['', 'The patch zonecraft made:', p.text, ...(p.warnings.length ? ['Warnings:', ...p.warnings.map(w => `- ${w}`)] : [])] : []),
        '',
        'Check it against the game data (knowledge/config-files.md), tell me what it changes in game and what else it ' +
          'affects (children, DLC copies), then add it to the mod if it is right.',
      ].join('\n'),
      asUser: true,
    })

    const header = (
      <Box flexDirection="column" key="head">
        <Box flexDirection="row" gap={1}>
          <Button key="back" dimColor onPress={() => set($, { page: 'search', editing: '' })}>‹ Back to results</Button>
          <Button key="fav" dimColor onPress={() => toggleFav(d.key)}>{favs.has(d.key) ? '★ Favourite' : '☆ Favourite'}</Button>
        </Box>
        <Text bold>{d.game ?? d.key}</Text>
        <Text dimColor wrap="truncate">{`${d.key} · ${d.file}:${d.line}${d.src === 'mod' ? ' · your mod' : ''}`}</Text>
        {d.chain.length ? <Text dimColor wrap="wrap">{`Inherits ${d.chain.map(c => c.name).join(' ‹ ')}`}</Text> : null}
        {d.kids || d.hasDlc
          ? <Text color={RUST} wrap="wrap">{`! ${[d.kids ? `${d.kids} ${d.kids === 1 ? 'entry inherits' : 'entries inherit'} from this (they keep their own values)` : '', d.hasDlc ? 'DLC copies exist: they need the same change' : ''].filter(Boolean).join('; ')}`}</Text>
          : null}
        {d.mine.length ? <Text color={ORANGE} wrap="wrap">{`Your mod already changes it (${d.mine.map(m => m.split('/').pop()).join(', ')}).`}</Text> : null}
      </Box>
    )

    const values = section(els, 'values', 'Values', 'Dim = inherited · orange = your mod changes it · press a value to change it.',
      ...shown.map(fieldRow),
      visible.length > shown.length ? <Text dimColor>{`and ${visible.length - shown.length} more: close a group, or ask Claude.`}</Text> : null,
      d.isCut ? <Text dimColor>Very large entry: only the first fields are listed.</Text> : null,
      d.isRemoved ? <Text color={RUST}>This entry is removed (removenode).</Text> : null)

    const changes = pending.length
      ? section(els, 'pending', `Pending changes (${pending.length})`, undefined,
        ...pending.map(([path, v], i) => (
          <Box flexDirection="row" gap={1} key={`pending:${i}`}>
            <Text>{path}</Text>
            <Text color={ORANGE}>{`${d.fields.find(f => f.path === path)?.value ?? '?'} → ${v}`}</Text>
            <Button key={`drop:${i}`} dimColor onPress={async () => {
              await update($, data, cur => {
                const edits = { ...cur.edits }
                delete edits[path]
                return { ...cur, edits }
              })
              await preview($, root)
            }}>Remove</Button>
          </Box>
        )),
        p ? <Text key="patch-text">{p.text}</Text> : null,
        p ? <Text dimColor wrap="wrap">{`→ ${p.file}${p.exists ? ' (added to what is there)' : ' (new file)'}`}</Text> : null,
        ...(p?.warnings ?? []).map((w, i) => <Text key={`warn:${i}`} color={RUST} wrap="wrap">{`! ${w}`}</Text>),
        p && !p.warnings.length ? <Text color="success">{`✓ Checked: every field exists on ${d.key}`}</Text> : null,
        <Box flexDirection="row" gap={1} key="patch-actions">
          {action(els, 'write', 'Add to my mod', () => void write($, root))}
          <Button key="ask" onPress={() => void askClaude()}>Send to Claude</Button>
          <Button key="copy" dimColor onPress={copyPatch}>Copy patch</Button>
        </Box>)
      : null

    return (
      <Box flexDirection="column" gap={1}>
        {top(els, e.surface === 'terminal', scene($, e, 'trading', 'Clawd trading an artifact for coins across the counter'), header)}
        {working}
        {failed}
        {values}
        {changes}
        {!pending.length
          ? <Box flexDirection="row" gap={1}><Button key="ask-about" dimColor onPress={() => void askClaude()}>Ask Claude about this entry</Button></Box>
          : null}
      </Box>
    )
  })
}
