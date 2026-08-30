# -*- coding: utf-8 -*-
"""
Least Connections Proxy Load Balancer for Roblox Multi-Account / Clone Farm
Thuật toán Kết nối ít nhất:
- Tự động đẩy tài khoản Roblox chuẩn bị đăng nhập vào IP Proxy nào đang có ít máy kết nối nhất.
- Tối ưu hóa băng thông cho từng acc clone, chống rate limit / ban wave.
- Hỗ trợ an toàn đa luồng (Thread-safe), Health Check, Max Limit per Proxy và Auto-Release.
"""

import json
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple, Any

try:
    from config.logging import setup_logger
    logger = setup_logger("least_connections_balancer")
except Exception:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("least_connections_balancer")


class ProxyNode:
    """
    Biểu diễn một Proxy Endpoint (IP/Domain + Port + Giao thức) cùng số lượng kết nối thực thời.
    """
    def __init__(
        self,
        proxy_id: str,
        host: str,
        port: int,
        protocol: str = "socks5",
        username: Optional[str] = None,
        password: Optional[str] = None,
        max_connections: int = 5,
        weight: int = 1,
        latency_ms: int = 50,
        country: str = "MULTI"
    ):
        self.proxy_id = str(proxy_id)
        self.host = host
        self.port = int(port)
        self.protocol = protocol.lower()
        self.username = username
        self.password = password
        self.max_connections = max(1, int(max_connections))
        self.weight = max(1, int(weight))
        self.latency_ms = int(latency_ms)
        self.country = country
        self.is_healthy = True
        
        # Thống kê tải
        self.active_connections = 0
        self.total_served = 0
        self.last_assigned_time: float = 0.0

    @property
    def endpoint(self) -> str:
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def load_ratio(self) -> float:
        """Tỷ lệ tải tính theo trọng số (Weighted Load Ratio)"""
        return self.active_connections / self.weight

    def is_available(self) -> bool:
        """Kiểm tra proxy có online và còn dung lượng nhận thêm acc không"""
        return self.is_healthy and (self.active_connections < self.max_connections)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proxy_id": self.proxy_id,
            "host": self.host,
            "port": self.port,
            "protocol": self.protocol,
            "endpoint": self.endpoint,
            "max_connections": self.max_connections,
            "active_connections": self.active_connections,
            "load_ratio": round(self.load_ratio, 2),
            "weight": self.weight,
            "latency_ms": self.latency_ms,
            "country": self.country,
            "is_healthy": self.is_healthy,
            "total_served": self.total_served
        }

    def __repr__(self) -> str:
        return (
            f"<ProxyNode id={self.proxy_id} {self.endpoint} "
            f"active={self.active_connections}/{self.max_connections} "
            f"ping={self.latency_ms}ms "
            f"status={'ONLINE' if self.is_healthy else 'DEAD'}>"
        )


class LeastConnectionsBalancer:
    """
    Bộ cân bằng tải thuật toán Kết nối ít nhất (Least Connections Load Balancer).
    Đảm bảo:
      1. Acc chuẩn bị đăng nhập luôn được đẩy vào Proxy có số acc đang chạy ít nhất.
      2. Nếu bằng nhau -> Ưu tiên Proxy có Ping (latency_ms) thấp nhất.
      3. An toàn 100% trong môi trường đa luồng (Multi-threading / Multi-clone).
    """

    def __init__(self, default_max_per_proxy: int = 5):
        self.default_max_per_proxy = default_max_per_proxy
        self._proxies: Dict[str, ProxyNode] = {}
        self._account_to_proxy: Dict[str, str] = {}  # account_id / clone_tag -> proxy_id
        self._lock = threading.RLock()

    def add_proxy(
        self,
        proxy_id: str,
        host: str,
        port: int,
        protocol: str = "socks5",
        username: Optional[str] = None,
        password: Optional[str] = None,
        max_connections: Optional[int] = None,
        weight: int = 1,
        latency_ms: int = 50,
        country: str = "MULTI"
    ) -> ProxyNode:
        """Thêm hoặc cập nhật một Proxy vào danh sách quản lý"""
        with self._lock:
            max_conn = max_connections if (max_connections and max_connections > 0) else self.default_max_per_proxy
            node = ProxyNode(
                proxy_id=proxy_id,
                host=host,
                port=port,
                protocol=protocol,
                username=username,
                password=password,
                max_connections=max_conn,
                weight=weight,
                latency_ms=latency_ms,
                country=country
            )
            self._proxies[str(proxy_id)] = node
            return node

    def add_proxies_from_list(self, proxy_list: List[Dict[str, Any]]):
        """Nạp danh sách Proxy từ dữ liệu JSON hoặc danh sách Proxy Scraped"""
        with self._lock:
            for idx, p in enumerate(proxy_list):
                pid = p.get("id") or p.get("proxy_id") or f"Proxy_{idx + 1}"
                host = p.get("host") or p.get("ip") or "127.0.0.1"
                port = int(p.get("port", 1080))
                proto = p.get("protocol") or p.get("type", "socks5")
                user = p.get("username") or p.get("user")
                pwd = p.get("password") or p.get("pass")
                max_conn = p.get("max_connections", self.default_max_per_proxy)
                weight = p.get("weight", 1)
                latency = p.get("latency_ms") or p.get("ping", 50)
                country = p.get("country", "MULTI")

                self.add_proxy(
                    proxy_id=pid,
                    host=host,
                    port=port,
                    protocol=proto,
                    username=user,
                    password=pwd,
                    max_connections=max_conn,
                    weight=weight,
                    latency_ms=latency,
                    country=country
                )

    def remove_proxy(self, proxy_id: str) -> bool:
        """Xóa Proxy khỏi pool và hủy liên kết các acc đang gắn với nó"""
        with self._lock:
            proxy_id = str(proxy_id)
            if proxy_id in self._proxies:
                del self._proxies[proxy_id]
                # Hủy map các acc gắn với proxy này để chúng được cấp lại proxy khác khi cần
                orphans = [acc for acc, pid in self._account_to_proxy.items() if pid == proxy_id]
                for acc in orphans:
                    del self._account_to_proxy[acc]
                return True
            return False

    def set_health_status(self, proxy_id: str, is_healthy: bool, latency_ms: Optional[int] = None):
        """Cập nhật trạng thái sống/chết (Health Check) & Ping mới"""
        with self._lock:
            proxy_id = str(proxy_id)
            node = self._proxies.get(proxy_id)
            if node:
                node.is_healthy = is_healthy
                if latency_ms is not None:
                    node.latency_ms = int(latency_ms)

    def allocate_proxy_for_account(
        self,
        account_id: str,
        preferred_country: Optional[str] = None
    ) -> Optional[ProxyNode]:
        """
        [CORE THUẬT TOÁN LEAST CONNECTIONS]
        Cấp phát Proxy cho một tài khoản / clone Roblox chuẩn bị vào game:
        1. Nếu tài khoản đã có Proxy hợp lệ đang gán -> Trả về Proxy đó (Sticky Session).
        2. Lọc các Proxy khả dụng (Healthy = True, Active < Max).
        3. Áp dụng bộ lọc quốc gia (nếu được yêu cầu).
        4. Chọn Proxy có:
             - Tỷ lệ kết nối ít nhất: min(active_connections / weight)
             - Nếu bằng nhau: min(latency_ms) (Ping thấp nhất)
             - Nếu vẫn bằng: min(total_served) (Phân bổ công bằng)
        5. Tăng active_connections lên 1 và gán session.
        """
        with self._lock:
            acc_key = str(account_id)

            # 1. Kiểm tra session hiện tại
            if acc_key in self._account_to_proxy:
                current_pid = self._account_to_proxy[acc_key]
                node = self._proxies.get(current_pid)
                if node and node.is_healthy:
                    return node
                else:
                    # Proxy cũ bị die, gỡ session để cấp IP mới
                    self._account_to_proxy.pop(acc_key, None)

            # 2. Lọc Proxy khả dụng
            candidates = [p for p in self._proxies.values() if p.is_available()]

            if not candidates:
                logger.warning(f"No available proxy in pool for account {acc_key} (all full or dead)!")
                return None

            # 3. Lọc quốc gia nếu có yêu cầu
            if preferred_country and preferred_country != "MULTI":
                matched = [p for p in candidates if p.country.upper() == preferred_country.upper()]
                if matched:
                    candidates = matched

            # 4. Tìm Proxy có ít kết nối nhất
            best_proxy = min(
                candidates,
                key=lambda p: (
                    p.load_ratio,        # Ít acc kết nối nhất
                    p.latency_ms,         # Ping thấp nhất
                    p.total_served,       # Ít lượt phục vụ nhất
                    p.last_assigned_time  # Cấp phát lâu nhất trước đó
                )
            )

            # 5. Gán kết nối
            best_proxy.active_connections += 1
            best_proxy.total_served += 1
            best_proxy.last_assigned_time = time.time()
            self._account_to_proxy[acc_key] = best_proxy.proxy_id

            logger.info(
                f"[LEAST-CONN] Allocated {best_proxy.proxy_id} ({best_proxy.endpoint}) "
                f"to {acc_key} | Load: {best_proxy.active_connections}/{best_proxy.max_connections} "
                f"| Ping: {best_proxy.latency_ms}ms"
            )
            return best_proxy

    def release_proxy_for_account(self, account_id: str) -> bool:
        """
        Giải phóng 1 slot kết nối khi tài khoản Roblox đăng xuất / tắt cửa sổ / crash
        """
        with self._lock:
            acc_key = str(account_id)
            if acc_key not in self._account_to_proxy:
                return False

            proxy_id = self._account_to_proxy.pop(acc_key)
            node = self._proxies.get(proxy_id)
            if node and node.active_connections > 0:
                node.active_connections -= 1
                logger.info(
                    f"[LEAST-CONN] Released {proxy_id} from {acc_key} | "
                    f"Remaining load: {node.active_connections}/{node.max_connections}"
                )
                return True
            return False

    def get_assigned_proxy(self, account_id: str) -> Optional[ProxyNode]:
        """Lấy Proxy đang được gán cho một tài khoản"""
        with self._lock:
            pid = self._account_to_proxy.get(str(account_id))
            if pid:
                return self._proxies.get(pid)
            return None

    def get_pool_status(self) -> List[Dict[str, Any]]:
        """Lấy danh sách thống kê toàn bộ Pool Proxy"""
        with self._lock:
            return [node.to_dict() for node in self._proxies.values()]

    def reset_all_connections(self):
        """Reset toàn bộ kết nối active về 0"""
        with self._lock:
            self._account_to_proxy.clear()
            for node in self._proxies.values():
                node.active_connections = 0


# Instance toàn cục để tái sử dụng trong hệ thống
global_balancer = LeastConnectionsBalancer()
