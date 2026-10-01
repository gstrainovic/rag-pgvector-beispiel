import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { toast } from 'sonner'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { dokumentLoeschen } from '@/app/aktionen'
import { BEISPIELE, DOKUMENTE } from '@/test/daten'
import { DokumentBereich } from './dokument-bereich'

const refresh = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh }) }))
vi.mock('@/app/aktionen', () => ({ dokumentLoeschen: vi.fn() }))
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }))

let fetchMock: ReturnType<typeof vi.fn<typeof fetch>>

beforeEach(() => {
  fetchMock = vi.fn<typeof fetch>()
  vi.stubGlobal('fetch', fetchMock)
  refresh.mockClear()
  for (const f of [toast.success, toast.error, toast.info])
    vi.mocked(f).mockClear()
})

afterEach(() => vi.unstubAllGlobals())

describe('DokumentBereich', () => {
  it('hat keinen Knopf mehr zum Laden der Beispiele: sie sind immer da', () => {
    render(<DokumentBereich dokumente={DOKUMENTE} beispiele={BEISPIELE} />)
    expect(screen.queryByRole('button', { name: /Beispieldokumente laden/ })).not.toBeInTheDocument()
    expect(screen.getAllByText('Beispiel')).toHaveLength(2)
  })

  it('schickt hochgeladene Dateien als Multipart an /api/dokumente/upload und lädt die Liste neu', async () => {
    fetchMock.mockResolvedValueOnce(Response.json([{ id: 5, titel: 'notiz.txt', anzahl_absaetze: 3 }], { status: 201 }))
    render(<DokumentBereich dokumente={[]} beispiele={[]} />)
    const datei = new File(['Hallo'], 'notiz.txt', { type: 'text/plain' })
    await userEvent.upload(screen.getByLabelText('Dateien auswählen'), datei)
    await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1))
    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toBe('/api/dokumente/upload')
    expect(init?.method).toBe('POST')
    expect((init?.body as FormData).getAll('dateien')).toEqual([datei])
    expect(toast.success).toHaveBeenCalledWith('«notiz.txt» geladen, 3 Absätze.')
  })

  it('zeigt die Fehlermeldung der API, wenn der Upload abgelehnt wird', async () => {
    fetchMock.mockResolvedValueOnce(Response.json({ detail: 'Nur pdf, txt, md sind erlaubt, nicht «bild.png»' }, { status: 415 }))
    render(<DokumentBereich dokumente={[]} beispiele={[]} />)
    await userEvent.upload(screen.getByLabelText('Dateien auswählen'), new File(['x'], 'bild.png', { type: 'image/png' }), { applyAccept: false })
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Nur pdf, txt, md sind erlaubt, nicht «bild.png»'))
    expect(refresh).not.toHaveBeenCalled()
  })

  it('zeigt eine erreichte Grenze der Demo als Hinweis, nicht als Fehler', async () => {
    const grenze = 'Die Demo hält höchstens 25 eigene Dokumente pro Besucher. Löschen Sie ältere eigene Dokumente, um Platz zu schaffen.'
    fetchMock.mockResolvedValueOnce(Response.json({ detail: grenze }, { status: 429 }))
    render(<DokumentBereich dokumente={[]} beispiele={[]} />)
    await userEvent.upload(screen.getByLabelText('Dateien auswählen'), new File(['x'], 'a.txt', { type: 'text/plain' }))
    await waitFor(() => expect(toast.info).toHaveBeenCalledWith(grenze))
    expect(toast.error).not.toHaveBeenCalled()
  })

  it('löscht über die Server-Aktion und meldet einen Fehler als Toast', async () => {
    vi.mocked(dokumentLoeschen).mockResolvedValueOnce({ ok: true, wert: null }).mockResolvedValueOnce({ ok: false, fehler: 'Dokument nicht gefunden' })
    render(<DokumentBereich dokumente={DOKUMENTE} beispiele={[]} />)
    await userEvent.click(screen.getByRole('button', { name: '«wartung.pdf» löschen' }))
    await waitFor(() => expect(dokumentLoeschen).toHaveBeenCalledWith(7))
    expect(toast.error).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.getByRole('button', { name: '«wartung.pdf» löschen' })).toBeEnabled())
    await userEvent.click(screen.getByRole('button', { name: '«wartung.pdf» löschen' }))
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Dokument nicht gefunden'))
  })
})
