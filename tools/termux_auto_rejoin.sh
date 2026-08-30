#!/data/data/com.termux/files/usr/bin/bash
# ====================================================================================
# ⚡ ROBLOX ANDROID / TERMUX AUTO-REJOIN SENTINEL (SHELL + LOGCAT + INTENT) ⚡
# Dựa trên kiến trúc Logcat Realtime & Intent Protocol từ DroidBlox-kt
# Tự động giám sát, bắt lỗi Disconnect (Time to disconnect replication data) và Rejoin
# ====================================================================================

# Cấu hình màu sắc ANSI
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[1;32m"
C_CYAN="\033[1;36m"
C_YELLOW="\033[1;33m"
C_RED="\033[1;31m"
C_PURPLE="\033[1;35m"
C_GRAY="\033[0;90m"

# Thư mục gốc và cấu hình
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROBLOX_PKG="com.roblox.client"
DEFAULT_PLACE_ID="2753915549" # Mặc định: Blox Fruits
PLACE_ID="${1:-$DEFAULT_PLACE_ID}"
JOB_ID="${2:-}"
USER_ID_SLOT="${3:-0}"
CHECK_INTERVAL=3
RETRY_COOLDOWN=15
MAX_CONSECUTIVE_RETRIES=3

RESTART_COUNT=0
CONSECUTIVE_FAILS=0
LAST_REJOIN_EPOCH=0

clear_hud() {
    clear 2>/dev/null || printf "\033c"
}

print_banner() {
    echo -e "${C_PURPLE}╔════════════════════════════════════════════════════════════════════════════╗${C_RESET}"
    echo -e "${C_PURPLE}║${C_RESET}  ${C_BOLD}${C_CYAN}⚡ [ ROBLOX ANDROID / TERMUX AUTO-REJOIN SENTINEL ] ⚡${C_RESET}                  ${C_PURPLE}║${C_RESET}"
    echo -e "${C_PURPLE}║${C_RESET}  ${C_GRAY}Engine:${C_RESET} ${C_YELLOW}DroidBlox-kt Protocol${C_RESET} | ${C_GRAY}Place ID:${C_RESET} ${C_YELLOW}${PLACE_ID}${C_RESET} | ${C_GRAY}User Slot:${C_RESET} ${C_GREEN}--user ${USER_ID_SLOT}${C_RESET}        ${C_PURPLE}║${C_RESET}"
    echo -e "${C_PURPLE}╚════════════════════════════════════════════════════════════════════════════╝${C_RESET}"
}

# 1. Kiểm tra môi trường Termux / Android
detect_environment() {
    IS_ROOT=false
    if command -v su >/dev/null 2>&1; then
        IS_ROOT=true
    fi

    HAS_AM=false
    if command -v am >/dev/null 2>&1 || [ -f "/system/bin/am" ]; then
        HAS_AM=true
    fi
}

# 2. Kiểm tra tiến trình Roblox PID
is_roblox_running() {
    if command -v pidof >/dev/null 2>&1; then
        PID=$(pidof "$ROBLOX_PKG" 2>/dev/null)
        if [ -n "$PID" ]; then
            echo "$PID"
            return 0
        fi
    fi

    if command -v pgrep >/dev/null 2>&1; then
        PID=$(pgrep -f "$ROBLOX_PKG" 2>/dev/null | head -n 1)
        if [ -n "$PID" ]; then
            echo "$PID"
            return 0
        fi
    fi

    PID=$(ps -ef 2>/dev/null | grep "$ROBLOX_PKG" | grep -v "grep" | awk '{print $2}' | head -n 1)
    if [ -n "$PID" ]; then
        echo "$PID"
        return 0
    fi

    echo ""
    return 1
}

# 3. Kích hoạt mở lại Roblox qua Android Intent chuẩn DroidBlox
launch_roblox_intent() {
    local target_url="roblox://experiences/start?placeId=${PLACE_ID}"
    if [ -n "$JOB_ID" ]; then
        target_url="roblox://experiences/start?placeId=${PLACE_ID}&gameInstanceId=${JOB_ID}"
    fi

    echo -e "  ${C_CYAN}[*] Đang gửi Android Intent mở Roblox... (Place ID: ${PLACE_ID})${C_RESET}"

    local user_args=()
    if [ "$USER_ID_SLOT" != "0" ] && [ -n "$USER_ID_SLOT" ]; then
        user_args=("--user" "$USER_ID_SLOT")
    fi

    # Intent 1: Component ActivityProtocolLaunch (chuẩn DroidBlox)
    if [ "$HAS_AM" = true ]; then
        am start "${user_args[@]}" -n "${ROBLOX_PKG}/com.roblox.client.ActivityProtocolLaunch" -a android.intent.action.VIEW -d "$target_url" >/dev/null 2>&1
        sleep 2
        am start "${user_args[@]}" -a android.intent.action.VIEW -d "$target_url" >/dev/null 2>&1
    elif [ "$IS_ROOT" = true ]; then
        su -c "am start -n ${ROBLOX_PKG}/com.roblox.client.ActivityProtocolLaunch -a android.intent.action.VIEW -d '$target_url'" >/dev/null 2>&1
    fi
}

# 4. Kích hoạt Rejoin có bảo vệ Circuit Breaker
trigger_rejoin() {
    local reason="$1"
    local now_epoch=$(date +%s)

    # Chống trigger quá nhanh (< 5 giây)
    if [ $((now_epoch - LAST_REJOIN_EPOCH)) -lt 5 ]; then
        return
    fi
    LAST_REJOIN_EPOCH=$now_epoch

    if [ "$CONSECUTIVE_FAILS" -ge "$MAX_CONSECUTIVE_RETRIES" ]; then
        echo -e "  ${C_YELLOW}⚠️ [CIRCUIT BREAKER] Đã Rejoin thất bại ${CONSECUTIVE_FAILS} lần liên tiếp. Tạm dừng 45s để tránh nghẽn CPU...${C_RESET}"
        sleep 45
        CONSECUTIVE_FAILS=0
    else
        CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1))
        RESTART_COUNT=$((RESTART_COUNT + 1))
        echo -e "  ${C_PURPLE}🚀 [AUTO-REJOIN] Lý do: ${reason} (Lần #${RESTART_COUNT}, Thử: ${CONSECUTIVE_FAILS}/${MAX_CONSECUTIVE_RETRIES})${C_RESET}"
        
        # Đóng tiến trình cũ nếu còn đơ
        if [ "$HAS_AM" = true ]; then
            am force-stop "$ROBLOX_PKG" >/dev/null 2>&1
        fi

        launch_roblox_intent
        
        echo -e "  ${C_GRAY}⏳ Đang chờ game khởi động và nạp bản đồ (${RETRY_COOLDOWN}s cooldown)...${C_RESET}"
        sleep "$RETRY_COOLDOWN"
    fi
}

# 5. Vòng lặp giám sát thời gian thực
main_supervision_loop() {
    detect_environment
    clear_hud
    print_banner

    echo -e "\n  ${C_GREEN}[✓] Khởi động Watchdog Sentinel thành công trên Termux!${C_RESET}"
    echo -e "  ${C_GRAY}Nhấn [ Ctrl + C ] để dừng và thoát công cụ.${C_RESET}\n"

    # Chạy nền logcat parser nếu có quyền đọc log
    if command -v logcat >/dev/null 2>&1; then
        (
            logcat -c 2>/dev/null
            logcat -v raw -s Roblox:* FLog:* 2>/dev/null | while read -r line; do
                # Bắt Job ID và Place ID
                if [[ "$line" =~ \!\ Joining\ game\ \'([0-9a-f\-]{36})\'\ place\ ([0-9]+) ]]; then
                    JOB_ID="${BASH_REMATCH[1]}"
                    PLACE_ID="${BASH_REMATCH[2]}"
                fi
                # Bắt sự kiện disconnect của DroidBlox
                if [[ "$line" == *"Time to disconnect replication data"* ]]; then
                    trigger_rejoin "Mất kết nối (Logcat Disconnect Event)"
                fi
            done
        ) &
        LOGCAT_BG_PID=$!
    fi

    while true; do
        NOW_TIME=$(date +"%H:%M:%S")
        RBX_PID=$(is_roblox_running)

        if [ -n "$RBX_PID" ]; then
            CONSECUTIVE_FAILS=0
            echo -e "  [${NOW_TIME}] ${C_GREEN}🟢 ONLINE${C_RESET} | Roblox Client đang chạy (PID: ${C_YELLOW}${RBX_PID}${C_RESET}) | Rejoin: ${RESTART_COUNT} lần"
        else
            echo -e "  [${NOW_TIME}] ${C_RED}⚪ OFFLINE / CRASH${C_RESET} | Phát hiện Roblox bị tắt / văng game!"
            trigger_rejoin "Tiến trình biến mất (PID = 0)"
        fi

        sleep "$CHECK_INTERVAL"
    done
}

# Xử lý tín hiệu ngắt an toàn
trap '
    if [ -n "$LOGCAT_BG_PID" ]; then
        kill "$LOGCAT_BG_PID" 2>/dev/null
    fi
    echo -e "\n\n  ${C_YELLOW}[!] Đã dừng Roblox Termux Sentinel an toàn. Tạm biệt!${C_RESET}\n"
    exit 0
' SIGINT SIGTERM

main_supervision_loop
