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
}

declare module 'claude-code' {
  interface PluginState {
    zonecraft: {
      /** Bumped after file-changing tool calls and on Refresh, so the panel redraws. */
      tick: Shaped<number>
      /** The paste last copied, and when, for the "copied" mark. */
      copied: Shaped<{ path: string; atMs: number }>
    }
  }
}
