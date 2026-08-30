# -*- coding: utf-8 -*-
"""
Smart Proxy Rotator & Sticky Session Manager (Oxylabs Architecture)
Quản lý Pool Proxy thông minh với các cơ chế:
  - Sticky Session Per-Tag (Giữ nguyên 1 IP cho mỗi Tag, chỉ xoay khi Server Hop hoặc lỗi).
  - Tự động Health Check & chấm điểm độ trễ (Latency Scoring).
  - Tự động chuyển đổi dự phòng (Automatic Failover) khi gặp HTTP 429, 403, Timeout.
  - Quản lý phiên tái kết nối an toàn chống văng Game Roblox.
"""

import time
import random
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from config.logging import setup_logger

logger = setup_logger("proxy_rotator")


@dataclass
class ProxyNode:
    ip: str
    port: int = 8080
    protocol: str = "http"
    country: str = "ALL"
    region: str = "AUTO"
    latency_ms: int = 100
    is_alive: bool = True
    consecutive_fails: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    last_checked: float = field(default_factory=time.time)

    @property
    def formatted_address(self) -> str:
        return f"{self.ip}:{self.port}" if self.port != 80 else self.ip

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests


@dataclass
class TagProxySession:
    tag_id: str
    current_node: ProxyNode
    assigned_at: float = field(default_factory=time.time)
    failover_count: int = 0
    sticky: bool = True
    history: List[str] = field(default_factory=list)


class SmartProxyRotator:
    """Bộ điều phối xoay vòng Proxy và quản lý Sticky Session thông minh"""

    def __init__(self):
        self.pool: Dict[str, ProxyNode] = {}
        self.sessions: Dict[str, TagProxySession] = {}
        self._lock = threading.RLock()
        self.rotation_mode: str = "STICKY"  # STICKY, ROUND_ROBIN, LEAST_PING

    def add_proxy(self, ip: str, port: int = 8080, country: str = "ALL", region: str = "AUTO", latency_ms: int = 100) -> ProxyNode:
        with self._lock:
            key = f"{ip}:{port}"
            node = ProxyNode(
                ip=ip,
                port=port,
                country=country,
                region=region,
                latency_ms=latency_ms,
                is_alive=True
            )
            self.pool[key] = node
            return node

    def add_proxies_batch(self, proxies_data: List[Dict]) -> int:
        added = 0
        with self._lock:
            for p in proxies_data:
                ip = p.get("ip", "")
                if not ip:
                    continue
                port = int(p.get("port", 8080))
                country = p.get("country", "ALL")
                region = p.get("region", f"[{country}] Dedicated")
                latency = int(p.get("latency_ms", 100))
                self.add_proxy(ip, port, country, region, latency)
                added += 1
        return added

    def get_or_create_tag_session(self, tag_id: str, country_code: str = "ALL") -> ProxyNode:
        """
        Lấy hoặc khởi tạo Sticky Proxy Session cho 1 Tag Roblox cụ thể.
        Mỗi Tag giữ nguyên IP này trong suốt quá trình cày game.
        """
        with self._lock:
            if tag_id in self.sessions:
                sess = self.sessions[tag_id]
                if sess.current_node.is_alive:
                    return sess.current_node
                else:
                    logger.info(f"🔄 [ROTATOR] Proxy cũ của [{tag_id}] đã chết, tự động xoay sang IP mới...")

            # Chọn node tối ưu mới
            candidate = self._select_best_candidate(country_code)
            if not candidate:
                candidate = ProxyNode(ip="127.0.0.1", port=8080, country=country_code, region=f"[{country_code}] Local")

            sess = TagProxySession(
                tag_id=tag_id,
                current_node=candidate,
                assigned_at=time.time(),
                sticky=True,
                history=[candidate.formatted_address]
            )
            self.sessions[tag_id] = sess
            logger.info(f"📍 [ROTATOR] Đã gán Sticky Proxy [{candidate.formatted_address}] ({candidate.country}) cho Tag [{tag_id}]")
            return candidate

    def trigger_failover_for_tag(self, tag_id: str, reason: str = "NETWORK_ERROR") -> ProxyNode:
        """Tự động chuyển đổi dự phòng sang IP khác cùng quốc gia khi phát hiện lỗi mạng / Rate Limit"""
        with self._lock:
            old_sess = self.sessions.get(tag_id)
            country = old_sess.current_node.country if old_sess else "ALL"
            if old_sess:
                old_sess.current_node.consecutive_fails += 1
                if old_sess.current_node.consecutive_fails >= 3:
                    old_sess.current_node.is_alive = False

            new_node = self._select_best_candidate(country, exclude_ip=old_sess.current_node.ip if old_sess else None)
            if not new_node:
                new_node = ProxyNode(ip="127.0.0.1", port=8080, country=country, region=f"[{country}] Backup")

            if old_sess:
                old_sess.current_node = new_node
                old_sess.failover_count += 1
                old_sess.history.append(new_node.formatted_address)
            else:
                self.sessions[tag_id] = TagProxySession(tag_id=tag_id, current_node=new_node, history=[new_node.formatted_address])

            logger.info(f"⚡ [ROTATOR FAILOVER] Tag [{tag_id}] đổi sang Proxy dự phòng: {new_node.formatted_address} (Lý do: {reason})")
            return new_node

    def _select_best_candidate(self, country_code: str = "ALL", exclude_ip: Optional[str] = None) -> Optional[ProxyNode]:
        """Chọn ứng viên Proxy còn sống có Ping thấp nhất theo quốc gia chỉ định"""
        valid_nodes = [
            node for node in self.pool.values()
            if node.is_alive and (country_code == "ALL" or country_code == "MULTI" or node.country == country_code)
            and (exclude_ip is None or node.ip != exclude_ip)
        ]

        if not valid_nodes:
            # Fallback nếu không có quốc gia chỉ định: lấy toàn bộ node còn sống
            valid_nodes = [node for node in self.pool.values() if node.is_alive and (exclude_ip is None or node.ip != exclude_ip)]

        if not valid_nodes:
            return None

        # Sắp xếp theo ping tăng dần
        valid_nodes.sort(key=lambda x: x.latency_ms)
        return valid_nodes[0]

    def report_request_outcome(self, ip: str, success: bool):
        """Ghi nhận kết quả request để điều chỉnh tỷ lệ thành công của Proxy"""
        with self._lock:
            for node in self.pool.values():
                if node.ip == ip:
                    node.total_requests += 1
                    if success:
                        node.successful_requests += 1
                        node.consecutive_fails = 0
                    else:
                        node.consecutive_fails += 1
                        if node.consecutive_fails >= 5:
                            node.is_alive = False
                    break

    def get_status_summary(self) -> Dict:
        with self._lock:
            total = len(self.pool)
            alive = len([n for n in self.pool.values() if n.is_alive])
            sessions_count = len(self.sessions)
            return {
                "total_proxies": total,
                "alive_proxies": alive,
                "active_sessions": sessions_count,
                "rotation_mode": self.rotation_mode,
                "sessions": {
                    tid: {
                        "ip": sess.current_node.ip,
                        "port": sess.current_node.port,
                        "country": sess.current_node.country,
                        "latency_ms": sess.current_node.latency_ms,
                        "failovers": sess.failover_count
                    }
                    for tid, sess in self.sessions.items()
                }
            }


# Singleton instance
proxy_rotator = SmartProxyRotator()
