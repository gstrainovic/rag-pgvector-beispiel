import { ArrowLeftIcon } from 'lucide-react'
import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Datenschutz',
  description: 'Welche Daten die RAG-Demo bearbeitet, wohin sie gehen und wie lange sie bleiben.',
}

const MAIL = 'info@strainovic-it.ch'

/**
 * Statische Server Component. Jede Aussage hier beschreibt, was der Code tut: Cookie und Sitzung in
 * app/main.py, Grenzen und IP-Adressen in app/grenzen.py, Protokolle in deploy/. Wer dort etwas
 * ändert, passt diese Seite im selben Commit an.
 */
export default function Datenschutz() {
  return (
    <main className="min-h-0 flex-1 lg:overflow-y-auto">
      <article className="rechtstext mx-auto w-full max-w-3xl px-4 py-6">
        <Link href="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeftIcon aria-hidden className="size-4" />
          Zurück zur Demo
        </Link>

        <h1>Datenschutzerklärung</h1>
        <p className="stand">Stand: Oktober 2026</p>

        <h2>1. Verantwortliche Stelle</h2>
        <p>
          <strong>Goran Strainovic</strong>
          <br />
          Strainovic IT (Einzelfirma)
          <br />
          Bahnstrasse 9b
          <br />
          9323 Steinach
          <br />
          Schweiz
          <br />
          E-Mail: <a href={`mailto:${MAIL}`}>{MAIL}</a>
        </p>

        <h2>2. Grundsatz</h2>
        <p>
          Diese Seite ist eine öffentliche Demo: Sie zeigt, wie sich Fragen an Dokumente beantworten lassen. Es gibt
          kein Konto und keine Anmeldung. Wir bearbeiten Personendaten im Einklang mit dem Schweizer
          Datenschutzgesetz (DSG) und, soweit anwendbar, der EU-Datenschutz-Grundverordnung (DSGVO), und nur so
          weit, wie es für die Demo nötig ist.
        </p>
        <p>
          <strong>Bitte laden Sie keine vertraulichen oder personenbezogenen Dokumente hoch.</strong> Zum
          Ausprobieren genügen die drei fiktiven Beispieldokumente.
        </p>

        <h2>3. Welche Daten wir bearbeiten</h2>

        <h3>3.1 Hochgeladene Dateien</h3>
        <p>
          Aus einer hochgeladenen Datei lesen wir den Text aus, teilen ihn in Absätze und berechnen zu jedem Absatz
          einen Vektor für die Suche. Gespeichert werden der Dateiname, die Absätze, die Vektoren, der Zeitpunkt
          und die Kennung Ihrer Sitzung (Abschnitt 3.4). Die Datei selbst speichern wir nicht. Andere Besucher
          sehen Ihre Dokumente nicht, und sie fliessen nicht in deren Antworten ein.
        </p>

        <h3>3.2 Fragen und Antworten</h3>
        <p>
          Fragen und Antworten werden nicht gespeichert. Ihre Frage wird für die Suche und die Antwort verarbeitet
          (Abschnitt 4) und danach verworfen. Der Verlauf steht nur in Ihrem Browser-Tab und ist nach dem Neuladen
          der Seite weg.
        </p>

        <h3>3.3 IP-Adresse</h3>
        <p>
          Damit niemand die Demo mit Anfragen überlastet, zählen wir die Fragen pro Minute je IP-Adresse. Die
          Adresse liegt dafür höchstens zwei Minuten im Arbeitsspeicher des Servers. Sie wird weder in der
          Datenbank gespeichert noch in ein Zugriffsprotokoll geschrieben (Abschnitt 5).
        </p>

        <h3>3.4 Sitzungs-Cookie</h3>
        <p>
          Die Demo setzt ein einziges Cookie mit dem Namen <code>rag_sitzung</code>. Es enthält eine zufällige
          Kennung ohne Bezug zu Ihrer Person und dient einem Zweck: Ihre Uploads von denen anderer Besucher zu
          trennen. Es wird gesetzt, sobald Ihr Browser die Demo zum ersten Mal etwas fragt oder hochlädt, gilt
          30 Tage und ist für Skripte nicht lesbar. Es dient nicht dem Tracking. Wenn Sie es löschen oder ein
          privates Fenster öffnen, gelten Sie als neuer Besucher und sehen frühere Uploads nicht mehr.
        </p>

        <h3>3.5 Zähler</h3>
        <p>
          Wir zählen, wie viele Fragen und Uploads die Demo pro Tag insgesamt verarbeitet, um die Tagesgrenzen
          einzuhalten. Die Zähler sind reine Zahlen ohne Bezug zu Besuchern.
        </p>

        <h2>4. Weitergabe an Dritte</h2>
        <p>Wir verkaufen keine Daten. Eine Weitergabe erfolgt ausschliesslich an:</p>
        <div className="tabelle">
          <table>
            <thead>
              <tr>
                <th>Dienst</th>
                <th>Zweck</th>
                <th>Standort</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Mistral AI</td>
                <td>
                  Berechnung der Vektoren und der Antworten. Übermittelt werden der Text hochgeladener Dateien, der
                  Text Ihrer Frage und die dazu gefundenen Absätze.
                </td>
                <td>Frankreich (EU)</td>
              </tr>
              <tr>
                <td>Infomaniak Network SA</td>
                <td>Server, auf dem die Demo und ihre Datenbank laufen</td>
                <td>Schweiz</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          Mistral AI bearbeitet die Texte als Auftragsbearbeiter zur Berechnung der Antwort. Die Anfragen laufen
          über unseren Server mit unserem Mistral-Konto; Sie schliessen keinen eigenen Vertrag mit Mistral ab. Die
          Verwendung zum Training der Modelle ist in unserem Konto deaktiviert. Wie Mistral Daten bearbeitet,
          steht in der{' '}
          <a href="https://legal.mistral.ai/terms/privacy-policy" target="_blank" rel="noopener noreferrer">
            Datenschutzerklärung von Mistral AI
          </a>
          . IP-Adresse und Cookie gehen nicht an Mistral. Die Daten werden
          verschlüsselt übertragen (TLS). Schriften und Skripte kommen vom selben Server, es werden keine Inhalte
          von fremden Servern nachgeladen.
        </p>

        <h2>5. Speicherdauer</h2>
        <ul>
          <li>
            <strong>Eigene Uploads:</strong> 24 Stunden, danach werden sie automatisch gelöscht. Sie können sie
            vorher jederzeit selbst löschen.
          </li>
          <li>
            <strong>Beispieldokumente:</strong> dauerhaft. Es sind fiktive Texte ohne Personendaten.
          </li>
          <li>
            <strong>Fragen und Antworten:</strong> werden nicht gespeichert.
          </li>
          <li>
            <strong>IP-Adresse:</strong> höchstens zwei Minuten im Arbeitsspeicher.
          </li>
          <li>
            <strong>Sitzungs-Cookie:</strong> 30 Tage in Ihrem Browser.
          </li>
          <li>
            <strong>Zähler der Tagesgrenzen:</strong> dauerhaft, ohne Bezug zu Besuchern.
          </li>
          <li>
            <strong>Server-Protokolle:</strong> Die Demo führt kein Zugriffsprotokoll. Tritt ein technischer
            Fehler auf, schreibt der Server eine Fehlermeldung; der Webserver kann dabei die IP-Adresse der
            betroffenen Anfrage vermerken. Diese Fehlerprotokolle sind auf wenige Megabyte begrenzt und werden
            laufend überschrieben.
          </li>
        </ul>

        <h2>6. Cookies und Analyse</h2>
        <p>
          Die Demo nutzt keinen Analysedienst, keine Werbe-Cookies und kein Tracking. Das einzige Cookie
          ist das technisch notwendige Sitzungs-Cookie aus Abschnitt 3.4; darum gibt es auch kein Cookie-Banner.
        </p>

        <h2>7. Ihre Rechte</h2>
        <p>Nach dem Schweizer DSG und der DSGVO haben Sie folgende Rechte:</p>
        <ul>
          <li>
            <strong>Auskunft:</strong> Sie können Auskunft über die zu Ihnen gespeicherten Daten verlangen.
          </li>
          <li>
            <strong>Löschung:</strong> Sie können Ihre Uploads jederzeit selbst in der Demo löschen; spätestens nach
            24 Stunden geschieht das automatisch.
          </li>
          <li>
            <strong>Widerspruch:</strong> Sie können der Datenbearbeitung jederzeit widersprechen.
          </li>
        </ul>
        <p>
          Für die Ausübung Ihrer Rechte schreiben Sie an <a href={`mailto:${MAIL}`}>{MAIL}</a>. Weil die Demo
          Uploads nur einer zufälligen Kennung zuordnet, können wir sie einer Person nur zuordnen, wenn Sie uns
          den Wert Ihres Cookies nennen.
        </p>

        <h2>8. Aufsichtsbehörde</h2>
        <p>
          Zuständige Datenschutzbehörde in der Schweiz:
          <br />
          <strong>Eidgenössischer Datenschutz- und Öffentlichkeitsbeauftragter (EDÖB)</strong>
          <br />
          Feldeggweg 1, 3003 Bern
          <br />
          <a href="https://www.edoeb.admin.ch" target="_blank" rel="noopener noreferrer">www.edoeb.admin.ch</a>
        </p>

        <h2>9. Änderungen</h2>
        <p>
          Wir können diese Datenschutzerklärung jederzeit anpassen. Die aktuelle Version ist stets auf dieser Seite
          verfügbar.
        </p>
      </article>
    </main>
  )
}
