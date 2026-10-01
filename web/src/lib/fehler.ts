/** Fehlerantwort der API mit ihrem Statuscode. */
export class ApiFehler extends Error {
  constructor(meldung: string, readonly status: number) {
    super(meldung)
    this.name = 'ApiFehler'
  }
}

/** Wirft bei einer Fehlerantwort; FastAPI nennt den Grund im Feld «detail». */
export async function pruefe(antwort: Response): Promise<Response> {
  if (antwort.ok)
    return antwort
  let grund = `${antwort.status} ${antwort.statusText}`.trim()
  try {
    const body: unknown = await antwort.json()
    const detail = (body as { detail?: unknown }).detail
    if (typeof detail === 'string')
      grund = detail
  }
  catch {
    // kein JSON: Statuszeile reicht
  }
  throw new ApiFehler(grund, antwort.status)
}

export function meldung(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

/** 429: eine Grenze der öffentlichen Demo ist erreicht. Das ist kein Defekt und wird als Hinweis gezeigt. */
export function istGrenze(e: unknown): boolean {
  return e instanceof ApiFehler && e.status === 429
}
