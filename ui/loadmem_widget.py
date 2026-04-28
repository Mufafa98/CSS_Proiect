from __future__ import annotations

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ui.style import BAR_BORDER, BORDER, CARD_BG, LABEL_BG, TEXT, TEXT_MUTED, color_for_pid


class LoadMemWidget(QWidget):
    LEFT_MARGIN = 110
    HEADER_HEIGHT = 22
    TOP_PADDING = 6
    BOTTOM_PADDING = 6
    STACK_MIN_HEIGHT = 80
    PIXELS_PER_UNIT = 1.0
    FOOTER_HEIGHT = 16
    FOOTER_MIN_UNIT = 16

    def __init__(self) -> None:
        super().__init__()
        self.memory_by_tick: list[list[tuple[int, int]]] = []
        self.final_time: int = 0
        self.memory_total: int = 0
        self.unit_width: int = 44
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def setData(
        self,
        memory_by_tick: list[list[tuple[int, int]]],
        final_time: int,
        memory_total: int,
    ) -> None:
        self.memory_by_tick = memory_by_tick
        self.final_time = max(final_time, 0)
        self.memory_total = max(memory_total, 0)
        self._update_size()

    def setUnitWidth(self, unit_width: int) -> None:
        self.unit_width = max(5, int(unit_width))
        self._update_size()

    def _stack_height(self) -> int:
        if self.memory_total <= 0:
            return self.STACK_MIN_HEIGHT
        return max(self.STACK_MIN_HEIGHT, int(self.memory_total * self.PIXELS_PER_UNIT))

    def _update_size(self) -> None:
        time_span = max(self.final_time, 1)
        width = self.LEFT_MARGIN + time_span * self.unit_width + 60
        height = (
            self.HEADER_HEIGHT
            + self.TOP_PADDING
            + self._stack_height()
            + self.BOTTOM_PADDING
            + self.FOOTER_HEIGHT
        )

        width = max(width, 400)
        height = max(height, 80)

        self.setMinimumSize(width, height)
        self.resize(width, height)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.fillRect(self.rect(), QColor(CARD_BG))

        if self.final_time <= 0 or self.memory_total <= 0:
            painter.setPen(QColor(TEXT_MUTED))
            painter.drawText(20, 30, "No memory data.")
            return

        unit = max(5, int(self.unit_width))
        left_margin = self.LEFT_MARGIN
        stack_height = self._stack_height()
        stack_top = self.HEADER_HEIGHT + self.TOP_PADDING
        footer_top = stack_top + stack_height + self.BOTTOM_PADDING

        # Left label area
        painter.fillRect(QRect(0, 0, left_margin, self.height()), QColor(LABEL_BG))
        painter.setPen(QPen(QColor(BORDER)))
        painter.drawLine(left_margin, 0, left_margin, self.height())

        painter.setPen(QColor(TEXT))
        painter.setFont(QFont(self.font().family(), 10, QFont.Weight.Bold))
        painter.drawText(
            QRect(12, 0, left_margin - 20, self.height()),
            Qt.AlignmentFlag.AlignVCenter,
            "Memory",
        )
        painter.setFont(QFont(self.font().family(), 8))
        painter.setPen(QColor(TEXT_MUTED))
        painter.drawText(12, footer_top + self.FOOTER_HEIGHT - 3, "Free")

        scale = stack_height / self.memory_total if self.memory_total > 0 else 1.0

        # Per-tick memory stacks
        for t in range(self.final_time):
            x = left_margin + t * unit
            if unit <= 4:
                continue

            container_rect = QRect(x + 2, stack_top, unit - 4, stack_height)
            painter.setPen(QPen(QColor(BORDER)))
            painter.setBrush(QColor(0, 0, 0, 0))
            painter.drawRoundedRect(container_rect, 3, 3)

            segments = self.memory_by_tick[t] if t < len(self.memory_by_tick) else []
            draw_segments = list(reversed(segments))  # newest processes on top

            # Precompute used height for free-space-on-top layout
            heights: list[tuple[int, int]] = []
            used_height = 0
            used_amount = 0
            for pid, amount in draw_segments:
                seg_h = max(1, int(amount * scale))
                heights.append((pid, seg_h))
                used_height += seg_h
                used_amount += amount

            free_height = max(stack_height - used_height, 0)

            # Free space at TOP
            if free_height > 0:
                free_rect = QRect(x + 4, stack_top, unit - 8, free_height)
                painter.setPen(QPen(QColor(BORDER)))
                painter.setBrush(QColor("#e5e7eb"))
                painter.drawRoundedRect(free_rect, 3, 3)

            # Used memory BELOW free space
            y = stack_top + free_height
            for pid, seg_h in heights:
                remaining_height = stack_top + stack_height - y
                if remaining_height <= 0:
                    break

                if seg_h > remaining_height:
                    seg_h = remaining_height

                rect = QRect(x + 4, y, unit - 8, seg_h)
                painter.setPen(QPen(QColor(BAR_BORDER)))
                painter.setBrush(QColor(color_for_pid(pid)))
                painter.drawRoundedRect(rect, 3, 3)

                if rect.height() >= 12 and rect.width() >= 18:
                    painter.setPen(QColor("white"))
                    painter.setFont(QFont(self.font().family(), 8, QFont.Weight.Bold))
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"P{pid}")

                y += seg_h

            # Free memory value under each cell
            if unit >= self.FOOTER_MIN_UNIT:
                free_mem = max(self.memory_total - used_amount, 0)
                footer_rect = QRect(x + 2, footer_top, unit - 4, self.FOOTER_HEIGHT)
                painter.setPen(QColor(TEXT_MUTED))
                painter.setFont(QFont(self.font().family(), 8))
                painter.drawText(footer_rect, Qt.AlignmentFlag.AlignCenter, str(free_mem))