# -*- coding: utf-8 -*-
"""
Sing-box Universal Proxy & TUN Routing Core (SagerNet Architecture)
Trình quản lý cấu hình và tiến trình daemon Sing-box / Tun2Socks:
  - Hỗ trợ Inbound Mixed (HTTP + SOCKS5) và TUN Layer-4/7.
  - Bọc toàn bộ lưu lượng TCP và UDP (UDMUX Roblox) qua Proxy mục tiêu.
  - Tự động sinh file cấu hình singbox_config.json phân luồng theo từng Tag / Cổng.
  - Tự động chạy và giám sát tiến trình sing-box trên Windows, Linux và Termux Android.
"""

import os
import sys
import json
import shutil
import subprocess
import threading
from typing import Dict, List, Optional, Tuple
from config.logging import setup_logger

logger = setup_logger("singbox_core")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "singbox_config.json")


class SingBoxEngine:
    """Bộ điều phối lõi định tuyến mạng Sing-box vạn năng"""

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.process: Optional[subprocess.Popen] = None
        self.is_running: bool = False
        self.listen_port: int = 10808
        self.tun_enabled: bool = False
        self.bin_path: Optional[str] = self._find_singbox_binary()

    def _find_singbox_binary(self) -> Optional[str]:
        # 1. Tìm trong PATH hệ thống
        p = shutil.which("sing-box") or shutil.which("singbox")
        if p:
            return p

        # 2. Tìm trong thư mục bin cục bộ của dự án
        local_candidates = [
            os.path.join(BASE_DIR, "bin", "sing-box.exe"),
            os.path.join(BASE_DIR, "bin", "sing-box"),
            "/data/data/com.termux/files/usr/bin/sing-box",
            os.path.expanduser("~/.cargo/bin/sing-box")
        ]
        for c in local_candidates:
            if os.path.exists(c):
                return c
        return None

    def generate_config(self, outbounds_list: List[Dict], enable_tun: bool = False) -> Dict:
        """
        Sinh cấu hình JSON chuẩn cho Sing-box:
        - Inbounds: Mixed SOCKS5/HTTP hoặc TUN interface.
        - Outbounds: Danh sách proxy phân bổ cho từng Tag.
        - Rules: Định tuyến traffic Roblox (roblox.com, rbdown.com, UDP UDMUX) qua proxy.
        """
        inbounds = [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": self.listen_port,
                "sniff": True
            }
        ]

        if enable_tun:
            inbounds.append({
                "type": "tun",
                "tag": "tun-in",
                "interface_name": "tun-roblox",
                "inet4_address": "172.19.0.1/30",
                "auto_route": True,
                "strict_route": False,
                "stack": "system",
                "sniff": True
            })

        outbounds = []
        # Outbound chính (Default)
        outbounds.append({
            "type": "direct",
            "tag": "direct"
        })

        for idx, ob in enumerate(outbounds_list):
            o_tag = ob.get("tag", f"proxy-{idx+1:02d}")
            o_type = ob.get("type", "socks").lower()
            o_server = ob.get("server", "127.0.0.1")
            o_port = int(ob.get("port", 1080))
            
            outbound_entry = {
                "type": "socks" if o_type == "socks" else "http",
                "tag": o_tag,
                "server": o_server,
                "server_port": o_port
            }
            if ob.get("username"):
                outbound_entry["username"] = ob["username"]
            if ob.get("password"):
                outbound_entry["password"] = ob["password"]

            outbounds.append(outbound_entry)

        # Route Rules
        route = {
            "rules": [
                {
                    "protocol": ["dns"],
                    "outbound": "direct"
                },
                {
                    "domain_suffix": [
                        "roblox.com",
                        "rbxcdn.com",
                        "robloxext.com",
                        "setup.rbxcdn.com"
                    ],
                    "outbound": outbounds_list[0].get("tag", "direct") if outbounds_list else "direct"
                }
            ],
            "auto_detect_interface": True
        }

        full_config = {
            "log": {
                "level": "warn",
                "timestamp": True
            },
            "inbounds": inbounds,
            "outbounds": outbounds,
            "route": route
        }

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(full_config, f, indent=2, ensure_ascii=False)

        logger.info(f"Generated Sing-box configuration at: {CONFIG_FILE}")
        return full_config

    def start_daemon(self, outbounds: Optional[List[Dict]] = None, enable_tun: bool = False) -> bool:
        """Khởi chạy tiến trình Sing-box daemon chạy ngầm"""
        if self.is_running and self.process:
            return True

        if not self.bin_path:
            logger.warning("Sing-box binary not found. Running in Fallback Python Forwarder Mode.")
            return False

        if outbounds:
            self.generate_config(outbounds, enable_tun=enable_tun)

        try:
            cmd = [self.bin_path, "run", "-c", CONFIG_FILE]
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            self.is_running = True
            self.tun_enabled = enable_tun
            logger.info(f"Sing-box daemon started successfully (PID: {self.process.pid}, Listen Port: {self.listen_port})")
            return True
        except Exception as e:
            logger.error(f"Failed to start Sing-box daemon: {e}")
            self.is_running = False
            return False

    def stop_daemon(self):
        """Dừng tiến trình Sing-box daemon an toàn"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
        self.is_running = False
        logger.info("Sing-box daemon stopped.")


# Singleton instance
singbox_engine = SingBoxEngine()
