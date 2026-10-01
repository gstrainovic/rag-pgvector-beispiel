'use client'

import DOMPurify from 'dompurify'
import { marked } from 'marked'

/**
 * Antwort des Sprachmodells als Markdown. Der Text stammt aus einem Modell, das fremde
 * Dokumente gelesen hat, darum läuft das erzeugte HTML durch DOMPurify. Ohne DOM (auf dem
 * Server) kann DOMPurify nicht filtern; dort bleibt es bei reinem Text.
 */
export function AntwortMarkdown({ text }: { text: string }) {
  if (!DOMPurify.isSupported)
    return <div className="antwort whitespace-pre-wrap">{text}</div>
  const html = DOMPurify.sanitize(marked.parse(text, { async: false, breaks: true }))
  return <div className="antwort" dangerouslySetInnerHTML={{ __html: html }} />
}
