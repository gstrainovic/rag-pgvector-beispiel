import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { sseAntwort } from '@/test/daten'
import { DELETE, GET, POST } from './route'

let fetchMock: ReturnType<typeof vi.fn<typeof fetch>>

beforeEach(() => {
  vi.stubEnv('API_URL', 'http://api:8000')
  fetchMock = vi.fn<typeof fetch>(async () => Response.json({ ok: true }))
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

function ziel(): { url: string, init: RequestInit & { duplex?: string } } {
  const [url, init] = fetchMock.mock.calls[0]!
  return { url: String(url), init: init ?? {} }
}

describe('Weiterleitung /api/* an die FastAPI', () => {
  it('reicht GET mit Pfad und Suchparametern an API_URL weiter', async () => {
    const antwort = await GET(new Request('http://localhost:3000/api/suche?q=Nachtruhe&k=2'))
    expect(ziel().url).toBe('http://api:8000/api/suche?q=Nachtruhe&k=2')
    expect(ziel().init.method).toBe('GET')
    expect(ziel().init.cache).toBe('no-store')
    expect(await antwort.json()).toEqual({ ok: true })
  })

  it('behält kodierte Dateinamen im Pfad', async () => {
    await GET(new Request('http://localhost:3000/api/beispiele/Hausordnung%20Sonnenhof.pdf'))
    expect(ziel().url).toBe('http://api:8000/api/beispiele/Hausordnung%20Sonnenhof.pdf')
  })

  it('reicht den Anfragekörper als Strom durch, ohne Host- und Längen-Header', async () => {
    const anfrage = new Request('http://localhost:3000/api/frage', {
      method: 'POST',
      // «Expect: 100-continue» schickt curl bei grossen Uploads; fetch in Node lehnt den Header ab
      headers: { 'Content-Type': 'application/json', 'Host': 'rag.example', 'Content-Length': '17', 'Expect': '100-continue' },
      body: JSON.stringify({ frage: 'Was?' }),
    })
    await POST(anfrage)
    const { init } = ziel()
    expect(init.method).toBe('POST')
    expect(init.body).toBeInstanceOf(ReadableStream)
    expect(init.duplex).toBe('half')
    const headers = new Headers(init.headers)
    expect(headers.get('content-type')).toBe('application/json')
    expect(headers.has('host')).toBe(false)
    expect(headers.has('content-length')).toBe(false)
    expect(headers.has('expect')).toBe(false)
  })

  it('reicht Sitzungs-Cookie und Besucher-Adresse an die API und deren Set-Cookie an den Browser', async () => {
    const mitCookie = Response.json([])
    mitCookie.headers.append('Set-Cookie', 'rag_sitzung=neu123; HttpOnly; Max-Age=2592000; Path=/; SameSite=Lax')
    fetchMock.mockResolvedValueOnce(mitCookie)
    const antwort = await GET(new Request('http://localhost:3000/api/dokumente', {
      headers: { 'Cookie': 'rag_sitzung=abc123', 'X-Forwarded-For': '203.0.113.5', 'X-Forwarded-Proto': 'https' },
    }))
    const headers = new Headers(ziel().init.headers)
    expect(headers.get('cookie')).toBe('rag_sitzung=abc123')
    expect(headers.get('x-forwarded-for')).toBe('203.0.113.5')
    expect(headers.get('x-forwarded-proto')).toBe('https')
    expect(antwort.headers.getSetCookie()).toEqual(['rag_sitzung=neu123; HttpOnly; Max-Age=2592000; Path=/; SameSite=Lax'])
  })

  it('gibt den Antwortstrom ungepuffert mit Status und Headern zurück', async () => {
    const strom = sseAntwort(['event: token\ndata: {"text":"A"}\n\n'])
    strom.headers.set('X-Accel-Buffering', 'no')
    strom.headers.set('Cache-Control', 'no-cache')
    fetchMock.mockResolvedValueOnce(strom)
    const antwort = await POST(new Request('http://localhost:3000/api/frage', { method: 'POST', body: '{}' }))
    expect(antwort.body).toBe(strom.body)
    expect(antwort.headers.get('content-type')).toBe('text/event-stream')
    expect(antwort.headers.get('x-accel-buffering')).toBe('no')
    expect(antwort.headers.get('cache-control')).toBe('no-cache')
  })

  it('übernimmt Fehlerstatus und Download-Header, aber keine Transport-Header', async () => {
    fetchMock.mockResolvedValueOnce(new Response('%PDF-', {
      status: 200,
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename="a.pdf"',
        'Content-Encoding': 'gzip',
        'Content-Length': '5',
        'Connection': 'keep-alive',
      },
    }))
    const download = await GET(new Request('http://localhost:3000/api/beispiele/a.pdf'))
    expect(download.headers.get('content-disposition')).toBe('attachment; filename="a.pdf"')
    expect(download.headers.has('content-encoding')).toBe(false)
    expect(download.headers.has('content-length')).toBe(false)
    expect(download.headers.has('connection')).toBe(false)

    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))
    expect((await DELETE(new Request('http://localhost:3000/api/dokumente/7', { method: 'DELETE' }))).status).toBe(204)
    fetchMock.mockResolvedValueOnce(Response.json({ detail: 'Dokument nicht gefunden' }, { status: 404 }))
    expect((await DELETE(new Request('http://localhost:3000/api/dokumente/7', { method: 'DELETE' }))).status).toBe(404)
  })

  it('verlässt den Pfad /api nicht', async () => {
    for (const pfad of ['/api/%2E%2E/docs', '/api/..%2Fdocs/x', '/api//evil.example/x']) {
      fetchMock.mockClear()
      const antwort = await GET(new Request(`http://localhost:3000${pfad}`))
      const aufruf = fetchMock.mock.calls[0]
      if (aufruf) {
        const url = new URL(String(aufruf[0]))
        expect(url.origin).toBe('http://api:8000')
        expect(url.pathname.startsWith('/api/')).toBe(true)
      }
      else {
        expect(antwort.status).toBe(400)
      }
    }
  })

  it('meldet 502 mit deutscher Meldung, wenn die API nicht erreichbar ist', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('fetch failed'))
    const antwort = await GET(new Request('http://localhost:3000/api/info'))
    expect(antwort.status).toBe(502)
    expect((await antwort.json()).detail).toMatch(/API nicht erreichbar/)
  })
})
