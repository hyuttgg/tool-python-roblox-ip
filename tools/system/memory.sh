#!/usr/bin/env bash
# ==============================================================================
# RAM & CACHE CLEANER
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"
source "$TOOLKIT_CORE/permissions.sh"

log_info "Giải phóng bộ nhớ RAM và dọn cache hệ thống..."
run_as_root "sync; echo 3 > /proc/sys/vm/drop_caches 2>/dev/null" || true
log_success "Đã tối ưu hóa bộ nhớ RAM."
