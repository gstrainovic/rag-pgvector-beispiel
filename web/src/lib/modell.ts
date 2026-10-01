import type { Info } from './typen'

const LOKALE_HOSTS = ['localhost', '127.0.0.1', 'ollama', 'host.docker.internal']

const MODELLE: [RegExp, string][] = [
  [/^mistral-small/, 'Mistral Small'],
  [/^mistral-medium/, 'Mistral Medium'],
  [/^mistral-large/, 'Mistral Large'],
  [/^qwen3:4b/, 'Qwen3 4B'],
]

const EMBEDDER: [RegExp, string][] = [
  [/^mistral-embed/, 'Mistral Embed'],
  [/^qwen3-embedding/, 'Qwen3 Embedding'],
  [/^fastembed:.*MiniLM/, 'fastembed MiniLM'],
]

export function host(info: Info): string {
  try {
    return new URL(info.llm_basis_url).hostname
  }
  catch {
    return ''
  }
}

function lesbar(name: string, bekannte: [RegExp, string][]): string {
  return bekannte.find(([muster]) => muster.test(name))?.[1] ?? name
}

/** «Mistral Small» oder «Qwen3 4B lokal»: Anzeigename des Sprachmodells für den Kopf der Seite. */
export function modellName(info: Info): string {
  const name = lesbar(info.llm_modell, MODELLE)
  return LOKALE_HOSTS.includes(host(info)) ? `${name} lokal` : name
}

/** fastembed rechnet immer im API-Container; sonst läuft der Embedder dort, wo auch das Sprachmodell läuft. */
export function embedderName(info: Info): string {
  const name = lesbar(info.embedder, EMBEDDER)
  const lokal = info.embedder.startsWith('fastembed:') || LOKALE_HOSTS.includes(host(info))
  return lokal ? `${name} lokal` : name
}
