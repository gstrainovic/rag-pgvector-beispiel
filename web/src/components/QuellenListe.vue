<script setup lang="ts">
import type { Quelle } from '../api'
import { ref } from 'vue'

defineProps<{ quellen: Quelle[] }>()
const offen = ref(false)

function prozent(score: number): string {
  return `${Math.round(score * 100)} %`
}
</script>

<template>
  <div v-if="quellen.length" class="quellen">
    <button type="button" class="quellen-kopf" data-test="quellen-kopf" @click="offen = !offen">
      <i :class="offen ? 'pi pi-chevron-down' : 'pi pi-chevron-right'" />
      {{ quellen.length === 1 ? '1 Quelle' : `${quellen.length} Quellen` }}
    </button>
    <ol v-if="offen" class="quellen-liste">
      <li v-for="(q, i) in quellen" :key="i" class="quelle" data-test="quelle">
        <div class="quelle-kopf">
          <span class="quelle-titel"><i class="pi pi-file" /> {{ q.titel }}</span>
          <span v-tooltip.left="'Ähnlichkeit zur Frage'" class="quelle-score">{{ prozent(q.score) }}</span>
        </div>
        <blockquote class="quelle-absatz">
          {{ q.absatz }}
        </blockquote>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.quellen {
  margin-top: 0.5rem;
  font-size: 0.85rem;
}

.quellen-kopf {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: none;
  border: none;
  padding: 0.2rem 0;
  color: var(--p-primary-color);
  cursor: pointer;
  font: inherit;
  font-weight: 500;
}

.quellen-liste {
  margin: 0.25rem 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.quelle {
  border-left: 3px solid color-mix(in srgb, var(--p-primary-color) 50%, transparent);
  padding-left: 0.6rem;
}

.quelle-kopf {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  font-weight: 500;
}

.quelle-score {
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
}

.quelle-absatz {
  margin: 0.2rem 0 0;
  color: var(--p-text-muted-color);
  line-height: 1.4;
}
</style>
