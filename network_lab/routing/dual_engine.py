# -*- coding: utf-8 -*-
"""
DUAL (Diffusing Update Algorithm - EIGRP concept) Engine
Hỗ trợ Feasible Distance (FD), Reported Distance (RD), và Feasible Successor (FS)
để thực hiện chuyển mạch dự phòng tức thì (Sub-millisecond Zero Recomputation Failover).
"""

from typing import Dict, List, Optional, Tuple
from network_lab.routing.graph import NetworkGraph
from network_lab.routing.bellman_ford import BellmanFordRouter


class NeighborRouteInfo:
    def __init__(self, neighbor: str, link_cost: int, reported_distance: int):
        self.neighbor = neighbor
        self.link_cost = link_cost
        self.reported_distance = reported_distance  # RD (khoảng cách từ neighbor tới đích)
        self.computed_distance = link_cost + reported_distance  # CD = c(S, V) + RD(V)

    def is_feasible_successor(self, feasible_distance: int) -> bool:
        """
        Feasibility Condition (FC):
        Neighbor là Tuyến dự phòng Khả thi (FS) nếu RD < FD hiện tại (chống routing loop tuyệt đối).
        """
        return self.reported_distance < feasible_distance


class DUALDestinationEntry:
    def __init__(self, destination: str):
        self.destination = destination
        self.feasible_distance: int = 999999
        self.successor: Optional[str] = None  # Tuyến chính hiện tại
        self.feasible_successors: List[str] = []  # Các tuyến dự phòng sẵn sàng thay thế ngay
        self.all_neighbors: Dict[str, NeighborRouteInfo] = {}

    def update_topology(self, fd: int, successor: Optional[str], neighbors_info: Dict[str, NeighborRouteInfo]):
        self.feasible_distance = fd
        self.successor = successor
        self.all_neighbors = neighbors_info
        self.feasible_successors = [
            n_id for n_id, info in neighbors_info.items()
            if n_id != successor and info.is_feasible_successor(fd)
        ]


class DUALRouter:
    """
    Bộ định tuyến DUAL Engine:
    - Xây dựng Topology Table đầy đủ.
    - Tìm Successor & Feasible Successor cho từng đích đến.
    - Cho phép chuyển đổi tức thì khi link chính đứt (Instant Failover).
    """

    @classmethod
    def build_topology_table(cls, graph: NetworkGraph, source_node: str) -> Dict[str, DUALDestinationEntry]:
        active_nodes = graph.get_active_nodes()
        if source_node not in active_nodes:
            return {}

        # 1. Chạy Bellman-Ford để lấy Reported Distance của các láng giềng
        neighbors = graph.get_neighbors(source_node)
        destinations = [n for n in active_nodes if n != source_node]

        # neighbor_id -> (RoutingTable from that neighbor)
        neighbor_tables = {}
        for n_id, cost, lat in neighbors:
            neighbor_tables[n_id] = BellmanFordRouter.calculate(graph, n_id)

        # 2. Xây dựng Topology Table cho từng Destination
        dual_table: Dict[str, DUALDestinationEntry] = {}

        for dest in destinations:
            entry = DUALDestinationEntry(dest)
            neighbors_info: Dict[str, NeighborRouteInfo] = {}

            best_neighbor = None
            min_cd = 999999

            for n_id, link_cost, lat in neighbors:
                nt = neighbor_tables.get(n_id)
                if not nt:
                    continue
                route = nt.get_route(dest)
                rd = route.cost if (route and route.cost < 999999) else 999999

                n_info = NeighborRouteInfo(n_id, link_cost, rd)
                neighbors_info[n_id] = n_info

                if n_info.computed_distance < min_cd:
                    min_cd = n_info.computed_distance
                    best_neighbor = n_id

            if best_neighbor is not None and min_cd < 999999:
                entry.update_topology(
                    fd=min_cd,
                    successor=best_neighbor,
                    neighbors_info=neighbors_info
                )
            dual_table[dest] = entry

        return dual_table

    @classmethod
    def instant_failover(
        cls,
        dual_entry: DUALDestinationEntry,
        failed_successor: str
    ) -> Tuple[Optional[str], str]:
        """
        Thực hiện chuyển mạch DUAL tức thì khi Successor hiện tại chết:
        - Nếu có Feasible Successor (FS) -> Chuyển sang FS ngay (0ms).
        - Nếu không có FS -> Báo hiệu cần chuyển sang trạng thái Active (Re-compute).
        """
        if failed_successor != dual_entry.successor:
            return dual_entry.successor, "NO_ACTION_NEEDED"

        if dual_entry.feasible_successors:
            # Chọn FS có Computed Distance nhỏ nhất
            best_fs = min(
                dual_entry.feasible_successors,
                key=lambda fs: dual_entry.all_neighbors[fs].computed_distance
            )
            old_succ = dual_entry.successor
            dual_entry.successor = best_fs
            dual_entry.feasible_distance = dual_entry.all_neighbors[best_fs].computed_distance
            dual_entry.feasible_successors.remove(best_fs)
            return best_fs, f"INSTANT_FAILOVER_TO_FS ({old_succ} -> {best_fs})"
        else:
            return None, "NO_FEASIBLE_SUCCESSOR (Need full Bellman-Ford recompute / Diffusing Query)"
