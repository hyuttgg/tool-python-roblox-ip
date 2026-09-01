# -*- coding: utf-8 -*-
"""
Roblox Tag Auto-Restart Watchdog & Supervisor Daemon
Giám sát trạng thái hoạt động thực tế của từng Tag Roblox qua:
  1. Nhịp tim (Lua Heartbeat Transmitter qua HTTP POST /api/heartbeat).
  2. Bộ bắt sự kiện lỗi ngắt kết nối (Lua Error & Disconnect Hook).
  3. Quét tiến trình hệ điều hành (Windows PID / Android / UGPhone).

Khi phát hiện Tag bị tắt (bị đóng cửa sổ, crash, bị kick, lỗi 277/268 hoặc mất nhịp tim > 45s):
  -> Tự động ghi nhận lỗi và kích hoạt cơ chế TỰ MỞ LẠI (AUTO-RESTART / RE-LAUNCH).
  -> Gán lại đúng Dedicated IP riêng biệt của Tag đó.
  -> Tự động Join lại Game Roblox đã chọn!

LƯU Ý QUAN TRỌNG:
  - Watchdog CHỈ quản lý các Tag mà người dùng đã chọn thông qua Pipeline.
  - KHÔNG tự động phát hiện và restart các tiến trình Roblox ngẫu nhiên trên máy.
  - Tag chỉ bị restart khi ĐÃ NHẬN ĐƯỢC ÍT NHẤT 1 heartbeat thật từ Lua script.
"""

import os
import sys
import time
import json
import socket
import threading
import subprocess
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple
from config.logging import setup_logger
from core.roblox_log_monitor import roblox_log_monitor
from core.screen_capture import capture_roblox_window
from network.discord_notifier import discord_notifier

logger = setup_logger("watchdog_supervisor")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
WATCHDOG_CONFIG_FILE = os.path.join(DATA_DIR, "watchdog_state.json")

HEARTBEAT_TIMEOUT_SEC = 45.0  # Tự động kích hoạt mở lại sau 45s mất nhịp tim (đủ thời gian load game)
RESTART_COOLDOWN_SEC = 15.0   # Cooldown 15s giữa các lần mở lại tránh spam
STARTUP_GRACE_PERIOD_SEC = 2.0   # Grace Period 2s sau khi start()
ROBLOX_ENDPOINTS = (("www.roblox.com", 443), ("apis.roblox.com", 443))


def internet_available(timeout: float = 3.0) -> bool:
    """Kiểm tra xem kết nối mạng tới các máy chủ Roblox có thông suốt hay không"""
    for endpoint in ROBLOX_ENDPOINTS:
        try:
            with socket.create_connection(endpoint, timeout=timeout):
                return True
        except OSError:
            continue
    return False


def wait_for_internet(timeout_max: float = 60.0) -> bool:
    """Chờ kết nối Internet phục hồi trước khi kích hoạt mở lại game"""
    if internet_available():
        return True
    logger.warning("⚠️ Không có kết nối tới máy chủ Roblox. Đang tạm hoãn và chờ mạng phục hồi...")
    deadline = time.time() + timeout_max
    while time.time() < deadline:
        time.sleep(3.0)
        if internet_available():
            logger.info("🟢 Kết nối Internet tới Roblox đã được phục hồi!")
            return True
    return internet_available()


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
    user_registered: bool = True    # Tag được đăng ký để watchdog quản lý
    heartbeat_received: bool = False
    has_been_active: bool = False   # CHỈ = True khi đã từng được launch hoặc chạy thực tế

    def to_dict(self) -> Dict:
        return asdict(self)


class RobloxWatchdogSupervisor:
    """Bộ điều phối và giám sát tự động mở lại Roblox Tags an toàn, không ngắt client khi Server Hop (RAM Architecture)"""

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.tags: Dict[str, TagWatchState] = {}
        self.is_enabled = True
        self.auto_reopen_on_disconnect = True
        self.setup_completed = True
        self._start_time: float = 0.0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self.total_restarts = 0
        self.recent_logs: List[str] = []
        self.max_managed_tags: int = 0

    def log_event(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        logger.info(entry)
        with self._lock:
            self.recent_logs.append(entry)
            if len(self.recent_logs) > 50:
                self.recent_logs.pop(0)

    def register_tag(self, tag_id: str, assigned_ip: str = "", region: str = "", username: str = "", place_id: str = "", pid: int = 0):
        """Đăng ký tag để giám sát và tự động Rejoin khi bị tắt hoặc mất kết nối."""
        with self._lock:
            if tag_id not in self.tags:
                self.tags[tag_id] = TagWatchState(
                    tag_id=tag_id,
                    assigned_ip=assigned_ip,
                    region=region,
                    username=username,
                    target_place_id=place_id,
                    process_pid=pid,
                    status="ONLINE" if pid > 0 else "OFFLINE",
                    user_registered=True,
                    heartbeat_received=True if pid > 0 else False,
                    has_been_active=True if pid > 0 else False
                )
            else:
                st = self.tags[tag_id]
                st.user_registered = True
                if assigned_ip: st.assigned_ip = assigned_ip
                if region: st.region = region
                if username: st.username = username
                if place_id: st.target_place_id = place_id
                if pid > 0:
                    st.process_pid = pid
                    st.has_been_active = True
                    if st.status != "TELEPORTING":
                        st.status = "ONLINE"

    def record_heartbeat(self, tag_id: str, data: Dict):
        """Ghi nhận nhịp tim thời gian thực được gửi từ Lua Client"""
        now = time.time()
        with self._lock:
            if tag_id not in self.tags:
                self.tags[tag_id] = TagWatchState(tag_id=tag_id, user_registered=True)
            
            st = self.tags[tag_id]
            st.last_heartbeat_time = now
            st.status = "ONLINE"
            st.heartbeat_received = True
            st.has_been_active = True
            st.restarts_count = 0  # Reset số lần lỗi khi đã kết nối ổn định
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
                self.tags[tag_id] = TagWatchState(tag_id=tag_id, user_registered=True)
            st = self.tags[tag_id]
            
            # Nếu Tag đang trong tiến trình Teleport / Server Hop -> Grace Period 60 giây
            if status_type in ["TELEPORTING", "SERVER_HOP", "HOPPING"]:
                st.status = "TELEPORTING"
                st.last_heartbeat_time = now + 60.0
                st.last_error_message = error_msg
                self.log_event(f"🔄 Tag [{tag_id}] Đang chuyển Server (Teleporting/Server Hop)... Tạm hoãn Watchdog trong 60s.")
                return

            st.status = status_type
            st.last_error_message = error_msg

        self.log_event(f"⚠️ Tag [{tag_id}] PHÁT HIỆN MẤT KẾT NỐI / CRASH: {error_msg} (Trạng thái: {status_type})")

        if self.is_enabled and self.auto_reopen_on_disconnect:
            threading.Thread(target=self._trigger_reopen_tag, args=(tag_id, f"Client Event: {error_msg}"), daemon=True).start()

    def _trigger_reopen_tag(self, tag_id: str, reason: str):
        """Tiến hành mở lại Tag Roblox sau khi bị tắt hoặc gặp sự cố (Tối đa 3 lần thử)"""
        # CHẶN: Không auto-reopen nếu chưa bật
        if not self.setup_completed or not self.is_enabled or not self.auto_reopen_on_disconnect:
            return

        with self._lock:
            if tag_id not in self.tags:
                return
            st = self.tags[tag_id]

            if not st.user_registered:
                return
            if st.status == "TELEPORTING":
                logger.debug(f"Tag [{tag_id}] đang chuyển server (Teleporting), không mở lại.")
                return
            if st.restarts_count >= 3:
                self.log_event(f"⚠️ Tag [{tag_id}] đã Rejoin {st.restarts_count} lần. Tạm dừng để tránh nghẽn CPU/Crash game.")
                st.status = "OFFLINE"
                return

            now = time.time()
            if now - st.last_restart_time < RESTART_COOLDOWN_SEC:
                logger.debug(f"Tag [{tag_id}] đang trong cooldown mở lại, bỏ qua.")
                return
            st.last_restart_time = now
            st.status = "RESTARTING"
            st.restarts_count += 1
            st.has_been_active = True
            self.total_restarts += 1

        self.log_event(f"🚀 [AUTO-WATCHDOG] TỰ ĐỘNG REJOIN TAG [{tag_id}]! (Lý do: {reason})")

        # 1. Chụp ảnh màn hình lưu vết sự cố & gửi thông báo Discord
        screenshot_path = None
        try:
            from core.game_selector import game_manager
            target_game = game_manager.get_game_for_tag(tag_id)
            g_name = target_game.get("name", "Roblox")
            p_id = target_game.get("place_id", "2753915549")

            screenshot_path = capture_roblox_window()
            discord_notifier.send_crash_alert(
                tag_id=tag_id,
                game_name=g_name,
                place_id=p_id,
                error_reason=reason,
                image_path=screenshot_path
            )
        except Exception as e:
            logger.debug(f"Lỗi chụp ảnh hoặc gửi Discord Alert: {e}")

        # 2. Dọn dẹp tiến trình treo / crash
        is_android_env = os.path.exists("/system/bin/am") or os.path.exists("/data/data/com.termux") or "ANDROID_ROOT" in os.environ
        if is_android_env or "UGPHONE" in tag_id or "ANDROID" in tag_id:
            try:
                subprocess.run(["am", "force-stop", "com.roblox.client"], capture_output=True, timeout=2)
            except Exception:
                pass

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

        # 3. Kiểm tra kết nối Internet tới máy chủ Roblox trước khi mở lại
        if not wait_for_internet(timeout_max=15.0):
            self.log_event(f"⚠️ [AUTO-WATCHDOG] Mạng chưa sẵn sàng để mở lại Tag [{tag_id}], sẽ thử lại chu kỳ sau.")
            with self._lock:
                st.status = "OFFLINE"
            return

        time.sleep(1.0)

        # 4. Khởi chạy lại Roblox với Server Region tối ưu
        try:
            from core.game_selector import game_manager
            # Tự động tìm Server tối ưu mới cùng Region cho Tag
            best_s = game_manager.resolve_server_for_tag(tag_id)
            target_game = game_manager.get_game_for_tag(tag_id)
            place_id = target_game.get("place_id", "2753915549")
            tag_reg = target_game.get("preferred_region", "AUTO")
            
            from core.java_sort_bridge import RobloxAutoLauncher
            launch_res = RobloxAutoLauncher.launch_single_instance(place_id=place_id, tag_id=tag_id)
            
            with self._lock:
                if launch_res.get("status") == "LAUNCHED":
                    st.process_pid = launch_res.get("pid", 0)
                    st.status = "ONLINE"
                    st.last_heartbeat_time = time.time() + 30.0
                    st.heartbeat_received = True
                    self.log_event(f"✅ [AUTO-WATCHDOG] REJOIN THÀNH CÔNG Tag [{tag_id}] vào Game [{target_game.get('name')}] (Region: [{tag_reg}], PlaceId: {place_id})!")
                    
                    # Gửi Discord thông báo Rejoin thành công
                    discord_notifier.send_rejoin_alert(
                        tag_id=tag_id,
                        game_name=target_game.get("name", "Roblox"),
                        place_id=place_id,
                        assigned_ip=st.assigned_ip,
                        region=tag_reg,
                        attempt=st.restarts_count
                    )
                else:
                    st.status = "OFFLINE"
                    self.log_event(f"❌ [AUTO-WATCHDOG] Rejoin Tag [{tag_id}] thất bại: {launch_res.get('error')}")
        except Exception as e:
            self.log_event(f"❌ [AUTO-WATCHDOG] Lỗi ngoại lệ khi mở lại Tag [{tag_id}]: {e}")
            with self._lock:
                st.status = "OFFLINE"

    def _detect_hung_or_crashed_windows(self) -> List[Tuple[str, str]]:
        """Phát hiện các cửa sổ Roblox bị treo (NOT RESPONDING)"""
        if os.name != "nt":
            return []
        hung_tags = []
        try:
            # 1. Quét qua tasklist STATUS eq NOT RESPONDING
            res = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq RobloxPlayerBeta.exe", "/FI", "STATUS eq NOT RESPONDING", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False
            )
            has_hung_proc = "RobloxPlayerBeta.exe" in res.stdout

            with self._lock:
                for tag_id, st in self.tags.items():
                    if not st.user_registered or not st.is_monitored:
                        continue
                    pid = st.process_pid
                    if pid <= 0:
                        continue
                    
                    if has_hung_proc:
                        hung_tags.append((tag_id, f"Phát hiện cửa sổ Roblox bị treo (NOT RESPONDING, PID: {pid})"))
                    else:
                        try:
                            import psutil
                            if psutil.pid_exists(pid):
                                p = psutil.Process(pid)
                                if p.status() == psutil.STATUS_STOPPED:
                                    hung_tags.append((tag_id, f"Tiến trình Roblox bị dừng (STOPPED, PID: {pid})"))
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"Error checking hung windows: {e}")
        return hung_tags

    def _detect_android_crashes(self) -> List[Tuple[str, str]]:
        """Phát hiện app Roblox bị crash trên Android"""
        crashed_tags = []
        try:
            with self._lock:
                android_tags = [t for t in self.tags.values() if t.user_registered and (t.tag_id.startswith("ANDROID-") or t.tag_id.startswith("UGPHONE-"))]
            if not android_tags:
                return []

            from devices.ugphone_bridge import UGPhoneBridge
            bridge = UGPhoneBridge()
            devices = bridge.refresh_devices()
            if devices:
                for dev in devices:
                    tag_name = f"ANDROID-{dev.replace(':', '_')}"
                    if any(t.tag_id == tag_name for t in android_tags):
                        st_info = bridge.get_roblox_status(dev)
                        if st_info.get("installed") == "Yes" and st_info.get("running") == "No":
                            crashed_tags.append((tag_name, f"Roblox Client bị tắt/crash trên Android [{dev}]"))
        except Exception:
            pass
        return crashed_tags

    def _supervisor_loop(self):
        """Vòng lặp giám sát đa nguồn: Tự động Rejoin khi Offline + Lua Heartbeat + Roblox Log Tailer + Windows Not Responding + PID Lifecycle"""
        logger.info("Watchdog Supervisor daemon loop started (Tự động giám sát & Auto-Rejoin).")
        while self._running:
            try:
                if self.is_enabled and self.setup_completed and self.auto_reopen_on_disconnect:
                    now = time.time()
                    tags_to_restart = []
                    
                    with self._lock:
                        for tag_id, st in list(self.tags.items()):
                            if not st.user_registered or not st.is_monitored or st.status == "TELEPORTING":
                                continue
                            
                            # 1. Kiểm tra PID Liveness
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

                            # 2. Heartbeat Timeout
                            if st.status == "ONLINE" and st.last_heartbeat_time > 0:
                                elapsed = now - st.last_heartbeat_time
                                if elapsed > HEARTBEAT_TIMEOUT_SEC:
                                    st.status = "OFFLINE"
                                    tags_to_restart.append((tag_id, f"Mất kết nối nhịp tim (Heartbeat Timeout > {int(elapsed)}s)"))
                                    continue

                            # 3. Tự động Rejoin khi Tag đã từng hoạt động và bị OFFLINE / DISCONNECTED / ERROR
                            if st.has_been_active and st.status in ["OFFLINE", "DISCONNECTED", "ERROR"] and st.process_pid == 0:
                                if st.restarts_count < 3 and (now - st.last_restart_time) >= RESTART_COOLDOWN_SEC:
                                    tags_to_restart.append((tag_id, "Tag đã bị ngắt kết nối / Văng game ➔ Kích hoạt Auto-Rejoin"))

                    # 4. Kiểm tra Log Monitor (Bắt lỗi Error 277, 268, 273, Kicked, Idle 20m)
                    try:
                        log_disconnect = roblox_log_monitor.check_for_disconnect()
                        if log_disconnect:
                            with self._lock:
                                for tag_id, st in self.tags.items():
                                    if st.user_registered and st.status in ["ONLINE", "RESTARTING"]:
                                        tags_to_restart.append((tag_id, f"Phát hiện lỗi trong Player Log: [{log_disconnect}]"))
                    except Exception as e:
                        logger.debug(f"Lỗi kiểm tra Roblox Log Monitor: {e}")

                    # 5. Kiểm tra Cửa sổ bị treo (NOT RESPONDING)
                    hung_list = self._detect_hung_or_crashed_windows()
                    for tid, h_reason in hung_list:
                        tags_to_restart.append((tid, h_reason))

                    # 6. Kiểm tra Android crash
                    android_crashes = self._detect_android_crashes()
                    for tid, a_reason in android_crashes:
                        tags_to_restart.append((tid, a_reason))

                    # Tiến hành mở lại (sau khi qua bộ lọc Deep-Check chống kill oan)
                    for tid, r_reason in tags_to_restart:
                        if self.auto_reopen_on_disconnect:
                            with self._lock:
                                st_tag = self.tags.get(tid)
                                if st_tag and st_tag.process_pid > 0:
                                    # Deep check on-device signal: nếu process pid vẫn sống và đang active
                                    try:
                                        import psutil
                                        if psutil.pid_exists(st_tag.process_pid):
                                            p = psutil.Process(st_tag.process_pid)
                                            if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                                                self.log_event(f"🛡️ [DEEP-CHECK] BỎ QUA REJOIN Tag [{tid}]: Tiến trình PID {st_tag.process_pid} vẫn đang hoạt động trên máy (Bảo vệ khỏi kill oan).")
                                                continue
                                    except Exception:
                                        pass
                            self._trigger_reopen_tag(tid, r_reason)

            except Exception as e:
                logger.error(f"Error in watchdog supervisor loop: {e}")

            time.sleep(3)

    def start(self):
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._supervisor_loop, daemon=True)
        self._thread.start()
        logger.info("Roblox Auto-Restart Watchdog started (Auto-Rejoin: %s).", self.auto_reopen_on_disconnect)

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
