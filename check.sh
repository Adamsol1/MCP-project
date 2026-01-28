#!/usr/bin/env bash
# ============================================
# MCP Threat Intelligence MVP - Pre-Push Check Script
# ============================================
# Cross-platform script for Linux, macOS, and Git Bash on Windows
# Run this manually with: ./check.sh
# Or configure as a git pre-push hook

set -e  # Exit on first error

echo "========================================"
echo "MCP-TI MVP - Code Quality Checks"
echo "========================================"
echo ""

# Track if any checks fail
FAILED=0

# Detect Python command (python3 on Linux/macOS, python on Windows)
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python not found. Install Python 3.11+"
    exit 1
fi

# Detect Poetry command
if command -v poetry &> /dev/null; then
    POETRY_CMD="poetry"
elif $PYTHON_CMD -m poetry --version &> /dev/null 2>&1; then
    POETRY_CMD="$PYTHON_CMD -m poetry"
else
    echo "❌ Error: Poetry not found."
    echo "   Install Poetry: curl -sSL https://install.python-poetry.org | $PYTHON_CMD -"
    echo "   Or: pip install poetry"
    exit 1
fi

echo "Using Python: $PYTHON_CMD"
echo "Using Poetry: $POETRY_CMD"
echo ""

# ============================================
# Backend Checks (Python)
# ============================================
echo "🐍 Running Backend Checks..."
echo "----------------------------------------"

cd backend || exit 1

echo "  → Running Ruff linter..."
if $POETRY_CMD run ruff check .; then
    echo "    ✅ Ruff linting passed"
else
    echo "    ❌ Ruff linting failed"
    FAILED=1
fi

echo "  → Running Ruff formatter check..."
if $POETRY_CMD run ruff format --check .; then
    echo "    ✅ Ruff formatting passed"
else
    echo "    ❌ Ruff formatting failed"
    FAILED=1
fi

echo "  → Running mypy type checker..."
if $POETRY_CMD run mypy src --ignore-missing-imports; then
    echo "    ✅ mypy type checking passed"
else
    echo "    ❌ mypy type checking failed"
    FAILED=1
fi

cd ..

echo ""

# ============================================
# Frontend Checks (TypeScript)
# ============================================
echo "⚛️  Running Frontend Checks..."
echo "----------------------------------------"

cd frontend || exit 1

echo "  → Running ESLint..."
if npm run lint; then
    echo "    ✅ ESLint passed"
else
    echo "    ❌ ESLint failed"
    FAILED=1
fi

echo "  → Running TypeScript compiler check..."
if npx tsc --noEmit; then
    echo "    ✅ TypeScript compilation passed"
else
    echo "    ❌ TypeScript compilation failed"
    FAILED=1
fi

cd ..

echo ""
echo "========================================"

# ============================================
# Final Result
# ============================================
if [ $FAILED -eq 0 ]; then
    echo "✅ All checks passed! Safe to push."
    echo "========================================"
    exit 0
else
    echo "❌ Some checks failed. Fix issues before pushing."
    echo "========================================"
    exit 1
fi
