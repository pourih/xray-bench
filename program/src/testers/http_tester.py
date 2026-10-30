"""Mode 1: Real HTTP connectivity & latency tester through xray-core."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import httpx

from src.config import AppConfig
from src.database import Database
from src.events import (
    BatchCompleted,
    BatchProgress,
    BatchStarted,
    EventBus,
    NodeEliminated,
    NodeTested,
    NodeTestingStarted,
    TestCompleted,
    TestStarted,
)
from src.geo.ip_lookup import GeoLookupService, format_remark
from src.parser.fingerprint import is_blacklisted, load_blacklist
from src.parser.uri_parser import ParsedNode, parse_uri, safe_b64decode, serialize_uri
from src.xray.config_builder import build_batch_config, clean_node_for_xray, is_node_valid_for_xray
from src.xray.runner import XrayBatchRunner


async def fetch_subscription_nodes(url: str, timeout_sec: float = 15.0) -> List[ParsedNode]:
    """Fetch and decode subscription content from an HTTP/HTTPS URL."""
    nodes: List[ParsedNode] = []
    try:
        async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return nodes
            raw_content = resp.text.strip()
    except Exception:
        return nodes

    # Try Base64 decoding first
    content_lines = []
    try:
        decoded = safe_b64decode(raw_content).decode("utf-8", errors="ignore")
        if any(proto in decoded for proto in ("vmess://", "vless://", "trojan://", "ss://")):
            content_lines = decoded.splitlines()
    except Exception:
        pass

    if not content_lines:
        content_lines = raw_content.splitlines()

    for line in content_lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("#"):
            continue
        parsed = parse_uri(line_str)
        if parsed:
            nodes.append(parsed)

    return nodes


async def fetch_nodes_from_sources(
    source_type: str,
    file_path: Optional[Path | str] = None,
    subs_path: Optional[Path | str] = None,
    blacklist: Optional[Set[str]] = None,
    event_bus: Optional[EventBus] = None,
) -> List[ParsedNode]:
    """
    Fetch, parse, deduplicate by node_id, and filter nodes against blacklist.
    source_type: 'subs' or 'file'.
    """
    if blacklist is None:
        blacklist = set()

    raw_nodes: List[ParsedNode] = []

    if source_type == "subs":
        subs_file = Path(subs_path or "data/subscriptions.txt")
        if not subs_file.is_file():
            if event_bus:
                event_bus.log(f"Subscriptions file not found: {subs_file}", level="WARNING")
            return []

        urls = []
        with open(subs_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                u = line.strip()
                if u and not u.startswith("#"):
                    urls.append(u)

        if event_bus:
            event_bus.log(f"Fetching nodes from {len(urls)} subscription URLs...", level="INFO")

        tasks = [fetch_subscription_nodes(u) for u in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, list):
                raw_nodes.extend(res)

    elif source_type in ("file", "custom"):
        in_file = Path(file_path or "data/custom_nodes.txt")
        if not in_file.is_file():
            if event_bus:
                event_bus.log(f"Input file not found: {in_file}", level="WARNING")
            return []

        with open(in_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_str = line.strip()
                if line_str and not line_str.startswith("#"):
                    parsed = parse_uri(line_str)
                    if parsed:
                        raw_nodes.append(parsed)

    elif source_type == "http-output":
        http_file = Path(file_path or "results/nodes_http.txt")
        if not http_file.is_file():
            http_file = Path("../results/nodes_http.txt")
        if not http_file.is_file():
            if event_bus:
                event_bus.log(f"HTTP output file not found: {http_file}", level="WARNING")
            return []

        with open(http_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_str = line.strip()
                if line_str and not line_str.startswith("#"):
                    parsed = parse_uri(line_str)
                    if parsed:
                        raw_nodes.append(parsed)

    elif source_type == "db":
        db_file = Path("data/nodes_cache.db")
        if db_file.is_file():
            db_inst = Database(str(db_file))
            for rec in db_inst.get_active_nodes():
                parsed = parse_uri(rec.raw_uri)
                if parsed:
                    raw_nodes.append(parsed)
            db_inst.close()

    # Deduplicate by node_id and filter against blacklist & Xray core compatibility
    seen_ids: Set[str] = set()
    filtered_nodes: List[ParsedNode] = []
    unsupported_count = 0

    for node in raw_nodes:
        if node.node_id in seen_ids:
            continue
        if is_blacklisted(node, blacklist):
            if event_bus:
                event_bus.emit(
                    NodeEliminated(node_id=node.node_id, round_num=0, reason="Blacklisted")
                )
            continue

        cleaned = clean_node_for_xray(node)
        is_ok, reason = is_node_valid_for_xray(cleaned)
        if not is_ok:
            unsupported_count += 1
            if event_bus:
                event_bus.emit(
                    NodeEliminated(node_id=node.node_id, round_num=0, reason=f"Unsupported: {reason}")
                )
            continue

        seen_ids.add(cleaned.node_id)
        filtered_nodes.append(cleaned)

    if event_bus:
        msg = f"Loaded {len(raw_nodes)} raw nodes -> {len(filtered_nodes)} valid Xray nodes."
        if unsupported_count > 0:
            msg += f" (Filtered out {unsupported_count} incompatible/prohibited nodes)"
        event_bus.log(msg, level="INFO")

    return filtered_nodes


class HttpLatencyTester:
    """Executes Mode 1 HTTP latency tests across batches of nodes."""

    def __init__(
        self,
        config: AppConfig,
        db: Database,
        geo_service: GeoLookupService,
        xray_binary: Path | str,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.config = config
        self.db = db
        self.geo_service = geo_service
        self.xray_binary = Path(xray_binary)
        self.event_bus = event_bus

    async def _quick_ping(
        self,
        proxy_url: str,
        test_url: str,
        timeout_sec: float,
    ) -> Optional[float]:
        """
        Ultra-fast single-shot HTTP liveness ping through proxy.
        Hard deadline enforced via asyncio.wait_for.
        Returns latency in milliseconds if 200/204 received within timeout, else None.
        """
        t0 = time.perf_counter()
        try:
            async def _do_get() -> Optional[float]:
                async with httpx.AsyncClient(
                    proxy=proxy_url,
                    timeout=httpx.Timeout(timeout_sec, connect=timeout_sec, read=timeout_sec),
                    follow_redirects=False,
                    verify=False,
                ) as client:
                    resp = await client.get(test_url)
                    if resp.status_code in (200, 204):
                        return (time.perf_counter() - t0) * 1000.0
                    return None

            return await asyncio.wait_for(_do_get(), timeout=timeout_sec + 0.3)
        except Exception:
            return None

    async def run(
        self,
        nodes: List[ParsedNode],
    ) -> List[Tuple[ParsedNode, float]]:
        """
        Run HTTP connectivity and latency tests in batches using a high-performance 2-Phase pipeline:
          Phase 1: Rapid concurrent ping to verify alive status and eliminate dead nodes instantly.
          Phase 2: GeoIP / ISP & Google country detection ONLY on surviving alive nodes.
        Returns list of (renamed_node, latency_ms) sorted by latency ascending.
        """
        start_time = time.time()
        if self.event_bus:
            self.event_bus.emit(TestStarted(mode="http-test", total_nodes=len(nodes)))

        for n in nodes:
            self.db.upsert_node(
                node_id=n.node_id,
                raw_uri=n.raw_uri,
                protocol=n.protocol,
                server_address=n.address,
                port=n.port,
            )

        batch_size = self.config.xray.batch_size
        batches = [nodes[i : i + batch_size] for i in range(0, len(nodes), batch_size)]
        passed_nodes_with_latency: List[Tuple[ParsedNode, float]] = []

        for b_idx, batch in enumerate(batches, start=1):
            if self.event_bus:
                self.event_bus.emit(
                    BatchStarted(
                        batch_index=b_idx,
                        total_batches=len(batches),
                        batch_size=len(batch),
                    )
                )

            batch_config, port_map = build_batch_config(
                batch, listen_host=self.config.xray.listen_host
            )

            passed_in_batch = 0
            failed_in_batch = 0

            try:
                async with XrayBatchRunner(
                    binary_path=self.xray_binary,
                    config_dict=batch_config,
                    port_map=port_map,
                    listen_host=self.config.xray.listen_host,
                    startup_timeout=self.config.xray.startup_timeout_sec,
                    event_bus=self.event_bus,
                ) as runner:

                    sem = asyncio.Semaphore(self.config.http_test.concurrency)
                    started_in_batch = 0
                    completed_in_batch = 0

                    async def test_single_node(node: ParsedNode):
                        nonlocal passed_in_batch, failed_in_batch, started_in_batch, completed_in_batch
                        async with sem:
                            started_in_batch += 1
                            current_started = started_in_batch

                            rec = self.db.get_node(node.node_id)
                            tag = f"xBench-{rec.seq_id:04d}" if (rec and rec.seq_id) else (node.remark or node.node_id[:8])

                            if self.event_bus:
                                self.event_bus.emit(
                                    NodeTestingStarted(
                                        node_id=node.node_id,
                                        node_tag=tag,
                                        address=node.address,
                                        port=node.port,
                                        protocol=node.protocol,
                                        current=current_started,
                                        total=len(batch),
                                        mode="http",
                                    )
                                )

                            proxy_url = runner.get_proxy_url(node.node_id)
                            if not proxy_url:
                                failed_in_batch += 1
                                completed_in_batch += 1
                                if self.event_bus:
                                    self.event_bus.emit(
                                        BatchProgress(
                                            batch_index=b_idx,
                                            current=completed_in_batch,
                                            total=len(batch),
                                            node_id=node.node_id,
                                            success=False,
                                            details=f"Failed (No proxy port for {tag})",
                                        )
                                    )
                                return

                            latency = await self._quick_ping(
                                proxy_url=proxy_url,
                                test_url=self.config.http_test.test_url,
                                timeout_sec=self.config.http_test.timeout_sec,
                            )

                            if latency is None:
                                failed_in_batch += 1
                                completed_in_batch += 1
                                self.db.update_http_result(node.node_id, latency_ms=None)
                                if self.event_bus:
                                    self.event_bus.emit(
                                        NodeTested(
                                            node_id=node.node_id,
                                            latency_ms=None,
                                            success=False,
                                            error="Connection failed or timed out",
                                        )
                                    )
                                    self.event_bus.emit(
                                        BatchProgress(
                                            batch_index=b_idx,
                                            current=completed_in_batch,
                                            total=len(batch),
                                            node_id=node.node_id,
                                            success=False,
                                            details=f"Failed ({tag})",
                                        )
                                    )
                                return

                            # Alive candidate -> resolve Geo & Google check
                            try:
                                geo_info = await self.geo_service.resolve_node_geo(
                                    node_id=node.node_id,
                                    proxy_url=proxy_url,
                                    server_address=node.address,
                                    timeout_sec=min(self.config.http_test.timeout_sec, 5.0),
                                )
                            except Exception:
                                from src.geo.ip_lookup import GeoInfo
                                geo_info = GeoInfo(country_code="XX", isp="Unknown", google_country="XX", is_google_bad=False)

                            blocked_set = {c.strip().upper() for c in (self.config.geo.blocked_google_countries or ["IR", "RU"])}
                            is_blocked = (
                                geo_info.is_google_bad
                                or (geo_info.country_code.upper() in blocked_set)
                                or (geo_info.google_country.upper() in blocked_set)
                            )

                            completed_in_batch += 1

                            if is_blocked:
                                failed_in_batch += 1
                                reason_desc = (
                                    f"Blocked country (Geo: {geo_info.country_code}, Google: {geo_info.google_country})"
                                    if geo_info.country_code != geo_info.google_country
                                    else f"Blocked country ({geo_info.country_code})"
                                )
                                if self.event_bus:
                                    self.event_bus.emit(
                                        NodeEliminated(
                                            node_id=node.node_id,
                                            round_num=0,
                                            reason=reason_desc,
                                        )
                                    )
                                    self.event_bus.emit(
                                        BatchProgress(
                                            batch_index=b_idx,
                                            current=completed_in_batch,
                                            total=len(batch),
                                            node_id=node.node_id,
                                            success=False,
                                            details=f"Dropped ({reason_desc})",
                                        )
                                    )
                                return

                            # Passed! Format new remark and update node
                            rec = self.db.get_node(node.node_id)
                            seq_id = rec.seq_id if rec else 0
                            score = rec.cumulative_score if rec else 0
                            new_remark = format_remark(
                                prefix=self.config.general.node_prefix,
                                geo_country=geo_info.country_code,
                                google_country=geo_info.google_country,
                                isp=geo_info.isp,
                                seq_id=seq_id,
                                score=score,
                            )
                            node.remark = new_remark
                            self.db.update_http_result(node.node_id, latency_ms=latency)

                            passed_in_batch += 1
                            passed_nodes_with_latency.append((node, latency))

                            if self.event_bus:
                                self.event_bus.emit(
                                    NodeTested(
                                        node_id=node.node_id,
                                        latency_ms=latency,
                                        success=True,
                                    )
                                )
                                self.event_bus.emit(
                                    BatchProgress(
                                        batch_index=b_idx,
                                        current=completed_in_batch,
                                        total=len(batch),
                                        node_id=node.node_id,
                                        success=True,
                                        details=f"{latency:.1f}ms - {new_remark}",
                                    )
                                )

                    await asyncio.gather(*(test_single_node(n) for n in batch))

            except Exception as e:
                if self.event_bus:
                    self.event_bus.log(f"Batch {b_idx} failed: {e}", level="ERROR")

            if self.event_bus:
                self.event_bus.emit(
                    BatchCompleted(
                        batch_index=b_idx,
                        passed_count=passed_in_batch,
                        failed_count=failed_in_batch,
                    )
                )

        # Sort passed nodes ascending by HTTP latency (fastest first)
        passed_nodes_with_latency.sort(key=lambda x: x[1])

        # Write output file
        out_path = Path(self.config.paths.output_http_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for node, _ in passed_nodes_with_latency:
                serialized = serialize_uri(node, new_remark=node.remark)
                f.write(serialized + "\n")

        duration = time.time() - start_time
        if self.event_bus:
            self.event_bus.emit(
                TestCompleted(
                    mode="http-test",
                    total_nodes=len(nodes),
                    passed_nodes=len(passed_nodes_with_latency),
                    duration_sec=duration,
                )
            )

        return passed_nodes_with_latency
