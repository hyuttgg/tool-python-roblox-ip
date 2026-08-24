#!/usr/bin/env bash
# ==============================================================================
# 1-CLICK TERMUX TOOLKIT INSTALLER
# ==============================================================================
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$ROOT_DIR/core/environment.sh"
source "$ROOT_DIR/core/logger.sh"
source "$ROOT_DIR/core/permissions.sh"
source "$ROOT_DIR/core/dependency.sh"
source "$ROOT_DIR/core/bootstrap.sh"

log_info "Bắt đầu cài đặt Termux Roblox Toolkit..."

# 1. Cấp quyền storage
check_storage_permission

# 2. Cài đặt dependencies
install_all_dependencies

# 3. Phân quyền thực thi
find "$ROOT_DIR/bin" -type f -exec chmod +x {} \; 2>/dev/null || true
find "$ROOT_DIR/core" -type f -exec chmod +x {} \; 2>/dev/null || true
find "$ROOT_DIR/lib" -type f -exec chmod +x {} \; 2>/dev/null || true
find "$ROOT_DIR/tools" -type f -exec chmod +x {} \; 2>/dev/null || true
find "$ROOT_DIR/tests" -type f -exec chmod +x {} \; 2>/dev/null || true
chmod +x "$ROOT_DIR/main.sh" "$ROOT_DIR/run.sh" 2>/dev/null || true

# 4. Tạo Symlink System-Wide trong $PREFIX/bin nếu ở Termux
if [ -n "$PREFIX" ] && [ -d "$PREFIX/bin" ]; then
    ln -sf "$ROOT_DIR/main.sh" "$PREFIX/bin/roblox-tool" 2>/dev/null || true
    ln -sf "$ROOT_DIR/bin/roblox-run" "$PREFIX/bin/roblox-run" 2>/dev/null || true
    ln -sf "$ROOT_DIR/bin/roblox-watchdog" "$PREFIX/bin/roblox-watchdog" 2>/dev/null || true
    ln -sf "$ROOT_DIR/bin/roblox-tproxy" "$PREFIX/bin/roblox-tproxy" 2>/dev/null || true
    log_success "Đã tạo lệnh gọi hệ thống: 'roblox-tool', 'roblox-run', 'roblox-watchdog', 'roblox-tproxy'."
fi

log_success "CÀI ĐẶT HOÀN TẤT! Khởi động bằng cách gõ: roblox-tool hoặc ./main.sh"
