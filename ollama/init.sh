#!/bin/sh
# Läuft einmal beim «docker compose up» im Dienst ollama-init: lädt die Modelle in das
# Ollama-Volume und legt die CPU-Variante des Embedders an. Idempotent.
set -eu

CHAT_MODELL="${LLM_MODEL:-qwen3:4b-instruct-2507-q4_K_M}"
EMBED_BASIS="qwen3-embedding:0.6b"

echo "Warte auf Ollama unter $OLLAMA_HOST ..."
until ollama list >/dev/null 2>&1; do sleep 1; done

echo "Lade $CHAT_MODELL ..."
ollama pull "$CHAT_MODELL"
echo "Lade $EMBED_BASIS ..."
ollama pull "$EMBED_BASIS"
echo "Lege qwen3-embedding-cpu an ..."
ollama create qwen3-embedding-cpu -f /init/Modelfile.qwen3-embedding-cpu
echo "Modelle bereit:"
ollama list
