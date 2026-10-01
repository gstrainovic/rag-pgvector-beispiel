'use client'

import { Loader2Icon, UploadIcon } from 'lucide-react'
import Link from 'next/link'
import { useRef, useState } from 'react'
import type { ChangeEvent, DragEvent, KeyboardEvent } from 'react'
import { cn } from '@/lib/utils'

interface Props {
  laeuft: boolean
  onDateien: (dateien: File[]) => void
}

/** Ablagefläche für PDF, TXT und Markdown: Drag-and-drop, Klick oder Tastatur. */
export function UploadZone({ laeuft, onDateien }: Props) {
  const feld = useRef<HTMLInputElement>(null)
  const [ziehen, setZiehen] = useState(false)

  function melde(dateien: FileList | null | undefined) {
    const liste = Array.from(dateien ?? [])
    if (liste.length && !laeuft)
      onDateien(liste)
  }

  function ausFeld(e: ChangeEvent<HTMLInputElement>) {
    melde(e.target.files)
    e.target.value = '' // dieselbe Datei soll sich erneut wählen lassen
  }

  function abgelegt(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setZiehen(false)
    melde(e.dataTransfer?.files)
  }

  function beimZiehen(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setZiehen(true)
  }

  function taste(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      feld.current?.click()
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div
        role="button"
        tabIndex={0}
        aria-busy={laeuft}
        data-ziehen={ziehen}
        onClick={() => feld.current?.click()}
        onKeyDown={taste}
        onDragEnter={beimZiehen}
        onDragOver={beimZiehen}
        onDragLeave={() => setZiehen(false)}
        onDrop={abgelegt}
        className={cn(
          'flex cursor-pointer items-center gap-4 rounded-xl border-2 border-dashed border-border p-4 text-muted-foreground transition-colors outline-none',
          'hover:border-primary/60 hover:bg-muted/60 hover:text-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50',
          'data-[ziehen=true]:border-primary data-[ziehen=true]:bg-muted data-[ziehen=true]:text-foreground',
        )}
      >
        <input
          ref={feld}
          type="file"
          multiple
          hidden
          aria-label="Dateien auswählen"
          accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
          onChange={ausFeld}
          onClick={e => e.stopPropagation()}
        />
        {laeuft
          ? <Loader2Icon aria-hidden className="size-8 shrink-0 animate-spin" />
          : <UploadIcon aria-hidden className="size-8 shrink-0" />}
        <span className="flex flex-col gap-0.5">
          <strong className="font-medium">{laeuft ? 'Wird verarbeitet …' : 'Dateien hierher ziehen oder klicken'}</strong>
          <small className="text-xs">PDF, TXT oder Markdown, bis 20 MB</small>
        </span>
      </div>
      <p className="px-1 text-xs text-muted-foreground">
        <span>Ihre Dateien sieht nur Ihr Browser; sie werden nach 24 Stunden gelöscht. Bitte nichts Vertrauliches hochladen.</span>
        {' '}
        <Link href="/datenschutz" className="underline underline-offset-3 hover:text-foreground">Datenschutz</Link>
      </p>
    </div>
  )
}
