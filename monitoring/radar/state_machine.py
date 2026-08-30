# -*- coding: utf-8 -*-
"""
Radar State Machine
Quan ly trang thai cua tung Tag Roblox voi chuyen doi trang thai (state transitions)
dua tren anomaly score va tin hieu telemetry.
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from monitoring.radar.filters import KalmanFilter


class RobloxState(str, Enum):
    """Tat ca cac trang thai co the cua 1 Tag Roblox."""
    NOT_RUNNING  = "NOT_RUNNING"
    STARTING     = "STARTING"
    RUNNING      = "RUNNING"
    FROZEN       = "FROZEN"
    CRASHED      = "CRASHED"
    DISCONNECTED = "DISCONNECTED"
    APP_CHANGED  = "APP_CHANGED"
    SUSPICIOUS   = "SUSPICIOUS"
    UNKNOWN      = "UNKNOWN"


# Mapping trang thai -> icon hien thi
STATE_ICONS: Dict[str, str] = {
    "NOT_RUNNING":  "OFFLINE",
    "STARTING":     "LOADING",
    "RUNNING":      "ONLINE",
    "FROZEN":       "FROZEN",
    "CRASHED":      "CRASHED",
    "DISCONNECTED": "DISCONNECTED",
    "APP_CHANGED":  "MODIFIED",
    "SUSPICIOUS":   "WARNING",
    "UNKNOWN":      "UNKNOWN",
}


@dataclass
class StateTransition:
    """Ban ghi chuyen doi trang thai."""
    from_state: str
    to_state: str
    reason: str
    anomaly_score: int
    timestamp: float = field(default_factory=time.time)


class StateTracker:
    """
    Bo theo doi trang thai cho 1 Tag Roblox.
    Su dung Kalman filter tren anomaly score de lam muot quyet dinh chuyen doi.
    Giu lich su chuyen doi de audit.
    """

    # Nguong de chuyen doi trang thai
    SCORE_WARNING_ENTER: int = 20
    SCORE_SUSPICIOUS_ENTER: int = 40
    SCORE_CRITICAL_ENTER: int = 70
    SCORE_NORMAL_EXIT: int = 15       # Score phai giam duoi muc nay de tro lai RUNNING

    # So chu ky STARTING truoc khi chuyen sang RUNNING
    STARTING_STABLE_CYCLES: int = 3

    def __init__(self, tag_id: str):
        self.tag_id = tag_id
        self.state = RobloxState.NOT_RUNNING
        self.previous_state = RobloxState.NOT_RUNNING

        # Kalman tren anomaly score
        self._score_kalman = KalmanFilter(process_noise=0.1, measurement_noise=2.0)
        self._smoothed_score: float = 0.0

        # Counter cho STARTING
        self._starting_cycles: int = 0

        # Counter cho FROZEN
        self._frozen_cycles: int = 0
        self.FROZEN_TRIGGER_CYCLES: int = 5

        # Lich su
        self.transitions: List[StateTransition] = []
        self.max_history: int = 50

    @property
    def smoothed_score(self) -> float:
        return self._smoothed_score

    def update(self, process_alive: bool, anomaly_score: int,
               triggered_signals: List[str], severity: str) -> RobloxState:
        """
        Cap nhat trang thai dua tren tin hieu moi.

        Args:
            process_alive: Process Roblox con song hay khong
            anomaly_score: Diem bat thuong tu AnomalyScorer
            triggered_signals: Danh sach tin hieu da kich hoat
            severity: Muc do nghiem trong (NORMAL/WARNING/SUSPICIOUS/CRITICAL)

        Returns:
            Trang thai moi cua Tag
        """
        # Lam muot score bang Kalman
        self._smoothed_score = self._score_kalman.update(float(anomaly_score))
        effective_score = int(self._smoothed_score)

        old_state = self.state
        new_state = self._compute_transition(
            process_alive=process_alive,
            score=effective_score,
            signals=triggered_signals,
            severity=severity,
        )

        if new_state != old_state:
            reason = self._build_reason(old_state, new_state, triggered_signals, effective_score)
            transition = StateTransition(
                from_state=old_state.value,
                to_state=new_state.value,
                reason=reason,
                anomaly_score=effective_score,
            )
            self.transitions.append(transition)
            if len(self.transitions) > self.max_history:
                self.transitions.pop(0)

            self.previous_state = old_state
            self.state = new_state

        return self.state

    def _compute_transition(self, process_alive: bool, score: int,
                            signals: List[str], severity: str) -> RobloxState:
        """Logic chuyen doi trang thai chinh."""

        current = self.state

        # --- Process khong ton tai ---
        if not process_alive:
            self._starting_cycles = 0
            self._frozen_cycles = 0

            if current in (RobloxState.RUNNING, RobloxState.FROZEN,
                           RobloxState.SUSPICIOUS, RobloxState.DISCONNECTED):
                # Dang chay ma bien mat -> CRASHED
                return RobloxState.CRASHED
            # Da biet la OFF
            return RobloxState.NOT_RUNNING

        # --- Process ton tai ---

        # NOT_RUNNING -> STARTING (vua phat hien process)
        if current == RobloxState.NOT_RUNNING:
            self._starting_cycles = 0
            return RobloxState.STARTING

        # CRASHED -> STARTING (process xuat hien lai)
        if current == RobloxState.CRASHED:
            self._starting_cycles = 0
            return RobloxState.STARTING

        # STARTING -> RUNNING (du so chu ky on dinh)
        if current == RobloxState.STARTING:
            if score < self.SCORE_WARNING_ENTER:
                self._starting_cycles += 1
            else:
                self._starting_cycles = 0

            if self._starting_cycles >= self.STARTING_STABLE_CYCLES:
                self._starting_cycles = 0
                return RobloxState.RUNNING
            return RobloxState.STARTING

        # --- Dang RUNNING ---
        if current == RobloxState.RUNNING:
            self._frozen_cycles = 0

            if "log_disconnect" in signals:
                return RobloxState.DISCONNECTED

            if "process_hung" in signals:
                return RobloxState.FROZEN

            if score >= self.SCORE_SUSPICIOUS_ENTER:
                return RobloxState.SUSPICIOUS

            return RobloxState.RUNNING

        # --- Dang FROZEN ---
        if current == RobloxState.FROZEN:
            if "process_hung" not in signals and score < self.SCORE_WARNING_ENTER:
                # Phuc hoi
                return RobloxState.RUNNING
            self._frozen_cycles += 1
            return RobloxState.FROZEN

        # --- Dang DISCONNECTED ---
        if current == RobloxState.DISCONNECTED:
            if "log_disconnect" not in signals and "network_timeout" not in signals:
                if score < self.SCORE_WARNING_ENTER:
                    return RobloxState.RUNNING
            return RobloxState.DISCONNECTED

        # --- Dang SUSPICIOUS ---
        if current == RobloxState.SUSPICIOUS:
            if "log_disconnect" in signals:
                return RobloxState.DISCONNECTED

            if "process_hung" in signals:
                return RobloxState.FROZEN

            if score < self.SCORE_NORMAL_EXIT:
                return RobloxState.RUNNING

            return RobloxState.SUSPICIOUS

        # --- APP_CHANGED ---
        if current == RobloxState.APP_CHANGED:
            if "file_modified" not in signals:
                return RobloxState.RUNNING
            return RobloxState.APP_CHANGED

        return current

    def _build_reason(self, old: RobloxState, new: RobloxState,
                      signals: List[str], score: int) -> str:
        """Tao chuoi ly do cho chuyen doi trang thai."""
        signal_str = ", ".join(signals[:3]) if signals else "score_change"
        return f"{old.value}->{new.value} (score={score}, signals=[{signal_str}])"

    def force_state(self, new_state: RobloxState, reason: str = "Manual override") -> None:
        """Ep chuyen trang thai thu cong (debug/admin)."""
        old = self.state
        self.state = new_state
        self.previous_state = old
        self.transitions.append(StateTransition(
            from_state=old.value,
            to_state=new_state.value,
            reason=reason,
            anomaly_score=int(self._smoothed_score),
        ))

    def get_recent_transitions(self, count: int = 10) -> List[StateTransition]:
        """Tra ve N chuyen doi gan nhat."""
        return list(self.transitions[-count:])

    def reset(self) -> None:
        """Reset ve trang thai ban dau."""
        self.state = RobloxState.NOT_RUNNING
        self.previous_state = RobloxState.NOT_RUNNING
        self._score_kalman.reset()
        self._smoothed_score = 0.0
        self._starting_cycles = 0
        self._frozen_cycles = 0
        self.transitions.clear()
