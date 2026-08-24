#!/usr/bin/env bash
# ==============================================================================
# SING-BOX TUN WINTUN MANAGER
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Sinh cấu hình Sing-Box Wintun TUN JSON..."
$PYTHON_CMD -c "from network.deep_interceptor import WindowsDeepInterceptor; p = WindowsDeepInterceptor.generate_singbox_config(); print('Đã tạo file cấu hình:', p)"
