# -*- coding: utf-8 -*-
"""
Dynamic Routing Async TCP Proxy Server
Tự động tra cứu Route Table / Cache để forward traffic sang Next-Hop tối ưu.
"""

import asyncio
import logging
import uuid
from typing import Dict, Optional
from network_lab.proxy.session import ProxySession
from network_lab.routing.graph import NetworkGraph
from network_lab.routing.bellman_ford import BellmanFordRouter
from network_lab.routing.route_cache import RouteCache

logger = logging.getLogger("tcp_proxy")


class DynamicTcpProxyServer:
    def __init__(
        self,
        graph: NetworkGraph,
        route_cache: RouteCache,
        listen_host: str = "127.0.0.1",
        listen_port: int = 8080,
        source_router_id: str = "Router",
        default_target_node: str = "Node_B"
    ):
        self.graph = graph
        self.route_cache = route_cache
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.source_router_id = source_router_id
        self.default_target_node = default_target_node

        self.server: Optional[asyncio.Server] = None
        self.is_running = False
        self.active_sessions: Dict[str, ProxySession] = {}
        self.total_connections = 0

    def resolve_next_hop(self, destination: str) -> Optional[str]:
        """Tra cứu Next-Hop từ Route Cache hoặc tính bằng Bellman-Ford"""
        cached = self.route_cache.get(destination)
        if cached and cached.next_hop:
            return cached.next_hop

        # Miss cache -> Tính toán lại từ Bellman-Ford
        rt = BellmanFordRouter.calculate(self.graph, self.source_router_id)
        route_entry = rt.get_route(destination)
        if route_entry and route_entry.next_hop:
            self.route_cache.put(destination, route_entry)
            return route_entry.next_hop

        return None

    async def _pipe(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, session: ProxySession, is_upstream: bool):
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
                if is_upstream:
                    session.bytes_received += len(data)
                else:
                    session.bytes_sent += len(data)
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _handle_connection(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        self.total_connections += 1
        client_info = client_writer.get_extra_info("peername")
        client_ip, client_port = client_info[0], client_info[1]
        session_id = str(uuid.uuid4())[:8]

        # 1. Tìm Next-Hop tối ưu cho đích đến
        target = self.default_target_node
        next_hop_id = self.resolve_next_hop(target)

        if not next_hop_id or next_hop_id not in self.graph.nodes:
            logger.error(f"[PROXY] Cannot route traffic to {target} (No route found!)")
            client_writer.close()
            await client_writer.wait_closed()
            return

        next_hop_node = self.graph.nodes[next_hop_id]
        if not next_hop_node.is_alive:
            logger.error(f"[PROXY] Next-Hop {next_hop_id} is DOWN!")
            client_writer.close()
            await client_writer.wait_closed()
            return

        # 2. Tạo Session và kết nối tới Next-Hop
        session = ProxySession(session_id, client_ip, client_port, next_hop_id)
        self.active_sessions[session_id] = session

        try:
            upstream_reader, upstream_writer = await asyncio.open_connection(
                next_hop_node.host,
                next_hop_node.port
            )

            # 3. Chuyển tiếp 2 chiều (Bidirectional stream piping)
            await asyncio.gather(
                self._pipe(client_reader, upstream_writer, session, is_upstream=False),
                self._pipe(upstream_reader, client_writer, session, is_upstream=True)
            )
        except Exception as e:
            logger.debug(f"[PROXY] Forwarding error: {e}")
        finally:
            session.is_active = False
            self.active_sessions.pop(session_id, None)
            try:
                client_writer.close()
                await client_writer.wait_closed()
            except Exception:
                pass

    async def start(self):
        if self.is_running:
            return
        self.server = await asyncio.start_server(
            self._handle_connection,
            self.listen_host,
            self.listen_port
        )
        self.is_running = True
        logger.info(f"Dynamic TCP Proxy Server started on {self.listen_host}:{self.listen_port}")

    async def stop(self):
        if not self.is_running or not self.server:
            return
        self.server.close()
        await self.server.wait_closed()
        self.is_running = False
        logger.info("Dynamic TCP Proxy Server stopped.")
