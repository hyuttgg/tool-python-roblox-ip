# -*- coding: utf-8 -*-
"""
Android Roblox Auto-Rejoin Engine
Dựa trên kiến trúc và log pattern từ DroidBlox-kt.
Hỗ trợ cả môi trường Native Android (Termux) và điều khiển qua ADB (PC / Cloud Phone / Giả lập).
"""

import os
import re
import sys
import time
import shutil
import logging
import threading
import subprocess
from enum import Enum
from typing import Optional, Dict, Callable, List, Tuple
from dataclasses import dataclass

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logger = logging.getLogger("android_rejoin")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class RejoinState(Enum):
    IDLE = "IDLE"
    LAUNCHING = "LAUNCHING"
    CONNECTING = "CONNECTING"
    IN_GAME = "IN_GAME"
    DISCONNECTED = "DISCONNECTED"
    CRASHED = "CRASHED"
    COOLDOWN = "COOLDOWN"


@dataclass
class RobloxSessionInfo:
    place_id: Optional[int] = None
    job_id: Optional[str] = None
    universe_id: Optional[int] = None
    user_id: Optional[int] = None
    udmux_ip: Optional[str] = None
    server_ip: Optional[str] = None
    joined_at: float = 0.0
    last_active: float = 0.0
    disconnect_reason: Optional[str] = None


class LogcatPatterns:
    """Các mẫu Regex bóc tách Logcat được chuyển giao trực tiếp từ droidblox-kt LogEntries"""
    # [FLog::Output] ! Joining game '<jobId>' place <placeId> at <ip>
    GAME_JOINING = re.compile(r"! Joining game '([0-9a-f\-]{36})' place ([0-9]+) at ([0-9.]+)")
    
    # [FLog::GameJoinLoadTime] Report game_join_loadtime: ... userid:<userId>, ... universeid:<universeId>
    GAME_JOINING_UNIVERSE = re.compile(r"userid:([0-9]+),.*universeid:([0-9]+)")
    
    # [FLog::Network] UDMUX Address = <ip>
    GAME_JOINING_UDMUX = re.compile(r"UDMUX Address = ([0-9.]+)")
    
    # [FLog::Network] serverId:
    GAME_JOINED_KEYWORD = "serverId:"
    
    # [FLog::Network] Time to disconnect replication data:
    GAME_DISCONNECTED_KEYWORD = "Time to disconnect replication data"
    
    # Mã lỗi phổ biến trong Logcat
    ERROR_CODE_PATTERN = re.compile(r"(?:Error Code|error code|ErrorCode|DisconnectReason):\s*([0-9]{3})")


class AndroidRobloxWatcher:
    """Theo dõi Logcat và tiến trình Roblox trên Android (trực tiếp hoặc qua ADB)"""

    def __init__(
        self,
        adb_bin: Optional[str] = None,
        device_id: Optional[str] = None,
        on_event_callback: Optional[Callable[[str, Dict], None]] = None
    ):
        self.adb_bin = adb_bin
        self.device_id = device_id
        self.callback = on_event_callback
        self.is_termux = self._detect_is_termux()
        self.session = RobloxSessionInfo()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @staticmethod
    def _detect_is_termux() -> bool:
        return os.path.exists("/data/data/com.termux") or os.environ.get("PREFIX", "").startswith("/data/data/com.termux")

    def _build_shell_cmd(self, subcmd: List[str]) -> List[str]:
        if self.adb_bin and self.device_id:
            return [self.adb_bin, "-s", self.device_id, "shell"] + subcmd
        elif self.adb_bin:
            return [self.adb_bin, "shell"] + subcmd
        else:
            return subcmd

    def get_roblox_pid(self) -> int:
        """Lấy PID của tiến trình Roblox Client com.roblox.client"""
        # Thử pidof
        try:
            cmd = self._build_shell_cmd(["pidof", "com.roblox.client"])
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            pid_str = res.stdout.strip()
            if pid_str and pid_str.isdigit():
                return int(pid_str)
            elif pid_str:
                pids = pid_str.split()
                if pids and pids[0].isdigit():
                    return int(pids[0])
        except Exception:
            pass

        # Fallback ps
        try:
            cmd = self._build_shell_cmd(["ps", "-A", "-o", "PID,NAME"])
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            for line in res.stdout.splitlines():
                if "com.roblox.client" in line:
                    parts = line.strip().split()
                    if parts and parts[0].isdigit():
                        return int(parts[0])
        except Exception:
            pass
        return 0

    def set_oom_score_adj(self, pid: int, score: int = -300) -> Tuple[bool, int]:
        """
        Hạ mức chống-kill từ -1000 về mức an toàn (-300) để tránh sập toàn bộ thiết bị khi hết RAM.
        Thực hiện đọc lại /proc/<pid>/oom_score_adj để xác nhận thực tế đã áp dụng thành công.
        """
        if pid <= 0:
            return False, 0

        # Ép score vào khoảng [-300, 1000] an toàn
        safe_score = max(-300, min(1000, score))
        write_sh = f"echo {safe_score} > /proc/{pid}/oom_score_adj"
        read_sh = f"cat /proc/{pid}/oom_score_adj"

        try:
            cmd_write = self._build_shell_cmd(["su", "-c", write_sh])
            subprocess.run(cmd_write, capture_output=True, text=True, timeout=2)
        except Exception:
            pass

        actual_score = 0
        try:
            cmd_read = self._build_shell_cmd(["su", "-c", read_sh])
            res = subprocess.run(cmd_read, capture_output=True, text=True, timeout=2)
            out = res.stdout.strip()
            if out and (out.isdigit() or (out.startswith("-") and out[1:].isdigit())):
                actual_score = int(out)
                logger.info(f"🛡️ [OOM Shield] Đã áp dụng oom_score_adj cho PID {pid}: {actual_score} (Target: {safe_score})")
                return (actual_score == safe_score), actual_score
        except Exception as e:
            logger.debug(f"Không thể đọc lại oom_score_adj: {e}")

        return False, actual_score

    def evaluate_line(self, line: str) -> None:
        """Phân tích 1 dòng logcat theo bộ Regex của droidblox-kt"""
        # 1. Bắt sự kiện Joining game
        match_join = LogcatPatterns.GAME_JOINING.search(line)
        if match_join:
            job_id = match_join.group(1)
            place_id = int(match_join.group(2))
            server_ip = match_join.group(3)
            self.session.job_id = job_id
            self.session.place_id = place_id
            self.session.server_ip = server_ip
            self.session.last_active = time.time()
            if self.callback:
                self.callback("GAME_JOINING", {
                    "job_id": job_id,
                    "place_id": place_id,
                    "server_ip": server_ip
                })
            return

        # 2. Bắt Universe & User
        match_universe = LogcatPatterns.GAME_JOINING_UNIVERSE.search(line)
        if match_universe:
            user_id = int(match_universe.group(1))
            universe_id = int(match_universe.group(2))
            self.session.user_id = user_id
            self.session.universe_id = universe_id
            if self.callback:
                self.callback("UNIVERSE_JOINING", {
                    "user_id": user_id,
                    "universe_id": universe_id
                })
            return

        # 3. Bắt UDMUX Address
        match_udmux = LogcatPatterns.GAME_JOINING_UDMUX.search(line)
        if match_udmux:
            udmux_ip = match_udmux.group(1)
            self.session.udmux_ip = udmux_ip
            if self.callback:
                self.callback("UDMUX_FOUND", {"udmux_ip": udmux_ip})
            return

        # 4. Bắt Game Joined thành công
        if LogcatPatterns.GAME_JOINED_KEYWORD in line:
            self.session.joined_at = time.time()
            self.session.last_active = time.time()
            if self.callback:
                self.callback("GAME_JOINED", {
                    "place_id": self.session.place_id,
                    "job_id": self.session.job_id
                })
            return

        # 5. Bắt Game Disconnected
        if LogcatPatterns.GAME_DISCONNECTED_KEYWORD in line:
            error_match = LogcatPatterns.ERROR_CODE_PATTERN.search(line)
            err_code = error_match.group(1) if error_match else "UNKNOWN"
            self.session.disconnect_reason = f"Network Disconnect (Code: {err_code})"
            if self.callback:
                self.callback("GAME_DISCONNECTED", {
                    "reason": self.session.disconnect_reason,
                    "place_id": self.session.place_id,
                    "job_id": self.session.job_id
                })
            return

    def _logcat_worker(self) -> None:
        """Luồng đọc logcat liên tục"""
        # Xóa buffer logcat cũ trước khi đọc
        try:
            subprocess.run(self._build_shell_cmd(["logcat", "-c"]), capture_output=True, timeout=2)
        except Exception:
            pass

        logcat_cmd = self._build_shell_cmd(["logcat", "-v", "raw", "-s", "Roblox:*", "FLog:*"])
        try:
            process = subprocess.Popen(
                logcat_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            while self._running and process.poll() is None:
                line = process.stdout.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                self.evaluate_line(line)
            if process.poll() is None:
                process.terminate()
        except Exception as e:
            logger.error(f"Lỗi trong luồng đọc logcat: {e}")

    def start_watcher(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._logcat_worker, daemon=True)
        self._thread.start()

    def stop_watcher(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)


class AndroidRejoinController:
    """
    Bộ điều khiển Auto-Rejoin Roblox trên Android.
    Bao gồm State Machine, Circuit Breaker và cơ chế Deep Link Intent.
    """

    def __init__(
        self,
        default_place_id: int = 2753915549,  # Default: Blox Fruits
        default_job_id: Optional[str] = None,
        user_slot: int = 0,
        adb_bin: Optional[str] = None,
        device_id: Optional[str] = None,
        cooldown_sec: int = 15,
        max_consecutive_fails: int = 3,
        circuit_cooldown_sec: int = 45,
        discord_webhook_url: Optional[str] = None
    ):
        self.place_id = default_place_id
        self.job_id = default_job_id
        self.user_slot = user_slot
        self.adb_bin = adb_bin
        self.device_id = device_id
        self.cooldown_sec = cooldown_sec
        self.max_consecutive_fails = max_consecutive_fails
        self.circuit_cooldown_sec = circuit_cooldown_sec
        self.discord_webhook_url = discord_webhook_url

        self.state = RejoinState.IDLE
        self.rejoin_count = 0
        self.consecutive_fails = 0
        self.last_rejoin_time = 0.0
        self.running = False

        self.watcher = AndroidRobloxWatcher(
            adb_bin=self.adb_bin,
            device_id=self.device_id,
            on_event_callback=self._handle_watcher_event
        )

    def _build_shell_cmd(self, subcmd: List[str]) -> List[str]:
        if self.adb_bin and self.device_id:
            return [self.adb_bin, "-s", self.device_id, "shell"] + subcmd
        elif self.adb_bin:
            return [self.adb_bin, "shell"] + subcmd
        else:
            return subcmd

    def _send_discord_alert(self, title: str, description: str, color: int = 0x00FFAA) -> None:
        """Gửi thông báo webhook qua Discord Rich Embeds nếu có cấu hình"""
        if not self.discord_webhook_url:
            return
        try:
            from network.roblox_presence import presence_tracker
            game_icon = presence_tracker.get_game_icon(str(self.place_id))
            payload = {
                "embeds": [{
                    "title": f"⚡ [Roblox Android Sentinel] {title}",
                    "description": description,
                    "color": color,
                    "thumbnail": {"url": game_icon},
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "footer": {"text": "Powered by DroidBlox & LxstCxn Telemetry Hub"}
                }]
            }
            import urllib.request
            import json
            req = urllib.request.Request(
                self.discord_webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
            )
            urllib.request.urlopen(req, timeout=4)
        except Exception as e:
            logger.warning(f"Không thể gửi Discord Webhook: {e}")

    def build_launch_intent_cmd(self, place_id: Optional[int] = None, job_id: Optional[str] = None) -> List[str]:
        """
        Tạo lệnh khởi chạy Android Intent dựa trên mẫu LaunchRoblox.kt của droidblox-kt:
        am start [-n com.roblox.client/com.roblox.client.ActivityProtocolLaunch] -d "roblox://experiences/start?placeId=...&gameInstanceId=..."
        """
        pid = place_id or self.place_id
        jid = job_id or self.job_id

        target_uri = f"roblox://experiences/start?placeId={pid}"
        if jid:
            target_uri += f"&gameInstanceId={jid}"

        intent_args = ["am", "start"]
        if self.user_slot > 0:
            intent_args += ["--user", str(self.user_slot)]

        # Sử dụng Action VIEW và Component ActivityProtocolLaunch
        intent_args += [
            "-a", "android.intent.action.VIEW",
            "-d", target_uri,
            "-n", "com.roblox.client/com.roblox.client.ActivityProtocolLaunch"
        ]
        return self._build_shell_cmd(intent_args)

    def launch_roblox(self, place_id: Optional[int] = None, job_id: Optional[str] = None) -> bool:
        """Kích hoạt Intent mở lại Roblox an toàn"""
        cmd = self.build_launch_intent_cmd(place_id, job_id)
        target_pid = place_id or self.place_id
        target_jid = job_id or self.job_id
        logger.info(f"🚀 Gửi Intent mở Roblox (Place: {target_pid}, Job: {target_jid or 'Auto'})...")

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 or "Starting:" in res.stdout:
                logger.info("✅ Gửi Intent thành công.")
                return True
        except Exception as e:
            logger.error(f"Lỗi khi gửi Intent: {e}")

        # Fallback qua su nếu có quyền root
        try:
            su_subcmd = f"am start -a android.intent.action.VIEW -d 'roblox://experiences/start?placeId={target_pid}'"
            if target_jid:
                su_subcmd = f"am start -a android.intent.action.VIEW -d 'roblox://experiences/start?placeId={target_pid}&gameInstanceId={target_jid}'"
            su_cmd = self._build_shell_cmd(["su", "-c", su_subcmd])
            res = subprocess.run(su_cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                logger.info("✅ Fallback Root Intent thành công.")
                return True
        except Exception:
            pass

        return False

    def _handle_watcher_event(self, event_name: str, data: Dict) -> None:
        """Xử lý sự kiện nhận được từ luồng Logcat Watcher"""
        if event_name == "GAME_JOINING":
            logger.info(f"🎯 [WATCHER] Đang kết nối Place {data.get('place_id')} | Job ID: {data.get('job_id')}")
            # Cập nhật thông tin session mới nhất để rejoin chuẩn xác
            self.place_id = data.get("place_id", self.place_id)
            self.job_id = data.get("job_id", self.job_id)
            self.state = RejoinState.CONNECTING

        elif event_name == "UDMUX_FOUND":
            udmux_ip = data.get("udmux_ip", "")
            from network.roblox_datacenter_resolver import datacenter_resolver
            loc_info = datacenter_resolver.resolve_udmux_ip(udmux_ip)
            logger.info(f"🌐 [WATCHER] UDMUX Gateway: {udmux_ip} ➔ {loc_info['flag']} {loc_info['city']} ({loc_info['country_name']})")

        elif event_name == "UNIVERSE_JOINING":
            logger.info(f"👤 [WATCHER] User ID: {data.get('user_id')} | Universe ID: {data.get('universe_id')}")

        elif event_name == "GAME_JOINED":
            logger.info(f"🟢 [WATCHER] Đã vào Server thành công! (Place: {self.place_id})")
            self.state = RejoinState.IN_GAME
            self.consecutive_fails = 0  # Reset Circuit Breaker

        elif event_name == "GAME_DISCONNECTED":
            reason = data.get("reason", "Unknown")
            logger.warning(f"🔴 [WATCHER] Mất kết nối ({reason})! Kích hoạt quy trình Auto-Rejoin...")
            self.state = RejoinState.DISCONNECTED
            self.trigger_rejoin(reason=reason)

    def trigger_rejoin(self, reason: str = "Client Disconnected") -> bool:
        """Kích hoạt quy trình Rejoin với kiểm tra Circuit Breaker"""
        now = time.time()
        # Tránh trigger liên tục quá nhanh (< 5s)
        if now - self.last_rejoin_time < 5.0:
            return False

        self.last_rejoin_time = now

        # 1. Kiểm tra Circuit Breaker
        if self.consecutive_fails >= self.max_consecutive_fails:
            self.state = RejoinState.COOLDOWN
            msg = f"⚠️ Circuit Breaker: Đã thất bại {self.consecutive_fails} lần liên tiếp. Tạm dừng {self.circuit_cooldown_sec}s để chống spam CPU."
            logger.warning(msg)
            self._send_discord_alert("Circuit Breaker Activated", msg, color=0xFFAA00)
            time.sleep(self.circuit_cooldown_sec)
            self.consecutive_fails = 0

        self.consecutive_fails += 1
        self.rejoin_count += 1
        self.state = RejoinState.LAUNCHING

        desc = f"Lý do: **{reason}**\nPlace ID: `{self.place_id}`\nJob ID: `{self.job_id or 'Auto Server'}`\nLần thử: `{self.consecutive_fails}/{self.max_consecutive_fails}` (Tổng: {self.rejoin_count} lần)"
        self._send_discord_alert("🔄 Đang thực hiện Auto-Rejoin", desc, color=0x3498DB)

        # 2. Đóng tiến trình cũ nếu còn treo
        try:
            subprocess.run(self._build_shell_cmd(["am", "force-stop", "com.roblox.client"]), capture_output=True, timeout=3)
            time.sleep(1.0)
        except Exception:
            pass

        # 3. Gửi Intent khởi động lại
        success = self.launch_roblox()
        if success:
            logger.info(f"⏳ Chờ game khởi động và nạp bản đồ ({self.cooldown_sec}s cooldown)...")
            time.sleep(self.cooldown_sec)
        return success

    def deep_check_vote_keep_alive(self, pid: int, api_reported_offline: bool = False) -> bool:
        """
        Deep-check phiếu bầu không-kill (Vote Keep-Alive):
        Ưu tiên tín hiệu thực tế trên thiết bị (Logcat active, PID running, heartbeat gần nhất)
        đè lên thông tin Offline trễ của Roblox API.
        """
        if pid <= 0:
            return False

        # Tín hiệu 1: Logcat đang xác nhận IN_GAME hoặc CONNECTING
        if self.state in [RejoinState.IN_GAME, RejoinState.CONNECTING]:
            logger.info(f"🛡️ [DEEP-CHECK] BỎ QUA API Offline! Logcat xác nhận game đang chạy (State: {self.state.value}, PID: {pid}).")
            return True

        # Tín hiệu 2: Tương tác gần nhất trên máy < 45s
        last_act = self.watcher.session.last_active
        if last_act > 0 and (time.time() - last_act < 45.0):
            logger.info(f"🛡️ [DEEP-CHECK] BỎ QUA API Offline! Tín hiệu trên máy active cách đây {int(time.time() - last_act)}s.")
            return True

        # Tín hiệu 3: Tiến trình Roblox PID vẫn sống trên thiết bị
        if pid > 0:
            logger.info(f"🛡️ [DEEP-CHECK] BỎ QUA API Offline! Tiến trình Roblox PID {pid} đang chạy thực tế trên thiết bị.")
            return True

        return False

    def run_monitor_loop(self, poll_interval: float = 3.0) -> None:
        """Vòng lặp giám sát chính (Watchdog Loop)"""
        self.running = True
        self.watcher.start_watcher()
        logger.info("🛰️ Khởi động Roblox Android Rejoin Sentinel thành công!")
        logger.info(f"   Place ID: {self.place_id} | User Slot: --user {self.user_slot} | Interval: {poll_interval}s")

        last_oom_pid = 0
        try:
            while self.running:
                pid = self.watcher.get_roblox_pid()

                if pid > 0:
                    # Ép mức OOM protection an toàn (-300) kèm readback xác nhận
                    if pid != last_oom_pid:
                        self.watcher.set_oom_score_adj(pid, score=-300)
                        last_oom_pid = pid

                    if self.state in [RejoinState.IDLE, RejoinState.LAUNCHING, RejoinState.DISCONNECTED, RejoinState.CRASHED]:
                        self.state = RejoinState.IN_GAME
                else:
                    # PID = 0 -> Game đã bị tắt hoặc crash. Kiểm tra phiếu bầu không-kill
                    if self.state == RejoinState.IN_GAME:
                        if not self.deep_check_vote_keep_alive(pid):
                            logger.warning("💥 [WATCHDOG] Phát hiện tiến trình Roblox biến mất (PID = 0 / Crash)!")
                            self.state = RejoinState.CRASHED
                            self.trigger_rejoin(reason="App Crash / PID Disappeared")
                        else:
                            logger.info("🛡️ [WATCHDOG] Deep-check bảo vệ: Không kích hoạt kill/rejoin do nhận tín hiệu active.")

                time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("🛑 Nhận tín hiệu dừng từ người dùng.")
        finally:
            self.stop()

    def stop(self) -> None:
        self.running = False
        self.watcher.stop_watcher()
        self.state = RejoinState.IDLE
        logger.info("Đã dừng Rejoin Controller an toàn.")
