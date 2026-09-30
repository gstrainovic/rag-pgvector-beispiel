<script setup lang="ts">
import type { Info } from '../api'
import Tag from 'primevue/tag'
import { computed } from 'vue'

const props = defineProps<{ info: Info | null }>()

const host = computed(() => {
  try {
    return new URL(props.info?.llm_basis_url ?? '').hostname
  }
  catch {
    return ''
  }
})
const istLokal = computed(() => ['localhost', '127.0.0.1', 'ollama'].includes(host.value))
const dokumente = computed(() => {
  const n = props.info?.anzahl_dokumente ?? 0
  return n === 1 ? '1 Dokument' : `${n} Dokumente`
})
</script>

<template>
  <div class="modell-hinweis">
    <template v-if="info">
      <span v-tooltip.bottom="'Sprachmodell, das die Antworten schreibt'" class="eintrag">
        <i class="pi pi-microchip-ai" />
        <span class="wert">{{ info.llm_modell }}</span>
        <Tag :value="istLokal ? 'lokal' : host" :severity="istLokal ? 'success' : 'info'" />
      </span>
      <span v-tooltip.bottom="'Modell, das Text in Vektoren für die Suche umwandelt'" class="eintrag">
        <i class="pi pi-sitemap" />
        <span class="wert">{{ info.embedder }}</span>
      </span>
      <span class="eintrag">
        <i class="pi pi-file" />
        {{ dokumente }}
      </span>
    </template>
    <span v-else class="eintrag">
      <i class="pi pi-spin pi-spinner" /> Verbinde mit der API …
    </span>
  </div>
</template>

<style scoped>
.modell-hinweis {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 1.25rem;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

.eintrag {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.wert {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--p-text-color);
}
</style>
