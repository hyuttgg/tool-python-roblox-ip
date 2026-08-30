# -*- coding: utf-8 -*-
"""
Thread-safe Route Cache with TTL and Hit/Miss Telemetry
"""

import threading
import time
from typing import Dict, Optional, Tuple, Any
from network_lab.routing.bellman_ford import RouteEntry


class CacheEntry:
    def __init__(self, route: RouteEntry, ttl_seconds: float = 30.0):
        self.route = route
        self.expires_at = time.time() + ttl_seconds

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class RouteCache:
    """
    Bộ nhớ đệm tuyến đường (Route Cache) chuẩn Concurrent:
    - Giảm thiểu độ trễ tra cứu routing table cho hàng ngàn kết nối TCP/sec.
    - Tự động hết hạn (TTL) và hỗ trợ Invalidation khi có sự kiện thay đổi Topology.
    """
    def __init__(self, default_ttl: float = 15.0):
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

        # Telemetry metrics
        self.hits = 0
        self.misses = 0
        self.invalidations = 0

    def get(self, destination: str) -> Optional[RouteEntry]:
        with self._lock:
            entry = self._cache.get(destination)
            if entry is not None:
                if not entry.is_expired():
                    self.hits += 1
                    return entry.route
                else:
                    # Đã hết hạn
                    del self._cache[destination]

            self.misses += 1
            return None

    def put(self, destination: str, route: RouteEntry, ttl: Optional[float] = None):
        with self._lock:
            actual_ttl = ttl or self.default_ttl
            self._cache[destination] = CacheEntry(route, actual_ttl)

    def invalidate_all(self):
        """Xóa sạch cache khi mạng có biến động lớn (Link Up / Link Down)"""
        with self._lock:
            self.invalidations += len(self._cache)
            self._cache.clear()

    def invalidate(self, destination: str):
        with self._lock:
            if destination in self._cache:
                del self._cache[destination]
                self.invalidations += 1

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_lookups = self.hits + self.misses
            hit_rate = (self.hits / total_lookups * 100.0) if total_lookups > 0 else 0.0
            return {
                "cached_routes_count": len(self._cache),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": f"{hit_rate:.1f}%",
                "invalidations": self.invalidations
            }
