from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QFileDialog,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ui.gantt_widget import GanttWidget
from ui.parsing import Interval, parse_log
from ui.style import MAIN_STYLE, TEXT_MUTED, color_for_pid


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Scheduler Gantt")
        self.resize(1100, 650)

        self.default_log = Path(".") / "logs" / "log.txt"

        self._watch_timer: QTimer | None = None
        self._last_path: Path | None = None
        self._last_mtime_ns: int | None = None
        self._last_size: int | None = None

        self._build_ui()
        self._apply_style()
        self._init_watcher()
        self.reload()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title = QLabel("Scheduler Gantt")
        title.setObjectName("Title")
        subtitle = QLabel("Visualize process execution over time")
        subtitle.setObjectName("Subtitle")

        header = QVBoxLayout()
        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        toolbar.addWidget(QLabel("Log file:"))
        self.path_edit = QLineEdit(str(self.default_log))
        self.path_edit.setMinimumWidth(500)
        toolbar.addWidget(self.path_edit, stretch=1)

        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse)
        toolbar.addWidget(browse)

        reload_btn = QPushButton("Reload")
        reload_btn.clicked.connect(self.reload)
        toolbar.addWidget(reload_btn)

        toolbar.addSpacing(12)
        toolbar.addWidget(QLabel("Zoom:"))

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 60)
        self.zoom_slider.setValue(44)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        self.zoom_slider.setFixedWidth(160)
        toolbar.addWidget(self.zoom_slider)

        self.zoom_label = QLabel("44")
        self.zoom_label.setFixedWidth(24)
        toolbar.addWidget(self.zoom_label)

        layout.addLayout(toolbar)

        legend_row = QHBoxLayout()
        legend_row.setSpacing(8)

        legend_title = QLabel("Legend:")
        legend_title.setObjectName("LegendTitle")
        legend_row.addWidget(legend_title)

        self.legend_container = QWidget()
        self.legend_items_layout = QHBoxLayout(self.legend_container)
        self.legend_items_layout.setContentsMargins(0, 0, 0, 0)
        self.legend_items_layout.setSpacing(8)

        legend_scroll = QScrollArea()
        legend_scroll.setObjectName("LegendScroll")
        legend_scroll.setWidgetResizable(True)
        legend_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        legend_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        legend_scroll.setFrameShape(QFrame.Shape.NoFrame)
        legend_scroll.setWidget(self.legend_container)

        legend_row.addWidget(legend_scroll, stretch=1)
        layout.addLayout(legend_row)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 8, 8, 8)

        self.chart = GanttWidget()
        self.chart_area = QScrollArea()
        self.chart_area.setWidgetResizable(False)
        self.chart_area.setFrameShape(QFrame.Shape.NoFrame)
        self.chart_area.setWidget(self.chart)

        card_layout.addWidget(self.chart_area)
        layout.addWidget(card, stretch=1)

        self.setCentralWidget(root)

    def _apply_style(self) -> None:
        self.setStyleSheet(MAIN_STYLE)

    def clear_layout(self, layout: QHBoxLayout | QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def browse(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select log file", str(self.default_log), "Log files (*.txt);;All files (*.*)"
        )
        if file_path:
            self.path_edit.setText(file_path)
            self.reload()

    def on_zoom_changed(self, value: int) -> None:
        self.zoom_label.setText(str(value))
        self.chart.setUnitWidth(value)

    def _init_watcher(self) -> None:
        self._watch_timer = QTimer(self)
        self._watch_timer.setInterval(500)  # ms
        self._watch_timer.timeout.connect(self._check_log_updates)
        self._watch_timer.start()

    def _set_watch_baseline(self, path: Path) -> None:
        self._last_path = path
        if path.is_file():
            stat = path.stat()
            self._last_mtime_ns = stat.st_mtime_ns
            self._last_size = stat.st_size
        else:
            self._last_mtime_ns = None
            self._last_size = None

    def _parse_and_render(self, path: Path) -> None:
        intervals, cores, final_time = parse_log(path)
        self.chart.setData(intervals, cores, final_time)
        self.update_legend(intervals)
        self.statusBar().showMessage(
            f"Loaded {len(intervals)} intervals, {len(cores)} cores, time 0..{final_time}"
        )

    def _check_log_updates(self) -> None:
        try:
            path = Path(self.path_edit.text())
            if path != self._last_path:
                self._set_watch_baseline(path)
                if path.is_file():
                    self._parse_and_render(path)
                else:
                    self.statusBar().showMessage("Waiting for log file...")
                return

            if not path.is_file():
                if self._last_mtime_ns is not None or self._last_size is not None:
                    self._set_watch_baseline(path)
                    self.statusBar().showMessage("Waiting for log file...")
                return

            stat = path.stat()
            changed = (
                self._last_mtime_ns is None
                or self._last_size is None
                or stat.st_mtime_ns != self._last_mtime_ns
                or stat.st_size != self._last_size
            )
            if changed:
                self._last_mtime_ns = stat.st_mtime_ns
                self._last_size = stat.st_size
                self._parse_and_render(path)
        except Exception as ex:
            self.statusBar().showMessage(f"Error: {ex}")

    def reload(self) -> None:
        try:
            path = Path(self.path_edit.text())
            self._parse_and_render(path)
            self._set_watch_baseline(path)
        except Exception as ex:
            self.chart.setData([], [], 0)
            self.update_legend([])
            self.statusBar().showMessage(f"Error: {ex}")

    def update_legend(self, intervals: list[Interval]) -> None:
        self.clear_layout(self.legend_items_layout)

        pids = sorted({i.pid for i in intervals})
        if not pids:
            label = QLabel("(no data)")
            label.setStyleSheet(f"color: {TEXT_MUTED};")
            self.legend_items_layout.addWidget(label)
            self.legend_items_layout.addStretch(1)
            return

        for pid in pids:
            item = QWidget()
            item_layout = QHBoxLayout(item)
            item_layout.setContentsMargins(4, 2, 4, 2)
            item_layout.setSpacing(6)

            swatch = QFrame()
            swatch.setFixedSize(12, 12)
            swatch.setStyleSheet(f"background: {color_for_pid(pid)}; border-radius: 2px;")
            item_layout.addWidget(swatch)

            label = QLabel(f"P{pid}")
            item_layout.addWidget(label)

            self.legend_items_layout.addWidget(item)

        sep = QLabel(" | ")
        sep.setStyleSheet(f"color: {TEXT_MUTED};")
        self.legend_items_layout.addWidget(sep)

        end_title = QLabel("End:")
        end_title.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: 600;")
        self.legend_items_layout.addWidget(end_title)

        self._add_marker_item("■", "#f59e0b", "time")
        self._add_marker_item("●", "#22c55e", "finished")
        self._add_marker_item("▶", "#3b82f6", "syscall")

        self.legend_items_layout.addStretch(1)

    def _add_marker_item(self, symbol: str, color: str, text: str) -> None:
        item = QWidget()
        item_layout = QHBoxLayout(item)
        item_layout.setContentsMargins(4, 2, 4, 2)
        item_layout.setSpacing(6)

        icon = QLabel(symbol)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedWidth(12)
        icon.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 12px;")
        item_layout.addWidget(icon)

        label = QLabel(text)
        item_layout.addWidget(label)

        self.legend_items_layout.addWidget(item)