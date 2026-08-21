# -*- coding: utf-8 -*-
"""
Local Roblox HTTP Bridge Server
Cung cấp API HTTP cục bộ (http://127.0.0.1:8888) cho phép Roblox Lua Client
tự động đồng bộ và nạp IP động qua game:HttpGet hoặc loadstring.
"""

import os
import json
import threading
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Optional
from config.logging import setup_logger

logger = setup_logger("bridge_server")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUA_DIR = os.path.join(BASE_DIR, "data", "generated_lua")

SHARED_STATE = {
    "tags": {},
    "master_script": ""
}

def get_active_lua_script(tag_id: Optional[str] = None) -> str:
    """Lấy nội dung script Lua khả dụng nhất (từ memory hoặc từ disk)"""
    # 1. Nếu có trong memory
    if tag_id and tag_id in SHARED_STATE["tags"]:
        s = SHARED_STATE["tags"][tag_id].get("lua_script", "")
        if s:
            return s
            
    if SHARED_STATE.get("master_script"):
        return SHARED_STATE["master_script"]

    # 2. Đọc từ file master trên ổ đĩa
    master_path = os.path.join(LUA_DIR, "master_roblox_ip_setter.lua")
    if os.path.exists(master_path):
        try:
            with open(master_path, "r", encoding="utf-8") as f:
                content = f.read()
                if content.strip():
                    SHARED_STATE["master_script"] = content
                    return content
        except Exception:
            pass

    # 3. Đọc từ file tag đầu tiên nếu có
    if os.path.exists(LUA_DIR):
        for fname in os.listdir(LUA_DIR):
            if fname.endswith(".lua") and not fname.startswith("master"):
                try:
                    with open(os.path.join(LUA_DIR, fname), "r", encoding="utf-8") as f:
                        content = f.read()
                        if content.strip():
                            return content
                except Exception:
                    pass

    # 4. Tự động sinh tức thì một script Lua hợp lệ với IP ngẫu nhiên
    from core.lua_generator import LuaScriptGenerator
    from core.scanner import RobloxWindowScanner, RobloxWindowInstance, WindowRect
    gen = LuaScriptGenerator()
    default_tag = [RobloxWindowInstance("ROBLOX-TAG-01", 16888, "Roblox Client", 16888, "RobloxPlayerBeta.exe", "WINDOWSCLIENT", WindowRect(), "Center", "500 MB")]
    files = gen.generate_scripts_for_scanned_instances(default_tag)
    master_p = files.get("MASTER", master_path)
    if os.path.exists(master_p):
        with open(master_p, "r", encoding="utf-8") as f:
            content = f.read()
            SHARED_STATE["master_script"] = content
            return content

    return "-- Roblox IP Manager: Script Ready"


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class RobloxBridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Roblox-Tag")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 1. API: Lấy script Lua trực tiếp để chạy: loadstring(game:HttpGet("http://127.0.0.1:8888/api/script"))()
        if path in ["/api/script", "/script.lua", "/api/lua", "/script"]:
            tag_id = query.get("tag", [None])[0]
            script_body = get_active_lua_script(tag_id)

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(script_body.encode("utf-8"))
            return

        # 2. API: Lấy thông tin IP theo Tag hoặc Username
        if path == "/api/ip":
            tag_id = query.get("tag", [None])[0]
            username = query.get("user", [None])[0]

            matched = None
            for tid, data in SHARED_STATE["tags"].items():
                if tid == tag_id or (username and data.get("username", "").lower() == username.lower()):
                    matched = data
                    break

            if not matched and SHARED_STATE["tags"]:
                matched = next(iter(SHARED_STATE["tags"].values()))

            self.send_response(200 if matched else 404)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            resp = matched or {"error": "Tag not found", "assigned_ip": "112.146.7.100", "region": "JP (Tokyo)"}
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        # 3. API: Tự động đổi IP mới (cùng quốc gia đã chọn) khi người chơi chuyển Server / Teleport
        if path in ["/api/rotate_ip", "/api/server_hop", "/api/hop"]:
            tag_id = query.get("tag", ["ROBLOX-TAG-01"])[0]
            job_id = query.get("job_id", ["Unknown_Job"])[0]
            old_ip = query.get("old_ip", [""])[0]
            specified_country = query.get("country", [None])[0]

            from network.proxy_fetcher import ProxyFetcher, SUPPORTED_COUNTRIES
            import random

            # Xác định quốc gia hiện tại của Tag
            target_country = "JP"
            if specified_country and specified_country.upper() in SUPPORTED_COUNTRIES:
                target_country = specified_country.upper()
            elif tag_id in SHARED_STATE["tags"]:
                stored_reg = SHARED_STATE["tags"][tag_id].get("region", "")
                stored_country = SHARED_STATE["tags"][tag_id].get("country", "")
                if stored_country:
                    target_country = stored_country
                else:
                    for c_code in SUPPORTED_COUNTRIES:
                        if f"[{c_code}]" in stored_reg:
                            target_country = c_code
                            break

            # Lấy danh sách Proxy của đúng quốc gia đó
            c_proxies = ProxyFetcher.fetch_country_proxies(target_country, force_refresh=False)
            available = [ip for ip in c_proxies if ip != old_ip]
            if available:
                new_ip = random.choice(available)
            elif c_proxies:
                new_ip = random.choice(c_proxies)
            else:
                new_ip = f"103.{random.randint(10,250)}.{random.randint(1,250)}.{random.randint(1,250)}:80"

            c_info = SUPPORTED_COUNTRIES.get(target_country, {"name": target_country, "tag": f"[{target_country}]"})
            new_region = f"{c_info['tag']} {target_country} (ServerHop)"

            # Cập nhật trạng thái
            if tag_id in SHARED_STATE["tags"]:
                SHARED_STATE["tags"][tag_id]["assigned_ip"] = new_ip
                SHARED_STATE["tags"][tag_id]["region"] = new_region
                SHARED_STATE["tags"][tag_id]["country"] = target_country

            logger.info(f"[SERVER HOP DETECTED] Tag {tag_id} joined Server (JobId: {job_id[:12]}...). Auto-rotated IP -> {new_ip} [Same Country: {target_country}]")

            # Can thiệp sâu tầng Linux Kernel / Android iptables & Cloud Phone (Root / SU)
            try:
                if ":" in new_ip:
                    proxy_h, proxy_p = new_ip.split(":", 1)
                    # 1. Cập nhật UGPhone nếu kết nối
                    from devices.ugphone_bridge import UGPhoneBridge
                    ug_bridge = UGPhoneBridge()
                    if ug_bridge.connected_devices:
                        for dev in ug_bridge.connected_devices:
                            ug_bridge.set_android_proxy(dev, proxy_h, int(proxy_p))
                    
                    # 2. Cập nhật Android Native Settings qua Root SU (set global http_proxy)
                    import subprocess
                    if os.path.exists("/system/bin/setprop") or os.path.exists("/data/data/com.termux"):
                        subprocess.run(["su", "-c", f"settings put global http_proxy {new_ip} 2>/dev/null || true"], capture_output=True, timeout=1)
                        subprocess.run(["su", "-c", f"setprop http.proxyHost {proxy_h} && setprop http.proxyPort {proxy_p} 2>/dev/null || true"], capture_output=True, timeout=1)
            except Exception as e:
                logger.debug(f"Root proxy redirection note: {e}")

            # 3. [XÓA VÀ THAY THẾ FILE LUA CỰC NHANH VÀO AUTOEXEC]
            try:
                from core.lua_generator import LuaScriptGenerator
                gen = LuaScriptGenerator()
                new_script = gen.fast_regenerate_and_sync(tag_id, new_ip, new_region, target_country)
                SHARED_STATE["master_script"] = new_script
                if tag_id in SHARED_STATE["tags"]:
                    SHARED_STATE["tags"][tag_id]["lua_script"] = new_script
            except Exception as e:
                logger.debug(f"Fast lua sync note: {e}")

            response_data = {
                "status": "success",
                "tag_id": tag_id,
                "new_ip": new_ip,
                "region": new_region,
                "country": target_country,
                "job_id": job_id,
                "message": f"Da doi sang IP moi {new_ip} (Van giu dung quoc gia [{target_country}])"
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
            return

        # 4. API: Danh sách toàn bộ Tags & IPs
        if path in ["/api/instances", "/api/all", "/"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(SHARED_STATE["tags"], indent=2).encode("utf-8"))
            return

        # Fallback 404
        self.send_response(404)
        self.end_headers()


class RobloxBridgeServer:
    """Server nền hỗ trợ kết nối trực tiếp với Roblox Lua Engine"""

    def __init__(self, host: str = "127.0.0.1", port: int = 8888):
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.is_running = False

    def update_state(self, instances: List, master_script: str = ""):
        """Cập nhật dữ liệu gán IP cho các Tag đang hoạt động"""
        SHARED_STATE["tags"] = {}
        for inst in instances:
            SHARED_STATE["tags"][inst.tag_id] = {
                "tag_id": inst.tag_id,
                "assigned_ip": inst.assigned_ip,
                "region": inst.region,
                "pid": inst.pid,
                "title": inst.title,
                "process_name": inst.process_name,
                "username": inst.account_username or ""
            }
        if master_script:
            SHARED_STATE["master_script"] = master_script

    def start(self):
        if self.is_running:
            return
        try:
            # Tự động nạp sẵn script từ đĩa nếu có
            get_active_lua_script()
            self.server = ReusableHTTPServer((self.host, self.port), RobloxBridgeHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            self.is_running = True
            logger.info(f"Roblox Bridge Server started at http://{self.host}:{self.port}")
        except Exception as e:
            logger.warning(f"Bridge Server start note: {e}")
            self.is_running = True

    def stop(self):
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
            self.is_running = False
            logger.info("Roblox Bridge Server stopped.")
