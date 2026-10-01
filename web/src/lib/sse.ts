import type { FrageEvent, Quelle } from './typen'

/**
 * Zerlegt einen SSE-Textstrom in Ereignisse. Der Puffer hält unvollständige Blöcke zurück,
 * weil ein Netzwerkstück mitten in einer Zeile enden kann.
 */
export function* sseEvents(puffer: { rest: string }, stueck: string): Generator<FrageEvent> {
  puffer.rest += stueck
  for (let ende = puffer.rest.indexOf('\n\n'); ende >= 0; ende = puffer.rest.indexOf('\n\n')) {
    const block = puffer.rest.slice(0, ende)
    puffer.rest = puffer.rest.slice(ende + 2)
    let event = 'message'
    let daten = ''
    for (const zeile of block.split('\n')) {
      if (zeile.startsWith('event:'))
        event = zeile.slice(6).trim()
      else if (zeile.startsWith('data:'))
        daten += zeile.slice(5).trim()
    }
    const d: unknown = daten ? JSON.parse(daten) : {}
    const feld = (name: string) => (d as Record<string, unknown>)[name]
    if (event === 'quellen')
      yield { typ: 'quellen', quellen: d as Quelle[] }
    else if (event === 'token')
      yield { typ: 'token', text: String(feld('text') ?? '') }
    else if (event === 'fehler')
      yield { typ: 'fehler', meldung: String(feld('meldung') ?? 'Unbekannter Fehler'), ...(feld('art') === 'grenze' ? { grenze: true } : {}) }
    else if (event === 'ende')
      yield { typ: 'ende' }
  }
}

/** Liest einen Antwortkörper bis zum Ende und meldet jedes Ereignis, sobald es vollständig da ist. */
export async function liesEvents(body: ReadableStream<Uint8Array>, aufEvent: (e: FrageEvent) => void): Promise<void> {
  const reader = body.getReader()
  const decoder = new TextDecoder() // stream: true hält angeschnittene UTF-8-Zeichen zurück
  const puffer = { rest: '' }
  for (;;) {
    const { value, done } = await reader.read()
    if (done)
      break
    for (const e of sseEvents(puffer, decoder.decode(value, { stream: true })))
      aufEvent(e)
  }
}
