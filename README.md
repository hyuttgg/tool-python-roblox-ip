# ⚡ ROBLOX MULTI-TAG NETWORK CONTROLLER ⚡
> Repository: `https://github.com/hyuttgg/tool-python-roblox-ip`

---

## 📱 HƯỚNG DẪN 3 BƯỚC CÀI ĐẶT & CHẠY TOOL TRÊN TERMUX

### 1️⃣ Thay đổi repository Termux
```bash
termux-change-repo
```
📌 *Nhấn **OK** ➔ **OK***

---

### 2️⃣ Cài đặt tool
```bash
. <(curl -sL https://raw.githubusercontent.com/hyuttgg/tool-python-roblox-ip/refs/heads/main/SetupRobloxIP)
```

---

### 3️⃣ Chạy tool
```bash
su -c "export PATH=$PATH:/data/data/com.termux/files/usr/bin && export TERM=xterm-256color && cd /sdcard/Download/tool-python-roblox-ip && python pyobfuscate_com.py"
```

---

## 💡 CÁC CÁCH CHẠY BỔ SUNG

### Cách 1: Chạy bằng lệnh tắt nhanh (Từ bất kỳ đâu trên Termux)
```bash
roblox-ip
```

### Cách 2: Chạy trực tiếp qua Script Runner
```bash
cd /sdcard/Download/tool-python-roblox-ip && bash run.sh
```

### Cách 3: Chạy Dashboard giám sát trực tiếp (Live Monitor)
```bash
cd /sdcard/Download/tool-python-roblox-ip && python main.py
```

### Cách 4: Chạy trên máy tính (PC / Windows / Linux)
```bash
python pyobfuscate_com.py
```

---

## 📁 Cấu trúc thư mục

```text
├── SetupRobloxIP              # Script cài đặt 1 chạm nhanh cho Android / Termux
├── run.sh                     # Trình điều khiển CLI Runner trung tâm
├── controller.py              # MASTER CONTROLLER: Menu điều khiển trung tâm toàn bộ tool
├── main.py                    # Entrypoint chạy trực tiếp Live Dashboard
├── requirements.txt           # Danh sách thư viện Python yêu cầu
├── config/
│   ├── settings.py            # Cấu hình chung, timeouts, paths
│   ├── devices.py             # Khai báo loại thiết bị & cấu hình Region (Japan, HK, SG, VN)
│   ├── profiles.py            # Định nghĩa cấu hình network profiles
│   └── logging.py             # Cấu hình Logger & log rotation
├── database/
│   ├── sqlite.py              # SQLite Connection Manager & Auto Migrations
│   ├── models.py              # Cấu trúc bảng (Instances, Snapshots, Events)
│   └── repository.py          # CRUD operations & Query helpers
├── core/
│   ├── manager.py             # Điều phối trung tâm các Instance & Dedicated IP Binding
│   ├── scheduler.py           # Lập lịch giám sát & ping tự động
│   ├── process_manager.py     # Quản lý PID, subprocess & watchdog
│   └── health_manager.py      # Đánh giá sức khỏe kết nối mạng
├── network/
│   ├── allocator.py           # Quản lý cấp phát Dedicated IP riêng biệt cho từng tag
│   ├── ip_generator.py        # Module sinh IP ngẫu nhiên dạng a.b.c.d
│   ├── interface.py           # Đọc thông tin card mạng (wlan0, rmnet, etc.)
│   ├── connectivity.py        # Kiểm tra kết nối Internet & Public IP
│   ├── dns.py                 # Phân giải DNS & đo thời gian query
│   └── diagnostics.py         # Chẩn đoán chi tiết (MTU, routing, hops)
├── monitoring/
│   ├── ping.py                # Đo Ping ICMP / Socket ping
│   ├── latency.py             # Phân tích độ trễ & jitter
│   ├── packet_loss.py         # Đo tỷ lệ rớt gói tin
│   └── status.py              # Tổng hợp trạng thái ONLINE/OFFLINE/DEGRADED
├── devices/
│   ├── base.py                # Base class cho Android Instance
│   ├── instances.py           # Drivers: UGPhone, VMOS, Redfinger, VSPhone
├── profiles/
│   ├── manager.py             # Quản lý và validate network profiles
├── cli/
│   ├── colors.py              # Bảng màu ANSI & định dạng giao diện
│   ├── status.py              # Render Dashboard TUI đẹp mắt
├── shell/
│   ├── config.sh              # Cấu hình môi trường Shell & biến hệ thống
│   ├── install.sh             # Trình cài đặt đa nền tảng
│   ├── termux_setup.sh        # Tự động cấu hình Termux & khởi chạy
│   ├── root_launcher.sh       # Trình khởi chạy quyền Root (SU)
│   └── network.sh             # Trích xuất thông số mạng từ Linux kernel
└── tests/
    └── test_all.py            # Bộ kiểm thử tự động toàn diện
```
