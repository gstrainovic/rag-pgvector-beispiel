import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Fusszeile } from './fusszeile'

describe('Fusszeile', () => {
  it('verlinkt Datenschutz (intern), Impressum (extern, neuer Tab) und den Code auf GitHub', () => {
    render(<Fusszeile />)
    expect(screen.getByRole('link', { name: 'Datenschutz' })).toHaveAttribute('href', '/datenschutz')
    expect(screen.getByRole('link', { name: 'Datenschutz' })).not.toHaveAttribute('target')

    const impressum = screen.getByRole('link', { name: 'Impressum' })
    expect(impressum).toHaveAttribute('href', 'https://www.strainovic-it.ch/impressum/')
    expect(impressum).toHaveAttribute('target', '_blank')
    expect(impressum).toHaveAttribute('rel', expect.stringContaining('noopener'))

    const code = screen.getByRole('link', { name: 'Code auf GitHub' })
    expect(code).toHaveAttribute('href', 'https://github.com/gstrainovic/rag-pgvector-beispiel')
    expect(code).toHaveAttribute('target', '_blank')
  })
})
