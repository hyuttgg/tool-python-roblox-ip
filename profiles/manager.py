from typing import Dict, Optional
from config.profiles import DEFAULT_PROFILES, NetworkProfile

class ProfileManager:
    def __init__(self):
        self._profiles: Dict[str, NetworkProfile] = DEFAULT_PROFILES.copy()

    def get_profile(self, profile_id: str) -> Optional[NetworkProfile]:
        return self._profiles.get(profile_id)

    def validate_profile(self, profile: NetworkProfile) -> bool:
        if not profile.dns_primary or not profile.dns_secondary:
            return False
        if profile.mtu < 576 or profile.mtu > 1500:
            return False
        return True

    def list_profiles(self) -> Dict[str, NetworkProfile]:
        return self._profiles
