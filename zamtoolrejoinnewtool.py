# -*- coding: utf-8 -*-
"""
⚡ ROBLOX AUTO-REJOIN MASTER LAUNCHER (BACKWARDS COMPATIBLE REDIRECT) ⚡
Tự động chuyển tiếp thực thi sang launcher.py
"""
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LAUNCHER_PATH = os.path.join(CURRENT_DIR, "launcher.py")

if os.path.exists(LAUNCHER_PATH):
    with open(LAUNCHER_PATH, "r", encoding="utf-8") as f:
        exec(f.read())
else:
    from controller import MasterController
    MasterController().main_menu()


