# -*- coding: utf-8 -*-
"""
Local Roblox HTTP Bridge Server
Cung cấp API HTTP cục bộ (http://127.0.0.1:8888) cho phép Roblox Lua Client:
  1. Tự động đồng bộ và nạp IP động qua game:HttpGet hoặc loadstring.
  2. Gửi Heartbeat thời gian thực (/api/heartbeat) về Python để theo dõi trạng thái Tag.
  3. Báo cáo lỗi ngắt kết nối / crash / kick (/api/tag_status) để Python Watchdog tự mở lại Tag.
  4. Lấy thông tin Game Place ID mục tiêu (/api/target_game) để tự động Teleport vào đúng game.
"""

import os
import json
import threading
import socket
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Optional
from config.logging import setup_logger
from core.game_selector import game_manager
from core.watchdog_supervisor import watchdog

logger = setup_logger("bridge_server")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUA_DIR = os.path.join(BASE_DIR, "data", "generated_lua")

SHARED_STATE = {
    "tags": {},
    "claimed_sessions": {},
    "master_script": "",
    "custom_script": ""
}


def get_active_lua_script(tag_id: Optional[str] = None) -> str:
    """Lấy nội dung script Lua khả dụng nhất (từ memory hoặc từ disk)"""
    if tag_id and tag_id in SHARED_STATE["tags"]:
        s = SHARED_STATE["tags"][tag_id].get("lua_script", "")
        if s:
            return s
            
    if SHARED_STATE.get("master_script"):
        return SHARED_STATE["master_script"]

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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Roblox-Tag, Authorization")

    def _respond_json(self, data: Dict, code: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _respond_text(self, text: str, code: int = 200, content_type: str = "text/plain; charset=utf-8"):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ""

        payload = {}
        if post_body:
            try:
                payload = json.loads(post_body)
            except Exception:
                try:
                    q = parse_qs(post_body)
                    payload = {k: v[0] for k, v in q.items()}
                except Exception:
                    payload = {"raw": post_body}

        # 1. API: Nhận Heartbeat thời gian thực từ Lua Client
        if path in ["/api/heartbeat", "/api/ping", "/heartbeat"]:
            tag_id = payload.get("tag_id") or payload.get("tag") or self.headers.get("X-Roblox-Tag") or "ROBLOX-TAG-01"
            watchdog.record_heartbeat(tag_id, payload)
            
            if tag_id in SHARED_STATE["tags"]:
                SHARED_STATE["tags"][tag_id]["status"] = "ONLINE"
                SHARED_STATE["tags"][tag_id]["last_heartbeat"] = time.time()
                if payload.get("username"):
                    SHARED_STATE["tags"][tag_id]["username"] = payload.get("username")

            target_game = game_manager.get_current_game()
            resp = {
                "status": "ok",
                "ack": time.time(),
                "tag_id": tag_id,
                "target_game": target_game
            }
            self._respond_json(resp, 200)
            return

        # 2. API: Nhận Báo lỗi / Mất kết nối / Bị Kick hoặc Trạng thái Chuyển Server từ Lua Client
        if path in ["/api/tag_status", "/api/error", "/api/disconnect", "/api/report"]:
            tag_id = payload.get("tag_id") or payload.get("tag") or self.headers.get("X-Roblox-Tag") or "ROBLOX-TAG-01"
            err_msg = payload.get("error_message") or payload.get("error") or payload.get("reason") or "Roblox Disconnected / Crash Detected"
            status_type = payload.get("status") or "DISCONNECTED"
            
            watchdog.record_error_or_disconnect(tag_id, err_msg, status_type=status_type)

            if tag_id in SHARED_STATE["tags"]:
                SHARED_STATE["tags"][tag_id]["status"] = status_type
                if status_type == "TELEPORTING":
                    SHARED_STATE["tags"][tag_id]["last_heartbeat"] = time.time() + 60.0

            resp = {
                "status": "recorded",
                "tag_id": tag_id,
                "action": "teleport_grace_active" if status_type == "TELEPORTING" else "watchdog_recorded",
                "timestamp": time.time()
            }
            self._respond_json(resp, 200)
            return

        # 3. Fallback POST
        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 1. API: Lấy script Lua trực tiếp để chạy: loadstring(game:HttpGet("http://127.0.0.1:8888/api/script"))()
        if path in ["/api/script", "/script.lua", "/api/lua", "/script"]:
            tag_id = query.get("tag", [None])[0]
            script_body = get_active_lua_script(tag_id)
            self._respond_text(script_body, 200)
            return

        # 2. API: Tự động phân giải và nhận Tag riêng biệt không trùng lặp cho từng Instance / Clone
        if path in ["/api/claim_tag", "/api/claim", "/api/auto_assign", "/api/bind"]:
            import random
            from network.proxy_fetcher import ProxyFetcher, SUPPORTED_COUNTRIES
            from core.lua_generator import LuaScriptGenerator

            user = query.get("user", [""])[0].strip()
            job_id = query.get("job_id", [""])[0].strip()
            session_id = query.get("session_id", [""])[0].strip()
            place_id = query.get("place_id", [""])[0].strip()

            if user and user.lower() not in ["unknown", "player", "player1"]:
                session_key = user.lower()
            elif session_id:
                session_key = session_id
            elif job_id and job_id != "Unknown_Job":
                session_key = job_id
            else:
                session_key = f"clone_client_{len(SHARED_STATE['claimed_sessions']) + 1}"

            chosen_tag_id = SHARED_STATE["claimed_sessions"].get(session_key)
            matched = None

            if chosen_tag_id and chosen_tag_id in SHARED_STATE["tags"]:
                matched = SHARED_STATE["tags"][chosen_tag_id]
            else:
                claimed_tag_ids = set(SHARED_STATE["claimed_sessions"].values())
                for tid, tdata in SHARED_STATE["tags"].items():
                    if tid not in claimed_tag_ids and not tdata.get("claimed_by"):
                        chosen_tag_id = tid
                        matched = tdata
                        break

                if not matched:
                    new_tag_num = len(SHARED_STATE["tags"]) + 1
                    chosen_tag_id = f"ROBLOX-CLONE-{new_tag_num:02d}"
                    new_proxies = ProxyFetcher.get_proxies_batch(count=1, country_code="MULTI")
                    new_p_info = new_proxies[0] if new_proxies else {
                        "ip": f"103.{random.randint(10,240)}.{random.randint(1,240)}.{random.randint(1,240)}:80",
                        "region": "[JP] Japan Dedicated",
                        "country": "JP"
                    }
                    gen = LuaScriptGenerator()
                    profile = gen._generate_unique_tag_profile(new_tag_num)
                    
                    matched = {
                        "tag_id": chosen_tag_id,
                        "assigned_ip": new_p_info["ip"],
                        "region": new_p_info["region"],
                        "country": new_p_info.get("country", "JP"),
                        "pid": 0,
                        "title": f"Roblox Clone {new_tag_num}",
                        "process_name": "ROBLOX_CLONE",
                        "username": user,
                        "hwid": profile["hwid"],
                        "client_uuid": profile["client_uuid"],
                        "mac_addr": profile["mac_addr"],
                        "user_agent": profile["user_agent"],
                        "dns_primary": profile["dns_primary"],
                        "dns_secondary": profile["dns_secondary"],
                    }
                    SHARED_STATE["tags"][chosen_tag_id] = matched

                SHARED_STATE["claimed_sessions"][session_key] = chosen_tag_id
                matched["claimed_by"] = session_key
                if user:
                    matched["username"] = user
                matched["job_id"] = job_id
                
                watchdog.register_tag(
                    tag_id=chosen_tag_id,
                    assigned_ip=matched.get("assigned_ip", ""),
                    region=matched.get("region", ""),
                    username=user,
                    place_id=place_id
                )
                logger.info(f"[TAG CLAIMED] Session '{session_key}' -> Gán Tag [{chosen_tag_id}] | IP: {matched['assigned_ip']} ({matched['region']})")

            custom_payload_path = os.path.join(BASE_DIR, "data", "custom_payload.lua")
            custom_code = ""
            if os.path.exists(custom_payload_path):
                try:
                    with open(custom_payload_path, "r", encoding="utf-8") as f:
                        custom_code = f.read()
                except Exception:
                    pass

            target_game = game_manager.get_game_for_tag(chosen_tag_id)

            resp_data = dict(matched)
            resp_data["status"] = "success"
            resp_data["custom_script"] = custom_code
            resp_data["custom_script_url"] = "http://127.0.0.1:8888/api/custom_script"
            resp_data["target_game"] = target_game

            self._respond_json(resp_data, 200)
            return

        # 3. API: Game mục tiêu đã chọn (Hỗ trợ truy vấn theo từng Tag riêng biệt: /api/target_game?tag=ROBLOX-TAG-01)
        if path in ["/api/target_game", "/api/game", "/api/selected_game"]:
            tag_id = query.get("tag", [None])[0] or query.get("tag_id", [None])[0]
            target_game = game_manager.get_game_for_tag(tag_id)
            self._respond_json(target_game, 200)
            return

        if path in ["/api/target_games_all", "/api/tag_games", "/api/all_games"]:
            self._respond_json({
                "per_tag_mode": game_manager.per_tag_mode,
                "global_game": game_manager.get_current_game(),
                "tag_games": game_manager.get_all_tag_games()
            }, 200)
            return

        # 4. API: Trạng thái Watchdog và nhịp tim
        if path in ["/api/watchdog/status", "/api/watchdog", "/api/status/watchdog"]:
            w_summary = watchdog.get_summary()
            self._respond_json(w_summary, 200)
            return

        # 5. API: Lấy thông tin IP theo Tag hoặc Username
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

            resp = matched or {"error": "Tag not found", "assigned_ip": "112.146.7.100", "region": "JP (Tokyo)"}
            self._respond_json(resp, 200 if matched else 404)
            return

        # 6. API: Cung cấp script người dùng muốn tự động chạy cho toàn bộ các Tag
        if path in ["/api/custom_script", "/api/custom", "/api/payload"]:
            custom_payload_path = os.path.join(BASE_DIR, "data", "custom_payload.lua")
            custom_code = "-- No custom payload configured"
            if os.path.exists(custom_payload_path):
                try:
                    with open(custom_payload_path, "r", encoding="utf-8") as f:
                        custom_code = f.read()
                except Exception:
                    pass

            self._respond_text(custom_code, 200)
            return

        # 7. API: Tự động đổi IP mới khi chuyển server
        if path in ["/api/rotate_ip", "/api/server_hop", "/api/hop"]:
            tag_id = query.get("tag", ["ROBLOX-TAG-01"])[0]
            job_id = query.get("job_id", ["Unknown_Job"])[0]
            old_ip = query.get("old_ip", [""])[0]
            specified_country = query.get("country", [None])[0]

            from network.proxy_fetcher import ProxyFetcher, SUPPORTED_COUNTRIES
            import random

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

            if tag_id in SHARED_STATE["tags"]:
                SHARED_STATE["tags"][tag_id]["assigned_ip"] = new_ip
                SHARED_STATE["tags"][tag_id]["region"] = new_region
                SHARED_STATE["tags"][tag_id]["country"] = target_country

            logger.info(f"[SERVER HOP DETECTED] Tag {tag_id} joined Server (JobId: {job_id[:12]}...). Auto-rotated IP -> {new_ip} [Same Country: {target_country}]")

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
            self._respond_json(response_data, 200)
            return

        # 8. API: Danh sách toàn bộ Tags & IPs
        if path in ["/api/instances", "/api/all", "/"]:
            self._respond_json(SHARED_STATE["tags"], 200)
            return

        # 9. API: Scrapestack Proxy Status & IP Query
        if path in ["/api/scrapestack", "/api/scrapestack/status", "/api/scrapestack/ip"]:
            from network.scrapestack_client import ScrapestackClient
            s_client = ScrapestackClient()
            if path == "/api/scrapestack/ip":
                ip = s_client.get_proxy_ip()
                resp = {"status": "ONLINE" if ip else "OFFLINE", "proxy_ip": ip}
            else:
                resp = s_client.test_connection()
            self._respond_json(resp, 200)
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
        SHARED_STATE["claimed_sessions"] = {}
        for inst in instances:
            SHARED_STATE["tags"][inst.tag_id] = {
                "tag_id": inst.tag_id,
                "assigned_ip": inst.assigned_ip or "127.0.0.1",
                "region": getattr(inst, "region", "[JP] Japan Dedicated"),
                "country": getattr(inst, "country", "JP"),
                "pid": inst.pid,
                "title": inst.title,
                "process_name": inst.process_name,
                "username": getattr(inst, "account_username", "") or "",
                "status": "ONLINE" if inst.pid > 0 or inst.hwnd > 0 else "OFFLINE"
            }
            watchdog.register_tag(
                tag_id=inst.tag_id,
                assigned_ip=inst.assigned_ip or "127.0.0.1",
                region=getattr(inst, "region", "[JP] Japan Dedicated"),
                username=getattr(inst, "account_username", "") or "",
                pid=inst.pid
            )
        if master_script:
            SHARED_STATE["master_script"] = master_script

    def start(self):
        if self.is_running:
            return
        try:
            get_active_lua_script()
            self.server = ReusableHTTPServer((self.host, self.port), RobloxBridgeHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            self.is_running = True
            watchdog.start()
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
            watchdog.stop()
            logger.info("Roblox Bridge Server stopped.")
