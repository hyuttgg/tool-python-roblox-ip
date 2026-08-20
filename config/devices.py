from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict

class DeviceType(str, Enum):
    UGPHONE = "ugphone"
    VMOS = "vmos"
    REDFINGER = "redfinger"
    VSPHONE = "vsphone"
    LOCAL_ANDROID = "local_android"

@dataclass
class DeviceConfig:
    id: str
    name: str
    device_type: DeviceType
    region: str
    interface: str = "wlan0"
    assigned_profile: Optional[str] = None
    enabled: bool = True
    metadata: Optional[Dict[str, str]] = None

DEFAULT_DEVICES = [
    DeviceConfig(
        id="UGP-JP-01",
        name="UGPhone-Japan-01",
        device_type=DeviceType.UGPHONE,
        region="JP (Tokyo)",
        interface="wlan0",
        assigned_profile="profile-jp-tokyo"
    ),
    DeviceConfig(
        id="UGP-HK-01",
        name="UGPhone-HK-01",
        device_type=DeviceType.UGPHONE,
        region="HK (Central)",
        interface="wlan0",
        assigned_profile="profile-hk-central"
    ),
    DeviceConfig(
        id="UGP-SG-01",
        name="UGPhone-SG-01",
        device_type=DeviceType.UGPHONE,
        region="SG (Jurong)",
        interface="wlan0",
        assigned_profile="profile-sg-jurong"
    ),
    DeviceConfig(
        id="RED-SG-01",
        name="Redfinger-SG-01",
        device_type=DeviceType.REDFINGER,
        region="SG (Cloud)",
        interface="rmnet0",
        assigned_profile="profile-sg-jurong"
    ),
    DeviceConfig(
        id="VMOS-VN-01",
        name="VMOS-Local-01",
        device_type=DeviceType.VMOS,
        region="VN (Direct)",
        interface="wlan0",
        assigned_profile="profile-vn-local"
    ),
]
