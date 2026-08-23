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
        if os.name == "nt":
            return self._scan_windows_processes()
        else:
            return self._scan_android_linux_processes()

    def _scan_windows_processes(self) -> List[Dict]:
        procs = []
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
                                "mem": mem,
                                "type": "WINDOWS"
                            })
                        except ValueError:
                            pass
        except Exception as e:
            logger.error(f"Error scanning Windows processes: {e}")
        return procs

    def _scan_android_linux_processes(self) -> List[Dict]:
        """Quét tiến trình trên Android / Termux / Linux (Hỗ trợ cả Root và Non-Root)"""
        procs = []
        target_keywords = [
            "com.roblox.client", "roblox", "arceus", "delta", "codex", "fluxus", 
            "vegax", "hydrogen", "parallel", "dualapp", "cloner"
        ]

        # 1. Thử dùng psutil nếu có sẵn
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'username', 'memory_info']):
                try:
                    pinfo = proc.info
                    name = pinfo.get('name') or ""
                    cmdline = " ".join(pinfo.get('cmdline') or [])
                    full_str = f"{name} {cmdline}".lower()

                    if any(kw in full_str for kw in target_keywords) and "crash" not in full_str:
                        mem_bytes = pinfo['memory_info'].rss if pinfo.get('memory_info') else 0
                        mem_mb = f"{mem_bytes / (1024*1024):.1f} MB" if mem_bytes > 0 else "Active"
                        user = pinfo.get('username') or "u0"
                        
                        # Xác định nhãn tiến trình
                        proc_title = name
                        if "com.roblox.client" in cmdline:
                            proc_title = "com.roblox.client"
                        elif name:
                            proc_title = name

                        procs.append({
                            "name": proc_title,
                            "pid": pinfo['pid'],
                            "session": user,
                            "mem": mem_mb,
                            "type": "ANDROID_PSUTIL",
                            "cmdline": cmdline
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass

        # 2. Nếu psutil chưa tìm thấy hoặc không đủ quyền, duyệt trực tiếp /proc hoặc gọi lệnh ps
        if not procs:
            # Thử qua ps command
            for cmd in [["ps", "-A", "-o", "PID,USER,NAME,ARGS"], ["ps", "-ef"], ["ps", "-A"], ["ps"]]:
                try:
                    out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=2)
                    lines = out.strip().splitlines()
                    if len(lines) > 1:
                        for line in lines[1:]:
                            line_lower = line.lower()
                            if any(kw in line_lower for kw in target_keywords) and "grep" not in line_lower:
                                parts = line.split()
                                if len(parts) >= 2:
                                    try:
                                        # Tìm PID (thường là cột 0 hoặc cột 1)
                                        pid_val = None
                                        user_val = "u0"
                                        for p in parts[:3]:
                                            if p.isdigit():
                                                pid_val = int(p)
                                                break
                                        if "u0_" in line or "u999_" in line or "u10_" in line:
                                            for p in parts:
                                                if p.startswith("u"):
                                                    user_val = p
                                                    break

                                        if pid_val and not any(x["pid"] == pid_val for x in procs):
                                            p_name = parts[-1] if len(parts) > 1 else "com.roblox.client"
                                            procs.append({
                                                "name": p_name,
                                                "pid": pid_val,
                                                "session": user_val,
                                                "mem": "Live",
                                                "type": "ANDROID_PS"
                                            })
                                    except Exception:
                                        pass
                        if procs:
                            break
                except Exception:
                    continue

        # 3. Quét trực tiếp thư mục /proc (Cực kỳ chính xác trên Android Linux)
        if not procs and os.path.exists("/proc"):
            try:
                for entry in os.listdir("/proc"):
                    if entry.isdigit():
                        pid_int = int(entry)
                        cmdline_path = f"/proc/{entry}/cmdline"
                        status_path = f"/proc/{entry}/status"
                        try:
                            if os.path.exists(cmdline_path):
                                with open(cmdline_path, "rb") as f:
                                    cmdline_raw = f.read().replace(b"\x00", b" ").decode("utf-8", errors="ignore").strip()
                                    if any(kw in cmdline_raw.lower() for kw in target_keywords):
                                        user_tag = "Android App"
                                        if os.path.exists(status_path):
                                            with open(status_path, "r", errors="ignore") as sf:
                                                for sline in sf:
                                                    if sline.startswith("Uid:"):
                                                        uids = sline.split()
                                                        if len(uids) > 1:
                                                            user_tag = f"UID:{uids[1]}"
                                                        break
                                        if not any(x["pid"] == pid_int for x in procs):
                                            procs.append({
                                                "name": cmdline_raw.split()[0] if cmdline_raw else "com.roblox.client",
                                                "pid": pid_int,
                                                "session": user_tag,
                                                "mem": "Active",
                                                "type": "ANDROID_PROC"
                                            })
                        except Exception:
                            continue
            except Exception as e:
                logger.error(f"Error scanning /proc: {e}")

        return procs

    def _get_window_info_for_pid(self, target_pid: int) -> Dict:
        """Tìm HWND, Title và Tọa độ của cửa sổ thuộc PID"""
        result = {"hwnd": 0, "title": "Roblox Client", "class_name": "ROBLOX_APP", "rect": WindowRect()}
        
        # Xử lý trên Windows
        if self.user32:
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

        # Xử lý trên Android / Termux
        result["class_name"] = "ANDROID_ROBLOX_INSTANCE"
        result["rect"] = WindowRect(left=0, top=0, right=1080, bottom=2400, width=1080, height=2400)
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
            screen_pos = f"PID:{p['pid']} [{p.get('session', 'u0')}]" if p.get("type", "").startswith("ANDROID") else (
                f"PID:{p['pid']} [{rect.width}x{rect.height}]" if rect.width > 0 else f"PID:{p['pid']} [Active]"
            )

            inst_title = p["name"] if p.get("type", "").startswith("ANDROID") else (win_info["title"] or f"Roblox Instance #{idx}")

            inst = RobloxWindowInstance(
                tag_id=tag_id,
                hwnd=win_info["hwnd"],
                title=inst_title,
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

    def scan_roblox_instances(self) -> List[RobloxWindowInstance]:
        """Tương thích alias quét tiến trình Roblox"""
        return self.scan_active_roblox_windows()

