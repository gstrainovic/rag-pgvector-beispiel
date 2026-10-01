import { describe, expect, it } from 'vitest'
import { sseAntwort } from '@/test/daten'
import type { FrageEvent } from './typen'
import { liesEvents, sseEvents } from './sse'

describe('sseEvents', () => {
  it('zerlegt vollständige Blöcke in Ereignisse', () => {
    const puffer = { rest: '' }
    const text = 'event: quellen\ndata: [{"titel":"A","absatz":"x","score":0.5}]\n\n'
      + 'event: token\ndata: {"text":"Hallo "}\n\n'
      + 'event: ende\ndata: {}\n\n'
    expect([...sseEvents(puffer, text)]).toEqual([
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

  it('kennzeichnet einen Fehler der Art «grenze» (Kontingent beim Modell-Anbieter)', () => {
    const text = 'event: fehler\ndata: {"meldung":"Monatskontingent erreicht","art":"grenze"}\n\n'
    expect([...sseEvents({ rest: '' }, text)]).toEqual([{ typ: 'fehler', meldung: 'Monatskontingent erreicht', grenze: true }])
  })

  it('behält Leerzeichen am Rand eines Tokens und überspringt unbekannte Ereignisse', () => {
    const puffer = { rest: '' }
    const text = 'event: ping\ndata: {}\n\nevent: token\ndata: {"text":" und "}\n\n'
    expect([...sseEvents(puffer, text)]).toEqual([{ typ: 'token', text: ' und ' }])
  })
})

describe('liesEvents', () => {
  it('liest einen Antwortstrom, auch wenn ein Umlaut über zwei Netzwerkstücke verteilt ist', async () => {
    const bytes = new TextEncoder().encode('event: token\ndata: {"text":"Grüsse"}\n\nevent: ende\ndata: {}\n\n')
    const mitte = bytes.indexOf(0xC3) + 1 // mitten im «ü» (zwei Bytes in UTF-8)
    const body = new ReadableStream<Uint8Array>({
      start(c) {
        c.enqueue(bytes.slice(0, mitte))
        c.enqueue(bytes.slice(mitte))
        c.close()
      },
    })
    const events: FrageEvent[] = []
    await liesEvents(body, e => events.push(e))
    expect(events).toEqual([{ typ: 'token', text: 'Grüsse' }, { typ: 'ende' }])
  })

  it('liefert die Ereignisse in der Reihenfolge des Stroms', async () => {
    const events: FrageEvent[] = []
    await liesEvents(sseAntwort(['event: quellen\ndata: []\n\nevent: tok', 'en\ndata: {"text":"A"}\n\n']).body!, e => events.push(e))
    expect(events.map(e => e.typ)).toEqual(['quellen', 'token'])
  })
})
