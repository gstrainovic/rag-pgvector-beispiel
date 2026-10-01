import { defineConfig } from 'vitest/config'

// JSX übersetzt Vite selbst (automatische Laufzeit laut tsconfig), der Alias «@/» kommt aus
// tsconfig.json. @vitejs/plugin-react bräuchte es nur für Fast Refresh im Browser.
export default defineConfig({
  resolve: { tsconfigPaths: true },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    setupFiles: ['src/test/setup.ts'],
    restoreMocks: true,
  },
})
