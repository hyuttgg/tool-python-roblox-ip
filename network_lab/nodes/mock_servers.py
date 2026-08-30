# -*- coding: utf-8 -*-
"""
Mock Destination Server Nodes for Network Lab
Mô phỏng 3 server Node A (:9001), Node B (:9002), Node C (:9003)
"""

import asyncio
import logging
from typing import Dict, Optional

logger = logging.getLogger("mock_nodes")


class MockNodeServer:
    def __init__(self, node_id: str, host: str = "127.0.0.1", port: int = 9001):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.server: Optional[asyncio.Server] = None
        self.is_running = False
        self.request_count = 0

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        client_addr = writer.get_extra_info("peername")
        self.request_count += 1
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break

                text = data.decode("utf-8", errors="ignore").strip()
                response = f"[{self.node_id} @ {self.host}:{self.port}] Echo -> {text}\n"
                writer.write(response.encode("utf-8"))
                await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self):
        if self.is_running:
            return
        self.server = await asyncio.start_server(self._handle_client, self.host, self.port)
        self.is_running = True
        logger.info(f"Mock Server [{self.node_id}] started on {self.host}:{self.port}")

    async def stop(self):
        if not self.is_running or not self.server:
            return
        self.server.close()
        await self.server.wait_closed()
        self.is_running = False
        logger.info(f"Mock Server [{self.node_id}] stopped.")


class MockClusterManager:
    """Quản lý cụm 3 server Node A, Node B, Node C"""
    def __init__(self):
        self.nodes: Dict[str, MockNodeServer] = {
            "Node_A": MockNodeServer("Node_A", "127.0.0.1", 9001),
            "Node_B": MockNodeServer("Node_B", "127.0.0.1", 9002),
            "Node_C": MockNodeServer("Node_C", "127.0.0.1", 9003)
        }

    async def start_all(self):
        for node in self.nodes.values():
            await node.start()

    async def stop_all(self):
        for node in self.nodes.values():
            await node.stop()

    async def stop_node(self, node_id: str):
        if node_id in self.nodes:
            await self.nodes[node_id].stop()

    async def start_node(self, node_id: str):
        if node_id in self.nodes:
            await self.nodes[node_id].start()
