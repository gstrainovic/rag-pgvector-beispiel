import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { INFO_LOKAL, INFO_MISTRAL } from '@/test/daten'
import { Seitenkopf } from './seitenkopf'

describe('Seitenkopf', () => {
  it('zeigt den Titel und die drei Schritte als Liste, ohne den Zusatz «alles lokal»', () => {
    render(<Seitenkopf info={INFO_MISTRAL} />)
    expect(screen.getByRole('heading', { level: 1, name: 'Dokumente befragen' })).toBeInTheDocument()
    const punkte = within(screen.getByRole('list', { name: 'So funktioniert es' })).getAllByRole('listitem')
    expect(punkte.map(p => p.textContent)).toEqual([
      'Eigene Dateien hochladen',
      'Fragen stellen',
      'Antworten mit Quellenangabe',
    ])
    expect(document.body.textContent).not.toMatch(/alles lokal|Cloud-Schlüssel/)
  })

  it('zeigt den Techstack als Badges, dazu Modell und Embedder aus /api/info', () => {
    render(<Seitenkopf info={INFO_MISTRAL} />)
    const badges = within(screen.getByRole('list', { name: 'Techstack' })).getAllByRole('listitem').map(b => b.textContent)
    expect(badges).toEqual([
      'Next.js',
      'TypeScript',
      'Tailwind',
      'shadcn/ui',
      'FastAPI',
      'PostgreSQL + pgvector',
      'Docker',
      'Modell: Mistral Small',
      'Embedder: Mistral Embed',
    ])
    expect(screen.getByText('Modell: Mistral Small')).toHaveAttribute('title', 'mistral-small-latest (api.mistral.ai)')
  })

  it('nennt im lokalen Betrieb das lokale Modell', () => {
    render(<Seitenkopf info={INFO_LOKAL} />)
    expect(screen.getByText('Modell: Qwen3 4B lokal')).toBeInTheDocument()
    expect(screen.getByText('Embedder: Qwen3 Embedding lokal')).toBeInTheDocument()
  })

  it('zeigt den Stack auch, wenn die API nicht antwortet', () => {
    render(<Seitenkopf info={null} />)
    const stack = screen.getByRole('list', { name: 'Techstack' })
    expect(within(stack).getAllByRole('listitem')).toHaveLength(7)
    expect(stack.textContent).not.toContain('Modell')
  })
})
