from typing import List, Optional
from database.sqlite import db
from database.models import InstanceModel, NetworkSnapshotModel
from datetime import datetime

class InstanceRepository:
    @staticmethod
    def upsert_instance(instance: InstanceModel) -> None:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO instances (id, name, device_type, region, interface, assigned_profile, status, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    device_type = excluded.device_type,
                    region = excluded.region,
                    interface = excluded.interface,
                    assigned_profile = excluded.assigned_profile,
                    status = excluded.status,
                    last_seen = excluded.last_seen
            """, (
                instance.id,
                instance.name,
                instance.device_type,
                instance.region,
                instance.interface,
                instance.assigned_profile,
                instance.status,
                datetime.utcnow().isoformat()
            ))

    @staticmethod
    def get_all_instances() -> List[InstanceModel]:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM instances ORDER BY id")
            rows = cursor.fetchall()
            return [
                InstanceModel(
                    id=row["id"],
                    name=row["name"],
                    device_type=row["device_type"],
                    region=row["region"] if "region" in row.keys() else "GLOBAL",
                    interface=row["interface"],
                    assigned_profile=row["assigned_profile"],
                    status=row["status"],
                    last_seen=row["last_seen"]
                ) for row in rows
            ]

class SnapshotRepository:
    @staticmethod
    def save_snapshot(snapshot: NetworkSnapshotModel) -> None:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO network_snapshots (
                    instance_id, region, public_ip, local_ip, interface,
                    latency_ms, packet_loss_pct, dns_response_ms, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot.instance_id,
                snapshot.region,
                snapshot.public_ip,
                snapshot.local_ip,
                snapshot.interface,
                snapshot.latency_ms,
                snapshot.packet_loss_pct,
                snapshot.dns_response_ms,
                snapshot.status
            ))

    @staticmethod
    def get_latest_snapshot(instance_id: str) -> Optional[NetworkSnapshotModel]:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM network_snapshots
                WHERE instance_id = ?
                ORDER BY id DESC LIMIT 1
            """, (instance_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return NetworkSnapshotModel(
                id=row["id"],
                instance_id=row["instance_id"],
                region=row["region"] if "region" in row.keys() else "GLOBAL",
                public_ip=row["public_ip"],
                local_ip=row["local_ip"],
                interface=row["interface"],
                latency_ms=row["latency_ms"],
                packet_loss_pct=row["packet_loss_pct"],
                dns_response_ms=row["dns_response_ms"],
                status=row["status"],
                timestamp=row["timestamp"]
            )
