import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Eigenständiger Server in .next/standalone: das Laufzeit-Image braucht weder node_modules noch npm
  output: 'standalone',
  // Caddy komprimiert vor dem Browser. Hier ausgeschaltet, weil gzip die SSE-Antwort von
  // /api/frage sammeln würde, statt jedes Textstück sofort weiterzugeben.
  compress: false,
  poweredByHeader: false,
}

export default nextConfig
