import { refresh } from 'next/cache'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { dokumentLoeschen } from './aktionen'

vi.mock('next/cache', () => ({ refresh: vi.fn() }))
vi.mock('next/headers', () => ({
  cookies: async () => ({ toString: () => 'rag_sitzung=abc123' }),
}))

let fetchMock: ReturnType<typeof vi.fn<typeof fetch>>

beforeEach(() => {
  vi.stubEnv('API_URL', 'http://api:8000')
  fetchMock = vi.fn<typeof fetch>()
  vi.stubGlobal('fetch', fetchMock)
  vi.mocked(refresh).mockClear()
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

describe('Server-Aktion dokumentLoeschen', () => {
  it('ruft DELETE mit dem Sitzungs-Cookie des Besuchers auf und frischt die Seite auf', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))
    expect(await dokumentLoeschen(7)).toEqual({ ok: true, wert: null })
    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toBe('http://api:8000/api/dokumente/7')
    expect(init?.method).toBe('DELETE')
    expect(new Headers(init?.headers).get('cookie')).toBe('rag_sitzung=abc123')
    expect(refresh).toHaveBeenCalledTimes(1)
  })

  it('gibt die Fehlermeldung der API zurück, statt zu werfen', async () => {
    fetchMock.mockResolvedValueOnce(Response.json({ detail: 'Beispieldokumente lassen sich nicht löschen' }, { status: 403 }))
    expect(await dokumentLoeschen(1)).toEqual({ ok: false, fehler: 'Beispieldokumente lassen sich nicht löschen' })
    fetchMock.mockRejectedValueOnce(new TypeError('fetch failed'))
    expect(await dokumentLoeschen(7)).toEqual({ ok: false, fehler: 'API nicht erreichbar: fetch failed' })
    expect(refresh).not.toHaveBeenCalled()
  })

  it('lehnt eine ID ab, die keine positive Ganzzahl ist', async () => {
    expect(await dokumentLoeschen(Number.NaN)).toEqual({ ok: false, fehler: 'Ungültige Dokument-ID' })
    expect(await dokumentLoeschen('7/../../x' as unknown as number)).toEqual({ ok: false, fehler: 'Ungültige Dokument-ID' })
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
