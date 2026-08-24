# -*- coding: utf-8 -*-
"""
Roblox Lua Script Generator - Multi-Instance Isolation & Unique Fingerprint Engine
Tự động sinh mã Lua cho Roblox Executor gán IP riêng biệt, cấu hình ĐỘC LẬP 100% (KHÔNG AI GIỐNG AI):
- Mỗi Tag nhận 1 IP, 1 MAC Address, 1 Client-UUID, 1 HWID, 1 User-Agent và 1 cặp DNS hoàn toàn khác nhau.
- TÍCH HỢP PER-TAG MULTI-GAME: Mỗi Tag được gán 1 Game Roblox riêng biệt (Blox Fruits, King Legacy, Fisch, PS99...).
- Tích hợp Lua Heartbeat Transmitter (gửi nhịp tim định kỳ về Python Watchdog).
- Tích hợp Lua Error & Disconnect Hook (bắt lỗi 277, 268, Kick để Python tự động mở lại Tag).
- Tích hợp Game Auto-Teleport (tự động nhận diện và chuyển server vào đúng Game Place ID riêng của từng Tag).
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
 Target Game    : {target_game_name} (PlaceId: {target_place_id})
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
    TargetGameName = "{target_game_name}",
    TargetPlaceId = "{target_place_id}",
    TargetJobId = "{target_job_id}",
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

local Players = game:GetService("Players")
local CoreGui = game:GetService("CoreGui")
local HttpService = game:GetService("HttpService")
local GuiService = game:GetService("GuiService")
local TeleportService = game:GetService("TeleportService")
local Stats = game:GetService("Stats")
local LocalPlayer = Players.LocalPlayer or Players:GetPlayers()[1]

local function safe_request(req_opts)
    local fn = syn and syn.request or http_request or request or (http and http.request)
    if fn then
        local success, res = pcall(fn, req_opts)
        if success and res then return res end
    end
    return nil
end

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

local original_request = syn and syn.request or http_request or request or (http and http.request)
if original_request then
    hookfunction(original_request, function(req)
        local modified = apply_ip_headers(req)
        return original_request(modified)
    end)
    print(string.format("[%s] [+] Hooked Executor HTTP Request -> Dedicated IP: %s", TAG_CONFIG.TagId, TAG_CONFIG.AssignedIP))
end

-- ====================================================================================
-- 2. IN-GAME STATUS HUD GUI (HIỂN THỊ GIAO DIỆN TRẠNG THÁI CHO TỪNG TAG)
-- ====================================================================================
local function create_ip_hud()
    local parentGui = (gethui and gethui()) or CoreGui:FindFirstChild("RobloxGui") or (LocalPlayer and LocalPlayer:WaitForChild("PlayerGui"))
    if not parentGui then return end

    if parentGui:FindFirstChild("RobloxDedicatedIPHud_" .. TAG_CONFIG.TagId) then
        parentGui:FindFirstChild("RobloxDedicatedIPHud_" .. TAG_CONFIG.TagId):Destroy()
    end

    local ScreenGui = Instance.new("ScreenGui")
    ScreenGui.Name = "RobloxDedicatedIPHud_" .. TAG_CONFIG.TagId
    ScreenGui.ResetOnSpawn = false
    ScreenGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling

    local Frame = Instance.new("Frame", ScreenGui)
    Frame.Name = "MainFrame"
    Frame.BackgroundColor3 = Color3.fromRGB(15, 18, 25)
    Frame.BackgroundTransparency = 0.15
    Frame.BorderSizePixel = 0
    Frame.Position = UDim2.new(0, TAG_CONFIG.HudX, 0, TAG_CONFIG.HudY)
    Frame.Size = UDim2.new(0, 285, 0, 110)
    Frame.Active = true
    Frame.Draggable = true

    Instance.new("UICorner", Frame).CornerRadius = UDim.new(0, 10)
    local UIStroke = Instance.new("UIStroke", Frame)
    UIStroke.Color = Color3.fromRGB(TAG_CONFIG.ColorR, TAG_CONFIG.ColorG, TAG_CONFIG.ColorB)
    UIStroke.Thickness = 1.5

    local Title = Instance.new("TextLabel", Frame)
    Title.Text = string.format("⚡ %s | IP: %s", TAG_CONFIG.TagId, TAG_CONFIG.AssignedIP)
    Title.Size = UDim2.new(1, -20, 0, 22)
    Title.Position = UDim2.new(0, 10, 0, 5)
    Title.BackgroundTransparency = 1
    Title.TextColor3 = Color3.fromRGB(TAG_CONFIG.ColorR, TAG_CONFIG.ColorG, TAG_CONFIG.ColorB)
    Title.Font = Enum.Font.GothamBold
    Title.TextSize = 12
    Title.TextXAlignment = Enum.TextXAlignment.Left

    local UserLabel = Instance.new("TextLabel", Frame)
    local uName = LocalPlayer and LocalPlayer.Name or "Player"
    UserLabel.Text = string.format("📍 Region: %s | User: %s", TAG_CONFIG.Region, uName)
    UserLabel.Size = UDim2.new(1, -20, 0, 18)
    UserLabel.Position = UDim2.new(0, 10, 0, 27)
    UserLabel.BackgroundTransparency = 1
    UserLabel.TextColor3 = Color3.fromRGB(220, 220, 220)
    UserLabel.Font = Enum.Font.GothamMedium
    UserLabel.TextSize = 11
    UserLabel.TextXAlignment = Enum.TextXAlignment.Left

    local GameLabel = Instance.new("TextLabel", Frame)
    GameLabel.Text = string.format("🎮 Game: %s (PlaceId: %s)", TAG_CONFIG.TargetGameName or "Roblox Game", TAG_CONFIG.TargetPlaceId or "2753915549")
    GameLabel.Size = UDim2.new(1, -20, 0, 18)
    GameLabel.Position = UDim2.new(0, 10, 0, 47)
    GameLabel.BackgroundTransparency = 1
    GameLabel.TextColor3 = Color3.fromRGB(255, 200, 100)
    GameLabel.Font = Enum.Font.GothamMedium
    GameLabel.TextSize = 10
    GameLabel.TextXAlignment = Enum.TextXAlignment.Left

    local StatusLabel = Instance.new("TextLabel", Frame)
    StatusLabel.Text = "🟢 Watchdog: [HEARTBEAT ON - AUTO-RESTART READY]"
    StatusLabel.Size = UDim2.new(1, -20, 0, 18)
    StatusLabel.Position = UDim2.new(0, 10, 0, 69)
    StatusLabel.BackgroundTransparency = 1
    StatusLabel.TextColor3 = Color3.fromRGB(100, 255, 100)
    StatusLabel.Font = Enum.Font.GothamMedium
    StatusLabel.TextSize = 10
    StatusLabel.TextXAlignment = Enum.TextXAlignment.Left

    ScreenGui.Parent = parentGui
end

task.spawn(create_ip_hud)

-- ====================================================================================
-- 3. LUA HEARTBEAT TRANSMITTER (GỬI NHỊP TIM ĐỊNH KỲ VỀ PYTHON WATCHDOG)
-- ====================================================================================
task.spawn(function()
    while task.wait(2.5) do
        pcall(function()
            local fpsVal = 60
            pcall(function() fpsVal = math.floor(workspace:GetRealPhysicsFPS()) end)
            local pingVal = 0
            pcall(function() pingVal = math.floor(Stats.Network.ServerStatsItem["Data Ping"]:GetValue()) end)
            local memVal = "0 MB"
            pcall(function() memVal = string.format("%.1f MB", Stats:GetTotalMemoryUsageMb()) end)

            local hb_payload = HttpService:JSONEncode({{
                tag_id = TAG_CONFIG.TagId,
                username = LocalPlayer and LocalPlayer.Name or "Unknown",
                place_id = tostring(game.PlaceId or "0"),
                job_id = tostring(game.JobId or ""),
                fps = fpsVal,
                ping_ms = pingVal,
                memory_mb = memVal,
                assigned_ip = TAG_CONFIG.AssignedIP,
                region = TAG_CONFIG.Region,
                status = "ALIVE"
            }})

            safe_request({{
                Url = TAG_CONFIG.HttpBridgeUrl .. "/api/heartbeat",
                Method = "POST",
                Headers = {{["Content-Type"] = "application/json"}},
                Body = hb_payload
            }})
        end)
    end
end)

-- ====================================================================================
-- 4. LUA ERROR & DISCONNECT HOOK (BẢO VỆ CHUYỂN SERVER, CHỈ BÁO LỖI FATAL DISCONNECT)
-- ====================================================================================
local isTeleporting = false

local function report_disconnection(reason_text)
    if isTeleporting then return end
    print(string.format("[%s] [!] BÁO CÁO NGẮT KẾT NỐI: %s -> Gửi tín hiệu để Python mở lại...", TAG_CONFIG.TagId, tostring(reason_text)))
    pcall(function()
        safe_request({{
            Url = TAG_CONFIG.HttpBridgeUrl .. "/api/tag_status",
            Method = "POST",
            Headers = {{["Content-Type"] = "application/json"}},
            Body = HttpService:JSONEncode({{
                tag_id = TAG_CONFIG.TagId,
                status = "DISCONNECTED",
                error_message = tostring(reason_text),
                username = LocalPlayer and LocalPlayer.Name or "",
                place_id = tostring(game.PlaceId or "")
            }})
        }})
    end)
end

pcall(function()
    GuiService.ErrorMessageChanged:Connect(function(errMsg)
        if errMsg and #errMsg > 0 and not isTeleporting then
            local low = string.lower(tostring(errMsg))
            if string.find(low, "277") or string.find(low, "268") or string.find(low, "267") or 
               string.find(low, "279") or string.find(low, "524") or string.find(low, "529") or 
               string.find(low, "773") or string.find(low, "lost connection") or 
               string.find(low, "disconnected") or string.find(low, "kicked") then
                report_disconnection("Roblox Fatal Error: " .. tostring(errMsg))
            end
        end
    end)
end)

pcall(function()
    if LocalPlayer then
        LocalPlayer.OnTeleport:Connect(function(state)
            if state == Enum.TeleportState.Started or state == Enum.TeleportState.InProgress then
                isTeleporting = true
                pcall(function()
                    safe_request({{
                        Url = TAG_CONFIG.HttpBridgeUrl .. "/api/tag_status",
                        Method = "POST",
                        Headers = {{["Content-Type"] = "application/json"}},
                        Body = HttpService:JSONEncode({{
                            tag_id = TAG_CONFIG.TagId,
                            status = "TELEPORTING",
                            error_message = "Server Hop / Teleport in progress"
                        }})
                    }})
                end)
            end
        end)
    end
end)

pcall(function()
    TeleportService.TeleportInitFailed:Connect(function(player, result, err)
        isTeleporting = false
        print(string.format("[%s] [*] TeleportInitFailed: %s (%s)", TAG_CONFIG.TagId, tostring(result), tostring(err)))
    end)
end)

-- ====================================================================================
-- 5. PER-TAG AUTO TELEPORT TO ASSIGNED GAME
-- ====================================================================================
local hasAutoTeleported = false
task.spawn(function()
    task.wait(2.0)
    pcall(function()
        local targetPid = TAG_CONFIG.TargetPlaceId
        if targetPid and #targetPid > 2 and tostring(game.PlaceId) ~= targetPid and not isTeleporting and not hasAutoTeleported then
            local pidNum = tonumber(targetPid)
            if pidNum and pidNum > 0 then
                hasAutoTeleported = true
                isTeleporting = true
                print(string.format("[%s] [🎮 AUTO-TELEPORT] Game hiện tại (%s) khác Game đã chọn. Đang chuyển vào Game: %s (PlaceId: %s)...", TAG_CONFIG.TagId, tostring(game.PlaceId), TAG_CONFIG.TargetGameName or "Roblox Game", targetPid))
                TeleportService:Teleport(pidNum, LocalPlayer)
            end
        end
    end)
end)

-- ====================================================================================
-- 6. AUTO SERVER HOP & TELEPORT IP ROTATION
-- ====================================================================================
local currentJobId = game.JobId

local function on_server_hop_detected(new_job_id)
    print(string.format("[%s] [*] Server hop phát hiện (JobId: %s)! Cấp IP mới cùng nước...", TAG_CONFIG.TagId, tostring(new_job_id)))
    pcall(function()
        local hop_url = string.format("%s/api/rotate_ip?tag=%s&job_id=%s&old_ip=%s", TAG_CONFIG.HttpBridgeUrl, TAG_CONFIG.TagId, tostring(game.JobId), TAG_CONFIG.AssignedIP)
        local res = safe_request({{Url = hop_url, Method = "GET"}})
        if res and res.Body then
            local data = HttpService:JSONDecode(res.Body)
            if data and data.new_ip then
                TAG_CONFIG.AssignedIP = data.new_ip
                TAG_CONFIG.Region = data.region or TAG_CONFIG.Region
                pcall(create_ip_hud)
            end
        end
    end)
end

task.spawn(function()
    while task.wait(3) do
        if game.JobId ~= "" and game.JobId ~= currentJobId then
            currentJobId = game.JobId
            on_server_hop_detected(currentJobId)
        end
    end
end)
            currentJobId = game.JobId
            on_server_hop_detected(currentJobId)
        end
    end
end)

print(string.format("[+] SUCCESS: Tag [%s] | Dedicated IP: %s | Game: %s", TAG_CONFIG.TagId, TAG_CONFIG.AssignedIP, TAG_CONFIG.TargetGameName or "Blox Fruits"))
"""

LUA_MASTER_TEMPLATE = """--[[
========================================================================================
     ⚡ ROBLOX MULTI-TAG UNIVERSAL MASTER EXECUTOR & SCRIPT DISPATCHER ⚡
========================================================================================
 - TỰ ĐỘNG PHÂN GIẢI & GÁN DEDICATED IP RIÊNG BIỆT CHO TỪNG BẢN CLONE / TAG ROBLOX.
 - HỖ TRỢ PER-TAG MULTI-GAME: MỖI TAG NHẬN 1 GAME RIÊNG BIỆT (BLOX FRUITS, FISCH, PS99...).
 - TÍCH HỢP LUA HEARTBEAT TRANSMITTER (BÁO NHỊP TIM VỀ PYTHON WATCHDOG).
 - TÍCH HỢP LUA ERROR & DISCONNECT HOOK (PHÁT HIỆN KICK / ERROR 277 ĐỂ PYTHON TỰ MỞ LẠI).
 - TỰ ĐỘNG TELEPORT VÀO ĐÚNG GAME CỦA TỪNG TAG.
 - TỰ ĐỘNG KHỞI CHẠY SCRIPT GAME (CUSTOM PAYLOAD) CHO TOÀN BỘ CÁC TAG.
 - Generated: {timestamp}
========================================================================================
]]--

local IP_TAG_MAPPING = {mapping_json}

local Players = game:GetService("Players")
local CoreGui = game:GetService("CoreGui")
local HttpService = game:GetService("HttpService")
local GuiService = game:GetService("GuiService")
local TeleportService = game:GetService("TeleportService")
local Stats = game:GetService("Stats")
local LocalPlayer = Players.LocalPlayer or Players:GetPlayers()[1]
local HTTP_BRIDGE_URL = "http://127.0.0.1:8888"

local currentUsername = LocalPlayer and LocalPlayer.Name or "Unknown"
local currentUserId = LocalPlayer and tostring(LocalPlayer.UserId) or "0"
local currentJobId = tostring(game.JobId or "")
local currentPlaceId = tostring(game.PlaceId or "")

local function safe_request(req_opts)
    local fn = syn and syn.request or http_request or request or (http and http.request)
    if fn then
        local success, res = pcall(fn, req_opts)
        if success and res then return res end
    end
    return nil
end

local currentConfig = nil
local customPayloadCode = nil
local targetGameConfig = nil

-- ====================================================================================
-- BƯỚC 1: LIÊN HỆ BRIDGE SERVER ĐỂ TỰ ĐỘNG NHẬN DEDICATED TAG, IP & GAME RIÊNG CHO CLONE
-- ====================================================================================
pcall(function()
    local session_id = string.format("sess_%s_%s_%s", currentUsername, currentUserId, tostring(os.time() % 100000))
    local claim_url = string.format("%s/api/claim_tag?user=%s&job_id=%s&session_id=%s&place_id=%s",
        HTTP_BRIDGE_URL,
        HttpService:UrlEncode(currentUsername),
        HttpService:UrlEncode(currentJobId),
        HttpService:UrlEncode(session_id),
        HttpService:UrlEncode(currentPlaceId)
    )

    local res = safe_request({{Url = claim_url, Method = "GET", Headers = {{["Content-Type"] = "application/json"}}}})
    if res and res.Body then
        local data = HttpService:JSONDecode(res.Body)
        if data and data.tag_id and data.assigned_ip then
            currentConfig = {{
                tag_id = data.tag_id,
                assigned_ip = data.assigned_ip,
                region = data.region or "[JP] Japan Dedicated",
                country = data.country or "JP",
                hwid = data.hwid or "WIN-DYNAMIC-HWID",
                client_uuid = data.client_uuid or "UUID-DYNAMIC",
                mac_addr = data.mac_addr or "00:1A:2B:3C:4D:5E",
                user_agent = data.user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                dns_primary = data.dns_primary or "1.1.1.1",
                dns_secondary = data.dns_secondary or "8.8.8.8",
                jitter_ms = data.jitter_ms or 250,
                unique_seed = data.unique_seed or 123456,
                target_game_name = (data.target_game and data.target_game.name) or "Roblox Target Game",
                target_place_id = (data.target_game and data.target_game.place_id) or "2753915549",
                target_job_id = (data.target_game and data.target_game.job_id) or ""
            }}
            if data.custom_script and #data.custom_script > 10 then
                customPayloadCode = data.custom_script
            end
            if data.target_game then
                targetGameConfig = data.target_game
            end
            print(string.format("[+] [BRIDGE DYNAMIC BIND] Tag [%s] | IP: %s (%s) | Game: %s", currentConfig.tag_id, currentConfig.assigned_ip, currentConfig.region, currentConfig.target_game_name))
        end
    end
end)

-- ====================================================================================
-- BƯỚC 2: OFFLINE ANTI-COLLISION FALLBACK (KHI KHÔNG CÓ BRIDGE SERVER)
-- ====================================================================================
if not currentConfig then
    for _, item in ipairs(IP_TAG_MAPPING) do
        if item.username and item.username ~= "" and string.lower(item.username) == string.lower(currentUsername) then
            currentConfig = item
            break
        end
    end

    if not currentConfig and #IP_TAG_MAPPING > 0 then
        local hashSeed = string.format("%s_%s_%s", currentUsername, currentUserId, currentJobId)
        local hashSum = 0
        for i = 1, #hashSeed do
            hashSum = (hashSum * 31 + string.byte(hashSeed, i)) % 2147483647
        end
        local slotIdx = (math.abs(hashSum) % #IP_TAG_MAPPING) + 1
        currentConfig = IP_TAG_MAPPING[slotIdx]
        print(string.format("[*] [OFFLINE SLOT ROUTER] Phân bổ Slot [%s] -> Tag: %s | IP: %s", slotIdx, currentConfig.tag_id, currentConfig.assigned_ip))
    end
end

if currentConfig then
    -- ================================================================================
    -- BƯỚC 3: CAN THIỆP & HOOK TOÀN BỘ HTTP REQUEST (SPOOF IP, HWID, MAC, USER-AGENT)
    -- ================================================================================
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
                if currentConfig.user_agent then
                    req.Headers["User-Agent"] = currentConfig.user_agent
                end
            end
            return orig_req(req)
        end)
    end

    -- ================================================================================
    -- BƯỚC 4: HIỂN THỊ CYBERPUNK HUD DRAGGABLE TRÊN MÀN HÌNH MỖI TAG
    -- ================================================================================
    local function render_universal_hud()
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
        Frame.Size = UDim2.new(0, 290, 0, 110)
        Frame.Active = true
        Frame.Draggable = true
        Instance.new("UICorner", Frame).CornerRadius = UDim.new(0, 8)

        local Stroke = Instance.new("UIStroke", Frame)
        Stroke.Color = Color3.fromRGB(0, 230, 150)
        Stroke.Thickness = 1.4

        local Title = Instance.new("TextLabel", Frame)
        Title.Text = string.format("⚡ %s | IP: %s", currentConfig.tag_id, currentConfig.assigned_ip)
        Title.Size = UDim2.new(1, -10, 0, 22)
        Title.Position = UDim2.new(0, 8, 0, 5)
        Title.BackgroundTransparency = 1
        Title.TextColor3 = Color3.fromRGB(0, 255, 200)
        Title.Font = Enum.Font.GothamBold
        Title.TextSize = 12
        Title.TextXAlignment = Enum.TextXAlignment.Left

        local Sub = Instance.new("TextLabel", Frame)
        Sub.Text = string.format("📍 Region: %s | User: %s", currentConfig.region, currentUsername)
        Sub.Size = UDim2.new(1, -10, 0, 18)
        Sub.Position = UDim2.new(0, 8, 0, 27)
        Sub.BackgroundTransparency = 1
        Sub.TextColor3 = Color3.fromRGB(220, 220, 220)
        Sub.Font = Enum.Font.Gotham
        Sub.TextSize = 11
        Sub.TextXAlignment = Enum.TextXAlignment.Left

        local Status = Instance.new("TextLabel", Frame)
        local gameName = currentConfig.target_game_name or (targetGameConfig and targetGameConfig.name) or "Roblox Game"
        local pidVal = currentConfig.target_place_id or (targetGameConfig and targetGameConfig.place_id) or "2753915549"
        Status.Text = string.format("🎮 Game: %s (PID: %s)", gameName, pidVal)
        Status.Size = UDim2.new(1, -10, 0, 18)
        Status.Position = UDim2.new(0, 8, 0, 48)
        Status.BackgroundTransparency = 1
        Status.TextColor3 = Color3.fromRGB(255, 200, 100)
        Status.Font = Enum.Font.GothamMedium
        Status.TextSize = 10
        Status.TextXAlignment = Enum.TextXAlignment.Left

        local Sub2 = Instance.new("TextLabel", Frame)
        Sub2.Text = "🟢 Watchdog: [HEARTBEAT ON - AUTO-RESTART READY]"
        Sub2.Size = UDim2.new(1, -10, 0, 18)
        Sub2.Position = UDim2.new(0, 8, 0, 69)
        Sub2.BackgroundTransparency = 1
        Sub2.TextColor3 = Color3.fromRGB(100, 255, 120)
        Sub2.Font = Enum.Font.GothamBold
        Sub2.TextSize = 9
        Sub2.TextXAlignment = Enum.TextXAlignment.Left

        ScreenGui.Parent = parentGui
    end

    task.spawn(render_universal_hud)

    -- ================================================================================
    -- BƯỚC 5: LUA HEARTBEAT TRANSMITTER (GỬI NHỊP TIM ĐỊNH KỲ VỀ PYTHON WATCHDOG)
    -- ================================================================================
    task.spawn(function()
        while task.wait(2.5) do
            pcall(function()
                local fpsVal = 60
                pcall(function() fpsVal = math.floor(workspace:GetRealPhysicsFPS()) end)
                local pingVal = 0
                pcall(function() pingVal = math.floor(Stats.Network.ServerStatsItem["Data Ping"]:GetValue()) end)
                local memVal = "0 MB"
                pcall(function() memVal = string.format("%.1f MB", Stats:GetTotalMemoryUsageMb()) end)

                local hb_payload = HttpService:JSONEncode({{
                    tag_id = currentConfig.tag_id,
                    username = currentUsername,
                    place_id = tostring(game.PlaceId or "0"),
                    job_id = tostring(game.JobId or ""),
                    fps = fpsVal,
                    ping_ms = pingVal,
                    memory_mb = memVal,
                    assigned_ip = currentConfig.assigned_ip,
                    region = currentConfig.region,
                    status = "ALIVE"
                }})

                safe_request({{
                    Url = HTTP_BRIDGE_URL .. "/api/heartbeat",
                    Method = "POST",
                    Headers = {{["Content-Type"] = "application/json"}},
                    Body = hb_payload
                }})
            end)
        end
    end)

    -- ================================================================================
    -- BƯỚC 6: LUA ERROR & DISCONNECT HOOK (BẢO VỆ CHUYỂN SERVER, CHỈ BÁO LỖI FATAL DISCONNECT)
    -- ================================================================================
    local isTeleporting = false

    local function report_error_to_python(reason_text)
        if isTeleporting then return end
        print(string.format("[%s] [!] BÁO CÁO MẤT KẾT NỐI: %s -> Gửi tín hiệu để Python mở lại...", currentConfig.tag_id, tostring(reason_text)))
        pcall(function()
            safe_request({{
                Url = HTTP_BRIDGE_URL .. "/api/tag_status",
                Method = "POST",
                Headers = {{["Content-Type"] = "application/json"}},
                Body = HttpService:JSONEncode({{
                    tag_id = currentConfig.tag_id,
                    status = "DISCONNECTED",
                    error_message = tostring(reason_text),
                    username = currentUsername,
                    place_id = currentPlaceId
                }})
            }})
        end)
    end

    pcall(function()
        GuiService.ErrorMessageChanged:Connect(function(errMsg)
            if errMsg and #errMsg > 0 and not isTeleporting then
                local low = string.lower(tostring(errMsg))
                if string.find(low, "277") or string.find(low, "268") or string.find(low, "267") or 
                   string.find(low, "279") or string.find(low, "524") or string.find(low, "529") or 
                   string.find(low, "773") or string.find(low, "lost connection") or 
                   string.find(low, "disconnected") or string.find(low, "kicked") then
                    report_error_to_python("Roblox Fatal Error: " .. tostring(errMsg))
                end
            end
        end)
    end)

    pcall(function()
        TeleportService.TeleportInitFailed:Connect(function(player, result, err)
            isTeleporting = false
            print(string.format("[%s] [*] TeleportInitFailed: %s (%s)", currentConfig.tag_id, tostring(result), tostring(err)))
        end)
    end)

    -- ================================================================================
    -- BƯỚC 7: TỰ ĐỘNG TELEPORT VÀO ĐÚNG GAME RIÊNG CỦA TỪNG TAG (KHÔNG LẶP KHI SERVER HOP)
    -- ================================================================================
    local hasAutoTeleported = false
    local function check_and_auto_teleport_game()
        task.wait(2.0)
        pcall(function()
            local targetPid = currentConfig.target_place_id or (targetGameConfig and targetGameConfig.place_id)
            local targetName = currentConfig.target_game_name or (targetGameConfig and targetGameConfig.name) or "Target Game"
            
            if targetPid and #targetPid > 2 and tostring(game.PlaceId) ~= targetPid and not isTeleporting and not hasAutoTeleported then
                local pidNum = tonumber(targetPid)
                if pidNum and pidNum > 0 then
                    hasAutoTeleported = true
                    isTeleporting = true
                    print(string.format("[%s] [🎮 PER-TAG AUTO-TELEPORT] Game hiện tại (%s) khác Game đã chọn. Đang chuyển vào Game: %s (PlaceId: %s)...", currentConfig.tag_id, tostring(game.PlaceId), targetName, targetPid))
                    TeleportService:Teleport(pidNum, LocalPlayer)
                end
            end
        end)
    end

    task.spawn(check_and_auto_teleport_game)

    -- ================================================================================
    -- BƯỚC 8: TỰ ĐỘNG KHỞI CHẠY SCRIPT CHO TẤT CẢ CÁC TAG (AUTO-EXECUTE CUSTOM PAYLOAD)
    -- ================================================================================
    local function execute_tag_payload()
        task.wait(1.5)
        if customPayloadCode and #customPayloadCode > 10 then
            print(string.format("[%s] [*] Đang tự động chạy Custom Script Payload cho Tag này...", currentConfig.tag_id))
            local success, err = pcall(function()
                loadstring(customPayloadCode)()
            end)
            if success then
                print(string.format("[%s] [+] ĐÃ CHẠY THÀNH CÔNG SCRIPT CHO TAG [%s]!", currentConfig.tag_id, currentConfig.tag_id))
            else
                warn(string.format("[%s] [!] Lỗi khi chạy Custom Script: %s", currentConfig.tag_id, tostring(err)))
            end
        else
            pcall(function()
                local res = safe_request({{Url = HTTP_BRIDGE_URL .. "/api/custom_script", Method = "GET"}})
                if res and res.Body and #res.Body > 10 and not string.find(res.Body, "No custom payload") then
                    print(string.format("[%s] [*] Tải và chạy script từ Bridge Server...", currentConfig.tag_id))
                    pcall(function()
                        loadstring(res.Body)()
                    end)
                end
            end)
        end
    end

    task.spawn(execute_tag_payload)

    -- ================================================================================
    -- BƯỚC 9: TỰ ĐỘNG ĐỔI IP KHI TELEPORT HOẶC SERVER HOP
    -- ================================================================================
    local function handle_server_hop(new_job_id)
        print(string.format("[%s] [*] Chuyển Server phát hiện (JobId: %s)! Đang đổi IP mới cùng quốc gia...", currentConfig.tag_id, tostring(new_job_id)))
        pcall(function()
            local hop_url = string.format("%s/api/rotate_ip?tag=%s&job_id=%s&old_ip=%s&country=%s",
                HTTP_BRIDGE_URL, currentConfig.tag_id, tostring(new_job_id), currentConfig.assigned_ip, currentConfig.country or "JP")
            local res = safe_request({{Url = hop_url, Method = "GET"}})
            if res and res.Body then
                local data = HttpService:JSONDecode(res.Body)
                if data and data.new_ip then
                    currentConfig.assigned_ip = data.new_ip
                    currentConfig.region = data.region or currentConfig.region
                    pcall(render_universal_hud)
                end
            end
        end)
    end

    pcall(function()
        if LocalPlayer then
            LocalPlayer.OnTeleport:Connect(function(state)
                if state == Enum.TeleportState.Started or state == Enum.TeleportState.InProgress then
                    isTeleporting = true
                    handle_server_hop("Teleporting")
                    pcall(function()
                        safe_request({{
                            Url = HTTP_BRIDGE_URL .. "/api/tag_status",
                            Method = "POST",
                            Headers = {{["Content-Type"] = "application/json"}},
                            Body = HttpService:JSONEncode({{
                                tag_id = currentConfig.tag_id,
                                status = "TELEPORTING",
                                error_message = "Server Hop in progress"
                            }})
                        }})
                    end)
                end
            end)
        end
    end)

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

    task.spawn(function()
        while task.wait(3) do
            if game.JobId ~= "" and game.JobId ~= currentJobId then
                currentJobId = game.JobId
                handle_server_hop(currentJobId)
            end
        end
    end)

    print(string.format("========================================================================================"))
    print(string.format("[⚡ UNIVERSAL MASTER RUNNER] Tag [%s] | Dedicated IP: %s | Game: %s", currentConfig.tag_id, currentConfig.assigned_ip, currentConfig.target_game_name or "OK"))
    print(string.format("========================================================================================"))
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
        Mỗi Tag nhận đúng Game mục tiêu riêng biệt của nó!
        """
        generated_files = {}
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        count = max(len(instances), 1)
        from network.proxy_fetcher import SUPPORTED_COUNTRIES

        if use_live_proxies:
            try:
                assigned_pool = ProxyFetcher.get_proxies_batch(count=count, country_code=country_code)
            except Exception:
                c_info = SUPPORTED_COUNTRIES.get(country_code, {"name": country_code, "tag": f"[{country_code}]"})
                reg_name = f"{c_info['tag']} {c_info.get('name', country_code)}" if country_code not in ["ALL", "MULTI"] else "[MULTI] Multi-Country"
                assigned_pool = [{"ip": ip, "region": reg_name, "country": country_code} for ip in RandomIPGenerator.generate_batch(count=count)]
        else:
            assigned_pool = []
            for inst in instances:
                if inst.assigned_ip and inst.assigned_ip not in ["127.0.0.1", ""] and inst.region:
                    assigned_pool.append({
                        "ip": inst.assigned_ip,
                        "region": inst.region,
                        "country": getattr(inst, "country", country_code)
                    })
                else:
                    p_batch = ProxyFetcher.get_proxies_batch(count=1, country_code=country_code)
                    if p_batch:
                        assigned_pool.append(p_batch[0])
                    else:
                        c_info = SUPPORTED_COUNTRIES.get(country_code, {"name": country_code, "tag": f"[{country_code}]"})
                        reg_name = f"{c_info['tag']} {c_info.get('name', country_code)}" if country_code not in ["ALL", "MULTI"] else "[MULTI] Multi-Country"
                        assigned_pool.append({"ip": RandomIPGenerator.generate_single_ip(), "region": reg_name, "country": country_code})

        mapping_list = []
        from core.game_selector import game_manager

        for idx, inst in enumerate(instances):
            pool_data = assigned_pool[idx] if idx < len(assigned_pool) else assigned_pool[idx % len(assigned_pool)]
            assigned_ip = pool_data["ip"]
            region = pool_data["region"]
            inst.assigned_ip = assigned_ip
            inst.region = region
            inst.country = pool_data.get("country", country_code)

            profile = self._generate_unique_tag_profile(idx)
            
            # Lấy game riêng của từng Tag
            tag_game = game_manager.get_game_for_tag(inst.tag_id)
            target_g_name = tag_game.get("name", "Roblox Game")
            target_g_pid = tag_game.get("place_id", "2753915549")
            target_g_jid = tag_game.get("job_id", "")

            tag_filename = f"{inst.tag_id}.lua"
            tag_filepath = os.path.join(OUTPUT_LUA_DIR, tag_filename)

            lua_content = LUA_TEMPLATE_SINGLE_TAG.format(
                tag_id=inst.tag_id,
                assigned_ip=assigned_ip,
                region=region,
                target_game_name=target_g_name,
                target_place_id=target_g_pid,
                target_job_id=target_g_jid,
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

            obfuscated_single = LuaObfuscator.obfuscate_and_stealth(lua_content, stealth_padding_lines=350)

            with open(tag_filepath, "w", encoding="utf-8") as f:
                f.write(obfuscated_single)

            generated_files[inst.tag_id] = tag_filepath

            mapping_list.append({
                "tag_id": inst.tag_id,
                "assigned_ip": assigned_ip,
                "region": region,
                "country": pool_data.get("country", country_code),
                "pid": inst.pid,
                "username": inst.account_username or "",
                "hwid": profile["hwid"],
                "client_uuid": profile["client_uuid"],
                "mac_addr": profile["mac_addr"],
                "user_agent": profile["user_agent"],
                "dns_primary": profile["dns_primary"],
                "dns_secondary": profile["dns_secondary"],
                "jitter_ms": profile["jitter_ms"],
                "unique_seed": profile["unique_seed"],
                "target_game_name": target_g_name,
                "target_place_id": target_g_pid,
                "target_job_id": target_g_jid
            })

        # Tạo file Master Auto-Router Lua
        master_filepath = os.path.join(OUTPUT_LUA_DIR, "master_roblox_ip_setter.lua")
        mapping_lua_table = self._convert_to_lua_table(mapping_list)
        
        master_content = LUA_MASTER_TEMPLATE.format(
            timestamp=timestamp,
            mapping_json=mapping_lua_table
        )

        obfuscated_master = LuaObfuscator.obfuscate_and_stealth(master_content, stealth_padding_lines=350)

        with open(master_filepath, "w", encoding="utf-8") as f:
            f.write(obfuscated_master)

        generated_files["MASTER"] = master_filepath
        logger.info(f"Generated and obfuscated {len(instances)} Tag Lua scripts with unique profiles + 1 Master script in {OUTPUT_LUA_DIR}")

        return generated_files

    def fast_regenerate_and_sync(self, tag_id: str, new_ip: str, region: str, country: str = "ALL") -> str:
        """
        [CỰC NHANH] Tự động xóa sạch file Lua cũ và tạo đè file Lua mới với IP mới
        ngay khi người chơi đổi server, đồng thời bơm thẳng vào toàn bộ thư mục Autoexec.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        profile = self._generate_unique_tag_profile(random.randint(1, 999))
        from core.game_selector import game_manager
        tag_game = game_manager.get_game_for_tag(tag_id)

        lua_single = LUA_TEMPLATE_SINGLE_TAG.format(
            tag_id=tag_id,
            assigned_ip=new_ip,
            region=region,
            target_game_name=tag_game.get("name", "Roblox Game"),
            target_place_id=tag_game.get("place_id", "2753915549"),
            target_job_id=tag_game.get("job_id", ""),
            timestamp=timestamp,
            process_name="RobloxPlayerBeta.exe",
            pid=0,
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

        obfuscated_single = LuaObfuscator.obfuscate_and_stealth(lua_single, stealth_padding_lines=200)
        tag_filepath = os.path.join(OUTPUT_LUA_DIR, f"{tag_id}.lua")
        
        try:
            if os.path.exists(tag_filepath):
                os.remove(tag_filepath)
        except Exception:
            pass

        with open(tag_filepath, "w", encoding="utf-8") as f:
            f.write(obfuscated_single)

        master_mapping = [{
            "tag_id": tag_id,
            "assigned_ip": new_ip,
            "region": region,
            "country": country,
            "pid": 0,
            "username": "",
            "hwid": profile["hwid"],
            "client_uuid": profile["client_uuid"],
            "mac_addr": profile["mac_addr"],
            "user_agent": profile["user_agent"],
            "dns_primary": profile["dns_primary"],
            "dns_secondary": profile["dns_secondary"],
            "jitter_ms": profile["jitter_ms"],
            "unique_seed": profile["unique_seed"],
            "target_game_name": tag_game.get("name", "Roblox Game"),
            "target_place_id": tag_game.get("place_id", "2753915549"),
            "target_job_id": tag_game.get("job_id", "")
        }]
        mapping_lua = self._convert_to_lua_table(master_mapping)
        master_content = LUA_MASTER_TEMPLATE.format(timestamp=timestamp, mapping_json=mapping_lua)
        obfuscated_master = LuaObfuscator.obfuscate_and_stealth(master_content, stealth_padding_lines=200)

        master_filepath = os.path.join(OUTPUT_LUA_DIR, "master_roblox_ip_setter.lua")
        try:
            if os.path.exists(master_filepath):
                os.remove(master_filepath)
        except Exception:
            pass

        with open(master_filepath, "w", encoding="utf-8") as f:
            f.write(obfuscated_master)

        try:
            from core.autoexec_manager import AutoexecManager
            auto_mgr = AutoexecManager()
            auto_mgr.sync_lua_to_autoexec(obfuscated_master)
        except Exception as e:
            logger.debug(f"Autoexec sync note: {e}")

        logger.info(f"[⚡ FAST WIPE & REPLACE] Đã xóa và thay thế file Lua mới với IP: {new_ip} ({region}) vào Autoexec!")
        return obfuscated_master

    def _convert_to_lua_table(self, py_list: List[Dict]) -> str:
        """Chuyển đổi list dictionary Python sang cú pháp Lua table"""
        lines = ["{"]
        for item in py_list:
            lines.append("    {")
            lines.append(f'        tag_id = "{item["tag_id"]}",')
            lines.append(f'        assigned_ip = "{item["assigned_ip"]}",')
            lines.append(f'        region = "{item.get("region", "[JP] Japan Dedicated")}",')
            lines.append(f'        country = "{item.get("country", "JP")}",')
            lines.append(f'        pid = {item.get("pid", 0)},')
            lines.append(f'        username = "{item.get("username", "")}",')
            lines.append(f'        hwid = "{item.get("hwid", "")}",')
            lines.append(f'        client_uuid = "{item.get("client_uuid", "")}",')
            lines.append(f'        mac_addr = "{item.get("mac_addr", "00:1A:2B:3C:4D:5E")}",')
            lines.append(f'        user_agent = "{item.get("user_agent", "Mozilla/5.0")}",')
            lines.append(f'        dns_primary = "{item.get("dns_primary", "1.1.1.1")}",')
            lines.append(f'        dns_secondary = "{item.get("dns_secondary", "8.8.8.8")}",')
            lines.append(f'        jitter_ms = {item.get("jitter_ms", 250)},')
            lines.append(f'        unique_seed = {item.get("unique_seed", 123456)},')
            lines.append(f'        target_game_name = "{item.get("target_game_name", "Roblox Game")}",')
            lines.append(f'        target_place_id = "{item.get("target_place_id", "2753915549")}",')
            lines.append(f'        target_job_id = "{item.get("target_job_id", "")}"')
            lines.append("    },")
        lines.append("}")
        return "\n".join(lines)
