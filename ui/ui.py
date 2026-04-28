from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.main_window import MainWindow


def ui(on_started: Callable[[], None] | None = None) -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    if on_started:
        QTimer.singleShot(0, on_started)
    sys.exit(app.exec())