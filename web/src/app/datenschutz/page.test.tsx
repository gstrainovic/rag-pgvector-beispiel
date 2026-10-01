import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import Datenschutz from './page'

describe('/datenschutz', () => {
  it('rendert die Erklärung mit Verantwortlichem, Stand und Rückweg zur Demo', () => {
    render(<Datenschutz />)
    expect(screen.getByRole('heading', { level: 1, name: 'Datenschutzerklärung' })).toBeInTheDocument()
    expect(screen.getByText(/^Stand: \w+ \d{4}$/)).toBeInTheDocument()
    expect(screen.getByText(/Strainovic IT \(Einzelfirma\)/)).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'info@strainovic-it.ch' })[0]).toHaveAttribute('href', 'mailto:info@strainovic-it.ch')
    expect(screen.getByRole('link', { name: /Zurück zur Demo/ })).toHaveAttribute('href', '/')
  })

  it('nennt, was die Demo tatsächlich tut: Cookie, 24 Stunden, Mistral, Infomaniak, keine Zugriffsprotokolle', () => {
    render(<Datenschutz />)
    const text = document.body.textContent ?? ''
    expect(text).toContain('rag_sitzung')
    expect(text).toContain('30 Tage')
    expect(text).toContain('24 Stunden')
    expect(text).toContain('Mistral AI')
    expect(text).toContain('Frankreich')
    expect(text).toContain('Infomaniak')
    expect(text).toMatch(/Fragen und Antworten werden nicht gespeichert/)
    expect(text).toContain('Die Verwendung zum Training der Modelle ist in unserem Konto deaktiviert.')
    expect(screen.getByRole('link', { name: 'Datenschutzerklärung von Mistral AI' }))
      .toHaveAttribute('href', 'https://legal.mistral.ai/terms/privacy-policy')
    expect(text).toMatch(/keinen Analysedienst, keine Werbe-Cookies/)
    expect(text).toMatch(/keine vertraulichen/i)
  })

  it('nennt keine UID oder Handelsregisternummer', () => {
    render(<Datenschutz />)
    expect(document.body.textContent).not.toMatch(/CHE-|UID|Handelsregister/)
  })
})
