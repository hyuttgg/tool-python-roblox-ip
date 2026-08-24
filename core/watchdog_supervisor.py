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

HEARTBEAT_TIMEOUT_SEC = 10.0  # Tự động kích hoạt mở lại sau 10s mất nhịp tim (Crash/Đơ game)
RESTART_COOLDOWN_SEC = 5.0    # Cooldown 5s giữa các lần mở lại tránh spam

@dataclass
class TagWatchState:
    tag_id: str
    username: str = ""
    assigned_ip: str = ""
    region: str = ""
    target_place_id: str = ""
    status: str = "OFFLINE"       # ONLINE, DISCONNECTED, ERROR, RESTARTING, TELEPORTING, OFFLINE
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
    """Bộ điều phối và giám sát tự động mở lại Roblox Tags an toàn, không ngắt client khi Server Hop (RAM Architecture)"""

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
                    if st.status != "TELEPORTING":
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
        """Ghi nhận khi Lua Client phát hiện lỗi mất mạng hoặc chuyển server (Server Hop)"""
        now = time.time()
        with self._lock:
            if tag_id not in self.tags:
                self.tags[tag_id] = TagWatchState(tag_id=tag_id)
            st = self.tags[tag_id]
            
            # Nếu Tag đang trong tiến trình Teleport / Server Hop -> Cho phép thời gian gia hạn (Grace Period) 60 giây
            if status_type in ["TELEPORTING", "SERVER_HOP", "HOPPING"]:
                st.status = "TELEPORTING"
                st.last_heartbeat_time = now + 60.0
                st.last_error_message = error_msg
                self.log_event(f"🔄 Tag [{tag_id}] Đang chuyển Server (Teleporting/Server Hop)... Tạm hoãn Watchdog trong 60s.")
                return

            st.status = status_type
            st.last_error_message = error_msg

        self.log_event(f"⚠️ Tag [{tag_id}] PHÁT HIỆN MẤT KẾT NỐI / CRASH: {error_msg} (Trạng thái: {status_type})")

        # Kích hoạt mở lại ngay lập tức nếu chế độ tự mở lại đang bật
        if self.is_enabled and self.auto_reopen_on_disconnect:
            threading.Thread(target=self._trigger_reopen_tag, args=(tag_id, f"Client Event: {error_msg}"), daemon=True).start()

    def _trigger_reopen_tag(self, tag_id: str, reason: str):
        """Tiến hành mở lại Tag Roblox sau khi bị tắt hoặc gặp sự cố (RAM & Auto-Rejoin Engine)"""
        with self._lock:
            if tag_id not in self.tags:
                self.tags[tag_id] = TagWatchState(tag_id=tag_id)
            st = self.tags[tag_id]
            if st.status == "TELEPORTING":
                logger.debug(f"Tag [{tag_id}] đang chuyển server (Teleporting), không mở lại.")
                return
            now = time.time()
            if now - st.last_restart_time < RESTART_COOLDOWN_SEC:
                logger.debug(f"Tag [{tag_id}] đang trong cooldown mở lại, bỏ qua.")
                return
            st.last_restart_time = now
            st.status = "RESTARTING"
            st.restarts_count += 1
            self.total_restarts += 1

        self.log_event(f"🚀 [AUTO-WATCHDOG] TỰ ĐỘNG MỞ LẠI TAG [{tag_id}]! (Lý do: {reason})")

        # 1. Dọn dẹp tiến trình treo hoặc hộp thoại crash cũ
        if st.process_pid > 0:
            try:
                import psutil
                if psutil.pid_exists(st.process_pid):
                    p = psutil.Process(st.process_pid)
                    if p.is_running():
                        p.terminate()
            except Exception:
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
                    st.last_heartbeat_time = time.time() + 15.0  # Grace period 15s để game load map
                    self.log_event(f"✅ [AUTO-WATCHDOG] MỞ LẠI THÀNH CÔNG Tag [{tag_id}] vào Game [{target_game.get('name')}] (PlaceId: {place_id})!")
                else:
                    st.status = "ERROR"
                    self.log_event(f"❌ [AUTO-WATCHDOG] Mở lại Tag [{tag_id}] thất bại: {launch_res.get('error')}")
        except Exception as e:
            self.log_event(f"❌ [AUTO-WATCHDOG] Lỗi ngoại lệ khi mở lại Tag [{tag_id}]: {e}")
            with self._lock:
                st.status = "ERROR"

    def _detect_hung_or_crashed_windows(self) -> List[Tuple[str, str]]:
        """Phát hiện các cửa sổ Roblox bị treo (Not Responding) hoặc hộp thoại Crash trên Windows"""
        if os.name != "nt":
            return []
        
        hung_tags = []
        try:
            import ctypes
            user32 = ctypes.windll.user32
            
            # Quét danh sách cửa sổ
            from core.scanner import RobloxWindowScanner
            scanner = RobloxWindowScanner()
            scanned = scanner.scan_active_roblox_windows()
            
            with self._lock:
                for inst in scanned:
                    hwnd = getattr(inst, "hwnd", 0)
                    pid = getattr(inst, "pid", 0)
                    title = getattr(inst, "title", "")
                    tag_id = getattr(inst, "tag_id", "")
                    
                    # 1. Kiểm tra Not Responding qua Win32 IsHungAppWindow
                    if hwnd and user32.IsHungAppWindow(hwnd):
                        hung_tags.append((tag_id, f"Cửa sổ Roblox bị treo (Not Responding - HWND: {hwnd})"))
                        continue
                    
                    # 2. Kiểm tra các hộp thoại Crash/Error popup của Roblox
                    crash_keywords = ["crash", "unexpected error", "error code", "roblox has crashed", "disconnected"]
                    if any(kw in title.lower() for kw in crash_keywords):
                        hung_tags.append((tag_id, f"Phát hiện hộp thoại Crash popup: '{title}' (PID: {pid})"))

        except Exception as e:
            logger.debug(f"Error checking hung windows: {e}")
        return hung_tags

    def _detect_android_crashes(self) -> List[Tuple[str, str]]:
        """Phát hiện app Roblox bị crash / văng trên Android / UGPhone qua ADB"""
        crashed_tags = []
        try:
            from devices.ugphone_bridge import UGPhoneBridge
            bridge = UGPhoneBridge()
            devices = bridge.refresh_devices()
            if devices:
                for dev in devices:
                    st_info = bridge.get_roblox_status(dev)
                    if st_info.get("installed") == "Yes" and st_info.get("running") == "No":
                        tag_name = f"ANDROID-{dev.replace(':', '_')}"
                        crashed_tags.append((tag_name, f"Roblox Client bị tắt/crash trên Android [{dev}]"))
        except Exception:
            pass
        return crashed_tags

    def _supervisor_loop(self):
        """Vòng lặp chạy ngầm kiểm tra nhịp tim, PID liveness, cửa sổ treo và crash để tự động Rejoin"""
        logger.info("Watchdog Supervisor daemon loop started (RAM & Auto-Rejoin Engine active).")
        while self._running:
            try:
                if self.is_enabled:
                    now = time.time()
                    tags_to_restart = []

                    # 0. Tự động phát hiện và đăng ký các cửa sổ / tiến trình Roblox đang chạy nếu chưa có trong self.tags
                    if os.name == "nt":
                        try:
                            from core.scanner import RobloxWindowScanner
                            scanned = RobloxWindowScanner().scan_active_roblox_windows()
                            with self._lock:
                                for inst in scanned:
                                    tid = getattr(inst, "tag_id", "") or f"ROBLOX-TAG-{inst.pid}"
                                    if tid not in self.tags:
                                        self.tags[tid] = TagWatchState(
                                            tag_id=tid,
                                            assigned_ip=getattr(inst, "assigned_ip", "") or "127.0.0.1",
                                            process_pid=inst.pid,
                                            status="ONLINE",
                                            last_heartbeat_time=time.time()
                                        )
                        except Exception:
                            pass

                    # 0.2 Tự động đăng ký các thiết bị Android/UGPhone kết nối qua ADB
                    try:
                        from devices.ugphone_bridge import UGPhoneBridge
                        bridge = UGPhoneBridge()
                        devices = bridge.refresh_devices()
                        with self._lock:
                            for dev in devices:
                                tid = f"ANDROID-{dev.replace(':', '_')}"
                                if tid not in self.tags:
                                    self.tags[tid] = TagWatchState(
                                        tag_id=tid,
                                        assigned_ip=dev,
                                        status="ONLINE",
                                        last_heartbeat_time=time.time()
                                    )
                    except Exception:
                        pass
                    
                    with self._lock:
                        for tag_id, st in list(self.tags.items()):
                            if not st.is_monitored or st.status == "TELEPORTING":
                                continue
                            
                            # 1. Kiểm tra PID Liveness: Nếu tiến trình đã chết (Crash / Closed)
                            if st.process_pid > 0:
                                try:
                                    import psutil
                                    if not psutil.pid_exists(st.process_pid):
                                        st.status = "OFFLINE"
                                        st.process_pid = 0
                                        tags_to_restart.append((tag_id, "Tiến trình Roblox đã bị tắt / Crash đột ngột"))
                                        continue
                                except Exception:
                                    pass

                            # 2. Kiểm tra Heartbeat Timeout (Mất kết nối quá 10s)
                            if st.status == "ONLINE" and st.last_heartbeat_time > 0:
                                elapsed = now - st.last_heartbeat_time
                                if elapsed > HEARTBEAT_TIMEOUT_SEC:
                                    st.status = "OFFLINE"
                                    tags_to_restart.append((tag_id, f"Mất kết nối nhịp tim (Heartbeat Timeout > {int(elapsed)}s)"))

                    # 3. Kiểm tra Cửa sổ bị treo hoặc Crash popup trên Windows
                    hung_list = self._detect_hung_or_crashed_windows()
                    for tid, h_reason in hung_list:
                        tags_to_restart.append((tid, h_reason))

                    # 4. Kiểm tra App văng trên Android / UGPhone
                    android_crashes = self._detect_android_crashes()
                    for tid, a_reason in android_crashes:
                        tags_to_restart.append((tid, a_reason))

                    # Tiến hành mở lại và rejoin game tự động
                    for tid, r_reason in tags_to_restart:
                        if self.auto_reopen_on_disconnect:
                            self._trigger_reopen_tag(tid, r_reason)

            except Exception as e:
                logger.error(f"Error in watchdog supervisor loop: {e}")

            time.sleep(2)

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
