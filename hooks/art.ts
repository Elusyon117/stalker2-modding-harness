// The crab by its campfire, from the pixels in clawd.ts: an SVG that flickers for the desktop and mobile panes, and
// half-block cells for the terminal's.
import { FRAMES, H, PALETTE, W } from './clawd'

const color = (ch: string): string | undefined => (ch === '.' ? undefined : PALETTE[parseInt(ch, 32)])

/** Horizontal runs of one color, as SVG rects; `keep(x, y)` picks the pixels drawn. */
function rects(rows: readonly string[], keep: (x: number, y: number) => boolean): string {
  let out = ''
  for (let y = 0; y < rows.length; y++) {
    const row = rows[y]
    let x = 0
    while (x < row.length) {
      const fill = keep(x, y) ? color(row[x]) : undefined
      let end = x + 1
      if (fill) {
        while (end < row.length && keep(end, y) && row[end] === row[x]) end++
        out += `<rect x="${x}" y="${y}" width="${end - x}" height="1" fill="${fill}"/>`
      }
      x = end
    }
  }
  return out
}

/** The scene as one SVG on a transparent background: the pixels every frame shares drawn once, and each frame's
 * own pixels in a group shown in its turn (the first frame's too, so a pixel can go back to transparent). */
export function sceneSvg(stepMs = 160): string {
  const n = FRAMES.length
  const dur = `${(n * stepMs) / 1000}s`
  const same = (x: number, y: number) => FRAMES.every(f => f[y][x] === FRAMES[0][y][x])
  let body = rects(FRAMES[0], same)
  for (let k = 0; k < n; k++) {
    const values = Array.from({ length: n }, (_, i) => (i === k ? 'visible' : 'hidden')).join(';')
    body += `<g visibility="${k === 0 ? 'visible' : 'hidden'}"><animate attributeName="visibility" values="${values}" ` +
      `dur="${dur}" calcMode="discrete" repeatCount="indefinite"/>${rects(FRAMES[k], (x, y) => !same(x, y))}</g>`
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" shape-rendering="crispEdges">${body}</svg>`
}

const DEFAULT = 0x01000000
const rgb = (hex: string | undefined) => (hex ? parseInt(hex.slice(1), 16) : DEFAULT)

/** One frame as Raster cells: each terminal cell is two pixels stacked, an upper half block in the top one's color
 * over the bottom one's. */
export function sceneCells(step = 0): { columns: number; rows: number; cells: string } {
  const frame = FRAMES[step % FRAMES.length]
  const rows = Math.ceil(H / 2)
  const words = new Uint32Array(W * rows * 3)
  for (let r = 0; r < rows; r++) {
    for (let x = 0; x < W; x++) {
      const top = color(frame[2 * r][x])
      const bottom = 2 * r + 1 < H ? color(frame[2 * r + 1][x]) : undefined
      const at = (r * W + x) * 3
      if (top) words.set([0x2580, rgb(top), rgb(bottom)], at)          // ▀
      else if (bottom) words.set([0x2584, rgb(bottom), DEFAULT], at)  // ▄
      else words.set([0x20, DEFAULT, DEFAULT], at)
    }
  }
  return { columns: W, rows, cells: toBase64(new Uint8Array(words.buffer)) }
}

const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

function toBase64(bytes: Uint8Array): string {
  let out = ''
  for (let i = 0; i < bytes.length; i += 3) {
    const a = bytes[i]
    const b = i + 1 < bytes.length ? bytes[i + 1] : 0
    const c = i + 2 < bytes.length ? bytes[i + 2] : 0
    out += B64[a >> 2] + B64[((a & 3) << 4) | (b >> 4)]
    out += i + 1 < bytes.length ? B64[((b & 15) << 2) | (c >> 6)] : '='
    out += i + 2 < bytes.length ? B64[c & 63] : '='
  }
  return out
}
