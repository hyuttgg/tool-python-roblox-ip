import urllib.request
import json
import socket
from typing import Optional, Dict
from config.logging import setup_logger

logger = setup_logger("connectivity")

class ConnectivityChecker:
    @staticmethod
    def get_public_ip(timeout: float = 3.0) -> Optional[str]:
        services = [
            "https://api.ipify.org?format=json",
            "https://ifconfig.me/all.json",
            "https://ipinfo.io/json"
        ]
        for url in services:
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "MultiInstanceNetworkManager/1.0"}
                )
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode())
                        if "ip" in data:
                            return data["ip"]
                        elif "ip_addr" in data:
                            return data["ip_addr"]
            except Exception as e:
                logger.debug(f"Failed querying {url}: {e}")
                continue
        return None

    @staticmethod
    def check_internet_reachability(host: str = "1.1.1.1", port: int = 53, timeout: float = 2.0) -> bool:
        try:
            sock = socket.create_connection((host, port), timeout=timeout)
            sock.close()
            return True
        except OSError:
            return False
