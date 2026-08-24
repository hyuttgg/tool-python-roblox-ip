# -*- coding: utf-8 -*-
"""
Roblox Game Selector & Per-Tag Auto-Join Hub
Quản lý danh bạ các tựa game Roblox hàng đầu (Place ID):
  1. Chế độ Global: Chọn 1 game chung cho tất cả các Tag.
  2. Chế độ Per-Tag Multi-Game: Gán mỗi Tag một Game hoàn toàn khác nhau để join độc lập!
  3. Đồng bộ với Bridge Server & Lua Engine để mỗi acc tự động Teleport vào đúng game riêng.
"""

import os
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from config.logging import setup_logger

logger = setup_logger("game_selector")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
GAME_CONFIG_FILE = os.path.join(DATA_DIR, "target_game_config.json")


@dataclass
class RobloxGameItem:
    id: str
    name: str
    place_id: str
    category: str
    description: str
    default_script_url: str = ""


# Danh bạ các tựa game Roblox phổ biến nhất
POPULAR_ROBLOX_GAMES: List[RobloxGameItem] = [
    RobloxGameItem("1", "Blox Fruits", "2753915549", "Anime / RPG", "Tựa game Anime RPG One Piece phổ biến nhất Roblox."),
    RobloxGameItem("2", "King Legacy", "4520749081", "Anime / RPG", "Game phiêu lưu One Piece đồ họa đẹp mắt."),
    RobloxGameItem("3", "Pet Simulator 99", "8737877873", "Simulator / Farm", "Game nuôi thú cưng cày cuốc & giao dịch lớn nhất."),
    RobloxGameItem("4", "Blade Ball", "13772394625", "Minigame / PvP", "Game né bóng kiếm phản xạ cực nhanh."),
    RobloxGameItem("5", "Fisch (Fishing Simulator)", "16732694052", "Simulator / Adventure", "Game câu cá thám hiểm đại dương hot nhất hiện nay."),
    RobloxGameItem("6", "Murder Mystery 2 (MM2)", "142823291", "Horror / Survival", "Game thám tử, sát thủ và cảnh sát kinh điển."),
    RobloxGameItem("7", "Adopt Me!", "920587237", "Roleplay / Social", "Game nuôi thú và gia đình tương tác xã hội số 1."),
    RobloxGameItem("8", "Rivals (FPS Shooter)", "17625359962", "FPS / Action", "Game bắn súng góc nhìn thứ nhất đối kháng kịch tính."),
    RobloxGameItem("9", "Anime Defenders", "17017769292", "Tower Defense", "Game thủ thành Anime Tower Defense đỉnh cao."),
    RobloxGameItem("10", "Deepwoken", "4111023553", "Hardcore RPG", "Game nhập vai sinh tồn Hardcore thế giới mở."),
    RobloxGameItem("11", "BedWars", "6872265039", "PvP / Strategy", "Game chiến thuật phá giường nhiều người chơi."),
    RobloxGameItem("12", "Doors", "6516141723", "Horror / Escape", "Game sinh tồn kinh dị vượt qua 100 cánh cửa."),
    RobloxGameItem("13", "Brookhaven 🏡RP", "4924922222", "Roleplay / Town", "Game nhập vai cuộc sống thành phố tự do."),
    RobloxGameItem("14", "The Strongest Battlegrounds", "10449761463", "Anime / Fighting", "Game đối kháng võ thuật Saitama / Garou."),
    RobloxGameItem("15", "Da Hood", "2788229376", "Action / PvP", "Game đường phố thế giới ngầm kinh điển.")
]


class GameSelectorManager:
    """Quản lý cấu hình game Roblox mục tiêu theo chế độ Global hoặc Per-Tag Multi-Game"""

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.current_game: Dict = {
            "name": "Blox Fruits",
            "place_id": "2753915549",
            "job_id": "",
            "private_server_link": "",
            "auto_teleport_enabled": True
        }
        self.tag_games_map: Dict[str, Dict] = {}
        self.per_tag_mode: bool = False
        self._load_config()

    def _load_config(self):
        if os.path.exists(GAME_CONFIG_FILE):
            try:
                with open(GAME_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "global_game" in data:
                        self.current_game.update(data["global_game"])
                        self.tag_games_map = data.get("tag_games", {})
                        self.per_tag_mode = data.get("per_tag_mode", False)
                    else:
                        self.current_game.update(data)
            except Exception as e:
                logger.warning(f"Error loading game config: {e}")

    def save_config(self):
        try:
            full_data = {
                "global_game": self.current_game,
                "tag_games": self.tag_games_map,
                "per_tag_mode": self.per_tag_mode
            }
            with open(GAME_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(full_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving game config: {e}")

    def get_current_game(self) -> Dict:
        return self.current_game

    def get_game_for_tag(self, tag_id: Optional[str] = None) -> Dict:
        """Lấy cấu hình game cho một Tag cụ thể. Nếu không có hoặc đang tắt per_tag_mode, trả về global_game"""
        if tag_id and self.per_tag_mode and tag_id in self.tag_games_map:
            return self.tag_games_map[tag_id]
        return self.current_game

    def set_game_by_item(self, item: RobloxGameItem, job_id: str = "", private_server_link: str = ""):
        self.per_tag_mode = False
        self.current_game = {
            "name": item.name,
            "place_id": item.place_id,
            "job_id": job_id.strip(),
            "private_server_link": private_server_link.strip(),
            "auto_teleport_enabled": True
        }
        for tid in list(self.tag_games_map.keys()):
            self.tag_games_map[tid] = dict(self.current_game)
        self.save_config()
        logger.info(f"Global target game set to: {item.name} (PlaceId: {item.place_id})")

    def set_custom_game(self, name: str, place_id: str, job_id: str = "", private_server_link: str = ""):
        clean_pid = "".join(filter(str.isdigit, str(place_id)))
        self.per_tag_mode = False
        self.current_game = {
            "name": name.strip() or f"Place_{clean_pid}",
            "place_id": clean_pid or "2753915549",
            "job_id": job_id.strip(),
            "private_server_link": private_server_link.strip(),
            "auto_teleport_enabled": True
        }
        for tid in list(self.tag_games_map.keys()):
            self.tag_games_map[tid] = dict(self.current_game)
        self.save_config()
        logger.info(f"Global custom game set to: {self.current_game['name']} (PlaceId: {self.current_game['place_id']})")

    def set_game_for_tag(self, tag_id: str, name: str, place_id: str, job_id: str = "", private_server_link: str = ""):
        """Gán một Game riêng biệt cho Tag chỉ định"""
        clean_pid = "".join(filter(str.isdigit, str(place_id))) or "2753915549"
        self.tag_games_map[tag_id] = {
            "name": name.strip() or f"Place_{clean_pid}",
            "place_id": clean_pid,
            "job_id": job_id.strip(),
            "private_server_link": private_server_link.strip(),
            "auto_teleport_enabled": True
        }
        self.per_tag_mode = True
        self.save_config()
        logger.info(f"Tag [{tag_id}] assigned specific game: {name} (PlaceId: {clean_pid})")

    def auto_distribute_multi_games(self, tag_ids: List[str]):
        """Tự động phân bổ mỗi Tag 1 Game khác nhau từ danh sách Top Games"""
        self.tag_games_map = {}
        for idx, tid in enumerate(tag_ids):
            g_item = POPULAR_ROBLOX_GAMES[idx % len(POPULAR_ROBLOX_GAMES)]
            self.tag_games_map[tid] = {
                "name": g_item.name,
                "place_id": g_item.place_id,
                "job_id": "",
                "private_server_link": "",
                "auto_teleport_enabled": True
            }
        self.per_tag_mode = True
        self.save_config()
        logger.info(f"Auto-distributed {len(tag_ids)} unique games across tags.")

    def get_all_tag_games(self) -> Dict[str, Dict]:
        return self.tag_games_map

    def get_launch_uri_for_tag(self, tag_id: Optional[str] = None) -> str:
        """Sinh URI khởi chạy Windows roblox:// cho Tag cụ thể"""
        target_g = self.get_game_for_tag(tag_id)
        pid = target_g.get("place_id", "2753915549")
        jid = target_g.get("job_id", "")
        if jid:
            return f"roblox://experiences/start?placeId={pid}&gameInstanceId={jid}"
        return f"roblox://experiences/start?placeId={pid}"

    def get_launch_uri(self) -> str:
        return self.get_launch_uri_for_tag(None)


# Singleton instance
game_manager = GameSelectorManager()
