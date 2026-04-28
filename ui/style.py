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
QFrame#Card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; }
QLineEdit { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; background: #ffffff; color: #111827; }
QPushButton { padding: 6px 12px; border: 1px solid #d1d5db; border-radius: 6px; background: #ffffff; color: #111827; }
QPushButton:hover { background: #f3f4f6; }
QScrollArea { background: #ffffff; border: none; }
QScrollArea#LegendScroll { background: #f5f7fb; border: none; }
QScrollArea#LegendScroll > QWidget { background: #f5f7fb; }
QScrollArea#LegendScroll > QWidget > QWidget { background: #f5f7fb; }
"""