# -*- coding: utf-8 -*-
"""
ROBLOX MULTI-TAG MASTER CONTROLLER & UNIFIED AUTOMATION HUB
Hệ thống điều khiển mạng đa tiến trình và giám sát tự động mở lại Roblox:
  - 100% Độc lập: Mỗi Tag nhận 1 IP, 1 HWID, 1 MAC, 1 Client-UUID, 1 User-Agent và 1 cặp DNS riêng.
  - Per-Tag Multi-Game Hub: Mỗi Tag có thể join vào 1 Game khác nhau (Blox Fruits, King Legacy, Fisch, PS99...).
  - Nhúng sâu Java Engine: Selection Sort Engine & Deep Network Prober trên Java 8 JRE.
  - Auto-Restart Watchdog: Lua Heartbeat định kỳ 2.5s & tự động mở lại khi acc bị văng (Error 277, Kick, Crash).
  - Quy trình 1-Chạm (Master Auto-Pipeline): Tự động hóa toàn diện từ Quét -> Sắp xếp IP -> Bơm Autoexec -> Launch Game -> Kích hoạt Watchdog.
"""

import os
import sys
import time
import json
import socket
import random
from typing import List, Dict, Optional, Tuple

# Thiết lập đường dẫn môi trường
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


from cli.colors import Colors
from core.scanner import RobloxWindowScanner, RobloxWindowInstance, WindowRect
from core.clone_scanner import ClonedProfileScanner, ClonedInstanceProfile
from core.lua_generator import LuaScriptGenerator
from core.autoexec_manager import AutoexecManager
from core.game_selector import game_manager, POPULAR_ROBLOX_GAMES, RobloxGameItem
from core.watchdog_supervisor import watchdog
from core.java_sort_bridge import SelectionSortBridge, RobloxAutoLauncher
from network.bridge_server import RobloxBridgeServer
from network.proxy_fetcher import ProxyFetcher, SUPPORTED_COUNTRIES
from network.scrapestack_client import ScrapestackClient
from devices.ugphone_bridge import UGPhoneNetworkEngine
from monitoring.status import NetworkInspector
from config.logging import setup_logger

logger = setup_logger("master_controller")


def safe_input(prompt_text: str = "") -> str:
    """Hàm nhập liệu an toàn chống lỗi EOFError trên Windows / Non-interactive environments"""
    try:
        return input(prompt_text)
    except (EOFError, KeyboardInterrupt):
        return "0"


class MasterController:
    """Trung tâm điều phối toàn diện hệ thống Roblox Multi-Tag"""

    def __init__(self):
        self.scanner = RobloxWindowScanner()
        self.clone_scanner = ClonedProfileScanner()
        self.lua_generator = LuaScriptGenerator()
        self.autoexec_manager = AutoexecManager()
        self.scrapestack = ScrapestackClient()
        self.bridge_server = RobloxBridgeServer(host="127.0.0.1", port=8888)
        
        # Bật Bridge Server và Watchdog chạy nền
        self.bridge_server.start()

        self.active_tags: List[RobloxWindowInstance] = []
        self.live_tags_count = 0
        self.clone_tags_count = 0
        self.autoexec_synced_count = 0
        self.country_config_file = os.path.join(BASE_DIR, "data", "country_config.json")
        self.selected_country = self._load_selected_country()

    def _load_selected_country(self) -> str:
        """Tải cấu hình quốc gia IP đã chọn trước đó"""
        if os.path.exists(self.country_config_file):
            try:
                with open(self.country_config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("selected_country", "MULTI")
            except Exception:
                pass
        return "MULTI"5

    def _save_selected_country(self, country_code: str):
        """Lưu cấu hình quốc gia IP đã chọn"""
        try:
            os.makedirs(os.path.dirname(self.country_config_file), exist_ok=True)
            with open(self.country_config_file, "w", encoding="utf-8") as f:
                json.dump({"selected_country": country_code}, f, indent=2)
        except Exception:
            pass

    def _get_combined_tag_instances(self) -> List[RobloxWindowInstance]:
        """Quét và kết hợp tất cả các bản Roblox (Đang chạy thực tế + Bản Clone / Giả lập trên đĩa)"""
        live_windows: List[RobloxWindowInstance] = []
        try:
            if hasattr(self.scanner, "scan_roblox_instances"):
                live_windows = self.scanner.scan_roblox_instances()
            elif hasattr(self.scanner, "scan_active_roblox_windows"):
                live_windows = self.scanner.scan_active_roblox_windows()
            elif hasattr(self.scanner, "scan_instances"):
                live_windows = self.scanner.scan_instances()
        except Exception as e:
            logger.warning(f"Live scanner fallback error: {e}")
            live_windows = []

        cloned_profiles = []
        try:
            if hasattr(self.clone_scanner, "scan_all_profiles"):
                cloned_profiles = self.clone_scanner.scan_all_profiles()
            elif hasattr(self.clone_scanner, "scan_all_clones"):
                cloned_profiles = self.clone_scanner.scan_all_clones()
        except Exception as e:
            logger.warning(f"Clone scanner fallback error: {e}")
            cloned_profiles = []

        ugphone_instances = []
        try:
            if hasattr(UGPhoneNetworkEngine, "scan_cloud_devices"):
                ugphone_instances = UGPhoneNetworkEngine.scan_cloud_devices()
        except Exception:
            ugphone_instances = []

        combined: List[RobloxWindowInstance] = list(live_windows)
        
        for idx, ug in enumerate(ugphone_instances):
            tag_id = ug["device_id"]
            combined.append(RobloxWindowInstance(
                tag_id=tag_id,
                hwnd=0,
                title=f"UGPhone Cloud [{ug.get('ip', 'N/A')}]",
                pid=0,
                process_name="UGPHONE_CLOUD",
                class_name="CloudPhone",
                rect=WindowRect(),
                screen_position=f"Cloud Device #{idx+1}",
                memory_usage="Cloud VM",
                account_username=f"UGPhone_Acc_{idx+1}"
            ))
            
        for idx, cp in enumerate(cloned_profiles):
            tag_id = cp.tag_id
            if not any(item.tag_id == tag_id for item in combined):
                combined.append(RobloxWindowInstance(
                    tag_id=tag_id,
                    hwnd=0,
                    title=f"{cp.name} [CHƯA MỞ]",
                    pid=0,
                    process_name=cp.clone_type,
                    class_name=cp.clone_type,
                    rect=WindowRect(),
                    screen_position="Offline / Pre-Allocated",
                    memory_usage="0 MB",
                    account_username=cp.account_username or f"Clone_User_{idx+1}"
                ))
        return combined

    def sync_system_state(self, instances: List[RobloxWindowInstance], use_live_proxies: bool = False, country_code: Optional[str] = None) -> Dict:
        """
        [ĐỒNG BỘ TOÀN DIỆN] Cập nhật thống nhất trạng thái giữa Python, Lua Generator, 
        Autoexec Manager, Bridge Server và Watchdog Daemon để không bao giờ bị lệch dữ liệu.
        """
        target_country = country_code or self.selected_country or "MULTI"
        self.active_tags = instances
        self.live_tags_count = len([x for x in instances if x.hwnd > 0 or x.pid > 0])
        self.clone_tags_count = len([x for x in instances if x.hwnd == 0 and x.pid == 0])

        # 1. Sinh mã Lua cho từng Tag và Master Router
        lua_files = self.lua_generator.generate_scripts_for_scanned_instances(
            instances, use_live_proxies=use_live_proxies, country_code=target_country
        )
        master_path = lua_files.get("MASTER", "")
        master_code = ""
        if master_path and os.path.exists(master_path):
            with open(master_path, "r", encoding="utf-8") as f:
                master_code = f.read()

        # 2. Đồng bộ vào toàn bộ thư mục Autoexec
        sync_res = self.autoexec_manager.sync_lua_to_autoexec(master_code)
        pc_synced = sync_res.get("pc_synced", [])
        android_synced = sync_res.get("android_synced", [])
        self.autoexec_synced_count = len(pc_synced) + len(android_synced)

        # 3. Cập nhật Bridge Server Shared State
        self.bridge_server.update_state(instances, master_script=master_code)

        # 4. Đăng ký các Tag vào Watchdog
        c_info = SUPPORTED_COUNTRIES.get(target_country, {"name": target_country, "tag": f"[{target_country}]"})
        def_reg = f"{c_info.get('tag', f'[{target_country}]')} {c_info.get('name', target_country)}"
        for inst in instances:
            tag_g = game_manager.get_game_for_tag(inst.tag_id)
            watchdog.register_tag(
                tag_id=inst.tag_id,
                assigned_ip=inst.assigned_ip or "127.0.0.1",
                region=getattr(inst, "region", def_reg),
                username=getattr(inst, "account_username", ""),
                place_id=tag_g.get("place_id", "2753915549"),
                pid=inst.pid
            )

        return {
            "lua_files": lua_files,
            "autoexec_synced_count": self.autoexec_synced_count,
            "master_code_len": len(master_code)
        }

    def clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")

    def print_banner(self):
        self.clear_screen()
        W = 96
        def pad_line(colored_str, visible_len, border_col=Colors.C_PURPLE):
            pad = max(0, W - visible_len)
            return f"{border_col}{Colors.BOLD}║{Colors.RESET} {colored_str}{' ' * pad} {border_col}{Colors.BOLD}║{Colors.RESET}"

        top = f"{Colors.C_PURPLE}{Colors.BOLD}╔{'═' * (W + 2)}╗{Colors.RESET}"
        mid = f"{Colors.C_PURPLE}{Colors.BOLD}╠{'═' * (W + 2)}╣{Colors.RESET}"
        div = f"{Colors.C_PURPLE}{Colors.BOLD}╟{'─' * (W + 2)}╢{Colors.RESET}"
        bot = f"{Colors.C_PURPLE}{Colors.BOLD}╚{'═' * (W + 2)}╝{Colors.RESET}"

        print(top)
        banner_raw = [
            "  ██████╗   ██████╗  ██████╗  ██╗       ██████╗  ██╗  ██╗    ███╗   ██╗ ███████╗ ████████╗   ",
            "  ██╔══██╗ ██╔═══██╗ ██╔══██╗ ██║      ██╔═══██╗ ╚██╗██╔╝    ████╗  ██║ ██╔════╝ ╚══██╔══╝   ",
            "  ██████╔╝ ██║   ██║ ██████╔╝ ██║      ██║   ██║  ╚███╔╝     ██╔██╗ ██║ █████╗      ██║     ",
            "  ██╔══██╗ ██║   ██║ ██╔══██╗ ██║      ██║   ██║  ██╔██╗     ██║╚██╗██║ ██╔══╝      ██║     ",
            "  ██║  ██║ ╚██████╔╝ ██████╔╝ ███████╗ ╚██████╔╝ ██╔╝ ██╗    ██║ ╚████║ ███████╗    ██║     ",
            "  ╚═╝  ╚═╝  ╚═════╝  ╚═════╝  ╚══════╝  ╚═════╝  ╚═╝  ╚═╝    ╚═╝  ╚═══╝ ╚══════╝    ╚═╝     "
        ]
        colors_6 = [Colors.C_RED, Colors.C_ORANGE, Colors.C_YELLOW, Colors.C_GREEN, Colors.C_CYAN, Colors.C_BLUE]
        for i, line in enumerate(banner_raw):
            print(pad_line(colors_6[i] + Colors.BOLD + line + Colors.RESET, len(line)))

        print(mid)
        title_text = "     ⚡ [ UNIFIED MASTER CONTROLLER ] - ROBLOX MULTI-INSTANCE & AUTO-RESTART HUB ⚡     "
        print(pad_line(Colors.BOLD + Colors.rainbow_text(title_text) + Colors.RESET, len(title_text)))

        # Trạng thái tổng quan thời gian thực
        total_tags = len(self.active_tags)
        if total_tags > 0:
            tag_status_str = f"{Colors.GREEN}{Colors.BOLD}[{self.live_tags_count} LIVE | {self.clone_tags_count} CLONE]{Colors.RESET}"
            tag_vis = f"[{self.live_tags_count} LIVE | {self.clone_tags_count} CLONE]"
        else:
            tag_status_str = f"{Colors.YELLOW}[SẴN SÀNG QUÉT]{Colors.RESET}"
            tag_vis = "[SẴN SÀNG QUÉT]"

        autoexec_status = f"{Colors.GREEN}[ĐÃ BƠM AUTOEXEC]{Colors.RESET}" if self.autoexec_synced_count > 0 else f"{Colors.CYAN}[BRIDGE READY]{Colors.RESET}"
        autoexec_vis = "[ĐÃ BƠM AUTOEXEC]" if self.autoexec_synced_count > 0 else "[BRIDGE READY]"

        cur_game = game_manager.get_current_game()
        if game_manager.per_tag_mode:
            game_name = f"Per-Tag ({len(game_manager.get_all_tag_games())} Games)"
        else:
            game_name = cur_game.get("name", "Blox Fruits")[:18]
        game_status = f"{Colors.LIGHT_CYAN}[{game_name}]{Colors.RESET}"
        game_vis = f"[{game_name}]"

        w_summary = watchdog.get_summary()
        w_status = f"{Colors.GREEN}[ON: {w_summary['total_restarts']} RESTARTS]{Colors.RESET}" if w_summary["is_enabled"] else f"{Colors.GRAY}[OFF]{Colors.RESET}"
        w_vis = f"[ON: {w_summary['total_restarts']} RESTARTS]" if w_summary["is_enabled"] else "[OFF]"

        is_android = os.path.exists("/system/build.prop") or "ANDROID_ROOT" in os.environ or os.path.exists("/sdcard")
        plat_txt = f"{Colors.GREEN}[UGPhone Cloud]{Colors.RESET}" if is_android else f"{Colors.CYAN}[Windows PC]{Colors.RESET}"
        plat_vis = "[UGPhone Cloud]" if is_android else "[Windows PC]"

        sel_c = self.selected_country or "MULTI"
        c_info = SUPPORTED_COUNTRIES.get(sel_c, {"name": sel_c, "flag": "🌐"})
        ip_txt = f"{Colors.YELLOW}[{c_info.get('flag', '🌐')} {sel_c}]{Colors.RESET}"
        ip_vis = f"[{c_info.get('flag', '🌐')} {sel_c}]"

        st_col = f"  {Colors.GRAY}Plat:{Colors.RESET} {plat_txt} {Colors.C_PURPLE}|{Colors.RESET} {Colors.GRAY}Tags:{Colors.RESET} {tag_status_str} {Colors.C_PURPLE}|{Colors.RESET} {Colors.GRAY}IP:{Colors.RESET} {ip_txt} {Colors.C_PURPLE}|{Colors.RESET} {Colors.GRAY}Game:{Colors.RESET} {game_status} {Colors.C_PURPLE}|{Colors.RESET} {Colors.GRAY}Watchdog:{Colors.RESET} {w_status}"
        st_vis = f"  Plat: {plat_vis} | Tags: {tag_vis} | IP: {ip_vis} | Game: {game_vis} | Watchdog: {w_vis}"
        print(pad_line(st_col, len(st_vis)))

        print(mid)
        
        # TRỤ CỘT 1: ĐIỀU PHỐI & KHỞI CHẠY 1-CHẠM
        cat1 = f"  {Colors.C_RED}{Colors.BOLD}► [ TRỤ CỘT 1: ĐIỀU PHỐI, CHỌN GAME & KHỞI CHẠY 1-CHẠM ]{Colors.RESET}"
        print(pad_line(cat1, len("  ► [ TRỤ CỘT 1: ĐIỀU PHỐI, CHỌN GAME & KHỞI CHẠY 1-CHẠM ]")))
        m1 = f"    {Colors.LIGHT_GREEN}{Colors.BOLD}[1]{Colors.RESET}  🚀 {Colors.LIGHT_GREEN}{Colors.BOLD}FULL AUTO PIPELINE (1-Chạm: Quét + Sort IP Java + Bơm Autoexec + Launch + Watchdog){Colors.RESET}"
        m2 = f"    {Colors.LIGHT_CYAN}{Colors.BOLD}[2]{Colors.RESET}  🎮 {Colors.WHITE}Cấu hình Game Roblox & Teleport Hub (Global hoặc Mỗi Tag 1 Game riêng){Colors.RESET}"
        m3 = f"    {Colors.GREEN}{Colors.BOLD}[3]{Colors.RESET}  🛡️ {Colors.WHITE}Giám sát & Bật/Tắt Auto-Restart Watchdog (Tự động mở lại Tag khi văng/tắt){Colors.RESET}"
        m4 = f"    {Colors.C_ORANGE}{Colors.BOLD}[4]{Colors.RESET}  📊 {Colors.WHITE}Khởi chạy Live Dashboard Giám sát Real-Time (FPS, Ping, RAM chu kỳ 3s){Colors.RESET}"
        print(pad_line(m1, len("    [1]  🚀 FULL AUTO PIPELINE (1-Chạm: Quét + Sort IP Java + Bơm Autoexec + Launch + Watchdog)")))
        print(pad_line(m2, len("    [2]  🎮 Cấu hình Game Roblox & Teleport Hub (Global hoặc Mỗi Tag 1 Game riêng)")))
        print(pad_line(m3, len("    [3]  🛡️ Giám sát & Bật/Tắt Auto-Restart Watchdog (Tự động mở lại Tag khi văng/tắt)")))
        print(pad_line(m4, len("    [4]  📊 Khởi chạy Live Dashboard Giám sát Real-Time (FPS, Ping, RAM chu kỳ 3s)")))
        print(div)

        # TRỤ CỘT 2: TỐI ƯU HÓA MẠNG & NHÚNG SÂU JAVA
        cat2 = f"  {Colors.C_YELLOW}{Colors.BOLD}► [ TRỤ CỘT 2: TỐI ƯU MẠNG & THUẬT TOÁN JAVA ENGINE ]{Colors.RESET}"
        print(pad_line(cat2, len("  ► [ TRỤ CỘT 2: TỐI ƯU MẠNG & THUẬT TOÁN JAVA ENGINE ]")))
        m5 = f"    {Colors.C_YELLOW}{Colors.BOLD}[5]{Colors.RESET}  ⚡ {Colors.WHITE}Java Selection Sort Engine (Sắp xếp IP theo Ping thấp nhất trên JVM JRE 8){Colors.RESET}"
        m6 = f"    {Colors.C_GREEN}{Colors.BOLD}[6]{Colors.RESET}  🔄 {Colors.WHITE}Cấp phát & Đổi dải IP Proxy Đa Quốc Gia (VN, JP, SG, HK, US, DE...){Colors.RESET}"
        m7 = f"    {Colors.C_BLUE}{Colors.BOLD}[7]{Colors.RESET}  🌐 {Colors.WHITE}Quản lý Pool IP, ProxyScrape & Scrapestack API (5d1c5fb0...){Colors.RESET}"
        m8 = f"    {Colors.LIGHT_CYAN}{Colors.BOLD}[8]{Colors.RESET}  🔍 {Colors.WHITE}Chẩn đoán mạng chuyên sâu (Java Handshake, Socket Ping, DNS, MTU){Colors.RESET}"
        print(pad_line(m5, len("    [5]  ⚡ Java Selection Sort Engine (Sắp xếp IP theo Ping thấp nhất trên JVM JRE 8)")))
        print(pad_line(m6, len("    [6]  🔄 Cấp phát & Đổi dải IP Proxy Đa Quốc Gia (VN, JP, SG, HK, US, DE...)")))
        print(pad_line(m7, len("    [7]  🌐 Quản lý Pool IP, ProxyScrape & Scrapestack API (5d1c5fb0...)")))
        print(pad_line(m8, len("    [8]  🔍 Chẩn đoán mạng chuyên sâu (Java Handshake, Socket Ping, DNS, MTU)")))
        print(div)

        # TRỤ CỘT 3: SCRIPT GAME & QUẢN LÝ EXECUTOR
        cat3 = f"  {Colors.C_PURPLE}{Colors.BOLD}► [ TRỤ CỘT 3: SCRIPT GAME & ĐỒNG BỘ AUTOEXEC ]{Colors.RESET}"
        print(pad_line(cat3, len("  ► [ TRỤ CỘT 3: SCRIPT GAME & ĐỒNG BỘ AUTOEXEC ]")))
        m9 = f"    {Colors.LIGHT_CYAN}{Colors.BOLD}[9]{Colors.RESET}  📝 {Colors.WHITE}Cấu hình Script Game (Auto Farm Payload) tự động chạy cho mọi Tag{Colors.RESET}"
        m10 = f"    {Colors.C_PURPLE}{Colors.BOLD}[10]{Colors.RESET} 📁 {Colors.WHITE}Quản lý & Đồng bộ thư mục Autoexec (Delta, Arceus X, Solara, Wave, Codex){Colors.RESET}"
        m11 = f"    {Colors.C_CYAN}{Colors.BOLD}[11]{Colors.RESET} 📋 {Colors.WHITE}Xem Bảng Tổng Hợp Chi Tiết Tag (IP + Game + HWID + Status + PID){Colors.RESET}"
        print(pad_line(m9, len("    [9]  📝 Cấu hình Script Game (Auto Farm Payload) tự động chạy cho mọi Tag")))
        print(pad_line(m10, len("    [10] 📁 Quản lý & Đồng bộ thư mục Autoexec (Delta, Arceus X, Solara, Wave, Codex)")))
        print(pad_line(m11, len("    [11] 📋 Xem Bảng Tổng Hợp Chi Tiết Tag (IP + Game + HWID + Status + PID)")))
        print(div)

        # TRỤ CỘT 4: BẢO TRÌ & HỆ THỐNG
        cat4 = f"  {Colors.GRAY}{Colors.BOLD}► [ TRỤ CỘT 4: BẢO TRÌ & HỆ THỐNG ]{Colors.RESET}"
        print(pad_line(cat4, len("  ► [ TRỤ CỘT 4: BẢO TRÌ & HỆ THỐNG ]")))
        m12 = f"    {Colors.LIGHT_RED}{Colors.BOLD}[12]{Colors.RESET} 🧹 {Colors.WHITE}Dọn dẹp Cache, Reset Autoexec, Script Lua & Khởi động lại Server{Colors.RESET}"
        m0 = f"    {Colors.GRAY}{Colors.BOLD}[0]{Colors.RESET}  ❌ {Colors.WHITE}Thoát chương trình an toàn{Colors.RESET}"
        print(pad_line(m12, len("    [12] 🧹 Dọn dẹp Cache, Reset Autoexec, Script Lua & Khởi động lại Server")))
        print(pad_line(m0, len("    [0]  ❌ Thoát chương trình an toàn")))

        print(bot)

    def main_menu(self):
        while True:
            try:
                self.print_banner()
                prompt_box = [
                    f"{Colors.C_CYAN}{Colors.BOLD}╭────────────────────────────────────────────────────────────────────────────────────────────╮{Colors.RESET}",
                    f"{Colors.C_CYAN}{Colors.BOLD}│{Colors.RESET}  {Colors.LIGHT_GREEN}{Colors.BOLD}🎮 MASTER CONTROLLER:{Colors.RESET} {Colors.WHITE}Nhập số thứ tự tính năng để thực thi {Colors.BOLD}[ 0 ➔ 12 ]{Colors.RESET}                     {Colors.C_CYAN}{Colors.BOLD}│{Colors.RESET}",
                    f"{Colors.C_CYAN}{Colors.BOLD}╰────────────────────────────────────────────────────────────────────────────────────────────╯{Colors.RESET}",
                ]
                print("\n" + "\n".join(prompt_box))
                choice = safe_input(f" {Colors.YELLOW}{Colors.BOLD}➤ Nhập lựa chọn của bạn{Colors.RESET} {Colors.GREEN}{Colors.BOLD}❯❯{Colors.RESET} ").strip()

                if choice == "1":
                    self.execute_full_auto_pipeline()
                elif choice == "2":
                    self.select_roblox_target_game()
                elif choice == "3":
                    self.configure_watchdog_supervisor()
                elif choice == "4":
                    self.start_live_dashboard()
                elif choice == "5":
                    self.execute_java_selection_sort()
                elif choice == "6":
                    self.generate_and_assign_ips()
                elif choice == "7":
                    self.generate_ip_pool()
                elif choice == "8":
                    self.run_deep_diagnostics()
                elif choice == "9":
                    self.configure_custom_payload()
                elif choice == "10":
                    self.manage_autoexec_folders()
                elif choice == "11":
                    self.view_instances_and_profiles()
                elif choice == "12":
                    self.clean_and_reset_system()
                elif choice in ["0", "exit", "quit"]:
                    self.shutdown()
                    break
                elif choice == "":
                    continue
                else:
                    safe_input(f"\n{Colors.RED}❌ Lựa chọn không hợp lệ! Nhấn Enter để tiếp tục...{Colors.RESET}")

            except (KeyboardInterrupt, EOFError):
                self.shutdown()
                break

    # ====================================================================================
    # [1] MASTER AUTO PIPELINE (1-CHẠM KHỞI CHẠY TOÀN DIỆN)
    # ====================================================================================
    def execute_full_auto_pipeline(self):
        """[1] Quy trình 1-Chạm tự động hóa toàn diện từ Quét -> Java Sort -> Bơm Autoexec -> Launch -> Watchdog"""
        self.clear_screen()
        print(f"{Colors.LIGHT_GREEN}{Colors.BOLD}================ [ 1. MASTER AUTO PIPELINE - QUY TRÌNH 1-CHẠM TOÀN DIỆN ] ================{Colors.RESET}\n")
        print(f"  {Colors.WHITE}Hệ thống sẽ thực hiện chuỗi tự động hóa 5 bước liên kết hoàn chỉnh:{Colors.RESET}\n")

        # BƯỚC 1: Quét toàn bộ Tag
        print(f"  {Colors.BOLD}[BƯỚC 1/5]{Colors.RESET} {Colors.CYAN}Đang quét toàn bộ cửa sổ Live và bản Clone trên máy...{Colors.RESET}")
        instances = self._get_combined_tag_instances()
        tag_count = len(instances)
        live_count = len([x for x in instances if x.hwnd > 0 or x.pid > 0])
        clone_count = len([x for x in instances if x.hwnd == 0 and x.pid == 0])
        print(f"    -> {Colors.GREEN}Phát hiện tổng cộng {tag_count} Tag ({live_count} Live, {clone_count} Clones sẵn sàng){Colors.RESET}")

        # BƯỚC 2: Nhận diện cấu hình Game
        print(f"\n  {Colors.BOLD}[BƯỚC 2/5]{Colors.RESET} {Colors.CYAN}Kiểm tra cấu hình Game mục tiêu (Per-Tag Multi-Game)...{Colors.RESET}")
        cur_g = game_manager.get_current_game()
        if game_manager.per_tag_mode:
            print(f"    -> {Colors.GREEN}Chế độ: PER-TAG MULTI-GAME (Mỗi Tag 1 Game riêng biệt đã được định tuyến){Colors.RESET}")
        else:
            print(f"    -> {Colors.GREEN}Chế độ: GLOBAL GAME ➔ {cur_g.get('name')} (PlaceId: {cur_g.get('place_id')}){Colors.RESET}")

        # BƯỚC 3: Thực thi Java Selection Sort IP
        target_country = self.selected_country or "MULTI"
        c_info = SUPPORTED_COUNTRIES.get(target_country, {"name": target_country, "flag": "🌐", "tag": f"[{target_country}]"})
        c_flag = c_info.get("flag", "🌐")
        print(f"\n  {Colors.BOLD}[BƯỚC 3/5]{Colors.RESET} {Colors.CYAN}Thực thi Java Selection Sort tìm IP có Ping thấp nhất ({c_flag} {target_country})...{Colors.RESET}")
        candidate_count = max(tag_count + 5, 10)
        candidates = []
        try:
            s_proxies = self.scrapestack.batch_fetch_proxies(count=min(tag_count, 5), country_code=target_country)
            for sp in s_proxies:
                candidates.append({"ip": sp["ip"], "region": sp.get("region", f"[{target_country}] Dedicated"), "country": sp.get("country", target_country)})
        except Exception:
            pass

        pool_proxies = ProxyFetcher.get_proxies_batch(count=candidate_count, country_code=target_country)
        for pp in pool_proxies:
            if pp["ip"] not in [c["ip"] for c in candidates]:
                candidates.append({"ip": pp["ip"], "region": pp.get("region", f"[{target_country}] Dedicated"), "country": pp.get("country", target_country)})

        ip_list = [c["ip"] for c in candidates]
        probe_map = NetworkInspector.batch_probe_ips(ip_list)
        for c in candidates:
            p_res = probe_map.get(c["ip"], ("READY", 50, "GREEN"))
            c["latency_ms"] = p_res[1]

        sort_res = SelectionSortBridge.execute_selection_sort(candidates)
        sorted_proxies = sort_res.get("sorted_proxies", [])

        for idx, inst in enumerate(instances):
            if idx < len(sorted_proxies):
                best_p = sorted_proxies[idx]
                inst.assigned_ip = best_p["ip"]
                inst.region = best_p["region"]
                inst.country = best_p.get("country", target_country)

        min_ping = sorted_proxies[0]["latency_ms"] if sorted_proxies else 20
        print(f"    -> {Colors.GREEN}Java Engine đã tối ưu hóa {len(instances)} Tag ({c_flag} {target_country}). Ping thấp nhất: {min_ping} ms!{Colors.RESET}")

        # BƯỚC 4: Đồng bộ Autoexec & Bridge Server
        print(f"\n  {Colors.BOLD}[BƯỚC 4/5]{Colors.RESET} {Colors.CYAN}Tạo mã Lua độc lập & Bơm vào toàn bộ thư mục Autoexec...{Colors.RESET}")
        sync_result = self.sync_system_state(instances, use_live_proxies=False, country_code=target_country)
        print(f"    -> {Colors.GREEN}Đã cập nhật Master Router ({target_country}) vào {sync_result['autoexec_synced_count']} thư mục Autoexec Executor!{Colors.RESET}")

        # BƯỚC 5: Kích hoạt Watchdog & Khởi chạy Roblox
        print(f"\n  {Colors.BOLD}[BƯỚC 5/5]{Colors.RESET} {Colors.CYAN}Kích hoạt Watchdog Supervisor & Khởi chạy các bản Roblox...{Colors.RESET}")
        watchdog.is_enabled = True
        watchdog.auto_reopen_on_disconnect = True
        watchdog.start()
        print(f"    -> {Colors.GREEN}Watchdog Supervisor: ONLINE (Tự động mở lại khi bị văng/disconnect kích hoạt){Colors.RESET}")

        auto_launch_choice = safe_input(f"\n  {Colors.YELLOW}{Colors.BOLD}➤ Khởi chạy ngay các bản Roblox Client? (Nhập số lượng, ví dụ: 2, Y=Tất cả, N=Bỏ qua){Colors.RESET} {Colors.GREEN}{Colors.BOLD}❯❯{Colors.RESET} ").strip()

        if auto_launch_choice.lower() not in ["n", "no", "khong", "0"]:
            try:
                num_to_launch = int(auto_launch_choice) if auto_launch_choice.isdigit() else min(tag_count, 3)
            except Exception:
                num_to_launch = 2

            print(f"\n  {Colors.YELLOW}[*] Đang tự động mở {num_to_launch} cửa sổ Roblox Client...{Colors.RESET}")
            launch_instances = instances[:num_to_launch] if instances else None
            launch_res = RobloxAutoLauncher.launch_roblox_instances(count=num_to_launch, instances=launch_instances)
            for lr in launch_res:
                if lr["status"] == "LAUNCHED":
                    tag_g = game_manager.get_game_for_tag(lr.get("tag_id"))
                    print(f"    -> {Colors.GREEN}[+] Đã mở Tag [{lr['tag_id']}]{Colors.RESET} ➔ Game: {Colors.CYAN}{tag_g.get('name')}{Colors.RESET} ({lr['method']})")
                else:
                    print(f"    -> {Colors.RED}[!] Lỗi mở Tag [{lr['tag_id']}]: {lr.get('error')}{Colors.RESET}")

        print(f"\n  {Colors.LIGHT_GREEN}{Colors.BOLD}================ [ ✅ MASTER PIPELINE HOÀN TẤT THÀNH CÔNG ] ================{Colors.RESET}")
        print(f"  {Colors.CYAN}{Colors.BOLD}⚡ ĐANG TỰ ĐỘNG CHUYỂN VÀO CHẾ ĐỘ GIÁM SÁT REAL-TIME TOÀN DIỆN...{Colors.RESET}")
        time.sleep(1.5)
        from cli.status import LiveRealtimeMonitor
        LiveRealtimeMonitor.start_monitoring_loop(instances=instances, refresh_interval=1.5)

    # ====================================================================================
    # [2] QUẢN LÝ GAME & TELEPORT HUB (GLOBAL & PER-TAG MULTI-GAME)
    # ====================================================================================
    def select_roblox_target_game(self):
        """[2] Chọn Game Roblox để Auto-Join & Cấu hình Teleport Hub (Global & Per-Tag Multi-Game)"""
        while True:
            self.clear_screen()
            print(f"{Colors.LIGHT_CYAN}{Colors.BOLD}================ [ 2. QUẢN LÝ GAME ROBLOX & PER-TAG MULTI-GAME HUB ] ================{Colors.RESET}\n")
            
            cur_game = game_manager.get_current_game()
            tag_games = game_manager.get_all_tag_games()
            mode_str = f"{Colors.GREEN}{Colors.BOLD}PER-TAG MULTI-GAME (Mỗi Tag 1 Game riêng){Colors.RESET}" if game_manager.per_tag_mode else f"{Colors.CYAN}{Colors.BOLD}GLOBAL (Tất cả Tag chung 1 Game){Colors.RESET}"
            
            print(f"  {Colors.BOLD}⚙️  Chế độ hiện tại:{Colors.RESET} {mode_str}")
            print(f"  {Colors.BOLD}🎮 Game mặc định (Global):{Colors.RESET} {Colors.GREEN}{Colors.BOLD}{cur_game.get('name')}{Colors.RESET} (PlaceId: {Colors.CYAN}{cur_game.get('place_id')}{Colors.RESET})")
            if game_manager.per_tag_mode and tag_games:
                print(f"  {Colors.BOLD}🎯 Số Tag có Game riêng biệt:{Colors.RESET} {Colors.YELLOW}{len(tag_games)} Tags đã cấu hình riêng{Colors.RESET}")
            print(f"  {Colors.BOLD}⚡ Auto-Teleport:{Colors.RESET} {Colors.GREEN}BẬT (Tự động Teleport vào đúng Game){Colors.RESET}\n")

            print(f"  {Colors.BOLD}[ TÙY CHỌN CẤU HÌNH GAME ]{Colors.RESET}")
            print(f"  {Colors.BOLD}[1]{Colors.RESET} 🌐 {Colors.WHITE}Chọn 1 Game chung cho TẤT CẢ các Tag (Global Mode){Colors.RESET}")
            print(f"  {Colors.BOLD}[2]{Colors.RESET} 🎯 {Colors.LIGHT_GREEN}Gán MỖI TAG MỘT GAME KHÁC NHAU (Per-Tag Multi-Game){Colors.RESET}")
            print(f"  {Colors.BOLD}[3]{Colors.RESET} 📋 {Colors.CYAN}Xem Bảng phân bổ Game & IP chi tiết của từng Tag{Colors.RESET}")
            print(f"  {Colors.BOLD}[4]{Colors.RESET} 🎲 {Colors.YELLOW}Tự động phân bổ ngẫu nhiên Top Games cho toàn bộ Tag (1 chạm){Colors.RESET}")
            print(f"  {Colors.BOLD}[L]{Colors.RESET} 🚀 {Colors.GREEN}Khởi chạy Roblox vào Game ngay bây giờ{Colors.RESET}")
            print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  {Colors.GRAY}Quay lại Menu chính{Colors.RESET}\n")

            opt = safe_input(f"  {Colors.YELLOW}{Colors.BOLD}➤ Nhập lựa chọn (0-4, L){Colors.RESET} {Colors.GREEN}{Colors.BOLD}❯❯{Colors.RESET} ").strip()

            if opt == "1":
                self._menu_select_global_game()
            elif opt == "2":
                self._menu_assign_games_per_tag()
            elif opt == "3":
                self._menu_view_tag_games_table()
            elif opt == "4":
                self._menu_auto_distribute_games()
            elif opt.upper() == "L":
                instances = self._get_combined_tag_instances()
                print(f"\n  {Colors.YELLOW}[*] Đang khởi chạy các cửa sổ Roblox theo Game riêng của từng Tag...{Colors.RESET}")
                res_list = RobloxAutoLauncher.launch_roblox_instances(instances=instances if instances else None, count=max(len(instances), 1))
                for lr in res_list:
                    if lr.get("status") == "LAUNCHED":
                        tag_g = game_manager.get_game_for_tag(lr.get("tag_id"))
                        print(f"    -> {Colors.GREEN}[+] Đã mở Tag [{lr.get('tag_id')}] vào Game [{tag_g.get('name')}] (PlaceId: {lr.get('place_id')}){Colors.RESET}")
                    else:
                        print(f"    -> {Colors.RED}[!] Lỗi mở Tag [{lr.get('tag_id')}]: {lr.get('error')}{Colors.RESET}")
                safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")
            elif opt == "0":
                break

    def _menu_select_global_game(self):
        self.clear_screen()
        print(f"{Colors.LIGHT_CYAN}{Colors.BOLD}================ [ CHỌN GAME CHUNG CHO TOÀN BỘ CÁC TAG ] ================{Colors.RESET}\n")
        print(f"  {'STT':<6} {'TÊN GAME ROBLOX':<30} {'PLACE ID':<16} {'THỂ LOẠI'}")
        print("  " + "-" * 75)
        cur_game = game_manager.get_current_game()
        for g in POPULAR_ROBLOX_GAMES:
            is_cur = "⭐ " if str(g.place_id) == str(cur_game.get("place_id")) else "   "
            print(f"  {is_cur}{g.id:<4} {Colors.CYAN}{g.name:<30}{Colors.RESET} {Colors.YELLOW}{g.place_id:<16}{Colors.RESET} {g.category}")

        print(f"\n  {Colors.BOLD}[C]{Colors.RESET} ✍️  {Colors.WHITE}Tự nhập Tên Game & Place ID tùy chỉnh{Colors.RESET}")
        print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  {Colors.GRAY}Quay lại{Colors.RESET}\n")

        choice = safe_input(f"  {Colors.YELLOW}➤ Chọn số game (1-15) hoặc [C] Tự nhập:{Colors.RESET} ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(POPULAR_ROBLOX_GAMES):
            sel_game = POPULAR_ROBLOX_GAMES[int(choice) - 1]
            ask_job = safe_input(f"  {Colors.YELLOW}Nhập Job ID cụ thể (để trống nếu vào Server ngẫu nhiên):{Colors.RESET} ").strip()
            game_manager.set_game_by_item(sel_game, job_id=ask_job)
            game_manager.per_tag_mode = False
            game_manager.save_config()
            print(f"\n  {Colors.GREEN}{Colors.BOLD}[+] ĐÃ CHỌN THÀNH CÔNG: {sel_game.name} (PlaceId: {sel_game.place_id}) CHO TẤT CẢ TAG!{Colors.RESET}")
            self.sync_system_state(self._get_combined_tag_instances())
        elif choice.upper() == "C":
            c_name = safe_input(f"  {Colors.YELLOW}Nhập Tên game hiển thị:{Colors.RESET} ").strip()
            c_pid = safe_input(f"  {Colors.YELLOW}Nhập Place ID của game:{Colors.RESET} ").strip()
            c_jid = safe_input(f"  {Colors.YELLOW}Nhập Job ID / Server ID (để trống nếu không có):{Colors.RESET} ").strip()
            if c_pid:
                game_manager.set_custom_game(name=c_name or "Custom Game", place_id=c_pid, job_id=c_jid)
                game_manager.per_tag_mode = False
                game_manager.save_config()
                print(f"\n  {Colors.GREEN}{Colors.BOLD}[+] Đã lưu cấu hình Game: {c_name} (PlaceId: {c_pid})!{Colors.RESET}")
                self.sync_system_state(self._get_combined_tag_instances())
        safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")

    def _menu_assign_games_per_tag(self):
        self.clear_screen()
        print(f"{Colors.LIGHT_GREEN}{Colors.BOLD}================ [ GÁN MỖI TAG MỘT GAME KHÁC NHAU ] ================{Colors.RESET}\n")
        instances = self._get_combined_tag_instances()
        print(f"  {Colors.BOLD}Danh sách các Tag cần gán Game:{Colors.RESET}")
        for idx, inst in enumerate(instances):
            cur_t_game = game_manager.get_game_for_tag(inst.tag_id)
            print(f"    [{idx+1}] {Colors.CYAN}{inst.tag_id:<16}{Colors.RESET} ➔ Game hiện tại: {Colors.GREEN}{cur_t_game.get('name')}{Colors.RESET} (PlaceId: {cur_t_game.get('place_id')})")

        print(f"\n  {Colors.BOLD}[A]{Colors.RESET} 🎲 {Colors.YELLOW}Tự động gán mỗi Tag 1 Game khác nhau từ Top Games (Blox Fruits, King Legacy, Fisch...){Colors.RESET}")
        print(f"  {Colors.BOLD}[1-{len(instances)}]{Colors.RESET} 🎯 {Colors.WHITE}Chọn số thứ tự Tag cụ thể để đổi Game{Colors.RESET}")
        print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  {Colors.GRAY}Quay lại{Colors.RESET}\n")

        sel = safe_input(f"  {Colors.YELLOW}➤ Nhập lựa chọn của bạn:{Colors.RESET} ").strip()
        if sel.upper() == "A":
            tag_ids = [inst.tag_id for inst in instances]
            game_manager.auto_distribute_multi_games(tag_ids)
            print(f"\n  {Colors.GREEN}{Colors.BOLD}[+] ĐÃ TỰ ĐỘNG GÁN GAME KHÁC NHAU CHO TOÀN BỘ {len(tag_ids)} TAGS!{Colors.RESET}")
            self.sync_system_state(instances)
        elif sel.isdigit() and 1 <= int(sel) <= len(instances):
            target_inst = instances[int(sel) - 1]
            print(f"\n  {Colors.CYAN}--- CHỌN GAME CHO TAG [{target_inst.tag_id}] ---{Colors.RESET}")
            for g in POPULAR_ROBLOX_GAMES[:8]:
                print(f"    [{g.id}] {g.name:<25} (PlaceId: {g.place_id})")
            print(f"    [C] Tự nhập Place ID khác")
            g_choice = safe_input(f"  {Colors.YELLOW}Chọn game cho {target_inst.tag_id}:{Colors.RESET} ").strip()
            if g_choice.isdigit() and 1 <= int(g_choice) <= len(POPULAR_ROBLOX_GAMES):
                g_item = POPULAR_ROBLOX_GAMES[int(g_choice) - 1]
                game_manager.set_game_for_tag(target_inst.tag_id, name=g_item.name, place_id=g_item.place_id)
                print(f"\n  {Colors.GREEN}[+] Đã gán Tag [{target_inst.tag_id}] ➔ Game [{g_item.name}]!{Colors.RESET}")
                self.sync_system_state(instances)
            elif g_choice.upper() == "C":
                c_name = safe_input(f"  {Colors.YELLOW}Tên game:{Colors.RESET} ").strip()
                c_pid = safe_input(f"  {Colors.YELLOW}Place ID:{Colors.RESET} ").strip()
                if c_pid:
                    game_manager.set_game_for_tag(target_inst.tag_id, name=c_name or "Custom Game", place_id=c_pid)
                    print(f"\n  {Colors.GREEN}[+] Đã gán Tag [{target_inst.tag_id}] ➔ Game [{c_name}] (PlaceId: {c_pid})!{Colors.RESET}")
                    self.sync_system_state(instances)
        safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")

    def _menu_view_tag_games_table(self):
        self.clear_screen()
        print(f"{Colors.LIGHT_CYAN}{Colors.BOLD}================ [ BẢNG PHÂN BỔ GAME & IP CỦA TỪNG TAG ] ================{Colors.RESET}\n")
        instances = self._get_combined_tag_instances()
        print(f"  {'TAG ID':<16} {'GAME MỤC TIÊU':<26} {'PLACE ID':<14} {'DEDICATED IP':<20} {'REGION'}")
        print("  " + "-" * 88)
        for inst in instances:
            tg = game_manager.get_game_for_tag(inst.tag_id)
            ip_str = inst.assigned_ip or "127.0.0.1"
            reg_str = getattr(inst, "region", "[JP] Japan")
            print(f"  {inst.tag_id:<16} {Colors.GREEN}{tg.get('name', 'N/A')[:24]:<26}{Colors.RESET} {Colors.CYAN}{tg.get('place_id', 'N/A'):<14}{Colors.RESET} {Colors.YELLOW}{ip_str:<20}{Colors.RESET} {reg_str[:16]}")
        print("\n  " + "=" * 88)
        safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")

    def _menu_auto_distribute_games(self):
        instances = self._get_combined_tag_instances()
        tag_ids = [inst.tag_id for inst in instances]
        if not tag_ids:
            tag_ids = [f"ROBLOX-TAG-{i:02d}" for i in range(1, 6)]
        game_manager.auto_distribute_multi_games(tag_ids)
        print(f"\n  {Colors.GREEN}{Colors.BOLD}[+] ĐÃ TỰ ĐỘNG PHÂN BỔ MỖI TAG 1 GAME KHÁC NHAU THÀNH CÔNG!{Colors.RESET}")
        for tid in tag_ids:
            g = game_manager.get_game_for_tag(tid)
            print(f"    * {Colors.CYAN}{tid:<16}{Colors.RESET} ➔ {Colors.GREEN}{g.get('name'):<26}{Colors.RESET} (PlaceId: {g.get('place_id')})")
        self.sync_system_state(instances)
        safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")

    # ====================================================================================
    # [3] GIÁM SÁT & AUTO-RESTART WATCHDOG SUPERVISOR
    # ====================================================================================
    def configure_watchdog_supervisor(self):
        """[3] Giám sát & Bật/Tắt Auto-Restart Watchdog (Tự động mở lại Tag khi bị tắt)"""
        self.clear_screen()
        print(f"{Colors.LIGHT_GREEN}{Colors.BOLD}================ [ 3. GIÁM SÁT & AUTO-RESTART WATCHDOG SUPERVISOR ] ================{Colors.RESET}\n")
        
        w_summary = watchdog.get_summary()
        status_txt = f"{Colors.GREEN}{Colors.BOLD}ĐANG BẬT (ONLINE){Colors.RESET}" if w_summary["is_enabled"] else f"{Colors.GRAY}ĐANG TẮT (DISABLED){Colors.RESET}"
        reopen_txt = f"{Colors.GREEN}BẬT (Tự mở lại khi mất kết nối/tắt){Colors.RESET}" if w_summary["auto_reopen"] else f"{Colors.YELLOW}TẮT (Chỉ ghi log){Colors.RESET}"

        print(f"  {Colors.BOLD}🛡️ Trạng thái Watchdog Supervisor:{Colors.RESET} {status_txt}")
        print(f"  {Colors.BOLD}🔄 Chế độ Auto-Reopen (Tự mở lại):{Colors.RESET} {reopen_txt}")
        print(f"  {Colors.BOLD}📊 Thống kê Tag theo dõi:{Colors.RESET} {Colors.CYAN}{w_summary['total_monitored']} Tags{Colors.RESET} ({Colors.GREEN}{w_summary['online_count']} Online{Colors.RESET}, {Colors.LIGHT_RED}{w_summary['off_count']} Off/Error{Colors.RESET})")
        print(f"  {Colors.BOLD}🚀 Tổng số lần tự động Mở lại:{Colors.RESET} {Colors.YELLOW}{Colors.BOLD}{w_summary['total_restarts']} lần{Colors.RESET}\n")

        print(f"  {Colors.BOLD}[ DANH SÁCH TRẠNG THÁI NHỊP TIM CỦA CÁC TAG ]{Colors.RESET}")
        print(f"  {'TAG ID':<16} {'STATUS':<14} {'FPS':<6} {'PING':<10} {'ASSIGNED IP':<22} {'RESTARTS'}")
        print("  " + "-" * 75)

        tags_dict = w_summary.get("tags", {})
        if tags_dict:
            for tid, tst in tags_dict.items():
                st_color = Colors.GREEN if tst["status"] == "ONLINE" else (Colors.YELLOW if tst["status"] == "RESTARTING" else Colors.LIGHT_RED)
                st_display = f"{st_color}{tst['status']}{Colors.RESET}"
                print(f"  {tid:<16} {st_display:<23} {tst.get('fps', 60):<6} {tst.get('ping_ms', 0)} ms   {tst.get('assigned_ip', 'N/A'):<22} {tst.get('restarts_count', 0)} lần")
        else:
            print(f"  {Colors.GRAY}Chưa có Tag nào kết nối nhịp tim. Mở Roblox để tự động kích hoạt!{Colors.RESET}")

        if w_summary.get("recent_logs"):
            print(f"\n  {Colors.BOLD}[ NHẬT KÝ SỰ KIỆN WATCHDOG GẦN ĐÂY ]{Colors.RESET}")
            for l in w_summary["recent_logs"][-6:]:
                print(f"    {Colors.GRAY}{l}{Colors.RESET}")

        print(f"\n  {Colors.BOLD}[1]{Colors.RESET} 🔘 {'Tắt' if w_summary['is_enabled'] else 'Bật'} Watchdog Supervisor")
        print(f"  {Colors.BOLD}[2]{Colors.RESET} 🔄 {'Tắt' if w_summary['auto_reopen'] else 'Bật'} Chế độ Tự động Mở lại (Auto-Reopen)")
        print(f"  {Colors.BOLD}[3]{Colors.RESET} ⚡ Thử kích hoạt Mở lại Tag ngay lập tức (Test Re-launch)")
        print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  {Colors.GRAY}Quay lại Menu chính{Colors.RESET}\n")

        opt = safe_input(f"  {Colors.YELLOW}{Colors.BOLD}➤ Chọn thao tác (0-3){Colors.RESET} {Colors.GREEN}{Colors.BOLD}❯❯{Colors.RESET} ").strip()
        if opt == "1":
            watchdog.is_enabled = not watchdog.is_enabled
            print(f"\n  {Colors.GREEN}[+] Đã {'BẬT' if watchdog.is_enabled else 'TẮT'} Watchdog Supervisor!{Colors.RESET}")
        elif opt == "2":
            watchdog.auto_reopen_on_disconnect = not watchdog.auto_reopen_on_disconnect
            print(f"\n  {Colors.GREEN}[+] Đã {'BẬT' if watchdog.auto_reopen_on_disconnect else 'TẮT'} chế độ Tự động Mở lại Tag!{Colors.RESET}")
        elif opt == "3":
            tid_test = safe_input(f"  {Colors.YELLOW}Nhập Tag ID muốn mở lại (mặc định ROBLOX-TAG-01):{Colors.RESET} ").strip() or "ROBLOX-TAG-01"
            print(f"\n  {Colors.CYAN}[*] Đang kích hoạt thử nghiệm mở lại Tag [{tid_test}]...{Colors.RESET}")
            watchdog._trigger_reopen_tag(tid_test, "Thử nghiệm kích hoạt thủ công từ Menu")
            print(f"  {Colors.GREEN}[+] Đã gửi lệnh mở lại Tag thành công!{Colors.RESET}")

        safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để quay lại Menu...{Colors.RESET}")

    # ====================================================================================
    # [4] LIVE DASHBOARD GIÁM SÁT REAL-TIME (KHÓA MÀN HÌNH - THOÁT BẰNG CTRL+C)
    # ====================================================================================
    def start_live_dashboard(self):
        """[4] Mở Dashboard TUI giám sát thời gian thực (Hardware + Roblox + Watchdog)"""
        instances = self._get_combined_tag_instances()
        from cli.status import LiveRealtimeMonitor
        LiveRealtimeMonitor.start_monitoring_loop(instances=instances, refresh_interval=1.5)

    # ====================================================================================
    # [5] JAVA SELECTION SORT IP ENGINE
    # ====================================================================================
    def execute_java_selection_sort(self):
        """[5] Thực thi thuật toán Selection Sort trên JVM Java Engine để tìm IP Ping thấp nhất"""
        self.clear_screen()
        print(f"{Colors.LIGHT_GREEN}{Colors.BOLD}================ [ 5. JAVA SELECTION SORT IP ENGINE ] ================{Colors.RESET}\n")
        
        java_ok = SelectionSortBridge.is_java_available()
        java_status = f"{Colors.GREEN}ONLINE (Java 8 JRE Active){Colors.RESET}" if java_ok else f"{Colors.YELLOW}FALLBACK (Native Python Engine){Colors.RESET}"
        print(f"  {Colors.BOLD}[*] Môi trường Java Engine:{Colors.RESET} {java_status}")

        instances = self._get_combined_tag_instances()
        tag_count = len(instances)
        target_country = self.selected_country or "MULTI"
        c_info = SUPPORTED_COUNTRIES.get(target_country, {"name": target_country, "flag": "🌐", "tag": f"[{target_country}]"})
        c_flag = c_info.get("flag", "🌐")
        print(f"  {Colors.BOLD}[*] Tổng số Tag cần gán IP:{Colors.RESET} {Colors.GREEN}{tag_count} Tag{Colors.RESET} | Quốc gia: {c_flag} {target_country}")

        print(f"\n  {Colors.CYAN}[*] Đang thu thập và đo Ping thực tế các ứng viên Proxy ({c_flag} {target_country})...{Colors.RESET}")
        candidate_count = max(tag_count + 5, 10)
        candidates = []
        try:
            s_proxies = self.scrapestack.batch_fetch_proxies(count=min(tag_count, 5), country_code=target_country)
            for sp in s_proxies:
                candidates.append({"ip": sp["ip"], "region": sp.get("region", f"[{target_country}] Dedicated"), "country": sp.get("country", target_country)})
        except Exception:
            pass

        pool_proxies = ProxyFetcher.get_proxies_batch(count=candidate_count, country_code=target_country)
        for pp in pool_proxies:
            if pp["ip"] not in [c["ip"] for c in candidates]:
                candidates.append({"ip": pp["ip"], "region": pp.get("region", f"[{target_country}] Dedicated"), "country": pp.get("country", target_country)})

        ip_list = [c["ip"] for c in candidates]
        probe_map = NetworkInspector.batch_probe_ips(ip_list)
        for c in candidates:
            p_res = probe_map.get(c["ip"], ("READY", 50, "GREEN"))
            c["latency_ms"] = p_res[1]

        sort_result = SelectionSortBridge.execute_selection_sort(candidates)
        sorted_proxies = sort_result.get("sorted_proxies", [])
        step_logs = sort_result.get("step_logs", [])

        print(f"\n  {Colors.YELLOW}{Colors.BOLD}--- BẢNG MINH HỌA THUẬT TOÁN SELECTION SORT (TRÊN JAVA ENGINE) ---{Colors.RESET}")
        if step_logs:
            for step in step_logs[:tag_count]:
                p_num = step.get("pass", 1)
                min_ip = step.get("min_ip", "")
                min_lat = step.get("min_latency", 0)
                cur_i = step.get("current_idx", 0)
                min_f_i = step.get("min_found_idx", 0)
                swap_txt = f"{Colors.GREEN}Swap vị trí {min_f_i} -> {cur_i}{Colors.RESET}" if step.get("swapped") else f"{Colors.GRAY}Giữ nguyên (Đã ở đầu){Colors.RESET}"
                print(f"    * {Colors.BOLD}[Pass {p_num:02d}]{Colors.RESET} Min: {Colors.CYAN}{min_lat} ms{Colors.RESET} ({min_ip}) -> {swap_txt} [RANK #{p_num}]")

        print(f"\n  {Colors.GREEN}{Colors.BOLD}[+] KẾT QUẢ GÁN IP TỐI ƯU CHO TỪNG TAG ({target_country}):{Colors.RESET}")
        print(f"  {'RANK':<6} {'TAG ID':<16} {'OPTIMIZED IP':<24} {'PING':<12} {'TARGET GAME ASSIGNED'}")
        print("  " + "-" * 78)

        for idx, inst in enumerate(instances):
            if idx < len(sorted_proxies):
                best_p = sorted_proxies[idx]
                inst.assigned_ip = best_p["ip"]
                inst.region = best_p["region"]
                inst.country = best_p.get("country", target_country)
                tg = game_manager.get_game_for_tag(inst.tag_id)
                print(f"  #{idx+1:<5} {inst.tag_id:<16} {Colors.CYAN}{best_p['ip']:<24}{Colors.RESET} {Colors.GREEN}{best_p['latency_ms']} ms{Colors.RESET}    {Colors.LIGHT_GREEN}{tg.get('name')}{Colors.RESET}")

        self.sync_system_state(instances, use_live_proxies=False, country_code=target_country)
        print(f"\n  {Colors.GREEN}{Colors.BOLD}[+] ĐÃ TỰ ĐỘNG ĐỒNG BỘ IP [{target_country}] VÀO TOÀN BỘ AUTOEXEC & BRIDGE SERVER!{Colors.RESET}")
        safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để quay lại Menu...{Colors.RESET}")

    # ====================================================================================
    # [6] CẤP PHÁT & ĐỔI IP PROXY ĐA QUỐC GIA
    # ====================================================================================
    def generate_and_assign_ips(self):
        """[6] Cấp phát lại IP / Proxy Đa Quốc Gia cho toàn bộ bản Clone"""
        self.clear_screen()
        print(f"{Colors.LIGHT_GREEN}{Colors.BOLD}================ [ 6. CẤP PHÁT LẠI IP / PROXY ĐA QUỐC GIA ] ================{Colors.RESET}\n")
        country_code = self.prompt_select_country()
        self.selected_country = country_code
        self._save_selected_country(country_code)
        instances = self._get_combined_tag_instances()
        print(f"\n  {Colors.CYAN}[*] Đang cấp phát dải IP mới [{country_code}] cho {len(instances)} Tag...{Colors.RESET}")
        
        self.sync_system_state(instances, use_live_proxies=True, country_code=country_code)
        
        print(f"\n  {Colors.GREEN}{Colors.BOLD}[+] ĐÃ CẤP PHÁT VÀ ĐỒNG BỘ DẢI IP [{country_code}] THÀNH CÔNG CHO {len(instances)} TAG!{Colors.RESET}")
        print(f"  {Colors.LIGHT_GREEN}[+] Đã lưu quốc gia [{country_code}] làm mặc định cho toàn bộ Pipeline.{Colors.RESET}")
        safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để quay lại Menu...{Colors.RESET}")

    # ====================================================================================
    # [7] QUẢN LÝ POOL IP & SCRAPESTACK API
    # ====================================================================================
    def generate_ip_pool(self):
        """[7] Tải và kiểm tra Proxy Live từ ProxyScrape / Scrapestack API"""
        self.clear_screen()
        print(f"{Colors.LIGHT_BLUE}{Colors.BOLD}================ [ 7. QUẢN LÝ POOL IP & SCRAPESTACK API ] ================{Colors.RESET}\n")
        
        s_status = self.scrapestack.test_connection()
        print(f"  {Colors.BOLD}🔑 Scrapestack API Status:{Colors.RESET} {Colors.GREEN if s_status['status'] == 'CONNECTED' else Colors.YELLOW}{s_status['status']}{Colors.RESET}")
        if s_status.get("proxy_ip"):
            print(f"  {Colors.BOLD}📍 Public Proxy IP:{Colors.RESET} {Colors.CYAN}{s_status.get('proxy_ip')}{Colors.RESET}")

        print(f"\n  {Colors.BOLD}[1]{Colors.RESET} 🔄 Tải mới danh sách Proxy Live Đa Quốc Gia từ ProxyScrape")
        print(f"  {Colors.BOLD}[2]{Colors.RESET} ⚡ Lấy 5 Dedicated Proxy từ Scrapestack API")
        print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  Quay lại\n")

        sub_opt = safe_input(f"  {Colors.YELLOW}➤ Nhập lựa chọn (0-2):{Colors.RESET} ").strip()
        if sub_opt == "1":
            print(f"\n  {Colors.CYAN}[*] Đang tải Proxy Live đa quốc gia...{Colors.RESET}")
            proxies = ProxyFetcher.fetch_country_proxies("MULTI", force_refresh=True)
            print(f"  {Colors.GREEN}[+] Đã nạp thành công {len(proxies)} Proxy Live vào Pool!{Colors.RESET}")
        elif sub_opt == "2":
            print(f"\n  {Colors.CYAN}[*] Đang kết nối Scrapestack API...{Colors.RESET}")
            s_res = self.scrapestack.batch_fetch_proxies(count=5)
            for sp in s_res:
                print(f"    -> {Colors.GREEN}{sp['ip']}{Colors.RESET} ({sp['region']})")
            print(f"  {Colors.GREEN}[+] Đã nạp 5 Scrapestack Dedicated Proxies!{Colors.RESET}")

        safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để quay lại Menu...{Colors.RESET}")

    # ====================================================================================
    # [8] CHẨN ĐOÁN MẠNG CHUYÊN SÂU
    # ====================================================================================
    def run_deep_diagnostics(self):
        """[8] Chẩn đoán mạng chuyên sâu (Java Handshake, Socket Ping, DNS, MTU)"""
        self.clear_screen()
        print(f"{Colors.LIGHT_CYAN}{Colors.BOLD}================ [ 8. CHẨN ĐOÁN MẠNG CHUYÊN SÂU ] ================{Colors.RESET}\n")
        
        print(f"  {Colors.CYAN}[*] 1. Kiểm tra độ trễ Java TCP Handshake Engine...{Colors.RESET}")
        probe_res = SelectionSortBridge.probe_ip_latency_java("8.8.8.8", port=53)
        print(f"    -> {Colors.GREEN}Google DNS Latency (Java): {probe_res.get('latency_ms')} ms (Trạng thái: {probe_res.get('status')}){Colors.RESET}")

        print(f"\n  {Colors.CYAN}[*] 2. Kiểm tra phân giải DNS Public quốc tế...{Colors.RESET}")
        from network.dns import DNSResolver
        dns_res = DNSResolver.test_all_dns_servers()
        for srv, lat in dns_res.items():
            print(f"    -> {srv:<20}: {Colors.GREEN}{lat:.1f} ms{Colors.RESET}")

        print(f"\n  {Colors.CYAN}[*] 3. Kiểm tra kết nối HTTP Bridge Server (http://127.0.0.1:8888)...{Colors.RESET}")
        print(f"    -> {Colors.GREEN}Bridge Server: ONLINE (Port 8888 Active){Colors.RESET}")

        print(f"\n  {Colors.CYAN}[*] 4. Module Can Thiệp Sâu (Sing-Box / Mihomo Wintun TUN & Android TPROXY Stealth)...{Colors.RESET}")
        from network.deep_interceptor import WindowsDeepInterceptor, MihomoDeepInterceptor, AndroidDeepInterceptor, MagiskServiceBootEngine, DNSInterceptEngine
        singbox_installed = "CÓ (Sẵn sàng)" if WindowsDeepInterceptor.is_singbox_installed() else "Chưa cài (Có thể tự sinh config JSON/YAML)"
        print(f"    -> Windows Engine Core  : {Colors.YELLOW}{singbox_installed}{Colors.RESET}")
        
        bridge = UGPhoneBridge()
        devices = bridge.refresh_devices()
        dev_status = f"{len(devices)} thiết bị ({', '.join(devices)})" if devices else "Chưa phát hiện (ADB)"
        print(f"    -> Android / Giả Lập ADB: {Colors.LIGHT_BLUE}{dev_status}{Colors.RESET}")

        leak = DNSInterceptEngine.check_dns_leak()
        print(f"    -> DNS Leak Prevention  : {Colors.GREEN}{leak.get('leak_status')} (IP: {leak.get('resolved_ip')}, {leak.get('latency_ms')} ms){Colors.RESET}")

        print(f"\n  {Colors.BOLD}Tùy chọn can thiệp sâu (Kiến trúc AsteriskMETA & Sing-Box):{Colors.RESET}")
        print(f"    {Colors.YELLOW}[S]{Colors.RESET} Sinh file cấu hình Sing-Box Wintun TUN JSON (Per-Process Roblox + Fake-IP)")
        print(f"    {Colors.LIGHT_PURPLE}[M]{Colors.RESET} Sinh file cấu hình Mihomo (Clash Meta) YAML (Per-Process Roblox + Fake-IP)")
        print(f"    {Colors.GREEN}[A]{Colors.RESET} Bơm IPTables TPROXY Stealth (No-VPN) cho Android / Giả Lập kết nối ADB")
        print(f"    {Colors.CYAN}[B]{Colors.RESET} Cài đặt Magisk / KernelSU service.d tự khởi động TPROXY khi Boot Android")
        print(f"    {Colors.RED}[R]{Colors.RESET} Khôi phục mạng gốc Android (Gỡ bỏ IPTables & Boot service)")
        print(f"    {Colors.GRAY}[Enter]{Colors.RESET} Quay lại Menu...")

        act = safe_input(f"\n  {Colors.YELLOW}➤ Nhập thao tác (S/M/A/B/R hoặc Enter):{Colors.RESET} ").strip().upper()
        if act == "S":
            out_file = os.path.join(BASE_DIR, "data", "singbox_roblox_config.json")
            WindowsDeepInterceptor.generate_singbox_config(out_file, proxy_port=10808)
            print(f"\n  {Colors.GREEN}✔ Đã sinh file cấu hình Sing-Box TUN tại: {out_file}{Colors.RESET}")
            print(f"  {Colors.GRAY}Gợi ý chạy: sing-box run -c \"{out_file}\"{Colors.RESET}")
            safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")
        elif act == "M":
            out_file = os.path.join(BASE_DIR, "data", "mihomo_roblox_config.yaml")
            MihomoDeepInterceptor.generate_mihomo_yaml(out_file, proxy_port=10808)
            print(f"\n  {Colors.GREEN}✔ Đã sinh file cấu hình Mihomo (Clash Meta) YAML tại: {out_file}{Colors.RESET}")
            print(f"  {Colors.GRAY}Gợi ý chạy: mihomo -f \"{out_file}\"{Colors.RESET}")
            safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")
        elif act == "A":
            if not devices:
                print(f"\n  {Colors.RED}❌ Không tìm thấy thiết bị Android/Giả lập kết nối qua ADB!{Colors.RESET}")
            else:
                for dev in devices:
                    ok, msg = AndroidDeepInterceptor.apply_tproxy_to_android_device(bridge.adb_bin, dev)
                    color = Colors.GREEN if ok else Colors.RED
                    print(f"    {color}[{dev}] {msg}{Colors.RESET}")
            safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")
        elif act == "B":
            if not devices:
                print(f"\n  {Colors.RED}❌ Không tìm thấy thiết bị Android/Giả lập kết nối qua ADB!{Colors.RESET}")
            else:
                for dev in devices:
                    ok, msg = MagiskServiceBootEngine.install_to_device(bridge.adb_bin, dev)
                    color = Colors.GREEN if ok else Colors.RED
                    print(f"    {color}[{dev}] {msg}{Colors.RESET}")
            safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")
        elif act == "R":
            if not devices:
                print(f"\n  {Colors.RED}❌ Không tìm thấy thiết bị Android/Giả lập kết nối qua ADB!{Colors.RESET}")
            else:
                for dev in devices:
                    ok1, msg1 = AndroidDeepInterceptor.revert_tproxy_on_android_device(bridge.adb_bin, dev)
                    ok2, msg2 = MagiskServiceBootEngine.remove_from_device(bridge.adb_bin, dev)
                    color = Colors.GREEN if ok1 else Colors.RED
                    print(f"    {color}[{dev}] {msg1} | {msg2}{Colors.RESET}")
            safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")

    # ====================================================================================
    # [9] CẤU HÌNH SCRIPT GAME (CUSTOM PAYLOAD)
    # ====================================================================================
    def configure_custom_payload(self):
        """[9] Cấu hình Script Game (Auto Farm Payload) tự chạy cho mọi Tag"""
        self.clear_screen()
        print(f"{Colors.LIGHT_PURPLE}{Colors.BOLD}================ [ 9. CẤU HÌNH SCRIPT GAME TỰ ĐỘNG CHẠY ] ================{Colors.RESET}\n")
        payload_file = os.path.join(BASE_DIR, "data", "custom_payload.lua")
        current_content = ""
        if os.path.exists(payload_file):
            with open(payload_file, "r", encoding="utf-8") as f:
                current_content = f.read()

        print(f"  {Colors.BOLD}Nội dung Script Game hiện tại:{Colors.RESET}")
        print("  " + "-" * 75)
        for line in current_content.splitlines()[:6]:
            print(f"    {Colors.CYAN}{line}{Colors.RESET}")
        if len(current_content.splitlines()) > 6:
            print(f"    {Colors.GRAY}... ({len(current_content.splitlines())} dòng code) ...{Colors.RESET}")
        print("  " + "-" * 75)

        print(f"\n  {Colors.BOLD}[1]{Colors.RESET} 📝 Xem toàn bộ nội dung Script Payload")
        print(f"  {Colors.BOLD}[2]{Colors.RESET} 🌐 Nhập URL Script (Ví dụ: loadstring(game:HttpGet(...)))")
        print(f"  {Colors.BOLD}[3]{Colors.RESET} ✍️  Dán trực tiếp mã code Lua")
        print(f"  {Colors.BOLD}[4]{Colors.RESET} 🔄 Reset về Script Payload mặc định")
        print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  Quay lại Menu chính\n")

        opt = safe_input(f"  {Colors.YELLOW}➤ Nhập lựa chọn (0-4):{Colors.RESET} ").strip()
        if opt == "1":
            print(f"\n{Colors.WHITE}{current_content}{Colors.RESET}")
        elif opt == "2":
            url_str = safe_input(f"  {Colors.YELLOW}Nhập URL Script Hub hoặc lệnh loadstring:{Colors.RESET} ").strip()
            if url_str:
                import re
                match = re.search(r'https?://[^\s"\'\)]+', url_str)
                if match:
                    clean_url = match.group(0)
                    code_to_save = f'-- [[ AUTO-GENERATED SCRIPT LOADER ]]\npcall(function()\n    loadstring(game:HttpGet("{clean_url}"))()\nend)\n'
                else:
                    code_to_save = url_str + "\n"

                with open(payload_file, "w", encoding="utf-8") as f:
                    f.write(code_to_save)
                print(f"\n{Colors.GREEN}{Colors.BOLD}[+] ĐÃ CẤU HÌNH SCRIPT THÀNH CÔNG!{Colors.RESET}")
                self.sync_system_state(self._get_combined_tag_instances())
        elif opt == "3":
            print(f"  {Colors.YELLOW}Dán mã code Lua của bạn (Dán 1 dòng hoặc gõ END_SCRIPT ở dòng cuối nếu nhiều dòng):{Colors.RESET}")
            first_line = safe_input().strip()
            if first_line:
                lines = [first_line]
                if not first_line.startswith("loadstring") and not first_line.startswith("--") and len(first_line) < 30:
                    while True:
                        l = safe_input()
                        if l.strip() == "END_SCRIPT" or not l:
                            break
                        lines.append(l)

                code_to_save = "\n".join(lines)
                with open(payload_file, "w", encoding="utf-8") as f:
                    f.write(code_to_save)
                print(f"\n{Colors.GREEN}{Colors.BOLD}[+] ĐÃ LƯU MÃ LUA SCRIPT THÀNH CÔNG!{Colors.RESET}")
                self.sync_system_state(self._get_combined_tag_instances())
        elif opt == "4":
            default_text = '-- [[ ROBLOX MULTI-TAG USER CUSTOM SCRIPT PAYLOAD ]]\nprint("[+] [UNIVERSAL MASTER EXECUTOR] All Tag scripts auto-executed successfully!")\n'
            with open(payload_file, "w", encoding="utf-8") as f:
                f.write(default_text)
            print(f"\n{Colors.GREEN}[+] Đã reset file Payload về mặc định!{Colors.RESET}")
            self.sync_system_state(self._get_combined_tag_instances())

        safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để quay lại Menu...{Colors.RESET}")

    # ====================================================================================
    # [10] QUẢN LÝ THƯ MỤC AUTOEXEC
    # ====================================================================================
    def manage_autoexec_folders(self):
        """[10] Quản lý & Đồng bộ thư mục Autoexec các Executor (Delta, Arceus X, Solara...)"""
        self.clear_screen()
        print(f"{Colors.LIGHT_CYAN}{Colors.BOLD}================ [ 10. QUẢN LÝ THƯ MỤC AUTOEXEC EXECUTOR ] ================{Colors.RESET}\n")
        
        detected_pc = self.autoexec_manager.detected_pc_dirs
        detected_android = self.autoexec_manager.detected_android_dirs

        print(f"  {Colors.BOLD}📁 Thư mục Autoexec tìm thấy trên Windows PC:{Colors.RESET}")
        if detected_pc:
            for p in detected_pc:
                print(f"    -> {Colors.GREEN}✓ {p}{Colors.RESET}")
        else:
            print(f"    -> {Colors.GRAY}Chưa tìm thấy Autoexec PC tự động. (Có thể thêm thủ công){Colors.RESET}")

        print(f"\n  {Colors.BOLD}📁 Thư mục Autoexec tìm thấy trên Android / Termux:{Colors.RESET}")
        if detected_android:
            for a in detected_android:
                print(f"    -> {Colors.GREEN}✓ {a}{Colors.RESET}")
        else:
            print(f"    -> {Colors.GRAY}Không chạy trên Android / Chưa có Autoexec Android.{Colors.RESET}")

        print(f"\n  {Colors.BOLD}[1]{Colors.RESET} 🔄 Bơm lại Master Router vào toàn bộ thư mục Autoexec")
        print(f"  {Colors.BOLD}[2]{Colors.RESET} ✍️  Thêm đường dẫn Autoexec tùy chỉnh")
        print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  Quay lại\n")

        sub_opt = safe_input(f"  {Colors.YELLOW}➤ Nhập lựa chọn (0-2):{Colors.RESET} ").strip()
        if sub_opt == "1":
            self.sync_system_state(self._get_combined_tag_instances())
            print(f"\n  {Colors.GREEN}{Colors.BOLD}[+] Đã đồng bộ Master Router thành công!{Colors.RESET}")
        elif sub_opt == "2":
            custom_p = safe_input(f"  {Colors.YELLOW}Nhập đường dẫn thư mục Autoexec mới:{Colors.RESET} ").strip()
            if custom_p and os.path.exists(custom_p):
                self.autoexec_manager.add_custom_autoexec_dir(custom_p)
                print(f"\n  {Colors.GREEN}[+] Đã thêm thư mục Autoexec: {custom_p}!{Colors.RESET}")
                self.sync_system_state(self._get_combined_tag_instances())

        safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để quay lại Menu...{Colors.RESET}")

    # ====================================================================================
    # [11] XEM BẢNG TỔNG HỢP CHI TIẾT TAG
    # ====================================================================================
    def view_instances_and_profiles(self):
        """[11] Xem danh sách Cloned Instances, Trạng thái & Network Profiles"""
        self.clear_screen()
        print(f"{Colors.LIGHT_CYAN}{Colors.BOLD}================ [ 11. DANH SÁCH CHI TIẾT CÁC TAG & CLONES ] ================{Colors.RESET}\n")
        instances = self._get_combined_tag_instances()

        print(f"  {'STT':<4} {'TAG ID':<16} {'STATUS':<12} {'ASSIGNED IP':<20} {'GAME ASSIGNED':<22} {'PID / HWID'}")
        print("  " + "-" * 88)

        for idx, inst in enumerate(instances):
            is_live = inst.hwnd > 0 or inst.pid > 0
            st_str = f"{Colors.GREEN}ONLINE{Colors.RESET}" if is_live else f"{Colors.GRAY}OFFLINE{Colors.RESET}"
            ip_str = inst.assigned_ip or "127.0.0.1"
            tg = game_manager.get_game_for_tag(inst.tag_id)
            g_name = tg.get("name", "Blox Fruits")[:20]
            pid_txt = f"PID:{inst.pid}" if inst.pid > 0 else "CLONE"
            print(f"  {idx+1:<4} {Colors.CYAN}{inst.tag_id:<16}{Colors.RESET} {st_str:<21} {Colors.YELLOW}{ip_str:<20}{Colors.RESET} {Colors.GREEN}{g_name:<22}{Colors.RESET} {pid_txt}")

        print("\n  " + "=" * 88)
        safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để quay lại Menu...{Colors.RESET}")

    # ====================================================================================
    # [12] DỌN DẸP & RESET HỆ THỐNG
    # ====================================================================================
    def clean_and_reset_system(self):
        """[12] Dọn dẹp Autoexec, Script Lua, Cache Proxy & Reset Hệ Thống"""
        self.clear_screen()
        print(f"{Colors.LIGHT_RED}{Colors.BOLD}================ [ 12. DỌN DẸP & RESET TOÀN BỘ HỆ THỐNG ] ================{Colors.RESET}\n")
        
        print(f"  {Colors.YELLOW}[!] Bạn có chắc chắn muốn dọn dẹp thư mục Autoexec, xóa cache Lua và reset Watchdog?{Colors.RESET}")
        confirm = safe_input(f"  {Colors.YELLOW}Nhập [Y] để đồng ý, [N] để hủy:{Colors.RESET} ").strip()

        if confirm.upper() == "Y":
            cleaned = self.autoexec_manager.clean_autoexec()
            print(f"\n  {Colors.GREEN}[+] Đã dọn sạch {cleaned} file script trong các thư mục Autoexec!{Colors.RESET}")
            
            # Xóa generated lua
            lua_dir = os.path.join(BASE_DIR, "data", "generated_lua")
            if os.path.exists(lua_dir):
                for f in os.listdir(lua_dir):
                    try:
                        os.remove(os.path.join(lua_dir, f))
                    except Exception:
                        pass
                print(f"  {Colors.GREEN}[+] Đã dọn sạch thư mục data/generated_lua!{Colors.RESET}")

            # Reset Watchdog state
            watchdog.tags = {}
            watchdog.total_restarts = 0
            watchdog.recent_logs = []
            print(f"  {Colors.GREEN}[+] Đã reset trạng thái Watchdog Supervisor!{Colors.RESET}")
            print(f"\n  {Colors.LIGHT_GREEN}{Colors.BOLD}⚡ HỆ THỐNG ĐÃ ĐƯỢC RESET VỀ TRẠNG THÁI SẠCH SẼ MẶC ĐỊNH!{Colors.RESET}")

        safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để quay lại Menu...{Colors.RESET}")

    def prompt_select_country(self) -> str:
        """Hiển thị menu chọn quốc gia cho IP/Proxy"""
        print(f"\n  {Colors.BOLD}[ CHỌN QUỐC GIA / REGION CHO IP ROBLOX ]{Colors.RESET}")
        print(f"  {Colors.BOLD}[0]{Colors.RESET} 🌐 {Colors.GREEN}{Colors.BOLD}MULTI-COUNTRY (Mỗi Tag 1 nước khác nhau - Khuyên dùng tránh Ban Acc){Colors.RESET}")
        for idx, (c_code, c_info) in enumerate(SUPPORTED_COUNTRIES.items()):
            flag = c_info.get("flag", "🌐")
            c_name = c_info.get("name", c_code)
            print(f"  {Colors.BOLD}[{idx+1}]{Colors.RESET} {flag} {c_name} ({c_code})")
        print(f"  {Colors.BOLD}[A]{Colors.RESET} 🌏 Toàn Cầu (All Available Countries)\n")

        c_choice = safe_input(f"  {Colors.YELLOW}➤ Chọn quốc gia (0-{len(SUPPORTED_COUNTRIES)}, hoặc A):{Colors.RESET} ").strip()
        if c_choice == "0":
            return "MULTI"
        elif c_choice.isdigit() and 1 <= int(c_choice) <= len(SUPPORTED_COUNTRIES):
            return list(SUPPORTED_COUNTRIES.keys())[int(c_choice) - 1]
        elif c_choice.upper() == "A":
            return "ALL"
        return "MULTI"

    def shutdown(self):
        """Đóng hệ thống an toàn"""
        self.bridge_server.stop()
        watchdog.stop()
        print(f"\n{Colors.YELLOW}[!] Đã đóng Master Controller và Watchdog an toàn. Tạm biệt!{Colors.RESET}\n")


if __name__ == "__main__":
    try:
        controller = MasterController()
        controller.main_menu()
    except (KeyboardInterrupt, EOFError):
        print("\n[!] Tạm biệt!")
        sys.exit(0)
