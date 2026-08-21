#!/usr/bin/env bash
# ==============================================================================
# Roblox Multi-Instance Root / SU Launcher
# ==============================================================================
# Script chạy với quyền Root (su) trực tiếp từ bộ nhớ máy hoặc Termux
# ==============================================================================

export PATH=$PATH:/data/data/com.termux/files/usr/bin
export TERM=xterm-256color
export PYTHONIOENCODING=utf-8

# Tìm thư mục chứa tool
if [ -d "/sdcard/Download/tool-python-roblox-ip" ]; then
    cd /sdcard/Download/tool-python-roblox-ip
elif [ -d "/storage/emulated/0/Download/tool-python-roblox-ip" ]; then
    cd /storage/emulated/0/Download/tool-python-roblox-ip
elif [ -d "/data/data/com.termux/files/home/tool-python-roblox-ip" ]; then
    cd /data/data/com.termux/files/home/tool-python-roblox-ip
elif [ -d "$HOME/tool-python-roblox-ip" ]; then
    cd "$HOME/tool-python-roblox-ip"
elif [ -d "/sdcard/tool-python-roblox-ip" ]; then
    cd /sdcard/tool-python-roblox-ip
fi

python controller.py
