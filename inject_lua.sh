#!/data/data/com.termux/files/usr/bin/bash
# ====================================================================================
# ⚡ INJECT_LUA.SH: TIÊM FILE [online_roblox.lua] VÀO MỤC EXECUTE CỦA CLIENT EXECUTOR ⚡
# Tự động nạp vào: Delta, Arceus X, Codex, Fluxus, VegaX, Hydrogen, v.v.
# ====================================================================================

C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[1;32m"
C_CYAN="\033[1;36m"
C_YELLOW="\033[1;33m"
C_RED="\033[1;31m"
C_PURPLE="\033[1;35m"

clear 2>/dev/null || printf "\033c"

echo -e "${C_PURPLE}╔════════════════════════════════════════════════════════════════════════════╗${C_RESET}"
echo -e "${C_PURPLE}║${C_RESET}  ${C_BOLD}${C_GREEN}⚡ [ TIÊM FILE LUA: ONLINE_ROBLOX.LUA VÀO CLIENT EXECUTOR ] ⚡${C_RESET}            ${C_PURPLE}║${C_RESET}"
echo -e "${C_PURPLE}╚════════════════════════════════════════════════════════════════════════════╝${C_RESET}\n"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
PROJECT_DIR="/sdcard/Download/tool-python-roblox-ip-main"

# Tìm file nguồn online_roblox.lua
SRC_LUA=""
for candidate in "${SCRIPT_DIR}/data/generated_lua/online_roblox.lua" \
                 "${PROJECT_DIR}/data/generated_lua/online_roblox.lua" \
                 "${SCRIPT_DIR}/data/generated_lua/master_roblox_ip_setter.lua" \
                 "${PROJECT_DIR}/data/generated_lua/master_roblox_ip_setter.lua" \
                 "/sdcard/Download/online_roblox.lua"; do
    if [ -f "$candidate" ]; then
        SRC_LUA="$candidate"
        break
    fi
done

# Nếu chưa có, kích hoạt Python sinh mới
if [ -z "$SRC_LUA" ]; then
    echo -e "  ${C_YELLOW}[*] Đang dùng Python để khởi tạo file online_roblox.lua mới nhất...${C_RESET}"
    if [ -f "${PROJECT_DIR}/controller.py" ]; then
        cd "${PROJECT_DIR}" && python -c "from controller import MasterController; c=MasterController(); c.sync_system_state(c._get_combined_tag_instances())" 2>/dev/null
    elif [ -f "${SCRIPT_DIR}/controller.py" ]; then
        cd "${SCRIPT_DIR}" && python -c "from controller import MasterController; c=MasterController(); c.sync_system_state(c._get_combined_tag_instances())" 2>/dev/null
    fi
    SRC_LUA="${PROJECT_DIR}/data/generated_lua/online_roblox.lua"
fi

if [ ! -f "$SRC_LUA" ]; then
    echo -e "  ${C_RED}❌ Không tìm thấy file online_roblox.lua! Đang tạo file mặc định...${C_RESET}"
    mkdir -p "/sdcard/Download"
    cat << 'EOF' > "/sdcard/Download/online_roblox.lua"
-- [[ ONLINE ROBLOX AUTO IP & REJOIN LUA ]]
pcall(function()
    print("🟢 [ONLINE ROBLOX] Lua Script Active!")
    game:GetService("GuiService").ErrorMessageChanged:Connect(function()
        task.wait(1.5)
        game:GetService("TeleportService"):Teleport(game.PlaceId, game.Players.LocalPlayer)
    end)
end)
EOF
    SRC_LUA="/sdcard/Download/online_roblox.lua"
fi

echo -e "  ${C_CYAN}[*] File nguồn Lua:${C_RESET} ${C_YELLOW}${SRC_LUA}${C_RESET}\n"

# Danh sách tất cả các thư mục Execute / Autoexec của các Client Executor
CLIENT_TARGET_DIRS=(
    "/sdcard/Delta/Autoexec"
    "/sdcard/Delta/execute"
    "/sdcard/Delta/scripts"
    "/sdcard/Arceus X/Autoexec"
    "/sdcard/Arceus X/execute"
    "/sdcard/Arceus X/scripts"
    "/sdcard/ArceusX/Autoexec"
    "/sdcard/ArceusX/execute"
    "/sdcard/Codex/Autoexec"
    "/sdcard/Codex/execute"
    "/sdcard/Codex/scripts"
    "/sdcard/Fluxus/Autoexec"
    "/sdcard/Fluxus/execute"
    "/sdcard/VegaX/Autoexec"
    "/sdcard/VegaX/execute"
    "/sdcard/Hydrogen/Autoexec"
    "/storage/emulated/0/Delta/Autoexec"
    "/storage/emulated/0/Delta/execute"
    "/storage/emulated/0/Arceus X/Autoexec"
    "/storage/emulated/0/Arceus X/execute"
    "/storage/emulated/0/Codex/Autoexec"
    "/storage/emulated/0/Codex/execute"
    "/storage/emulated/0/Fluxus/Autoexec"
    "/storage/emulated/999/Delta/Autoexec"
    "/storage/emulated/999/Arceus X/Autoexec"
    "/storage/emulated/10/Delta/Autoexec"
    "/storage/emulated/10/Arceus X/Autoexec"
    "/sdcard/Download/RobloxIPTool"
)

SUCCESS_COUNT=0

for target_dir in "${CLIENT_TARGET_DIRS[@]}"; do
    mkdir -p "${target_dir}" 2>/dev/null || true
    if [ -d "${target_dir}" ]; then
        cp -f "${SRC_LUA}" "${target_dir}/online_roblox.lua" 2>/dev/null && \
        cp -f "${SRC_LUA}" "${target_dir}/online roblox.lua" 2>/dev/null && \
        cp -f "${SRC_LUA}" "${target_dir}/roblox_auto_ip_setter.lua" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e "  ${C_GREEN}✔ Đã tiêm vào:${C_RESET} ${target_dir}/online_roblox.lua"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        fi
    fi
done

# Lưu thêm trực tiếp ra /sdcard/Download
cp -f "${SRC_LUA}" "/sdcard/Download/online_roblox.lua" 2>/dev/null || true

echo -e "\n  ${C_GREEN}${C_BOLD}✓ ĐÃ TIÊM THÀNH CÔNG VÀO ${SUCCESS_COUNT} THƯ MỤC CLIENT EXECUTE & AUTOEXEC!${C_RESET}\n"
