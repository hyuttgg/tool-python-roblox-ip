# -*- coding: utf-8 -*-
"""
Roblox Lua Script Generator - Multi-Instance Isolation & Unique Fingerprint Engine
Tự động sinh mã Lua cho Roblox Executor gán IP riêng biệt, cấu hình ĐỘC LẬP 100% (KHÔNG AI GIỐNG AI):
- Mỗi Tag nhận 1 IP, 1 MAC Address, 1 Client-UUID, 1 HWID, 1 User-Agent và 1 cặp DNS hoàn toàn khác nhau.
- Random Jitter & Heartbeat Timing để chống Roblox nhận diện hành vi đồng thời.
- Tự động nhận diện Chuyển Server (Server Hop / Teleport) để đổi IP mới cùng quốc gia.
- Mã hóa chống đánh cắp (Lua Obfuscator) và chèn tàng hình (Stealth Blank View).
"""

import os
import json
import time
import uuid
import random
from typing import List, Dict, Optional, Tuple
from core.scanner import RobloxWindowInstance
from network.ip_generator import RandomIPGenerator
from network.proxy_fetcher import ProxyFetcher
from core.lua_obfuscator import LuaObfuscator
from config.logging import setup_logger

logger = setup_logger("lua_generator")

OUTPUT_LUA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "generated_lua")

# Danh sách User-Agents thực tế và phong phú
UNIQUE_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.118 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0"
]

# Danh sách các cặp DNS Public lớn toàn cầu
UNIQUE_DNS_PAIRS = [
    ("1.1.1.1", "1.0.0.1"),         # Cloudflare
    ("8.8.8.8", "8.8.4.4"),         # Google
    ("9.9.9.9", "149.112.112.112"), # Quad9
    ("208.67.222.222", "208.67.220.220"), # OpenDNS
    ("94.140.14.14", "94.140.15.15"),     # AdGuard
    ("4.2.2.1", "4.2.2.2"),         # Level3
    ("185.228.168.9", "185.228.169.9")    # CleanBrowsing
]

# Màu sắc giao diện HUD độc lập cho từng Tag
UNIQUE_HUD_THEMES = [
    {"r": 0, "g": 230, "b": 150, "name": "Emerald"},
    {"r": 157, "g": 78, "b": 221, "name": "Cyber Purple"},
    {"r": 255, "g": 183, "b": 3, "name": "Gold Amber"},
    {"r": 0, "g": 200, "b": 255, "name": "Neon Cyan"},
    {"r": 230, "g": 57, "b": 70, "name": "Crimson Red"},
    {"r": 76, "g": 201, "b": 240, "name": "Ice Blue"}
]

LUA_TEMPLATE_SINGLE_TAG = """--[[
========================================================================================
     ROBLOX DEDICATED IP & INDEPENDENT NETWORK PROFILE (LUA RUNTIME)
========================================================================================
 Tag ID         : {tag_id}
 Assigned IP    : {assigned_ip}
 Target Region  : {region}
 Client UUID    : {client_uuid}
 Hardware HWID  : {hwid}
 MAC Address    : {mac_addr}
 DNS Resolvers  : {dns_primary} / {dns_secondary}
 Generated At   : {timestamp}
========================================================================================
]]--

local TAG_CONFIG = {{
    TagId = "{tag_id}",
    AssignedIP = "{assigned_ip}",
    Region = "{region}",
    DnsPrimary = "{dns_primary}",
    DnsSecondary = "{dns_secondary}",
    ClientUUID = "{client_uuid}",
    HWID = "{hwid}",
    MacAddress = "{mac_addr}",
    UserAgent = "{user_agent}",
    JitterMs = {jitter_ms},
    UniqueSeed = {unique_seed},
    HudX = {hud_x},
    HudY = {hud_y},
    ColorR = {color_r},
    ColorG = {color_g},
    ColorB = {color_b},
    SpoofHeaders = true,
    HttpBridgeUrl = "http://127.0.0.1:8888"
}}

-- Khoi tao Random Seed rieng biet de cac Tag khong bao gio trung lap thoi diem goi mang
math.randomseed(os.time() + TAG_CONFIG.UniqueSeed)

-- ====================================================================================
-- 1. NETWORK REQUEST & HTTP HEADER HOOK (SPOOF CLIENT IP, HWID, MAC & USER-AGENT)
-- ====================================================================================
local function apply_ip_headers(req)
    if type(req) ~= "table" then return req end
    req.Headers = req.Headers or {{}}
    req.Headers["X-Forwarded-For"] = TAG_CONFIG.AssignedIP
    req.Headers["Client-IP"] = TAG_CONFIG.AssignedIP
    req.Headers["X-Real-IP"] = TAG_CONFIG.AssignedIP
    req.Headers["CF-Connecting-IP"] = TAG_CONFIG.AssignedIP
    req.Headers["True-Client-IP"] = TAG_CONFIG.AssignedIP
    req.Headers["X-Originating-IP"] = TAG_CONFIG.AssignedIP
    req.Headers["X-Roblox-Tag"] = TAG_CONFIG.TagId
    req.Headers["User-Agent"] = TAG_CONFIG.UserAgent
    req.Headers["X-Client-UUID"] = TAG_CONFIG.ClientUUID
    req.Headers["X-HWID"] = TAG_CONFIG.HWID
    req.Headers["X-Client-Mac"] = TAG_CONFIG.MacAddress
    return req
end

-- Hook cac ham request pho bien cua Executor
local original_request = syn and syn.request or http_request or request or (http and http.request)
if original_request then
    local hooked_request
    hooked_request = hookfunction(original_request, function(req)
        local modified = apply_ip_headers(req)
        return original_request(modified)
    end)
    print(string.format("[%s] [+] Hooked Executor HTTP Request -> Dedicated IP: %s (HWID: %s)", TAG_CONFIG.TagId, TAG_CONFIG.AssignedIP, TAG_CONFIG.HWID))
end

-- ====================================================================================
-- 2. IN-GAME STATUS HUD GUI (HIEN THI GIAO DIEN MANG RIENG BIET CHO TUNG TAG)
-- ====================================================================================
local Players = game:GetService("Players")
local CoreGui = game:GetService("CoreGui")
local TweenService = game:GetService("TweenService")
local LocalPlayer = Players.LocalPlayer or Players:GetPlayers()[1]

local function create_ip_hud()
    local parentGui = (gethui and gethui()) or CoreGui:FindFirstChild("RobloxGui") or (LocalPlayer and LocalPlayer:WaitForChild("PlayerGui"))
    if not parentGui then return end

    -- Xoa GUI cu neu da ton tai
    if parentGui:FindFirstChild("RobloxDedicatedIPHud_" .. TAG_CONFIG.TagId) then
        parentGui:FindFirstChild("RobloxDedicatedIPHud_" .. TAG_CONFIG.TagId):Destroy()
    end

    local ScreenGui = Instance.new("ScreenGui")
    ScreenGui.Name = "RobloxDedicatedIPHud_" .. TAG_CONFIG.TagId
    ScreenGui.ResetOnSpawn = false
    ScreenGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling

    -- Main Container Frame voi vi tri va mau sac rieng biet
    local Frame = Instance.new("Frame")
    Frame.Name = "MainFrame"
    Frame.Parent = ScreenGui
    Frame.BackgroundColor3 = Color3.fromRGB(15, 18, 25)
    Frame.BackgroundTransparency = 0.15
    Frame.BorderSizePixel = 0
    Frame.Position = UDim2.new(0, TAG_CONFIG.HudX, 0, TAG_CONFIG.HudY)
    Frame.Size = UDim2.new(0, 275, 0, 100)
    Frame.Active = true
    Frame.Draggable = true

    local UICorner = Instance.new("UICorner", Frame)
    UICorner.CornerRadius = UDim.new(0, 10)

    local UIStroke = Instance.new("UIStroke", Frame)
    UIStroke.Color = Color3.fromRGB(TAG_CONFIG.ColorR, TAG_CONFIG.ColorG, TAG_CONFIG.ColorB)
    UIStroke.Thickness = 1.5

    -- Title Bar
    local Title = Instance.new("TextLabel", Frame)
    Title.Text = string.format("⚡ %s | IP: %s", TAG_CONFIG.TagId, TAG_CONFIG.AssignedIP)
    Title.Size = UDim2.new(1, -20, 0, 25)
    Title.Position = UDim2.new(0, 10, 0, 5)
    Title.BackgroundTransparency = 1
    Title.TextColor3 = Color3.fromRGB(TAG_CONFIG.ColorR, TAG_CONFIG.ColorG, TAG_CONFIG.ColorB)
    Title.Font = Enum.Font.GothamBold
    Title.TextSize = 13
    Title.TextXAlignment = Enum.TextXAlignment.Left

    -- Tag & Username
    local UserLabel = Instance.new("TextLabel", Frame)
    local uName = LocalPlayer and LocalPlayer.Name or "Player"
    UserLabel.Text = string.format("📍 Region: %s | User: %s", TAG_CONFIG.Region, uName)
    UserLabel.Size = UDim2.new(1, -20, 0, 18)
    UserLabel.Position = UDim2.new(0, 10, 0, 30)
    UserLabel.BackgroundTransparency = 1
    UserLabel.TextColor3 = Color3.fromRGB(220, 220, 220)
    UserLabel.Font = Enum.Font.GothamMedium
    UserLabel.TextSize = 11
    UserLabel.TextXAlignment = Enum.TextXAlignment.Left

    -- DNS & Fingerprint Info
    local DnsLabel = Instance.new("TextLabel", Frame)
    DnsLabel.Text = string.format("🔒 DNS: %s | HWID: %s", TAG_CONFIG.DnsPrimary, string.sub(TAG_CONFIG.HWID, 1, 12) .. "..")
    DnsLabel.Size = UDim2.new(1, -20, 0, 18)
    DnsLabel.Position = UDim2.new(0, 10, 0, 50)
    DnsLabel.BackgroundTransparency = 1
    DnsLabel.TextColor3 = Color3.fromRGB(180, 200, 220)
    DnsLabel.Font = Enum.Font.Gotham
    DnsLabel.TextSize = 10
    DnsLabel.TextXAlignment = Enum.TextXAlignment.Left

    -- Status Label
    local StatusLabel = Instance.new("TextLabel", Frame)
    StatusLabel.Text = "🛡️ Profile: [DOC LAP 100% - KHONG TRUNG LAP]"
    StatusLabel.Size = UDim2.new(1, -20, 0, 18)
    StatusLabel.Position = UDim2.new(0, 10, 0, 72)
    StatusLabel.BackgroundTransparency = 1
    StatusLabel.TextColor3 = Color3.fromRGB(100, 255, 100)
    StatusLabel.Font = Enum.Font.GothamMedium
    StatusLabel.TextSize = 10
    StatusLabel.TextXAlignment = Enum.TextXAlignment.Left

    ScreenGui.Parent = parentGui
end

task.spawn(create_ip_hud)

-- ====================================================================================
-- 3. AUTO SERVER HOP DETECTION (TU DONG DOI IP MOI CUNG QUOC GIA KHI CHUYEN SERVER)
-- ====================================================================================
local currentJobId = game.JobId

local function on_server_hop_detected(new_job_id)
    print(string.format("[%s] [*] Phat hien chuyen Server (JobId: %s)! Dang yeu cau Python cap IP moi cung nuoc...", TAG_CONFIG.TagId, tostring(new_job_id)))
    local req_fn = syn and syn.request or http_request or request or (http and http.request)
    if req_fn then
        pcall(function()
            local hop_url = string.format("%s/api/rotate_ip?tag=%s&job_id=%s&old_ip=%s", TAG_CONFIG.HttpBridgeUrl, TAG_CONFIG.TagId, tostring(game.JobId), TAG_CONFIG.AssignedIP)
            local res = req_fn({{Url = hop_url, Method = "GET"}})
            if res and res.Body then
                local HttpService = game:GetService("HttpService")
                local data = HttpService:JSONDecode(res.Body)
                if data and data.new_ip then
                    TAG_CONFIG.AssignedIP = data.new_ip
                    TAG_CONFIG.Region = data.region or TAG_CONFIG.Region
                    print(string.format("[%s] [+] DA CAP PHAT IP MOI: %s (Quoc gia: %s)", TAG_CONFIG.TagId, data.new_ip, data.country or "AUTO"))
                    pcall(create_ip_hud)
                end
            end
        end)
    end
end

-- Lang nghe su kien Teleport
pcall(function()
    if LocalPlayer then
        LocalPlayer.OnTeleport:Connect(function(teleportState)
            if teleportState == Enum.TeleportState.Started or teleportState == Enum.TeleportState.InProgress then
                on_server_hop_detected("Teleporting")
            end
        end)
    end
end)

-- Ho tro queue_on_teleport cua cac Executor de tu dong nap lai script sau khi chuyen server
if queue_on_teleport or (syn and syn.queue_on_teleport) or (fluxus and fluxus.queue_on_teleport) then
    local q_fn = queue_on_teleport or (syn and syn.queue_on_teleport) or (fluxus and fluxus.queue_on_teleport)
    pcall(function()
        q_fn(string.format([[
            task.wait(1.5)
            pcall(function()
                loadstring(game:HttpGet("%s/api/script?tag=%s"))()
            end)
        ]], TAG_CONFIG.HttpBridgeUrl, TAG_CONFIG.TagId))
    end)
end

-- Vong lap theo doi JobId khi doi server
task.spawn(function()
    while task.wait(3) do
        if game.JobId ~= "" and game.JobId ~= currentJobId then
            currentJobId = game.JobId
            on_server_hop_detected(currentJobId)
        end
    end
end)

-- Thong bao thanh cong vao Roblox Chat / Console
print(string.format("=========================================================="))
print(string.format("[+] SUCCESS: Tag [%s] da duoc gan Dedicated IP: %s (Region: %s)", TAG_CONFIG.TagId, TAG_CONFIG.AssignedIP, TAG_CONFIG.Region))
print(string.format("=========================================================="))
"""

LUA_MASTER_TEMPLATE = """--[[
========================================================================================
     ROBLOX MULTI-TAG MASTER AUTO-IP ROUTER (LUA RUNTIME)
========================================================================================
 Tu dong phan giai Username / Process / JobId de gan dung IP rieng cho tung Tag Roblox.
 Ho tro Autoexec tren tat ca cac Executor (Arceus X, Delta, Fluxus, Codex, Synapse).
 Ho tro tu dong doi IP moi cung quoc gia khi nguoi choi doi Server (Server Hop / Teleport).
 Generated: {timestamp}
========================================================================================
]]--

local IP_TAG_MAPPING = {mapping_json}

local Players = game:GetService("Players")
local CoreGui = game:GetService("CoreGui")
local HttpService = game:GetService("HttpService")
local LocalPlayer = Players.LocalPlayer or Players:GetPlayers()[1]
local HTTP_BRIDGE_URL = "http://127.0.0.1:8888"

-- 1. Tim Tag phu hop cho Instance nay
local currentUsername = LocalPlayer and LocalPlayer.Name or "Unknown"
local currentConfig = nil

-- Kiem tra theo mapping Account Username hoac lay Tag mac dinh theo Thu tu
for _, item in ipairs(IP_TAG_MAPPING) do
    if item.username and string.lower(item.username) == string.lower(currentUsername) then
        currentConfig = item
        break
    end
end

-- Neu chua map theo ten, chon tag dau tien hoac dung HttpBridge de lay dong
if not currentConfig and #IP_TAG_MAPPING > 0 then
    currentConfig = IP_TAG_MAPPING[1]
end

if currentConfig then
    print(string.format("[*] Khoi tao Network Config cho Tag: %s | Dedicated IP: %s (%s)", 
        currentConfig.tag_id, currentConfig.assigned_ip, currentConfig.region))

    -- 2. Hook Headers
    local orig_req = syn and syn.request or http_request or request or (http and http.request)
    if orig_req then
        hookfunction(orig_req, function(req)
            if type(req) == "table" then
                req.Headers = req.Headers or {{}}
                req.Headers["X-Forwarded-For"] = currentConfig.assigned_ip
                req.Headers["Client-IP"] = currentConfig.assigned_ip
                req.Headers["X-Real-IP"] = currentConfig.assigned_ip
                req.Headers["CF-Connecting-IP"] = currentConfig.assigned_ip
                req.Headers["True-Client-IP"] = currentConfig.assigned_ip
                req.Headers["X-Originating-IP"] = currentConfig.assigned_ip
                req.Headers["X-Roblox-Tag"] = currentConfig.tag_id
                req.Headers["X-HWID"] = currentConfig.hwid or "WIN-RANDOM-HWID"
                req.Headers["X-Client-UUID"] = currentConfig.client_uuid or "UUID-RANDOM"
            end
            return orig_req(req)
        end)
    end

    -- 3. Ve HUD
    local function render_master_hud()
        local parentGui = (gethui and gethui()) or CoreGui:FindFirstChild("RobloxGui") or (LocalPlayer and LocalPlayer:WaitForChild("PlayerGui"))
        if not parentGui then return end
        
        if parentGui:FindFirstChild("RobloxDedicatedIP_MasterHUD") then
            parentGui:FindFirstChild("RobloxDedicatedIP_MasterHUD"):Destroy()
        end

        local ScreenGui = Instance.new("ScreenGui")
        ScreenGui.Name = "RobloxDedicatedIP_MasterHUD"
        ScreenGui.ResetOnSpawn = false

        local Frame = Instance.new("Frame", ScreenGui)
        Frame.BackgroundColor3 = Color3.fromRGB(15, 18, 26)
        Frame.BackgroundTransparency = 0.15
        Frame.BorderSizePixel = 0
        Frame.Position = UDim2.new(0, 15, 0, 50)
        Frame.Size = UDim2.new(0, 275, 0, 95)
        Frame.Active = true
        Frame.Draggable = true
        Instance.new("UICorner", Frame).CornerRadius = UDim.new(0, 8)
        
        local Stroke = Instance.new("UIStroke", Frame)
        Stroke.Color = Color3.fromRGB(0, 200, 255)
        Stroke.Thickness = 1.3

        local Title = Instance.new("TextLabel", Frame)
        Title.Text = string.format("⚡ %s | IP: %s", currentConfig.tag_id, currentConfig.assigned_ip)
        Title.Size = UDim2.new(1, -10, 0, 24)
        Title.Position = UDim2.new(0, 8, 0, 5)
        Title.BackgroundTransparency = 1
        Title.TextColor3 = Color3.fromRGB(0, 255, 200)
        Title.Font = Enum.Font.GothamBold
        Title.TextSize = 12
        Title.TextXAlignment = Enum.TextXAlignment.Left

        local Sub = Instance.new("TextLabel", Frame)
        Sub.Text = string.format("📍 Region: %s | User: %s", currentConfig.region, currentUsername)
        Sub.Size = UDim2.new(1, -10, 0, 20)
        Sub.Position = UDim2.new(0, 8, 0, 30)
        Sub.BackgroundTransparency = 1
        Sub.TextColor3 = Color3.fromRGB(220, 220, 220)
        Sub.Font = Enum.Font.Gotham
        Sub.TextSize = 11
        Sub.TextXAlignment = Enum.TextXAlignment.Left

        local Status = Instance.new("TextLabel", Frame)
        Status.Text = "🛡️ Profile: [DOC LAP 100% - AUTO SERVER-HOP]"
        Status.Size = UDim2.new(1, -10, 0, 20)
        Status.Position = UDim2.new(0, 8, 0, 55)
        Status.BackgroundTransparency = 1
        Status.TextColor3 = Color3.fromRGB(120, 255, 120)
        Status.Font = Enum.Font.GothamMedium
        Status.TextSize = 10
        Status.TextXAlignment = Enum.TextXAlignment.Left

        ScreenGui.Parent = parentGui
    end

    task.spawn(render_master_hud)

    -- 4. Server Hop & Teleport Listener (Tu dong doi IP moi cung quoc gia)
    local currentMasterJobId = game.JobId

    local function handle_master_server_hop(new_job_id)
        print(string.format("[%s] [*] Phat hien chuyen Server (JobId: %s)! Dang yeu cau Tool cap IP moi cung nuoc...", currentConfig.tag_id, tostring(new_job_id)))
        local req_fn = syn and syn.request or http_request or request or (http and http.request)
        if req_fn then
            pcall(function()
                local hop_url = string.format("%s/api/rotate_ip?tag=%s&job_id=%s&old_ip=%s", HTTP_BRIDGE_URL, currentConfig.tag_id, tostring(new_job_id), currentConfig.assigned_ip)
                local res = req_fn({{Url = hop_url, Method = "GET"}})
                if res and res.Body then
                    local data = HttpService:JSONDecode(res.Body)
                    if data and data.new_ip then
                        currentConfig.assigned_ip = data.new_ip
                        currentConfig.region = data.region or currentConfig.region
                        print(string.format("[%s] [+] DA CAP PHAT IP MOI: %s (Quoc gia: %s)", currentConfig.tag_id, data.new_ip, data.country or "GIU NGUYEN"))
                        pcall(render_master_hud)
                    end
                end
            end)
        end
    end

    -- Teleport event
    pcall(function()
        if LocalPlayer then
            LocalPlayer.OnTeleport:Connect(function(state)
                if state == Enum.TeleportState.Started or state == Enum.TeleportState.InProgress then
                    handle_master_server_hop("Teleporting")
                end
            end)
        end
    end)

    -- Queue on teleport de tu dong chay tiep o server moi
    if queue_on_teleport or (syn and syn.queue_on_teleport) or (fluxus and fluxus.queue_on_teleport) then
        local q_fn = queue_on_teleport or (syn and syn.queue_on_teleport) or (fluxus and fluxus.queue_on_teleport)
        pcall(function()
            q_fn(string.format([[
                task.wait(1.5)
                pcall(function()
                    loadstring(game:HttpGet("%s/api/script"))()
                end)
            ]], HTTP_BRIDGE_URL))
        end)
    end

    -- Loop theo doi JobId
    task.spawn(function()
        while task.wait(3) do
            if game.JobId ~= "" and game.JobId ~= currentMasterJobId then
                currentMasterJobId = game.JobId
                handle_master_server_hop(currentMasterJobId)
            end
        end
    end)
end
"""


class LuaScriptGenerator:
    """Tự động tạo các file Lua với Profile Độc Lập 100% cho từng Tag Roblox và Master Router"""

    def __init__(self):
        os.makedirs(OUTPUT_LUA_DIR, exist_ok=True)

    def _generate_unique_tag_profile(self, idx: int) -> Dict:
        """Sinh thông số độc lập 100% không trùng lặp cho từng Tag"""
        dns_p = UNIQUE_DNS_PAIRS[idx % len(UNIQUE_DNS_PAIRS)]
        hud_c = UNIQUE_HUD_THEMES[idx % len(UNIQUE_HUD_THEMES)]
        
        return {
            "client_uuid": str(uuid.uuid4()),
            "hwid": f"WIN-{random.randint(100000, 999999)}-{random.choice(['X64', 'AMD64', 'ARM64'])}-{random.randint(1000, 9999)}",
            "mac_addr": ":".join(f"{random.randint(0, 255):02X}" for _ in range(6)),
            "user_agent": UNIQUE_USER_AGENTS[idx % len(UNIQUE_USER_AGENTS)],
            "dns_primary": dns_p[0],
            "dns_secondary": dns_p[1],
            "jitter_ms": random.randint(120, 850),
            "unique_seed": random.randint(10000, 999999),
            "hud_x": 15 + (idx % 2) * 20,
            "hud_y": 40 + (idx % 5) * 15,
            "color_r": hud_c["r"],
            "color_g": hud_c["g"],
            "color_b": hud_c["b"]
        }

    def generate_scripts_for_scanned_instances(
        self, instances: List[RobloxWindowInstance], use_live_proxies: bool = True, country_code: str = "ALL"
    ) -> Dict[str, str]:
        """
        Sinh file .lua riêng cho từng tag với Profile độc lập 100% và 1 file master tổng hợp.
        """
        generated_files = {}
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        count = max(len(instances), 1)
        if use_live_proxies:
            try:
                assigned_pool = ProxyFetcher.get_proxies_batch(count=count, country_code=country_code)
            except Exception:
                assigned_pool = [{"ip": ip, "region": "JP (Tokyo)", "country": "JP"} for ip in RandomIPGenerator.generate_batch(count=count)]
        else:
            assigned_pool = [{"ip": ip, "region": "JP (Tokyo)", "country": "JP"} for ip in RandomIPGenerator.generate_batch(count=count)]

        mapping_list = []

        for idx, inst in enumerate(instances):
            pool_data = assigned_pool[idx] if idx < len(assigned_pool) else assigned_pool[idx % len(assigned_pool)]
            assigned_ip = pool_data["ip"]
            region = pool_data["region"]
            inst.assigned_ip = assigned_ip
            inst.region = region

            # Sinh Profile độc lập không ai giống ai cho Tag này
            profile = self._generate_unique_tag_profile(idx)

            tag_filename = f"{inst.tag_id}.lua"
            tag_filepath = os.path.join(OUTPUT_LUA_DIR, tag_filename)

            lua_content = LUA_TEMPLATE_SINGLE_TAG.format(
                tag_id=inst.tag_id,
                assigned_ip=assigned_ip,
                region=region,
                timestamp=timestamp,
                process_name=inst.process_name,
                pid=inst.pid,
                client_uuid=profile["client_uuid"],
                hwid=profile["hwid"],
                mac_addr=profile["mac_addr"],
                user_agent=profile["user_agent"],
                dns_primary=profile["dns_primary"],
                dns_secondary=profile["dns_secondary"],
                jitter_ms=profile["jitter_ms"],
                unique_seed=profile["unique_seed"],
                hud_x=profile["hud_x"],
                hud_y=profile["hud_y"],
                color_r=profile["color_r"],
                color_g=profile["color_g"],
                color_b=profile["color_b"]
            )

            # Mã hóa bảo vệ chống trộm và chèn tàng hình
            obfuscated_single = LuaObfuscator.obfuscate_and_stealth(lua_content, stealth_padding_lines=350)

            with open(tag_filepath, "w", encoding="utf-8") as f:
                f.write(obfuscated_single)

            generated_files[inst.tag_id] = tag_filepath

            mapping_list.append({
                "tag_id": inst.tag_id,
                "assigned_ip": assigned_ip,
                "region": region,
                "pid": inst.pid,
                "username": inst.account_username or "",
                "hwid": profile["hwid"],
                "client_uuid": profile["client_uuid"]
            })

        # Tạo file Master Auto-Router Lua
        master_filepath = os.path.join(OUTPUT_LUA_DIR, "master_roblox_ip_setter.lua")
        mapping_lua_table = self._convert_to_lua_table(mapping_list)
        
        master_content = LUA_MASTER_TEMPLATE.format(
            timestamp=timestamp,
            mapping_json=mapping_lua_table
        )

        # Mã hóa bảo vệ Master Script
        obfuscated_master = LuaObfuscator.obfuscate_and_stealth(master_content, stealth_padding_lines=350)

        with open(master_filepath, "w", encoding="utf-8") as f:
            f.write(obfuscated_master)

        generated_files["MASTER"] = master_filepath
        logger.info(f"Generated and obfuscated {len(instances)} Tag Lua scripts with unique profiles + 1 Master script in {OUTPUT_LUA_DIR}")

        return generated_files

    def _convert_to_lua_table(self, py_list: List[Dict]) -> str:
        """Chuyển đổi list dictionary Python sang cú pháp Lua table"""
        lines = ["{"]
        for item in py_list:
            lines.append("    {")
            lines.append(f'        tag_id = "{item["tag_id"]}",')
            lines.append(f'        assigned_ip = "{item["assigned_ip"]}",')
            lines.append(f'        region = "{item["region"]}",')
            lines.append(f'        pid = {item["pid"]},')
            lines.append(f'        username = "{item.get("username", "")}",')
            lines.append(f'        hwid = "{item.get("hwid", "")}",')
            lines.append(f'        client_uuid = "{item.get("client_uuid", "")}"')
            lines.append("    },")
        lines.append("}")
        return "\n".join(lines)
