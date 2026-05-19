#!/usr/bin/env bash
set -e

# IDE Python extensions (VS Code, etc.) can set VIRTUAL_ENV to point at the
# selected interpreter — even when it's a system Python, not a real venv.
# Poetry honors VIRTUAL_ENV and skips venv creation, installing every project
# into the same site-packages where they overwrite each other's deps.
unset VIRTUAL_ENV

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing root npm dependencies..."
cd "$ROOT" && npm install

echo "==> Installing frontend npm dependencies..."
cd "$ROOT/frontend" && npm install

for dir in backend council_mcp_server generation_mcp_server review_mcp_server; do
  if [ -f "$ROOT/$dir/pyproject.toml" ]; then
    echo "==> Checking poetry lock in $dir..."
    cd "$ROOT/$dir"
    if [ ! -f "poetry.lock" ] || ! poetry check --lock 2>/dev/null; then
      echo "    Lock file missing or stale — running poetry lock..."
      poetry lock
    fi
    echo "==> Running poetry install in $dir..."
    poetry install
    if [ "$dir" = "backend" ]; then
      mkdir -p "$ROOT/backend/data/logs"
      echo "==> Running database migrations in $dir..."
      poetry run alembic -c alembic_sessions.ini upgrade head
      poetry run alembic -c alembic_knowledge.ini upgrade head
      echo "==> Seeding knowledge database in $dir..."
      poetry run python scripts/seed_knowledge.py
      echo "==> Seeding perspective documents in $dir..."
      poetry run python scripts/seed_perspective_docs.py
    fi
  fi
done

echo ""
echo "All dependencies installed."
