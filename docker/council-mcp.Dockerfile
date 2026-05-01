FROM python:3.11-slim

ENV POETRY_VERSION=2.2.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    COUNCIL_MCP_HOST=0.0.0.0 \
    COUNCIL_MCP_PORT=8003 \
    COUNCIL_TRANSCRIPTS_DIR=transcripts \
    COUNCIL_DECISION_GRAPH_DB_PATH=/app/council_mcp_server/decision_graph_data/decision_graph.db

WORKDIR /app/council_mcp_server

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY council_mcp_server/pyproject.toml council_mcp_server/poetry.lock ./
RUN poetry install --only main --no-root --no-interaction --no-ansi

COPY council_mcp_server/ ./
RUN mkdir -p /app/council_mcp_server/transcripts /app/council_mcp_server/decision_graph_data

EXPOSE 8003

CMD ["poetry", "run", "python", "server_http.py"]
