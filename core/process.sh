#!/usr/bin/env bash
# ==============================================================================
# PROCESS & DAEMON MANAGER
# ==============================================================================

find_roblox_pids() {
    pidof com.roblox.client 2>/dev/null || pgrep -f "roblox" 2>/dev/null || echo ""
}

kill_roblox_instances() {
    local pids=$(find_roblox_pids)
    if [ -n "$pids" ]; then
        log_info "Đang tắt các tiến trình Roblox cũ ($pids)..."
        kill -9 $pids 2>/dev/null || run_as_root "kill -9 $pids" 2>/dev/null || true
    fi
}

start_background_daemon() {
    local script_cmd="$1"
    local log_out="$2"
    nohup $script_cmd > "$log_out" 2>&1 &
    echo $!
}
