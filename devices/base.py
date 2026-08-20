from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from database.models import InstanceModel, NetworkSnapshotModel
from network.connectivity import ConnectivityChecker
from network.interface import InterfaceManager
from network.dns import DNSResolver
from monitoring.ping import PingMonitor
from monitoring.status import HealthEvaluator, HealthState
from config.logging import setup_logger

logger = setup_logger("device_base")

class BaseDeviceDriver(ABC):
    def __init__(self, instance_config: InstanceModel):
        self.config = instance_config
        self.logger = setup_logger(f"device.{instance_config.id}")

    def inspect_network(self) -> NetworkSnapshotModel:
        local_ip = InterfaceManager.get_local_ip(self.config.interface)
        public_ip = ConnectivityChecker.get_public_ip()
        
        # Ping target
        latency, packet_loss = PingMonitor.ping_host("1.1.1.1", count=2)
        _, dns_time = DNSResolver.resolve_domain("www.roblox.com")
        
        state = HealthEvaluator.evaluate(latency, packet_loss)
        
        return NetworkSnapshotModel(
            id=None,
            instance_id=self.config.id,
            region=self.config.region,
            public_ip=public_ip or "N/A",
            local_ip=local_ip,
            interface=self.config.interface,
            latency_ms=latency,
            packet_loss_pct=packet_loss,
            dns_response_ms=dns_time,
            status=state.value
        )
