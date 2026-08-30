# -*- coding: utf-8 -*-
"""
Radar Signal Processing Filters
Ba bo loc tin hieu hoat dong song song tren moi Tag Roblox:
  1. KalmanFilter  — Lam muot telemetry (CPU, RAM, Ping, FPS)
  2. CFARDetector  — Phat hien bat thuong kieu radar (Constant False Alarm Rate)
  3. MTIFilter     — Phat hien thay doi trang thai (Moving Target Indicator)
"""

from collections import deque
import math
from typing import Tuple, Dict, Optional


class KalmanFilter:
    """
    Bo loc Kalman 1 chieu don gian cho lam muot telemetry.

    Loai bo spike don le (VD: ping nhay 42 -> 300 -> 45, Kalman giu ~50).
    Moi metric (cpu, ram, ping, fps) co KalmanFilter rieng.

    Tham so:
        process_noise (q): Do nhieu he thong — cang nho cang muot
        measurement_noise (r): Do nhieu phep do — cang lon cang it tin mau moi
    """

    def __init__(self, process_noise: float = 0.01, measurement_noise: float = 1.0):
        self.q = process_noise
        self.r = measurement_noise
        self.x: Optional[float] = None  # Estimated state
        self.p: float = 1.0             # Estimation error covariance

    def update(self, measurement: float) -> float:
        """Cap nhat voi phep do moi, tra ve gia tri da loc."""
        if self.x is None:
            self.x = measurement
            return self.x

        # Prediction step
        self.p += self.q

        # Update step
        k = self.p / (self.p + self.r)          # Kalman gain
        self.x += k * (measurement - self.x)    # State update
        self.p *= (1.0 - k)                     # Covariance update

        return self.x

    def reset(self) -> None:
        """Reset bo loc ve trang thai ban dau."""
        self.x = None
        self.p = 1.0

    @property
    def current_value(self) -> Optional[float]:
        return self.x


class CFARDetector:
    """
    Bo phat hien bat thuong kieu CFAR (Constant False Alarm Rate).

    Sliding window lay mean + std cua N mau xung quanh.
    Threshold = mean + multiplier x max(std, noise_floor)
    guard_cells bo qua mau lien ke (dung chuan CFAR radar).

    Khi gia tri vuot threshold -> ANOMALY.
    """

    def __init__(self, window_size: int = 20, guard_cells: int = 2, multiplier: float = 3.0,
                 noise_floor: float = 1.0):
        self.window_size = window_size
        self.guard_cells = guard_cells
        self.multiplier = multiplier
        self.noise_floor = noise_floor
        self._values: deque = deque(maxlen=window_size + guard_cells * 2)
        self._anomaly_count: int = 0
        self._total_count: int = 0

    def update(self, value: float) -> Tuple[bool, float]:
        """
        Cap nhat voi gia tri moi.
        Tra ve (is_anomaly, threshold).
        """
        self._total_count += 1

        # Chua du du lieu de phan tich
        min_required = self.guard_cells * 2 + 3
        if len(self._values) < min_required:
            self._values.append(value)
            return False, 0.0

        # Lay cac mau tham chieu (bo qua guard cells gan nhat)
        ref_values = list(self._values)
        if self.guard_cells > 0 and len(ref_values) > self.guard_cells:
            ref_values = ref_values[:-self.guard_cells]

        if not ref_values:
            self._values.append(value)
            return False, 0.0

        # Tinh mean va std
        n = len(ref_values)
        mean = sum(ref_values) / n
        variance = sum((v - mean) ** 2 for v in ref_values) / n
        std = math.sqrt(variance)

        # Threshold = mean + multiplier * max(std, noise_floor)
        threshold = mean + self.multiplier * max(std, self.noise_floor)

        is_anomaly = value > threshold

        if is_anomaly:
            self._anomaly_count += 1

        self._values.append(value)
        return is_anomaly, threshold

    def get_stats(self) -> Dict:
        """Tra ve thong ke hien tai cua bo phat hien."""
        values = list(self._values)
        if not values:
            return {"count": 0, "mean": 0, "std": 0, "anomalies": 0}

        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        std = math.sqrt(variance)

        return {
            "count": self._total_count,
            "window_size": n,
            "mean": round(mean, 2),
            "std": round(std, 2),
            "anomalies": self._anomaly_count,
            "anomaly_rate": round(self._anomaly_count / max(self._total_count, 1), 4),
        }

    def reset(self) -> None:
        self._values.clear()
        self._anomaly_count = 0
        self._total_count = 0


class MTIFilter:
    """
    Bo loc Moving Target Indicator (MTI) — phat hien thay doi trang thai.

    Su dung EMA (Exponential Moving Average) de lam muot delta giua cac mau lien tiep.
    Neu delta lon -> "muc tieu di chuyen" = trang thai dang thay doi.

    Vi du: CPU tu 30 -> 95 = MTI delta cao -> tin hieu canh bao.

    Tham so:
        alpha: He so lam muot EMA (0 < alpha < 1). Cang lon cang nhay voi thay doi.
    """

    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self._prev_value: Optional[float] = None
        self._ema_delta: float = 0.0

    def update(self, value: float) -> float:
        """
        Cap nhat voi gia tri moi.
        Tra ve do lon thay doi da lam muot (EMA delta magnitude).
        """
        if self._prev_value is None:
            self._prev_value = value
            return 0.0

        raw_delta = abs(value - self._prev_value)
        self._ema_delta = self.alpha * raw_delta + (1.0 - self.alpha) * self._ema_delta
        self._prev_value = value

        return self._ema_delta

    @property
    def current_delta(self) -> float:
        return self._ema_delta

    def reset(self) -> None:
        self._prev_value = None
        self._ema_delta = 0.0


class FilterBank:
    """
    Ngan hang bo loc cho 1 Tag Roblox.
    Moi Tag co 4 kenh Kalman + 4 kenh CFAR + 4 kenh MTI cho (cpu, ram, ping, fps).
    """

    CHANNELS = ("cpu", "ram", "ping", "fps")

    def __init__(self, kalman_q: float = 0.01, kalman_r: float = 1.0,
                 cfar_window: int = 20, cfar_guard: int = 2, cfar_multiplier: float = 3.0,
                 mti_alpha: float = 0.3):
        self.kalman: Dict[str, KalmanFilter] = {}
        self.cfar: Dict[str, CFARDetector] = {}
        self.mti: Dict[str, MTIFilter] = {}

        for ch in self.CHANNELS:
            self.kalman[ch] = KalmanFilter(process_noise=kalman_q, measurement_noise=kalman_r)
            self.cfar[ch] = CFARDetector(window_size=cfar_window, guard_cells=cfar_guard,
                                         multiplier=cfar_multiplier)
            self.mti[ch] = MTIFilter(alpha=mti_alpha)

    def process(self, cpu: float, ram: float, ping: float, fps: float) -> Dict:
        """
        Chay tat ca bo loc dong thoi cho 1 mau telemetry.
        Tra ve dict voi gia tri da loc, anomaly flags, va MTI deltas.
        """
        raw = {"cpu": cpu, "ram": ram, "ping": ping, "fps": fps}
        result = {}

        for ch in self.CHANNELS:
            v = raw[ch]
            filtered = self.kalman[ch].update(v)
            is_anomaly, threshold = self.cfar[ch].update(v)
            mti_delta = self.mti[ch].update(v)

            result[ch] = {
                "raw": v,
                "filtered": round(filtered, 2),
                "cfar_anomaly": is_anomaly,
                "cfar_threshold": round(threshold, 2),
                "mti_delta": round(mti_delta, 2),
            }

        return result

    def reset_all(self) -> None:
        for ch in self.CHANNELS:
            self.kalman[ch].reset()
            self.cfar[ch].reset()
            self.mti[ch].reset()
