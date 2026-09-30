<script setup lang="ts">
import type { Quelle } from '../api'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import Textarea from 'primevue/textarea'
import { nextTick, ref, watch } from 'vue'
import QuellenListe from './QuellenListe.vue'

export interface Nachricht {
  id: number
  rolle: 'nutzer' | 'assistent'
  text: string
  quellen: Quelle[]
  fehler?: string
}

const props = withDefaults(defineProps<{ verlauf: Nachricht[], laden: boolean, vorschlaege?: string[] }>(), {
  vorschlaege: () => [],
})
const emit = defineEmits<{ senden: [text: string] }>()

marked.setOptions({ breaks: true })

function markdown(text: string): string {
  return DOMPurify.sanitize(marked.parse(text) as string)
}

const eingabe = ref('')
const verlaufElement = ref<HTMLElement | null>(null)

function senden(text = eingabe.value) {
  const t = text.trim()
  if (!t || props.laden)
    return
  emit('senden', t)
  eingabe.value = ''
}

function tastendruck(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    senden()
  }
}

// Beim Streamen unten bleiben
watch(() => props.verlauf.map(n => n.text.length), async () => {
  await nextTick()
  verlaufElement.value?.scrollTo({ top: verlaufElement.value.scrollHeight })
}, { deep: true })
</script>

<template>
  <div class="chat">
    <div ref="verlaufElement" class="verlauf">
      <div v-if="verlauf.length === 0" class="begruessung">
        <p>Stellen Sie eine Frage zu den geladenen Dokumenten. Die Antwort nennt die Absätze, auf die sie sich stützt.</p>
        <div v-if="vorschlaege.length" class="vorschlaege">
          <button
            v-for="v in vorschlaege"
            :key="v"
            type="button"
            class="vorschlag"
            data-test="vorschlag"
            @click="senden(v)"
          >
            <i class="pi pi-comment" /> {{ v }}
          </button>
        </div>
      </div>

      <div
        v-for="n in verlauf"
        :key="n.id"
        class="nachricht"
        :class="n.rolle"
        data-test="nachricht"
      >
        <div class="absender">
          {{ n.rolle === 'nutzer' ? 'Sie' : 'Assistent' }}
        </div>
        <div class="blase">
          <div v-if="n.text" class="chat-markdown" v-html="markdown(n.text)" />
          <ProgressSpinner v-else-if="!n.fehler" style="width: 20px; height: 20px" stroke-width="5" />
          <div v-if="n.fehler" class="fehler">
            <i class="pi pi-exclamation-triangle" /> {{ n.fehler }}
          </div>
          <QuellenListe v-if="n.rolle === 'assistent'" :quellen="n.quellen" />
        </div>
      </div>

      <div v-if="laden" class="ladehinweis" data-test="laden">
        <i class="pi pi-spin pi-spinner" /> Antwort wird erzeugt …
      </div>
    </div>

    <div class="eingabe">
      <Textarea
        v-model="eingabe"
        auto-resize
        rows="1"
        placeholder="Frage zu den Dokumenten … (Enter sendet, Shift+Enter neue Zeile)"
        class="feld"
        @keydown="tastendruck"
      />
      <Button
        icon="pi pi-send"
        rounded
        aria-label="Senden"
        :disabled="laden || !eingabe.trim()"
        @click="senden()"
      />
    </div>
  </div>
</template>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.verlauf {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0.25rem 0.25rem 1rem;
}

.begruessung {
  color: var(--p-text-muted-color);
}

.begruessung p {
  margin: 0 0 0.75rem;
}

.vorschlaege {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.vorschlag {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 0.85rem;
  border-radius: 1.5rem;
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 40%, transparent);
  background: color-mix(in srgb, var(--p-primary-color) 8%, transparent);
  color: var(--p-primary-color);
  font: inherit;
  font-size: 0.85rem;
  cursor: pointer;
  text-align: left;
}

.vorschlag:hover {
  background: color-mix(in srgb, var(--p-primary-color) 18%, transparent);
}

.nachricht {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  max-width: 85%;
}

.nachricht.nutzer {
  align-self: flex-end;
  align-items: flex-end;
}

.absender {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.blase {
  padding: 0.6rem 0.9rem;
  border-radius: 1rem;
  background: var(--p-surface-card, #fff);
  border: 1px solid var(--p-surface-border, #e2e8f0);
}

.nutzer .blase {
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color, #fff);
  border-color: transparent;
}

.fehler {
  color: var(--p-red-500, #dc2626);
  font-size: 0.9rem;
}

.ladehinweis {
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

.eingabe {
  display: flex;
  gap: 0.5rem;
  align-items: flex-end;
  padding-top: 0.5rem;
  border-top: 1px solid var(--p-surface-border, #e2e8f0);
}

.feld {
  flex: 1;
  max-height: 8rem;
}
</style>
