# -*- coding: utf-8 -*-
"""
Discord Rich Embed Reporter & Telemetry Notifier
Gửi thông báo Discord định dạng Rich Embed cao cấp:
  - Hiển thị Avatar 3D nhân vật & Icon Game.
  - Cờ Quốc gia & Datacenter Region (Singapore, Tokyo, US...).
  - Chỉ số Ping thời gian thực, RAM, FPS và thời gian cày liên tục (Uptime).
  - Lịch sử Auto-Rejoin khi xảy ra sự cố.
"""

import time
import json
import urllib.request
from typing import Optional, Dict
from config.logging import setup_logger
from network.roblox_presence import presence_tracker

logger = setup_logger("discord_rich_reporter")


class DiscordRichReporter:
    """Trình gửi thông báo Discord Rich Embeds cao cấp"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url

    def send_game_joined_embed(
        self,
        tag_id: str,
        username: str,
        user_id: str,
        game_name: str,
        place_id: str,
        assigned_ip: str,
        region: str,
        flag: str = "🌐",
        ping_ms: int = 45,
        fps: int = 60,
        webhook_url: Optional[str] = None
    ) -> bool:
        url = webhook_url or self.webhook_url
        if not url:
            return False

        avatar_url = presence_tracker.get_user_avatar_headshot(user_id)
        game_icon_url = presence_tracker.get_game_icon(place_id)
        presence_tracker.start_tag_session(tag_id)

        embed = {
            "title": f"🟢 [ROBLOX ONLINE] Tag [{tag_id}] Đã Kết Nối Server Thành Công!",
            "color": 3066993,  # Màu xanh lá đậm
            "thumbnail": {"url": avatar_url},
            "image": {"url": game_icon_url},
            "fields": [
                {"name": "👤 Tài Khoản / User", "value": f"**{username or 'RobloxPlayer'}** (ID: `{user_id or '0'}`)", "inline": True},
                {"name": "🎮 Tựa Game", "value": f"**{game_name}** (`{place_id}`)", "inline": True},
                {"name": "🌐 Dedicated IP", "value": f"`{assigned_ip}`", "inline": True},
                {"name": f"{flag} Server Region", "value": f"**{region}**", "inline": True},
                {"name": "⚡ Ping Kết Nối", "value": f"`{ping_ms} ms` (FPS: `{fps}`)", "inline": True},
                {"name": "🛡️ Trạng Thái", "value": "🟢 **AUTO-REJOIN SENTINEL READY**", "inline": True}
            ],
            "footer": {"text": f"Roblox Multi-Instance Hub • Tag: {tag_id} • {time.strftime('%H:%M:%S %d/%m/%Y')}"}
        }

        return self._send_payload(url, {"embeds": [embed]})

    def send_rejoin_success_embed(
        self,
        tag_id: str,
        username: str,
        user_id: str,
        game_name: str,
        place_id: str,
        assigned_ip: str,
        region: str,
        flag: str = "🌐",
        attempt: int = 1,
        reason: str = "Disconnect / Crash Recovery",
        webhook_url: Optional[str] = None
    ) -> bool:
        url = webhook_url or self.webhook_url
        if not url:
            return False

        avatar_url = presence_tracker.get_user_avatar_headshot(user_id)
        game_icon_url = presence_tracker.get_game_icon(place_id)
        uptime = presence_tracker.get_session_uptime_str(tag_id)

        embed = {
            "title": f"⚡ [AUTO-REJOIN THÀNH CÔNG] Tag [{tag_id}] Đã Khôi Phục Game!",
            "color": 15844367,  # Màu vàng hổ phách
            "thumbnail": {"url": avatar_url},
            "image": {"url": game_icon_url},
            "fields": [
                {"name": "👤 Tài Khoản", "value": f"**{username or 'RobloxPlayer'}**", "inline": True},
                {"name": "🎮 Tựa Game", "value": f"**{game_name}**", "inline": True},
                {"name": "🔄 Lần Thử Rejoin", "value": f"**#{attempt}** (Lý do: `{reason}`)", "inline": True},
                {"name": f"{flag} Server Region", "value": f"**{region}**", "inline": True},
                {"name": "🌐 Dedicated IP", "value": f"`{assigned_ip}`", "inline": True},
                {"name": "⏱️ Thời Gian Treo", "value": f"**{uptime}**", "inline": True}
            ],
            "footer": {"text": f"Roblox Watchdog Sentinel • Auto Recovered at {time.strftime('%H:%M:%S')}"}
        }

        return self._send_payload(url, {"embeds": [embed]})

    def _send_payload(self, webhook_url: str, payload: Dict) -> bool:
        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "RobloxRichReporter/2.0"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                return resp.status in (200, 204)
        except Exception as e:
            logger.debug(f"Discord rich embed send error: {e}")
            return False


# Singleton instance
rich_reporter = DiscordRichReporter()
