#!/usr/bin/env bash
# ==============================================================================
# CONNECTION & ROBLOX SERVER TESTER
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Kiểm tra kết nối Internet & Roblox Server..."
if curl -Is --max-time 5 https://www.roblox.com >/dev/null 2>&1; then
    log_success "Kết nối tới máy chủ Roblox: ONLINE"
else
    log_warn "Không thể kết nối trực tiếp tới Roblox (Cần bật Proxy/TPROXY)."
fi
