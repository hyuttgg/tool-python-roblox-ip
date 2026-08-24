#!/usr/bin/env bash
# ==============================================================================
# ROBLOX CRASH WATCHDOG & AUTO-REJOIN SUPERVISOR
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

ACTION="${1:-status}"

case "$ACTION" in
    start|on)
        log_info "Kích hoạt Watchdog Supervisor chạy nền..."
        $PYTHON_CMD -c "from core.watchdog_supervisor import watchdog; watchdog.start(); print('Watchdog Active!')"
        ;;
    status)
        log_info "Kiểm tra trạng thái Watchdog..."
        $PYTHON_CMD -c "from core.watchdog_supervisor import watchdog; import pprint; pprint.pprint(watchdog.get_summary())"
        ;;
    *)
        echo "Sử dụng: $0 {start|status}"
        ;;
esac
