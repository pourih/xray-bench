"""Settings & Configuration view for tuning benchmark parameters."""
from __future__ import annotations

from pathlib import Path
from typing import Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.config import AppConfig, load_config


class SettingsView(QWidget):
    """Configuration editor for concurrency, timeouts, banned geos, and GitHub sync."""

    theme_changed = Signal(str)

    def __init__(self, config_path: str = "config.yaml", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.config_path = config_path
        self._init_ui()
        self.load_settings()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Title
        header_col = QVBoxLayout()
        header_col.setSpacing(4)
        title = QLabel("Engine Configuration")
        title.setProperty("class", "heading-1")
        header_col.addWidget(title)

        subtitle = QLabel("Tune concurrency, timeouts, banned country detection, and GitHub publishing")
        subtitle.setProperty("class", "label-muted")
        header_col.addWidget(subtitle)
        main_layout.addLayout(header_col)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(16)

        # ── Group 0: Appearance & Interface ──
        c0 = QFrame()
        c0.setProperty("class", "card")
        l0 = QVBoxLayout(c0)
        l0.setContentsMargins(18, 16, 18, 16)
        l0.setSpacing(12)

        t0 = QLabel("🎨 Appearance & Interface")
        t0.setProperty("class", "heading-2")
        l0.addWidget(t0)

        self.combo_theme = QComboBox()
        self.combo_theme.addItem("🌙  Dark Theme", "dark")
        self.combo_theme.addItem("☀️  Light Theme", "light")
        self.combo_theme.setFixedWidth(200)
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)
        l0.addLayout(self._create_setting_row("Interface Theme:", self.combo_theme))

        layout.addWidget(c0)

        # ── Group 1: Concurrency & Performance ──
        c1 = QFrame()
        c1.setProperty("class", "card")
        l1 = QVBoxLayout(c1)
        l1.setContentsMargins(18, 16, 18, 16)
        l1.setSpacing(12)

        t1 = QLabel("⚡ Concurrency & Xray Process Allocation")
        t1.setProperty("class", "heading-2")
        l1.addWidget(t1)

        self.spin_batch = QSpinBox()
        self.spin_batch.setRange(5, 100)
        self.spin_batch.setValue(40)
        self.spin_batch.setFixedWidth(120)
        l1.addLayout(self._create_setting_row("Xray Batch Size (nodes loaded per core instance):", self.spin_batch))

        self.spin_http_conc = QSpinBox()
        self.spin_http_conc.setRange(1, 40)
        self.spin_http_conc.setValue(12)
        self.spin_http_conc.setFixedWidth(120)
        l1.addLayout(self._create_setting_row("HTTP Test Rolling Concurrency (workers):", self.spin_http_conc))

        self.spin_speed_conc = QSpinBox()
        self.spin_speed_conc.setRange(1, 10)
        self.spin_speed_conc.setValue(4)
        self.spin_speed_conc.setFixedWidth(120)
        l1.addLayout(self._create_setting_row("Speed Test Concurrency (concurrent download streams):", self.spin_speed_conc))

        layout.addWidget(c1)

        # ── Group 2: Timeouts & Geo Defense ──
        c2 = QFrame()
        c2.setProperty("class", "card")
        l2 = QVBoxLayout(c2)
        l2.setContentsMargins(18, 16, 18, 16)
        l2.setSpacing(12)

        t2 = QLabel("🛡️ Geolocation & Stealth Defense")
        t2.setProperty("class", "heading-2")
        l2.addWidget(t2)

        self.input_blocked = QLineEdit()
        self.input_blocked.setPlaceholderText("IR, RU")
        self.input_blocked.setFixedWidth(200)
        l2.addLayout(self._create_setting_row("Blocked Countries (comma separated ISO codes):", self.input_blocked))

        self.chk_google = QCheckBox("Enable Deep Google Exit-IP Localization Check")
        l2.addLayout(self._create_setting_row("Google Geo Localization:", self.chk_google))

        self.spin_http_timeout = QSpinBox()
        self.spin_http_timeout.setRange(1, 30)
        self.spin_http_timeout.setValue(10)
        self.spin_http_timeout.setFixedWidth(120)
        l2.addLayout(self._create_setting_row("HTTP Ping Timeout (seconds):", self.spin_http_timeout))

        self.spin_speed_timeout = QSpinBox()
        self.spin_speed_timeout.setRange(1, 30)
        self.spin_speed_timeout.setValue(5)
        self.spin_speed_timeout.setFixedWidth(120)
        l2.addLayout(self._create_setting_row("Speed Measurement Duration (seconds):", self.spin_speed_timeout))

        layout.addWidget(c2)

        # ── Group 3: GitHub Publishing ──
        c3 = QFrame()
        c3.setProperty("class", "card")
        l3 = QVBoxLayout(c3)
        l3.setContentsMargins(18, 16, 18, 16)
        l3.setSpacing(12)

        t3 = QLabel("🌐 GitHub Automated Publishing")
        t3.setProperty("class", "heading-2")
        l3.addWidget(t3)

        self.input_repo = QLineEdit()
        self.input_repo.setPlaceholderText("pourih/xray-bench")
        self.input_repo.setFixedWidth(320)
        l3.addLayout(self._create_setting_row("GitHub Repository (owner/repo):", self.input_repo))

        self.input_token = QLineEdit()
        self.input_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_token.setPlaceholderText("ghp_...")
        self.input_token.setFixedWidth(320)
        l3.addLayout(self._create_setting_row("Personal Access Token (PAT):", self.input_token))

        layout.addWidget(c3)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # Footer
        footer = QHBoxLayout()
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #10b981; font-weight: 600;")
        footer.addWidget(self.lbl_status)
        footer.addStretch()

        btn_save = QPushButton("💾 Save Configuration")
        btn_save.setProperty("class", "btn-primary")
        btn_save.clicked.connect(self.save_settings)
        footer.addWidget(btn_save)
        main_layout.addLayout(footer)

    def _create_setting_row(self, label_text: str, widget: QWidget) -> QHBoxLayout:
        """Create a consistent form row with fixed-width label to align all inputs into a vertical column."""
        row = QHBoxLayout()
        row.setSpacing(16)
        lbl = QLabel(label_text)
        lbl.setFixedWidth(360)
        lbl.setStyleSheet("background-color: transparent;")
        row.addWidget(lbl)
        row.addWidget(widget)
        row.addStretch()
        return row

    def _on_theme_changed(self) -> None:
        """Switch application stylesheet dynamically when theme combobox changes."""
        theme = self.combo_theme.currentData()
        from src.gui.theme import get_stylesheet
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_stylesheet(theme))
        self.theme_changed.emit(theme)

    def load_settings(self) -> None:
        """Load from config.yaml and .env."""
        cfg = load_config(self.config_path)

        # Appearance
        theme_val = cfg.general.theme if hasattr(cfg.general, "theme") else "dark"
        idx = self.combo_theme.findData(theme_val)
        if idx >= 0:
            self.combo_theme.blockSignals(True)
            self.combo_theme.setCurrentIndex(idx)
            self.combo_theme.blockSignals(False)

        self.spin_batch.setValue(cfg.xray.batch_size)
        self.spin_http_conc.setValue(cfg.http_test.concurrency)
        self.spin_speed_conc.setValue(cfg.speed_test.concurrency)
        self.spin_http_timeout.setValue(int(cfg.http_test.timeout_sec))
        self.spin_speed_timeout.setValue(int(cfg.speed_test.timeout_sec))

        self.input_blocked.setText(", ".join(cfg.geo.blocked_google_countries or ["IR", "RU"]))
        self.chk_google.setChecked(cfg.geo.check_google_country)

        self.input_repo.setText(cfg.github.repo or "")
        self.input_token.setText(cfg.github.token or "")

    def save_settings(self) -> None:
        """Update YAML and .env."""
        import yaml

        # 1. Update config.yaml
        cfg_file = Path(self.config_path)
        data = {}
        if cfg_file.is_file():
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

        if "general" not in data:
            data["general"] = {}
        data["general"]["theme"] = self.combo_theme.currentData()

        if "xray" not in data:
            data["xray"] = {}
        data["xray"]["batch_size"] = self.spin_batch.value()

        if "http_test" not in data:
            data["http_test"] = {}
        data["http_test"]["concurrency"] = self.spin_http_conc.value()
        data["http_test"]["timeout_sec"] = float(self.spin_http_timeout.value())

        if "speed_test" not in data:
            data["speed_test"] = {}
        data["speed_test"]["concurrency"] = self.spin_speed_conc.value()
        data["speed_test"]["timeout_sec"] = float(self.spin_speed_timeout.value())

        if "geo" not in data:
            data["geo"] = {}
        raw_banned = [c.strip().upper() for c in self.input_blocked.text().split(",") if c.strip()]
        data["geo"]["blocked_google_countries"] = raw_banned
        data["geo"]["check_google_country"] = self.chk_google.isChecked()

        with open(cfg_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        # 2. Update .env
        env_p = Path(".env")
        token = self.input_token.text().strip()
        repo = self.input_repo.text().strip()
        lines = []
        if token:
            lines.append(f"GITHUB_TOKEN={token}")
        if repo:
            lines.append(f"GITHUB_REPO={repo}")
        lines.append("GITHUB_BRANCH=main\n")
        env_p.write_text("\n".join(lines), encoding="utf-8")

        self.lbl_status.setText("✔ Settings saved successfully!")
