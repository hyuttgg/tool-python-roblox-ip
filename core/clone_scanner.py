# -*- coding: utf-8 -*-
"""
Roblox Cloned Applications & Multi-Instance Scanner
Quét và phát hiện tất cả các ứng dụng Roblox đã được nhân bản (Cloned Apps, Multi-Instances,
Roblox Account Manager Profiles, LDPlayer/Nox/MuMu VMs trên ổ đĩa) NGAY CẢ KHI NGƯỜI DÙNG CHƯA MỞ!
Tự động gán sẵn Tag ID và Dedicated IP riêng cho từng bản nhân bản.
"""

import os
import json
import glob
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from config.logging import setup_logger

logger = setup_logger("clone_scanner")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CLONE_DB_FILE = os.path.join(DATA_DIR, "cloned_profiles.json")

@dataclass
class RobloxCloneProfile:
    tag_id: str
    name: str
    clone_type: str  # EMULATOR_VM, RAM_ACCOUNT, APP_CLONE, WINDOWS_CLIENT
    path_or_id: str
    status: str  # RUNNING, CLOSED_READY
    assigned_ip: str = ""
    region: str = ""
    account_username: str = ""

class RobloxCloneScanner:
    """Quét và nhận diện các bản nhân bản Roblox dù đang đóng hay mở"""

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.cached_clones: List[RobloxCloneProfile] = []

    def scan_all_clones(self) -> List[RobloxCloneProfile]:
        """
        Quét toàn diện:
        1. Quét các máy ảo Emulator đã tạo trên ổ đĩa (LDPlayer, Nox, MuMu, MEmu, BlueStacks)
        2. Quét tài khoản trong Roblox Account Manager (nếu có)
        3. Quét các thư mục/phiên bản nhân bản trên Windows
        4. Đọc từ database clone đã lưu trước đó
        """
        user_home = os.path.expanduser("~")
        discovered: List[RobloxCloneProfile] = []

        # 1. Quét LDPlayer / Nox / BlueStacks Multi-Instances trên ổ đĩa PC (nếu trên Windows)
        if os.name == "nt":
            emulator_vm_dirs = [
                (r"C:\LDPlayer\LDPlayer9\vms", "LDPlayer9"),
                (r"D:\LDPlayer\LDPlayer9\vms", "LDPlayer9"),
                (r"C:\LDPlayer\LDPlayer4.0\vms", "LDPlayer4"),
                (r"D:\LDPlayer\LDPlayer4.0\vms", "LDPlayer4"),
                (r"C:\Program Files\Nox\BignoxVMS", "NoxPlayer"),
                (r"D:\Program Files\Nox\BignoxVMS", "NoxPlayer"),
                (r"C:\Program Files\Microvirt\MEmu\MemuHyperv VMs", "MEmu"),
                (r"C:\Program Files\BlueStacks_nxt\Engine\UserData\Instances", "BlueStacks"),
                (os.path.join(user_home, "Documents", "LDPlayer"), "LDPlayer-Doc"),
            ]

            for vm_root, emu_name in emulator_vm_dirs:
                if os.path.exists(vm_root) and os.path.isdir(vm_root):
                    try:
                        for sub in os.listdir(vm_root):
                            sub_path = os.path.join(vm_root, sub)
                            if os.path.isdir(sub_path) and ("leidian" in sub.lower() or "nox" in sub.lower() or "instance" in sub.lower() or "memu" in sub.lower()):
                                tag_num = len(discovered) + 1
                                discovered.append(RobloxCloneProfile(
                                    tag_id=f"ROBLOX-CLONE-{tag_num:02d}",
                                    name=f"{emu_name}-{sub}",
                                    clone_type="EMULATOR_VM",
                                    path_or_id=sub_path,
                                    status="CLOSED_READY"
                                ))
                    except Exception as e:
                        logger.warning(f"Error scanning VM dir {vm_root}: {e}")

            # 2. Quét cấu hình Roblox Account Manager (RAM) trên Windows
            ram_account_files = [
                os.path.join(user_home, "AppData", "Local", "Roblox Account Manager", "Accounts.json"),
                os.path.join(user_home, "Desktop", "Roblox Account Manager", "Accounts.json"),
                os.path.join(user_home, "Downloads", "Roblox Account Manager", "Accounts.json"),
            ]
            for ram_f in ram_account_files:
                if os.path.exists(ram_f):
                    try:
                        with open(ram_f, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            accounts = data if isinstance(data, list) else data.get("Accounts", [])
                            for acc in accounts:
                                acc_name = acc.get("Username") or acc.get("Name") or f"Account_{len(discovered)+1}"
                                tag_num = len(discovered) + 1
                                discovered.append(RobloxCloneProfile(
                                    tag_id=f"ROBLOX-CLONE-{tag_num:02d}",
                                    name=f"RAM-{acc_name}",
                                    clone_type="RAM_ACCOUNT",
                                    path_or_id=ram_f,
                                    status="CLOSED_READY",
                                    account_username=acc_name
                                ))
                    except Exception:
                        pass
        else:
            # Quét trên môi trường ANDROID / TERMUX
            # 1. Quét danh sách package cài đặt qua lệnh pm
            try:
                import subprocess
                pm_out = subprocess.check_output(["pm", "list", "packages", "-u"], text=True, stderr=subprocess.DEVNULL, timeout=2)
                for line in pm_out.splitlines():
                    if "roblox" in line.lower() or "clone" in line.lower() or "parallel" in line.lower():
                        pkg = line.replace("package:", "").strip()
                        if pkg and "crash" not in pkg:
                            tag_num = len(discovered) + 1
                            discovered.append(RobloxCloneProfile(
                                tag_id=f"ROBLOX-CLONE-{tag_num:02d}",
                                name=f"AndroidPkg-{pkg}",
                                clone_type="APP_CLONE",
                                path_or_id=pkg,
                                status="CLOSED_READY"
                            ))
            except Exception:
                pass

            # 2. Quét các thư mục lưu trữ Dual Apps / Multi-User trên Android
            android_dual_roots = [
                "/storage/emulated/0/Android/data/com.roblox.client",
                "/storage/emulated/999/Android/data/com.roblox.client",
                "/storage/emulated/10/Android/data/com.roblox.client",
                "/data/data/com.roblox.client",
                "/data/user/0/com.roblox.client",
                "/data/user/999/com.roblox.client",
                "/data/user/10/com.roblox.client",
            ]
            for pth in android_dual_roots:
                if os.path.exists(pth):
                    tag_num = len(discovered) + 1
                    user_label = "DualApp-999" if "999" in pth else ("WorkProfile-10" if "10" in pth else "MainUser-0")
                    discovered.append(RobloxCloneProfile(
                        tag_id=f"ROBLOX-CLONE-{tag_num:02d}",
                        name=f"Roblox-{user_label}",
                        clone_type="APP_CLONE",
                        path_or_id=pth,
                        status="CLOSED_READY"
                    ))

            # 3. Quét các thư mục Executor trên Android (/sdcard/Delta, /sdcard/Arceus X,...)
            executor_android_roots = [
                ("/sdcard/Delta", "Delta-Android"),
                ("/storage/emulated/0/Delta", "Delta-Android"),
                ("/sdcard/Arceus X", "ArceusX-Android"),
                ("/sdcard/ArceusX", "ArceusX-Android"),
                ("/sdcard/Codex", "Codex-Android"),
                ("/sdcard/Fluxus", "Fluxus-Android"),
                ("/sdcard/VegaX", "VegaX-Android"),
                ("/sdcard/Hydrogen", "Hydrogen-Android"),
            ]
            for efolder, ename in executor_android_roots:
                if os.path.exists(efolder) and not any(x.path_or_id == efolder for x in discovered):
                    tag_num = len(discovered) + 1
                    discovered.append(RobloxCloneProfile(
                        tag_id=f"ROBLOX-CLONE-{tag_num:02d}",
                        name=f"{ename}-Instance",
                        clone_type="APP_CLONE",
                        path_or_id=efolder,
                        status="CLOSED_READY"
                    ))

        # 3. Đọc từ file đã lưu nếu có
        saved_clones = self._load_saved_clones()
        
        # Nếu chưa tìm thấy clone nào trên đĩa, tự động tạo sẵn các Slot Clone tiêu chuẩn (mặc định 5 Slot Clone)
        if not discovered and not saved_clones:
            default_slots = [
                ("ROBLOX-CLONE-01", "Roblox-Clone-Client-01", "APP_CLONE"),
                ("ROBLOX-CLONE-02", "Roblox-Clone-Client-02", "APP_CLONE"),
                ("ROBLOX-CLONE-03", "Roblox-Clone-Client-03", "APP_CLONE"),
                ("ROBLOX-CLONE-04", "Roblox-Clone-Client-04", "APP_CLONE"),
                ("ROBLOX-CLONE-05", "Roblox-Clone-Client-05", "APP_CLONE"),
            ]
            for t_id, t_name, t_type in default_slots:
                discovered.append(RobloxCloneProfile(
                    tag_id=t_id,
                    name=t_name,
                    clone_type=t_type,
                    path_or_id="Auto-Registered Slot",
                    status="CLOSED_READY"
                ))
        elif saved_clones:
            # Gộp và giữ lại các cấu hình IP đã lưu
            existing_tags = {c.tag_id for c in discovered}
            for sc in saved_clones:
                if sc.tag_id not in existing_tags:
                    discovered.append(sc)

        self.cached_clones = discovered
        self._save_clones(discovered)
        logger.info(f"Discovered {len(discovered)} cloned Roblox profiles/instances.")
        return discovered

    def _load_saved_clones(self) -> List[RobloxCloneProfile]:
        if os.path.exists(CLONE_DB_FILE):
            try:
                with open(CLONE_DB_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return [RobloxCloneProfile(**item) for item in data]
            except Exception:
                pass
        return []

    def _save_clones(self, clones: List[RobloxCloneProfile]):
        try:
            with open(CLONE_DB_FILE, "w", encoding="utf-8") as f:
                json.dump([asdict(c) for c in clones], f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def add_custom_clone_slot(self, name: str, count: int = 1) -> List[RobloxCloneProfile]:
        """Thêm các slot nhân bản mới theo yêu cầu"""
        clones = self._load_saved_clones() or self.cached_clones
        start_idx = len(clones) + 1
        for i in range(count):
            tag_id = f"ROBLOX-CLONE-{start_idx + i:02d}"
            clones.append(RobloxCloneProfile(
                tag_id=tag_id,
                name=f"{name}-{start_idx + i:02d}" if count > 1 else name,
                clone_type="APP_CLONE",
                path_or_id="User Registered",
                status="CLOSED_READY"
            ))
        self._save_clones(clones)
        self.cached_clones = clones
        return clones
