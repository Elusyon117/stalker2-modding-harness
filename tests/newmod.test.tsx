import { expect, test } from 'claude-code/testing'

// The New mod form: filling it in, the suggested details, the check before sending, and the brief Claude gets.
const PANE = {
  plugin: 'zonecraft',
  component: 'Pane',
  requestId: 'zonecraft-newmod',
  props: {
    title: 'New mod',
    isFocused: false,
    bodyColumns: 80,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 60 },
    view: {},
  },
} as const

type Seen = { prompts: string[]; toasts: string[]; store: Record<string, unknown> }

function fake(on: Parameters<Parameters<typeof test>[1]>[1]): Seen {
  const seen: Seen = { prompts: [], toasts: [], store: {} }
  on('clock.now', () => ({ value: Date.UTC(2026, 10, 8, 12) }))
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
  return seen
}

test('the form builds a brief and sends it to Claude', async ($, on) => {
  const seen = fake(on)
  for (const surface of ['terminal', 'desktop'] as const) {
    seen.prompts = []
    seen.toasts = []
    const ui = await $.ui.mount({ ...PANE, surface })
    expect(await ui.find({ type: surface === 'terminal' ? 'Raster' : 'Svg' })).toBeDefined()

    // nothing filled in: sending only says what is missing
    await ui.press({ key: 'send' })
    expect(seen.prompts).toEqual([])
    expect(seen.toasts.at(-1)).toContain('a name')

    await ui.input({ key: 'name', text: 'Immersive Campfires' })
    await ui.input({ key: 'idea', text: 'Sit down at any campfire to rest and heal.' })
    await ui.input({ key: 'feature:0', text: 'Sit with a key near a fire' })
    await ui.input({ key: 'feature:1', text: '  Time passes faster while sitting ' })
    expect((await ui.find({ type: 'Text', text: /^Time passes/ }))?.text).toBe('Time passes faster while sitting')
    await ui.press({ key: 'suggest:0' })
    expect(await ui.find({ key: 'suggest:0' })).toBeUndefined()
    await ui.input({ key: 'detail:1', text: 'Works with Campfire Saves' })

    await ui.press({ key: 'remove-features:0' })
    await ui.input({ key: 'feature:1', text: 'Sit with a key near a fire' })

    await ui.press({ key: 'send' })
    expect(seen.prompts).toHaveLength(1)
    const sent = seen.prompts[0]
    expect(sent).toContain('Name: Immersive Campfires')
    expect(sent).toContain('Main idea: Sit down at any campfire to rest and heal.')
    expect(sent).toContain('Features:\n- Time passes faster while sitting\n- Sit with a key near a fire')
    expect(sent).toContain('Details to check:\n- Keyboard and gamepad\n- Works with Campfire Saves')
    expect(sent).toContain('PLAN.md')
    expect((await ui.find({ type: 'Text', text: /^Sent to Claude/ }))?.text).toContain('just now')
    expect((seen.store['newmod-draft'] as { name: string }).name).toBe('Immersive Campfires')

    await ui.press({ key: 'clear' })
    expect((await ui.find({ type: 'Text', text: /^Still needed/ }))?.text).toContain('a name')
    await ui.unmount()
  }
})
