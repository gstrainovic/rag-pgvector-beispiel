import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { globalOptionen } from '../test-utils'
import QuellenListe from './QuellenListe.vue'

const quellen = [
  { titel: 'Hausordnung Sonnenhof', absatz: 'Die Nachtruhe dauert von 22 Uhr bis 6 Uhr.', score: 0.5912 },
  { titel: 'FAQ Schreinerei Holzwerk', absatz: 'Innerhalb von 30 Kilometern liefern wir kostenlos.', score: 0.3 },
]

describe('QuellenListe', () => {
  it('ist zugeklappt und nennt die Anzahl Quellen', () => {
    const w = mount(QuellenListe, { props: { quellen }, global: globalOptionen })
    expect(w.find('[data-test="quellen-kopf"]').text()).toContain('2 Quellen')
    expect(w.find('[data-test="quelle"]').exists()).toBe(false)
  })

  it('zeigt nach dem Aufklappen Titel, Absatz und Score', async () => {
    const w = mount(QuellenListe, { props: { quellen }, global: globalOptionen })
    await w.find('[data-test="quellen-kopf"]').trigger('click')
    const eintraege = w.findAll('[data-test="quelle"]')
    expect(eintraege).toHaveLength(2)
    expect(eintraege[0]!.text()).toContain('Hausordnung Sonnenhof')
    expect(eintraege[0]!.text()).toContain('Die Nachtruhe dauert von 22 Uhr bis 6 Uhr.')
    expect(eintraege[0]!.text()).toContain('59 %')
    expect(eintraege[1]!.text()).toContain('30 %')
  })

  it('rendert nichts ohne Quellen', () => {
    const w = mount(QuellenListe, { props: { quellen: [] }, global: globalOptionen })
    expect(w.find('[data-test="quellen-kopf"]').exists()).toBe(false)
  })
})
