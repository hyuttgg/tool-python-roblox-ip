#!/usr/bin/env bash
# ====================================================================
# Network Extraction Script (Kernel & Android Native)
# ====================================================================

echo "=== [INTERFACE & IP ADDRESSES] ==="
ip -br addr show

echo ""
echo "=== [DEFAULT GATEWAY & ROUTING] ==="
ip route show

echo ""
echo "=== [DNS RESOLUTION TEST] ==="
nslookup www.roblox.com

echo ""
echo "=== [ANDROID GETPROP NETWORK INFO] ==="
getprop net.dns1
getprop net.dns2
getprop dhcp.wlan0.gateway
