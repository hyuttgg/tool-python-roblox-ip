#!/usr/bin/env bash
# ==============================================================================
# ANDROID IPTABLES TPROXY ENGINE (ASTERISK-META ARCHITECTURE)
# ==============================================================================

get_roblox_uid() {
    dumpsys package com.roblox.client 2>/dev/null | grep -E "userId=" | head -n 1 | cut -d= -f2 | tr -d ' '
}

apply_tproxy_rules() {
    local uid="$(get_roblox_uid)"
    local tproxy_port="${TPROXY_TCP_PORT:-10808}"
    local dns_srv="${DEFAULT_DNS_UPSTREAM:-1.1.1.1}"

    if [ -z "$uid" ]; then
        log_error "Không tìm thấy UID của Roblox Client (com.roblox.client)."
        return 1
    fi

    log_info "Bơm IPTables TPROXY cho Roblox UID: $uid (Port $tproxy_port, DNS $dns_srv)..."
    
    run_as_root "iptables -t nat -N ROBLOX_TPROXY 2>/dev/null || iptables -t nat -F ROBLOX_TPROXY"
    run_as_root "iptables -t nat -A ROBLOX_TPROXY -d 127.0.0.0/8 -j RETURN"
    run_as_root "iptables -t nat -A ROBLOX_TPROXY -d 10.0.0.0/8 -j RETURN"
    run_as_root "iptables -t nat -A ROBLOX_TPROXY -d 192.168.0.0/16 -j RETURN"
    run_as_root "iptables -t nat -A ROBLOX_TPROXY -p udp --dport 53 -j DNAT --to-destination ${dns_srv}:53"
    run_as_root "iptables -t nat -A ROBLOX_TPROXY -p tcp -j REDIRECT --to-ports ${tproxy_port}"
    
    run_as_root "iptables -t nat -D OUTPUT -m owner --uid-owner ${uid} -j ROBLOX_TPROXY 2>/dev/null || true"
    run_as_root "iptables -t nat -A OUTPUT -m owner --uid-owner ${uid} -j ROBLOX_TPROXY"
    
    log_success "Đã kích hoạt TPROXY Stealth thành công (Không hiện icon VPN)!"
}

flush_tproxy_rules() {
    log_info "Đang gỡ bỏ toàn bộ IPTables TPROXY..."
    run_as_root "iptables -t nat -D OUTPUT -j ROBLOX_TPROXY 2>/dev/null || true"
    run_as_root "iptables -t nat -F ROBLOX_TPROXY 2>/dev/null || true"
    run_as_root "iptables -t nat -X ROBLOX_TPROXY 2>/dev/null || true"
    run_as_root "iptables -t nat -F OUTPUT 2>/dev/null || true"
    log_success "Đã khôi phục mạng gốc thành công."
}
