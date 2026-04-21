#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing root npm dependencies..."
cd "$ROOT" && npm install

echo "==> Installing frontend npm dependencies..."
cd "$ROOT/frontend" && npm install

for dir in backend council_mcp_server generation_mcp_server review_mcp_server; do
  if [ -f "$ROOT/$dir/pyproject.toml" ]; then
    echo "==> Running poetry install in $dir..."
    cd "$ROOT/$dir" && poetry install
  fi
done

echo ""
echo "All dependencies installed."
