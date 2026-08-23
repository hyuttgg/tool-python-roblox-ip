# -*- coding: utf-8 -*-
"""
Roblox Tag Auto-Restart Watchdog & Supervisor Daemon
Giám sát trạng thái hoạt động thực tế của từng Tag Roblox qua:
  1. Nhịp tim (Lua Heartbeat Transmitter qua HTTP POST /api/heartbeat).
  2. Bộ bắt sự kiện lỗi ngắt kết nối (Lua Error & Disconnect Hook).
  3. Quét tiến trình hệ điều hành (Windows PID / Android / UGPhone).

Khi phát hiện Tag bị tắt (bị đóng cửa sổ, crash, bị kick, lỗi 277/268 hoặc mất nhịp tim > 15s):
  -> Tự động ghi nhận lỗi và kích hoạt cơ chế TỰ MỞ LẠI (AUTO-RESTART / RE-LAUNCH).
  -> Gán lại đúng Dedicated IP riêng biệt của Tag đó.
  -> Tự động Join lại Game Roblox đã chọn!
"""

import os
import sys
import time
import json
import threading
import subprocess
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from config.logging import setup_logger

logger = setup_logger("watchdog_supervisor")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
WATCHDOG_CONFIG_FILE = os.path.join(DATA_DIR, "watchdog_state.json")

HEARTBEAT_TIMEOUT_SEC = 15.0  # Quá 15 giây không có nhịp tim -> Coi là bị tắt / mất kết nối
RESTART_COOLDOWN_SEC = 5.0    # Thời gian chờ giữa các lần tự động mở lại tránh spam


@dataclass
class TagWatchState:
    tag_id: str
    username: str = ""
    assigned_ip: str = ""
    region: str = ""
    target_place_id: str = ""
    status: str = "OFFLINE"       # ONLINE, DISCONNECTED, ERROR, RESTARTING, OFFLINE
    last_heartbeat_time: float = 0.0
    last_error_message: str = ""
    fps: int = 60
    ping_ms: int = 0
    memory_mb: str = "0 MB"
    restarts_count: int = 0
    last_restart_time: float = 0.0
    process_pid: int = 0
    is_monitored: bool = True

    def to_dict(self) -> Dict:
        return asdict(self)


class RobloxWatchdogSupervisor:
    """Bộ điều phối và giám sát tự động mở lại Roblox Tags"""

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.tags: Dict[str, TagWatchState] = {}
        self.is_enabled = True
        self.auto_reopen_on_disconnect = True
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self.total_restarts = 0
        self.recent_logs: List[str] = []

    def log_event(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        logger.info(entry)
        with self._lock:
            self.recent_logs.append(entry)
            if len(self.recent_logs) > 50:
                self.recent_logs.pop(0)

    def register_tag(self, tag_id: str, assigned_ip: str = "", region: str = "", username: str = "", place_id: str = "", pid: int = 0):
        with self._lock:
            if tag_id not in self.tags:
                self.tags[tag_id] = TagWatchState(
                    tag_id=tag_id,
                    assigned_ip=assigned_ip,
                    region=region,
                    username=username,
                    target_place_id=place_id,
                    process_pid=pid,
                    status="ONLINE" if pid > 0 else "OFFLINE"
                )
            else:
                st = self.tags[tag_id]
                if assigned_ip: st.assigned_ip = assigned_ip
                if region: st.region = region
                if username: st.username = username
                if place_id: st.target_place_id = place_id
                if pid > 0:
                    st.process_pid = pid
                    st.status = "ONLINE"

    def record_heartbeat(self, tag_id: str, data: Dict):
        """Ghi nhận nhịp tim thời gian thực được gửi từ Lua Client"""
        now = time.time()
        with self._lock:
            if tag_id not in self.tags:
                self.tags[tag_id] = TagWatchState(tag_id=tag_id)
            
            st = self.tags[tag_id]
            st.last_heartbeat_time = now
            st.status = "ONLINE"
            st.username = data.get("username") or st.username
            st.fps = int(data.get("fps", 60))
            st.ping_ms = int(data.get("ping_ms", 0))
            st.memory_mb = data.get("memory_mb", "N/A")
            if data.get("place_id"):
                st.target_place_id = str(data.get("place_id"))
            if data.get("assigned_ip"):
                st.assigned_ip = data.get("assigned_ip")

    def record_error_or_disconnect(self, tag_id: str, error_msg: str, status_type: str = "DISCONNECTED"):
        """Ghi nhận khi Lua Client phát hiện lỗi mất mạng hoặc bị Kick"""
        now = time.time()
        with self._lock:
            if tag_id not in self.tags:
                self.tags[tag_id] = TagWatchState(tag_id=tag_id)
            st = self.tags[tag_id]
            st.status = status_type
            st.last_error_message = error_msg

        self.log_event(f"⚠️ Tag [{tag_id}] BÁO LỖI: {error_msg} (Trạng thái: {status_type})")

        # Kích hoạt mở lại ngay lập tức nếu chế độ tự mở lại đang bật
        if self.is_enabled and self.auto_reopen_on_disconnect:
            threading.Thread(target=self._trigger_reopen_tag, args=(tag_id, f"Lua Event: {error_msg}"), daemon=True).start()

    def _trigger_reopen_tag(self, tag_id: str, reason: str):
        """Tiến hành mở lại Tag Roblox sau khi bị tắt hoặc gặp sự cố"""
        with self._lock:
            st = self.tags.get(tag_id)
            if not st:
                return
            now = time.time()
            if now - st.last_restart_time < RESTART_COOLDOWN_SEC:
                logger.debug(f"Tag [{tag_id}] đang trong cooldown mở lại, bỏ qua.")
                return
            st.last_restart_time = now
            st.status = "RESTARTING"
            st.restarts_count += 1
            self.total_restarts += 1

        self.log_event(f"🚀 [AUTO-WATCHDOG] Đang tự động MỞ LẠI Tag [{tag_id}]! (Lý do: {reason})")

        # 1. Tắt tiến trình treo cũ (nếu có PID)
        if st.process_pid > 0:
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/PID", str(st.process_pid)], capture_output=True, timeout=2)
                else:
                    subprocess.run(["kill", "-9", str(st.process_pid)], capture_output=True, timeout=2)
            except Exception:
                pass

        time.sleep(1.5)

        # 2. Khởi chạy lại Roblox với Place ID đã cấu hình riêng cho Tag này
        try:
            from core.game_selector import game_manager
            target_game = game_manager.get_game_for_tag(tag_id)
            place_id = target_game.get("place_id", "2753915549")
            
            from core.java_sort_bridge import RobloxAutoLauncher
            launch_res = RobloxAutoLauncher.launch_single_instance(place_id=place_id, tag_id=tag_id)
            
            with self._lock:
                if launch_res.get("status") == "LAUNCHED":
                    st.process_pid = launch_res.get("pid", 0)
                    st.status = "ONLINE"
                    self.log_event(f"✅ [AUTO-WATCHDOG] MỞ LẠI THÀNH CÔNG Tag [{tag_id}] vào Game [{target_game.get('name')}] (PlaceId: {place_id})!")
                else:
                    st.status = "ERROR"
                    self.log_event(f"❌ [AUTO-WATCHDOG] Mở lại Tag [{tag_id}] thất bại: {launch_res.get('error')}")
        except Exception as e:
            self.log_event(f"❌ [AUTO-WATCHDOG] Lỗi ngoại lệ khi mở lại Tag [{tag_id}]: {e}")
            with self._lock:
                st.status = "ERROR"

    def _supervisor_loop(self):
        """Vòng lặp chạy ngầm kiểm tra nhịp tim và trạng thái thực tế của các Tag"""
        logger.info("Watchdog Supervisor daemon loop started.")
        while self._running:
            try:
                if self.is_enabled:
                    now = time.time()
                    tags_to_restart = []
                    
                    with self._lock:
                        for tag_id, st in list(self.tags.items()):
                            if not st.is_monitored:
                                continue
                            
                            # Nếu Tag đang được đánh dấu là ONLINE nhưng đã quá lâu không có Heartbeat
                            if st.status == "ONLINE" and st.last_heartbeat_time > 0:
                                elapsed = now - st.last_heartbeat_time
                                if elapsed > HEARTBEAT_TIMEOUT_SEC:
                                    st.status = "OFFLINE"
                                    tags_to_restart.append((tag_id, f"Mất kết nối nhịp tim (Heartbeat Timeout > {int(elapsed)}s)"))

                    # Tiến hành mở lại các Tag bị mất kết nối
                    for tid, r_reason in tags_to_restart:
                        if self.auto_reopen_on_disconnect:
                            self._trigger_reopen_tag(tid, r_reason)

            except Exception as e:
                logger.error(f"Error in watchdog supervisor loop: {e}")

            time.sleep(3)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._supervisor_loop, daemon=True)
        self._thread.start()
        logger.info("Roblox Auto-Restart Watchdog started.")

    def stop(self):
        self._running = False
        logger.info("Roblox Auto-Restart Watchdog stopped.")

    def get_summary(self) -> Dict:
        with self._lock:
            online_count = sum(1 for t in self.tags.values() if t.status == "ONLINE")
            off_count = sum(1 for t in self.tags.values() if t.status in ["OFFLINE", "DISCONNECTED", "ERROR"])
            return {
                "is_enabled": self.is_enabled,
                "auto_reopen": self.auto_reopen_on_disconnect,
                "total_monitored": len(self.tags),
                "online_count": online_count,
                "off_count": off_count,
                "total_restarts": self.total_restarts,
                "tags": {k: v.to_dict() for k, v in self.tags.items()},
                "recent_logs": list(self.recent_logs[-15:])
            }


# Singleton instance
watchdog = RobloxWatchdogSupervisor()
