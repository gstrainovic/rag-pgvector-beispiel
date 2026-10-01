import { FolderOpenIcon, MessagesSquareIcon, TriangleAlertIcon } from 'lucide-react'
import { cookies } from 'next/headers'
import { ChatBereich } from '@/components/chat-bereich'
import { DokumentBereich } from '@/components/dokument-bereich'
import { Seitenkopf } from '@/components/seitenkopf'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { holeStartdaten } from '@/lib/api-server'

const VORSCHLAEGE = [
  'Wann ist Nachtruhe in der Siedlung Sonnenhof?',
  'Was bedeutet der Störungscode E12 bei der Heizung?',
  'Wie lange dauert die Anfertigung einer Einbauküche?',
]

/**
 * Server Component: holt Modell-Info, Dokumentliste und Beispieldateien direkt bei der FastAPI
 * (internes Netz) und liefert fertiges HTML. cookies() macht die Seite dynamisch; das Sitzungs-
 * Cookie des Besuchers geht an die API, damit die Liste neben den Beispielen seine Uploads zeigt.
 * Interaktiv sind nur die beiden Client Components DokumentBereich und ChatBereich.
 */
export default async function Startseite() {
  const { info, dokumente, beispiele, fehler } = await holeStartdaten((await cookies()).toString())

  return (
    <main className="mx-auto flex min-h-0 w-full max-w-6xl flex-1 flex-col gap-4 px-4 pt-4">
      <Seitenkopf info={info} />

      {fehler && (
        <Alert variant="destructive">
          <TriangleAlertIcon aria-hidden />
          <AlertTitle>Die Demo ist gerade nicht erreichbar</AlertTitle>
          <AlertDescription>{fehler}</AlertDescription>
        </Alert>
      )}

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(18rem,1fr)_2fr]">
        <Card className="min-h-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-muted-foreground">
              <FolderOpenIcon aria-hidden className="size-4" />
              <h2>Dokumente</h2>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col">
            <DokumentBereich dokumente={dokumente} beispiele={beispiele} />
          </CardContent>
        </Card>

        <Card className="min-h-[60vh] bg-muted/40 lg:min-h-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-muted-foreground">
              <MessagesSquareIcon aria-hidden className="size-4" />
              <h2>Fragen</h2>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col">
            <ChatBereich vorschlaege={dokumente.length > 0 ? VORSCHLAEGE : []} />
          </CardContent>
        </Card>
      </div>
    </main>
  )
}
