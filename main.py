#!/usr/bin/env python3
"""
Vinh's Dictionary App - Main entry point.
Fixes:
  - Single-instance lock (only one copy runs)
  - DISPLAY/XDG env set before pynput starts
  - Real SVG tray icon (not just a pixmap circle)
  - Configurable hotkey with live reload
"""
import sys
import os
import fcntl
import subprocess
import threading
import time
import signal
import logging
from pathlib import Path

# ── MUST set DISPLAY before any X11/Qt import ────────────────────────────────
if not os.environ.get("DISPLAY"):
    os.environ["DISPLAY"] = ":0"
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["XDG_SESSION_TYPE"] = "x11"   # suppress Wayland warning

APP_DIR = Path(__file__).parent
sys.path.insert(0, str(APP_DIR))

# ── File logging (always works, even when stdout is piped) ────────────────────
LOG_FILE = APP_DIR / "logs" / "app.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("dict")

# ── Single-instance lock ──────────────────────────────────────────────────────
LOCK_FILE = APP_DIR / "data" / "app.lock"
LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
_lock_fh = None

def acquire_lock():
    global _lock_fh
    _lock_fh = open(LOCK_FILE, "w")
    try:
        fcntl.flock(_lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_fh.write(str(os.getpid()))
        _lock_fh.flush()
        os.fsync(_lock_fh.fileno())   # make PID visible to start.sh immediately
        return True
    except OSError:
        return False   # another instance is running

def release_lock():
    global _lock_fh
    if _lock_fh:
        try:
            fcntl.flock(_lock_fh, fcntl.LOCK_UN)
            _lock_fh.close()
        except Exception:
            pass

# ── Now safe to import Qt ─────────────────────────────────────────────────────
from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QAction
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QImage

import database as db
import config as cfg_mod


# ─── Signals bridge ───────────────────────────────────────────────────────────
class Bridge(QObject):
    lookup_signal = pyqtSignal(str)
    open_signal   = pyqtSignal()

bridge = Bridge()


# ─── Clipboard / selection helper ────────────────────────────────────────────
def get_selected_text() -> str:
    """Get currently highlighted/selected text from X PRIMARY selection."""
    # Method 1: xclip primary (most reliable after highlight)
    try:
        r = subprocess.run(
            ["xclip", "-o", "-selection", "primary"],
            capture_output=True, text=True, timeout=2,
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}
        )
        if r.returncode == 0:
            t = r.stdout.strip()
            if t:
                return t
    except Exception:
        pass

    # Method 2: xsel
    try:
        r = subprocess.run(["xsel", "--primary", "--output"],
                           capture_output=True, text=True, timeout=2)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass

    # Method 3: pyperclip clipboard
    try:
        import pyperclip
        t = pyperclip.paste()
        if t and t.strip():
            return t.strip()
    except Exception:
        pass

    return ""


# ─── Hotkey parsing ───────────────────────────────────────────────────────────
def parse_hotkey(hotkey_str: str):
    from pynput import keyboard
    parts = [p.strip().lower() for p in hotkey_str.split("+")]
    modifier_map = {
        "ctrl":  keyboard.Key.ctrl,
        "shift": keyboard.Key.shift,
        "alt":   keyboard.Key.alt,
        "super": keyboard.Key.cmd,
        "cmd":   keyboard.Key.cmd,
    }
    fkey_map = {f"f{i}": getattr(keyboard.Key, f"f{i}") for i in range(1, 13)}

    modifiers = set()
    trigger = None
    for part in parts:
        if part in modifier_map:
            modifiers.add(modifier_map[part])
        elif part in fkey_map:
            trigger = fkey_map[part]
        elif len(part) == 1:
            trigger = keyboard.KeyCode.from_char(part)
        else:
            try:
                trigger = getattr(keyboard.Key, part)
            except AttributeError:
                pass
    return modifiers, trigger


# ─── Hotkey manager ───────────────────────────────────────────────────────────
class HotkeyManager:
    def __init__(self):
        self._listener = None
        self._pressed  = set()

    def start(self, hotkey_str: str = ""):
        self.stop()
        if not hotkey_str:
            hotkey_str = cfg_mod.cfg().get("hotkey", "f6")

        try:
            from pynput import keyboard
            modifiers, trigger = parse_hotkey(hotkey_str)

            def on_press(key):
                # Track modifier state
                for mod in modifiers:
                    # pynput fires e.g. Key.ctrl_l AND Key.ctrl
                    if hasattr(key, 'name') and hasattr(mod, 'name'):
                        if key.name and mod.name and key.name.startswith(mod.name):
                            self._pressed.add(mod)
                    if key == mod:
                        self._pressed.add(mod)

                if key == trigger:
                    if modifiers and not modifiers.issubset(self._pressed):
                        return
                    text = get_selected_text()
                    word = text.strip()
                    if word and len(word) < 80 and "\n" not in word:
                        bridge.lookup_signal.emit(word)
                    else:
                        bridge.open_signal.emit()

            def on_release(key):
                for mod in list(self._pressed):
                    if key == mod:
                        self._pressed.discard(mod)

            # Use suppress=False so other apps still get the key
            self._listener = keyboard.Listener(
                on_press=on_press,
                on_release=on_release,
                suppress=False
            )
            self._listener.daemon = True
            self._listener.start()
            log.info(f"[hotkey] Listening: {hotkey_str.upper()}")
        except Exception as e:
            log.info(f"[hotkey] Failed to start: {e}")

    def stop(self):
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
            self._pressed.clear()

    def restart(self, new_hotkey: str):
        self.start(new_hotkey)


hotkey_manager = HotkeyManager()


# ─── Notification ────────────────────────────────────────────────────────────
def send_notification(title: str, body: str):
    try:
        subprocess.Popen(
            ["notify-send", "-i", "accessories-dictionary", "-t", "4000", title, body],
            env={**os.environ, "DISPLAY": ":0"}
        )
    except Exception:
        pass


def check_and_notify_reviews():
    if not cfg_mod.cfg().get("notify_reviews", True):
        return
    count = db.count_due_reviews()
    if count > 0:
        hk = cfg_mod.cfg().get("hotkey", "F6").upper()
        send_notification(
            "📖 Vinh's Dictionary",
            f"{count} word{'s' if count > 1 else ''} due for review! Press {hk} to open."
        )


def sync_gnome_binding(hotkey: str):
    """Register/update the GNOME system-wide keybinding for Wayland support."""
    try:
        bp = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/vinh-dict/"
        subprocess.run([
            "gsettings", "set",
            "org.gnome.settings-daemon.plugins.media-keys",
            "custom-keybindings", f"['{bp}']"
        ], capture_output=True, timeout=3)
        schema = f"org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:{bp}"
        subprocess.run(["gsettings", "set", schema, "name",    "Vinh Dictionary"],  capture_output=True, timeout=3)
        subprocess.run(["gsettings", "set", schema, "command",
                        f"python3 {APP_DIR}/hotkey_trigger.py"],                    capture_output=True, timeout=3)
        subprocess.run(["gsettings", "set", schema, "binding", hotkey.upper()],     capture_output=True, timeout=3)
        log.info(f"[gnome] Keybinding synced: {hotkey.upper()}")
    except Exception as e:
        log.warning(f"[gnome] Could not sync keybinding: {e}")


# ─── Tray icon ────────────────────────────────────────────────────────────────
def make_tray_icon() -> QIcon:
    """Load icon from installed PNG, fall back to drawing one."""
    # Try installed icon first (best quality, matches .desktop file)
    icon_paths = [
        Path.home() / ".local/share/icons/hicolor/256x256/apps/vinh-dictionary.png",
        Path.home() / ".local/share/icons/hicolor/48x48/apps/vinh-dictionary.png",
        APP_DIR / "assets" / "icon.png",
    ]
    for path in icon_paths:
        if path.exists():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon

    # Fallback: draw it
    return _draw_tray_icon()


def _draw_tray_icon() -> QIcon:
    """Draw a book icon programmatically."""
    size = 64
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)

    # Outer rounded rectangle (book cover)
    p.setBrush(QColor("#7aa2f7"))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(4, 4, 56, 56, 10, 10)

    # Spine line
    p.setBrush(QColor("#5a82d7"))
    p.drawRect(4, 4, 8, 56)

    # White lines (pages)
    p.setPen(QColor("white"))
    p.setBrush(Qt.NoBrush)
    from PyQt5.QtGui import QPen
    pen = QPen(QColor("white"), 2.5)
    p.setPen(pen)
    for y in [22, 30, 38]:
        p.drawLine(18, y, 50, y)

    # "D" letter
    p.setPen(QColor("white"))
    font = QFont("Arial", 22, QFont.Bold)
    p.setFont(font)
    p.drawText(img.rect(), Qt.AlignCenter, "D")

    p.end()
    return QIcon(QPixmap.fromImage(img))


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    # ── Single instance check ──
    if not acquire_lock():
        log.info("[app] Already running. Exiting.")
        # Try to bring existing window to front via signal file
        signal_file = APP_DIR / "data" / "show.signal"
        signal_file.touch()
        sys.exit(0)

    try:
        _run_app()
    finally:
        release_lock()


def _run_app():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Vinh's Dictionary")
    app.setApplicationDisplayName("Vinh's Dictionary")
    app.setDesktopFileName("vinh-dictionary")   # must match .desktop filename

    # Import UI after QApplication is created
    from ui import DictionaryPopup
    popup = DictionaryPopup()

    # Set window icon (shows in taskbar + alt-tab)
    app_icon = make_tray_icon()
    app.setWindowIcon(app_icon)
    popup.setWindowIcon(app_icon)

    # ── Signal file watcher ──────────────────────────────────────────────────
    # Polls signal files written by start.sh / hotkey_trigger.py:
    #   data/show.signal    → open popup
    #   data/lookup.signal  → lookup a word (content = word)
    #   data/action.signal  → switch tab (content = review | settings)
    show_sig   = APP_DIR / "data" / "show.signal"
    lookup_sig = APP_DIR / "data" / "lookup.signal"
    action_sig = APP_DIR / "data" / "action.signal"

    def check_signal_files():
        if lookup_sig.exists():
            try:
                word = lookup_sig.read_text(encoding="utf-8").strip()
                lookup_sig.unlink(missing_ok=True)
                if word:
                    popup.lookup_word(word)
                    return
            except Exception:
                lookup_sig.unlink(missing_ok=True)
        if action_sig.exists():
            try:
                action = action_sig.read_text(encoding="utf-8").strip()
                action_sig.unlink(missing_ok=True)
                tab_map = {"review": 1, "settings": popup.settings_tab_index}
                if action in tab_map:
                    popup.tabs.setCurrentIndex(tab_map[action])
                popup.show_at_cursor()
                return
            except Exception:
                action_sig.unlink(missing_ok=True)
        if show_sig.exists():
            show_sig.unlink(missing_ok=True)
            popup.show_at_cursor()

    signal_timer = QTimer()
    signal_timer.timeout.connect(check_signal_files)
    signal_timer.start(300)

    # ── Bridge connections ──
    bridge.lookup_signal.connect(popup.lookup_word)
    bridge.open_signal.connect(popup.show_at_cursor)

    # ── Hotkey change signal ──
    popup.hotkey_changed.connect(hotkey_manager.restart)

    # ── System tray ──
    tray = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = QSystemTrayIcon(make_tray_icon(), parent=app)
        hk = cfg_mod.cfg().get("hotkey", "F6").upper()
        tray.setToolTip(f"Vinh's Dictionary  [{hk}]")

        menu = QMenu()
        act_open = QAction("📖 Open Dictionary", menu)
        act_open.triggered.connect(popup.show_at_cursor)
        menu.addAction(act_open)

        act_review = QAction("🔁 Review Words", menu)
        act_review.triggered.connect(lambda: (popup.tabs.setCurrentIndex(1), popup.show()))
        menu.addAction(act_review)

        act_settings = QAction("⚙️  Settings", menu)
        act_settings.triggered.connect(
            lambda: (popup.tabs.setCurrentIndex(popup.settings_tab_index), popup.show())
        )
        menu.addAction(act_settings)

        menu.addSeparator()
        act_quit = QAction("✕  Quit", menu)
        act_quit.triggered.connect(app.quit)
        menu.addAction(act_quit)

        tray.setContextMenu(menu)
        tray.activated.connect(
            lambda reason: popup.show_at_cursor()
            if reason == QSystemTrayIcon.Trigger else None   # single-click opens
        )
        tray.show()

        # Update tooltip + GNOME binding when hotkey changes
        def on_hotkey_changed(hk):
            tray.setToolTip(f"Vinh's Dictionary  [{hk.upper()}]")
            sync_gnome_binding(hk)
        popup.hotkey_changed.connect(on_hotkey_changed)
        log.info(f"[tray] Icon shown, tray available: {QSystemTrayIcon.isSystemTrayAvailable()}")
    else:
        log.info("[tray] System tray NOT available on this desktop")

    # ── Review notifications ──
    interval_ms = cfg_mod.cfg().get("notify_interval_minutes", 30) * 60 * 1000
    review_timer = QTimer()
    review_timer.timeout.connect(check_and_notify_reviews)
    review_timer.start(interval_ms)
    QTimer.singleShot(4000, check_and_notify_reviews)

    # ── Start hotkey listener (XWayland apps) + sync GNOME binding (all apps) ──
    hotkey_manager.start()
    sync_gnome_binding(cfg_mod.cfg().get("hotkey", "f9"))

    # ── Show window on startup ────────────────────────────────────────────────
    # Open immediately so the user sees the app appeared; honour tab hint from
    # start.sh (DICT_OPEN_TAB env var set when called with --review/--settings)
    open_tab = os.environ.get("DICT_OPEN_TAB", "").strip().lower()
    def _show_on_startup():
        tab_map = {"review": 1, "settings": popup.settings_tab_index}
        if open_tab in tab_map:
            popup.tabs.setCurrentIndex(tab_map[open_tab])
        popup.show_at_cursor()
    QTimer.singleShot(400, _show_on_startup)   # small delay so tray icon settles first

    # ── Startup notification ──
    hk = cfg_mod.cfg().get("hotkey", "F6").upper()
    QTimer.singleShot(1500, lambda: send_notification(
        "📖 Vinh's Dictionary",
        f"Running! Highlight any word → press {hk} to look it up."
    ))

    log.info(f"[app] Ready. Hotkey: {cfg_mod.cfg().get('hotkey','f6').upper()}")
    log.info(f"[app] Config: {cfg_mod.CONFIG_PATH}")
    log.info(f"[app] DB:     {db.DB_PATH}")

    ret = app.exec_()
    hotkey_manager.stop()
    sys.exit(ret)


if __name__ == "__main__":
    main()
