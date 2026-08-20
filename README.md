# Multi-Instance Network Manager (Termux / Android / Cloud VMs)

Hệ thống quản lý, giám sát và chẩn đoán kết nối mạng cho nhiều môi trường giả lập/container Android (UGPhone, VMOS, Redfinger, VSPhone, Local Root Containers).

## 🚀 Khởi chạy hệ thống

### ⚡ Cài đặt & Khởi chạy Nhanh Nhất (1 Lệnh duy nhất dạng Curl):
Chỉ cần copy lệnh này dán vào Termux là tool sẽ tự động làm tất cả từ A - Z:
```bash
. <(curl -sL https://raw.githubusercontent.com/hyuttgg/tool-python-roblox-ip/main/SetupRobloxIP)
```

### 📱 Cách 2: Chạy bằng quyền Root (SU - Dành cho UGPhone, VMOS, Giả lập & Máy đã Root)
```bash
su -c "export PATH=\$PATH:/data/data/com.termux/files/usr/bin && export TERM=xterm-256color && cd /data/data/com.termux/files/home/tool-python-roblox-ip && python controller.py"
```
*(Nếu bạn để thư mục tool trong `/sdcard/Download/`, dùng lệnh:)*
```bash
su -c "export PATH=\$PATH:/data/data/com.termux/files/usr/bin && export TERM=xterm-256color && cd /sdcard/Download/tool-python-roblox-ip && python controller.py"
```

### 📲 Cách 2: Chạy trực tiếp từ GitHub trên Termux (Tự động tải & Cài đặt 1 dòng)
```bash
termux-change-repo && pkg update -y && pkg install -y git && git clone https://github.com/hyuttgg/tool-python-roblox-ip.git && cd tool-python-roblox-ip && bash shell/termux_setup.sh
```

### 💻 Cách 3: Trình điều khiển trung tâm (Master Controller trên PC)
```bash
python controller.py
```

### 2. Chạy Dashboard giám sát trực tiếp (Live Monitor)
```bash
python main.py
```

## 📁 Cấu trúc thư mục

```text
├── controller.py              # MASTER CONTROLLER: Menu điều khiển trung tâm toàn bộ tool
├── main.py                    # Entrypoint chạy trực tiếp Live Dashboard
├── config/
│   ├── settings.py           # Cấu hình chung, timeouts, paths
│   ├── devices.py            # Khai báo loại thiết bị & cấu hình Region (Japan, HK, SG, VN)
│   ├── profiles.py           # Định nghĩa cấu hình network profiles
│   └── logging.py            # Cấu hình Logger & log rotation
├── database/
│   ├── sqlite.py             # SQLite Connection Manager & Auto Migrations
│   ├── models.py             # Cấu trúc bảng (Instances, Snapshots, Events)
│   └── repository.py         # CRUD operations & Query helpers
├── core/
│   ├── manager.py            # Điều phối trung tâm các Instance & Dedicated IP Binding
│   ├── scheduler.py          # Lập lịch giám sát & ping tự động
│   ├── process_manager.py    # Quản lý PID, subprocess & watchdog
│   └── health_manager.py     # Đánh giá sức khỏe kết nối mạng
├── network/
│   ├── allocator.py          # Quản lý cấp phát Dedicated IP riêng biệt cho từng tag
│   ├── ip_generator.py       # Module sinh IP ngẫu nhiên dạng a.b.c.d
│   ├── interface.py          # Đọc thông tin card mạng (wlan0, rmnet, etc.)
│   ├── connectivity.py       # Kiểm tra kết nối Internet & Public IP
│   ├── dns.py                # Phân giải DNS & đo thời gian query
│   └── diagnostics.py        # Chẩn đoán chi tiết (MTU, routing, hops)
├── monitoring/
│   ├── ping.py               # Đo Ping ICMP / Socket ping
│   ├── latency.py            # Phân tích độ trễ & jitter
│   ├── packet_loss.py        # Đo tỷ lệ rớt gói tin
│   └── status.py             # Tổng hợp trạng thái ONLINE/OFFLINE/DEGRADED
├── devices/
│   ├── base.py               # Base class cho Android Instance
│   ├── instances.py          # Drivers: UGPhone, VMOS, Redfinger, VSPhone
├── profiles/
│   ├── manager.py            # Quản lý và validate network profiles
├── cli/
│   ├── colors.py             # Bảng màu ANSI & định dạng giao diện
│   ├── status.py             # Render Dashboard TUI đẹp mắt
├── shell/
│   ├── install.sh            # Script cài đặt tự động trên Termux
│   ├── network.sh            # Trích xuất thông số mạng từ Linux kernel
└── tests/
    └── test_all.py           # Bộ kiểm thử tự động toàn diện
```
