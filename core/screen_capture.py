# -*- coding: utf-8 -*-
"""
Roblox Window & Screen Capture Utility (Windows & Android)
Chụp ảnh màn hình Roblox Player (hỗ trợ lưu vết khi văng game, crash, hoặc gửi qua Discord):
  - Windows: Tìm HWND ("Roblox", "Win32Window0") + DPI Awareness + PIL.ImageGrab.
  - Android / Termux: Tự động gọi lệnh 'screencap -p' qua Root/Shell.
"""

import os
import sys
import time
import subprocess
from typing import Optional
from config.logging import setup_logger

logger = setup_logger("screen_capture")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SCREENSHOTS_DIR = os.path.join(DATA_DIR, "screenshots")


def is_screenshot_supported() -> bool:
    """Kiểm tra xem hệ thống có hỗ trợ chụp màn hình hay không"""
    if os.name == "nt":
        try:
            import win32gui
            from PIL import ImageGrab
            return True
        except ImportError:
            return False
    else:
        # Android / Termux: Kiểm tra xem có lệnh screencap không
        return os.path.exists("/system/bin/screencap") or shutil_which("screencap") is not None


def shutil_which(cmd: str) -> Optional[str]:
    import shutil
    return shutil.which(cmd)


def capture_roblox_window(hwnd: Optional[int] = None, output_filename: Optional[str] = None) -> Optional[str]:
    """
    Chụp ảnh màn hình Roblox trên Windows hoặc Android.
    Trả về đường dẫn tệp ảnh đã lưu, hoặc None nếu thất bại.
    """
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    if not output_filename:
        output_filename = f"roblox_snap_{timestamp}.png"
    save_path = os.path.join(SCREENSHOTS_DIR, output_filename)

    # 1. Xử lý trên Windows
    if os.name == "nt":
        try:
            import win32gui
            from PIL import ImageGrab
            import ctypes
        except ImportError as e:
            logger.debug(f"Không thể chụp màn hình Windows: thiếu thư viện (pywin32 / Pillow): {e}")
            return None

        target_hwnd = hwnd
        if not target_hwnd or not win32gui.IsWindow(target_hwnd):
            target_hwnd = win32gui.FindWindow(None, "Roblox") or win32gui.FindWindow("Win32Window0", "Roblox")

        if not target_hwnd or not win32gui.IsWindow(target_hwnd):
            logger.debug("Không tìm thấy cửa sổ Roblox đang hoạt động để chụp ảnh.")
            return None

        try:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

            rect = win32gui.GetWindowRect(target_hwnd)
            left, top, right, bottom = rect

            if left <= -32000 or (right - left) <= 0 or (bottom - top) <= 0:
                logger.debug(f"Cửa sổ Roblox đang bị thu nhỏ: rect={rect}")
                return None

            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
            screenshot.save(save_path)
            logger.info(f"Đã chụp ảnh màn hình Roblox Windows thành công: {save_path}")
            return save_path
        except Exception as e:
            logger.warning(f"Lỗi khi chụp ảnh màn hình Roblox Windows: {e}")
            return None

    # 2. Xử lý trên Android / Termux
    else:
        try:
            # Thử qua su -c screencap hoặc screencap trực tiếp
            cmds = [
                ["su", "-c", f"screencap -p {save_path}"],
                ["screencap", "-p", save_path]
            ]
            for cmd in cmds:
                try:
                    res = subprocess.run(cmd, capture_output=True, timeout=5)
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 1000:
                        logger.info(f"Đã chụp ảnh màn hình Roblox Android thành công: {save_path}")
                        return save_path
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Lỗi chụp ảnh màn hình Android: {e}")

    return None
