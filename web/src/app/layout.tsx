import type { Metadata, Viewport } from 'next'
import { Geist } from 'next/font/google'
import { Fusszeile } from '@/components/fusszeile'
import { Toaster } from '@/components/ui/sonner'
import './globals.css'

// next/font lädt die Schrift beim Build und liefert sie vom eigenen Server aus: keine Anfrage an Google im Browser
const geist = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })

export const metadata: Metadata = {
  title: { default: 'Dokumente befragen – RAG-Demo', template: '%s – RAG-Demo' },
  description: 'Dateien hochladen, Fragen stellen, Antworten mit Quellenangabe. RAG mit Next.js, FastAPI und pgvector.',
}

export const viewport: Viewport = {
  colorScheme: 'light dark',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de" className={`${geist.variable} antialiased`}>
      {/* Ab Desktop-Breite füllt die Seite genau das Fenster, der Chat scrollt in sich; auf dem Handy scrollt die Seite */}
      <body className="flex min-h-dvh flex-col lg:h-dvh">
        {children}
        <Fusszeile />
        <Toaster position="top-center" />
      </body>
    </html>
  )
}
