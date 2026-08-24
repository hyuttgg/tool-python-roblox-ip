#!/usr/bin/env bash
# ==============================================================================
# PERMISSIONS & STORAGE MANAGER
# ==============================================================================

check_storage_permission() {
    if [ -d "/sdcard" ] && [ -w "/sdcard" ]; then
        return 0
    fi
    if [ "$IS_TERMUX" = "1" ]; then
        log_warn "Yêu cầu cấp quyền Storage Termux (Vui lòng bấm 'Allow' trên màn hình)..."
        termux-setup-storage 2>/dev/null || true
        sleep 2
    fi
}

check_root_permission() {
    if [ "$IS_ROOT" = "1" ]; then
        return 0
    fi
    if command -v su >/dev/null 2>&1 || command -v tsu >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

run_as_root() {
    local cmd="$*"
    if [ "$IS_ROOT" = "1" ]; then
        eval "$cmd"
    elif command -v tsu >/dev/null 2>&1; then
        tsu -c "$cmd"
    elif command -v su >/dev/null 2>&1; then
        su -c "$cmd"
    else
        log_error "Không có quyền Root để thực thi: $cmd"
        return 1
    fi
}
