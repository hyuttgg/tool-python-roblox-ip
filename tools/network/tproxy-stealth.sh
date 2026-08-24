#!/usr/bin/env bash
# ==============================================================================
# ANDROID STEALTH TPROXY CONTROLLER (NO-VPN ICON)
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"
source "$TOOLKIT_CORE/iptables.sh"
source "$TOOLKIT_CORE/permissions.sh"

ACTION="${1:-status}"

case "$ACTION" in
    enable|on|start)
        apply_tproxy_rules
        ;;
    disable|off|stop)
        flush_tproxy_rules
        ;;
    status)
        log_info "Trạng thái IPTables TPROXY hiện tại:"
        run_as_root "iptables -t nat -L ROBLOX_TPROXY -n -v 2>/dev/null || echo 'TPROXY chưa kích hoạt.'"
        ;;
    *)
        echo "Sử dụng: $0 {enable|disable|status}"
        ;;
esac
