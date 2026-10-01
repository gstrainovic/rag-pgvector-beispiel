import { describe, expect, it } from 'vitest'
import { INFO_LOKAL, INFO_MISTRAL } from '@/test/daten'
import { embedderName, modellName } from './modell'

describe('modellName', () => {
  it('nennt das Cloud-Modell lesbar', () => {
    expect(modellName(INFO_MISTRAL)).toBe('Mistral Small')
  })

  it('kennzeichnet ein Modell hinter Ollama als lokal', () => {
    expect(modellName(INFO_LOKAL)).toBe('Qwen3 4B lokal')
    expect(modellName({ ...INFO_LOKAL, llm_basis_url: 'http://localhost:11434/v1' })).toBe('Qwen3 4B lokal')
  })

  it('zeigt unbekannte Modelle mit ihrem Namen', () => {
    expect(modellName({ ...INFO_MISTRAL, llm_modell: 'gpt-4o-mini', llm_basis_url: 'https://api.openai.com/v1' })).toBe('gpt-4o-mini')
    expect(modellName({ ...INFO_LOKAL, llm_modell: 'gemma4:e2b' })).toBe('gemma4:e2b lokal')
  })
})

describe('embedderName', () => {
  it('nennt den Embedder lesbar und kennzeichnet lokale Embedder', () => {
    expect(embedderName(INFO_MISTRAL)).toBe('Mistral Embed')
    expect(embedderName(INFO_LOKAL)).toBe('Qwen3 Embedding lokal')
    expect(embedderName({ ...INFO_MISTRAL, embedder: 'fastembed:paraphrase-multilingual-MiniLM-L12-v2' })).toBe('fastembed MiniLM lokal')
    expect(embedderName({ ...INFO_MISTRAL, embedder: 'text-embedding-3-small' })).toBe('text-embedding-3-small')
  })
})
