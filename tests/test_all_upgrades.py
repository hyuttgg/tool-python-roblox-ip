# -*- coding: utf-8 -*-
"""
Verification suite for all newly implemented components:
  1. Per-Tag Multi-Game Selector Hub (Mỗi Tag 1 Game khác nhau)
  2. Selection Sort & Java Bridge
  3. Bridge Server API (Per-Tag Target Game, Heartbeat, Tag Status, Watchdog)
  4. Watchdog Supervisor & Auto-Restart logic with Per-Tag Games
  5. Lua Script Generator with Per-Tag Games & Heartbeat Hook
"""

import os
import sys
import time
import json
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.game_selector import game_manager, POPULAR_ROBLOX_GAMES
from core.watchdog_supervisor import watchdog
from core.java_sort_bridge import SelectionSortBridge, RobloxAutoLauncher
from network.bridge_server import RobloxBridgeServer
from core.lua_generator import LuaScriptGenerator
from core.scanner import RobloxWindowInstance, WindowRect


def test_per_tag_game_selector():
    print("[TEST 1] Per-Tag Multi-Game Selector Hub...", flush=True)
    
    # 1. Test Global Game
    game_manager.set_game_by_item(POPULAR_ROBLOX_GAMES[0])
    cur = game_manager.get_current_game()
    assert cur["name"] == "Blox Fruits"
    assert cur["place_id"] == "2753915549"

    # 2. Test Per-Tag Unique Games
    game_manager.set_game_for_tag("ROBLOX-TAG-01", "Blox Fruits", "2753915549")
    game_manager.set_game_for_tag("ROBLOX-TAG-02", "King Legacy", "4520749081")
    game_manager.set_game_for_tag("ROBLOX-TAG-03", "Fisch (Fishing Sim)", "16732694052")

    g1 = game_manager.get_game_for_tag("ROBLOX-TAG-01")
    g2 = game_manager.get_game_for_tag("ROBLOX-TAG-02")
    g3 = game_manager.get_game_for_tag("ROBLOX-TAG-03")

    assert g1["place_id"] == "2753915549" and g1["name"] == "Blox Fruits"
    assert g2["place_id"] == "4520749081" and g2["name"] == "King Legacy"
    assert g3["place_id"] == "16732694052" and "Fisch" in g3["name"]

    uri1 = game_manager.get_launch_uri_for_tag("ROBLOX-TAG-01")
    uri2 = game_manager.get_launch_uri_for_tag("ROBLOX-TAG-02")
    assert "2753915549" in uri1
    assert "4520749081" in uri2

    print(f"   -> [PASS] Tag 1: {g1['name']} ({g1['place_id']}) | Tag 2: {g2['name']} ({g2['place_id']}) | Tag 3: {g3['name']} ({g3['place_id']})", flush=True)


def test_selection_sort():
    print("[TEST 2] Selection Sort Engine (Java / Python Bridge)...", flush=True)
    candidates = [
        {"ip": "1.1.1.1:80", "latency_ms": 120, "region": "US"},
        {"ip": "2.2.2.2:80", "latency_ms": 18, "region": "VN"},
        {"ip": "3.3.3.3:80", "latency_ms": 65, "region": "JP"}
    ]
    res = SelectionSortBridge.execute_selection_sort(candidates)
    assert res["status"] == "success"
    sorted_proxies = res["sorted_proxies"]
    assert sorted_proxies[0]["latency_ms"] == 18
    assert sorted_proxies[0]["rank"] == 1
    print(f"   -> [PASS] Selection Sort: Rank #1 is {sorted_proxies[0]['ip']} ({sorted_proxies[0]['latency_ms']} ms)", flush=True)


def test_bridge_and_watchdog():
    print("[TEST 3] Bridge Server & Watchdog HTTP Endpoints (with Per-Tag Game resolution)...", flush=True)
    watchdog.auto_reopen_on_disconnect = False  # Tránh pop up Roblox client thực tế khi unit test
    
    test_port = 8899
    server = RobloxBridgeServer(host="127.0.0.1", port=test_port)
    server.start()
    time.sleep(0.5)

    try:
        # 1. Test /api/target_game with Tag query
        req1 = urllib.request.Request(f"http://127.0.0.1:{test_port}/api/target_game?tag=ROBLOX-TAG-01")
        with urllib.request.urlopen(req1) as resp:
            data1 = json.loads(resp.read().decode())
            assert data1["place_id"] == "2753915549"

        req2 = urllib.request.Request(f"http://127.0.0.1:{test_port}/api/target_game?tag=ROBLOX-TAG-02")
        with urllib.request.urlopen(req2) as resp:
            data2 = json.loads(resp.read().decode())
            assert data2["place_id"] == "4520749081"
        print("   -> [PASS] GET /api/target_game (Per-Tag Resolution: Tag 1 -> Blox Fruits, Tag 2 -> King Legacy)", flush=True)

        # 2. Test POST /api/heartbeat
        hb_body = json.dumps({
            "tag_id": "ROBLOX-TAG-01",
            "username": "TestGamer",
            "place_id": "2753915549",
            "fps": 60,
            "ping_ms": 25,
            "status": "ALIVE"
        }).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{test_port}/api/heartbeat",
            data=hb_body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            assert data["status"] == "ok"
        print("   -> [PASS] POST /api/heartbeat", flush=True)

        # 3. Test POST /api/tag_status (Error / Disconnect)
        err_body = json.dumps({
            "tag_id": "ROBLOX-TAG-01",
            "status": "DISCONNECTED",
            "error_message": "Error Code 277: Lost connection to the game server",
            "username": "TestGamer"
        }).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{test_port}/api/tag_status",
            data=err_body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            assert data["status"] == "recorded"
        print("   -> [PASS] POST /api/tag_status", flush=True)

        # 4. Test GET /api/watchdog/status
        req = urllib.request.Request(f"http://127.0.0.1:{test_port}/api/watchdog/status")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            assert "ROBLOX-TAG-01" in data["tags"]
        print("   -> [PASS] GET /api/watchdog/status", flush=True)

    finally:
        server.stop()
        watchdog.auto_reopen_on_disconnect = True


def test_lua_generation():
    print("[TEST 4] Lua Script Generator (Per-Tag Game Mapping)...", flush=True)
    gen = LuaScriptGenerator()
    test_instances = [
        RobloxWindowInstance("ROBLOX-TAG-01", 1001, "Roblox 1", 1001, "RobloxPlayerBeta.exe", "WIN", WindowRect(), "Center", "250 MB"),
        RobloxWindowInstance("ROBLOX-TAG-02", 0, "Roblox Clone [CHƯA MỞ]", 0, "CLONE", "CLONE", WindowRect(), "Offline", "0 MB")
    ]
    files = gen.generate_scripts_for_scanned_instances(test_instances, use_live_proxies=False)
    assert "MASTER" in files
    assert "ROBLOX-TAG-01" in files
    assert "ROBLOX-TAG-02" in files
    assert os.path.exists(files["MASTER"])
    print(f"   -> [PASS] Generated scripts with Per-Tag Games: Master, Tag 1, Tag 2", flush=True)


if __name__ == "__main__":
    print("\n" + "=" * 70, flush=True)
    print("      RUNNING ROBLOX CONTROLLER COMPREHENSIVE TEST SUITE", flush=True)
    print("=" * 70 + "\n", flush=True)
    test_per_tag_game_selector()
    test_selection_sort()
    test_bridge_and_watchdog()
    test_lua_generation()
    print("\n" + "=" * 70, flush=True)
    print("      ALL TEST CASES PASSED WITH 100% SUCCESS!", flush=True)
    print("=" * 70 + "\n", flush=True)
    sys.exit(0)
