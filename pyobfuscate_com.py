# -*- coding: utf-8 -*-
"""
ROBLOX MULTI-TAG MASTER CONTROLLER ENTRYPOINT
Launcher entrypoint for Windows PC, Termux Android, Linux & Emulators.
Tích hợp:
  - 100% Độc lập: Mỗi Tag nhận 1 IP, 1 HWID, 1 MAC, 1 Client-UUID, 1 User-Agent và 1 cặp DNS riêng.
  - Per-Tag Multi-Game Hub: Mỗi Tag có thể join vào 1 Game khác nhau (Blox Fruits, King Legacy, Fisch, PS99...).
  - Nhúng sâu Java Engine: Selection Sort Engine & Deep Network Prober trên Java 8 JRE.
  - Auto-Restart Watchdog: Lua Heartbeat định kỳ 2.5s & tự động mở lại khi acc bị văng (Error 277, Kick, Crash).
  - Quy trình 1-Chạm (Master Auto-Pipeline): Tự động hóa toàn diện.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from controller import MasterController

if __name__ == "__main__":
    try:
        controller = MasterController()
        controller.main_menu()
    except (KeyboardInterrupt, EOFError):
        print("\n[!] Tạm biệt!")
        sys.exit(0)