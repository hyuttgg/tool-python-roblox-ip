# -*- coding: utf-8 -*-
"""
⚡ ROBLOX AUTO-REJOIN & NETWORK CONTROLLER MASTER LAUNCHER ⚡
File nạp chính tại /sdcard/Download/launcher.py
Tự động định vị mã nguồn dự án tool-python-roblox-ip-main, chuyển thư mục làm việc và nạp controller.py
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 1. Tìm kiếm và định vị thư mục gốc chứa dự án
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
POSSIBLE_TOOL_DIRS = [
    os.path.join(CURRENT_DIR, "tool-python-roblox-ip-main"),
    "/sdcard/Download/tool-python-roblox-ip-main",
    os.path.expanduser("~/storage/shared/Download/tool-python-roblox-ip-main"),
    os.path.expanduser("~/tool-python-roblox-ip"),
    "/data/data/com.termux/files/home/tool-python-roblox-ip",
    CURRENT_DIR,
    os.path.join(CURRENT_DIR, "RobloxRejoinTool"),
    "/sdcard/Download/RobloxRejoinTool"
]

PROJECT_ROOT = None
for p in POSSIBLE_TOOL_DIRS:
    if os.path.exists(p) and os.path.isfile(os.path.join(p, "controller.py")):
        PROJECT_ROOT = p
        break

if PROJECT_ROOT:
    # Chuyển thư mục làm việc vào gốc dự án để nạp toàn bộ config/data/core
    try:
        os.chdir(PROJECT_ROOT)
    except Exception:
        pass
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

if __name__ == "__main__":
    try:
        # Nạp Master Controller của dự án
        from controller import MasterController
        try:
            controller = MasterController()
            controller.main_menu()
        except (KeyboardInterrupt, EOFError):
            print("\n[!] Đã dừng tool an toàn. Hẹn gặp lại!")
            sys.exit(0)
    except Exception as e_ctrl:
        print(f"[!] Chú ý khi nạp controller.py: {e_ctrl}")
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
