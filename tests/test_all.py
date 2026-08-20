import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from network.connectivity import ConnectivityChecker
from network.dns import DNSResolver
from monitoring.status import HealthEvaluator, HealthState
from profiles.manager import ProfileManager
from database.repository import InstanceRepository
from core.scanner import RobloxWindowScanner, RobloxWindowInstance, WindowRect
from core.lua_generator import LuaScriptGenerator
from network.bridge_server import RobloxBridgeServer

class TestNetworkManager(unittest.TestCase):
    def test_health_evaluation(self):
        self.assertEqual(HealthEvaluator.evaluate(30.0, 0.0), HealthState.ONLINE)
        self.assertEqual(HealthEvaluator.evaluate(200.0, 0.0), HealthState.DEGRADED)
        self.assertEqual(HealthEvaluator.evaluate(-1.0, 100.0), HealthState.OFFLINE)

    def test_profile_manager(self):
        pm = ProfileManager()
        profiles = pm.list_profiles()
        self.assertIn("profile-jp-tokyo", profiles)
        self.assertTrue(pm.validate_profile(profiles["profile-jp-tokyo"]))

    def test_database_instances(self):
        instances = InstanceRepository.get_all_instances()
        self.assertGreaterEqual(len(instances), 5)

    def test_roblox_scanner_and_lua_generation(self):
        scanner = RobloxWindowScanner()
        generator = LuaScriptGenerator()

        # Quét màn hình
        scanned = scanner.scan_active_roblox_windows()
        self.assertIsInstance(scanned, list)

        # Tạo mẫu test
        test_instances = [
            RobloxWindowInstance("TEST-TAG-01", 1, "Roblox - 1", 100, "RobloxPlayerBeta.exe", "WINDOWSCLIENT", WindowRect(), "Top-Left", "500 MB", account_username="Player1"),
            RobloxWindowInstance("TEST-TAG-02", 2, "Roblox - 2", 200, "RobloxPlayerBeta.exe", "WINDOWSCLIENT", WindowRect(), "Top-Right", "510 MB", account_username="Player2")
        ]

        files = generator.generate_scripts_for_scanned_instances(test_instances)
        self.assertIn("TEST-TAG-01", files)
        self.assertIn("TEST-TAG-02", files)
        self.assertIn("MASTER", files)

        # Kiểm tra nội dung file sinh ra đã được mã hóa bảo vệ (Obfuscated & Stealth)
        with open(files["TEST-TAG-01"], "r", encoding="utf-8") as f:
            content = f.read()
            self.assertTrue(content.startswith("--[[ \n"))
            self.assertIn("loadstring or load", content)
            self.assertGreater(len(content), 300)

if __name__ == "__main__":
    unittest.main()
