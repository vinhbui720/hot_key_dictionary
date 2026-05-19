#!/usr/bin/env bash
# =============================================================================
#  Vinh's Dictionary – One-shot setup script
#  Run once after cloning:  bash setup.sh
#  Safe to re-run (idempotent).
# =============================================================================
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$APP_DIR/.venv"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[setup]${NC} $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC}  $*"; }
error() { echo -e "${RED}[error]${NC} $*"; }

info "Setting up Vinh's Dictionary at: $APP_DIR"
mkdir -p "$APP_DIR/data" "$APP_DIR/logs" "$APP_DIR/assets"

# ── 1. Python version check ──────────────────────────────────────────────────
PY=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
MAJOR=${PY%%.*}; MINOR=${PY##*.}
if [ "$MAJOR" -lt 3 ] || [ "$MINOR" -lt 10 ]; then
    error "Python 3.10+ required (found $PY). Install it and retry."
    exit 1
fi
info "Python $PY ✓"

# ── 2. System packages (optional but improves TTS/audio) ────────────────────
MISSING_SYS=""
for pkg in xclip xsel espeak-ng mpg123; do
    command -v "$pkg" &>/dev/null || MISSING_SYS="$MISSING_SYS $pkg"
done
if [ -n "$MISSING_SYS" ]; then
    warn "Optional system packages missing:$MISSING_SYS"
    warn "Install with: sudo apt install$MISSING_SYS"
    warn "App will work without them (TTS falls back to pyttsx3)."
else
    info "System packages ✓"
fi

# ── 3. Python packages ───────────────────────────────────────────────────────
info "Installing Python packages..."
pip3 install --quiet --user \
    PyQt5 \
    pynput \
    pyperclip \
    requests \
    nltk \
    gtts \
    pyttsx3 \
    2>&1 | grep -v "already satisfied" || true
info "Python packages ✓"

# ── 4. NLTK WordNet data ─────────────────────────────────────────────────────
info "Downloading WordNet offline data..."
NLTK_DIR="$APP_DIR/data/nltk"
mkdir -p "$NLTK_DIR"
python3 - <<PYEOF
import nltk, sys
nltk.data.path.insert(0, "$NLTK_DIR")
nltk.download("wordnet",  download_dir="$NLTK_DIR", quiet=True)
nltk.download("omw-1.4", download_dir="$NLTK_DIR", quiet=True)
print("  WordNet ready at $NLTK_DIR")
PYEOF
info "WordNet ✓"

# ── 5. Generate app icon ──────────────────────────────────────────────────────
info "Generating app icon..."
DISPLAY="${DISPLAY:-:0}" XDG_SESSION_TYPE=x11 QT_QPA_PLATFORM=xcb \
    python3 "$APP_DIR/make_icon.py" 2>/dev/null \
    && info "Icons ✓" \
    || warn "Icon generation skipped (needs a display – run manually if needed)"

# ── 6. Install .desktop app entry ────────────────────────────────────────────
info "Installing application launcher..."
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"

HOTKEY=$(python3 -c "
import json, pathlib
cfg = pathlib.Path('$APP_DIR/data/config.json')
if cfg.exists():
    print(json.loads(cfg.read_text()).get('hotkey','F9').upper())
else:
    print('F9')
" 2>/dev/null || echo "F9")

cat > "$APPS_DIR/vinh-dictionary.desktop" <<EOF
[Desktop Entry]
Version=1.1
Type=Application
Name=Vinh's Dictionary
GenericName=Dictionary
Comment=IELTS dictionary with spaced repetition – press $HOTKEY on any highlighted word
Exec=env DISPLAY=:0 XDG_SESSION_TYPE=x11 QT_QPA_PLATFORM=xcb $APP_DIR/start.sh
Icon=vinh-dictionary
Terminal=false
StartupNotify=true
StartupWMClass=vinh-dictionary
Categories=Education;Dictionary;Office;
Keywords=dictionary;ielts;english;vocabulary;translate;
Actions=Review;Settings;

[Desktop Action Review]
Name=Review Due Words
Exec=env DISPLAY=:0 XDG_SESSION_TYPE=x11 QT_QPA_PLATFORM=xcb $APP_DIR/start.sh --review

[Desktop Action Settings]
Name=Settings
Exec=env DISPLAY=:0 XDG_SESSION_TYPE=x11 QT_QPA_PLATFORM=xcb $APP_DIR/start.sh --settings
EOF

desktop-file-validate "$APPS_DIR/vinh-dictionary.desktop" 2>/dev/null && true
update-desktop-database "$APPS_DIR" 2>/dev/null && true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null && true
info "App launcher installed ✓"

# ── 7. Autostart on login ────────────────────────────────────────────────────
info "Setting up autostart..."
AUTOSTART="$HOME/.config/autostart"
mkdir -p "$AUTOSTART"
cat > "$AUTOSTART/vinh-dictionary.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Vinh's Dictionary
Comment=IELTS dictionary with spaced repetition
Exec=env DISPLAY=:0 XDG_SESSION_TYPE=x11 QT_QPA_PLATFORM=xcb $APP_DIR/start.sh
Icon=vinh-dictionary
Terminal=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF
info "Autostart ✓"

# ── 8. Pin to Ubuntu dock ────────────────────────────────────────────────────
CURRENT=$(gsettings get org.gnome.shell favorite-apps 2>/dev/null || echo "[]")
if echo "$CURRENT" | grep -q "vinh-dictionary"; then
    info "Already pinned to dock ✓"
else
    NEW=$(echo "$CURRENT" | sed "s/\]$/, 'vinh-dictionary.desktop']/")
    gsettings set org.gnome.shell favorite-apps "$NEW" 2>/dev/null \
        && info "Pinned to dock ✓" \
        || warn "Could not pin to dock (non-GNOME desktop?)"
fi

# ── 9. Register GNOME hotkey ────────────���────────────────────────────────────
info "Registering system hotkey ($HOTKEY)..."
BP="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/vinh-dict/"
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "['$BP']" 2>/dev/null || true
SCHEMA="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$BP"
gsettings set "$SCHEMA" name    "Vinh Dictionary"               2>/dev/null || true
gsettings set "$SCHEMA" command "python3 $APP_DIR/hotkey_trigger.py" 2>/dev/null || true
gsettings set "$SCHEMA" binding "$HOTKEY"                        2>/dev/null || true
info "GNOME hotkey $HOTKEY ✓"

# ── 10. Ollama (optional, for AI sentence checking) ──────────────────────────
echo ""
if command -v ollama &>/dev/null; then
    info "Ollama found: $(ollama --version 2>/dev/null | head -1)"
    if ollama list 2>/dev/null | grep -q "llama3.2:3b"; then
        info "llama3.2:3b already downloaded ✓"
    else
        info "Downloading llama3.2:3b model (~2GB)..."
        ollama pull llama3.2:3b || warn "Model download failed – AI checking will be limited"
    fi
else
    warn "Ollama not installed. AI sentence checking will show 'not running'."
    warn "To install: curl -fsSL https://ollama.com/install.sh | sh"
    warn "Then run:   ollama pull llama3.2:3b"
fi

# ── 11. Initialize database ───────────────────────────────────────────────────
info "Initialising database..."
python3 -c "import sys; sys.path.insert(0,'$APP_DIR'); import database" \
    && info "Database ✓"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅  Setup complete!${NC}"
echo ""
echo "  Start the app:"
echo "    $APP_DIR/start.sh"
echo ""
echo "  Or click 'Vinh's Dictionary' in the Ubuntu app launcher."
echo ""
echo "  Hotkey: highlight any word → press ${HOTKEY}"
echo "  Change hotkey anytime in the ⚙️ Settings tab."
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
