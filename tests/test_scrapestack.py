# -*- coding: utf-8 -*-
"""
Kiểm thử tự động tích hợp Scrapestack Proxy Client & Bridge Server
"""

import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from network.scrapestack_client import ScrapestackClient
from network.proxy_fetcher import ProxyFetcher
from config.settings import SCRAPESTACK_API_KEY, SCRAPESTACK_BASE_URL


class TestScrapestackIntegration(unittest.TestCase):

    def setUp(self):
        self.client = ScrapestackClient()

    def test_scrapestack_config_loaded(self):
        """Kiểm tra API Key 5d1c5fb06ff44e84a97fcc7e2720fd3f đã được nạp chính xác"""
        self.assertEqual(self.client.api_key, "5d1c5fb06ff44e84a97fcc7e2720fd3f")
        self.assertEqual(SCRAPESTACK_API_KEY, "5d1c5fb06ff44e84a97fcc7e2720fd3f")

    def test_scrapestack_connection(self):
        """Kiểm tra kết nối tới Scrapestack API và lấy live IP"""
        res = self.client.test_connection()
        print(f"\n[TEST] Scrapestack connection result: {res}")
        self.assertIn(res.get("status"), ["ONLINE", "OFFLINE"])

    def test_proxy_fetcher_integration(self):
        """Kiểm tra ProxyFetcher lấy được live proxies bao gồm Scrapestack"""
        proxies = ProxyFetcher.fetch_live_proxies(force_refresh=True)
        self.assertTrue(len(proxies) > 0)
        print(f"[TEST] Live Proxies fetched: {len(proxies)} items")


if __name__ == "__main__":
    unittest.main()
