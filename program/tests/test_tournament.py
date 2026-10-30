"""Unit tests for the iterative tournament speed test algorithm and 3-strike pruning."""
import asyncio
import gc
from pathlib import Path
import pytest

from src.config import AppConfig
from src.database import Database
from src.events import EventBus
from src.geo.ip_lookup import GeoLookupService
from src.parser.uri_parser import parse_uri
from src.testers.speed_tournament import SpeedTournamentEngine


@pytest.fixture
def mock_db_and_engine():
    db_path = Path("data/test_tournament.sqlite")
    if db_path.exists():
        db_path.unlink(missing_ok=True)
    db = Database(db_path)
    config = AppConfig()
    config.paths.database_path = db_path
    config.paths.output_speed_file = Path("data/test_nodes_speed.txt")
    config.speed_test.min_speed_mbps = 1.0

    geo_service = GeoLookupService(db=db, check_google=False)
    event_bus = EventBus()
    engine = SpeedTournamentEngine(
        config=config,
        db=db,
        geo_service=geo_service,
        xray_binary=Path("dummy_xray"),
        event_bus=event_bus,
    )
    yield db, engine, config
    db.close()
    gc.collect()
    for ext in ("", "-wal", "-shm"):
        p = Path(f"{db_path}{ext}")
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
    try:
        Path("data/test_nodes_speed.txt").unlink(missing_ok=True)
    except OSError:
        pass


def test_tournament_exact_tier_ordering(mock_db_and_engine):
    db, engine, config = mock_db_and_engine

    # Create 9 mock VLESS nodes
    raw_nodes = [
        parse_uri(f"vless://00000000-0000-0000-0000-00000000000{i}@node{i}.com:443?type=tcp#Node{i}")
        for i in range(1, 10)
    ]
    # N1 .. N9
    n1, n2, n3, n4, n5, n6, n7, n8, n9 = raw_nodes

    def mock_speeds_for_pool(pool, round_num):
        pool_ids = {n.node_id for n in pool}
        res = {}
        if round_num == 1:
            speeds_map = {
                n1.node_id: 100.0,
                n2.node_id: 80.0,
                n3.node_id: 60.0,
                n4.node_id: 40.0,
                n5.node_id: 30.0,
                n6.node_id: 20.0,
                n7.node_id: 10.0,
                n8.node_id: 0.0,
                n9.node_id: 0.0,
            }
        elif round_num == 2:
            speeds_map = {
                n1.node_id: 95.0,
                n2.node_id: 85.0,
                n3.node_id: 65.0,
                n4.node_id: 45.0,
                n5.node_id: 0.0,
            }
        elif round_num == 3:
            speeds_map = {
                n1.node_id: 110.0,
                n2.node_id: 90.0,
                n3.node_id: 70.0,
            }
        elif round_num == 4:
            speeds_map = {
                n1.node_id: 105.0,
                n2.node_id: 92.0,
            }
        elif round_num == 5:
            speeds_map = {
                n1.node_id: 100.0,
            }
        else:
            speeds_map = {}
        for nid in pool_ids:
            res[nid] = speeds_map.get(nid, 0.0)
        return res

    async def mock_test_batches(pool, round_num):
        return mock_speeds_for_pool(pool, round_num)

    engine._test_pool_in_batches = mock_test_batches

    async def _run():
        await engine.run_tournament(raw_nodes)

    asyncio.run(_run())

    # Verify ranks assigned in DB
    rec_n1 = db.get_node(n1.node_id)
    rec_n2 = db.get_node(n2.node_id)
    rec_n3 = db.get_node(n3.node_id)
    rec_n4 = db.get_node(n4.node_id)
    rec_n5 = db.get_node(n5.node_id)
    rec_n6 = db.get_node(n6.node_id)
    rec_n7 = db.get_node(n7.node_id)
    rec_n8 = db.get_node(n8.node_id)
    rec_n9 = db.get_node(n9.node_id)

    # Winner: N1 (Rank 1)
    assert rec_n1.current_tournament_rank == 1

    # E4: N2 (Rank 2)
    assert rec_n2.current_tournament_rank == 2

    # E3: N3 (Rank 3)
    assert rec_n3.current_tournament_rank == 3

    # E2: N4 (Rank 4)
    assert rec_n4.current_tournament_rank == 4

    # E1: N6, N7 (Ranks 5, 6)
    assert rec_n6.current_tournament_rank in (5, 6)
    assert rec_n7.current_tournament_rank in (5, 6)

    # F2: N5 (Rank 7)
    assert rec_n5.current_tournament_rank == 7

    # F1: N8, N9 (Ranks 8, 9)
    assert rec_n8.current_tournament_rank in (8, 9)
    assert rec_n9.current_tournament_rank in (8, 9)

    # Verify tier relative order assertions:
    # 1. F1 at very bottom
    assert rec_n8.current_tournament_rank > rec_n5.current_tournament_rank
    assert rec_n9.current_tournament_rank > rec_n5.current_tournament_rank

    # 2. F2 above F1
    assert rec_n5.current_tournament_rank < rec_n8.current_tournament_rank

    # 3. E1 directly above F_last (F2)
    assert rec_n6.current_tournament_rank < rec_n5.current_tournament_rank
    assert rec_n7.current_tournament_rank < rec_n5.current_tournament_rank

    # 4. E2 directly above E1
    assert rec_n4.current_tournament_rank < rec_n6.current_tournament_rank

    # 5. E3 directly above E2
    assert rec_n3.current_tournament_rank < rec_n4.current_tournament_rank

    # 6. E4 directly above E3
    assert rec_n2.current_tournament_rank < rec_n3.current_tournament_rank

    # 7. Winner at the very top
    assert rec_n1.current_tournament_rank == 1


def test_3_strike_pruning(mock_db_and_engine):
    db, engine, _ = mock_db_and_engine

    node = parse_uri("vless://bad-uuid@fail.node.com:443?type=tcp#FailNode")
    good_node = parse_uri("vless://good-uuid@good.node.com:443?type=tcp#GoodNode")

    async def _run():
        # Run 1: node fails Round 1 (consecutive_zero_runs -> 1)
        async def mock_run_1(pool, round_num):
            return {node.node_id: 0.0, good_node.node_id: 50.0}

        engine._test_pool_in_batches = mock_run_1
        await engine.run_tournament([node, good_node])

        rec = db.get_node(node.node_id)
        assert rec.consecutive_zero_runs == 1
        assert rec.is_dead is False

        # Run 2: node fails Round 1 again (consecutive_zero_runs -> 2)
        await engine.run_tournament([node, good_node])

        rec = db.get_node(node.node_id)
        assert rec.consecutive_zero_runs == 2
        assert rec.is_dead is False

        # Run 3: node fails Round 1 3rd time (consecutive_zero_runs -> 3, marked dead!)
        await engine.run_tournament([node, good_node])

        rec = db.get_node(node.node_id)
        assert rec.consecutive_zero_runs == 3
        assert rec.is_dead is True

        # Run 4: dead node is excluded from tournament execution and output
        async def mock_run_4(pool, round_num):
            return {good_node.node_id: 50.0}

        engine._test_pool_in_batches = mock_run_4
        survivors = await engine.run_tournament([node, good_node])
        survivor_ids = [n.node_id for n, _ in survivors]
        assert node.node_id not in survivor_ids
        assert good_node.node_id in survivor_ids

    asyncio.run(_run())


def test_consecutive_zero_runs_reset_on_pass(mock_db_and_engine):
    db, engine, _ = mock_db_and_engine

    node = parse_uri("vless://recover-uuid@recover.node.com:443?type=tcp#RecoverNode")

    async def _run():
        # Run 1: Fails Round 1 (strike 1)
        async def mock_fail(pool, round_num):
            return {node.node_id: 0.0}

        engine._test_pool_in_batches = mock_fail
        await engine.run_tournament([node])
        assert db.get_node(node.node_id).consecutive_zero_runs == 1

        # Run 2: Fails Round 1 (strike 2)
        await engine.run_tournament([node])
        assert db.get_node(node.node_id).consecutive_zero_runs == 2

        # Run 3: Passes Round 1 -> strike count resets to 0!
        async def mock_pass(pool, round_num):
            return {node.node_id: 25.0}

        engine._test_pool_in_batches = mock_pass
        await engine.run_tournament([node])

        rec = db.get_node(node.node_id)
        assert rec.consecutive_zero_runs == 0
        assert rec.is_dead is False
        assert rec.cumulative_score >= 1

    asyncio.run(_run())
