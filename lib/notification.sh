#!/usr/bin/env bash
# ==============================================================================
# TERMUX NOTIFICATION WRAPPER
# ==============================================================================

send_termux_notification() {
    local title="$1"
    local content="$2"
    if command -v termux-notification >/dev/null 2>&1; then
        termux-notification --title "$title" --content "$content" --priority high 2>/dev/null || true
    fi
}
