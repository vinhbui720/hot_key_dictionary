#!/usr/bin/env bash
# Vinh's Dictionary – launcher script
# Usage: start.sh [--review | --settings]
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export DISPLAY="${DISPLAY:-:0}"
export XDG_SESSION_TYPE=x11
export QT_QPA_PLATFORM=xcb
mkdir -p "$APP_DIR/logs"

ARG="${1:-}"
LOCK="$APP_DIR/data/app.lock"
DATA="$APP_DIR/data"

# ── Stale-lock cleanup ────────────────────────────────────────────────────────
# The lock is held by fcntl.flock; if the PID inside no longer exists the file
# is stale (crash or SIGKILL). Remove it so a fresh instance can start.
if [ -f "$LOCK" ]; then
    LOCK_PID="$(cat "$LOCK" 2>/dev/null)"
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        : # process is alive – lock is valid
    else
        rm -f "$LOCK"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Removed stale lock (pid=$LOCK_PID)" \
            >> "$APP_DIR/logs/app.log"
    fi
fi

# ── If already running, signal it ────────────────────────────────────────────
if [ -f "$LOCK" ] || pgrep -xf "python3 $APP_DIR/main.py" > /dev/null 2>&1; then
    case "$ARG" in
        --review)   echo "review"   > "$DATA/action.signal" ;;
        --settings) echo "settings" > "$DATA/action.signal" ;;
        *)          touch "$DATA/show.signal" ;;
    esac
    exit 0
fi

# ── Start fresh ───────────────────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Launching Vinh's Dictionary (arg=$ARG)" \
    >> "$APP_DIR/logs/app.log"

# Pass the open-tab hint via env var so main.py can show the right tab on boot
case "$ARG" in
    --review)
        DICT_OPEN_TAB=review   python3 "$APP_DIR/main.py" >> "$APP_DIR/logs/app.log" 2>&1 &
        ;;
    --settings)
        DICT_OPEN_TAB=settings python3 "$APP_DIR/main.py" >> "$APP_DIR/logs/app.log" 2>&1 &
        ;;
    *)
        python3 "$APP_DIR/main.py" >> "$APP_DIR/logs/app.log" 2>&1 &
        ;;
esac
