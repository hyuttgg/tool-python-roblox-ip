# -*- coding: utf-8 -*-
"""
Radar Telemetry Collectors
Thu thap du lieu trang thai (telemetry) tu Roblox tren Windows (psutil) va Android (ADB).
"""

import os
import time
from dataclasses import dataclass, field
from typing import Optional, Dict
from config.logging import setup_logger

logger = setup_logger("radar_telemetry")


@dataclass
class TelemetrySnapshot:
    """Mau telemetry cho 1 chu ky radar."""
    timestamp: float = field(default_factory=time.time)
    tag_id: str = ""
    platform: str = "WINDOWS"       # "WINDOWS" | "ANDROID"

    # Process metrics
    pid: int = 0
    process_alive: bool = False
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    thread_count: int = 0
    process_status: str = "unknown"  # "running" | "stopped" | "zombie" | "not_found"
    uptime_sec: float = 0.0

    # Network metrics
    ping_ms: float = 0.0
    packet_loss: float = 0.0
    dns_ms: float = 0.0

    # Game metrics (tu heartbeat data)
    fps: int = 0
    in_game_ping: int = 0

    # Log signals
    log_disconnect_detected: bool = False
    log_error_code: Optional[str] = None

    # Integrity
    exe_hash_match: Optional[bool] = None


class WindowsCollector:
    """
    Thu thap telemetry tu psutil + Windows API.
    Yeu cau: pip install psutil (da co trong requirements.txt)
    """

    def __init__(self):
        self._psutil = None
        try:
            import psutil
            self._psutil = psutil
        except ImportError:
            logger.warning("psutil chua duoc cai dat. WindowsCollector se bi gioi han.")

    def collect(self, tag_id: str, pid: int,
                heartbeat_data: Optional[Dict] = None) -> TelemetrySnapshot:
        """
        Thu thap telemetry tu process Roblox tren Windows.

        Args:
            tag_id: Ma dinh danh Tag
            pid: Process ID cua Roblox
            heartbeat_data: Du lieu heartbeat tu Lua (fps, ping, memory)

        Returns:
            TelemetrySnapshot da dien day du
        """
        snap = TelemetrySnapshot(
            tag_id=tag_id,
            platform="WINDOWS",
            pid=pid,
        )

        if not self._psutil:
            snap.process_status = "no_psutil"
            return snap

        # Thu thap tu psutil
        try:
            if not self._psutil.pid_exists(pid):
                snap.process_alive = False
                snap.process_status = "not_found"
                return snap

            proc = self._psutil.Process(pid)

            # CPU (interval=0.2 de co gia tri chinh xac)
            snap.cpu_percent = proc.cpu_percent(interval=0.2)
            snap.process_alive = True

            # Memory
            mem_info = proc.memory_info()
            snap.memory_mb = round(mem_info.rss / (1024 * 1024), 2)

            # Thread count
            snap.thread_count = proc.num_threads()

            # Process status
            snap.process_status = proc.status()

            # Uptime
            create_time = proc.create_time()
            snap.uptime_sec = round(time.time() - create_time, 1)

        except self._psutil.NoSuchProcess:
            snap.process_alive = False
            snap.process_status = "not_found"
        except self._psutil.AccessDenied:
            snap.process_alive = True  # Ton tai nhung khong doc duoc
            snap.process_status = "access_denied"
        except Exception as e:
            logger.debug(f"Loi thu thap telemetry PID {pid}: {e}")
            snap.process_status = "error"

        # Ghep du lieu heartbeat tu Lua
        if heartbeat_data:
            snap.fps = int(heartbeat_data.get("fps", 0))
            snap.in_game_ping = int(heartbeat_data.get("ping_ms", 0))
            if heartbeat_data.get("memory_mb"):
                try:
                    snap.memory_mb = float(str(heartbeat_data["memory_mb"]).replace(" MB", "").replace(",", ""))
                except (ValueError, TypeError):
                    pass

        # Ping he thong
        try:
            from monitoring.ping import PingMonitor
            latency, loss = PingMonitor.ping_host(host="1.1.1.1", count=1, timeout_sec=1.5)
            snap.ping_ms = max(latency, 0)
            snap.packet_loss = loss
        except Exception:
            snap.ping_ms = 0
            snap.packet_loss = 0

        return snap


class AndroidCollector:
    """
    Thu thap telemetry tu Android qua ADB commands.
    Su dung UGPhoneBridge da co san trong du an.
    """

    def __init__(self):
        self._adb_bridge = None
        try:
            from devices.ugphone_bridge import UGPhoneBridge
            self._adb_bridge = UGPhoneBridge()
        except Exception:
            logger.debug("Khong the khoi tao UGPhoneBridge cho AndroidCollector.")

    def collect(self, tag_id: str, device_id: str,
                heartbeat_data: Optional[Dict] = None) -> TelemetrySnapshot:
        """
        Thu thap telemetry tu Roblox tren thiet bi Android.

        Args:
            tag_id: Ma dinh danh Tag
            device_id: ADB device ID (vd: "192.168.1.100:5555")
            heartbeat_data: Du lieu heartbeat tu Lua

        Returns:
            TelemetrySnapshot da dien
        """
        snap = TelemetrySnapshot(
            tag_id=tag_id,
            platform="ANDROID",
        )

        if not self._adb_bridge or not self._adb_bridge.adb_bin:
            snap.process_status = "no_adb"
            return snap

        # 1. Kiem tra trang thai Roblox
        try:
            status = self._adb_bridge.get_roblox_status(device_id)
            if status.get("running") == "Yes":
                snap.process_alive = True
                snap.process_status = "running"
                pid_str = status.get("pid", "0").strip()
                if pid_str:
                    # pidof co the tra ve nhieu PID, lay dau tien
                    snap.pid = int(pid_str.split()[0])
            else:
                snap.process_alive = False
                snap.process_status = "not_found"
                return snap
        except Exception as e:
            logger.debug(f"Loi kiem tra trang thai Android [{device_id}]: {e}")
            snap.process_status = "error"
            return snap

        # 2. Thu thap CPU tu top
        if snap.pid > 0:
            try:
                import subprocess
                out = subprocess.check_output(
                    [self._adb_bridge.adb_bin, "-s", device_id, "shell",
                     "top", "-n", "1", "-b", "-p", str(snap.pid)],
                    timeout=3
                ).decode("utf-8", errors="ignore")

                for line in out.splitlines():
                    if str(snap.pid) in line:
                        parts = line.split()
                        # Tim cot CPU% (thuong la cot thu 9 hoac 8)
                        for p in parts:
                            try:
                                v = float(p.replace("%", ""))
                                if 0 <= v <= 800:  # CPU% co the > 100 tren multi-core
                                    snap.cpu_percent = v
                                    break
                            except ValueError:
                                continue
                        break
            except Exception:
                pass

        # 3. Thu thap RAM tu dumpsys meminfo
        if snap.pid > 0:
            try:
                import subprocess
                out = subprocess.check_output(
                    [self._adb_bridge.adb_bin, "-s", device_id, "shell",
                     "dumpsys", "meminfo", "com.roblox.client"],
                    timeout=3
                ).decode("utf-8", errors="ignore")

                for line in out.splitlines():
                    if "TOTAL" in line and "PSS" not in line:
                        parts = line.split()
                        for p in parts:
                            try:
                                v = int(p.replace(",", ""))
                                if v > 1000:  # KB
                                    snap.memory_mb = round(v / 1024.0, 2)
                                    break
                            except ValueError:
                                continue
                        break
            except Exception:
                pass

        # 4. Thread count tu /proc/pid/stat
        if snap.pid > 0:
            try:
                import subprocess
                out = subprocess.check_output(
                    [self._adb_bridge.adb_bin, "-s", device_id, "shell",
                     "cat", f"/proc/{snap.pid}/status"],
                    timeout=2
                ).decode("utf-8", errors="ignore")

                for line in out.splitlines():
                    if line.startswith("Threads:"):
                        parts = line.split()
                        if len(parts) >= 2:
                            snap.thread_count = int(parts[1])
                        break
            except Exception:
                pass

        # 5. Ghep heartbeat data
        if heartbeat_data:
            snap.fps = int(heartbeat_data.get("fps", 0))
            snap.in_game_ping = int(heartbeat_data.get("ping_ms", 0))

        return snap
