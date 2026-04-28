# NETS Homework Builder — launchd Auto-Restart

The uvicorn server dies on SSH disconnect (SIGHUP), macOS sleep, or reboot. This launchd agent 
keeps it up 24/7, respawning on crash and starting at login.

## Install

```bash
bash scripts/install_launchd.sh
```

## Uninstall

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aisigma.netsbuilder.plist && \
  rm ~/Library/LaunchAgents/com.aisigma.netsbuilder.plist
```

## Status / Control

```bash
# Check if running
launchctl print gui/$(id -u)/com.aisigma.netsbuilder | head -30

# Stop (without uninstalling)
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aisigma.netsbuilder.plist

# Start
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aisigma.netsbuilder.plist

# Restart immediately
launchctl kickstart -k gui/$(id -u)/com.aisigma.netsbuilder
```

## Logs

Stdout + stderr: `/Users/aisigma/nets-builder/uvicorn.log`

```bash
tail -f /Users/aisigma/nets-builder/uvicorn.log
```

## Troubleshooting

**Service not loading** — Check `launchctl error <code>`. Likely: missing venv, wrong path, or 
non-Mach-O binary.

**Server crashes immediately** — Tail the log for `ImportError` or `ModuleNotFoundError`. The 
plist sets only `PATH`; if `.env` is needed, load it in `server/config.py` before FastAPI boots.

**Port 8000 in use** — Find the process: `lsof -nP -iTCP:8000 -sTCP:LISTEN`, kill it, then 
`launchctl kickstart -k gui/$(id -u)/com.aisigma.netsbuilder`.

**KeepAlive** — The plist respawns on crash after 30 seconds, but `launchctl bootout` stops it 
cleanly. `launchctl kickstart` restarts immediately.
