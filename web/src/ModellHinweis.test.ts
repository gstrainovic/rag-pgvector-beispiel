import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ModellHinweis from './components/ModellHinweis.vue'
import { globalOptionen } from './test-utils'

describe('ModellHinweis', () => {
  it('nennt Sprachmodell, Embedder und Anzahl Dokumente', () => {
    const w = mount(ModellHinweis, {
      props: { info: { llm_modell: 'qwen3:4b-instruct-2507-q4_K_M', llm_basis_url: 'http://ollama:11434/v1', embedder: 'qwen3-embedding:0.6b', anzahl_dokumente: 3 } },
      global: globalOptionen,
    })
    expect(w.text()).toContain('qwen3:4b-instruct-2507-q4_K_M')
    expect(w.text()).toContain('qwen3-embedding:0.6b')
    expect(w.text()).toContain('3 Dokumente')
    expect(w.text()).toContain('lokal')
  })

  it('erkennt einen Cloud-Dienst an der Basis-URL', () => {
    const w = mount(ModellHinweis, {
      props: { info: { llm_modell: 'mistral-small-latest', llm_basis_url: 'https://api.mistral.ai/v1', embedder: 'mistral-embed', anzahl_dokumente: 1 } },
      global: globalOptionen,
    })
    expect(w.text()).toContain('api.mistral.ai')
    expect(w.text()).toContain('1 Dokument')
    expect(w.text()).not.toContain('lokal')
  })

  it('zeigt ohne Info einen Ladehinweis', () => {
    const w = mount(ModellHinweis, { props: { info: null }, global: globalOptionen })
    expect(w.text()).toContain('Verbinde')
  })
})
