// jsdom kennt keinen ResizeObserver; PrimeVue Textarea (auto-resize) braucht ihn beim Mounten.
class ResizeObserverAttrappe {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver ??= ResizeObserverAttrappe as unknown as typeof ResizeObserver
