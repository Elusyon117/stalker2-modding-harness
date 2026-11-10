export type Status = 'ok' | 'warn' | 'bad' | 'none'

/** One Blueprint paste file under <mod>/zonekit/paste, with what verify_paste reported for it. */
export type Paste = {
  path: string
  name: string
  mtimeMs: number
  nodes: number
  lint: Status
  lintText: string
  compare: Status
  compareText: string
}

/** A mod the panel can track: its folder (forward slashes) and its mod.json name. */
export type ModChoice = {
  root: string
  name: string
  /** The mod this session's folder is in. */
  isHere: boolean
}

/** One checklist line of a mod's PLAN.md (`- [ ] text` / `- [x] text`). */
export type PlanItem = {
  text: string
  isDone: boolean
}

/** How a mod's packaged files are copied and renamed into its Release Candidate folder (mod.json "release"). */
export type ReleaseNaming = {
  /** The folder, relative to the mod folder (or absolute). */
  folder: string
  /** Base name of the override files; {mod} is the plugin name. */
  override: string
  /** Base name of the new-content files; "{kit}" keeps the kit's own name. */
  newcontent: string
  /** Copy after every successful packaging. */
  auto: boolean
}

/** What the New mod form holds while it is being filled in. */
export type NewModDraft = {
  name: string
  idea: string
  features: string[]
  details: string[]
  release: ReleaseNaming
  /** When the brief was sent to Claude; 0 while it has not been. */
  sentAtMs: number
}

/** What the panel shows; read fresh from disk on each draw. */
export type Dashboard = {
  modRoot?: string
  modName?: string
  short?: string
  state?: string
  isLegacy: boolean
  kit?: string
  game?: string
  cookMs?: number
  testPakMs?: number
  testPakFiles: number
  checkpoints: number
  lastCheckpoint?: string
  pastes: Paste[]
  /** PLAN.md's "## Idea", first line. */
  idea?: string
  /** PLAN.md's "## Features" checklist. */
  features: PlanItem[]
  /** PLAN.md's "## Details to check" checklist. */
  details: PlanItem[]
}

/** The latest packaging zcwatch.py saw (the editor's Package Mod, cook_and_install.ps1, a Workshop upload). */
export type PackageInfo = {
  active?: boolean
  phase?: string
  mod?: string
  startedMs?: number
  endedMs?: number
  result?: 'ok' | 'failed'
  progress?: [number, number]
  errors?: string[]
  last?: string
  log?: string
  note?: string
}

/** The mod's release candidate copy (tools/build/release_candidate.py). */
export type RcInfo = {
  folder?: string
  files?: string[]
  copied?: number
  isNew?: boolean
  pending?: boolean
  error?: string
}

/** One log line worth showing. */
export type LogEvent = {
  kind: 'crash' | 'patch' | 'data' | 'text' | 'mod' | 'mount' | 'error'
  level: 'bad' | 'warn' | 'info'
  source: 'game' | 'kit'
  text: string
  atMs: number
}

/** A crash report with its known family, if any (tools/watch/crash_rules.json). */
export type CrashInfo = {
  atMs: number
  path: string
  message: string
  stack: string[]
  family: string
  advice: string
}

/** What the band and the Logs panel draw, refreshed every few seconds by the watcher. */
export type WatchState = {
  package: PackageInfo
  rc?: RcInfo
  isGameRunning: boolean
  isEditorRunning: boolean
  events: LogEvent[]
  crashes: CrashInfo[]
  lastPollMs: number
  error?: string
  /** The band is hidden for what happened before this time. */
  dismissedMs: number
  /** The "what to test" list is open in the band. */
  isTestOpen: boolean
}

/** One character of a quest. */
export type QuestCharacter = {
  name: string
  role: string
  faction: string
  /** A vanilla NPC SID to use, or '' for a new character. */
  sid: string
  behavior: string
  count: string
  notes: string
}

/** One stage (objective) of a quest. */
export type QuestStage = {
  kind: string
  text: string
  marker: string
  optional: boolean
}

/** What the Quest designer holds for one quest of one mod. */
export type QuestDraft = {
  modRoot: string
  sid: string
  title: string
  kind: string
  summary: string
  journal: string
  start: string
  startDetail: string
  region: string
  place: string
  characters: QuestCharacter[]
  stages: QuestStage[]
  dialogs: string[]
  items: string[]
  rewards: string[]
  success: string
  failure: string
  branches: string[]
  world: string[]
  rules: string[]
  audio: string[]
  languages: string
  notes: string
  /** The character and the stage being put together before they are added (their pickers' values). */
  pending: { character: QuestCharacter; stage: QuestStage }
  sentAtMs: number
  /** When it was last saved to <mod>/zonekit/quests/; 0 while it has not been. */
  savedAtMs: number
}

/** One conflict the conflict check found. */
export type Conflict = {
  /** asset (a package path) or cfg (a field of a prototype) */
  kind: 'asset' | 'cfg' | 'cfg-file'
  /** The asset path, or file › struct › field. */
  what: string
  /** Mods involved, the winner first. */
  mods: { name: string; file: string; order: number }[]
  verdict: 'same' | 'wins' | 'tie' | 'risky'
  note: string
  /** Whether a mod of yours is involved. */
  isYours: boolean
}

/** The last conflict scan. */
export type ConflictReport = {
  atMs: number
  sources: string[]
  mods: { name: string; files: number; order: number; isYours: boolean; source: string }[]
  conflicts: Conflict[]
  errors: string[]
}

/** gamedata.py --json status: the index on this PC. */
export type DataStatus = {
  exists: boolean
  kit?: string
  builtMs?: number
  entries?: number
  files?: number
  texts?: string
  stale?: boolean
  mod?: string | null
  modContent?: string | null
  modEntries?: number
}

/** One search result. */
export type DataHit = {
  key: string
  name: string
  file: string
  line: number
  src: string
  kind: string
  game: string | null
  isMine: boolean
}

/** One field of a resolved prototype; origin: its own value, inherited, or set by the mod's patch. */
export type DataField = {
  path: string
  key: string
  depth: number
  isStruct: boolean
  count?: number
  value: string | null
  origin: 'own' | 'inherited' | 'mine'
}

/** gamedata.py --json find. */
export type DataEntry = {
  key: string
  name: string
  sid: string | null
  file: string
  line: number
  src: string
  path: string
  kind: string
  game: string | null
  chain: { name: string; file: string }[]
  kids: number
  hasDlc: boolean
  mine: string[]
  mod: string | null
  patchFile: string
  isRemoved: boolean
  fields: DataField[]
  isCut: boolean
}

/** gamedata.py --json patch. */
export type DataPatch = {
  key: string
  file: string
  target: string | null
  text: string
  warnings: string[]
  exists: boolean
  written: boolean
}

/** What the Game data panel holds. */
export type DataState = {
  modRoot: string
  page: 'search' | 'entry'
  query: string
  kind: string
  status?: DataStatus
  hits?: DataHit[]
  hasMore: boolean
  entry?: DataEntry
  /** Struct paths opened in the entry's field list. */
  open: string[]
  /** The field being edited, '' for none. */
  editing: string
  /** Changes waiting to be written: field path → new value. */
  edits: Record<string, string>
  preview?: DataPatch
  /** What runs now: '', 'status', 'search', 'find', 'patch', 'write' or 'build'. */
  busy: string
  error?: string
  recent: string[]
  favorites: string[]
}

declare module 'claude-code' {
  interface PluginState {
    zonecraft: {
      /** Bumped after file-changing tool calls and on Refresh, so the panel redraws. */
      tick: Shaped<number>
      /** The paste last copied, and when, for the "copied" mark. */
      copied: Shaped<{ path: string; atMs: number }>
      /** The mod folder picked in the panel this session; '' for none (the session's own mod is shown). */
      tracked: Shaped<string>
      /** Which page the dashboard shows: every mod, one mod, or chosen from where the session is ('auto'). */
      view: Shaped<'auto' | 'mods' | 'mod'>
      /** The Game data panel: search, the open entry, pending edits. */
      data: Shaped<DataState>
      /** The New mod form as filled in so far (also kept in $.store, so a new session finds it). */
      draft: Shaped<NewModDraft>
      /** Packaging, logs and crashes, from tools/watch/zcwatch.py. */
      watch: Shaped<WatchState>
      /** The Quest designer's draft (also in $.store per mod). */
      quest: Shaped<QuestDraft>
      /** The conflict check's last report and whether a scan is running. */
      conflicts: Shaped<{ report?: ConflictReport; isScanning: boolean; collection: string; onlyYours: boolean }>
    }
  }
}
