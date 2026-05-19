"""
Vinh's Dictionary – UI
Two-window design:
  QuickPopup  – frameless, cursor-anchored, Lookup only; shown by F9 hotkey;
                hides automatically when the user clicks outside.
  MainWindow  – full app (all tabs, normal window chrome); opened only via
                the system-tray / Ubuntu-header icon menu.
"""
import sys
import json
import threading
import subprocess
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QScrollArea, QFrame, QLineEdit,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QSizePolicy, QGraphicsDropShadowEffect,
    QSystemTrayIcon, QMenu, QAction, QCheckBox, QSpinBox,
    QComboBox, QFormLayout, QGroupBox, QSlider, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint, QSize, QEvent
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QPixmap, QCursor

sys.path.insert(0, str(Path(__file__).parent))
import database as db
import dictionary_api as api
import tts
import ai_checker
import config as cfg_mod

APP_DIR = Path(__file__).parent


# ─── Colors ──────────────────────────────────────────────────────────────────
BG       = "#1a1b26"
BG2      = "#24283b"
BG3      = "#2f3549"
BORDER   = "#3b4261"
ACCENT   = "#7aa2f7"
GREEN    = "#9ece6a"
YELLOW   = "#e0af68"
RED      = "#f7768e"
ORANGE   = "#ff9e64"
MUTED    = "#565f89"
TEXT     = "#c0caf5"
TEXT_DIM = "#737aa2"


STYLE = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: 'Segoe UI', 'Inter', 'Noto Sans', sans-serif;
    font-size: 14px;
}}
QScrollArea, QScrollArea > QWidget > QWidget {{
    background-color: {BG};
    border: none;
}}
QScrollBar:vertical {{
    background: {BG2};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QPushButton {{
    background-color: {BG3};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {ACCENT};
    color: {BG};
    border-color: {ACCENT};
}}
QPushButton:pressed {{ background-color: #5a7fd6; }}
QPushButton#btn_save {{
    background-color: {GREEN};
    color: {BG};
    font-weight: bold;
    border: none;
}}
QPushButton#btn_save:hover {{ background-color: #7eba52; }}
QLineEdit {{
    background-color: {BG2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 14px;
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}
QTextEdit {{
    background-color: {BG2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px;
    font-size: 14px;
}}
QSpinBox, QComboBox {{
    background-color: {BG2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 13px;
}}
QSpinBox:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{
    background: {BG2};
    color: {TEXT};
    selection-background-color: {BG3};
}}
QCheckBox {{
    color: {TEXT};
    font-size: 13px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {BORDER};
    border-radius: 3px;
    background: {BG2};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QGroupBox {{
    color: {TEXT_DIM};
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
    font-size: 12px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: {MUTED};
    letter-spacing: 1px;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background: {BG};
}}
QTabBar::tab {{
    background: {BG2};
    color: {TEXT_DIM};
    padding: 8px 16px;
    border: none;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
    background: {BG};
}}
QTabBar::tab:hover {{ color: {TEXT}; }}
QTableWidget {{
    background: {BG2};
    border: 1px solid {BORDER};
    gridline-color: {BORDER};
    border-radius: 6px;
}}
QTableWidget::item {{ padding: 6px; }}
QTableWidget::item:selected {{ background: {BG3}; color: {ACCENT}; }}
QHeaderView::section {{
    background: {BG3};
    color: {TEXT_DIM};
    padding: 6px;
    border: none;
    font-size: 12px;
    font-weight: bold;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 14px; height: 14px;
    border-radius: 7px;
    margin: -5px 0;
}}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QLabel#word_title {{
    font-size: 26px;
    font-weight: bold;
    color: {ACCENT};
}}
QLabel#phonetic {{
    font-size: 14px;
    color: {TEXT_DIM};
}}
QLabel#section_header {{
    font-size: 11px;
    font-weight: bold;
    color: {MUTED};
    letter-spacing: 1.5px;
}}
QLabel#pos_badge {{
    font-size: 11px;
    font-weight: bold;
    color: {BG};
    background: {YELLOW};
    border-radius: 4px;
    padding: 2px 7px;
}}
QFrame#card {{
    background: {BG2};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QLabel#badge_due {{
    background: {RED};
    color: white;
    border-radius: 10px;
    font-size: 11px;
    font-weight: bold;
    padding: 2px 7px;
}}
QLabel#suggest_label {{
    color: {ORANGE};
    font-size: 13px;
    font-style: italic;
}}
"""


# ─── Worker threads ───────────────────────────────────────────────────────────

class LookupThread(QThread):
    result_ready  = pyqtSignal(dict)
    not_found     = pyqtSignal(str, list)   # (word, suggestions)

    def __init__(self, word):
        super().__init__()
        self.word = word

    def run(self):
        result, suggestions = api.lookup_with_suggestions(self.word)
        if result:
            self.result_ready.emit(result)
        else:
            self.not_found.emit(self.word, suggestions)


class AICheckThread(QThread):
    result_ready = pyqtSignal(dict)

    def __init__(self, word, sentence, online):
        super().__init__()
        self.word = word
        self.sentence = sentence
        self.online = online

    def run(self):
        result = ai_checker.check_sentence(self.word, self.sentence, self.online)
        self.result_ready.emit(result)


# ─── Definition Card ──────────────────────────────────────────────────────────

class DefinitionCard(QFrame):
    def __init__(self, pos: str, definition: str, example: str, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(14, 12, 14, 12)

        if pos:
            top = QHBoxLayout()
            badge = QLabel(pos)
            badge.setObjectName("pos_badge")
            top.addWidget(badge)
            top.addStretch()
            layout.addLayout(top)

        defn_label = QLabel(definition)
        defn_label.setWordWrap(True)
        defn_label.setStyleSheet(f"color: {TEXT}; font-size: 14px;")
        layout.addWidget(defn_label)

        if example:
            ex_label = QLabel(f'"{example}"')
            ex_label.setWordWrap(True)
            ex_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; font-style: italic;")
            layout.addWidget(ex_label)


# ─── Review Widget ────────────────────────────────────────────────────────────

class ReviewWidget(QWidget):
    review_done = pyqtSignal()

    def __init__(self, reviews: list, parent=None):
        super().__init__(parent)
        self.reviews = reviews
        self.current_idx = 0
        self.online = api.is_online()
        self._check_thread = None
        self._last_result = None
        self._build_ui()
        self._load_current()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        hdr = QHBoxLayout()
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px;")
        hdr.addWidget(self.progress_label)
        hdr.addStretch()
        skip_btn = QPushButton("Skip All")
        skip_btn.setFixedWidth(90)
        skip_btn.clicked.connect(self.review_done.emit)
        hdr.addWidget(skip_btn)
        layout.addLayout(hdr)

        self.word_label = QLabel()
        self.word_label.setObjectName("word_title")
        self.word_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.word_label)

        self.def_label = QLabel()
        self.def_label.setWordWrap(True)
        self.def_label.setAlignment(Qt.AlignCenter)
        self.def_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; padding: 0 20px;")
        layout.addWidget(self.def_label)

        instr = QLabel("✍️  Write a sentence using this word:")
        instr.setStyleSheet(f"color: {YELLOW}; font-size: 13px; font-weight: bold;")
        layout.addWidget(instr)

        self.sentence_input = QTextEdit()
        self.sentence_input.setPlaceholderText("Type your sentence here...")
        self.sentence_input.setFixedHeight(80)
        layout.addWidget(self.sentence_input)

        check_btn = QPushButton("🔍 Check My Sentence")
        check_btn.clicked.connect(self._check_sentence)
        layout.addWidget(check_btn)

        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setStyleSheet(
            f"color: {TEXT}; font-size: 13px; background: {BG2}; "
            f"border: 1px solid {BORDER}; border-radius: 6px; padding: 10px;"
        )
        self.feedback_label.hide()
        layout.addWidget(self.feedback_label)

        btn_row = QHBoxLayout()
        self.fail_btn = QPushButton("❌ Not yet")
        self.fail_btn.setStyleSheet(f"background: {RED}; color: white; font-weight: bold;")
        self.fail_btn.clicked.connect(lambda: self._submit("fail"))
        self.fail_btn.hide()

        self.pass_btn = QPushButton("✅ Got it!")
        self.pass_btn.setStyleSheet(f"background: {GREEN}; color: {BG}; font-weight: bold;")
        self.pass_btn.clicked.connect(lambda: self._submit("pass"))
        self.pass_btn.hide()

        btn_row.addWidget(self.fail_btn)
        btn_row.addWidget(self.pass_btn)
        layout.addLayout(btn_row)
        layout.addStretch()

    def _load_current(self):
        if self.current_idx >= len(self.reviews):
            self.review_done.emit()
            return
        item = self.reviews[self.current_idx]
        self.progress_label.setText(f"Word {self.current_idx + 1} of {len(self.reviews)}")
        self.word_label.setText(item["word"].upper())
        self.sentence_input.clear()
        self.feedback_label.hide()
        self.pass_btn.hide()
        self.fail_btn.hide()
        try:
            defs = json.loads(item["definitions"]) if isinstance(item["definitions"], str) else item["definitions"]
            self.def_label.setText(defs[0]["definition"] if defs else "")
        except Exception:
            self.def_label.setText("")

    def _check_sentence(self):
        sentence = self.sentence_input.toPlainText().strip()
        if not sentence:
            return
        item = self.reviews[self.current_idx]
        self.feedback_label.setText("⏳ Checking with AI...")
        self.feedback_label.show()
        self._check_thread = AICheckThread(item["word"], sentence, self.online)
        self._check_thread.result_ready.connect(self._on_check_done)
        self._check_thread.start()

    def _on_check_done(self, result):
        self._last_result = result
        self.feedback_label.setText(result["summary"])
        self.pass_btn.show()
        self.fail_btn.show()

    def _submit(self, outcome: str):
        item = self.reviews[self.current_idx]
        sentence = self.sentence_input.toPlainText().strip()
        ai_fb = grammar_fb = ""
        if self._last_result:
            if self._last_result.get("ollama"):
                ai_fb = self._last_result["ollama"].get("feedback", "")
            if self._last_result.get("languagetool"):
                grammar_fb = "; ".join(
                    m["message"] for m in self._last_result["languagetool"].get("matches", [])
                )
        db.mark_review_result(
            item["schedule_id"], item["word_id"], item["interval_index"],
            outcome, sentence, ai_fb, grammar_fb
        )
        self.current_idx += 1
        self._load_current()


# ─── Settings Tab ─────────────────────────────────────────────────────────────

class SettingsTab(QWidget):
    settings_saved   = pyqtSignal(dict)
    database_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(16)

        # ── Hotkey ──────────────────────────────────────────────
        hk_group = QGroupBox("HOTKEY")
        hk_layout = QFormLayout(hk_group)
        hk_layout.setSpacing(10)
        self.hotkey_input = QLineEdit()
        self.hotkey_input.setPlaceholderText("e.g. f9  or  ctrl+d  or  alt+f2")
        hk_layout.addRow("Hotkey:", self.hotkey_input)
        hint = QLabel("Tip: F1–F12 work best. Combos: ctrl+d, alt+f2, ctrl+shift+d")
        hint.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        hint.setWordWrap(True)
        hk_layout.addRow("", hint)
        layout.addWidget(hk_group)

        # ── TTS ─────────────────────────────────────────────────
        tts_group = QGroupBox("TEXT TO SPEECH")
        tts_layout = QFormLayout(tts_group)
        tts_layout.setSpacing(10)
        self.tts_enabled = QCheckBox("Enable TTS")
        tts_layout.addRow(self.tts_enabled)
        self.tts_autoplay = QCheckBox("Auto-speak word when popup opens")
        tts_layout.addRow(self.tts_autoplay)
        speed_row = QHBoxLayout()
        self.tts_speed = QSlider(Qt.Horizontal)
        self.tts_speed.setRange(80, 300)
        self.tts_speed.setTickInterval(20)
        self.tts_speed_label = QLabel("150 wpm")
        self.tts_speed_label.setFixedWidth(60)
        self.tts_speed_label.setStyleSheet(f"color: {TEXT_DIM};")
        self.tts_speed.valueChanged.connect(lambda v: self.tts_speed_label.setText(f"{v} wpm"))
        speed_row.addWidget(self.tts_speed)
        speed_row.addWidget(self.tts_speed_label)
        tts_layout.addRow("Speed:", speed_row)
        layout.addWidget(tts_group)

        # ── Dictionary ──────────────────────────────────────────
        dict_group = QGroupBox("DICTIONARY")
        dict_layout = QFormLayout(dict_group)
        dict_layout.setSpacing(10)
        self.max_defs = QSpinBox()
        self.max_defs.setRange(1, 15)
        self.max_defs.setSuffix(" definitions")
        dict_layout.addRow("Show max:", self.max_defs)
        self.max_syns = QSpinBox()
        self.max_syns.setRange(1, 20)
        self.max_syns.setSuffix(" synonyms")
        dict_layout.addRow("Synonyms:", self.max_syns)
        self.online_timeout = QSpinBox()
        self.online_timeout.setRange(2, 15)
        self.online_timeout.setSuffix(" sec")
        dict_layout.addRow("Online timeout:", self.online_timeout)
        layout.addWidget(dict_group)

        # ── Spaced Repetition ────────────────────────────────────
        sr_group = QGroupBox("SPACED REPETITION INTERVALS (days)")
        sr_layout = QFormLayout(sr_group)
        sr_layout.setSpacing(8)
        self.sr_inputs = []
        for lbl in ["1st review:", "2nd review:", "3rd review:", "4th review:", "5th review:"]:
            spin = QSpinBox()
            spin.setRange(1, 365)
            spin.setSuffix(" days")
            sr_layout.addRow(lbl, spin)
            self.sr_inputs.append(spin)
        layout.addWidget(sr_group)

        # ── AI Checker ──────────────────────────────────────────
        ai_group = QGroupBox("AI SENTENCE CHECKER")
        ai_layout = QFormLayout(ai_group)
        ai_layout.setSpacing(10)
        self.ollama_model = QComboBox()
        self.ollama_model.setEditable(True)
        self.ollama_model.addItems([
            "llama3.2:3b", "llama3.2:7b", "llama3.1:8b",
            "mistral:7b", "phi3:mini", "gemma2:2b"
        ])
        ai_layout.addRow("Ollama model:", self.ollama_model)
        self.ollama_url = QLineEdit()
        self.ollama_url.setPlaceholderText("http://localhost:11434")
        ai_layout.addRow("Ollama URL:", self.ollama_url)
        self.languagetool_enabled = QCheckBox("Enable LanguageTool grammar check (requires internet)")
        ai_layout.addRow(self.languagetool_enabled)
        layout.addWidget(ai_group)

        # ── Notifications ────────────────────────────────────────
        notif_group = QGroupBox("NOTIFICATIONS")
        notif_layout = QFormLayout(notif_group)
        notif_layout.setSpacing(10)
        self.notify_reviews = QCheckBox("Notify when words are due for review")
        notif_layout.addRow(self.notify_reviews)
        self.notify_interval = QSpinBox()
        self.notify_interval.setRange(5, 240)
        self.notify_interval.setSuffix(" min")
        notif_layout.addRow("Check interval:", self.notify_interval)
        layout.addWidget(notif_group)

        # ── Window ──────────────────────────────────────────────
        win_group = QGroupBox("MAIN WINDOW SIZE")
        win_layout = QFormLayout(win_group)
        win_layout.setSpacing(10)
        self.always_on_top = QCheckBox("Main window always on top")
        win_layout.addRow(self.always_on_top)
        w_row = QHBoxLayout()
        self.win_width = QSpinBox()
        self.win_width.setRange(400, 1200)
        self.win_width.setSuffix("px")
        self.win_height = QSpinBox()
        self.win_height.setRange(300, 1000)
        self.win_height.setSuffix("px")
        w_row.addWidget(QLabel("W:"))
        w_row.addWidget(self.win_width)
        w_row.addWidget(QLabel("H:"))
        w_row.addWidget(self.win_height)
        w_row.addStretch()
        win_layout.addRow("Size:", w_row)
        layout.addWidget(win_group)

        # ── Quick Popup ──────────────────────────────────────────
        qp_group = QGroupBox("QUICK POPUP (hotkey)")
        qp_layout = QFormLayout(qp_group)
        qp_layout.setSpacing(10)
        self.popup_width = QSpinBox()
        self.popup_width.setRange(300, 900)
        self.popup_width.setSuffix("px")
        qp_layout.addRow("Width:", self.popup_width)
        self.popup_height = QSpinBox()
        self.popup_height.setRange(200, 800)
        self.popup_height.setSuffix("px")
        qp_layout.addRow("Height:", self.popup_height)
        layout.addWidget(qp_group)

        # ── Save ────────────────────────────────────────────────
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("btn_save")
        save_btn.setFixedHeight(42)
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"color: {GREEN}; font-size: 13px;")
        layout.addWidget(self.status_label)

        # ── Database ────────────────────────────────────────────
        db_group = QGroupBox("DATABASE")
        db_layout = QVBoxLayout(db_group)
        db_layout.setSpacing(10)
        self.db_stats_label = QLabel()
        self.db_stats_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        self.db_stats_label.setWordWrap(True)
        db_layout.addWidget(self.db_stats_label)
        db_btn_row = QHBoxLayout()
        refresh_db_btn = QPushButton("Refresh Stats")
        refresh_db_btn.clicked.connect(self._refresh_db_stats)
        db_btn_row.addWidget(refresh_db_btn)
        clear_btn = QPushButton("Clear All Data")
        clear_btn.setStyleSheet(f"background: {RED}; color: white; border: none; font-weight: bold;")
        clear_btn.clicked.connect(self._clear_database)
        db_btn_row.addWidget(clear_btn)
        db_layout.addLayout(db_btn_row)
        layout.addWidget(db_group)

        layout.addStretch()
        self._refresh_db_stats()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _load_values(self):
        c = cfg_mod.cfg()
        self.hotkey_input.setText(c.get("hotkey", "f9"))
        self.tts_enabled.setChecked(c.get("tts_enabled", True))
        self.tts_autoplay.setChecked(c.get("tts_autoplay", False))
        self.tts_speed.setValue(c.get("tts_speed", 150))
        self.max_defs.setValue(c.get("max_definitions", 6))
        self.max_syns.setValue(c.get("max_synonyms", 10))
        self.online_timeout.setValue(c.get("online_timeout", 5))
        intervals = c.get("sr_intervals", [1, 3, 7, 20, 30])
        for i, spin in enumerate(self.sr_inputs):
            spin.setValue(intervals[i] if i < len(intervals) else 30)
        self.ollama_model.setCurrentText(c.get("ollama_model", "llama3.2:3b"))
        self.ollama_url.setText(c.get("ollama_url", "http://localhost:11434"))
        self.languagetool_enabled.setChecked(c.get("languagetool_enabled", True))
        self.notify_reviews.setChecked(c.get("notify_reviews", True))
        self.notify_interval.setValue(c.get("notify_interval_minutes", 30))
        self.always_on_top.setChecked(c.get("always_on_top", True))
        self.win_width.setValue(c.get("window_width", 580))
        self.win_height.setValue(c.get("window_height", 600))
        self.popup_width.setValue(c.get("popup_width", 520))
        self.popup_height.setValue(c.get("popup_height", 480))

    def _save(self):
        new_cfg = cfg_mod.update(
            hotkey=self.hotkey_input.text().strip().lower() or "f9",
            tts_enabled=self.tts_enabled.isChecked(),
            tts_autoplay=self.tts_autoplay.isChecked(),
            tts_speed=self.tts_speed.value(),
            max_definitions=self.max_defs.value(),
            max_synonyms=self.max_syns.value(),
            online_timeout=self.online_timeout.value(),
            sr_intervals=[s.value() for s in self.sr_inputs],
            ollama_model=self.ollama_model.currentText().strip(),
            ollama_url=self.ollama_url.text().strip() or "http://localhost:11434",
            languagetool_enabled=self.languagetool_enabled.isChecked(),
            notify_reviews=self.notify_reviews.isChecked(),
            notify_interval_minutes=self.notify_interval.value(),
            always_on_top=self.always_on_top.isChecked(),
            window_width=self.win_width.value(),
            window_height=self.win_height.value(),
            popup_width=self.popup_width.value(),
            popup_height=self.popup_height.value(),
        )
        cfg_mod.reload()
        ai_checker.OLLAMA_MODEL = new_cfg.get("ollama_model", "llama3.2:3b")
        ai_checker.OLLAMA_URL = new_cfg.get("ollama_url", "http://localhost:11434") + "/api/generate"
        self.status_label.setText("✅ Saved!")
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))
        self.settings_saved.emit(new_cfg)

    def _refresh_db_stats(self):
        stats = db.get_stats()
        self.db_stats_label.setText(
            f"Words looked up: {stats['total_words']}   |   "
            f"Pending review: {stats['pending_reviews']}   |   "
            f"Mastered: {stats['mastered']}   |   "
            f"Review sessions: {stats['total_sessions']}"
        )

    def _clear_database(self):
        stats = db.get_stats()
        total = stats["total_words"]
        if total == 0:
            self.status_label.setText("Database is already empty.")
            return
        reply = QMessageBox.question(
            self, "Clear all data",
            f"This will permanently delete all {total} word(s) and their review history.\n\nAre you sure?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            deleted = db.clear_all()
            self.status_label.setStyleSheet(f"color: {RED}; font-size: 13px;")
            self.status_label.setText(f"Deleted {deleted} words and all review history.")
            QTimer.singleShot(4000, lambda: (
                self.status_label.setText(""),
                self.status_label.setStyleSheet(f"color: {GREEN}; font-size: 13px;")
            ))
            self._refresh_db_stats()
            self.database_cleared.emit()


# ─── Shared lookup mixin ──────────────────────────────────────────────────────
# Both QuickPopup and MainWindow use this to avoid duplicating lookup logic.

class LookupMixin:
    """
    Mixin that provides a fully functional lookup area.
    The host widget must call _init_lookup_mixin(layout) once, passing the
    QVBoxLayout where the search bar + result scroll should be inserted.
    It must also define self._lookup_thread = None before calling.
    """

    def _init_lookup_mixin(self, layout: QVBoxLayout):
        # Search bar
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        hotkey = cfg_mod.cfg().get("hotkey", "F9").upper()
        self.search_input.setPlaceholderText(
            f"Type a word or highlight text → {hotkey}…"
        )
        self.search_input.returnPressed.connect(self._do_lookup)
        search_row.addWidget(self.search_input)

        search_btn = QPushButton("🔍")
        search_btn.setFixedSize(38, 38)
        search_btn.setToolTip("Search")
        search_btn.clicked.connect(self._do_lookup)
        search_row.addWidget(search_btn)

        clear_btn = QPushButton("✕")
        clear_btn.setFixedSize(30, 38)
        clear_btn.setStyleSheet(
            f"color: {MUTED}; background: transparent; border: none; font-size: 13px;"
        )
        clear_btn.setToolTip("Clear")
        clear_btn.clicked.connect(self._clear_search)
        search_row.addWidget(clear_btn)
        layout.addLayout(search_row)

        # Result scroll area
        self.result_scroll = QScrollArea()
        self.result_scroll.setWidgetResizable(True)
        self.result_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.result_content = QWidget()
        self.result_layout = QVBoxLayout(self.result_content)
        self.result_layout.setSpacing(10)
        self.result_layout.setContentsMargins(0, 0, 8, 0)
        self.result_layout.addStretch()
        self.result_scroll.setWidget(self.result_content)
        layout.addWidget(self.result_scroll)

    def _clear_search(self):
        self.search_input.clear()
        self._clear_results()
        self.search_input.setFocus()

    def _clear_results(self):
        while self.result_layout.count() > 1:
            item = self.result_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_loading(self):
        self._clear_results()
        loading = QLabel("⏳ Looking up…")
        loading.setAlignment(Qt.AlignCenter)
        loading.setStyleSheet(f"color: {TEXT_DIM}; font-size: 15px;")
        self.result_layout.insertWidget(0, loading)

    def _do_lookup(self):
        word = self.search_input.text().strip()
        if not word:
            self.search_input.setFocus()
            return
        self._current_word = word
        self._show_loading()
        self._lookup_thread = LookupThread(word)
        self._lookup_thread.result_ready.connect(self._on_result)
        self._lookup_thread.not_found.connect(self._on_not_found)
        self._lookup_thread.start()

    def lookup_word(self, word: str):
        """Public entry: fill search bar and trigger lookup."""
        self.search_input.setText(word)
        self.show()
        self.raise_()
        self.activateWindow()
        self._do_lookup()
        if cfg_mod.cfg().get("tts_autoplay", False) and cfg_mod.cfg().get("tts_enabled", True):
            QTimer.singleShot(800, lambda: tts.speak(word))

    def _on_result(self, result: dict):
        self._clear_results()

        db.upsert_word(
            result["word"],
            result.get("phonetic", ""),
            result.get("definitions", []),
            result.get("synonyms", []),
            result.get("audio_url", "")
        )

        idx = 0

        # Word header card
        top_card = QFrame()
        top_card.setObjectName("card")
        top_l = QHBoxLayout(top_card)
        top_l.setContentsMargins(16, 14, 16, 14)

        word_col = QVBoxLayout()
        wl = QLabel(result["word"])
        wl.setObjectName("word_title")
        word_col.addWidget(wl)
        if result.get("phonetic"):
            pl = QLabel(result["phonetic"])
            pl.setObjectName("phonetic")
            word_col.addWidget(pl)
        src = QLabel(f"via {result.get('source', 'online')}")
        src.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        word_col.addWidget(src)
        top_l.addLayout(word_col)
        top_l.addStretch()

        if cfg_mod.cfg().get("tts_enabled", True):
            speak_btn = QPushButton("🔊")
            speak_btn.setFixedSize(40, 40)
            speak_btn.setToolTip("Listen to pronunciation")
            speak_btn.clicked.connect(
                lambda: tts.speak(result["word"], result.get("audio_url", ""))
            )
            top_l.addWidget(speak_btn)

        self.result_layout.insertWidget(idx, top_card); idx += 1

        if result.get("definitions"):
            hdr = QLabel("DEFINITIONS")
            hdr.setObjectName("section_header")
            self.result_layout.insertWidget(idx, hdr); idx += 1
            for d in result["definitions"]:
                card = DefinitionCard(d.get("pos",""), d.get("definition",""), d.get("example",""))
                self.result_layout.insertWidget(idx, card); idx += 1

        if result.get("synonyms"):
            hdr2 = QLabel("SYNONYMS")
            hdr2.setObjectName("section_header")
            self.result_layout.insertWidget(idx, hdr2); idx += 1
            syn_frame = QFrame()
            syn_frame.setObjectName("card")
            syn_l = QHBoxLayout(syn_frame)
            syn_l.setContentsMargins(12, 10, 12, 10)
            syn_l.setSpacing(8)
            for syn in result["synonyms"]:
                btn = QPushButton(syn)
                btn.setFixedHeight(28)
                btn.setStyleSheet(
                    f"background: {BG3}; color: {ACCENT}; border: 1px solid {ACCENT}; "
                    f"border-radius: 14px; padding: 0 10px; font-size: 12px;"
                )
                btn.clicked.connect(lambda _, w=syn: self.lookup_word(w))
                syn_l.addWidget(btn)
            syn_l.addStretch()
            self.result_layout.insertWidget(idx, syn_frame); idx += 1

        # Notify main window to refresh history (if we're the quick popup)
        self._notify_history_refresh()

    def _on_not_found(self, word: str, suggestions: list):
        self._clear_results()
        err_frame = QFrame()
        err_frame.setObjectName("card")
        err_l = QVBoxLayout(err_frame)
        err_l.setContentsMargins(16, 14, 16, 14)
        err_l.setSpacing(8)
        err_msg = QLabel(f'❌  Word not found: "<b>{word}</b>"')
        err_msg.setStyleSheet(f"color: {RED}; font-size: 14px;")
        err_l.addWidget(err_msg)
        if suggestions:
            did_you_mean = QLabel("Did you mean:")
            did_you_mean.setObjectName("suggest_label")
            err_l.addWidget(did_you_mean)
            btn_row = QHBoxLayout()
            btn_row.setSpacing(8)
            for sug in suggestions:
                btn = QPushButton(sug)
                btn.setFixedHeight(30)
                btn.setStyleSheet(
                    f"background: {BG3}; color: {ORANGE}; border: 1px solid {ORANGE}; "
                    f"border-radius: 15px; padding: 0 12px; font-size: 13px;"
                )
                btn.clicked.connect(lambda _, w=sug: self.lookup_word(w))
                btn_row.addWidget(btn)
            btn_row.addStretch()
            err_l.addLayout(btn_row)
        else:
            no_sug = QLabel("No similar words found. Check spelling?")
            no_sug.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px;")
            err_l.addWidget(no_sug)
        self.result_layout.insertWidget(0, err_frame)

    def _notify_history_refresh(self):
        """Override in subclass if needed."""
        pass


# ─── Quick Popup ─────────────────────────────────────────────────────────────
# Frameless, no window controls, appears below the mouse cursor.
# Hides automatically when focus is lost (user clicks outside).

class QuickPopup(LookupMixin, QWidget):
    """
    Lightweight lookup popup triggered by hotkey.
    - Frameless, tool-window style (no titlebar, no taskbar entry)
    - Positioned directly below the mouse cursor
    - Auto-hides on focus-out (click anywhere outside)
    - Stays alive while user types / clicks inside
    """

    # Signal so MainWindow can refresh its history tab after a lookup
    word_looked_up = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_word = ""
        self._lookup_thread = None
        self._main_window = None      # set by main.py after both are created

        c = cfg_mod.cfg()
        self.resize(c.get("popup_width", 520), c.get("popup_height", 480))

        self.setWindowFlags(
            Qt.Tool                     # no taskbar entry, no focus-steal from tray
            | Qt.FramelessWindowHint    # no titlebar / window controls
            | Qt.WindowStaysOnTopHint   # float above other apps
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setStyleSheet(STYLE + f"""
            QuickPopup {{
                border: 2px solid {BORDER};
                border-radius: 10px;
            }}
        """)

        self._build_ui()

        # Install app-level event filter to detect clicks outside
        QApplication.instance().installEventFilter(self)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        # Slim header: title + close button
        hdr = QHBoxLayout()
        title = QLabel("📖 Quick Lookup")
        title.setStyleSheet(f"color: {ACCENT}; font-size: 13px; font-weight: bold;")
        hdr.addWidget(title)
        hdr.addStretch()

        open_full_btn = QPushButton("Open Full →")
        open_full_btn.setFixedHeight(24)
        open_full_btn.setStyleSheet(
            f"background: transparent; color: {TEXT_DIM}; border: 1px solid {BORDER}; "
            f"border-radius: 4px; font-size: 11px; padding: 0 8px;"
        )
        open_full_btn.setToolTip("Open the full dictionary window")
        open_full_btn.clicked.connect(self._open_full)
        hdr.addWidget(open_full_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(
            f"background: transparent; border: none; color: {MUTED}; font-size: 14px;"
        )
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)
        root.addLayout(hdr)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        root.addWidget(sep)

        # Lookup area (search bar + results) from mixin
        self._init_lookup_mixin(root)

    def _open_full(self):
        """Open the full MainWindow and hide this popup."""
        if self._main_window:
            self._main_window.show_window()
        self.hide()

    def _notify_history_refresh(self):
        """After a successful lookup, tell MainWindow to refresh history."""
        if self._main_window:
            self._main_window._load_history()
        self.word_looked_up.emit()

    # ── Positioning ──────────────────────────────────────────────────────────

    def show_at_cursor(self, word: str = ""):
        """Show below the cursor; optionally prefill + lookup a word."""
        pos  = QCursor.pos()
        geo  = QApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()

        # Place below cursor, nudge left so cursor is in the top area
        x = pos.x() - 20
        y = pos.y() + 18   # 18px below cursor tip

        # Keep within screen bounds
        x = max(geo.left(), min(x, geo.right()  - w))
        y = max(geo.top(),  min(y, geo.bottom() - h))

        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        self.search_input.setFocus()

        if word:
            self.lookup_word(word)

    # ── Auto-hide on outside click ────────────────────────────────────────────

    def eventFilter(self, obj, event):
        if self.isVisible() and event.type() == QEvent.MouseButtonPress:
            # Convert global click position to local coords
            try:
                global_pos = event.globalPos()
            except AttributeError:
                return False
            if not self.geometry().contains(global_pos):
                self.hide()
        return False   # never consume the event

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)


# ─── Main Window ─────────────────────────────────────────────────────────────
# Full app: all four tabs, normal window chrome.
# Only opened from the system tray / Ubuntu header icon menu.

class MainWindow(LookupMixin, QWidget):
    hotkey_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        c = cfg_mod.cfg()
        self.setWindowTitle("Vinh's Dictionary")
        self.setObjectName("vinh-dictionary")
        self.setMinimumSize(500, 400)
        self.resize(c.get("window_width", 580), c.get("window_height", 600))

        flags = Qt.Window
        if c.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setStyleSheet(STYLE)

        self._current_word = ""
        self._lookup_thread = None
        self.settings_tab_index = 3

        self._build_ui()
        self._center_on_screen()

        self._review_timer = QTimer(self)
        self._review_timer.timeout.connect(self._check_reviews)
        self._review_timer.start(30 * 60 * 1000)
        self._check_reviews()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──
        header = QWidget()
        header.setFixedHeight(52)
        header.setStyleSheet(f"background: {BG2}; border-bottom: 1px solid {BORDER};")
        hdr = QHBoxLayout(header)
        hdr.setContentsMargins(16, 0, 12, 0)

        title = QLabel("📖 Vinh's Dictionary")
        title.setStyleSheet(f"color: {ACCENT}; font-size: 15px; font-weight: bold;")
        hdr.addWidget(title)
        hdr.addStretch()

        self.due_badge = QLabel()
        self.due_badge.setObjectName("badge_due")
        self.due_badge.hide()
        hdr.addWidget(self.due_badge)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            f"background: transparent; border: none; color: {MUTED}; font-size: 16px;"
        )
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)
        root.addWidget(header)

        # ── Tabs ──
        self.tabs = QTabWidget()

        # Lookup tab – built with mixin
        lookup_tab = QWidget()
        lookup_layout = QVBoxLayout(lookup_tab)
        lookup_layout.setContentsMargins(14, 14, 14, 14)
        lookup_layout.setSpacing(10)
        self._init_lookup_mixin(lookup_layout)
        self.tabs.addTab(lookup_tab, "Lookup")

        # Review tab
        self.review_tab_container = QWidget()
        self.review_tab_layout = QVBoxLayout(self.review_tab_container)
        self.review_tab_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs.addTab(self.review_tab_container, "Review")

        # History tab
        self.history_tab = self._build_history_tab()
        self.tabs.addTab(self.history_tab, "History")

        # Settings tab
        self.settings_widget = SettingsTab()
        self.settings_widget.settings_saved.connect(self._on_settings_saved)
        self.settings_widget.database_cleared.connect(self._load_history)
        self.settings_widget.database_cleared.connect(self._check_reviews)
        self.tabs.addTab(self.settings_widget, "Settings")
        self.settings_tab_index = 3

        root.addWidget(self.tabs)

    # ── History tab ───────────────────────────────────────────────────────────

    def _build_history_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        top_row = QHBoxLayout()
        title = QLabel("Your word history")
        title.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px;")
        top_row.addWidget(title)
        top_row.addStretch()
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setFixedWidth(90)
        refresh_btn.clicked.connect(self._load_history)
        top_row.addWidget(refresh_btn)
        layout.addLayout(top_row)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(
            ["Word", "Last Lookup", "Next Review", "Stage", "Status"]
        )
        h = self.history_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.cellDoubleClicked.connect(self._history_double_click)
        layout.addWidget(self.history_table)

        hint = QLabel("💡 Double-click a word to look it up again")
        hint.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        layout.addWidget(hint)

        self._load_history()
        return widget

    def _load_history(self):
        rows = db.get_word_history(100)
        self.history_table.setRowCount(len(rows))
        stage_names = ["1d", "3d", "7d", "20d", "1mo", "✅"]
        for i, row in enumerate(rows):
            self.history_table.setItem(i, 0, QTableWidgetItem(row["word"]))
            self.history_table.setItem(i, 1, QTableWidgetItem((row.get("last_looked_up") or "")[:10]))
            self.history_table.setItem(i, 2, QTableWidgetItem((row.get("next_review") or "")[:10]))
            stage_idx = row.get("interval_index") or 0
            self.history_table.setItem(i, 3, QTableWidgetItem(stage_names[min(stage_idx, 5)]))
            status = row.get("status") or "pending"
            sit = QTableWidgetItem(status)
            sit.setForeground(QColor(
                GREEN if status == "mastered" else YELLOW if status == "pending" else MUTED
            ))
            self.history_table.setItem(i, 4, sit)

    def _history_double_click(self, row, col):
        item = self.history_table.item(row, 0)
        if item:
            self.lookup_word(item.text())
            self.tabs.setCurrentIndex(0)

    # ── Reviews ───────────────────────────────────────────────────────────────

    def _check_reviews(self):
        count = db.count_due_reviews()
        if count > 0:
            self.due_badge.setText(f"{count} due")
            self.due_badge.show()
            self._load_review_tab()
        else:
            self.due_badge.hide()

    def _load_review_tab(self):
        reviews = db.get_due_reviews()
        while self.review_tab_layout.count():
            item = self.review_tab_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not reviews:
            empty = QLabel("✅  No words due for review right now!\nCheck back later.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {GREEN}; font-size: 15px;")
            self.review_tab_layout.addWidget(empty)
            return
        rw = ReviewWidget(reviews)
        rw.review_done.connect(self._on_review_done)
        self.review_tab_layout.addWidget(rw)

    def _on_review_done(self):
        self._check_reviews()
        self._load_history()

    # ── Settings ──────────────────────────────────────────────────────────────

    def _on_settings_saved(self, new_cfg: dict):
        flags = Qt.Window
        if new_cfg.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()
        hotkey = new_cfg.get("hotkey", "f9").upper()
        self.search_input.setPlaceholderText(
            f"Type a word or highlight text → {hotkey}…"
        )
        self.resize(new_cfg.get("window_width", 580), new_cfg.get("window_height", 600))
        self.hotkey_changed.emit(new_cfg.get("hotkey", "f9"))

    # ── Window helpers ────────────────────────────────────────────────────────

    def _center_on_screen(self):
        geo = QApplication.primaryScreen().geometry()
        self.move((geo.width() - self.width()) // 2, (geo.height() - self.height()) // 2)

    def show_window(self, tab: str = ""):
        """Open/raise the main window, optionally jumping to a tab."""
        tab_map = {"review": 1, "history": 2, "settings": self.settings_tab_index}
        if tab in tab_map:
            self.tabs.setCurrentIndex(tab_map[tab])
        self._center_on_screen()
        self.show()
        self.raise_()
        self.activateWindow()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    # Keep old name as alias so main.py keeps working
    def show_at_cursor(self):
        self.show_window()


# ─── Backward-compat alias ───────────────────────────────────────────────────
DictionaryPopup = MainWindow
