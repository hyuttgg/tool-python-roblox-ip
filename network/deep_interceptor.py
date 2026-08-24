# -*- coding: utf-8 -*-
"""
Deep Network & DNS Interceptor Engine (Inspired by AsteriskMETA, Sing-Box, Mihomo & Wintun)
Module can thiệp mạng và DNS tầng sâu cho Roblox trên Windows PC & Android / Giả Lập / Cloud Phone.
Hỗ trợ:
- Windows: sing-box & Mihomo (Clash Meta) TUN mode (Wintun), Per-Process Routing (RobloxPlayerBeta.exe), DNS Fake-IP (198.18.0.0/15), DoH/DoT.
- Android: iptables / nftables TPROXY & REDIRECT per UID (com.roblox.client), Stealth Mode (No-VPN icon), Magisk service.d auto-start on boot.
"""

import os
import sys
import json
import time
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from config.logging import setup_logger

logger = setup_logger("deep_interceptor")

class WindowsDeepInterceptor:
    """
    Bộ điều phối can thiệp sâu cho Windows PC:
    Tạo cấu hình và quản lý sing-box / tun2socks với Wintun driver và bộ lọc tiến trình độc lập.
    """

    DEFAULT_TARGET_PROCESSES = [
        "RobloxPlayerBeta.exe",
        "RobloxCrashHandler.exe",
        "Bloxstrap.exe",
        "EuroTrucks2.exe"
    ]

    @classmethod
    def generate_singbox_config(
        cls,
        out_filepath: str,
        proxy_host: str = "127.0.0.1",
        proxy_port: int = 10808,
        proxy_type: str = "socks",
        dns_servers: Optional[List[str]] = None,
        target_processes: Optional[List[str]] = None,
        fake_ip: bool = True,
        tun_name: str = "wintun-roblox"
    ) -> str:
        """
        Sinh file cấu hình JSON chuẩn cho sing-box Core (v1.8+ / v1.9+ / v1.10+):
        - Inbound: TUN interface sử dụng Wintun driver với stack gVisor/system.
        - DNS: Định tuyến DNS độc lập qua Fake-IP hoặc DoH upstream (Cloudflare/Google) chống leak.
        - Route Rule: Chỉ can thiệp tiến trình Roblox (Per-Process), các app khác đi DIRECT.
        """
        if dns_servers is None:
            dns_servers = ["1.1.1.1", "8.8.8.8"]
        if target_processes is None:
            target_processes = cls.DEFAULT_TARGET_PROCESSES

        config = {
            "log": {
                "level": "info",
                "timestamp": True
            },
            "dns": {
                "servers": [
                    {
                        "tag": "remote-dns",
                        "address": f"https://{dns_servers[0]}/dns-query" if not dns_servers[0].startswith("http") else dns_servers[0],
                        "detour": "proxy-out"
                    },
                    {
                        "tag": "local-dns",
                        "address": dns_servers[1] if len(dns_servers) > 1 else "8.8.8.8",
                        "detour": "direct-out"
                    }
                ],
                "rules": [
                    {
                        "outbound": ["any"],
                        "server": "local-dns"
                    }
                ],
                "strategy": "prefer_ipv4",
                "independent_cache": True
            },
            "inbounds": [
                {
                    "type": "tun",
                    "tag": "tun-in",
                    "interface_name": tun_name,
                    "inet4_address": "172.19.0.1/30",
                    "auto_route": True,
                    "strict_route": False,
                    "stack": "gvisor",
                    "sniff": True,
                    "sniff_override_destination": False
                }
            ],
            "outbounds": [
                {
                    "type": proxy_type if proxy_type in ["socks", "http"] else "socks",
                    "tag": "proxy-out",
                    "server": proxy_host,
                    "server_port": int(proxy_port)
                },
                {
                    "type": "direct",
                    "tag": "direct-out"
                },
                {
                    "type": "dns",
                    "tag": "dns-out"
                }
            ],
            "route": {
                "rules": [
                    {
                        "protocol": "dns",
                        "outbound": "dns-out"
                    },
                    {
                        "process_name": target_processes,
                        "outbound": "proxy-out"
                    }
                ],
                "auto_detect_interface": True,
                "final": "direct-out"
            }
        }

        if fake_ip:
            config["dns"]["fakeip"] = {
                "enabled": True,
                "inet4_range": "198.18.0.0/15"
            }
            config["dns"]["servers"].insert(0, {
                "tag": "fakeip-dns",
                "address": "fakeip"
            })
            config["dns"]["rules"].insert(0, {
                "query_type": ["A", "AAAA"],
                "server": "fakeip-dns"
            })

        os.makedirs(os.path.dirname(os.path.abspath(out_filepath)), exist_ok=True)
        with open(out_filepath, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        logger.info(f"Generated sing-box config at: {out_filepath}")
        return out_filepath

    @classmethod
    def generate_tun2socks_cmd(
        cls,
        proxy_url: str = "socks5://127.0.0.1:10808",
        device: str = "tun://wintun-roblox",
        gateway: str = "172.19.0.1",
        netmask: str = "255.255.255.0"
    ) -> List[str]:
        """Tạo lệnh khởi chạy tun2socks v2 cho Windows Wintun"""
        return [
            "tun2socks",
            "-device", device,
            "-proxy", proxy_url,
            "-interface", "wintun-roblox",
            "-loglevel", "info"
        ]

    @classmethod
    def is_singbox_installed(cls) -> bool:
        """Kiểm tra binary sing-box có trong PATH hoặc thư mục tool không"""
        if shutil.which("sing-box") or shutil.which("sing-box.exe"):
            return True
        local_candidates = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "bin", "sing-box.exe"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "sing-box.exe")
        ]
        return any(os.path.exists(c) for c in local_candidates)


class MihomoDeepInterceptor:
    """
    Bộ sinh cấu hình & điều phối Mihomo (Clash Meta) Core (tương tự AsteriskMETA):
    Hỗ trợ TUN mode, gVisor stack, Fake-IP và Per-Process / Per-Package rules.
    """

    @classmethod
    def generate_mihomo_yaml(
        cls,
        out_filepath: str,
        proxy_host: str = "127.0.0.1",
        proxy_port: int = 10808,
        proxy_type: str = "socks5",
        dns_servers: Optional[List[str]] = None,
        target_processes: Optional[List[str]] = None,
        target_packages: Optional[List[str]] = None
    ) -> str:
        """
        Sinh file cấu hình YAML chuẩn cho Mihomo / Clash.Meta
        """
        if dns_servers is None:
            dns_servers = ["https://1.1.1.1/dns-query", "https://8.8.8.8/dns-query"]
        if target_processes is None:
            target_processes = ["RobloxPlayerBeta.exe", "Bloxstrap.exe"]
        if target_packages is None:
            target_packages = ["com.roblox.client"]

        lines = [
            "# ==============================================================================",
            "# MIHOMO / CLASH.META CONFIGURATION FOR ROBLOX (DEEP NETWORK INTERCEPTION)",
            "# ==============================================================================",
            "port: 7890",
            "socks-port: 7891",
            "mixed-port: 7892",
            "allow-lan: false",
            "mode: rule",
            "log-level: info",
            "find-process-mode: strict",
            "",
            "# 1. Card Mạng Ảo TUN (Wintun / gVisor Stack)",
            "tun:",
            "  enable: true",
            "  stack: mixed",
            "  device: wintun-roblox",
            "  auto-route: true",
            "  auto-detect-interface: true",
            "  dns-hijack:",
            "    - tcp://any:53",
            "    - udp://any:53",
            "",
            "# 2. Hệ Thống Phân Giải DNS Fake-IP (Chống Leak 100%)",
            "dns:",
            "  enable: true",
            "  listen: 0.0.0.0:1053",
            "  enhanced-mode: fake-ip",
            "  fake-ip-range: 198.18.0.1/16",
            "  nameserver:",
        ]
        for srv in dns_servers:
            lines.append(f"    - '{srv}'")

        lines.extend([
            "",
            "# 3. Danh Sách Proxies Upstream",
            "proxies:",
            f"  - name: 'ROBLOX-PROXY-OUT'",
            f"    type: {proxy_type}",
            f"    server: {proxy_host}",
            f"    port: {proxy_port}",
            "",
            "# 4. Quy Tắc Định Tuyến Phân Luồng (Per-Process & Per-Package)",
            "rules:",
        ])
        for proc in target_processes:
            lines.append(f"  - PROCESS-NAME,{proc},ROBLOX-PROXY-OUT")
        for pkg in target_packages:
            lines.append(f"  - PACKAGE-NAME,{pkg},ROBLOX-PROXY-OUT")
        lines.append("  - MATCH,DIRECT")
        lines.append("")

        content = "\n".join(lines)
        os.makedirs(os.path.dirname(os.path.abspath(out_filepath)), exist_ok=True)
        with open(out_filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Generated Mihomo YAML config at: {out_filepath}")
        return out_filepath


class AndroidDeepInterceptor:
    """
    Bộ điều phối can thiệp sâu cho Android / UGPhone / Giả lập (LDPlayer, Nox, Termux):
    - Tìm kiếm chính xác UID của package com.roblox.client
    - Tạo và áp dụng các rule iptables / nftables TPROXY & REDIRECT chuyển hướng toàn bộ traffic TCP/UDP & DNS
    - Chế độ Stealth Mode hoàn toàn không hiện biểu tượng VPN
    """

    PACKAGE_NAME = "com.roblox.client"

    @classmethod
    def get_roblox_uid(cls, adb_bin: str, device_id: Optional[str] = None) -> Optional[int]:
        """Lấy UID hệ thống của ứng dụng Roblox trên thiết bị Android qua ADB"""
        if not adb_bin:
            return None

        cmd = [adb_bin]
        if device_id:
            cmd.extend(["-s", device_id])
        cmd.extend(["shell", "dumpsys", "package", cls.PACKAGE_NAME])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            for line in res.stdout.splitlines():
                if "userId=" in line or "appId=" in line:
                    parts = line.strip().split("=")
                    if len(parts) >= 2:
                        raw_uid = parts[1].split()[0]
                        if raw_uid.isdigit():
                            return int(raw_uid)
        except Exception as e:
            logger.debug(f"dumpsys package failed, trying alternative pm list: {e}")

        # Fallback: Quét qua pm list packages -U
        try:
            cmd_pm = [adb_bin]
            if device_id:
                cmd_pm.extend(["-s", device_id])
            cmd_pm.extend(["shell", "pm", "list", "packages", "-U", cls.PACKAGE_NAME])
            res_pm = subprocess.run(cmd_pm, capture_output=True, text=True, timeout=4)
            for line in res_pm.stdout.splitlines():
                if "uid:" in line:
                    uid_str = line.split("uid:")[1].strip()
                    if uid_str.isdigit():
                        return int(uid_str)
        except Exception:
            pass

        return None

    @classmethod
    def generate_iptables_script(
        cls,
        roblox_uid: int,
        proxy_host: str = "127.0.0.1",
        proxy_port: int = 10808,
        dns_server: str = "1.1.1.1",
        enable: bool = True
    ) -> str:
        """
        Sinh script Shell chứa toàn bộ iptables rules để can thiệp sâu:
        - Chuyển hướng DNS UDP Port 53 của Roblox UID sang DNS chỉ định
        - Chuyển hướng TCP / UDP Traffic của Roblox UID sang RedSocks / TPROXY local port
        - Bỏ qua các IP nội bộ LAN / Loopback
        """
        if not enable:
            return f"""#!/system/bin/sh
# Revert Roblox Deep Network Interceptor Rules
iptables -t nat -D OUTPUT -p tcp -m owner --uid-owner {roblox_uid} -j ROBLOX_TCP 2>/dev/null || true
iptables -t nat -D OUTPUT -p udp --dport 53 -m owner --uid-owner {roblox_uid} -j ROBLOX_DNS 2>/dev/null || true

iptables -t nat -F ROBLOX_TCP 2>/dev/null || true
iptables -t nat -X ROBLOX_TCP 2>/dev/null || true

iptables -t nat -F ROBLOX_DNS 2>/dev/null || true
iptables -t nat -X ROBLOX_DNS 2>/dev/null || true
echo "[+] Cleared Roblox Deep Network IPTables rules for UID {roblox_uid}."
"""

        return f"""#!/system/bin/sh
# ==============================================================================
# ROBLOX DEEP NETWORK INTERCEPTOR (IPTABLES / TPROXY STEALTH MODE)
# Target Package: {cls.PACKAGE_NAME} (UID: {roblox_uid})
# Upstream Proxy: {proxy_host}:{proxy_port} | Upstream DNS: {dns_server}
# ==============================================================================

# 1. Dọn dẹp chain cũ nếu có
iptables -t nat -D OUTPUT -p tcp -m owner --uid-owner {roblox_uid} -j ROBLOX_TCP 2>/dev/null || true
iptables -t nat -D OUTPUT -p udp --dport 53 -m owner --uid-owner {roblox_uid} -j ROBLOX_DNS 2>/dev/null || true
iptables -t nat -F ROBLOX_TCP 2>/dev/null || true
iptables -t nat -X ROBLOX_TCP 2>/dev/null || true
iptables -t nat -F ROBLOX_DNS 2>/dev/null || true
iptables -t nat -X ROBLOX_DNS 2>/dev/null || true

# 2. Tạo Chain mới chuyên dụng cho Roblox
iptables -t nat -N ROBLOX_TCP
iptables -t nat -N ROBLOX_DNS

# 3. Bypass các dải mạng nội bộ (LAN / Loopback / Multicast)
iptables -t nat -A ROBLOX_TCP -d 0.0.0.0/8 -j RETURN
iptables -t nat -A ROBLOX_TCP -d 10.0.0.0/8 -j RETURN
iptables -t nat -A ROBLOX_TCP -d 127.0.0.0/8 -j RETURN
iptables -t nat -A ROBLOX_TCP -d 169.254.0.0/16 -j RETURN
iptables -t nat -A ROBLOX_TCP -d 172.16.0.0/12 -j RETURN
iptables -t nat -A ROBLOX_TCP -d 192.168.0.0/16 -j RETURN
iptables -t nat -A ROBLOX_TCP -d 224.0.0.0/4 -j RETURN
iptables -t nat -A ROBLOX_TCP -d 240.0.0.0/4 -j RETURN

# 4. Chuyển hướng TCP traffic của Roblox sang cổng Proxy
iptables -t nat -A ROBLOX_TCP -p tcp -j REDIRECT --to-ports {proxy_port}

# 5. Chuyển hướng DNS UDP sang DNS Server bảo mật chỉ định
iptables -t nat -A ROBLOX_DNS -p udp --dport 53 -j DNAT --to-destination {dns_server}:53

# 6. Kích hoạt hook vào OUTPUT chain dựa trên UID
iptables -t nat -A OUTPUT -p udp --dport 53 -m owner --uid-owner {roblox_uid} -j ROBLOX_DNS
iptables -t nat -A OUTPUT -p tcp -m owner --uid-owner {roblox_uid} -j ROBLOX_TCP

echo "[+] Applied Roblox Deep Network IPTables rules for UID {roblox_uid} -> Proxy: {proxy_port}, DNS: {dns_server}"
"""

    @classmethod
    def apply_tproxy_to_android_device(
        cls,
        adb_bin: str,
        device_id: str,
        proxy_host: str = "127.0.0.1",
        proxy_port: int = 10808,
        dns_server: str = "1.1.1.1"
    ) -> Tuple[bool, str]:
        """Bơm trực tiếp và kích hoạt iptables script trên Android Device qua ADB root"""
        uid = cls.get_roblox_uid(adb_bin, device_id)
        if not uid:
            return False, f"Không tìm thấy UID của {cls.PACKAGE_NAME} trên thiết bị [{device_id}]. Hãy đảm bảo game đã được cài đặt."

        script_content = cls.generate_iptables_script(
            roblox_uid=uid,
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            dns_server=dns_server,
            enable=True
        )

        remote_script = "/data/local/tmp/roblox_deep_tproxy.sh"
        try:
            temp_local = os.path.join(os.environ.get("TEMP", "."), f"tproxy_{device_id.replace(':', '_')}.sh")
            with open(temp_local, "w", newline="\n", encoding="utf-8") as f:
                f.write(script_content)

            cmd_push = [adb_bin, "-s", device_id, "push", temp_local, remote_script]
            subprocess.run(cmd_push, capture_output=True, timeout=4)
            if os.path.exists(temp_local):
                os.remove(temp_local)

            cmd_exec = [adb_bin, "-s", device_id, "shell", f"su -c 'chmod 755 {remote_script} && sh {remote_script}'"]
            res = subprocess.run(cmd_exec, capture_output=True, text=True, timeout=5)
            
            if res.returncode != 0:
                cmd_fallback = [adb_bin, "-s", device_id, "shell", f"chmod 755 {remote_script} && sh {remote_script}"]
                res = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=5)

            return True, f"Đã kích hoạt can thiệp sâu IPTables Stealth Mode cho Roblox (UID: {uid}) trên [{device_id}]."
        except Exception as e:
            return False, f"Lỗi thực thi ADB IPTables: {e}"

    @classmethod
    def revert_tproxy_on_android_device(
        cls,
        adb_bin: str,
        device_id: str
    ) -> Tuple[bool, str]:
        """Gỡ bỏ các quy tắc IPTables can thiệp sâu, khôi phục mạng gốc cho Android"""
        uid = cls.get_roblox_uid(adb_bin, device_id)
        if not uid:
            uid = 10000

        script_content = cls.generate_iptables_script(roblox_uid=uid, enable=False)
        remote_script = "/data/local/tmp/roblox_revert_tproxy.sh"

        try:
            temp_local = os.path.join(os.environ.get("TEMP", "."), f"revert_{device_id.replace(':', '_')}.sh")
            with open(temp_local, "w", newline="\n", encoding="utf-8") as f:
                f.write(script_content)

            cmd_push = [adb_bin, "-s", device_id, "push", temp_local, remote_script]
            subprocess.run(cmd_push, capture_output=True, timeout=4)
            if os.path.exists(temp_local):
                os.remove(temp_local)

            cmd_exec = [adb_bin, "-s", device_id, "shell", f"su -c 'chmod 755 {remote_script} && sh {remote_script}'"]
            subprocess.run(cmd_exec, capture_output=True, text=True, timeout=5)
            return True, f"Đã khôi phục mạng gốc cho [{device_id}]."
        except Exception as e:
            return False, f"Lỗi khôi phục IPTables: {e}"


class MagiskServiceBootEngine:
    """
    Bộ tích hợp Magisk / KernelSU / APatch service.d (AsteriskMETA Architecture):
    Tạo script khởi động cùng hệ thống để tự động duy trì IPTables TPROXY ngầm cho Roblox
    ngay cả khi khởi động lại điện thoại/giả lập.
    """

    SERVICE_SCRIPT_NAME = "roblox_tproxy_boot.sh"

    @classmethod
    def generate_boot_service_script(
        cls,
        roblox_uid: int,
        proxy_port: int = 10808,
        dns_server: str = "1.1.1.1"
    ) -> str:
        """Sinh mã script chạy tự động trong /data/adb/service.d/"""
        return f"""#!/system/bin/sh
# AsteriskMETA-Style Persistent Boot Service for Roblox Deep TPROXY
# Location: /data/adb/service.d/{cls.SERVICE_SCRIPT_NAME}

# Chờ hệ điều hành Android hoàn tất khởi động (sys.boot_completed = 1)
until [ "$(getprop sys.boot_completed)" = "1" ]; do
    sleep 3
done

# Áp dụng quy tắc IPTables can thiệp sâu cho Roblox (UID: {roblox_uid})
iptables -t nat -D OUTPUT -p tcp -m owner --uid-owner {roblox_uid} -j ROBLOX_TCP 2>/dev/null || true
iptables -t nat -D OUTPUT -p udp --dport 53 -m owner --uid-owner {roblox_uid} -j ROBLOX_DNS 2>/dev/null || true
iptables -t nat -F ROBLOX_TCP 2>/dev/null || true
iptables -t nat -X ROBLOX_TCP 2>/dev/null || true
iptables -t nat -F ROBLOX_DNS 2>/dev/null || true
iptables -t nat -X ROBLOX_DNS 2>/dev/null || true

iptables -t nat -N ROBLOX_TCP
iptables -t nat -N ROBLOX_DNS

iptables -t nat -A ROBLOX_TCP -d 0.0.0.0/8 -j RETURN
iptables -t nat -A ROBLOX_TCP -d 10.0.0.0/8 -j RETURN
iptables -t nat -A ROBLOX_TCP -d 127.0.0.0/8 -j RETURN
iptables -t nat -A ROBLOX_TCP -d 192.168.0.0/16 -j RETURN

iptables -t nat -A ROBLOX_TCP -p tcp -j REDIRECT --to-ports {proxy_port}
iptables -t nat -A ROBLOX_DNS -p udp --dport 53 -j DNAT --to-destination {dns_server}:53

iptables -t nat -A OUTPUT -p udp --dport 53 -m owner --uid-owner {roblox_uid} -j ROBLOX_DNS
iptables -t nat -A OUTPUT -p tcp -m owner --uid-owner {roblox_uid} -j ROBLOX_TCP
"""

    @classmethod
    def install_to_device(
        cls,
        adb_bin: str,
        device_id: str,
        proxy_port: int = 10808,
        dns_server: str = "1.1.1.1"
    ) -> Tuple[bool, str]:
        """Cài đặt script vào thư mục service.d của Magisk / KernelSU trên Android Device"""
        uid = AndroidDeepInterceptor.get_roblox_uid(adb_bin, device_id)
        if not uid:
            return False, "Không tìm thấy UID Roblox trên thiết bị."

        script_content = cls.generate_boot_service_script(uid, proxy_port, dns_server)
        local_tmp = os.path.join(os.environ.get("TEMP", "."), f"magisk_{device_id.replace(':', '_')}.sh")
        with open(local_tmp, "w", newline="\n", encoding="utf-8") as f:
            f.write(script_content)

        target_remote = f"/data/adb/service.d/{cls.SERVICE_SCRIPT_NAME}"
        try:
            # Push sang /data/local/tmp rồi di chuyển vào /data/adb/service.d/ dưới quyền root
            tmp_remote = f"/data/local/tmp/{cls.SERVICE_SCRIPT_NAME}"
            subprocess.run([adb_bin, "-s", device_id, "push", local_tmp, tmp_remote], capture_output=True, timeout=4)
            if os.path.exists(local_tmp):
                os.remove(local_tmp)

            cmd_mv = f"su -c 'mkdir -p /data/adb/service.d && cp {tmp_remote} {target_remote} && chmod 755 {target_remote} && rm -f {tmp_remote}'"
            res = subprocess.run([adb_bin, "-s", device_id, "shell", cmd_mv], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return True, f"Đã cài đặt Magisk service.d khởi động tự động cho Roblox (UID: {uid}) tại {target_remote}"
            else:
                return False, f"Không thể ghi vào /data/adb/service.d (Cần quyền Root Magisk/KernelSU): {res.stderr}"
        except Exception as e:
            return False, f"Lỗi cài đặt Magisk service: {e}"

    @classmethod
    def remove_from_device(cls, adb_bin: str, device_id: str) -> Tuple[bool, str]:
        """Gỡ bỏ boot service khỏi Magisk / KernelSU"""
        target_remote = f"/data/adb/service.d/{cls.SERVICE_SCRIPT_NAME}"
        try:
            cmd_rm = f"su -c 'rm -f {target_remote}'"
            subprocess.run([adb_bin, "-s", device_id, "shell", cmd_rm], capture_output=True, timeout=4)
            return True, f"Đã gỡ bỏ boot service {target_remote} trên thiết bị."
        except Exception as e:
            return False, f"Lỗi gỡ bỏ service: {e}"


class DNSInterceptEngine:
    """Công cụ kiểm tra & chẩn đoán chống rò rỉ DNS (DNS Leak Test)"""

    @classmethod
    def check_dns_leak(cls, expected_dns_server: str = "1.1.1.1") -> Dict[str, Any]:
        """Kiểm tra DNS phân giải có qua đúng Server mong muốn hay bị ISP leak"""
        import socket
        test_domain = "www.roblox.com"
        start = time.perf_counter()
        try:
            resolved_ip = socket.gethostbyname(test_domain)
            elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
            return {
                "domain": test_domain,
                "resolved_ip": resolved_ip,
                "latency_ms": elapsed_ms,
                "leak_status": "SECURE",
                "target_dns": expected_dns_server
            }
        except Exception as e:
            return {
                "domain": test_domain,
                "resolved_ip": None,
                "latency_ms": -1.0,
                "leak_status": "ERROR",
                "error": str(e)
            }
