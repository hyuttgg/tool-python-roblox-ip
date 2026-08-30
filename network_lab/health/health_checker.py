# -*- coding: utf-8 -*-
"""
Health Checker & Realtime Latency Monitor
Định kỳ kiểm tra trạng thái sống/chết (TCP Ping, RTT) và cập nhật đồ thị mạng.
"""

import asyncio
import logging
import time
from typing import Callable, Dict, List, Optional
from network_lab.routing.graph import NetworkGraph
from network_lab.routing.route_cache import RouteCache

logger = logging.getLogger("health_checker")


class HealthReport:
    def __init__(self, node_id: str, is_alive: bool, latency_ms: float):
        self.node_id = node_id
        self.is_alive = is_alive
        self.latency_ms = latency_ms
        self.checked_at = time.time()


class NodeHealthChecker:
    def __init__(
        self,
        graph: NetworkGraph,
        route_cache: Optional[RouteCache] = None,
        check_interval: float = 2.0,
        timeout: float = 1.0,
        on_topology_change: Optional[Callable[[], None]] = None
    ):
        self.graph = graph
        self.route_cache = route_cache
        self.check_interval = check_interval
        self.timeout = timeout
        self.on_topology_change = on_topology_change
        self.is_running = False
        self.last_reports: Dict[str, HealthReport] = {}
        self._task: Optional[asyncio.Task] = None

    async def probe_node(self, host: str, port: int) -> Tuple[bool, float]:
        start = time.perf_counter()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=self.timeout
            )
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            writer.close()
            await writer.wait_closed()
            return True, max(0.5, elapsed_ms)
        except Exception:
            return False, 999.0

    async def _check_cycle(self):
        changed = False
        nodes_copy = dict(self.graph.nodes)

        for node_id, node in nodes_copy.items():
            alive, latency = await self.probe_node(node.host, node.port)
            old_alive = node.is_alive
            
            if old_alive != alive:
                changed = True
                self.graph.set_node_status(node_id, alive)
                logger.warning(f"[HEALTH] Node [{node_id}] status changed: {'ALIVE' if alive else 'DOWN'}")

            if alive:
                # Cập nhật dynamic cost dựa trên latency
                self.graph.update_edge_metric("Router", node_id, latency_ms=latency, cost_multiplier=1.0)

            self.last_reports[node_id] = HealthReport(node_id, alive, latency)

        if changed:
            if self.route_cache:
                self.route_cache.invalidate_all()
            if self.on_topology_change:
                self.on_topology_change()

    async def start(self):
        self.is_running = True
        while self.is_running:
            try:
                await self._check_cycle()
            except Exception as e:
                logger.error(f"Error in health check cycle: {e}")
            await asyncio.sleep(self.check_interval)

    def stop(self):
        self.is_running = False
