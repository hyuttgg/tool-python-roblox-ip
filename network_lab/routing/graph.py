# -*- coding: utf-8 -*-
"""
Graph Topology Model for Dynamic Routing Engine
"""

import threading
from typing import Dict, List, Optional, Set, Tuple


class Edge:
    def __init__(self, src: str, dst: str, cost: int = 1, latency_ms: float = 10.0, is_active: bool = True):
        self.src = src
        self.dst = dst
        self.cost = max(1, cost)
        self.latency_ms = max(0.1, latency_ms)
        self.is_active = is_active

    def __repr__(self):
        return f"<Edge {self.src} -> {self.dst} (Cost: {self.cost}, Latency: {self.latency_ms:.1f}ms, Active: {self.is_active})>"


class Node:
    def __init__(self, node_id: str, host: str = "127.0.0.1", port: int = 9001, is_alive: bool = True):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.is_alive = is_alive

    def __repr__(self):
        return f"<Node {self.node_id} ({self.host}:{self.port}) Status={'ALIVE' if self.is_alive else 'DOWN'}>"


class NetworkGraph:
    """
    Đồ thị mạng lưu trữ trạng thái các Node và Cạnh kết nối (Edges) giữa các router/nodes.
    Hỗ trợ Thread-Safe để các tiến trình Health-Checker và Routing Solver chạy song song.
    """
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._lock = threading.RLock()

    def add_node(self, node_id: str, host: str = "127.0.0.1", port: int = 9001) -> Node:
        with self._lock:
            if node_id not in self.nodes:
                self.nodes[node_id] = Node(node_id, host, port)
            return self.nodes[node_id]

    def set_node_status(self, node_id: str, is_alive: bool):
        with self._lock:
            if node_id in self.nodes:
                self.nodes[node_id].is_alive = is_alive

    def add_edge(self, src: str, dst: str, cost: int = 1, latency_ms: float = 10.0, bidirectional: bool = True):
        with self._lock:
            self.add_node(src)
            self.add_node(dst)

            # Cập nhật nếu đã có hoặc thêm mới
            found = False
            for e in self.edges:
                if e.src == src and e.dst == dst:
                    e.cost = cost
                    e.latency_ms = latency_ms
                    e.is_active = True
                    found = True
                    break
            if not found:
                self.edges.append(Edge(src, dst, cost, latency_ms))

            if bidirectional:
                found_rev = False
                for e in self.edges:
                    if e.src == dst and e.dst == src:
                        e.cost = cost
                        e.latency_ms = latency_ms
                        e.is_active = True
                        found_rev = True
                        break
                if not found_rev:
                    self.edges.append(Edge(dst, src, cost, latency_ms))

    def set_edge_status(self, src: str, dst: str, is_active: bool, bidirectional: bool = True):
        with self._lock:
            for e in self.edges:
                if (e.src == src and e.dst == dst) or (bidirectional and e.src == dst and e.dst == src):
                    e.is_active = is_active

    def update_edge_metric(self, src: str, dst: str, latency_ms: float, cost_multiplier: float = 1.0):
        with self._lock:
            for e in self.edges:
                if e.src == src and e.dst == dst:
                    e.latency_ms = latency_ms
                    e.cost = max(1, int(latency_ms * cost_multiplier))

    def get_active_nodes(self) -> List[str]:
        with self._lock:
            return [nid for nid, node in self.nodes.items() if node.is_alive]

    def get_active_edges(self) -> List[Edge]:
        with self._lock:
            alive_nodes = set(self.get_active_nodes())
            return [
                e for e in self.edges
                if e.is_active and e.src in alive_nodes and e.dst in alive_nodes
            ]

    def get_neighbors(self, node_id: str) -> List[Tuple[str, int, float]]:
        """Trả về danh sách (neighbor_id, cost, latency_ms) của các node láng giềng còn sống"""
        with self._lock:
            active_edges = self.get_active_edges()
            return [(e.dst, e.cost, e.latency_ms) for e in active_edges if e.src == node_id]

    def snapshot(self) -> Tuple[Dict[str, Node], List[Edge]]:
        """Lấy bản sao dữ liệu đồ thị bất biến tại thời điểm gọi"""
        with self._lock:
            nodes_copy = {k: Node(v.node_id, v.host, v.port, v.is_alive) for k, v in self.nodes.items()}
            edges_copy = [Edge(e.src, e.dst, e.cost, e.latency_ms, e.is_active) for e in self.edges]
            return nodes_copy, edges_copy
