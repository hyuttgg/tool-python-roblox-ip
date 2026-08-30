# -*- coding: utf-8 -*-
"""
Continuous Test Client for Network Lab
Gửi luồng traffic TCP liên tục qua Proxy, đo RTT, Packet Success Rate và Node Failover Transition.
"""

import asyncio
import time
from typing import Dict, List, Optional


class RequestMetric:
    def __init__(self, seq: int, success: bool, rtt_ms: float, responder_node: Optional[str], error: Optional[str] = None):
        self.seq = seq
        self.success = success
        self.rtt_ms = rtt_ms
        self.responder_node = responder_node
        self.error = error
        self.timestamp = time.time()


class NetworkLabTestClient:
    def __init__(self, proxy_host: str = "127.0.0.1", proxy_port: int = 8080):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.metrics: List[RequestMetric] = []
        self.is_running = False

    async def send_single_request(self, seq: int, message: str = "PING") -> RequestMetric:
        start = time.perf_counter()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.proxy_host, self.proxy_port),
                timeout=2.0
            )

            payload = f"{message} #{seq}\n".encode("utf-8")
            writer.write(payload)
            await writer.drain()

            response_data = await asyncio.wait_for(reader.readline(), timeout=2.0)
            rtt_ms = (time.perf_counter() - start) * 1000.0

            writer.close()
            await writer.wait_closed()

            text = response_data.decode("utf-8", errors="ignore").strip()
            # Trích xuất node trả lời từ header echo "[Node_B @ 127.0.0.1:9002]"
            responder = "UNKNOWN"
            if text.startswith("["):
                parts = text.split("]", 1)
                if len(parts) > 1:
                    responder = parts[0][1:].split("@")[0].strip()

            metric = RequestMetric(seq, True, rtt_ms, responder)
            self.metrics.append(metric)
            return metric
        except Exception as e:
            rtt_ms = (time.perf_counter() - start) * 1000.0
            metric = RequestMetric(seq, False, rtt_ms, None, str(e))
            self.metrics.append(metric)
            return metric

    async def run_traffic_loop(self, count: int = 20, interval_seconds: float = 0.5):
        self.is_running = True
        for i in range(1, count + 1):
            if not self.is_running:
                break
            metric = await self.send_single_request(i)
            status_icon = "[OK]" if metric.success else "[FAIL]"
            if metric.success:
                print(f"  {status_icon} [Packet #{metric.seq:02d}] Handled by: {metric.responder_node:<10} | RTT: {metric.rtt_ms:>5.1f} ms")
            else:
                print(f"  {status_icon} [Packet #{metric.seq:02d}] FAILED ({metric.error}) | RTT: {metric.rtt_ms:>5.1f} ms")
            await asyncio.sleep(interval_seconds)

    def get_summary(self) -> Dict:
        if not self.metrics:
            return {"total": 0, "success": 0, "failed": 0, "avg_rtt": 0.0}

        successes = [m for m in self.metrics if m.success]
        avg_rtt = sum(m.rtt_ms for m in successes) / len(successes) if successes else 0.0

        node_distribution = {}
        for m in successes:
            node_distribution[m.responder_node] = node_distribution.get(m.responder_node, 0) + 1

        return {
            "total_packets": len(self.metrics),
            "success_packets": len(successes),
            "failed_packets": len(self.metrics) - len(successes),
            "success_rate": f"{(len(successes) / len(self.metrics) * 100.0):.1f}%",
            "avg_rtt_ms": f"{avg_rtt:.2f} ms",
            "node_distribution": node_distribution
        }
