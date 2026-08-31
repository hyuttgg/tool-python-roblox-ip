#!/data/data/com.termux/files/usr/bin/bash
# ====================================================================================
# ⚡ ROBLOX AUTO-REJOIN LAUNCHER (CHẠY TOOL TẠI /sdcard/Download/RobloxRejoinTool) ⚡
# Tự động nạp môi trường Termux PATH và khởi chạy Controller (Root hoặc Non-Root)
# ====================================================================================

export PATH="/data/data/com.termux/files/usr/bin:$PATH"
export TERM=xterm-256color

TERMUX_PYTHON="/data/data/com.termux/files/usr/bin/python"
if [ ! -x "$TERMUX_PYTHON" ]; then
    TERMUX_PYTHON="python"
fi

for TOOL_DIR in "/sdcard/Download/RobloxRejoinTool" "/sdcard/Download/tool-python-roblox-ip-main" "$HOME/tool-python-roblox-ip"; do
    if [ -f "$TOOL_DIR/controller.py" ]; then
        cd "$TOOL_DIR" 2>/dev/null
        break
    fi
done

if command -v su >/dev/null 2>&1; then
    su -c "export PATH=/data/data/com.termux/files/usr/bin:\$PATH && cd \"$(pwd)\" && $TERMUX_PYTHON controller.py"
else
    $TERMUX_PYTHON controller.py
fi

