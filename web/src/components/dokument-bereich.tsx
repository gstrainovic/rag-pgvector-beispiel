'use client'

import { useRouter } from 'next/navigation'
import { useTransition } from 'react'
import { toast } from 'sonner'
import { dokumentLoeschen } from '@/app/aktionen'
import { ladeHoch } from '@/lib/api-client'
import { istGrenze, meldung } from '@/lib/fehler'
import type { BeispielDatei, Dokument } from '@/lib/typen'
import { absatzZahl, DokumentListe } from './dokument-liste'
import { UploadZone } from './upload-zone'

interface Props {
  /** Kommt von der Server Component; nach jeder Änderung liefert der Server die Liste neu. */
  dokumente: Dokument[]
  beispiele: BeispielDatei[]
}

function uploadMeldung(neu: Dokument[]): string {
  const absaetze = absatzZahl(neu.reduce((summe, d) => summe + d.anzahl_absaetze, 0))
  return neu.length === 1 ? `«${neu[0]!.titel}» geladen, ${absaetze}.` : `${neu.length} Dateien geladen, ${absaetze}.`
}

/** Client Component: Upload und Löschen; der Zustand der Liste bleibt beim Server. */
export function DokumentBereich({ dokumente, beispiele }: Props) {
  const router = useRouter()
  // Die Transition bleibt offen, bis der Server die Seite neu geliefert hat
  const [laeuft, starte] = useTransition()

  function hochladen(dateien: File[]) {
    starte(async () => {
      try {
        toast.success(uploadMeldung(await ladeHoch(dateien)))
        router.refresh()
      }
      catch (e) {
        if (istGrenze(e))
          toast.info(meldung(e))
        else
          toast.error(meldung(e))
      }
    })
  }

  function loeschen(id: number) {
    starte(async () => {
      const ergebnis = await dokumentLoeschen(id)
      if (!ergebnis.ok)
        toast.error(ergebnis.fehler)
    })
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <UploadZone laeuft={laeuft} onDateien={hochladen} />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <DokumentListe dokumente={dokumente} beispiele={beispiele} gesperrt={laeuft} onLoeschen={loeschen} />
      </div>
    </div>
  )
}
