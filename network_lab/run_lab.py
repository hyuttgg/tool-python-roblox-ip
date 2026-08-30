# -*- coding: utf-8 -*-
"""
NetworkLab 1-Click Interactive Runner & Demo
Chạy kịch bản mô phỏng toàn diện:
  1. Khởi chạy 3 Mock Server Nodes (A, B, C)
  2. Dựng Đồ thị Mạng & Dynamic TCP Proxy
  3. Tính toán đường đi tối ưu bằng Bellman-Ford & DUAL
  4. Test Client bắn luồng traffic liên tục
  5. Giả lập sự cố ngắt kết nối (Chaos Failover) và quan sát chuyển mạch tự động
  6. Khôi phục trạng thái mạng và hội tụ lại đường đi ngắn nhất
"""

import asyncio
import logging
import os
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from network_lab.nodes.mock_servers import MockClusterManager
from network_lab.routing.graph import NetworkGraph
from network_lab.routing.bellman_ford import BellmanFordRouter
from network_lab.routing.dual_engine import DUALRouter
from network_lab.routing.route_cache import RouteCache
from network_lab.proxy.tcp_proxy import DynamicTcpProxyServer
from network_lab.health.health_checker import NodeHealthChecker
from network_lab.health.chaos_injector import ChaosInjector
from network_lab.client.test_client import NetworkLabTestClient
from network_lab.dashboard.live_monitor import NetworkLabDashboard

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_lab")


async def run_network_lab_demo():
    print("=" * 80)
    print("        SAFE RESEARCH LAB: PROXY + DYNAMIC ROUTING ENGINE")
    print("=" * 80)

    # 1. Khởi tạo Topology Đồ thị
    graph = NetworkGraph()
    graph.add_node("Router", "127.0.0.1", 8080)
    graph.add_node("Node_A", "127.0.0.1", 9001)
    graph.add_node("Node_B", "127.0.0.1", 9002)
    graph.add_node("Node_C", "127.0.0.1", 9003)

    # Cấu hình các cạnh (Edges):
    # Router -> Node_A (Cost 10, Latency 20ms)
    # Router -> Node_C (Cost 5,  Latency 10ms)
    # Node_C -> Node_B (Cost 2,  Latency 5ms)   ==> Tổng Cost Router -> C -> B = 7 (TỐI ƯU NHẤT)
    # Node_A -> Node_B (Cost 10, Latency 20ms)  ==> Tổng Cost Router -> A -> B = 20 (DỰ PHÒNG)
    graph.add_edge("Router", "Node_A", cost=10, latency_ms=20.0)
    graph.add_edge("Router", "Node_C", cost=5,  latency_ms=10.0)
    graph.add_edge("Node_C", "Node_B", cost=2,  latency_ms=5.0)
    graph.add_edge("Node_A", "Node_B", cost=10, latency_ms=20.0)

    # 2. Khởi tạo cụm Server Mock Nodes
    cluster = MockClusterManager()
    await cluster.start_all()

    # 3. Khởi tạo Route Cache & Dynamic TCP Proxy
    route_cache = RouteCache(default_ttl=30.0)
    proxy_server = DynamicTcpProxyServer(
        graph=graph,
        route_cache=route_cache,
        listen_host="127.0.0.1",
        listen_port=8080,
        source_router_id="Router",
        default_target_node="Node_B"
    )
    await proxy_server.start()

    # 4. Khởi tạo Health Checker & Chaos Injector
    health_checker = NodeHealthChecker(graph, route_cache, check_interval=1.0)
    health_task = asyncio.create_task(health_checker.start())
    chaos = ChaosInjector(cluster, graph, route_cache)

    client = NetworkLabTestClient(proxy_host="127.0.0.1", proxy_port=8080)

    try:
        # -------------------------------------------------------------
        # GIAI ĐOẠN 1: TRẠNG THÁI BÌNH THƯỜNG (NORMAL STATE)
        # -------------------------------------------------------------
        print("\n[BUOC 1] Khoi tao trang thai ban dau va hien thi Dashboard:")
        NetworkLabDashboard.render(graph, route_cache, proxy_server, source_node="Router")

        print("\n[BUOC 2] Test Client gui 5 goi tin qua Proxy toi Node_B (Tuyen toi uu: Router -> Node_C):")
        await client.run_traffic_loop(count=5, interval_seconds=0.3)

        # -------------------------------------------------------------
        # GIAI ĐOẠN 2: GIẢ LẬP SỰ CỐ ĐỨT NODE C (CHAOS INJECTION)
        # -------------------------------------------------------------
        print("\n" + "-" * 80)
        print("[BUOC 3] [!] GIA LAP SU CO: Node_C bi sap (Link Down)!")
        await chaos.kill_node("Node_C")
        await asyncio.sleep(0.5)

        print("\n[BUOC 4] Routing Engine tu dong tinh lai duong di (Failover sang Node_A):")
        NetworkLabDashboard.render(graph, route_cache, proxy_server, source_node="Router")

        print("\n[BUOC 5] Test Client tiep tuc gui 5 goi tin (Kiem chung chuyen mach tu dong):")
        await client.run_traffic_loop(count=5, interval_seconds=0.3)

        # -------------------------------------------------------------
        # GIAI ĐOẠN 3: KHÔI PHỤC NODE C VÀ TỰ ĐỘNG HỘI TỤ
        # -------------------------------------------------------------
        print("\n" + "-" * 80)
        print("[BUOC 6] [*] KHOI PHUC: Node_C hoat dong tro lai (Link Up)!")
        await chaos.revive_node("Node_C")
        await asyncio.sleep(1.2)  # Đợi health checker quét

        print("\n[BUOC 7] Mang tu dong hoi tu lai tuyen duong co Cost nho nhat (Router -> Node_C):")
        NetworkLabDashboard.render(graph, route_cache, proxy_server, source_node="Router")

        print("\n[BUOC 8] Test Client gui 5 goi tin cuoi cung xac nhan hoan tat hoi tu:")
        await client.run_traffic_loop(count=5, interval_seconds=0.3)

        # -------------------------------------------------------------
        # TỔNG KẾT BÁO CÁO LAB
        # -------------------------------------------------------------
        print("\n" + "=" * 80)
        print("                         BAO CAO TONG KET LAB")
        print("=" * 80)
        summary = client.get_summary()
        for k, v in summary.items():
            print(f"  • {k:<20}: {v}")
        print("=" * 80)

    finally:
        # Dọn dẹp tiến trình
        health_checker.stop()
        health_task.cancel()
        await proxy_server.stop()
        await cluster.stop_all()


if __name__ == "__main__":
    asyncio.run(run_network_lab_demo())
