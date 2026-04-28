#!/usr/bin/env bash
# Convenience wrapper for watching student simulations in a real browser.
#
# Usage:
#   bash scripts/watch.sh                          # mid persona, default speed
#   bash scripts/watch.sh strong                   # ~95% accuracy
#   bash scripts/watch.sh weak                     # ~30% accuracy
#   bash scripts/watch.sh mid 250                  # custom slowMo (ms per action)
#   bash scripts/watch.sh strong 100 boss          # jump to Boss phase only
#
# Pre-reqs:
#   - dev server on http://127.0.0.1:8000 with HW-20260427-008 populated
#   - puppeteer reachable via NODE_PATH (export NODE_PATH=$(npm root -g))
set -euo pipefail

PERSONA="${1:-mid}"
SLOWMO="${2:-120}"
PHASE="${3:-}"

if ! curl -fsS -o /dev/null --max-time 3 http://127.0.0.1:8000/api/health 2>/dev/null; then
  echo "✗ dev server not reachable on http://127.0.0.1:8000 — start uvicorn first."
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default NODE_PATH if user didn't set it.
if [ -z "${NODE_PATH:-}" ] && command -v npm >/dev/null 2>&1; then
  NODE_PATH="$(npm root -g 2>/dev/null || echo)"
  export NODE_PATH
fi

PERSONA="$PERSONA" SLOWMO="$SLOWMO" PHASE="$PHASE" \
  node "$SCRIPT_DIR/watch_simulation.cjs"
