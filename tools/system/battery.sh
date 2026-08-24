#!/usr/bin/env bash
# ==============================================================================
# BATTERY & THERMAL STATUS
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"

if command -v termux-battery-status >/dev/null 2>&1; then
    termux-battery-status
elif [ -f "/sys/class/power_supply/battery/capacity" ]; then
    echo "Battery Level: $(cat /sys/class/power_supply/battery/capacity)%"
    echo "Temperature  : $(cat /sys/class/power_supply/battery/temp 2>/dev/null || echo 'N/A')"
else
    echo "Không thể lấy thông tin pin trên thiết bị này."
fi
