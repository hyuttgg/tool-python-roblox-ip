# -*- coding: utf-8 -*-
"""
Roblox Autoexec Manager & Auto-Injector
Tự động tìm kiếm và copy script Lua vào tất cả thư mục Autoexec của các Client / Executor
(Arceus X, Delta, Codex, Fluxus, Solara, Wave, Real, LDPlayer, Nox, MuMu, v.v.)
để khi người dùng vào game là script tự động chạy và set IP riêng ngay lập tức!
"""

import os
import shutil
import subprocess
import glob
import json
from typing import List, Dict, Tuple, Optional
from config.logging import setup_logger

logger = setup_logger("autoexec_manager")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "autoexec_config.json")

COMMON_EXECUTOR_NAMES = [
    "Arceus X", "ArceusX", "Delta", "Codex", "Fluxus", "Solara",
    "Wave", "Real", "Synapse", "KRNL", "Electron", "VegaX"
]

COMMON_ADB_PATHS = [
    r"C:\LDPlayer\LDPlayer9\adb.exe",
    r"D:\LDPlayer\LDPlayer9\adb.exe",
    r"C:\LDPlayer\LDPlayer4.0\adb.exe",
    r"D:\LDPlayer\LDPlayer4.0\adb.exe",
    r"C:\Program Files\Nox\bin\nox_adb.exe",
    r"D:\Program Files\Nox\bin\nox_adb.exe",
    r"C:\Program Files\Microvirt\MEmu\adb.exe",
    r"D:\Program Files\Microvirt\MEmu\adb.exe",
    r"C:\Program Files (x86)\MuMuPlayerGlobal-12.0\shell\adb.exe",
    r"D:\Program Files (x86)\MuMuPlayerGlobal-12.0\shell\adb.exe",
    r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe",
]

ANDROID_AUTOEXEC_SDCARD_PATHS = [
    "/sdcard/Arceus X/Autoexec",
    "/sdcard/ArceusX/Autoexec",
    "/sdcard/Delta/Autoexec",
    "/sdcard/Codex/Autoexec",
    "/sdcard/Fluxus/Autoexec",
    "/storage/emulated/0/Arceus X/Autoexec",
    "/storage/emulated/0/ArceusX/Autoexec",
    "/storage/emulated/0/Delta/Autoexec",
    "/storage/emulated/0/Codex/Autoexec",
    "/storage/emulated/0/Fluxus/Autoexec"
]

class AutoexecManager:
    """Quản lý và tự động bơm script vào Autoexec folders của PC và Giả lập"""

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.cached_pc_paths: List[str] = []
        self.adb_bin: Optional[str] = None
        self._load_config()
        self._find_adb()

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.cached_pc_paths = data.get("pc_paths", [])
            except Exception:
                self.cached_pc_paths = []

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"pc_paths": list(set(self.cached_pc_paths))}, f, indent=2)
        except Exception:
            pass

    def _find_adb(self) -> Optional[str]:
        # 1. Kiểm tra ADB trong PATH
        path_adb = shutil.which("adb")
        if path_adb:
            self.adb_bin = path_adb
            return self.adb_bin

        # 2. Kiểm tra các thư mục giả lập LDPlayer, Nox, MuMu
        for candidate in COMMON_ADB_PATHS:
            if os.path.exists(candidate):
                self.adb_bin = candidate
                return self.adb_bin
        return None

    def scan_all_autoexec_folders(self) -> List[str]:
        """Tự động quét toàn bộ các thư mục Autoexec trên máy tính"""
        user_home = os.path.expanduser("~")
        search_roots = [
            os.path.join(user_home, "AppData", "Local"),
            os.path.join(user_home, "AppData", "Roaming"),
            os.path.join(user_home, "Documents"),
            os.path.join(user_home, "Desktop"),
            os.path.join(user_home, "Downloads"),
        ]

        found_folders = set(self.cached_pc_paths)

        # 1. Quét các đường dẫn trên PC (Windows / Linux)
        for root in search_roots:
            if not os.path.exists(root):
                continue
            for exc in COMMON_EXECUTOR_NAMES:
                direct_path = os.path.join(root, exc, "autoexec")
                if os.path.exists(direct_path) and os.path.isdir(direct_path):
                    found_folders.add(direct_path)
                direct_path_cap = os.path.join(root, exc, "Autoexec")
                if os.path.exists(direct_path_cap) and os.path.isdir(direct_path_cap):
                    found_folders.add(direct_path_cap)

        # 2. Quét trực tiếp các đường dẫn Executor trên thiết bị Android / Termux
        android_roots = [
            "/sdcard", "/storage/emulated/0", "/storage/emulated/999", "/storage/emulated/10"
        ]
        for a_root in android_roots:
            if os.path.exists(a_root):
                for exc in COMMON_EXECUTOR_NAMES:
                    for sub_auto in ["Autoexec", "autoexec", "scripts", "Scripts"]:
                        candidate = os.path.join(a_root, exc, sub_auto)
                        if os.path.exists(candidate) and os.path.isdir(candidate):
                            found_folders.add(candidate)
                        elif os.path.exists(os.path.join(a_root, exc)):
                            # Nếu có thư mục Executor nhưng chưa có subfolder autoexec, tạo luôn
                            try:
                                os.makedirs(candidate, exist_ok=True)
                                found_folders.add(candidate)
                            except Exception:
                                pass

        # Quét đệ quy cấp 2 trong search_roots
        for root in search_roots:
            if not os.path.exists(root):
                continue
            try:
                for entry in os.scandir(root):
                    if entry.is_dir() and not entry.name.startswith("."):
                        # Kiểm tra subfolder
                        try:
                            for sub in os.scandir(entry.path):
                                if sub.is_dir() and sub.name.lower() == "autoexec":
                                    found_folders.add(sub.path)
                        except Exception:
                            pass
            except Exception:
                pass

        valid_list = [f for f in found_folders if os.path.exists(f) and os.path.isdir(f)]
        self.cached_pc_paths = valid_list
        self._save_config()
        logger.info(f"Discovered {len(valid_list)} Autoexec folders.")
        return valid_list

    def add_custom_autoexec_path(self, path: str) -> bool:
        """Thêm thủ công 1 đường dẫn thư mục Autoexec nếu muốn"""
        if os.path.exists(path) and os.path.isdir(path):
            if path not in self.cached_pc_paths:
                self.cached_pc_paths.append(path)
                self._save_config()
            return True
        return False

    def sync_lua_to_autoexec(self, lua_script_content: str) -> Dict[str, List[str]]:
        """
        Bơm và ghi đè script Lua vào TẤT CẢ các thư mục Autoexec (PC & Android Termux & Emulator).
        Trả về kết quả chi tiết các nơi đã nạp thành công.
        """
        results = {
            "pc_synced": [],
            "android_synced": [],
            "errors": []
        }

        # 1. Đồng bộ trực tiếp vào các thư mục Autoexec tìm thấy (PC & Android Native)
        all_folders = self.scan_all_autoexec_folders()
        for folder in all_folders:
            try:
                target_file = os.path.join(folder, "roblox_auto_ip_setter.lua")
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(lua_script_content)
                # Cấp quyền đọc ghi
                try:
                    os.chmod(target_file, 0o666)
                except Exception:
                    pass
                if folder.startswith("/sdcard") or folder.startswith("/storage"):
                    results["android_synced"].append(target_file)
                else:
                    results["pc_synced"].append(target_file)
                logger.info(f"Synced Lua script to: {target_file}")
            except Exception as e:
                results["errors"].append(f"Folder ({folder}): {e}")

        # 2. Đồng bộ vào Android Emulator qua ADB (nếu chạy trên PC có giả lập nối qua ADB)
        if self.adb_bin:
            try:
                output = subprocess.check_output([self.adb_bin, "devices"], timeout=3).decode("utf-8")
                devices = []
                for line in output.splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 2 and parts[1] == "device":
                        devices.append(parts[0])

                if devices:
                    temp_lua = os.path.join(DATA_DIR, "roblox_auto_ip_setter.lua")
                    with open(temp_lua, "w", encoding="utf-8") as f:
                        f.write(lua_script_content)

                    for dev in devices:
                        for sd_path in ANDROID_AUTOEXEC_SDCARD_PATHS:
                            try:
                                subprocess.run([self.adb_bin, "-s", dev, "shell", "mkdir", "-p", f'"{sd_path}"'], capture_output=True, timeout=2)
                                target_android_file = f"{sd_path}/roblox_auto_ip_setter.lua"
                                push_res = subprocess.run([self.adb_bin, "-s", dev, "push", temp_lua, target_android_file], capture_output=True, timeout=3)
                                if push_res.returncode == 0:
                                    results["android_synced"].append(f"[{dev}] {target_android_file}")
                                    logger.info(f"Pushed to Android [{dev}]: {target_android_file}")
                            except Exception:
                                pass
            except Exception as e:
                results["errors"].append(f"ADB: {e}")

        return results

    def clean_all_autoexec_scripts(self) -> Dict[str, List[str]]:
        """Xóa toàn bộ các script đã bơm vào Autoexec trên PC và Android"""
        results = {"pc_cleaned": [], "android_cleaned": [], "errors": []}
        
        # 1. Xóa trên các thư mục local
        all_folders = self.scan_all_autoexec_folders()
        for folder in all_folders:
            for fname in ["roblox_auto_ip_setter.lua", "master_roblox_ip_setter.lua", "set_ip.lua"]:
                fpath = os.path.join(folder, fname)
                if os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                        if folder.startswith("/sdcard") or folder.startswith("/storage"):
                            results["android_cleaned"].append(fpath)
                        else:
                            results["pc_cleaned"].append(fpath)
                    except Exception as e:
                        results["errors"].append(f"{fpath}: {e}")

        # 2. Xóa trên Android ADB
        if self.adb_bin:
            try:
                output = subprocess.check_output([self.adb_bin, "devices"], timeout=3).decode("utf-8")
                devices = [l.split()[0] for l in output.splitlines() if len(l.split()) >= 2 and l.split()[1] == "device"]
                for dev in devices:
                    for sd_path in ANDROID_AUTOEXEC_SDCARD_PATHS:
                        try:
                            for fname in ["roblox_auto_ip_setter.lua", "master_roblox_ip_setter.lua", "set_ip.lua"]:
                                target = f"{sd_path}/{fname}"
                                subprocess.run([self.adb_bin, "-s", dev, "shell", f"rm -f '{target}'"], capture_output=True, timeout=2)
                                results["android_cleaned"].append(f"[{dev}] {target}")
                        except Exception:
                            pass
            except Exception as e:
                results["errors"].append(f"ADB Clean: {e}")

        return results

