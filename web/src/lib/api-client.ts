/** Aufrufe aus dem Browser. /api/* reicht der Route Handler an die FastAPI weiter. */

import { pruefe } from './fehler'
import { liesEvents } from './sse'
import type { Dokument, FrageEvent } from './typen'

export async function ladeHoch(dateien: File[]): Promise<Dokument[]> {
  const form = new FormData()
  for (const d of dateien)
    form.append('dateien', d, d.name)
  const antwort = await pruefe(await fetch('/api/dokumente/upload', { method: 'POST', body: form }))
  return antwort.json() as Promise<Dokument[]>
}

/** Stellt eine Frage und meldet Quellen, Textstücke und Fehler, während die Antwort entsteht. */
export async function frage(text: string, aufEvent: (e: FrageEvent) => void, k = 4): Promise<void> {
  const antwort = await pruefe(await fetch('/api/frage', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ frage: text, k }),
  }))
  if (antwort.body)
    await liesEvents(antwort.body, aufEvent)
}
