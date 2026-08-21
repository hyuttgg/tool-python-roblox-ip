#!/usr/bin/env bash
# ==============================================================================
# ROBLOX MULTI-TAG NETWORK CONTROLLER - ROOT (SU) LAUNCHER
# ==============================================================================
# Repository: https://github.com/hyuttgg/tool-python-roblox-ip
# ==============================================================================

export TERM="${TERM:-xterm-256color}"
export PYTHONIOENCODING="utf-8"

# Termux binary paths in Root context
export PATH="/data/data/com.termux/files/usr/bin:/data/data/com.termux/files/usr/bin/applets:/system/bin:/system/xbin:${PATH}"

# Detect Python Binary
PYTHON_CMD=""
for py in "/data/data/com.termux/files/usr/bin/python" "/data/data/com.termux/files/usr/bin/python3" "$(which python3 2>/dev/null)" "$(which python 2>/dev/null)"; do
    if [ -n "$py" ] && [ -x "$py" ]; then
        PYTHON_CMD="$py"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    PYTHON_CMD="python"
fi

# Locate Target Directory
TARGET_DIR=""
candidates=(
    "$(pwd)"
    "/sdcard/Download/tool-python-roblox-ip"
    "/storage/emulated/0/Download/tool-python-roblox-ip"
    "/data/data/com.termux/files/home/tool-python-roblox-ip"
    "$HOME/tool-python-roblox-ip"
    "/sdcard/tool-python-roblox-ip"
)

for dir in "${candidates[@]}"; do
    if [ -f "${dir}/pyobfuscate_com.py" ] || [ -f "${dir}/controller.py" ]; then
        TARGET_DIR="${dir}"
        break
    fi
done

if [ -n "$TARGET_DIR" ]; then
    cd "$TARGET_DIR" || exit 1
    MAIN_PY="controller.py"
    if [ -f "pyobfuscate_com.py" ]; then
        MAIN_PY="pyobfuscate_com.py"
    fi
    echo "[*] Launching Roblox Multi-Tag Controller (${MAIN_PY}) as Root in: ${TARGET_DIR}"
    exec "${PYTHON_CMD}" "${MAIN_PY}" "$@"
else
    echo "[-] Error: Could not locate tool-python-roblox-ip directory."
    exit 1
fi
