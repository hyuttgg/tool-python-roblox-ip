# -*- coding: utf-8 -*-
"""
Radar Anomaly Scorer
Ket hop tin hieu tu Kalman + CFAR + MTI thanh anomaly score duy nhat.
Diem so quyet dinh muc do nghiem trong cua tung Tag Roblox.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# Bang trong so diem bat thuong
SCORE_WEIGHTS: Dict[str, int] = {
    "cpu_spike": 20,          # CFAR anomaly tren CPU
    "ram_spike": 15,          # CFAR anomaly tren RAM
    "ping_spike": 15,         # CFAR anomaly tren Ping
    "fps_zero": 30,           # FPS = 0 (man hinh dong bang)
    "fps_drop": 10,           # FPS giam manh (MTI delta cao)
    "process_hung": 40,       # Process ton tai nhung CPU ~ 0
    "process_dead": 50,       # Process bien mat bat thuong
    "network_timeout": 20,    # Ping > 999ms hoac mat ket noi
    "log_disconnect": 45,     # Roblox log bao mat ket noi
    "file_modified": 10,      # File integrity thay doi
    "high_mti_cpu": 12,       # MTI delta CPU cao bat thuong
    "high_mti_ram": 8,        # MTI delta RAM cao bat thuong
}

# Muc do nghiem trong
SEVERITY_THRESHOLDS: List[Tuple[int, int, str]] = [
    (0,  19,  "NORMAL"),
    (20, 39,  "WARNING"),
    (40, 69,  "SUSPICIOUS"),
    (70, 999, "CRITICAL"),
]


@dataclass
class AnomalyResult:
    """Ket qua phan tich bat thuong cho 1 chu ky radar."""
    score: int = 0
    severity: str = "NORMAL"
    triggered_signals: List[str] = field(default_factory=list)
    details: Dict[str, float] = field(default_factory=dict)

    def __str__(self) -> str:
        signals_str = ", ".join(self.triggered_signals) if self.triggered_signals else "none"
        return f"Score={self.score} [{self.severity}] signals=[{signals_str}]"


def _score_to_severity(score: int) -> str:
    """Chuyen diem thanh muc do nghiem trong."""
    for low, high, label in SEVERITY_THRESHOLDS:
        if low <= score <= high:
            return label
    return "CRITICAL"


class AnomalyScorer:
    """
    Bo tinh diem bat thuong tong hop.
    Nhan filter_result (tu FilterBank.process) + cac tin hieu bo sung
    -> tra ve AnomalyResult voi score + severity + triggered signals.
    """

    def __init__(self, weights: Optional[Dict[str, int]] = None):
        self.weights = weights or SCORE_WEIGHTS.copy()

        # Nguong MTI de coi la "cao"
        self.mti_cpu_threshold: float = 15.0
        self.mti_ram_threshold: float = 50.0
        self.fps_drop_mti_threshold: float = 10.0

        # Nguong "process hung" — CPU cuc thap + RAM cao
        self.hung_cpu_max: float = 0.5
        self.hung_ram_min: float = 300.0
        self.hung_consecutive: int = 0
        self.hung_trigger_count: int = 5  # Can 5 mau lien tiep

        # Nguong ping timeout
        self.ping_timeout_ms: float = 999.0

    def evaluate(self, filter_result: Dict, process_alive: bool = True,
                 log_disconnect: bool = False, file_modified: bool = False) -> AnomalyResult:
        """
        Danh gia bat thuong tu ket qua filter.

        Args:
            filter_result: Output cua FilterBank.process() voi keys: cpu, ram, ping, fps
            process_alive: Process Roblox con song hay khong
            log_disconnect: Co phat hien disconnect trong log khong
            file_modified: File integrity co thay doi khong

        Returns:
            AnomalyResult voi score tich luy, severity va danh sach tin hieu
        """
        score = 0
        signals: List[str] = []
        details: Dict[str, float] = {}

        cpu_data = filter_result.get("cpu", {})
        ram_data = filter_result.get("ram", {})
        ping_data = filter_result.get("ping", {})
        fps_data = filter_result.get("fps", {})

        # --- CFAR anomalies ---
        if cpu_data.get("cfar_anomaly", False):
            score += self.weights.get("cpu_spike", 20)
            signals.append("cpu_spike")
            details["cpu_raw"] = cpu_data.get("raw", 0)

        if ram_data.get("cfar_anomaly", False):
            score += self.weights.get("ram_spike", 15)
            signals.append("ram_spike")
            details["ram_raw"] = ram_data.get("raw", 0)

        if ping_data.get("cfar_anomaly", False):
            score += self.weights.get("ping_spike", 15)
            signals.append("ping_spike")
            details["ping_raw"] = ping_data.get("raw", 0)

        # --- FPS zero ---
        fps_raw = fps_data.get("raw", 60)
        if fps_raw <= 0:
            score += self.weights.get("fps_zero", 30)
            signals.append("fps_zero")

        # --- FPS drop (MTI) ---
        fps_mti = fps_data.get("mti_delta", 0)
        if fps_mti > self.fps_drop_mti_threshold:
            score += self.weights.get("fps_drop", 10)
            signals.append("fps_drop")
            details["fps_mti_delta"] = fps_mti

        # --- MTI high deltas ---
        cpu_mti = cpu_data.get("mti_delta", 0)
        if cpu_mti > self.mti_cpu_threshold:
            score += self.weights.get("high_mti_cpu", 12)
            signals.append("high_mti_cpu")
            details["cpu_mti_delta"] = cpu_mti

        ram_mti = ram_data.get("mti_delta", 0)
        if ram_mti > self.mti_ram_threshold:
            score += self.weights.get("high_mti_ram", 8)
            signals.append("high_mti_ram")
            details["ram_mti_delta"] = ram_mti

        # --- Process hung detection ---
        cpu_filtered = cpu_data.get("filtered", 50)
        ram_filtered = ram_data.get("filtered", 0)
        if process_alive and cpu_filtered < self.hung_cpu_max and ram_filtered > self.hung_ram_min:
            self.hung_consecutive += 1
        else:
            self.hung_consecutive = 0

        if self.hung_consecutive >= self.hung_trigger_count:
            score += self.weights.get("process_hung", 40)
            signals.append("process_hung")
            details["hung_cycles"] = self.hung_consecutive

        # --- Process dead ---
        if not process_alive:
            score += self.weights.get("process_dead", 50)
            signals.append("process_dead")
            self.hung_consecutive = 0

        # --- Network timeout ---
        ping_raw = ping_data.get("raw", 0)
        if ping_raw >= self.ping_timeout_ms:
            score += self.weights.get("network_timeout", 20)
            signals.append("network_timeout")

        # --- Log disconnect ---
        if log_disconnect:
            score += self.weights.get("log_disconnect", 45)
            signals.append("log_disconnect")

        # --- File integrity ---
        if file_modified:
            score += self.weights.get("file_modified", 10)
            signals.append("file_modified")

        severity = _score_to_severity(score)

        return AnomalyResult(
            score=score,
            severity=severity,
            triggered_signals=signals,
            details=details,
        )

    def reset(self) -> None:
        """Reset trang thai tich luy."""
        self.hung_consecutive = 0
