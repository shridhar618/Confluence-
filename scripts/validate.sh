#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[1/3] Running backend tests"
(
  cd "$ROOT_DIR/backend"
  python3 -m pytest -q
)

echo "[2/3] Running API contract tests"
(
  cd "$ROOT_DIR/backend"
  python3 -m pytest -q tests/test_api_contract.py
)

echo "[3/3] Building frontend"
(
  cd "$ROOT_DIR/frontend"
  npm ci
  npm run build
)

echo "Validation passed"
