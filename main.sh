#!/usr/bin/env bash
# ==============================================================================
# ROBLOX MULTI-TAG MASTER CONTROLLER - TERMUX TOOLKIT MAIN HUB
# ==============================================================================
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$ROOT_DIR/core/environment.sh"
source "$ROOT_DIR/core/logger.sh"
source "$ROOT_DIR/core/bootstrap.sh"
source "$ROOT_DIR/lib/ui.sh"
source "$ROOT_DIR/lib/banner.sh"
source "$ROOT_DIR/lib/menu.sh"
source "$ROOT_DIR/lib/terminal.sh"

while true; do
    clear_screen
    show_banner

    echo -e "  ${C_BOLD:-}${C_NEON_CYAN:-}[ 🚀 ROBLOX & NETWORK CONTROLLER HUB ]${C_RESET:-}"
    print_menu_option "1" "🚀" "Full Auto Pipeline 1-Chạm (Quét + Sort IP + Autoexec + Launch + Watchdog)"
    print_menu_option "2" "🎮" "Quản lý Game & Multi-Game Hub (Blox Fruits, King Legacy, PS99...)"
    print_menu_option "3" "🛡️ " "Bật / Tắt & Giám sát Crash Watchdog (Tự động Rejoin khi văng/tắt)"
    print_menu_option "4" "💉" "Bơm mã Lua vào Autoexec Executor (/sdcard/Arceus X, Delta, Codex...)"
    print_menu_option "5" "📱" "Quét thiết bị Android / UGPhone Cloud Phone (ADB Bridge)"
    print_menu_option "6" "🌐" "Bật / Tắt IPTables TPROXY Stealth (Can thiệp mạng sâu không hiện VPN)"
    print_menu_option "7" "⚡" "Thực thi Java Selection Sort IP & Đo độ trễ Google DNS"
    print_menu_option "8" "🔍" "Kiểm tra Rò rỉ DNS & Sinh file cấu hình Sing-Box / Mihomo"
    
    echo -e "\n  ${C_BOLD:-}${C_YELLOW:-}[ ⚙️ HỆ THỐNG & CÔNG CỤ TERMUX ]${C_RESET:-}"
    print_menu_option "9" "🩺" "Termux Doctor (Kiểm tra môi trường, Root, Python, Java, Storage)"
    print_menu_option "10" "🔄" "Cập nhật mã nguồn mới nhất từ GitHub (git pull)"
    print_menu_option "11" "📦" "Cài đặt lại toàn bộ Dependencies (pkg & pip requirements)"
    print_menu_option "0" "🚪" "Thoát chương trình"
    echo ""

    read -rp "$(echo -e "  ${C_YELLOW:-}${C_BOLD:-}➤ Chọn chức năng (0-11):${C_RESET:-} ")" choice

    case "$choice" in
        1)
            bash "$ROOT_DIR/tools/roblox/pipeline.sh"
            read -rp "Bấm Enter để tiếp tục..." _
            ;;
        2)
            $PYTHON_CMD -c "from controller import MasterController; mc = MasterController(); mc.select_roblox_target_game()"
            ;;
        3)
            $PYTHON_CMD -c "from controller import MasterController; mc = MasterController(); mc.manage_watchdog_supervisor()"
            ;;
        4)
            bash "$ROOT_DIR/tools/roblox/autoexec.sh"
            read -rp "Bấm Enter để tiếp tục..." _
            ;;
        5)
            bash "$ROOT_DIR/tools/android/adb-devices.sh"
            read -rp "Bấm Enter để tiếp tục..." _
            ;;
        6)
            bash "$ROOT_DIR/tools/network/tproxy-stealth.sh"
            read -rp "Bấm Enter để tiếp tục..." _
            ;;
        7)
            bash "$ROOT_DIR/tools/network/java-sort-ping.sh"
            read -rp "Bấm Enter để tiếp tục..." _
            ;;
        8)
            bash "$ROOT_DIR/tools/network/dns-leak-test.sh"
            read -rp "Bấm Enter để tiếp tục..." _
            ;;
        9)
            bash "$ROOT_DIR/tools/system/info.sh"
            read -rp "Bấm Enter để tiếp tục..." _
            ;;
        10)
            bash "$ROOT_DIR/tools/development/git-sync.sh"
            read -rp "Bấm Enter để tiếp tục..." _
            ;;
        11)
            bash "$ROOT_DIR/requirements.sh"
            read -rp "Bấm Enter để tiếp tục..." _
            ;;
        0)
            echo -e "\n${C_GREEN:-}Tạm biệt!${C_RESET:-}\n"
            exit 0
            ;;
        *)
            echo -e "${C_RED:-}Lựa chọn không hợp lệ.${C_RESET:-}"
            sleep 1
            ;;
    esac
done
