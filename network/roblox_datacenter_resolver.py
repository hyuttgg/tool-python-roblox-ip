# -*- coding: utf-8 -*-
"""
Roblox Offline Datacenter & UDMUX GeoIP Resolver
Dựa trên cơ sở dữ liệu RoValra Datacenters từ DroidBlox-kt.
Tra cứu thông tin vị trí máy chủ Roblox (Singapore, Japan, Sydney, US, EU...)
hoàn toàn OFFLINE với tốc độ mili-giây, không bị rate-limit.
"""

import os
import json
import ipaddress
from typing import Dict, List, Optional, Tuple
from config.logging import setup_logger

logger = setup_logger("datacenter_resolver")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATACENTER_FILE = os.path.join(DATA_DIR, "rovalradatacenters.json")

# Mapping cờ quốc gia
COUNTRY_FLAGS = {
    "SG": "🇸🇬", "JP": "🇯🇵", "US": "🇺🇸", "HK": "🇭🇰", "AU": "🇦🇺",
    "DE": "🇩🇪", "GB": "🇬🇧", "FR": "🇫🇷", "BR": "🇧🇷", "IN": "🇮🇳",
    "KR": "🇰🇷", "NL": "🇳🇱", "IE": "🇮🇪", "CA": "🇨🇦", "PL": "🇵🇱"
}


class RobloxDatacenterResolver:
    """Bộ giải mã và đối soát Datacenter / UDMUX IP Roblox Offline"""

    def __init__(self):
        self.datacenters: List[Dict] = []
        self.dc_id_map: Dict[int, Dict] = {}
        self._load_database()

    def _load_database(self) -> None:
        if os.path.exists(DATACENTER_FILE):
            try:
                with open(DATACENTER_FILE, "r", encoding="utf-8") as f:
                    self.datacenters = json.load(f)
                
                for entry in self.datacenters:
                    loc = entry.get("location", {})
                    dc_ids = entry.get("dataCenterIds", [])
                    for dc_id in dc_ids:
                        self.dc_id_map[dc_id] = {
                            "location_id": entry.get("location_id"),
                            "city": loc.get("city", "Unknown"),
                            "region": loc.get("region", "Unknown"),
                            "country": loc.get("country", "UN"),
                            "country_name": loc.get("country_name", "Unknown"),
                            "flag": COUNTRY_FLAGS.get(loc.get("country", "UN"), "🌐"),
                            "lat_long": loc.get("latLong", ["0", "0"]),
                            "inactive": entry.get("inactive", False),
                            "loadbalancing": entry.get("loadbalancing", False)
                        }
                logger.info(f"Loaded {len(self.dc_id_map)} Datacenter IDs across {len(self.datacenters)} Global Locations.")
            except Exception as e:
                logger.error(f"Failed to load rovalradatacenters.json: {e}")
        else:
            logger.warning(f"Datacenter database not found at: {DATACENTER_FILE}")

    def lookup_by_datacenter_id(self, dc_id: int) -> Optional[Dict]:
        """Tra cứu thông tin theo mã Datacenter ID"""
        return self.dc_id_map.get(dc_id)

    def resolve_udmux_ip(self, ip_str: str) -> Dict:
        """
        Phân giải địa chỉ IP UDMUX của Roblox server sang vị trí địa lý.
        Sử dụng phân tích dải IP chuẩn của Roblox kết hợp cơ sở dữ liệu Datacenter.
        """
        clean_ip = ip_str.strip()
        
        # Dải IP đặc thù của hạ tầng Roblox AS22697
        # 128.116.x.x, 209.206.x.x, 142.250.x.x
        res = {
            "ip": clean_ip,
            "city": "Unknown",
            "country": "US",
            "country_name": "United States",
            "region_code": "AUTO",
            "flag": "🌐",
            "datacenter_id": None,
            "provider": "Roblox UDMUX Edge"
        }

        try:
            ip_obj = ipaddress.ip_address(clean_ip)
            
            # Heuristic dải subnet hạ tầng Roblox
            # Singapore: 128.116.48.0/20, 128.116.50.0/24
            if ip_obj in ipaddress.ip_network("128.116.48.0/20", strict=False) or ip_obj in ipaddress.ip_network("128.116.50.0/24", strict=False):
                res.update({
                    "city": "Singapore",
                    "country": "SG",
                    "country_name": "Singapore",
                    "region_code": "SG",
                    "flag": "🇸🇬"
                })
            # Tokyo Japan: 128.116.112.0/20, 128.116.114.0/24
            elif ip_obj in ipaddress.ip_network("128.116.112.0/20", strict=False) or ip_obj in ipaddress.ip_network("128.116.114.0/24", strict=False):
                res.update({
                    "city": "Tokyo",
                    "country": "JP",
                    "country_name": "Japan",
                    "region_code": "JP",
                    "flag": "🇯🇵"
                })
            # Hong Kong: 128.116.120.0/21
            elif ip_obj in ipaddress.ip_network("128.116.120.0/21", strict=False):
                res.update({
                    "city": "Hong Kong",
                    "country": "HK",
                    "country_name": "Hong Kong",
                    "region_code": "HK",
                    "flag": "🇭🇰"
                })
            # Sydney Australia: 128.116.104.0/21
            elif ip_obj in ipaddress.ip_network("128.116.104.0/21", strict=False):
                res.update({
                    "city": "Sydney",
                    "country": "AU",
                    "country_name": "Australia",
                    "region_code": "AU",
                    "flag": "🇦🇺"
                })
            # Frankfurt Germany: 128.116.80.0/20
            elif ip_obj in ipaddress.ip_network("128.116.80.0/20", strict=False):
                res.update({
                    "city": "Frankfurt",
                    "country": "DE",
                    "country_name": "Germany",
                    "region_code": "DE",
                    "flag": "🇩🇪"
                })
            # London UK: 128.116.64.0/20
            elif ip_obj in ipaddress.ip_network("128.116.64.0/20", strict=False):
                res.update({
                    "city": "London",
                    "country": "GB",
                    "country_name": "United Kingdom",
                    "region_code": "GB",
                    "flag": "🇬🇧"
                })
            # US West / San Mateo / Los Angeles: 128.116.0.0/19
            elif ip_obj in ipaddress.ip_network("128.116.0.0/19", strict=False):
                res.update({
                    "city": "San Mateo, CA",
                    "country": "US",
                    "country_name": "United States (West)",
                    "region_code": "US-WEST",
                    "flag": "🇺🇸"
                })
            # US East / Ashburn / New York: 128.116.32.0/19
            elif ip_obj in ipaddress.ip_network("128.116.32.0/19", strict=False):
                res.update({
                    "city": "Ashburn, VA",
                    "country": "US",
                    "country_name": "United States (East)",
                    "region_code": "US-EAST",
                    "flag": "🇺🇸"
                })
            else:
                res.update({
                    "city": "United States",
                    "country": "US",
                    "country_name": "United States",
                    "region_code": "US",
                    "flag": "🇺🇸"
                })
        except Exception:
            pass

        return res

    def get_supported_locations_summary(self) -> List[Dict]:
        """Tổng hợp danh sách các địa điểm Datacenter khả dụng trên toàn cầu"""
        summary = []
        for entry in self.datacenters:
            loc = entry.get("location", {})
            c_code = loc.get("country", "UN")
            summary.append({
                "city": loc.get("city"),
                "country": c_code,
                "country_name": loc.get("country_name"),
                "flag": COUNTRY_FLAGS.get(c_code, "🌐"),
                "datacenters_count": len(entry.get("dataCenterIds", [])),
                "inactive": entry.get("inactive", False)
            })
        return summary


# Singleton instance
datacenter_resolver = RobloxDatacenterResolver()
