#!/usr/bin/env bash
# ==============================================================================
#            ROBLOX MULTI-TAG NETWORK CONTROLLER - TERMUX SETUP SCRIPT
# ==============================================================================
# Tự động:
# 1. Thay đổi Repository Termux sang Mirror nhanh & ổn định nhất (Grimler / BFSU / Tsinghua)
# 2. Cài đặt Python, Git, Java (OpenJDK), SQLite, Curl và các gói phụ thuộc
# 3. Cấp quyền và tự động khởi chạy Tool
# ==============================================================================

set -e

# Màu sắc hiển thị
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo -e "${CYAN}======================================================================${NC}"
echo -e "${GREEN}    ROBLOX MULTI-TAG NETWORK CONTROLLER - TERMUX INSTALLER           ${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

# ------------------------------------------------------------------------------
# BƯỚC 1: THAY ĐỔI VÀ TỐI ƯU REPOSITORY TERMUX (CHỐNG LỖI 404 / TIMEOUT)
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[1/3] [*] Dang thay doi Repository Termux sang Mirror on dinh nhat...${NC}"

# Tạo thư mục apt nếu chưa có
mkdir -p $PREFIX/etc/apt/sources.list.d

# Đổi sang mirror chính thức ổn định của Grimler & A1batross
cat << 'EOF' > $PREFIX/etc/apt/sources.list
deb https://grimler.se/termux/termux-main stable main
deb https://packages.termux.dev/apt/termux-main stable main
EOF

echo -e "${GREEN}[+] Da cap nhat Repository Termux thanh cong!${NC}"
echo ""

# ------------------------------------------------------------------------------
# BƯỚC 2: CẬP NHẬT VÀ CÀI ĐẶT CÁC GÓI PHỤ THUỘC (PYTHON, GIT, JAVA, SQLITE)
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[2/3] [*] Dang cap nhat he thong va cai dat cac goi can thiet...${NC}"

# Cập nhật danh sách gói
pkg update -y -o Dpkg::Options::="--force-confold" || apt-get update -y
pkg upgrade -y -o Dpkg::Options::="--force-confold" || true

# Cài đặt các công cụ cốt lõi
pkg install -y git python python-pip sqlite iproute2 dnsutils curl wget openjdk-17 tsu

# Cập nhật pip
pip install --upgrade pip requests psutil 2>/dev/null || true

echo -e "${GREEN}[+] Da cai dat thanh cong Python, Git, Java va cac thu vien can thiet!${NC}"
echo ""

# ------------------------------------------------------------------------------
# BƯỚC 3: CẤP QUYỀN VÀ KHỞI CHẠY TOOL
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[3/3] [*] Dang cap quyen thuc thi cho cac script shell...${NC}"
chmod +x shell/*.sh 2>/dev/null || true
chmod +x *.py 2>/dev/null || true

echo ""
echo -e "${GREEN}======================================================================${NC}"
echo -e "${GREEN}[+] CAI DAT HOAN TAT! DANG KHOI CHAY MASTER CONTROLLER...             ${NC}"
echo -e "${GREEN}======================================================================${NC}"
sleep 1

# Khởi chạy tool
python controller.py
