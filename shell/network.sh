#!/usr/bin/env bash
# ==============================================================================
# ROBLOX MULTI-TAG NETWORK CONTROLLER - KERNEL & NETWORK DIAGNOSTIC
# ==============================================================================
# Repository: https://github.com/hyuttgg/tool-python-roblox-ip
# ==============================================================================

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}======================================================================${NC}"
echo -e "${GREEN}       🌐 SYSTEM & KERNEL NETWORK DIAGNOSTICS REPORT 🌐              ${NC}"
echo -e "${CYAN}======================================================================${NC}"

# 1. Interface & IP
echo -e "\n${YELLOW}=== [1. NETWORK INTERFACES & IP ADDRESSES] ===${NC}"
if command -v ip >/dev/null 2>&1; then
    ip -br addr show 2>/dev/null || ip addr show 2>/dev/null
elif command -v ifconfig >/dev/null 2>&1; then
    ifconfig
else
    echo "[-] Neither 'ip' nor 'ifconfig' command found."
fi

# 2. Routing & Gateway
echo -e "\n${YELLOW}=== [2. ROUTING TABLE & DEFAULT GATEWAY] ===${NC}"
if command -v ip >/dev/null 2>&1; then
    ip route show 2>/dev/null
elif command -v route >/dev/null 2>&1; then
    route -n 2>/dev/null
elif command -v netstat >/dev/null 2>&1; then
    netstat -rn 2>/dev/null
fi

# 3. DNS Resolution
echo -e "\n${YELLOW}=== [3. DNS RESOLUTION TEST (roblox.com)] ===${NC}"
if command -v nslookup >/dev/null 2>&1; then
    nslookup www.roblox.com 2>/dev/null || echo "[-] NSLookup failed"
elif command -v host >/dev/null 2>&1; then
    host www.roblox.com 2>/dev/null
elif command -v ping >/dev/null 2>&1; then
    ping -c 2 -W 2 www.roblox.com 2>/dev/null || echo "[-] Ping host resolution failed"
fi

# 4. Android Getprop Info
echo -e "\n${YELLOW}=== [4. ANDROID SYSTEM NETWORK PROPERTIES] ===${NC}"
if command -v getprop >/dev/null 2>&1; then
    echo "DNS 1:          $(getprop net.dns1)"
    echo "DNS 2:          $(getprop net.dns2)"
    echo "WiFi Gateway:   $(getprop dhcp.wlan0.gateway)"
    echo "WiFi IP:        $(getprop dhcp.wlan0.ipaddress)"
    echo "WiFi Mask:      $(getprop dhcp.wlan0.mask)"
    echo "HTTP Proxy:     $(getprop http.proxy)"
else
    echo "[-] Android getprop is not applicable in this environment."
fi

# 5. Public IP Check
echo -e "\n${YELLOW}=== [5. PUBLIC IP & WAN TEST] ===${NC}"
PUBLIC_IP=$(curl -s --connect-timeout 4 https://api.ipify.org 2>/dev/null || curl -s --connect-timeout 4 https://ifconfig.me 2>/dev/null || echo "Unavailable")
echo -e "Public IP Address: ${GREEN}${PUBLIC_IP}${NC}"

echo -e "\n${CYAN}======================================================================${NC}"
