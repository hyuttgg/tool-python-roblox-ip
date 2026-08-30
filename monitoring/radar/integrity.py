# -*- coding: utf-8 -*-
"""
Radar File Integrity Monitor
Kiem tra version/hash cua Roblox executable de phat hien thay doi.
KHONG tu dong ket luan "crack" — chi bao khi hash khac baseline.
"""

import os
import hashlib
import json
from typing import Optional, Dict
from dataclasses import dataclass
from config.logging import setup_logger
from config.settings import DATA_DIR

logger = setup_logger("radar_integrity")

INTEGRITY_BASELINE_FILE = os.path.join(str(DATA_DIR), "radar_integrity_baseline.json")

# Cac duong dan mac dinh cua Roblox tren Windows
ROBLOX_INSTALL_PATHS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Roblox\Versions"),
    os.path.expandvars(r"%PROGRAMFILES(x86)%\Roblox\Versions"),
    os.path.expandvars(r"%PROGRAMFILES%\Roblox\Versions"),
]


@dataclass
class IntegrityResult:
    """Ket qua kiem tra toan ven."""
    exe_found: bool = False
    exe_path: str = ""
    current_hash: str = ""
    baseline_hash: str = ""
    version: str = ""
    match: Optional[bool] = None  # None = chua co baseline
    details: str = ""


class IntegrityMonitor:
    """Giam sat toan ven file Roblox."""

    def __init__(self):
        self._baseline: Dict[str, str] = {}
        self._load_baseline()

    def _load_baseline(self) -> None:
        """Tai baseline tu file JSON."""
        if os.path.exists(INTEGRITY_BASELINE_FILE):
            try:
                with open(INTEGRITY_BASELINE_FILE, "r", encoding="utf-8") as f:
                    self._baseline = json.load(f)
            except Exception as e:
                logger.debug(f"Loi doc baseline: {e}")

    def _save_baseline(self) -> None:
        """Luu baseline vao file JSON."""
        try:
            os.makedirs(os.path.dirname(INTEGRITY_BASELINE_FILE), exist_ok=True)
            with open(INTEGRITY_BASELINE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._baseline, f, indent=2)
        except Exception as e:
            logger.debug(f"Loi luu baseline: {e}")

    def compute_hash(self, filepath: str) -> str:
        """Tinh SHA-256 hash cua file."""
        sha256 = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.debug(f"Loi tinh hash {filepath}: {e}")
            return ""

    def get_roblox_exe_path(self) -> Optional[str]:
        """Tim file RobloxPlayerBeta.exe tren he thong."""
        for base_dir in ROBLOX_INSTALL_PATHS:
            if not os.path.isdir(base_dir):
                continue
            try:
                # Roblox luu tung version trong thu muc rieng
                for version_dir in sorted(os.listdir(base_dir), reverse=True):
                    exe_path = os.path.join(base_dir, version_dir, "RobloxPlayerBeta.exe")
                    if os.path.isfile(exe_path):
                        return exe_path
            except Exception:
                continue
        return None

    def get_roblox_version(self) -> Optional[str]:
        """Lay version hien tai tu thu muc cai dat."""
        for base_dir in ROBLOX_INSTALL_PATHS:
            if not os.path.isdir(base_dir):
                continue
            try:
                versions = sorted(os.listdir(base_dir), reverse=True)
                if versions:
                    return versions[0]
            except Exception:
                continue
        return None

    def check_integrity(self) -> IntegrityResult:
        """
        Kiem tra toan ven file Roblox.

        Logic:
        - Tim RobloxPlayerBeta.exe
        - Tinh SHA-256
        - So sanh voi baseline da luu
        - Neu chua co baseline -> luu baseline moi
        - Neu khac baseline -> bao APP_CHANGED (nhung KHONG ket luan la crack)
        """
        result = IntegrityResult()

        exe_path = self.get_roblox_exe_path()
        if not exe_path:
            result.details = "Khong tim thay RobloxPlayerBeta.exe"
            return result

        result.exe_found = True
        result.exe_path = exe_path
        result.version = self.get_roblox_version() or "unknown"

        current_hash = self.compute_hash(exe_path)
        if not current_hash:
            result.details = "Khong the tinh hash file"
            return result

        result.current_hash = current_hash
        baseline_hash = self._baseline.get("exe_hash", "")
        result.baseline_hash = baseline_hash

        if not baseline_hash:
            # Chua co baseline -> luu lam baseline
            self._baseline["exe_hash"] = current_hash
            self._baseline["exe_path"] = exe_path
            self._baseline["version"] = result.version
            self._save_baseline()
            result.match = None  # Khong co gi de so sanh
            result.details = f"Baseline moi da luu (version: {result.version})"
        elif current_hash == baseline_hash:
            result.match = True
            result.details = "File toan ven — khop voi baseline"
        else:
            result.match = False
            old_version = self._baseline.get("version", "unknown")
            result.details = (
                f"Hash KHAC voi baseline! "
                f"(Baseline version: {old_version}, Current version: {result.version}). "
                f"Co the do Roblox update. Kiem tra truoc khi ket luan."
            )

        return result

    def update_baseline(self) -> bool:
        """Cap nhat baseline voi hash hien tai (goi khi xac nhan khong co van de)."""
        exe_path = self.get_roblox_exe_path()
        if not exe_path:
            return False

        current_hash = self.compute_hash(exe_path)
        if not current_hash:
            return False

        self._baseline["exe_hash"] = current_hash
        self._baseline["exe_path"] = exe_path
        self._baseline["version"] = self.get_roblox_version() or "unknown"
        self._save_baseline()
        logger.info(f"Radar integrity baseline updated: {current_hash[:16]}...")
        return True
