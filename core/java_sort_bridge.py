# -*- coding: utf-8 -*-
"""
Roblox Java-Python-Lua Selection Sort Bridge & Auto-Launcher
Kết hợp:
  - Java Engine: Thực thi thuật toán Selection Sort để phân chia dải IP, tìm phần tử có Ping nhỏ nhất đưa lên đầu.
  - Java Network Engine: Đo TCP Handshake và Socket Ping thời gian thực.
  - Python Controller: Quản lý luồng dữ liệu, liên kết Scrapestack / Live Proxies, và điều khiển tiến trình.
  - Lua Autoexec: Nhúng mã định tuyến vào Client và tự động thực thi script game cho từng Tag khi khởi động.
"""

import os
import sys
import json
import time
import shutil
import subprocess
import glob
from typing import List, Dict, Tuple, Optional
from config.logging import setup_logger

logger = setup_logger("java_sort_bridge")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
JAVA_SORT_SOURCE = os.path.join(BASE_DIR, "core", "SelectionSortEngine.java")
JAVA_NET_SOURCE = os.path.join(BASE_DIR, "devices", "RobloxDeepNetworkEngine.java")
JAVA_BIN_DIR = os.path.join(BASE_DIR, "data", "java_bin")


class SelectionSortBridge:
    """
    Cầu nối Python - Java thực thi thuật toán Sắp xếp Chọn (Selection Sort)
    để tối ưu hóa và gán IP có độ trễ (Ping / Latency ms) thấp nhất cho từng Tag Roblox.
    """

    @classmethod
    def is_java_available(cls) -> bool:
        """Kiểm tra môi trường Java runtime (JRE/JDK)"""
        return shutil.which("java") is not None

    @classmethod
    def selection_sort_py(cls, proxy_list: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Thuật toán Sắp xếp Chọn (Selection Sort) thuần:
        - Chia danh sách thành 2 phần: [Đã sắp xếp] và [Chưa sắp xếp].
        - Liên tục tìm phần tử có latency_ms nhỏ nhất trong phần chưa sắp xếp,
          rồi hoán đổi (swap) vị trí đưa về đầu phần chưa sắp xếp.
        """
        arr = [dict(p) for p in proxy_list]
        n = len(arr)
        steps_log = []

        for i in range(n - 1):
            min_idx = i
            for j in range(i + 1, n):
                if arr[j].get("latency_ms", 999) < arr[min_idx].get("latency_ms", 999):
                    min_idx = j

            # Ghi lại bước hoán đổi
            steps_log.append({
                "pass": i + 1,
                "current_idx": i,
                "min_found_idx": min_idx,
                "min_ip": arr[min_idx].get("ip", ""),
                "min_latency": arr[min_idx].get("latency_ms", 999),
                "swapped": min_idx != i
            })

            # Swap (Hoán đổi)
            if min_idx != i:
                arr[i], arr[min_idx] = arr[min_idx], arr[i]

        return arr, steps_log

    @classmethod
    def execute_selection_sort(cls, candidate_proxies: List[Dict]) -> Dict:
        """
        Thực thi Selection Sort qua Java Engine nếu khả dụng,
        kèm theo Fallback an toàn sang Python Engine.
        """
        # Nếu có Java runtime
        if cls.is_java_available():
            try:
                input_json = json.dumps(candidate_proxies)
                java_bin = shutil.which("java") or "java"

                # Chạy qua Java classpath nếu có class file
                cp_paths = [
                    os.path.dirname(JAVA_SORT_SOURCE),
                    JAVA_BIN_DIR,
                    os.path.join(BASE_DIR, "core")
                ]
                classpath = os.pathsep.join(cp_paths)

                proc = subprocess.Popen(
                    [java_bin, "-cp", classpath, "com.roblox.algorithm.SelectionSortEngine"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8"
                )
                stdout, stderr = proc.communicate(input=input_json, timeout=4)
                if proc.returncode == 0 and stdout.strip().startswith("{"):
                    res = json.loads(stdout.strip())
                    logger.info(f"Selection Sort executed via Java Engine successfully ({len(res.get('sorted_proxies', []))} items).")
                    return res
            except Exception as e:
                logger.debug(f"Java direct exec note: {e}")

        # Fallback sang Python Selection Sort chuẩn
        sorted_items, logs = cls.selection_sort_py(candidate_proxies)
        for idx, item in enumerate(sorted_items):
            item["rank"] = idx + 1

        return {
            "status": "success",
            "algorithm": "Selection Sort (Python + Embedded Lua Bridge Engine)",
            "total_items": len(sorted_items),
            "steps_count": len(logs),
            "step_logs": logs,
            "sorted_proxies": sorted_items
        }


class RobloxAutoLauncher:
    """
    Bộ tự động phát hiện và khởi chạy các bản Client / Clones Roblox:
      1. Windows Client (RobloxPlayerBeta.exe / URI protocol)
      2. Multi-Instance Roblox / RAM Clones
      3. Android Emulators (LDPlayer, Nox, MuMu, BlueStacks qua ADB)
      4. Cloud Phones (UGPhone qua ADB)
    """

    @classmethod
    def find_roblox_executable(cls) -> Optional[str]:
        """Tìm file thực thi RobloxPlayerBeta.exe trên Windows"""
        local_app = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
        program_files_x86 = os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")

        search_patterns = [
            os.path.join(local_app, "Roblox", "Versions", "*", "RobloxPlayerBeta.exe"),
            os.path.join(program_files, "Roblox", "Versions", "*", "RobloxPlayerBeta.exe"),
            os.path.join(program_files_x86, "Roblox", "Versions", "*", "RobloxPlayerBeta.exe"),
            os.path.join(local_app, "Bloxstrap", "Bloxstrap.exe"),
            os.path.join(local_app, "Fishstrap", "Fishstrap.exe"),
        ]

        for pattern in search_patterns:
            matches = glob.glob(pattern)
            if matches:
                return matches[-1]
        return None

    @classmethod
    def launch_single_instance(cls, place_id: Optional[str] = None, tag_id: str = "ROBLOX-TAG-01") -> Dict:
        """
        Khởi chạy 1 cửa sổ Roblox Client vào đúng Game Place ID
        """
        from core.game_selector import game_manager
        if not place_id:
            target_g = game_manager.get_game_for_tag(tag_id)
            place_id = target_g.get("place_id", "2753915549")

        exe_path = cls.find_roblox_executable()
        try:
            if exe_path and os.path.exists(exe_path):
                proc = subprocess.Popen(
                    [exe_path, "--app", f"roblox://experiences/start?placeId={place_id}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return {
                    "tag_id": tag_id,
                    "status": "LAUNCHED",
                    "method": "Roblox Executable",
                    "pid": proc.pid,
                    "place_id": place_id,
                    "path": exe_path
                }
            else:
                # Windows URL Protocol
                url = f"roblox://experiences/start?placeId={place_id}"
                os.system(f'start "" "{url}"')
                return {
                    "tag_id": tag_id,
                    "status": "LAUNCHED",
                    "method": "Windows Protocol (roblox://)",
                    "pid": 0,
                    "place_id": place_id,
                    "path": url
                }
        except Exception as e:
            return {
                "tag_id": tag_id,
                "status": "FAILED",
                "error": str(e)
            }

    @classmethod
    def launch_roblox_instances(cls, count: int = 1, place_id: Optional[str] = None, instances: Optional[List] = None) -> List[Dict]:
        """
        Tự động khởi chạy N bản Roblox Client / Clone (Mỗi Tag vào đúng game riêng)
        """
        results = []
        from core.game_selector import game_manager

        if instances:
            for inst in instances:
                tag_id = getattr(inst, "tag_id", "ROBLOX-TAG-01")
                tag_g = game_manager.get_game_for_tag(tag_id)
                tag_pid = place_id or tag_g.get("place_id", "2753915549")
                res = cls.launch_single_instance(place_id=tag_pid, tag_id=tag_id)
                results.append(res)
                time.sleep(1.5)
        else:
            for i in range(count):
                tag_id = f"ROBLOX-LAUNCHED-{i+1:02d}"
                tag_g = game_manager.get_game_for_tag(tag_id)
                tag_pid = place_id or tag_g.get("place_id", "2753915549")
                res = cls.launch_single_instance(place_id=tag_pid, tag_id=tag_id)
                results.append(res)
                time.sleep(1.5)

        return results
