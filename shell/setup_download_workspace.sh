#!/usr/bin/env bash
# ==============================================================================
# ROBLOX MULTI-TAG NETWORK CONTROLLER - DOWNLOADS WORKSPACE LINKER
# ==============================================================================
# Thiết lập không gian chạy tool tại thư mục Downloads trên điện thoại Android:
#   - Cài đặt & Core Tool lưu trong Termux: $HOME/tool-python-roblox-ip
#   - Không gian chạy, file Lua & Configs lưu tại: /sdcard/Download/RobloxIPTool
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 1. Xác định đường dẫn thư mục Downloads trên Android
DOWNLOAD_CANDIDATES=(
    "/sdcard/Download/RobloxIPTool"
    "/storage/emulated/0/Download/RobloxIPTool"
    "$HOME/storage/downloads/RobloxIPTool"
)

TARGET_DOWNLOAD_DIR=""
for d in "${DOWNLOAD_CANDIDATES[@]}"; do
    parent_dir="$(dirname "$d")"
    if [ -d "$parent_dir" ] || [ -w "$parent_dir" ]; then
        TARGET_DOWNLOAD_DIR="$d"
        break
    fi
done

if [ -z "$TARGET_DOWNLOAD_DIR" ]; then
    TARGET_DOWNLOAD_DIR="/sdcard/Download/RobloxIPTool"
fi

echo -e "\033[0;36m[*] Đang thiết lập không gian chạy Tool tại thư mục Downloads:\033[0m"
echo -e "    -> \033[1;33m${TARGET_DOWNLOAD_DIR}\033[0m"

# 2. Tạo thư mục Downloads/RobloxIPTool và các thư mục con
mkdir -p "${TARGET_DOWNLOAD_DIR}" 2>/dev/null || true
mkdir -p "${TARGET_DOWNLOAD_DIR}/data" 2>/dev/null || true
mkdir -p "${TARGET_DOWNLOAD_DIR}/data/generated_lua" 2>/dev/null || true
mkdir -p "${TARGET_DOWNLOAD_DIR}/logs" 2>/dev/null || true

# 3. Tạo Script chạy 'run.sh' & 'start.sh' trực tiếp trong thư mục Downloads
cat << EOF > "${TARGET_DOWNLOAD_DIR}/run.sh"
#!/usr/bin/env bash
# ==============================================================================
# LAUNCHER CHẠY TOOL ROBLOX IP TỪ THƯ MỤC DOWNLOADS
# ==============================================================================
CORE_DIR="${PROJECT_ROOT}"

if [ ! -d "\$CORE_DIR" ]; then
    CORE_DIR="\$HOME/tool-python-roblox-ip"
fi

if [ -f "\$CORE_DIR/controller.py" ]; then
    cd "\$CORE_DIR" && bash run.sh "\$@"
elif [ -f "\$CORE_DIR/pyobfuscate_com.py" ]; then
    cd "\$CORE_DIR" && bash run.sh "\$@"
else
    echo "[-] Khong tim thay ma nguon tool tai: \$CORE_DIR"
    echo "[*] Vui long mo Termux va chay lai Setup!"
fi
EOF

chmod +x "${TARGET_DOWNLOAD_DIR}/run.sh" 2>/dev/null || true
cp "${TARGET_DOWNLOAD_DIR}/run.sh" "${TARGET_DOWNLOAD_DIR}/start.sh" 2>/dev/null || true
chmod +x "${TARGET_DOWNLOAD_DIR}/start.sh" 2>/dev/null || true

# 4. Tạo file Hướng dẫn sử dụng trong Downloads để người dùng đọc trên điện thoại
cat << 'EOF' > "${TARGET_DOWNLOAD_DIR}/HUONG_DAN_CHAY.txt"
================================================================================
  HƯỚNG DẪN CHẠY TOOL PYTHON ROBLOX IP TỪ THƯ MỤC DOWNLOADS TRÊN ĐIỆN THOẠI
================================================================================

1. CÁCH CHẠY TOOL NHANH NHẤT TRÊN TERMUX:
   - Cách 1 (Khuyên dùng): Mở ứng dụng Termux, gõ:
       roblox-ip
     (Lệnh tắt này hoạt động ở bất kỳ đâu trên Termux)

   - Cách 2: Mở Termux, vào thư mục Downloads rồi chạy:
       cd /sdcard/Download/RobloxIPTool
       bash run.sh

2. CÁC TỆP TIN ĐƯỢC LƯU TRONG THƯ MỤC DOWNLOADS NÀY:
   - run.sh / start.sh : File script khởi chạy tool.
   - data/generated_lua/ : Chứa toàn bộ các file script Lua đã tạo cho từng Tag
                          (ROBLOX-TAG-01.lua, master_roblox_ip_setter.lua...)
                          Bạn có thể dùng ZArchiver / File Manager copy vào Executor!
   - data/target_game_config.json : Cấu hình Game Place ID đã chọn.
   - data/country_config.json     : Cấu hình Quốc gia IP đã chọn.
   - data/Live_Proxies.txt        : Danh sách Proxy quốc tế trực tiếp.

3. NƠI LƯU MÔI TRƯỜNG CÀI ĐẶT:
   - Môi trường cài đặt (Python, Clang, Rust, Java, Packages): Lưu an toàn trong Termux (~).
   - Không gian chạy và file xuất ra: Lưu tại thư mục Downloads này.
================================================================================
EOF

# 5. Đồng bộ thư mục data giữa Core và Downloads
if [ -d "${PROJECT_ROOT}/data" ]; then
    cp -rn "${PROJECT_ROOT}/data"/* "${TARGET_DOWNLOAD_DIR}/data/" 2>/dev/null || true
fi

echo -e "\033[0;32m[+] Đã tạo không gian chạy Tool thành công tại:\033[0m \033[1;32m${TARGET_DOWNLOAD_DIR}\033[0m"
echo -e "    • File khởi chạy : \033[1;33m${TARGET_DOWNLOAD_DIR}/run.sh\033[0m"
echo -e "    • Hướng dẫn      : \033[1;33m${TARGET_DOWNLOAD_DIR}/HUONG_DAN_CHAY.txt\033[0m"
echo -e "    • Thư mục Script : \033[1;33m${TARGET_DOWNLOAD_DIR}/data/generated_lua/\033[0m"
