FROM python:3.11-slim

ENV POETRY_VERSION=2.3.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    REVIEW_MCP_HOST=0.0.0.0 \
    REVIEW_MCP_PORT=8002

WORKDIR /app/review_mcp_server

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY review_mcp_server/pyproject.toml review_mcp_server/poetry.lock ./
RUN poetry install --only main \
    --no-root \
    --no-interaction \
    --no-ansi

COPY review_mcp_server/ ./

EXPOSE 8002

CMD ["python", "src/server.py"]
