/** Datenformen der FastAPI (app/main.py). */

export interface Dokument {
  id: number
  titel: string
  anzahl_absaetze: number
  erstellt?: string
  /** Beispieldokument: für alle sichtbar, nicht löschbar. Fehlt in der Antwort auf einen Upload. */
  beispiel?: boolean
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

export interface BeispielDatei {
  titel: string
  dateiname: string
  groesse: number
}

/** Ereignisse im SSE-Strom von POST /api/frage. */
export type FrageEvent
  = | { typ: 'quellen', quellen: Quelle[] }
    | { typ: 'token', text: string }
    // grenze: kein Defekt, sondern ein erreichtes Kontingent; die Oberfläche zeigt es als Hinweis
    | { typ: 'fehler', meldung: string, grenze?: boolean }
    | { typ: 'ende' }

/** Rückgabe der Server-Aktionen: Fehler als Wert, damit die Meldung beim Nutzer ankommt. */
export type Ergebnis<T> = { ok: true, wert: T } | { ok: false, fehler: string }
