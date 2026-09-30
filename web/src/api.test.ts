import { describe, expect, it } from 'vitest'
import { sseEvents } from './api'

describe('sseEvents', () => {
  it('zerlegt vollständige Blöcke in Ereignisse', () => {
    const puffer = { rest: '' }
    const text = 'event: quellen\ndata: [{"titel":"A","absatz":"x","score":0.5}]\n\n'
      + 'event: token\ndata: {"text":"Hallo "}\n\n'
      + 'event: ende\ndata: {}\n\n'
    const events = [...sseEvents(puffer, text)]
    expect(events).toEqual([
      { typ: 'quellen', quellen: [{ titel: 'A', absatz: 'x', score: 0.5 }] },
      { typ: 'token', text: 'Hallo ' },
      { typ: 'ende' },
    ])
    expect(puffer.rest).toBe('')
  })

  it('hält unvollständige Blöcke zurück, bis der Rest kommt', () => {
    const puffer = { rest: '' }
    expect([...sseEvents(puffer, 'event: token\ndata: {"te')]).toEqual([])
    expect([...sseEvents(puffer, 'xt":"Welt"}\n\nevent: fehler\ndata: {"meldung":"kaputt"}\n\n')]).toEqual([
      { typ: 'token', text: 'Welt' },
      { typ: 'fehler', meldung: 'kaputt' },
    ])
  })
})
