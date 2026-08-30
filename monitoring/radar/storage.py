# -*- coding: utf-8 -*-
"""
Radar Storage — Repository luu tru telemetry va su kien radar vao SQLite.
"""

import time
from typing import List, Dict, Optional
from config.logging import setup_logger

logger = setup_logger("radar_storage")


# SQL tao bang — se duoc goi tu init_radar_tables()
CREATE_TELEMETRY_TABLE = """
CREATE TABLE IF NOT EXISTS radar_telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_id TEXT NOT NULL,
    platform TEXT,
    pid INTEGER,
    cpu_percent REAL,
    memory_mb REAL,
    fps INTEGER,
    ping_ms REAL,
    anomaly_score INTEGER,
    severity TEXT,
    state TEXT,
    filtered_cpu REAL,
    filtered_ram REAL,
    filtered_ping REAL,
    filtered_fps REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS radar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT,
    anomaly_score INTEGER,
    details TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""


class RadarStorage:
    """Repository cho radar telemetry va event data."""

    def __init__(self):
        self._db = None
        self._initialized = False

    def _get_db(self):
        """Lazy-load database connection."""
        if self._db is None:
            try:
                from database.sqlite import db
                self._db = db
            except Exception as e:
                logger.warning(f"Khong the ket noi database: {e}")
        return self._db

    def init_tables(self) -> bool:
        """Tao cac bang radar neu chua ton tai."""
        db = self._get_db()
        if not db:
            return False

        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(CREATE_TELEMETRY_TABLE)
                cursor.execute(CREATE_EVENTS_TABLE)
            self._initialized = True
            logger.info("Radar database tables initialized.")
            return True
        except Exception as e:
            logger.error(f"Loi khoi tao radar tables: {e}")
            return False

    def save_telemetry(self, tag_id: str, platform: str, pid: int,
                       cpu: float, memory_mb: float, fps: int, ping_ms: float,
                       anomaly_score: int, severity: str, state: str,
                       filtered_cpu: float, filtered_ram: float,
                       filtered_ping: float, filtered_fps: float) -> bool:
        """Luu 1 mau telemetry vao database."""
        db = self._get_db()
        if not db:
            return False

        try:
            with db.get_connection() as conn:
                conn.execute(
                    """INSERT INTO radar_telemetry
                       (tag_id, platform, pid, cpu_percent, memory_mb, fps, ping_ms,
                        anomaly_score, severity, state, filtered_cpu, filtered_ram,
                        filtered_ping, filtered_fps)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (tag_id, platform, pid, cpu, memory_mb, fps, ping_ms,
                     anomaly_score, severity, state, filtered_cpu, filtered_ram,
                     filtered_ping, filtered_fps)
                )
            return True
        except Exception as e:
            logger.debug(f"Loi luu telemetry: {e}")
            return False

    def save_event(self, tag_id: str, event_type: str,
                   from_state: str, to_state: str,
                   anomaly_score: int, details: str) -> bool:
        """Luu 1 su kien radar (chuyen trang thai, canh bao)."""
        db = self._get_db()
        if not db:
            return False

        try:
            with db.get_connection() as conn:
                conn.execute(
                    """INSERT INTO radar_events
                       (tag_id, event_type, from_state, to_state, anomaly_score, details)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (tag_id, event_type, from_state, to_state, anomaly_score, details)
                )
            return True
        except Exception as e:
            logger.debug(f"Loi luu radar event: {e}")
            return False

    def get_telemetry_history(self, tag_id: str, limit: int = 100) -> List[Dict]:
        """Lay lich su telemetry cua 1 tag."""
        db = self._get_db()
        if not db:
            return []

        try:
            with db.get_connection() as conn:
                cursor = conn.execute(
                    """SELECT * FROM radar_telemetry
                       WHERE tag_id = ?
                       ORDER BY id DESC LIMIT ?""",
                    (tag_id, limit)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.debug(f"Loi doc telemetry history: {e}")
            return []

    def get_events(self, tag_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Lay danh sach su kien radar."""
        db = self._get_db()
        if not db:
            return []

        try:
            with db.get_connection() as conn:
                if tag_id:
                    cursor = conn.execute(
                        """SELECT * FROM radar_events
                           WHERE tag_id = ?
                           ORDER BY id DESC LIMIT ?""",
                        (tag_id, limit)
                    )
                else:
                    cursor = conn.execute(
                        """SELECT * FROM radar_events
                           ORDER BY id DESC LIMIT ?""",
                        (limit,)
                    )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.debug(f"Loi doc radar events: {e}")
            return []

    def cleanup_old(self, days: int = 7) -> int:
        """Xoa du lieu cu hon N ngay."""
        db = self._get_db()
        if not db:
            return 0

        deleted = 0
        try:
            with db.get_connection() as conn:
                cursor = conn.execute(
                    """DELETE FROM radar_telemetry
                       WHERE timestamp < datetime('now', ?)""",
                    (f"-{days} days",)
                )
                deleted += cursor.rowcount
                cursor = conn.execute(
                    """DELETE FROM radar_events
                       WHERE timestamp < datetime('now', ?)""",
                    (f"-{days} days",)
                )
                deleted += cursor.rowcount
            if deleted > 0:
                logger.info(f"Radar cleanup: da xoa {deleted} ban ghi cu hon {days} ngay.")
        except Exception as e:
            logger.debug(f"Loi cleanup radar data: {e}")

        return deleted
