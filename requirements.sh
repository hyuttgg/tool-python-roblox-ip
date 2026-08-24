#!/usr/bin/env bash
# ==============================================================================
# REQUIREMENTS & DEPENDENCY INSTALLER
# ==============================================================================
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$ROOT_DIR/core/environment.sh"
source "$ROOT_DIR/core/logger.sh"
source "$ROOT_DIR/core/dependency.sh"

log_info "=================================================="
log_info "      CÀI ĐẶT TOÀN BỘ DEPENDENCIES (PKG & PIP)    "
log_info "=================================================="

install_all_dependencies

log_success "Tất cả dependencies đã sẵn sàng!"
