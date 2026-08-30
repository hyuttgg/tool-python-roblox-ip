# -*- coding: utf-8 -*-
"""
Chaos Injector for Failure & Latency Simulation
Cho phép giả lập mất kết nối, spike ping và kiểm thử failover.
"""

import asyncio
import logging
from typing import Optional
from network_lab.nodes.mock_servers import MockClusterManager
from network_lab.routing.graph import NetworkGraph
from network_lab.routing.route_cache import RouteCache

logger = logging.getLogger("chaos_injector")


class ChaosInjector:
    def __init__(self, cluster: MockClusterManager, graph: NetworkGraph, route_cache: RouteCache):
        self.cluster = cluster
        self.graph = graph
        self.route_cache = route_cache

    async def kill_node(self, node_id: str):
        """Giả lập sự cố sập Node"""
        logger.warning(f"💥 [CHAOS] Killing {node_id}...")
        await self.cluster.stop_node(node_id)
        self.graph.set_node_status(node_id, False)
        self.route_cache.invalidate_all()

    async def revive_node(self, node_id: str):
        """Giả lập khôi phục Node"""
        logger.info(f"✨ [CHAOS] Reviving {node_id}...")
        await self.cluster.start_node(node_id)
        self.graph.set_node_status(node_id, True)
        self.route_cache.invalidate_all()

    def inject_latency_spike(self, src: str, dst: str, spike_ms: float = 250.0):
        """Giả lập nghẽn mạng tăng đột biến Ping"""
        logger.warning(f"⚠️ [CHAOS] Injected latency spike on {src} -> {dst}: {spike_ms}ms")
        self.graph.update_edge_metric(src, dst, latency_ms=spike_ms, cost_multiplier=1.0)
        self.route_cache.invalidate_all()

    def restore_latency(self, src: str, dst: str, normal_ms: float = 15.0):
        """Khôi phục Ping bình thường"""
        logger.info(f"🟢 [CHAOS] Restored normal latency on {src} -> {dst}: {normal_ms}ms")
        self.graph.update_edge_metric(src, dst, latency_ms=normal_ms, cost_multiplier=1.0)
        self.route_cache.invalidate_all()
