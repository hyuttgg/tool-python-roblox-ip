#!/usr/bin/env bash
# ==============================================================================
# ROBLOX MULTI-TAG NETWORK CONTROLLER - MASTER RUNNER & CLI DISPATCHER
# ==============================================================================
# Repository: https://github.com/hyuttgg/tool-python-roblox-ip
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Source config if available
if [ -f "${SCRIPT_DIR}/shell/config.sh" ]; then
    source "${SCRIPT_DIR}/shell/config.sh"
fi

# Detect Python
PYTHON_EXEC="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_EXEC}" >/dev/null 2>&1; then
    PYTHON_EXEC="python"
fi

# Detect Target Python Entry Script
ENTRY_SCRIPT="controller.py"
if [ -f "pyobfuscate_com.py" ]; then
    ENTRY_SCRIPT="pyobfuscate_com.py"
fi

show_help() {
    echo "======================================================================"
    echo "    ROBLOX MULTI-TAG CONTROLLER - COMMAND LINE LAUNCHER"
    echo "======================================================================"
    echo "Usage: ./run.sh [OPTION]"
    echo ""
    echo "Options:"
    echo "  (no arguments)     Launch Master Controller UI (${ENTRY_SCRIPT})"
    echo "  -m, --monitor      Launch Realtime Network Monitor Dashboard (main.py)"
    echo "  -r, --root         Launch with SuperUser / Root permissions"
    echo "  -s, --setup        Run Termux Auto-Setup & Install dependencies"
    echo "  -i, --install      Run Universal Linux/Termux Package Installer"
    echo "  -n, --net          Run System & Kernel Network Diagnostics"
    echo "  -t, --test         Execute Project Automated Test Suite"
    echo "  -h, --help         Display this help message"
    echo "======================================================================"
}

case "$1" in
    -h|--help)
        show_help
        exit 0
        ;;
    -m|--monitor)
        exec "${PYTHON_EXEC}" main.py
        ;;
    -r|--root)
        if [ -f "shell/root_launcher.sh" ]; then
            exec bash shell/root_launcher.sh "${@:2}"
        elif command -v su >/dev/null 2>&1; then
            exec su -c "cd '${SCRIPT_DIR}' && ${PYTHON_EXEC} ${ENTRY_SCRIPT} ${*:2}"
        else
            echo "[-] Error: 'su' command not found."
            exit 1
        fi
        ;;
    -s|--setup)
        exec bash shell/termux_setup.sh
        ;;
    -i|--install)
        exec bash shell/install.sh
        ;;
    -n|--net)
        exec bash shell/network.sh
        ;;
    -t|--test)
        exec "${PYTHON_EXEC}" tests/test_all.py
        ;;
    *)
        exec "${PYTHON_EXEC}" "${ENTRY_SCRIPT}" "$@"
        ;;
esac
