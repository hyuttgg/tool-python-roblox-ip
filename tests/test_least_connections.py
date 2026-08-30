# -*- coding: utf-8 -*-
"""
Unit tests for Least Connections Load Balancer (Python)
"""

import threading
import unittest
from network.least_connections_balancer import LeastConnectionsBalancer, ProxyNode


class TestLeastConnectionsBalancer(unittest.TestCase):

    def setUp(self):
        self.balancer = LeastConnectionsBalancer(default_max_per_proxy=3)
        self.balancer.add_proxy("Proxy_A", "1.1.1.1", 1080, latency_ms=50, max_connections=3)
        self.balancer.add_proxy("Proxy_B", "2.2.2.2", 1080, latency_ms=20, max_connections=3)
        self.balancer.add_proxy("Proxy_C", "3.3.3.3", 1080, latency_ms=80, max_connections=3)

    def test_basic_allocation_and_tie_breaking(self):
        # 1. Khi tất cả proxy đang có 0 kết nối, acc đầu tiên phải vào Proxy_B (vì latency_ms=20 thấp nhất)
        p1 = self.balancer.allocate_proxy_for_account("acc1")
        self.assertIsNotNone(p1)
        self.assertEqual(p1.proxy_id, "Proxy_B")
        self.assertEqual(p1.active_connections, 1)

        # 2. Acc thứ 2 phải vào Proxy_A (latency=50 < Proxy_C=80, và cả 2 đều có 0 kết nối < Proxy_B có 1 kết nối)
        p2 = self.balancer.allocate_proxy_for_account("acc2")
        self.assertIsNotNone(p2)
        self.assertEqual(p2.proxy_id, "Proxy_A")
        self.assertEqual(p2.active_connections, 1)

        # 3. Acc thứ 3 phải vào Proxy_C (0 kết nối)
        p3 = self.balancer.allocate_proxy_for_account("acc3")
        self.assertIsNotNone(p3)
        self.assertEqual(p3.proxy_id, "Proxy_C")
        self.assertEqual(p3.active_connections, 1)

        # 4. Khi cả A, B, C đều có 1 kết nối, acc thứ 4 phải quay lại Proxy_B (vì ping 20 thấp nhất)
        p4 = self.balancer.allocate_proxy_for_account("acc4")
        self.assertEqual(p4.proxy_id, "Proxy_B")
        self.assertEqual(p4.active_connections, 2)

    def test_sticky_session(self):
        # Đã gán acc1 -> lấy lại phải ra cùng proxy đó
        p1 = self.balancer.allocate_proxy_for_account("acc_sticky")
        p2 = self.balancer.allocate_proxy_for_account("acc_sticky")
        self.assertEqual(p1.proxy_id, p2.proxy_id)
        self.assertEqual(p1.active_connections, 1)

    def test_release_and_reallocation(self):
        p1 = self.balancer.allocate_proxy_for_account("acc1")
        p2 = self.balancer.allocate_proxy_for_account("acc2")
        p3 = self.balancer.allocate_proxy_for_account("acc3")
        
        # Release acc1 (Proxy_B)
        self.assertTrue(self.balancer.release_proxy_for_account("acc1"))
        
        # Giờ Proxy_B có 0 active_connections -> acc_new phải vào lại Proxy_B
        p_new = self.balancer.allocate_proxy_for_account("acc_new")
        self.assertEqual(p_new.proxy_id, "Proxy_B")

    def test_max_connections_limit(self):
        # 3 proxy * max 3 = 9 accs
        for i in range(9):
            p = self.balancer.allocate_proxy_for_account(f"clone_{i}")
            self.assertIsNotNone(p)

        # Acc thứ 10 phải None vì full tải
        p10 = self.balancer.allocate_proxy_for_account("clone_10")
        self.assertIsNone(p10)

    def test_unhealthy_proxy_exclusion(self):
        # Tắt Proxy_B
        self.balancer.set_health_status("Proxy_B", is_healthy=False)
        
        # Acc mới không được vào Proxy_B
        p = self.balancer.allocate_proxy_for_account("acc_healthy_test")
        self.assertNotEqual(p.proxy_id, "Proxy_B")
        self.assertEqual(p.proxy_id, "Proxy_A")

    def test_multithreaded_concurrency(self):
        threads = []
        errors = []

        def worker(acc_id):
            try:
                node = self.balancer.allocate_proxy_for_account(f"thread_acc_{acc_id}")
                if node is None:
                    errors.append(f"acc_{acc_id} got None")
            except Exception as e:
                errors.append(str(e))

        for i in range(9):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        # Mỗi proxy phải có đúng 3 kết nối
        for node in self.balancer._proxies.values():
            self.assertEqual(node.active_connections, 3)


if __name__ == "__main__":
    unittest.main()
