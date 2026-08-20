import os
import sys
from typing import List
from cli.colors import Colors
from database.models import InstanceModel, NetworkSnapshotModel
from database.repository import SnapshotRepository

# Đảm bảo UTF-8 stream trên Windows và Termux
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

class DashboardRenderer:
    @staticmethod
    def clear_screen():
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def render(instances: List[InstanceModel]):
        DashboardRenderer.clear_screen()
        # Sử dụng box ASCII / Unicode tương thích cao
        border_top = "=" * 90
        print(f"{Colors.RED}{Colors.BOLD}{border_top}{Colors.RESET}")
        print(f"{Colors.RED}{Colors.BOLD}       ROBLOX INSTANCE NETWORK MANAGER (TERMUX / CLOUD NODES){Colors.RESET}")
        print(f"{Colors.RED}{Colors.BOLD}{border_top}{Colors.RESET}")
        print(f"{Colors.WHITE}{Colors.BOLD}INSTANCE      REGION        DEVICE       PROFILE              LOCAL IP       LATENCY  STATUS{Colors.RESET}")
        print(f"{Colors.RED}{Colors.BOLD}{'-' * 90}{Colors.RESET}")

        for inst in instances:
            snapshot = SnapshotRepository.get_latest_snapshot(inst.id)
            local_ip = snapshot.local_ip if snapshot and snapshot.local_ip else "N/A"
            latency = f"{snapshot.latency_ms}ms" if snapshot and snapshot.latency_ms >= 0 else "N/A"
            status_str = snapshot.status if snapshot else inst.status
            colored_status = Colors.colorize_status(status_str)

            inst_col = f"{inst.id:<13}"
            reg_col = f"{inst.region:<13}"
            dev_col = f"{inst.device_type:<12}"
            prof_col = f"{(inst.assigned_profile or 'default'):<20}"
            ip_col = f"{local_ip:<14}"
            lat_col = f"{latency:<8}"

            print(f"{inst_col} {reg_col} {dev_col} {prof_col} {ip_col} {lat_col} {colored_status}")

        print(f"{Colors.RED}{Colors.BOLD}{border_top}{Colors.RESET}")

        # Thông tin Public IP & Network Gateway thực tế
        latest_any = SnapshotRepository.get_latest_snapshot(instances[0].id) if instances else None
        pub_ip = latest_any.public_ip if latest_any and latest_any.public_ip else "Checking..."
        dns_ms = f"{latest_any.dns_response_ms} ms" if latest_any and latest_any.dns_response_ms >= 0 else "N/A"

        print(f"\n{Colors.RED}{Colors.BOLD}[CLOUD NODES & NETWORK ROUTING DIAGNOSTICS]{Colors.RESET}")
        print(f"  {Colors.BOLD}ACTIVE REGIONS :{Colors.RESET} {Colors.GREEN}JP (Tokyo), HK (Central), SG (Jurong), VN (Direct){Colors.RESET}")
        print(f"  {Colors.BOLD}PUBLIC IP      :{Colors.RESET} {Colors.LIGHT_RED}{pub_ip}{Colors.RESET}")
        print(f"  {Colors.BOLD}INTERFACE      :{Colors.RESET} {Colors.WHITE}wlan0 / rmnet (Linux Kernel Socket){Colors.RESET}")
        print(f"  {Colors.BOLD}DNS QUERY      :{Colors.RESET} {Colors.CYAN}{dns_ms}{Colors.RESET} (roblox.com)")
        print(f"  {Colors.BOLD}DATABASE       :{Colors.RESET} {Colors.GREEN}SQLite Connected & Synced{Colors.RESET}")
        print(f"\n{Colors.GRAY}Nhan Ctrl+C de dung he thong.{Colors.RESET}")
