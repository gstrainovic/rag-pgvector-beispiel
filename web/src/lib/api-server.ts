/** Zugriff auf die FastAPI vom Next-Server aus (Server Components, Server-Aktionen, Route Handler). */

import 'server-only'
import { meldung, pruefe } from './fehler'
import type { BeispielDatei, Dokument, Info } from './typen'

/** Interne Adresse der FastAPI, zur Laufzeit gelesen: dasselbe Image läuft lokal und auf dem Server. */
export function apiUrl(): string {
  return process.env.API_URL ?? 'http://localhost:8000'
}

/**
 * Anfrage an die API im Namen des Besuchers: sein Cookie-Header geht mit, weil die API daran
 * die anonyme Sitzung erkennt und nur deren Dokumente zeigt.
 */
export async function apiAnfrage(pfad: string, cookies: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  if (cookies)
    headers.set('cookie', cookies)
  let antwort: Response
  try {
    antwort = await fetch(`${apiUrl()}${pfad}`, { cache: 'no-store', ...init, headers })
  }
  catch (e) {
    throw new Error(`API nicht erreichbar: ${meldung(e)}`)
  }
  return pruefe(antwort)
}

async function hole<T>(pfad: string, cookies: string): Promise<T> {
  return (await apiAnfrage(pfad, cookies)).json() as Promise<T>
}

export interface Startdaten {
  info: Info | null
  dokumente: Dokument[]
  beispiele: BeispielDatei[]
  fehler: string | null
}

/** Alles, was die Seite beim ersten Laden zeigt, in einem Rutsch und parallel. */
export async function holeStartdaten(cookies: string): Promise<Startdaten> {
  try {
    const [info, dokumente, beispiele] = await Promise.all([
      hole<Info>('/api/info', cookies),
      hole<Dokument[]>('/api/dokumente', cookies),
      hole<BeispielDatei[]>('/api/beispiele', cookies),
    ])
    return { info, dokumente, beispiele, fehler: null }
  }
  catch (e) {
    return { info: null, dokumente: [], beispiele: [], fehler: meldung(e) }
  }
}
