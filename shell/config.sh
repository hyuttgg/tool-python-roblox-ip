#!/usr/bin/env bash
# ==============================================================================
# ROBLOX MULTI-TAG NETWORK CONTROLLER - SHELL CONFIGURATION & ENVIRONMENT
# ==============================================================================
# Repository: https://github.com/hyuttgg/tool-python-roblox-ip
# ==============================================================================

# --- GitHub Repository Information ---
export REPO_OWNER="hyuttgg"
export REPO_NAME="tool-python-roblox-ip"
export REPO_BRANCH="main"
export GITHUB_REPO_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}.git"
export GITHUB_RAW_URL="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${REPO_BRANCH}"
export GITHUB_ARCHIVE_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/refs/heads/${REPO_BRANCH}.tar.gz"

# --- ANSI Terminal Colors ---
export COLOR_RED='\033[0;31m'
export COLOR_GREEN='\033[0;32m'
export COLOR_YELLOW='\033[1;33m'
export COLOR_BLUE='\033[0;34m'
export COLOR_MAGENTA='\033[0;35m'
export COLOR_CYAN='\033[0;36m'
export COLOR_WHITE='\033[1;37m'
export COLOR_GRAY='\033[0;90m'
export COLOR_RESET='\033[0m'
export COLOR_BOLD='\033[1m'

# --- Logging Utilities ---
log_info() {
    echo -e "${COLOR_CYAN}[INFO]${COLOR_RESET} $*"
}

log_success() {
    echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} $*"
}

log_warn() {
    echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $*"
}

log_error() {
    echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $*" >&2
}

log_step() {
    local step_num="$1"
    local total_steps="$2"
    local message="$3"
    echo -e "${COLOR_YELLOW}[${step_num}/${total_steps}] [*] ${message}${COLOR_RESET}"
}

# --- Banner Header ---
print_banner() {
    local title="${1:-ROBLOX MULTI-TAG NETWORK CONTROLLER}"
    echo -e "${COLOR_CYAN}======================================================================${COLOR_RESET}"
    echo -e "${COLOR_GREEN}    ⚡ ${title} ⚡${COLOR_RESET}"
    echo -e "${COLOR_CYAN}    GitHub: ${GITHUB_REPO_URL}${COLOR_RESET}"
    echo -e "${COLOR_CYAN}======================================================================${COLOR_RESET}"
    echo ""
}

# --- Environment & Paths Detection ---
detect_environment() {
    export IS_TERMUX=0
    export IS_ANDROID=0
    export IS_ROOT=0

    # Check root
    if [ "$(id -u 2>/dev/null)" = "0" ]; then
        IS_ROOT=1
    fi

    # Check Termux
    if [ -n "$TERMUX_VERSION" ] || [ -d "/data/data/com.termux" ]; then
        IS_TERMUX=1
        IS_ANDROID=1
        export TERMUX_PREFIX="/data/data/com.termux/files/usr"
        export PATH="${TERMUX_PREFIX}/bin:${PATH}"
    elif [ -d "/system/bin" ] && [ -d "/sdcard" ]; then
        IS_ANDROID=1
    fi

    # Detect Tool Base Directory
    export TOOL_DIR=""
    local candidates=(
        "$(pwd)"
        "/sdcard/Download/${REPO_NAME}"
        "/storage/emulated/0/Download/${REPO_NAME}"
        "$HOME/storage/downloads/${REPO_NAME}"
        "$HOME/${REPO_NAME}"
        "/data/data/com.termux/files/home/${REPO_NAME}"
        "/sdcard/${REPO_NAME}"
    )

    for dir in "${candidates[@]}"; do
        if [ -f "${dir}/controller.py" ]; then
            TOOL_DIR="${dir}"
            break
        fi
    done

    if [ -z "$TOOL_DIR" ]; then
        if [ -d "/sdcard/Download" ]; then
            TOOL_DIR="/sdcard/Download/${REPO_NAME}"
        elif [ -d "/storage/emulated/0/Download" ]; then
            TOOL_DIR="/storage/emulated/0/Download/${REPO_NAME}"
        else
            TOOL_DIR="$HOME/${REPO_NAME}"
        fi
    fi
}

# --- Detect Python Binary ---
detect_python() {
    export PYTHON_BIN=""
    local python_candidates=(
        "$(which python3 2>/dev/null)"
        "$(which python 2>/dev/null)"
        "/data/data/com.termux/files/usr/bin/python"
        "/data/data/com.termux/files/usr/bin/python3"
        "/usr/bin/python3"
        "/usr/local/bin/python3"
    )

    for py in "${python_candidates[@]}"; do
        if [ -n "$py" ] && [ -x "$py" ]; then
            PYTHON_BIN="$py"
            break
        fi
    done

    if [ -z "$PYTHON_BIN" ]; then
        PYTHON_BIN="python"
    fi
}

# Auto-execute detection on source
detect_environment
detect_python

# Export common runtime variables
export TERM="${TERM:-xterm-256color}"
export PYTHONIOENCODING="utf-8"
