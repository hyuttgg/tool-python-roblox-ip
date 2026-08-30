# -*- coding: utf-8 -*-
"""
Session & Connection Tracking for Proxy Layer
"""

import time
from typing import Dict, Optional


class ProxySession:
    def __init__(self, session_id: str, client_ip: str, client_port: int, upstream_node: str):
        self.session_id = session_id
        self.client_ip = client_ip
        self.client_port = client_port
        self.upstream_node = upstream_node
        self.bytes_sent = 0
        self.bytes_received = 0
        self.created_at = time.time()
        self.is_active = True

    @property
    def duration_seconds(self) -> float:
        return time.time() - self.created_at

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "client": f"{self.client_ip}:{self.client_port}",
            "upstream_node": self.upstream_node,
            "bytes_tx": self.bytes_sent,
            "bytes_rx": self.bytes_received,
            "duration": f"{self.duration_seconds:.1f}s",
            "active": self.is_active
        }
