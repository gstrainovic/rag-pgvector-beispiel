import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { QUELLEN } from '@/test/daten'
import { QuellenListe } from './quellen-liste'

describe('QuellenListe', () => {
  it('ist zugeklappt und nennt die Anzahl Quellen', () => {
    render(<QuellenListe quellen={QUELLEN} />)
    expect(screen.getByRole('button', { name: '2 Quellen' })).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('Die Nachtruhe dauert von 22 Uhr bis 6 Uhr.')).not.toBeInTheDocument()
  })

  it('zeigt nach dem Aufklappen Titel, Absatz und Score', async () => {
    render(<QuellenListe quellen={QUELLEN} />)
    await userEvent.click(screen.getByRole('button', { name: '2 Quellen' }))
    const eintraege = screen.getAllByRole('listitem')
    expect(eintraege).toHaveLength(2)
    expect(eintraege[0]).toHaveTextContent('Hausordnung Sonnenhof')
    expect(eintraege[0]).toHaveTextContent('Die Nachtruhe dauert von 22 Uhr bis 6 Uhr.')
    expect(eintraege[0]).toHaveTextContent('59 %')
    expect(eintraege[1]).toHaveTextContent('30 %')
  })

  it('schreibt bei einer Quelle die Einzahl und rendert nichts ohne Quellen', () => {
    const { rerender } = render(<QuellenListe quellen={QUELLEN.slice(0, 1)} />)
    expect(screen.getByRole('button', { name: '1 Quelle' })).toBeInTheDocument()
    rerender(<QuellenListe quellen={[]} />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
