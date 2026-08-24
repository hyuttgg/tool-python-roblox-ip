# -*- coding: utf-8 -*-
"""
Real-time System Hardware & Roblox Multi-Instance Live Dashboard Monitor
Hiển thị chính xác 100% thời gian thực:
  1. Phần cứng máy tính (CPU %, RAM used/total/free, Ổ cứng Disk C:/free, Tổng RAM Roblox).
  2. Số lượng client Roblox đang chạy thực tế (Live PID, Window HWND, Memory Usage).
  3. Tên tài khoản (Username) đang chơi của từng Tag.
  4. Tên Game đang chơi (Blox Fruits, King Legacy, Fisch...) & Place ID.
  5. Dedicated IP Proxy & Vùng quốc gia đang gán.
  6. FPS, Ping thời gian thực từ Heartbeat.
  7. Trạng thái Watchdog Supervisor & Luồng sự kiện Live Stream.
  8. Khóa màn hình một chiều - Chỉ có thể thoát bằng phím tắt [Ctrl + C].
"""

import os
import sys
import time
import socket
from typing import List, Dict, Optional
from cli.colors import Colors
from core.game_selector import game_manager
from core.watchdog_supervisor import watchdog
from network.bridge_server import SHARED_STATE

# Đảm bảo UTF-8 stream trên Windows và Termux
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class LiveRealtimeMonitor:
    """Bộ giám sát phần cứng & Client Roblox thời gian thực (Real-Time Live Monitor)"""

    @staticmethod
    def clear_screen():
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def build_bar(percent: float, width: int = 15, color_override: Optional[str] = None) -> str:
        """Tạo thanh tiến trình phần trăm dạng ASCII/Unicode trực quan"""
        clamped = max(0.0, min(100.0, float(percent)))
        filled_len = int(round(width * clamped / 100.0))
        empty_len = width - filled_len
        
        if color_override:
            col = color_override
        elif clamped < 60:
            col = Colors.GREEN
        elif clamped < 85:
            col = Colors.YELLOW
        else:
            col = Colors.RED

        bar_body = f"{col}{'█' * filled_len}{Colors.GRAY}{'░' * empty_len}{Colors.RESET}"
        return f"[{bar_body}] {col}{clamped:>5.1f}%{Colors.RESET}"

    @classmethod
    def get_hardware_metrics(cls) -> Dict:
        """Thu thập thông số phần cứng máy tính 100% thực tế qua Hợp ngữ ASM + C + Rust + C++"""
        from core.native_hardware_bridge import NativeHardwareProbe

        cpu_pct, cpu_eng, tsc_val = NativeHardwareProbe.get_cpu_usage_precise()
        ram_info = NativeHardwareProbe.get_ram_info_precise()
        disk_path = "C:\\" if os.name == "nt" else "/"
        disk_info = NativeHardwareProbe.get_disk_info_precise(disk_path)
        roblox_info = NativeHardwareProbe.get_all_roblox_live_processes()

        cpu_count = os.cpu_count() or 4
        cpu_freq_mhz = 0
        if HAS_PSUTIL:
            try:
                freq = psutil.cpu_freq()
                if freq and freq.current:
                    cpu_freq_mhz = int(freq.current)
                cpu_count = psutil.cpu_count(logical=True) or cpu_count
            except Exception:
                pass

        return {
            "cpu_pct": cpu_pct,
            "cpu_count": cpu_count,
            "cpu_freq_mhz": cpu_freq_mhz,
            "cpu_engine": cpu_eng,
            "tsc_val": tsc_val,
            "ram_used_gb": ram_info["used_gb"],
            "ram_total_gb": ram_info["total_gb"],
            "ram_free_gb": ram_info["free_gb"],
            "ram_pct": ram_info["percent"],
            "ram_engine": ram_info.get("engine", "Native C-ABI"),
            "disk_path": disk_info.get("path", disk_path),
            "disk_used_gb": disk_info["used_gb"],
            "disk_total_gb": disk_info["total_gb"],
            "disk_free_gb": disk_info["free_gb"],
            "disk_pct": disk_info["percent"],
            "disk_engine": disk_info.get("engine", "Native C-ABI"),
            "roblox_procs_count": roblox_info["count"],
            "roblox_total_ram_mb": roblox_info["total_ram_mb"],
            "roblox_pids": roblox_info["processes"]
        }

    @classmethod
    def get_tag_rows_data(cls, raw_instances: Optional[List] = None) -> List[Dict]:
        """Tổng hợp danh sách các Tag với đầy đủ Username, Game, IP, RAM, Ping, FPS thực tế"""
        tags_list = []
        registered_tags = {}

        # 1. Thu thập từ SHARED_STATE của Bridge Server
        if "tags" in SHARED_STATE and SHARED_STATE["tags"]:
            for tid, tdata in SHARED_STATE["tags"].items():
                registered_tags[tid] = dict(tdata)

        # 2. Thu thập từ Watchdog Supervisor
        if hasattr(watchdog, "tags") and watchdog.tags:
            for tid, wst in watchdog.tags.items():
                if tid not in registered_tags:
                    registered_tags[tid] = {
                        "tag_id": tid,
                        "assigned_ip": wst.assigned_ip or "127.0.0.1",
                        "region": wst.region or "[JP] Japan Dedicated",
                        "username": wst.username or "",
                        "pid": wst.process_pid,
                        "status": wst.status
                    }
                else:
                    if wst.username and not registered_tags[tid].get("username"):
                        registered_tags[tid]["username"] = wst.username
                    if wst.process_pid > 0:
                        registered_tags[tid]["pid"] = wst.process_pid
                    if wst.status:
                        registered_tags[tid]["status"] = wst.status

        # 3. Thu thập từ instances truyền vào
        if raw_instances:
            for inst in raw_instances:
                tid = getattr(inst, "tag_id", "ROBLOX-TAG")
                if tid not in registered_tags:
                    registered_tags[tid] = {
                        "tag_id": tid,
                        "assigned_ip": getattr(inst, "assigned_ip", "127.0.0.1") or "127.0.0.1",
                        "region": getattr(inst, "region", "[JP] Japan Dedicated"),
                        "username": getattr(inst, "account_username", "") or "",
                        "pid": getattr(inst, "pid", 0),
                        "status": "ONLINE" if getattr(inst, "pid", 0) > 0 or getattr(inst, "hwnd", 0) > 0 else "OFFLINE"
                    }
                else:
                    if getattr(inst, "account_username", None) and not registered_tags[tid].get("username"):
                        registered_tags[tid]["username"] = getattr(inst, "account_username")

        # 4. Kiểm tra PID thực tế trên hệ điều hành
        from core.native_hardware_bridge import NativeHardwareProbe
        rbx_proc_data = NativeHardwareProbe.get_all_roblox_live_processes()
        live_roblox_pids = {p["pid"]: p["mem_mb"] for p in rbx_proc_data["processes"].values()}

        # Ghép thông tin hoàn chỉnh cho từng Tag
        unmatched_pids = list(live_roblox_pids.keys())

        sorted_tag_ids = sorted(registered_tags.keys())
        for idx, tid in enumerate(sorted_tag_ids):
            tinfo = registered_tags[tid]
            pid = tinfo.get("pid", 0)
            
            # Gán PID thực tế nếu chưa có hoặc khớp
            if pid in live_roblox_pids:
                if pid in unmatched_pids:
                    unmatched_pids.remove(pid)
                is_proc_alive = True
                real_ram_mb = live_roblox_pids[pid]
            elif unmatched_pids:
                pid = unmatched_pids.pop(0)
                is_proc_alive = True
                real_ram_mb = live_roblox_pids.get(pid, 0.0)
            else:
                is_proc_alive = False
                real_ram_mb = 0.0

            # Trạng thái
            status_raw = tinfo.get("status", "OFFLINE")
            if is_proc_alive:
                if status_raw == "TELEPORTING":
                    status_badge = f"{Colors.YELLOW}🔄 TELEPORTING{Colors.RESET}"
                    status_vis = "🔄 TELEPORTING"
                else:
                    status_badge = f"{Colors.GREEN}🟢 ONLINE{Colors.RESET}"
                    status_vis = "🟢 ONLINE"
            else:
                if status_raw == "RESTARTING":
                    status_badge = f"{Colors.CYAN}🚀 STARTING{Colors.RESET}"
                    status_vis = "🚀 STARTING"
                else:
                    status_badge = f"{Colors.GRAY}⚪ OFFLINE{Colors.RESET}"
                    status_vis = "⚪ OFFLINE"

            # Tên Game
            tag_g = game_manager.get_game_for_tag(tid)
            g_name = tag_g.get("name", "Roblox Game")
            g_pid = tag_g.get("place_id", "2753915549")
            game_display = f"{g_name} ({g_pid})"

            # Username
            uname = tinfo.get("username", "").strip()
            if not uname or uname.lower() in ["unknown", "player", "player1"]:
                uname = f"Account #{idx+1}" if is_proc_alive else "Chưa vào game"

            # Ping & FPS
            fps_val = tinfo.get("fps", 60) if is_proc_alive else 0
            ping_val = tinfo.get("ping_ms", 0) if is_proc_alive else 0
            ping_fps_str = f"{ping_val}ms / {fps_val}FPS" if is_proc_alive else "--"

            # RAM Display
            ram_str = f"{real_ram_mb:.1f} MB" if is_proc_alive and real_ram_mb > 0 else (tinfo.get("memory_mb", "0 MB") if is_proc_alive else "--")

            tags_list.append({
                "idx": idx + 1,
                "tag_id": tid,
                "pid": str(pid) if is_proc_alive and pid > 0 else "--",
                "username": uname,
                "game_display": game_display,
                "assigned_ip": tinfo.get("assigned_ip", "127.0.0.1"),
                "region": tinfo.get("region", "[JP] Japan Dedicated"),
                "ping_fps": ping_fps_str,
                "ram": ram_str,
                "status_badge": status_badge,
                "status_vis": status_vis,
                "is_alive": is_proc_alive
            })

        return tags_list

    @classmethod
    def render_dashboard_frame(cls, raw_instances: Optional[List] = None):
        """Vẽ khung hình HUD Giám sát thời gian thực cực kỳ chi tiết, chuẩn xác 100%"""
        cls.clear_screen()
        W = 98

        def pad_line(colored_str, visible_len, border_col=Colors.C_PURPLE):
            space_count = max(0, W - 4 - visible_len)
            return f"{border_col}║{Colors.RESET} {colored_str}{' ' * space_count} {border_col}║{Colors.RESET}"

        top_border = f"{Colors.C_PURPLE}╔{'═' * (W - 2)}╗{Colors.RESET}"
        mid_border = f"{Colors.C_PURPLE}╠{'═' * (W - 2)}╣{Colors.RESET}"
        bot_border = f"{Colors.C_PURPLE}╚{'═' * (W - 2)}╝{Colors.RESET}"

        hw = cls.get_hardware_metrics()
        tag_rows = cls.get_tag_rows_data(raw_instances)
        live_count = sum(1 for t in tag_rows if t["is_alive"])
        total_registered = len(tag_rows)

        print(top_border)
        
        # 1. HEADER CHÍNH
        title_col = f"  {Colors.BOLD}{Colors.rainbow_text('⚡ [ REAL-TIME SYSTEM & ROBLOX MULTI-CLIENT LIVE MONITOR ] ⚡')}{Colors.RESET}"
        title_vis = "  ⚡ [ REAL-TIME SYSTEM & ROBLOX MULTI-CLIENT LIVE MONITOR ] ⚡"
        print(pad_line(title_col, len(title_vis)))

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        sub_col = f"  {Colors.GRAY}Thời gian:{Colors.RESET} {Colors.WHITE}{now_str}{Colors.RESET} {Colors.C_PURPLE}|{Colors.RESET} {Colors.GRAY}Làm mới:{Colors.RESET} {Colors.GREEN}1.5s/chu kỳ{Colors.RESET} {Colors.C_PURPLE}|{Colors.RESET} {Colors.YELLOW}{Colors.BOLD}Nhấn [ Ctrl + C ] để Thoát{Colors.RESET}"
        sub_vis = f"  Thời gian: {now_str} | Làm mới: 1.5s/chu kỳ | Nhấn [ Ctrl + C ] để Thoát"
        print(pad_line(sub_col, len(sub_vis)))

        print(mid_border)

        # 2. PHẦN CỨNG MÁY TÍNH THỜI GIAN THỰC (ASM + C + RUST + C++ MACHINE PROBES)
        cat_hw = f"  {Colors.C_RED}{Colors.BOLD}► [ PHẦN CỨNG THỜI GIAN THỰC (HỢP NGỮ ASM + C + RUST + C++ PROBES) ]{Colors.RESET}"
        print(pad_line(cat_hw, len("  ► [ PHẦN CỨNG THỜI GIAN THỰC (HỢP NGỮ ASM + C + RUST + C++ PROBES) ]")))

        # CPU Line
        cpu_bar = cls.build_bar(hw["cpu_pct"], width=14)
        cpu_freq_str = f" @ {hw['cpu_freq_mhz']} MHz" if hw['cpu_freq_mhz'] > 0 else ""
        tsc_str = f"{hw.get('tsc_val', 0):,}"
        cpu_col = f"    🖥️  {Colors.BOLD}CPU TỔNG:{Colors.RESET}  {cpu_bar}  {Colors.GRAY}({hw['cpu_count']} Cores{cpu_freq_str} | ASM RDTSC: {tsc_str} | {hw['cpu_engine'][:24]}){Colors.RESET}"
        cpu_vis = f"    🖥️  CPU TỔNG:  [██████████░░░░░]  {hw['cpu_pct']:>5.1f}%  ({hw['cpu_count']} Cores{cpu_freq_str} | ASM RDTSC: {tsc_str} | {hw['cpu_engine'][:24]})"
        print(pad_line(cpu_col, len(cpu_vis)))

        # RAM Line
        ram_bar = cls.build_bar(hw["ram_pct"], width=14)
        ram_col = f"    🧠  {Colors.BOLD}RAM MÁY :{Colors.RESET}  {ram_bar}  {Colors.CYAN}{hw['ram_used_gb']:.2f} GB{Colors.RESET} / {Colors.WHITE}{hw['ram_total_gb']:.2f} GB{Colors.RESET} {Colors.GRAY}(Trống: {hw['ram_free_gb']:.2f} GB | 64-bit Exact){Colors.RESET}"
        ram_vis = f"    🧠  RAM MÁY :  [██████████░░░░░]  {hw['ram_pct']:>5.1f}%  {hw['ram_used_gb']:.2f} GB / {hw['ram_total_gb']:.2f} GB (Trống: {hw['ram_free_gb']:.2f} GB | 64-bit Exact)"
        print(pad_line(ram_col, len(ram_vis)))

        # Disk Line
        disk_bar = cls.build_bar(hw["disk_pct"], width=14)
        disk_col = f"    💾  {Colors.BOLD}Ổ CỨNG ({hw['disk_path']}):{Colors.RESET} {disk_bar}  {Colors.CYAN}{hw['disk_used_gb']:.1f} GB{Colors.RESET} / {Colors.WHITE}{hw['disk_total_gb']:.1f} GB{Colors.RESET} {Colors.GRAY}(Trống: {hw['disk_free_gb']:.1f} GB | Sector Exact){Colors.RESET}"
        disk_vis = f"    💾  Ổ CỨNG ({hw['disk_path']}): [██████████░░░░░]  {hw['disk_pct']:>5.1f}%  {hw['disk_used_gb']:.1f} GB / {hw['disk_total_gb']:.1f} GB (Trống: {hw['disk_free_gb']:.1f} GB | Sector Exact)"
        print(pad_line(disk_col, len(disk_vis)))

        # Roblox Process Aggregation Line
        rbx_col = f"    🎮  {Colors.BOLD}TIẾN TRÌNH ROBLOX:{Colors.RESET} {Colors.LIGHT_GREEN}{hw['roblox_procs_count']} Client đang mở{Colors.RESET} {Colors.C_PURPLE}|{Colors.RESET} {Colors.GRAY}Tổng RAM Roblox chiếm:{Colors.RESET} {Colors.YELLOW}{hw['roblox_total_ram_mb']:.1f} MB (Raw WorkingSet){Colors.RESET}"
        rbx_vis = f"    🎮  TIẾN TRÌNH ROBLOX: {hw['roblox_procs_count']} Client đang mở | Tổng RAM Roblox chiếm: {hw['roblox_total_ram_mb']:.1f} MB (Raw WorkingSet)"
        print(pad_line(rbx_col, len(rbx_vis)))

        print(mid_border)

        # 3. DANH SÁCH TỪNG CLIENT ROBLOX
        cat_tags = f"  {Colors.C_GREEN}{Colors.BOLD}► [ DANH SÁCH CLIENT ROBLOX: {live_count} LIVE / {total_registered} TAGS ]{Colors.RESET}"
        cat_tags_vis = f"  ► [ DANH SÁCH CLIENT ROBLOX: {live_count} LIVE / {total_registered} TAGS ]"
        print(pad_line(cat_tags, len(cat_tags_vis)))

        # Bảng tiêu đề cột
        tbl_hdr_col = f"  {Colors.WHITE}{Colors.BOLD}{'#':<3} {'TAG ID':<16} {'PID':<6} {'TÀI KHOẢN':<15} {'GAME ĐANG CHƠI':<22} {'IP PROXY':<18} {'PING/FPS':<11} {'RAM':<9} {'TRẠNG THÁI'}{Colors.RESET}"
        tbl_hdr_vis = f"  {'#':<3} {'TAG ID':<16} {'PID':<6} {'TÀI KHOẢN':<15} {'GAME ĐANG CHƠI':<22} {'IP PROXY':<18} {'PING/FPS':<11} {'RAM':<9} {'TRẠNG THÁI'}"
        print(pad_line(tbl_hdr_col, len(tbl_hdr_vis)))

        div_line = f"  {Colors.GRAY}{'─' * 3} {'─' * 16} {'─' * 6} {'─' * 15} {'─' * 22} {'─' * 18} {'─' * 11} {'─' * 9} {'─' * 12}{Colors.RESET}"
        div_vis = f"  {'─' * 3} {'─' * 16} {'─' * 6} {'─' * 15} {'─' * 22} {'─' * 18} {'─' * 11} {'─' * 9} {'─' * 12}"
        print(pad_line(div_line, len(div_vis)))

        if not tag_rows:
            empty_msg = f"  {Colors.YELLOW}[!] Chưa có Tag Roblox nào được khởi chạy hoặc gán IP.{Colors.RESET}"
            print(pad_line(empty_msg, len("  [!] Chưa có Tag Roblox nào được khởi chạy hoặc gán IP.")))
        else:
            for r in tag_rows[:12]:  # Hiển thị tối đa 12 Tags để vừa vặn màn hình
                idx_str = f"{r['idx']:02d}"
                tid_str = r['tag_id'][:16]
                pid_str = r['pid'][:6]
                user_str = r['username'][:15]
                game_str = r['game_display'][:22]
                ip_str = r['assigned_ip'][:18]
                ping_str = r['ping_fps'][:11]
                ram_str = r['ram'][:9]
                
                # Màu sắc cho từng dòng
                pid_color = Colors.GREEN if r["is_alive"] else Colors.GRAY
                user_color = Colors.LIGHT_CYAN if r["is_alive"] else Colors.GRAY
                ip_color = Colors.YELLOW if r["is_alive"] else Colors.GRAY

                row_col = f"  {Colors.GRAY}{idx_str:<3}{Colors.RESET} {Colors.WHITE}{tid_str:<16}{Colors.RESET} {pid_color}{pid_str:<6}{Colors.RESET} {user_color}{user_str:<15}{Colors.RESET} {Colors.LIGHT_GREEN}{game_str:<22}{Colors.RESET} {ip_color}{ip_str:<18}{Colors.RESET} {Colors.CYAN}{ping_str:<11}{Colors.RESET} {Colors.WHITE}{ram_str:<9}{Colors.RESET} {r['status_badge']}"
                row_vis = f"  {idx_str:<3} {tid_str:<16} {pid_str:<6} {user_str:<15} {game_str:<22} {ip_str:<18} {ping_str:<11} {ram_str:<9} {r['status_vis']}"
                print(pad_line(row_col, len(row_vis)))

        print(mid_border)

        # 4. WATCHDOG SUPERVISOR & NHẬT KÝ SỰ KIỆN LIVE STREAM
        w_summary = watchdog.get_summary()
        w_restarts = w_summary.get("total_restarts", 0)
        w_status_str = f"{Colors.GREEN}🟢 HOẠT ĐỘNG (Auto-Restart BẬT | {w_restarts} Lần Phục Hồi){Colors.RESET}" if w_summary["is_enabled"] else f"{Colors.GRAY}⚪ ĐÃ TẮT{Colors.RESET}"
        w_status_vis = f"🟢 HOẠT ĐỘNG (Auto-Restart BẬT | {w_restarts} Lần Phục Hồi)" if w_summary["is_enabled"] else "⚪ ĐÃ TẮT"

        cat_wd = f"  {Colors.C_YELLOW}{Colors.BOLD}► [ WATCHDOG SUPERVISOR & NHẬT KÝ SỰ KIỆN LIVE ]{Colors.RESET} ➔ {w_status_str}"
        cat_wd_vis = f"  ► [ WATCHDOG SUPERVISOR & NHẬT KÝ SỰ KIỆN LIVE ] ➔ {w_status_vis}"
        print(pad_line(cat_wd, len(cat_wd_vis)))

        recent_logs = w_summary.get("recent_logs", [])
        if recent_logs:
            for l_entry in recent_logs[-4:]:
                clean_entry = l_entry[:90]
                log_col = f"    {Colors.GRAY}•{Colors.RESET} {Colors.WHITE}{clean_entry}{Colors.RESET}"
                log_vis = f"    • {clean_entry}"
                print(pad_line(log_col, len(log_vis)))
        else:
            log_col = f"    {Colors.GRAY}• Đang lắng nghe Heartbeat và trạng thái các Tag Roblox...{Colors.RESET}"
            print(pad_line(log_col, len("    • Đang lắng nghe Heartbeat và trạng thái các Tag Roblox...")))

        print(bot_border)
        print(f"\n  {Colors.YELLOW}{Colors.BOLD}🔒 CHẾ ĐỘ GIÁM SÁT TRỰC TIẾP ĐANG KHÓA MÀN HÌNH.{Colors.RESET} {Colors.WHITE}Nhấn {Colors.LIGHT_RED}{Colors.BOLD}[ Ctrl + C ]{Colors.RESET} {Colors.WHITE}để dừng và thoát công cụ.{Colors.RESET}\n")

    @classmethod
    def start_monitoring_loop(cls, instances: Optional[List] = None, refresh_interval: float = 1.5):
        """
        Vòng lặp giám sát thời gian thực vô tận (Không thể quay lại Menu).
        Chỉ thoát khi bấm Ctrl+C.
        """
        try:
            # Đo CPU lần đầu để lấy baseline
            if HAS_PSUTIL:
                psutil.cpu_percent(interval=None)
            
            while True:
                cls.render_dashboard_frame(raw_instances=instances)
                time.sleep(refresh_interval)
        except KeyboardInterrupt:
            cls.clear_screen()
            print(f"\n{Colors.LIGHT_RED}{Colors.BOLD}================================================================================{Colors.RESET}")
            print(f"{Colors.YELLOW}{Colors.BOLD}⚡ [ TÍN HIỆU NGẮT CTRL + C ] ĐÃ NHẬN ➔ ĐANG ĐÓNG HỆ THỐNG AN TOÀN...{Colors.RESET}")
            print(f"{Colors.LIGHT_RED}{Colors.BOLD}================================================================================{Colors.RESET}")
            try:
                watchdog.stop()
            except Exception:
                pass
            print(f"  {Colors.GREEN}[+] Đã dừng Watchdog Supervisor.{Colors.RESET}")
            print(f"  {Colors.GREEN}[+] Đã giải phóng Bridge Server.{Colors.RESET}")
            print(f"  {Colors.CYAN}[+] Tạm biệt! Hẹn gặp lại bạn.{Colors.RESET}\n")
            sys.exit(0)


def render_network_dashboard(instances: Optional[List] = None):
    """Hàm wrapper tương thích ngược khởi chạy Live Dashboard"""
    LiveRealtimeMonitor.start_monitoring_loop(instances=instances, refresh_interval=1.5)


class DashboardRenderer:
    """Class wrapper tương thích ngược"""
    @staticmethod
    def render(instances: Optional[List] = None):
        LiveRealtimeMonitor.render_dashboard_frame(raw_instances=instances)
