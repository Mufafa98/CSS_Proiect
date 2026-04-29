from __future__ import annotations

from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygon
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ui.parsing import Interval
from ui.style import (
    BAR_BORDER,
    BORDER,
    CARD_BG,
    GRID_MAJOR,
    GRID_MINOR,
    HEADER_BG,
    LABEL_BG,
    ROW_ALT,
    TEXT,
    TEXT_MUTED,
    color_for_pid,
)


class GanttWidget(QWidget):
    LEFT_MARGIN = 110
    TOP_MARGIN = 64
    ROW_HEIGHT = 46
    FOOTER = 30

    hoverTickChanged = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        self.intervals: list[Interval] = []
        self.cores: list[int] = []
        self.final_time: int = 0
        self.unit_width: int = 44
        self._hover_tick: int = -1
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def setData(self, intervals: list[Interval], cores: list[int], final_time: int) -> None:
        self.intervals = intervals
        self.cores = cores
        self.final_time = max(final_time, 0)
        if self._hover_tick >= self.final_time:
            self._hover_tick = -1
        self._update_size()

    def setUnitWidth(self, unit_width: int) -> None:
        self.unit_width = max(5, int(unit_width))
        self._update_size()

    def setHoverTick(self, tick: int, emit: bool = False) -> None:
        if tick < 0 or tick >= self.final_time:
            tick = -1
        if tick == self._hover_tick:
            return
        self._hover_tick = tick
        if emit:
            self.hoverTickChanged.emit(tick)
        self.update()

    def _tick_from_pos(self, x: float) -> int:
        if self.final_time <= 0:
            return -1
        unit = max(5, int(self.unit_width))
        if x < self.LEFT_MARGIN:
            return -1
        tick = int((x - self.LEFT_MARGIN) // unit)
        if 0 <= tick < self.final_time:
            return tick
        return -1

    def mouseMoveEvent(self, event) -> None:
        tick = self._tick_from_pos(event.position().x())
        self.setHoverTick(tick, emit=True)

    def leaveEvent(self, event) -> None:
        self.setHoverTick(-1, emit=True)

    def _update_size(self) -> None:
        left_margin = self.LEFT_MARGIN
        top_margin = self.TOP_MARGIN
        row_height = self.ROW_HEIGHT
        footer = self.FOOTER

        time_span = max(self.final_time, 1)
        width = left_margin + time_span * self.unit_width + 60
        height = top_margin + max(len(self.cores), 1) * row_height + footer

        width = max(width, 400)
        height = max(height, 220)

        self.setMinimumSize(width, height)
        self.resize(width, height)
        self.update()

    def _end_marker_space(self, rect: QRect) -> int:
        if rect.width() < 16:
            return 0
        size = min(12, rect.height() - 6)
        if size < 6:
            return 0
        return size + 8  # marker + padding

    def _draw_end_marker(self, painter: QPainter, rect: QRect, reason: str | None) -> None:
        if rect.width() < 16:
            return

        size = min(12, rect.height() - 6)
        if size < 6:
            return

        x = rect.right() - size - 4
        y = rect.center().y() - size // 2
        reason_key = (reason or "unknown").lower()

        if reason_key.startswith("finished"):
            color = QColor("#22c55e")  # green
            painter.setPen(QPen(QColor("white")))
            painter.setBrush(color)
            painter.drawEllipse(QRect(x, y, size, size))
        elif reason_key.startswith("time"):
            color = QColor("#f59e0b")  # amber
            painter.setPen(QPen(QColor("white")))
            painter.setBrush(color)
            painter.drawRect(QRect(x, y, size, size))
        elif reason_key.startswith("syscall"):
            color = QColor("#3b82f6")  # blue
            painter.setPen(QPen(QColor("white")))
            painter.setBrush(color)
            points = QPolygon(
                [
                    QPoint(x, y),
                    QPoint(x, y + size),
                    QPoint(x + size, y + size // 2),
                ]
            )
            painter.drawPolygon(points)
        else:
            color = QColor("#9ca3af")  # gray
            painter.setPen(QPen(QColor("white")))
            painter.setBrush(color)
            points = QPolygon(
                [
                    QPoint(x + size // 2, y),
                    QPoint(x + size, y + size // 2),
                    QPoint(x + size // 2, y + size),
                    QPoint(x, y + size // 2),
                ]
            )
            painter.drawPolygon(points)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        painter.fillRect(self.rect(), QColor(CARD_BG))

        if not self.cores or not self.intervals:
            painter.setPen(QColor(TEXT_MUTED))
            painter.drawText(20, 30, "No intervals to display.")
            return

        unit = max(5, int(self.unit_width))
        left_margin = self.LEFT_MARGIN
        top_margin = self.TOP_MARGIN
        row_height = self.ROW_HEIGHT
        footer = self.FOOTER

        total_width = left_margin + self.final_time * unit + 60
        total_height = top_margin + len(self.cores) * row_height + footer

        header_top = 16
        header_bottom = top_margin - 8
        grid_top = top_margin
        grid_bottom = total_height - footer

        # Header band
        painter.fillRect(
            QRect(left_margin, header_top, total_width - 20 - left_margin, header_bottom - header_top),
            QColor(HEADER_BG),
        )
        painter.setPen(QPen(QColor(BORDER)))
        painter.drawLine(left_margin, header_bottom, total_width - 20, header_bottom)

        # Label column background and separator
        painter.fillRect(
            QRect(0, grid_top, left_margin, grid_bottom - grid_top),
            QColor(LABEL_BG),
        )
        painter.drawLine(left_margin, grid_top, left_margin, grid_bottom)

        # Alternating rows
        for idx in range(len(self.cores)):
            y = top_margin + idx * row_height
            if idx % 2 == 0:
                painter.fillRect(
                    QRect(left_margin, y, total_width - 20 - left_margin, row_height),
                    QColor(ROW_ALT),
                )

        # Time grid
        if self.final_time <= 20:
            major_step = 1
        elif self.final_time <= 60:
            major_step = 5
        else:
            major_step = 10

        for t in range(0, self.final_time + 1):
            x = left_margin + t * unit
            if t % major_step == 0:
                painter.setPen(QPen(QColor(GRID_MAJOR)))
                painter.drawLine(x, grid_top, x, grid_bottom)

                painter.setPen(QColor(TEXT_MUTED))
                painter.drawText(
                    QRect(x - 24, header_top, 48, header_bottom - header_top),
                    Qt.AlignmentFlag.AlignCenter,
                    str(t),
                )
            else:
                painter.setPen(QPen(QColor(GRID_MINOR)))
                painter.drawLine(x, grid_top, x, grid_bottom)

        # Time label
        painter.setPen(QColor(TEXT_MUTED))
        painter.setFont(QFont(self.font().family(), 9, QFont.Weight.Bold))
        painter.drawText(
            QRect(left_margin, 4, total_width - left_margin, 16),
            Qt.AlignmentFlag.AlignLeft,
            "Time",
        )

        # Core labels and row lines
        painter.setFont(QFont(self.font().family(), 10, QFont.Weight.Bold))
        for idx, core in enumerate(self.cores):
            y = top_margin + idx * row_height
            painter.setPen(QColor(TEXT))
            painter.drawText(
                QRect(12, y, left_margin - 20, row_height),
                Qt.AlignmentFlag.AlignVCenter,
                f"Core {core}",
            )

            painter.setPen(QPen(QColor(BORDER)))
            painter.drawLine(left_margin, y, total_width - 20, y)

        painter.drawLine(
            left_margin,
            top_margin + len(self.cores) * row_height,
            total_width - 20,
            top_margin + len(self.cores) * row_height,
        )

        # Bars
        core_index = {core: idx for idx, core in enumerate(self.cores)}
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setFont(QFont(self.font().family(), 9, QFont.Weight.Bold))

        for it in self.intervals:
            idx = core_index.get(it.core, 0)
            y1 = top_margin + idx * row_height + 8
            y2 = y1 + row_height - 16

            x1 = left_margin + it.start * unit
            x2 = left_margin + it.end * unit
            if x2 - x1 < 6:
                x2 = x1 + 6

            rect = QRect(x1, y1, x2 - x1, y2 - y1)
            shadow_rect = QRect(rect.x() + 1, rect.y() + 1, rect.width(), rect.height())

            painter.setPen(QPen(QColor(0, 0, 0, 0)))
            painter.setBrush(QColor(0, 0, 0, 28))
            painter.drawRoundedRect(shadow_rect, 6, 6)

            painter.setPen(QPen(QColor(BAR_BORDER)))
            painter.setBrush(QColor(color_for_pid(it.pid)))
            painter.drawRoundedRect(rect, 6, 6)

            self._draw_end_marker(painter, rect, it.end_reason)

            marker_space = self._end_marker_space(rect)
            text_rect = rect.adjusted(6, 0, -marker_space, 0)
            if text_rect.width() >= 18:
                painter.setPen(QColor("white"))
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, f"P{it.pid}")

        # Hover column overlay
        if self._hover_tick >= 0:
            x = left_margin + self._hover_tick * unit
            hover_rect = QRect(x, grid_top, unit, grid_bottom - grid_top)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 20))
            painter.drawRect(hover_rect)