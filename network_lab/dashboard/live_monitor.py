# -*- coding: utf-8 -*-
"""
Live Monitor & Topology Dashboard for Network Lab
Hiển thị sơ đồ ASCII, Routing Table, DUAL Topology, Cache Hit Rate và Event Log.
"""

from network_lab.routing.graph import NetworkGraph
from network_lab.routing.bellman_ford import BellmanFordRouter
from network_lab.routing.dual_engine import DUALRouter
from network_lab.routing.route_cache import RouteCache
from network_lab.proxy.tcp_proxy import DynamicTcpProxyServer


class NetworkLabDashboard:
    @staticmethod
    def render(
        graph: NetworkGraph,
        route_cache: RouteCache,
        proxy_server: DynamicTcpProxyServer,
        source_node: str = "Router"
    ):
        print("\n" + "=" * 80)
        print("                   NETWORK LAB DYNAMIC ROUTING DASHBOARD")
        print("=" * 80)

        # 1. Topology & Edge Costs
        print("\n[1] TOPOLOGY & EDGE METRICS:")
        print(f"{'Source':<12} -> {'Destination':<12} | {'Cost':<6} | {'Latency':<10} | {'Status'}")
        print("-" * 55)
        for e in graph.edges:
            status = "ACTIVE" if e.is_active else "DISABLED"
            print(f"{e.src:<12} -> {e.dst:<12} | {e.cost:<6} | {e.latency_ms:>6.1f} ms  | {status}")

        # 2. Bellman-Ford Routing Table
        rt = BellmanFordRouter.calculate(graph, source_node)
        print(f"\n[2] BELLMAN-FORD ROUTING TABLE (Node: {source_node}):")
        print(f"{'Destination':<15} | {'NextHop':<12} | {'Cost':<8} | {'Estimated Latency'} | {'Path'}")
        print("-" * 75)
        for dest, entry in sorted(rt.routes.items()):
            cost_val = str(entry.cost) if entry.cost < 999999 else "INF"
            next_hop = entry.next_hop or "NONE"
            path_str = " -> ".join(entry.path) if entry.path else "UNREACHABLE"
            print(f"{dest:<15} | {next_hop:<12} | {cost_val:<8} | {entry.latency_ms:>13.1f} ms | {path_str}")

        # 3. DUAL Feasible Successor Table
        dual_table = DUALRouter.build_topology_table(graph, source_node)
        print(f"\n[3] DUAL CONVERGENCE TABLE (EIGRP Concept):")
        print(f"{'Destination':<15} | {'Successor (Primary)':<20} | {'FD':<6} | {'Feasible Successor (Backup)'}")
        print("-" * 75)
        for dest, d_entry in sorted(dual_table.items()):
            fs_str = ", ".join(d_entry.feasible_successors) if d_entry.feasible_successors else "NONE (No FS)"
            succ_str = d_entry.successor or "NONE"
            print(f"{dest:<15} | {succ_str:<20} | {d_entry.feasible_distance:<6} | {fs_str}")

        # 4. Proxy & Cache Telemetry
        c_stats = route_cache.get_stats()
        print(f"\n[4] PROXY & ROUTE CACHE METRICS:")
        print(f"  • Proxy Address      : {proxy_server.listen_host}:{proxy_server.listen_port}")
        print(f"  • Total Connections  : {proxy_server.total_connections}")
        print(f"  • Active Sessions    : {len(proxy_server.active_sessions)}")
        print(f"  • Route Cache Hits   : {c_stats['hits']} | Misses: {c_stats['misses']} | Hit Rate: {c_stats['hit_rate']}")
        print("=" * 80 + "\n")
