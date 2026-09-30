import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import Tooltip from 'primevue/tooltip'

/** Globale Optionen für mount(): PrimeVue-Plugin und Tooltip-Direktive wie in main.ts */
export const globalOptionen = {
  plugins: [[PrimeVue, { theme: { preset: Aura } }]],
  directives: { tooltip: Tooltip },
}
