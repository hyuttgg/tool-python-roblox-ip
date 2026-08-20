# -*- coding: utf-8 -*-
import unittest
import urllib.request
import json
from network.bridge_server import RobloxBridgeServer

class TestServerHopRotation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = RobloxBridgeServer(host="127.0.0.1", port=8899)
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_rotate_ip_same_country(self):
        url = "http://127.0.0.1:8899/api/rotate_ip?tag=ROBLOX-TAG-01&country=JP&job_id=job_12345&old_ip=1.1.1.1:80"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "success")
            self.assertEqual(data.get("country"), "JP")
            self.assertIn("JP", data.get("region"))
            self.assertNotEqual(data.get("new_ip"), "1.1.1.1:80")

if __name__ == "__main__":
    unittest.main()
