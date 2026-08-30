# -*- coding: utf-8 -*-
"""
Bellman-Ford & Distance Vector Routing Engine
"""

from typing import Dict, List, Optional, Tuple
from network_lab.routing.graph import NetworkGraph, Edge


class RouteEntry:
    def __init__(
        self,
        destination: str,
        next_hop: Optional[str],
        cost: int,
        path: List[str],
        latency_ms: float = 0.0
    ):
        self.destination = destination
        self.next_hop = next_hop
        self.cost = cost
        self.path = path
        self.latency_ms = latency_ms

    def to_dict(self):
        return {
            "destination": self.destination,
            "next_hop": self.next_hop,
            "cost": self.cost if self.cost < 999999 else "UNREACHABLE",
            "path": " -> ".join(self.path) if self.path else "NONE",
            "latency_ms": f"{self.latency_ms:.1f}ms"
        }

    def __repr__(self):
        return f"<Route to={self.destination} next_hop={self.next_hop} cost={self.cost} path={'->'.join(self.path)}>"


class RoutingTable:
    def __init__(self, source_node: str, routes: Dict[str, RouteEntry], iterations: int, converged: bool):
        self.source_node = source_node
        self.routes = routes
        self.iterations = iterations
        self.converged = converged

    def get_route(self, destination: str) -> Optional[RouteEntry]:
        return self.routes.get(destination)

    def print_table(self):
        print(f"\n=== ROUTING TABLE FOR NODE [{self.source_node}] (Converged in {self.iterations} iterations) ===")
        print(f"{'Destination':<15} | {'NextHop':<15} | {'Cost':<10} | {'Latency':<12} | {'Full Path'}")
        print("-" * 75)
        for dest, entry in sorted(self.routes.items()):
            cost_str = str(entry.cost) if entry.cost < 999999 else "INF"
            next_hop_str = entry.next_hop or "NONE"
            path_str = " -> ".join(entry.path) if entry.path else "UNREACHABLE"
            print(f"{dest:<15} | {next_hop_str:<15} | {cost_str:<10} | {entry.latency_ms:>6.1f} ms    | {path_str}")


class BellmanFordRouter:
    """
    Bộ giải thuật toán Bellman-Ford / Distance Vector:
    D_x(y) = min_{v in N(x)} { c(x, v) + D_v(y) }
    """
    INF = 999999

    @classmethod
    def calculate(cls, graph: NetworkGraph, source_node: str) -> RoutingTable:
        active_nodes = set(graph.get_active_nodes())
        active_edges = graph.get_active_edges()

        if source_node not in active_nodes:
            return RoutingTable(source_node, {}, 0, False)

        # 1. Khởi tạo khoảng cách và predecessor
        distance: Dict[str, int] = {node: cls.INF for node in active_nodes}
        latency_map: Dict[str, float] = {node: 0.0 for node in active_nodes}
        predecessor: Dict[str, Optional[str]] = {node: None for node in active_nodes}

        distance[source_node] = 0

        # 2. Relax các cạnh |V| - 1 lần
        iterations = 0
        num_nodes = len(active_nodes)

        for i in range(num_nodes - 1):
            changed = False
            iterations += 1
            for edge in active_edges:
                u, v, cost, lat = edge.src, edge.dst, edge.cost, edge.latency_ms
                if distance[u] != cls.INF and distance[u] + cost < distance[v]:
                    distance[v] = distance[u] + cost
                    latency_map[v] = latency_map[u] + lat
                    predecessor[v] = u
                    changed = True

            if not changed:
                break

        # 3. Xây dựng Routing Table & Next-Hop
        routes: Dict[str, RouteEntry] = {}

        for node in active_nodes:
            if distance[node] == cls.INF:
                routes[node] = RouteEntry(node, None, cls.INF, [], 0.0)
                continue

            if node == source_node:
                routes[node] = RouteEntry(node, source_node, 0, [source_node], 0.0)
                continue

            # Tái tạo đường đi từ source tới node
            curr = node
            path = []
            visited = set()
            while curr is not None and curr not in visited:
                path.append(curr)
                visited.add(curr)
                if curr == source_node:
                    break
                curr = predecessor.get(curr)

            path.reverse()

            if path and path[0] == source_node:
                # Next hop là node ngay sau source_node
                next_hop = path[1] if len(path) > 1 else node
                routes[node] = RouteEntry(node, next_hop, distance[node], path, latency_map[node])
            else:
                routes[node] = RouteEntry(node, None, cls.INF, [], 0.0)

        return RoutingTable(source_node, routes, iterations, True)
