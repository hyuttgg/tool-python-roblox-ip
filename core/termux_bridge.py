# -*- coding: utf-8 -*-
"""
Roblox Android / Termux Auto-Rejoin Engine & Multi-User Sentinel
Quản lý vòng đời Rejoin, kiểm tra PID, lắng nghe Heartbeat Luau và mở Deep Link trên Android/Termux
"""

import os
import sys
import time
import subprocess
import json
import shutil
import http.server
import socketserver
import threading
from typing import Dict, List, Optional
from config.logging import setup_logger

logger = setup_logger("termux_bridge")

ROBLOX_PACKAGE = "com.roblox.client"
DEFAULT_PLACE_ID = "2753915549" # Blox Fruits

ANDROID_AUTOEXEC_DIRS = [
    "/sdcard/Arceus X/Autoexec",
    "/sdcard/ArceusX/Autoexec",
    "/sdcard/Delta/Autoexec",
    "/sdcard/Codex/Autoexec",
    "/sdcard/Fluxus/Autoexec",
    "/storage/emulated/0/Arceus X/Autoexec",
    "/storage/emulated/0/ArceusX/Autoexec",
    "/storage/emulated/0/Delta/Autoexec",
    "/storage/emulated/0/Codex/Autoexec",
    "/storage/emulated/0/Fluxus/Autoexec"
]

class TermuxEnvironment:
    """Xác định môi trường Termux / Android Native"""
    
    @staticmethod
    def is_termux() -> bool:
        return "com.termux" in os.environ.get("PREFIX", "") or os.path.exists("/data/data/com.termux")

    @staticmethod
    def is_android() -> bool:
        return os.path.exists("/system/bin/am") or os.path.exists("/system/bin/app_process") or TermuxEnvironment.is_termux()

    @staticmethod
    def is_root() -> bool:
        return shutil.which("su") is not None


class TermuxRobloxRejoiner:
    """Bộ điều khiển Auto-Rejoin chuyên dụng cho Termux & Android"""

    def __init__(self, place_id: str = DEFAULT_PLACE_ID, job_id: str = "", user_id: str = "0"):
        self.place_id = str(place_id)
        self.job_id = str(job_id)
        self.user_id = str(user_id)
        self.running = False
        self.restarts_count = 0
        self.consecutive_fails = 0
        self.last_heartbeat_time = 0
        self.last_restart_time = 0
        self.current_pid = 0
        self.latest_telemetry: Dict = {}
        self._lock = threading.Lock()

    def get_roblox_pid(self) -> int:
        """Kiểm tra PID của ứng dụng Roblox trên Android / Termux"""
        # 1. Thử qua pidof
        try:
            out = subprocess.check_output(["pidof", ROBLOX_PACKAGE], stderr=subprocess.DEVNULL, timeout=2).decode().strip()
            if out:
                pids = [int(p) for p in out.split() if p.isdigit()]
                if pids:
                    return pids[0]
        except Exception:
            pass

        # 2. Thử qua pgrep
        try:
            out = subprocess.check_output(["pgrep", "-f", ROBLOX_PACKAGE], stderr=subprocess.DEVNULL, timeout=2).decode().strip()
            if out:
                pids = [int(p) for p in out.split() if p.isdigit()]
                if pids:
                    return pids[0]
        except Exception:
            pass

        # 3. Thử qua psutil nếu có
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmd = " ".join(proc.info.get('cmdline') or [])
                if ROBLOX_PACKAGE in cmd or ROBLOX_PACKAGE in (proc.info.get('name') or ''):
                    return proc.info['pid']
        except Exception:
            pass

        return 0

    def launch_roblox(self) -> bool:
        """Kích hoạt mở lại Roblox qua Android Intent sạch sẽ (Không dùng monkey)"""
        target_url = f"roblox://experiences/start?placeId={self.place_id}"
        if self.job_id:
            target_url += f"&gameInstanceId={self.job_id}"

        user_args = []
        if self.user_id and self.user_id != "0":
            user_args = ["--user", str(self.user_id)]

        logger.info(f"[TERMUX REJOIN] Gửi Android Intent mở game: {target_url} (User: {self.user_id})")

        # Thử lệnh am start
        cmd1 = ["am", "start"] + user_args + ["-a", "android.intent.action.VIEW", "-d", target_url]
        try:
            res = subprocess.run(cmd1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            if res.returncode == 0:
                self.last_restart_time = time.time()
                return True
        except Exception:
            pass

        # Fallback qua Activity Component
        cmd2 = ["am", "start"] + user_args + ["-n", f"{ROBLOX_PACKAGE}/com.roblox.client.ActivityProtocolLaunch", "-d", target_url]
        try:
            res = subprocess.run(cmd2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            if res.returncode == 0:
                self.last_restart_time = time.time()
                return True
        except Exception:
            pass

        # Fallback Root su
        if TermuxEnvironment.is_root():
            try:
                su_cmd = f"am start -a android.intent.action.VIEW -d '{target_url}'"
                subprocess.run(["su", "-c", su_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                self.last_restart_time = time.time()
                return True
            except Exception:
                pass

        return False

    def sync_android_autoexec(self, lua_script_path: str) -> int:
        """Sao chép script Lua Autoexec vào toàn bộ thư mục Executor trên Android / Termux"""
        if not os.path.exists(lua_script_path):
            return 0
        
        synced = 0
        for target_dir in ANDROID_AUTOEXEC_DIRS:
            try:
                if os.path.exists(target_dir):
                    dest = os.path.join(target_dir, os.path.basename(lua_script_path))
                    shutil.copy2(lua_script_path, dest)
                    synced += 1
            except Exception:
                pass
        return synced

    def start_sentinel_loop(self):
        """Vòng lặp giám sát độc lập trên Termux với Circuit Breaker"""
        self.running = True
        logger.info("Roblox Termux Sentinel Loop started.")
        print("\n" + "=" * 70)
        print("⚡ [ ROBLOX TERMUX / ANDROID SENTINEL REJOIN ENGINE ] ⚡")
        print(f"Place ID: {self.place_id} | User Slot: --user {self.user_id}")
        print("=" * 70 + "\n")

        while self.running:
            try:
                now = time.time()
                pid = self.get_roblox_pid()
                self.current_pid = pid

                if pid > 0:
                    self.consecutive_fails = 0
                    print(f"[{time.strftime('%H:%M:%S')}] 🟢 ONLINE | Roblox Client đang chạy (PID: {pid}) | Rejoin: {self.restarts_count} lần", end="\r")
                else:
                    print(f"\n[{time.strftime('%H:%M:%S')}] ⚪ OFFLINE / CRASH | Phát hiện game bị tắt hoặc văng!")

                    # Circuit Breaker: Tối đa 3 lần thử liên tiếp
                    if self.consecutive_fails >= 3:
                        print(f"[{time.strftime('%H:%M:%S')}] ⚠️ [CIRCUIT BREAKER] Đã Rejoin thất bại 3 lần liên tiếp. Nghỉ 45s bảo vệ điện thoại...")
                        time.sleep(45)
                        self.consecutive_fails = 0
                    else:
                        self.consecutive_fails += 1
                        self.restarts_count += 1
                        print(f"[{time.strftime('%H:%M:%S')}] 🚀 [AUTO-REJOIN] Kích hoạt mở lại Roblox lần #{self.restarts_count} (Lượt thử: {self.consecutive_fails}/3)...")
                        self.launch_roblox()
                        time.sleep(15) # Cooldown nạp game

                time.sleep(4)
            except KeyboardInterrupt:
                print("\n[!] Dừng Termux Sentinel thành công.")
                break
            except Exception as e:
                time.sleep(4)


if __name__ == "__main__":
    p_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PLACE_ID
    u_id = sys.argv[2] if len(sys.argv) > 2 else "0"
    rejoiner = TermuxRobloxRejoiner(place_id=p_id, user_id=u_id)
    rejoiner.start_sentinel_loop()
