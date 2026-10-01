'use client'

import { ChevronRightIcon, FileTextIcon } from 'lucide-react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import type { Quelle } from '@/lib/typen'

function prozent(score: number): string {
  return `${Math.round(score * 100)} %`
}

/** Aufklappbare Liste der Absätze, auf die sich eine Antwort stützt. */
export function QuellenListe({ quellen }: { quellen: Quelle[] }) {
  if (quellen.length === 0)
    return null
  return (
    <Collapsible className="mt-2 text-sm">
      <CollapsibleTrigger className="group inline-flex items-center gap-1 rounded-md py-0.5 font-medium text-muted-foreground outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50">
        <ChevronRightIcon aria-hidden className="size-4 transition-transform group-data-panel-open:rotate-90" />
        {quellen.length === 1 ? '1 Quelle' : `${quellen.length} Quellen`}
      </CollapsibleTrigger>
      <CollapsibleContent>
        <ol className="mt-1 flex flex-col gap-2">
          {quellen.map((q, i) => (
            <li key={i} className="border-l-2 border-border pl-2.5">
              <div className="flex justify-between gap-2 font-medium">
                <span className="inline-flex min-w-0 items-center gap-1.5">
                  <FileTextIcon aria-hidden className="size-3.5 shrink-0" />
                  <span className="truncate">{q.titel}</span>
                </span>
                <span className="whitespace-nowrap text-muted-foreground tabular-nums" title="Ähnlichkeit zur Frage">
                  {prozent(q.score)}
                </span>
              </div>
              <blockquote className="mt-0.5 leading-snug text-muted-foreground">{q.absatz}</blockquote>
            </li>
          ))}
        </ol>
      </CollapsibleContent>
    </Collapsible>
  )
}
