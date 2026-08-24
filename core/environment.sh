#!/usr/bin/env bash
# ==============================================================================
# CORE ENVIRONMENT DETECTOR
# ==============================================================================

export TOOLKIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load configuration files
if [ -f "$TOOLKIT_ROOT/config.env" ]; then
    source "$TOOLKIT_ROOT/config.env"
fi
if [ -f "$TOOLKIT_ROOT/config/colors.conf" ]; then
    source "$TOOLKIT_ROOT/config/colors.conf"
fi
if [ -f "$TOOLKIT_ROOT/config/paths.conf" ]; then
    source "$TOOLKIT_ROOT/config/paths.conf"
fi

detect_environment() {
    export IS_TERMUX=0
    export IS_ANDROID=0
    export IS_ROOT=0
    export OS_TYPE="Linux"
    export CPU_ARCH="$(uname -m 2>/dev/null || echo 'unknown')"

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

    # Detect Python
    export PYTHON_CMD="python"
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="python3"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_CMD="python"
    fi
}

detect_environment
