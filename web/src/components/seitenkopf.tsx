import { BoxesIcon, CheckIcon, CpuIcon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { embedderName, host, modellName } from '@/lib/modell'
import type { Info } from '@/lib/typen'

const SCHRITTE = ['Eigene Dateien hochladen', 'Fragen stellen', 'Antworten mit Quellenangabe']
const STACK = ['Next.js', 'TypeScript', 'Tailwind', 'shadcn/ui', 'FastAPI', 'PostgreSQL + pgvector', 'Docker']

/** Server Component: Titel, die drei Schritte und der Techstack samt laufendem Modell aus /api/info. */
export function Seitenkopf({ info }: { info: Info | null }) {
  return (
    <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between sm:gap-8">
      <div>
        <h1 className="font-heading text-2xl font-semibold tracking-tight">Dokumente befragen</h1>
        <ul aria-label="So funktioniert es" className="mt-2 flex flex-col gap-1 text-sm text-muted-foreground">
          {SCHRITTE.map(schritt => (
            <li key={schritt} className="flex items-center gap-2">
              <CheckIcon aria-hidden className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
              {schritt}
            </li>
          ))}
        </ul>
      </div>

      <ul aria-label="Techstack" className="flex flex-wrap gap-1.5 sm:max-w-md sm:justify-end">
        {STACK.map(name => (
          <li key={name} className="flex">
            <Badge variant="outline">{name}</Badge>
          </li>
        ))}
        {info && (
          <>
            <li className="flex">
              <Badge variant="secondary" title={`${info.llm_modell} (${host(info)})`}>
                <CpuIcon aria-hidden />
                {`Modell: ${modellName(info)}`}
              </Badge>
            </li>
            <li className="flex">
              <Badge variant="secondary" title={info.embedder}>
                <BoxesIcon aria-hidden />
                {`Embedder: ${embedderName(info)}`}
              </Badge>
            </li>
          </>
        )}
      </ul>
    </header>
  )
}
