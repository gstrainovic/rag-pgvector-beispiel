/** Zugriff auf die FastAPI unter /api, inklusive SSE-Stream für Fragen. */

export interface Dokument {
  id: number
  titel: string
  anzahl_absaetze: number
  erstellt?: string
}

export interface Quelle {
  titel: string
  absatz: string
  score: number
}

export interface Info {
  llm_modell: string
  llm_basis_url: string
  embedder: string
  anzahl_dokumente: number
}

export type FrageEvent
  = | { typ: 'quellen', quellen: Quelle[] }
    | { typ: 'token', text: string }
    | { typ: 'fehler', meldung: string }
    | { typ: 'ende' }

const BASIS = '/api'

async function pruefe(r: Response): Promise<Response> {
  if (r.ok)
    return r
  let detail = `${r.status} ${r.statusText}`
  try {
    const body = await r.json()
    if (typeof body.detail === 'string')
      detail = body.detail
  }
  catch {}
  throw new Error(detail)
}

export async function holeInfo(): Promise<Info> {
  return (await pruefe(await fetch(`${BASIS}/info`))).json()
}

export async function holeDokumente(): Promise<Dokument[]> {
  return (await pruefe(await fetch(`${BASIS}/dokumente`))).json()
}

export async function ladeHoch(dateien: File[]): Promise<Dokument[]> {
  const form = new FormData()
  for (const d of dateien)
    form.append('dateien', d, d.name)
  return (await pruefe(await fetch(`${BASIS}/dokumente/upload`, { method: 'POST', body: form }))).json()
}

export async function loesche(id: number): Promise<void> {
  await pruefe(await fetch(`${BASIS}/dokumente/${id}`, { method: 'DELETE' }))
}

export async function ladeBeispiele(): Promise<Dokument[]> {
  return (await pruefe(await fetch(`${BASIS}/beispiele`, { method: 'POST' }))).json()
}

/**
 * Zerlegt einen SSE-Textstrom in Ereignisse. Der Puffer hält unvollständige Blöcke zurück,
 * weil ein Netzwerk-Chunk mitten in einer Zeile enden kann.
 */
export function* sseEvents(puffer: { rest: string }, chunk: string): Generator<FrageEvent> {
  puffer.rest += chunk
  let idx: number
  // eslint-disable-next-line no-cond-assign
  while ((idx = puffer.rest.indexOf('\n\n')) >= 0) {
    const block = puffer.rest.slice(0, idx)
    puffer.rest = puffer.rest.slice(idx + 2)
    let event = 'message'
    let daten = ''
    for (const zeile of block.split('\n')) {
      if (zeile.startsWith('event:'))
        event = zeile.slice(6).trim()
      else if (zeile.startsWith('data:'))
        daten += zeile.slice(5).trim()
    }
    const d = daten ? JSON.parse(daten) : {}
    if (event === 'quellen')
      yield { typ: 'quellen', quellen: d as Quelle[] }
    else if (event === 'token')
      yield { typ: 'token', text: String(d.text ?? '') }
    else if (event === 'fehler')
      yield { typ: 'fehler', meldung: String(d.meldung ?? 'Unbekannter Fehler') }
    else if (event === 'ende')
      yield { typ: 'ende' }
  }
}

export async function frage(text: string, aufEvent: (e: FrageEvent) => void, k = 4): Promise<void> {
  const r = await pruefe(await fetch(`${BASIS}/frage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ frage: text, k }),
  }))
  const reader = r.body!.getReader()
  const decoder = new TextDecoder()
  const puffer = { rest: '' }
  for (;;) {
    const { value, done } = await reader.read()
    if (done)
      break
    for (const e of sseEvents(puffer, decoder.decode(value, { stream: true })))
      aufEvent(e)
  }
}
