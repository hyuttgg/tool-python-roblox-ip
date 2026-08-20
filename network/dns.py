import socket
import time
from typing import Tuple, Optional
from config.logging import setup_logger

logger = setup_logger("dns_resolver")

class DNSResolver:
    @staticmethod
    def resolve_domain(domain: str = "www.roblox.com", server: Optional[str] = None) -> Tuple[Optional[str], float]:
        start_time = time.perf_counter()
        try:
            ip = socket.gethostbyname(domain)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ip, round(elapsed_ms, 2)
        except Exception as e:
            logger.debug(f"DNS Resolution failed for {domain}: {e}")
            return None, -1.0
