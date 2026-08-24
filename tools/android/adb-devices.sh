#!/usr/bin/env bash
# ==============================================================================
# ADB DEVICES SCANNER & CONNECTOR
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"
source "$TOOLKIT_CORE/adb.sh"

log_info "Quét danh sách thiết bị ADB kết nối..."
devices=$(list_connected_adb_devices)

if [ -z "$devices" ]; then
    log_warn "Chưa phát hiện thiết bị ADB nào."
else
    log_success "Danh sách thiết bị kết nối:"
    echo "$devices"
fi
