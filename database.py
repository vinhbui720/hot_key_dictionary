"""
Database module - SQLite backend for word history and spaced repetition.
"""
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "dictionary.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Spaced repetition intervals in days (SM-2 inspired)
SR_INTERVALS = [1, 3, 7, 20, 30]


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE NOT NULL,
            phonetic TEXT,
            definitions TEXT,   -- JSON array of {pos, definition, example}
            synonyms TEXT,      -- JSON array of strings
            audio_url TEXT,
            first_looked_up TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            lookup_count INTEGER DEFAULT 1,
            last_looked_up TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS review_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER NOT NULL REFERENCES words(id),
            interval_index INTEGER DEFAULT 0,   -- index into SR_INTERVALS
            next_review TIMESTAMP NOT NULL,
            last_reviewed TIMESTAMP,
            status TEXT DEFAULT 'pending',      -- pending, known, forgotten
            UNIQUE(word_id, interval_index)
        );

        CREATE TABLE IF NOT EXISTS review_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER NOT NULL REFERENCES words(id),
            reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sentence TEXT,
            ai_feedback TEXT,
            grammar_feedback TEXT,
            result TEXT   -- 'pass' | 'fail' | 'skip'
        );
    """)
    conn.commit()
    conn.close()


def upsert_word(word: str, phonetic: str, definitions: list, synonyms: list, audio_url: str):
    """Insert or update a word lookup. Returns word_id."""
    conn = get_connection()
    c = conn.cursor()

    defs_json = json.dumps(definitions)
    syns_json = json.dumps(synonyms)
    now = datetime.now().isoformat()

    c.execute("SELECT id, lookup_count FROM words WHERE word = ?", (word.lower(),))
    row = c.fetchone()

    if row:
        word_id = row["id"]
        c.execute("""
            UPDATE words SET lookup_count = lookup_count + 1,
                last_looked_up = ?,
                phonetic = COALESCE(NULLIF(?, ''), phonetic),
                definitions = ?,
                synonyms = ?,
                audio_url = COALESCE(NULLIF(?, ''), audio_url)
            WHERE id = ?
        """, (now, phonetic, defs_json, syns_json, audio_url, word_id))
    else:
        c.execute("""
            INSERT INTO words (word, phonetic, definitions, synonyms, audio_url, first_looked_up, last_looked_up)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (word.lower(), phonetic, defs_json, syns_json, audio_url, now, now))
        word_id = c.lastrowid

        # Schedule first review in 1 day
        next_review = (datetime.now() + timedelta(days=SR_INTERVALS[0])).isoformat()
        c.execute("""
            INSERT OR IGNORE INTO review_schedule (word_id, interval_index, next_review)
            VALUES (?, 0, ?)
        """, (word_id, next_review))

    conn.commit()
    conn.close()
    return word_id


def get_due_reviews():
    """Return list of words due for review right now."""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""
        SELECT w.word, w.phonetic, w.definitions, w.synonyms,
               rs.id as schedule_id, rs.interval_index, rs.next_review, rs.word_id
        FROM review_schedule rs
        JOIN words w ON w.id = rs.word_id
        WHERE rs.next_review <= ? AND rs.status = 'pending'
        ORDER BY rs.next_review ASC
    """, (now,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def count_due_reviews():
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""
        SELECT COUNT(*) as cnt FROM review_schedule
        WHERE next_review <= ? AND status = 'pending'
    """, (now,))
    count = c.fetchone()["cnt"]
    conn.close()
    return count


def mark_review_result(schedule_id: int, word_id: int, interval_index: int,
                       result: str, sentence: str = "", ai_feedback: str = "",
                       grammar_feedback: str = ""):
    """Mark a review as done and schedule next one."""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()

    # Save session
    c.execute("""
        INSERT INTO review_sessions (word_id, sentence, ai_feedback, grammar_feedback, result)
        VALUES (?, ?, ?, ?, ?)
    """, (word_id, sentence, ai_feedback, grammar_feedback, result))

    if result == "pass":
        next_idx = interval_index + 1
        if next_idx < len(SR_INTERVALS):
            next_review = (datetime.now() + timedelta(days=SR_INTERVALS[next_idx])).isoformat()
            # Mark current as done
            c.execute("UPDATE review_schedule SET status = 'known', last_reviewed = ? WHERE id = ?",
                      (now, schedule_id))
            # Schedule next interval
            c.execute("""
                INSERT OR REPLACE INTO review_schedule (word_id, interval_index, next_review, status)
                VALUES (?, ?, ?, 'pending')
            """, (word_id, next_idx, next_review))
        else:
            # All intervals done - word is mastered
            c.execute("UPDATE review_schedule SET status = 'mastered', last_reviewed = ? WHERE id = ?",
                      (now, schedule_id))
    else:
        # Failed - reset to interval 0 (review again tomorrow)
        next_review = (datetime.now() + timedelta(days=SR_INTERVALS[0])).isoformat()
        c.execute("""
            UPDATE review_schedule SET interval_index = 0, next_review = ?, 
                last_reviewed = ?, status = 'pending'
            WHERE id = ?
        """, (next_review, now, schedule_id))

    conn.commit()
    conn.close()


def get_word_history(limit=50):
    """Return recent word lookup history."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT w.word, w.phonetic, w.lookup_count, w.last_looked_up,
               rs.interval_index, rs.next_review, rs.status
        FROM words w
        LEFT JOIN review_schedule rs ON rs.word_id = w.id
        ORDER BY w.last_looked_up DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_word(word: str):
    """Fetch a cached word from DB."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM words WHERE word = ?", (word.lower(),))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def clear_all() -> int:
    """Delete all words, reviews and sessions. Returns count of deleted words."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM words")
    count = c.fetchone()[0]
    c.executescript("""
        DELETE FROM review_sessions;
        DELETE FROM review_schedule;
        DELETE FROM words;
    """)
    conn.commit()
    conn.close()
    return count


def delete_word(word: str) -> bool:
    """Delete a single word and all its review records."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM words WHERE word = ?", (word.lower(),))
    row = c.fetchone()
    if not row:
        conn.close()
        return False
    wid = row[0]
    c.execute("DELETE FROM review_sessions WHERE word_id = ?", (wid,))
    c.execute("DELETE FROM review_schedule WHERE word_id = ?", (wid,))
    c.execute("DELETE FROM words WHERE id = ?", (wid,))
    conn.commit()
    conn.close()
    return True


def get_stats() -> dict:
    """Return summary stats for the Settings tab."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM words")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM review_schedule WHERE status = 'pending'")
    pending = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM review_schedule WHERE status = 'mastered'")
    mastered = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM review_sessions")
    sessions = c.fetchone()[0]
    conn.close()
    return {"total_words": total, "pending_reviews": pending,
            "mastered": mastered, "total_sessions": sessions}


# Init on import
init_db()
