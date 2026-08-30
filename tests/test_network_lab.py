# -*- coding: utf-8 -*-
"""
Automated Unit Tests for NetworkLab (Routing, DUAL, Cache, Proxy)
"""

import asyncio
import unittest
from network_lab.routing.graph import NetworkGraph
from network_lab.routing.bellman_ford import BellmanFordRouter
from network_lab.routing.dual_engine import DUALRouter
from network_lab.routing.route_cache import RouteCache
from network_lab.nodes.mock_servers import MockClusterManager
from network_lab.proxy.tcp_proxy import DynamicTcpProxyServer
from network_lab.client.test_client import NetworkLabTestClient


class TestNetworkLab(unittest.TestCase):

    def setUp(self):
        self.graph = NetworkGraph()
        self.graph.add_node("Router", "127.0.0.1", 8080)
        self.graph.add_node("Node_A", "127.0.0.1", 9001)
        self.graph.add_node("Node_B", "127.0.0.1", 9002)
        self.graph.add_node("Node_C", "127.0.0.1", 9003)

        # Topology:
        # Router -> A (Cost 10)
        # Router -> C (Cost 5)
        # C -> B (Cost 2)  => Router->C->B Cost = 7
        # A -> B (Cost 10) => Router->A->B Cost = 20
        self.graph.add_edge("Router", "Node_A", cost=10, latency_ms=20.0)
        self.graph.add_edge("Router", "Node_C", cost=5,  latency_ms=10.0)
        self.graph.add_edge("Node_C", "Node_B", cost=2,  latency_ms=5.0)
        self.graph.add_edge("Node_A", "Node_B", cost=10, latency_ms=20.0)

    def test_bellman_ford_shortest_path(self):
        rt = BellmanFordRouter.calculate(self.graph, "Router")
        route_to_b = rt.get_route("Node_B")

        self.assertIsNotNone(route_to_b)
        self.assertEqual(route_to_b.cost, 7)
        self.assertEqual(route_to_b.next_hop, "Node_C")
        self.assertEqual(route_to_b.path, ["Router", "Node_C", "Node_B"])

    def test_bellman_ford_failover_on_node_down(self):
        # Giết Node C
        self.graph.set_node_status("Node_C", False)

        rt = BellmanFordRouter.calculate(self.graph, "Router")
        route_to_b = rt.get_route("Node_B")

        self.assertIsNotNone(route_to_b)
        self.assertEqual(route_to_b.cost, 20)
        self.assertEqual(route_to_b.next_hop, "Node_A")
        self.assertEqual(route_to_b.path, ["Router", "Node_A", "Node_B"])

    def test_dual_engine_topology_and_feasible_successor(self):
        dual_table = DUALRouter.build_topology_table(self.graph, "Router")
        entry_b = dual_table.get("Node_B")

        self.assertIsNotNone(entry_b)
        self.assertEqual(entry_b.successor, "Node_C")
        self.assertEqual(entry_b.feasible_distance, 7)

    def test_route_cache_hits_and_invalidation(self):
        cache = RouteCache(default_ttl=5.0)
        rt = BellmanFordRouter.calculate(self.graph, "Router")
        route_b = rt.get_route("Node_B")

        cache.put("Node_B", route_b)
        self.assertIsNotNone(cache.get("Node_B"))
        self.assertEqual(cache.hits, 1)

        cache.invalidate_all()
        self.assertIsNone(cache.get("Node_B"))
        self.assertEqual(cache.misses, 1)

    def test_end_to_end_proxy_forwarding(self):
        async def run_async_test():
            cluster = MockClusterManager()
            await cluster.start_all()

            cache = RouteCache()
            proxy = DynamicTcpProxyServer(
                graph=self.graph,
                route_cache=cache,
                listen_host="127.0.0.1",
                listen_port=8089,
                source_router_id="Router",
                default_target_node="Node_B"
            )
            await proxy.start()

            client = NetworkLabTestClient(proxy_host="127.0.0.1", proxy_port=8089)
            metric = await client.send_single_request(seq=1, message="HELO")

            self.assertTrue(metric.success)
            # Proxy forward tới Next-Hop được tính toán (Node_C)
            self.assertEqual(metric.responder_node, "Node_C")

            await proxy.stop()
            await cluster.stop_all()

        asyncio.run(run_async_test())


if __name__ == "__main__":
    unittest.main()
