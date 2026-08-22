# -*- coding: utf-8 -*-
"""
Unit tests for Feature 10: Selection Sort IP Optimizer & Auto-Launcher
"""

import unittest
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.java_sort_bridge import SelectionSortBridge, RobloxAutoLauncher

class TestSelectionSortFeature(unittest.TestCase):

    def test_selection_sort_algorithm(self):
        """Kiểm tra thuật toán Selection Sort sắp xếp chính xác theo latency tăng dần"""
        unsorted_data = [
            {"ip": "103.1.1.1:80", "latency_ms": 320, "region": "VN"},
            {"ip": "136.227.167.23:80", "latency_ms": 25, "region": "JP"},
            {"ip": "104.28.1.1:80", "latency_ms": 110, "region": "US"},
            {"ip": "134.199.74.35:80", "latency_ms": 45, "region": "JP"},
            {"ip": "112.146.7.1:80", "latency_ms": 78, "region": "SG"},
        ]

        sorted_res, logs = SelectionSortBridge.selection_sort_py(unsorted_data)
        
        # Kiểm tra thứ tự tăng dần của Latency (25 -> 45 -> 78 -> 110 -> 320)
        latencies = [x["latency_ms"] for x in sorted_res]
        self.assertEqual(latencies, [25, 45, 78, 110, 320])
        self.assertEqual(sorted_res[0]["ip"], "136.227.167.23:80")
        self.assertEqual(sorted_res[1]["ip"], "134.199.74.35:80")
        self.assertTrue(len(logs) > 0)

    def test_execute_selection_sort_bridge(self):
        """Kiểm tra cầu nối thực thi Selection Sort trả về kết quả đầy đủ"""
        candidates = [
            {"ip": "1.1.1.1:80", "latency_ms": 150},
            {"ip": "2.2.2.2:80", "latency_ms": 30},
            {"ip": "3.3.3.3:80", "latency_ms": 80},
        ]
        res = SelectionSortBridge.execute_selection_sort(candidates)
        self.assertEqual(res.get("status"), "success")
        sorted_list = res.get("sorted_proxies", [])
        self.assertEqual(len(sorted_list), 3)
        self.assertEqual(sorted_list[0]["latency_ms"], 30)

    def test_roblox_launcher_detection(self):
        """Kiểm tra hàm dò tìm Roblox executable"""
        exe = RobloxAutoLauncher.find_roblox_executable()
        # Không được văng exception, có thể trả về str hoặc None
        self.assertTrue(exe is None or isinstance(exe, str))

if __name__ == "__main__":
    unittest.main()
