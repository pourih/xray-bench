"""Node Explorer view for filtering, searching, inspecting, and copying proxy nodes."""
from __future__ import annotations

from typing import List, Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.database import Database, NodeRecord
from src.parser.uri_parser import parse_uri, serialize_uri


class NodesView(QWidget):
    """Modern node table explorer with live search and 1-click clipboard copying."""

    def __init__(self, db_path: str = "data/nodes_cache.db", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.db_path = db_path
        self._all_records: List[NodeRecord] = []
        self._init_ui()
        self.refresh_nodes()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ── Header Row ──
        header_row = QHBoxLayout()
        header_col = QVBoxLayout()
        header_col.setSpacing(4)

        title = QLabel("Node Intelligence Explorer")
        title.setProperty("class", "heading-1")
        header_col.addWidget(title)

        subtitle = QLabel("Browse, filter, and copy benchmarked proxy configurations")
        subtitle.setProperty("class", "label-muted")
        header_col.addWidget(subtitle)

        header_row.addLayout(header_col)
        header_row.addStretch()

        # Action buttons
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setProperty("class", "btn-secondary")
        btn_refresh.clicked.connect(self.refresh_nodes)
        header_row.addWidget(btn_refresh)

        btn_copy_all = QPushButton("📋 Copy All Active URIs")
        btn_copy_all.setProperty("class", "btn-primary")
        btn_copy_all.clicked.connect(self._copy_all_uris)
        header_row.addWidget(btn_copy_all)

        layout.addLayout(header_row)

        # ── Search & Filter Bar ──
        filter_card = QFrame()
        filter_card.setProperty("class", "card")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(14, 10, 14, 10)
        filter_layout.setSpacing(12)

        lbl_search = QLabel("🔍")
        lbl_search.setStyleSheet("background-color: transparent; font-size: 14px;")
        filter_layout.addWidget(lbl_search)

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Filter by country code (e.g. DE, NL), tag (xBench-0042), ISP, protocol, or host...")
        self.input_search.textChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.input_search)

        self.lbl_count = QLabel("0 nodes")
        self.lbl_count.setStyleSheet("background-color: transparent; color: #818cf8; font-weight: 600; font-size: 12px;")
        filter_layout.addWidget(self.lbl_count)

        layout.addWidget(filter_card)

        # ── Table Widget ──
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Tag",
            "Location",
            "Protocol",
            "Host:Port",
            "ISP / Org",
            "Latency",
            "Speed",
            "Points",
            "Copy",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().resizeSection(0, 110)
        self.table.horizontalHeader().resizeSection(1, 140)
        self.table.horizontalHeader().resizeSection(2, 90)
        self.table.horizontalHeader().resizeSection(3, 190)
        self.table.horizontalHeader().resizeSection(4, 180)
        self.table.horizontalHeader().resizeSection(5, 90)
        self.table.horizontalHeader().resizeSection(6, 100)
        self.table.horizontalHeader().resizeSection(7, 80)
        self.table.horizontalHeader().resizeSection(8, 90)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.verticalHeader().setMinimumSectionSize(46)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table)

    def refresh_nodes(self) -> None:
        """Fetch nodes from SQLite database and populate table."""
        try:
            db = Database(self.db_path)
            self._all_records = db.get_active_nodes()
            db.close()
        except Exception:
            self._all_records = []

        self._apply_filter(self.input_search.text())

    def _apply_filter(self, query: str) -> None:
        """Filter cached records against search string."""
        q = query.strip().lower()
        filtered = [
            r for r in self._all_records
            if not q or (
                q in (f"xbench-{r.seq_id:04d}" if r.seq_id else "").lower()
                or q in (r.geo_country or "").lower()
                or q in (r.google_country or "").lower()
                or q in (r.isp or "").lower()
                or q in (r.protocol or "").lower()
                or q in (r.server_address or "").lower()
            )
        ]

        # Sort primarily by cumulative score descending
        filtered.sort(key=lambda x: (-x.cumulative_score, x.current_tournament_rank or 9999))

        self.table.setRowCount(len(filtered))
        for row_idx, r in enumerate(filtered):
            tag = f"xBench-{r.seq_id:04d}" if r.seq_id else r.node_id[:8]

            # Country label with flag
            from src.geo.ip_lookup import cc_to_flag
            geo_flag = cc_to_flag(r.geo_country) if r.geo_country else ""
            if r.google_country and r.google_country != r.geo_country:
                g_flag = cc_to_flag(r.google_country)
                loc_str = f"{geo_flag} {r.geo_country} (or {g_flag} {r.google_country})"
            else:
                loc_str = f"{geo_flag} {r.geo_country}" if r.geo_country else "Unknown"

            # Latency display
            lat_str = f"{r.http_latency_ms:.0f} ms" if r.http_latency_ms else "--"
            # Speed display
            spd_str = f"{r.last_speed_mbps:.2f} Mbps" if r.last_speed_mbps and r.last_speed_mbps > 0 else "--"

            self.table.setItem(row_idx, 0, QTableWidgetItem(tag))
            self.table.setItem(row_idx, 1, QTableWidgetItem(loc_str))
            self.table.setItem(row_idx, 2, QTableWidgetItem(r.protocol.upper()))
            self.table.setItem(row_idx, 3, QTableWidgetItem(f"{r.server_address}:{r.port}"))
            self.table.setItem(row_idx, 4, QTableWidgetItem(r.isp or "Unknown"))
            self.table.setItem(row_idx, 5, QTableWidgetItem(lat_str))
            self.table.setItem(row_idx, 6, QTableWidgetItem(spd_str))
            self.table.setItem(row_idx, 7, QTableWidgetItem(f"{r.cumulative_score}pts"))
            self.table.setRowHeight(row_idx, 46)

            # Copy button inside centered container with zero vertical clipping
            container = QWidget()
            c_layout = QHBoxLayout(container)
            c_layout.setContentsMargins(0, 0, 0, 0)
            c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_copy = QPushButton("Copy")
            btn_copy.setProperty("class", "btn-copy")
            btn_copy.setFixedSize(68, 28)
            btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
            raw_uri = r.raw_uri
            btn_copy.clicked.connect(lambda _, b=btn_copy, u=raw_uri: self._copy_single_uri(b, u))
            c_layout.addWidget(btn_copy)

            self.table.setCellWidget(row_idx, 8, container)

        self.lbl_count.setText(f"{len(filtered)} / {len(self._all_records)} nodes")

    def _copy_single_uri(self, btn: QPushButton, uri: str) -> None:
        """Copy single URI string to system clipboard with temporary feedback."""
        clipboard = QApplication.clipboard()
        clipboard.setText(uri)
        btn.setText("Copied!")
        btn.setStyleSheet("color: #10b981; font-weight: 700; border-color: #10b981; padding: 0px 4px;")
        QTimer.singleShot(1400, lambda: (btn.setText("Copy"), btn.setStyleSheet("")))

    def _copy_all_uris(self) -> None:
        """Copy all active URIs to system clipboard."""
        uris = [r.raw_uri for r in self._all_records if r.raw_uri]
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(uris))
