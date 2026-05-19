"""
TTS module - Text to Speech.
Uses gTTS (online) or pyttsx3 (offline).
"""
import threading
import tempfile
import os
from pathlib import Path


def speak(word: str, audio_url: str = ""):
    """Speak a word in a background thread."""
    t = threading.Thread(target=_speak_worker, args=(word, audio_url), daemon=True)
    t.start()


def _speak_worker(word: str, audio_url: str = ""):
    try:
        # Try to play the audio_url from dictionary API first (MP3)
        if audio_url:
            if _play_url(audio_url):
                return

        # Try gTTS (online)
        _speak_gtts(word)
    except Exception:
        # Fallback to pyttsx3 (offline)
        try:
            _speak_pyttsx3(word)
        except Exception:
            pass


def _play_url(url: str) -> bool:
    """Download and play an MP3 from URL."""
    try:
        import requests
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return False
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(resp.content)
            tmp = f.name
        # Try multiple players
        for player in ["mpg123", "mpg321", "ffplay", "aplay"]:
            if os.system(f"which {player} > /dev/null 2>&1") == 0:
                ret = os.system(f"{player} -q '{tmp}' > /dev/null 2>&1")
                os.unlink(tmp)
                return ret == 0
        os.unlink(tmp)
        return False
    except Exception:
        return False


def _speak_gtts(word: str):
    from gtts import gTTS
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    tts = gTTS(text=word, lang="en", slow=False)
    tts.save(tmp)
    for player in ["mpg123", "mpg321", "ffplay"]:
        if os.system(f"which {player} > /dev/null 2>&1") == 0:
            os.system(f"{player} -q '{tmp}' > /dev/null 2>&1")
            break
    os.unlink(tmp)


def _speak_pyttsx3(word: str):
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty("rate", 150)
    engine.say(word)
    engine.runAndWait()
    engine.stop()
