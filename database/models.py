from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class InstanceModel:
    id: str
    name: str
    device_type: str
    region: str
    interface: str
    assigned_profile: Optional[str]
    status: str = "OFFLINE"
    last_seen: Optional[datetime] = None

@dataclass
class NetworkSnapshotModel:
    id: Optional[int]
    instance_id: str
    region: str
    public_ip: Optional[str]
    local_ip: Optional[str]
    interface: str
    latency_ms: float
    packet_loss_pct: float
    dns_response_ms: float
    status: str
    timestamp: Optional[datetime] = None
