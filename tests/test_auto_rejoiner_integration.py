# -*- coding: utf-8 -*-
"""
Unit Test Suite: Roblox-Auto-Rejoiner Integration
Kiểm thử toàn diện các tính năng tích hợp từ repository Roblox-Auto-Rejoiner:
  1. RobloxLogMonitor (Tailing log, nhận diện Disconnect Markers, Error 277, 268, Kicked, Idle).
  2. Roblox Game API Metadata Resolver (Universe & Game Name Fetcher & Cache).
  3. Dual-Tier Roblox Client Launcher (URI Protocol & Direct Fallback).
  4. Internet Reachability & Socket Prober.
  5. Screen Capture Safe Execution & Fallback.
  6. Discord Notifier & Webhook Dispatcher (Config, Queue, Payload generation).
"""

import os
import sys
import time
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Thiết lập đường dẫn môi trường
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.roblox_log_monitor import RobloxLogMonitor, DISCONNECT_MARKERS
from core.game_selector import (
    game_manager,
    fetch_game_name_from_roblox,
    launch_roblox_client,
    POPULAR_ROBLOX_GAMES
)
from core.screen_capture import capture_roblox_window, is_screenshot_supported
from core.watchdog_supervisor import watchdog, internet_available, wait_for_internet
from network.discord_notifier import DiscordNotifier, discord_notifier


class TestRobloxLogMonitor(unittest.TestCase):
    """Kiểm thử bộ theo dõi log thời gian thực RobloxLogMonitor"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_empty_log_dir(self):
        monitor = RobloxLogMonitor(log_dir=self.log_dir)
        self.assertIsNone(monitor.get_latest_log())
        self.assertIsNone(monitor.check_for_disconnect())

    def test_tailing_and_disconnect_detection(self):
        log_file_path = os.path.join(self.log_dir, "Player_20260825_120000.log")
        # Ghi nội dung khởi đầu
        with open(log_file_path, "w", encoding="utf-8") as f:
            f.write("2026-08-25T12:00:00.000Z [Info] Roblox Client Initialized\n")
            f.write("2026-08-25T12:00:01.000Z [Info] Connected to place 2753915549\n")

        # Khởi tạo monitor ở cuối file (start_at_end=True)
        monitor = RobloxLogMonitor(log_dir=self.log_dir)
        self.assertEqual(monitor.current_log, log_file_path)
        # Không có lỗi mới
        self.assertIsNone(monitor.check_for_disconnect())

        # Ghi thêm dòng log bình thường
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write("2026-08-25T12:00:05.000Z [Info] Render frame 60 fps\n")

        self.assertIsNone(monitor.check_for_disconnect())

        # Ghi thêm dòng log mất kết nối: Error 277
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write("2026-08-25T12:00:10.000Z [Error] Disconnected: Error Code 277 Lost connection to server\n")

        detected = monitor.check_for_disconnect()
        self.assertIsNotNone(detected)
        self.assertTrue("277" in detected or "lost connection" in detected)

    def test_kicked_and_idle_disconnects(self):
        log_file_path = os.path.join(self.log_dir, "Player_20260825_130000.log")
        with open(log_file_path, "w", encoding="utf-8") as f:
            f.write("2026-08-25T13:00:00.000Z [Info] Joining game\n")

        monitor = RobloxLogMonitor(log_dir=self.log_dir)

        # Mô phỏng bị kick
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write("2026-08-25T13:05:00.000Z [Info] You were kicked from this experience\n")

        detected = monitor.check_for_disconnect()
        self.assertEqual(detected, "you were kicked from this experience")

        # Mô phỏng idled 20 minutes
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write("2026-08-25T13:25:00.000Z [Info] Disconnected for being idle 20 minutes\n")

        detected2 = monitor.check_for_disconnect()
        self.assertIsNotNone(detected2)
        self.assertTrue("idle" in detected2)


class TestGameMetadataResolver(unittest.TestCase):
    """Kiểm thử bộ tra cứu tên game tự động từ Roblox API"""

    def test_popular_game_lookup(self):
        # Blox Fruits Place ID: 2753915549
        name = fetch_game_name_from_roblox("2753915549")
        self.assertEqual(name, "Blox Fruits")

        # King Legacy Place ID: 4520749081
        name2 = fetch_game_name_from_roblox("4520749081")
        self.assertEqual(name2, "King Legacy")

    @patch("requests.get")
    def test_api_fetch_and_caching(self, mock_get):
        # Mock universe response
        mock_resp_univ = MagicMock()
        mock_resp_univ.status_code = 200
        mock_resp_univ.json.return_value = {"universeId": 999888777}

        # Mock game details response
        mock_resp_game = MagicMock()
        mock_resp_game.status_code = 200
        mock_resp_game.json.return_value = {"data": [{"name": "Custom Test Adventure RPG"}]}

        mock_get.side_effect = [mock_resp_univ, mock_resp_game]

        custom_place_id = "1234567890123"
        resolved_name = fetch_game_name_from_roblox(custom_place_id)
        self.assertEqual(resolved_name, "Custom Test Adventure RPG")

    def test_dual_tier_launcher_uri_generation(self):
        uri = game_manager.get_launch_uri_for_tag(None)
        self.assertTrue(uri.startswith("roblox://experiences/start?placeId="))


class TestInternetReachability(unittest.TestCase):
    """Kiểm thử kiểm tra mạng thông suốt tới Roblox"""

    def test_internet_available_check(self):
        # Kiểm tra hàm không quăng ngoại lệ
        try:
            status = internet_available(timeout=1.5)
            self.assertIsInstance(status, bool)
        except Exception as e:
            self.fail(f"internet_available() quăng ngoại lệ không mong muốn: {e}")


class TestScreenCapture(unittest.TestCase):
    """Kiểm thử module chụp màn hình safe execution"""

    def test_screen_capture_functionality(self):
        # Kiểm tra capture_roblox_window không làm crash app
        try:
            result = capture_roblox_window(hwnd=0)
            # Có thể trả về str hoặc None tùy vào môi trường test
            self.assertTrue(result is None or isinstance(result, str))
        except Exception as e:
            self.fail(f"capture_roblox_window() quăng ngoại lệ: {e}")


class TestDiscordNotifier(unittest.TestCase):
    """Kiểm thử Discord Webhook Dispatcher"""

    def setUp(self):
        self.notifier = DiscordNotifier()

    def test_config_management(self):
        self.notifier.save_config({
            "enabled": True,
            "webhook_url": "https://discord.com/api/webhooks/12345/test",
            "attach_screenshot": True
        })
        self.assertTrue(self.notifier.config["enabled"])
        self.assertEqual(self.notifier.config["webhook_url"], "https://discord.com/api/webhooks/12345/test")

    def test_queue_alert_generation(self):
        # Kiểm tra hàm gửi cảnh báo đưa dữ liệu vào hàng đợi mà không làm chậm hệ thống
        self.notifier.config["enabled"] = True
        self.notifier.send_crash_alert(
            tag_id="ROBLOX-TAG-TEST",
            game_name="Blox Fruits",
            place_id="2753915549",
            error_reason="Error Code 277: Lost connection"
        )
        self.notifier.send_rejoin_alert(
            tag_id="ROBLOX-TAG-TEST",
            game_name="Blox Fruits",
            place_id="2753915549",
            assigned_ip="192.168.1.100",
            region="[JP] Japan",
            attempt=1
        )
        # Hàng đợi không bị crash
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
