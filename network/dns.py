import socket
import time
import concurrent.futures
from typing import Tuple, Optional, Dict
from config.logging import setup_logger

logger = setup_logger("dns_resolver")

PUBLIC_DNS_SERVERS = {
    "Google DNS (8.8.8.8)": "8.8.8.8",
    "Cloudflare (1.1.1.1)": "1.1.1.1",
    "Quad9 (9.9.9.9)": "9.9.9.9",
    "OpenDNS (208.67.222.222)": "208.67.222.222",
    "AdGuard (94.140.14.14)": "94.140.14.14",
    "CleanBrowsing (185.228.168.9)": "185.228.168.9"
}

class DNSResolver:
    @staticmethod
    def _build_dns_query(domain: str) -> bytes:
        """Tạo gói tin DNS Query UDP chuẩn theo RFC 1035"""
        domain_clean = domain.strip().strip(".")
        header = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
        qname = b"".join(bytes([len(p)]) + p.encode("ascii") for p in domain_clean.split(".") if p) + b"\x00"
        footer = b"\x00\x01\x00\x01"  # Type A (1), Class IN (1)
        return header + qname + footer

    @staticmethod
    def _parse_dns_response_ip(data: bytes) -> Optional[str]:
        """Trích xuất địa chỉ IPv4 từ gói phản hồi DNS UDP"""
        try:
            if len(data) < 12:
                return None
            ancount = int.from_bytes(data[6:8], byteorder="big")
            if ancount == 0:
                return None
            offset = 12
            # Bỏ qua phần Question
            while offset < len(data) and data[offset] != 0:
                if (data[offset] & 0xC0) == 0xC0:
                    offset += 2
                    break
                offset += 1 + data[offset]
            if offset < len(data) and data[offset] == 0:
                offset += 5  # Null byte (1) + QTYPE (2) + QCLASS (2)

            # Duyệt phần Answer
            for _ in range(ancount):
                if offset >= len(data):
                    break
                if (data[offset] & 0xC0) == 0xC0:
                    offset += 2
                else:
                    while offset < len(data) and data[offset] != 0:
                        offset += 1 + data[offset]
                    offset += 1
                if offset + 10 > len(data):
                    break
                rtype = int.from_bytes(data[offset:offset + 2], byteorder="big")
                rdlength = int.from_bytes(data[offset + 8:offset + 10], byteorder="big")
                offset += 10
                if rtype == 1 and rdlength == 4 and offset + 4 <= len(data):
                    return socket.inet_ntoa(data[offset:offset + 4])
                offset += rdlength
            return None
        except Exception:
            return None

    @classmethod
    def resolve_domain(cls, domain: str = "www.roblox.com", server: Optional[str] = None, timeout: float = 2.0) -> Tuple[Optional[str], float]:
        """Phân giải tên miền thành địa chỉ IP kèm thời gian phản hồi (ms)"""
        start_time = time.perf_counter()
        if server:
            try:
                query = cls._build_dns_query(domain)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(timeout)
                sock.sendto(query, (server, 53))
                data, _ = sock.recvfrom(512)
                sock.close()
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                ip = cls._parse_dns_response_ip(data)
                if ip:
                    return ip, round(elapsed_ms, 2)
            except Exception as e:
                logger.debug(f"Direct DNS query to {server} failed for {domain}: {e}")

        # Fallback dùng socket hệ thống
        try:
            ip = socket.gethostbyname(domain)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ip, round(elapsed_ms, 2)
        except Exception as e:
            logger.debug(f"DNS Resolution failed for {domain}: {e}")
            return None, -1.0

    @classmethod
    def test_dns_server(cls, server_ip: str, domain: str = "www.roblox.com", timeout: float = 2.0) -> float:
        """Đo độ trễ phân giải DNS (ms) từ một máy chủ DNS cụ thể"""
        start = time.perf_counter()
        try:
            query = cls._build_dns_query(domain)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            sock.sendto(query, (server_ip, 53))
            _, _ = sock.recvfrom(512)
            sock.close()
            return round((time.perf_counter() - start) * 1000.0, 1)
        except Exception:
            # Fallback kết nối TCP Handshake port 53 nếu UDP bị chặn
            try:
                start_tcp = time.perf_counter()
                with socket.create_connection((server_ip, 53), timeout=timeout):
                    return round((time.perf_counter() - start_tcp) * 1000.0, 1)
            except Exception:
                return -1.0

    @classmethod
    def test_all_dns_servers(cls, domain: str = "www.roblox.com", timeout: float = 2.0) -> Dict[str, float]:
        """Đo độ trễ song song toàn bộ các Public DNS Servers phổ biến"""
        results: Dict[str, float] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(PUBLIC_DNS_SERVERS)) as executor:
            futures = {
                executor.submit(cls.test_dns_server, ip, domain, timeout): name
                for name, ip in PUBLIC_DNS_SERVERS.items()
            }
            for future in concurrent.futures.as_completed(futures):
                name = futures[future]
                try:
                    latency = future.result()
                    results[name] = latency
                except Exception:
                    results[name] = -1.0
        return {name: results.get(name, -1.0) for name in PUBLIC_DNS_SERVERS}

