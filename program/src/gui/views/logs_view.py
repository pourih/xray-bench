"""Console & Logs view with colored log formatting and real-time streaming."""
from __future__ import annotations

import time
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LogsView(QWidget):
    """Terminal-like log console with syntax coloring and search."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # Title row
        title_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title = QLabel("System & Engine Logs")
        title.setProperty("class", "heading-1")
        header_col = title_col
        title_col.addWidget(title)

        subtitle = QLabel("Real-time diagnostic events, Xray core output, and pipeline status")
        subtitle.setProperty("class", "label-muted")
        title_col.addWidget(subtitle)
        title_row.addLayout(title_col)
        title_row.addStretch()

        # Autoscroll
        self.chk_autoscroll = QCheckBox("Autoscroll")
        self.chk_autoscroll.setChecked(True)
        title_row.addWidget(self.chk_autoscroll)

        btn_clear = QPushButton("Clear Console")
        btn_clear.setProperty("class", "btn-secondary")
        btn_clear.clicked.connect(self.clear_logs)
        title_row.addWidget(btn_clear)

        layout.addLayout(title_row)

        # Console Text Edit
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0d0e12;
                border: 1px solid #232530;
                border-radius: 10px;
                color: #e5e7eb;
                font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
                font-size: 12px;
                padding: 12px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(self.console)

    def append_log(self, level: str, message: str) -> None:
        """Append a colored log message."""
        ts = time.strftime("%H:%M:%S")
        color = "#38bdf8" if level == "INFO" else "#fbbf24" if level == "WARNING" else "#f87171"
        line = f"<span style='color:#6b7280;'>[{ts}]</span> <span style='color:{color}; font-weight:bold;'>[{level}]</span> <span style='color:#f3f4f6;'>{message}</span>"

        self.console.appendHtml(line)
        if self.chk_autoscroll.isChecked():
            self.console.moveCursor(QTextCursor.MoveOperation.End)

    def clear_logs(self) -> None:
        """Clear all lines."""
        self.console.clear()
