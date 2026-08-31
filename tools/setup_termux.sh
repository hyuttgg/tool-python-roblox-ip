#!/data/data/com.termux/files/usr/bin/bash
# ====================================================================================
# ⚡ ROBLOX AUTO-REJOIN TERMUX INSTALLER (SETUP SCRIPT) ⚡
# Script tự động cài đặt thư viện vào Termux và thiết lập tool chạy tại /sdcard/Download
# Tương thích: Android 8 - 15, Root (su), Non-Root, UGPhone, Cloud Phone, Giả lập
# ====================================================================================

# Cấu hình màu sắc
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[1;32m"
C_CYAN="\033[1;36m"
C_YELLOW="\033[1;33m"
C_RED="\033[1;31m"
C_PURPLE="\033[1;35m"
C_GRAY="\033[0;90m"

clear 2>/dev/null || printf "\033c"

echo -e "${C_PURPLE}╔════════════════════════════════════════════════════════════════════════════╗${C_RESET}"
echo -e "${C_PURPLE}║${C_RESET}  ${C_BOLD}${C_CYAN}⚡ [ TRÌNH CÀI ĐẶT ROBLOX AUTO-REJOIN TOOL TRÊN TERMUX ] ⚡${C_RESET}             ${C_PURPLE}║${C_RESET}"
echo -e "${C_PURPLE}║${C_RESET}  ${C_GRAY}Thư mục cài đặt tool:${C_RESET} ${C_YELLOW}/sdcard/Download/RobloxRejoinTool${C_RESET}                       ${C_PURPLE}║${C_RESET}"
echo -e "${C_PURPLE}╚════════════════════════════════════════════════════════════════════════════╝${C_RESET}"
echo ""

# 1. Cấp quyền truy cập bộ nhớ lưu trữ (/sdcard)
echo -e "  ${C_CYAN}[1/5] Kiểm tra và cấp quyền bộ nhớ Android (Storage Permission)...${C_RESET}"
if [ ! -d "$HOME/storage/shared" ]; then
    echo -e "  ${C_YELLOW}➔ Vui lòng nhấn [ CHO PHÉP / ALLOW ] trên màn hình điện thoại khi pop-up hiện lên!${C_RESET}"
    termux-setup-storage 2>/dev/null
    sleep 2
fi

# 2. Cập nhật Repository & Cài đặt gói hệ thống Termux
echo -e "\n  ${C_CYAN}[2/5] Đang cập nhật Package & cài đặt các công cụ cần thiết (Python, Git, Curl, JQ, TSU)...${C_RESET}"
export DEBIAN_FRONTEND=noninteractive

# Kiểm tra mirror Termux và tự động chọn mirror chính thức nếu cần
pkg update -y 2>/dev/null || apt-get update -y 2>/dev/null || {
    echo -e "  ${C_YELLOW}➔ Đang kết nối tới Mirror chính thức của Termux...${C_RESET}"
    apt-get update --fix-missing -y 2>/dev/null || true
}

# Cài đặt triệt để gói python và git
pkg install -y python python-pip git curl jq tsu proot procps sqlite 2>/dev/null || \
apt-get install -y python python3 python3-pip git curl jq tsu proot procps sqlite3 2>/dev/null || \
apt install -y python python3 git curl jq 2>/dev/null || true


# Tự động phát hiện và đảm bảo phím tắt python
PYTHON_BIN=""
if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif [ -x "/data/data/com.termux/files/usr/bin/python" ]; then
    PYTHON_BIN="/data/data/com.termux/files/usr/bin/python"
elif [ -x "/data/data/com.termux/files/usr/bin/python3" ]; then
    PYTHON_BIN="/data/data/com.termux/files/usr/bin/python3"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo -e "  ${C_YELLOW}➔ Đang thử nạp lại gói Python...${C_RESET}"
    pkg install -y python 2>/dev/null || apt-get install -y python3 2>/dev/null || true
    if command -v python3 >/dev/null 2>&1 && [ ! -x "/data/data/com.termux/files/usr/bin/python" ]; then
        ln -sf "$(which python3)" /data/data/com.termux/files/usr/bin/python 2>/dev/null || true
    fi
    PYTHON_BIN="python"
fi

# 3. Cài đặt các thư viện Python
echo -e "\n  ${C_CYAN}[3/5] Đang cài đặt thư viện Python (requests, psutil, urllib3)...${C_RESET}"
$PYTHON_BIN -m pip install --upgrade pip --no-warn-script-location 2>/dev/null || true
$PYTHON_BIN -m pip install requests psutil urllib3 --no-warn-script-location 2>/dev/null || pip install requests psutil urllib3 2>/dev/null || true


# 4. Tạo thư mục làm việc tại /sdcard/Download/RobloxRejoinTool
TARGET_DIR="/sdcard/Download/RobloxRejoinTool"
echo -e "\n  ${C_CYAN}[4/5] Đang thiết lập thư mục tool tại: ${C_YELLOW}${TARGET_DIR}${C_RESET}..."
mkdir -p "${TARGET_DIR}"
mkdir -p "${TARGET_DIR}/core"
mkdir -p "${TARGET_DIR}/config"
mkdir -p "${TARGET_DIR}/data"
mkdir -p "${TARGET_DIR}/tools"

# Sao chép mã nguồn sang thư mục Download nếu đang chạy từ source hiện tại
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd)"
if [ -f "${CURRENT_DIR}/controller.py" ]; then
    echo -e "  ${C_GRAY}➔ Đang đồng bộ mã nguồn vào /sdcard/Download...${C_RESET}"
    cp -rf "${CURRENT_DIR}/"* "${TARGET_DIR}/" 2>/dev/null
fi

# Tạo file chạy nhanh tại /sdcard/Download/RobloxRejoinTool/start.sh
cat << 'EOF' > "${TARGET_DIR}/start.sh"
#!/data/data/com.termux/files/usr/bin/bash
export PATH="/data/data/com.termux/files/usr/bin:$PATH"
export TERM=xterm-256color

TERMUX_PYTHON="/data/data/com.termux/files/usr/bin/python"
if [ ! -x "$TERMUX_PYTHON" ]; then
    TERMUX_PYTHON="python"
fi

for TARGET_DIR in "/sdcard/Download/RobloxRejoinTool" "/sdcard/Download/tool-python-roblox-ip-main" "$HOME/tool-python-roblox-ip"; do
    if [ -f "$TARGET_DIR/controller.py" ]; then
        cd "$TARGET_DIR" 2>/dev/null
        break
    fi
done

if command -v su >/dev/null 2>&1; then
    su -c "export PATH=/data/data/com.termux/files/usr/bin:\$PATH && cd \"$(pwd)\" && $TERMUX_PYTHON controller.py"
else
    $TERMUX_PYTHON controller.py
fi
EOF
chmod +x "${TARGET_DIR}/start.sh" 2>/dev/null

# Tạo shortcut lệnh nhanh 'roblox-rejoin', 'rejoin', 'run' trong Termux
for LAUNCHER_PATH in "/data/data/com.termux/files/usr/bin/roblox-rejoin" "/data/data/com.termux/files/usr/bin/rejoin" "/data/data/com.termux/files/usr/bin/run"; do
cat << 'EOF' > "$LAUNCHER_PATH"
#!/data/data/com.termux/files/usr/bin/bash
export PATH="/data/data/com.termux/files/usr/bin:$PATH"
export TERM=xterm-256color

TERMUX_PYTHON="/data/data/com.termux/files/usr/bin/python"
if [ ! -x "$TERMUX_PYTHON" ]; then
    TERMUX_PYTHON="python"
fi

for TARGET_DIR in "/sdcard/Download/RobloxRejoinTool" "/sdcard/Download/tool-python-roblox-ip-main" "$HOME/tool-python-roblox-ip"; do
    if [ -f "$TARGET_DIR/controller.py" ]; then
        cd "$TARGET_DIR" 2>/dev/null
        break
    fi
done

if command -v su >/dev/null 2>&1; then
    su -c "export PATH=/data/data/com.termux/files/usr/bin:\$PATH && cd \"$(pwd)\" && /data/data/com.termux/files/usr/bin/python controller.py" 2>/dev/null || $TERMUX_PYTHON controller.py
else
    $TERMUX_PYTHON controller.py
fi
EOF
chmod +x "$LAUNCHER_PATH" 2>/dev/null
done



# 5. Hoàn tất cài đặt
echo -e "\n  ${C_GREEN}${C_BOLD}[5/5] CÀI ĐẶT HOÀN TẤT 100%!${C_RESET}\n"
echo -e "${C_PURPLE}════════════════════════════════════════════════════════════════════════════${C_RESET}"
echo -e "  ${C_BOLD}CÁCH CHẠY TOOL TRÊN TERMUX:${C_RESET}"
echo -e "  ${C_YELLOW}Cách 1 (Gõ lệnh nhanh bất kỳ đâu):${C_RESET}"
echo -e "    ${C_GREEN}run${C_RESET}  hoặc  ${C_GREEN}rejoin${C_RESET}\n"
echo -e "  ${C_YELLOW}Cách 2 (Chạy trực tiếp):${C_RESET}"
echo -e "    ${C_GREEN}cd /sdcard/Download/RobloxRejoinTool && python controller.py${C_RESET}"
echo -e "${C_PURPLE}════════════════════════════════════════════════════════════════════════════${C_RESET}\n"

# Khởi chạy trực tiếp Master Controller
cd "${TARGET_DIR}" 2>/dev/null || true

RUN_PY="python"
if command -v python >/dev/null 2>&1; then
    RUN_PY="python"
elif command -v python3 >/dev/null 2>&1; then
    RUN_PY="python3"
elif [ -x "/data/data/com.termux/files/usr/bin/python" ]; then
    RUN_PY="/data/data/com.termux/files/usr/bin/python"
elif [ -x "/data/data/com.termux/files/usr/bin/python3" ]; then
    RUN_PY="/data/data/com.termux/files/usr/bin/python3"
fi

if command -v su >/dev/null 2>&1; then
    su -c "export PATH=/data/data/com.termux/files/usr/bin:\$PATH && cd \"${TARGET_DIR}\" && $RUN_PY controller.py" 2>/dev/null || $RUN_PY controller.py
else
    $RUN_PY controller.py
fi


