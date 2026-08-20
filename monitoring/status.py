from enum import Enum
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
