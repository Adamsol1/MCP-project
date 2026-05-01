FROM python:3.11-slim

ENV POETRY_VERSION=2.3.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MCP_SERVER_HOST=0.0.0.0 \
    MCP_SERVER_PORT=8001

WORKDIR /app/generation_mcp_server

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY generation_mcp_server/pyproject.toml generation_mcp_server/poetry.lock ./
RUN poetry install --only main \
    --no-root \
    --no-interaction \
    --no-ansi

COPY generation_mcp_server/ ./
RUN mkdir -p /app/backend/data

EXPOSE 8001

CMD ["python", "src/server.py"]
