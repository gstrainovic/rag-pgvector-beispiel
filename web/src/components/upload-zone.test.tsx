import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { UploadZone } from './upload-zone'

describe('UploadZone', () => {
  it('meldet ausgewählte Dateien aus dem Dateifeld', async () => {
    const onDateien = vi.fn()
    render(<UploadZone laeuft={false} onDateien={onDateien} />)
    const datei = new File(['Hallo'], 'notiz.txt', { type: 'text/plain' })
    await userEvent.upload(screen.getByLabelText('Dateien auswählen'), datei)
    expect(onDateien).toHaveBeenCalledWith([datei])
  })

  it('nimmt abgelegte Dateien per Drag-and-drop an und hebt die Zone beim Ziehen hervor', () => {
    const onDateien = vi.fn()
    render(<UploadZone laeuft={false} onDateien={onDateien} />)
    const zone = screen.getByRole('button', { name: /Dateien hierher ziehen oder klicken/ })
    const datei = new File(['%PDF'], 'scan.pdf', { type: 'application/pdf' })
    fireEvent.dragEnter(zone)
    expect(zone).toHaveAttribute('data-ziehen', 'true')
    fireEvent.drop(zone, { dataTransfer: { files: [datei] } })
    expect(zone).toHaveAttribute('data-ziehen', 'false')
    expect(onDateien).toHaveBeenCalledWith([datei])
  })

  it('öffnet den Dateidialog per Klick und per Tastatur', async () => {
    render(<UploadZone laeuft={false} onDateien={() => {}} />)
    const feld = screen.getByLabelText<HTMLInputElement>('Dateien auswählen')
    const klick = vi.spyOn(feld, 'click')
    await userEvent.click(screen.getByRole('button', { name: /Dateien hierher ziehen/ }))
    screen.getByRole('button', { name: /Dateien hierher ziehen/ }).focus()
    await userEvent.keyboard('{Enter}')
    expect(klick).toHaveBeenCalledTimes(2)
    expect(feld.accept).toContain('.pdf')
  })

  it('sagt, wer die Dateien sieht und wie lange sie bleiben, mit Link zur Datenschutzerklärung', () => {
    render(<UploadZone laeuft={false} onDateien={() => {}} />)
    const hinweis = screen.getByText(/Ihre Dateien sieht nur Ihr Browser/)
    expect(hinweis).toHaveTextContent(
      'Ihre Dateien sieht nur Ihr Browser; sie werden nach 24 Stunden gelöscht. Bitte nichts Vertrauliches hochladen.',
    )
    expect(screen.getByRole('link', { name: 'Datenschutz' })).toHaveAttribute('href', '/datenschutz')
    // der Link liegt neben der Ablagefläche, nicht in ihr: ein Klick darauf öffnet keinen Dateidialog
    expect(screen.getByRole('button', { name: /Dateien hierher ziehen/ })).not.toContainElement(hinweis)
  })

  it('zeigt während der Verarbeitung einen Hinweis und nimmt nichts an', () => {
    const onDateien = vi.fn()
    render(<UploadZone laeuft onDateien={onDateien} />)
    const zone = screen.getByRole('button', { name: /Wird verarbeitet/ })
    expect(zone).toHaveAttribute('aria-busy', 'true')
    fireEvent.drop(zone, { dataTransfer: { files: [new File(['x'], 'a.txt')] } })
    expect(onDateien).not.toHaveBeenCalled()
  })
})
