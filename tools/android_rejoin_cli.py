# -*- coding: utf-8 -*-
"""
Roblox Android Auto-Rejoin CLI Sentinel
Giao diện dòng lệnh chuyên nghiệp hỗ trợ cả Termux Native và ADB PC/Cloud Phone.
Tích hợp kiến trúc bóc tách logcat thời gian thực từ DroidBlox-kt.
"""

import os
import sys
import time
import argparse
import shutil
import subprocess

# Thêm thư mục gốc vào PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from devices.android_rejoin import AndroidRejoinController, RejoinState

# Màu ANSI
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_GREEN = "\033[1;32m"
C_CYAN = "\033[1;36m"
C_YELLOW = "\033[1;33m"
C_RED = "\033[1;31m"
C_PURPLE = "\033[1;35m"
C_GRAY = "\033[0;90m"

POPULAR_PLACES = {
    "1": ("Blox Fruits", 2753915549),
    "2": ("King Legacy", 4520749081),
    "3": ("Blade Ball", 13772394625),
    "4": ("Pet Simulator 99", 8737899170),
    "5": ("Rivals", 17625359962),
    "6": ("Anime Vanguards", 16146832113),
    "7": ("Dress to Impress", 15101393044),
    "8": ("Toilet Tower Defense", 13775256536),
}


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_banner():
    print(f"{C_PURPLE}╔════════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_PURPLE}║{C_RESET}  {C_BOLD}{C_CYAN}⚡ [ ROBLOX ANDROID / TERMUX AUTO-REJOIN SENTINEL ] ⚡{C_RESET}                       {C_PURPLE}║{C_RESET}")
    print(f"{C_PURPLE}║{C_RESET}  {C_GRAY}Core Engine:{C_RESET} {C_YELLOW}DroidBlox-kt Architecture{C_RESET} | {C_GRAY}Realtime Logcat & Deep Link Intent{C_RESET}  {C_PURPLE}║{C_RESET}")
    print(f"{C_PURPLE}╚════════════════════════════════════════════════════════════════════════════════╝{C_RESET}\n")


def scan_adb_devices(adb_bin: str) -> list:
    devices = []
    try:
        res = subprocess.run([adb_bin, "devices"], capture_output=True, text=True, timeout=3)
        for line in res.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
    except Exception:
        pass
    return devices


def interactive_menu():
    clear_screen()
    print_banner()

    is_termux = os.path.exists("/data/data/com.termux") or os.environ.get("PREFIX", "").startswith("/data/data/com.termux")
    adb_bin = shutil.which("adb")
    
    selected_adb_bin = None
    selected_device_id = None

    if is_termux:
        print(f"  {C_GREEN}[✓] Phát hiện môi trường: NATIVE ANDROID / TERMUX{C_RESET}")
    else:
        print(f"  {C_CYAN}[*] Phát hiện môi trường: PC / SERVER / ADB BRIDGE{C_RESET}")
        if adb_bin:
            devices = scan_adb_devices(adb_bin)
            if devices:
                print(f"  {C_GREEN}[✓] Tìm thấy {len(devices)} thiết bị ADB đang kết nối:{C_RESET}")
                for idx, d in enumerate(devices, 1):
                    print(f"      {C_YELLOW}[{idx}]{C_RESET} {d}")
                if len(devices) == 1:
                    selected_device_id = devices[0]
                    print(f"  {C_GREEN}➡️  Tự động chọn thiết bị: {selected_device_id}{C_RESET}")
                else:
                    choice = input(f"  {C_CYAN}Chọn số thiết bị ADB (1-{len(devices)}) [Mặc định: 1]: {C_RESET}").strip()
                    idx = int(choice) - 1 if choice.isdigit() and 1 <= int(choice) <= len(devices) else 0
                    selected_device_id = devices[idx]
            else:
                print(f"  {C_YELLOW}[!] Chưa có thiết bị ADB nào kết nối. Hãy kết nối cáp USB hoặc qua Wireless ADB (adb connect <IP>:5555){C_RESET}")
            selected_adb_bin = adb_bin
        else:
            print(f"  {C_RED}[!] Không tìm thấy công cụ ADB trong PATH.{C_RESET}")

    print(f"\n{C_BOLD}--- CHỌN TRÒ CHƠI MỤC TIÊU ---{C_RESET}")
    for k, (name, pid) in POPULAR_PLACES.items():
        print(f"  {C_YELLOW}[{k}]{C_RESET} {name.ljust(22)} (Place ID: {C_CYAN}{pid}{C_RESET})")
    print(f"  {C_YELLOW}[C]{C_RESET} Tự nhập Place ID tùy chỉnh...")

    game_choice = input(f"\n  {C_CYAN}Lựa chọn game [1-8 hoặc C, mặc định: 1]: {C_RESET}").strip()
    if game_choice.upper() == "C":
        custom_pid_str = input(f"  {C_CYAN}Nhập Place ID: {C_RESET}").strip()
        place_id = int(custom_pid_str) if custom_pid_str.isdigit() else 2753915549
    elif game_choice in POPULAR_PLACES:
        place_id = POPULAR_PLACES[game_choice][1]
    else:
        place_id = 2753915549

    job_id_input = input(f"  {C_CYAN}Nhập Job ID cụ thể (Bỏ trống để tự động bắt Job ID khi vào game): {C_RESET}").strip()
    job_id = job_id_input if job_id_input else None

    user_slot_input = input(f"  {C_CYAN}User Slot (0 = Mặc định, 999 = Dual Apps, 10 = Work Profile) [Mặc định: 0]: {C_RESET}").strip()
    user_slot = int(user_slot_input) if user_slot_input.isdigit() else 0

    webhook_input = input(f"  {C_CYAN}Discord Webhook URL thông báo (Bỏ trống nếu không dùng): {C_RESET}").strip()
    webhook = webhook_input if webhook_input.startswith("http") else None

    print(f"\n  {C_GREEN}[✓] Cấu hình hoàn tất! Khởi chạy Sentinel...{C_RESET}")
    time.sleep(1)

    controller = AndroidRejoinController(
        default_place_id=place_id,
        default_job_id=job_id,
        user_slot=user_slot,
        adb_bin=selected_adb_bin,
        device_id=selected_device_id,
        cooldown_sec=15,
        max_consecutive_fails=3,
        circuit_cooldown_sec=45,
        discord_webhook_url=webhook
    )

    controller.run_monitor_loop(poll_interval=3.0)


def main():
    parser = argparse.ArgumentParser(description="Roblox Android Auto-Rejoin Sentinel (DroidBlox Engine)")
    parser.add_argument("--place-id", "-p", type=int, default=None, help="Place ID của game Roblox")
    parser.add_argument("--job-id", "-j", type=str, default=None, help="Job ID máy chủ cụ thể")
    parser.add_argument("--user", "-u", type=int, default=0, help="User slot ID (--user 999 cho Dual Apps)")
    parser.add_argument("--device", "-d", type=str, default=None, help="Device ID của ADB")
    parser.add_argument("--adb", type=str, default=None, help="Đường dẫn file thực thi ADB")
    parser.add_argument("--webhook", "-w", type=str, default=None, help="Discord Webhook URL")
    parser.add_argument("--headless", action="store_true", help="Chạy không có menu tương tác")

    args = parser.parse_args()

    if args.headless or args.place_id is not None:
        place_id = args.place_id or 2753915549
        adb_bin = args.adb or shutil.which("adb")
        controller = AndroidRejoinController(
            default_place_id=place_id,
            default_job_id=args.job_id,
            user_slot=args.user,
            adb_bin=adb_bin,
            device_id=args.device,
            cooldown_sec=15,
            max_consecutive_fails=3,
            circuit_cooldown_sec=45,
            discord_webhook_url=args.webhook
        )
        controller.run_monitor_loop(poll_interval=3.0)
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
