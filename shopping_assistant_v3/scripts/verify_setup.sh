#!/usr/bin/env bash
# Verify the Shopping Assistant V3 runtime structure exists.
# Local check only: no network, no model calls, no scraping, no secrets.
set -u

V3_DIR="$(cd "$(dirname "$0")/.." && pwd)"

REQUIRED_DIRS=(
  backend
  backend/shared
  backend/database
  backend/api
  backend/router
  backend/tools/deal_search
  backend/tools/price_estimator
  backend/synthesizer
  frontend
  scripts
  guides
  reports
)

REQUIRED_FILES=(
  gameplan.md
  .env.example
  backend/README.md
  frontend/README.md
  scripts/README.md
)

missing=0

for d in "${REQUIRED_DIRS[@]}"; do
  if [ ! -d "$V3_DIR/$d" ]; then
    echo "MISSING DIR:  $d"
    missing=1
  fi
done

for f in "${REQUIRED_FILES[@]}"; do
  if [ ! -f "$V3_DIR/$f" ]; then
    echo "MISSING FILE: $f"
    missing=1
  fi
done

if [ "$missing" -ne 0 ]; then
  echo "verify_setup: FAILED"
  exit 1
fi

echo "verify_setup: OK"
