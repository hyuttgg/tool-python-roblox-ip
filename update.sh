#!/usr/bin/env bash
# ==============================================================================
# TOOLKIT AUTO-UPDATER
# ==============================================================================
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$ROOT_DIR/core/environment.sh"
source "$ROOT_DIR/core/logger.sh"

log_info "Kiểm tra và cập nhật Toolkit từ GitHub..."
git pull origin main 2>/dev/null || log_warn "Git pull note."

log_info "Cập nhật permissions và sinh lại mã Lua..."
find "$ROOT_DIR/bin" -type f -exec chmod +x {} \; 2>/dev/null || true
find "$ROOT_DIR/tools" -type f -exec chmod +x {} \; 2>/dev/null || true

$PYTHON_CMD -c "from controller import MasterController; mc = MasterController(); insts = mc._get_combined_tag_instances(); mc.sync_system_state(insts, use_live_proxies=False); print('Đã cập nhật mã Lua thành công!')" 2>/dev/null || true

log_success "Toolkit đã được cập nhật bản mới nhất!"
