#!/usr/bin/env bash
# ==============================================================================
# ANDROID MULTI-USER / DUAL APP HELPER
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"
source "$TOOLKIT_CORE/permissions.sh"

log_info "Danh sách người dùng / Profile trên Android:"
run_as_root "pm list users 2>/dev/null || echo 'Không có quyền root.'"
