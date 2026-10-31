"""StatCard widget for displaying key benchmark metrics with modern visual styling."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class StatCard(QFrame):
    """Modern stat card with title, large numeric value, icon, and sub-badge."""

    def __init__(
        self,
        title: str,
        value: str = "0",
        badge: str = "",
        icon: str = "📊",
        highlight: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setProperty("class", "card-highlight" if highlight else "card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        # Header row: Icon & Title
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self.icon_label = QLabel(icon)
        self.icon_label.setStyleSheet("background-color: transparent; font-size: 18px;")
        header_row.addWidget(self.icon_label)

        self.title_label = QLabel(title.upper())
        self.title_label.setProperty("class", "label-muted")
        self.title_label.setStyleSheet(
            "background-color: transparent; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;"
        )
        header_row.addWidget(self.title_label)
        header_row.addStretch()

        layout.addLayout(header_row)

        # Main Value
        self.value_label = QLabel(value)
        self.value_label.setProperty("class", "stat-value")
        self.value_label.setStyleSheet(
            "background-color: transparent; font-size: 26px; font-weight: 800;"
        )
        layout.addWidget(self.value_label)

        # Subtitle / Badge
        self.badge_label = QLabel(badge)
        self.badge_label.setStyleSheet(
            "background-color: transparent; font-size: 11px; font-weight: 500; color: #818cf8;"
        )
        layout.addWidget(self.badge_label)

    def set_value(self, value: str, badge: str = "") -> None:
        """Update stat value and badge."""
        self.value_label.setText(value)
        if badge:
            self.badge_label.setText(badge)
