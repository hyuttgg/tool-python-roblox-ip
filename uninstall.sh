#!/usr/bin/env bash
# ==============================================================================
# TOOLKIT UNINSTALLER & CLEANER
# ==============================================================================
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$ROOT_DIR/core/environment.sh"
source "$ROOT_DIR/core/logger.sh"
source "$ROOT_DIR/core/iptables.sh"
source "$ROOT_DIR/core/magisk.sh"

log_info "Bắt đầu gỡ bỏ Toolkit và khôi phục cài đặt gốc..."

# 1. Khôi phục IPTables
flush_tproxy_rules 2>/dev/null || true

# 2. Xóa Magisk boot service
remove_magisk_boot_service 2>/dev/null || true

# 3. Xóa symlinks trong $PREFIX/bin
if [ -n "$PREFIX" ] && [ -d "$PREFIX/bin" ]; then
    rm -f "$PREFIX/bin/roblox-tool" "$PREFIX/bin/roblox-run" "$PREFIX/bin/roblox-watchdog" "$PREFIX/bin/roblox-tproxy" 2>/dev/null || true
fi

log_success "Đã gỡ bỏ sạch sẽ."
