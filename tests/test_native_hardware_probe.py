# -*- coding: utf-8 -*-
"""
Unit tests for Native C++ & C-ABI Hardware Probe Engine
"""

import unittest
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.native_hardware_bridge import NativeHardwareProbe


class TestNativeHardwareProbe(unittest.TestCase):

    def test_cpu_probe_precision(self):
        """Kiểm tra đo lường CPU qua C++/C-ABI với độ chính xác cao"""
        cpu_pct, cpu_eng = NativeHardwareProbe.get_cpu_usage_precise()
        self.assertIsInstance(cpu_pct, float)
        self.assertGreaterEqual(cpu_pct, 0.0)
        self.assertLessEqual(cpu_pct, 100.0)
        self.assertIsInstance(cpu_eng, str)
        self.assertTrue(len(cpu_eng) > 0)

    def test_ram_probe_precision(self):
        """Kiểm tra đo lường RAM qua 64-bit byte introspection"""
        ram_info = NativeHardwareProbe.get_ram_info_precise()
        self.assertIn("total_gb", ram_info)
        self.assertIn("used_gb", ram_info)
        self.assertIn("free_gb", ram_info)
        self.assertIn("percent", ram_info)
        self.assertGreater(ram_info["total_gb"], 0.0)
        self.assertGreaterEqual(ram_info["percent"], 0.0)
        self.assertLessEqual(ram_info["percent"], 100.0)

    def test_disk_probe_precision(self):
        """Kiểm tra đo lường Ổ cứng qua sector introspection"""
        disk_path = "C:\\" if os.name == "nt" else "/"
        disk_info = NativeHardwareProbe.get_disk_info_precise(disk_path)
        self.assertIn("total_gb", disk_info)
        self.assertIn("used_gb", disk_info)
        self.assertIn("free_gb", disk_info)
        self.assertIn("percent", disk_info)
        self.assertGreater(disk_info["total_gb"], 0.0)

    def test_roblox_processes_scan(self):
        """Kiểm tra quét tiến trình Roblox qua C++/C-ABI"""
        rbx_data = NativeHardwareProbe.get_all_roblox_live_processes()
        self.assertIn("count", rbx_data)
        self.assertIn("total_ram_mb", rbx_data)
        self.assertIn("processes", rbx_data)
        self.assertGreaterEqual(rbx_data["count"], 0)


if __name__ == "__main__":
    unittest.main()
