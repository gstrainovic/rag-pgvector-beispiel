import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import Tooltip from 'primevue/tooltip'
import { createApp } from 'vue'
import App from './App.vue'

import 'primeicons/primeicons.css'
import './style.css'

const app = createApp(App)
app.directive('tooltip', Tooltip)
app.use(PrimeVue, {
  theme: { preset: Aura, options: { darkModeSelector: '.dark-mode' } },
})
app.mount('#app')
