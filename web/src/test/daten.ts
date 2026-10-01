import type { BeispielDatei, Dokument, Info, Quelle } from '@/lib/typen'

export const INFO_MISTRAL: Info = {
  llm_modell: 'mistral-small-latest',
  llm_basis_url: 'https://api.mistral.ai/v1',
  embedder: 'mistral-embed',
  anzahl_dokumente: 3,
}

export const INFO_LOKAL: Info = {
  llm_modell: 'qwen3:4b-instruct-2507-q4_K_M',
  llm_basis_url: 'http://ollama:11434/v1',
  embedder: 'qwen3-embedding-cpu',
  anzahl_dokumente: 0,
}

/** Wie GET /api/dokumente: Beispiele zuerst, dann die Uploads des Besuchers. */
export const DOKUMENTE: Dokument[] = [
  { id: 1, titel: 'Hausordnung Sonnenhof', anzahl_absaetze: 10, erstellt: '2026-10-01T10:00:00Z', beispiel: true },
  { id: 2, titel: 'Wartungsanleitung Heizung HZ-40', anzahl_absaetze: 9, erstellt: '2026-10-01T10:00:00Z', beispiel: true },
  { id: 7, titel: 'wartung.pdf', anzahl_absaetze: 1, erstellt: '2026-10-01T10:05:00Z', beispiel: false },
]

export const QUELLEN: Quelle[] = [
  { titel: 'Hausordnung Sonnenhof', absatz: 'Die Nachtruhe dauert von 22 Uhr bis 6 Uhr.', score: 0.5912 },
  { titel: 'FAQ Schreinerei Holzwerk', absatz: 'Innerhalb von 30 Kilometern liefern wir kostenlos.', score: 0.3 },
]

export const BEISPIELE: BeispielDatei[] = ['FAQ Schreinerei Holzwerk', 'Hausordnung Sonnenhof', 'Wartungsanleitung Heizung HZ-40']
  .flatMap(titel => [
    { titel, dateiname: `${titel}.md`, groesse: 1800 },
    { titel, dateiname: `${titel}.pdf`, groesse: 2900 },
  ])

/** Antwort wie von POST /api/frage: der SSE-Text kommt in den angegebenen Stücken an. */
export function sseAntwort(stuecke: string[]): Response {
  const encoder = new TextEncoder()
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const s of stuecke)
        controller.enqueue(encoder.encode(s))
      controller.close()
    },
  })
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}
