"""Mode 2: Iterative Tournament Speed Test & Cumulative Ranking Engine."""
from __future__ import annotations

import asyncio
import math
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import httpx

from src.config import AppConfig
from src.database import Database, NodeRecord
from src.events import (
    BatchStarted,
    EventBus,
    NodeEliminated,
    NodeTested,
    NodeTestingStarted,
    RoundCompleted,
    RoundProgress,
    RoundStarted,
    TestCompleted,
    TestStarted,
)
from src.geo.ip_lookup import GeoLookupService, format_remark
from src.parser.fingerprint import is_blacklisted, load_blacklist
from src.parser.uri_parser import ParsedNode, parse_uri, serialize_uri
from src.xray.config_builder import build_batch_config
from src.xray.runner import XrayBatchRunner


class SpeedTournamentEngine:
    """
    Executes iterative tournament speed testing, assigns cumulative points,
    computes tournament ranks, and applies 3-strike dead node pruning.
    """

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

    async def _measure_node_speed(
        self,
        node: ParsedNode,
        proxy_url: str,
        payload_url: str,
        timeout_sec: float,
    ) -> float:
        """
        Download payload through proxy and calculate throughput in Mbps.
        Returns speed in Mbps (>= 0.0) with strict asyncio.wait_for timeout enforcement.
        """
        async def _download() -> float:
            total_bytes = 0
            t0 = time.perf_counter()
            async with httpx.AsyncClient(
                proxy=proxy_url,
                timeout=httpx.Timeout(timeout_sec, connect=timeout_sec, read=timeout_sec),
                verify=False,
            ) as client:
                async with client.stream("GET", payload_url) as resp:
                    if resp.status_code != 200:
                        return 0.0
                    async for chunk in resp.aiter_bytes(chunk_size=16384):
                        total_bytes += len(chunk)
                        if (time.perf_counter() - t0) >= timeout_sec:
                            break
            elapsed = time.perf_counter() - t0
            if elapsed > 0 and total_bytes > 0:
                return (total_bytes * 8.0) / (elapsed * 1_000_000.0)
            return 0.0

        try:
            return await asyncio.wait_for(_download(), timeout=timeout_sec + 0.5)
        except Exception:
            return 0.0

    async def _test_pool_in_batches(
        self,
        pool: List[ParsedNode],
        round_num: int,
    ) -> Dict[str, float]:
        """
        Test all nodes in the current round pool in batches.
        Returns mapping: {node_id: speed_mbps}.
        """
        speeds: Dict[str, float] = {}
        batch_size = self.config.xray.batch_size
        batches = [pool[i : i + batch_size] for i in range(0, len(pool), batch_size)]
        completed_count = 0
        started_count = 0

        for b_idx, batch in enumerate(batches, start=1):
            batch_config, port_map = build_batch_config(
                batch, listen_host=self.config.xray.listen_host
            )

            try:
                async with XrayBatchRunner(
                    binary_path=self.xray_binary,
                    config_dict=batch_config,
                    port_map=port_map,
                    listen_host=self.config.xray.listen_host,
                    startup_timeout=self.config.xray.startup_timeout_sec,
                    event_bus=self.event_bus,
                ) as runner:

                    sem = asyncio.Semaphore(self.config.speed_test.concurrency)

                    async def run_node(node: ParsedNode):
                        nonlocal completed_count, started_count
                        async with sem:
                            started_count += 1
                            current_started = started_count
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
                                        total=len(pool),
                                        mode="speed",
                                    )
                                )

                            proxy_url = runner.get_proxy_url(node.node_id)
                            speed = 0.0
                            if proxy_url:
                                speed = await self._measure_node_speed(
                                    node=node,
                                    proxy_url=proxy_url,
                                    payload_url=self.config.speed_test.payload_url,
                                    timeout_sec=self.config.speed_test.timeout_sec,
                                )
                            speeds[node.node_id] = speed
                            completed_count += 1

                            if self.event_bus:
                                self.event_bus.emit(
                                    RoundProgress(
                                        round_num=round_num,
                                        completed=completed_count,
                                        total=len(pool),
                                        node_id=node.node_id,
                                        speed_mbps=speed,
                                        success=(speed >= self.config.speed_test.min_speed_mbps),
                                        node_tag=tag,
                                    )
                                )

                    await asyncio.gather(*(run_node(n) for n in batch))

            except Exception as e:
                if self.event_bus:
                    self.event_bus.log(
                        f"Round {round_num} Batch {b_idx} encountered error: {e}",
                        level="ERROR",
                    )
                for n in batch:
                    if n.node_id not in speeds:
                        speeds[n.node_id] = 0.0

        return speeds

    async def run_tournament(
        self,
        nodes: List[ParsedNode],
    ) -> List[Tuple[ParsedNode, NodeRecord]]:
        """
        Execute the iterative tournament algorithm.
        Returns sorted list of (node, updated_db_record) surviving nodes.
        """
        start_time = time.time()
        if self.event_bus:
            self.event_bus.emit(TestStarted(mode="speed-test", total_nodes=len(nodes)))

        # Ensure all nodes are in DB
        node_map: Dict[str, ParsedNode] = {}
        for n in nodes:
            node_map[n.node_id] = n
            self.db.upsert_node(
                node_id=n.node_id,
                raw_uri=n.raw_uri,
                protocol=n.protocol,
                server_address=n.address,
                port=n.port,
            )

        # Filter out nodes currently marked is_dead
        current_pool: List[ParsedNode] = []
        for n in nodes:
            rec = self.db.get_node(n.node_id)
            if rec and rec.is_dead:
                if self.event_bus:
                    self.event_bus.emit(
                        NodeEliminated(
                            node_id=n.node_id,
                            round_num=0,
                            reason="Already marked dead (3 strikes)",
                        )
                    )
                continue
            current_pool.append(n)

        # Tournament data structures
        # failed_tiers: list of F_r tiers. [F_1, F_2, ..., F_last]
        # eliminated_passed_tiers: list of E_r tiers. [E_1, E_2, ..., E_last]
        failed_tiers: List[List[Tuple[ParsedNode, float]]] = []
        eliminated_passed_tiers: List[List[Tuple[ParsedNode, float]]] = []
        tournament_winner: Optional[Tuple[ParsedNode, float]] = None

        round_num = 1
        all_round_1_passed_ids: Set[str] = set()
        latest_speeds: Dict[str, float] = {}

        while len(current_pool) > 0:
            if self.event_bus:
                self.event_bus.emit(
                    RoundStarted(round_num=round_num, pool_size=len(current_pool))
                )

            # 1. Speed Test Round r
            speeds = await self._test_pool_in_batches(current_pool, round_num=round_num)
            latest_speeds.update(speeds)

            # 2. Partition into Passed (S_r) and Failed (F_r)
            min_speed = self.config.speed_test.min_speed_mbps
            s_r: List[Tuple[ParsedNode, float]] = []
            f_r: List[Tuple[ParsedNode, float]] = []

            for n in current_pool:
                spd = speeds.get(n.node_id, 0.0)
                if spd >= min_speed:
                    s_r.append((n, spd))
                else:
                    f_r.append((n, spd))

            # Sort S_r descending by speed
            s_r.sort(key=lambda x: x[1], reverse=True)
            # Sort F_r descending by speed (if any partial)
            f_r.sort(key=lambda x: x[1], reverse=True)

            # Record round 1 passes for 3-strike check
            if round_num == 1:
                all_round_1_passed_ids = {n.node_id for n, _ in s_r}

            # 3. Award cumulative points (+1 point for each node in S_r)
            passed_ids = [n.node_id for n, _ in s_r]
            self.db.record_speed_round_pass(passed_ids)

            # 4. Record Failed Nodes of Round r
            failed_tiers.append(f_r)

            if self.event_bus:
                for n, _ in f_r:
                    self.event_bus.emit(
                        NodeEliminated(
                            node_id=n.node_id,
                            round_num=round_num,
                            reason=f"Failed Round {round_num} speed requirement (< {min_speed} Mbps)",
                        )
                    )

            # 5. Termination Check
            if len(s_r) == 0:
                if self.event_bus:
                    self.event_bus.emit(
                        RoundCompleted(
                            round_num=round_num,
                            passed_count=0,
                            failed_count=len(f_r),
                            eliminated_count=0,
                        )
                    )
                break

            if len(s_r) == 1:
                # Single remaining node is tournament winner!
                tournament_winner = s_r[0]
                if self.event_bus:
                    self.event_bus.emit(
                        RoundCompleted(
                            round_num=round_num,
                            passed_count=1,
                            failed_count=len(f_r),
                            eliminated_count=0,
                        )
                    )
                break

            # 6. Eliminate Bottom Third
            divisor = max(1, self.config.speed_test.bottom_third_divisor)
            k = max(1, math.floor(len(s_r) / divisor))

            # Slice slowest k nodes from bottom of S_r
            e_r = s_r[-k:]  # slowest k, already sorted descending by speed
            survivors = s_r[:-k]  # top two-thirds advancing to next round

            eliminated_passed_tiers.append(e_r)

            if self.event_bus:
                for n, spd in e_r:
                    self.event_bus.emit(
                        NodeEliminated(
                            node_id=n.node_id,
                            round_num=round_num,
                            reason=f"Eliminated in bottom-third of Round {round_num} ({spd:.2f} Mbps)",
                        )
                    )
                self.event_bus.emit(
                    RoundCompleted(
                        round_num=round_num,
                        passed_count=len(s_r),
                        failed_count=len(f_r),
                        eliminated_count=len(e_r),
                    )
                )

            current_pool = [n for n, _ in survivors]
            round_num += 1

        # Flatten tiers from top to bottom:
        # [Tournament Winner] -> [E_last] -> ... -> [E_2] -> [E_1] -> [F_last] -> ... -> [F_2] -> [F_1]
        flattened_run_order: List[Tuple[ParsedNode, float]] = []

        if tournament_winner:
            flattened_run_order.append(tournament_winner)

        # Reversed eliminated_passed_tiers (E_last down to E_1)
        for e_tier in reversed(eliminated_passed_tiers):
            flattened_run_order.extend(e_tier)

        # Reversed failed_tiers (F_last down to F_1)
        for f_tier in reversed(failed_tiers):
            flattened_run_order.extend(f_tier)

        # Assign current_tournament_rank (1, 2, ..., M) and update 3-strike dead node status
        max_zero = self.config.speed_test.max_consecutive_zero_runs

        for rank, (node, speed) in enumerate(flattened_run_order, start=1):
            passed_r1 = node.node_id in all_round_1_passed_ids
            newly_dead = self.db.update_tournament_result(
                node_id=node.node_id,
                rank=rank,
                speed_mbps=speed,
                passed_round_1=passed_r1,
                max_zero_runs=max_zero,
            )
            if newly_dead and self.event_bus:
                self.event_bus.emit(
                    NodeEliminated(
                        node_id=node.node_id,
                        round_num=1,
                        reason=f"Marked DEAD (failed Round 1 for {max_zero} consecutive runs)",
                    )
                )

        # Ensure GeoIP and Google check are populated for nodes that passed
        # and resolve remarks
        surviving_nodes_with_records: List[Tuple[ParsedNode, NodeRecord]] = []
        blocked_set = {c.strip().upper() for c in (self.config.geo.blocked_google_countries or ["IR", "RU"])}
        for node, _ in flattened_run_order:
            rec = self.db.get_node(node.node_id)
            if not rec or rec.is_dead:
                continue

            # If node doesn't have geo country yet, resolve it or use existing
            if not rec.geo_country:
                cached = self.db.get_geo_cache(rec.server_address)
                if cached:
                    rec.geo_country = cached.country_code
                    rec.isp = cached.isp
                    rec.google_country = cached.google_country
                    rec.is_google_bad = cached.is_google_bad

            is_blocked = (
                rec.is_google_bad
                or (rec.geo_country and rec.geo_country.upper() in blocked_set)
                or (rec.google_country and rec.google_country.upper() in blocked_set)
            )
            if is_blocked:
                continue

            # Format remark
            new_remark = format_remark(
                prefix=self.config.general.node_prefix,
                geo_country=rec.geo_country,
                google_country=rec.google_country,
                isp=rec.isp,
                seq_id=rec.seq_id,
                score=rec.cumulative_score,
            )
            node.remark = new_remark
            surviving_nodes_with_records.append((node, rec))

        # Final Sorting Rule:
        # Sort surviving nodes primarily by cumulative_score DESCENDING,
        # using current_tournament_rank ASCENDING as tie-breaker.
        surviving_nodes_with_records.sort(
            key=lambda item: (-item[1].cumulative_score, item[1].current_tournament_rank)
        )

        # Write output file
        out_path = Path(self.config.paths.output_speed_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for node, _ in surviving_nodes_with_records:
                serialized = serialize_uri(node, new_remark=node.remark)
                f.write(serialized + "\n")

        duration = time.time() - start_time
        if self.event_bus:
            self.event_bus.emit(
                TestCompleted(
                    mode="speed-test",
                    total_nodes=len(nodes),
                    passed_nodes=len(surviving_nodes_with_records),
                    duration_sec=duration,
                )
            )

        return surviving_nodes_with_records
