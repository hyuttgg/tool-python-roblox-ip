# -*- coding: utf-8 -*-
"""
Radar Engine — Pipeline Orchestrator
Pipeline chinh: Collect -> Filter -> Detect -> Track -> Store
Chay daemon thread giam sat tat ca Tag Roblox.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from config.logging import setup_logger

from monitoring.radar.filters import FilterBank
from monitoring.radar.anomaly_scorer import AnomalyScorer, AnomalyResult
from monitoring.radar.state_machine import RobloxState, StateTracker
from monitoring.radar.telemetry import TelemetrySnapshot, WindowsCollector, AndroidCollector
from monitoring.radar.storage import RadarStorage
from monitoring.radar.integrity import IntegrityMonitor

logger = setup_logger("radar_engine")


@dataclass
class RadarTagConfig:
    """Cau hinh cho 1 Tag trong Radar Engine."""
    tag_id: str
    pid: int = 0
    device_id: str = ""        # ADB device ID (cho Android)
    platform: str = "WINDOWS"  # "WINDOWS" | "ANDROID"
    heartbeat_data: Optional[Dict] = None


@dataclass
class RadarTagReport:
    """Bao cao trang thai tong hop cho 1 Tag."""
    tag_id: str = ""
    state: str = "NOT_RUNNING"
    anomaly_score: int = 0
    severity: str = "NORMAL"
    smoothed_score: float = 0.0
    # Kalman-filtered metrics
    filtered_cpu: float = 0.0
    filtered_ram: float = 0.0
    filtered_ping: float = 0.0
    filtered_fps: float = 0.0
    # Raw metrics
    raw_cpu: float = 0.0
    raw_ram: float = 0.0
    raw_ping: float = 0.0
    raw_fps: int = 0
    # Process info
    pid: int = 0
    platform: str = "WINDOWS"
    process_alive: bool = False
    uptime_sec: float = 0.0
    thread_count: int = 0
    # Last update
    last_update: float = 0.0
    # State history
    state_history: List[Dict] = field(default_factory=list)
    # Triggered signals
    triggered_signals: List[str] = field(default_factory=list)


class RadarEngine:
    """
    Pipeline chinh cua he thong Radar Monitor.

    Moi cycle:
    1. Collect telemetry cho tung tag
    2. Kalman filter smooth
    3. CFAR anomaly check
    4. MTI change detection
    5. Anomaly score
    6. State machine transition
    7. Store to DB
    8. Emit alerts neu CRITICAL
    """

    def __init__(self, scan_interval: float = 2.0):
        self.scan_interval = scan_interval

        # Tag registry
        self._tags: Dict[str, RadarTagConfig] = {}
        self._lock = threading.RLock()

        # Per-tag components
        self._filter_banks: Dict[str, FilterBank] = {}
        self._scorers: Dict[str, AnomalyScorer] = {}
        self._trackers: Dict[str, StateTracker] = {}
        self._latest_reports: Dict[str, RadarTagReport] = {}
        self._latest_snapshots: Dict[str, TelemetrySnapshot] = {}
        self._telemetry_history: Dict[str, List[TelemetrySnapshot]] = {}

        # Collectors
        self._win_collector = WindowsCollector()
        self._android_collector = AndroidCollector()

        # Storage
        self._storage = RadarStorage()

        # Integrity
        self._integrity = IntegrityMonitor()
        self._last_integrity_check: float = 0
        self._integrity_check_interval: float = 300.0  # Kiem tra moi 5 phut
        self._integrity_mismatch: bool = False

        # Log monitor
        self._log_monitor = None
        try:
            from core.roblox_log_monitor import roblox_log_monitor
            self._log_monitor = roblox_log_monitor
        except Exception:
            pass

        # Daemon thread
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cycle_count: int = 0
        self._start_time: float = 0

        # Event callbacks
        self._on_state_change_callbacks: List = []

    # ------------------------------------------------------------------
    # Tag Management
    # ------------------------------------------------------------------

    def register_tag(self, tag_id: str, pid: int = 0,
                     device_id: str = "", platform: str = "WINDOWS") -> None:
        """Dang ky 1 Tag de giam sat."""
        with self._lock:
            config = RadarTagConfig(
                tag_id=tag_id,
                pid=pid,
                device_id=device_id,
                platform=platform,
            )
            self._tags[tag_id] = config
            self._filter_banks[tag_id] = FilterBank()
            self._scorers[tag_id] = AnomalyScorer()
            self._trackers[tag_id] = StateTracker(tag_id)
            self._latest_reports[tag_id] = RadarTagReport(tag_id=tag_id)
            self._telemetry_history[tag_id] = []

        logger.info(f"Radar: Registered tag [{tag_id}] (PID={pid}, platform={platform})")

    def unregister_tag(self, tag_id: str) -> None:
        """Huy dang ky 1 Tag."""
        with self._lock:
            self._tags.pop(tag_id, None)
            self._filter_banks.pop(tag_id, None)
            self._scorers.pop(tag_id, None)
            self._trackers.pop(tag_id, None)
            self._latest_reports.pop(tag_id, None)
            self._latest_snapshots.pop(tag_id, None)
            self._telemetry_history.pop(tag_id, None)

        logger.info(f"Radar: Unregistered tag [{tag_id}]")

    def update_tag_pid(self, tag_id: str, pid: int) -> None:
        """Cap nhat PID cho 1 Tag (sau restart)."""
        with self._lock:
            if tag_id in self._tags:
                self._tags[tag_id].pid = pid

    def update_heartbeat(self, tag_id: str, heartbeat_data: Dict) -> None:
        """Cap nhat du lieu heartbeat tu Lua cho 1 Tag."""
        with self._lock:
            if tag_id in self._tags:
                self._tags[tag_id].heartbeat_data = heartbeat_data

    # ------------------------------------------------------------------
    # State Queries
    # ------------------------------------------------------------------

    def get_tag_state(self, tag_id: str) -> RobloxState:
        """Lay trang thai hien tai cua 1 Tag."""
        with self._lock:
            tracker = self._trackers.get(tag_id)
            if tracker:
                return tracker.state
        return RobloxState.UNKNOWN

    def get_tag_report(self, tag_id: str) -> Optional[RadarTagReport]:
        """Lay bao cao day du cua 1 Tag."""
        with self._lock:
            report = self._latest_reports.get(tag_id)
            if report:
                # Copy to avoid race conditions
                return RadarTagReport(**{
                    k: (list(v) if isinstance(v, list) else v)
                    for k, v in report.__dict__.items()
                })
        return None

    def get_all_reports(self) -> Dict[str, RadarTagReport]:
        """Lay bao cao cua tat ca Tag."""
        with self._lock:
            return {
                tag_id: RadarTagReport(**{
                    k: (list(v) if isinstance(v, list) else v)
                    for k, v in report.__dict__.items()
                })
                for tag_id, report in self._latest_reports.items()
            }

    def get_telemetry_history(self, tag_id: str, limit: int = 100) -> List[TelemetrySnapshot]:
        """Lay lich su telemetry cua 1 Tag (in-memory)."""
        with self._lock:
            history = self._telemetry_history.get(tag_id, [])
            return list(history[-limit:])

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def uptime_sec(self) -> float:
        if self._start_time > 0:
            return time.time() - self._start_time
        return 0

    @property
    def tag_count(self) -> int:
        return len(self._tags)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Khoi dong Radar Engine daemon thread."""
        if self._running:
            return

        # Init database tables
        self._storage.init_tables()

        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._radar_loop, daemon=True, name="RadarEngine")
        self._thread.start()
        logger.info(f"Radar Engine started (interval={self.scan_interval}s)")

    def stop(self) -> None:
        """Dung Radar Engine."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        logger.info("Radar Engine stopped.")

    def on_state_change(self, callback) -> None:
        """Dang ky callback khi trang thai Tag thay doi."""
        self._on_state_change_callbacks.append(callback)

    # ------------------------------------------------------------------
    # Main Loop
    # ------------------------------------------------------------------

    def _radar_loop(self) -> None:
        """Vong lap chinh cua Radar Engine."""
        logger.info("Radar loop started.")

        while self._running:
            cycle_start = time.time()
            self._cycle_count += 1

            try:
                # Lay danh sach tag hien tai
                with self._lock:
                    tag_configs = list(self._tags.values())

                # Kiem tra integrity dinh ky
                self._periodic_integrity_check()

                # Kiem tra log disconnect
                log_disconnect = False
                if self._log_monitor:
                    try:
                        disconnect_marker = self._log_monitor.check_for_disconnect()
                        if disconnect_marker:
                            log_disconnect = True
                    except Exception:
                        pass

                # Xu ly tung tag
                for config in tag_configs:
                    try:
                        self._process_tag(config, log_disconnect)
                    except Exception as e:
                        logger.debug(f"Radar error processing [{config.tag_id}]: {e}")

            except Exception as e:
                logger.error(f"Radar loop error: {e}")

            # Sleep cho du interval
            elapsed = time.time() - cycle_start
            sleep_time = max(0.1, self.scan_interval - elapsed)
            time.sleep(sleep_time)

    def _process_tag(self, config: RadarTagConfig, log_disconnect: bool) -> None:
        """Xu ly 1 Tag trong 1 cycle radar."""
        tag_id = config.tag_id

        # --- 1. COLLECT ---
        if config.platform == "ANDROID":
            snapshot = self._android_collector.collect(
                tag_id=tag_id,
                device_id=config.device_id,
                heartbeat_data=config.heartbeat_data,
            )
        else:
            snapshot = self._win_collector.collect(
                tag_id=tag_id,
                pid=config.pid,
                heartbeat_data=config.heartbeat_data,
            )

        snapshot.log_disconnect_detected = log_disconnect

        # --- 2. FILTER ---
        with self._lock:
            filter_bank = self._filter_banks.get(tag_id)
            scorer = self._scorers.get(tag_id)
            tracker = self._trackers.get(tag_id)

        if not filter_bank or not scorer or not tracker:
            return

        # Su dung FPS tu heartbeat hoac tu snapshot
        fps_value = float(snapshot.fps or snapshot.in_game_ping or 0)
        ping_value = snapshot.ping_ms if snapshot.ping_ms > 0 else float(snapshot.in_game_ping)

        filter_result = filter_bank.process(
            cpu=snapshot.cpu_percent,
            ram=snapshot.memory_mb,
            ping=ping_value,
            fps=fps_value,
        )

        # --- 3. SCORE ---
        anomaly_result = scorer.evaluate(
            filter_result=filter_result,
            process_alive=snapshot.process_alive,
            log_disconnect=log_disconnect,
            file_modified=self._integrity_mismatch,
        )

        # --- 4. STATE TRANSITION ---
        old_state = tracker.state
        new_state = tracker.update(
            process_alive=snapshot.process_alive,
            anomaly_score=anomaly_result.score,
            triggered_signals=anomaly_result.triggered_signals,
            severity=anomaly_result.severity,
        )

        # --- 5. UPDATE REPORT ---
        cpu_data = filter_result.get("cpu", {})
        ram_data = filter_result.get("ram", {})
        ping_data = filter_result.get("ping", {})
        fps_data = filter_result.get("fps", {})

        report = RadarTagReport(
            tag_id=tag_id,
            state=new_state.value,
            anomaly_score=anomaly_result.score,
            severity=anomaly_result.severity,
            smoothed_score=tracker.smoothed_score,
            filtered_cpu=cpu_data.get("filtered", 0),
            filtered_ram=ram_data.get("filtered", 0),
            filtered_ping=ping_data.get("filtered", 0),
            filtered_fps=fps_data.get("filtered", 0),
            raw_cpu=snapshot.cpu_percent,
            raw_ram=snapshot.memory_mb,
            raw_ping=snapshot.ping_ms,
            raw_fps=snapshot.fps,
            pid=snapshot.pid,
            platform=config.platform,
            process_alive=snapshot.process_alive,
            uptime_sec=snapshot.uptime_sec,
            thread_count=snapshot.thread_count,
            last_update=time.time(),
            state_history=[
                {
                    "from": t.from_state,
                    "to": t.to_state,
                    "reason": t.reason,
                    "score": t.anomaly_score,
                    "time": t.timestamp,
                }
                for t in tracker.get_recent_transitions(10)
            ],
            triggered_signals=list(anomaly_result.triggered_signals),
        )

        with self._lock:
            self._latest_reports[tag_id] = report
            self._latest_snapshots[tag_id] = snapshot

            # Luu lich su in-memory (gioi han 500 mau)
            history = self._telemetry_history.setdefault(tag_id, [])
            history.append(snapshot)
            if len(history) > 500:
                self._telemetry_history[tag_id] = history[-500:]

        # --- 6. STORE ---
        self._storage.save_telemetry(
            tag_id=tag_id,
            platform=config.platform,
            pid=snapshot.pid,
            cpu=snapshot.cpu_percent,
            memory_mb=snapshot.memory_mb,
            fps=snapshot.fps,
            ping_ms=snapshot.ping_ms,
            anomaly_score=anomaly_result.score,
            severity=anomaly_result.severity,
            state=new_state.value,
            filtered_cpu=cpu_data.get("filtered", 0),
            filtered_ram=ram_data.get("filtered", 0),
            filtered_ping=ping_data.get("filtered", 0),
            filtered_fps=fps_data.get("filtered", 0),
        )

        # --- 7. EMIT EVENTS ---
        if new_state != old_state:
            self._storage.save_event(
                tag_id=tag_id,
                event_type="STATE_CHANGE",
                from_state=old_state.value,
                to_state=new_state.value,
                anomaly_score=anomaly_result.score,
                details=str(anomaly_result),
            )

            # Callbacks
            for cb in self._on_state_change_callbacks:
                try:
                    cb(tag_id, old_state, new_state, anomaly_result)
                except Exception:
                    pass

            logger.info(
                f"Radar [{tag_id}]: {old_state.value} -> {new_state.value} "
                f"(score={anomaly_result.score}, severity={anomaly_result.severity})"
            )

    def _periodic_integrity_check(self) -> None:
        """Kiem tra integrity dinh ky."""
        now = time.time()
        if now - self._last_integrity_check < self._integrity_check_interval:
            return

        self._last_integrity_check = now
        try:
            result = self._integrity.check_integrity()
            if result.match is False:
                self._integrity_mismatch = True
                logger.warning(f"Radar Integrity: {result.details}")
            else:
                self._integrity_mismatch = False
        except Exception as e:
            logger.debug(f"Integrity check error: {e}")


# Singleton instance
radar_engine = RadarEngine()
