import os
import time
from random import randint
from typing import List
from cli.colors import Colors
from config.logging import setup_logger

logger = setup_logger("ip_generator")

class RandomIPGenerator:
    """
    Module sinh chuỗi IP IPv4 ngẫu nhiên (Public / Local format)
    tích hợp từ thuật toán IP-Generator để kiểm thử và phân bổ tag.
    """
    @staticmethod
    def generate_single_ip() -> str:
        a = randint(1, 254)
        b = randint(1, 254)
        c = randint(1, 254)
        d = randint(1, 254)
        return f"{a}.{b}.{c}.{d}"

    @staticmethod
    def generate_batch(count: int = 10, output_file: str = "data/Generated_IPs.txt") -> List[str]:
        ips = []
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "a", encoding="utf-8") as f:
            for _ in range(count):
                ip = RandomIPGenerator.generate_single_ip()
                ips.append(ip)
                f.write(ip + "\n")
        logger.info(f"Generated {count} random IPs to {output_file}")
        return ips
