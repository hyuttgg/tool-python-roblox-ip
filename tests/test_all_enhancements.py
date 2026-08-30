# -*- coding: utf-8 -*-
"""
Unit Tests for All 3 Enhancement Directions:
1. Smart Proxy Rotator & Sticky Sessions (Oxylabs)
2. Sing-box Universal Proxy & TUN Core (SagerNet)
3. Roblox Presence & Rich Discord Tracker (LxstCxn)
4. Android Transparent Proxy & IPTables UID Interceptor (Proxydroid)
"""

import unittest
import os
import time
from network.proxy_rotator import SmartProxyRotator, ProxyNode
from network.singbox_core import SingBoxEngine
from network.roblox_presence import RobloxPresenceTracker
from network.discord_rich_reporter import DiscordRichReporter
from devices.android_transparent import AndroidTransparentProxyManager


class TestProxyRotator(unittest.TestCase):

    def setUp(self):
        self.rotator = SmartProxyRotator()
        self.rotator.add_proxy("103.150.12.1", port=8080, country="SG", region="[SG] Singapore", latency_ms=30)
        self.rotator.add_proxy("103.150.12.2", port=8080, country="SG", region="[SG] Singapore", latency_ms=45)
        self.rotator.add_proxy("133.242.10.5", port=8080, country="JP", region="[JP] Tokyo", latency_ms=60)

    def test_sticky_session_per_tag(self):
        node1 = self.rotator.get_or_create_tag_session("ROBLOX-TAG-01", country_code="SG")
        self.assertEqual(node1.country, "SG")
        self.assertEqual(node1.ip, "103.150.12.1")

        # Calling again should return the exact same sticky node
        node2 = self.rotator.get_or_create_tag_session("ROBLOX-TAG-01", country_code="SG")
        self.assertEqual(node1.ip, node2.ip)

    def test_failover_mechanism(self):
        node_orig = self.rotator.get_or_create_tag_session("ROBLOX-TAG-02", country_code="SG")
        self.assertEqual(node_orig.ip, "103.150.12.1")

        # Trigger failover
        node_backup = self.rotator.trigger_failover_for_tag("ROBLOX-TAG-02", reason="Rate Limit 429")
        self.assertNotEqual(node_orig.ip, node_backup.ip)
        self.assertEqual(node_backup.ip, "103.150.12.2")


class TestSingBoxCore(unittest.TestCase):

    def setUp(self):
        self.engine = SingBoxEngine()

    def test_generate_config(self):
        outbounds = [
            {"tag": "sg-proxy", "type": "socks", "server": "103.150.12.1", "port": 1080}
        ]
        config = self.engine.generate_config(outbounds, enable_tun=False)
        self.assertIn("inbounds", config)
        self.assertIn("outbounds", config)
        self.assertIn("route", config)
        self.assertEqual(config["inbounds"][0]["type"], "mixed")
        self.assertEqual(len(config["outbounds"]), 2)  # direct + sg-proxy


class TestRobloxPresence(unittest.TestCase):

    def setUp(self):
        self.tracker = RobloxPresenceTracker()

    def test_session_uptime_str(self):
        self.tracker.start_tag_session("TAG-TEST")
        time.sleep(0.1)
        uptime = self.tracker.get_session_uptime_str("TAG-TEST")
        self.assertIn("m", uptime)
        self.assertIn("s", uptime)

    def test_avatar_headshot_fallback(self):
        url = self.tracker.get_user_avatar_headshot("12345678")
        self.assertTrue(url.startswith("http"))

    def test_game_icon_fallback(self):
        url = self.tracker.get_game_icon("2753915549")
        self.assertTrue(url.startswith("http"))


class TestAndroidTransparentProxy(unittest.TestCase):

    def test_get_roblox_uid(self):
        uid = AndroidTransparentProxyManager.get_roblox_uid()
        self.assertIsInstance(uid, int)
        self.assertGreater(uid, 0)


if __name__ == "__main__":
    unittest.main()
