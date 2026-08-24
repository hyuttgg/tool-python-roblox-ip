#!/usr/bin/env bash
# ==============================================================================
# GIT REPOSITORY SYNC & PULL
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Đồng bộ mã nguồn từ GitHub Repository..."
git pull origin main 2>/dev/null || log_warn "Không thể git pull trực tiếp."
log_success "Đã cập nhật repository mới nhất."
