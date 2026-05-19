# 📖 Vinh's Dictionary

A smart IELTS/English vocabulary tool for Ubuntu with:
- **Instant popup** on any highlighted word (system-wide hotkey)
- **Eng–Eng definitions** with examples (Free Dictionary API + WordNet offline fallback)
- **Synonyms** shown as clickable chips
- **Text-to-speech** pronunciation
- **Spaced repetition** review system (1d → 3d → 7d → 20d → 30d)
- **AI sentence checker** (Ollama local LLM + LanguageTool grammar)
- **Smart suggestions** when a word is misspelled / not found
- **Fully configurable** – hotkey, TTS, intervals, AI model, all in the Settings tab

---

## Requirements

| Requirement | Notes |
|---|---|
| Ubuntu 20.04+ / Debian-based Linux | GNOME desktop recommended |
| Python 3.10+ | Usually pre-installed |
| `xclip` | For reading highlighted text |
| `mpg123` | For audio pronunciation |
| Ollama *(optional)* | Local AI sentence checking |

---

## Quick install

```bash
# 1. Clone
git clone git@github.com:vinhbui720/hot_key_dictionary.git
cd hot_key_dictionary

# 2. Install system packages (once)
sudo apt install xclip mpg123 xsel

# 3. Run setup (no sudo needed after step 2)
bash setup.sh
```

That's it. The app is now:
- Available in the Ubuntu app launcher (search "Vinh")
- Pinned to the dock
- Set to auto-start on login
- Listening on **F9** (default hotkey)

---

## Usage

### Lookup a word
1. **Highlight** any word in any application
2. Press **F9** (or your configured hotkey)
3. The popup appears with definition, examples, synonyms, and a 🔊 button

Or open the app manually and type in the search box.

### Review (spaced repetition)
Words you look up are automatically scheduled for review at:
`1 day → 3 days → 7 days → 20 days → 30 days`

When words are due, you'll get a system notification.
In the **🔁 Review** tab:
1. See the word and its definition
2. Write a sentence using it
3. Click **Check** – Ollama checks usage, LanguageTool checks grammar
4. Mark **Got it ✅** or **Not yet ❌** to adjust the schedule

### Change the hotkey
Open the app → **⚙️ Settings** tab → change **Hotkey** field → **Save**.
The GNOME system binding updates immediately (works in all apps including Firefox).

---

## Project structure

```
hot_key_dictionary/
├── main.py              # Entry point, single-instance lock, GNOME keybinding
├── ui.py                # PyQt5 UI (Lookup, Review, History, Settings tabs)
├── database.py          # SQLite word history + spaced repetition scheduler
├── dictionary_api.py    # Free Dict API + WordNet fallback + fuzzy suggestions
├── ai_checker.py        # Ollama (usage) + LanguageTool (grammar) checker
├── tts.py               # Text-to-speech (gTTS online / pyttsx3 offline)
├── config.py            # JSON config with defaults, load/save/update helpers
├── hotkey_trigger.py    # Called by GNOME on hotkey press – signals main app
├── make_icon.py         # Generates icon PNGs for all sizes
├── setup.sh             # One-shot installer (run after cloning)
├── start.sh             # Launcher (used by .desktop file and autostart)
└── assets/
    └── icon.png         # 256×256 app icon
```

---

## Installing on a new machine

```bash
git clone git@github.com:vinhbui720/hot_key_dictionary.git
cd hot_key_dictionary
sudo apt install xclip mpg123 xsel   # system deps
bash setup.sh                         # everything else
```

`setup.sh` is fully idempotent – safe to re-run after pulling updates:

```bash
git pull
bash setup.sh
```

### Optional: AI sentence checking

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Download the model (~2 GB)
ollama pull llama3.2:3b

# Start Ollama service
ollama serve &
```

Then in the Settings tab set the Ollama model to `llama3.2:3b`.

---

## Configuration

Settings are stored in `data/config.json` (auto-created on first run, not committed to git).

You can edit them in the **⚙️ Settings** tab or directly in the JSON file:

```json
{
  "hotkey": "f9",
  "tts_enabled": true,
  "tts_autoplay": false,
  "tts_speed": 150,
  "max_definitions": 6,
  "max_synonyms": 10,
  "sr_intervals": [1, 3, 7, 20, 30],
  "ollama_model": "llama3.2:3b",
  "ollama_url": "http://localhost:11434",
  "languagetool_enabled": true,
  "notify_reviews": true,
  "notify_interval_minutes": 30,
  "always_on_top": true,
  "show_at_cursor": true,
  "window_width": 580,
  "window_height": 600
}
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| F9 does nothing | Run `bash setup.sh` again to re-register GNOME keybinding |
| No sound | `sudo apt install mpg123 espeak-ng` |
| Word not found | A "Did you mean?" list of similar words is shown automatically |
| Ollama says "not running" | Run `ollama serve` in a terminal, or `systemctl start ollama` |
| App not in launcher | Run `bash setup.sh` to re-install the `.desktop` file |
| Multiple popups | Kill all: `pkill -f "python3.*main.py"` then relaunch |

---

## License

MIT – do whatever you want with it.
