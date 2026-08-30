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
            "preferred_region": "AUTO",
            "server_filter_mode": "LOW_PLAYERS",
            "private_server_link": private_server_link.strip(),
            "auto_teleport_enabled": True
        }
        for tid in list(self.tag_games_map.keys()):
            self.tag_games_map[tid] = dict(self.current_game)
        self.save_config()
        logger.info(f"Global custom game set to: {self.current_game['name']} (PlaceId: {self.current_game['place_id']})")

    def set_game_for_tag(self, tag_id: str, name: str, place_id: str, job_id: str = "", private_server_link: str = "", preferred_region: str = "AUTO"):
        """Gán một Game riêng biệt cho Tag chỉ định kèm Region"""
        clean_pid = "".join(filter(str.isdigit, str(place_id))) or "2753915549"
        self.tag_games_map[tag_id] = {
            "name": name.strip() or f"Place_{clean_pid}",
            "place_id": clean_pid,
            "job_id": job_id.strip(),
            "preferred_region": preferred_region,
            "server_filter_mode": "LOW_PLAYERS",
            "private_server_link": private_server_link.strip(),
            "auto_teleport_enabled": True
        }
        self.per_tag_mode = True
        self.save_config()
        logger.info(f"Tag [{tag_id}] assigned specific game: {name} (PlaceId: {clean_pid}, Region: {preferred_region})")

    def set_region_for_tag(self, tag_id: str, region_code: str, filter_mode: str = "LOW_PLAYERS") -> Optional[Dict]:
        """Cấu hình Region mục tiêu và tự động tìm Server tối ưu cho Tag"""
        from network.roblox_region_finder import region_finder
        target_g = self.get_game_for_tag(tag_id)
        place_id = target_g.get("place_id", "2753915549")

        best_server = region_finder.get_best_server(place_id, target_region=region_code, filter_mode=filter_mode)
        new_job_id = best_server.get("job_id", "") if best_server else ""

        if tag_id not in self.tag_games_map:
            self.tag_games_map[tag_id] = dict(target_g)

        self.tag_games_map[tag_id]["preferred_region"] = region_code
        self.tag_games_map[tag_id]["server_filter_mode"] = filter_mode
        if new_job_id:
            self.tag_games_map[tag_id]["job_id"] = new_job_id

        self.per_tag_mode = True
        self.save_config()
        logger.info(f"Tag [{tag_id}] configured region: {region_code} | JobId: {new_job_id}")
        return best_server

    def set_global_region(self, region_code: str, filter_mode: str = "LOW_PLAYERS") -> Optional[Dict]:
        """Cấu hình Region mục tiêu cho tất cả các Tag"""
        from network.roblox_region_finder import region_finder
        place_id = self.current_game.get("place_id", "2753915549")
        best_server = region_finder.get_best_server(place_id, target_region=region_code, filter_mode=filter_mode)
        new_job_id = best_server.get("job_id", "") if best_server else ""

        self.current_game["preferred_region"] = region_code
        self.current_game["server_filter_mode"] = filter_mode
        if new_job_id:
            self.current_game["job_id"] = new_job_id

        for tid in self.tag_games_map:
            self.tag_games_map[tid]["preferred_region"] = region_code
            self.tag_games_map[tid]["server_filter_mode"] = filter_mode
            if new_job_id:
                self.tag_games_map[tid]["job_id"] = new_job_id

        self.save_config()
        logger.info(f"Global region set to: {region_code} | JobId: {new_job_id}")
        return best_server

    def resolve_server_for_tag(self, tag_id: Optional[str] = None) -> Optional[Dict]:
        """Tự động tìm hoặc làm mới Server JobId theo Region đã cấu hình"""
        from network.roblox_region_finder import region_finder
        target_g = self.get_game_for_tag(tag_id)
        place_id = target_g.get("place_id", "2753915549")
        region_code = target_g.get("preferred_region", "AUTO")
        filter_mode = target_g.get("server_filter_mode", "LOW_PLAYERS")

        best_server = region_finder.get_best_server(place_id, target_region=region_code, filter_mode=filter_mode)
        if best_server and best_server.get("job_id"):
            if tag_id and tag_id in self.tag_games_map:
                self.tag_games_map[tag_id]["job_id"] = best_server["job_id"]
            else:
                self.current_game["job_id"] = best_server["job_id"]
            self.save_config()
        return best_server

    def auto_distribute_multi_games(self, tag_ids: List[str]):
        """Tự động phân bổ mỗi Tag 1 Game khác nhau từ danh sách Top Games"""
        self.tag_games_map = {}
        for idx, tid in enumerate(tag_ids):
            g_item = POPULAR_ROBLOX_GAMES[idx % len(POPULAR_ROBLOX_GAMES)]
            self.tag_games_map[tid] = {
                "name": g_item.name,
                "place_id": g_item.place_id,
                "job_id": "",
                "preferred_region": "SG" if idx % 2 == 0 else "JP",
                "server_filter_mode": "LOW_PLAYERS",
                "private_server_link": "",
                "auto_teleport_enabled": True
            }
        self.per_tag_mode = True
        self.save_config()
        logger.info(f"Auto-distributed {len(tag_ids)} unique games across tags.")

    def get_all_tag_games(self) -> Dict[str, Dict]:
        return self.tag_games_map

    def get_launch_uri_for_tag(self, tag_id: Optional[str] = None) -> str:
        """Sinh URI khởi chạy Windows roblox:// cho Tag cụ thể (Bao gồm JobId nếu có)"""
        target_g = self.get_game_for_tag(tag_id)
        pid = target_g.get("place_id", "2753915549")
        jid = target_g.get("job_id", "")
        if jid:
            return f"roblox://experiences/start?placeId={pid}&gameInstanceId={jid}"
        return f"roblox://experiences/start?placeId={pid}"

    def get_launch_uri(self) -> str:
        return self.get_launch_uri_for_tag(None)


GAME_CACHE_FILE = os.path.join(DATA_DIR, "roblox_game_cache.json")


def fetch_game_name_from_roblox(place_id: str) -> str:
    """
    Tra cứu tên trải nghiệm / Game Roblox chuẩn xác từ Place ID thông qua Roblox Open API.
    Có tích hợp bộ nhớ đệm cache để phản hồi tức thì và không bị rate-limit.
    """
    clean_pid = "".join(filter(str.isdigit, str(place_id)))
    if not clean_pid:
        return "Unknown Place"

    # 1. Kiểm tra danh bạ phổ biến
    for item in POPULAR_ROBLOX_GAMES:
        if item.place_id == clean_pid:
            return item.name

    # 2. Kiểm tra bộ nhớ cache cục bộ
    cache = {}
    if os.path.exists(GAME_CACHE_FILE):
        try:
            with open(GAME_CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
                if clean_pid in cache:
                    return cache[clean_pid]
        except Exception:
            pass

    # 3. Tra cứu qua Roblox Open API
    try:
        headers = {"User-Agent": "Roblox-Auto-Rejoiner-Sentinel/2.0"}
        univ_url = f"https://apis.roblox.com/universes/v1/places/{clean_pid}/universe"
        
        try:
            import requests
            resp = requests.get(univ_url, headers=headers, timeout=5)
            univ_data = resp.json() if resp.status_code == 200 else {}
        except ImportError:
            import urllib.request
            req = urllib.request.Request(univ_url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as u_resp:
                univ_data = json.loads(u_resp.read().decode("utf-8"))

        universe_id = univ_data.get("universeId")
        if universe_id:
            game_url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
            try:
                import requests
                g_resp = requests.get(game_url, headers=headers, timeout=5)
                g_data = g_resp.json() if g_resp.status_code == 200 else {}
            except ImportError:
                import urllib.request
                g_req = urllib.request.Request(game_url, headers=headers)
                with urllib.request.urlopen(g_req, timeout=5) as g_u_resp:
                    g_data = json.loads(g_u_resp.read().decode("utf-8"))

            games_list = g_data.get("data", [])
            if games_list and games_list[0].get("name"):
                game_title = games_list[0]["name"]
                cache[clean_pid] = game_title
                try:
                    os.makedirs(os.path.dirname(GAME_CACHE_FILE), exist_ok=True)
                    with open(GAME_CACHE_FILE, "w", encoding="utf-8") as cf:
                        json.dump(cache, cf, indent=2, ensure_ascii=False)
                except Exception:
                    pass
                logger.info(f"Đã tra cứu thành công tên Game từ Roblox API: {game_title} (Place ID: {clean_pid})")
                return game_title
    except Exception as e:
        logger.debug(f"Không thể tra cứu tên game từ Roblox API: {e}")

    return f"Place {clean_pid}"


def launch_roblox_client(place_id: str, job_id: str = "", tag_id: Optional[str] = None) -> Dict:
    """
    Khởi chạy Roblox Client theo cơ chế Dual-Tier (Windows & Android):
      - Tier 1: Khởi chạy giao thức URL Scheme 'roblox://'
      - Tier 2 (Windows Fallback): Quét %LOCALAPPDATA%\\Roblox\\Versions và gọi trực tiếp RobloxPlayerBeta.exe
      - Android / Termux: Gọi Intent qua ADB / am start
    """
    clean_pid = "".join(filter(str.isdigit, str(place_id))) or "2753915549"
    if job_id:
        uri = f"roblox://experiences/start?placeId={clean_pid}&gameInstanceId={job_id}"
    else:
        uri = f"roblox://experiences/start?placeId={clean_pid}"

    logger.info(f"Khởi chạy Roblox Client -> PlaceId: {clean_pid} (JobId: {job_id or 'None'})")

    if os.name == "nt":
        # 1. Thử qua os.startfile (Tier 1)
        try:
            os.startfile(uri)
            time.sleep(1.0)
            return {"status": "LAUNCHED", "method": "URI_SCHEME", "place_id": clean_pid}
        except Exception as e:
            logger.debug(f"Khởi chạy URI Scheme thất bại, chuyển sang Fallback Binary: {e}")

        # 2. Thử qua quét Version Folder (Tier 2)
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        versions_dir = os.path.join(local_app_data, "Roblox", "Versions")
        if os.path.isdir(versions_dir):
            try:
                executables = []
                for entry in os.scandir(versions_dir):
                    if entry.is_dir():
                        exe_path = os.path.join(entry.path, "RobloxPlayerBeta.exe")
                        if os.path.isfile(exe_path):
                            executables.append(exe_path)
                if executables:
                    latest_exe = max(executables, key=os.path.getmtime)
                    import subprocess
                    proc = subprocess.Popen([latest_exe, "--app", "--launchtime=0", uri])
                    return {"status": "LAUNCHED", "method": "DIRECT_EXE", "pid": proc.pid, "place_id": clean_pid}
            except Exception as e:
                logger.warning(f"Fallback Direct EXE launch thất bại: {e}")

    else:
        # Android / Termux
        import subprocess
        intent_cmds = [
            ["su", "-c", f"am start -a android.intent.action.VIEW -d '{uri}' com.roblox.client"],
            ["am", "start", "-a", "android.intent.action.VIEW", "-d", uri, "com.roblox.client"],
            ["su", "-c", "monkey -p com.roblox.client 1"]
        ]
        for cmd in intent_cmds:
            try:
                subprocess.run(cmd, capture_output=True, timeout=5)
                return {"status": "LAUNCHED", "method": "ANDROID_INTENT", "place_id": clean_pid}
            except Exception:
                continue

    return {"status": "ERROR", "error": "Không thể khởi chạy Roblox Client trên thiết bị này"}


# Singleton instance
game_manager = GameSelectorManager()

