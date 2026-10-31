"""Tests for HttpLatencyTester two-phase pipeline."""
import asyncio
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.config import AppConfig
from src.database import Database
from src.geo.ip_lookup import GeoInfo, GeoLookupService
from src.parser.uri_parser import ParsedNode
from src.testers.http_tester import HttpLatencyTester


def test_two_phase_alive_filter_and_enrichment(tmp_path):
    async def _async_test():
        db_path = tmp_path / "test_nodes.db"
        db = Database(db_path)
        config = AppConfig()
        config.paths.output_http_file = str(tmp_path / "output_http.txt")
        config.xray.batch_size = 10
        config.http_test.timeout_sec = 1.0

        geo_service = MagicMock(spec=GeoLookupService)
        # Mock resolve_node_geo
        geo_service.resolve_node_geo = AsyncMock(
            return_value=GeoInfo(
                exit_ip="1.2.3.4",
                country_code="DE",
                isp="Hetzner",
                google_country="DE",
                is_google_bad=False,
            )
        )

        tester = HttpLatencyTester(
            config=config,
            db=db,
            geo_service=geo_service,
            xray_binary=Path("dummy_xray"),
        )

        nodes = [
            ParsedNode(
                raw_uri="vless://u1@1.1.1.1:443?type=tcp#Node1",
                protocol="vless",
                address="1.1.1.1",
                port=443,
                uuid_or_password="u1",
                remark="Node1",
                node_id="id1",
            ),
            ParsedNode(
                raw_uri="vless://u2@2.2.2.2:443?type=tcp#Node2",
                protocol="vless",
                address="2.2.2.2",
                port=443,
                uuid_or_password="u2",
                remark="Node2",
                node_id="id2",
            ),
            ParsedNode(
                raw_uri="vless://u3@3.3.3.3:443?type=tcp#Node3",
                protocol="vless",
                address="3.3.3.3",
                port=443,
                uuid_or_password="u3",
                remark="Node3",
                node_id="id3",
            ),
        ]

        # Mock XrayBatchRunner context manager
        mock_runner = MagicMock()
        mock_runner.get_proxy_url.side_effect = lambda nid: f"socks5://127.0.0.1:1000{nid[-1]}"

        # Mock _quick_ping: id1 (dead -> None), id2 (alive -> 150ms), id3 (alive -> 80ms)
        async def fake_quick_ping(proxy_url, test_url, timeout_sec):
            if "10001" in proxy_url:
                return None
            if "10002" in proxy_url:
                return 150.0
            if "10003" in proxy_url:
                return 80.0
            return None

        with patch("src.testers.http_tester.XrayBatchRunner") as MockRunnerCls:
            MockRunnerCls.return_value.__aenter__ = AsyncMock(return_value=mock_runner)
            MockRunnerCls.return_value.__aexit__ = AsyncMock(return_value=None)
            with patch.object(tester, "_quick_ping", side_effect=fake_quick_ping):
                survivors = await tester.run(nodes)

        # id1 is dead -> eliminated in Phase 1
        # id2 and id3 are alive -> passed Phase 1 and enriched in Phase 2
        assert len(survivors) == 2
        # Sorted ascending by latency: id3 (80ms) first, then id2 (150ms)
        assert survivors[0][0].node_id == "id3"
        assert survivors[0][1] == 80.0
        assert survivors[1][0].node_id == "id2"
        assert survivors[1][1] == 150.0

        # Ensure geo_service was only called for id2 and id3, NOT id1!
        called_node_ids = [call.kwargs["node_id"] for call in geo_service.resolve_node_geo.call_args_list]
        assert "id1" not in called_node_ids
        assert "id2" in called_node_ids
        assert "id3" in called_node_ids

        # Check that remarks were formatted
        assert "🇩🇪 DE" in survivors[0][0].remark
        assert "Hetzner" in survivors[0][0].remark
        assert "xBench-" in survivors[0][0].remark
        assert "0pts" in survivors[0][0].remark
        assert "🇩🇪 DE" in survivors[1][0].remark

        db.close()

    asyncio.run(_async_test())


def test_rolling_events_emitted(tmp_path):
    async def _async_test():
        from src.events import EventBus, NodeTestingStarted

        db_path = tmp_path / "test_events.db"
        db = Database(db_path)
        config = AppConfig()
        config.paths.output_http_file = str(tmp_path / "output_http.txt")
        config.http_test.concurrency = 2

        geo_service = MagicMock(spec=GeoLookupService)
        geo_service.resolve_node_geo = AsyncMock(
            return_value=GeoInfo(
                exit_ip="1.2.3.4",
                country_code="DE",
                isp="Hetzner",
                google_country="DE",
                is_google_bad=False,
            )
        )

        event_bus = EventBus()
        started_events = []
        event_bus.subscribe(NodeTestingStarted, lambda ev: started_events.append(ev))

        tester = HttpLatencyTester(
            config=config,
            db=db,
            geo_service=geo_service,
            xray_binary=Path("dummy_xray"),
            event_bus=event_bus,
        )

        nodes = [
            ParsedNode(
                raw_uri="vless://u1@1.1.1.1:443?type=tcp#Node1",
                protocol="vless",
                address="1.1.1.1",
                port=443,
                uuid_or_password="u1",
                remark="Node1",
                node_id="id1",
            ),
            ParsedNode(
                raw_uri="vless://u2@2.2.2.2:443?type=tcp#Node2",
                protocol="vless",
                address="2.2.2.2",
                port=443,
                uuid_or_password="u2",
                remark="Node2",
                node_id="id2",
            ),
        ]

        mock_runner = MagicMock()
        mock_runner.get_proxy_url.side_effect = lambda nid: f"socks5://127.0.0.1:1000{nid[-1]}"

        with patch("src.testers.http_tester.XrayBatchRunner") as MockRunnerCls:
            MockRunnerCls.return_value.__aenter__ = AsyncMock(return_value=mock_runner)
            MockRunnerCls.return_value.__aexit__ = AsyncMock(return_value=None)
            with patch.object(tester, "_quick_ping", AsyncMock(return_value=120.0)):
                await tester.run(nodes)

        assert len(started_events) == 2
        assert started_events[0].total == 2
        assert started_events[0].current in (1, 2)
        assert started_events[0].mode == "http"
        assert "xBench-" in started_events[0].node_tag
        assert started_events[0].address in ("1.1.1.1", "2.2.2.2")

        db.close()

    asyncio.run(_async_test())
