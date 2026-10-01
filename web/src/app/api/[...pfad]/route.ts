/**
 * Reicht /api/* an die FastAPI weiter (Backend for Frontend): der Browser spricht nur mit
 * Next, die API bleibt im internen Netz. Anfrage- und Antwortkörper laufen als Strom durch,
 * darum kommen Uploads ohne Zwischenpuffer an und die SSE-Antwort von POST /api/frage Stück
 * für Stück beim Browser.
 *
 * Bewusst kein `rewrites` in next.config.ts: dessen Ziel wird beim Build festgeschrieben,
 * API_URL soll aber zur Laufzeit gelten.
 */

import { apiUrl } from '@/lib/api-server'

// Header, die nur für eine einzelne Verbindung gelten oder die fetch selbst setzt
const NICHT_WEITERGEBEN = ['connection', 'content-encoding', 'content-length', 'expect', 'host', 'keep-alive', 'transfer-encoding']

function ohneTransportHeader(quelle: Headers): Headers {
  const headers = new Headers(quelle)
  for (const name of NICHT_WEITERGEBEN)
    headers.delete(name)
  return headers
}

async function weiterleiten(anfrage: Request): Promise<Response> {
  const { pathname, search } = new URL(anfrage.url)
  const ziel = new URL(pathname + search, apiUrl())
  if (ziel.origin !== new URL(apiUrl()).origin || !ziel.pathname.startsWith('/api/'))
    return Response.json({ detail: 'Ungültiger Pfad' }, { status: 400 })

  const headers = ohneTransportHeader(anfrage.headers)
  headers.delete('accept-encoding') // fetch würde sonst entpacken, der Browser bekäme falsche Header
  const hatKoerper = anfrage.method !== 'GET' && anfrage.method !== 'HEAD' && anfrage.body !== null

  let antwort: Response
  try {
    antwort = await fetch(ziel, {
      method: anfrage.method,
      headers,
      body: hatKoerper ? anfrage.body : undefined,
      // Pflicht in Node, wenn der Körper ein Strom ist; fehlt noch in den DOM-Typen
      ...(hatKoerper ? { duplex: 'half' } : {}),
      cache: 'no-store',
      redirect: 'manual',
      signal: anfrage.signal,
    } as RequestInit)
  }
  catch (e) {
    console.error('Weiterleitung an die API fehlgeschlagen:', e) // samt Ursache (e.cause) ins Server-Log
    const grund = e instanceof Error ? e.message : String(e)
    return Response.json({ detail: `API nicht erreichbar: ${grund}` }, { status: 502 })
  }

  return new Response(antwort.body, {
    status: antwort.status,
    statusText: antwort.statusText,
    headers: ohneTransportHeader(antwort.headers),
  })
}

export { weiterleiten as DELETE, weiterleiten as GET, weiterleiten as POST }
