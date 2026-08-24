#!/usr/bin/env bash
# ==============================================================================
# ROBLOX MULTI-TAG NETWORK CONTROLLER - TERMUX FAST SETUP & LAUNCHER
# ==============================================================================
# Repository: https://github.com/hyuttgg/tool-python-roblox-ip
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/config.sh" ]; then
    source "${SCRIPT_DIR}/config.sh"
else
    COLOR_GREEN='\033[0;32m'
    COLOR_YELLOW='\033[1;33m'
    COLOR_CYAN='\033[0;36m'
    COLOR_RESET='\033[0m'
    log_info() { echo -e "${COLOR_CYAN}[INFO]${COLOR_RESET} $*"; }
    log_success() { echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} $*"; }
    log_step() { echo -e "${COLOR_YELLOW}[$1/$2] [*] $3${COLOR_RESET}"; }
    print_banner() { echo -e "${COLOR_GREEN}=== ROBLOX MULTI-TAG CONTROLLER ===${COLOR_RESET}"; }
fi

clear
print_banner "TERMUX AUTO-SETUP & LAUNCHER"

# --- Bước 1: Quyền bộ nhớ & Cấu hình an toàn Git ---
log_step 1 4 "Cấp quyền bộ nhớ và cấu hình an toàn..."
if command -v termux-setup-storage >/dev/null 2>&1; then
    if [ ! -d "$HOME/storage" ]; then
        termux-setup-storage 2>/dev/null || true
        sleep 1
    fi
fi

git config --global --add safe.directory "*" 2>/dev/null || true
git config --global core.filemode false 2>/dev/null || true

# --- Bước 2: Tối ưu Repository & Cài đặt gói hệ thống ---
log_step 2 4 "Cập nhật Termux packages & cài đặt công cụ cần thiết..."
if [ -n "$PREFIX" ] && [ -d "$PREFIX/etc/apt" ]; then
    mkdir -p "$PREFIX/etc/apt/sources.list.d"
    # Giữ mirror chính thức & bổ sung backup mirror
    if [ ! -s "$PREFIX/etc/apt/sources.list" ]; then
        echo "deb https://packages.termux.dev/apt/termux-main stable main" > "$PREFIX/etc/apt/sources.list"
    fi
fi

pkg update -y -o Dpkg::Options::="--force-confold" 2>/dev/null || true
pkg install -y git python python-pip sqlite iproute2 dnsutils curl wget tsu openssl openjdk-17 clang make 2>/dev/null || true

# --- Bước 3: Cài đặt thư viện Python & Biên dịch Native C++ Hardware Engine ---
log_step 3 4 "Cài đặt thư viện Python & Biên dịch Native C++ Probe..."
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
if [ -f "${PROJECT_ROOT}/requirements.txt" ]; then
    python -m pip install -r "${PROJECT_ROOT}/requirements.txt" 2>/dev/null || \
    pip install -r "${PROJECT_ROOT}/requirements.txt" 2>/dev/null || true
else
    pip install requests psutil prettytable rich pytz 2>/dev/null || true
fi

# Biên dịch Native C++ Shared Library cho Android
mkdir -p "${PROJECT_ROOT}/data/native_bin"
if command -v clang++ >/dev/null 2>&1 && [ -f "${PROJECT_ROOT}/core/native_hardware_probe.cpp" ]; then
    clang++ -O3 -shared -fPIC -o "${PROJECT_ROOT}/data/native_bin/libhardware_probe.so" "${PROJECT_ROOT}/core/native_hardware_probe.cpp" 2>/dev/null || true
fi

# --- Bước 4: Cấp quyền thực thi & Tạo lệnh gọi nhanh roblox-ip ---
log_step 4 4 "Cấp quyền và thiết lập phím tắt lệnh..."
chmod +x "${PROJECT_ROOT}"/*.py 2>/dev/null || true
chmod +x "${PROJECT_ROOT}"/*.sh 2>/dev/null || true
chmod +x "${PROJECT_ROOT}"/shell/*.sh 2>/dev/null || true
chmod +x "${PROJECT_ROOT}/SetupRobloxIP" 2>/dev/null || true

if [ -d "/data/data/com.termux/files/usr/bin" ]; then
    cat << 'EOF' > /data/data/com.termux/files/usr/bin/roblox-ip
#!/data/data/com.termux/files/usr/bin/bash
TARGET_DIR=""
candidates=(
    "/sdcard/Download/tool-python-roblox-ip"
    "/storage/emulated/0/Download/tool-python-roblox-ip"
    "$HOME/tool-python-roblox-ip"
    "/data/data/com.termux/files/home/tool-python-roblox-ip"
)
for dir in "${candidates[@]}"; do
    if [ -f "${dir}/controller.py" ]; then
        TARGET_DIR="${dir}"
        break
    fi
done

if [ -n "$TARGET_DIR" ]; then
    cd "$TARGET_DIR" && bash run.sh "$@"
else
    echo "[-] Khong tim thay thu muc tool-python-roblox-ip!"
fi
EOF
    chmod +x /data/data/com.termux/files/usr/bin/roblox-ip 2>/dev/null || true
    log_success "Đã tạo lệnh tắt: Gõ 'roblox-ip' ở bất kỳ đâu trên Termux để mở tool!"
fi

echo ""
log_success "Cài đặt thành công! Đang khởi động Master Controller..."
sleep 1

cd "${PROJECT_ROOT}"
if [ -f "pyobfuscate_com.py" ]; then
    python pyobfuscate_com.py
else
    python controller.py
fi
