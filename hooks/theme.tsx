// The look the zonecraft panels share: Zone orange for headings and the main action (the PDA's colors), the crab's
// scene at the top right, and one spacing rule (a blank line between sections, none inside one).
import type { ElementTable, EngineInterface as Engine, RenderNode } from 'claude-code'

import type { SceneName } from './art'
import { SCENES, sceneCells, svgOf } from './art'

/** Zone orange: headings, the main action, highlights. Reads on light and dark panels alike. */
export const ORANGE = '#e8772e'
/** Rust, for a warning that is not an error (a stale test copy). */
export const RUST = '#c2410c'

type Els = Pick<ElementTable, 'Box' | 'Text' | 'Button'>
type RenderArg = Parameters<Engine['ui']['resolve']>[0]

/** A section: an orange heading in the PDA's capitals, an optional dim hint, then its body. */
export function section(els: Els, key: string, title: string, hint: string | undefined, ...body: RenderNode[]) {
  const { Box, Text } = els
  return (
    <Box flexDirection="column" key={key}>
      <Text bold color={ORANGE}>{title.toUpperCase()}</Text>
      {hint ? <Text dimColor>{hint}</Text> : null}
      {body}
    </Box>
  )
}

/** The main action of a panel: a plain button with its label in Zone orange (a primary button would take the
 * app's own accent, blue on the desktop). */
export function action(els: Els, key: string, label: string, onPress: (e: { surface?: string }) => void) {
  const { Button, Text } = els
  return <Button key={key} onPress={onPress}><Text bold color={ORANGE}>{label}</Text></Button>
}

/** One of Clawd's scenes, animated where the surface draws SVG, half-block cells in a terminal; nothing elsewhere.
 * `alt` says what it shows, for a reader that cannot see it. */
export function scene($: Engine, e: RenderArg, name: SceneName, alt: string) {
  const art = SCENES[name]
  if (e.surface === 'desktop' || e.surface === 'mobile' || e.surface === 'vscode') {
    const { Svg } = $.ui.resolve({ ...e, surface: e.surface })
    return <Svg source={svgOf(name)} alt={alt} width={art.w * 2} height={art.h * 2} />
  }
  if (e.surface === 'terminal') {
    const { Raster } = $.ui.resolve({ ...e, surface: e.surface })
    return <Raster key={`scene:${name}`} {...sceneCells(art)} />
  }
  return null
}

/** The top of a panel: its first section at the left and the scene at the top right; in a terminal, whose cells are
 * wide, the scene takes its own row above. */
export function top(els: Els, isTerminal: boolean, art: RenderNode, first: RenderNode) {
  const { Box } = els
  if (isTerminal) {
    return [
      <Box flexDirection="row" justifyContent="flex-end" key="scene">{art}</Box>,
      first,
    ]
  }
  return (
    <Box flexDirection="row" justifyContent="space-between" alignItems="flex-start" gap={2} key="top">
      <Box flexDirection="column" flexShrink={1}>{first}</Box>
      <Box flexShrink={0}>{art}</Box>
    </Box>
  )
}

