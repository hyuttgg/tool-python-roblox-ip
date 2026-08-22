# -*- coding: utf-8 -*-
"""
Scrapestack Proxy Client Module
Tích hợp API Scrapestack (apilayer) để xoay vòng IP, định tuyến Proxy và vượt kiểm tra Roblox Multi-Account.
"""

import os
import json
import time
import urllib.request
import urllib.parse
from typing import Dict, List, Optional, Any
from config.logging import setup_logger

logger = setup_logger("scrapestack_client")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "proxy_config.json")


def load_scrapestack_config() -> Dict[str, Any]:
    """Tải cấu hình Scrapestack từ file JSON hoặc fallback settings"""
    default_config = {
        "api_key": "5d1c5fb06ff44e84a97fcc7e2720fd3f",
        "base_url": "http://api.scrapestack.com/scrape",
        "enabled": True,
        "timeout_sec": 8.0,
        "default_country": "ALL"
    }

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                default_config.update(saved)
        except Exception as e:
            logger.warning(f"Không thể đọc file cấu hình {CONFIG_FILE}: {e}")

    # Cho phép ghi đè từ biến môi trường
    env_key = os.getenv("SCRAPESTACK_API_KEY")
    if env_key:
        default_config["api_key"] = env_key

    return default_config


class ScrapestackClient:
    """Quản lý kết nối, lấy IP và định tuyến dữ liệu qua mạng Proxy Scrapestack"""

    def __init__(self, api_key: Optional[str] = None):
        config = load_scrapestack_config()
        self.api_key = api_key or config.get("api_key", "5d1c5fb06ff44e84a97fcc7e2720fd3f")
        self.base_url = config.get("base_url", "http://api.scrapestack.com/scrape")
        self.timeout = float(config.get("timeout_sec", 8.0))
        self.enabled = config.get("enabled", True)
        self._last_test_cache: Dict[str, Any] = {}

    def test_connection(self) -> Dict[str, Any]:
        """
        Kiểm tra trạng thái kết nối tới Scrapestack API và đo độ trễ.
        Trả về: { status: 'ONLINE'/'OFFLINE', latency_ms: int, ip: str, error: str/None }
        """
        t0 = time.time()
        test_target = "https://api.ipify.org?format=json"
        
        params = {
            "access_key": self.api_key,
            "url": test_target
        }
        query_str = urllib.parse.urlencode(params)
        full_url = f"{self.base_url}?{query_str}"

        try:
            req = urllib.request.Request(
                full_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RobloxProxyEngine/2.0"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
                latency_ms = int((time.time() - t0) * 1000)

                # Parse JSON IP
                try:
                    data = json.loads(raw)
                    proxy_ip = data.get("ip") or data.get("origin") or raw.strip()
                except Exception:
                    proxy_ip = raw.strip()

                result = {
                    "status": "ONLINE",
                    "latency_ms": latency_ms,
                    "proxy_ip": proxy_ip,
                    "api_key_masked": f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else self.api_key,
                    "error": None
                }
                self._last_test_cache = result
                logger.info(f"Scrapestack API hoạt động tốt. IP: {proxy_ip} (Latency: {latency_ms}ms)")
                return result
        except Exception as e:
            latency_ms = int((time.time() - t0) * 1000)
            err_msg = str(e)
            result = {
                "status": "OFFLINE",
                "latency_ms": latency_ms,
                "proxy_ip": None,
                "api_key_masked": f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else self.api_key,
                "error": err_msg
            }
            self._last_test_cache = result
            logger.warning(f"Lỗi kiểm tra Scrapestack API: {err_msg}")
            return result

    def get_proxy_ip(self, country_code: Optional[str] = None) -> Optional[str]:
        """Lấy một IP duy nhất xoay vòng qua Scrapestack theo mã quốc gia"""
        test_target = "https://api.ipify.org?format=json"
        params = {
            "access_key": self.api_key,
            "url": test_target
        }
        if country_code and country_code.upper() not in ["ALL", "MULTI"]:
            params["country_code"] = country_code.lower()

        query_str = urllib.parse.urlencode(params)
        full_url = f"{self.base_url}?{query_str}"

        try:
            req = urllib.request.Request(
                full_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RobloxProxyEngine/2.0"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
                data = json.loads(raw)
                return data.get("ip") or data.get("origin")
        except Exception as e:
            logger.warning(f"Không thể lấy IP từ Scrapestack: {e}")
            return None

    def fetch_url(self, url: str, country_code: Optional[str] = None, render_js: bool = False) -> Optional[str]:
        """Tải nội dung trang web bất kỳ qua mạng Proxy Scrapestack"""
        params = {
            "access_key": self.api_key,
            "url": url
        }
        if country_code and country_code.upper() not in ["ALL", "MULTI"]:
            params["country_code"] = country_code.lower()
        if render_js:
            params["render_js"] = "1"

        query_str = urllib.parse.urlencode(params)
        full_url = f"{self.base_url}?{query_str}"

        try:
            req = urllib.request.Request(
                full_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RobloxProxyEngine/2.0"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Lỗi truy vấn URL qua Scrapestack: {e}")
            return None

    def batch_fetch_proxies(self, count: int = 5, country_code: str = "ALL") -> List[Dict[str, str]]:
        """Lấy danh sách các IP riêng biệt từ Scrapestack cho từng Tag Roblox"""
        proxies = []
        c_upper = country_code.upper()

        country_rotation = ["JP", "SG", "US", "VN", "KR", "DE", "GB"]
        for i in range(count):
            target_country = country_rotation[i % len(country_rotation)] if c_upper in ["ALL", "MULTI"] else c_upper
            ip = self.get_proxy_ip(country_code=target_country)
            if ip:
                proxies.append({
                    "ip": f"{ip}:80",
                    "country": target_country,
                    "region": f"[{target_country}] Scrapestack Dedicated",
                    "source": "Scrapestack API"
                })
        return proxies
