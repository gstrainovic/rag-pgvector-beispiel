'use server'

/**
 * Server-Aktion für das Löschen: Sie läuft auf dem Next-Server, ruft die FastAPI im internen
 * Netz und frischt danach die Seite auf, sodass die Dokumentliste neu vom Server kommt.
 * Der Datei-Upload geht nicht über eine Aktion, sondern als Strom über /api (siehe
 * app/api/[...pfad]/route.ts), damit 20-MB-Dateien nicht im Speicher des Next-Servers landen.
 */

import { refresh } from 'next/cache'
import { cookies } from 'next/headers'
import { apiAnfrage } from '@/lib/api-server'
import { meldung } from '@/lib/fehler'
import type { Ergebnis } from '@/lib/typen'

export async function dokumentLoeschen(id: number): Promise<Ergebnis<null>> {
  // Aktionen sind öffentliche Endpunkte: Eingaben prüfen wie bei jeder API.
  // Ob das Dokument dem Besucher gehört, entscheidet die API anhand seines Sitzungs-Cookies.
  if (!Number.isSafeInteger(id) || id < 1)
    return { ok: false, fehler: 'Ungültige Dokument-ID' }
  try {
    await apiAnfrage(`/api/dokumente/${id}`, (await cookies()).toString(), { method: 'DELETE' })
    refresh()
    return { ok: true, wert: null }
  }
  catch (e) {
    return { ok: false, fehler: meldung(e) }
  }
}
