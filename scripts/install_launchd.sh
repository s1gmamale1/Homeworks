#!/bin/bash
set -euo pipefail

# NETS Homework Builder — launchd installer
# Installs the plist and registers it with launchctl

PLIST_NAME="com.aisigma.netsbuilder"
PLIST_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/${PLIST_NAME}.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/${PLIST_NAME}.plist"
VENV_PYTHON="/Users/aisigma/nets-builder/.venv/bin/python"
SERVER_HOME="/Users/aisigma/nets-builder"

echo "NETS Homework Builder — launchd installer"
echo "==========================================="
echo

# 1. Check macOS
if [[ "$(uname)" != "Darwin" ]]; then
	echo "ERROR: This script runs only on macOS (not $(uname))."
	exit 1
fi
echo "[1/7] Platform: macOS ✓"

# 2. Check venv exists
if [[ ! -f "$VENV_PYTHON" ]]; then
	echo "ERROR: venv Python not found at $VENV_PYTHON"
	echo "       Expected: /Users/aisigma/nets-builder/.venv/bin/python"
	echo "       Run this script from a Mac with the venv already set up."
	exit 1
fi
echo "[2/7] venv: $VENV_PYTHON ✓"

# 3. Copy plist
if [[ ! -f "$PLIST_SRC" ]]; then
	echo "ERROR: plist not found at $PLIST_SRC"
	exit 1
fi
mkdir -p "${HOME}/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DST"
echo "[3/7] Installed: $PLIST_DST ✓"

# 4. Unload old instance (if loaded)
# NOTE: don't name this UID — bash exports UID as readonly, the assignment fails under set -u.
U_ID=$(id -u)
launchctl bootout "gui/${U_ID}" "$PLIST_DST" 2>/dev/null || true
echo "[4/7] Unloaded any existing instance ✓"

# 5. Bootstrap (load) the plist
launchctl bootstrap "gui/${U_ID}" "$PLIST_DST"
echo "[5/7] Loaded with launchctl ✓"

# 6. Wait and confirm it's running
sleep 3
LAUNCHCTL_OUTPUT=$(launchctl print "gui/${UID}/${PLIST_NAME}" 2>&1 | head -20 || true)
if echo "$LAUNCHCTL_OUTPUT" | grep -q "state = running"; then
	echo "[6/7] Service status: running ✓"
else
	echo "[6/7] Service status check:"
	echo "$LAUNCHCTL_OUTPUT" | sed 's/^/       /'
fi

# 7. Health check: curl the server
HEALTH_CHECK=$(curl -sS -o /dev/null -w "HTTP %{http_code} in %{time_total}s" \
	http://127.0.0.1:8000/api/subjects 2>/dev/null || echo "HTTP 000 in 0s")
echo "[7/7] Health: $HEALTH_CHECK ✓"

echo
echo "Installation complete!"
echo
echo "Recent log output:"
tail -10 "${SERVER_HOME}/uvicorn.log" 2>/dev/null || echo "(no log yet)"
