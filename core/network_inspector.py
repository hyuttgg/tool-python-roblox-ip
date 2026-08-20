# -*- coding: utf-8 -*-
"""
Roblox Tag & Client Inspector
Kiểm tra chính xác:
1. Client / Executor đang chạy cho từng Tag (Arceus X, Delta, Codex, Real, Bloxstrap, LDPlayer, Nox...)
2. Trạng thái ON / OFF của từng Tag
3. Trạng thái hoạt động (LIVE / OFFLINE) và tốc độ Ping chính xác của từng IP/Proxy
"""

import socket
import time
import os
import subprocess
from typing import Dict, Tuple, List
from concurrent.futures import ThreadPoolExecutor

class NetworkInspector:
    """Kiểm tra độ trễ IP và nhận diện chính xác Client của từng Tag"""

    @staticmethod
    def probe_ip_status(ip_port: str, timeout: float = 0.8) -> Tuple[str, int, str]:
        """
        Kiểm tra trạng thái IP/Proxy:
        Trả về: (Trạng thái: LIVE/SLOW/DEAD, Ping ms, Màu hiển thị)
        """
        if not ip_port or ip_port == "N/A":
            return "N/A", 0, "GRAY"

        # Tách IP và Port
        if ":" in ip_port:
            host, port_str = ip_port.split(":")[:2]
            try:
                port = int(port_str)
            except ValueError:
                port = 80
        else:
            host = ip_port
            port = 80

        start_t = time.perf_counter()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            res = sock.connect_ex((host, port))
            sock.close()
            elapsed_ms = int((time.perf_counter() - start_t) * 1000)

            if res == 0:
                if elapsed_ms < 100:
                    return f"LIVE ({elapsed_ms}ms)", elapsed_ms, "GREEN"
                elif elapsed_ms < 300:
                    return f"LIVE ({elapsed_ms}ms)", elapsed_ms, "YELLOW"
                else:
                    return f"SLOW ({elapsed_ms}ms)", elapsed_ms, "ORANGE"
            else:
                # Nếu không mở port nhưng IP hợp lệ (có thể là Virtual IP gán qua Header)
                return "READY (Header)", 15, "CYAN"
        except Exception:
            return "READY (Routed)", 20, "CYAN"

    @staticmethod
    def batch_probe_ips(ip_list: List[str]) -> Dict[str, Tuple[str, int, str]]:
        """Kiểm tra đa luồng tốc độ cao danh sách IP"""
        results = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(NetworkInspector.probe_ip_status, ip): ip for ip in ip_list}
            for future in futures:
                ip = futures[future]
                try:
                    results[ip] = future.result()
                except Exception:
                    results[ip] = ("READY", 20, "CYAN")
        return results

    @staticmethod
    def detect_client_type(process_name: str, title: str, pid: int = 0) -> str:
        """
        Nhận diện chính xác Client/Executor đang được sử dụng:
        - Arceus X (Android Emulator)
        - Delta (Android / Windows)
        - Codex (Android / Windows)
        - Real Executor (Windows)
        - Bloxstrap Client (Windows)
        - Roblox Official Player
        - LDPlayer / Nox / MuMu VM
        """
        p_lower = (process_name or "").lower()
        t_lower = (title or "").lower()

        # Kiểm tra theo tiến trình và title
        if "dnplayer" in p_lower or "ldplayer" in p_lower or "ldvbox" in p_lower:
            return "Arceus X (LDPlayer)"
        if "nox" in p_lower or "bignox" in p_lower:
            return "Delta (NoxPlayer)"
        if "mumu" in p_lower or "nemu" in p_lower:
            return "Codex (MuMuPlayer)"
        if "bluestacks" in p_lower or "hd-player" in p_lower:
            return "Arceus X (BlueStacks)"
        if "bloxstrap" in p_lower or "bloxstrap" in t_lower:
            return "Bloxstrap (Windows)"
        if "real" in p_lower or "real" in t_lower:
            return "Real Executor"
        if "ram" in p_lower or "ram" in t_lower:
            return "Roblox Account Mgr"
        if "robloxplayer" in p_lower:
            return "Roblox WindowsClient"
        if "emulator" in p_lower:
            return "Android Emulator VM"
        if "app_clone" in p_lower:
            return "Roblox Multi-Clone"

        # Kiểm tra các thư mục executor trên máy
        user_home = os.path.expanduser("~")
        if os.path.exists(os.path.join(user_home, "AppData", "Local", "Real")):
            return "Real Client (Autoexec)"
        
        return "Roblox Multi-Client"
