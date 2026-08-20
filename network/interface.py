import socket
import subprocess
import re
from typing import Dict, List, Optional
from config.logging import setup_logger

logger = setup_logger("network_interface")

class InterfaceManager:
    @staticmethod
    def get_local_ip(interface: Optional[str] = None) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    @staticmethod
    def list_interfaces() -> List[Dict[str, str]]:
        interfaces = []
        try:
            output = subprocess.check_output(["ip", "-o", "addr", "show"], text=True, stderr=subprocess.DEVNULL)
            for line in output.splitlines():
                parts = line.split()
                if len(parts) >= 4 and parts[2] == "inet":
                    iface_name = parts[1]
                    ip_addr = parts[3].split("/")[0]
                    interfaces.append({"interface": iface_name, "ip": ip_addr})
        except Exception:
            interfaces.append({"interface": "wlan0", "ip": InterfaceManager.get_local_ip()})
        return interfaces
