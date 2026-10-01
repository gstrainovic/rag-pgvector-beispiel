import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

afterEach(cleanup)

// «server-only» wirft ausserhalb des React-Server-Bündels; in Tests zählt nur die Logik.
vi.mock('server-only', () => ({}))

// jsdom kennt scrollTo auf Elementen nicht (der Chat bleibt beim Streamen unten).
Element.prototype.scrollTo ??= () => {}
