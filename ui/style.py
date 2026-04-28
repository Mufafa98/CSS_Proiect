from __future__ import annotations

PALETTE = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
    "#edc949", "#af7aa1", "#ff9da7", "#9c755f", "#bab0ab"
]


def color_for_pid(pid: int) -> str:
    return PALETTE[pid % len(PALETTE)]


BG = "#f5f7fb"
CARD_BG = "#ffffff"
GRID_MINOR = "#eef1f6"
GRID_MAJOR = "#d7dde7"
ROW_ALT = "#f8fafc"
LABEL_BG = "#f1f5f9"
TEXT = "#111827"
TEXT_MUTED = "#4b5563"
BORDER = "#e5e7eb"
HEADER_BG = "#f3f4f6"
BAR_BORDER = "#0f172a"

MAIN_STYLE = """
QMainWindow { background: #f5f7fb; }
QWidget { color: #111827; }
QStatusBar { color: #4b5563; background: transparent; }
QLabel#Title { font-size: 20px; font-weight: 700; color: #111827; }
QLabel#Subtitle { color: #4b5563; }
QLabel#LegendTitle { color: #4b5563; font-weight: 600; }
QLabel#SectionTitle { color: #111827; font-weight: 600; font-size: 14px; }
QFrame#Card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; }
QFrame#ProcessCard { background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px; }
QLineEdit { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; background: #ffffff; color: #111827; }
QPushButton { padding: 6px 12px; border: 1px solid #d1d5db; border-radius: 6px; background: #ffffff; color: #111827; }
QPushButton:hover { background: #f3f4f6; }
QScrollArea { background: #ffffff; border: none; }
QScrollArea#LegendScroll { background: #f5f7fb; border: none; }
QScrollArea#LegendScroll > QWidget { background: #f5f7fb; }
QScrollArea#LegendScroll > QWidget > QWidget { background: #f5f7fb; }
QScrollArea#ProcessScroll { background: #f5f7fb; border: none; }
QScrollArea#ProcessScroll > QWidget { background: #f5f7fb; }
QScrollArea#ProcessScroll > QWidget > QWidget { background: #f5f7fb; }
QWidget#ProcessCardsContainer { background: #f5f7fb; }
QProgressBar { background: #f5f7fb; border: none; }

/* Scrollbars */
QAbstractScrollArea::corner { background: #f5f7fb; }
QScrollBar:vertical {
    background: #f5f7fb;
    width: 12px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 6px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #94a3b8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    background: transparent;
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QScrollBar:horizontal {
    background: #f5f7fb;
    height: 12px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #cbd5e1;
    border-radius: 6px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover { background: #94a3b8; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    background: transparent;
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
"""