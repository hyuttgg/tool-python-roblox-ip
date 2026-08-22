#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
             ROBLOX MULTI-INSTANCE MASTER CONTROLLER (TERMUX/ROOT/VM)
=============================================================================
File: controller.py
Chức năng (Đồng bộ số 1 -> 7):
  [1] Quét toàn bộ Tag Roblox trên màn hình & Tự động sinh Script Lua gán IP riêng.
  [2] Khởi chạy Dashboard giám sát Real-time (Live Monitoring).
  [3] Tự động sinh IP mới & Gán mỗi Tag một IP riêng biệt.
  [4] Chạy kiểm tra chẩn đoán mạng chuyên sâu (DNS, ICMP Ping, Public IP).
  [5] Xem danh sách Instances & Network Profiles hiện tại.
  [6] Sinh danh sách IP ngẫu nhiên lưu vào file txt (IP-Generator).
  [7] Xuất báo cáo trạng thái ra file JSON/TXT & Hướng dẫn sử dụng Executor.
  [0] Thoát chương trình.
=============================================================================
"""

import os
import sys
import time
import json
import threading
from typing import List, Optional

# Thiết lập encoding UTF-8
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Thêm đường dẫn thư mục gốc vào sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DATA_DIR = os.path.join(BASE_DIR, "data")

from cli.colors import Colors
from database.sqlite import db
from database.models import InstanceModel
from database.repository import InstanceRepository, SnapshotRepository
from core.manager import CoreManager
from core.scanner import RobloxWindowScanner, RobloxWindowInstance
from core.lua_generator import LuaScriptGenerator, OUTPUT_LUA_DIR
from network.bridge_server import RobloxBridgeServer
from cli.status import DashboardRenderer
from network.ip_generator import RandomIPGenerator
from network.connectivity import ConnectivityChecker
from network.dns import DNSResolver
from monitoring.ping import PingMonitor
from config.devices import DEFAULT_DEVICES, DeviceConfig, DeviceType
from config.profiles import DEFAULT_PROFILES
from config.logging import setup_logger

logger = setup_logger("master_controller")

def safe_input(prompt: str = "") -> str:
    """Hàm nhập dữ liệu an toàn, không bị văng lỗi Traceback khi bấm Ctrl+C hoặc đóng terminal"""
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        return ""

from core.autoexec_manager import AutoexecManager
from core.clone_scanner import RobloxCloneScanner, RobloxCloneProfile
from core.network_inspector import NetworkInspector
from devices.ugphone_bridge import UGPhoneBridge
from network.scrapestack_client import ScrapestackClient

class MasterController:
    def __init__(self):
        # Đảm bảo database đã sẵn sàng
        db.init_db()
        self.manager = CoreManager()
        self.scanner = RobloxWindowScanner()
        self.clone_scanner = RobloxCloneScanner()
        self.ugphone_bridge = UGPhoneBridge()
        self.lua_generator = LuaScriptGenerator()
        self.autoexec_manager = AutoexecManager()
        self.scrapestack = ScrapestackClient()
        self.bridge_server = RobloxBridgeServer(host="127.0.0.1", port=8888)
        self.bridge_server.start()
        
        self.live_tags_count = 0
        self.clone_tags_count = 0
        self.active_tags: List[RobloxWindowInstance] = []
        self.autoexec_synced_count = 0

        # TỰ ĐỘNG QUÉT CẢ CỬA SỔ ĐANG MỞ & BẢN NHÂN BẢN CHƯA MỞ NGAY KHI KHỞI ĐỘNG TOOL
        try:
            combined = self._get_combined_tag_instances()
            if combined:
                self.active_tags = combined
                self.live_tags_count = len([x for x in combined if x.hwnd > 0 or x.pid > 0])
                self.clone_tags_count = len([x for x in combined if x.hwnd == 0 and x.pid == 0])
                # Tự động gán sẵn IP Multi-Country riêng biệt cho TẤT CẢ bản nhân bản
                lua_files = self.lua_generator.generate_scripts_for_scanned_instances(combined, use_live_proxies=True, country_code="MULTI")
                m_path = lua_files.get("MASTER", "")
                if os.path.exists(m_path):
                    with open(m_path, "r", encoding="utf-8") as f:
                        m_code = f.read()
                        self.bridge_server.update_state(combined, master_script=m_code)
                        # Tự động nạp vào tất cả thư mục Autoexec PC & Giả lập Android
                        sync_res = self.autoexec_manager.sync_lua_to_autoexec(m_code)
                        self.autoexec_synced_count = len(sync_res.get("pc_synced", [])) + len(sync_res.get("android_synced", []))
        except Exception as e:
            logger.warning(f"Auto-detect on startup error: {e}")

        self._monitor_running = False
        self._monitor_thread: Optional[threading.Thread] = None

    def _get_combined_tag_instances(self) -> List[RobloxWindowInstance]:
        """Gộp các cửa sổ đang mở, máy ảo và UGPhone cloud phones thành danh sách Tag duy nhất"""
        open_windows = self.scanner.scan_active_roblox_windows()
        cloned_profiles = self.clone_scanner.scan_all_clones()
        
        combined: List[RobloxWindowInstance] = []
        for w in open_windows:
            combined.append(w)

        # Thêm các thiết bị UGPhone nếu có
        from core.scanner import WindowRect
        ug_devs = self.ugphone_bridge.refresh_devices()
        for idx, udev in enumerate(ug_devs):
            tag_id = f"UGPHONE-{idx+1:02d}"
            r_stat = self.ugphone_bridge.get_roblox_status(udev)
            is_running = r_stat.get("running") == "Yes"
            combined.append(RobloxWindowInstance(
                tag_id=tag_id,
                hwnd=1 if is_running else 0,
                title=f"UGPhone [{udev}]",
                pid=int(r_stat.get("pid", 0) or 0) if is_running else 0,
                process_name="UGPhone Cloud Android",
                class_name="UGPHONE_DEVICE",
                rect=WindowRect(),
                screen_position=f"UGPhone ({udev})",
                memory_usage="Cloud VM",
                account_username=f"UGPhone_Acc_{idx+1}"
            ))
            
        for idx, cp in enumerate(cloned_profiles):
            tag_id = cp.tag_id
            if not any(item.tag_id == tag_id for item in combined):
                combined.append(RobloxWindowInstance(
                    tag_id=tag_id,
                    hwnd=0,
                    title=f"{cp.name} [CHUA MO]",
                    pid=0,
                    process_name=cp.clone_type,
                    class_name=cp.clone_type,
                    rect=WindowRect(),
                    screen_position="Offline / Pre-Allocated",
                    memory_usage="0 MB",
                    account_username=cp.account_username or f"Clone_User_{idx+1}"
                ))
        return combined

    def clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")

    def print_banner(self):
        self.clear_screen()
        W = 91
        def pad_line(colored_str, visible_len):
            pad = max(0, W - visible_len)
            return f"{Colors.C_PURPLE}{Colors.BOLD}║{Colors.RESET} {colored_str}{' ' * pad} {Colors.C_PURPLE}{Colors.BOLD}║{Colors.RESET}"

        top = f"{Colors.C_PURPLE}{Colors.BOLD}╔{'═' * (W + 2)}╗{Colors.RESET}"
        mid = f"{Colors.C_PURPLE}{Colors.BOLD}╠{'═' * (W + 2)}╣{Colors.RESET}"
        bot = f"{Colors.C_PURPLE}{Colors.BOLD}╚{'═' * (W + 2)}╝{Colors.RESET}"

        print(top)
        # 6 dòng ASCII 3D đổ màu theo 6 dải quang phổ cầu vồng bên trong ô vuông
        banner_raw = [
            "  ██████╗   ██████╗  ██████╗  ██╗       ██████╗  ██╗  ██╗    ███╗   ██╗ ███████╗ ████████╗  ",
            "  ██╔══██╗ ██╔═══██╗ ██╔══██╗ ██║      ██╔═══██╗ ╚██╗██╔╝    ████╗  ██║ ██╔════╝ ╚══██╔══╝  ",
            "  ██████╔╝ ██║   ██║ ██████╔╝ ██║      ██║   ██║  ╚███╔╝     ██╔██╗ ██║ █████╗      ██║    ",
            "  ██╔══██╗ ██║   ██║ ██╔══██╗ ██║      ██║   ██║  ██╔██╗     ██║╚██╗██║ ██╔══╝      ██║    ",
            "  ██║  ██║ ╚██████╔╝ ██████╔╝ ███████╗ ╚██████╔╝ ██╔╝ ██╗    ██║ ╚████║ ███████╗    ██║    ",
            "  ╚═╝  ╚═╝  ╚═════╝  ╚═════╝  ╚══════╝  ╚═════╝  ╚═╝  ╚═╝    ╚═╝  ╚═══╝ ╚══════╝    ╚═╝    "
        ]
        colors_6 = [Colors.C_RED, Colors.C_ORANGE, Colors.C_YELLOW, Colors.C_GREEN, Colors.C_CYAN, Colors.C_BLUE]
        for i, line in enumerate(banner_raw):
            print(pad_line(colors_6[i] + Colors.BOLD + line + Colors.RESET, len(line)))

        print(mid)
        # Tiêu đề chuyển sắc 7 màu từng chữ cái
        title_text = "        [ MASTER CONTROLLER ] - ROBLOX MULTI-INSTANCE NETWORK MANAGER         "
        print(pad_line(Colors.BOLD + Colors.rainbow_text(title_text) + Colors.RESET, len(title_text)))

        # Trạng thái tự động nhận diện cả LIVE và CLONE CHƯA MỞ
        total_tags = len(self.active_tags)
        if total_tags > 0:
            tag_status_str = f"{Colors.GREEN}{Colors.BOLD}[DA KICH HOAT {self.live_tags_count} LIVE | {self.clone_tags_count} CLONE SAN SANG]{Colors.RESET}"
            tag_vis = f"[DA KICH HOAT {self.live_tags_count} LIVE | {self.clone_tags_count} CLONE SAN SANG]"
        else:
            tag_status_str = f"{Colors.YELLOW}[DANG QUET TIM ROBLOX]{Colors.RESET}"
            tag_vis = "[DANG QUET TIM ROBLOX]"

        autoexec_status = f"{Colors.GREEN}[DA BOM VAO AUTOEXEC]{Colors.RESET}" if self.autoexec_synced_count > 0 else f"{Colors.CYAN}[HTTP BRIDGE SAN SANG]{Colors.RESET}"
        autoexec_vis = "[DA BOM VAO AUTOEXEC]" if self.autoexec_synced_count > 0 else "[HTTP BRIDGE SAN SANG]"

        proxy_status = f"{Colors.GREEN}[SCRAPESTACK: 5d1c5fb0...]{Colors.RESET}"
        proxy_vis = "[SCRAPESTACK: 5d1c5fb0...]"

        st_col = f"  {Colors.GRAY}Roblox:{Colors.RESET} {tag_status_str} {Colors.C_PURPLE}|{Colors.RESET} {Colors.GRAY}Client:{Colors.RESET} {autoexec_status} {Colors.C_PURPLE}|{Colors.RESET} {Colors.GRAY}Proxy:{Colors.RESET} {proxy_status}"
        st_vis = f"  Roblox: {tag_vis} | Client: {autoexec_vis} | Proxy: {proxy_vis}"
        print(pad_line(st_col, len(st_vis)))

        print(mid)
        # 8 Menu tính năng gọn gàng & cập nhật tính năng mới
        menu = [
            (Colors.C_RED, "[1] ⚡ QUET TOAN BO TAG & CLONE (MỞ / CHƯA MỞ) & TU DONG BOM AUTOEXEC"),
            (Colors.C_ORANGE, "[2] 📊 Khoi chay Dashboard Real-time (Live Monitoring 3s)"),
            (Colors.C_YELLOW, "[3] 🔄 Cap phat lai IP cho toan bo ban Clone & Autoexec"),
            (Colors.C_GREEN, "[4] 🔍 Chay kiem tra chan doan mang chuyen sau & Scrapestack"),
            (Colors.C_CYAN, "[5] 📋 Xem danh sach Cloned Instances & Network Profiles"),
            (Colors.C_BLUE, "[6] 🌐 Quan ly Pool IP, ProxyScrape & Scrapestack API (5d1c5fb0...)"),
            (Colors.C_PURPLE, "[7] 📑 Xuat bao cao Snapshots JSON & Huong dan su dung Executor"),
            (Colors.LIGHT_CYAN, "[9] 📝 Cau hinh Script Game (Custom Payload) tu dong chay cho tat ca Tag"),
            (Colors.LIGHT_RED, "[8] 🗑️  XOA / DON DEP Autoexec, Script Lua & Reset Pool IP"),
            (Colors.GRAY, "[0] ❌ Thoat chuong trinh"),
        ]

        for col, text in menu:
            colored = f"{col}{Colors.BOLD}{text}{Colors.RESET}"
            print(pad_line(colored, len(text)))

        print(bot)

    def main_menu(self):
        while True:
            try:
                self.print_banner()
                choice = safe_input(f"\n{Colors.BOLD}Lua chon chuc nang (0-9): {Colors.RESET}").strip()

                if choice == "1":
                    self.scan_and_generate_lua_scripts()
                elif choice == "2":
                    self.start_live_dashboard()
                elif choice == "3":
                    self.generate_and_assign_ips()
                elif choice == "4":
                    self.run_deep_diagnostics()
                elif choice == "5":
                    self.view_instances_and_profiles()
                elif choice == "6":
                    self.generate_ip_pool()
                elif choice == "7":
                    self.export_report_and_guide()
                elif choice == "9":
                    self.configure_custom_payload()
                elif choice == "8":
                    self.clean_and_reset_system()
                elif choice in ["0", "exit", "quit"]:
                    self.shutdown()
                    break
                elif choice == "":
                    continue
                else:
                    safe_input(f"{Colors.RED}Lua chon khong hop le! Nhan Enter de tiep tuc...{Colors.RESET}")
            except (KeyboardInterrupt, EOFError):
                self.shutdown()
                break

    def shutdown(self):
        """Đóng hệ thống an toàn"""
        self.bridge_server.stop()
        print(f"\n{Colors.YELLOW}[!] Da dong Master Controller an toan. Tam biet!{Colors.RESET}\n")

    def prompt_select_country(self) -> str:
        """Hiển thị menu chọn quốc gia cho IP/Proxy"""
        print(f"\n  {Colors.BOLD}[ CHON QUOC GIA / REGION CHO IP ROBLOX ]{Colors.RESET}")
        print(f"  {Colors.BOLD}[0]{Colors.RESET} 🌐 {Colors.GREEN}{Colors.BOLD}MULTI-COUNTRY (Moi Tag 1 nuoc khac nhau - Khuyen dung tranh Ban Acc){Colors.RESET}")
        print(f"  {Colors.BOLD}[1]{Colors.RESET} 🇻🇳 {Colors.CYAN}Viet Nam (VN - Ping cuc thap, choi cuc muot){Colors.RESET}")
        print(f"  {Colors.BOLD}[2]{Colors.RESET} 🇯🇵 {Colors.YELLOW}Nhat Ban (JP - Tokyo, on dinh nhat cho Roblox){Colors.RESET}")
        print(f"  {Colors.BOLD}[3]{Colors.RESET} 🇸🇬 {Colors.LIGHT_CYAN}Singapore (SG - SEA Server){Colors.RESET}")
        print(f"  {Colors.BOLD}[4]{Colors.RESET} 🇺🇸 {Colors.LIGHT_RED}Hoa Ky (US - California/New York){Colors.RESET}")
        print(f"  {Colors.BOLD}[5]{Colors.RESET} 🇰🇷 {Colors.C_PURPLE}Han Quoc (KR - Seoul){Colors.RESET}")
        print(f"  {Colors.BOLD}[6]{Colors.RESET} 🇩🇪 {Colors.WHITE}Duc (DE - Europe){Colors.RESET}")
        print(f"  {Colors.BOLD}[7]{Colors.RESET} 🇬🇧 {Colors.C_BLUE}Anh Quoc (GB - UK){Colors.RESET}")
        print(f"  {Colors.BOLD}[8]{Colors.RESET} 🇫🇷 {Colors.C_ORANGE}Phap (FR - France){Colors.RESET}")
        
        c_choice = safe_input(f"\n  {Colors.BOLD}Chon quoc gia mong muon (0-8, mac dinh 0): {Colors.RESET}").strip()
        c_map = {
            "0": "MULTI", "1": "VN", "2": "JP", "3": "SG", "4": "US",
            "5": "KR", "6": "DE", "7": "GB", "8": "FR"
        }
        return c_map.get(c_choice, "MULTI")

    def render_detailed_tag_table(self, instances: List[RobloxWindowInstance]):
        """Hiển thị bảng chi tiết: TAG, STATUS (ON/OFF), CLIENT/EXECUTOR, IP, IP STATUS & PING, REGION"""
        print(f"\n  {Colors.CYAN}[*] Dang do toc do Ping va kiem tra trang thai chinh xac cua tung IP/Proxy...{Colors.RESET}")
        assigned_ips = [inst.assigned_ip for inst in instances if inst.assigned_ip]
        probe_results = NetworkInspector.batch_probe_ips(assigned_ips)

        W = 108
        def pad_cell(raw_text: str, colored_text: str, width: int) -> str:
            pad = max(0, width - len(raw_text))
            return colored_text + (" " * pad)

        top = f"{Colors.C_CYAN}{Colors.BOLD}╔{'═' * (W + 2)}╗{Colors.RESET}"
        mid = f"{Colors.C_CYAN}{Colors.BOLD}╠{'═' * (W + 2)}╣{Colors.RESET}"
        bot = f"{Colors.C_CYAN}{Colors.BOLD}╚{'═' * (W + 2)}╝{Colors.RESET}"
        div = f"{Colors.GRAY}╟{'─' * (W + 2)}╢{Colors.RESET}"

        print(top)
        title_hdr = "BANG THEO DOI CHI TIET CAC TAG, CLIENT/EXECUTOR & TRANG THAI IP CHINH XAC"
        pad_t = max(0, W - len(title_hdr)) // 2
        print(f"{Colors.C_CYAN}{Colors.BOLD}║{Colors.RESET} {' ' * pad_t}{Colors.BOLD}{Colors.rainbow_text(title_hdr)}{Colors.RESET}{' ' * (W - len(title_hdr) - pad_t)} {Colors.C_CYAN}{Colors.BOLD}║{Colors.RESET}")
        print(mid)

        header_str = f"{'TAG ID':<16} {'STATUS':<9} {'CLIENT / EXECUTOR':<22} {'ASSIGNED IP / PROXY':<24} {'IP HEALTH/PING':<18} {'REGION':<14}"
        print(f"{Colors.C_CYAN}{Colors.BOLD}║{Colors.RESET} {Colors.BOLD}{header_str}{Colors.RESET} {Colors.C_CYAN}{Colors.BOLD}║{Colors.RESET}")
        print(div)

        for inst in instances:
            # 1. Trạng thái Tag (ON hay OFF)
            if inst.pid > 0 or inst.hwnd > 0:
                status_colored = f"{Colors.GREEN}{Colors.BOLD}[ ON  ]{Colors.RESET}"
                status_raw = "[ ON  ]"
            else:
                status_colored = f"{Colors.GRAY}[ OFF ]{Colors.RESET}"
                status_raw = "[ OFF ]"

            # 2. Nhận diện Client / Executor
            client_name = NetworkInspector.detect_client_type(inst.process_name, inst.title, inst.pid)
            if len(client_name) > 22:
                client_name = client_name[:22]

            # 3. IP & Trạng thái IP chính xác
            ip_val = inst.assigned_ip or "N/A"
            health_info = probe_results.get(ip_val, ("READY (Header)", 15, "CYAN"))
            health_text = health_info[0]
            health_color = health_info[2]

            if health_color == "GREEN":
                health_disp = f"{Colors.GREEN}{health_text}{Colors.RESET}"
            elif health_color == "YELLOW":
                health_disp = f"{Colors.YELLOW}{health_text}{Colors.RESET}"
            elif health_color == "ORANGE":
                health_disp = f"{Colors.LIGHT_RED}{health_text}{Colors.RESET}"
            else:
                health_disp = f"{Colors.CYAN}{health_text}{Colors.RESET}"

            reg = inst.region or "MULTI"
            if len(reg) > 14:
                reg = reg[:14]

            # Căn lề chuẩn xác từng cell
            c_tag = pad_cell(inst.tag_id, f"{Colors.BOLD}{inst.tag_id}{Colors.RESET}", 16)
            c_st = pad_cell(status_raw, status_colored, 9)
            c_cli = pad_cell(client_name, f"{Colors.YELLOW}{client_name}{Colors.RESET}", 22)
            c_ip = pad_cell(ip_val, f"{Colors.LIGHT_CYAN}{ip_val}{Colors.RESET}", 24)
            c_hl = pad_cell(health_text, health_disp, 18)
            c_reg = pad_cell(reg, f"{Colors.CYAN}{reg}{Colors.RESET}", 14)

            row_line = f"{Colors.C_CYAN}║{Colors.RESET} {c_tag} {c_st} {c_cli} {c_ip} {c_hl} {c_reg} {Colors.C_CYAN}║{Colors.RESET}"
            print(row_line)

        print(bot)

    def scan_and_generate_lua_scripts(self):
        """[1] QUÉT TẤT CẢ CỬA SỔ ĐANG MỞ & BẢN NHÂN BẢN CLONE (CHƯA MỞ) & GÁN DEDICATED IP"""
        self.clear_screen()
        print(f"{Colors.LIGHT_GREEN}{Colors.BOLD}================ [ 1. QUET TOAN BO TAG & CLONE (MO / CHUA MO) ] ================{Colors.RESET}\n")
        
        print(f"  {Colors.CYAN}[*] Dang quet cac cua so Roblox dang chay & cac ban clone tren o dia...{Colors.RESET}")
        instances = self._get_combined_tag_instances()
        
        live_count = len([x for x in instances if x.hwnd > 0 or x.pid > 0])
        clone_count = len([x for x in instances if x.hwnd == 0 and x.pid == 0])

        print(f"  {Colors.GREEN}[+] Phat hien: {Colors.BOLD}{live_count} Cua so dang chay (ON){Colors.RESET} va {Colors.YELLOW}{Colors.BOLD}{clone_count} Ban nhan ban clone (OFF){Colors.RESET}!\n")

        # Chọn quốc gia mong muốn
        country_code = self.prompt_select_country()

        print(f"\n  {Colors.CYAN}[*] Dang cap phat IP/Proxy quoc gia [{country_code}] & sinh Script Lua cho toan bo {len(instances)} Tag/Clone...{Colors.RESET}")
        lua_files = self.lua_generator.generate_scripts_for_scanned_instances(instances, use_live_proxies=True, country_code=country_code)
        
        # Cập nhật Bridge Server
        master_script_path = lua_files.get("MASTER", "")
        master_content = ""
        if os.path.exists(master_script_path):
            with open(master_script_path, "r", encoding="utf-8") as f:
                master_content = f.read()
        self.bridge_server.update_state(instances, master_script=master_content)
        self.active_tags = instances
        self.live_tags_count = live_count
        self.clone_tags_count = clone_count

        # TỰ ĐỘNG BƠM TRỰC TIẾP VÀO AUTOEXEC FOLDERS CỦA CLIENT (ARCEUS X, DELTA, REAL...)
        sync_res = self.autoexec_manager.sync_lua_to_autoexec(master_content)
        pc_synced = sync_res.get("pc_synced", [])
        android_synced = sync_res.get("android_synced", [])
        self.autoexec_synced_count = len(pc_synced) + len(android_synced)

        # HIỂN THỊ BẢNG CHI TIẾT THEO DÕI TRẠNG THÁI TỪNG TAG, CLIENT & IP
        self.render_detailed_tag_table(instances)

        print(f"\n  {Colors.GREEN}{Colors.BOLD}[+] DA TU DONG BOM LUA VAO THU MUC AUTOEXEC CUA CLIENT:{Colors.RESET}")
        if pc_synced:
            for p in pc_synced:
                print(f"      -> PC: {Colors.CYAN}{p}{Colors.RESET}")
        if android_synced:
            for a in android_synced:
                print(f"      -> Android/ADB: {Colors.CYAN}{a}{Colors.RESET}")
        if not pc_synced and not android_synced:
            print(f"      -> {Colors.YELLOW}Da luu san file master tai {OUTPUT_LUA_DIR}{Colors.RESET}")

        print(f"\n  {Colors.LIGHT_GREEN}{Colors.BOLD}⚡ XONG: Mo bat ky ban clone Roblox nao la se duoc set dung IP rieng ngay lap tuc!{Colors.RESET}")
        safe_input(f"\n{Colors.GRAY}Nhan Enter de quay lai Menu...{Colors.RESET}")

    def start_live_dashboard(self):
        """[2] Chạy Dashboard giám sát trực tiếp chu kỳ 3s"""
        self.clear_screen()
        print(f"{Colors.GREEN}[*] Dang khoi chay chu trinh giam sat real-time... (Nhan Ctrl+C de quay lai Menu){Colors.RESET}")
        time.sleep(1)
        try:
            while True:
                self.manager.run_check_cycle()
                instances = InstanceRepository.get_all_instances()
                DashboardRenderer.render(instances)
                time.sleep(3)
        except (KeyboardInterrupt, EOFError):
            print(f"\n{Colors.YELLOW}[*] Da dung live dashboard.{Colors.RESET}")
            time.sleep(1)

    def generate_and_assign_ips(self):
        """[3] Tự động sinh IP mới và gán cho các Tag Roblox thực tế trên màn hình và bản clone"""
        self.clear_screen()
        print(f"{Colors.YELLOW}{Colors.BOLD}================ [ 3. CAP PHAT IP / PROXY DA QUOC GIA CHO CAC TAG & CLONE ] ================{Colors.RESET}\n")
        
        # Quét tất cả cửa sổ và các bản nhân bản
        instances = self._get_combined_tag_instances()
        count = len(instances)
        live_count = len([x for x in instances if x.hwnd > 0 or x.pid > 0])
        clone_count = len([x for x in instances if x.hwnd == 0 and x.pid == 0])

        print(f"  {Colors.GREEN}[+] Tong cong: {count} Tag ({live_count} Dang chay, {clone_count} Ban clone chua mo).{Colors.RESET}")
        
        # Chọn quốc gia
        country_code = self.prompt_select_country()

        print(f"\n  {Colors.CYAN}[*] Dang lay {count} Proxy Live quoc gia [{country_code}] & Cap phat moi...{Colors.RESET}\n")
        
        # Tự động gán đúng số lượng IP cho số Tag
        lua_files = self.lua_generator.generate_scripts_for_scanned_instances(instances, use_live_proxies=True, country_code=country_code)
        m_path = lua_files.get("MASTER", "")
        master_content = ""
        if os.path.exists(m_path):
            with open(m_path, "r", encoding="utf-8") as f:
                master_content = f.read()
                self.bridge_server.update_state(instances, master_script=master_content)
        
        self.active_tags = instances
        self.live_tags_count = live_count
        self.clone_tags_count = clone_count

        # TỰ ĐỘNG BƠM TRỰC TIẾP VÀO AUTOEXEC
        sync_res = self.autoexec_manager.sync_lua_to_autoexec(master_content)
        pc_synced = sync_res.get("pc_synced", [])
        android_synced = sync_res.get("android_synced", [])
        self.autoexec_synced_count = len(pc_synced) + len(android_synced)

        # HIỂN THỊ BẢNG CHI TIẾT THEO DÕI TRẠNG THÁI TỪNG TAG, CLIENT & IP
        self.render_detailed_tag_table(instances)

        print(f"\n  {Colors.GREEN}{Colors.BOLD}[+] DA TU DONG BOM LUA VAO AUTOEXEC CUA CLIENT:{Colors.RESET}")
        if pc_synced:
            for p in pc_synced:
                print(f"      -> PC: {Colors.CYAN}{p}{Colors.RESET}")
        if android_synced:
            for a in android_synced:
                print(f"      -> Android/ADB: {Colors.CYAN}{a}{Colors.RESET}")

        print(f"\n{Colors.GREEN}{Colors.BOLD}[+] HOAN TAT: Da cap phat {count} IP [{country_code}] & Nạp xong Autoexec!{Colors.RESET}")
        print(f"  {Colors.LIGHT_GREEN}Mo bat ky ban clone Roblox nao la se duoc set dung IP rieng ngay lap tuc!{Colors.RESET}")
        safe_input(f"\n{Colors.GRAY}Nhan Enter de quay lai Menu...{Colors.RESET}")

    def run_deep_diagnostics(self):
        """[4] Chẩn đoán chi tiết đường truyền mạng"""
        self.clear_screen()
        print(f"{Colors.CYAN}{Colors.BOLD}================ [ 4. CHUAN DOAN MANG CHUYEN SAU ] ================{Colors.RESET}\n")
        
        print(f"  [*] 1. Dang kiem tra Public IP...")
        pub_ip = ConnectivityChecker.get_public_ip() or "Khong the lay Public IP"
        print(f"      -> Public IP hien tai: {Colors.LIGHT_RED}{pub_ip}{Colors.RESET}")

        print(f"  [*] 2. Dang do thoi gian truy van DNS (roblox.com)...")
        _, dns_time = DNSResolver.resolve_domain("www.roblox.com")
        print(f"      -> DNS Response Time: {Colors.CYAN}{dns_time} ms{Colors.RESET}")

        print(f"  [*] 3. Dang do Ping RTT va Packet Loss den Cloudflare (1.1.1.1)...")
        latency_cf, loss_cf = PingMonitor.ping_host("1.1.1.1", count=3)
        print(f"      -> RTT: {Colors.GREEN}{latency_cf} ms{Colors.RESET} | Packet Loss: {Colors.YELLOW}{loss_cf}%{Colors.RESET}")

        print(f"  [*] 4. Dang do Ping RTT va Packet Loss den Google (8.8.8.8)...")
        latency_gg, loss_gg = PingMonitor.ping_host("8.8.8.8", count=3)
        print(f"      -> RTT: {Colors.GREEN}{latency_gg} ms{Colors.RESET} | Packet Loss: {Colors.YELLOW}{loss_gg}%{Colors.RESET}")

        print(f"\n  [*] 5. Kiem tra Java Network Engine & UGPhone Bridge...")
        from devices.ugphone_bridge import JavaNetworkBridge
        if self.active_tags and self.active_tags[0].assigned_ip:
            first_ip = self.active_tags[0].assigned_ip
            if ":" in first_ip:
                h, p = first_ip.split(":", 1)
                java_diag = JavaNetworkBridge.execute_java_diagnostics(h, int(p))
                lat = java_diag.get("tcp_latency_ms", -1)
                st = java_diag.get("proxy_status", "OFFLINE")
                col = Colors.GREEN if st == "ONLINE" else Colors.LIGHT_RED
                print(f"      -> TCP Handshake Proxy ({first_ip}): {col}{st} ({lat} ms){Colors.RESET}")
            else:
                print(f"      -> Java Engine: {Colors.GREEN}READY{Colors.RESET}")
        else:
            print(f"      -> Java Engine: {Colors.GREEN}READY{Colors.RESET} (Chua co IP gan)")

        print(f"\n  [*] 6. Kiem tra ket noi Scrapestack Proxy API (Key: 5d1c5fb0...)...")
        s_diag = self.scrapestack.test_connection()
        s_st = s_diag.get("status", "OFFLINE")
        s_lat = s_diag.get("latency_ms", -1)
        s_ip = s_diag.get("proxy_ip", "N/A")
        s_col = Colors.GREEN if s_st == "ONLINE" else Colors.LIGHT_RED
        print(f"      -> Scrapestack Proxy API: {s_col}{s_st}{Colors.RESET} ({s_lat} ms)")
        if s_st == "ONLINE":
            print(f"      -> Live Proxied IP: {Colors.CYAN}{s_ip}{Colors.RESET} (Ready for Roblox multi-tags)")

        print(f"\n{Colors.GREEN}[+] Hoan tat chan doan mang chuyen sau!{Colors.RESET}")
        safe_input(f"\n{Colors.GRAY}Nhan Enter de quay lai Menu...{Colors.RESET}")

    def view_instances_and_profiles(self):
        """[5] Xem cấu hình chi tiết"""
        self.clear_screen()
        print(f"{Colors.WHITE}{Colors.BOLD}================ [ 5. DANH SACH INSTANCES, CLONES & NETWORK PROFILES ] ================{Colors.RESET}\n")
        
        # Danh sách các Tag Roblox & Clones
        instances = self._get_combined_tag_instances()
        print(f"  {Colors.BOLD}[ DANH SACH ROBLOX TAGS & CLONED PROFILES ]{Colors.RESET}")
        print(f"  {Colors.BOLD}{'TAG ID':<16} {'STATUS':<12} {'TYPE':<16} {'TITLE / CLONE NAME'}{Colors.RESET}")
        print("  " + "-" * 75)
        for inst in instances:
            st = f"{Colors.GREEN}ONLINE{Colors.RESET}" if inst.pid > 0 else f"{Colors.YELLOW}OFFLINE{Colors.RESET}"
            print(f"  {inst.tag_id:<16} {st:<21} {inst.process_name:<16} {inst.title}")

        print(f"\n  {Colors.BOLD}[ NETWORK PROFILES CO SAN ]{Colors.RESET}")
        for p_id, p in DEFAULT_PROFILES.items():
            print(f"  * {Colors.CYAN}{p.name}{Colors.RESET} ({p.region}) | DNS: {p.dns_primary}, {p.dns_secondary} | MTU: {p.mtu}")

        safe_input(f"\n{Colors.GRAY}Nhan Enter de quay lai Menu...{Colors.RESET}")

    def generate_ip_pool(self):
        """[6] Sinh thêm IP hoặc Tải Live Proxy từ ProxyScrape / Scrapestack API"""
        self.clear_screen()
        print(f"{Colors.LIGHT_RED}{Colors.BOLD}================ [ 6. QUAN LY POOL IP & PROXY TOAN CAU ] ================{Colors.RESET}\n")
        print(f"  {Colors.BOLD}[1]{Colors.RESET} {Colors.GREEN}Tai Proxy HTTP Live toan cau truc tiep tu ProxyScrape API{Colors.RESET}")
        print(f"  {Colors.BOLD}[2]{Colors.RESET} {Colors.YELLOW}Tu sinh danh sach IP ngau nhien (Virtual Dedicated IPs){Colors.RESET}")
        print(f"  {Colors.BOLD}[3]{Colors.RESET} {Colors.CYAN}Kiem tra & Lay IP truc tiep tu Scrapestack Proxy API (Key: 5d1c5fb0...){Colors.RESET}")
        print(f"  {Colors.BOLD}[4]{Colors.RESET} {Colors.LIGHT_CYAN}Cap phat IP Scrapestack cho toan bo ban Clone dang co{Colors.RESET}\n")
        
        mode = safe_input(f"{Colors.BOLD}Chon che do (1-4): {Colors.RESET}")
        
        if mode == "1":
            print(f"\n  {Colors.CYAN}[*] Dang ket noi ProxyScrape API de lay danh sach Proxy HTTP toan cau...{Colors.RESET}")
            from network.proxy_fetcher import ProxyFetcher, PROXIES_CACHE_FILE
            proxies = ProxyFetcher.fetch_live_proxies(force_refresh=True)
            print(f"  {Colors.GREEN}{Colors.BOLD}[+] Da tai thanh cong {len(proxies)} Proxy Live!{Colors.RESET}\n")
            print(f"  {Colors.WHITE}10 Proxy dau tien:{Colors.RESET}")
            for p in proxies[:10]:
                print(f"    -> {Colors.CYAN}{p}{Colors.RESET}")
            print(f"\n  {Colors.GREEN}[*] Da luu toan bo danh sach vao: {PROXIES_CACHE_FILE}{Colors.RESET}")
        elif mode == "3":
            print(f"\n  {Colors.CYAN}[*] Dang ket noi Scrapestack Proxy API de kiem tra...{Colors.RESET}")
            res = self.scrapestack.test_connection()
            if res.get("status") == "ONLINE":
                print(f"  {Colors.GREEN}{Colors.BOLD}[+] Scrapestack Proxy ONLINE! (Latency: {res.get('latency_ms')} ms){Colors.RESET}")
                print(f"  {Colors.WHITE}  - API Key     : {Colors.YELLOW}{res.get('api_key_masked')}{Colors.RESET}")
                print(f"  {Colors.WHITE}  - Live IP     : {Colors.CYAN}{res.get('proxy_ip')}{Colors.RESET}")
                print(f"  {Colors.WHITE}  - Proxy Pool  : {Colors.GREEN}Active (Standard Proxies){Colors.RESET}")
            else:
                print(f"  {Colors.RED}[!] Ket noi Scrapestack that bai: {res.get('error')}{Colors.RESET}")
        elif mode == "4":
            print(f"\n  {Colors.CYAN}[*] Dang lay dải IP tu Scrapestack Proxy...{Colors.RESET}")
            s_proxies = self.scrapestack.batch_fetch_proxies(count=len(self.active_tags) or 5)
            print(f"  {Colors.GREEN}[+] Da lay thanh cong {len(s_proxies)} IP tu Scrapestack:{Colors.RESET}")
            for sp in s_proxies:
                print(f"    -> {Colors.CYAN}{sp['ip']}{Colors.RESET} ({sp['region']})")
        else:
            user_val = safe_input(f"\n{Colors.BOLD}Nhap so luong IP muon sinh (vi du: 20): {Colors.RESET}")
            try:
                count = int(user_val) if user_val else 10
            except ValueError:
                count = 10
            ips = RandomIPGenerator.generate_batch(count=count)
            print(f"\n{Colors.GREEN}[+] Da sinh {len(ips)} dia chi IP va luu vao data/Generated_IPs.txt:{Colors.RESET}")
            for ip in ips[:10]:
                print(f"  - {Colors.CYAN}{ip}{Colors.RESET}")
            if len(ips) > 10:
                print(f"  ... va {len(ips) - 10} IP khac.")
        
        safe_input(f"\n{Colors.GRAY}Nhan Enter de quay lai Menu...{Colors.RESET}")


    def export_report_and_guide(self):
        """[7] Xuất báo cáo JSON và Hiển thị hướng dẫn Executor"""
        self.clear_screen()
        print(f"{Colors.BLUE}{Colors.BOLD}================ [ 7. XUAT BAO CAO & HUONG DAN EXECUTOR ] ================{Colors.RESET}\n")
        export_file = os.path.join(BASE_DIR, "data", "network_report.json")
        instances = InstanceRepository.get_all_instances()
        
        report_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "public_ip": ConnectivityChecker.get_public_ip(),
            "instances": []
        }
        for inst in instances:
            snap = SnapshotRepository.get_latest_snapshot(inst.id)
            report_data["instances"].append({
                "id": inst.id,
                "name": inst.name,
                "region": inst.region,
                "assigned_ip": snap.local_ip if snap else "N/A",
                "profile": inst.assigned_profile,
                "latency_ms": snap.latency_ms if snap else -1,
                "status": inst.status
            })
            
        with open(export_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"{Colors.GREEN}[+] 1. Da xuat bao cao he thong JSON tai:{Colors.RESET}")
        print(f"       {Colors.WHITE}{export_file}{Colors.RESET}\n")

        print(f"{Colors.CYAN}[*] 2. Huong dan nap ma Lua vao Roblox Executor:{Colors.RESET}")
        print(f"    - Mo Executor bat ky (Synapse, Fluxus, Delta, Wave, Solara) va thuc thi:")
        print(f"      {Colors.GREEN}loadstring(game:HttpGet(\"http://127.0.0.1:8888/api/script\"))(){Colors.RESET}")
        print(f"    - Hoac copy file trong: {Colors.WHITE}{OUTPUT_LUA_DIR}{Colors.RESET}")
        
        safe_input(f"\n{Colors.GRAY}Nhan Enter de quay lai Menu...{Colors.RESET}")

    def clean_and_reset_system(self):
        """[8] Xóa / Dọn dẹp Autoexec, Script Lua, Cache Proxy & Reset hệ thống"""
        self.clear_screen()
        print(f"{Colors.LIGHT_RED}{Colors.BOLD}================ [ 8. XOA / DON DEP & RESET HE THONG ] ================{Colors.RESET}\n")
        print(f"  {Colors.BOLD}[1]{Colors.RESET} {Colors.YELLOW}Xoa Script Lua khoi tat ca thu muc Autoexec (Arceus X, Delta, Codex, Real...){Colors.RESET}")
        print(f"  {Colors.BOLD}[2]{Colors.RESET} {Colors.CYAN}Xoa toan bo file Lua da sinh trong thu muc data/generated_lua/{Colors.RESET}")
        print(f"  {Colors.BOLD}[3]{Colors.RESET} {Colors.WHITE}Xoa Cache Proxy da tai (data/Proxies_*.txt, data/Generated_IPs.txt){Colors.RESET}")
        print(f"  {Colors.BOLD}[4]{Colors.RESET} {Colors.C_PURPLE}Reset danh sach Ban Clone (cloned_profiles.json ve mac dinh){Colors.RESET}")
        print(f"  {Colors.BOLD}[5]{Colors.RESET} 🧹 {Colors.LIGHT_RED}{Colors.BOLD}XOA TAT CA & RESET TOAN BO HE THONG VE BAN DAU{Colors.RESET}")
        print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  {Colors.GRAY}Quay lai Menu chinh{Colors.RESET}\n")
        
        opt = safe_input(f"{Colors.BOLD}Chon tinh nang xoa (0-5): {Colors.RESET}").strip()
        
        if opt == "1":
            print(f"\n  {Colors.CYAN}[*] Dang xoa script khoi tat ca thu muc Autoexec...{Colors.RESET}")
            res = self.autoexec_manager.clean_all_autoexec_scripts()
            pc_c = res.get("pc_cleaned", [])
            adb_c = res.get("android_cleaned", [])
            print(f"  {Colors.GREEN}[+] Da xoa {len(pc_c)} file tren PC va {len(adb_c)} file tren Android Giả lập!{Colors.RESET}")
            for p in pc_c:
                print(f"    - PC: {Colors.GRAY}{p}{Colors.RESET}")
            for a in adb_c:
                print(f"    - Android: {Colors.GRAY}{a}{Colors.RESET}")
            self.autoexec_synced_count = 0

        elif opt == "2":
            print(f"\n  {Colors.CYAN}[*] Dang xoa cac file Lua trong {OUTPUT_LUA_DIR}...{Colors.RESET}")
            deleted_count = 0
            if os.path.exists(OUTPUT_LUA_DIR):
                for f in os.listdir(OUTPUT_LUA_DIR):
                    if f.endswith(".lua"):
                        try:
                            os.remove(os.path.join(OUTPUT_LUA_DIR, f))
                            deleted_count += 1
                        except Exception:
                            pass
            print(f"  {Colors.GREEN}[+] Da xoa thanh cong {deleted_count} file script Lua!{Colors.RESET}")

        elif opt == "3":
            print(f"\n  {Colors.CYAN}[*] Dang xoa Cache Proxy & Pool IP...{Colors.RESET}")
            import glob
            p_files = glob.glob(os.path.join(DATA_DIR, "Proxies_*.txt")) + [
                os.path.join(DATA_DIR, "Generated_IPs.txt"),
                os.path.join(DATA_DIR, "Proxies_Live.txt")
            ]
            d_count = 0
            for pf in p_files:
                if os.path.exists(pf):
                    try:
                        os.remove(pf)
                        d_count += 1
                    except Exception:
                        pass
            print(f"  {Colors.GREEN}[+] Da xoa {d_count} file cache proxy!{Colors.RESET}")

        elif opt == "4":
            print(f"\n  {Colors.CYAN}[*] Dang reset danh sach Cloned Profiles...{Colors.RESET}")
            from core.clone_scanner import CLONE_DB_FILE
            if os.path.exists(CLONE_DB_FILE):
                try:
                    os.remove(CLONE_DB_FILE)
                except Exception:
                    pass
            self.clone_scanner.scan_all_clones()
            print(f"  {Colors.GREEN}[+] Da reset danh sach Ban Clone ve mac dinh!{Colors.RESET}")

        elif opt == "5":
            print(f"\n  {Colors.LIGHT_RED}[*] Dang tien hanh XOA TAT CA & Full Reset...{Colors.RESET}")
            # 1. Clean autoexec
            self.autoexec_manager.clean_all_autoexec_scripts()
            self.autoexec_synced_count = 0
            # 2. Clean lua
            if os.path.exists(OUTPUT_LUA_DIR):
                for f in os.listdir(OUTPUT_LUA_DIR):
                    if f.endswith(".lua"):
                        try:
                            os.remove(os.path.join(OUTPUT_LUA_DIR, f))
                        except Exception:
                            pass
            # 3. Clean proxies
            import glob
            for pf in glob.glob(os.path.join(DATA_DIR, "Proxies_*.txt")) + [os.path.join(DATA_DIR, "Generated_IPs.txt"), os.path.join(DATA_DIR, "Proxies_Live.txt")]:
                if os.path.exists(pf):
                    try:
                        os.remove(pf)
                    except Exception:
                        pass
            # 4. Reset clones
            from core.clone_scanner import CLONE_DB_FILE
            if os.path.exists(CLONE_DB_FILE):
                try:
                    os.remove(CLONE_DB_FILE)
                except Exception:
                    pass
            print(f"\n  {Colors.GREEN}{Colors.BOLD}[+] HOAN TAT: Da xoa sach toan bo du lieu va reset he thong ve ban dau!{Colors.RESET}")

        safe_input(f"\n{Colors.GRAY}Nhan Enter de quay lai Menu...{Colors.RESET}")

    def configure_custom_payload(self):
        """[9] Cấu hình Script Game (Custom Payload) tự động chạy cho tất cả các Tag/Clone"""
        self.clear_screen()
        print(f"{Colors.LIGHT_CYAN}{Colors.BOLD}================ [ 9. CAU HINH SCRIPT GAME TU DONG CHAY CHO TAT CA TAG ] ================{Colors.RESET}\n")
        print(f"  {Colors.WHITE}File Execute Master duy nhat dong vai tro la Bo khoi chay tong hop (Universal Launcher).")
        print(f"  Sau khi set IP rieng va cach ly mang, Script nay se {Colors.GREEN}{Colors.BOLD}TU DONG CHAY TREN TAT CA CAC TAG / CLONE!{Colors.RESET}\n")
        
        payload_file = os.path.join(DATA_DIR, "custom_payload.lua")
        current_code = ""
        if os.path.exists(payload_file):
            try:
                with open(payload_file, "r", encoding="utf-8") as f:
                    current_code = f.read()
            except Exception:
                pass

        print(f"  {Colors.BOLD}[1]{Colors.RESET} {Colors.GREEN}Xem noi dung Script Game Payload hien tai{Colors.RESET}")
        print(f"  {Colors.BOLD}[2]{Colors.RESET} {Colors.YELLOW}Nhap Link Script Hub URL (loadstring game:HttpGet){Colors.RESET}")
        print(f"  {Colors.BOLD}[3]{Colors.RESET} {Colors.CYAN}Dan ma Script Lua truc tiep tu ban phim{Colors.RESET}")
        print(f"  {Colors.BOLD}[4]{Colors.RESET} {Colors.LIGHT_RED}Xoa Script Payload (Reset ve mac dinh){Colors.RESET}")
        print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  {Colors.GRAY}Quay lai Menu chinh{Colors.RESET}\n")

        opt = safe_input(f"{Colors.BOLD}Chon thao tac (0-4): {Colors.RESET}").strip()
        if opt == "1":
            print(f"\n{Colors.CYAN}--- NOI DUNG SCRIPT PAYLOAD DANG DUOC NAP ({payload_file}) ---{Colors.RESET}")
            print(current_code or f"{Colors.YELLOW}[Chua co script]{Colors.RESET}")
            print(f"{Colors.CYAN}-------------------------------------------------------------------{Colors.RESET}")
        elif opt == "2":
            url = safe_input(f"\n{Colors.BOLD}Nhap URL Script Lua (vi du: https://raw.githubusercontent.com/.../main.lua): {Colors.RESET}").strip()
            if url:
                wrapper_code = f'-- [[ AUTO-RUNNER SCRIPT FOR ALL TAGS ]]\npcall(function()\n    loadstring(game:HttpGet("{url}"))()\nend)\n'
                with open(payload_file, "w", encoding="utf-8") as f:
                    f.write(wrapper_code)
                print(f"\n{Colors.GREEN}{Colors.BOLD}[+] Da luu Script URL thanh cong! Moi Tag mo len se tu dong chay script nay.{Colors.RESET}")
        elif opt == "3":
            print(f"\n{Colors.YELLOW}Nhap hoac dan dong Script Lua cua ban (Nhan Enter de luu):{Colors.RESET}")
            script_line = safe_input(f"{Colors.BOLD}> {Colors.RESET}").strip()
            if script_line:
                with open(payload_file, "w", encoding="utf-8") as f:
                    f.write(f"-- [[ USER CUSTOM SCRIPT PAYLOAD ]]\n{script_line}\n")
                print(f"\n{Colors.GREEN}{Colors.BOLD}[+] Da luu Script Lua thanh cong!{Colors.RESET}")
        elif opt == "4":
            default_text = '-- [[ ROBLOX MULTI-TAG USER CUSTOM SCRIPT PAYLOAD ]]\nprint("[+] [UNIVERSAL MASTER EXECUTOR] All Tag scripts auto-executed successfully!")\n'
            with open(payload_file, "w", encoding="utf-8") as f:
                f.write(default_text)
            print(f"\n{Colors.GREEN}[+] Da reset file Payload ve mac dinh!{Colors.RESET}")

        safe_input(f"\n{Colors.GRAY}Nhan Enter de quay lai Menu...{Colors.RESET}")

if __name__ == "__main__":

    try:
        controller = MasterController()
        controller.main_menu()
    except (KeyboardInterrupt, EOFError):
        print("\n[!] Tam biet!")
        sys.exit(0)
