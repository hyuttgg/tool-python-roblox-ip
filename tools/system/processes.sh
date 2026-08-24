#!/usr/bin/env bash
# ==============================================================================
# ROBLOX & PYTHON PROCESS MONITOR
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"

echo "=== TIẾN TRÌNH ĐANG CHẠY ==="
ps -ef 2>/dev/null | grep -E "roblox|python|controller" | grep -v grep || ps aux 2>/dev/null | grep -E "roblox|python"
