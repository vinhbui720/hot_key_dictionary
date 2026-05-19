#!/usr/bin/env bash
# Vinh's Dictionary – launcher script
# Usage: start.sh [--review | --settings]
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export DISPLAY="${DISPLAY:-:0}"
export XDG_SESSION_TYPE=x11
export QT_QPA_PLATFORM=xcb
mkdir -p "$APP_DIR/logs"

ARG="${1:-}"

# If already running (check both lockfile and process), signal it and exit
LOCK="$APP_DIR/data/app.lock"
if [ -f "$LOCK" ] || pgrep -f "python3.*main\.py" > /dev/null 2>&1; then
    case "$ARG" in
        --review)   echo "review"   > "$APP_DIR/data/action.signal" ;;
        --settings) echo "settings" > "$APP_DIR/data/action.signal" ;;
        *)          touch "$APP_DIR/data/show.signal" ;;
    esac
    exit 0
fi

# Start fresh
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Launching Vinh's Dictionary (arg=$ARG)" >> "$APP_DIR/logs/app.log"

case "$ARG" in
    --review)   DICT_OPEN_TAB=review   python3 "$APP_DIR/main.py" >> "$APP_DIR/logs/app.log" 2>&1 & ;;
    --settings) DICT_OPEN_TAB=settings python3 "$APP_DIR/main.py" >> "$APP_DIR/logs/app.log" 2>&1 & ;;
    *)                                  python3 "$APP_DIR/main.py" >> "$APP_DIR/logs/app.log" 2>&1 & ;;
esac
