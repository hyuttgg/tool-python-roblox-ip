#!/data/data/com.termux/files/usr/bin/bash
# ====================================================================================
# ⚡ INSTALL_TOOL.SH: TRÌNH CÀI ĐẶT TỰ ĐỘNG GÓI THƯ VIỆN & CORE CHO TERMUX ANDROID ⚡
# Cài đặt toàn bộ: Python, Pip, Git, Curl, JQ, TSU, Procps, SQLite và thư viện Python
# ====================================================================================

C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[1;32m"
C_CYAN="\033[1;36m"
C_YELLOW="\033[1;33m"
C_RED="\033[1;31m"
C_PURPLE="\033[1;35m"
C_GRAY="\033[0;90m"

clear 2>/dev/null || printf "\033c"

echo -e "${C_CYAN}╔════════════════════════════════════════════════════════════════════════════╗${C_RESET}"
echo -e "${C_CYAN}║${C_RESET}  ${C_BOLD}${C_GREEN}⚡ [ INSTALL TOOL: CÀI ĐẶT GÓI THƯ VIỆN & CORE CHO TERMUX ] ⚡${C_RESET}             ${C_CYAN}║${C_RESET}"
echo -e "${C_CYAN}║${C_RESET}  ${C_GRAY}Vị trí bộ não:${C_RESET} ${C_YELLOW}/sdcard/Download/tool-python-roblox-ip-main/controller.py${C_RESET}     ${C_CYAN}║${C_RESET}"
echo -e "${C_CYAN}╚════════════════════════════════════════════════════════════════════════════╝${C_RESET}"
echo ""

# 1. Cấp quyền truy cập bộ nhớ lưu trữ
echo -e "  ${C_CYAN}[1/4] Đang thiết lập quyền bộ nhớ lưu trữ (/sdcard)...${C_RESET}"
if [ ! -d "$HOME/storage/shared" ]; then
    echo -e "  ${C_YELLOW}➔ Nếu có thông báo hiện lên trên màn hình, hãy chọn [ CHO PHÉP / ALLOW ]!${C_RESET}"
    termux-setup-storage 2>/dev/null
    sleep 2
fi

# Cấu hình Git an toàn
git config --global --add safe.directory "*" 2>/dev/null || true
git config --global core.filemode false 2>/dev/null || true

# 2. Cập nhật hệ thống & Cài đặt toàn bộ gói cần thiết trên Termux
echo -e "\n  ${C_CYAN}[2/4] Đang cài đặt các gói hệ thống (Python, Git, Curl, JQ, TSU, Procps, SQLite)...${C_RESET}"
if command -v pkg >/dev/null 2>&1; then
    yes | pkg update -o Dpkg::Options::="--force-confold" 2>/dev/null || true
    yes | pkg upgrade -y -o Dpkg::Options::="--force-confold" 2>/dev/null || true
    pkg install -y python python-pip git curl jq tsu proot procps sqlite iproute2 dnsutils wget 2>/dev/null || apt update -y && apt install -y python python3-pip git curl jq
elif command -v apt-get >/dev/null 2>&1; then
    apt-get update -y 2>/dev/null || true
    apt-get install -y python3 python3-pip git curl jq sqlite3 iproute2 dnsutils wget 2>/dev/null || true
fi

# 3. Cài đặt các thư viện Python chuyên dụng
echo -e "\n  ${C_CYAN}[3/4] Đang cài đặt thư viện Python (requests, psutil, urllib3, rich, prettytable, pytz)...${C_RESET}"
python -m pip install --upgrade pip --no-warn-script-location 2>/dev/null || true
python -m pip install requests psutil urllib3 rich prettytable pytz --no-warn-script-location 2>/dev/null || pip install requests psutil urllib3 rich prettytable pytz 2>/dev/null || true

# 4. Thiết lập thư mục và đồng bộ toàn bộ dự án vào /sdcard/Download
DOWNLOAD_DIR="/sdcard/Download"
PROJECT_DIR="${DOWNLOAD_DIR}/tool-python-roblox-ip-main"
mkdir -p "${DOWNLOAD_DIR}" 2>/dev/null || true
mkdir -p "${PROJECT_DIR}" 2>/dev/null || true

echo -e "\n  ${C_CYAN}[4/4] Đang đồng bộ mã nguồn vào ${C_YELLOW}${PROJECT_DIR}${C_RESET}..."

# Nếu có mã nguồn cục bộ, sao chép sang
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
if [ -f "${SCRIPT_DIR}/controller.py" ]; then
    cp -rf "${SCRIPT_DIR}/"* "${PROJECT_DIR}/" 2>/dev/null
elif [ ! -f "${PROJECT_DIR}/controller.py" ]; then
    # Tải mới từ GitHub nếu chạy độc lập
    git clone --depth=1 https://github.com/hyuttgg/tool-python-roblox-ip.git "${PROJECT_DIR}" 2>/dev/null || true
    if [ ! -f "${PROJECT_DIR}/controller.py" ]; then
        curl -sL https://github.com/hyuttgg/tool-python-roblox-ip/archive/refs/heads/main.tar.gz | tar -xz -C "${PROJECT_DIR}" --strip-components=1 2>/dev/null || true
    fi
fi

# Tạo sẵn thư mục Execute / Autoexec trên Android cho tất cả Executor
echo -e "  ${C_CYAN}[*] Đang tạo sẵn thư mục Execute & Autoexec cho Client Executor...${C_RESET}"
for exec_dir in "/sdcard/Delta/Autoexec" "/sdcard/Delta/execute" "/sdcard/Delta/scripts" \
                "/sdcard/Arceus X/Autoexec" "/sdcard/Arceus X/execute" "/sdcard/Arceus X/scripts" \
                "/sdcard/Codex/Autoexec" "/sdcard/Codex/execute" "/sdcard/Codex/scripts" \
                "/sdcard/Fluxus/Autoexec" "/sdcard/Fluxus/execute" \
                "/sdcard/VegaX/Autoexec" "/sdcard/VegaX/execute" \
                "/sdcard/Hydrogen/Autoexec"; do
    mkdir -p "${exec_dir}" 2>/dev/null || true
done

echo -e "\n  ${C_GREEN}${C_BOLD}✓ CÀI ĐẶT HOÀN TẤT THÀNH CÔNG TOÀN BỘ GÓI VÀ BỘ NÃO CONTROLLER!${C_RESET}\n"
echo -e "${C_PURPLE}════════════════════════════════════════════════════════════════════════════${C_RESET}"
echo -e "  ${C_BOLD}${C_YELLOW}🚀 LỆNH DUY NHẤT ĐỂ CHẠY BỘ NÃO ĐIỀU KHIỂN (CONTROLLER.PY):${C_RESET}"
echo -e "  ${C_GREEN}cd /sdcard/Download/tool-python-roblox-ip-main && python controller.py${C_RESET}"
echo -e "${C_PURPLE}════════════════════════════════════════════════════════════════════════════${C_RESET}\n"
