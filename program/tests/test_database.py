"""Unit tests for SQLite database repository, GeoIP caching, and intelligence records."""
import gc
import time
from pathlib import Path
import pytest

from src.database import Database, GeoCacheRecord


@pytest.fixture
def temp_db():
    db_path = Path("data/test_db.sqlite")
    if db_path.exists():
        db_path.unlink(missing_ok=True)
    db = Database(db_path)
    yield db
    db.close()
    gc.collect()
    for ext in ("", "-wal", "-shm"):
        p = Path(f"{db_path}{ext}")
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass


def test_geo_cache_expiration(temp_db):
    now = time.time()
    # Cache an entry from 20 days ago
    old_record = GeoCacheRecord(
        ip="8.8.8.8",
        country_code="US",
        isp="Google LLC",
        google_country="US",
        is_google_bad=False,
        updated_at=now - (20 * 86400),
    )
    temp_db.save_geo_cache(old_record)

    # With TTL 14 days, it should be considered expired and return None
    fetched = temp_db.get_geo_cache("8.8.8.8", ttl_days=14)
    assert fetched is None

    # Fresh record
    fresh_record = GeoCacheRecord(
        ip="1.1.1.1",
        country_code="AU",
        isp="Cloudflare",
        google_country="AU",
        is_google_bad=False,
        updated_at=now,
    )
    temp_db.save_geo_cache(fresh_record)

    fetched_fresh = temp_db.get_geo_cache("1.1.1.1", ttl_days=14)
    assert fetched_fresh is not None
    assert fetched_fresh.country_code == "AU"
    assert fetched_fresh.isp == "Cloudflare"


def test_node_record_lifecycle(temp_db):
    node_id = "test-node-12345"
    raw_uri = "vless://uuid@host.com:443#Test"

    # Upsert node
    node = temp_db.upsert_node(
        node_id=node_id,
        raw_uri=raw_uri,
        protocol="vless",
        server_address="host.com",
        port=443,
    )
    assert node.node_id == node_id
    assert node.seq_id == 1
    assert node.cumulative_score == 0
    assert node.consecutive_zero_runs == 0
    assert node.is_dead is False

    # Update geo
    temp_db.update_node_geo(
        node_id=node_id,
        exit_ip="1.2.3.4",
        geo_country="DE",
        isp="Hetzner",
        google_country="DE",
        is_google_bad=False,
    )
    node_updated = temp_db.get_node(node_id)
    assert node_updated.geo_country == "DE"
    assert node_updated.isp == "Hetzner"

    # Add points
    temp_db.add_cumulative_point(node_id)
    temp_db.add_cumulative_point(node_id)
    node_scored = temp_db.get_node(node_id)
    assert node_scored.cumulative_score == 2
