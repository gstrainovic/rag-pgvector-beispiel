# Oberfläche (Next.js) als eigenständiger Node-Server, nach dem Muster des offiziellen
# Next-Beispiels «with-docker»: output: 'standalone' kopiert nur, was zur Laufzeit gebraucht wird.

FROM node:24-alpine AS basis
ENV NEXT_TELEMETRY_DISABLED=1

# Stufe 1: Abhängigkeiten, eigener Layer, damit Codeänderungen ihn nicht verwerfen
FROM basis AS abhaengigkeiten
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Stufe 2: Build. API_URL wird hier nicht gebraucht: die Startseite wird je Anfrage gerendert,
# der Route Handler liest die Adresse zur Laufzeit.
FROM basis AS build
WORKDIR /app
COPY --from=abhaengigkeiten /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Stufe 3: Laufzeit ohne node_modules, npm-Cache und Quelltext, als Benutzer «node» (nicht root)
FROM basis AS laufzeit
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
