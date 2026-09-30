import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { globalOptionen } from '../test-utils'
import DokumentListe from './DokumentListe.vue'

const dokumente = [
  { id: 1, titel: 'Hausordnung Sonnenhof', anzahl_absaetze: 10, erstellt: '2026-10-01T10:00:00Z' },
  { id: 2, titel: 'wartung.pdf', anzahl_absaetze: 2, erstellt: '2026-10-01T10:05:00Z' },
]

function mounten(props: Partial<InstanceType<typeof DokumentListe>['$props']> = {}) {
  return mount(DokumentListe, {
    props: { dokumente, laden: false, ...props },
    global: globalOptionen,
  })
}

describe('DokumentListe', () => {
  it('zeigt jedes Dokument mit Titel und Anzahl Absätze', () => {
    const w = mounten()
    const zeilen = w.findAll('[data-test="dokument"]')
    expect(zeilen).toHaveLength(2)
    expect(zeilen[0]!.text()).toContain('Hausordnung Sonnenhof')
    expect(zeilen[0]!.text()).toContain('10 Absätze')
    expect(zeilen[1]!.text()).toContain('wartung.pdf')
    expect(zeilen[1]!.text()).toContain('2 Absätze')
  })

  it('zeigt bei leerer Liste den Hinweis und den Beispiel-Knopf', async () => {
    const w = mounten({ dokumente: [] })
    expect(w.text()).toContain('Noch keine Dokumente')
    await w.find('[data-test="beispiele"]').trigger('click')
    expect(w.emitted('beispiele')).toHaveLength(1)
  })

  it('meldet Löschen mit der Dokument-ID', async () => {
    const w = mounten()
    await w.findAll('[data-test="loeschen"]')[1]!.trigger('click')
    expect(w.emitted('loeschen')).toEqual([[2]])
  })

  it('meldet ausgewählte Dateien aus dem Dateifeld', async () => {
    const w = mounten()
    const input = w.find<HTMLInputElement>('input[type="file"]')
    const datei = new File(['Hallo'], 'notiz.txt', { type: 'text/plain' })
    Object.defineProperty(input.element, 'files', { value: [datei] })
    await input.trigger('change')
    expect(w.emitted('hochladen')).toEqual([[[datei]]])
  })

  it('nimmt abgelegte Dateien per Drag-and-drop an', async () => {
    const w = mounten()
    const datei = new File(['%PDF'], 'scan.pdf', { type: 'application/pdf' })
    const zone = w.find('[data-test="dropzone"]')
    await zone.trigger('dragenter')
    expect(zone.classes()).toContain('aktiv')
    await zone.trigger('drop', { dataTransfer: { files: [datei] } })
    expect(zone.classes()).not.toContain('aktiv')
    expect(w.emitted('hochladen')).toEqual([[[datei]]])
  })

  it('zeigt den Ladeindikator, solange hochgeladen wird', () => {
    expect(mounten({ laden: true }).find('[data-test="laden"]').exists()).toBe(true)
    expect(mounten({ laden: false }).find('[data-test="laden"]').exists()).toBe(false)
  })
})
