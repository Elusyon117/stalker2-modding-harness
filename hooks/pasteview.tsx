// "Show nodes" on a Blueprint paste: the paste drawn the way the Zone Kit's graph editor will show it (from
// <paste>.view.json, which tools/blueprints/paste_view.py writes), one comment box at a time, with buttons to zoom
// and move, in the dashboard or in a pane of its own. The wires to draw by hand after pasting are listed too.
import { atom, read, update } from 'claude-code'
import type { ElementTable, EngineInterface as Engine, Register, RenderNode } from 'claude-code'

import type { NodesState, PasteViewFile, PasteViewPart } from '../types'
import { readSettings, runJson } from './data'
import { ORANGE } from './theme'

export const NODES_PANE = 'zonecraft-nodes'
export const NODES_NONE: NodesState = { path: '', box: 0, zoom: 0, x: 0, y: 0 }
export const nodes = atom({ plugin: 'zonecraft', key: 'nodes' } as const, NODES_NONE, { shape: 'nodes-1' })

/** The most an Svg element takes; a bigger picture is described instead. */
export const SVG_MAX = 131072
/** Zoom steps: how much of the graph a window shows across, in graph units (0: the whole box). */
const STEPS = [0, 1400, 700]
/** The zoom a new picture opens at: the closest step there is (clamped). */
export const ZOOM_CLOSE = 99

type Els = Pick<ElementTable, 'Box' | 'Text' | 'Button'>
type RenderArg = Parameters<Engine['ui']['resolve']>[0]
export type Win = { x: number; y: number; w: number; h: number }

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v))

/** The zoom steps a picture has: the whole box, then each window narrower than most of the picture. */
export function zoomSteps(v: { w: number }): number[] {
  return [0, ...STEPS.slice(1).filter(s => s < v.w * 0.85)]
}

/** The part of a picture a zoom step shows, moved into the picture. */
export function windowOf(v: { w: number; h: number }, zoom: number, x: number, y: number): Win {
  const steps = zoomSteps(v)
  const ww = steps[clamp(zoom, 0, steps.length - 1)]
  if (!ww) return { x: 0, y: 0, w: v.w, h: v.h }
  const wh = v.h <= ww * 0.9 ? v.h : Math.round(ww * 0.6)
  return { x: clamp(x, 0, v.w - ww), y: clamp(y, 0, v.h - wh), w: ww, h: wh }
}

/** The picture's SVG cut to a window: its size and viewBox rewritten, nothing else. */
export function windowSvg(v: PasteViewPart, win: Win): string {
  return v.svg.replace(/^<svg\b[^>]*>/, head => head
    .replace(/\swidth="[^"]*"/, ` width="${win.w}"`)
    .replace(/\sheight="[^"]*"/, ` height="${win.h}"`)
    .replace(/viewBox="[^"]*"/, `viewBox="${v.minx + win.x} ${v.miny + win.y} ${win.w} ${win.h}"`))
}

const viewPath = (paste: string) => `${paste.replace(/\.txt$/i, '')}.view.json`
export const pasteName = (paste: string) => paste.slice(paste.lastIndexOf('/') + 1).replace(/\.txt$/i, '')

async function readView($: Engine, paste: string): Promise<PasteViewFile | undefined> {
  try {
    const v = JSON.parse((await $.fs.read(viewPath(paste))).replace(/^﻿/, '')) as PasteViewFile
    return Array.isArray(v.views) ? v : undefined
  } catch {
    return undefined
  }
}

/** Shows a paste's nodes: draws its picture first when it is missing or older than the paste. */
export async function showNodes($: Engine, paste: string, isFresh: boolean): Promise<void> {
  let error: string | undefined
  if (!isFresh) {
    const r = await runJson<{ views: number }>($, await readSettings($), 'tools/blueprints/paste_view.py', [paste])
    error = r.error
  }
  await update($, nodes, () => ({ path: paste, box: 0, zoom: ZOOM_CLOSE, x: 0, y: 0, error }))
}

export async function hideNodes($: Engine): Promise<void> {
  await update($, nodes, () => NODES_NONE)
}

/** The nodes of the paste `s.path`: box tabs, the wires to draw by hand, the picture and its buttons. */
export async function nodesBody($: Engine, e: RenderArg, els: Els, s: NodesState, inPane: boolean): Promise<RenderNode> {
  const { Box, Text, Button } = els
  const k = inPane ? 'pane' : 'dash'
  if (s.error) return <Text color="error" wrap="wrap">{`Could not draw the nodes: ${s.error}`}</Text>
  const file = await readView($, s.path)
  if (!file || file.views.length === 0) {
    return <Text dimColor wrap="wrap">No picture of this paste yet. Run the paste check, or press Show nodes again.</Text>
  }
  const box = clamp(s.box, 0, file.views.length - 1)
  const v = file.views[box]
  const steps = zoomSteps(v)
  const zoom = clamp(s.zoom, 0, steps.length - 1)
  const win = windowOf(v, zoom, s.x, s.y)
  const set = (fn: (s: NodesState) => Partial<NodesState>) => update($, nodes, cur => ({ ...cur, ...fn(cur) }))
  const move = (dx: number, dy: number) => set(cur => {
    const w = windowOf(v, zoom, cur.x, cur.y)
    return { zoom, x: w.x + dx * Math.round(w.w * 0.6), y: w.y + dy * Math.round(w.h * 0.6) }
  })
  const zoomTo = (z: number) => set(cur => {          // keep the window's middle where it was
    const w = windowOf(v, zoom, cur.x, cur.y)
    const n = windowOf(v, z, 0, 0)
    return { zoom: z, x: Math.round(w.x + w.w / 2 - n.w / 2), y: Math.round(w.y + w.h / 2 - n.h / 2) }
  })

  const tabs = file.views.length > 1
    ? (
      <Box flexDirection="row" flexWrap="wrap" gap={1} key={`${k}:tabs`}>
        {file.views.map((p, i) => (
          <Button key={`${k}:tab:${i}`} onPress={() => set(() => ({ box: i, zoom: ZOOM_CLOSE, x: 0, y: 0 }))}>
            <Text bold={i === box} color={i === box ? ORANGE : undefined}>{p.title} <Text dimColor>{p.nodes}</Text></Text>
          </Button>
        ))}
      </Box>
    )
    : null
  const hand = file.hand.length
    ? (
      <Box flexDirection="column" key={`${k}:hand`}>
        <Box flexDirection="row" gap={1}>
          <Text color={ORANGE}>!</Text>
          <Text dimColor>{`wire by hand after pasting (${file.hand.length}):`}</Text>
        </Box>
        {file.hand.map((line, i) => (
          <Box paddingLeft={4} key={`${k}:hand:${i}`}><Text dimColor wrap="wrap">{line}</Text></Box>
        ))}
      </Box>
    )
    : null

  const surface = e.surface
  if (surface !== 'desktop' && surface !== 'mobile' && surface !== 'vscode') {
    return (
      <Box flexDirection="column" key={`${k}:nodes`}>
        {hand}
        <Text dimColor wrap="wrap">The picture of the nodes shows in the panel of the Claude desktop app or the editor.</Text>
      </Box>
    )
  }
  const { Svg } = $.ui.resolve({ ...e, surface })
  const source = windowSvg(v, win)
  const picture = source.length > SVG_MAX
    ? <Text dimColor wrap="wrap">{`${v.title} is too big to draw here (${v.nodes} nodes); smaller comment boxes draw.`}</Text>
    : <Svg source={source} alt={`${v.title}: ${v.nodes} nodes as they will look in the Zone Kit graph`} />
  const btn = (key: string, label: string, onPress: () => unknown, when = true) =>
    when ? <Button key={`${k}:${key}`} dimColor onPress={() => void onPress()}>{label}</Button> : null
  const canX = win.w < v.w
  const canY = win.h < v.h
  return (
    <Box flexDirection="column" key={`${k}:nodes`}>
      {tabs}
      {hand}
      {picture}
      <Box flexDirection="row" flexWrap="wrap" gap={1}>
        {btn('in', '+ Closer', () => zoomTo(zoom + 1), zoom < steps.length - 1)}
        {btn('out', '− Whole box', () => zoomTo(0), zoom > 0)}
        {btn('left', '◀', () => move(-1, 0), canX && win.x > 0)}
        {btn('right', '▶', () => move(1, 0), canX && win.x + win.w < v.w)}
        {btn('up', '▲', () => move(0, -1), canY && win.y > 0)}
        {btn('down', '▼', () => move(0, 1), canY && win.y + win.h < v.h)}
        {btn('pane', 'Own pane', () => $.ui.open({ id: NODES_PANE, title: `${pasteName(s.path)} nodes` }), !inPane)}
        {btn('hide', 'Hide nodes', () => hideNodes($), !inPane)}
      </Box>
      <Text dimColor wrap="wrap">Dashed orange: wire by hand. Dashed grey: goes on in another box.</Text>
    </Box>
  )
}

/** The pane of its own: the same picture, as wide as the pane. */
export const registerNodes: Register = on => {
  on('ui.render', { component: 'Pane', requestId: NODES_PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const s = await read($, nodes)
    if (!s.path) return <Text dimColor>Press Show nodes on a Blueprint paste in the zonecraft panel.</Text>
    return (
      <Box flexDirection="column" gap={1}>
        <Text bold color={ORANGE}>{`${pasteName(s.path).toUpperCase()} · NODES`}</Text>
        {await nodesBody($, e, { Box, Text, Button }, s, true)}
      </Box>
    )
  })
}
