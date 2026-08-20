import ipaddress
from typing import List, Dict, Optional
from database.models import InstanceModel
from network.ip_generator import RandomIPGenerator
from config.logging import setup_logger

logger = setup_logger("ip_allocator")

class IPAllocator:
    """
    Quản lý cấp phát dải IP riêng biệt (Dedicated/Virtual IP) cho từng Instance Tag.
    Hỗ trợ cả chế độ Subnet cục bộ và Random Tag IP Generator.
    """
    def __init__(self, base_subnet: str = "192.168.10.0/24", use_random_pool: bool = False):
        self.network = ipaddress.ip_network(base_subnet)
        self.available_hosts = list(self.network.hosts())[1:]
        self.use_random_pool = use_random_pool
        self._assignments: Dict[str, str] = {}

    def allocate_ips_for_instances(self, instances: List[InstanceModel]) -> Dict[str, str]:
        """
        Gán mỗi instance tag một địa chỉ IP duy nhất, không trùng lặp.
        """
        for idx, inst in enumerate(instances):
            if self.use_random_pool:
                # Dùng module IP-Generator để sinh IP ngẫu nhiên riêng cho tag
                self._assignments[inst.id] = RandomIPGenerator.generate_single_ip()
            else:
                if idx < len(self.available_hosts):
                    self._assignments[inst.id] = str(self.available_hosts[idx])
                else:
                    self._assignments[inst.id] = f"192.168.20.{idx + 2}"
        return self._assignments

    def get_instance_ip(self, instance_id: str, default_ip: Optional[str] = None) -> str:
        return self._assignments.get(instance_id, default_ip or "192.168.10.2")
