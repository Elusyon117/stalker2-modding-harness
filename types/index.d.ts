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

/** What the New mod form holds while it is being filled in. */
export type NewModDraft = {
  name: string
  idea: string
  features: string[]
  details: string[]
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

declare module 'claude-code' {
  interface PluginState {
    zonecraft: {
      /** Bumped after file-changing tool calls and on Refresh, so the panel redraws. */
      tick: Shaped<number>
      /** The paste last copied, and when, for the "copied" mark. */
      copied: Shaped<{ path: string; atMs: number }>
      /** The mod folder picked in the panel this session; '' for none (the session's own mod is shown). */
      tracked: Shaped<string>
      /** The New mod form as filled in so far (also kept in $.store, so a new session finds it). */
      draft: Shaped<NewModDraft>
    }
  }
}
