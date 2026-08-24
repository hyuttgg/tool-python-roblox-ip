#!/usr/bin/env bash
# ==============================================================================
# CLEANUP & SYSTEM SANITIZER
# ==============================================================================

cleanup_temp_files() {
    log_info "Dọn dẹp cache và file tạm..."
    rm -rf "$TOOLKIT_ROOT/__pycache__" 2>/dev/null || true
    rm -rf "$TOOLKIT_ROOT/*/__pycache__" 2>/dev/null || true
    rm -rf "$TOOLKIT_ROOT/*.pyc" 2>/dev/null || true
    log_success "Dọn dẹp hoàn tất."
}
