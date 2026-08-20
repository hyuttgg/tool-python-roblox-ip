import sqlite3
from contextlib import contextmanager
from typing import Generator
from config.settings import DB_PATH
from config.logging import setup_logger

logger = setup_logger("database")

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)
        self.init_db()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS instances (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    region TEXT DEFAULT 'GLOBAL',
                    interface TEXT NOT NULL,
                    assigned_profile TEXT,
                    status TEXT DEFAULT 'OFFLINE',
                    last_seen DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Migration check: nếu bảng cũ chưa có cột region thì ALTER TABLE
            cursor.execute("PRAGMA table_info(instances)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "region" not in columns:
                cursor.execute("ALTER TABLE instances ADD COLUMN region TEXT DEFAULT 'GLOBAL'")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS network_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_id TEXT NOT NULL,
                    region TEXT DEFAULT 'GLOBAL',
                    public_ip TEXT,
                    local_ip TEXT,
                    interface TEXT,
                    latency_ms REAL,
                    packet_loss_pct REAL,
                    dns_response_ms REAL,
                    status TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (instance_id) REFERENCES instances (id)
                )
            """)
            cursor.execute("PRAGMA table_info(network_snapshots)")
            snapshot_cols = [row["name"] for row in cursor.fetchall()]
            if "region" not in snapshot_cols:
                cursor.execute("ALTER TABLE network_snapshots ADD COLUMN region TEXT DEFAULT 'GLOBAL'")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Database schema initialized and migrated successfully.")

db = Database()
