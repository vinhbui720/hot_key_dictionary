"""
Config module - persistent JSON settings.
All app settings live here. Changes take effect immediately or on restart (noted per setting).
"""
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "data" / "config.json"
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

DEFAULTS = {
    # Hotkey - pynput key name. Special keys: "f1"-"f12", "ctrl", etc.
    # Format: single key like "f6", or combo like "ctrl+d"
    "hotkey": "f6",

    # TTS
    "tts_enabled": True,
    "tts_speed": 150,           # words per minute for pyttsx3
    "tts_autoplay": False,      # auto-speak when popup opens

    # UI
    "window_width": 580,
    "window_height": 600,
    "always_on_top": True,
    "show_at_cursor": True,     # False = center screen

    # Dictionary
    "max_definitions": 6,
    "max_synonyms": 10,
    "online_timeout": 5,        # seconds

    # Spaced repetition intervals (days)
    "sr_intervals": [1, 3, 7, 20, 30],

    # AI checker
    "ollama_model": "llama3.2:3b",
    "ollama_url": "http://localhost:11434",
    "languagetool_enabled": True,

    # Notifications
    "notify_reviews": True,
    "notify_interval_minutes": 30,

    # Startup
    "start_minimized": True,
}


def load() -> dict:
    """Load config from disk, merging with defaults for any missing keys."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                saved = json.load(f)
            # Merge: defaults first, then saved values on top
            merged = {**DEFAULTS, **saved}
            return merged
        except Exception:
            pass
    return dict(DEFAULTS)


def save(cfg: dict):
    """Save config to disk."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def get(key: str, default=None):
    """Convenience: load and get a single key."""
    return load().get(key, default)


# Module-level cache so we don't re-read disk on every access
_cache: dict | None = None


def cfg() -> dict:
    """Return cached config (reload if needed)."""
    global _cache
    if _cache is None:
        _cache = load()
    return _cache


def reload():
    """Force reload from disk."""
    global _cache
    _cache = load()
    return _cache


def update(**kwargs):
    """Update one or more keys and save."""
    global _cache
    current = load()
    current.update(kwargs)
    save(current)
    _cache = current
    return current


# Ensure config file exists on first import
if not CONFIG_PATH.exists():
    save(DEFAULTS)
