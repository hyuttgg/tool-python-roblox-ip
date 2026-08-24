#!/usr/bin/env bash
# ==============================================================================
# MIHOMO / CLASH.META MANAGER
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Sinh cấu hình Mihomo (Clash.Meta) YAML..."
$PYTHON_CMD -c "from network.deep_interceptor import MihomoDeepInterceptor; p = MihomoDeepInterceptor.generate_mihomo_config(); print('Đã tạo file cấu hình:', p)"
