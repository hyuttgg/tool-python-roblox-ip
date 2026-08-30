# -*- coding: utf-8 -*-
"""
⚡ ROBLOX AUTO-REJOIN MASTER LAUNCHER (ANDROID TERMUX & PC) ⚡
File chạy chính tại /sdcard/Download/zamtoolrejoinnewtool.py
Tự động nạp toàn bộ module lõi, khởi chạy HUD Giám sát thời gian thực và Watchdog Auto-Rejoin
Dựa trên kiến trúc DroidBlox-kt (Logcat Realtime Stream & Android Intent).
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Thiết lập đường dẫn gốc cho các module của tool
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
POSSIBLE_TOOL_DIRS = [
    CURRENT_DIR,
    os.path.join(CURRENT_DIR, "tool-python-roblox-ip-main"),
    os.path.join(CURRENT_DIR, "RobloxRejoinTool"),
    "/sdcard/Download/tool-python-roblox-ip-main",
    "/sdcard/Download/RobloxRejoinTool",
    os.path.expanduser("~/storage/shared/Download/tool-python-roblox-ip-main"),
    os.path.expanduser("~/storage/shared/Download/RobloxRejoinTool"),
    os.path.expanduser("~/tool-python-roblox-ip"),
    "/data/data/com.termux/files/home/tool-python-roblox-ip"
]

for p in POSSIBLE_TOOL_DIRS:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

if __name__ == "__main__":
    try:
        from controller import MasterController
        try:
            controller = MasterController()
            controller.main_menu()
        except (KeyboardInterrupt, EOFError):
            print("\n[!] Đã thoát tool an toàn. Tạm biệt!")
            sys.exit(0)
    except Exception as e_ctrl:
        # Fallback 1: Chạy DroidBlox Android Rejoin CLI Sentinel
        try:
            from tools.android_rejoin_cli import interactive_menu
            interactive_menu()
        except Exception:
            # Fallback 2: Chạy Termux Bridge Sentinel Loop
            try:
                from core.termux_bridge import TermuxRobloxRejoiner
                print("⚡ [ ROBLOX TERMUX AUTO-REJOIN ENGINE (FALLBACK) ] ⚡")
                rejoiner = TermuxRobloxRejoiner()
                rejoiner.start_sentinel_loop()
            except Exception as e_final:
                print(f"[!] Lỗi khởi chạy: {e_final}")
                sys.exit(1)
