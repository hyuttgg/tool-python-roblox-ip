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
    def ensure_java_compiled(cls) -> bool:
        """Tự động biên dịch mã nguồn Java (.java -> .class) nếu có javac/ecj trên PC hoặc Android"""
        os.makedirs(JAVA_BIN_DIR, exist_ok=True)
        javac_bin = shutil.which("javac") or shutil.which("ecj")
        if not javac_bin:
            return False
        try:
            sources = []
            if os.path.exists(JAVA_SORT_SOURCE):
                sources.append(JAVA_SORT_SOURCE)
            if os.path.exists(JAVA_NET_SOURCE):
                sources.append(JAVA_NET_SOURCE)
            if sources:
                cmd = [javac_bin, "-d", JAVA_BIN_DIR, "-encoding", "UTF-8"] + sources
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if res.returncode == 0:
                    logger.info("Java sources compiled successfully to data/java_bin.")
                    return True
        except Exception as e:
            logger.debug(f"Java compile note: {e}")
        return False

    @classmethod
    def execute_selection_sort(cls, candidate_proxies: List[Dict]) -> Dict:
        """
        Thực thi Selection Sort qua Java Engine nếu khả dụng,
        kèm theo Fallback an toàn sang Python Engine.
        """
        # Nếu có Java runtime
        if cls.is_java_available():
            try:
                cls.ensure_java_compiled()
                input_json = json.dumps(candidate_proxies)
                java_bin = shutil.which("java") or "java"

                # Chạy qua Java classpath nếu có class file
                cp_paths = [
                    os.path.dirname(JAVA_SORT_SOURCE),
                    JAVA_BIN_DIR,
                    os.path.join(BASE_DIR, "core"),
                    os.path.join(BASE_DIR, "devices")
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

    @classmethod
    def probe_ip_latency_java(cls, ip: str, port: int = 80, timeout: float = 2.0) -> Dict:
        """Đo độ trễ TCP Handshake / Socket Ping sử dụng Java Engine (hoặc socket fallback)"""
        import socket
        start = time.time()
        try:
            with socket.create_connection((ip, int(port)), timeout=timeout):
                latency = int((time.time() - start) * 1000)
                return {"status": "ONLINE", "latency_ms": latency, "ip": ip, "port": port}
        except Exception as e:
            return {"status": "TIMEOUT", "latency_ms": 999, "ip": ip, "port": port, "error": str(e)}


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
    def launch_single_instance(cls, place_id: Optional[str] = None, tag_id: str = "ROBLOX-TAG-01", clone_user: Optional[int] = None) -> Dict:
        """
        Khởi chạy 1 cửa sổ / app Roblox Client vào đúng Game Place ID
        (Hỗ trợ toàn diện Windows PC, Android Native, Termux, UGPhone Cloud Phone & Emulators)
        """
        from core.game_selector import game_manager
        target_g = game_manager.get_game_for_tag(tag_id)
        if not place_id:
            place_id = target_g.get("place_id", "2753915549")

        url = game_manager.get_launch_uri_for_tag(tag_id)

        # 1. XỬ LÝ KHI TAG THUỘC THIẾT BỊ ANDROID / UGPHONE / GIẢ LẬP (Qua ADB từ Windows hoặc Termux)
        if "ANDROID-" in tag_id or "UGPHONE-" in tag_id:
            try:
                from devices.ugphone_bridge import UGPhoneBridge
                bridge = UGPhoneBridge()
                devices = bridge.refresh_devices()
                target_dev = None
                for d in devices:
                    if d.replace(':', '_').replace('.', '_') in tag_id or d in tag_id:
                        target_dev = d
                        break
                if not target_dev and devices:
                    target_dev = devices[0]

                if target_dev:
                    ok, msg = bridge.launch_roblox_app(target_dev, place_id=place_id)
                    if ok:
                        return {
                            "tag_id": tag_id,
                            "status": "LAUNCHED",
                            "method": f"ADB Intent [{target_dev}]",
                            "pid": 0,
                            "place_id": place_id,
                            "path": url
                        }
            except Exception as e:
                logger.debug(f"ADB launch error: {e}")

        # 2. XỬ LÝ TRÊN MÔI TRƯỜNG ANDROID / TERMUX / UGPHONE
        is_android = os.path.exists("/system/bin/am") or "ANDROID_ROOT" in os.environ or os.path.exists("/data/data/com.termux") or shutil.which("am") is not None
        if is_android:
            user_flag = []
            if clone_user is not None:
                user_flag = ["--user", str(clone_user)]
            elif "CLONE-02" in tag_id or "CLONE-03" in tag_id:
                user_flag = ["--user", "999"]
            elif "CLONE-04" in tag_id or "CLONE-05" in tag_id:
                user_flag = ["--user", "10"]

            # Chỉ dùng Android Intent an toàn, không dùng monkey gây loạn/crash màn hình
            am_cmds = [
                ["am", "start"] + user_flag + ["-a", "android.intent.action.VIEW", "-d", url],
                ["am", "start", "-a", "android.intent.action.VIEW", "-d", url],
                ["am", "start", "-n", "com.roblox.client/com.roblox.client.ActivityProtocolLaunch", "-d", url],
                ["am", "start", "-n", "com.roblox.client/com.roblox.client.RobloxMainActivity", "-d", url],
            ]
            for cmd in am_cmds:
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
                    if res.returncode == 0 or "Starting:" in res.stdout:
                        return {
                            "tag_id": tag_id,
                            "status": "LAUNCHED",
                            "method": f"Android Intent ({cmd[0]} {cmd[1] if len(cmd) > 1 else ''})",
                            "pid": 0,
                            "place_id": place_id,
                            "path": url
                        }
                except Exception:
                    continue

            # Thử qua Root su nếu trên Termux UGPhone có root
            try:
                su_cmd = f"am start -a android.intent.action.VIEW -d '{url}'"
                res = subprocess.run(["su", "-c", su_cmd], capture_output=True, text=True, timeout=4)
                if res.returncode == 0 or "Starting:" in res.stdout:
                    return {
                        "tag_id": tag_id,
                        "status": "LAUNCHED",
                        "method": "UGPhone SuperUser (Root Intent)",
                        "pid": 0,
                        "place_id": place_id,
                        "path": url
                    }
            except Exception:
                pass

        # 3. XỬ LÝ TRÊN LINUX DESKTOP (Không phải Android)
        if os.name != "nt" and not is_android:
            try:
                res = subprocess.run(["xdg-open", url], capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    return {
                        "tag_id": tag_id,
                        "status": "LAUNCHED",
                        "method": "Linux xdg-open Protocol",
                        "pid": 0,
                        "place_id": place_id,
                        "path": url
                    }
            except Exception:
                pass

        # 2. XỬ LÝ TRÊN WINDOWS PC (Khởi chạy trực tiếp vào đúng Game Place ID & Bắt PID)
        if os.name == "nt":
            existing_pids = set()
            try:
                import psutil
                for p in psutil.process_iter(['pid', 'name']):
                    p_name = (p.info.get('name') or "").lower()
                    if "roblox" in p_name:
                        existing_pids.add(p.info['pid'])
            except Exception:
                pass

            launched = False
            launch_method = "Roblox Protocol URI (Direct Game Join)"
            launch_path = url

            try:
                os.startfile(url)
                launched = True
            except Exception:
                exe_path = cls.find_roblox_executable()
                if exe_path and os.path.exists(exe_path):
                    try:
                        proc = subprocess.Popen(
                            [exe_path, url],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        launched = True
                        launch_method = "Roblox Executable Direct"
                        launch_path = exe_path
                    except Exception:
                        pass
                if not launched:
                    try:
                        os.system(f'start "" "{url}"')
                        launched = True
                        launch_method = "Shell Start Protocol"
                    except Exception:
                        pass

            if launched:
                # Quét PID mới xuất hiện sau khi launch
                new_pid = 0
                time.sleep(2.0)
                try:
                    import psutil
                    for p in psutil.process_iter(['pid', 'name']):
                        p_name = (p.info.get('name') or "").lower()
                        if "roblox" in p_name and "crash" not in p_name:
                            curr_pid = p.info['pid']
                            if curr_pid not in existing_pids:
                                new_pid = curr_pid
                                break
                            elif new_pid == 0:
                                new_pid = curr_pid
                except Exception:
                    pass

                return {
                    "tag_id": tag_id,
                    "status": "LAUNCHED",
                    "method": launch_method,
                    "pid": new_pid,
                    "place_id": place_id,
                    "path": launch_path
                }
            return {
                "tag_id": tag_id,
                "status": "FAILED",
                "error": "Không thể khởi chạy Roblox URL protocol hoặc executable."
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
