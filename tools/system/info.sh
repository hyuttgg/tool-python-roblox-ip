#!/usr/bin/env bash
# ==============================================================================
# SYSTEM & HARDWARE INFORMATION
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"

echo ""
echo "=================================================="
echo "          THÔNG TIN THIẾT BỊ & HỆ THỐNG"
echo "=================================================="
echo "OS / Kernel    : $(uname -a)"
echo "Architecture   : $(uname -m)"
echo "Termux Prefix  : ${PREFIX:-N/A}"
echo "Root Status    : $([ "$IS_ROOT" = "1" ] && echo "YES (Rooted)" || echo "NO (Non-root)")"
echo "Python Version : $($PYTHON_CMD --version 2>/dev/null || echo 'Chưa cài')"
echo "Java Version   : $(java -version 2>&1 | head -n 1 || echo 'Chưa cài')"
echo "=================================================="
echo ""
