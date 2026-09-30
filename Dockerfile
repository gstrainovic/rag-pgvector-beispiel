FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.10 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    FASTEMBED_CACHE_PATH=/modelle

WORKDIR /app

# Abhängigkeiten zuerst, damit der Layer bei Codeänderungen erhalten bleibt
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY sql ./sql

RUN useradd --create-home rag && mkdir -p /modelle && chown rag:rag /modelle
USER rag

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "--factory", "app.main:app_aus_umgebung", "--host", "0.0.0.0", "--port", "8000"]
