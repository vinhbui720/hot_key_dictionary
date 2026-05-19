#!/usr/bin/env python3
"""
hotkey_trigger.py - Called by GNOME keybinding (F9 by default).
On Wayland, GNOME fires this BEFORE releasing the key, so PRIMARY selection
is still set from the mouse highlight. We grab it and signal main app.
"""
import subprocess
import os
import sys
import time
from pathlib import Path

APP_DIR = Path(__file__).parent
SIGNAL_DIR = APP_DIR / "data"
SIGNAL_DIR.mkdir(parents=True, exist_ok=True)

def get_selected_text() -> str:
    env = {**os.environ, "DISPLAY": ":0"}
    for cmd in [
        ["xclip", "-o", "-selection", "primary"],
        ["xsel",  "--primary", "--output"],
        ["xclip", "-o", "-selection", "clipboard"],
    ]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=2, env=env)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except Exception:
            pass
    return ""

def ensure_app_running():
    """Start the dictionary app if not already running."""
    r = subprocess.run(["pgrep", "-f", "python3.*main\\.py"], capture_output=True)
    if r.returncode != 0:
        env = {**os.environ, "DISPLAY": ":0", "XDG_SESSION_TYPE": "x11", "QT_QPA_PLATFORM": "xcb"}
        subprocess.Popen(
            ["python3", str(APP_DIR / "main.py")],
            env=env, start_new_session=True,
            stdout=open(APP_DIR / "logs" / "app.log", "a"),
            stderr=subprocess.STDOUT
        )
        time.sleep(1.5)  # give it time to start

def main():
    word = get_selected_text().strip()
    # Filter: only single words or short phrases, no newlines
    if word and len(word) < 80 and "\n" not in word:
        (SIGNAL_DIR / "lookup.signal").write_text(word, encoding="utf-8")
    else:
        (SIGNAL_DIR / "show.signal").touch()
    ensure_app_running()

if __name__ == "__main__":
    main()
