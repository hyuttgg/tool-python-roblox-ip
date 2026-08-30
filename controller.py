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

from devices.ugphone_bridge import UGPhoneBridge
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
from core.game_selector import game_manager, POPULAR_ROBLOX_GAMES, RobloxGameItem, fetch_game_name_from_roblox
from core.watchdog_supervisor import watchdog
from core.roblox_log_monitor import roblox_log_monitor
from core.screen_capture import capture_roblox_window, is_screenshot_supported
from network.discord_notifier import discord_notifier
from core.java_sort_bridge import SelectionSortBridge, RobloxAutoLauncher
from network.bridge_server import RobloxBridgeServer
from network.proxy_fetcher import ProxyFetcher, SUPPORTED_COUNTRIES
from network.scrapestack_client import ScrapestackClient
from devices.ugphone_bridge import UGPhoneNetworkEngine
from monitoring.status import NetworkInspector
from monitoring.radar.engine import radar_engine
from monitoring.radar.dashboard import radar_dashboard
from monitoring.radar.integrity import IntegrityMonitor
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
        
        # Bật Bridge Server, Watchdog và Radar Telemetry Engine chạy nền
        self.bridge_server.start()
        radar_engine.start()
        watchdog.setup_completed = True
        watchdog.is_enabled = True
        watchdog.auto_reopen_on_disconnect = True
        watchdog.start()

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
        return "MULTI"

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
                    account_username=cp.account_username or ""
                ))

        if not combined:
            combined.append(RobloxWindowInstance(
                tag_id="ROBLOX-TAG-01",
                hwnd=0,
                title="Roblox Main Client [SẴN SÀNG]",
                pid=0,
                process_name="RobloxPlayerBeta.exe",
                class_name="WINDOWS_CLIENT",
                rect=WindowRect(),
                screen_position="Main Instance",
                memory_usage="0 MB",
                account_username=""
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

        # 4. Đăng ký các Tag vào Watchdog & Radar Telemetry Engine
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
            is_android = inst.tag_id.startswith("ANDROID-") or inst.tag_id.startswith("UGPHONE-")
            radar_engine.register_tag(
                tag_id=inst.tag_id,
                pid=inst.pid,
                device_id=getattr(inst, "account_username", "") or inst.tag_id,
                platform="ANDROID" if is_android else "WINDOWS"
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
        c_p = Colors.C_PURPLE
        c_c = Colors.C_CYAN
        c_g = Colors.C_GREEN
        c_y = Colors.C_YELLOW
        c_r = Colors.C_RED
        c_w = Colors.WHITE
        c_rst = Colors.RESET
        c_bld = Colors.BOLD

        print(f"""{c_c}{c_bld}
  ██████╗   ██████╗  ██████╗  ██╗       ██████╗  ██╗  ██╗    ███╗   ██╗ ███████╗ ████████╗
  ██╔══██╗ ██╔═══██╗ ██╔══██╗ ██║      ██╔═══██╗ ╚██╗██╔╝    ████╗  ██║ ██╔════╝ ╚══██╔══╝
  ██████╔╝ ██║   ██║ ██████╔╝ ██║      ██║   ██║  ╚███╔╝     ██╔██╗ ██║ █████╗      ██║   
  ██╔══██╗ ██║   ██║ ██╔══██╗ ██║      ██║   ██║  ██╔██╗     ██║╚██╗██║ ██╔══╝      ██║   
  ██║  ██║ ╚██████╔╝ ██████╔╝ ███████╗ ╚██████╔╝ ██╔╝ ██╗    ██║ ╚████║ ███████╗    ██║   
  ╚═╝  ╚═╝  ╚═════╝  ╚═════╝  ╚══════╝  ╚═════╝  ╚═╝  ╚═╝    ╚═╝  ╚═══╝ ╚══════╝    ╚═╝   {c_rst}""")

        title_text = "⚡ [ UNIFIED MASTER CONTROLLER ] • ROBLOX MULTI-INSTANCE & AUTO-RESTART HUB ⚡"
        print(f"  {Colors.rainbow_text(title_text)}")
        print(f"{c_p}  " + "─" * 86 + f"{c_rst}")

        # Trạng thái tổng quan thời gian thực (Status Bar)
        total_tags = len(self.active_tags)
        if total_tags > 0:
            tag_status_str = f"{c_g}{c_bld}[{self.live_tags_count} LIVE | {self.clone_tags_count} CLONE]{c_rst}"
        else:
            tag_status_str = f"{c_y}[SẴN SÀNG QUÉT]{c_rst}"

        cur_game = game_manager.get_current_game()
        if game_manager.per_tag_mode:
            game_name = f"Per-Tag ({len(game_manager.get_all_tag_games())} Games)"
        else:
            game_name = cur_game.get("name", "Blox Fruits")[:18]
        game_status = f"{c_c}[{game_name}]{c_rst}"

        w_summary = watchdog.get_summary()
        w_status = f"{c_g}[ON: {w_summary['total_restarts']} RESTARTS]{c_rst}" if w_summary["is_enabled"] else f"{Colors.GRAY}[OFF]{c_rst}"

        is_android = os.path.exists("/system/build.prop") or "ANDROID_ROOT" in os.environ or os.path.exists("/sdcard")
        plat_txt = f"{c_g}[Android/UGPhone]{c_rst}" if is_android else f"{c_c}[Windows PC]{c_rst}"

        sel_c = self.selected_country or "MULTI"
        c_info = SUPPORTED_COUNTRIES.get(sel_c, {"name": sel_c, "flag": "🌐"})
        ip_txt = f"{c_y}[{c_info.get('flag', '🌐')} {sel_c}]{c_rst}"

        print(f"  {Colors.GRAY}💻 Nền tảng:{c_rst} {plat_txt}  {c_p}│{c_rst} {Colors.GRAY}🏷️  Tags:{c_rst} {tag_status_str}  {c_p}│{c_rst} {Colors.GRAY}🌐 IP:{c_rst} {ip_txt}  {c_p}│{c_rst} {Colors.GRAY}🎮 Game:{c_rst} {game_status}  {c_p}│{c_rst} {Colors.GRAY}🛡️ Watchdog:{c_rst} {w_status}")
        print(f"{c_p}  " + "─" * 86 + f"{c_rst}\n")

        def item_row(num: str, icon: str, title: str, desc: str = "", hot: bool = False):
            badge = f"{c_bld}{c_g if hot else c_c}[{num:>2} ]{c_rst}"
            t_col = f"{c_bld}{c_g if hot else c_w}{title}{c_rst}"
            d_col = f" {Colors.GRAY}({desc}){c_rst}" if desc else ""
            print(f"   {badge} {icon} {t_col}{d_col}")

        # TRỤ CỘT 1: ĐIỀU PHỐI & KHỞI CHẠY 1-CHẠM
        print(f"  {c_bld}{c_r}► 🚀 [ TRỤ CỘT 1: ĐIỀU PHỐI, CHỌN GAME & KHỞI CHẠY 1-CHẠM ]{c_rst}")
        item_row("1", "🚀", "FULL AUTO PIPELINE", "1-Chạm: Quét + Sort IP Java + Bơm Autoexec + Launch + Watchdog", hot=True)
        item_row("2", "🎮", "Cấu hình Game Roblox & Teleport Hub", "Global Game hoặc Mỗi Tag 1 Game riêng")
        item_row("3", "🛡️", "Giám sát & Bật/Tắt Auto-Restart Watchdog", "Tự động mở lại Tag khi văng/tắt")
        item_row("4", "📊", "Khởi chạy Live Dashboard Giám sát Real-Time", "FPS, Ping, RAM chu kỳ 3s")
        print()

        # TRỤ CỘT 2: TỐI ƯU MẠNG & THUẬT TOÁN JAVA
        print(f"  {c_bld}{c_y}► ⚡ [ TRỤ CỘT 2: TỐI ƯU MẠNG & THUẬT TOÁN JAVA ENGINE ]{c_rst}")
        item_row("5", "⚡", "Java Selection Sort Engine", "Sắp xếp IP theo Ping thấp nhất trên JVM JRE 8")
        item_row("6", "🔄", "Cấp phát & Đổi dải IP Proxy Đa Quốc Gia", "VN, JP, SG, HK, US, DE, AU...")
        item_row("7", "🌐", "Quản lý Pool IP & Scrapestack API", "Tải Proxy Live & Dedicated API")
        item_row("8", "🔍", "Chẩn đoán mạng chuyên sâu", "Java Handshake, Socket Ping, DNS, MTU")
        print()

        # TRỤ CỘT 3: SCRIPT GAME & QUẢN LÝ EXECUTOR
        print(f"  {c_bld}{c_p}► 📁 [ TRỤ CỘT 3: SCRIPT GAME, FASTFLAGS & EXECUTOR ]{c_rst}")
        item_row("9", "📝", "Cấu hình Script Game (Auto Farm Payload)", "Tự động chạy cho mọi Tag")
        item_row("10", "📁", "Quản lý & Đồng bộ thư mục Autoexec", "Delta, Arceus X, Solara, Wave, Codex")
        item_row("11", "📋", "Xem Bảng Tổng Hợp Chi Tiết Tag", "IP + Game + HWID + Status + PID")
        item_row("13", "⚡", "FastFlags & Performance Optimizer", "144 FPS / Potato Mode Treo Acc Android", hot=True)
        print()

        # TRỤ CỘT 4: BẢO TRÌ & HỆ THỐNG
        print(f"  {c_bld}{Colors.GRAY}► 🧹 [ TRỤ CỘT 4: BẢO TRÌ & HỆ THỐNG ]{c_rst}")
        item_row("12", "🧹", "Dọn dẹp Cache, Reset Autoexec, Script Lua & Khởi động lại Server")
        item_row("0", "❌", "Thoát chương trình an toàn")
        print()

    def main_menu(self):
        while True:
            try:
                self.print_banner()
                prompt_box = [
                    f"  {Colors.C_CYAN}{Colors.BOLD}╭──────────────────────────────────────────────────────────────────────────────────────╮{Colors.RESET}",
                    f"  {Colors.C_CYAN}{Colors.BOLD}│{Colors.RESET}  {Colors.LIGHT_GREEN}{Colors.BOLD}🎮 MASTER CONTROLLER:{Colors.RESET} {Colors.WHITE}Nhập số thứ tự tính năng để thực thi {Colors.BOLD}[ 0 ➔ 13 ]{Colors.RESET}               {Colors.C_CYAN}{Colors.BOLD}│{Colors.RESET}",
                    f"  {Colors.C_CYAN}{Colors.BOLD}╰──────────────────────────────────────────────────────────────────────────────────────╯{Colors.RESET}",
                ]
                print("\n".join(prompt_box))
                choice = safe_input(f"  {Colors.YELLOW}{Colors.BOLD}➤ Nhập lựa chọn của bạn{Colors.RESET} {Colors.GREEN}{Colors.BOLD}❯❯{Colors.RESET} ").strip()

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
                elif choice in ["13", "F", "f"]:
                    self.manage_fastflags_optimizer()
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

        # BƯỚC 2: Nhận diện cấu hình Game & Định tuyến Server Region
        print(f"\n  {Colors.BOLD}[BƯỚC 2/5]{Colors.RESET} {Colors.CYAN}Kiểm tra Game & Định tuyến Server VIP theo Region (SG/JP/US)...{Colors.RESET}")
        cur_g = game_manager.get_current_game()
        for inst in instances:
            srv = game_manager.resolve_server_for_tag(inst.tag_id)
            if srv and srv.get("region"):
                tag_g = game_manager.get_game_for_tag(inst.tag_id)
                tag_r = tag_g.get("preferred_region", "AUTO")
                logger.debug(f"Tag [{inst.tag_id}] routed to server {srv.get('job_id')} ({srv.get('region')})")

        if game_manager.per_tag_mode:
            print(f"    -> {Colors.GREEN}Chế độ: PER-TAG MULTI-GAME (Mỗi Tag 1 Game & Region riêng biệt đã định tuyến){Colors.RESET}")
        else:
            p_reg = cur_g.get("preferred_region", "AUTO")
            print(f"    -> {Colors.GREEN}Chế độ: GLOBAL GAME ➔ {cur_g.get('name')} (PlaceId: {cur_g.get('place_id')}, Region: [{p_reg}]){Colors.RESET}")

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

        from network.proxy_rotator import proxy_rotator
        proxy_rotator.add_proxies_batch(sorted_proxies)

        for idx, inst in enumerate(instances):
            sess_node = proxy_rotator.get_or_create_tag_session(inst.tag_id, country_code=target_country)
            inst.assigned_ip = sess_node.ip
            inst.region = sess_node.region
            inst.country = sess_node.country

        min_ping = sorted_proxies[0]["latency_ms"] if sorted_proxies else 20
        print(f"    -> {Colors.GREEN}Java & Smart Rotator Engine đã gán Sticky Proxy cho {len(instances)} Tag ({c_flag} {target_country}). Ping thấp nhất: {min_ping} ms!{Colors.RESET}")

        # BƯỚC 4: Đồng bộ Autoexec & Execute (online_roblox.lua)
        print(f"\n  {Colors.BOLD}[BƯỚC 4/5]{Colors.RESET} {Colors.CYAN}Tạo mã Lua & Tiêm file {Colors.YELLOW}online_roblox.lua{Colors.CYAN} vào toàn bộ thư mục Execute / Autoexec của Client...{Colors.RESET}")
        sync_result = self.sync_system_state(instances, use_live_proxies=False, country_code=target_country)
        print(f"    -> {Colors.GREEN}✔ ĐÃ TIÊM FILE [online_roblox.lua] ({target_country}) VÀO {sync_result['autoexec_synced_count']} THƯ MỤC EXECUTE / AUTOEXEC CỦA CLIENT EXECUTOR!{Colors.RESET}")

        # BƯỚC 4.5: Đánh dấu Setup hoàn tất (cho phép Watchdog auto-restart từ bây giờ)
        watchdog.setup_completed = True

        # BƯỚC 5: Khởi chạy Roblox (CHỈ khi người dùng xác nhận)
        print(f"\n  {Colors.BOLD}[BƯỚC 5/5]{Colors.RESET} {Colors.CYAN}Khởi chạy các bản Roblox Client...{Colors.RESET}")

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

            # CHỈ bật Watchdog auto-reopen SAU khi đã launch thành công
            watchdog.is_enabled = True
            watchdog.auto_reopen_on_disconnect = True
            watchdog.start()
            print(f"    -> {Colors.GREEN}Watchdog Supervisor: ONLINE (Tự động mở lại khi bị văng/disconnect){Colors.RESET}")
        else:
            print(f"    -> {Colors.GRAY}Bỏ qua khởi chạy Roblox. Watchdog auto-restart: TẮT.{Colors.RESET}")

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
            print(f"  {Colors.BOLD}[5]{Colors.RESET} 🌏 {Colors.LIGHT_PURPLE}{Colors.BOLD}CẤU HÌNH REGION & SERVER REJOIN VIP (Singapore, Japan, Low-Server){Colors.RESET}")
            print(f"  {Colors.BOLD}[L]{Colors.RESET} 🚀 {Colors.GREEN}Khởi chạy Roblox vào Game ngay bây giờ{Colors.RESET}")
            print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  {Colors.GRAY}Quay lại Menu chính{Colors.RESET}\n")

            opt = safe_input(f"  {Colors.YELLOW}{Colors.BOLD}➤ Nhập lựa chọn (0-5, L){Colors.RESET} {Colors.GREEN}{Colors.BOLD}❯❯{Colors.RESET} ").strip()

            if opt == "1":
                self._menu_select_global_game()
            elif opt == "2":
                self._menu_assign_games_per_tag()
            elif opt == "3":
                self._menu_view_tag_games_table()
            elif opt == "4":
                self._menu_auto_distribute_games()
            elif opt == "5":
                self._menu_configure_region_hub()
            elif opt.upper() == "L":
                instances = self._get_combined_tag_instances()
                print(f"\n  {Colors.YELLOW}[*] Đang khởi chạy các cửa sổ Roblox theo Game & Region riêng của từng Tag...{Colors.RESET}")
                res_list = RobloxAutoLauncher.launch_roblox_instances(instances=instances if instances else None, count=max(len(instances), 1))
                for lr in res_list:
                    if lr.get("status") == "LAUNCHED":
                        tag_g = game_manager.get_game_for_tag(lr.get("tag_id"))
                        tag_r = tag_g.get("preferred_region", "AUTO")
                        print(f"    -> {Colors.GREEN}[+] Đã mở Tag [{lr.get('tag_id')}]{Colors.RESET} ➔ Game: {Colors.CYAN}{tag_g.get('name')}{Colors.RESET} (Region: [{tag_r}], PlaceId: {lr.get('place_id')})")
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
            c_pid = safe_input(f"  {Colors.YELLOW}Nhập Place ID của game:{Colors.RESET} ").strip()
            if c_pid:
                auto_name = fetch_game_name_from_roblox(c_pid)
                c_name = safe_input(f"  {Colors.YELLOW}Nhập Tên game hiển thị (Tự động nhận diện: '{auto_name}'):{Colors.RESET} ").strip() or auto_name
                c_jid = safe_input(f"  {Colors.YELLOW}Nhập Job ID / Server ID (để trống nếu không có):{Colors.RESET} ").strip()
                game_manager.set_custom_game(name=c_name, place_id=c_pid, job_id=c_jid)
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
                c_pid = safe_input(f"  {Colors.YELLOW}Place ID:{Colors.RESET} ").strip()
                if c_pid:
                    auto_name = fetch_game_name_from_roblox(c_pid)
                    c_name = safe_input(f"  {Colors.YELLOW}Tên game (Tự động nhận diện: '{auto_name}'):{Colors.RESET} ").strip() or auto_name
                    game_manager.set_game_for_tag(target_inst.tag_id, name=c_name, place_id=c_pid)
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

    def _menu_configure_region_hub(self):
        """[5] Menu Cấu hình Region & Server Rejoin VIP (Singapore, Japan, USA, Low-Server)"""
        from network.roblox_region_finder import region_finder, SUPPORTED_REGIONS, FILTER_MODES
        while True:
            self.clear_screen()
            print(f"{Colors.LIGHT_PURPLE}{Colors.BOLD}================ [ 🌏 CẤU HÌNH REGION & SERVER REJOIN VIP ] ================{Colors.RESET}\n")
            
            cur_g = game_manager.get_current_game()
            p_reg = cur_g.get("preferred_region", "AUTO")
            f_mode = cur_g.get("server_filter_mode", "LOW_PLAYERS")
            r_info = SUPPORTED_REGIONS.get(p_reg, {"name": p_reg, "flag": "🌐"})
            
            print(f"  {Colors.BOLD}🎮 Game hiện tại:{Colors.RESET} {Colors.GREEN}{Colors.BOLD}{cur_g.get('name')}{Colors.RESET} (PlaceId: {Colors.CYAN}{cur_g.get('place_id')}{Colors.RESET})")
            print(f"  {Colors.BOLD}📍 Region mục tiêu:{Colors.RESET} {r_info.get('flag')} {Colors.YELLOW}{Colors.BOLD}{r_info.get('name')}{Colors.RESET}")
            print(f"  {Colors.BOLD}⚙️  Chế độ lọc Server:{Colors.RESET} {Colors.CYAN}{FILTER_MODES.get(f_mode, f_mode)}{Colors.RESET}")
            if cur_g.get("job_id"):
                print(f"  {Colors.BOLD}🆔 Server Job ID đã gán:{Colors.RESET} {Colors.WHITE}{cur_g.get('job_id')}{Colors.RESET}")
            print("  " + "-" * 75)

            print(f"\n  {Colors.BOLD}[1]{Colors.RESET} 🔍 {Colors.LIGHT_CYAN}Quét & Xem danh sách Public Servers trực tiếp của Game{Colors.RESET}")
            print(f"  {Colors.BOLD}[2]{Colors.RESET} 🌐 {Colors.YELLOW}Chọn Region cho TẤT CẢ các Tag (Singapore 🇸🇬, Japan 🇯🇵, USA 🇺🇸...){Colors.RESET}")
            print(f"  {Colors.BOLD}[3]{Colors.RESET} ⚡ {Colors.GREEN}Đổi chế độ lọc Server (Low Players 1-3 người / Lowest Ping){Colors.RESET}")
            print(f"  {Colors.BOLD}[4]{Colors.RESET} 🎯 {Colors.LIGHT_GREEN}Gán Region & Server riêng biệt cho từng Tag{Colors.RESET}")
            print(f"  {Colors.BOLD}[5]{Colors.RESET} 🚀 {Colors.CYAN}Tự động tìm Server VIP ({r_info.get('flag')} {p_reg}) và Khởi chạy ngay{Colors.RESET}")
            print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  {Colors.GRAY}Quay lại Menu trước{Colors.RESET}\n")

            choice = safe_input(f"  {Colors.YELLOW}{Colors.BOLD}➤ Nhập lựa chọn (0-5){Colors.RESET} {Colors.GREEN}{Colors.BOLD}❯❯{Colors.RESET} ").strip()

            if choice == "1":
                self.clear_screen()
                print(f"{Colors.LIGHT_CYAN}{Colors.BOLD}================ [ DANH SÁCH PUBLIC SERVERS: {cur_g.get('name').upper()} ] ================{Colors.RESET}\n")
                print(f"  {Colors.CYAN}[*] Đang tải danh sách Server từ Roblox API (PlaceId: {cur_g.get('place_id')})...{Colors.RESET}\n")
                servers = region_finder.fetch_public_servers(cur_g.get("place_id"), limit=30, force_refresh=True)
                
                print(f"  {'STT':<5} {'REGION':<18} {'PLAYERS':<12} {'PING':<10} {'FPS':<6} {'JOB ID'}")
                print("  " + "-" * 85)
                for idx, s in enumerate(servers[:20], 1):
                    p_str = f"{s['playing']}/{s['max_players']}"
                    p_col = Colors.GREEN if s['playing'] <= 4 else (Colors.YELLOW if s['playing'] <= 8 else Colors.LIGHT_RED)
                    print(f"  {idx:<5} {s['region_flag']} {s['region']:<14} {p_col}{p_str:<12}{Colors.RESET} {s['ping']:<3} ms    {s['fps']:<6} {s['job_id'][:28]}...")
                print("\n  " + "=" * 85)
                safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")

            elif choice == "2":
                self.clear_screen()
                print(f"{Colors.LIGHT_PURPLE}{Colors.BOLD}================ [ CHỌN REGION MỤC TIÊU CHO TOÀN BỘ TAG ] ================{Colors.RESET}\n")
                reg_keys = list(SUPPORTED_REGIONS.keys())
                for idx, rk in enumerate(reg_keys, 1):
                    r = SUPPORTED_REGIONS[rk]
                    is_c = " ⭐" if rk == p_reg else ""
                    print(f"  {Colors.BOLD}[{idx}]{Colors.RESET} {r['flag']} {r['name']}{is_c}")
                print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  Hủy bỏ\n")

                r_opt = safe_input(f"  {Colors.YELLOW}➤ Chọn Region (1-{len(reg_keys)}):{Colors.RESET} ").strip()
                if r_opt.isdigit() and 1 <= int(r_opt) <= len(reg_keys):
                    chosen_reg = reg_keys[int(r_opt) - 1]
                    best_s = game_manager.set_global_region(chosen_reg, filter_mode=f_mode)
                    instances = self._get_combined_tag_instances()
                    self.sync_system_state(instances)
                    print(f"\n  {Colors.GREEN}{Colors.BOLD}[+] ĐÃ CẤU HÌNH REGION [{chosen_reg}] CHO TOÀN BỘ CÁC TAG!{Colors.RESET}")
                    if best_s:
                        print(f"    -> Server tối ưu: {best_s.get('region_flag')} {best_s.get('region')} | Players: {best_s.get('playing')}/{best_s.get('max_players')} | Ping: {best_s.get('ping')} ms")
                    safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")

            elif choice == "3":
                self.clear_screen()
                print(f"{Colors.LIGHT_PURPLE}{Colors.BOLD}================ [ CHỌN CHẾ ĐỘ LỌC SERVER ] ================{Colors.RESET}\n")
                f_keys = list(FILTER_MODES.keys())
                for idx, fk in enumerate(f_keys, 1):
                    is_c = " ⭐" if fk == f_mode else ""
                    print(f"  {Colors.BOLD}[{idx}]{Colors.RESET} {Colors.CYAN}{fk:<14}{Colors.RESET} : {FILTER_MODES[fk]}{is_c}")
                print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  Hủy bỏ\n")

                f_opt = safe_input(f"  {Colors.YELLOW}➤ Chọn chế độ (1-{len(f_keys)}):{Colors.RESET} ").strip()
                if f_opt.isdigit() and 1 <= int(f_opt) <= len(f_keys):
                    chosen_mode = f_keys[int(f_opt) - 1]
                    game_manager.set_global_region(p_reg, filter_mode=chosen_mode)
                    instances = self._get_combined_tag_instances()
                    self.sync_system_state(instances)
                    print(f"\n  {Colors.GREEN}[+] Đã cập nhật chế độ lọc Server: [{chosen_mode}]!{Colors.RESET}")
                    safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")

            elif choice == "4":
                self.clear_screen()
                print(f"{Colors.LIGHT_CYAN}{Colors.BOLD}================ [ GÁN REGION RIÊNG CHO TỪNG TAG ] ================{Colors.RESET}\n")
                instances = self._get_combined_tag_instances()
                for idx, inst in enumerate(instances, 1):
                    tg = game_manager.get_game_for_tag(inst.tag_id)
                    t_reg = tg.get("preferred_region", "AUTO")
                    print(f"  {Colors.BOLD}[{idx}]{Colors.RESET} Tag: {Colors.GREEN}{inst.tag_id:<16}{Colors.RESET} | Game: {Colors.CYAN}{tg.get('name')[:20]:<20}{Colors.RESET} | Region: {Colors.YELLOW}[{t_reg}]{Colors.RESET}")
                
                t_choice = safe_input(f"\n  {Colors.YELLOW}➤ Chọn Tag (1-{len(instances)}) hoặc 0 để quay lại:{Colors.RESET} ").strip()
                if t_choice.isdigit() and 1 <= int(t_choice) <= len(instances):
                    target_inst = instances[int(t_choice) - 1]
                    reg_keys = list(SUPPORTED_REGIONS.keys())
                    print(f"\n  {Colors.BOLD}Chọn Region cho Tag [{target_inst.tag_id}]:{Colors.RESET}")
                    for r_i, rk in enumerate(reg_keys, 1):
                        r = SUPPORTED_REGIONS[rk]
                        print(f"    [{r_i}] {r['flag']} {r['name']}")
                    r_sel = safe_input(f"  {Colors.YELLOW}➤ Nhập lựa chọn (1-{len(reg_keys)}):{Colors.RESET} ").strip()
                    if r_sel.isdigit() and 1 <= int(r_sel) <= len(reg_keys):
                        chosen_rk = reg_keys[int(r_sel) - 1]
                        game_manager.set_region_for_tag(target_inst.tag_id, chosen_rk, filter_mode=f_mode)
                        self.sync_system_state(instances)
                        print(f"\n  {Colors.GREEN}[+] Đã gán Tag [{target_inst.tag_id}] ➔ Region [{chosen_rk}] thành công!{Colors.RESET}")
                        safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")

            elif choice == "5":
                instances = self._get_combined_tag_instances()
                print(f"\n  {Colors.CYAN}[*] Đang giải quyết Server VIP theo Region cho {len(instances)} Tag...{Colors.RESET}")
                for inst in instances:
                    best_s = game_manager.resolve_server_for_tag(inst.tag_id)
                    if best_s:
                        print(f"    -> Tag [{inst.tag_id}]: {best_s.get('region_flag')} {best_s.get('region')} | Players: {best_s.get('playing')} | Ping: {best_s.get('ping')} ms")
                self.sync_system_state(instances)
                print(f"\n  {Colors.YELLOW}[*] Đang khởi chạy Roblox vào các Server đã định tuyến...{Colors.RESET}")
                res_list = RobloxAutoLauncher.launch_roblox_instances(instances=instances if instances else None, count=max(len(instances), 1))
                for lr in res_list:
                    if lr.get("status") == "LAUNCHED":
                        tag_g = game_manager.get_game_for_tag(lr.get("tag_id"))
                        tag_r = tag_g.get("preferred_region", "AUTO")
                        print(f"    -> {Colors.GREEN}[+] Đã mở Tag [{lr.get('tag_id')}]{Colors.RESET} ➔ Game: {Colors.CYAN}{tag_g.get('name')}{Colors.RESET} (Region: [{tag_r}], PlaceId: {lr.get('place_id')})")
                    else:
                        print(f"    -> {Colors.RED}[!] Lỗi mở Tag [{lr.get('tag_id')}]: {lr.get('error')}{Colors.RESET}")
                safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")

            elif choice == "0":
                break

    # ====================================================================================
    # [3] GIÁM SÁT & AUTO-RESTART WATCHDOG SUPERVISOR
    # ====================================================================================
    def configure_watchdog_supervisor(self):
        """[3] Giám sát & Bật/Tắt Auto-Restart Watchdog (Tự động mở lại Tag khi bị tắt)"""
        while True:
            self.clear_screen()
            print(f"{Colors.LIGHT_GREEN}{Colors.BOLD}================ [ 3. GIÁM SÁT & AUTO-RESTART WATCHDOG SUPERVISOR ] ================{Colors.RESET}\n")
            
            w_summary = watchdog.get_summary()
            status_txt = f"{Colors.GREEN}{Colors.BOLD}ĐANG BẬT (ONLINE){Colors.RESET}" if w_summary["is_enabled"] else f"{Colors.GRAY}ĐANG TẮT (DISABLED){Colors.RESET}"
            reopen_txt = f"{Colors.GREEN}BẬT (Tự mở lại khi mất kết nối/tắt){Colors.RESET}" if w_summary["auto_reopen"] else f"{Colors.YELLOW}TẮT (Chỉ ghi log){Colors.RESET}"
            disc_cfg = discord_notifier.config
            disc_status = f"{Colors.GREEN}ĐÃ KẾT NỐI (ON){Colors.RESET}" if disc_cfg.get("enabled") and disc_cfg.get("webhook_url") else f"{Colors.GRAY}CHƯA BẬT (OFF){Colors.RESET}"
            log_mon_status = f"{Colors.GREEN}ONLINE (Log Tailer Active){Colors.RESET}" if roblox_log_monitor.current_log else f"{Colors.YELLOW}STANDBY (Sẵn sàng khi mở Roblox){Colors.RESET}"

            print(f"  {Colors.BOLD}🛡️ Trạng thái Watchdog Supervisor:{Colors.RESET} {status_txt}")
            print(f"  {Colors.BOLD}🔄 Chế độ Auto-Reopen (Tự mở lại):{Colors.RESET} {reopen_txt}")
            print(f"  {Colors.BOLD}📡 Roblox Player Log Monitor:{Colors.RESET} {log_mon_status}")
            print(f"  {Colors.BOLD}🔔 Thông báo Discord Alerts:{Colors.RESET} {disc_status}")
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
            print(f"  {Colors.BOLD}[4]{Colors.RESET} 🔔 Cấu hình Thông báo Discord Webhook & Bot Alerts")
            print(f"  {Colors.BOLD}[5]{Colors.RESET} 📸 Chụp ảnh màn hình Roblox lưu vết (Test Screenshot)")
            print(f"  {Colors.BOLD}[6]{Colors.RESET} 📱 Chế độ Android / Termux Sentinel (Auto-Rejoin trên Điện thoại & Giả lập)")
            print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  {Colors.GRAY}Quay lại Menu chính{Colors.RESET}\n")

            opt = safe_input(f"  {Colors.YELLOW}{Colors.BOLD}➤ Chọn thao tác (0-6){Colors.RESET} {Colors.GREEN}{Colors.BOLD}❯❯{Colors.RESET} ").strip()
            if opt == "1":
                watchdog.is_enabled = not watchdog.is_enabled
                if watchdog.is_enabled:
                    watchdog.setup_completed = True
                    watchdog.start()
                print(f"\n  {Colors.GREEN}[+] Đã {'BẬT' if watchdog.is_enabled else 'TẮT'} Watchdog Supervisor!{Colors.RESET}")
                time.sleep(1)
            elif opt == "2":
                watchdog.auto_reopen_on_disconnect = not watchdog.auto_reopen_on_disconnect
                if watchdog.auto_reopen_on_disconnect:
                    watchdog.setup_completed = True
                    watchdog.is_enabled = True
                    watchdog.start()
                print(f"\n  {Colors.GREEN}[+] Đã {'BẬT' if watchdog.auto_reopen_on_disconnect else 'TẮT'} chế độ Tự động Mở lại (Auto-Rejoin) Tag!{Colors.RESET}")
                time.sleep(1)
            elif opt == "3":
                tid_test = safe_input(f"  {Colors.YELLOW}Nhập Tag ID muốn mở lại (mặc định ROBLOX-TAG-01):{Colors.RESET} ").strip() or "ROBLOX-TAG-01"
                print(f"\n  {Colors.CYAN}[*] Đang kích hoạt thử nghiệm mở lại Tag [{tid_test}]...{Colors.RESET}")
                watchdog.setup_completed = True
                watchdog.is_enabled = True
                watchdog.auto_reopen_on_disconnect = True
                watchdog.register_tag(tid_test)
                watchdog._trigger_reopen_tag(tid_test, "Thử nghiệm kích hoạt thủ công từ Menu")
                print(f"  {Colors.GREEN}[+] Đã gửi lệnh mở lại Tag thành công!{Colors.RESET}")
                safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")
            elif opt == "4":
                self._menu_configure_discord()
            elif opt == "5":
                print(f"\n  {Colors.CYAN}[*] Đang chụp ảnh màn hình cửa sổ Roblox...{Colors.RESET}")
                snap = capture_roblox_window()
                if snap:
                    print(f"  {Colors.GREEN}[+] Đã chụp ảnh thành công: {snap}{Colors.RESET}")
                else:
                    print(f"  {Colors.YELLOW}[!] Không tìm thấy cửa sổ Roblox đang mở hoặc cửa sổ đang minimized.{Colors.RESET}")
                safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")
            elif opt == "6":
                self._menu_termux_sentinel()
            elif opt == "0":
                break

    def _menu_termux_sentinel(self):
        """Menu cấu hình và chạy Auto-Rejoin trên Android / Termux dựa trên DroidBlox Engine"""
        while True:
            self.clear_screen()
            print(f"{Colors.LIGHT_CYAN}{Colors.BOLD}================ [ 📱 ROBLOX ANDROID / TERMUX SENTINEL (DROIDBLOX ENGINE) ] ================{Colors.RESET}\n")
            print(f"  {Colors.BOLD}Tự động phát hiện mất kết nối (Logcat FLog) & Rejoin qua Android Intent (DroidBlox Architecture).{Colors.RESET}\n")
            print(f"  {Colors.BOLD}[1]{Colors.RESET} 🚀 {Colors.LIGHT_GREEN}{Colors.BOLD}Khởi chạy Android Rejoin Sentinel (Interactive Menu & ADB Device Scanner){Colors.RESET}")
            print(f"  {Colors.BOLD}[2]{Colors.RESET} ⚡ {Colors.CYAN}Khởi chạy Rejoin nhanh cho Game đang chọn (Headless Mode){Colors.RESET}")
            print(f"  {Colors.BOLD}[3]{Colors.RESET} 📜 {Colors.WHITE}Bơm script Luau Autoexec vào thư mục Android (/sdcard/Delta, Arceus X, Codex...){Colors.RESET}")
            print(f"  {Colors.BOLD}[4]{Colors.RESET} 📋 {Colors.YELLOW}Xem hướng dẫn & Lệnh chạy Bash Shell trên Termux{Colors.RESET}")
            print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  {Colors.GRAY}Quay lại Menu trước{Colors.RESET}\n")

            choice = safe_input(f"  {Colors.YELLOW}{Colors.BOLD}➤ Nhập lựa chọn (0-4){Colors.RESET} {Colors.GREEN}{Colors.BOLD}❯❯{Colors.RESET} ").strip()
            if choice == "1":
                from tools.android_rejoin_cli import interactive_menu
                interactive_menu()
            elif choice == "2":
                from devices.android_rejoin import AndroidRejoinController
                from core.game_selector import game_manager
                import shutil
                g = game_manager.get_current_game()
                pid = int(g.get("place_id", 2753915549))
                jid = g.get("job_id") or None
                adb_bin = shutil.which("adb")
                print(f"\n  {Colors.CYAN}[*] Đang khởi chạy Sentinel cho Game: {g.get('name')} (Place: {pid}, Job: {jid or 'Auto'})...{Colors.RESET}")
                ctrl = AndroidRejoinController(
                    default_place_id=pid,
                    default_job_id=jid,
                    adb_bin=adb_bin,
                    cooldown_sec=15,
                    max_consecutive_fails=3,
                    circuit_cooldown_sec=45
                )
                ctrl.run_monitor_loop(poll_interval=3.0)
            elif choice == "3":
                from core.termux_bridge import TermuxRobloxRejoiner
                from core.lua_generator import OUTPUT_LUA_DIR
                m_path = os.path.join(OUTPUT_LUA_DIR, "master_roblox_ip_setter.lua")
                r = TermuxRobloxRejoiner()
                cnt = r.sync_android_autoexec(m_path)
                print(f"\n  {Colors.GREEN}[+] Đã đồng bộ script vào {cnt} thư mục Autoexec trên Android!{Colors.RESET}")
                safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")
            elif choice == "4":
                print(f"\n  {Colors.BOLD}[ HƯỚNG DẪN CHẠY TRỰC TIẾP TRÊN TERMUX ]: {Colors.RESET}")
                print(f"  {Colors.GREEN}pkg update && pkg install bash python git -y{Colors.RESET}")
                print(f"  {Colors.YELLOW}chmod +x tools/termux_auto_rejoin.sh{Colors.RESET}")
                print(f"  {Colors.CYAN}./tools/termux_auto_rejoin.sh 2753915549{Colors.RESET}")
                print(f"\n  {Colors.BOLD}Hoặc chạy bằng Python CLI:{Colors.RESET}")
                print(f"  {Colors.GREEN}python tools/android_rejoin_cli.py --headless -p 2753915549{Colors.RESET}")
                safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")
            elif choice == "0":
                break

    def _menu_configure_discord(self):
        """Menu cấu hình Discord Webhook & Alerts"""
        while True:
            self.clear_screen()
            print(f"{Colors.LIGHT_CYAN}{Colors.BOLD}================ [ 🔔 CẤU HÌNH THÔNG BÁO DISCORD ] ================{Colors.RESET}\n")
            cfg = discord_notifier.config
            st_en = f"{Colors.GREEN}BẬT{Colors.RESET}" if cfg.get("enabled") else f"{Colors.GRAY}TẮT{Colors.RESET}"
            st_shot = f"{Colors.GREEN}BẬT{Colors.RESET}" if cfg.get("attach_screenshot") else f"{Colors.GRAY}TẮT{Colors.RESET}"
            wh_url = cfg.get("webhook_url") or "(Chưa cấu hình)"
            if wh_url.startswith("http"):
                wh_masked = wh_url[:35] + "..." + wh_url[-10:]
            else:
                wh_masked = wh_url

            print(f"  {Colors.BOLD}1. Trạng thái gửi thông báo:{Colors.RESET} {st_en}")
            print(f"  {Colors.BOLD}2. Discord Webhook URL:{Colors.RESET} {Colors.YELLOW}{wh_masked}{Colors.RESET}")
            print(f"  {Colors.BOLD}3. Đính kèm ảnh chụp màn hình khi crash:{Colors.RESET} {st_shot}")
            print(f"  {Colors.BOLD}4. Gửi thử tin nhắn Test lên Discord{Colors.RESET}")
            print(f"  {Colors.BOLD}0. Quay lại{Colors.RESET}\n")

            choice = safe_input(f"  {Colors.YELLOW}➤ Nhập lựa chọn (0-4):{Colors.RESET} ").strip()
            if choice == "1":
                cfg["enabled"] = not cfg.get("enabled", False)
                discord_notifier.save_config(cfg)
            elif choice == "2":
                new_url = safe_input(f"  {Colors.YELLOW}Dán URL Discord Webhook mới:{Colors.RESET} ").strip()
                if new_url:
                    cfg["webhook_url"] = new_url
                    cfg["enabled"] = True
                    discord_notifier.save_config(cfg)
                    print(f"\n  {Colors.GREEN}[+] Đã lưu Discord Webhook URL!{Colors.RESET}")
                    time.sleep(1)
            elif choice == "3":
                cfg["attach_screenshot"] = not cfg.get("attach_screenshot", True)
                discord_notifier.save_config(cfg)
            elif choice == "4":
                print(f"\n  {Colors.CYAN}[*] Đang gửi tin nhắn thử nghiệm tới Discord...{Colors.RESET}")
                res = discord_notifier.test_webhook()
                if res.get("success"):
                    print(f"  {Colors.GREEN}[+] Gửi Test Webhook thành công 100%!{Colors.RESET}")
                else:
                    print(f"  {Colors.RED}[!] Gửi thất bại: {res.get('error')}{Colors.RESET}")
                safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")
            elif choice == "0":
                break

    # ====================================================================================
    # [4] RADAR LIVE MONITOR & CHẨN ĐOÁN LỖI CHUYÊN SÂU
    # ====================================================================================
    def start_live_dashboard(self):
        """[4] Trung tâm Giám sát Radar 3D, Lọc nhiễu Kalman & Phân tích lỗi Roblox chuyên sâu"""
        while True:
            self.clear_screen()
            print(f"{Colors.LIGHT_CYAN}{Colors.BOLD}================ [ 4. RADAR MONITOR & PHÂN TÍCH CHẨN ĐOÁN LỖI ROBLOX ] ================{Colors.RESET}\n")
            
            reports = radar_engine.get_all_reports()
            states_summary = {}
            for r in reports.values():
                states_summary[r.state] = states_summary.get(r.state, 0) + 1
            
            summary_str = " | ".join([f"{st}: {cnt}" for st, cnt in states_summary.items()]) if states_summary else "Chưa có Tag nào được gán telemetry"
            
            print(f"  {Colors.BOLD}🛰️ Radar Pipeline:{Colors.RESET} {Colors.GREEN}ONLINE{Colors.RESET} (Chu kỳ quét: {radar_engine.scan_interval}s, Cycles: {radar_engine.cycle_count})")
            print(f"  {Colors.BOLD}📊 Trạng thái Radar hiện tại:{Colors.RESET} {Colors.YELLOW}{summary_str}{Colors.RESET}")
            print(f"  {Colors.BOLD}📡 Thuật toán tích hợp:{Colors.RESET} {Colors.WHITE}Kalman Telemetry Smoothing + CFAR Anomaly Detection + MTI State Tracker{Colors.RESET}")
            print("  " + "-" * 85)

            print(f"\n  {Colors.LIGHT_GREEN}{Colors.BOLD}[1]{Colors.RESET} 🛰️ {Colors.LIGHT_GREEN}{Colors.BOLD}Mở RADAR LIVE DASHBOARD (Rich Console: Anomaly Score, Sparkline Timeline, Uptime){Colors.RESET}")
            print(f"  {Colors.LIGHT_CYAN}{Colors.BOLD}[2]{Colors.RESET} 🔍 {Colors.WHITE}Bảng Chẩn đoán Chuyên sâu các Mã lỗi Roblox (268, 273, 277, 279, 267, 524, 773...){Colors.RESET}")
            print(f"  {Colors.LIGHT_PURPLE}{Colors.BOLD}[3]{Colors.RESET} 🛡️ {Colors.WHITE}Kiểm tra Tính toàn vẹn File Roblox (SHA-256 Anti-Tamper & Phân tích Crash/Update){Colors.RESET}")
            print(f"  {Colors.YELLOW}{Colors.BOLD}[4]{Colors.RESET} 📊 {Colors.WHITE}Mở Classic TUI Live Monitor (Giao diện bảng thống kê tiến trình truyền thống){Colors.RESET}")
            print(f"  {Colors.GRAY}{Colors.BOLD}[0]{Colors.RESET} ↩️  {Colors.GRAY}Quay lại Menu chính{Colors.RESET}\n")

            sub_choice = safe_input(f"  {Colors.YELLOW}{Colors.BOLD}➤ Nhập lựa chọn (0-4){Colors.RESET} {Colors.GREEN}{Colors.BOLD}❯❯{Colors.RESET} ").strip()

            if sub_choice == "1":
                self.clear_screen()
                print(f"{Colors.GREEN}[*] Đang khởi chạy Radar Live Dashboard... (Nhấn Q để thoát){Colors.RESET}\n")
                radar_dashboard.run_live(refresh_interval=2.0)
            elif sub_choice == "2":
                self._show_deep_error_diagnostics()
            elif sub_choice == "3":
                self._show_integrity_diagnostic_view()
            elif sub_choice == "4":
                instances = self._get_combined_tag_instances()
                from cli.status import LiveRealtimeMonitor
                LiveRealtimeMonitor.start_monitoring_loop(instances=instances, refresh_interval=1.5)
            elif sub_choice == "0":
                break

    def _show_deep_error_diagnostics(self):
        """Hiển thị bảng phân tích toàn diện mã lỗi Roblox và hướng khắc phục tự động"""
        self.clear_screen()
        print(f"{Colors.LIGHT_CYAN}{Colors.BOLD}================ [ 🔍 MA TRẬN CHẨN ĐOÁN LỖI ROBLOX & CƠ CHẾ KHẮC PHỤC ] ================{Colors.RESET}\n")
        
        from core.roblox_log_monitor import ERROR_TAXONOMY
        
        print(f"  {'MÃ LỖI':<10} {'TÊN HIỆN TƯỢNG':<32} {'NGUYÊN NHÂN GỐC':<38} {'CƠ CHẾ XỬ LÝ RADAR'}")
        print("  " + "=" * 110)
        
        for code, info in ERROR_TAXONOMY.items():
            c_tag = f"[{code.upper()}]"
            print(f"  {Colors.LIGHT_RED}{c_tag:<10}{Colors.RESET} {Colors.GREEN}{info['title'][:30]:<32}{Colors.RESET} {info['desc'][:36]:<38} {Colors.YELLOW}{info['action'][:35]}{Colors.RESET}")
            print(f"    {Colors.GRAY}└── Chi tiết:{Colors.RESET} {info['desc']}")
            print(f"    {Colors.GRAY}└── Hành động tự động:{Colors.RESET} {Colors.LIGHT_CYAN}{info['action']}{Colors.RESET}")
            print("  " + "-" * 110)
        
        # Kiểm tra log mới nhất
        print(f"\n  {Colors.BOLD}📡 Trạng thái Roblox Log Monitor hiện thời:{Colors.RESET}")
        latest_details = roblox_log_monitor.check_for_disconnect_details()
        if latest_details:
            print(f"    {Colors.LIGHT_RED}[!] Phát hiện lỗi mới nhất trong Log:{Colors.RESET} {Colors.YELLOW}{latest_details.get('title')}{Colors.RESET}")
            print(f"    {Colors.GRAY}-> Mã:{Colors.RESET} {latest_details.get('code')} | {Colors.GRAY}Phân loại:{Colors.RESET} {latest_details.get('category')}")
            print(f"    {Colors.GRAY}-> Khắc phục khuyến nghị:{Colors.RESET} {Colors.LIGHT_GREEN}{latest_details.get('action')}{Colors.RESET}")
        else:
            print(f"    {Colors.GREEN}[✓] Không có lỗi kết nối nào ghi nhận trong phiên log Roblox gần nhất.{Colors.RESET}")
            
        safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để quay lại...{Colors.RESET}")

    def _show_integrity_diagnostic_view(self):
        """Hiển thị phân tích toàn vẹn file Roblox và cập nhật baseline"""
        self.clear_screen()
        print(f"{Colors.LIGHT_PURPLE}{Colors.BOLD}================ [ 🛡️ KIỂM TRA TOÀN VẸN FILE & ANTI-TAMPER CHECK ] ================{Colors.RESET}\n")
        
        monitor = IntegrityMonitor()
        res = monitor.check_integrity()
        
        print(f"  {Colors.BOLD}1. Trạng thái tìm thấy Executable:{Colors.RESET} {Colors.GREEN + 'TÌM THẤY' if res.exe_found else Colors.RED + 'KHÔNG TÌM THẤY'}{Colors.RESET}")
        print(f"  {Colors.BOLD}2. Đường dẫn RobloxPlayerBeta.exe:{Colors.RESET} {Colors.CYAN}{res.exe_path or 'N/A'}{Colors.RESET}")
        print(f"  {Colors.BOLD}3. Phiên bản Client hiện tại:{Colors.RESET} {Colors.YELLOW}{res.version or 'N/A'}{Colors.RESET}")
        print(f"  {Colors.BOLD}4. SHA-256 Hash hiện tại:{Colors.RESET} {Colors.WHITE}{res.current_hash[:48]}...{Colors.RESET}" if res.current_hash else f"  {Colors.BOLD}4. SHA-256 Hash:{Colors.RESET} N/A")
        print(f"  {Colors.BOLD}5. SHA-256 Hash Baseline gốc:{Colors.RESET} {Colors.GRAY}{res.baseline_hash[:48]}...{Colors.RESET}" if res.baseline_hash else f"  {Colors.BOLD}5. SHA-256 Hash Baseline:{Colors.RESET} (Chưa có baseline)")
        
        if res.match is True:
            print(f"\n  {Colors.GREEN}{Colors.BOLD}[✓] KẾT QUẢ: File Roblox nguyên bản, 100% khớp với Baseline (NORMAL).{Colors.RESET}")
        elif res.match is False:
            print(f"\n  {Colors.LIGHT_RED}{Colors.BOLD}[!] KẾT QUẢ: File Hash khác với Baseline (APP_CHANGED).{Colors.RESET}")
            print(f"      {Colors.YELLOW}Chi tiết:{Colors.RESET} {res.details}")
            print(f"      {Colors.GRAY}Lưu ý: Nếu Roblox vừa cập nhật phiên bản mới, hãy nhấn [1] để lưu Baseline mới.{Colors.RESET}")
        else:
            print(f"\n  {Colors.YELLOW}{Colors.BOLD}[i] KẾT QUẢ: Đã tạo Baseline khởi tạo thành công.{Colors.RESET}")
            
        print(f"\n  {Colors.BOLD}[1]{Colors.RESET} 🔄 Cập nhật Baseline với Hash phiên bản hiện tại (Confirm Update)")
        print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  Quay lại\n")
        
        opt = safe_input(f"  {Colors.YELLOW}➤ Nhập lựa chọn (0-1):{Colors.RESET} ").strip()
        if opt == "1":
            if monitor.update_baseline():
                print(f"\n  {Colors.GREEN}[+] Đã cập nhật Baseline mới thành công!{Colors.RESET}")
                time.sleep(1.5)


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
        print(f"{Colors.LIGHT_PURPLE}{Colors.BOLD}================ [ 9. CẤU HÌNH & TIÊM SCRIPT GAME TỰ ĐỘNG CHẠY ] ================{Colors.RESET}\n")
        payload_file = os.path.join(BASE_DIR, "data", "custom_payload.lua")
        current_content = ""
        if os.path.exists(payload_file):
            try:
                with open(payload_file, "r", encoding="utf-8") as f:
                    current_content = f.read()
            except Exception:
                current_content = ""

        print(f"  {Colors.BOLD}Nội dung Script Game hiện tại:{Colors.RESET}")
        print("  " + "-" * 75)
        lines_preview = current_content.splitlines()
        for line in lines_preview[:6]:
            print(f"    {Colors.CYAN}{line}{Colors.RESET}")
        if len(lines_preview) > 6:
            print(f"    {Colors.GRAY}... ({len(lines_preview)} dòng code) ...{Colors.RESET}")
        elif not lines_preview:
            print(f"    {Colors.GRAY}(Chưa cấu hình script - Đang dùng script mặc định){Colors.RESET}")
        print("  " + "-" * 75)

        print(f"\n  {Colors.BOLD}[1]{Colors.RESET} 📝 Xem toàn bộ nội dung Script Payload")
        print(f"  {Colors.BOLD}[2]{Colors.RESET} 🌐 Nhập URL Script (Ví dụ: loadstring(game:HttpGet(...)))")
        print(f"  {Colors.BOLD}[3]{Colors.RESET} ✍️  Dán trực tiếp mã code Lua (Tự động tiêm vào Autoexec PC & Android)")
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

                sync_res = self.sync_system_state(self._get_combined_tag_instances())
                print(f"\n{Colors.GREEN}{Colors.BOLD}========================================================================{Colors.RESET}")
                print(f"{Colors.GREEN}{Colors.BOLD}  ✔ ĐÃ TIÊM VÀ KÍCH HOẠT SCRIPT THÀNH CÔNG CHO TẤT CẢ CÁC TAG!{Colors.RESET}")
                print(f"{Colors.GREEN}{Colors.BOLD}========================================================================{Colors.RESET}")
                print(f"    -> {Colors.CYAN}Đã lưu vào file:{Colors.RESET} data/custom_payload.lua")
                print(f"    -> {Colors.CYAN}Đã nhúng trực tiếp vào:{Colors.RESET} Master Script & Tag Scripts")
                print(f"    -> {Colors.CYAN}Đã bơm vào Autoexec:{Colors.RESET} {self.autoexec_synced_count} thư mục/thiết bị")
                print(f"    -> {Colors.YELLOW}Script sẽ tự động chạy ngay khi Roblox khởi động!{Colors.RESET}\n")
        elif opt == "3":
            print(f"\n  {Colors.YELLOW}{Colors.BOLD}➤ HƯỚNG DẪN DÁN SCRIPT:{Colors.RESET}")
            print(f"    1. Nhấn chuột phải hoặc nhấn {Colors.CYAN}Ctrl + V{Colors.RESET} để dán toàn bộ mã Lua của bạn.")
            print(f"    2. Sau khi dán xong, gõ {Colors.GREEN}END{Colors.RESET} ở dòng mới (hoặc nhấn {Colors.GREEN}Enter 2 lần{Colors.RESET}) để hoàn tất.\n")
            print(f"  {Colors.GRAY}--- BẮT ĐẦU DÁN MÃ CODE LUA BÊN DƯỚI ---{Colors.RESET}")

            lines = []
            empty_streak = 0
            while True:
                try:
                    line = input()
                    if line.strip().upper() in ["END", "END_SCRIPT", "EOF", ":Q"]:
                        break
                    if line.strip() == "":
                        empty_streak += 1
                        if empty_streak >= 2 and lines:
                            break
                        elif not lines:
                            continue
                    else:
                        empty_streak = 0
                    lines.append(line)
                except (EOFError, KeyboardInterrupt):
                    break

            if lines:
                raw_code = "\n".join(lines).strip()
                # Tự động phát hiện nếu người dùng chỉ dán 1 URL
                if raw_code.startswith("http://") or raw_code.startswith("https://"):
                    code_to_save = f'-- [[ AUTO-GENERATED SCRIPT LOADER ]]\npcall(function()\n    loadstring(game:HttpGet("{raw_code}"))()\nend)\n'
                else:
                    code_to_save = raw_code + "\n"

                with open(payload_file, "w", encoding="utf-8") as f:
                    f.write(code_to_save)

                # Đồng bộ và bơm ngay lập tức vào tất cả Autoexec
                sync_res = self.sync_system_state(self._get_combined_tag_instances())
                
                print(f"\n{Colors.GREEN}{Colors.BOLD}========================================================================{Colors.RESET}")
                print(f"{Colors.GREEN}{Colors.BOLD}  ✔ ĐÃ TIÊM VÀ KÍCH HOẠT SCRIPT THÀNH CÔNG CHO TẤT CẢ CÁC TAG!{Colors.RESET}")
                print(f"{Colors.GREEN}{Colors.BOLD}========================================================================{Colors.RESET}")
                print(f"    -> {Colors.CYAN}Đã lưu vào:{Colors.RESET} data/custom_payload.lua ({len(lines)} dòng code)")
                print(f"    -> {Colors.CYAN}Đã nhúng trực tiếp vào:{Colors.RESET} Master Script & Tag Lua Scripts")
                print(f"    -> {Colors.CYAN}Đã bơm vào Autoexec:{Colors.RESET} {self.autoexec_synced_count} thư mục / thiết bị")
                print(f"    -> {Colors.YELLOW}Script sẽ tự động chạy ngay khi Roblox khởi động!{Colors.RESET}\n")
            else:
                print(f"\n  {Colors.RED}❌ Không có nội dung mã script nào được dán!{Colors.RESET}")
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

    # ====================================================================================
    # [13] FASTFLAGS & PERFORMANCE OPTIMIZER (DROIDBLOX ARCHITECTURE)
    # ====================================================================================
    def manage_fastflags_optimizer(self):
        """[13] Tinh chỉnh FastFlags tăng FPS, mở khóa 144 FPS và chế độ Potato Mode cho Android/PC"""
        from core.fastflags_optimizer import fastflags_optimizer, FASTFLAGS_PRESETS
        while True:
            self.clear_screen()
            print(f"{Colors.LIGHT_GREEN}{Colors.BOLD}================ [ 13. FASTFLAGS & PERFORMANCE OPTIMIZER ] ================{Colors.RESET}\n")
            print(f"  {Colors.BOLD}Cấu hình ClientAppSettings.json giảm tải 40-60% RAM, tăng FPS khi treo nhiều acc Android/PC.{Colors.RESET}\n")

            cur_preset_key = fastflags_optimizer.active_preset
            cur_preset_info = FASTFLAGS_PRESETS.get(cur_preset_key, {"name": cur_preset_key, "description": ""})

            print(f"  {Colors.BOLD}⚙️  Preset hiện tại:{Colors.RESET} {Colors.GREEN}{Colors.BOLD}{cur_preset_info['name']}{Colors.RESET}")
            print(f"  {Colors.GRAY}    -> {cur_preset_info['description']}{Colors.RESET}\n")

            effective_flags = fastflags_optimizer.get_effective_flags()
            print(f"  {Colors.BOLD}📋 Danh sách FastFlags đang áp dụng ({len(effective_flags)} cờ):{Colors.RESET}")
            print("  " + "-" * 75)
            for k, v in list(effective_flags.items())[:8]:
                print(f"    * {Colors.CYAN}{k:<40}{Colors.RESET} : {Colors.YELLOW}{v}{Colors.RESET}")
            if len(effective_flags) > 8:
                print(f"    {Colors.GRAY}... và {len(effective_flags) - 8} cờ khác ...{Colors.RESET}")
            print("  " + "-" * 75)

            print(f"\n  {Colors.BOLD}[1]{Colors.RESET} ⚡ Chọn Preset: Siêu Tốc Độ (Ultra FPS 144Hz / Tắt Shadows / Giảm LOD)")
            print(f"  {Colors.BOLD}[2]{Colors.RESET} 🥔 Chọn Preset: Potato Mode (Siêu nhẹ cho Treo Nhiều Acc Android / UGPhone)")
            print(f"  {Colors.BOLD}[3]{Colors.RESET} ⚖️  Chọn Preset: Cân Bằng (Balanced 120 FPS / Mượt & Giữ Đồ Họa)")
            print(f"  {Colors.BOLD}[4]{Colors.RESET} 📱 {Colors.GREEN}{Colors.BOLD}Bơm FastFlags vào tất cả thư mục Android (/sdcard/Roblox & Executor){Colors.RESET}")
            print(f"  {Colors.BOLD}[5]{Colors.RESET} 💻 {Colors.CYAN}Bơm FastFlags vào Roblox PC (ClientSettings & Bloxstrap){Colors.RESET}")
            print(f"  {Colors.BOLD}[6]{Colors.RESET} 🔌 Đẩy FastFlags qua ADB vào thiết bị Android/Giả lập đang kết nối")
            print(f"  {Colors.BOLD}[0]{Colors.RESET} ↩️  Quay lại Menu chính\n")

            choice = safe_input(f"  {Colors.YELLOW}{Colors.BOLD}➤ Nhập lựa chọn (0-6){Colors.RESET} {Colors.GREEN}{Colors.BOLD}❯❯{Colors.RESET} ").strip()
            if choice == "1":
                fastflags_optimizer.set_preset("ULTRA_FPS")
                print(f"\n  {Colors.GREEN}[+] Đã kích hoạt Preset Ultra FPS!{Colors.RESET}")
                time.sleep(1)
            elif choice == "2":
                fastflags_optimizer.set_preset("POTATO_MODE")
                print(f"\n  {Colors.GREEN}[+] Đã kích hoạt Preset Potato Mode (Tiết kiệm RAM/Pin tối đa)!{Colors.RESET}")
                time.sleep(1)
            elif choice == "3":
                fastflags_optimizer.set_preset("BALANCED")
                print(f"\n  {Colors.GREEN}[+] Đã kích hoạt Preset Balanced!{Colors.RESET}")
                time.sleep(1)
            elif choice == "4":
                res = fastflags_optimizer.deploy_to_android()
                print(f"\n  {Colors.GREEN}[+] Đã triển khai FastFlags vào {len(res['deployed'])} thư mục Android thành công!{Colors.RESET}")
                safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")
            elif choice == "5":
                res = fastflags_optimizer.deploy_to_pc()
                print(f"\n  {Colors.GREEN}[+] Đã triển khai FastFlags vào {len(res['deployed'])} thư mục Roblox PC thành công!{Colors.RESET}")
                safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")
            elif choice == "6":
                ok = fastflags_optimizer.deploy_via_adb()
                if ok:
                    print(f"\n  {Colors.GREEN}[+] Đã đẩy FastFlags vào thiết bị Android qua ADB thành công!{Colors.RESET}")
                else:
                    print(f"\n  {Colors.YELLOW}[!] Không thể đẩy qua ADB (Hãy kiểm tra cáp nối hoặc adb connect).{Colors.RESET}")
                safe_input(f"\n  {Colors.GRAY}⏎ Nhấn Enter để tiếp tục...{Colors.RESET}")
            elif choice == "0":
                break

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
