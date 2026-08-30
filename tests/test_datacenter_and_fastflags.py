# -*- coding: utf-8 -*-
"""
Unit Tests for Roblox Datacenter Resolver & FastFlags Optimizer
"""

import unittest
import json
import os
import tempfile
from network.roblox_datacenter_resolver import RobloxDatacenterResolver
from core.fastflags_optimizer import FastFlagsOptimizer, FASTFLAGS_PRESETS


class TestRobloxDatacenterResolver(unittest.TestCase):

    def setUp(self):
        self.resolver = RobloxDatacenterResolver()

    def test_database_loaded(self):
        self.assertGreater(len(self.resolver.datacenters), 0)
        self.assertGreater(len(self.resolver.dc_id_map), 0)

    def test_lookup_by_datacenter_id(self):
        # ID 369 is Sydney, AU from rovalradatacenters.json
        dc_info = self.resolver.lookup_by_datacenter_id(369)
        self.assertIsNotNone(dc_info)
        self.assertEqual(dc_info.get("city"), "Sydney")
        self.assertEqual(dc_info.get("country"), "AU")

    def test_resolve_udmux_ip_singapore(self):
        sg_ip = "128.116.49.12"
        res = self.resolver.resolve_udmux_ip(sg_ip)
        self.assertEqual(res.get("region_code"), "SG")
        self.assertEqual(res.get("country"), "SG")
        self.assertEqual(res.get("flag"), "🇸🇬")

    def test_resolve_udmux_ip_tokyo(self):
        jp_ip = "128.116.113.88"
        res = self.resolver.resolve_udmux_ip(jp_ip)
        self.assertEqual(res.get("region_code"), "JP")
        self.assertEqual(res.get("country"), "JP")
        self.assertEqual(res.get("flag"), "🇯🇵")

    def test_summary_not_empty(self):
        summary = self.resolver.get_supported_locations_summary()
        self.assertIsInstance(summary, list)
        self.assertGreater(len(summary), 0)


class TestFastFlagsOptimizer(unittest.TestCase):

    def setUp(self):
        self.optimizer = FastFlagsOptimizer()

    def test_presets_exist(self):
        self.assertIn("ULTRA_FPS", FASTFLAGS_PRESETS)
        self.assertIn("POTATO_MODE", FASTFLAGS_PRESETS)
        self.assertIn("BALANCED", FASTFLAGS_PRESETS)

    def test_set_preset(self):
        self.assertTrue(self.optimizer.set_preset("POTATO_MODE"))
        self.assertEqual(self.optimizer.active_preset, "POTATO_MODE")
        flags = self.optimizer.get_effective_flags()
        self.assertIn("FIntTerrainArraySliceSize", flags)
        self.assertEqual(flags["FIntTerrainArraySliceSize"], "0")

    def test_json_generation(self):
        self.optimizer.set_preset("ULTRA_FPS")
        json_str = self.optimizer.generate_client_app_settings_json()
        parsed = json.loads(json_str)
        self.assertIn("FFlagTaskSchedulerLimitTargetFps", parsed)
        self.assertEqual(parsed["FFlagTaskSchedulerLimitTargetFps"], "144")

    def test_custom_flags(self):
        self.optimizer.set_custom_flag("TestCustomFlag123", "True")
        flags = self.optimizer.get_effective_flags()
        self.assertEqual(flags.get("TestCustomFlag123"), "True")
        self.optimizer.remove_custom_flag("TestCustomFlag123")
        flags_after = self.optimizer.get_effective_flags()
        self.assertNotIn("TestCustomFlag123", flags_after)


if __name__ == "__main__":
    unittest.main()
