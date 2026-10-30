"""SQLite ORM and repository for GeoIP caching and node intelligence."""
from __future__ import annotations

import contextlib
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, List, Optional


@dataclass
class GeoCacheRecord:
    ip: str
    country_code: str = ""
    isp: str = ""
    google_country: str = ""
    is_google_bad: bool = False
    updated_at: float = 0.0

    @property
    def is_expired(self, ttl_days: int = 14) -> bool:
        ttl_seconds = ttl_days * 86400
        return (time.time() - self.updated_at) > ttl_seconds


@dataclass
class NodeRecord:
    node_id: str
    raw_uri: str
    seq_id: int = 0
    protocol: str = ""
    server_address: str = ""
    port: int = 0
    exit_ip: str = ""
    geo_country: str = ""
    isp: str = ""
    google_country: str = ""
    is_google_bad: bool = False
    http_latency_ms: Optional[float] = None
    last_speed_mbps: Optional[float] = None
    cumulative_score: int = 0
    current_tournament_rank: int = 0
    consecutive_zero_runs: int = 0
    is_dead: bool = False
    first_seen_at: float = 0.0
    last_tested_at: float = 0.0


class Database:
    """Manages SQLite connection and schemas for xray-bench."""

    def __init__(self, db_path: Path | str = "data/nodes_cache.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # Enable WAL mode once at creation
        try:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        self._init_tables()

    @contextlib.contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def close(self) -> None:
        """Close the underlying database connection."""
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass

    def _init_tables(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS geo_cache (
                    ip TEXT PRIMARY KEY,
                    country_code TEXT NOT NULL,
                    isp TEXT NOT NULL,
                    google_country TEXT DEFAULT '',
                    is_google_bad INTEGER DEFAULT 0,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS nodes (
                    node_id TEXT PRIMARY KEY,
                    seq_id INTEGER UNIQUE,
                    raw_uri TEXT NOT NULL,
                    protocol TEXT NOT NULL,
                    server_address TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    exit_ip TEXT DEFAULT '',
                    geo_country TEXT DEFAULT '',
                    isp TEXT DEFAULT '',
                    google_country TEXT DEFAULT '',
                    is_google_bad INTEGER DEFAULT 0,
                    http_latency_ms REAL,
                    last_speed_mbps REAL,
                    cumulative_score INTEGER DEFAULT 0,
                    current_tournament_rank INTEGER DEFAULT 0,
                    consecutive_zero_runs INTEGER DEFAULT 0,
                    is_dead INTEGER DEFAULT 0,
                    first_seen_at REAL NOT NULL,
                    last_tested_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_nodes_is_dead ON nodes(is_dead);
                CREATE INDEX IF NOT EXISTS idx_nodes_score ON nodes(cumulative_score, current_tournament_rank);
                CREATE INDEX IF NOT EXISTS idx_geo_updated ON geo_cache(updated_at);
                """
            )
            # Automatic schema migration for seq_id
            try:
                conn.execute("ALTER TABLE nodes ADD COLUMN seq_id INTEGER;")
            except Exception:
                pass
            try:
                conn.execute("UPDATE nodes SET seq_id = rowid WHERE seq_id IS NULL OR seq_id = 0;")
            except Exception:
                pass
            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_seq_id ON nodes(seq_id);")
            except Exception:
                pass

    # ---------------- Geo Cache Operations ----------------

    def get_geo_cache(self, ip: str, ttl_days: int = 14) -> Optional[GeoCacheRecord]:
        """Fetch cached GeoIP if present and not expired."""
        if not ip:
            return None
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM geo_cache WHERE ip = ?", (ip,))
            row = cur.fetchone()
            if not row:
                return None
            record = GeoCacheRecord(
                ip=row["ip"],
                country_code=row["country_code"] or "",
                isp=row["isp"] or "",
                google_country=row["google_country"] or "",
                is_google_bad=bool(row["is_google_bad"]),
                updated_at=row["updated_at"],
            )
            if (time.time() - record.updated_at) > (ttl_days * 86400):
                return None
            return record

    def save_geo_cache(self, record: GeoCacheRecord) -> None:
        """Upsert GeoIP record into cache."""
        now = time.time()
        updated_at = record.updated_at if record.updated_at > 0 else now
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO geo_cache (ip, country_code, isp, google_country, is_google_bad, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(ip) DO UPDATE SET
                    country_code = excluded.country_code,
                    isp = excluded.isp,
                    google_country = excluded.google_country,
                    is_google_bad = excluded.is_google_bad,
                    updated_at = excluded.updated_at;
                """,
                (
                    record.ip,
                    record.country_code,
                    record.isp,
                    record.google_country,
                    int(record.is_google_bad),
                    updated_at,
                ),
            )

    # ---------------- Node Intelligence Operations ----------------

    def get_node(self, node_id: str) -> Optional[NodeRecord]:
        """Retrieve a node record by node_id."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM nodes WHERE node_id = ?", (node_id,))
            row = cur.fetchone()
            if not row:
                return None
            return NodeRecord(
                node_id=row["node_id"],
                raw_uri=row["raw_uri"],
                seq_id=row["seq_id"] if ("seq_id" in row.keys() and row["seq_id"] is not None) else 0,
                protocol=row["protocol"],
                server_address=row["server_address"],
                port=row["port"],
                exit_ip=row["exit_ip"] or "",
                geo_country=row["geo_country"] or "",
                isp=row["isp"] or "",
                google_country=row["google_country"] or "",
                is_google_bad=bool(row["is_google_bad"]),
                http_latency_ms=row["http_latency_ms"],
                last_speed_mbps=row["last_speed_mbps"],
                cumulative_score=row["cumulative_score"] or 0,
                current_tournament_rank=row["current_tournament_rank"] or 0,
                consecutive_zero_runs=row["consecutive_zero_runs"] or 0,
                is_dead=bool(row["is_dead"]),
                first_seen_at=row["first_seen_at"],
                last_tested_at=row["last_tested_at"],
            )

    def upsert_node(
        self,
        node_id: str,
        raw_uri: str,
        protocol: str = "",
        server_address: str = "",
        port: int = 0,
    ) -> NodeRecord:
        """Ensure node exists in DB and return the current record."""
        now = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO nodes (node_id, seq_id, raw_uri, protocol, server_address, port, first_seen_at, last_tested_at)
                VALUES (?, COALESCE((SELECT MAX(seq_id) FROM nodes), 0) + 1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    raw_uri = excluded.raw_uri,
                    protocol = CASE WHEN excluded.protocol != '' THEN excluded.protocol ELSE nodes.protocol END,
                    server_address = CASE WHEN excluded.server_address != '' THEN excluded.server_address ELSE nodes.server_address END,
                    port = CASE WHEN excluded.port > 0 THEN excluded.port ELSE nodes.port END;
                """,
                (node_id, raw_uri, protocol, server_address, port, now, now),
            )
        rec = self.get_node(node_id)
        assert rec is not None
        return rec

    def update_node_geo(
        self,
        node_id: str,
        exit_ip: str,
        geo_country: str,
        isp: str,
        google_country: str,
        is_google_bad: bool,
    ) -> None:
        """Update node's geo information."""
        now = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE nodes SET
                    exit_ip = ?,
                    geo_country = ?,
                    isp = ?,
                    google_country = ?,
                    is_google_bad = ?,
                    last_tested_at = ?
                WHERE node_id = ?;
                """,
                (
                    exit_ip,
                    geo_country,
                    isp,
                    google_country,
                    int(is_google_bad),
                    now,
                    node_id,
                ),
            )

    def update_http_result(self, node_id: str, latency_ms: Optional[float]) -> None:
        """Update latency from HTTP connectivity test."""
        now = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE nodes SET
                    http_latency_ms = ?,
                    last_tested_at = ?
                WHERE node_id = ?;
                """,
                (latency_ms, now, node_id),
            )

    def add_cumulative_point(self, node_id: str) -> None:
        """Add +1 to cumulative_score for surviving a speed round."""
        now = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE nodes SET
                    cumulative_score = cumulative_score + 1,
                    last_tested_at = ?
                WHERE node_id = ?;
                """,
                (now, node_id),
            )

    def record_speed_round_pass(self, node_ids: List[str]) -> None:
        """Batch increment cumulative_score by 1 for passed nodes."""
        if not node_ids:
            return
        now = time.time()
        with self._get_connection() as conn:
            conn.executemany(
                """
                UPDATE nodes SET
                    cumulative_score = cumulative_score + 1,
                    last_tested_at = ?
                WHERE node_id = ?;
                """,
                [(now, nid) for nid in node_ids],
            )

    def update_tournament_result(
        self,
        node_id: str,
        rank: int,
        speed_mbps: Optional[float],
        passed_round_1: bool,
        max_zero_runs: int = 3,
    ) -> bool:
        """
        Update tournament placement and 3-strike dead node tracking.
        Returns True if node was newly marked dead, False otherwise.
        """
        now = time.time()
        with self._get_connection() as conn:
            cur = conn.execute("SELECT consecutive_zero_runs, is_dead FROM nodes WHERE node_id = ?", (node_id,))
            row = cur.fetchone()
            current_zero_runs = row["consecutive_zero_runs"] if row else 0
            already_dead = bool(row["is_dead"]) if row else False

            if passed_round_1:
                new_zero_runs = 0
                is_dead = False
            else:
                new_zero_runs = current_zero_runs + 1
                is_dead = already_dead or (new_zero_runs >= max_zero_runs)

            conn.execute(
                """
                UPDATE nodes SET
                    current_tournament_rank = ?,
                    last_speed_mbps = ?,
                    consecutive_zero_runs = ?,
                    is_dead = ?,
                    last_tested_at = ?
                WHERE node_id = ?;
                """,
                (
                    rank,
                    speed_mbps,
                    new_zero_runs,
                    int(is_dead),
                    now,
                    node_id,
                ),
            )
            return (not already_dead) and is_dead

    def get_active_nodes(self) -> List[NodeRecord]:
        """Retrieve all nodes that are not marked dead."""
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                SELECT * FROM nodes
                WHERE is_dead = 0
                ORDER BY cumulative_score DESC, current_tournament_rank ASC;
                """
            )
            results = []
            for row in cur.fetchall():
                results.append(
                    NodeRecord(
                        node_id=row["node_id"],
                        raw_uri=row["raw_uri"],
                        seq_id=row["seq_id"] if ("seq_id" in row.keys() and row["seq_id"] is not None) else 0,
                        protocol=row["protocol"],
                        server_address=row["server_address"],
                        port=row["port"],
                        exit_ip=row["exit_ip"] or "",
                        geo_country=row["geo_country"] or "",
                        isp=row["isp"] or "",
                        google_country=row["google_country"] or "",
                        is_google_bad=bool(row["is_google_bad"]),
                        http_latency_ms=row["http_latency_ms"],
                        last_speed_mbps=row["last_speed_mbps"],
                        cumulative_score=row["cumulative_score"] or 0,
                        current_tournament_rank=row["current_tournament_rank"] or 0,
                        consecutive_zero_runs=row["consecutive_zero_runs"] or 0,
                        is_dead=bool(row["is_dead"]),
                        first_seen_at=row["first_seen_at"],
                        last_tested_at=row["last_tested_at"],
                    )
                )
            return results
