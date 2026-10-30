"""Background worker thread bridging EventBus async events into Qt signals."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, QThread, Signal

from src.config import AppConfig, load_config
from src.database import Database
from src.events import (
    BatchCompleted,
    BatchProgress,
    BatchStarted,
    Event,
    EventBus,
    GitHubSyncStatus,
    LogMessage,
    NodeEliminated,
    NodeTested,
    NodeTestingStarted,
    RoundCompleted,
    RoundProgress,
    RoundStarted,
    TestCompleted,
    TestStarted,
)
from src.geo.ip_lookup import GeoLookupService
from src.parser.fingerprint import load_blacklist
from src.parser.uri_parser import ParsedNode, parse_uri
from src.publisher.github_sync import GitHubPublisher
from src.testers.http_tester import HttpLatencyTester, fetch_nodes_from_sources
from src.testers.speed_tournament import SpeedTournamentEngine
from src.xray.binary_manager import BinaryManager


class BenchmarkWorker(QThread):
    """Executes HTTP or Speed testing in a separate thread with asyncio."""

    # Qt Signals for GUI reactivity
    test_started = Signal(str, int)  # mode, total_nodes
    node_testing_started = Signal(str, str, str, int, str, int, int, str)  # node_id, tag, addr, port, proto, cur, tot, mode
    batch_started = Signal(int, int, int)  # batch_idx, total_batches, batch_size
    batch_progress = Signal(int, int, int, str, bool, str)  # batch_idx, cur, tot, node_id, success, details
    batch_completed = Signal(int, int, int)  # batch_idx, passed, failed
    round_started = Signal(int, int)  # round_num, pool_size
    round_progress = Signal(int, int, int, str, float, bool, str)  # round_num, comp, tot, node_id, speed, success, tag
    round_completed = Signal(int, int, int, int)  # round_num, passed, failed, eliminated
    node_eliminated = Signal(str, int, str)  # node_id, round_num, reason
    node_tested = Signal(str, object, object, bool, str)  # node_id, latency, speed, success, error
    github_sync = Signal(str, str)  # status, message
    log_emitted = Signal(str, str)  # level, message
    test_completed = Signal(str, int, int, float)  # mode, total, passed, duration_sec
    error_occurred = Signal(str)

    def __init__(
        self,
        mode: str = "http",  # 'http' or 'speed'
        source_type: str = "subs",  # 'subs', 'file', 'http-output', 'db'
        file_path: Optional[str] = None,
        limit: Optional[int] = None,
        auto_push: bool = False,
        config: Optional[AppConfig] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.mode = mode
        self.source_type = source_type
        self.file_path = file_path
        self.limit = limit
        self.auto_push = auto_push
        self.config = config or load_config()
        self.event_bus = EventBus()
        self._is_cancelled = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._wire_event_bus()

    def _wire_event_bus(self) -> None:
        """Route engine EventBus events directly into Qt Signals."""
        self.event_bus.subscribe(TestStarted, lambda ev: self.test_started.emit(ev.mode, ev.total_nodes))
        self.event_bus.subscribe(
            NodeTestingStarted,
            lambda ev: self.node_testing_started.emit(
                ev.node_id, ev.node_tag, ev.address, ev.port, ev.protocol, ev.current, ev.total, ev.mode
            ),
        )
        self.event_bus.subscribe(
            BatchStarted,
            lambda ev: self.batch_started.emit(ev.batch_index, ev.total_batches, ev.batch_size),
        )
        self.event_bus.subscribe(
            BatchProgress,
            lambda ev: self.batch_progress.emit(
                ev.batch_index, ev.current, ev.total, ev.node_id, ev.success, ev.details
            ),
        )
        self.event_bus.subscribe(
            BatchCompleted,
            lambda ev: self.batch_completed.emit(ev.batch_index, ev.passed_count, ev.failed_count),
        )
        self.event_bus.subscribe(
            RoundStarted,
            lambda ev: self.round_started.emit(ev.round_num, ev.pool_size),
        )
        self.event_bus.subscribe(
            RoundProgress,
            lambda ev: self.round_progress.emit(
                ev.round_num, ev.completed, ev.total, ev.node_id, ev.speed_mbps, ev.success, getattr(ev, "node_tag", "")
            ),
        )
        self.event_bus.subscribe(
            RoundCompleted,
            lambda ev: self.round_completed.emit(
                ev.round_num, ev.passed_count, ev.failed_count, ev.eliminated_count
            ),
        )
        self.event_bus.subscribe(
            NodeEliminated,
            lambda ev: self.node_eliminated.emit(ev.node_id, ev.round_num, ev.reason),
        )
        self.event_bus.subscribe(
            NodeTested,
            lambda ev: self.node_tested.emit(ev.node_id, ev.latency_ms, ev.speed_mbps, ev.success, ev.error or ""),
        )
        self.event_bus.subscribe(
            GitHubSyncStatus,
            lambda ev: self.github_sync.emit(ev.status, ev.message),
        )
        self.event_bus.subscribe(
            LogMessage,
            lambda ev: self.log_emitted.emit(ev.level, ev.message),
        )
        self.event_bus.subscribe(
            TestCompleted,
            lambda ev: self.test_completed.emit(ev.mode, ev.total_nodes, ev.passed_nodes, ev.duration_sec),
        )

    def cancel(self) -> None:
        """Cancel execution."""
        self._is_cancelled = True
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    def run(self) -> None:
        """Entry point for QThread execution."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            if self.mode == "http":
                self._loop.run_until_complete(self._run_http_test())
            elif self.mode == "speed":
                self._loop.run_until_complete(self._run_speed_test())
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            try:
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            except Exception:
                pass
            self._loop.close()

    async def _run_http_test(self) -> None:
        bin_manager = BinaryManager(bin_dir=self.config.paths.bin_dir, event_bus=self.event_bus)
        xray_binary = bin_manager.ensure_binary()

        db = Database(self.config.paths.database_path)
        blacklist = load_blacklist(self.config.paths.blacklist_file)
        geo_service = GeoLookupService(
            db=db,
            cache_ttl_days=self.config.geo.cache_ttl_days,
            blocked_google_countries=self.config.geo.blocked_google_countries,
            check_google=self.config.geo.check_google_country,
            primary_api_url=self.config.geo.primary_api_url,
            backup_api_urls=self.config.geo.backup_api_urls,
            google_check_url=self.config.geo.google_check_url,
            google_fallback_url=self.config.geo.google_fallback_url,
            event_bus=self.event_bus,
        )

        nodes = await fetch_nodes_from_sources(
            source_type=self.source_type,
            file_path=self.file_path,
            subs_path=self.config.paths.subscriptions_file,
            blacklist=blacklist,
            event_bus=self.event_bus,
        )

        if self.limit and self.limit > 0:
            nodes = nodes[: self.limit]

        if not nodes:
            self.event_bus.log("No valid nodes found to test.", level="WARNING")
            db.close()
            return

        tester = HttpLatencyTester(
            config=self.config,
            db=db,
            geo_service=geo_service,
            xray_binary=xray_binary,
            event_bus=self.event_bus,
        )

        passed_nodes = await tester.run(nodes)
        db.close()

        if self.auto_push and self.config.github.token and self.config.github.repo:
            publisher = GitHubPublisher(
                token=self.config.github.token,
                repo=self.config.github.repo,
                branch=self.config.github.branch,
                commit_prefix=self.config.github.commit_message_prefix,
                event_bus=self.event_bus,
            )
            await publisher.publish_file(
                self.config.paths.output_http_file,
                target_repo_path=f"results/{Path(self.config.paths.output_http_file).name}",
            )

    async def _run_speed_test(self) -> None:
        bin_manager = BinaryManager(bin_dir=self.config.paths.bin_dir, event_bus=self.event_bus)
        xray_binary = bin_manager.ensure_binary()

        db = Database(self.config.paths.database_path)
        blacklist = load_blacklist(self.config.paths.blacklist_file)
        geo_service = GeoLookupService(
            db=db,
            cache_ttl_days=self.config.geo.cache_ttl_days,
            blocked_google_countries=self.config.geo.blocked_google_countries,
            check_google=False,
            primary_api_url=self.config.geo.primary_api_url,
            backup_api_urls=self.config.geo.backup_api_urls,
            google_check_url=self.config.geo.google_check_url,
            google_fallback_url=self.config.geo.google_fallback_url,
            event_bus=self.event_bus,
        )

        nodes: List[ParsedNode] = []
        if self.source_type == "http-output":
            http_out = Path(self.file_path or self.config.paths.output_http_file)
            if http_out.is_file():
                with open(http_out, "r", encoding="utf-8") as f:
                    for line in f:
                        line_str = line.strip()
                        if line_str and not line_str.startswith("#"):
                            parsed = parse_uri(line_str)
                            if parsed:
                                nodes.append(parsed)
        elif self.source_type == "db":
            active_records = db.get_active_nodes()
            for rec in active_records:
                parsed = parse_uri(rec.raw_uri)
                if parsed:
                    nodes.append(parsed)
        elif self.source_type == "file":
            in_file = Path(self.file_path or self.config.paths.custom_nodes_file)
            if in_file.is_file():
                with open(in_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line_str = line.strip()
                        if line_str and not line_str.startswith("#"):
                            parsed = parse_uri(line_str)
                            if parsed:
                                nodes.append(parsed)

        if self.limit and self.limit > 0:
            nodes = nodes[: self.limit]

        if not nodes:
            self.event_bus.log("No valid nodes found for speed tournament.", level="WARNING")
            db.close()
            return

        engine = SpeedTournamentEngine(
            config=self.config,
            db=db,
            geo_service=geo_service,
            xray_binary=xray_binary,
            event_bus=self.event_bus,
        )

        survivors = await engine.run_tournament(nodes)
        db.close()

        if self.auto_push and self.config.github.token and self.config.github.repo:
            publisher = GitHubPublisher(
                token=self.config.github.token,
                repo=self.config.github.repo,
                branch=self.config.github.branch,
                commit_prefix=self.config.github.commit_message_prefix,
                event_bus=self.event_bus,
            )
            await publisher.publish_file(
                self.config.paths.output_speed_file,
                target_repo_path=f"results/{Path(self.config.paths.output_speed_file).name}",
            )
