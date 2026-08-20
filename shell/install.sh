#!/usr/bin/env bash
# ====================================================================
# Installation Script for Termux Android
# ====================================================================

echo "======================================================"
echo " [*] Installing dependencies for Network Manager..."
echo "======================================================"

pkg update -y && pkg upgrade -y
pkg install -y python python-pip sqlite iproute2 dnsutils curl tsu

# Optional packages
pip install --upgrade pip

echo " [*] Making shell scripts executable..."
chmod +x shell/*.sh

echo " [+] Installation completed successfully!"
