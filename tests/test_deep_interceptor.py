# -*- coding: utf-8 -*-
import unittest
import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from network.deep_interceptor import WindowsDeepInterceptor, AndroidDeepInterceptor, DNSInterceptEngine

class TestDeepInterceptor(unittest.TestCase):

    def test_windows_singbox_config_generation(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            generated = WindowsDeepInterceptor.generate_singbox_config(
                out_filepath=tmp_path,
                proxy_host="192.168.1.100",
                proxy_port=10809,
                proxy_type="socks",
                dns_servers=["1.1.1.1", "8.8.8.8"],
                target_processes=["RobloxPlayerBeta.exe", "Bloxstrap.exe"],
                fake_ip=True
            )
            self.assertTrue(os.path.exists(generated))

            with open(generated, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Kiểm tra các thành phần cốt lõi của sing-box
            self.assertIn("inbounds", data)
            self.assertIn("outbounds", data)
            self.assertIn("route", data)
            self.assertIn("dns", data)

            # Inbound TUN wintun
            tun_inbound = [ib for ib in data["inbounds"] if ib.get("type") == "tun"][0]
            self.assertEqual(tun_inbound["interface_name"], "wintun-roblox")

            # Route rule per process
            rules = data["route"]["rules"]
            proc_rule = [r for r in rules if "process_name" in r][0]
            self.assertIn("RobloxPlayerBeta.exe", proc_rule["process_name"])
            self.assertEqual(proc_rule["outbound"], "proxy-out")

            # DNS FakeIP
            self.assertTrue(data["dns"]["fakeip"]["enabled"])
            self.assertEqual(data["dns"]["fakeip"]["inet4_range"], "198.18.0.0/15")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_android_iptables_script_generation(self):
        script_enable = AndroidDeepInterceptor.generate_iptables_script(
            roblox_uid=10234,
            proxy_host="127.0.0.1",
            proxy_port=10808,
            dns_server="1.1.1.1",
            enable=True
        )

        self.assertIn("10234", script_enable)
        self.assertIn("ROBLOX_TCP", script_enable)
        self.assertIn("ROBLOX_DNS", script_enable)
        self.assertIn("--to-ports 10808", script_enable)
        self.assertIn("1.1.1.1:53", script_enable)

        script_disable = AndroidDeepInterceptor.generate_iptables_script(
            roblox_uid=10234,
            enable=False
        )
        self.assertIn("-D OUTPUT", script_disable)
        self.assertIn("-X ROBLOX_TCP", script_disable)

    def test_dns_intercept_engine_leak_check(self):
        leak_res = DNSInterceptEngine.check_dns_leak("1.1.1.1")
        self.assertIsInstance(leak_res, dict)
        self.assertIn("leak_status", leak_res)
        self.assertIn(leak_res["leak_status"], ["SECURE", "ERROR"])

    def test_mihomo_yaml_generation(self):
        from network.deep_interceptor import MihomoDeepInterceptor
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            out_file = MihomoDeepInterceptor.generate_mihomo_yaml(
                out_filepath=tmp_path,
                proxy_host="127.0.0.1",
                proxy_port=10808,
                target_processes=["RobloxPlayerBeta.exe"],
                target_packages=["com.roblox.client"]
            )
            self.assertTrue(os.path.exists(out_file))
            with open(out_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("enhanced-mode: fake-ip", content)
            self.assertIn("wintun-roblox", content)
            self.assertIn("PROCESS-NAME,RobloxPlayerBeta.exe,ROBLOX-PROXY-OUT", content)
            self.assertIn("PACKAGE-NAME,com.roblox.client,ROBLOX-PROXY-OUT", content)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_magisk_service_generation(self):
        from network.deep_interceptor import MagiskServiceBootEngine
        boot_script = MagiskServiceBootEngine.generate_boot_service_script(
            roblox_uid=10555,
            proxy_port=10808,
            dns_server="1.1.1.1"
        )
        self.assertIn("sys.boot_completed", boot_script)
        self.assertIn("10555", boot_script)
        self.assertIn("ROBLOX_TCP", boot_script)

if __name__ == "__main__":
    unittest.main()
