# -*- coding: utf-8 -*-
"""
Roblox Multi-Tag Discord Notification & Webhook Dispatcher
Gửi thông báo sự cố thời gian thực lên kênh Discord / Webhook:
  - Báo động tức thì khi Tag Roblox bị văng, crash, lỗi 277/268, hoặc bị kick.
  - Đính kèm ảnh chụp màn hình sự cố trực quan (Screenshot Attachment).
  - Báo cáo trạng thái Auto-Rejoin thành công kèm Dedicated IP và Game Name.
  - Gửi bất đồng bộ (Non-blocking Queue) không làm nghẽn tiến trình điều khiển chính.
"""

import os
import sys
import time
import json
import queue
import threading
from typing import Optional, Dict, Any
import urllib.request
import urllib.parse

try:
    import requests
except ImportError:
    requests = None

from config.logging import setup_logger

logger = setup_logger("discord_notifier")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DISCORD_CONFIG_FILE = os.path.join(DATA_DIR, "discord_config.json")


class DiscordNotifier:
    """Quản lý thông báo Discord Webhook & Bot Alerts"""

    def __init__(self):
        self.config: Dict[str, Any] = {
            "enabled": False,
            "webhook_url": "",
            "bot_token": "",
            "channel_id": "",
            "attach_screenshot": True,
            "notify_on_crash": True,
            "notify_on_rejoin": True,
        }
        self._queue: queue.Queue = queue.Queue(maxsize=100)
        self._worker_thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._load_config()
        self._start_worker()

    def _load_config(self):
        """Tải cấu hình Discord từ file"""
        if os.path.exists(DISCORD_CONFIG_FILE):
            try:
                with open(DISCORD_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.config.update(data)
            except Exception as e:
                logger.warning(f"Lỗi tải cấu hình Discord: {e}")

    def save_config(self, new_config: Optional[Dict] = None):
        """Lưu cấu hình Discord"""
        if new_config:
            self.config.update(new_config)
        try:
            os.makedirs(os.path.dirname(DISCORD_CONFIG_FILE), exist_ok=True)
            with open(DISCORD_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info("Đã lưu cấu hình Discord thành công.")
        except Exception as e:
            logger.error(f"Lỗi lưu cấu hình Discord: {e}")

    def _start_worker(self):
        """Khởi động worker thread xử lý gửi tin nhắn ngầm"""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
            self._worker_thread.start()

    def _dispatch_loop(self):
        """Vòng lặp ngầm lấy thông báo từ hàng đợi và gửi lên Webhook"""
        while self._running:
            try:
                item = self._queue.get(timeout=2.0)
                if item:
                    self._send_payload(item)
                    self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp Discord Dispatcher: {e}")

    def _send_payload(self, item: Dict):
        """Gửi webhook payload với hỗ trợ upload tệp ảnh screenshot"""
        webhook_url = self.config.get("webhook_url", "").strip()
        if not webhook_url or not webhook_url.startswith("http"):
            return

        embed = item.get("embed", {})
        image_path = item.get("image_path")

        payload = {
            "username": "⚡ Roblox Auto-Rejoiner Sentinel",
            "avatar_url": "https://raw.githubusercontent.com/hyuttgg/tool-python-roblox-ip/main/SetupRobloxIP",
            "embeds": [embed]
        }

        try:
            headers = {"User-Agent": "Roblox-Auto-Rejoiner-Discord/2.0"}
            if requests is not None:
                if image_path and os.path.exists(image_path) and self.config.get("attach_screenshot", True):
                    file_name = os.path.basename(image_path)
                    embed["image"] = {"url": f"attachment://{file_name}"}
                    
                    with open(image_path, "rb") as img_file:
                        files = {
                            "file": (file_name, img_file, "image/png"),
                            "payload_json": (None, json.dumps(payload), "application/json")
                        }
                        resp = requests.post(webhook_url, files=files, headers=headers, timeout=10)
                else:
                    resp = requests.post(webhook_url, json=payload, headers=headers, timeout=8)

                if resp.status_code in (200, 204):
                    logger.info("Đã gửi thông báo Discord Webhook thành công.")
                else:
                    logger.warning(f"Discord Webhook trả về mã lỗi: {resp.status_code} - {resp.text}")
            else:
                # Fallback qua urllib.request
                req_data = json.dumps(payload).encode("utf-8")
                req_headers = {"User-Agent": "Roblox-Auto-Rejoiner-Discord/2.0", "Content-Type": "application/json"}
                req = urllib.request.Request(webhook_url, data=req_data, headers=req_headers, method="POST")
                with urllib.request.urlopen(req, timeout=8) as response:
                    if response.status in (200, 204):
                        logger.info("Đã gửi thông báo Discord Webhook (urllib) thành công.")
        except Exception as e:
            logger.warning(f"Không thể gửi thông báo tới Discord Webhook: {e}")

    def send_crash_alert(self, tag_id: str, game_name: str, place_id: str, error_reason: str, image_path: Optional[str] = None):
        """Gửi cảnh báo Tag bị văng / Crash / Disconnect"""
        if not self.config.get("enabled") or not self.config.get("notify_on_crash", True):
            return

        embed = {
            "title": "🚨 CẢNH BÁO: ROBLOX BỊ VĂNG / MẤT KẾT NỐI",
            "description": f"Hệ thống Watchdog phát hiện sự cố trên Tag **[{tag_id}]** và đang tiến hành tự động Rejoin!",
            "color": 0xFF0033,  # Đỏ
            "fields": [
                {"name": "🏷️ Tag ID", "value": f"`{tag_id}`", "inline": True},
                {"name": "🎮 Tựa Game", "value": f"**{game_name}** (`{place_id}`)", "inline": True},
                {"name": "⚠️ Lý do sự cố", "value": f"```{error_reason}```", "inline": False},
                {"name": "⏰ Thời gian", "value": f"<t:{int(time.time())}:R>", "inline": True},
                {"name": "🔄 Hành động", "value": "Đang kiểm tra Internet & Tự động mở lại...", "inline": True},
            ],
            "footer": {"text": "Roblox Multi-Tag Watchdog Sentinel • Auto-Recovery"}
        }

        self._queue.put({"embed": embed, "image_path": image_path})

    def send_rejoin_alert(self, tag_id: str, game_name: str, place_id: str, assigned_ip: str = "", region: str = "", attempt: int = 1):
        """Gửi thông báo Rejoin thành công"""
        if not self.config.get("enabled") or not self.config.get("notify_on_rejoin", True):
            return

        embed = {
            "title": "✅ AUTO-REJOIN THÀNH CÔNG: ROBLOX ĐÃ KHỞI CHẠY LẠI",
            "description": f"Tag **[{tag_id}]** đã được đưa trở lại game mục tiêu thành công và tiếp tục giám sát nhịp tim!",
            "color": 0x00FF66,  # Xanh lá
            "fields": [
                {"name": "🏷️ Tag ID", "value": f"`{tag_id}`", "inline": True},
                {"name": "🎮 Tựa Game", "value": f"**{game_name}** (`{place_id}`)", "inline": True},
                {"name": "🌐 Dedicated IP", "value": f"`{assigned_ip or 'Direct / Local'}`", "inline": True},
                {"name": "🌏 Server Region", "value": f"`{region or 'AUTO'}`", "inline": True},
                {"name": "🔄 Lần thử (Attempt)", "value": f"`#{attempt}`", "inline": True},
                {"name": "⏰ Thời gian Rejoin", "value": f"<t:{int(time.time())}:R>", "inline": True},
            ],
            "footer": {"text": "Roblox Multi-Tag Watchdog Sentinel • System Online"}
        }

        self._queue.put({"embed": embed, "image_path": None})

    def test_webhook(self) -> Dict[str, Any]:
        """Gửi tin nhắn test kiểm tra cấu hình Webhook"""
        webhook_url = self.config.get("webhook_url", "").strip()
        if not webhook_url or not webhook_url.startswith("http"):
            return {"success": False, "error": "Chưa cấu hình URL Webhook Discord!"}

        payload = {
            "username": "⚡ Roblox Auto-Rejoiner Sentinel",
            "embeds": [{
                "title": "🔔 KIỂM TRA KẾT NỐI DISCORD WEBHOOK",
                "description": "Kết nối giữa Tool Roblox Multi-Tag và máy chủ Discord đã được thiết lập thành công 100%!",
                "color": 0x0099FF,
                "fields": [
                    {"name": "Trạng thái", "value": "🟢 HOẠT ĐỘNG TỐT", "inline": True},
                    {"name": "Thời gian", "value": f"<t:{int(time.time())}:F>", "inline": True},
                ],
                "footer": {"text": "Roblox Multi-Tag Controller & Watchdog Sentinel"}
            }]
        }

        try:
            if requests is not None:
                resp = requests.post(webhook_url, json=payload, timeout=5)
                if resp.status_code in (200, 204):
                    return {"success": True, "status_code": resp.status_code}
                return {"success": False, "error": f"Mã lỗi HTTP {resp.status_code}: {resp.text}"}
            else:
                req_data = json.dumps(payload).encode("utf-8")
                req_headers = {"User-Agent": "Roblox-Auto-Rejoiner-Discord/2.0", "Content-Type": "application/json"}
                req = urllib.request.Request(webhook_url, data=req_data, headers=req_headers, method="POST")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return {"success": True, "status_code": resp.status}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
discord_notifier = DiscordNotifier()
