import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { sseAntwort } from '@/test/daten'
import { ChatBereich } from './chat-bereich'

const STROM = [
  'event: quellen\ndata: [{"titel":"Hausordnung Sonnenhof","absatz":"Die Nachtruhe dauert von 22 Uhr bis 6 Uhr.","score":0.59}]\n\n',
  'event: token\ndata: {"text":"Die Nachtruhe dauert "}\n\nevent: tok',
  'en\ndata: {"text":"**von 22 Uhr bis 6 Uhr**."}\n\n',
  'event: ende\ndata: {}\n\n',
]

function mitFetch(antwort: () => Response | Promise<Response>) {
  const fetchMock = vi.fn<typeof fetch>(async () => antwort())
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => vi.unstubAllGlobals())

describe('ChatBereich', () => {
  it('schickt die Frage an /api/frage und zeigt die gestreamte Antwort als Markdown mit Quellen', async () => {
    const fetchMock = mitFetch(() => sseAntwort(STROM))
    render(<ChatBereich vorschlaege={[]} />)
    const feld = screen.getByRole('textbox', { name: 'Frage' })
    await userEvent.type(feld, 'Wann ist Nachtruhe?{Enter}')

    expect(fetchMock).toHaveBeenCalledWith('/api/frage', expect.objectContaining({ method: 'POST' }))
    expect(JSON.parse(String(fetchMock.mock.calls[0]![1]!.body))).toEqual({ frage: 'Wann ist Nachtruhe?', k: 4 })
    expect(feld).toHaveValue('')

    const antwort = await screen.findByText('von 22 Uhr bis 6 Uhr')
    expect(antwort.tagName).toBe('STRONG')
    const nachrichten = screen.getAllByRole('article')
    expect(nachrichten).toHaveLength(2)
    expect(nachrichten[0]).toHaveTextContent('Wann ist Nachtruhe?')
    expect(nachrichten[1]).toHaveTextContent('Die Nachtruhe dauert von 22 Uhr bis 6 Uhr.')
    expect(within(nachrichten[1]!).getByRole('button', { name: '1 Quelle' })).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByText('Antwort wird erzeugt …')).not.toBeInTheDocument())
  })

  it('entfernt Skripte und Ereignis-Attribute aus der Antwort', async () => {
    mitFetch(() => sseAntwort([
      'event: token\ndata: {"text":"Hallo <img src=x onerror=\\"alert(1)\\"> <script>alert(1)</script>[klick](javascript:alert(1))"}\n\nevent: ende\ndata: {}\n\n',
    ]))
    const { container } = render(<ChatBereich vorschlaege={[]} />)
    await userEvent.type(screen.getByRole('textbox', { name: 'Frage' }), 'Egal{Enter}')
    await screen.findByText(/Hallo/)
    expect(container.innerHTML).not.toContain('onerror')
    expect(container.innerHTML).not.toContain('<script')
    expect(container.innerHTML).not.toContain('javascript:')
  })

  it('sendet mit Enter, Shift+Enter fügt eine Zeile ein, ein leeres Feld sendet nichts', async () => {
    const fetchMock = mitFetch(() => sseAntwort(STROM))
    render(<ChatBereich vorschlaege={[]} />)
    const feld = screen.getByRole('textbox', { name: 'Frage' })
    expect(screen.getByRole('button', { name: 'Senden' })).toBeDisabled()
    await userEvent.type(feld, '   {Enter}')
    expect(fetchMock).not.toHaveBeenCalled()
    await userEvent.clear(feld)
    await userEvent.type(feld, 'Zeile eins{Shift>}{Enter}{/Shift}Zeile zwei')
    expect(fetchMock).not.toHaveBeenCalled()
    expect(feld).toHaveValue('Zeile eins\nZeile zwei')
    await userEvent.click(screen.getByRole('button', { name: 'Senden' }))
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('zeigt den Ladehinweis und sperrt das Senden, solange die Antwort läuft', async () => {
    let fertig!: (r: Response) => void
    const fetchMock = mitFetch(() => new Promise<Response>((resolve) => { fertig = resolve }))
    render(<ChatBereich vorschlaege={[]} />)
    const feld = screen.getByRole('textbox', { name: 'Frage' })
    await userEvent.type(feld, 'Erste Frage{Enter}')
    expect(await screen.findByText('Antwort wird erzeugt …')).toBeInTheDocument()
    await userEvent.type(feld, 'Zweite Frage{Enter}')
    expect(fetchMock).toHaveBeenCalledTimes(1)
    fertig(sseAntwort(STROM))
    await waitFor(() => expect(screen.queryByText('Antwort wird erzeugt …')).not.toBeInTheDocument())
  })

  it('zeigt ein Fehler-Ereignis aus dem Strom in der Antwort', async () => {
    mitFetch(() => sseAntwort(['event: quellen\ndata: []\n\nevent: fehler\ndata: {"meldung":"Das Sprachmodell hat nicht geantwortet"}\n\nevent: ende\ndata: {}\n\n']))
    render(<ChatBereich vorschlaege={[]} />)
    await userEvent.type(screen.getByRole('textbox', { name: 'Frage' }), 'Was?{Enter}')
    expect(await screen.findByText('Das Sprachmodell hat nicht geantwortet')).toBeInTheDocument()
  })

  it('zeigt die Fehlermeldung der API, wenn die Anfrage scheitert', async () => {
    mitFetch(() => Response.json({ detail: 'API nicht erreichbar' }, { status: 502 }))
    render(<ChatBereich vorschlaege={[]} />)
    await userEvent.type(screen.getByRole('textbox', { name: 'Frage' }), 'Was?{Enter}')
    const fehler = await screen.findByText('API nicht erreichbar')
    expect(fehler.closest('[data-art]')).toHaveAttribute('data-art', 'fehler')
    expect(screen.getByRole('alert')).toContainElement(fehler)
  })

  it('zeigt eine erreichte Grenze der Demo als freundlichen Hinweis statt als Fehler', async () => {
    mitFetch(() => Response.json({ detail: 'Tageslimit der Demo erreicht, morgen geht es weiter.' }, { status: 429 }))
    render(<ChatBereich vorschlaege={[]} />)
    await userEvent.type(screen.getByRole('textbox', { name: 'Frage' }), 'Was?{Enter}')
    const hinweis = await screen.findByText('Tageslimit der Demo erreicht, morgen geht es weiter.')
    expect(hinweis.closest('[data-art]')).toHaveAttribute('data-art', 'hinweis')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('zeigt ein erschöpftes Kontingent beim Modell-Anbieter als Hinweis, auch mitten im Strom', async () => {
    const meldung = 'Die Demo hat ihr Monatskontingent beim Modell-Anbieter erreicht.'
    mitFetch(() => sseAntwort([`event: quellen\ndata: []\n\nevent: fehler\ndata: {"meldung":"${meldung}","art":"grenze"}\n\nevent: ende\ndata: {}\n\n`]))
    render(<ChatBereich vorschlaege={[]} />)
    await userEvent.type(screen.getByRole('textbox', { name: 'Frage' }), 'Was?{Enter}')
    expect((await screen.findByText(meldung)).closest('[data-art]')).toHaveAttribute('data-art', 'hinweis')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('bietet Beispielfragen an, die als Frage gesendet werden', async () => {
    const fetchMock = mitFetch(() => sseAntwort(STROM))
    render(<ChatBereich vorschlaege={['Wann ist Nachtruhe in der Siedlung Sonnenhof?']} />)
    await userEvent.click(screen.getByRole('button', { name: 'Wann ist Nachtruhe in der Siedlung Sonnenhof?' }))
    expect(JSON.parse(String(fetchMock.mock.calls[0]![1]!.body)).frage).toBe('Wann ist Nachtruhe in der Siedlung Sonnenhof?')
    await screen.findByText('von 22 Uhr bis 6 Uhr')
    expect(screen.queryByRole('button', { name: 'Wann ist Nachtruhe in der Siedlung Sonnenhof?' })).not.toBeInTheDocument()
  })
})
