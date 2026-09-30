<script setup lang="ts">
import type { Dokument } from '../api'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import { ref } from 'vue'

defineProps<{ dokumente: Dokument[], laden: boolean }>()
const emit = defineEmits<{
  hochladen: [dateien: File[]]
  loeschen: [id: number]
  beispiele: []
}>()

const dateiFeld = ref<HTMLInputElement | null>(null)
const ziehen = ref(false)

function waehlen() {
  dateiFeld.value?.click()
}

function ausFeld(e: Event) {
  const input = e.target as HTMLInputElement
  const dateien = Array.from(input.files ?? [])
  if (dateien.length)
    emit('hochladen', dateien)
  input.value = ''
}

function abgelegt(e: DragEvent) {
  e.preventDefault()
  ziehen.value = false
  const dateien = Array.from(e.dataTransfer?.files ?? [])
  if (dateien.length)
    emit('hochladen', dateien)
}

function symbol(titel: string): string {
  return titel.toLowerCase().endsWith('.pdf') ? 'pi pi-file-pdf' : 'pi pi-file'
}
</script>

<template>
  <div class="dokumente">
    <div
      class="dropzone"
      :class="{ aktiv: ziehen }"
      data-test="dropzone"
      role="button"
      tabindex="0"
      @click="waehlen"
      @keydown.enter="waehlen"
      @dragenter.prevent="ziehen = true"
      @dragover.prevent="ziehen = true"
      @dragleave.prevent="ziehen = false"
      @drop="abgelegt"
    >
      <input
        ref="dateiFeld"
        type="file"
        accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
        multiple
        hidden
        @change="ausFeld"
      >
      <ProgressSpinner v-if="laden" data-test="laden" style="width: 2rem; height: 2rem" stroke-width="5" />
      <i v-else class="pi pi-cloud-upload" style="font-size: 2rem" />
      <div class="dropzone-text">
        <strong>{{ laden ? 'Wird verarbeitet …' : 'Dateien hierher ziehen oder klicken' }}</strong>
        <small>PDF, TXT oder Markdown, bis 20 MB</small>
      </div>
    </div>

    <div v-if="dokumente.length === 0" class="leer">
      <p>Noch keine Dokumente. Laden Sie eigene Dateien hoch oder probieren Sie die Beispiele.</p>
      <Button
        label="Beispieldokumente laden"
        icon="pi pi-sparkles"
        data-test="beispiele"
        :loading="laden"
        @click="emit('beispiele')"
      />
    </div>

    <ul v-else class="liste">
      <li v-for="d in dokumente" :key="d.id" class="dokument" data-test="dokument">
        <i :class="symbol(d.titel)" class="dokument-symbol" />
        <div class="dokument-text">
          <div class="dokument-titel">{{ d.titel }}</div>
          <small>{{ d.anzahl_absaetze }} {{ d.anzahl_absaetze === 1 ? 'Absatz' : 'Absätze' }}</small>
        </div>
        <Button
          v-tooltip.left="'Dokument löschen'"
          icon="pi pi-trash"
          text
          rounded
          severity="secondary"
          aria-label="Dokument löschen"
          data-test="loeschen"
          @click="emit('loeschen', d.id)"
        />
      </li>
    </ul>

    <div v-if="dokumente.length" class="fuss">
      <Button
        label="Beispieldokumente laden"
        icon="pi pi-sparkles"
        text
        size="small"
        data-test="beispiele"
        :loading="laden"
        @click="emit('beispiele')"
      />
    </div>
  </div>
</template>

<style scoped>
.dokumente {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  height: 100%;
}

.dropzone {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border: 2px dashed var(--p-surface-border, #cbd5e1);
  border-radius: 0.75rem;
  cursor: pointer;
  color: var(--p-text-muted-color);
  transition: all 0.15s;
}

.dropzone:hover,
.dropzone.aktiv {
  border-color: var(--p-primary-color);
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 8%, transparent);
}

.dropzone-text {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.leer {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.75rem;
  color: var(--p-text-muted-color);
}

.leer p {
  margin: 0;
}

.liste {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  overflow-y: auto;
}

.dokument {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.25rem 0.5rem 0.5rem;
  border-radius: 0.5rem;
}

.dokument:hover {
  background: color-mix(in srgb, var(--p-text-color) 5%, transparent);
}

.dokument-symbol {
  font-size: 1.25rem;
  color: var(--p-primary-color);
}

.dokument-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.dokument-titel {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.fuss {
  margin-top: auto;
}
</style>
