# -*- coding: utf-8 -*-
"""
WebScraping.AI Proxy & AI Client Module
Tích hợp API WebScraping.AI để xoay vòng IP, scraping thông minh qua AI,
và định tuyến Proxy cho Roblox Multi-Account.
Tài liệu: https://pypi.org/project/webscraping-ai/
"""

import os
import json
import time
import urllib.request
import urllib.parse
from typing import Dict, List, Optional, Any
from config.logging import setup_logger

logger = setup_logger("webscraping_ai_client")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
WSAI_CONFIG_FILE = os.path.join(DATA_DIR, "webscraping_ai_config.json")

# WebScraping.AI REST API base URL
WSAI_API_BASE = "https://api.webscraping.ai"


def load_wsai_config() -> Dict[str, Any]:
    """Tải cấu hình WebScraping.AI từ file JSON hoặc fallback settings"""
    default_config = {
        "api_key": "51f5dc82-0410-4f1c-9bef-ac5b9e1eb948",
        "base_url": WSAI_API_BASE,
        "enabled": True,
        "timeout_sec": 12.0,
        "default_proxy_type": "datacenter",   # datacenter | residential
        "js_rendering": False,
    }

    if os.path.exists(WSAI_CONFIG_FILE):
        try:
            with open(WSAI_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                default_config.update(saved)
        except Exception as e:
            logger.warning(f"Không thể đọc file cấu hình {WSAI_CONFIG_FILE}: {e}")

    # Cho phép ghi đè từ biến môi trường
    env_key = os.getenv("WEBSCRAPING_AI_API_KEY")
    if env_key:
        default_config["api_key"] = env_key

    return default_config


class WebScrapingAIClient:
    """
    Quản lý kết nối, scraping qua AI, lấy IP và định tuyến dữ liệu
    qua mạng Proxy WebScraping.AI.

    Sử dụng nhanh (SDK):
        pip install webscraping_ai
        from webscraping_ai import Client
        client = Client(api_key="...")
        answer = client.question(url, question="...")

    Module này cung cấp tương đương bằng REST thuần (urllib) để không
    phụ thuộc SDK, đồng thời hỗ trợ tải SDK khi có sẵn.
    """

    def __init__(self, api_key: Optional[str] = None):
        config = load_wsai_config()
        self.api_key = api_key or config.get("api_key", "")
        self.base_url = config.get("base_url", WSAI_API_BASE).rstrip("/")
        self.timeout = float(config.get("timeout_sec", 12.0))
        self.enabled = config.get("enabled", True)
        self.proxy_type = config.get("default_proxy_type", "datacenter")
        self.js_rendering = config.get("js_rendering", False)
        self._last_test_cache: Dict[str, Any] = {}
        self._sdk_client: Any = None

    # ------------------------------------------------------------------
    # SDK wrapper (dùng khi đã pip install webscraping_ai)
    # ------------------------------------------------------------------
    def _get_sdk_client(self) -> Any:
        """Khởi tạo SDK Client nếu thư viện đã được cài đặt"""
        if self._sdk_client is not None:
            return self._sdk_client
        try:
            from webscraping_ai import Client as WsaiSdkClient
            self._sdk_client = WsaiSdkClient(api_key=self.api_key)
            logger.info("WebScraping.AI SDK đã được tải thành công.")
            return self._sdk_client
        except ImportError:
            logger.debug("SDK webscraping_ai chưa được cài đặt — sử dụng REST API thuần.")
            return None

    # ------------------------------------------------------------------
    # Kiểm tra kết nối
    # ------------------------------------------------------------------
    def test_connection(self) -> Dict[str, Any]:
        """
        Kiểm tra trạng thái kết nối tới WebScraping.AI API và đo độ trễ.
        Trả về: { status, latency_ms, proxy_ip, api_key_masked, error }
        """
        t0 = time.time()
        # Dùng endpoint /html để kiểm tra — scrape trang nhẹ nhất có thể
        test_target = "https://api.ipify.org?format=json"
        params = {
            "api_key": self.api_key,
            "url": test_target,
            "proxy": self.proxy_type,
        }
        query_str = urllib.parse.urlencode(params)
        full_url = f"{self.base_url}/html?{query_str}"

        try:
            req = urllib.request.Request(
                full_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RobloxProxyEngine/2.0"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
                latency_ms = int((time.time() - t0) * 1000)

                # ipify trả về JSON — cố parse
                try:
                    data = json.loads(raw)
                    proxy_ip = data.get("ip") or data.get("origin") or raw.strip()
                except Exception:
                    proxy_ip = raw.strip()[:64]

                result = {
                    "status": "ONLINE",
                    "latency_ms": latency_ms,
                    "proxy_ip": proxy_ip,
                    "api_key_masked": self._mask_key(),
                    "error": None,
                }
                self._last_test_cache = result
                logger.info(f"WebScraping.AI API hoạt động tốt. IP: {proxy_ip} (Latency: {latency_ms}ms)")
                return result

        except Exception as e:
            latency_ms = int((time.time() - t0) * 1000)
            result = {
                "status": "OFFLINE",
                "latency_ms": latency_ms,
                "proxy_ip": None,
                "api_key_masked": self._mask_key(),
                "error": str(e),
            }
            self._last_test_cache = result
            logger.warning(f"Lỗi kiểm tra WebScraping.AI API: {e}")
            return result

    # ------------------------------------------------------------------
    # Lấy Proxy IP xoay vòng
    # ------------------------------------------------------------------
    def get_proxy_ip(self, country_code: Optional[str] = None) -> Optional[str]:
        """Lấy một IP duy nhất xoay vòng qua WebScraping.AI theo mã quốc gia"""
        test_target = "https://api.ipify.org?format=json"
        params: Dict[str, str] = {
            "api_key": self.api_key,
            "url": test_target,
            "proxy": self.proxy_type,
        }
        if country_code and country_code.upper() not in ["ALL", "MULTI"]:
            params["country"] = country_code.upper()

        query_str = urllib.parse.urlencode(params)
        full_url = f"{self.base_url}/html?{query_str}"

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
            logger.warning(f"Không thể lấy IP từ WebScraping.AI: {e}")
            return None

    # ------------------------------------------------------------------
    # Web Scraping — lấy HTML thuần
    # ------------------------------------------------------------------
    def fetch_url(self, url: str, country_code: Optional[str] = None,
                  render_js: Optional[bool] = None) -> Optional[str]:
        """Tải nội dung trang web bất kỳ qua mạng Proxy WebScraping.AI"""
        params: Dict[str, str] = {
            "api_key": self.api_key,
            "url": url,
            "proxy": self.proxy_type,
        }
        if country_code and country_code.upper() not in ["ALL", "MULTI"]:
            params["country"] = country_code.upper()
        js_flag = render_js if render_js is not None else self.js_rendering
        if js_flag:
            params["js"] = "true"

        query_str = urllib.parse.urlencode(params)
        full_url = f"{self.base_url}/html?{query_str}"

        try:
            req = urllib.request.Request(
                full_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RobloxProxyEngine/2.0"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Lỗi truy vấn URL qua WebScraping.AI: {e}")
            return None

    # ------------------------------------------------------------------
    # AI Question — hỏi đáp thông minh về nội dung trang web
    # ------------------------------------------------------------------
    def question(self, url: str, question: str,
                 country_code: Optional[str] = None,
                 context_limit: int = 4000) -> Optional[str]:
        """
        Hỏi AI về nội dung của một trang web — tương đương SDK:
            client.question(url, question="...")

        Ưu tiên dùng SDK nếu đã cài; nếu không thì gọi REST /question.
        """
        # Thử SDK trước
        sdk = self._get_sdk_client()
        if sdk is not None:
            try:
                answer = sdk.question(url, question=question)
                logger.info(f"AI Question (SDK) thành công cho URL: {url[:60]}")
                return answer
            except Exception as e:
                logger.warning(f"SDK question() thất bại, fallback REST: {e}")

        # Fallback — REST /question
        params: Dict[str, str] = {
            "api_key": self.api_key,
            "url": url,
            "question": question,
            "proxy": self.proxy_type,
        }
        if country_code and country_code.upper() not in ["ALL", "MULTI"]:
            params["country"] = country_code.upper()

        query_str = urllib.parse.urlencode(params)
        full_url = f"{self.base_url}/question?{query_str}"

        try:
            req = urllib.request.Request(
                full_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RobloxProxyEngine/2.0"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout + 10) as resp:
                answer = resp.read().decode("utf-8", errors="ignore").strip()
                logger.info(f"AI Question (REST) thành công cho URL: {url[:60]}")
                return answer[:context_limit] if len(answer) > context_limit else answer
        except Exception as e:
            logger.error(f"Lỗi AI Question qua WebScraping.AI: {e}")
            return None

    # ------------------------------------------------------------------
    # Batch Proxy Fetch — phục vụ Roblox Multi-Tag
    # ------------------------------------------------------------------
    def batch_fetch_proxies(self, count: int = 5, country_code: str = "ALL") -> List[Dict[str, str]]:
        """Lấy danh sách các IP riêng biệt từ WebScraping.AI cho từng Tag Roblox"""
        proxies: List[Dict[str, str]] = []
        c_upper = country_code.upper()

        country_rotation = ["JP", "SG", "US", "VN", "KR", "DE", "GB"]
        for i in range(count):
            target_country = country_rotation[i % len(country_rotation)] if c_upper in ["ALL", "MULTI"] else c_upper
            ip = self.get_proxy_ip(country_code=target_country)
            if ip:
                proxies.append({
                    "ip": f"{ip}:80",
                    "country": target_country,
                    "region": f"[{target_country}] WebScraping.AI Proxy",
                    "source": "WebScraping.AI API",
                })
        return proxies

    # ------------------------------------------------------------------
    # Tiện ích nội bộ
    # ------------------------------------------------------------------
    def _mask_key(self) -> str:
        """Che bớt API key cho mục đích hiển thị an toàn"""
        if len(self.api_key) > 12:
            return f"{self.api_key[:8]}...{self.api_key[-4:]}"
        return self.api_key

    def get_status_summary(self) -> Dict[str, Any]:
        """Trả về tóm tắt trạng thái client cho dashboard"""
        return {
            "provider": "WebScraping.AI",
            "enabled": self.enabled,
            "api_key_masked": self._mask_key(),
            "proxy_type": self.proxy_type,
            "js_rendering": self.js_rendering,
            "last_test": self._last_test_cache or "Chưa kiểm tra",
        }
