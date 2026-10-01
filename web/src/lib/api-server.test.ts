import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { BEISPIELE, DOKUMENTE, INFO_MISTRAL } from '@/test/daten'
import { holeStartdaten } from './api-server'

let fetchMock: ReturnType<typeof vi.fn<typeof fetch>>

beforeEach(() => {
  vi.stubEnv('API_URL', 'http://api:8000')
  fetchMock = vi.fn<typeof fetch>(async (url) => {
    const pfad = new URL(String(url)).pathname
    if (pfad === '/api/info')
      return Response.json(INFO_MISTRAL)
    if (pfad === '/api/dokumente')
      return Response.json(DOKUMENTE)
    if (pfad === '/api/beispiele')
      return Response.json(BEISPIELE)
    return new Response(null, { status: 404 })
  })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

describe('holeStartdaten', () => {
  it('lädt Info, Dokumente und Beispiele von der internen API-Adresse, ohne Cache', async () => {
    expect(await holeStartdaten('')).toEqual({ info: INFO_MISTRAL, dokumente: DOKUMENTE, beispiele: BEISPIELE, fehler: null })
    expect(fetchMock.mock.calls.map(c => String(c[0])).sort()).toEqual([
      'http://api:8000/api/beispiele',
      'http://api:8000/api/dokumente',
      'http://api:8000/api/info',
    ])
    for (const [, init] of fetchMock.mock.calls)
      expect(init?.cache).toBe('no-store')
  })

  it('reicht das Sitzungs-Cookie des Besuchers weiter, damit die Liste seine Uploads enthält', async () => {
    await holeStartdaten('rag_sitzung=abc123')
    const dokumente = fetchMock.mock.calls.find(c => String(c[0]).endsWith('/api/dokumente'))!
    expect(new Headers(dokumente[1]?.headers).get('cookie')).toBe('rag_sitzung=abc123')
  })

  it('schickt ohne Cookie keinen leeren Cookie-Header', async () => {
    await holeStartdaten('')
    for (const [, init] of fetchMock.mock.calls)
      expect(new Headers(init?.headers).has('cookie')).toBe(false)
  })

  it('liefert leere Daten und eine Meldung, wenn die API nicht antwortet', async () => {
    fetchMock.mockRejectedValue(new TypeError('fetch failed'))
    expect(await holeStartdaten('')).toEqual({
      info: null,
      dokumente: [],
      beispiele: [],
      fehler: 'API nicht erreichbar: fetch failed',
    })
  })
})
