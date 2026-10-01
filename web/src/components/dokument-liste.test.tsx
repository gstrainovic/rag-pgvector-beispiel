import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { BEISPIELE, DOKUMENTE } from '@/test/daten'
import { DokumentListe } from './dokument-liste'

function zeige(props: Partial<Parameters<typeof DokumentListe>[0]> = {}) {
  return render(<DokumentListe dokumente={DOKUMENTE} beispiele={BEISPIELE} gesperrt={false} onLoeschen={() => {}} {...props} />)
}

describe('DokumentListe', () => {
  it('zeigt jedes Dokument mit Titel und Anzahl Absätze', () => {
    zeige()
    const zeilen = screen.getAllByRole('listitem')
    expect(zeilen).toHaveLength(3)
    expect(zeilen[0]).toHaveTextContent('Hausordnung Sonnenhof')
    expect(zeilen[0]).toHaveTextContent('10 Absätze')
    expect(zeilen[2]).toHaveTextContent('wartung.pdf')
    expect(zeilen[2]).toHaveTextContent('1 Absatz')
    expect(zeilen[2]).not.toHaveTextContent('1 Absätze')
  })

  it('markiert Beispiele und bietet dort das Original statt des Löschens an', () => {
    zeige()
    const beispiel = screen.getAllByRole('listitem')[0]!
    expect(within(beispiel).getByText('Beispiel')).toBeInTheDocument()
    expect(within(beispiel).queryByRole('button')).not.toBeInTheDocument()
    const original = within(beispiel).getByRole('link', { name: 'Original ansehen: Hausordnung Sonnenhof (PDF)' })
    expect(original).toHaveTextContent('Original ansehen')
    expect(original).toHaveAttribute('href', '/api/beispiele/Hausordnung%20Sonnenhof.pdf')
    expect(original).toHaveAttribute('target', '_blank')
    expect(original).toHaveAttribute('rel', expect.stringContaining('noopener'))
    expect(within(beispiel).getByRole('link', { name: 'Hausordnung Sonnenhof als Markdown' }))
      .toHaveAttribute('href', '/api/beispiele/Hausordnung%20Sonnenhof.md')
  })

  it('erklärt, wozu die Originale da sind', () => {
    zeige()
    expect(screen.getByText('Zum Gegenprüfen der Antworten: die Originale der Beispieldokumente.')).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/wieder hochladen|Beispieldokumente laden/)
  })

  it('zeigt eigene Dokumente ohne Markierung und mit Lösch-Knopf', async () => {
    const onLoeschen = vi.fn()
    zeige({ onLoeschen })
    const eigenes = screen.getAllByRole('listitem')[2]!
    expect(within(eigenes).queryByText('Beispiel')).not.toBeInTheDocument()
    expect(within(eigenes).queryByRole('link')).not.toBeInTheDocument()
    await userEvent.click(within(eigenes).getByRole('button', { name: '«wartung.pdf» löschen' }))
    expect(onLoeschen).toHaveBeenCalledWith(7)
    expect(screen.getAllByRole('button')).toHaveLength(1)
  })

  it('lässt den Link weg, wenn es zu einem Beispiel keine Datei gibt', () => {
    zeige({ beispiele: [] })
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    expect(screen.queryByText(/Zum Gegenprüfen/)).not.toBeInTheDocument()
  })

  it('sperrt das Löschen, solange eine Änderung läuft', () => {
    zeige({ gesperrt: true })
    expect(screen.getByRole('button', { name: '«wartung.pdf» löschen' })).toBeDisabled()
  })

  it('zeigt bei leerer Liste einen Hinweis', () => {
    zeige({ dokumente: [] })
    expect(screen.getByText(/Keine Dokumente/)).toBeInTheDocument()
    expect(screen.queryByRole('list')).not.toBeInTheDocument()
  })
})
