#!/usr/bin/env bash
# Run all end-to-end Puppeteer audits in sequence.
# Exits non-zero on the first failure so CI can pick it up cleanly.
#
# Pre-reqs:
#   - dev server on http://127.0.0.1:8000 with HW-20260427-008 populated
#   - puppeteer installed somewhere node can resolve
#     (export NODE_PATH=$(npm root -g) if you installed it globally)
#
# Usage:
#   bash scripts/run_e2e.sh            # run everything
#   bash scripts/run_e2e.sh katex      # filter by substring
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
E2E_DIR="$SCRIPT_DIR/e2e"
FILTER="${1:-}"

# Probe server health up front so failures are obvious.
if ! curl -fsS -o /dev/null --max-time 3 http://127.0.0.1:8000/api/health 2>/dev/null; then
  echo "✗ dev server not reachable on http://127.0.0.1:8000 — start uvicorn first."
  exit 2
fi

# Ordered list — keep cheap audits first so a fast-fail surfaces early.
AUDITS=(
  verify_hw008.cjs
  mechanics.cjs
  new_mechanics.cjs
  post_tilematch.cjs
  katex.cjs
  katex_builder.cjs
  preview_quality.cjs
  amr_results.cjs
)

passed=0
failed=0
for audit in "${AUDITS[@]}"; do
  if [[ -n "$FILTER" && "$audit" != *"$FILTER"* ]]; then continue; fi
  echo
  echo "──────────────────────────────────────────────────────────────"
  echo "  $audit"
  echo "──────────────────────────────────────────────────────────────"
  if node "$E2E_DIR/$audit"; then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
    echo "✗ $audit failed"
  fi
done

echo
echo "═══════════════════════════════════════════════════════════════"
echo "  passed: $passed   failed: $failed"
echo "═══════════════════════════════════════════════════════════════"
exit $((failed == 0 ? 0 : 1))
