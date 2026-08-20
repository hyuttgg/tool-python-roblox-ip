# -*- coding: utf-8 -*-
"""
Roblox Window & Instance Scanner
Quét tự động tất cả các cửa sổ/tiến trình Roblox đang mở trên màn hình máy tính.
"""

import os
import sys
import csv
import io
import ctypes
from ctypes import wintypes
import subprocess
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from config.logging import setup_logger

logger = setup_logger("roblox_scanner")

@dataclass
class WindowRect:
    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0
    width: int = 0
    height: int = 0

@dataclass
class RobloxWindowInstance:
    tag_id: str
    hwnd: int
    title: str
    pid: int
    process_name: str
    class_name: str
    rect: WindowRect
    screen_position: str
    memory_usage: str = "N/A"
    assigned_ip: Optional[str] = None
    region: Optional[str] = None
    account_username: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class RobloxWindowScanner:
    """Quét màn hình và tiến trình để tìm tất cả các tag/instance Roblox"""

    def __init__(self):
        self.user32 = ctypes.windll.user32 if os.name == "nt" else None
        self.kernel32 = ctypes.windll.kernel32 if os.name == "nt" else None

    def _scan_by_processes(self) -> List[Dict]:
        """Quét tiến trình hệ thống để tìm các phiên bản Roblox hoặc Emulator"""
        procs = []
        if os.name != "nt":
            return procs

        try:
            out = subprocess.check_output(
                ["tasklist", "/FO", "CSV", "/NH"], 
                text=True, 
                creationflags=0x08000000 if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            )
            reader = csv.reader(io.StringIO(out))
            for row in reader:
                if len(row) >= 5:
                    name, pid_str, session, session_num, mem = row[0], row[1], row[2], row[3], row[4]
                    name_lower = name.lower()
                    if ("roblox" in name_lower or any(em in name_lower for em in [
                        "dnplayer", "hd-player", "nox", "mumu", "ugphone", "vmos", "redfinger"
                    ])) and "crash" not in name_lower:
                        try:
                            pid = int(pid_str)
                            procs.append({
                                "name": name,
                                "pid": pid,
                                "session": session,
                                "mem": mem
                            })
                        except ValueError:
                            pass
        except Exception as e:
            logger.error(f"Error scanning processes: {e}")
        return procs

    def _get_window_info_for_pid(self, target_pid: int) -> Dict:
        """Tìm HWND, Title và Tọa độ của cửa sổ thuộc PID"""
        result = {"hwnd": 0, "title": "Roblox Client", "class_name": "WINDOWSCLIENT", "rect": WindowRect()}
        if not self.user32:
            return result

        def enum_cb(hwnd, lParam):
            if self.user32.IsWindowVisible(hwnd):
                pid = wintypes.DWORD()
                self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value == target_pid:
                    length = self.user32.GetWindowTextLengthW(hwnd)
                    title_buf = ctypes.create_unicode_buffer(length + 1)
                    self.user32.GetWindowTextW(hwnd, title_buf, length + 1)
                    
                    class_buf = ctypes.create_unicode_buffer(256)
                    self.user32.GetClassNameW(hwnd, class_buf, 256)
                    
                    rect_struct = wintypes.RECT()
                    self.user32.GetWindowRect(hwnd, ctypes.byref(rect_struct))
                    w = rect_struct.right - rect_struct.left
                    h = rect_struct.bottom - rect_struct.top
                    
                    if w > 50 and h > 50:
                        result["hwnd"] = hwnd
                        result["title"] = title_buf.value or "Roblox"
                        result["class_name"] = class_buf.value
                        result["rect"] = WindowRect(
                            left=rect_struct.left,
                            top=rect_struct.top,
                            right=rect_struct.right,
                            bottom=rect_struct.bottom,
                            width=w,
                            height=h
                        )
                        return False # Dừng duyệt khi đã tìm thấy cửa sổ chính
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        self.user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        return result

    def scan_active_roblox_windows(self) -> List[RobloxWindowInstance]:
        """
        Quét và nhận diện tất cả các tag/cửa sổ Roblox đang chạy trên màn hình.
        Tự động gán mã định danh ROBLOX-TAG-01, ROBLOX-TAG-02,...
        """
        detected_procs = self._scan_by_processes()
        instances: List[RobloxWindowInstance] = []

        for idx, p in enumerate(detected_procs, start=1):
            tag_id = f"ROBLOX-TAG-{idx:02d}"
            win_info = self._get_window_info_for_pid(p["pid"])
            rect = win_info["rect"]
            
            # Tính vị trí hiển thị
            screen_pos = f"PID:{p['pid']} [{rect.width}x{rect.height}]" if rect.width > 0 else f"PID:{p['pid']} [Active]"

            inst = RobloxWindowInstance(
                tag_id=tag_id,
                hwnd=win_info["hwnd"],
                title=win_info["title"] or f"Roblox Instance #{idx}",
                pid=p["pid"],
                process_name=p["name"],
                class_name=win_info["class_name"],
                rect=rect,
                screen_position=screen_pos,
                memory_usage=p["mem"]
            )
            instances.append(inst)

        logger.info(f"Scan complete: Found {len(instances)} active Roblox instances.")
        return instances
