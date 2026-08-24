#!/usr/bin/env bash
# ==============================================================================
# ROBLOX CLIENT LAUNCHER (ANDROID INTENT & DIRECT PLACE JOIN)
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

PLACE_ID="${1:-2753915549}"
USER_ID="${2:-0}"
URL="roblox://experiences/start?placeId=${PLACE_ID}"

log_info "Đang khởi chạy Roblox vào Place ID: ${PLACE_ID}..."

if [ "$IS_ANDROID" = "1" ]; then
    if [ "$USER_ID" != "0" ]; then
        am start --user "$USER_ID" -a android.intent.action.VIEW -d "$URL" 2>/dev/null || \
        am start --user "$USER_ID" -n com.roblox.client/com.roblox.client.ActivityProtocolLaunch -d "$URL"
    else
        am start -a android.intent.action.VIEW -d "$URL" 2>/dev/null || \
        am start -n com.roblox.client/com.roblox.client.ActivityProtocolLaunch -d "$URL" 2>/dev/null || \
        monkey -p com.roblox.client -c android.intent.category.LAUNCHER 1
    fi
    log_success "Đã gửi lệnh Intent mở Roblox."
else
    log_warn "Hệ điều hành hiện tại không phải Android, sử dụng Python Launcher..."
    $PYTHON_CMD -c "from core.java_sort_bridge import RobloxAutoLauncher; RobloxAutoLauncher.launch_single_instance(place_id='$PLACE_ID')"
fi
