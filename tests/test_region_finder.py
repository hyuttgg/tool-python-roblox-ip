# -*- coding: utf-8 -*-
"""
Unit tests for Roblox Region Finder & VIP Auto-Rejoin Engine
"""

import unittest
from network.roblox_region_finder import RobloxRegionFinder, SUPPORTED_REGIONS, FILTER_MODES
from core.game_selector import GameSelectorManager, RobloxGameItem


class TestRobloxRegionFinder(unittest.TestCase):

    def setUp(self):
        self.finder = RobloxRegionFinder(cache_ttl_sec=60)
        self.place_id = "2753915549"  # Blox Fruits Place ID

    def test_fetch_public_servers(self):
        """Kiểm tra lấy danh sách máy chủ công khai"""
        servers = self.finder.fetch_public_servers(self.place_id, limit=20)
        self.assertIsInstance(servers, list)
        self.assertGreater(len(servers), 0)
        first = servers[0]
        self.assertIn("job_id", first)
        self.assertIn("playing", first)
        self.assertIn("ping", first)
        self.assertIn("region", first)

    def test_filter_by_region_singapore(self):
        """Kiểm tra lọc server theo Region Singapore (SG)"""
        sg_servers = self.finder.filter_servers(self.place_id, target_region="SG")
        self.assertIsInstance(sg_servers, list)
        self.assertGreater(len(sg_servers), 0)
        for s in sg_servers:
            self.assertEqual(s.get("region"), "SG")

    def test_filter_mode_low_players(self):
        """Kiểm tra chế độ sắp xếp ưu tiên ít người chơi nhất (Low Players)"""
        servers = self.finder.filter_servers(self.place_id, target_region="AUTO", filter_mode="LOW_PLAYERS")
        self.assertGreater(len(servers), 1)
        for i in range(len(servers) - 1):
            self.assertLessEqual(servers[i]["playing"], servers[i+1]["playing"])

    def test_filter_mode_best_ping(self):
        """Kiểm tra chế độ sắp xếp ưu tiên Ping thấp nhất"""
        servers = self.finder.filter_servers(self.place_id, target_region="AUTO", filter_mode="BEST_PING")
        self.assertGreater(len(servers), 1)
        for i in range(len(servers) - 1):
            self.assertLessEqual(servers[i]["ping"], servers[i+1]["ping"])

    def test_get_best_server(self):
        """Kiểm tra hàm lấy 1 server tối ưu duy nhất"""
        best = self.finder.get_best_server(self.place_id, target_region="JP", filter_mode="LOW_PLAYERS")
        self.assertIsNotNone(best)
        self.assertEqual(best.get("region"), "JP")
        self.assertTrue(best.get("job_id"))

    def test_launch_uri_generation(self):
        """Kiểm tra sinh URI Roblox chứa Place ID và Game Instance ID"""
        uri = self.finder.get_launch_uri_for_server("2753915549", "test-job-id-12345")
        self.assertEqual(uri, "roblox://placeId=2753915549&gameInstanceId=test-job-id-12345")

    def test_game_selector_region_integration(self):
        """Kiểm tra tích hợp Region vào GameSelectorManager"""
        mgr = GameSelectorManager()
        mgr.set_custom_game("Test Game", "12345678")
        
        # Test gán Region Global
        best_s = mgr.set_global_region("SG", filter_mode="LOW_PLAYERS")
        cur_g = mgr.get_current_game()
        self.assertEqual(cur_g["preferred_region"], "SG")
        self.assertTrue(cur_g["job_id"])

        # Test gán Region riêng cho Tag
        mgr.set_region_for_tag("ROBLOX-TAG-99", "JP", filter_mode="BEST_PING")
        tag_g = mgr.get_game_for_tag("ROBLOX-TAG-99")
        self.assertEqual(tag_g["preferred_region"], "JP")
        self.assertTrue(tag_g["job_id"])

        # Test sinh URI cho Tag
        uri = mgr.get_launch_uri_for_tag("ROBLOX-TAG-99")
        self.assertIn("placeId=12345678", uri)
        self.assertIn("gameInstanceId=", uri)


if __name__ == "__main__":
    unittest.main()
