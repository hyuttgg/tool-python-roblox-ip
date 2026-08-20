import threading
import time
from typing import Dict
from database.models import InstanceModel
from database.repository import InstanceRepository, SnapshotRepository
from config.devices import DEFAULT_DEVICES
from devices.instances import UGPhoneDriver, VMOSDriver, RedfingerDriver, VSPhoneDriver
from network.allocator import IPAllocator
from config.logging import setup_logger

logger = setup_logger("core_manager")

class CoreManager:
    def __init__(self):
        self.drivers: Dict[str, object] = {}
        # Bật use_random_pool=True để mỗi tag instance nhận một IP riêng biệt ngẫu nhiên từ IP-Generator
        self.ip_allocator = IPAllocator(base_subnet="192.168.10.0/24", use_random_pool=True)
        self.running = False
        self.init_instances()

    def init_instances(self):
        instances = []
        for dev in DEFAULT_DEVICES:
            inst = InstanceModel(
                id=dev.id,
                name=dev.name,
                device_type=dev.device_type.value,
                region=dev.region,
                interface=dev.interface,
                assigned_profile=dev.assigned_profile,
                status="OFFLINE"
            )
            instances.append(inst)
            InstanceRepository.upsert_instance(inst)
            
            if dev.device_type.value == "ugphone":
                self.drivers[dev.id] = UGPhoneDriver(inst)
            elif dev.device_type.value == "vmos":
                self.drivers[dev.id] = VMOSDriver(inst)
            elif dev.device_type.value == "redfinger":
                self.drivers[dev.id] = RedfingerDriver(inst)
            else:
                self.drivers[dev.id] = VSPhoneDriver(inst)

        # Cấp phát IP ngẫu nhiên riêng biệt cho từng tag
        self.ip_allocator.allocate_ips_for_instances(instances)

    def run_check_cycle(self):
        for inst_id, driver in self.drivers.items():
            try:
                snapshot = driver.inspect_network()
                # Gán Dedicated IP riêng biệt của tag
                snapshot.local_ip = self.ip_allocator.get_instance_ip(inst_id, default_ip=snapshot.local_ip)
                SnapshotRepository.save_snapshot(snapshot)
                
                inst = InstanceModel(
                    id=inst_id,
                    name=driver.config.name,
                    device_type=driver.config.device_type,
                    region=driver.config.region,
                    interface=driver.config.interface,
                    assigned_profile=driver.config.assigned_profile,
                    status=snapshot.status
                )
                InstanceRepository.upsert_instance(inst)
            except Exception as e:
                logger.error(f"Error checking {inst_id}: {e}")
