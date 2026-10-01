# API (FastAPI). Die Oberfläche hat ihr eigenes Image: web/Dockerfile.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.10 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Abhängigkeiten zuerst, damit der Layer bei Codeänderungen erhalten bleibt.
# fastembed (ONNX-Laufzeit, ~200 MB) nur auf Wunsch: --build-arg EXTRAS=fastembed
ARG EXTRAS=""
COPY pyproject.toml uv.lock ./
RUN if [ -n "$EXTRAS" ]; then uv sync --frozen --no-dev --no-install-project --extra "$EXTRAS"; \
    else uv sync --frozen --no-dev --no-install-project; fi

COPY app ./app
COPY sql ./sql

RUN useradd --create-home rag && mkdir -p /modelle && chown rag:rag /modelle
USER rag
ENV FASTEMBED_CACHE_PATH=/modelle

EXPOSE 8000
# Kein Zugriffsprotokoll: so landen weder Adressen noch Pfade der Besucher in den Container-Logs
# (zugesagt in der Datenschutzerklärung, web/src/app/datenschutz/page.tsx).
CMD ["uv", "run", "--no-sync", "uvicorn", "--factory", "app.main:app_aus_umgebung", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
