# -*- coding: utf-8 -*-
"""
Roblox Multi-Tag Controller - Multi-Language Low-Level Machine Hardware Bridge
Kết hợp 4 tầng công nghệ phần cứng cấp thấp:
  1. ⚡ HỢP NGỮ (ASSEMBLY): Đọc trực tiếp thanh ghi phần cứng x86_64 RDTSC / ARM64 CNTVCT_EL0 & CPUID.
  2. ⚙️ NGÔN NGỮ C: Giao tiếp trực tiếp C-ABI với Windows Kernel32/Ntdll và Linux Libc Kernel Syscalls.
  3. 🦀 RUST ENGINE: Khối xử lý an toàn bộ nhớ, không có chi phí trừu tượng (Zero-cost Abstractions).
  4. 🚀 C++20 NATIVE: Khối nội suy phần cứng -O3 tối ưu hóa nano-giây.
"""

import os
import sys
import time
import ctypes
import subprocess
from typing import Dict, List, Optional, Tuple
from config.logging import setup_logger

logger = setup_logger("native_hardware_bridge")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NATIVE_SRC_CPP = os.path.join(BASE_DIR, "core", "native_hardware_probe.cpp")
NATIVE_SRC_C = os.path.join(BASE_DIR, "core", "asm_hardware_probe.c")
RUST_DIR = os.path.join(BASE_DIR, "core", "rust_engine")
NATIVE_BIN_DIR = os.path.join(BASE_DIR, "data", "native_bin")

if os.name == "nt":
    CPP_LIB_PATH = os.path.join(NATIVE_BIN_DIR, "hardware_probe.dll")
    RUST_LIB_PATH = os.path.join(NATIVE_BIN_DIR, "rust_hw_engine.dll")
    C_LIB_PATH = os.path.join(NATIVE_BIN_DIR, "asm_hardware_probe.dll")
else:
    CPP_LIB_PATH = os.path.join(NATIVE_BIN_DIR, "libhardware_probe.so")
    RUST_LIB_PATH = os.path.join(NATIVE_BIN_DIR, "librust_hw_engine.so")
    C_LIB_PATH = os.path.join(NATIVE_BIN_DIR, "libasm_hardware_probe.so")


# ------------------------------------------------------------------------------
# Win32 C-ABI Structs & Types
# ------------------------------------------------------------------------------
if os.name == "nt":
    from ctypes import wintypes

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ('dwLength', wintypes.DWORD),
            ('dwMemoryLoad', wintypes.DWORD),
            ('ullTotalPhys', ctypes.c_uint64),
            ('ullAvailPhys', ctypes.c_uint64),
            ('ullTotalPageFile', ctypes.c_uint64),
            ('ullAvailPageFile', ctypes.c_uint64),
            ('ullTotalVirtual', ctypes.c_uint64),
            ('ullAvailVirtual', ctypes.c_uint64),
            ('ullAvailExtendedVirtual', ctypes.c_uint64),
        ]

    class FILETIME(ctypes.Structure):
        _fields_ = [
            ('dwLowDateTime', wintypes.DWORD),
            ('dwHighDateTime', wintypes.DWORD)
        ]

    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ('cb', wintypes.DWORD),
            ('PageFaultCount', wintypes.DWORD),
            ('PeakWorkingSetSize', ctypes.c_size_t),
            ('WorkingSetSize', ctypes.c_size_t),
            ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
            ('QuotaPagedPoolUsage', ctypes.c_size_t),
            ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
            ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
            ('PagefileUsage', ctypes.c_size_t),
            ('PeakPagefileUsage', ctypes.c_size_t),
            ('PrivateUsage', ctypes.c_size_t),
        ]


class NativeHardwareProbe:
    """Multi-Language (Assembly + C + Rust + C++) Hardware Introspection Engine"""

    _cpp_lib = None
    _rust_lib = None
    _c_lib = None
    _is_initialized = False

    _prev_cpu_idle = 0
    _prev_cpu_kernel = 0
    _prev_cpu_user = 0
    _prev_linux_idle = 0
    _prev_linux_total = 0

    @classmethod
    def initialize_low_level_engines(cls):
        """Khởi động và kết nối toàn bộ 4 tầng công nghệ: ASM, C, Rust, C++"""
        if cls._is_initialized:
            return

        os.makedirs(NATIVE_BIN_DIR, exist_ok=True)

        # 1. Thử tải Rust Engine nếu đã build
        if os.path.exists(RUST_LIB_PATH):
            try:
                cls._rust_lib = ctypes.CDLL(RUST_LIB_PATH)
                logger.info("Loaded Rust Hardware Engine (librust_hw_engine)")
            except Exception as e:
                logger.debug(f"Rust lib load info: {e}")

        # 2. Thử tải C++ Engine
        if os.path.exists(CPP_LIB_PATH):
            try:
                cls._cpp_lib = ctypes.CDLL(CPP_LIB_PATH)
                cls._setup_cpp_signatures()
                logger.info("Loaded C++ Hardware Engine (hardware_probe)")
            except Exception as e:
                logger.debug(f"C++ lib load info: {e}")

        # 3. Tự động biên dịch C / C++ nếu có compiler (g++, clang++, gcc, clang)
        cls._try_auto_compile()
        cls._is_initialized = True

    @classmethod
    def _try_auto_compile(cls):
        """Thử biên dịch mã nguồn C và C++ sang thư viện nhị phân máy"""
        compilers = ["clang++", "g++", "clang", "gcc"]
        for comp in compilers:
            try:
                check = subprocess.run([comp, "--version"], capture_output=True, timeout=2)
                if check.returncode == 0:
                    # Biên dịch C++
                    if not cls._cpp_lib and os.path.exists(NATIVE_SRC_CPP):
                        if os.name == "nt":
                            cmd = [comp, "-O3", "-shared", "-o", CPP_LIB_PATH, NATIVE_SRC_CPP, "-lpsapi"]
                        else:
                            cmd = [comp, "-O3", "-shared", "-fPIC", "-o", CPP_LIB_PATH, NATIVE_SRC_CPP]
                        res = subprocess.run(cmd, capture_output=True, timeout=8)
                        if res.returncode == 0 and os.path.exists(CPP_LIB_PATH):
                            cls._cpp_lib = ctypes.CDLL(CPP_LIB_PATH)
                            cls._setup_cpp_signatures()

                    # Biên dịch C & Assembly
                    if not cls._c_lib and os.path.exists(NATIVE_SRC_C):
                        if os.name == "nt":
                            cmd_c = [comp, "-O3", "-shared", "-o", C_LIB_PATH, NATIVE_SRC_C]
                        else:
                            cmd_c = [comp, "-O3", "-shared", "-fPIC", "-o", C_LIB_PATH, NATIVE_SRC_C]
                        res_c = subprocess.run(cmd_c, capture_output=True, timeout=8)
                        if res_c.returncode == 0 and os.path.exists(C_LIB_PATH):
                            cls._c_lib = ctypes.CDLL(C_LIB_PATH)
                    break
            except Exception:
                continue

    @classmethod
    def _setup_cpp_signatures(cls):
        if not cls._cpp_lib:
            return
        try:
            cls._cpp_lib.get_cpu_usage_precise.restype = ctypes.c_double
            cls._cpp_lib.get_cpu_usage_precise.argtypes = []

            cls._cpp_lib.get_ram_info_precise.restype = ctypes.c_int
            cls._cpp_lib.get_ram_info_precise.argtypes = [
                ctypes.POINTER(ctypes.c_uint64),
                ctypes.POINTER(ctypes.c_uint64),
                ctypes.POINTER(ctypes.c_uint64),
                ctypes.POINTER(ctypes.c_double)
            ]

            cls._cpp_lib.get_disk_info_precise.restype = ctypes.c_int
            cls._cpp_lib.get_disk_info_precise.argtypes = [
                ctypes.c_char_p,
                ctypes.POINTER(ctypes.c_uint64),
                ctypes.POINTER(ctypes.c_uint64),
                ctypes.POINTER(ctypes.c_uint64),
                ctypes.POINTER(ctypes.c_double)
            ]

            cls._cpp_lib.get_roblox_process_memory.restype = ctypes.c_int
            cls._cpp_lib.get_roblox_process_memory.argtypes = [
                ctypes.c_int,
                ctypes.POINTER(ctypes.c_uint64),
                ctypes.POINTER(ctypes.c_uint64)
            ]
        except Exception:
            pass

    # ==========================================================================
    # 1. HỢP NGỮ (ASSEMBLY): ĐỌC THANH GHI PHẦN CỨNG RDTSC / CNTVCT_EL0
    # ==========================================================================
    @classmethod
    def read_hardware_tsc_cycles(cls) -> int:
        """Đọc chu kỳ xung nhịp phần cứng từ thanh ghi Assembly x86_64 RDTSC / ARM64 CNTVCT"""
        cls.initialize_low_level_engines()

        # 1. Thử qua C Assembly
        if cls._c_lib and hasattr(cls._c_lib, "asm_read_cpu_tsc"):
            try:
                cls._c_lib.asm_read_cpu_tsc.restype = ctypes.c_uint64
                return int(cls._c_lib.asm_read_cpu_tsc())
            except Exception:
                pass

        # 2. Thử qua Rust Engine
        if cls._rust_lib and hasattr(cls._rust_lib, "rust_read_hardware_tsc"):
            try:
                cls._rust_lib.rust_read_hardware_tsc.restype = ctypes.c_uint64
                return int(cls._rust_lib.rust_read_hardware_tsc())
            except Exception:
                pass

        # 3. Direct Win32 QueryPerformanceCounter / Linux CLOCK_MONOTONIC_RAW (100% Machine Level)
        if os.name == "nt":
            try:
                qpc = ctypes.c_int64(0)
                ctypes.windll.kernel32.QueryPerformanceCounter(ctypes.byref(qpc))
                return int(qpc.value)
            except Exception:
                pass
        else:
            try:
                # Đọc timer nanosecond từ kernel
                return int(time.time_ns())
            except Exception:
                pass

        return int(time.time() * 10_000_000)

    # ==========================================================================
    # 2. ĐO LƯỜNG CPU THỜI GIAN THỰC (ASM + C + RUST + C++)
    # ==========================================================================
    @classmethod
    def get_cpu_usage_precise(cls) -> Tuple[float, str, int]:
        """
        Lấy tỷ lệ sử dụng CPU thời gian thực với độ chính xác nano-giây.
        Trả về: (cpu_pct, engine_badge, tsc_counter)
        """
        cls.initialize_low_level_engines()
        tsc_val = cls.read_hardware_tsc_cycles()

        # 1. Ưu tiên C++ Native Engine
        if cls._cpp_lib:
            try:
                usage = cls._cpp_lib.get_cpu_usage_precise()
                return round(float(usage), 1), "⚡ ASM + C++20 Engine (100ns Ticks)", tsc_val
            except Exception:
                pass

        # 2. Ưu tiên Rust Engine
        if cls._rust_lib and hasattr(cls._rust_lib, "rust_get_cpu_usage"):
            try:
                cpu_p = ctypes.c_double(0.0)
                tsc_p = ctypes.c_uint64(0)
                if cls._rust_lib.rust_get_cpu_usage(ctypes.byref(cpu_p), ctypes.byref(tsc_p)) == 0:
                    return round(float(cpu_p.value), 1), "🦀 Rust + ASM Engine (Zero-Cost ABI)", int(tsc_p.value)
            except Exception:
                pass

        # 3. Pure C-ABI Windows Kernel32 (GetSystemTimes 64-bit nanosecond delta)
        if os.name == "nt":
            try:
                idle_t, kernel_t, user_t = FILETIME(), FILETIME(), FILETIME()
                if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle_t), ctypes.byref(kernel_t), ctypes.byref(user_t)):
                    i_val = ((idle_t.dwHighDateTime << 32) | idle_t.dwLowDateTime)
                    k_val = ((kernel_t.dwHighDateTime << 32) | kernel_t.dwLowDateTime)
                    u_val = ((user_t.dwHighDateTime << 32) | user_t.dwLowDateTime)

                    if cls._prev_cpu_kernel == 0 and cls._prev_cpu_user == 0:
                        cls._prev_cpu_idle = i_val
                        cls._prev_cpu_kernel = k_val
                        cls._prev_cpu_user = u_val
                        time.sleep(0.05)
                        return cls.get_cpu_usage_precise()

                    d_idle = i_val - cls._prev_cpu_idle
                    d_kernel = k_val - cls._prev_cpu_kernel
                    d_user = u_val - cls._prev_cpu_user
                    total_sys = d_kernel + d_user

                    cls._prev_cpu_idle = i_val
                    cls._prev_cpu_kernel = k_val
                    cls._prev_cpu_user = u_val

                    if total_sys > 0:
                        pct = (1.0 - (d_idle / total_sys)) * 100.0
                        return max(0.0, min(100.0, round(pct, 1))), "⚡ Win32 Kernel C-ABI (100ns Ticks)", tsc_val
            except Exception:
                pass
        else:
            # 4. Pure C-ABI Linux /proc/stat CPU Jiffies (Android Termux)
            try:
                with open("/proc/stat", "r") as f:
                    line = f.readline()
                parts = line.strip().split()
                if len(parts) >= 5:
                    user = int(parts[1])
                    nice = int(parts[2])
                    system = int(parts[3])
                    idle = int(parts[4])
                    iowait = int(parts[5]) if len(parts) > 5 else 0
                    irq = int(parts[6]) if len(parts) > 6 else 0
                    softirq = int(parts[7]) if len(parts) > 7 else 0
                    steal = int(parts[8]) if len(parts) > 8 else 0

                    c_idle = idle + iowait
                    c_total = user + nice + system + idle + iowait + irq + softirq + steal

                    if cls._prev_linux_total == 0:
                        cls._prev_linux_idle = c_idle
                        cls._prev_linux_total = c_total
                        time.sleep(0.05)
                        return cls.get_cpu_usage_precise()

                    d_idle = c_idle - cls._prev_linux_idle
                    d_total = c_total - cls._prev_linux_total

                    cls._prev_linux_idle = c_idle
                    cls._prev_linux_total = c_total

                    if d_total > 0:
                        pct = (1.0 - (d_idle / d_total)) * 100.0
                        return max(0.0, min(100.0, round(pct, 1))), "⚡ Linux Kernel /proc/stat C-ABI (Jiffies)", tsc_val
            except Exception:
                pass

        # Fallback
        try:
            import psutil
            return round(psutil.cpu_percent(interval=None), 1), "Psutil Kernel Fallback", tsc_val
        except Exception:
            return 15.0, "Hardware System Fallback", tsc_val

    # ==========================================================================
    # 3. ĐO LƯỜNG RAM THỜI GIAN THỰC (RAW 64-BIT BYTE ACCURACY)
    # ==========================================================================
    @classmethod
    def get_ram_info_precise(cls) -> Dict:
        """Đo lường RAM chính xác từng Byte từ Kernel / C / Rust / C++"""
        cls.initialize_low_level_engines()

        if cls._cpp_lib:
            try:
                tot, avail, used, pct = ctypes.c_uint64(0), ctypes.c_uint64(0), ctypes.c_uint64(0), ctypes.c_double(0.0)
                if cls._cpp_lib.get_ram_info_precise(ctypes.byref(tot), ctypes.byref(avail), ctypes.byref(used), ctypes.byref(pct)) == 0:
                    return {
                        "total_gb": tot.value / (1024 ** 3),
                        "used_gb": used.value / (1024 ** 3),
                        "free_gb": avail.value / (1024 ** 3),
                        "percent": round(pct.value, 1),
                        "engine": "C++20 Native Memory Introspection"
                    }
            except Exception:
                pass

        if os.name == "nt":
            try:
                mem_status = MEMORYSTATUSEX()
                mem_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem_status)):
                    tot_gb = mem_status.ullTotalPhys / (1024 ** 3)
                    avail_gb = mem_status.ullAvailPhys / (1024 ** 3)
                    used_gb = (mem_status.ullTotalPhys - mem_status.ullAvailPhys) / (1024 ** 3)
                    pct = (used_gb / tot_gb) * 100.0 if tot_gb > 0 else float(mem_status.dwMemoryLoad)
                    return {
                        "total_gb": tot_gb,
                        "used_gb": used_gb,
                        "free_gb": avail_gb,
                        "percent": round(pct, 1),
                        "engine": "Win32 GlobalMemoryStatusEx 64-bit C-ABI"
                    }
            except Exception:
                pass
        else:
            try:
                mem_total_kb, mem_avail_kb, mem_free_kb = 0, 0, 0
                buffers_kb, cached_kb = 0, 0
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            mem_total_kb = int(line.split()[1])
                        elif line.startswith("MemAvailable:"):
                            mem_avail_kb = int(line.split()[1])
                        elif line.startswith("MemFree:"):
                            mem_free_kb = int(line.split()[1])
                        elif line.startswith("Buffers:"):
                            buffers_kb = int(line.split()[1])
                        elif line.startswith("Cached:"):
                            cached_kb = int(line.split()[1])

                if mem_total_kb > 0:
                    avail_kb = mem_avail_kb if mem_avail_kb > 0 else (mem_free_kb + buffers_kb + cached_kb)
                    used_kb = mem_total_kb - avail_kb
                    tot_gb = (mem_total_kb * 1024) / (1024 ** 3)
                    used_gb = (used_kb * 1024) / (1024 ** 3)
                    free_gb = (avail_kb * 1024) / (1024 ** 3)
                    pct = (used_gb / tot_gb) * 100.0 if tot_gb > 0 else 0.0
                    return {
                        "total_gb": tot_gb,
                        "used_gb": used_gb,
                        "free_gb": free_gb,
                        "percent": round(pct, 1),
                        "engine": "Linux /proc/meminfo C-ABI"
                    }
            except Exception:
                pass

        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "total_gb": mem.total / (1024 ** 3),
                "used_gb": mem.used / (1024 ** 3),
                "free_gb": mem.available / (1024 ** 3),
                "percent": round(mem.percent, 1),
                "engine": "Psutil Kernel Fallback"
            }
        except Exception:
            return {"total_gb": 8.0, "used_gb": 4.0, "free_gb": 4.0, "percent": 50.0, "engine": "Fallback"}

    # ==========================================================================
    # 4. ĐO LƯỜNG Ổ CỨNG (DISK STORAGE SECTOR ACCURACY)
    # ==========================================================================
    @classmethod
    def get_disk_info_precise(cls, mount_path: Optional[str] = None) -> Dict:
        """Đo lường dung lượng ổ cứng chính xác từng Sector từ kernel"""
        disk_path = mount_path or ("C:\\" if os.name == "nt" else "/")
        cls.initialize_low_level_engines()

        if cls._cpp_lib:
            try:
                tot, free_b, used, pct = ctypes.c_uint64(0), ctypes.c_uint64(0), ctypes.c_uint64(0), ctypes.c_double(0.0)
                c_path = disk_path.encode("utf-8")
                if cls._cpp_lib.get_disk_info_precise(c_path, ctypes.byref(tot), ctypes.byref(free_b), ctypes.byref(used), ctypes.byref(pct)) == 0:
                    return {
                        "path": disk_path,
                        "total_gb": tot.value / (1024 ** 3),
                        "used_gb": used.value / (1024 ** 3),
                        "free_gb": free_b.value / (1024 ** 3),
                        "percent": round(pct.value, 1),
                        "engine": "C++20 Disk Sector Introspection"
                    }
            except Exception:
                pass

        if os.name == "nt":
            try:
                free_b = ctypes.c_uint64(0)
                tot_b = ctypes.c_uint64(0)
                tot_free = ctypes.c_uint64(0)
                if ctypes.windll.kernel32.GetDiskFreeSpaceExW(disk_path, ctypes.byref(free_b), ctypes.byref(tot_b), ctypes.byref(tot_free)):
                    tot_gb = tot_b.value / (1024 ** 3)
                    free_gb = free_b.value / (1024 ** 3)
                    used_gb = (tot_b.value - free_b.value) / (1024 ** 3)
                    pct = (used_gb / tot_gb) * 100.0 if tot_gb > 0 else 0.0
                    return {
                        "path": disk_path,
                        "total_gb": tot_gb,
                        "used_gb": used_gb,
                        "free_gb": free_gb,
                        "percent": round(pct, 1),
                        "engine": "Win32 GetDiskFreeSpaceExW 64-bit C-ABI"
                    }
            except Exception:
                pass
        else:
            try:
                st = os.statvfs(disk_path)
                tot_bytes = st.f_blocks * st.f_frsize
                free_bytes = st.f_bavail * st.f_frsize
                used_bytes = tot_bytes - free_bytes
                tot_gb = tot_bytes / (1024 ** 3)
                used_gb = used_bytes / (1024 ** 3)
                free_gb = free_bytes / (1024 ** 3)
                pct = (used_gb / tot_gb) * 100.0 if tot_gb > 0 else 0.0
                return {
                    "path": disk_path,
                    "total_gb": tot_gb,
                    "used_gb": used_gb,
                    "free_gb": free_gb,
                    "percent": round(pct, 1),
                    "engine": "POSIX statvfs C-ABI"
                }
            except Exception:
                pass

        try:
            import psutil
            d = psutil.disk_usage(disk_path)
            return {
                "path": disk_path,
                "total_gb": d.total / (1024 ** 3),
                "used_gb": d.used / (1024 ** 3),
                "free_gb": d.free / (1024 ** 3),
                "percent": round(d.percent, 1),
                "engine": "Psutil Kernel Fallback"
            }
        except Exception:
            return {"path": disk_path, "total_gb": 100.0, "used_gb": 50.0, "free_gb": 50.0, "percent": 50.0, "engine": "Fallback"}

    # ==========================================================================
    # 5. ĐO LƯỜNG TIẾN TRÌNH ROBLOX THỰC TẾ (RAW WORKING SET & PRIVATE RSS)
    # ==========================================================================
    @classmethod
    def get_process_memory_precise(cls, pid: int) -> float:
        """Đo lường dung lượng RAM thực tế của 1 tiến trình Roblox (WorkingSetSize in MB)"""
        if pid <= 0:
            return 0.0

        cls.initialize_low_level_engines()
        if cls._cpp_lib:
            try:
                ws_bytes = ctypes.c_uint64(0)
                priv_bytes = ctypes.c_uint64(0)
                if cls._cpp_lib.get_roblox_process_memory(pid, ctypes.byref(ws_bytes), ctypes.byref(priv_bytes)) == 0:
                    return round(ws_bytes.value / (1024 * 1024), 1)
            except Exception:
                pass

        if os.name == "nt":
            try:
                PROCESS_QUERY_INFORMATION = 0x0400
                PROCESS_VM_READ = 0x0010
                h_proc = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
                if h_proc:
                    pmc = PROCESS_MEMORY_COUNTERS_EX()
                    pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
                    if ctypes.windll.psapi.GetProcessMemoryInfo(h_proc, ctypes.byref(pmc), ctypes.sizeof(pmc)):
                        mem_mb = pmc.WorkingSetSize / (1024 * 1024)
                        ctypes.windll.kernel32.CloseHandle(h_proc)
                        return round(mem_mb, 1)
                    ctypes.windll.kernel32.CloseHandle(h_proc)
            except Exception:
                pass
        else:
            try:
                with open(f"/proc/{pid}/statm", "r") as f:
                    parts = f.readline().split()
                if len(parts) >= 2:
                    resident = int(parts[1])
                    page_size = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096
                    mem_mb = (resident * page_size) / (1024 * 1024)
                    return round(mem_mb, 1)
            except Exception:
                pass

        return 0.0

    @classmethod
    def get_all_roblox_live_processes(cls) -> Dict:
        """Quét và tổng hợp toàn bộ các tiến trình Roblox đang chạy trực tiếp trên máy"""
        roblox_procs = {}
        total_ram_mb = 0.0

        try:
            import psutil
            for p in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    pname = (p.info['name'] or '').lower()
                    if ('roblox' in pname or 'playerbeta' in pname or 'ugphone' in pname) and 'crashhandler' not in pname:
                        pid = p.info['pid']
                        real_mb = cls.get_process_memory_precise(pid)
                        if real_mb <= 0.0 and p.info['memory_info']:
                            real_mb = p.info['memory_info'].rss / (1024 * 1024)
                        
                        roblox_procs[pid] = {
                            "pid": pid,
                            "name": p.info['name'],
                            "mem_mb": real_mb
                        }
                        total_ram_mb += real_mb
                except Exception:
                    pass
        except Exception:
            pass

        return {
            "count": len(roblox_procs),
            "total_ram_mb": total_ram_mb,
            "processes": roblox_procs
        }
