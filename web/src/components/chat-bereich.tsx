'use client'

import { ClockIcon, Loader2Icon, MessageSquareIcon, SendIcon, TriangleAlertIcon } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { frage } from '@/lib/api-client'
import { istGrenze, meldung } from '@/lib/fehler'
import type { FrageEvent, Quelle } from '@/lib/typen'
import { cn } from '@/lib/utils'
import { AntwortMarkdown } from './antwort-markdown'
import { QuellenListe } from './quellen-liste'

interface Nachricht {
  id: number
  rolle: 'nutzer' | 'assistent'
  text: string
  quellen: Quelle[]
  fehler?: string
  hinweis?: string
}

/** Wendet ein Ereignis aus dem Antwortstrom auf die entstehende Antwort an. */
function mitEvent(n: Nachricht, e: FrageEvent): Nachricht {
  switch (e.typ) {
    case 'quellen': return { ...n, quellen: e.quellen }
    case 'token': return { ...n, text: n.text + e.text }
    case 'fehler': return e.grenze ? { ...n, hinweis: e.meldung } : { ...n, fehler: e.meldung }
    case 'ende': return n
  }
}

/** Client Component: Verlauf im Browser-Tab, Antworten kommen Stück für Stück per SSE. */
export function ChatBereich({ vorschlaege }: { vorschlaege: string[] }) {
  const [verlauf, setVerlauf] = useState<Nachricht[]>([])
  const [eingabe, setEingabe] = useState('')
  const [laeuft, setLaeuft] = useState(false)
  const naechsteId = useRef(1)
  const verlaufElement = useRef<HTMLDivElement>(null)

  // Beim Streamen unten bleiben
  useEffect(() => {
    const el = verlaufElement.current
    el?.scrollTo({ top: el.scrollHeight })
  }, [verlauf])

  async function senden(text: string) {
    const t = text.trim()
    if (!t || laeuft)
      return
    const antwortId = naechsteId.current + 1
    naechsteId.current += 2
    const aendereAntwort = (aenderung: (n: Nachricht) => Nachricht) =>
      setVerlauf(v => v.map(n => (n.id === antwortId ? aenderung(n) : n)))

    setVerlauf(v => [
      ...v,
      { id: antwortId - 1, rolle: 'nutzer', text: t, quellen: [] },
      { id: antwortId, rolle: 'assistent', text: '', quellen: [] },
    ])
    setEingabe('')
    setLaeuft(true)
    try {
      await frage(t, e => aendereAntwort(n => mitEvent(n, e)))
    }
    catch (e) {
      // Eine erreichte Grenze der Demo (429) ist kein Defekt: als Hinweis zeigen, nicht als Fehler
      aendereAntwort(n => (istGrenze(e) ? { ...n, hinweis: meldung(e) } : { ...n, fehler: meldung(e) }))
    }
    finally {
      setLaeuft(false)
    }
  }

  function taste(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void senden(eingabe)
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div ref={verlaufElement} className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-1 pb-4">
        {verlauf.length === 0 && (
          <div className="text-sm text-muted-foreground">
            <p>Stellen Sie eine Frage zu den geladenen Dokumenten. Die Antwort nennt die Absätze, auf die sie sich stützt.</p>
            {vorschlaege.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {vorschlaege.map(v => (
                  <Button key={v} variant="outline" size="sm" className="h-auto rounded-full py-1.5 text-left whitespace-normal" onClick={() => void senden(v)}>
                    <MessageSquareIcon aria-hidden />
                    {v}
                  </Button>
                ))}
              </div>
            )}
          </div>
        )}

        {verlauf.map(n => (
          <article
            key={n.id}
            aria-label={n.rolle === 'nutzer' ? 'Ihre Frage' : 'Antwort'}
            className={cn('flex max-w-[85%] flex-col gap-1', n.rolle === 'nutzer' && 'items-end self-end')}
          >
            <span className="text-xs text-muted-foreground">{n.rolle === 'nutzer' ? 'Sie' : 'Assistent'}</span>
            <div
              className={cn(
                'rounded-2xl px-3.5 py-2 text-sm',
                n.rolle === 'nutzer' ? 'bg-primary text-primary-foreground' : 'bg-card ring-1 ring-foreground/10',
              )}
            >
              {n.text && (n.rolle === 'assistent' ? <AntwortMarkdown text={n.text} /> : <p className="whitespace-pre-wrap">{n.text}</p>)}
              {!n.text && !n.fehler && !n.hinweis && <Loader2Icon aria-hidden className="size-4 animate-spin text-muted-foreground" />}
              {n.fehler && (
                <p role="alert" data-art="fehler" className="flex items-start gap-1.5 text-destructive">
                  <TriangleAlertIcon aria-hidden className="mt-0.5 size-4 shrink-0" />
                  <span>{n.fehler}</span>
                </p>
              )}
              {n.hinweis && (
                <p data-art="hinweis" className="flex items-start gap-1.5 text-muted-foreground">
                  <ClockIcon aria-hidden className="mt-0.5 size-4 shrink-0" />
                  <span>{n.hinweis}</span>
                </p>
              )}
              {n.rolle === 'assistent' && <QuellenListe quellen={n.quellen} />}
            </div>
          </article>
        ))}

        {laeuft && <p role="status" className="text-xs text-muted-foreground">Antwort wird erzeugt …</p>}
      </div>

      <form
        className="flex items-end gap-2 border-t pt-3"
        onSubmit={(e) => {
          e.preventDefault()
          void senden(eingabe)
        }}
      >
        <Textarea
          aria-label="Frage"
          rows={1}
          value={eingabe}
          placeholder="Frage zu den Dokumenten … (Enter sendet, Shift+Enter neue Zeile)"
          className="max-h-32 min-h-9 flex-1 bg-background"
          onChange={e => setEingabe(e.target.value)}
          onKeyDown={taste}
        />
        <Button type="submit" size="icon-lg" aria-label="Senden" disabled={laeuft || !eingabe.trim()}>
          <SendIcon aria-hidden />
        </Button>
      </form>
    </div>
  )
}
