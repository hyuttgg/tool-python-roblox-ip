#!/data/data/com.termux/files/usr/bin/bash
# ====================================================================================
# ⚡ ROBLOX AUTO-REJOIN LAUNCHER (CHẠY TOOL TẠI /sdcard/Download/RobloxRejoinTool) ⚡
# Tự động nạp môi trường Termux PATH và khởi chạy Controller (Root hoặc Non-Root)
# ====================================================================================

export PATH=$PATH:/data/data/com.termux/files/usr/bin
export TERM=xterm-256color

TOOL_DIR="/sdcard/Download/RobloxRejoinTool"
if [ -d "$TOOL_DIR" ]; then
    cd "$TOOL_DIR" || cd /sdcard/Download
else
    cd /sdcard/Download
fi

# Kiểm tra quyền Root
if command -v su >/dev/null 2>&1; then
    su -c "export PATH=\$PATH:/data/data/com.termux/files/usr/bin && export TERM=xterm-256color && cd /sdcard/Download/RobloxRejoinTool && python controller.py"
else
    python controller.py
fi
