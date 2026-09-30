# Stufe 1: Web-Oberfläche bauen (Vue 3 + Vite)
FROM node:24-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# Stufe 2: API (FastAPI) mit der gebauten Oberfläche
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.10 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    WEB_DIST=/app/web/dist

WORKDIR /app

# Abhängigkeiten zuerst, damit der Layer bei Codeänderungen erhalten bleibt.
# fastembed (ONNX-Laufzeit, ~200 MB) nur auf Wunsch: --build-arg EXTRAS=fastembed
ARG EXTRAS=""
COPY pyproject.toml uv.lock ./
RUN if [ -n "$EXTRAS" ]; then uv sync --frozen --no-dev --no-install-project --extra "$EXTRAS"; \
    else uv sync --frozen --no-dev --no-install-project; fi

COPY app ./app
COPY sql ./sql
COPY --from=web /web/dist ./web/dist

RUN useradd --create-home rag && mkdir -p /modelle && chown rag:rag /modelle
USER rag
ENV FASTEMBED_CACHE_PATH=/modelle

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "--factory", "app.main:app_aus_umgebung", "--host", "0.0.0.0", "--port", "8000"]
