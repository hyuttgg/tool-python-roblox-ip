from enum import Enum
import socket
import time
from typing import List, Dict, Tuple
from config.settings import LATENCY_GOOD_MS, LATENCY_WARN_MS, PACKET_LOSS_WARN_PCT

class HealthState(str, Enum):
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"

class HealthEvaluator:
    @staticmethod
    def evaluate(latency_ms: float, packet_loss_pct: float) -> HealthState:
        if latency_ms < 0 or packet_loss_pct >= 100.0:
            return HealthState.OFFLINE
        if latency_ms > LATENCY_WARN_MS or packet_loss_pct > PACKET_LOSS_WARN_PCT:
            return HealthState.DEGRADED
        return HealthState.ONLINE

class NetworkInspector:
    """Đo lường kiểm tra độ trễ mạng và trạng thái kết nối IP Proxy"""

    @classmethod
    def probe_ip(cls, host: str, port: int = 80, timeout: float = 1.0) -> Tuple[str, int, str]:
        start = time.time()
        try:
            with socket.create_connection((host, int(port)), timeout=timeout):
                latency = int((time.time() - start) * 1000)
                color = "GREEN" if latency < 100 else ("YELLOW" if latency < 250 else "RED")
                return "READY", latency, color
        except Exception:
            return "TIMEOUT", 999, "RED"

    @classmethod
    def batch_probe_ips(cls, ip_list: List[str]) -> Dict[str, Tuple[str, int, str]]:
        result = {}
        for item in ip_list:
            parts = item.split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 80
            result[item] = cls.probe_ip(host, port)
        return result
