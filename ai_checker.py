"""
AI checker module.
Uses Ollama (local) for semantic/usage check + LanguageTool for grammar.
Falls back gracefully when offline or Ollama not running.
"""
import requests
import json


OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"
LANGUAGETOOL_URL = "https://api.languagetool.org/v2/check"


def check_with_ollama(word: str, sentence: str) -> dict:
    """
    Ask Ollama if the word is used correctly in the sentence.
    Returns: {ok: bool, feedback: str, corrected: str}
    """
    prompt = f"""You are an English teacher. A student wrote this sentence using the word "{word}":

"{sentence}"

Please check:
1. Is "{word}" used correctly in context?
2. Does the sentence make natural, grammatical sense?

Reply in this exact JSON format (no extra text):
{{
  "correct_usage": true or false,
  "feedback": "one sentence explanation",
  "corrected_sentence": "improved version of the sentence if needed, or same if already good"
}}"""

    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 200}
        }, timeout=30)
        if resp.status_code != 200:
            return {"ok": None, "feedback": "Ollama unavailable", "corrected": sentence}

        raw = resp.json().get("response", "")
        # Extract JSON from response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
            return {
                "ok": data.get("correct_usage", None),
                "feedback": data.get("feedback", ""),
                "corrected": data.get("corrected_sentence", sentence)
            }
        return {"ok": None, "feedback": raw[:200], "corrected": sentence}
    except requests.exceptions.ConnectionError:
        return {"ok": None, "feedback": "Ollama not running (install: curl -fsSL https://ollama.com/install.sh | sh)", "corrected": sentence}
    except Exception as e:
        return {"ok": None, "feedback": f"Error: {str(e)}", "corrected": sentence}


def check_with_languagetool(sentence: str) -> dict:
    """
    Check grammar with LanguageTool API.
    Returns: {matches: list of {message, suggestion, offset, length}}
    """
    try:
        resp = requests.post(LANGUAGETOOL_URL, data={
            "text": sentence,
            "language": "en-US",
        }, timeout=10)
        if resp.status_code != 200:
            return {"matches": [], "error": f"HTTP {resp.status_code}"}
        data = resp.json()
        matches = []
        for m in data.get("matches", []):
            replacements = [r["value"] for r in m.get("replacements", [])[:3]]
            matches.append({
                "message": m.get("message", ""),
                "suggestion": ", ".join(replacements) if replacements else "",
                "offset": m.get("offset", 0),
                "length": m.get("length", 0),
                "rule": m.get("rule", {}).get("id", "")
            })
        return {"matches": matches}
    except Exception as e:
        return {"matches": [], "error": str(e)}


def check_sentence(word: str, sentence: str, online: bool = True) -> dict:
    """
    Full check: Ollama + LanguageTool (if online), or just Ollama if offline.
    Returns combined result dict.
    """
    result = {
        "ollama": None,
        "languagetool": None,
        "summary": ""
    }

    # Always try Ollama (local)
    result["ollama"] = check_with_ollama(word, sentence)

    # LanguageTool requires internet
    if online:
        result["languagetool"] = check_with_languagetool(sentence)

    # Build summary
    parts = []
    if result["ollama"] and result["ollama"]["feedback"]:
        ok = result["ollama"]["ok"]
        icon = "✅" if ok else ("❌" if ok is False else "⚠️")
        parts.append(f"{icon} {result['ollama']['feedback']}")

    if result["languagetool"] and result["languagetool"].get("matches"):
        for m in result["languagetool"]["matches"][:3]:
            sug = f" → **{m['suggestion']}**" if m["suggestion"] else ""
            parts.append(f"📝 {m['message']}{sug}")

    result["summary"] = "\n".join(parts) if parts else "✅ Looks good!"
    return result


def is_ollama_running() -> bool:
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False
