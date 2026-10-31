"""Main application window with sidebar navigation and reactive view switching."""
from __future__ import annotations

from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.database import Database
from src.gui.views.dashboard_view import DashboardView
from src.gui.views.logs_view import LogsView
from src.gui.views.nodes_view import NodesView
from src.gui.views.settings_view import SettingsView
from src.gui.views.sources_view import SourcesView
from src.gui.worker import BenchmarkWorker


class MainWindow(QMainWindow):
    """Modern dashboard main window with persistent sidebar and stacked views."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("xBench")
        self.resize(1180, 760)
        self.setMinimumSize(960, 620)

        # Set Window Icon
        icon_path = self._resolve_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(str(icon_path)))

        self.current_theme = "dark"
        self.worker: Optional[BenchmarkWorker] = None
        self._init_ui()
        self._refresh_db_stats()

    def _resolve_icon_path(self) -> Optional[Path]:
        """Locate app icon asset file."""
        base = Path(__file__).resolve().parent.parent.parent
        candidates = [
            base.parent / "assets" / "icon.png",
            base / "assets" / "icon.png",
            Path("assets/icon.png").resolve(),
        ]
        return next((p for p in candidates if p.is_file()), None)

    def _init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 1. Left Sidebar ──
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 16)
        sidebar_layout.setSpacing(4)

        # Brand Title
        title_label = QLabel("xBench")
        title_label.setObjectName("sidebarTitle")
        sidebar_layout.addWidget(title_label)

        # Navigation Buttons Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_nav_dashboard = self._create_nav_btn("⚡  Dashboard", 0, checked=True)
        self.btn_nav_nodes = self._create_nav_btn("📋  Node Explorer", 1)
        self.btn_nav_sources = self._create_nav_btn("🌐  Subscriptions", 2)
        self.btn_nav_settings = self._create_nav_btn("⚙️  Settings", 3)
        self.btn_nav_logs = self._create_nav_btn("📜  Console Logs", 4)

        sidebar_layout.addWidget(self.btn_nav_dashboard)
        sidebar_layout.addWidget(self.btn_nav_nodes)
        sidebar_layout.addWidget(self.btn_nav_sources)
        sidebar_layout.addWidget(self.btn_nav_settings)
        sidebar_layout.addWidget(self.btn_nav_logs)

        sidebar_layout.addStretch()

        # Sidebar footer info
        self.lbl_sidebar_nodes = QLabel("Nodes in DB: --")
        self.lbl_sidebar_nodes.setStyleSheet("color: #6b7280; font-size: 11px; padding: 0 16px;")
        sidebar_layout.addWidget(self.lbl_sidebar_nodes)

        main_layout.addWidget(sidebar)

        # ── 2. Right Content Area (Stacked Views) ──
        self.stacked_widget = QStackedWidget()

        self.view_dashboard = DashboardView()
        self.view_nodes = NodesView()
        self.view_sources = SourcesView()
        self.view_settings = SettingsView()
        self.view_logs = LogsView()

        self.stacked_widget.addWidget(self.view_dashboard)
        self.stacked_widget.addWidget(self.view_nodes)
        self.stacked_widget.addWidget(self.view_sources)
        self.stacked_widget.addWidget(self.view_settings)
        self.stacked_widget.addWidget(self.view_logs)

        main_layout.addWidget(self.stacked_widget)

        # Connect Dashboard actions
        self.view_dashboard.start_http_requested.connect(self._start_http_benchmark)
        self.view_dashboard.start_speed_requested.connect(self._start_speed_benchmark)
        self.view_dashboard.stop_requested.connect(self._stop_benchmark)

        # Connect Settings actions
        self.view_settings.theme_changed.connect(self._on_theme_changed)

    def _create_nav_btn(self, text: str, page_index: int, checked: bool = False) -> QPushButton:
        """Helper to create unified navigation buttons."""
        btn = QPushButton(text)
        btn.setProperty("class", "nav-btn")
        btn.setCheckable(True)
        btn.setChecked(checked)
        self.nav_group.addButton(btn)
        btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(page_index))
        return btn

    def _on_theme_changed(self, theme: str) -> None:
        """Handle theme change from settings."""
        self.current_theme = theme

    def _refresh_db_stats(self) -> None:
        """Query database for quick summary stats."""
        try:
            db = Database("data/nodes_cache.db")
            active = db.get_active_nodes()
            dead_count = 0
            with db._get_connection() as conn:
                cur = conn.execute("SELECT COUNT(*) FROM nodes WHERE is_dead = 1;")
                row = cur.fetchone()
                if row:
                    dead_count = row[0]
            db.close()

            total_count = len(active)
            passed_http = len([r for r in active if r.http_latency_ms is not None])
            speeds = [r.last_speed_mbps for r in active if r.last_speed_mbps and r.last_speed_mbps > 0]
            max_speed = max(speeds) if speeds else 0.0

            self.view_dashboard.card_total.set_value(f"{total_count:,}", f"Active in SQLite")
            self.view_dashboard.card_passed.set_value(f"{passed_http:,}", f"Passed ping")
            self.view_dashboard.card_speed.set_value(f"{max_speed:.2f}", f"Mbps peak")
            self.view_dashboard.card_dead.set_value(f"{dead_count:,}", f"3-Strike policy")
            self.lbl_sidebar_nodes.setText(f"Active Nodes: {total_count:,}")
        except Exception:
            pass

    def _start_http_benchmark(self, source_type: str, limit: int, auto_push: bool) -> None:
        """Launch HTTP benchmark worker."""
        self._launch_worker(mode="http", source_type=source_type, limit=limit, auto_push=auto_push)

    def _start_speed_benchmark(self, source_type: str, limit: int, auto_push: bool) -> None:
        """Launch Speed tournament worker."""
        self._launch_worker(mode="speed", source_type=source_type, limit=limit, auto_push=auto_push)

    def _launch_worker(self, mode: str, source_type: str, limit: int, auto_push: bool) -> None:
        """Initialize worker thread and wire signals to GUI."""
        self.worker = BenchmarkWorker(
            mode=mode,
            source_type=source_type,
            limit=limit,
            auto_push=auto_push,
        )

        # Wire worker signals to dashboard and logs
        self.worker.test_started.connect(self._on_test_started)
        self.worker.node_testing_started.connect(self._on_node_testing_started)
        self.worker.batch_started.connect(self._on_batch_started)
        self.worker.batch_progress.connect(self._on_batch_progress)
        self.worker.batch_completed.connect(self._on_batch_completed)
        self.worker.round_started.connect(self._on_round_started)
        self.worker.round_progress.connect(self._on_round_progress)
        self.worker.round_completed.connect(self._on_round_completed)
        self.worker.node_eliminated.connect(self._on_node_eliminated)
        self.worker.log_emitted.connect(self._on_log_emitted)
        self.worker.test_completed.connect(self._on_test_completed)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.error_occurred.connect(self._on_worker_error)

        self.view_logs.append_log("INFO", f"Starting {mode.upper()} benchmark (source: {source_type}, limit: {limit or 'ALL'})...")
        self.worker.start()

    def _stop_benchmark(self) -> None:
        """Stop current running benchmark."""
        if self.worker and self.worker.isRunning():
            self.view_logs.append_log("WARNING", "Termination requested by user. Aborting...")
            self.worker.cancel()

    def _on_test_started(self, mode: str, total_nodes: int) -> None:
        self.view_dashboard.progress_bar.setValue(0)
        self.view_dashboard.lbl_active_info.setText(
            f"⚡ Loaded {total_nodes} valid nodes. Starting {mode.upper()} benchmark..."
        )
        self.view_logs.append_log("INFO", f"Benchmark started: {mode.upper()} with {total_nodes} nodes.")

    def _on_batch_started(self, batch_idx: int, total_batches: int, batch_size: int) -> None:
        self.view_logs.append_log("INFO", f"Batch {batch_idx}/{total_batches} started ({batch_size} nodes).")

    def _on_batch_completed(self, batch_idx: int, passed: int, failed: int) -> None:
        self.view_logs.append_log("INFO", f"Batch {batch_idx} completed: {passed} passed, {failed} failed.")
        self._refresh_db_stats()

    def _on_round_started(self, round_num: int, pool_size: int) -> None:
        self.view_logs.append_log("INFO", f"Round {round_num} started with {pool_size} candidate nodes.")

    def _on_round_completed(self, round_num: int, passed: int, failed: int, eliminated: int) -> None:
        self.view_logs.append_log(
            "INFO",
            f"Round {round_num} finished: {passed} passed, {failed} failed, {eliminated} eliminated.",
        )
        self._refresh_db_stats()

    def _on_node_testing_started(self, node_id: str, tag: str, addr: str, port: int, proto: str, cur: int, tot: int, mode: str) -> None:
        self.view_dashboard.update_active_node(cur, tot, tag, addr, port, proto, mode)

    def _on_batch_progress(self, b_idx: int, cur: int, tot: int, node_id: str, success: bool, details: str) -> None:
        sym = "✓ PASS" if success else "✗ FAIL"
        self.view_dashboard.add_stream_entry(sym, node_id[:8], f"Batch {b_idx}", details)

    def _on_round_progress(self, r_num: int, comp: int, tot: int, node_id: str, speed: float, success: bool, tag: str) -> None:
        sym = "✓ SPEED" if success else "✗ SLOW"
        spd_str = f"{speed:.2f} Mbps" if speed > 0 else "0.00 Mbps"
        self.view_dashboard.add_stream_entry(sym, tag or node_id[:8], f"Round {r_num} [{comp}/{tot}]", spd_str)

    def _on_node_eliminated(self, node_id: str, r_num: int, reason: str) -> None:
        self.view_dashboard.add_stream_entry("↪ ELIM", node_id[:8], f"R{r_num}", reason)
        self.view_logs.append_log("WARNING", f"Node {node_id[:8]} eliminated: {reason}")
        self._refresh_db_stats()

    def _on_log_emitted(self, level: str, message: str) -> None:
        self.view_logs.append_log(level, message)

    def _on_test_completed(self, mode: str, total: int, passed: int, duration_sec: float) -> None:
        self.view_logs.append_log("INFO", f"Completed {mode.upper()}! {passed}/{total} passed in {duration_sec:.1f}s.")
        self._refresh_db_stats()
        self.view_nodes.refresh_nodes()

    def _on_worker_finished(self) -> None:
        self.view_dashboard.set_running_state(False, "IDLE")
        self.view_dashboard.progress_bar.setValue(100)
        self._refresh_db_stats()

    def _on_worker_error(self, err_msg: str) -> None:
        self.view_logs.append_log("ERROR", f"Worker encountered error: {err_msg}")
        self.view_dashboard.set_running_state(False, "ERROR")
        self.view_dashboard.lbl_active_info.setText(f"<b style='color:#ef4444;'>Error:</b> {err_msg}")
