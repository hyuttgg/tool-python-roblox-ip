# -*- coding: utf-8 -*-
"""
Roblox Player Log Monitor & Disconnect Detector (Cross-Platform: Windows & Android)
Theo dõi thời gian thực các tệp log của Roblox Player:
  - Windows: %LOCALAPPDATA%\\Roblox\\logs
  - Android / Termux / Root: /data/data/com.roblox.client/files/logs hoặc /sdcard/Android/data/com.roblox.client/files/logs
  - Tự động tìm tệp log mới nhất của tiến trình Roblox Client.
  - Tail từng byte dữ liệu mới sinh ra mà không quét lại các sự cố cũ.
  - Bắt trọn vẹn các mã lỗi mất kết nối kinh điển (Error 277, 279, 268, 273, Kicked, Idle 20m).
"""

import os
import sys
import time
from typing import Optional, List, Tuple
from config.logging import setup_logger

logger = setup_logger("roblox_log_monitor")

# Danh sách toàn diện các dấu hiệu mất kết nối / disconnect markers trong log Roblox
DISCONNECT_MARKERS: Tuple[str, ...] = (
    "connection lost",
    "lost connection",
    "error code 277",
    "error code: 277",
    "error code 279",
    "error code: 279",
    "error code 268",
    "error code: 268",
    "error code 273",
    "error code: 273",
    "error code 267",
    "error code: 267",
    "error code 271",
    "error code 272",
    "error code 280",
    "error code: 280",
    "error code 282",
    "error code 284",
    "error code 285",
    "error code 286",
    "error code 524",
    "error code: 524",
    "error code 529",
    "error code: 529",
    "error code 610",
    "error code: 610",
    "error code 773",
    "error code: 773",
    "disconnected for being idle",
    "idled for 20 minutes",
    "you were kicked from this experience",
    "disconnect reason received",
    "game disconnected",
    "security detection",
    "authentication failed",
    "received disconnect with reason",
    "connection closed by server",
    "client crashed",
    "out of memory",
    "memory exception",
    "hyperion exception",
    "byfron",
)

# Phân loại chuyên sâu các lỗi Roblox phổ biến
ERROR_TAXONOMY: Dict[str, Dict[str, str]] = {
    "268": {
        "category": "KICK_BYFRON_UNEXPECTED_CLIENT",
        "title": "Bị Kick: Unexpected Client Behavior (Error 268)",
        "desc": "Roblox phát hiện can thiệp vào Client, thay đổi IP đột ngột khi đang trong game hoặc file bị sửa.",
        "action": "Tự động đổi IP Proxy sạch mới, dọn Cache và mở lại Tag."
    },
    "273": {
        "category": "SAME_ACCOUNT_LAUNCHED",
        "title": "Bị Kick: Cùng tài khoản đăng nhập từ nơi khác (Error 273)",
        "desc": "Tài khoản đang bị chạy đè trên thiết bị khác hoặc tiến trình cũ chưa thoát hết.",
        "action": "Dọn sạch tiến trình cũ theo PID, chờ 10s cooldown rồi join lại."
    },
    "277": {
        "category": "CONNECTION_LOST",
        "title": "Mất kết nối mạng (Error 277)",
        "desc": "Mất kết nối tới Server Roblox (Proxy timeout / đứt mạng / lag quá cao).",
        "action": "Kiểm tra Proxy, tự động định tuyến lại IP mới và Rejoin game."
    },
    "279": {
        "category": "CONNECTION_ATTEMPT_FAILED",
        "title": "Không thể kết nối vào Server (Error 279)",
        "desc": "Không thể handshake với Game Server Roblox (thường do Proxy lỗi port hoặc DNS chặn).",
        "action": "Đổi DNS sang 1.1.1.1 / 8.8.8.8 và chọn Server Region khác."
    },
    "267": {
        "category": "KICKED_BY_GAME_SCRIPT",
        "title": "Bị Kick bởi Game Script (Error 267)",
        "desc": "Server Script trong game chủ động Kick (anti-afk của game, bot detection của Dev game).",
        "action": "Tự động Server Hop sang Server khác để tránh bị Mod/Script chú ý."
    },
    "524": {
        "category": "UNAUTHORIZED_JOIN",
        "title": "Không có quyền tham gia Server (Error 524 / 403)",
        "desc": "Server riêng (VIP Server) đã hết hạn hoặc không có quyền vào.",
        "action": "Chuyển sang quét Public Server mới cùng Region."
    },
    "529": {
        "category": "ROBLOX_SERVICE_DOWN",
        "title": "Máy chủ Roblox bảo trì / quá tải (Error 529 / HTTP 500)",
        "desc": "Hệ thống Roblox Backend gặp sự cố kỹ thuật diện rộng.",
        "action": "Tạm dừng mở lại, chờ hệ thống Roblox ổn định sau 30-60s."
    },
    "610": {
        "category": "HTTP_400_JOIN_ERROR",
        "title": "Lỗi tài khoản không thể tham gia Game (Error 610)",
        "desc": "Phiên đăng nhập Roblox Cookie/Token bị lỗi hoặc tài khoản chưa xác minh.",
        "action": "Làm mới Session và thử lại."
    },
    "773": {
        "category": "TELEPORT_RESTRICTED",
        "title": "Dịch chuyển thất bại (Error 773 / Teleport Failed)",
        "desc": "Không thể dịch chuyển sang Sub-Place (Sea 1 sang Sea 2, Trade Hub...).",
        "action": "Chờ 15s rồi kích hoạt Rejoin lại Place ID đích."
    },
    "idle": {
        "category": "IDLE_TIMEOUT_20M",
        "title": "Treo máy quá 20 phút (Idle 20 Minutes Disconnect)",
        "desc": "Roblox tự động ngắt kết nối do không có thao tác bàn phím/chuột trong 20 phút.",
        "action": "Tự động Rejoin ngay lập tức và bơm script Anti-Idle qua Autoexec."
    },
    "security": {
        "category": "SECURITY_DETECTION",
        "title": "Phát hiện bảo mật (Security Detection / Auth Failed)",
        "desc": "Hệ thống bảo mật Roblox chặn kết nối do dải IP bị gắn cờ Datacenter/Spam.",
        "action": "Đổi sang Proxy Residential hoặc ProxyScrape IP sạch."
    }
}


ANDROID_POSSIBLE_LOG_DIRS = [
    "/data/data/com.roblox.client/files/logs",
    "/sdcard/Android/data/com.roblox.client/files/logs",
    "/storage/emulated/0/Android/data/com.roblox.client/files/logs",
    "/data/media/0/Android/data/com.roblox.client/files/logs",
]


class RobloxLogMonitor:
    """Theo dõi log thời gian thực của Roblox Player trên Windows PC & Android / Termux"""

    def __init__(self, log_dir: Optional[str] = None):
        if log_dir:
            self.log_dir = log_dir
        else:
            self.log_dir = self._detect_platform_log_dir()

        self.current_log: Optional[str] = None
        self.position: int = 0
        self.pending_line: str = ""
        self.last_detected_reason: Optional[str] = None
        self._select_latest(start_at_end=True)

    def _detect_platform_log_dir(self) -> str:
        """Tự động nhận diện thư mục log theo nền tảng (Windows vs Android/Linux)"""
        if os.name == "nt":
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            if local_app_data:
                win_path = os.path.join(local_app_data, "Roblox", "logs")
                if os.path.isdir(win_path):
                    return win_path
            return os.path.expandvars(r"%LOCALAPPDATA%\Roblox\logs")
        else:
            # Android / Termux / Linux
            for adir in ANDROID_POSSIBLE_LOG_DIRS:
                if os.path.isdir(adir):
                    return adir
            return ANDROID_POSSIBLE_LOG_DIRS[0]

    def get_latest_log(self) -> Optional[str]:
        """Tìm file log mới nhất trong thư mục logs"""
        if not self.log_dir or not os.path.isdir(self.log_dir):
            return None
        try:
            entries = [
                os.path.join(self.log_dir, name)
                for name in os.listdir(self.log_dir)
                if name.lower().endswith(".log") or name.lower().endswith(".txt")
            ]
            if not entries:
                return None
            player_logs = [path for path in entries if "player" in os.path.basename(path).lower()]
            candidates = player_logs or entries
            return max(candidates, key=os.path.getmtime)
        except (FileNotFoundError, OSError, PermissionError) as e:
            logger.debug(f"Không thể đọc thư mục log Roblox ({self.log_dir}): {e}")
            return None

    def _select_latest(self, start_at_end: bool = True) -> bool:
        """Chọn file log mới nhất và đặt con trỏ đọc (mặc định tại cuối file để bỏ qua lỗi cũ)"""
        latest = self.get_latest_log()
        if not latest:
            return False
        self.current_log = latest
        self.pending_line = ""
        try:
            self.position = os.path.getsize(latest) if start_at_end else 0
        except OSError:
            self.position = 0
        return True

    def reset_to_beginning(self) -> None:
        """Đặt con trỏ đọc về đầu file (phục vụ test hoặc đọc lại)"""
        self.position = 0
        self.pending_line = ""

    def check_for_disconnect(self) -> Optional[str]:
        """
        Kiểm tra xem có sự kiện mất kết nối nào mới xuất hiện trong log không.
        Trả về chuỗi marker nếu phát hiện lỗi, ngược lại trả về None.
        """
        latest = self.get_latest_log()
        if not latest:
            return None

        # Nếu có log mới được tạo ra (Roblox vừa khởi động phiên mới)
        if latest != self.current_log:
            self.current_log = latest
            self.position = 0
            self.pending_line = ""

        try:
            size = os.path.getsize(latest)
            if size < self.position:
                # File log bị xoay vòng hoặc truncate
                self.position = 0
                self.pending_line = ""

            with open(latest, "rb") as log_file:
                log_file.seek(self.position)
                new_data = log_file.read(512 * 1024)
                self.position = log_file.tell()
        except (OSError, PermissionError):
            return None

        if not new_data:
            return None

        text = self.pending_line + new_data.decode("utf-8", errors="ignore")
        lines = text.splitlines(keepends=True)
        if lines and not lines[-1].endswith(("\n", "\r")):
            self.pending_line = lines.pop()
        else:
            self.pending_line = ""

        for line in lines:
            lowered = line.lower()
            for marker in DISCONNECT_MARKERS:
                if marker in lowered:
                    self.last_detected_reason = marker
                    logger.warning(f"Phát hiện lỗi kết nối Roblox từ log: '{marker}' (Dòng log: {line.strip()})")
                    return marker

        return None

    def check_for_disconnect_details(self) -> Optional[Dict]:
        """
        Kiểm tra lỗi và trả về dữ liệu phân tích chi tiết theo ERROR_TAXONOMY:
        { marker, code, category, title, desc, action, raw_line }
        """
        marker = self.check_for_disconnect()
        if not marker:
            return None

        # Tìm taxonomy tương ứng
        matched_info = None
        for code_key, info in ERROR_TAXONOMY.items():
            if code_key in marker:
                matched_info = {**info, "code": code_key}
                break

        if not matched_info:
            matched_info = {
                "code": "UNKNOWN",
                "category": "GENERIC_DISCONNECT",
                "title": f"Mất kết nối: {marker}",
                "desc": "Roblox client bị ngắt kết nối do sự cố không xác định.",
                "action": "Tự động kiểm tra mạng và mở lại game."
            }

        matched_info["marker"] = marker
        return matched_info


# Singleton instance
roblox_log_monitor = RobloxLogMonitor()

