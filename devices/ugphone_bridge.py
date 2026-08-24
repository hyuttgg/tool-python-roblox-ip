# -*- coding: utf-8 -*-
"""
UGPhone & Android Java Network Bridge
Cầu nối Python - Java / ADB để can thiệp và thiết lập Proxy, Autoexec cho ứng dụng Roblox
trên điện thoại đám mây UGPhone, VMOS, Redfinger và các thiết bị Android.
"""

import os
import subprocess
import shutil
import json
from typing import List, Dict, Optional, Tuple
from config.logging import setup_logger

logger = setup_logger("ugphone_bridge")

class UGPhoneBridge:
    """Quản lý kết nối và can thiệp Proxy cho Roblox trên UGPhone qua Android ADB & Java Environment"""

    def __init__(self, adb_path: Optional[str] = None):
        self.adb_bin = adb_path or self._find_adb()
        self.connected_devices: List[str] = []
        self.refresh_devices()

    def _find_adb(self) -> Optional[str]:
        # 1. Tìm ADB trong PATH
        path_adb = shutil.which("adb")
        if path_adb:
            return path_adb
        
        # 2. Tìm ADB tại các vị trí mặc định
        candidates = [
            r"C:\LDPlayer\LDPlayer9\adb.exe",
            r"D:\LDPlayer\LDPlayer9\adb.exe",
            r"C:\Program Files\Nox\bin\nox_adb.exe",
            r"C:\Program Files (x86)\MuMuPlayerGlobal-12.0\shell\adb.exe",
            r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    def connect_ugphone(self, host: str, port: int = 5555) -> Tuple[bool, str]:
        """Kết nối tới điện thoại đám mây UGPhone qua Wireless ADB"""
        if not self.adb_bin:
            return False, "Không tìm thấy công cụ ADB trên máy tính."

        target = f"{host}:{port}"
        try:
            res = subprocess.run([self.adb_bin, "connect", target], capture_output=True, text=True, timeout=5)
            output = res.stdout.strip()
            self.refresh_devices()
            if "connected" in output.lower():
                logger.info(f"Connected to UGPhone device: {target}")
                return True, f"Kết nối thành công tới UGPhone: {target}"
            else:
                return False, f"Kết quả kết nối: {output}"
        except Exception as e:
            return False, f"Lỗi kết nối ADB: {e}"

    def refresh_devices(self) -> List[str]:
        """Lấy danh sách các thiết bị UGPhone / Android đang kết nối"""
        self.connected_devices = []
        if not self.adb_bin:
            return []

        try:
            output = subprocess.check_output([self.adb_bin, "devices"], timeout=3).decode("utf-8")
            for line in output.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == "device":
                    self.connected_devices.append(parts[0])
        except Exception:
            pass
        return self.connected_devices

    def set_android_proxy(self, device_id: str, proxy_host: str, proxy_port: int) -> bool:
        """
        Thiết lập Proxy ở tầng Android System Settings qua ADB:
        Tất cả các gói tin từ Roblox và Executor sẽ tự động định tuyến qua Proxy này.
        """
        if not self.adb_bin or device_id not in self.connected_devices:
            return False

        try:
            proxy_str = f"{proxy_host}:{proxy_port}"
            subprocess.run([self.adb_bin, "-s", device_id, "shell", "settings", "put", "global", "http_proxy", proxy_str], timeout=3)
            logger.info(f"Set global http_proxy on UGPhone [{device_id}] -> {proxy_str}")
            return True
        except Exception as e:
            logger.error(f"Error setting proxy on {device_id}: {e}")
            return False

    def clear_android_proxy(self, device_id: str) -> bool:
        """Xóa thiết lập Proxy trên UGPhone (trở về mạng gốc)"""
        if not self.adb_bin or device_id not in self.connected_devices:
            return False

        try:
            subprocess.run([self.adb_bin, "-s", device_id, "shell", "settings", "put", "global", "http_proxy", ":0"], timeout=3)
            logger.info(f"Cleared global http_proxy on UGPhone [{device_id}]")
            return True
        except Exception as e:
            logger.error(f"Error clearing proxy on {device_id}: {e}")
            return False

    def apply_deep_iptables_tproxy(self, device_id: str, proxy_host: str = "127.0.0.1", proxy_port: int = 10808, dns_server: str = "1.1.1.1") -> Tuple[bool, str]:
        """Kích hoạt can thiệp mạng sâu TPROXY / IPTables Per-UID (Stealth No-VPN Icon)"""
        if not self.adb_bin or device_id not in self.connected_devices:
            return False, "Thiết bị không kết nối hoặc không tìm thấy ADB."
        from network.deep_interceptor import AndroidDeepInterceptor
        return AndroidDeepInterceptor.apply_tproxy_to_android_device(
            adb_bin=self.adb_bin,
            device_id=device_id,
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            dns_server=dns_server
        )

    def clear_deep_iptables_tproxy(self, device_id: str) -> Tuple[bool, str]:
        """Gỡ bỏ can thiệp sâu IPTables trên thiết bị Android"""
        if not self.adb_bin or device_id not in self.connected_devices:
            return False, "Thiết bị không kết nối hoặc không tìm thấy ADB."
        from network.deep_interceptor import AndroidDeepInterceptor
        return AndroidDeepInterceptor.revert_tproxy_on_android_device(
            adb_bin=self.adb_bin,
            device_id=device_id
        )

    def get_roblox_status(self, device_id: str) -> Dict[str, str]:
        """Kiểm tra trạng thái cài đặt và tiến trình của Roblox trên UGPhone"""
        if not self.adb_bin or device_id not in self.connected_devices:
            return {"installed": "No", "running": "No", "pid": "0"}

        info = {"installed": "No", "running": "No", "pid": "0"}
        try:
            # 1. Kiểm tra package com.roblox.client
            pkg_res = subprocess.check_output([self.adb_bin, "-s", device_id, "shell", "pm", "list", "packages", "com.roblox.client"], timeout=3).decode("utf-8")
            if "com.roblox.client" in pkg_res:
                info["installed"] = "Yes"

            # 2. Kiểm tra tiến trình đang chạy
            pid_res = subprocess.check_output([self.adb_bin, "-s", device_id, "shell", "pidof", "com.roblox.client"], timeout=3).decode("utf-8").strip()
            if pid_res:
                info["running"] = "Yes"
                info["pid"] = pid_res
        except Exception:
            pass
        return info

    def inject_autoexec_lua(self, device_id: str, lua_file_path: str) -> bool:
        """Bơm trực tiếp file Lua vào thư mục Autoexec của Arceus X / Delta trên UGPhone"""
        if not self.adb_bin or device_id not in self.connected_devices:
            return False

        sdcard_destinations = [
            "/sdcard/Arceus X/Autoexec/roblox_auto_ip_setter.lua",
            "/sdcard/Delta/Autoexec/roblox_auto_ip_setter.lua",
            "/sdcard/Codex/Autoexec/roblox_auto_ip_setter.lua",
            "/storage/emulated/0/Arceus X/Autoexec/roblox_auto_ip_setter.lua",
            "/storage/emulated/0/Delta/Autoexec/roblox_auto_ip_setter.lua",
        ]

        success = False
        for dst in sdcard_destinations:
            try:
                parent_dir = os.path.dirname(dst)
                subprocess.run([self.adb_bin, "-s", device_id, "shell", "mkdir", "-p", f'"{parent_dir}"'], capture_output=True, timeout=2)
                res = subprocess.run([self.adb_bin, "-s", device_id, "push", lua_file_path, dst], capture_output=True, timeout=3)
                if res.returncode == 0:
                    success = True
                    logger.info(f"Injected Autoexec Lua to UGPhone [{device_id}]: {dst}")
            except Exception:
                pass
        return success

    def launch_roblox_app(self, device_id: str, place_id: str = "2753915549") -> Tuple[bool, str]:
        """Khởi chạy ứng dụng Roblox Client và vào đúng Game Place ID trên Android / UGPhone qua ADB"""
        if not self.adb_bin or device_id not in self.connected_devices:
            return False, f"Thiết bị [{device_id}] không kết nối hoặc không tìm thấy ADB."

        url = f"roblox://experiences/start?placeId={place_id}"
        intents = [
            f"am start -a android.intent.action.VIEW -d '{url}'",
            f"am start -n com.roblox.client/com.roblox.client.ActivityProtocolLaunch -d '{url}'",
            "am start -n com.roblox.client/com.roblox.client.RobloxMainActivity",
            "monkey -p com.roblox.client -c android.intent.category.LAUNCHER 1"
        ]

        for intent_cmd in intents:
            try:
                res = subprocess.run([self.adb_bin, "-s", device_id, "shell", intent_cmd], capture_output=True, text=True, timeout=4)
                if res.returncode == 0 or "Starting:" in res.stdout or "Events injected: 1" in res.stdout:
                    logger.info(f"Launched Roblox on Android [{device_id}] via {intent_cmd}")
                    return True, f"Khởi chạy thành công trên [{device_id}] (PlaceId: {place_id})"
            except Exception:
                continue

        try:
            su_cmd = f"su -c 'am start -a android.intent.action.VIEW -d \"{url}\"'"
            res = subprocess.run([self.adb_bin, "-s", device_id, "shell", su_cmd], capture_output=True, text=True, timeout=4)
            if res.returncode == 0:
                return True, f"Khởi chạy Root thành công trên [{device_id}]"
        except Exception:
            pass

        return False, "Không thể khởi chạy Roblox qua ADB Intents."



class JavaNetworkBridge:
    """Cầu nối thực thi và tích hợp mã Java chuyên sâu với Python Controller"""

    JAVA_SOURCE_FILE = os.path.join(os.path.dirname(__file__), "RobloxDeepNetworkEngine.java")

    @classmethod
    def is_java_available(cls) -> bool:
        """Kiểm tra môi trường Java có sẵn sàng trên máy không"""
        return shutil.which("java") is not None

    @classmethod
    def execute_java_diagnostics(cls, host: str, port: int, target_domain: str = "www.roblox.com") -> Dict:
        """Thực thi kiểm tra chẩn đoán kết nối tầng sâu qua Java Engine nếu có Java"""
        if cls.is_java_available():
            try:
                cmd = ["java", "-cp", os.path.dirname(__file__), "com.roblox.network.RobloxDeepNetworkEngine", "--diagnose", host, str(port), target_domain]
                out = subprocess.check_output(cmd, timeout=4).decode("utf-8").strip()
                return json.loads(out)
            except Exception:
                pass
        
        # Fallback socket diagnostics nếu môi trường chưa cài JDK
        import socket
        import time
        start = time.time()
        try:
            with socket.create_connection((host, int(port)), timeout=2):
                latency = int((time.time() - start) * 1000)
                return {"proxy": f"{host}:{port}", "tcp_latency_ms": latency, "proxy_status": "ONLINE", "mode": "Socket-Fallback"}
        except Exception as e:
            return {"proxy": f"{host}:{port}", "tcp_latency_ms": -1, "proxy_status": "OFFLINE", "error": str(e)}


class UGPhoneNetworkEngine:
    """Điều phối quét và quản lý thiết bị đám mây UGPhone"""

    @classmethod
    def scan_cloud_devices(cls) -> List[Dict]:
        try:
            bridge = UGPhoneBridge()
            devices = bridge.refresh_devices()
            return [{"device_id": f"UGPHONE-{d.replace(':', '_').replace('.', '_')}", "ip": d, "status": "ONLINE"} for d in devices]
        except Exception:
            return []


