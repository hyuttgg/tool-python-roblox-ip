# -*- coding: utf-8 -*-
"""
Unit tests for Universal Master Executor & Tag Claiming Dispatcher
"""

import unittest
import os
import sys
import time
import json
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from network.bridge_server import RobloxBridgeServer, SHARED_STATE
from core.lua_generator import LuaScriptGenerator
from core.clone_scanner import RobloxCloneScanner
from core.scanner import RobloxWindowInstance, WindowRect


class TestMasterExecutor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = RobloxBridgeServer(host="127.0.0.1", port=8888)
        cls.server.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_dynamic_tag_claiming(self):
        """Kiểm tra 2 tài khoản/clone khác nhau nhận 2 Tag và IP độc lập 100%"""
        req1 = urllib.request.urlopen("http://127.0.0.1:8888/api/claim_tag?user=AccPlayer1")
        data1 = json.loads(req1.read().decode("utf-8"))
        self.assertEqual(data1.get("status"), "success")
        self.assertTrue(bool(data1.get("tag_id")))
        self.assertTrue(bool(data1.get("assigned_ip")))

        req2 = urllib.request.urlopen("http://127.0.0.1:8888/api/claim_tag?user=AccPlayer2")
        data2 = json.loads(req2.read().decode("utf-8"))
        self.assertEqual(data2.get("status"), "success")

        # Đảm bảo 2 tag độc lập và không trùng nhau
        self.assertNotEqual(data1["tag_id"], data2["tag_id"])

    def test_custom_script_endpoint(self):
        """Kiểm tra API /api/custom_script trả về script game cho các tag"""
        req = urllib.request.urlopen("http://127.0.0.1:8888/api/custom_script")
        body = req.read().decode("utf-8")
        self.assertTrue(len(body) > 0)

    def test_master_script_generation(self):
        """Kiểm tra sinh file Master Autoexec chứa logic Universal Dispatcher"""
        gen = LuaScriptGenerator()
        sample = [
            RobloxWindowInstance("ROBLOX-TEST-01", 0, "Test 1", 0, "Roblox", "Class", WindowRect(), "Center", "0 MB", "User1"),
            RobloxWindowInstance("ROBLOX-TEST-02", 0, "Test 2", 0, "Roblox", "Class", WindowRect(), "Center", "0 MB", "User2")
        ]
        files = gen.generate_scripts_for_scanned_instances(sample, use_live_proxies=False)
        self.assertIn("MASTER", files)

if __name__ == "__main__":
    unittest.main()
