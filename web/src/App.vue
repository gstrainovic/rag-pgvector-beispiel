<script setup lang="ts">
import type { Dokument, Info } from './api'
import type { Nachricht } from './components/ChatBereich.vue'
import Message from 'primevue/message'
import { onMounted, ref } from 'vue'
import * as api from './api'
import ChatBereich from './components/ChatBereich.vue'
import DokumentListe from './components/DokumentListe.vue'
import ModellHinweis from './components/ModellHinweis.vue'

const info = ref<Info | null>(null)
const dokumente = ref<Dokument[]>([])
const verlauf = ref<Nachricht[]>([])
const dokumenteLaden = ref(false)
const antwortLaeuft = ref(false)
const fehler = ref('')
let naechsteId = 1

const VORSCHLAEGE = [
  'Wann ist Nachtruhe in der Siedlung Sonnenhof?',
  'Was bedeutet der Störungscode E12 bei der Heizung?',
  'Wie lange dauert die Anfertigung einer Einbauküche?',
]

async function aktualisieren() {
  try {
    ;[info.value, dokumente.value] = await Promise.all([api.holeInfo(), api.holeDokumente()])
    fehler.value = ''
  }
  catch (e) {
    fehler.value = `API nicht erreichbar: ${(e as Error).message}`
  }
}

async function mitLadeanzeige(aktion: () => Promise<unknown>) {
  dokumenteLaden.value = true
  fehler.value = ''
  try {
    await aktion()
  }
  catch (e) {
    fehler.value = (e as Error).message
  }
  finally {
    dokumenteLaden.value = false
    await aktualisieren()
  }
}

const hochladen = (dateien: File[]) => mitLadeanzeige(() => api.ladeHoch(dateien))
const loeschen = (id: number) => mitLadeanzeige(() => api.loesche(id))
const beispiele = () => mitLadeanzeige(() => api.ladeBeispiele())

async function fragen(text: string) {
  verlauf.value.push({ id: naechsteId++, rolle: 'nutzer', text, quellen: [] })
  const antwort: Nachricht = { id: naechsteId++, rolle: 'assistent', text: '', quellen: [] }
  verlauf.value.push(antwort)
  const ziel = verlauf.value[verlauf.value.length - 1]!
  antwortLaeuft.value = true
  try {
    await api.frage(text, (e) => {
      if (e.typ === 'quellen')
        ziel.quellen = e.quellen
      else if (e.typ === 'token')
        ziel.text += e.text
      else if (e.typ === 'fehler')
        ziel.fehler = e.meldung
    })
  }
  catch (e) {
    ziel.fehler = (e as Error).message
  }
  finally {
    antwortLaeuft.value = false
  }
}

onMounted(aktualisieren)
</script>

<template>
  <div class="seite">
    <header class="kopf">
      <div class="kopf-titel">
        <h1>Dokumente befragen</h1>
        <p>Eigene Dateien hochladen, Fragen stellen, Antworten mit Quellenangabe – alles lokal, ohne Cloud-Schlüssel.</p>
      </div>
      <ModellHinweis :info="info" />
    </header>

    <Message v-if="fehler" severity="error" :closable="true" class="fehler" @close="fehler = ''">
      {{ fehler }}
    </Message>

    <main class="inhalt">
      <section class="bereich dokumente">
        <h2><i class="pi pi-folder-open" /> Dokumente</h2>
        <DokumentListe
          :dokumente="dokumente"
          :laden="dokumenteLaden"
          @hochladen="hochladen"
          @loeschen="loeschen"
          @beispiele="beispiele"
        />
      </section>
      <section class="bereich chat">
        <h2><i class="pi pi-comments" /> Fragen</h2>
        <ChatBereich
          :verlauf="verlauf"
          :laden="antwortLaeuft"
          :vorschlaege="dokumente.length ? VORSCHLAEGE : []"
          @senden="fragen"
        />
      </section>
    </main>
  </div>
</template>

<style scoped>
.seite {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
  gap: 1rem;
}

.kopf {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-end;
  gap: 0.5rem 2rem;
}

.kopf h1 {
  margin: 0;
  font-size: 1.5rem;
}

.kopf p {
  margin: 0.25rem 0 0;
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
}

.inhalt {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(260px, 1fr) 2fr;
  gap: 1rem;
}

.bereich {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--p-surface-card, #fff);
  border: 1px solid var(--p-surface-border, #e2e8f0);
  border-radius: 1rem;
  padding: 1rem;
}

.bereich h2 {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-muted-color);
}

.bereich.chat {
  background: var(--p-surface-ground, #f6f7f9);
}

.bereich > :last-child {
  flex: 1;
  min-height: 0;
}

.fehler {
  margin: 0;
}

/* Handy: untereinander, Chat bekommt den grösseren Teil */
@media (max-width: 760px) {
  .seite {
    height: auto;
    min-height: 100%;
  }

  .inhalt {
    grid-template-columns: 1fr;
    grid-template-rows: auto minmax(60vh, auto);
  }
}
</style>
