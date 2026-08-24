#!/usr/bin/env bash
# ==============================================================================
# SDCARD & EXECUTOR PERMISSIONS FIXER
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"
source "$TOOLKIT_CORE/permissions.sh"

log_info "Sửa quyền truy cập thư mục Autoexec trên /sdcard..."
check_storage_permission

if [ -d "/sdcard" ]; then
    mkdir -p "/sdcard/Arceus X/Autoexec" 2>/dev/null || true
    mkdir -p "/sdcard/Delta/Autoexec" 2>/dev/null || true
    mkdir -p "/sdcard/Codex/Autoexec" 2>/dev/null || true
    log_success "Đã chuẩn bị sẵn các thư mục Autoexec."
fi
