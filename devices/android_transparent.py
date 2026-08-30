# -*- coding: utf-8 -*-
"""
Android Transparent Proxy & Per-UID IPTables Interceptor (Proxydroid Architecture)
Quản lý chuyển hướng mạng cấp hệ thống trên Android Root & UGPhone Cloud Phone:
  - Chuyển hướng lưu lượng TCP/UDP của Roblox (hoặc UID clone 999, 10) sang cổng Proxy cục bộ.
  - Hỗ trợ cô lập từng bản Clone/Dual Apps bằng IPTables UID Owner.
  - Tự động hoàn nguyên (Revert / Flush) IPTables khi đóng tool để không làm nghẽn mạng thiết bị.
"""

import os
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple
from config.logging import setup_logger

logger = setup_logger("android_transparent")


class AndroidTransparentProxyManager:
    """Quản lý Transparent Proxy và IPTables Per-UID cho Android"""

    ROBLOX_PACKAGE = "com.roblox.client"

    @classmethod
    def get_roblox_uid(cls, adb_bin: Optional[str] = None, device_id: Optional[str] = None) -> Optional[int]:
        """Lấy UID hệ thống của ứng dụng Roblox trên Android"""
        cmd = []
        if adb_bin and shutil.which(adb_bin):
            cmd = [adb_bin]
            if device_id:
                cmd += ["-s", device_id]
            cmd += ["shell", f"dumpsys package {cls.ROBLOX_PACKAGE} | grep userId="]
        else:
            # Chạy trực tiếp trên Termux
            cmd = ["dumpsys", "package", cls.ROBLOX_PACKAGE]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            for line in res.stdout.splitlines():
                if "userId=" in line:
                    parts = line.strip().split("userId=")
                    if len(parts) > 1:
                        uid_str = "".join(filter(str.isdigit, parts[1].split()[0]))
                        if uid_str:
                            return int(uid_str)
        except Exception as e:
            logger.debug(f"Failed to get Roblox UID: {e}")
        return 10000  # Default fallback UID

    @classmethod
    def enable_transparent_proxy_uid(
        cls,
        local_proxy_port: int = 10808,
        uid: Optional[int] = None,
        adb_bin: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Kích hoạt chuyển hướng IPTables NAT sang cổng Proxy cục bộ cho riêng UID Roblox.
        Tất cả các app khác trên điện thoại không bị ảnh hưởng.
        """
        target_uid = uid or cls.get_roblox_uid(adb_bin, device_id) or 10000
        
        # Các lệnh IPTables thiết lập Transparent Proxy
        iptables_cmds = [
            # 1. Tạo chain ROBLOX_PROXY nếu chưa có
            "iptables -t nat -N ROBLOX_PROXY 2>/dev/null || true",
            "iptables -t nat -F ROBLOX_PROXY",
            # 2. Bỏ qua mạng nội bộ LAN / Loopback
            "iptables -t nat -A ROBLOX_PROXY -d 127.0.0.0/8 -j RETURN",
            "iptables -t nat -A ROBLOX_PROXY -d 192.168.0.0/16 -j RETURN",
            "iptables -t nat -A ROBLOX_PROXY -d 10.0.0.0/8 -j RETURN",
            # 3. Chuyển hướng toàn bộ TCP của Roblox UID vào cổng local_proxy_port
            f"iptables -t nat -A ROBLOX_PROXY -p tcp -j REDIRECT --to-ports {local_proxy_port}",
            # 4. Gắn chain vào OUTPUT của UID
            f"iptables -t nat -D OUTPUT -m owner --uid-owner {target_uid} -j ROBLOX_PROXY 2>/dev/null || true",
            f"iptables -t nat -A OUTPUT -m owner --uid-owner {target_uid} -j ROBLOX_PROXY"
        ]

        full_sh = " && ".join(iptables_cmds)

        if adb_bin and shutil.which(adb_bin):
            adb_base = [adb_bin]
            if device_id:
                adb_base += ["-s", device_id]
            cmd = adb_base + ["shell", f"su -c '{full_sh}'"]
        else:
            # Chạy trực tiếp trong Termux (yêu cầu tsu / root)
            cmd = ["su", "-c", full_sh]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                msg = f"Đã áp dụng IPTables Transparent Proxy cho UID [{target_uid}] ➔ Cổng {local_proxy_port}"
                logger.info(msg)
                return True, msg
            else:
                return False, f"Lỗi thực thi IPTables: {res.stderr.strip()}"
        except Exception as e:
            return False, f"Ngoại lệ khi bật IPTables: {e}"

    @classmethod
    def disable_transparent_proxy(
        cls,
        adb_bin: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Dọn dẹp và hoàn nguyên toàn bộ IPTables Transparent Proxy"""
        clean_cmds = [
            "iptables -t nat -D OUTPUT -j ROBLOX_PROXY 2>/dev/null || true",
            "iptables -t nat -F ROBLOX_PROXY 2>/dev/null || true",
            "iptables -t nat -X ROBLOX_PROXY 2>/dev/null || true"
        ]
        full_sh = " && ".join(clean_cmds)

        if adb_bin and shutil.which(adb_bin):
            adb_base = [adb_bin]
            if device_id:
                adb_base += ["-s", device_id]
            cmd = adb_base + ["shell", f"su -c '{full_sh}'"]
        else:
            cmd = ["su", "-c", full_sh]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            return True, "Đã hoàn nguyên và xóa sạch IPTables Transparent Proxy an toàn."
        except Exception as e:
            return False, f"Lỗi dọn dẹp IPTables: {e}"


# Singleton instance
transparent_proxy_mgr = AndroidTransparentProxyManager()
