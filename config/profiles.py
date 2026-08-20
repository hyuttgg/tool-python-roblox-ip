from dataclasses import dataclass
from typing import List, Dict

@dataclass
class NetworkProfile:
    id: str
    name: str
    region: str
    dns_primary: str
    dns_secondary: str
    gateway_hint: str
    mtu: int = 1500
    description: str = ""

DEFAULT_PROFILES: Dict[str, NetworkProfile] = {
    "profile-jp-tokyo": NetworkProfile(
        id="profile-jp-tokyo",
        name="Japan (Tokyo) Cloud Node",
        region="JP-Tokyo",
        dns_primary="1.1.1.1",
        dns_secondary="8.8.8.8",
        gateway_hint="jp-tyo.cloud-gw.internal",
        mtu=1500,
        description="Tokyo Cloud Server profile with low-latency NTT/KDDI routing"
    ),
    "profile-hk-central": NetworkProfile(
        id="profile-hk-central",
        name="Hong Kong Cloud Node",
        region="HK-Central",
        dns_primary="1.1.1.1",
        dns_secondary="1.0.0.1",
        gateway_hint="hk-central.cloud-gw.internal",
        mtu=1500,
        description="Hong Kong Cloud Server profile with direct HKIX route"
    ),
    "profile-sg-jurong": NetworkProfile(
        id="profile-sg-jurong",
        name="Singapore Cloud Node",
        region="SG-Jurong",
        dns_primary="8.8.8.8",
        dns_secondary="8.8.4.4",
        gateway_hint="sg-jurong.cloud-gw.internal",
        mtu=1500,
        description="Singapore Cloud Server profile for Southeast Asia routing"
    ),
    "profile-vn-local": NetworkProfile(
        id="profile-vn-local",
        name="Vietnam Local Gateway",
        region="VN-Local",
        dns_primary="1.1.1.1",
        dns_secondary="8.8.8.8",
        gateway_hint="192.168.0.1",
        mtu=1500,
        description="Direct local Wi-Fi / LTE gateway"
    ),
}
