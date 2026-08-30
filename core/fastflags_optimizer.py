# -*- coding: utf-8 -*-
"""
Roblox FastFlags Manager & Performance Optimizer
Cấu hình và triển khai ClientAppSettings.json để tối ưu hóa hiệu năng,
mở khóa 120/144/240 FPS, giảm 40-60% RAM & GPU khi cày nhiều acc trên Android / Termux / PC.
Dựa trên kiến trúc FastFlagsManager từ DroidBlox-kt.
"""

import os
import sys
import json
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple
from config.logging import setup_logger

logger = setup_logger("fastflags_optimizer")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "fastflags_config.json")


# CÁC BỘ PRESET FASTFLAGS CHUYÊN DỤNG
FASTFLAGS_PRESETS = {
    "ULTRA_FPS": {
        "name": "⚡ Siêu Tốc Độ (Ultra FPS / Giảm Đồ Họa)",
        "description": "Mở khóa 120/144 FPS, tắt đổ bóng, giảm chi tiết bề mặt và hiệu ứng hậu kỳ.",
        "flags": {
            "FFlagTaskSchedulerLimitTargetFps": "144",
            "DFIntTaskSchedulerTargetFps": "144",
            "FIntRenderShadowIntensity": "0",
            "FFlagDisablePostFx": "True",
            "FIntTerrainArraySliceSize": "0",
            "FFlagDebugGraphicsDisableDirect3D11": "False",
            "FIntFRMMinGrassDistance": "0",
            "FIntFRMMaxGrassDistance": "0",
            "FFlagGlobalWindEnabled": "False",
            "FFlagFastGPULightCulling3": "True"
        }
    },
    "POTATO_MODE": {
        "name": "🥔 Chế Độ Máy Yếu / Treo Nhiều Acc (Potato Low-RAM Mode)",
        "description": "Tối ưu hóa tối đa cho Android / UGPhone / Giả lập cày nhiều acc: Tắt texture, tắt cỏ 3D, giảm tiêu thụ RAM.",
        "flags": {
            "FFlagTaskSchedulerLimitTargetFps": "60",
            "DFIntTaskSchedulerTargetFps": "60",
            "FIntRenderShadowIntensity": "0",
            "FFlagDisablePostFx": "True",
            "FIntTerrainArraySliceSize": "0",
            "FIntFRMMinGrassDistance": "0",
            "FIntFRMMaxGrassDistance": "0",
            "FFlagGlobalWindEnabled": "False",
            "FIntRenderGrassDetailStrands": "0",
            "FFlagDebugDisableOptimizedTextureLoading": "True",
            "FIntMeshContentProviderLOD": "0",
            "FFlagDebugGraphicsPreferD3D11": "True"
        }
    },
    "BALANCED": {
        "name": "⚖️ Cân Bằng (Balanced Mode - Mượt & Đẹp)",
        "description": "Mở khóa 120 FPS, giữ đồ họa vừa phải, tối ưu luồng CPU.",
        "flags": {
            "FFlagTaskSchedulerLimitTargetFps": "120",
            "DFIntTaskSchedulerTargetFps": "120",
            "FFlagFastGPULightCulling3": "True",
            "FFlagGlobalWindEnabled": "True"
        }
    }
}


class FastFlagsOptimizer:
    """Quản lý và triển khai FastFlags cho Roblox Client trên PC và Android"""

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.active_preset: str = "ULTRA_FPS"
        self.custom_flags: Dict[str, str] = {}
        self._load_config()

    def _load_config(self) -> None:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.active_preset = data.get("active_preset", "ULTRA_FPS")
                    self.custom_flags = data.get("custom_flags", {})
            except Exception as e:
                logger.warning(f"Error loading fastflags config: {e}")

    def save_config(self) -> None:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "active_preset": self.active_preset,
                    "custom_flags": self.custom_flags
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving fastflags config: {e}")

    def get_effective_flags(self) -> Dict[str, str]:
        """Lấy toàn bộ FastFlags đang áp dụng (Kết hợp Preset và Custom Flags)"""
        flags = {}
        if self.active_preset in FASTFLAGS_PRESETS:
            flags.update(FASTFLAGS_PRESETS[self.active_preset]["flags"])
        flags.update(self.custom_flags)
        return flags

    def set_preset(self, preset_key: str) -> bool:
        if preset_key in FASTFLAGS_PRESETS:
            self.active_preset = preset_key
            self.save_config()
            logger.info(f"Active FastFlags preset set to: {preset_key}")
            return True
        return False

    def set_custom_flag(self, flag_name: str, flag_value: str) -> None:
        self.custom_flags[flag_name] = str(flag_value)
        self.save_config()

    def remove_custom_flag(self, flag_name: str) -> None:
        if flag_name in self.custom_flags:
            del self.custom_flags[flag_name]
            self.save_config()

    def generate_client_app_settings_json(self) -> str:
        """Sinh chuỗi JSON ClientAppSettings chuẩn của Roblox"""
        return json.dumps(self.get_effective_flags(), indent=2)

    def deploy_to_android(self) -> Dict[str, List[str]]:
        """Triển khai ClientAppSettings.json vào các thư mục Android nội bộ"""
        results = {"deployed": [], "failed": []}
        json_content = self.generate_client_app_settings_json()

        android_targets = [
            "/sdcard/Roblox/ClientSettings",
            "/storage/emulated/0/Roblox/ClientSettings",
            "/data/data/com.roblox.client/files/ClientSettings",
            "/data/data/com.roblox.client/app_textures",
            "/sdcard/Delta/ClientSettings",
            "/sdcard/Arceus X/ClientSettings",
            "/sdcard/Codex/ClientSettings"
        ]

        for target_dir in android_targets:
            try:
                os.makedirs(target_dir, exist_ok=True)
                target_file = os.path.join(target_dir, "ClientAppSettings.json")
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(json_content)
                results["deployed"].append(target_file)
                logger.info(f"Deployed FastFlags to Android: {target_file}")
            except Exception as e:
                results["failed"].append(f"{target_dir}: {e}")

        return results

    def deploy_to_pc(self) -> Dict[str, List[str]]:
        """Triển khai ClientAppSettings.json vào các thư mục Roblox trên PC (Windows / Bloxstrap)"""
        results = {"deployed": [], "failed": []}
        json_content = self.generate_client_app_settings_json()

        local_app = os.environ.get("LOCALAPPDATA", "")
        pc_targets = []
        if local_app:
            # 1. Roblox Official Client
            versions_dir = os.path.join(local_app, "Roblox", "Versions")
            if os.path.exists(versions_dir):
                for entry in os.scandir(versions_dir):
                    if entry.is_dir() and os.path.exists(os.path.join(entry.path, "RobloxPlayerBeta.exe")):
                        pc_targets.append(os.path.join(entry.path, "ClientSettings"))

            pc_targets.append(os.path.join(local_app, "Roblox", "ClientSettings"))

            # 2. Bloxstrap
            pc_targets.append(os.path.join(local_app, "Bloxstrap", "Modifications", "ClientSettings"))

        for target_dir in pc_targets:
            try:
                os.makedirs(target_dir, exist_ok=True)
                target_file = os.path.join(target_dir, "ClientAppSettings.json")
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(json_content)
                results["deployed"].append(target_file)
                logger.info(f"Deployed FastFlags to PC: {target_file}")
            except Exception as e:
                results["failed"].append(f"{target_dir}: {e}")

        return results

    def deploy_via_adb(self, adb_bin: Optional[str] = None, device_id: Optional[str] = None) -> bool:
        """Đẩy ClientAppSettings.json vào thiết bị Android qua ADB"""
        bin_path = adb_bin or shutil.which("adb")
        if not bin_path:
            return False

        temp_json = os.path.join(DATA_DIR, "ClientAppSettings.json")
        with open(temp_json, "w", encoding="utf-8") as f:
            f.write(self.generate_client_app_settings_json())

        target_remote_dir = "/sdcard/Roblox/ClientSettings"
        target_remote_file = f"{target_remote_dir}/ClientAppSettings.json"

        cmd_base = [bin_path]
        if device_id:
            cmd_base += ["-s", device_id]

        try:
            subprocess.run(cmd_base + ["shell", "mkdir", "-p", target_remote_dir], capture_output=True, timeout=3)
            res = subprocess.run(cmd_base + ["push", temp_json, target_remote_file], capture_output=True, timeout=3)
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Failed to push FastFlags via ADB: {e}")
            return False


# Singleton instance
fastflags_optimizer = FastFlagsOptimizer()
