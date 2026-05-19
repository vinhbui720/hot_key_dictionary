"""
Dictionary lookup module.
Primary: Free Dictionary API (api.dictionaryapi.dev)
Fallback: WordNet (offline via NLTK)
Not found: fuzzy similar word suggestions via difflib + WordNet morphy
"""
import requests
import json
import sys
from pathlib import Path
from difflib import get_close_matches

# Point NLTK to local data folder
import nltk
NLTK_DATA = str(Path(__file__).parent / "data" / "nltk")
if NLTK_DATA not in nltk.data.path:
    nltk.data.path.insert(0, NLTK_DATA)

import config as cfg_mod


def _get_cfg():
    return cfg_mod.cfg()


def lookup_online(word: str) -> dict | None:
    """Query Free Dictionary API. Returns normalized dict or None."""
    try:
        timeout = _get_cfg().get("online_timeout", 5)
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word.lower()}"
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not isinstance(data, list) or not data:
            return None

        entry = data[0]
        phonetic = entry.get("phonetic", "")
        if not phonetic:
            for ph in entry.get("phonetics", []):
                if ph.get("text"):
                    phonetic = ph["text"]
                    break

        # Find audio URL
        audio_url = ""
        for ph in entry.get("phonetics", []):
            if ph.get("audio"):
                audio_url = ph["audio"]
                break

        definitions = []
        synonyms = set()
        max_defs = _get_cfg().get("max_definitions", 6)
        max_syns = _get_cfg().get("max_synonyms", 10)

        for meaning in entry.get("meanings", []):
            pos = meaning.get("partOfSpeech", "")
            for defn in meaning.get("definitions", []):
                definitions.append({
                    "pos": pos,
                    "definition": defn.get("definition", ""),
                    "example": defn.get("example", "")
                })
            for syn in meaning.get("synonyms", []):
                synonyms.add(syn)

        return {
            "word": word.lower(),
            "phonetic": phonetic,
            "audio_url": audio_url,
            "definitions": definitions[:max_defs],
            "synonyms": sorted(list(synonyms))[:max_syns],
            "source": "online"
        }
    except Exception:
        return None


def lookup_wordnet(word: str) -> dict | None:
    """Query WordNet offline fallback."""
    try:
        from nltk.corpus import wordnet as wn
        synsets = wn.synsets(word.lower())
        if not synsets:
            return None

        definitions = []
        synonyms = set()
        max_defs = _get_cfg().get("max_definitions", 6)
        max_syns = _get_cfg().get("max_synonyms", 10)

        for synset in synsets[:max_defs]:
            pos_map = {"n": "noun", "v": "verb", "a": "adjective", "r": "adverb", "s": "adjective satellite"}
            pos = pos_map.get(synset.pos(), synset.pos())
            examples = synset.examples()
            definitions.append({
                "pos": pos,
                "definition": synset.definition(),
                "example": examples[0] if examples else ""
            })
            for lemma in synset.lemmas():
                if lemma.name().lower() != word.lower():
                    synonyms.add(lemma.name().replace("_", " "))

        return {
            "word": word.lower(),
            "phonetic": "",
            "audio_url": "",
            "definitions": definitions,
            "synonyms": sorted(list(synonyms))[:max_syns],
            "source": "wordnet"
        }
    except Exception:
        return None


def find_similar_words(word: str, n: int = 8) -> list[str]:
    """
    Find similar/close words when the exact word isn't found.
    Uses multiple strategies:
    1. WordNet morphy (lemmatization - finds base form)
    2. difflib close matches against a common English word list
    3. WordNet similar lemmas
    """
    suggestions = []
    word_lower = word.lower()

    # Strategy 1: WordNet morphy (handles inflections like "running" → "run")
    try:
        from nltk.corpus import wordnet as wn
        for pos in [wn.NOUN, wn.VERB, wn.ADJ, wn.ADV]:
            base = wn.morphy(word_lower, pos)
            if base and base != word_lower and base not in suggestions:
                suggestions.append(base)
    except Exception:
        pass

    # Strategy 2: WordNet lemmas - find words that start similarly
    try:
        from nltk.corpus import wordnet as wn
        # Get all lemma names and find close matches
        all_lemmas = set()
        # Sample from synsets whose name starts with same letters (faster than all lemmas)
        prefix = word_lower[:3] if len(word_lower) >= 3 else word_lower
        for synset in list(wn.all_synsets())[:50000]:
            name = synset.name().split(".")[0].replace("_", " ")
            if name.startswith(prefix):
                all_lemmas.add(name)
            if len(all_lemmas) > 500:
                break

        close = get_close_matches(word_lower, list(all_lemmas), n=6, cutoff=0.6)
        for c in close:
            if c not in suggestions:
                suggestions.append(c)
    except Exception:
        pass

    # Strategy 3: Common English word list via difflib (fast, no internet)
    try:
        common_words = _get_common_words()
        close = get_close_matches(word_lower, common_words, n=5, cutoff=0.7)
        for c in close:
            if c not in suggestions:
                suggestions.append(c)
    except Exception:
        pass

    return suggestions[:n]


def _get_common_words() -> list[str]:
    """Return a list of ~5000 common English words for fuzzy matching."""
    # Inline the most common ~200 for fast startup; use wordnet for the rest
    base = [
        "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract",
        "accept", "access", "account", "accurate", "achieve", "acknowledge", "across",
        "action", "active", "actual", "addition", "adequate", "adjust", "admit", "adopt",
        "advance", "advantage", "affect", "afford", "afraid", "after", "again", "against",
        "agree", "ahead", "allow", "although", "always", "amount", "analyze", "ancient",
        "angry", "announce", "annual", "another", "anxious", "apparent", "approach",
        "appropriate", "argue", "arrange", "aspect", "assess", "assist", "assume",
        "attempt", "attend", "attract", "authority", "available", "aware", "balance",
        "basic", "because", "become", "before", "begin", "belief", "benefit", "between",
        "beyond", "blame", "board", "brave", "break", "bright", "build", "business",
        "calculate", "capable", "careful", "cause", "certain", "challenge", "chance",
        "change", "character", "charge", "choice", "claim", "clear", "climate", "close",
        "collect", "combine", "comfort", "commit", "common", "compare", "complete",
        "complex", "concern", "condition", "confident", "connect", "consider", "consist",
        "contain", "continue", "control", "convince", "correct", "create", "crisis",
        "critical", "culture", "damage", "decide", "define", "degree", "deliver",
        "depend", "describe", "develop", "difference", "difficult", "discuss", "distance",
        "diverse", "divide", "dominant", "during", "effect", "effort", "either",
        "emerge", "enable", "encourage", "establish", "evaluate", "evidence", "except",
        "exist", "expand", "expect", "experience", "explain", "express", "extend",
        "factor", "failure", "familiar", "feature", "finally", "focus", "follow",
        "forget", "former", "frequent", "function", "further", "future", "general",
        "generate", "global", "government", "growth", "happen", "helpful", "human",
        "identify", "ignore", "impact", "improve", "include", "increase", "indicate",
        "influence", "initial", "involve", "issue", "justice", "knowledge", "language",
        "likely", "maintain", "manage", "mention", "method", "migrate", "necessary",
        "observe", "obvious", "obtain", "occur", "offer", "operate", "opportunity",
        "organize", "original", "outcome", "overcome", "participate", "particular",
        "pattern", "perform", "persistent", "positive", "powerful", "prepare", "present",
        "prevent", "previous", "primary", "principle", "process", "produce", "provide",
        "purpose", "quality", "question", "realize", "reason", "receive", "recognize",
        "reduce", "reflect", "reform", "relate", "remain", "remember", "remove",
        "replace", "require", "research", "resolve", "respond", "result", "review",
        "revise", "scientific", "section", "serious", "significant", "similar", "simple",
        "situation", "society", "solution", "specific", "strategy", "structure",
        "subject", "success", "suggest", "support", "survive", "system", "technical",
        "theory", "transfer", "transform", "typical", "understand", "unique", "useful",
        "various", "version", "visible", "vision", "whether", "without", "written"
    ]
    return base


def lookup(word: str) -> dict | None:
    """
    Main lookup: try online first, fall back to WordNet.
    Returns dict or None if not found anywhere.
    """
    word = word.strip().lower()
    if not word:
        return None

    result = lookup_online(word)
    if result and result["definitions"]:
        max_syns = _get_cfg().get("max_synonyms", 10)
        if len(result["synonyms"]) < 3:
            wn_result = lookup_wordnet(word)
            if wn_result:
                extra = [s for s in wn_result["synonyms"] if s not in result["synonyms"]]
                result["synonyms"] = (result["synonyms"] + extra)[:max_syns]
        return result

    # Fallback to WordNet
    return lookup_wordnet(word)


def lookup_with_suggestions(word: str) -> tuple[dict | None, list[str]]:
    """
    Lookup a word. If not found, return (None, [similar words]).
    If found, return (result, []).
    """
    result = lookup(word)
    if result:
        return result, []
    suggestions = find_similar_words(word)
    return None, suggestions


def is_online() -> bool:
    try:
        timeout = _get_cfg().get("online_timeout", 5)
        requests.get("https://api.dictionaryapi.dev", timeout=min(timeout, 3))
        return True
    except Exception:
        return False
