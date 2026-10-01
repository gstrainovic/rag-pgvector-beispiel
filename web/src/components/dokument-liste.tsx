import { ExternalLinkIcon, FileTextIcon, Trash2Icon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { BeispielDatei, Dokument } from '@/lib/typen'

interface Props {
  /** Beispiele zuerst, dann die eigenen Uploads (so liefert es die API) */
  dokumente: Dokument[]
  /** Dateien aus GET /api/beispiele: zu jedem Beispieltitel das Original als PDF und Markdown */
  beispiele: BeispielDatei[]
  gesperrt: boolean
  onLoeschen: (id: number) => void
}

export function absatzZahl(n: number): string {
  return n === 1 ? '1 Absatz' : `${n} Absätze`
}

function downloadPfad(dateiname: string): string {
  return `/api/beispiele/${encodeURIComponent(dateiname)}`
}

function original(beispiele: BeispielDatei[], titel: string, endung: string): BeispielDatei | undefined {
  return beispiele.find(b => b.titel === titel && b.dateiname.endsWith(endung))
}

export function DokumentListe({ dokumente, beispiele, gesperrt, onLoeschen }: Props) {
  if (dokumente.length === 0)
    return <p className="text-sm text-muted-foreground">Keine Dokumente geladen.</p>

  const hatOriginale = dokumente.some(d => d.beispiel && original(beispiele, d.titel, '.pdf'))
  return (
    <div className="flex flex-col gap-2">
      <ul className="flex flex-col gap-0.5">
        {dokumente.map((d) => {
          const pdf = d.beispiel ? original(beispiele, d.titel, '.pdf') : undefined
          const md = d.beispiel ? original(beispiele, d.titel, '.md') : undefined
          return (
            <li key={d.id} className="flex items-center gap-3 rounded-lg py-1.5 pr-1 pl-2 hover:bg-muted/60">
              <FileTextIcon aria-hidden className="size-5 shrink-0 text-muted-foreground" />
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="flex min-w-0 items-center gap-2">
                  <span className="truncate text-sm font-medium" title={d.titel}>{d.titel}</span>
                  {d.beispiel && <Badge variant="secondary">Beispiel</Badge>}
                </span>
                <span className="flex flex-wrap items-center gap-x-3 text-xs text-muted-foreground">
                  <span>{absatzZahl(d.anzahl_absaetze)}</span>
                  {pdf && (
                    <a
                      href={downloadPfad(pdf.dateiname)}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Original ansehen: ${d.titel} (PDF)`}
                      className="inline-flex items-center gap-1 text-foreground underline underline-offset-3 hover:no-underline"
                    >
                      <ExternalLinkIcon aria-hidden className="size-3" />
                      Original ansehen
                    </a>
                  )}
                  {md && (
                    <a
                      href={downloadPfad(md.dateiname)}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`${d.titel} als Markdown`}
                      className="underline underline-offset-3 hover:no-underline"
                    >
                      .md
                    </a>
                  )}
                </span>
              </div>
              {!d.beispiel && (
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`«${d.titel}» löschen`}
                  title="Dokument löschen"
                  disabled={gesperrt}
                  onClick={() => onLoeschen(d.id)}
                >
                  <Trash2Icon aria-hidden />
                </Button>
              )}
            </li>
          )
        })}
      </ul>
      {hatOriginale && (
        <p className="px-2 text-xs text-muted-foreground">
          Zum Gegenprüfen der Antworten: die Originale der Beispieldokumente.
        </p>
      )}
    </div>
  )
}
