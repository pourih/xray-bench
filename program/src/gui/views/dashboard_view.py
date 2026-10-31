"""Main Dashboard view for initiating benchmarks and monitoring live progress."""
from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.components.stat_card import StatCard


class DashboardView(QWidget):
    """Modern dashboard view with control deck, live indicators, stat cards, and activity stream."""

    start_http_requested = Signal(str, int, bool)  # source_type, limit, auto_push
    start_speed_requested = Signal(str, int, bool)  # source_type, limit, auto_push
    stop_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # ── Top Title Row ──
        title_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        header = QLabel("Benchmark Dashboard")
        header.setProperty("class", "heading-1")
        title_col.addWidget(header)

        sub = QLabel("Real-time proxy connectivity, Google localization & speed tournament engine")
        sub.setProperty("class", "label-muted")
        title_col.addWidget(sub)

        title_row.addLayout(title_col)
        title_row.addStretch()

        layout.addLayout(title_row)

        # ── Stat Cards Row ──
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(14)

        self.card_total = StatCard(title="Total Nodes", value="--", badge="In Database", icon="📦")
        self.card_passed = StatCard(title="Passed HTTP", value="--", badge="Verified alive", icon="⚡", highlight=True)
        self.card_speed = StatCard(title="Top Speed", value="--", badge="Mbps bandwidth", icon="🚀")
        self.card_dead = StatCard(title="Pruned Dead", value="--", badge="3-Strike policy", icon="🛡️")

        stats_layout.addWidget(self.card_total)
        stats_layout.addWidget(self.card_passed)
        stats_layout.addWidget(self.card_speed)
        stats_layout.addWidget(self.card_dead)

        layout.addLayout(stats_layout)

        # ── Control Deck & Hero Action Card ──
        deck_card = QFrame()
        deck_card.setProperty("class", "card")
        deck_layout = QVBoxLayout(deck_card)
        deck_layout.setContentsMargins(20, 18, 20, 18)
        deck_layout.setSpacing(14)

        deck_title_row = QHBoxLayout()
        deck_title = QLabel("Execution Controls")
        deck_title.setProperty("class", "heading-2")
        deck_title_row.addWidget(deck_title)

        # Live status pill
        self.status_pill = QLabel("IDLE")
        self.status_pill.setObjectName("statusPill")
        deck_title_row.addWidget(self.status_pill)
        deck_title_row.addStretch()
        deck_layout.addLayout(deck_title_row)

        # 1. Parameters Row
        params_row = QHBoxLayout()
        params_row.setSpacing(14)

        # Source selector
        lbl_source = QLabel("Source:")
        lbl_source.setProperty("class", "label-muted")
        params_row.addWidget(lbl_source)

        self.combo_source = QComboBox()
        self.combo_source.addItem("Subscriptions URL (subscriptions.txt)", "subs")
        self.combo_source.addItem("HTTP Output (results/nodes_http.txt)", "http-output")
        self.combo_source.addItem("Active Database Nodes", "db")
        self.combo_source.addItem("Custom File (custom_nodes.txt)", "file")
        params_row.addWidget(self.combo_source)

        # Limit input
        lbl_limit = QLabel("Limit:")
        lbl_limit.setProperty("class", "label-muted")
        params_row.addWidget(lbl_limit)

        self.input_limit = QLineEdit()
        self.input_limit.setPlaceholderText("All (e.g. 50)")
        self.input_limit.setFixedWidth(95)
        params_row.addWidget(self.input_limit)

        # Push to GitHub toggle
        self.chk_push = QCheckBox("Auto-push results to GitHub")
        params_row.addWidget(self.chk_push)

        params_row.addStretch()
        deck_layout.addLayout(params_row)

        # 2. Action Triggers Row (separate row prevents horizontal clipping on unmaximized windows)
        actions_row = QHBoxLayout()
        actions_row.setSpacing(12)

        self.btn_run_http = QPushButton("⚡ Run HTTP Test")
        self.btn_run_http.setProperty("class", "btn-primary")
        self.btn_run_http.clicked.connect(self._on_start_http)
        actions_row.addWidget(self.btn_run_http)

        self.btn_run_speed = QPushButton("🏆 Run Speed Tournament")
        self.btn_run_speed.setProperty("class", "btn-secondary")
        self.btn_run_speed.clicked.connect(self._on_start_speed)
        actions_row.addWidget(self.btn_run_speed)

        self.btn_stop = QPushButton("■ Stop")
        self.btn_stop.setProperty("class", "btn-danger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setCursor(Qt.CursorShape.ArrowCursor)
        self.btn_stop.clicked.connect(self._on_stop)
        actions_row.addWidget(self.btn_stop)

        actions_row.addStretch()
        deck_layout.addLayout(actions_row)

        # In-Flight Testing Badge
        self.active_test_banner = QFrame()
        self.active_test_banner.setObjectName("activeBanner")
        banner_layout = QHBoxLayout(self.active_test_banner)
        banner_layout.setContentsMargins(6, 4, 6, 4)

        self.lbl_active_info = QLabel("Ready. Select a mode above to begin benchmarking.")
        self.lbl_active_info.setProperty("class", "label-muted")
        banner_layout.addWidget(self.lbl_active_info)

        deck_layout.addWidget(self.active_test_banner)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        deck_layout.addWidget(self.progress_bar)

        layout.addWidget(deck_card)

        # ── Live Activity Stream Table ──
        stream_card = QFrame()
        stream_card.setProperty("class", "card")
        stream_layout = QVBoxLayout(stream_card)
        stream_layout.setContentsMargins(18, 16, 18, 16)
        stream_layout.setSpacing(10)

        stream_header = QHBoxLayout()
        stream_title = QLabel("Live Activity Stream")
        stream_title.setProperty("class", "heading-2")
        stream_header.addWidget(stream_title)

        self.lbl_stream_counter = QLabel("0 events")
        self.lbl_stream_counter.setObjectName("streamCounter")
        stream_header.addWidget(self.lbl_stream_counter)
        stream_header.addStretch()

        btn_clear = QPushButton("Clear Stream")
        btn_clear.setProperty("class", "btn-secondary")
        btn_clear.setFixedHeight(26)
        btn_clear.clicked.connect(self.clear_stream)
        stream_header.addWidget(btn_clear)

        stream_layout.addLayout(stream_header)

        self.stream_table = QTableWidget()
        self.stream_table.setColumnCount(5)
        self.stream_table.setHorizontalHeaderLabels(["Status", "Target / Tag", "Endpoint", "Result / Details", "Time"])
        header = self.stream_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 85)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(1, 140)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 90)
        header.setStretchLastSection(False)

        for col_idx in range(5):
            h_item = self.stream_table.horizontalHeaderItem(col_idx)
            if h_item:
                if col_idx in (0, 4):
                    h_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    h_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.stream_table.verticalHeader().setVisible(False)
        self.stream_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.stream_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        stream_layout.addWidget(self.stream_table)
        layout.addWidget(stream_card)

    def _on_start_http(self) -> None:
        source = self.combo_source.currentData()
        limit = int(self.input_limit.text().strip()) if self.input_limit.text().strip().isdigit() else 0
        push = self.chk_push.isChecked()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.set_running_state(True, "HTTP TEST IN PROGRESS")
        self.lbl_active_info.setText("⏳ Initializing Xray core & fetching candidate nodes...")
        self.start_http_requested.emit(source, limit, push)

    def _on_start_speed(self) -> None:
        source = self.combo_source.currentData()
        limit = int(self.input_limit.text().strip()) if self.input_limit.text().strip().isdigit() else 0
        push = self.chk_push.isChecked()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.set_running_state(True, "SPEED TOURNAMENT IN PROGRESS")
        self.lbl_active_info.setText("⏳ Preparing candidate nodes for Speed Tournament...")
        self.start_speed_requested.emit(source, limit, push)

    def _on_stop(self) -> None:
        self.stop_requested.emit()
        self.set_running_state(False, "STOPPING...")

    def set_running_state(self, is_running: bool, status_text: str = "IDLE") -> None:
        """Toggle button states and status pill."""
        self.btn_run_http.setEnabled(not is_running)
        self.btn_run_speed.setEnabled(not is_running)
        self.btn_stop.setEnabled(is_running)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor if is_running else Qt.CursorShape.ArrowCursor)
        self.combo_source.setEnabled(not is_running)
        self.input_limit.setEnabled(not is_running)

        if is_running:
            self.progress_bar.setVisible(True)
            self.status_pill.setText(status_text)
            self.status_pill.setProperty("running", "true")
        else:
            if self.progress_bar.value() == 0 or status_text == "IDLE":
                self.progress_bar.setVisible(False)
            self.status_pill.setText("IDLE")
            self.status_pill.setProperty("running", "false")
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)

    def update_active_node(self, current: int, total: int, tag: str, addr: str, port: int, proto: str, mode: str) -> None:
        """Update live testing pill."""
        pct = int((current / max(1, total)) * 100)
        self.progress_bar.setValue(pct)
        mode_label = "HTTP Ping" if mode == "http" else "Speed Test"
        self.lbl_active_info.setText(
            f"⏳ Testing [{current}/{total}] ({pct}%):  <b style='color:#ffffff;'>{tag}</b>  ({addr}:{port}) [{proto.upper()}] - {mode_label}"
        )

    def add_stream_entry(self, status: str, tag: str, endpoint: str, details: str) -> None:
        """Append an event line to the activity table."""
        import time
        row = self.stream_table.rowCount()
        self.stream_table.insertRow(row)

        status_item = QTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if "✓" in status or "PASS" in status.upper():
            status_item.setForeground(Qt.GlobalColor.green)
        elif "✗" in status or "FAIL" in status.upper() or "DROP" in status.upper():
            status_item.setForeground(Qt.GlobalColor.red)
        elif "ELIM" in status.upper():
            status_item.setForeground(Qt.GlobalColor.yellow)

        tag_item = QTableWidgetItem(tag)
        tag_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        endpoint_item = QTableWidgetItem(endpoint)
        endpoint_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        details_item = QTableWidgetItem(details)
        details_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        time_item = QTableWidgetItem(time.strftime("%H:%M:%S"))
        time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.stream_table.setItem(row, 0, status_item)
        self.stream_table.setItem(row, 1, tag_item)
        self.stream_table.setItem(row, 2, endpoint_item)
        self.stream_table.setItem(row, 3, details_item)
        self.stream_table.setItem(row, 4, time_item)

        # Scroll to bottom
        self.stream_table.scrollToBottom()
        self.lbl_stream_counter.setText(f"{row + 1} events")

    def clear_stream(self) -> None:
        """Reset live stream table."""
        self.stream_table.setRowCount(0)
        self.lbl_stream_counter.setText("0 events")
