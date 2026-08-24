#!/usr/bin/env bash
# ==============================================================================
# MAGISK & KERNELSU SERVICE.D AUTO-BOOT ENGINE
# ==============================================================================

install_magisk_boot_service() {
    local target_file="/data/adb/service.d/roblox_tproxy_boot.sh"
    log_info "Cài đặt dịch vụ tự khởi động TPROXY tại $target_file..."

    local script_body="#!/system/bin/sh
# Roblox Stealth TPROXY Auto-boot Script
sleep 15
ROBLOX_UID=\$(dumpsys package com.roblox.client 2>/dev/null | grep -E 'userId=' | head -n 1 | cut -d= -f2 | tr -d ' ')
if [ -n \"\$ROBLOX_UID\" ]; then
    iptables -t nat -N ROBLOX_TPROXY 2>/dev/null || iptables -t nat -F ROBLOX_TPROXY
    iptables -t nat -A ROBLOX_TPROXY -p udp --dport 53 -j DNAT --to-destination 1.1.1.1:53
    iptables -t nat -A ROBLOX_TPROXY -p tcp -j REDIRECT --to-ports 10808
    iptables -t nat -A OUTPUT -m owner --uid-owner \$ROBLOX_UID -j ROBLOX_TPROXY
fi
"
    run_as_root "mkdir -p /data/adb/service.d"
    run_as_root "echo '$script_body' > $target_file"
    run_as_root "chmod 755 $target_file"
    log_success "Đã cài đặt Magisk service.d boot service thành công!"
}

remove_magisk_boot_service() {
    local target_file="/data/adb/service.d/roblox_tproxy_boot.sh"
    log_info "Gỡ bỏ dịch vụ khởi động cùng Android..."
    run_as_root "rm -f $target_file"
    log_success "Đã gỡ bỏ Magisk boot service."
}
