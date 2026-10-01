import Link from 'next/link'

const LINK = 'underline-offset-3 hover:text-foreground hover:underline'

/** Steht im Root-Layout und damit unter jeder Seite. */
export function Fusszeile() {
  return (
    <footer className="mx-auto flex w-full max-w-6xl shrink-0 flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-xs text-muted-foreground">
      <span>RAG-Demo von Strainovic IT</span>
      <nav aria-label="Rechtliches und Quellcode" className="flex flex-wrap gap-x-4 gap-y-1 sm:ml-auto">
        <Link href="/datenschutz" className={LINK}>Datenschutz</Link>
        <a href="https://www.strainovic-it.ch/impressum/" target="_blank" rel="noopener noreferrer" className={LINK}>Impressum</a>
        <a href="https://github.com/gstrainovic/rag-pgvector-beispiel" target="_blank" rel="noopener noreferrer" className={LINK}>Code auf GitHub</a>
      </nav>
    </footer>
  )
}
