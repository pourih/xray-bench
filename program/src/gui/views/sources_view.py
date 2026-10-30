"""Sources & Subscriptions management view."""
from __future__ import annotations

from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class SourcesView(QWidget):
    """Editor for subscription URLs, custom nodes, and blacklist."""

    def __init__(self, data_dir: str = "data", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.data_dir = Path(data_dir)
        self._init_ui()
        self.load_all_files()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        header_col = QVBoxLayout()
        header_col.setSpacing(4)
        title = QLabel("Sources & Subscriptions")
        title.setProperty("class", "heading-1")
        header_col.addWidget(title)

        subtitle = QLabel("Manage your subscription feeds, manual node lists, and blacklisted fingerprints")
        subtitle.setProperty("class", "label-muted")
        header_col.addWidget(subtitle)
        layout.addLayout(header_col)

        # Tab Widget
        self.tabs = QTabWidget()

        # Tab 1: Subscriptions
        tab_subs = QWidget()
        subs_layout = QVBoxLayout(tab_subs)
        subs_hint = QLabel("Enter subscription URLs (one per line). Supported: Base64 or plain URI lists.")
        subs_hint.setStyleSheet("color: #9ca3af; font-size: 12px;")
        subs_layout.addWidget(subs_hint)
        self.edit_subs = QPlainTextEdit()
        subs_layout.addWidget(self.edit_subs)
        self.tabs.addTab(tab_subs, "📡 Subscriptions (subscriptions.txt)")

        # Tab 2: Custom Nodes
        tab_custom = QWidget()
        custom_layout = QVBoxLayout(tab_custom)
        custom_hint = QLabel("Enter manual proxy URIs (one per line). Supports vmess://, vless://, trojan://, ss://, etc.")
        custom_hint.setStyleSheet("color: #9ca3af; font-size: 12px;")
        custom_layout.addWidget(custom_hint)
        self.edit_custom = QPlainTextEdit()
        custom_layout.addWidget(self.edit_custom)
        self.tabs.addTab(tab_custom, "📝 Custom Nodes (custom_nodes.txt)")

        # Tab 3: Blacklist
        tab_bl = QWidget()
        bl_layout = QVBoxLayout(tab_bl)
        bl_hint = QLabel("Blacklisted fingerprints, hashes, server IPs, or full URIs to discard before testing.")
        bl_hint.setStyleSheet("color: #9ca3af; font-size: 12px;")
        bl_layout.addWidget(bl_hint)
        self.edit_bl = QPlainTextEdit()
        bl_layout.addWidget(self.edit_bl)
        self.tabs.addTab(tab_bl, "🚫 Blacklist (blacklist.txt)")

        layout.addWidget(self.tabs)

        # Footer Actions
        footer_row = QHBoxLayout()
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #10b981; font-weight: 600;")
        footer_row.addWidget(self.lbl_status)
        footer_row.addStretch()

        btn_reload = QPushButton("Revert Changes")
        btn_reload.setProperty("class", "btn-secondary")
        btn_reload.clicked.connect(self.load_all_files)
        footer_row.addWidget(btn_reload)

        btn_save = QPushButton("💾 Save All Files")
        btn_save.setProperty("class", "btn-primary")
        btn_save.clicked.connect(self.save_all_files)
        footer_row.addWidget(btn_save)

        layout.addLayout(footer_row)

    def load_all_files(self) -> None:
        """Read content from data files into editors."""
        p_subs = self.data_dir / "subscriptions.txt"
        if p_subs.is_file():
            self.edit_subs.setPlainText(p_subs.read_text(encoding="utf-8", errors="ignore"))

        p_custom = self.data_dir / "custom_nodes.txt"
        if p_custom.is_file():
            self.edit_custom.setPlainText(p_custom.read_text(encoding="utf-8", errors="ignore"))

        p_bl = self.data_dir / "blacklist.txt"
        if p_bl.is_file():
            self.edit_bl.setPlainText(p_bl.read_text(encoding="utf-8", errors="ignore"))

        self.lbl_status.setText("Files loaded successfully.")

    def save_all_files(self) -> None:
        """Write editor text back to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

        (self.data_dir / "subscriptions.txt").write_text(self.edit_subs.toPlainText(), encoding="utf-8")
        (self.data_dir / "custom_nodes.txt").write_text(self.edit_custom.toPlainText(), encoding="utf-8")
        (self.data_dir / "blacklist.txt").write_text(self.edit_bl.toPlainText(), encoding="utf-8")

        self.lbl_status.setText("✔ All files saved successfully!")
