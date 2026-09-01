# -*- coding: utf-8 -*-
"""
Roblox Presence & User Tracker (LxstCxn Architecture)
Theo dõi thời gian thực sự hiện diện của tài khoản Roblox:
  - Tự động lấy Avatar 3D Headshot của người chơi qua Roblox Thumbnails API.
  - Tự động lấy Icon / Thumbnail của Game đang chơi.
  - Đo đếm thời gian chơi liên tục (Playtime / Session Uptime).
  - Định danh Universe ID, Place ID, Job ID và thông tin Server.
  - Tự động đính kèm Cookie account (sau khi checkpoint WAL) để hiển thị chính xác InGame.
"""

import os
import time
import urllib.request
import json
from typing import Dict, Optional, Tuple
from config.logging import setup_logger

logger = setup_logger("roblox_presence")

# Cache lưu trữ thumbnail tránh spam API Roblox
AVATAR_CACHE: Dict[str, str] = {}
GAME_ICON_CACHE: Dict[str, str] = {}


class RobloxPresenceTracker:
    """Bộ theo dõi hiện diện và tài nguyên hình ảnh của người chơi Roblox"""

    def __init__(self):
        self.session_start_times: Dict[str, float] = {}

    def start_tag_session(self, tag_id: str):
        """Bắt đầu tính giờ phiên chơi của Tag"""
        self.session_start_times[tag_id] = time.time()

    def get_session_uptime_str(self, tag_id: str) -> str:
        """Lấy chuỗi thời gian chơi (ví dụ: 2h 45m 12s)"""
        start_t = self.session_start_times.get(tag_id, time.time())
        elapsed_sec = int(time.time() - start_t)
        hours = elapsed_sec // 3600
        minutes = (elapsed_sec % 3600) // 60
        seconds = elapsed_sec % 60
        if hours > 0:
            return f"{hours}h {minutes:02d}m {seconds:02d}s"
        return f"{minutes}m {seconds:02d}s"

    @classmethod
    def get_user_presence(cls, user_id: str, cookie_value: Optional[str] = None, db_path: Optional[str] = None) -> Dict:
        """
        Lấy thông tin Presence của user từ Roblox API có đính kèm Cookie account.
        Tự động gộp WAL checkpoint trước khi đọc cookie để tương thích VSPhone / Termux.
        """
        clean_uid = "".join(filter(str.isdigit, str(user_id)))
        if not clean_uid or clean_uid == "0":
            return {"user_id": user_id, "user_presence_type": 0, "status_str": "Offline"}

        # Tự động nạp Raw Cookie từ DB nếu không truyền trực tiếp
        if not cookie_value and db_path and os.path.exists(db_path):
            try:
                from database.termux_cookie import TermuxCookieManager
                mgr = TermuxCookieManager(db_path)
                cookie_value = mgr.get_raw_cookie_from_db()
            except Exception as e:
                logger.debug(f"Không thể đọc cookie từ DB cho presence: {e}")

        url = "https://presence.roblox.com/v1/presence/users"
        payload = json.dumps({"userIds": [int(clean_uid)]}).encode("utf-8")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if cookie_value:
            raw_cookie = cookie_value.strip()
            if not raw_cookie.startswith(".ROBLOSECURITY="):
                raw_cookie = f".ROBLOSECURITY={raw_cookie}"
            headers["Cookie"] = raw_cookie

        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                presences = data.get("userPresences", [])
                if presences:
                    p = presences[0]
                    p_type = p.get("userPresenceType", 0)
                    type_map = {0: "Offline", 1: "Online", 2: "InGame", 3: "InStudio"}
                    p["status_str"] = type_map.get(p_type, "Offline")
                    return p
        except Exception as e:
            logger.debug(f"Failed to fetch presence for {clean_uid}: {e}")

        return {"user_id": clean_uid, "user_presence_type": 0, "status_str": "Offline"}

    @classmethod
    def get_user_avatar_headshot(cls, user_id: str) -> str:
        """Lấy URL ảnh đại diện 3D (Avatar Headshot) của người chơi"""
        clean_uid = "".join(filter(str.isdigit, str(user_id)))
        if not clean_uid or clean_uid == "0":
            return "https://tr.rbxcdn.com/30DAY-AvatarHeadshot-Default/150/150/AvatarHeadshot/Png/noFilter"

        if clean_uid in AVATAR_CACHE:
            return AVATAR_CACHE[clean_uid]

        url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={clean_uid}&size=150x150&format=Png&isCircular=false"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("data", [])
                if items and items[0].get("imageUrl"):
                    img_url = items[0]["imageUrl"]
                    AVATAR_CACHE[clean_uid] = img_url
                    return img_url
        except Exception as e:
            logger.debug(f"Failed to fetch avatar headshot for {clean_uid}: {e}")

        fallback = f"https://www.roblox.com/headshot-thumbnail/image?userId={clean_uid}&width=150&height=150&format=png"
        AVATAR_CACHE[clean_uid] = fallback
        return fallback

    @classmethod
    def get_game_icon(cls, place_id: str) -> str:
        """Lấy URL ảnh Thumbnail của tựa Game Roblox"""
        clean_pid = "".join(filter(str.isdigit, str(place_id)))
        if not clean_pid:
            return "https://tr.rbxcdn.com/30DAY-GameIcon-Default/150/150/GameIcon/Png/noFilter"

        if clean_pid in GAME_ICON_CACHE:
            return GAME_ICON_CACHE[clean_pid]

        url = f"https://thumbnails.roblox.com/v1/places/gameicons?placeIds={clean_pid}&size=150x150&format=Png"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("data", [])
                if items and items[0].get("imageUrl"):
                    img_url = items[0]["imageUrl"]
                    GAME_ICON_CACHE[clean_pid] = img_url
                    return img_url
        except Exception as e:
            logger.debug(f"Failed to fetch game icon for {clean_pid}: {e}")

        fallback = "https://tr.rbxcdn.com/30DAY-GameIcon-Default/150/150/GameIcon/Png/noFilter"
        GAME_ICON_CACHE[clean_pid] = fallback
        return fallback


# Singleton instance
presence_tracker = RobloxPresenceTracker()
