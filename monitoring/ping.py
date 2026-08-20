import subprocess
import time
import socket
from typing import Tuple
from config.logging import setup_logger

logger = setup_logger("ping_monitor")

class PingMonitor:
    @staticmethod
    def ping_host(host: str = "1.1.1.1", count: int = 2, timeout_sec: float = 2.0) -> Tuple[float, float]:
        """
        Trả về (latency_ms, packet_loss_pct)
        Hỗ trợ cả fallback bằng TCP socket nếu ICMP bị chặn/không có root.
        """
        # Phương pháp 1: Subprocess Ping (ICMP Linux/Android)
        try:
            cmd = ["ping", "-c", str(count), "-W", str(int(timeout_sec)), host]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_sec * count + 1)
            if proc.returncode == 0:
                output = proc.stdout
                loss = 0.0
                if "% packet loss" in output:
                    loss_part = output.split("% packet loss")[0].split()[-1]
                    loss = float(loss_part)
                # Parse rtt avg
                if "rtt min/avg/max" in output or "round-trip min/avg/max" in output:
                    avg_line = [line for line in output.splitlines() if "min/avg" in line][0]
                    avg_val = float(avg_line.split("/")[4])
                    return round(avg_val, 2), loss
        except Exception:
            pass

        # Phương pháp 2: TCP Socket Ping Fallback
        latencies = []
        lost = 0
        for _ in range(count):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout_sec)
            start = time.perf_counter()
            try:
                # Cố gắng kết nối tới port 80/443/53
                target_port = 53 if host in ["1.1.1.1", "8.8.8.8", "9.9.9.9"] else 80
                s.connect((host, target_port))
                latencies.append((time.perf_counter() - start) * 1000.0)
            except Exception:
                lost += 1
            finally:
                s.close()
            time.sleep(0.1)

        packet_loss = (lost / count) * 100.0
        avg_latency = sum(latencies) / len(latencies) if latencies else -1.0
        return round(avg_latency, 2), packet_loss
