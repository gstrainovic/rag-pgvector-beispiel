import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { globalOptionen } from '../test-utils'
import ChatBereich from './ChatBereich.vue'

const verlauf = [
  { id: 1, rolle: 'nutzer' as const, text: 'Wann ist Nachtruhe?', quellen: [] },
  {
    id: 2,
    rolle: 'assistent' as const,
    text: 'Die Nachtruhe dauert **von 22 Uhr bis 6 Uhr**.',
    quellen: [{ titel: 'Hausordnung Sonnenhof', absatz: 'Die Nachtruhe dauert von 22 Uhr bis 6 Uhr.', score: 0.59 }],
  },
]

describe('ChatBereich', () => {
  it('rendert Nutzer- und Assistent-Nachrichten, Markdown als HTML', () => {
    const w = mount(ChatBereich, { props: { verlauf, laden: false }, global: globalOptionen })
    const nachrichten = w.findAll('[data-test="nachricht"]')
    expect(nachrichten).toHaveLength(2)
    expect(nachrichten[0]!.classes()).toContain('nutzer')
    expect(nachrichten[1]!.find('strong').text()).toBe('von 22 Uhr bis 6 Uhr')
  })

  it('entfernt Skripte aus der Antwort (DOMPurify)', () => {
    const boese = [{ id: 1, rolle: 'assistent' as const, text: 'Hallo <img src=x onerror="alert(1)"> <script>alert(1)</script>', quellen: [] }]
    const w = mount(ChatBereich, { props: { verlauf: boese, laden: false }, global: globalOptionen })
    expect(w.html()).not.toContain('onerror')
    expect(w.html()).not.toContain('<script')
  })

  it('zeigt Quellen unter der Assistent-Antwort', () => {
    const w = mount(ChatBereich, { props: { verlauf, laden: false }, global: globalOptionen })
    expect(w.find('[data-test="quellen-kopf"]').text()).toContain('1 Quelle')
  })

  it('sendet mit Enter und leert das Feld, Shift+Enter fügt eine Zeile ein', async () => {
    const w = mount(ChatBereich, { props: { verlauf: [], laden: false }, global: globalOptionen })
    const feld = w.find('textarea')
    await feld.setValue('Was kostet die Lieferung?')
    await feld.trigger('keydown', { key: 'Enter', shiftKey: true })
    expect(w.emitted('senden')).toBeUndefined()
    await feld.trigger('keydown', { key: 'Enter' })
    expect(w.emitted('senden')).toEqual([['Was kostet die Lieferung?']])
    expect((feld.element as HTMLTextAreaElement).value).toBe('')
  })

  it('sendet nichts, solange geladen wird oder das Feld leer ist', async () => {
    const w = mount(ChatBereich, { props: { verlauf: [], laden: true }, global: globalOptionen })
    expect(w.find('[data-test="laden"]').exists()).toBe(true)
    await w.find('textarea').setValue('Frage')
    await w.find('textarea').trigger('keydown', { key: 'Enter' })
    expect(w.emitted('senden')).toBeUndefined()
    const w2 = mount(ChatBereich, { props: { verlauf: [], laden: false }, global: globalOptionen })
    await w2.find('textarea').setValue('   ')
    await w2.find('textarea').trigger('keydown', { key: 'Enter' })
    expect(w2.emitted('senden')).toBeUndefined()
  })

  it('bietet Beispielfragen an, die als Nachricht gesendet werden', async () => {
    const w = mount(ChatBereich, { props: { verlauf: [], laden: false, vorschlaege: ['Wann ist Nachtruhe?'] }, global: globalOptionen })
    await w.find('[data-test="vorschlag"]').trigger('click')
    expect(w.emitted('senden')).toEqual([['Wann ist Nachtruhe?']])
  })
})
