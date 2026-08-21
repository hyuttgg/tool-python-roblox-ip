#!/usr/bin/env bash
# ==============================================================================
# ROBLOX MULTI-TAG NETWORK CONTROLLER - UNIVERSAL DEPENDENCY INSTALLER
# ==============================================================================
# Repository: https://github.com/hyuttgg/tool-python-roblox-ip
# Supports: Termux (Android), Debian/Ubuntu, Arch Linux, Fedora, Alpine
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/config.sh" ]; then
    source "${SCRIPT_DIR}/config.sh"
else
    # Minimal fallback
    COLOR_RED='\033[0;31m'
    COLOR_GREEN='\033[0;32m'
    COLOR_YELLOW='\033[1;33m'
    COLOR_CYAN='\033[0;36m'
    COLOR_RESET='\033[0m'
    log_info() { echo -e "${COLOR_CYAN}[INFO]${COLOR_RESET} $*"; }
    log_success() { echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} $*"; }
    log_warn() { echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $*"; }
    log_error() { echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $*" >&2; }
    log_step() { echo -e "${COLOR_YELLOW}[$1/$2] [*] $3${COLOR_RESET}"; }
fi

print_banner "INSTALLING DEPENDENCIES & ENVIRONMENT"

# 1. Package Manager Detection & Installation
log_step 1 3 "Detecting Package Manager & Installing System Packages..."

if command -v pkg >/dev/null 2>&1; then
    log_info "Termux environment detected (pkg)"
    pkg update -y -o Dpkg::Options::="--force-confold" || true
    pkg install -y git python python-pip sqlite iproute2 dnsutils curl wget openssl tsu || true
elif command -v apt-get >/dev/null 2>&1; then
    log_info "Debian/Ubuntu environment detected (apt-get)"
    sudo apt-get update -y || apt-get update -y || true
    sudo apt-get install -y git python3 python3-pip sqlite3 iproute2 dnsutils curl wget || apt-get install -y git python3 python3-pip sqlite3 iproute2 dnsutils curl wget || true
elif command -v pacman >/dev/null 2>&1; then
    log_info "Arch Linux environment detected (pacman)"
    sudo pacman -Sy --noconfirm git python python-pip sqlite iproute2 bind curl wget || true
elif command -v dnf >/dev/null 2>&1; then
    log_info "Fedora/RHEL environment detected (dnf)"
    sudo dnf install -y git python3 python3-pip sqlite iproute bind-utils curl wget || true
elif command -v apk >/dev/null 2>&1; then
    log_info "Alpine Linux environment detected (apk)"
    apk update && apk add git python3 py3-pip sqlite iproute2 bind-tools curl wget || true
else
    log_warn "No recognized package manager found. Proceeding with Python PIP check..."
fi

# 2. Python Packages Installation
log_step 2 3 "Installing Python Dependencies..."
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

detect_python

if [ -f "${PROJECT_ROOT}/requirements.txt" ]; then
    "${PYTHON_BIN}" -m pip install -r "${PROJECT_ROOT}/requirements.txt" --upgrade || \
    pip install -r "${PROJECT_ROOT}/requirements.txt" --upgrade || true
else
    "${PYTHON_BIN}" -m pip install requests psutil prettytable rich pytz --upgrade || \
    pip install requests psutil prettytable rich pytz || true
fi

# 3. File Permissions & Shortcuts
log_step 3 3 "Configuring execution permissions..."
chmod +x "${PROJECT_ROOT}"/*.py 2>/dev/null || true
chmod +x "${PROJECT_ROOT}"/*.sh 2>/dev/null || true
chmod +x "${PROJECT_ROOT}"/shell/*.sh 2>/dev/null || true
chmod +x "${PROJECT_ROOT}/SetupRobloxIP" 2>/dev/null || true

# Setup command shortcut in Termux / Linux bin if writable
if [ -d "/data/data/com.termux/files/usr/bin" ]; then
    BIN_DIR="/data/data/com.termux/files/usr/bin"
elif [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
    BIN_DIR="/usr/local/bin"
elif [ -d "$HOME/.local/bin" ]; then
    mkdir -p "$HOME/.local/bin"
    BIN_DIR="$HOME/.local/bin"
else
    BIN_DIR=""
fi

if [ -n "$BIN_DIR" ]; then
    cat << EOF > "${BIN_DIR}/roblox-ip"
#!/usr/bin/env bash
cd "${PROJECT_ROOT}" && bash run.sh "\$@"
EOF
    chmod +x "${BIN_DIR}/roblox-ip" 2>/dev/null || true
    log_success "Created global shortcut command: 'roblox-ip'"
fi

echo ""
log_success "Dependencies installation and shell configuration completed!"
